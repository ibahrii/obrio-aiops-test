"""FastAPI service: CRM webhook + classify/assist endpoints.

  uvicorn src.api:app --port 8000

POST /webhook/ticket  Zendesk / Intercom / generic payload -> classify -> route (idempotent by ticket_id)
POST /classify        {"text": ...} -> classification (+ the masked text that was sent to the LLM)
POST /assist          {"text": ...} -> agent-assistant drafts
GET  /health

If WEBHOOK_SECRET is set, /webhook/ticket requires a valid HMAC signature:
Zendesk (X-Zendesk-Webhook-Signature = base64 HMAC-SHA256 of timestamp+body),
Intercom (X-Hub-Signature = "sha1=" + hex HMAC-SHA1 of body) or generic X-Signature (hex HMAC-SHA256 of body).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import assistant, classifier, config, pii, router

app = FastAPI(title="Nebula Support AI", version="1.0")


class TextIn(BaseModel):
    text: str = Field(min_length=1)
    model: str | None = None
    requester_name: str | None = None


def _check_model(model: str | None) -> str | None:
    if model and model not in config.MODELS:
        raise HTTPException(422, f"unknown model {model!r}; one of {list(config.MODELS)}")
    return model


def _verify_signature(request: Request, body: bytes) -> None:
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        return
    key, h = secret.encode(), request.headers
    candidates = []
    if "x-zendesk-webhook-signature" in h:
        ts = h.get("x-zendesk-webhook-signature-timestamp", "").encode()
        expected = base64.b64encode(hmac.new(key, ts + body, hashlib.sha256).digest()).decode()
        candidates.append((h["x-zendesk-webhook-signature"], expected))
    if "x-hub-signature" in h:
        candidates.append((h["x-hub-signature"], "sha1=" + hmac.new(key, body, hashlib.sha1).hexdigest()))
    if "x-signature" in h:
        candidates.append((h["x-signature"], hmac.new(key, body, hashlib.sha256).hexdigest()))
    if not any(hmac.compare_digest(got, exp) for got, exp in candidates):
        raise HTTPException(401, "invalid or missing webhook signature")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "default_model": config.DEFAULT_MODEL, "classifier_prompt": config.CLASSIFIER_PROMPT_VERSION,
            "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))}


@app.post("/webhook/ticket")
async def webhook_ticket(request: Request) -> dict:
    body = await request.body()
    _verify_signature(request, body)
    try:
        ticket = router.parse_webhook(json.loads(body))
    except (json.JSONDecodeError, router.WebhookFormatError, AttributeError) as e:
        raise HTTPException(422, str(e))
    # the LLM call is blocking: run it in the threadpool instead of the event loop
    return await run_in_threadpool(router.process, ticket, _check_model(request.query_params.get("model")))


@app.post("/classify")
def classify(inp: TextIn) -> dict:
    names = (inp.requester_name,) if inp.requester_name else ()
    masked = pii.mask(inp.text, names)
    r = classifier.classify(inp.text, model_key=_check_model(inp.model), known_names=names)
    out = r.model_dump()
    out["meta"] = {k: v for k, v in r.meta.items() if k not in ("attempts", "model_raw")}
    return {"masked_text": masked.text, "pii_masked": masked.counts, "classification": out}


@app.post("/assist")
def assist(inp: TextIn) -> dict:
    names = (inp.requester_name,) if inp.requester_name else ()
    masked = pii.mask(inp.text, names)
    r = assistant.assist(inp.text, model_key=_check_model(inp.model), known_names=names)
    out = r.model_dump(exclude={"classification"})
    out["meta"] = {k: v for k, v in r.meta.items() if k != "attempts"}
    out["classification"] = {"category": r.classification.category, "priority": r.classification.priority,
                             "needs_human": r.classification.needs_human} if r.classification else None
    return {"masked_text": masked.text, "pii_masked": masked.counts, "result": out}
