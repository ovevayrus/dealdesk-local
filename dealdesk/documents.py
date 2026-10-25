"""Synthetic knowledge pack loading and simple local lexical search (BM25).

Documents are Markdown with a small front-matter header. Each H2 section is a
citable passage. Retrieved text is evidence only: passages containing
instruction-like text are flagged and never treated as commands.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from .config import POLICY_DOC, SYNTHETIC_DIR

DOCUMENTS_DIR = SYNTHETIC_DIR / "documents"
POLICY_META = {
    "doc_id": "POLICY-001",
    "title": "Synthetic demonstration pricing policy (synthetic-demo-v1)",
    "doc_type": "pricing_policy",
    "account_id": "all",
    "effective_date": "2026-10-25",
    "classification": "internal_synthetic",
}

_STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i in is it its of on or our so that the "
    "their them there these this to was we what when where which who why will with you your about into "
    "than then they us".split()
)
_TOKEN = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")
_INSTRUCTION_LIKE = re.compile(
    r"(ignore (?:the |all |any |previous |prior )*(?:instructions|policy|pricing policy|rules))|"
    r"(note to (?:any )?ai)|(ai assistant)|(system (?:note|prompt))|(approve an? \d+% discount)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Passage:
    passage_id: str
    doc_id: str
    title: str
    doc_type: str
    account_id: str
    effective_date: str
    section: str
    text: str
    path: str
    instruction_like: bool

    def citation(self) -> dict[str, Any]:
        data = asdict(self)
        data["untrusted_instruction_detected"] = data.pop("instruction_like")
        return data


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in _TOKEN.findall(text.lower()):
        if token in _STOPWORDS:
            continue
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tokens


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    _, header, body = text.split("---", 2)
    meta = {}
    for line in header.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.split("  #")[0].strip()
    return meta, body


def _sections(body: str) -> Iterable[tuple[str, str]]:
    heading = "Overview"
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if "".join(lines).strip():
                yield heading, "\n".join(lines).strip()
            heading, lines = line[3:].strip(), []
        elif line.startswith("# "):
            continue
        else:
            lines.append(line)
    if "".join(lines).strip():
        yield heading, "\n".join(lines).strip()


def _passages_for(path: Path, meta: dict[str, str], body: str) -> list[Passage]:
    relative = path.relative_to(SYNTHETIC_DIR.parents[1]).as_posix()
    passages = []
    for index, (section, text) in enumerate(_sections(body), start=1):
        passages.append(Passage(
            passage_id=f"{meta['doc_id']}#s{index}",
            doc_id=meta["doc_id"],
            title=meta.get("title", meta["doc_id"]),
            doc_type=meta.get("doc_type", "document"),
            account_id=meta.get("account_id", "all"),
            effective_date=meta.get("effective_date", ""),
            section=section,
            text=text,
            path=relative,
            instruction_like=bool(_INSTRUCTION_LIKE.search(text)),
        ))
    return passages


@lru_cache(maxsize=1)
def load_corpus() -> tuple[Passage, ...]:
    passages: list[Passage] = []
    for path in sorted(DOCUMENTS_DIR.rglob("*.md")):
        meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        if meta.get("doc_id"):
            passages.extend(_passages_for(path, meta, body))
    if POLICY_DOC.is_file():
        _, body = _parse_front_matter(POLICY_DOC.read_text(encoding="utf-8"))
        passages.extend(_passages_for(POLICY_DOC, POLICY_META, body))
    return tuple(passages)


@lru_cache(maxsize=1)
def _index() -> tuple[list[Counter], dict[str, int], float]:
    docs = [Counter(tokenize(f"{p.title} {p.section} {p.section} {p.text}")) for p in load_corpus()]
    frequency: Counter = Counter()
    for counts in docs:
        frequency.update(counts.keys())
    average = sum(sum(c.values()) for c in docs) / max(len(docs), 1)
    return docs, dict(frequency), average


def search_documents(query: str, *, account_id: str | None = None, doc_types: Iterable[str] | None = None,
                     limit: int = 4, min_score: float = 1.0) -> list[dict[str, Any]]:
    """Rank passages with BM25. ``account_id`` is a server-side filter: other accounts' profiles are excluded."""
    corpus = load_corpus()
    docs, frequency, average = _index()
    terms = tokenize(query)
    allowed_types = set(doc_types) if doc_types else None
    k1, b, total = 1.4, 0.75, len(corpus)
    results = []
    for passage, counts in zip(corpus, docs):
        if account_id and passage.account_id not in ("all", account_id):
            continue
        if allowed_types and passage.doc_type not in allowed_types:
            continue
        length = sum(counts.values())
        score = 0.0
        for term in set(terms):
            tf = counts.get(term, 0)
            if not tf:
                continue
            idf = math.log(1 + (total - frequency[term] + 0.5) / (frequency[term] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average))
        if score >= min_score:
            results.append((score, passage))
    results.sort(key=lambda item: (-item[0], item[1].passage_id))
    return [dict(passage.citation(), score=round(score, 3)) for score, passage in results[:limit]]


def best_sentence(text: str, query: str) -> str:
    """Pick the passage sentence or bullet that best overlaps the query, for a short cited fact."""
    pieces = [piece.strip(" -*\t") for piece in re.split(r"(?<=[.!?])\s+|\n+", text) if piece.strip(" -*\t")]
    wanted = set(tokenize(query))
    if not pieces:
        return text.strip()
    return max(pieces, key=lambda piece: (len(wanted & set(tokenize(piece))), -pieces.index(piece)))


def get_document(doc_id: str) -> dict[str, Any] | None:
    passages = [p for p in load_corpus() if p.doc_id == doc_id]
    if not passages:
        return None
    first = passages[0]
    return {
        "doc_id": doc_id,
        "title": first.title,
        "doc_type": first.doc_type,
        "account_id": first.account_id,
        "effective_date": first.effective_date,
        "path": first.path,
        "sections": [{"passage_id": p.passage_id, "section": p.section, "text": p.text} for p in passages],
    }
