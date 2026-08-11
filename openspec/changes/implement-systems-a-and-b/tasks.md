# Tasks: Implement Systems A and B baselines (work unit 17)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 293 |
| 400-line budget risk | Low |
| Delivery strategy | single-pr |

## Implementation (strict TDD)

- [x] **RED:** `test_llm_client.py`/`test_system_a.py`/`test_system_b.py`
  written against nonexistent modules. Evidence: `python -m pytest
  tests/test_llm_client.py tests/test_system_a.py tests/test_system_b.py`
  → `ModuleNotFoundError: No module named 'erp_agent_os.llm_client'`
  (collection error). <!-- sdd-owner: implementation -->
- [x] **GREEN:** Implement `llm_client.py`, `system_a.py`, `system_b.py`.
  Evidence: same command → 9 passed. <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 118 passed.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check` → all checks passed (after formatting
  fixes); `ruff format --check` → all formatted; `mypy src` → no issues
  found in 21 source files. <!-- sdd-owner: implementation -->
- [x] Measure retained files: 50+59+61+18+44+61 = 293, below 400.
  <!-- sdd-owner: implementation -->

## Deferred follow-on dependency

- Real `LLMClient` implementation requiring provider credentials.
- A/B/C comparison runner (needs the real client above).
- Frozen-manifest confirmatory protocol (roadmap P8.2–P9).

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the 293-line diff.
  <!-- sdd-owner: parent -->
