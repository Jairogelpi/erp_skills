# Tasks: Implement FastAPI layer over System C (work unit 16, P6.1)

## Review Workload Forecast

| Field | Value |
|---|---|
| Hand-authored diff | 266 lines |
| Dependency-lock diff | 867 lines (flagged separately, machine-generated) |
| 400-line budget risk | Low (hand-authored) |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] Add `fastapi==0.121.2`, `uvicorn==0.38.0` (main deps) and
  `httpx==0.28.1` (dev, `TestClient`). `uv lock` + `uv sync --frozen
  --group dev`. <!-- sdd-owner: implementation -->
- [x] **RED:** `tests/test_api.py` written against nonexistent
  `erp_agent_os.api`. Evidence: `python -m pytest tests/test_api.py` →
  `ModuleNotFoundError: No module named 'erp_agent_os.api'` (collection
  error). <!-- sdd-owner: implementation -->
- [x] **GREEN → discovered bug → fix:** first implementation forgot to
  attach `enforce_rate_limit` to `/skills` (only `/requests` had it); the
  rate-limit test caught it (`200` instead of expected `429`). Fixed by
  adding the missing dependency, not by weakening the test. Evidence:
  `python -m pytest tests/test_api.py` → 7 passed after the fix.
  <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 109 passed.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed (after manual
  line-length fixes); `ruff format --check` → all formatted; `mypy src` →
  no issues found in 18 source files. <!-- sdd-owner: implementation -->
- [x] Measure retained diff: `api.py` (162) + `test_api.py` (104) = 266,
  below 400. Lock diff 867 lines, flagged separately.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- PostgreSQL/pgvector persistence (roadmap P6.2) — audit/approval state
  is process-local in-memory only.
- Broader integration/contract test coverage (roadmap P6.4).
- Real deployment auth model (the demo API key is explicitly not one).

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 266-line hand-authored diff.
  <!-- sdd-owner: parent -->
- [ ] Confirm the follow-on change owns persistence before any scope
  expansion. <!-- sdd-owner: parent -->
