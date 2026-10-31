"""Webhook ingestion and post-classification routing (no n8n: plain Python).

  P1            -> Telegram message (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID), or a log line if they are not set
  needs_human   -> review queue (data/runtime/review_queue.jsonl, shown in the Streamlit Review queue)
  everything else -> CRM write, simulated as a row in data/runtime/crm_tickets.csv

A P1 ticket is notified AND lands in the queue or the CSV, so nothing is handled by the alert alone.
Idempotency: a ticket_id is claimed in SQLite before any side effect; a re-delivered webhook returns the
stored result and triggers nothing. Each side effect is additionally keyed by (ticket_id, action) so a retry
after a crash mid-way cannot send a second Telegram message.
Only masked text is written to the queue, the CSV, the log and Telegram.
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import logging
import os
import pathlib
import re
import sqlite3
import threading
from contextlib import contextmanager

import httpx
from pydantic import BaseModel

from . import classifier, config, pii

log = logging.getLogger("router")
_lock = threading.Lock()

CSV_FIELDS = ["ticket_id", "source", "received_at", "category", "secondary_category", "priority", "route_to",
              "action", "confidence", "language", "requester_type"]


class Ticket(BaseModel):
    ticket_id: str
    source: str
    subject: str = ""
    body: str = ""
    requester_name: str = ""
    requester_email: str = ""

    @property
    def text(self) -> str:
        return f"{self.subject}\n{self.body}".strip() if self.subject else self.body.strip()


class WebhookFormatError(ValueError):
    pass


def state_dir() -> pathlib.Path:
    d = pathlib.Path(os.getenv("ROUTER_STATE_DIR", str(config.DATA_DIR / "runtime")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>|</p>", "\n", s or "", flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# --------------------------------------------------------------------------- parsing
def parse_webhook(payload: dict) -> Ticket:
    """Zendesk-style {"ticket": {...}}, Intercom-style notification_event, or generic {"ticket_id","text"}."""
    if isinstance(payload.get("ticket"), dict):  # Zendesk trigger/webhook body
        t = payload["ticket"]
        if "id" not in t:
            raise WebhookFormatError("zendesk payload without ticket.id")
        req = t.get("requester") or {}
        return Ticket(ticket_id=f"zendesk:{t['id']}", source="zendesk", subject=t.get("subject") or "",
                      body=t.get("description") or t.get("comment", {}).get("body", "") or "",
                      requester_name=req.get("name") or "", requester_email=req.get("email") or "")
    if payload.get("type") == "notification_event":  # Intercom webhook
        item = (payload.get("data") or {}).get("item") or {}
        src = item.get("source") or {}
        author = src.get("author") or {}
        if "id" not in item:
            raise WebhookFormatError("intercom payload without data.item.id")
        return Ticket(ticket_id=f"intercom:{item['id']}", source="intercom", subject=_strip_html(src.get("subject", "")),
                      body=_strip_html(src.get("body", "")), requester_name=author.get("name") or "",
                      requester_email=author.get("email") or "")
    if "ticket_id" in payload and "text" in payload:
        return Ticket(ticket_id=f"generic:{payload['ticket_id']}", source="generic", body=payload["text"],
                      requester_name=payload.get("requester_name", ""))
    raise WebhookFormatError("unknown webhook format (expected Zendesk, Intercom or {ticket_id, text})")


# --------------------------------------------------------------------------- idempotency store
@contextmanager
def _db():
    """Serialised, committed and closed SQLite connection."""
    with _lock:
        con = sqlite3.connect(state_dir() / "router.sqlite", timeout=10)
        try:
            con.execute("CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, status TEXT, result TEXT, "
                        "created_at TEXT, updated_at TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS side_effects (ticket_id TEXT, action TEXT, status TEXT, "
                        "created_at TEXT, PRIMARY KEY (ticket_id, action))")
            yield con
            con.commit()
        finally:
            con.close()


def _claim(ticket_id: str) -> dict | None:
    """Insert ticket_id as 'processing'. Returns None if claimed now, else the existing row."""
    with _db() as con:
        try:
            con.execute("INSERT INTO tickets VALUES (?, 'processing', NULL, ?, ?)", (ticket_id, _now(), _now()))
            return None
        except sqlite3.IntegrityError:
            status, result = con.execute("SELECT status, result FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            return {"status": status, "result": json.loads(result) if result else None}


def _finish(ticket_id: str, result: dict) -> None:
    with _db() as con:
        con.execute("UPDATE tickets SET status='done', result=?, updated_at=? WHERE ticket_id=?",
                    (json.dumps(result, ensure_ascii=False), _now(), ticket_id))


def _release(ticket_id: str) -> None:
    """Processing failed before completion: let the CRM's webhook retry process it again."""
    with _db() as con:
        con.execute("DELETE FROM tickets WHERE ticket_id=? AND status='processing'", (ticket_id,))


