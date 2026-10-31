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

from src import config, cost, llm  # noqa: E402
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
        if s["n"] == 0:
            rows.append({"model": m, "label": config.MODELS[m].label, "api_id": config.MODELS[m].api_id, "n": 0,
                         "n_total": s.get("n_total", 30), "price_in_per_1m": prices[m]["input"], "price_out_per_1m": prices[m]["output"]})
            continue
        per_ticket = cost.call_cost(m, s["avg_in_tokens"], s["avg_out_tokens"], prices)
        rows.append({
            "model": m, "label": config.MODELS[m].label, "api_id": config.MODELS[m].api_id, "n": s["n"],
            "n_total": s.get("n_total", s["n"]), "holdout_n": h["n"] if h else 0,
            "holdout_n_total": h.get("n_total", h["n"]) if h else 0,
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


def holdout_cell(r: dict) -> str:
    if r["holdout_both_acc"] is None or not r["holdout_n"]:
        return "-"
    partial = f" ({r['holdout_n']}/{r['holdout_n_total']})" if r["holdout_n"] < r["holdout_n_total"] else ""
    return f"{r['holdout_both_acc']}%{partial}"


def to_markdown(rows: list[dict], prompt: str) -> str:
    out = [f"# Model comparison: classifier prompt `{prompt}` (fallback off)", "",
           "| model | measured | category | priority | both | holdout both | needs_human | valid JSON 1st try | API p50 / p95, s | wall p50 / p95, s | tokens in / out | $/ticket | $/10k |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["n"] == 0:
            out.append(f"| {r['label']} | 0/{r['n_total']} | не виміряно: free tier 20 запитів/добу вичерпано таймаутами | | | | | | | | | | |")
            continue
        out.append(
            f"| {r['label']} | {r['n']}/{r['n_total']} | {r['category_acc']}% | {r['priority_acc']}% | {r['both_acc']}% | "
            f"{holdout_cell(r)} | {r['needs_human_acc']}% | "
            f"{r['valid_json_first_try']}% | {r['api_latency_p50']} / {r['api_latency_p95']} | "
            f"{r['wall_latency_p50']} / {r['wall_latency_p95']} | {r['avg_in_tokens']:.0f} / {r['avg_out_tokens']:.0f} | "
            f"{r['cost_per_ticket_usd']:.6f} | {r['cost_10k_usd']:.2f} |")
    out += ["", "Prices: public paid tier per 1M tokens (input / output), from `pricing_snapshot.json`:", ""]
    for r in rows:
        out.append(f"- {r['label']} (`{r['api_id']}`): ${r['price_in_per_1m']} / ${r['price_out_per_1m']}")
    out += ["", "API latency = HTTP time of the successful call. Wall latency also includes retries and Retry-After waits "
            "caused by free-tier limits (e.g. Groq 8000 TPM), so it reflects the free tier, not the model.",
            "", "Gemini 3.8 / 3.6 Flash were measured with a 60 s request timeout (LLM_TIMEOUT_S=60) from two free-tier Google "
            "projects (20 requests/day/model each); all other models with the default 20 s. A row with measured < total covers "
            "only the tickets that got an answer, so its accuracy is not directly comparable with fully measured rows."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=config.CLASSIFIER_PROMPT_VERSION)
    ap.add_argument("--run", nargs="*", default=[], choices=MODELS)
    ap.add_argument("--holdout", action="store_true", help="also run the holdout set")
    ap.add_argument("--export-failures", action="store_true",
                    help="overwrite eval/results/failure_stats.json from this machine's logs/ (only after live runs)")
    a = ap.parse_args()
    for m in a.run:
        evaluate(m, a.prompt, fallback=False)
        if a.holdout:
            evaluate(m, a.prompt, fallback=False, dataset="holdout")
    rows = aggregate(a.prompt)
    (config.RESULTS_DIR / "model_comparison.json").write_text(json.dumps(rows, indent=1))
    if a.export_failures or a.run:
        # snapshot of real provider failures seen during live runs; logs/ is local and not committed,
        # so a cache-only regeneration must not overwrite the committed snapshot
        (config.RESULTS_DIR / "failure_stats.json").write_text(json.dumps(llm.failure_stats(), indent=1))
    (config.RESULTS_DIR / "model_comparison.md").write_text(to_markdown(rows, a.prompt), encoding="utf-8")
    print(to_markdown(rows, a.prompt))
