"""Evaluate the agent assistant (Task 2) on data/assistant_eval.jsonl.

  python eval/run_assistant_eval.py --model gemini-flash-lite --prompt v1

Metrics: retrieval hit@3 (+ ablation: ticket only / +category boost / +query expansion), citation validity,
reply language, tone length limits, human_decision_required correctness. Results -> eval/results/.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import assistant, classifier, config, llm, retrieval  # noqa: E402

EVAL_PATH = config.DATA_DIR / "assistant_eval.jsonl"


def hit(expected: list[str], ids: list[str]) -> bool | None:
    return None if not expected else any(e in ids for e in expected)


def pct(xs) -> float:
    xs = [x for x in xs if x is not None]
    return round(100 * sum(xs) / len(xs), 1) if xs else 0.0


def evaluate(model: str, prompt: str, classifier_model: str | None = None) -> dict:
    tickets = [json.loads(l) for l in EVAL_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for i, t in enumerate(tickets, 1):
        cls = classifier.classify(t["text"], model_key=classifier_model or model)
        cats = tuple(c for c in (cls.category, cls.secondary_category) if c)
        abl = {
            "ticket_only": [h["id"] for h in retrieval.search(t["text"])],
            "plus_boost": [h["id"] for h in retrieval.search(t["text"], categories=cats)],
            "plus_boost_expansion": [h["id"] for h in retrieval.search(retrieval.build_query(t["text"], cls), categories=cats)],
        }
        r = assistant.assist(t["text"], model_key=model, prompt_version=prompt, classifier_model=classifier_model)
        ids = [h["id"] for h in r.retrieved]
        lengths = r.checks.get("lengths", {})
        row = {
            "id": t["id"], "scenario": t["scenario"], "language": t["language"], "input": t["text"][:80],
            "expected_articles": t["expected_articles"], "retrieved": ids, "hit3": hit(t["expected_articles"], ids),
            "ablation": {k: hit(t["expected_articles"], v) for k, v in abl.items()}, "ablation_ids": abl,
            "citations": r.citations, "citations_valid": r.checks.get("citations_valid", 0),
            "citations_total": r.checks.get("citations_total", 0),
            "kb_has_answer": r.kb_has_answer, "kb_answer_expected": bool(t["expected_articles"]),
            "language_ok": all(r.checks.get("language", {}).values()) if r.checks.get("language") else False,
            "language_per_tone": r.checks.get("language", {}),
            "length_ok": {k: v.get("ok") for k, v in lengths.items()},
            "words": {k: v.get("words") for k, v in lengths.items()},
            "exp_human": t["expected_human_decision"], "act_human": r.human_decision_required,
            "human_pass": r.human_decision_required == t["expected_human_decision"], "reasons": r.reasons,
            "summary": r.summary, "replies": r.replies.model_dump(),
            "classification": f"{cls.category}/{cls.priority}",
            "model_used": r.meta.get("model"), "in_tokens": r.meta.get("in_tokens", 0),
            "out_tokens": r.meta.get("out_tokens", 0), "latency_s": r.meta.get("latency_s"),
            "api_latency_s": r.meta.get("api_latency_s"),
        }
        rows.append(row)
        print(f"[{i:02d}] {t['id']} hit3={row['hit3']} cit={row['citations_valid']}/{row['citations_total']} "
              f"lang={row['language_ok']} len={row['length_ok']} human={r.human_decision_required} (exp {t['expected_human_decision']})", flush=True)

    tones = ("formal", "empathetic", "short")
    s = {
        "model": model, "prompt": prompt, "n": len(rows),
        "hit3": pct([r["hit3"] for r in rows]),
        "ablation_hit3": {k: pct([r["ablation"][k] for r in rows]) for k in rows[0]["ablation"]},
        "citation_validity": round(100 * sum(r["citations_valid"] for r in rows) / max(1, sum(r["citations_total"] for r in rows)), 1),
        "tickets_with_valid_citation": pct([r["citations_valid"] > 0 for r in rows if r["kb_answer_expected"]]),
        "kb_has_answer_acc": pct([r["kb_has_answer"] == r["kb_answer_expected"] for r in rows]),
        "language_acc": pct([r["language_ok"] for r in rows]),
        "length_ok": {t: pct([r["length_ok"].get(t) for r in rows]) for t in tones},
        "avg_words": {t: round(sum(r["words"].get(t) or 0 for r in rows) / len(rows), 1) for t in tones},
        "human_acc": pct([r["human_pass"] for r in rows]),
        "human_recall": pct([r["act_human"] for r in rows if r["exp_human"]]),
        "avg_in_tokens": round(sum(r["in_tokens"] for r in rows) / len(rows), 1),
        "avg_out_tokens": round(sum(r["out_tokens"] for r in rows) / len(rows), 1),
    }
    tag = f"assistant_{prompt}_{model}"
    (config.RESULTS_DIR / f"{tag}.json").write_text(json.dumps({"summary": s, "rows": rows}, indent=1, ensure_ascii=False))
    (config.RESULTS_DIR / f"{tag}.md").write_text(to_markdown(s, rows), encoding="utf-8")
    return {"summary": s, "rows": rows}


def to_markdown(s: dict, rows: list[dict]) -> str:
    yn = lambda b: "-" if b is None else ("✅" if b else "❌")  # noqa: E731
    out = [f"# Assistant eval: prompt `{s['prompt']}`, model `{s['model']}`", "",
           f"hit@3 {s['hit3']}% (ablation: {s['ablation_hit3']}) · citation validity {s['citation_validity']}% · "
           f"language {s['language_acc']}% · length ok {s['length_ok']} · avg words {s['avg_words']} · "
           f"human decision {s['human_acc']}% (recall {s['human_recall']}%) · kb_has_answer {s['kb_has_answer_acc']}%", "",
           "| id | scenario | lang | expected -> retrieved | hit@3 | citations valid | language | length f/e/s | human exp -> act |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lo = r["length_ok"]
        out.append(f"| {r['id']} | {r['scenario']} | {r['language']} | {r['expected_articles']} -> {r['retrieved']} | {yn(r['hit3'])} | "
                   f"{r['citations_valid']}/{r['citations_total']} | {yn(r['language_ok'])} | "
                   f"{yn(lo.get('formal'))}{yn(lo.get('empathetic'))}{yn(lo.get('short'))} | {r['exp_human']} -> {r['act_human']} |")
    out += ["", "## Drafts (for manual review)", ""]
    for r in rows:
        out.append(f"### {r['id']}: {r['scenario']}\n\n**Ticket:** {r['input']}\n\n**Summary:** {r['summary']}\n")
        for t, txt in r["replies"].items():
            out.append(f"- **{t}** ({r['words'].get(t)} words): {txt}")
        out.append(f"\n**Citations:** " + "; ".join(f"`{c['article_id']}` {'✅' if c['valid'] else '❌'} “{c['quote']}”" for c in r["citations"]))
        out.append(f"\n**Reasons:** {r['reasons']}\n")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.DEFAULT_MODEL, choices=list(config.MODELS))
    ap.add_argument("--prompt", default=config.ASSISTANT_PROMPT_VERSION)
    ap.add_argument("--classifier-model", default=None)
    ap.add_argument("--cache-only", action="store_true")
    a = ap.parse_args()
    llm.CACHE_ONLY = a.cache_only
    res = evaluate(a.model, a.prompt, a.classifier_model)
    print(json.dumps(res["summary"], indent=1, ensure_ascii=False))
