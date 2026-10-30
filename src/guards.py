"""Deterministic guards: human-in-the-loop rules, routing, injection/crisis detection,
citation verification, tone length limits and a light language check.

The model's opinion (`needs_human`, `human_reasons`) is kept, but code can only ADD
reasons / escalate, never remove them. Code is the source of truth for routing.
"""
from __future__ import annotations

import re
import unicodedata

from . import config

ROUTE_BY_CATEGORY = {
    "billing_subscription": "Billing",
    "refund_request": "Billing",
    "technical_issue": "Tech",
    "account_access": "Tech",
    "expert_complaint": "Expert Quality",
    "product_question": "General Support",
    "privacy_legal": "Legal & Privacy",
    "safety_wellbeing": "Trust & Safety",
    "feedback_other": "General Support",
    "unclassified": "General Support",
}
MONEY_CATEGORIES = {"billing_subscription", "refund_request"}

# --- regex nets (multilingual where it matters; deliberately high-recall) -----------------
INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?|rules)",
    r"disregard (all |the )?(previous|prior|above)",
    r"you are now (in )?(admin|developer|dan|god) mode",
    r"\bsystem prompt\b", r"\bact as (an? )?(admin|system)\b",
    r"(mark|set|classify) (this|the) ticket as",
    r"approve (a |the )?(full )?refund",
    r"ignora (todas )?las instrucciones", r"ignoriere (alle )?(vorherigen )?anweisungen",
    r"ігноруй (всі |усі )?(попередні )?інструкції",
]
CRISIS_PATTERNS = [
    r"\b(kill|hurt|harm) (myself|me)\b", r"\bsuicid", r"\bend (it all|my life)\b",
    r"\b(want|wanna) to die\b", r"\bdon'?t want to (live|be here)\b",
    r"\b(easier|better) .{0,30}if i (just )?(disappear|wasn'?t here|was gone)",
    r"\b(no|stopped seeing the) point (in|of) (anything|living|life)",
    r"не хочу жити", r"покінчити з собою", r"no quiero vivir", r"quitarme la vida",
    r"não quero viver", r"ich will nicht mehr leben", r"umbringen",
]
CHARGEBACK_PATTERNS = [r"charge ?back", r"dispute (the|this|with my) (charge|bank)", r"contracargo",
                       r"r[üu]ckbuchung", r"estorno", r"lawyer", r"attorney", r"sue you", r"legal action",
                       r"юрист", r"адвокат", r"суд\b", r"abogado", r"anwalt", r"advogado"]
OUT_OF_POLICY_PATTERNS = [r"\b(\d+|two|three|four|five|six|several) months? ago\b", r"last year",
                          r"\ball (my|the) (money|payments)\b", r"\bevery (payment|month) since\b"]
SERIOUS_EXPERT_PATTERNS = [r"\bfraud", r"\bscam", r"\bfake\b", r"\bcheat", r"\blied\b", r"\binsult",
                           r"\brude\b", r"\bcalled me\b", r"\bharass", r"\bthreat", r"\bstupid\b", r"\bugly\b",
                           r"шахра", r"обман", r"образ", r"estafa", r"betrug", r"golpe"]
REPEAT_CONTACT_PATTERNS = [r"\b(again|third time|second time|already (wrote|contacted|asked|told))\b",
                           r"\bstill (no|not|haven'?t)\b", r"\bno one (answers|replied)\b",
                           r"вже (писав|писала|звертав)", r"знову", r"otra vez", r"schon wieder"]
MONEY_PROMISE_PATTERNS = [
    r"\bwe(?:'ll| will| have| ve|'ve)? (?:issue|process|refund|credit|compensat)\w*",
    r"\byou will (?:receive|get) (?:a |your )?(?:full |partial )?(?:refund|money back|credits? back|compensation)",
    r"\b(?:refund|compensation|credits?) (?:has|have) been (?:issued|processed|added|approved)",
    r"\bfree (?:month|credits?|reading|session)\b",
    r"\bas a (?:gesture|goodwill)\b",
]


def _any(patterns: list[str], text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in patterns)


def detect_injection(text: str) -> bool:
    return _any(INJECTION_PATTERNS, text)


def detect_crisis(text: str) -> bool:
    return _any(CRISIS_PATTERNS, text)


def detect_chargeback_or_legal(text: str) -> bool:
    return _any(CHARGEBACK_PATTERNS, text)


def detect_repeat_angry(text: str, sentiment: str | None) -> bool:
    return _any(REPEAT_CONTACT_PATTERNS, text) and sentiment in ("angry", "frustrated")


def promises_money(text: str) -> bool:
    return _any(MONEY_PROMISE_PATTERNS, text)


