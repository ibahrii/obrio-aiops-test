"""Disk cache for model responses.

Key = sha256(normalized ticket text + model + prompt version + kb version + schema).
Only the hash is used as a filename, so ticket text never appears in paths.
Any change of model / prompt / taxonomy / KB version yields a new key -> natural invalidation.
Entries older than the TTL are ignored and overwritten.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata

from . import config


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def make_key(*, text: str, model: str, prompt_version: str, kb_version: str = "", schema: str = "") -> str:
    raw = "\x1f".join([normalize_text(text), model, prompt_version, kb_version, schema, config.TAXONOMY_VERSION])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _path(key: str):
    return config.CACHE_DIR / key[:2] / f"{key}.json"


def get(key: str, ttl_s: float | None = None) -> dict | None:
    p = _path(key)
    if not p.exists():
        return None
    try:
        entry = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    ttl = config.CACHE_TTL_S if ttl_s is None else ttl_s
    if time.time() - entry.get("created_at", 0) > ttl:
        return None
    return entry


def put(key: str, payload: dict) -> None:
    p = _path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "created_at": time.time()}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
