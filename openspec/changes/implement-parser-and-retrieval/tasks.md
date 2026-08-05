# Tasks: Implement intent parser and TF-IDF retrieval (work unit 7)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 272 (2 source + 2 focused test files) |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `tests/test_parser.py` and `tests/test_retrieval.py` written
  against nonexistent `erp_agent_os.parser`/`erp_agent_os.retrieval`.
  Evidence: `python -m pytest tests/test_parser.py tests/test_retrieval.py`
  → `ModuleNotFoundError: No module named 'erp_agent_os.parser'`
  (collection error on both). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `src/erp_agent_os/parser.py`
  (`IntentProposal`, `structure_proposal`) and
  `src/erp_agent_os/retrieval.py` (`TfidfRetriever`, `should_abstain`).
  Evidence: same command → 10 passed. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** Independent cases — all-present-yields-no-missing,
  out-of-range confidence, extra-field rejection, role-filter exclusion,
  and all four `should_abstain` branches. Evidence: same 10-test run, all
  pass. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Line-length fixes in `retrieval.py` (`_vector`) and
  `test_retrieval.py`; no semantic change. Evidence: `python -m pytest` →
  50 passed (full suite). <!-- sdd-owner: implementation -->
- [x] Measure retained files: `parser.py` (60) + `retrieval.py` (96) +
  `test_parser.py` (48) + `test_retrieval.py` (68) = 272 additions, below
  400. <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed; `ruff format --check`
  → all formatted; `mypy src` → no issues found in 9 source files.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Embeddings retriever and hybrid ranking (§22 points 2–3): needs a model
  choice and, likely, a network-fetched model — deferred, not silently
  dropped.
- LLM-backed proposal generation, module/operation-match retrieval boosts,
  and full system-C wiring (P5.4) are the next SDD change(s).

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the parser/retrieval diff,
  reliability as dominant lens, 272-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns embeddings/hybrid-ranking and P5.4
  wiring before any scope expansion. <!-- sdd-owner: parent -->
