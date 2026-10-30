"""Simulate provider failures with a fake transport and show which fallback fired.

  python eval/simulate_failures.py   -> prints a table, writes eval/results/failure_simulation.md
Also run by tests/test_failures.py. No real API calls are made.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import classifier, config, llm  # noqa: E402

GOOD = {
    "category": "billing_subscription", "secondary_category": None, "priority": "P3", "requester_type": "user",
    "language": "en", "sentiment": "calm", "next_step": {"route_to": "Billing", "action": "Explain cancellation"},
    "confidence": 0.9, "needs_human": False, "human_reasons": [], "rationale": "How-to cancel.",
}
TICKET = "How do I cancel my subscription?"


class Script:
    """Fake transport: per model key, a list of behaviours consumed one per call."""

    def __init__(self, plan: dict[str, list]):
        self.plan = {k: list(v) for k, v in plan.items()}
        self.calls: list[str] = []

    def __call__(self, spec, system, messages, schema):
        self.calls.append(spec.key)
        step = self.plan.get(spec.key, ["ok"]).pop(0) if self.plan.get(spec.key) else "ok"
        if step == "ok":
            return llm.RawResponse(text=json.dumps(GOOD), in_tokens=100, out_tokens=50, latency_s=0.1, model_version=spec.api_id)
        if step == "broken_json":
            return llm.RawResponse(text='{"category": "billing_subscription", "priority": ', in_tokens=100, out_tokens=10)
        if step == "bad_schema":
            return llm.RawResponse(text=json.dumps({**GOOD, "category": "billing", "priority": "urgent"}), in_tokens=100, out_tokens=50)
        if step == "timeout":
            raise llm.LLMTimeout("simulated timeout after 20s")
        if step == "503":
            raise llm.LLMServerError("simulated 503 high demand")
        if step.startswith("429"):
            ra = float(step.split(":")[1]) if ":" in step else None
            raise llm.LLMRateLimit("simulated 429", retry_after=ra)
        raise AssertionError(step)


SCENARIOS = [
    ("invalid JSON once -> repair prompt succeeds", {"gemini-flash-lite": ["broken_json", "ok"]},
     {"model": "gemini-flash-lite", "fallback": False, "category": "billing_subscription", "events": ["invalid_json", "ok_after_repair"]}),
    ("schema violation twice -> fallback to Groq", {"gemini-flash-lite": ["bad_schema", "bad_schema"]},
     {"model": "groq-gpt-oss-120b", "fallback": True, "category": "billing_subscription", "events": ["schema_error", "schema_error", "fallback", "ok"]}),
    ("timeout x2 -> 3rd attempt ok (exp. backoff 1s, 2s)", {"gemini-flash-lite": ["timeout", "timeout", "ok"]},
     {"model": "gemini-flash-lite", "fallback": False, "sleeps": [1, 2]}),
    ("timeout x3 -> fallback to Groq", {"gemini-flash-lite": ["timeout", "timeout", "timeout"]},
     {"model": "groq-gpt-oss-120b", "fallback": True}),
    ("429 with Retry-After 7s -> waits 7s -> ok", {"gemini-flash-lite": ["429:7", "ok"]},
     {"model": "gemini-flash-lite", "fallback": False, "sleeps": [7]}),
    ("429 Retry-After 120s is capped at 30s", {"gemini-flash-lite": ["429:120", "ok"]},
     {"model": "gemini-flash-lite", "sleeps": [30]}),
    ("429 persistent -> fallback provider", {"gemini-flash-lite": ["429:1", "429:1", "429:1"]},
     {"model": "groq-gpt-oss-120b", "fallback": True}),
    ("503 then Groq also times out -> 3rd model in chain", {"gemini-flash-lite": ["503", "503", "503"],
                                                           "groq-gpt-oss-120b": ["timeout", "timeout", "timeout"]},
     {"model": "gemini-flash", "fallback": True}),
    ("everything fails -> safe default (unclassified, P2, needs_human)",
     {k: ["broken_json"] * 4 for k in config.MODELS},
     {"model": None, "category": "unclassified", "priority": "P2", "needs_human": True}),
]


def run_scenario(plan: dict, use_cache: bool = False):
    script = Script(plan)
    sleeps: list[float] = []
    old = (llm.TRANSPORT_OVERRIDE, llm.SLEEP, config.LOG_DIR, config.CACHE_DIR)
    tmp = pathlib.Path(tempfile.mkdtemp())
    llm.TRANSPORT_OVERRIDE, llm.SLEEP = script, sleeps.append
    config.LOG_DIR, config.CACHE_DIR = tmp / "logs", tmp / "cache"
    try:
        res = classifier.classify(TICKET, model_key="gemini-flash-lite", prompt_version="v4", use_cache=use_cache)
        log = (tmp / "logs" / "failures.jsonl")
        logged = [json.loads(l)["kind"] for l in log.read_text().splitlines()] if log.exists() else []
        return res, script.calls, sleeps, logged
    finally:
        llm.TRANSPORT_OVERRIDE, llm.SLEEP, config.LOG_DIR, config.CACHE_DIR = old


def check(res, sleeps, expect) -> list[str]:
    problems = []
    m = res.meta
    if "model" in expect and m.get("model") != expect["model"]:
        problems.append(f"model {m.get('model')} != {expect['model']}")
    if "fallback" in expect and m.get("fallback_used") != expect["fallback"]:
        problems.append(f"fallback {m.get('fallback_used')}")
    for k in ("category", "priority", "needs_human"):
        if k in expect and getattr(res, k) != expect[k]:
            problems.append(f"{k} {getattr(res, k)}")
    if "sleeps" in expect and sleeps != expect["sleeps"]:
        problems.append(f"sleeps {sleeps}")
    if "events" in expect:
        ev = [a["event"] for a in m.get("attempts", [])]
        if ev != expect["events"]:
            problems.append(f"events {ev}")
    return problems


def main() -> int:
    lines = ["# Failure simulation (fake transport, no real API calls)", "",
             "| scenario | calls made | backoff sleeps, s | answered by | fallback | result | logged failures | pass |",
             "|---|---|---|---|---|---|---|---|"]
    failed = 0
    for name, plan, expect in SCENARIOS:
        res, calls, sleeps, logged = run_scenario(plan)
        problems = check(res, sleeps, expect)
        failed += bool(problems)
        lines.append(f"| {name} | {' → '.join(calls)} | {sleeps or '—'} | {res.meta.get('model')} | {res.meta.get('fallback_used')} | "
                     f"{res.category}/{res.priority}/human={res.needs_human} | {', '.join(sorted(set(logged))) or '—'} | "
                     f"{'✅' if not problems else '❌ ' + '; '.join(problems)} |")
    # cache: second identical call must not hit the transport
    script = Script({"gemini-flash-lite": ["ok"]})
    old = (llm.TRANSPORT_OVERRIDE, config.CACHE_DIR, config.LOG_DIR)
    tmp = pathlib.Path(tempfile.mkdtemp())
    llm.TRANSPORT_OVERRIDE, config.CACHE_DIR, config.LOG_DIR = script, tmp / "cache", tmp / "logs"
    try:
        classifier.classify(TICKET, model_key="gemini-flash-lite", prompt_version="v4")
        r2 = classifier.classify("  how do I CANCEL my subscription?  ", model_key="gemini-flash-lite", prompt_version="v4")
        r3 = classifier.classify(TICKET, model_key="gemini-flash-lite", prompt_version="v3")
    finally:
        llm.TRANSPORT_OVERRIDE, config.CACHE_DIR, config.LOG_DIR = old
    ok = r2.meta.get("from_cache") and not r3.meta.get("from_cache") and len(script.calls) == 2
    failed += not ok
    lines.append(f"| cache: same ticket (normalised case/spaces) served from disk; new prompt version = new key | "
                 f"{' → '.join(script.calls)} | — | — | — | 2nd from_cache={r2.meta.get('from_cache')}, other version from_cache={r3.meta.get('from_cache')} | — | {'✅' if ok else '❌'} |")
    out = "\n".join(lines) + "\n"
    (config.RESULTS_DIR / "failure_simulation.md").write_text(out, encoding="utf-8")
    print(out)
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
