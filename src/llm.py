"""LLM provider clients with retries, timeouts, fallback chain, disk cache and token accounting.

Failure policy (per model in the chain):
  * timeout / 5xx / network  -> up to TIMEOUT_RETRIES extra attempts, exponential backoff
  * 429 rate limit           -> honour Retry-After (capped), up to RATE_LIMIT_RETRIES extra attempts
  * invalid JSON / schema    -> exactly 1 repair attempt with the validation error fed back
  * still failing            -> next model in the fallback chain
  * chain exhausted          -> caller receives ok=False and applies a safe default
Every failure is appended to logs/failures.jsonl (no ticket text, only event metadata).
"""
from __future__ import annotations

import copy
import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Type

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import RetryCallState, Retrying, retry_if_exception_type

from . import cache, config


# --------------------------------------------------------------------------- errors
class LLMError(Exception):
    kind = "error"

    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


class LLMTimeout(LLMError):
    kind = "timeout"


class LLMServerError(LLMError):
    kind = "server_error"


class LLMRateLimit(LLMError):
    kind = "rate_limit"


class LLMClientError(LLMError):
    """4xx other than 429: bad request, auth, unknown model. Not retried."""
    kind = "client_error"


class LLMNoKey(LLMError):
    kind = "no_api_key"


# --------------------------------------------------------------------------- data
@dataclass
class RawResponse:
    text: str
    in_tokens: int = 0
    out_tokens: int = 0          # billed output incl. thinking/reasoning
    thinking_tokens: int = 0
    cached_tokens: int = 0
    latency_s: float = 0.0
    model_version: str = ""


@dataclass
class StructuredResult:
    ok: bool
    data: Optional[dict] = None
    model: Optional[str] = None            # model key that produced `data`
    requested_model: str = ""
    from_cache: bool = False
    fallback_used: bool = False
    valid_first_try: Optional[bool] = None  # of the requested model's first response
    strict_json_first_try: Optional[bool] = None
    in_tokens: int = 0
    out_tokens: int = 0
    thinking_tokens: int = 0
    latency_s: float = 0.0                  # wall time of all attempts incl. retry waits (original, if cached)
    api_latency_s: float = 0.0              # HTTP time of the successful call only (model speed)
    attempts: list[dict] = field(default_factory=list)
    raw_text: str = ""

    def meta(self) -> dict:
        return {
            "model": self.model, "requested_model": self.requested_model, "from_cache": self.from_cache,
            "fallback_used": self.fallback_used, "valid_first_try": self.valid_first_try,
            "strict_json_first_try": self.strict_json_first_try,
            "in_tokens": self.in_tokens, "out_tokens": self.out_tokens, "thinking_tokens": self.thinking_tokens,
            "latency_s": round(self.latency_s, 3), "api_latency_s": round(self.api_latency_s, 3),
            "attempts": self.attempts,
        }


# Test hook: if set, called instead of real HTTP -> (spec, system, messages, schema) -> RawResponse
TRANSPORT_OVERRIDE: Optional[Callable[..., RawResponse]] = None
SLEEP: Callable[[float], None] = time.sleep  # patched in tests to keep them fast

_last_call: dict[str, float] = {}
_pace_lock = threading.Lock()
_paced = threading.local()  # seconds spent in free-tier pacing; excluded from reported latency


