"""Task 2: agent assistant. ticket -> classifier -> BM25 top-3 -> one LLM call -> checked JSON."""
from __future__ import annotations

import re

from . import classifier, config, guards, llm, pii, retrieval
from .schemas import AssistantOutput, AssistantResult, Replies

USER_SPLIT = "---USER---"


def load_prompt(version: str) -> tuple[str, str]:
    text = (config.PROMPTS_DIR / f"assistant_{version}.md").read_text(encoding="utf-8")
    system, _, user_tpl = text.partition(USER_SPLIT)
    return system.strip(), user_tpl.strip()


def _articles_block(hits: list[dict]) -> str:
    kb = retrieval.load_kb()
    if not hits:
        return "(no articles retrieved)"
    return "\n\n".join(f'<article id="{h["id"]}" title="{kb[h["id"]].title}">\n{kb[h["id"]].body}\n</article>' for h in hits)


def assist(text: str, model_key: str | None = None, prompt_version: str | None = None,
           classifier_model: str | None = None, use_fallback: bool = True, expand_query: bool = True,
           use_cache: bool = True, known_names: tuple[str, ...] = ()) -> AssistantResult:
    model_key = model_key or config.DEFAULT_MODEL
    prompt_version = prompt_version or config.ASSISTANT_PROMPT_VERSION
    cls = classifier.classify(text, model_key=classifier_model or model_key, use_fallback=use_fallback,
                              use_cache=use_cache, known_names=known_names)
    masked = pii.mask(text, known_names)  # the LLM only ever sees this; local checks use the original
    cats = tuple(c for c in (cls.category, cls.secondary_category) if c)
    hits = retrieval.search(retrieval.build_query(masked.text, cls, expand=expand_query), categories=cats, k=3)

    kb = retrieval.load_kb()
    system, user_tpl = load_prompt(prompt_version)
    lang = cls.language if cls.language and cls.language != "unknown" else "en"
    fill = {"{tone_guide}": kb[retrieval.INTERNAL_GUIDE_ID].body, "{language}": lang, "{category}": cls.category,
            "{priority}": cls.priority, "{articles}": _articles_block(hits)}
    for k, v in fill.items():  # placeholders may sit in the system part as well as in the user part
        system, user_tpl = system.replace(k, v), user_tpl.replace(k, v)
    user = user_tpl.replace("{ticket}", masked.text)
    res = llm.call_structured(model_key, system, user, AssistantOutput, cache_text=masked.text,
                              prompt_version=f"assistant_{prompt_version}", kb_version=config.KB_VERSION,
                              use_fallback=use_fallback, use_cache=use_cache)

    if not (res.ok and res.data):
        return AssistantResult(
            summary="Automatic draft failed; handle this ticket manually.",
            replies=Replies(formal="", empathetic="", short=""), reply_language=lang, kb_has_answer=False,
            human_decision_required=True, reasons=["assistant model output invalid after all fallbacks"],
            classification=cls, retrieved=hits, meta=res.meta(),
        )

    out = res.data
    reasons: list[str] = []
    if out.get("human_decision_required"):
        for r in out.get("reasons", []) or ["flagged for review"]:
            # Discernment: a model claim of a chargeback/legal threat is checked against the ticket text.
            unsupported = re.search(r"chargeback|legal", r, re.I) and not guards.detect_chargeback_or_legal(text)
            reasons.append(f"model (not supported by ticket text): {r}" if unsupported else f"model: {r}")
    # Every classifier HITL reason is shown to the agent too, including "mixed topics with money"
    # (Ihor's decision, REPORT.md section 17): a money topic next to another one is the agent's call.
    reasons += [f"classifier: {r}" for r in cls.human_reasons]

    citations, invalid = [], 0
    for c in out.get("citations", []):
        art = kb.get(c["article_id"])
        ok = bool(art) and c["article_id"] in {h["id"] for h in hits} and guards.verify_citation(c["quote"], art.body if art else None)
        invalid += not ok
        citations.append({**c, "valid": ok})
    if invalid:
        reasons.append(f"{invalid} citation(s) not found verbatim in the retrieved KB articles")
    if not out.get("kb_has_answer") or not any(c["valid"] for c in citations):
        reasons.append("no source in the knowledge base for this answer")
    replies = out["replies"]
    if any(guards.promises_money(replies[t]) for t in ("formal", "empathetic", "short")):
        reasons.append("a draft reply promises money, credits or an exception")
    if guards.detect_repeat_angry(text, cls.sentiment):
        reasons.append("repeated contact from an angry customer")

    lengths = guards.check_lengths(replies)
    lang_ok = {t: guards.language_matches(lang, replies[t]) for t in ("formal", "empathetic", "short")}
    checks = {"lengths": lengths, "language": lang_ok, "expected_language": lang,
              "citations_valid": sum(c["valid"] for c in citations), "citations_total": len(citations)}

    reasons = list(dict.fromkeys(reasons))
    return AssistantResult(
        summary=out["summary"], replies=Replies(**replies), citations=citations,
        reply_language=out.get("reply_language", lang), kb_has_answer=bool(out.get("kb_has_answer")),
        human_decision_required=bool(reasons), reasons=reasons, checks=checks,
        classification=cls, retrieved=hits, meta=res.meta(),
    )
