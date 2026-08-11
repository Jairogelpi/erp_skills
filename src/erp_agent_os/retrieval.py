"""TF-IDF retrieval baseline, hybrid ranker, and abstention gate.

Scope per CLAUDE.md §22 (recuperación semántica) and RF-04–05: rank
registered skills against a query by cosine similarity over hand-rolled
TF-IDF vectors (stdlib only — no ML dependency for this baseline), filtered
by role; combine any vector-similarity retriever (TF-IDF or embeddings)
with module/operation-match boosts (`HybridRetriever`, §22 formula
`w1..w3`); and a pure abstention rule over score threshold, score margin,
and missing required fields. `w4` (`slot_compatibility`) and `w5`
(`historical_reliability`) are omitted pending an argument-schema
compatibility scorer and execution-history data that don't exist yet.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from erp_agent_os.skills import SkillDefinition

_TOKEN_RE = re.compile(r"[a-záéíóúñ0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _term_frequencies(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    total = len(tokens) or 1
    return {term: count / total for term, count in counts.items()}


def _inverse_document_frequencies(corpus: list[list[str]]) -> dict[str, float]:
    doc_count = len(corpus)
    document_frequency: Counter[str] = Counter()
    for tokens in corpus:
        for term in set(tokens):
            document_frequency[term] += 1
    return {
        term: math.log((doc_count + 1) / (df + 1)) + 1
        for term, df in document_frequency.items()
    }


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    frequencies = _term_frequencies(tokens)
    return {term: tf * idf.get(term, 0.0) for term, tf in frequencies.items()}


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    common_terms = set(a) & set(b)
    dot_product = sum(a[term] * b[term] for term in common_terms)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


@dataclass(frozen=True)
class RetrievalCandidate:
    skill: SkillDefinition
    score: float


class TfidfRetriever:
    def __init__(self, skills: list[SkillDefinition]) -> None:
        self._skills = skills
        corpus = [_tokenize(skill.description) for skill in skills]
        self._idf = _inverse_document_frequencies(corpus)
        self._vectors = [_vector(tokens, self._idf) for tokens in corpus]

    def rank(self, query: str, *, role: str | None = None) -> list[RetrievalCandidate]:
        query_vector = _vector(_tokenize(query), self._idf)
        candidates = [
            RetrievalCandidate(skill, _cosine_similarity(query_vector, vector))
            for skill, vector in zip(self._skills, self._vectors, strict=True)
            if role is None or role in skill.permissions.allowed_roles
        ]
        return sorted(candidates, key=lambda c: c.score, reverse=True)


class VectorRetriever(Protocol):
    def rank(
        self, query: str, *, role: str | None = None
    ) -> list[RetrievalCandidate]: ...


@dataclass(frozen=True)
class HybridWeights:
    vector_similarity: float = 0.6
    module_match: float = 0.25
    operation_match: float = 0.15


class HybridRetriever:
    """Combines a vector retriever with module/operation-match boosts.

    `w4`/`w5` from the CLAUDE.md §22 formula are intentionally absent —
    see module docstring.
    """

    def __init__(
        self,
        skills: list[SkillDefinition],
        vector_retriever: VectorRetriever,
        weights: HybridWeights = HybridWeights(),
    ) -> None:
        self._skills = skills
        self._vector_retriever = vector_retriever
        self._weights = weights

    def rank(
        self,
        query: str,
        *,
        role: str | None = None,
        module: str | None = None,
        operation: str | None = None,
    ) -> list[RetrievalCandidate]:
        vector_scores = {
            candidate.skill.skill_id: candidate.score
            for candidate in self._vector_retriever.rank(query, role=role)
        }
        candidates = []
        for skill in self._skills:
            if skill.skill_id not in vector_scores:
                continue
            module_match = 1.0 if module is not None and skill.module == module else 0.0
            operation_match = (
                1.0 if operation is not None and skill.operation == operation else 0.0
            )
            score = (
                self._weights.vector_similarity * vector_scores[skill.skill_id]
                + self._weights.module_match * module_match
                + self._weights.operation_match * operation_match
            )
            candidates.append(RetrievalCandidate(skill, score))
        return sorted(candidates, key=lambda c: c.score, reverse=True)


def should_abstain(
    ranked: list[RetrievalCandidate],
    missing_fields: list[str],
    *,
    threshold: float = 0.15,
    margin: float = 0.05,
) -> bool:
    if missing_fields:
        return True
    if not ranked:
        return True
    if ranked[0].score < threshold:
        return True
    if len(ranked) > 1 and (ranked[0].score - ranked[1].score) < margin:
        return True
    return False
