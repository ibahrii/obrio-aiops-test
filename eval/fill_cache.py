"""Fill the response cache for tickets a model has not answered yet, stopping as soon as the free-tier daily
quota is exhausted. Nothing is written to eval/results here: afterwards run run_eval.py --cache-only, which
reports only the measured tickets.

  LLM_TIMEOUT_S=60 python eval/fill_cache.py --model gemini-flash-3.6 --dataset eval
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import classifier, config, llm  # noqa: E402
from eval.run_eval import load_eval  # noqa: E402


def is_cached(text: str, model: str, prompt: str) -> bool:
    llm.CACHE_ONLY = True
    try:
        r = classifier.classify(text, model_key=model, prompt_version=prompt, use_fallback=False)
    finally:
        llm.CACHE_ONLY = False
    return bool(r.meta.get("from_cache"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(config.MODELS))
    ap.add_argument("--prompt", default=config.CLASSIFIER_PROMPT_VERSION)
    ap.add_argument("--dataset", default="eval", choices=["eval", "holdout", "noisy", "holdout2"])
    a = ap.parse_args()
    print(f"timeout {config.REQUEST_TIMEOUT_S}s")
    answered = failed = 0
    tickets = load_eval(a.dataset)
    todo = [t for t in tickets if not is_cached(t["text"], a.model, a.prompt)]
    print(f"{a.model} / {a.dataset}: {len(tickets) - len(todo)} already measured, {len(todo)} to go")
    for t in todo:
        r = classifier.classify(t["text"], model_key=a.model, prompt_version=a.prompt, use_fallback=False)
        if r.category != "unclassified":
            answered += 1
            print(f"  {t['id']} ok {r.category}/{r.priority} {r.meta.get('api_latency_s')}s")
            continue
        failed += 1
        last = json.dumps(r.meta.get("attempts", [])[-1:], ensure_ascii=False)
        print(f"  {t['id']} FAILED {last[:200]}")
        if "quota" in last.lower() or "PerDay" in last:
            print("daily quota exhausted -> stop (remaining tickets stay 'not measured')")
            break
    print(f"answered now: {answered}, failed: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
