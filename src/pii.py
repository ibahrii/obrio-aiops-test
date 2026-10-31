"""PII masking applied to ticket text before ANY LLM call.

Masks emails, card numbers, phone numbers and customer names with fixed
placeholders: [EMAIL], [CARD], [PHONE], [NAME].

Names are found three ways:
  * names the caller already knows (requester name from the CRM webhook) — the most reliable source;
  * self-introductions ("my name is ...", "мене звати ...", "me llamo ...");
  * a sign-off at the very end of the ticket ("Regards,\\nAnna Kovalenko").
Expert profile names inside complaints ("expert Luna Starr") are deliberately NOT masked: they are public
marketplace pseudonyms that the triage needs, not customer PII.

Over-masking (e.g. a long order number read as a phone) is accepted: it is safe, under-masking is not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD_CANDIDATE_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
PHONE_RE = re.compile(r"(?<![\w$€£₴.,])\+?\(?\d[\d\s().-]{7,}\d(?![\w%])")

_NAME = r"[A-ZÀ-ÖØ-ÞА-ЯІЇЄҐ][a-zà-öø-ÿа-яіїєґ'’-]+"
_FULL_NAME = rf"{_NAME}(?:\s+{_NAME}){{0,2}}"
INTRO_RE = re.compile(
    r"(?:\bmy name is|\bthis is|\bname:|\bмене звати|\bменя зовут|\bme llamo|\bmi nombre es|\bmeu nome é|"
    r"\bme chamo|\bich heiße|\bmein name ist|\bje m'appelle)\s+(" + _FULL_NAME + ")",
    re.IGNORECASE,
)
SIGNOFF_RE = re.compile(
    r"(?:^|\n)\s*(?:thanks|thank you|regards|kind regards|best regards|best|cheers|sincerely|br|"
    r"дякую|з повагою|спасибо|gracias|saludos|obrigad[oa]|atenciosamente|danke|grüße|mit freundlichen grüßen)"
    r"[,!.]?\s+(" + _FULL_NAME + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)


@dataclass
class MaskResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return bool(self.counts)


def _sub(pattern: re.Pattern, text: str, token: str, counts: dict, check=None) -> str:
    def repl(m: re.Match) -> str:
        if check and not check(m.group(0)):
            return m.group(0)
        counts[token] = counts.get(token, 0) + 1
        return f"[{token}]"
    return pattern.sub(repl, text)


def _phone_ok(s: str) -> bool:
    n = len(re.sub(r"\D", "", s))
    return 9 <= n <= 15


_NAME_WORD_RE = re.compile(_NAME)


def _mask_name_group(pattern: re.Pattern, text: str, counts: dict) -> str:
    def repl(m: re.Match) -> str:
        # The trigger phrases are case-insensitive, but the name itself must be Proper Case, checked
        # case-sensitively: "This is Anna" is masked, "THIS IS RIDICULOUS" and "this is THE worst" are not.
        words = m.group(1).split()
        keep = 0
        for w in words:
            if not _NAME_WORD_RE.fullmatch(w):
                break
            keep += 1
        if keep == 0:
            return m.group(0)
        counts["NAME"] = counts.get("NAME", 0) + 1
        start = m.start(1) - m.start()
        end = 0  # end of the kept words inside group(1); the name may contain several spaces
        for w in words[:keep]:
            end = m.group(1).index(w, end) + len(w)
        return m.group(0)[:start] + "[NAME]" + m.group(0)[start + end:]
    return pattern.sub(repl, text)


def mask(text: str, known_names: list[str] | tuple[str, ...] = ()) -> MaskResult:
    """Return masked text and per-type counts. Text without PII is returned unchanged (byte-identical)."""
    if not text:
        return MaskResult(text or "")
    counts: dict[str, int] = {}
    out = _sub(EMAIL_RE, text, "EMAIL", counts)
    # Any 13-19 digit run is treated as a card, without a Luhn check: a mistyped real card must still be masked.
    out = _sub(CARD_CANDIDATE_RE, out, "CARD", counts)
    out = _sub(PHONE_RE, out, "PHONE", counts, check=_phone_ok)

    # Names known from the CRM: full name first, then each part of 3+ letters as a whole word.
    for full in sorted({n.strip() for n in known_names if n and n.strip()}, key=len, reverse=True):
        parts = [full] + [p for p in re.split(r"\s+", full) if len(p) >= 3]
        for p in parts:
            out = _sub(re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.IGNORECASE), out, "NAME", counts)
    out = _mask_name_group(INTRO_RE, out, counts)
    out = _mask_name_group(SIGNOFF_RE, out, counts)
    return MaskResult(out, counts)