# --------------------------------------------------------------------------- logging
def log_failure(model: str, kind: str, detail: str, stage: str = "") -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), "model": model, "kind": kind, "stage": stage, "detail": detail[:300]}
    with open(config.LOG_DIR / "failures.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def failure_stats() -> dict:
    p = config.LOG_DIR / "failures.jsonl"
    stats: dict[str, dict[str, int]] = {}
    if not p.exists():
        return stats
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        stats.setdefault(r["kind"], {}).setdefault(r["model"], 0)
        stats[r["kind"]][r["model"]] += 1
    return stats


# --------------------------------------------------------------------------- helpers
def inline_refs(schema: dict) -> dict:
    """Resolve $ref/$defs so every provider gets a flat JSON schema."""
    defs = schema.get("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items() if k not in ("$defs", "title")}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


def extract_json(text: str) -> tuple[Any, bool]:
    """Return (obj, strict). strict=True if the raw text was valid JSON as-is."""
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, TypeError):
        pass
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return json.loads(t[start:end + 1]), False


def _parse_retry_after(resp: httpx.Response) -> float | None:
    h = resp.headers.get("retry-after")
    if h:
        try:
            return float(h)
        except ValueError:
            pass
    try:  # Gemini: error.details[].retryDelay = "13s"
        for d in resp.json().get("error", {}).get("details", []):
            if "retryDelay" in d:
                return float(str(d["retryDelay"]).rstrip("s"))
    except Exception:
        pass
    return None


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    body = resp.text[:300]
    if resp.status_code == 429:
        raise LLMRateLimit(f"429: {body}", retry_after=_parse_retry_after(resp))
    if resp.status_code >= 500:
        raise LLMServerError(f"{resp.status_code}: {body}")
    raise LLMClientError(f"{resp.status_code}: {body}")


def _pace(spec: config.ModelSpec) -> None:
    with _pace_lock:
        wait = spec.min_interval_s - (time.time() - _last_call.get(spec.key, 0))
        if wait > 0 and TRANSPORT_OVERRIDE is None:
            time.sleep(wait)
            _paced.total = getattr(_paced, "total", 0.0) + wait
        _last_call[spec.key] = time.time()


# --------------------------------------------------------------------------- providers
def _call_gemini(spec: config.ModelSpec, system: str, messages: list[dict], schema: dict | None) -> RawResponse:
    key = config.get_api_key("gemini")
    if not key:
        raise LLMNoKey("GEMINI_API_KEY missing")
    gen_cfg: dict[str, Any] = {"temperature": 0}
    if schema:
        gen_cfg["responseMimeType"] = "application/json"
        gen_cfg["responseJsonSchema"] = schema
    if spec.extra.get("thinking_level"):
        gen_cfg["thinkingConfig"] = {"thinkingLevel": spec.extra["thinking_level"]}
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                     for m in messages],
        "generationConfig": gen_cfg,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{spec.api_id}:generateContent"
    t0 = time.perf_counter()
    try:
        resp = httpx.post(url, json=body, headers={"x-goog-api-key": key}, timeout=config.REQUEST_TIMEOUT_S)
    except httpx.TimeoutException as e:
        raise LLMTimeout(f"timeout after {config.REQUEST_TIMEOUT_S}s") from e
    except httpx.TransportError as e:
        raise LLMServerError(f"transport: {type(e).__name__}") from e
    latency = time.perf_counter() - t0
    _raise_for_status(resp)
    d = resp.json()
    cands = d.get("candidates") or []
    if not cands:
        raise LLMServerError(f"no candidates: {str(d.get('promptFeedback'))[:200]}")
    parts = cands[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    u = d.get("usageMetadata", {})
    thinking = u.get("thoughtsTokenCount", 0)
    return RawResponse(
        text=text, in_tokens=u.get("promptTokenCount", 0),
        out_tokens=u.get("candidatesTokenCount", 0) + thinking, thinking_tokens=thinking,
        cached_tokens=u.get("cachedContentTokenCount", 0), latency_s=latency,
        model_version=d.get("modelVersion", ""),
    )


def _call_openai_compat(spec: config.ModelSpec, system: str, messages: list[dict], schema: dict | None) -> RawResponse:
    if spec.provider == "groq":
        base, key = "https://api.groq.com/openai/v1", config.get_api_key("groq")
    else:
        if not spec.api_id.endswith(":free"):  # hard rule: free models only
            raise LLMClientError(f"refusing non-free OpenRouter model {spec.api_id}")
        base, key = "https://openrouter.ai/api/v1", config.get_api_key("openrouter")
    if not key:
        raise LLMNoKey(f"{spec.provider} key missing")
    body: dict[str, Any] = {
        "model": spec.api_id, "temperature": 0,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    if schema:
        if spec.provider == "groq":
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "output", "schema": schema, "strict": False}}
        else:
            body["response_format"] = {"type": "json_object"}
    if spec.extra.get("reasoning_effort"):
        body["reasoning_effort"] = spec.extra["reasoning_effort"]
    t0 = time.perf_counter()
    try:
        resp = httpx.post(f"{base}/chat/completions", json=body, timeout=config.REQUEST_TIMEOUT_S,
                          headers={"Authorization": f"Bearer {key}"})
    except httpx.TimeoutException as e:
        raise LLMTimeout(f"timeout after {config.REQUEST_TIMEOUT_S}s") from e
    except httpx.TransportError as e:
        raise LLMServerError(f"transport: {type(e).__name__}") from e
    latency = time.perf_counter() - t0
    _raise_for_status(resp)
    d = resp.json()
    if "error" in d:  # OpenRouter sometimes returns 200 with an error body
        code = d["error"].get("code")
        if code == 429:
            raise LLMRateLimit(str(d["error"])[:300])
        raise LLMServerError(str(d["error"])[:300])
    msg = d["choices"][0]["message"]
    u = d.get("usage", {}) or {}
    reasoning = (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
    return RawResponse(
        text=msg.get("content") or "", in_tokens=u.get("prompt_tokens", 0),
        out_tokens=u.get("completion_tokens", 0), thinking_tokens=reasoning, cached_tokens=cached,
        latency_s=latency, model_version=d.get("model", spec.api_id),
    )


def raw_call(spec: config.ModelSpec, system: str, messages: list[dict], schema: dict | None) -> RawResponse:
    if TRANSPORT_OVERRIDE is not None:
        return TRANSPORT_OVERRIDE(spec, system, messages, schema)
    _pace(spec)
    if spec.provider == "gemini":
        return _call_gemini(spec, system, messages, schema)
    return _call_openai_compat(spec, system, messages, schema)


# --------------------------------------------------------------------------- retry policy
def _stop(state: RetryCallState) -> bool:
    exc = state.outcome.exception() if state.outcome else None
    counts = state.retry_object.statistics.setdefault("by_kind", {})
    kind = "rate_limit" if isinstance(exc, LLMRateLimit) else "transient"  # timeout + 5xx share a budget
    counts[kind] = counts.get(kind, 0) + 1
    if kind == "rate_limit":
        return counts[kind] > config.RATE_LIMIT_RETRIES
    return counts[kind] > config.TIMEOUT_RETRIES


def _wait(state: RetryCallState) -> float:
    exc = state.outcome.exception() if state.outcome else None
    if isinstance(exc, LLMRateLimit):
        ra = exc.retry_after if exc.retry_after is not None else 2 ** state.attempt_number
        return min(ra, config.MAX_RETRY_AFTER_S)
    return min(2 ** (state.attempt_number - 1), 8)  # 1s, 2s, 4s ...


def call_with_retries(spec: config.ModelSpec, system: str, messages: list[dict], schema: dict | None,
                      attempts_log: list[dict]) -> RawResponse:
    def before_sleep(state: RetryCallState) -> None:
        exc = state.outcome.exception()
        attempts_log.append({"model": spec.key, "event": f"retry_{exc.kind}", "detail": str(exc)[:160]})
        log_failure(spec.key, exc.kind, str(exc), stage="transport")

    retryer = Retrying(
        retry=retry_if_exception_type((LLMTimeout, LLMServerError, LLMRateLimit)),
        stop=_stop, wait=_wait, sleep=lambda s: SLEEP(s), before_sleep=before_sleep, reraise=True,
    )
    return retryer(raw_call, spec, system, messages, schema)


# --------------------------------------------------------------------------- main entry
def call_structured(
    model_key: str, system: str, user: str, schema_cls: Type[BaseModel], *,
    cache_text: str | None = None, prompt_version: str = "", kb_version: str = "",
    use_fallback: bool = True, use_cache: bool = True,
) -> StructuredResult:
    """Call `model_key` (and fallbacks) until a response validates against `schema_cls`."""
    schema = inline_refs(schema_cls.model_json_schema())
    key = None
    if use_cache and cache_text is not None:
        key = cache.make_key(text=cache_text + "\x1e" + user, model=model_key, prompt_version=prompt_version,
                             kb_version=kb_version, schema=f"{schema_cls.__name__}|fb={use_fallback}")
        hit = cache.get(key)
        if hit:
            r = StructuredResult(**{k: v for k, v in hit["result"].items() if k in StructuredResult.__dataclass_fields__})
            r.from_cache = True
            return r

    chain = [model_key] + (config.FALLBACK_CHAIN.get(model_key, []) if use_fallback else [])
    res = StructuredResult(ok=False, requested_model=model_key)
    t_start = time.perf_counter()
    _paced.total = 0.0

    for idx, mkey in enumerate(chain):
        spec = config.MODELS[mkey]
        if idx > 0:
            res.fallback_used = True
            res.attempts.append({"model": mkey, "event": "fallback", "detail": f"after {chain[idx - 1]}"})
        messages = [{"role": "user", "content": user}]
        try:
            for repair_round in range(2):  # first try + 1 repair
                raw = call_with_retries(spec, system, messages, schema, res.attempts)
                res.in_tokens += raw.in_tokens
                res.out_tokens += raw.out_tokens
                res.thinking_tokens += raw.thinking_tokens
                res.raw_text = raw.text
                try:
                    obj, strict = extract_json(raw.text)
                    validated = schema_cls.model_validate(obj)
                    if idx == 0 and repair_round == 0:
                        res.valid_first_try, res.strict_json_first_try = True, strict
                    res.ok, res.data, res.model = True, validated.model_dump(), mkey
                    res.api_latency_s = raw.latency_s
                    res.attempts.append({"model": mkey, "event": "ok" if repair_round == 0 else "ok_after_repair",
                                         "detail": raw.model_version})
                    break
                except (ValueError, ValidationError) as e:
                    err = str(e)[:800]
                    if idx == 0 and repair_round == 0:
                        res.valid_first_try, res.strict_json_first_try = False, False
                    kind = "invalid_json" if isinstance(e, (ValueError,)) and not isinstance(e, ValidationError) else "schema_error"
                    res.attempts.append({"model": mkey, "event": kind, "detail": err[:160]})
                    log_failure(mkey, kind, err, stage=f"parse_round_{repair_round}")
                    messages = messages + [
                        {"role": "assistant", "content": raw.text or "(empty)"},
                        {"role": "user", "content": "Your previous output failed validation:\n" + err +
                         "\nReturn ONLY the corrected JSON object that matches the schema. No prose, no code fences."},
                    ]
            if res.ok:
                break
        except LLMError as e:
            res.attempts.append({"model": mkey, "event": f"failed_{e.kind}", "detail": str(e)[:160]})
            log_failure(mkey, e.kind, str(e), stage="final")
            if idx == 0 and res.valid_first_try is None:
                res.valid_first_try = False
                res.strict_json_first_try = False

    res.latency_s = time.perf_counter() - t_start - getattr(_paced, "total", 0.0)
    if not res.ok:
        log_failure(model_key, "chain_exhausted", f"tried {chain}", stage="final")
    elif key:
        cache.put(key, {"result": res.__dict__})
    return res
