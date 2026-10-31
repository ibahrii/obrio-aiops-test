"""End-to-end demo: 5 CRM webhooks (Zendesk / Intercom) -> HTTP API -> PII masking -> LLM -> routing.

  python eval/webhook_demo.py   -> eval/results/webhook_demo.md (+ eval/results/webhook_demo/ artefacts)

Starts the real FastAPI app under uvicorn on localhost, posts the webhooks over HTTP, then re-delivers the first
one to show idempotency. Real LLM calls (Gemini Flash-Lite, fallback on). The outgoing request to the provider is
recorded by wrapping llm.raw_call in this process, to show that only masked text leaves the service.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
import threading
import time

import httpx
import uvicorn

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

STATE = pathlib.Path(tempfile.mkdtemp(prefix="router_state_"))
os.environ["ROUTER_STATE_DIR"] = str(STATE)
os.environ.pop("TELEGRAM_BOT_TOKEN", None)

from src import api, config, llm  # noqa: E402

PORT = 8765
OUT_DIR = config.RESULTS_DIR / "webhook_demo"
SENT: list[dict] = []
_orig_raw_call = llm.raw_call


def recording_raw_call(spec, system, messages, schema):
    SENT.append({"model": spec.key, "user_message": messages[-1]["content"]})
    return _orig_raw_call(spec, system, messages, schema)


def zendesk(tid, subject, text, name, email):
    return {"ticket": {"id": tid, "subject": subject, "description": text, "status": "new",
                       "requester": {"name": name, "email": email}, "via": {"channel": "email"}}}


def intercom(cid, html, name, email):
    return {"type": "notification_event", "topic": "conversation.user.created", "app_id": "demo",
            "data": {"item": {"type": "conversation", "id": cid,
                              "source": {"subject": "", "body": html,
                                         "author": {"type": "user", "name": name, "email": email}}}}}


WEBHOOKS = [
    ("Zendesk: double charge, card + phone + signature",
     zendesk(48213, "Charged twice!",
             "Hello, I see two identical charges of $29.99 on my card 4111 1111 1111 1111 from Oct 28. "
             "I only have one subscription. You can call me on +44 7700 900123.\nRegards,\nOliver Bennett",
             "Oliver Bennett", "oliver.bennett@example.com")),
    ("Intercom: indirect crisis",
     intercom("215467", "<p>Hi, it's Daria. Lately I feel like nothing matters and maybe everyone would be better off "
                        "without me.</p><p>Also how do I turn off the daily notifications?</p>",
              "Daria Melnyk", "daria.m@example.com")),
    ("Zendesk: cancel on Android, email in body",
     zendesk(48215, "Cancel", "How do I cancel my subscription on Android? My account email is mark.t@example.com.",
             "Mark Taylor", "mark.t@example.com")),
    ("Intercom: GDPR deletion in Ukrainian, phone + intro",
     intercom("215470", "<p>Добрий день! Мене звати Олена Шевчук. Прошу видалити мій акаунт і всі мої дані. "
                        "Мій телефон +380 67 123 4567.</p>", "Олена Шевчук", "olena.sh@example.com")),
    ("Zendesk: praise",
     zendesk(48217, "Thank you", "The new moon calendar is lovely, thank you for adding it!\nCheers,\nSam",
             "Sam Lee", "sam.lee@example.com")),
]


def main() -> None:
    llm.raw_call = recording_raw_call
    config.LOG_DIR = STATE / "logs"
    server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.1)

    base = f"http://127.0.0.1:{PORT}"
    results = []
    for title, payload in WEBHOOKS + [("Zendesk: SAME ticket 48213 re-delivered", WEBHOOKS[0][1])]:
        n_before = len(SENT)
        t0 = time.perf_counter()
        r = httpx.post(f"{base}/webhook/ticket", json=payload, timeout=120)
        r.raise_for_status()
        results.append((title, r.json(), round(time.perf_counter() - t0, 2), SENT[n_before:]))
        print(title, "->", json.dumps(r.json(), ensure_ascii=False)[:200])
    server.should_exit = True

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("review_queue.jsonl", "crm_tickets.csv"):
        if (STATE / name).exists():
            shutil.copy(STATE / name, OUT_DIR / name)
    notif = STATE / "logs" / "notifications.log"
    if notif.exists():
        shutil.copy(notif, OUT_DIR / "notifications.log")
    (OUT_DIR / "llm_requests.json").write_text(json.dumps(SENT, indent=1, ensure_ascii=False), encoding="utf-8")
    write_report(results)


def write_report(results) -> None:
    md = ["# Webhook end-to-end demo", "",
          f"Real HTTP calls to `uvicorn src.api:app` on localhost; real LLM calls ({config.DEFAULT_MODEL}, fallback on); "
          "Telegram variables not set, so P1 alerts go to the notification log. Artefacts: `eval/results/webhook_demo/`.", "",
          "| # | webhook | ticket_id | PII masked | category / priority | needs_human | actions | LLM calls | time, s |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, (title, r, secs, sent) in enumerate(results, 1):
        if r["duplicate"]:
            md.append(f"| {i} | {title} | {r['ticket_id']} | — | — | — | **duplicate: no side effects** | {len(sent)} | {secs} |")
            continue
        c = r["classification"]
        acts = ", ".join(f"{a['type']} ({a.get('channel', a.get('status'))})" for a in r["actions"])
        md.append(f"| {i} | {title} | {r['ticket_id']} | {r['pii_masked'] or '—'} | {c['category']}"
                  f"{' + ' + c['secondary_category'] if c['secondary_category'] else ''} / {c['priority']} | "
                  f"{c['needs_human']} | {acts} | {len(sent)} | {secs} |")
    md += ["", "## What the model actually received", "",
           "Recorded at `llm.raw_call`, i.e. the last point before the HTTP request to the provider:", ""]
    for i, (title, r, secs, sent) in enumerate(results, 1):
        for s in sent:
            ticket = s["user_message"].split("<ticket>")[-1].split("</ticket>")[0].strip()
            md.append(f"**#{i} {title}** → `{s['model']}`\n```\n{ticket}\n```")
    md += ["", "## Routing outputs", ""]
    for name in ("notifications.log", "review_queue.jsonl", "crm_tickets.csv"):
        p = OUT_DIR / name
        md += [f"**{name}**", "```", p.read_text(encoding="utf-8").strip() if p.exists() else "(empty)", "```", ""]
    (config.RESULTS_DIR / "webhook_demo.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("saved eval/results/webhook_demo.md")


if __name__ == "__main__":
    main()