# --------------------------------------------------------------------------- Task 1
def apply_classifier_guards(model_out: dict, ticket_text: str) -> tuple[dict, list[str]]:
    """Return (result_dict, overrides). Adds HITL reasons, enforces routing and safety priority."""
    r = dict(model_out)
    r["next_step"] = dict(r.get("next_step") or {})
    overrides: list[str] = []
    model_needs_human = bool(r.get("needs_human"))
    reasons: list[str] = [f"model: {x}" for x in (r.get("human_reasons") or [])] if model_needs_human else []
    if model_needs_human and not reasons:
        reasons.append("model: flagged for review")
    cat, sec = r["category"], r.get("secondary_category")
    if sec == cat:
        r["secondary_category"] = sec = None

    # Safety net: crisis wording found by regex but model chose another category -> escalate.
    if detect_crisis(ticket_text) and cat != "safety_wellbeing" and sec != "safety_wellbeing":
        reasons.append("crisis keywords detected by code (model did not flag safety)")
        overrides.append(f"crisis_net: kept category {cat}, forced P1 + human")
        r["priority"] = "P1"
    if "safety_wellbeing" in (cat, sec):
        if cat != "safety_wellbeing":
            overrides.append(f"safety_wellbeing promoted from secondary over {cat}")
            r["secondary_category"], r["category"] = cat, "safety_wellbeing"
            cat, sec = "safety_wellbeing", r["secondary_category"]
        if r["priority"] != "P1":
            overrides.append(f"priority {r['priority']}->P1 (safety always P1)")
            r["priority"] = "P1"
        reasons.append("safety_wellbeing: possible vulnerable user")

    if cat == "privacy_legal":
        reasons.append("privacy_legal: legal/GDPR consequences")
    if cat == "refund_request" or sec == "refund_request":
        if detect_chargeback_or_legal(ticket_text):
            reasons.append("refund with chargeback/legal threat")
        if _any(OUT_OF_POLICY_PATTERNS, ticket_text):
            reasons.append("refund possibly outside 14-day policy")
    if detect_chargeback_or_legal(ticket_text) and cat != "privacy_legal" and "refund with chargeback/legal threat" not in reasons:
        reasons.append("chargeback/legal threat mentioned")
    if "expert_complaint" in (cat, sec) and _any(SERIOUS_EXPERT_PATTERNS, ticket_text):
        reasons.append("expert_complaint with fraud/insult accusation (two-sided marketplace)")
    # Mixed = two different domains, one of them money. refund+billing is one (money) domain, not "mixed".
    if sec and (cat in MONEY_CATEGORIES) != (sec in MONEY_CATEGORIES):
        reasons.append("mixed topics involving money")
    if detect_injection(ticket_text):
        reasons.append("prompt-injection attempt detected")
    conf = float(r.get("confidence") or 0.0)
    if conf < config.CONFIDENCE_THRESHOLD:
        reasons.append(f"low confidence {conf:.2f} < {config.CONFIDENCE_THRESHOLD}")

    # Deterministic routing
    route = "Expert Ops" if r.get("requester_type") == "expert" else ROUTE_BY_CATEGORY.get(cat, "General Support")
    if r["next_step"].get("route_to") != route:
        overrides.append(f"route {r['next_step'].get('route_to')}->{route}")
        r["next_step"]["route_to"] = route

    uniq = list(dict.fromkeys(reasons))  # dedupe, keep order
    r["human_reasons"] = uniq
    r["needs_human"] = bool(uniq)
    if r["needs_human"] and not model_needs_human:
        overrides.append("needs_human set by code")
    return r, overrides


def safe_default(reason: str) -> dict:
    return {
        "category": "unclassified", "secondary_category": None, "priority": "P2",
        "requester_type": "unknown", "language": "unknown", "sentiment": "calm",
        "next_step": {"route_to": "General Support", "action": "Manual triage: automatic classification failed"},
        "confidence": 0.0, "needs_human": True, "human_reasons": [f"invalid model output after all fallbacks: {reason}"],
        "rationale": "Safe default applied by code.",
    }


# --------------------------------------------------------------------------- Task 2
TONE_LIMITS = {"formal": 120, "empathetic": 150, "short": 50}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_citation(quote: str, article_body: str | None) -> bool:
    if not article_body or not quote or len(quote.strip()) < 8:
        return False
    q = _norm(quote).strip(' ."\'…')
    return q in _norm(article_body)


def word_count(s: str) -> int:
    return len(re.findall(r"\S+", s or ""))


def check_lengths(replies: dict) -> dict:
    out = {}
    for tone, limit in TONE_LIMITS.items():
        n = word_count(replies.get(tone, ""))
        out[tone] = {"words": n, "limit": limit, "ok": n <= limit}
    out["formal"]["no_emoji"] = not EMOJI_RE.search(replies.get("formal", ""))
    out["formal"]["ok"] = out["formal"]["ok"] and out["formal"]["no_emoji"]
    return out


# Tiny stop-word language guesser (no external deps); good enough to catch "replied in English to a Spanish ticket".
_STOP = {
    "en": "the and you your to is are we for of with this that please have can not".split(),
    "es": "el la los las de que y en por para su usted gracias hola con una le es".split(),
    "pt": "o a os as de que e em para por sua você obrigado olá com uma não é".split(),
    "de": "der die das und ist nicht sie ihr wir zu mit für ein eine bitte den".split(),
    "fr": "le la les et est vous nous pour de des une avec merci pas".split(),
    "it": "il la le e di che per con una non sono grazie ciao".split(),
    "uk": "і в на що не ви ми ваш для це з як будь ласка дякуємо".split(),
}


def guess_language(text: str) -> str:
    t = (text or "").lower()
    if not t.strip():
        return "unknown"
    cyr = len(re.findall(r"[а-яіїєґ]", t))
    lat = len(re.findall(r"[a-z]", t))
    if cyr > lat:
        return "uk" if re.search(r"[іїєґ]", t) else "ru"
    words = re.findall(r"[a-zà-ÿßäöü']+", t)
    scores = {lang: sum(w in set(sw) for w in words) for lang, sw in _STOP.items() if lang != "uk"}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def language_matches(expected: str, reply: str) -> bool:
    if not expected or expected == "unknown":
        return True
    return guess_language(reply) == expected.split("-")[0].lower()