def _once(ticket_id: str, action: str) -> bool:
    """True exactly once per (ticket_id, action)."""
    with _db() as con:
        cur = con.execute("INSERT OR IGNORE INTO side_effects VALUES (?, ?, 'done', ?)", (ticket_id, action, _now()))
        return cur.rowcount == 1


# --------------------------------------------------------------------------- side effects
def notify_telegram(message: str) -> dict:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        line = f"{_now()} TELEGRAM (not configured, logged instead): {message}"
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.LOG_DIR / "notifications.log", "a", encoding="utf-8") as f:
            f.write(line.replace("\n", " | ") + "\n")
        log.warning(line)
        return {"channel": "log", "status": "logged"}
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                       json={"chat_id": chat, "text": message, "disable_web_page_preview": True}, timeout=10)
        ok = r.status_code == 200 and r.json().get("ok")
        return {"channel": "telegram", "status": "sent" if ok else f"failed: HTTP {r.status_code}"}
    except httpx.HTTPError as e:  # never log the token-bearing URL
        return {"channel": "telegram", "status": f"failed: {type(e).__name__}"}


def _p1_message(t: Ticket, c, masked_text: str) -> str:
    reasons = "; ".join(c.human_reasons) or "—"
    return (f"🚨 P1 ticket {t.ticket_id} ({t.source})\n{c.category}"
            f"{' + ' + c.secondary_category if c.secondary_category else ''} → {c.next_step.route_to}\n"
            f"Action: {c.next_step.action}\nHuman review: {'yes' if c.needs_human else 'no'} ({reasons})\n\n"
            f"{masked_text[:300]}")


def _append_queue(t: Ticket, c, masked_text: str) -> None:
    rec = {"ticket_id": t.ticket_id, "source": t.source, "received_at": _now(), "text": masked_text,
           "category": c.category, "secondary_category": c.secondary_category, "priority": c.priority,
           "reasons": c.human_reasons, "route_to": c.next_step.route_to, "model": c.meta.get("model"),
           "prompt": config.CLASSIFIER_PROMPT_VERSION}
    with _lock, open(state_dir() / "review_queue.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _append_csv(t: Ticket, c) -> None:
    p = state_dir() / "crm_tickets.csv"
    with _lock:
        new = not p.exists()
        with open(p, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if new:
                w.writeheader()
            w.writerow({"ticket_id": t.ticket_id, "source": t.source, "received_at": _now(), "category": c.category,
                        "secondary_category": c.secondary_category or "", "priority": c.priority,
                        "route_to": c.next_step.route_to, "action": c.next_step.action,
                        "confidence": c.confidence, "language": c.language, "requester_type": c.requester_type})


def route(t: Ticket, c, masked_text: str) -> list[dict]:
    actions = []
    if c.priority == "P1":
        if _once(t.ticket_id, "telegram"):
            actions.append({"type": "p1_alert", **notify_telegram(_p1_message(t, c, masked_text))})
        else:
            actions.append({"type": "p1_alert", "status": "skipped: already sent"})
    if c.needs_human:
        if _once(t.ticket_id, "review_queue"):
            _append_queue(t, c, masked_text)
        actions.append({"type": "review_queue", "status": "queued", "reasons": c.human_reasons})
    else:
        if _once(t.ticket_id, "crm_csv"):
            _append_csv(t, c)
        actions.append({"type": "crm_csv", "status": "written", "route_to": c.next_step.route_to})
    return actions


# --------------------------------------------------------------------------- entry point
def process(t: Ticket, model_key: str | None = None) -> dict:
    existing = _claim(t.ticket_id)
    if existing:
        return {"ticket_id": t.ticket_id, "duplicate": True, "status": existing["status"],
                "previous_result": existing["result"]}
    try:
        names = tuple(n for n in (t.requester_name,) if n)
        masked = pii.mask(t.text, names)
        c = classifier.classify(t.text, model_key=model_key, known_names=names)
        result = {
            "ticket_id": t.ticket_id, "duplicate": False, "source": t.source,
            "masked_text": masked.text, "pii_masked": masked.counts,
            "classification": {
                "category": c.category, "secondary_category": c.secondary_category, "priority": c.priority,
                "needs_human": c.needs_human, "human_reasons": c.human_reasons, "route_to": c.next_step.route_to,
                "action": c.next_step.action, "confidence": c.confidence, "language": c.language,
                "model": c.meta.get("model"), "fallback_used": c.meta.get("fallback_used"),
            },
            "actions": route(t, c, masked.text),
        }
    except Exception:
        _release(t.ticket_id)
        raise
    _finish(t.ticket_id, result)
    return result
