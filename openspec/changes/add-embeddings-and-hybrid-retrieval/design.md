# Design: embeddings retriever and hybrid ranker

## Contract

```python
EmbedFn = Callable[[list[str]], list[list[float]]]

class EmbeddingRetriever:
    def __init__(self, skills, embed: EmbedFn | None = None) -> None: ...
    def rank(self, query, *, role=None) -> list[RetrievalCandidate]: ...

@dataclass(frozen=True)
class HybridWeights:
    vector_similarity: float = 0.6
    module_match: float = 0.25
    operation_match: float = 0.15

class HybridRetriever:
    def __init__(self, skills, vector_retriever: VectorRetriever,
                 weights: HybridWeights = HybridWeights()) -> None: ...
    def rank(self, query, *, role=None, module=None, operation=None) -> list[RetrievalCandidate]: ...
```

## Alternatives considered

- **Test against the real model**: rejected for the unit-test suite. A
  real `SentenceTransformer` load is slow and needs the model cached
  on-disk; dependency injection (`embed`) lets tests be instant and
  network-free while the same code path is exercised in production
  through the default loader. The user's download authorization was used
  to confirm the model loads and is importable (verified directly, not
  folded into `pytest`), not to make every test run depend on it.
- **`w4`/`w5` as zero-weighted no-op terms in the formula**: rejected in
  favor of omitting them entirely. A zero-weighted term that's never
  computed would silently imply "supported but tuned to zero"; omitting
  the parameters makes "not implemented yet" the honest, visible state
  instead of a hidden default.
- **numpy for the dot product in `EmbeddingRetriever`**: rejected. numpy
  is already a transitive dependency via `sentence-transformers`/torch,
  but `_dot` over two `list[float]` in pure Python is simpler than adding
  an explicit numpy import for one one-line reduction, and keeps
  `embeddings.py`'s own code numpy-free.
- **`VectorRetriever` as an ABC**: rejected. A `Protocol` (structural
  typing) lets `TfidfRetriever` and `EmbeddingRetriever` satisfy
  `HybridRetriever`'s dependency without either inheriting from a shared
  base class they don't otherwise need.
- **mypy performance**: `follow_imports = "silent"` plus per-module
  `ignore_missing_imports`/`follow_imports = "skip"` overrides for
  `sentence_transformers`/`torch`/`transformers`/`numpy` were added to
  `pyproject.toml` — without them, mypy attempted to type-check torch's
  own multi-hundred-file internals on every run (minutes, not seconds).

## Risks

- `paraphrase-multilingual-MiniLM-L12-v2` is downloaded to the local
  sentence-transformers cache on first real use; this repository has no
  synthetic/mocked model artifact committed (consistent with "no secrets/
  binaries committed" policy) — first real use in a fresh environment
  will re-download.
- Hybrid weight defaults (`0.6/0.25/0.15`) are placeholders, not tuned;
  CLAUDE.md §22 requires tuning only against dev/validation data, which
  needs the populated skill catalog (not yet built).

## Test strategy

`tests/test_embeddings.py`: closer-match-ranks-first and role-filter,
both via a deterministic bag-of-words stub embedder; a call-counting stub
confirms the injected embedder (not a real model) is what gets used.
`tests/test_retrieval.py` (extended): module-match boost overriding a
vector tie, vector-only fallback when module/operation are omitted, and
role-filter propagation through the hybrid layer.
