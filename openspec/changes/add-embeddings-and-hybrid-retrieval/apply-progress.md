# Apply progress: embeddings retriever and hybrid ranker (work unit 10, closes P5.2)

## Status

Complete; all tasks checked in `tasks.md`. 220 hand-authored added lines
(below the 400-line budget) plus a separately-flagged 814-line
machine-generated dependency-lock diff. No commit created by apply.

## Retained files

- `src/erp_agent_os/embeddings.py`
- `src/erp_agent_os/retrieval.py` (extended: `HybridRetriever`,
  `HybridWeights`, `VectorRetriever`)
- `tests/test_embeddings.py`
- `tests/test_retrieval.py` (extended: 3 hybrid tests)
- `pyproject.toml` (`sentence-transformers==5.6.1` moved to main deps;
  mypy overrides added for the ML dependency tree)
- `uv.lock` (relocked: ~70 packages including torch, transformers, numpy,
  scipy, scikit-learn)
- embeddings/hybrid-only SDD artifacts under this change

## TDD Cycle Evidence

| Area | Test file | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|
| Embeddings + hybrid | `tests/test_embeddings.py`, `tests/test_retrieval.py` | `ModuleNotFoundError: erp_agent_os.embeddings` | 11 passed | 11 passed; role-filter/injection/module-match/fallback cases | 11 passed; formatting only |

## Verification evidence

- `python -c "import sentence_transformers; print(sentence_transformers.__version__)"` → `5.6.1`.
- `python -m pytest tests/test_embeddings.py tests/test_retrieval.py` — 11 passed.
- `python -m pytest` — 67 passed (full suite through work unit 10).
- `ruff check` — all checks passed.
- `ruff format --check` — all files formatted.
- `python -m mypy src` — no issues found in 12 source files (~39s after
  performance overrides; the pre-override background run exceeded 120s).
- Hand-authored measurement: `49 + 63 + 75 + 33 = 220` additions.
- Lock diff (flagged, not counted against the 400-line budget):
  `git diff --stat -- pyproject.toml uv.lock` → 814 insertions.

## Deferred follow-on dependency

`SystemC` retriever wiring to `HybridRetriever`/`EmbeddingRetriever`;
weight tuning against dev/validation data (needs the populated skill
catalog, roadmap P3.2–P3.5); a documented real-model smoke check outside
`pytest`.

## Deferred lifecycle actions

- Parent-owned bounded reliability review of the 220-line hand-authored
  diff (lock diff hash-verified, not line-reviewed).
- Parent-owned confirmation that catalog population is the next priority
  before further retrieval tuning (per user's explicit direction this
  session).
