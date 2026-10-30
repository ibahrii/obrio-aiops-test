"""BM25 retrieval over the (simulated) knowledge base, with a boost for articles of the ticket's category.

Why BM25 and not embeddings: 18 short articles with distinctive vocabulary (refund, cancel, password,
GDPR...), zero infra, deterministic and explainable scores. See REPORT.md section 8 for what changes at
hundreds of articles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from rank_bm25 import BM25Okapi

from . import config

INTERNAL_GUIDE_ID = "kb-017"  # tone guide: always given to the assistant as style rules, never cited to customers
CATEGORY_BOOST = 0.3          # added to the max-normalised BM25 score

_STOP = set("""a an the and or but if to of in on at for with from by is are was were be been it this that these those
i me my you your we our they them he she his her do does did have has had not no can could will would should
please hi hello thanks thank just so as about what when where how why which who there here am any all""".split())


def _stem(w: str) -> str:
    for suf in ("ing", "edly", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> list[str]:
    words = re.findall(r"\w+", (text or "").lower())
    return [_stem(w) for w in words if w not in _STOP and len(w) > 1]


@dataclass
class Article:
    id: str
    title: str
    category: str
    last_updated: str
    body: str
    path: str


def _parse(path) -> Article:
    raw = path.read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    meta = dict(line.split(":", 1) for line in fm.strip().splitlines())
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    return Article(meta["id"], meta["title"], meta["category"], meta["last_updated"], body.strip(), path.name)


@lru_cache(maxsize=1)
def load_kb() -> dict[str, Article]:
    return {a.id: a for a in (_parse(p) for p in sorted(config.KB_DIR.glob("*.md")))}


@lru_cache(maxsize=1)
def _index():
    arts = [a for a in load_kb().values() if a.id != INTERNAL_GUIDE_ID]
    docs = [tokenize(f"{a.title} {a.title} {a.body}") for a in arts]
    return arts, BM25Okapi(docs)


def search(query: str, categories: tuple[str, ...] = (), k: int = 3) -> list[dict]:
    arts, bm25 = _index()
    scores = bm25.get_scores(tokenize(query))
    top = float(max(scores)) if len(scores) and max(scores) > 0 else 1.0
    results = []
    for a, s in zip(arts, scores):
        norm = float(s) / top
        boost = CATEGORY_BOOST if a.category in categories else 0.0
        results.append({"id": a.id, "title": a.title, "category": a.category, "bm25": round(float(s), 3),
                        "score": round(norm + boost, 3), "boosted": bool(boost)})
    results.sort(key=lambda r: r["score"], reverse=True)
    return [r for r in results[:k] if r["score"] > 0]


def build_query(ticket: str, classification=None, expand: bool = True) -> str:
    """Ticket text, optionally expanded with the classifier's English rationale and action.
    Expansion is what makes non-English tickets match the English KB."""
    if not expand or classification is None:
        return ticket
    return f"{ticket}\n{classification.rationale}\n{classification.next_step.action}"
