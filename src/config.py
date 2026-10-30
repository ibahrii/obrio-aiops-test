"""Central configuration: models, prices, rate limits, prompt/KB versions.

Model IDs were picked from the providers' /models listings on 2026-10-30
(see eval/results/env_check.md), not from memory.
"""
from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
KB_DIR = DATA_DIR / "kb"
RESULTS_DIR = ROOT / "eval" / "results"
CACHE_DIR = ROOT / ".cache" / "llm"
LOG_DIR = ROOT / "logs"
CORRECTIONS_PATH = DATA_DIR / "corrections.jsonl"
PRICING_SNAPSHOT = RESULTS_DIR / "pricing_snapshot.json"

# Versions are part of every cache key: bumping any of them invalidates cached answers.
CLASSIFIER_PROMPT_VERSION = os.getenv("CLASSIFIER_PROMPT_VERSION", "v4")
ASSISTANT_PROMPT_VERSION = os.getenv("ASSISTANT_PROMPT_VERSION", "v2")
TAXONOMY_VERSION = "2026-10-30"
KB_VERSION = "kb-2026-10-30"

REQUEST_TIMEOUT_S = 20.0
TIMEOUT_RETRIES = 2          # extra attempts after a timeout / 5xx, exponential backoff
RATE_LIMIT_RETRIES = 2       # extra attempts after 429, honouring Retry-After
MAX_RETRY_AFTER_S = 30.0     # never sleep longer than this on a single 429
CACHE_TTL_S = 30 * 24 * 3600  # eval cache; in prod this would be hours, see REPORT.md

CONFIDENCE_THRESHOLD = 0.9   # chosen on eval data (threshold sweep), see REPORT.md section 9


@dataclass(frozen=True)
class ModelSpec:
    key: str               # short name used across the repo
    provider: str          # gemini | groq | openrouter
    api_id: str            # id sent to the provider API
    label: str
    min_interval_s: float  # pacing between live calls (free-tier RPM/TPM)
    pricing_id: str        # key in pricing_snapshot.json
    extra: dict = field(default_factory=dict)


MODELS: dict[str, ModelSpec] = {
    "gemini-flash": ModelSpec(
        "gemini-flash", "gemini", "gemini-3.8-flash", "Gemini 3.8 Flash",
        min_interval_s=7.0, pricing_id="google/gemini-3.8-flash",
        extra={"thinking_level": "low"},
    ),
    "gemini-flash-3.6": ModelSpec(
        "gemini-flash-3.6", "gemini", "gemini-3.6-flash", "Gemini 3.6 Flash",
        min_interval_s=7.0, pricing_id="google/gemini-3.6-flash",
        extra={"thinking_level": "low"},
    ),
    "gemini-flash-lite": ModelSpec(
        "gemini-flash-lite", "gemini", "gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite",
        min_interval_s=4.5, pricing_id="google/gemini-3.5-flash-lite",
    ),
    "groq-gpt-oss-120b": ModelSpec(
        "groq-gpt-oss-120b", "groq", "openai/gpt-oss-120b", "GPT-OSS-120B (Groq)",
        min_interval_s=2.0, pricing_id="openai/gpt-oss-120b",
        extra={"reasoning_effort": "low"},
    ),
    "groq-gpt-oss-20b": ModelSpec(
        "groq-gpt-oss-20b", "groq", "openai/gpt-oss-20b", "GPT-OSS-20B (Groq)",
        min_interval_s=2.0, pricing_id="openai/gpt-oss-20b",
        extra={"reasoning_effort": "low"},
    ),
    "openrouter-nemotron-free": ModelSpec(
        "openrouter-nemotron-free", "openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free",
        "Nemotron 3 Ultra 550B (OpenRouter :free)",
        min_interval_s=4.0, pricing_id="nvidia/nemotron-3-ultra-550b-a55b",
    ),
}

# Default production chain (decided on eval data, see REPORT.md section 5).
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-flash-lite")
FALLBACK_CHAIN: dict[str, list[str]] = {
    "gemini-flash": ["groq-gpt-oss-120b", "gemini-flash-lite"],
    "gemini-flash-3.6": ["groq-gpt-oss-120b", "gemini-flash-lite"],
    "gemini-flash-lite": ["groq-gpt-oss-120b", "gemini-flash"],
    "groq-gpt-oss-120b": ["gemini-flash-lite", "groq-gpt-oss-20b"],
    "groq-gpt-oss-20b": ["groq-gpt-oss-120b", "gemini-flash-lite"],
    "openrouter-nemotron-free": ["gemini-flash-lite", "groq-gpt-oss-120b"],
}

PROVIDER_ENV = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


def get_api_key(provider: str) -> str | None:
    """Env var first, then Streamlit secrets (for Community Cloud). Never logged."""
    name = PROVIDER_ENV[provider]
    val = os.getenv(name)
    if val:
        return val
    try:  # streamlit is optional for CLI scripts
        import streamlit as st
        return st.secrets.get(name)  # type: ignore[no-any-return]
    except Exception:
        return None


def load_prices() -> dict[str, dict]:
    """USD per 1M tokens, paid tier, from the snapshot fetched by eval/fetch_prices.py."""
    snap = json.loads(PRICING_SNAPSHOT.read_text())
    out = {}
    for key, spec in MODELS.items():
        chosen = snap["models"][spec.pricing_id]["chosen"]
        out[key] = {
            "input": chosen["input_per_1m"],
            "output": chosen["output_per_1m"],
            "cached_input": chosen["cached_input_per_1m"],
            "source": f"{chosen['provider']} via OpenRouter endpoints API, {snap['fetched_at'][:10]}",
        }
    return out
