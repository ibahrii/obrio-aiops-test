import json
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import assistant, classifier, config, llm, pii  # noqa: E402
from eval.simulate_failures import GOOD  # noqa: E402

RAW = {
    "email": "anna.kovalenko@gmail.com",
    "card": "4111 1111 1111 1111",
    "phone": "+380 67 123 4567",
    "name": "Anna Kovalenko",
}
TICKET = (f"Hi, my name is {RAW['name']}. I was charged twice on card {RAW['card']}. "
          f"Please reply to {RAW['email']} or call {RAW['phone']}.\nRegards,\n{RAW['name']}")


@pytest.mark.parametrize("text,expected", [
    ("write to john.doe+x@mail.co.uk please", "write to [EMAIL] please"),
    ("card 4111-1111-1111-1111 failed", "card [CARD] failed"),
    ("card 5375414100001235 (typo, fails Luhn) still masked", "card [CARD] (typo, fails Luhn) still masked"),
    ("call me at +1 (415) 555-0132", "call me at [PHONE]"),
    ("телефон 067 123 45 67", "телефон [PHONE]"),
    ("My name is Maria Lopez and I need help", "My name is [NAME] and I need help"),
    ("Мене звати Олена, допоможіть", "Мене звати [NAME], допоможіть"),
    ("Me llamo Lucía, gracias", "Me llamo [NAME], gracias"),
    ("thanks for help\nBest regards,\nJohn Smith", "thanks for help\nBest regards,\n[NAME]"),
])
def test_mask_types(text, expected):
    assert pii.mask(text).text == expected


@pytest.mark.parametrize("text", [
    "THIS IS RIDICULOUS!!! Your stupid app logs me out",
    "this is THE third time I'm writing",
    "Charged $49.99 on 2026-10-12, error 503 at 3am, last 4 digits 1234",
    "My reading with expert Luna Starr was very generic",   # expert pseudonyms are not customer PII
    "Thanks Mira for the amazing reading <3",
])
def test_no_false_positives(text):
    assert pii.mask(text).text == text


def test_known_names_from_crm_are_masked_everywhere():
    r = pii.mask("Anna here. anna is upset, KOVALENKO account", known_names=["Anna Kovalenko"])
    assert "anna" not in r.text.lower() and "kovalenko" not in r.text.lower()


def test_existing_datasets_are_unchanged_by_masking():
    """Guarantees eval/results stay valid: no eval/holdout/assistant ticket contains maskable PII."""
    for f in ("tickets_eval.jsonl", "tickets_holdout.jsonl", "assistant_eval.jsonl"):
        for line in (config.DATA_DIR / f).read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            assert pii.mask(t["text"]).text == t["text"], t["id"]


class Capture:
    """Fake transport that records exactly what would be sent to the provider."""

    def __init__(self, response: dict):
        self.response, self.sent = response, []

    def __call__(self, spec, system, messages, schema):
        self.sent.append(system + "\n" + "\n".join(m["content"] for m in messages))
        return llm.RawResponse(text=json.dumps(self.response), in_tokens=1, out_tokens=1)


@pytest.fixture
def capture(monkeypatch):
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(config, "CACHE_DIR", tmp / "cache")
    monkeypatch.setattr(config, "LOG_DIR", tmp / "logs")
    cap = Capture(GOOD)
    monkeypatch.setattr(llm, "TRANSPORT_OVERRIDE", cap)
    return cap


def _assert_no_raw_pii(payloads: list[str]):
    assert payloads, "no LLM call was made"
    for p in payloads:
        for kind, value in RAW.items():
            assert value not in p, f"raw {kind} reached the LLM"
        assert "[EMAIL]" in p and "[CARD]" in p and "[PHONE]" in p and "[NAME]" in p


def test_classifier_sends_only_masked_text(capture):
    r = classifier.classify(TICKET, model_key="gemini-flash-lite")
    _assert_no_raw_pii(capture.sent)
    assert r.meta["pii_masked"] == {"EMAIL": 1, "CARD": 1, "PHONE": 1, "NAME": 2}


def test_assistant_sends_only_masked_text(capture, monkeypatch):
    assistant_answer = {"summary": "s", "replies": {"formal": "f", "empathetic": "e", "short": "s"},
                        "citations": [], "reply_language": "en", "kb_has_answer": False,
                        "human_decision_required": True, "reasons": ["the KB does not answer"]}

    def transport(spec, system, messages, schema):
        capture.sent.append(system + "\n" + "\n".join(m["content"] for m in messages))
        body = assistant_answer if "replies" in json.dumps(schema) else GOOD
        return llm.RawResponse(text=json.dumps(body), in_tokens=1, out_tokens=1)

    monkeypatch.setattr(llm, "TRANSPORT_OVERRIDE", transport)
    assistant.assist(TICKET, model_key="gemini-flash-lite")
    assert len(capture.sent) == 2  # classifier call + assistant call
    _assert_no_raw_pii(capture.sent)
