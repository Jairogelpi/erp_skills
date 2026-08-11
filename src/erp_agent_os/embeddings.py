"""Embeddings retriever (CLAUDE.md §22, point 2).

`SentenceTransformer` is loaded lazily and only when no `embed` function is
injected — unit tests inject a deterministic stub so the suite never needs
network access or a model download. Production callers get the real
multilingual model by default.
"""

from collections.abc import Callable

from erp_agent_os.retrieval import RetrievalCandidate
from erp_agent_os.skills import SkillDefinition

EmbedFn = Callable[[list[str]], list[list[float]]]

DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _load_default_embedder() -> EmbedFn:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(DEFAULT_MODEL_NAME)

    def embed(texts: list[str]) -> list[list[float]]:
        return model.encode(texts, normalize_embeddings=True).tolist()

    return embed


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class EmbeddingRetriever:
    def __init__(
        self, skills: list[SkillDefinition], embed: EmbedFn | None = None
    ) -> None:
        self._skills = skills
        self._embed = embed or _load_default_embedder()
        self._vectors = self._embed([skill.description for skill in skills])

    def rank(self, query: str, *, role: str | None = None) -> list[RetrievalCandidate]:
        query_vector = self._embed([query])[0]
        candidates = [
            RetrievalCandidate(skill, _dot(query_vector, vector))
            for skill, vector in zip(self._skills, self._vectors, strict=True)
            if role is None or role in skill.permissions.allowed_roles
        ]
        return sorted(candidates, key=lambda c: c.score, reverse=True)
