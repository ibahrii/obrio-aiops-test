"""Task 1: support ticket classifier (LLM + deterministic guards)."""
from __future__ import annotations

from . import config, guards, llm, pii
from .schemas import ClassificationResult, ClassifierOutput

USER_SPLIT = "---USER---"


def load_prompt(version: str) -> tuple[str, str]:
    """Prompt file = system part, then a `---USER---` line, then the user template with {ticket}."""
    text = (config.PROMPTS_DIR / f"classifier_{version}.md").read_text(encoding="utf-8")
    system, _, user_tpl = text.partition(USER_SPLIT)
    return system.strip(), (user_tpl.strip() or "{ticket}")


def classify(text: str, model_key: str | None = None, prompt_version: str | None = None,
             use_fallback: bool = True, use_cache: bool = True,
             known_names: tuple[str, ...] = ()) -> ClassificationResult:
    model_key = model_key or config.DEFAULT_MODEL
    prompt_version = prompt_version or config.CLASSIFIER_PROMPT_VERSION

    if not (text or "").strip():
        return ClassificationResult(
            category="feedback_other", priority="P4", needs_human=False, confidence=1.0,
            next_step={"route_to": "General Support", "action": "Close as empty ticket"},
            rationale="Empty ticket handled by code without an LLM call.", meta={"model": None, "rule": "empty"},
        )

    # Only masked text leaves the process; guards below still see the original text locally.
    masked = pii.mask(text, known_names)
    system, user_tpl = load_prompt(prompt_version)
    user = user_tpl.replace("{ticket}", masked.text)
    res = llm.call_structured(model_key, system, user, ClassifierOutput, cache_text=masked.text,
                              prompt_version=f"classifier_{prompt_version}", use_fallback=use_fallback,
                              use_cache=use_cache)
    if res.ok and res.data:
        out, overrides = guards.apply_classifier_guards(res.data, text)
        return ClassificationResult(**out, guard_overrides=overrides,
                                    meta={**res.meta(), "model_raw": res.data, "pii_masked": masked.counts})
    out = guards.safe_default("; ".join(a["event"] for a in res.attempts[-3:]))
    return ClassificationResult(**out, guard_overrides=["safe_default"], meta={**res.meta(), "pii_masked": masked.counts})
