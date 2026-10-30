"""Compare models on the final classifier prompt.

  python eval/compare_models.py --run gemini-flash-lite groq-gpt-oss-120b   # run (cached) evals
  python eval/compare_models.py                                          # only aggregate existing results

Writes eval/results/model_comparison.{json,md}. Fallback is OFF so each model is measured on its own.
Cost uses real token counts from the runs x public paid-tier prices (eval/results/pricing_snapshot.json).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config, cost  # noqa: E402
from eval.run_eval import evaluate  # noqa: E402

MODELS = ["gemini-flash", "gemini-flash-3.6", "gemini-flash-lite", "groq-gpt-oss-120b", "groq-gpt-oss-20b",
          "openrouter-nemotron-free"]


def load(prompt: str, model: str, dataset: str) -> dict | None:
    suffix = "" if dataset == "eval" else f"_{dataset}"
    p = config.RESULTS_DIR / f"classifier_{prompt}_{model}{suffix}.json"
    return json.loads(p.read_text())["summary"] if p.exists() else None


def aggregate(prompt: str) -> list[dict]:
    prices = config.load_prices()
    rows = []
    for m in MODELS:
        s, h = load(prompt, m, "eval"), load(prompt, m, "holdout")
        if not s:
            continue
        per_ticket = cost.call_cost(m, s["avg_in_tokens"], s["avg_out_tokens"], prices)
        rows.append({
            "model": m, "label": config.MODELS[m].label, "api_id": config.MODELS[m].api_id, "n": s["n"],
            "category_acc": s["category_acc"], "priority_acc": s["priority_acc"], "both_acc": s["both_acc"],
            "needs_human_acc": s["needs_human_acc"], "needs_human_recall": s["needs_human_recall"],
            "edge_both": None, "holdout_both_acc": h["both_acc"] if h else None,
            "valid_json_first_try": s["valid_json_first_try"], "strict_json_first_try": s["strict_json_first_try"],
            "safe_defaults": s["safe_defaults"],
            "api_latency_p50": s.get("api_latency_p50"), "api_latency_p95": s.get("api_latency_p95"),
            "wall_latency_p50": s["latency_p50"], "wall_latency_p95": s["latency_p95"],
            "avg_in_tokens": s["avg_in_tokens"], "avg_out_tokens": s["avg_out_tokens"],
            "avg_thinking_tokens": s["avg_thinking_tokens"],
            "price_in_per_1m": prices[m]["input"], "price_out_per_1m": prices[m]["output"],
            "cost_per_ticket_usd": round(per_ticket, 6), "cost_10k_usd": round(cost.monthly(per_ticket), 2),
        })
    return rows


def to_markdown(rows: list[dict], prompt: str) -> str:
    out = [f"# Model comparison — classifier prompt `{prompt}` (fallback off)", "",
           "| model | category | priority | both | holdout both | needs_human | valid JSON 1st try | API p50 / p95, s | wall p50 / p95, s | tokens in / out | $/ticket | $/10k |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            f"| {r['label']} | {r['category_acc']}% | {r['priority_acc']}% | {r['both_acc']}% | "
            f"{r['holdout_both_acc'] if r['holdout_both_acc'] is not None else '—'}% | {r['needs_human_acc']}% | "
            f"{r['valid_json_first_try']}% | {r['api_latency_p50']} / {r['api_latency_p95']} | "
            f"{r['wall_latency_p50']} / {r['wall_latency_p95']} | {r['avg_in_tokens']:.0f} / {r['avg_out_tokens']:.0f} | "
            f"{r['cost_per_ticket_usd']:.6f} | {r['cost_10k_usd']:.2f} |")
    out += ["", "Prices: public paid tier per 1M tokens (input / output), from `pricing_snapshot.json`:", ""]
    for r in rows:
        out.append(f"- {r['label']} (`{r['api_id']}`): ${r['price_in_per_1m']} / ${r['price_out_per_1m']}")
    out += ["", "API latency = HTTP time of the successful call. Wall latency also includes retries and Retry-After waits "
            "caused by free-tier limits (e.g. Groq 8000 TPM), so it reflects the free tier, not the model."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=config.CLASSIFIER_PROMPT_VERSION)
    ap.add_argument("--run", nargs="*", default=[], choices=MODELS)
    ap.add_argument("--holdout", action="store_true", help="also run the holdout set")
    a = ap.parse_args()
    for m in a.run:
        evaluate(m, a.prompt, fallback=False)
        if a.holdout:
            evaluate(m, a.prompt, fallback=False, dataset="holdout")
    rows = aggregate(a.prompt)
    (config.RESULTS_DIR / "model_comparison.json").write_text(json.dumps(rows, indent=1))
    (config.RESULTS_DIR / "model_comparison.md").write_text(to_markdown(rows, a.prompt), encoding="utf-8")
    print(to_markdown(rows, a.prompt))
