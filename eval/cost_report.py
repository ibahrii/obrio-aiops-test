"""Cost per ticket and 10k/month forecast from REAL token counts of the eval runs.

  python eval/cost_report.py  -> eval/results/cost_report.{json,md}

Inputs: classifier results per model (final prompt), assistant eval (Flash-Lite), pricing snapshot.
Static prompt sizes were measured with the Gemini countTokens API (see STATIC_TOKENS).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config, cost  # noqa: E402

R = config.RESULTS_DIR
# measured with models/gemini-3.5-flash-lite:countTokens on 2026-10-30
STATIC_TOKENS = {"classifier_v4_system": 1919, "assistant_v2_system": 698}
MONTH = 10_000
PRIMARY, STRONG = "gemini-flash-lite", "groq-gpt-oss-120b"


def load(name):
    p = R / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main() -> None:
    prices = config.load_prices()
    v = config.CLASSIFIER_PROMPT_VERSION
    comp = json.loads((R / "model_comparison.json").read_text())
    asst = load(f"assistant_{config.ASSISTANT_PROMPT_VERSION}_{PRIMARY}")["summary"]
    base = next(r for r in comp if r["model"] == PRIMARY)

    rows = []
    for r in comp:
        m = r["model"]
        if not r["n"]:
            continue
        t1 = cost.call_cost(m, r["avg_in_tokens"], r["avg_out_tokens"], prices)
        # Assistant tokens were measured on Flash-Lite only -> other models are an ESTIMATE:
        # same input tokens, output scaled by the model's classifier output ratio (captures reasoning tokens).
        ratio = r["avg_out_tokens"] / base["avg_out_tokens"] if base["avg_out_tokens"] else 1
        t2 = cost.call_cost(m, asst["avg_in_tokens"], asst["avg_out_tokens"] * ratio, prices)
        t1_cached = cost.with_prompt_cache(m, r["avg_in_tokens"], r["avg_out_tokens"], STATIC_TOKENS["classifier_v4_system"], prices)
        rows.append({"model": m, "label": r["label"], "task1_per_ticket": t1, "task2_call_per_ticket": t2,
                     "task2_measured": m == PRIMARY, "task1_10k": t1 * MONTH, "task1_2_10k": (t1 + t2) * MONTH,
                     "task1_cached_per_ticket": t1_cached, "task1_cached_10k": t1_cached * MONTH,
                     "both_acc": r["both_acc"], "n": r["n"], "n_total": r["n_total"]})

    # Cascade simulated on real answers: Flash-Lite everywhere, ticket re-asked to the strong model when confidence < threshold.
    cheap = load(f"classifier_{v}_{PRIMARY}")["rows"]
    strong = {x["id"]: x for x in load(f"classifier_{v}_{STRONG}")["rows"]}
    th = config.CONFIDENCE_THRESHOLD
    esc = [x for x in cheap if x["confidence"] < th or x["act_category"] == "unclassified"]
    casc_both = [(strong[x["id"]] if x in esc else x)["both_pass"] for x in cheap]
    r_cheap = next(x for x in rows if x["model"] == PRIMARY)
    r_strong = next(x for x in rows if x["model"] == STRONG)
    casc_cost = cost.cascade_cost({"cost": r_cheap["task1_per_ticket"]}, {"cost": r_strong["task1_per_ticket"]}, len(esc) / len(cheap))
    cascade = {"threshold": th, "escalated": len(esc), "n": len(cheap), "escalation_rate": len(esc) / len(cheap),
               "both_acc": round(100 * sum(casc_both) / len(casc_both), 1), "cost_per_ticket": casc_cost,
               "cost_10k": casc_cost * MONTH}

    # Batch API applies to work that can wait: Task 2 drafts for tickets triaged P3/P4 (not to the first triage call).
    p34 = sum(1 for x in cheap if x["act_priority"] in ("P3", "P4")) / len(cheap)
    batch_saving_10k = p34 * r_cheap["task2_call_per_ticket"] * 0.5 * MONTH

    out = {"prices": prices, "static_tokens": STATIC_TOKENS, "rows": rows, "cascade": cascade,
           "p3_p4_share": p34, "batch_saving_task2_10k": batch_saving_10k,
           "assistant_tokens_flash_lite": {"in": asst["avg_in_tokens"], "out": asst["avg_out_tokens"]}}
    (R / "cost_report.json").write_text(json.dumps(out, indent=1))

    md = ["# Cost report (real tokens × public paid-tier prices)", "",
          "| model | both acc | Task 1 $/ticket | Task 1 $/10k | Task 2 call $/ticket | Task 1+2 $/10k | Task 1 with prompt cache $/10k |",
          "|---|---|---|---|---|---|---|"]
    for x in rows:
        est = "" if x["task2_measured"] else " (оцінка)"
        partial = f" (лише {x['n']}/{x['n_total']})" if x["n"] < x["n_total"] else ""
        md.append(f"| {x['label']} | {x['both_acc']}%{partial} | {x['task1_per_ticket']:.6f} | {x['task1_10k']:.2f} | "
                  f"{x['task2_call_per_ticket']:.6f}{est} | {x['task1_2_10k']:.2f}{est} | {x['task1_cached_10k']:.2f} |")
    md += ["", f"**Cascade** (Flash-Lite → GPT-OSS-120B when confidence < {th}): escalated {cascade['escalated']}/{cascade['n']} tickets, "
           f"both accuracy {cascade['both_acc']}%, ${cascade['cost_per_ticket']:.6f}/ticket, ${cascade['cost_10k']:.2f}/10k.",
           f"**Batch API** (50% off) for Task 2 drafts of P3/P4 tickets ({p34:.0%} of tickets): saves ≈ ${batch_saving_10k:.2f} per 10k.",
           f"Prompt cache column: static system prompt ({STATIC_TOKENS['classifier_v4_system']} tokens) billed at the cached-input price; "
           "storage fees and minimum cacheable size not included (оцінка).",
           f"Task 2 tokens measured on Flash-Lite only (in {asst['avg_in_tokens']}, out {asst['avg_out_tokens']}); other models are estimates."]
    (R / "cost_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
