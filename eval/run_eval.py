"""Run the classifier on data/tickets_eval.jsonl and write results to eval/results/.

Usage:
  python eval/run_eval.py --model gemini-flash-lite --prompt v1
  python eval/run_eval.py --model groq-gpt-oss-120b --prompt v3 --fallback

By default fallback is OFF so a model's own failures are visible in the metrics.
Every model answer is cached on disk (.cache/llm), so re-runs cost no API calls.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import classifier, config, cost  # noqa: E402

EVAL_PATH = config.DATA_DIR / "tickets_eval.jsonl"


def load_eval(dataset: str = "eval") -> list[dict]:
    path = config.DATA_DIR / f"tickets_{dataset}.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def pct(xs: list[bool]) -> float:
    return round(100 * sum(xs) / len(xs), 1) if xs else 0.0


def percentile(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 3)


def evaluate(model: str, prompt: str, fallback: bool = False, verbose: bool = True, dataset: str = "eval") -> dict:
    tickets = load_eval(dataset)
    rows = []
    for i, t in enumerate(tickets, 1):
        r = classifier.classify(t["text"], model_key=model, prompt_version=prompt, use_fallback=fallback)
        m = r.meta or {}
        raw = m.get("model_raw") or {}
        cat_ok = r.category == t["expected_category"]
        lenient = cat_ok or (
            t["expected_secondary"] is not None and r.category == t["expected_secondary"]
            and r.secondary_category == t["expected_category"])
        row = {
            "id": t["id"], "edge_case_type": t["edge_case_type"], "input": t["text"][:90],
            "exp_category": t["expected_category"], "exp_secondary": t["expected_secondary"],
            "exp_priority": t["expected_priority"], "exp_needs_human": t["expected_needs_human"],
            "act_category": r.category, "act_secondary": r.secondary_category, "act_priority": r.priority,
            "act_needs_human": r.needs_human,
            "model_category": raw.get("category"), "model_priority": raw.get("priority"),
            "model_needs_human": raw.get("needs_human"),
            "category_pass": cat_ok, "category_lenient_pass": lenient,
            "priority_pass": r.priority == t["expected_priority"],
            "needs_human_pass": r.needs_human == t["expected_needs_human"],
            "requester_pass": r.requester_type == t["expected_requester_type"],
            "language_pass": (r.language or "").lower()[:2] == t["language"][:2] if t["language"] != "unknown" else True,
            "confidence": r.confidence, "route_to": r.next_step.route_to, "sentiment": r.sentiment,
            "human_reasons": r.human_reasons, "guard_overrides": r.guard_overrides, "rationale": r.rationale,
            "model_used": m.get("model"), "from_cache": m.get("from_cache"), "fallback_used": m.get("fallback_used"),
            "valid_first_try": m.get("valid_first_try"), "strict_json_first_try": m.get("strict_json_first_try"),
            "latency_s": m.get("latency_s"), "api_latency_s": m.get("api_latency_s"), "in_tokens": m.get("in_tokens", 0), "out_tokens": m.get("out_tokens", 0),
            "thinking_tokens": m.get("thinking_tokens", 0), "attempts": m.get("attempts", []),
        }
        row["both_pass"] = row["category_pass"] and row["priority_pass"]
        rows.append(row)
        if verbose:
            flag = "OK " if row["both_pass"] else "ERR"
            print(f"[{i:02d}/{len(tickets)}] {flag} {t['id']} exp={t['expected_category']}/{t['expected_priority']} "
                  f"act={r.category}/{r.priority} nh={r.needs_human} conf={r.confidence:.2f} "
                  f"{'cache' if m.get('from_cache') else str(m.get('latency_s')) + 's'}", flush=True)

    edge = [r for r in rows if r["edge_case_type"] != "none"]
    regular = [r for r in rows if r["edge_case_type"] == "none"]
    exp_h = [r for r in rows if r["exp_needs_human"]]
    act_h = [r for r in rows if r["act_needs_human"]]
    confusion: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        confusion[r["exp_category"]][r["act_category"]] += 1
    lat = [r["latency_s"] for r in rows if r["latency_s"] is not None and r["model_used"]]
    api_lat = [r["api_latency_s"] for r in rows if r.get("api_latency_s") and r["model_used"]]
    answered = [r for r in rows if r["model_used"]]

    # Confidence threshold sweep: how many category/priority errors each threshold would route to a human.
    sweep = []
    for th in [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
        low = [r for r in rows if r["confidence"] < th]
        errs = [r for r in rows if not r["both_pass"]]
        sweep.append({
            "threshold": th, "flagged": len(low),
            "errors_caught": sum(1 for r in errs if r["confidence"] < th), "errors_total": len(errs),
            "correct_flagged": sum(1 for r in low if r["both_pass"]),
        })

    prices = config.load_prices()
    cost_per_ticket = [cost.call_cost(r["model_used"] or model, r["in_tokens"], r["out_tokens"], prices) for r in answered]
    summary = {
        "model": model, "prompt": prompt, "fallback": fallback, "dataset": dataset, "n": len(rows),
        "category_acc": pct([r["category_pass"] for r in rows]),
        "category_lenient_acc": pct([r["category_lenient_pass"] for r in rows]),
        "priority_acc": pct([r["priority_pass"] for r in rows]),
        "both_acc": pct([r["both_pass"] for r in rows]),
        "needs_human_acc": pct([r["needs_human_pass"] for r in rows]),
        "needs_human_recall": pct([r["act_needs_human"] for r in exp_h]),
        "needs_human_precision": pct([r["exp_needs_human"] for r in act_h]),
        "escalation_rate": pct([r["act_needs_human"] for r in rows]),
        "model_needs_human_recall": pct([bool(r["model_needs_human"]) for r in exp_h]),
        "edge_category_acc": pct([r["category_pass"] for r in edge]),
        "edge_priority_acc": pct([r["priority_pass"] for r in edge]),
        "regular_category_acc": pct([r["category_pass"] for r in regular]),
        "regular_priority_acc": pct([r["priority_pass"] for r in regular]),
        "requester_acc": pct([r["requester_pass"] for r in rows]),
        "language_acc": pct([r["language_pass"] for r in rows]),
        "valid_json_first_try": pct([bool(r["valid_first_try"]) for r in rows if r["model_used"] or r["valid_first_try"] is not None]),
        "strict_json_first_try": pct([bool(r["strict_json_first_try"]) for r in rows if r["valid_first_try"] is not None]),
        "fallbacks": sum(1 for r in rows if r["fallback_used"]),
        "safe_defaults": sum(1 for r in rows if r["act_category"] == "unclassified"),
        "latency_p50": percentile(lat, 0.5), "latency_p95": percentile(lat, 0.95),
        "api_latency_p50": percentile(api_lat, 0.5), "api_latency_p95": percentile(api_lat, 0.95),
        "avg_in_tokens": round(statistics.mean([r["in_tokens"] for r in answered]), 1) if answered else 0,
        "avg_out_tokens": round(statistics.mean([r["out_tokens"] for r in answered]), 1) if answered else 0,
        "avg_thinking_tokens": round(statistics.mean([r["thinking_tokens"] for r in answered]), 1) if answered else 0,
        "avg_cost_usd": round(statistics.mean(cost_per_ticket), 7) if cost_per_ticket else 0,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "confidence_sweep": sweep,
    }
    tag = f"classifier_{prompt}_{model}" + ("_fb" if fallback else "") + ("" if dataset == "eval" else f"_{dataset}")
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / f"{tag}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False))
    (config.RESULTS_DIR / f"{tag}.md").write_text(to_markdown(summary, rows), encoding="utf-8")
    return {"summary": summary, "rows": rows}


def to_markdown(s: dict, rows: list[dict]) -> str:
    yn = lambda b: "✅" if b else "❌"  # noqa: E731
    out = [f"# Classifier eval ({s.get('dataset', 'eval')}) — prompt `{s['prompt']}`, model `{s['model']}`{' (fallback on)' if s['fallback'] else ''}", ""]
    out.append(f"n={s['n']} · category **{s['category_acc']}%** (lenient {s['category_lenient_acc']}%) · "
               f"priority **{s['priority_acc']}%** · both **{s['both_acc']}%** · needs_human {s['needs_human_acc']}% "
               f"(recall {s['needs_human_recall']}%, precision {s['needs_human_precision']}%)")
    out.append(f"edge cases: category {s['edge_category_acc']}% / priority {s['edge_priority_acc']}% · "
               f"regular: category {s['regular_category_acc']}% / priority {s['regular_priority_acc']}%")
    out.append(f"valid JSON first try {s['valid_json_first_try']}% · fallbacks {s['fallbacks']} · safe defaults {s['safe_defaults']} · "
               f"latency p50 {s['latency_p50']}s / p95 {s['latency_p95']}s · tokens in {s['avg_in_tokens']} / out {s['avg_out_tokens']}")
    out += ["", "| id | edge | input | expected cat / prio / human | actual cat / prio / human | cat | prio | human | conf |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        inp = r["input"].replace("|", "/").replace("\n", " ")
        exp = f"{r['exp_category']}{'+' + r['exp_secondary'] if r['exp_secondary'] else ''} / {r['exp_priority']} / {r['exp_needs_human']}"
        act = f"{r['act_category']}{'+' + r['act_secondary'] if r['act_secondary'] else ''} / {r['act_priority']} / {r['act_needs_human']}"
        out.append(f"| {r['id']} | {r['edge_case_type']} | {inp} | {exp} | {act} | {yn(r['category_pass'])} | "
                   f"{yn(r['priority_pass'])} | {yn(r['needs_human_pass'])} | {r['confidence']:.2f} |")
    out += ["", "## Errors", ""]
    for r in rows:
        if not (r["both_pass"] and r["needs_human_pass"]):
            out.append(f"- **{r['id']}** ({r['edge_case_type']}): expected {r['exp_category']}/{r['exp_priority']}/human={r['exp_needs_human']}, "
                       f"got {r['act_category']}/{r['act_priority']}/human={r['act_needs_human']}. "
                       f"Model rationale: _{r['rationale']}_ Reasons: {r['human_reasons']}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.DEFAULT_MODEL, choices=list(config.MODELS))
    ap.add_argument("--prompt", default=config.CLASSIFIER_PROMPT_VERSION)
    ap.add_argument("--fallback", action="store_true")
    ap.add_argument("--dataset", default="eval", choices=["eval", "holdout"])
    a = ap.parse_args()
    res = evaluate(a.model, a.prompt, a.fallback, dataset=a.dataset)
    s = res["summary"]
    print(json.dumps({k: v for k, v in s.items() if k not in ("confusion", "confidence_sweep")}, indent=1))
