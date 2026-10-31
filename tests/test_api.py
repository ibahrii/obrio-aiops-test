import base64
import hashlib
import hmac
import json
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import api, config, llm  # noqa: E402
from eval.simulate_failures import GOOD  # noqa: E402

P1_SAFE = {**GOOD, "category": "account_access", "priority": "P1", "next_step": {"route_to": "Tech", "action": "Secure account"}}
GDPR = {**GOOD, "category": "privacy_legal", "priority": "P2", "next_step": {"route_to": "Legal & Privacy", "action": "Forward"}}


def zendesk(tid, text, name="Anna Kovalenko", email="anna@example.com"):
    return {"ticket": {"id": tid, "subject": "Help", "description": text, "requester": {"name": name, "email": email},
                       "via": {"channel": "email"}}}


def intercom(cid, html_body, name="Lucía Pérez"):
    return {"type": "notification_event", "topic": "conversation.user.created",
            "data": {"item": {"type": "conversation", "id": cid,
                              "source": {"subject": "", "body": html_body, "author": {"type": "user", "name": name}}}}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    sent = []

    def transport(spec, system, messages, schema):
        content = messages[-1]["content"]
        sent.append(content)
        body = P1_SAFE if "hacked" in content else GDPR if "delete" in content else GOOD
        return llm.RawResponse(text=json.dumps(body), in_tokens=1, out_tokens=1)

    monkeypatch.setattr(llm, "TRANSPORT_OVERRIDE", transport)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setenv("ROUTER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    return {"client": TestClient(api.app), "sent": sent, "tmp": tmp_path}


def notifications(tmp):
    p = tmp / "logs" / "notifications.log"
    return p.read_text().splitlines() if p.exists() else []


def test_p1_alerts_once_even_if_webhook_is_redelivered(env):
    c, payload = env["client"], zendesk(101, "My account was hacked, card 4111 1111 1111 1111. Anna Kovalenko")
    first = c.post("/webhook/ticket", json=payload).json()
    assert first["duplicate"] is False and first["classification"]["priority"] == "P1"
    assert [a["type"] for a in first["actions"]] == ["p1_alert", "crm_csv"]
    assert first["actions"][0]["channel"] == "log"  # Telegram env not set -> logged instead of sent
    second = c.post("/webhook/ticket", json=payload).json()
    assert second["duplicate"] is True and second["previous_result"]["ticket_id"] == "zendesk:101"
    assert len(notifications(env["tmp"])) == 1
    assert len(env["sent"]) == 1  # the duplicate did not even call the LLM
    log_line = notifications(env["tmp"])[0]
    assert "4111" not in log_line and "Kovalenko" not in log_line


def test_needs_human_goes_to_review_queue_not_csv(env):
    r = env["client"].post("/webhook/ticket", json=intercom("c-7", "<p>Please delete my data</p><p>Lucía</p>")).json()
    assert r["ticket_id"] == "intercom:c-7" and r["classification"]["needs_human"] is True
    assert [a["type"] for a in r["actions"]] == ["review_queue"]
    queue = [json.loads(l) for l in (env["tmp"] / "state" / "review_queue.jsonl").read_text().splitlines()]
    assert queue[0]["ticket_id"] == "intercom:c-7" and "<p>" not in queue[0]["text"]
    assert "Lucía" not in queue[0]["text"] and "Lucía" not in env["sent"][0]  # CRM requester name masked
    assert not (env["tmp"] / "state" / "crm_tickets.csv").exists()


def test_routine_ticket_written_to_crm_csv(env):
    env["client"].post("/webhook/ticket", json=zendesk(7, "How do I cancel on Android?"))
    rows = (env["tmp"] / "state" / "crm_tickets.csv").read_text().splitlines()
    assert rows[0].startswith("ticket_id,") and rows[1].startswith("zendesk:7,zendesk,")


def test_unknown_format_is_rejected(env):
    assert env["client"].post("/webhook/ticket", json={"foo": 1}).status_code == 422


def test_classify_endpoint_returns_masked_text(env):
    r = env["client"].post("/classify", json={"text": "I'm locked out, write to bob@mail.com"}).json()
    assert r["masked_text"] == "I'm locked out, write to [EMAIL]" and "bob@mail.com" not in env["sent"][0]
    assert r["classification"]["category"] == "billing_subscription"


def test_webhook_signature(env, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    body = json.dumps(zendesk(55, "How do I cancel?")).encode()
    assert env["client"].post("/webhook/ticket", content=body).status_code == 401
    ts = "2026-10-31T10:00:00Z"
    sig = base64.b64encode(hmac.new(b"s3cret", ts.encode() + body, hashlib.sha256).digest()).decode()
    ok = env["client"].post("/webhook/ticket", content=body, headers={
        "X-Zendesk-Webhook-Signature": sig, "X-Zendesk-Webhook-Signature-Timestamp": ts})
    assert ok.status_code == 200


def test_failed_processing_can_be_retried(env, monkeypatch):
    real, fail = api.router.classifier.classify, [True]

    def flaky(*a, **k):
        if fail.pop() if fail else False:
            raise RuntimeError("crash before routing")
        return real(*a, **k)

    monkeypatch.setattr(api.router.classifier, "classify", flaky)
    client = TestClient(api.app, raise_server_exceptions=False)
    assert client.post("/webhook/ticket", json=zendesk(9, "hello")).status_code == 500
    # the claim was released, so the CRM's retry is processed instead of being treated as a duplicate
    assert client.post("/webhook/ticket", json=zendesk(9, "hello")).json()["duplicate"] is False


def test_telegram_send_path(env, monkeypatch):
    calls = []

    class Resp:
        status_code = 200

        def json(self):
            return {"ok": True}

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        return Resp()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100500")
    monkeypatch.setattr(api.router.httpx, "post", fake_post)
    r = env["client"].post("/webhook/ticket", json=zendesk(77, "My account was hacked, call +44 7700 900123")).json()
    assert r["actions"][0] == {"type": "p1_alert", "channel": "telegram", "status": "sent"}
    url, body = calls[0]
    assert url == "https://api.telegram.org/bot123:abc/sendMessage" and body["chat_id"] == "-100500"
    assert "7700" not in body["text"] and "[PHONE]" in body["text"]
    assert not notifications(env["tmp"])  # sent, so nothing logged instead
