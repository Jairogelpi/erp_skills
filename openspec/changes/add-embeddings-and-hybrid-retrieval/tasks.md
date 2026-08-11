# Tasks: Add embeddings retriever and hybrid ranker (work unit 10, closes P5.2)

## Review Workload Forecast

| Field | Value |
|---|---|
| Hand-authored diff | 220 lines (2 source + 2 test files, net) |
| Dependency-lock diff | 814 lines (`pyproject.toml`/`uv.lock`, machine-generated) |
| 400-line budget risk | Low for hand-authored diff; lock diff flagged separately, not counted against it |
| Delivery strategy | single-pr |

## Implementation

- [x] User authorization obtained (`AskUserQuestion`) before downloading a
  model: "Descargar modelo ahora" selected over skipping embeddings.
  <!-- sdd-owner: implementation -->
- [x] Add `sentence-transformers==5.6.1` to `[project.dependencies]`
  (main, not dev — production retrieval code depends on it); `uv lock` +
  `uv sync --frozen --group dev`. Evidence: `python -c "import
  sentence_transformers; print(sentence_transformers.__version__)"` →
  `5.6.1`. <!-- sdd-owner: implementation -->
- [x] **RED:** `tests/test_embeddings.py` written against nonexistent
  `erp_agent_os.embeddings`. Evidence: `python -m pytest
  tests/test_embeddings.py` → `ModuleNotFoundError: No module named
  'erp_agent_os.embeddings'` (collection error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/embeddings.py`
  (`EmbeddingRetriever`) and extend `src/erp_agent_os/retrieval.py` with
  `HybridRetriever`/`HybridWeights`/`VectorRetriever`. Evidence: `python -m
  pytest tests/test_embeddings.py tests/test_retrieval.py` → 11 passed.
  <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases — role filter on embeddings,
  injected-embedder-is-used (call-counting stub), module-match overriding
  a vector tie, vector-only fallback, hybrid role-filter propagation.
  Evidence: same 11-test run, all pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Formatting/line-length fixes across the four files;
  no semantic change. Evidence: `python -m pytest` → 67 passed (full
  suite). <!-- sdd-owner: implementation -->
- [x] mypy performance: added `follow_imports`/`ignore_missing_imports`
  overrides for the ML dependency tree. Evidence: `python -m mypy src` —
  first run (before overrides) exceeded 120s in the background; after the
  overrides, `time python -m mypy src` → `Success: no issues found in 12
  source files` in ~39s. <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found in 12 source files.
  <!-- sdd-owner: implementation -->
- [x] Measure retained diff: hand-authored 220 lines (below 400); lock
  diff 814 lines flagged separately as machine-generated, hash-pinned.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Wiring `HybridRetriever`/`EmbeddingRetriever` into `SystemC` (currently
  uses `TfidfRetriever`) — needs `SystemC` to derive a module/operation
  guess from `IntentProposal`, which it doesn't yet.
- Weight tuning against dev/validation data — needs the populated skill
  catalog (roadmap P3.2–P3.5, not yet built).
- A real-model smoke check (documented, not part of `pytest`).

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 220-line hand-authored diff;
  treat the 814-line lock diff as hash-verified, not line-reviewed.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns catalog-driven weight tuning and
  `SystemC` retriever wiring before any scope expansion.
  <!-- sdd-owner: parent -->
