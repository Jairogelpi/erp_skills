# Tasks: Add core safety property tests (work unit 6, closes P4.6)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 184 (dependency lock + one test file) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

## Implementation

- [x] Add `hypothesis==6.123.7` to `[dependency-groups].dev`; run `uv lock`
  (resolved `attrs`, `hypothesis`, `sortedcontainers`) and
  `uv sync --frozen --group dev`. Evidence: `python -c "import hypothesis;
  print(hypothesis.__version__)"` → `6.123.7`. <!-- sdd-owner: implementation -->
- [x] Write `tests/test_properties.py`: five `@given` properties over
  `SkillDefinition`, `FakeERPAdapter`, `Runtime`, `AuditStore`, and
  `policy.decide`. Evidence: `python -m pytest tests/test_properties.py` →
  6 passed (5 properties; the R4-rejection property yields 1 test).
  <!-- sdd-owner: implementation -->
- [x] Full-suite regression: `python -m pytest` → 40 passed.
  <!-- sdd-owner: implementation -->
- [x] Quality gates: `ruff check .` → all checks passed; `ruff format
  --check .` → all formatted; `mypy src` → no issues found in 7 source
  files. <!-- sdd-owner: implementation -->
- [x] Measure retained diff: `pyproject.toml`+`uv.lock` (34) +
  `test_properties.py` (150) = 184 additions, below 400.
  <!-- sdd-owner: implementation -->

## Honesty note on TDD cycle

These are property tests over invariants already built and individually
RED/GREEN/TRIANGULATE/REFACTOR'd in work units 2–5 (R4 rejection: unit 3;
idempotent replay: unit 4; model allowlist: unit 2; audit append: unit 5;
deny-by-default: unit 4). There is no new production behavior here, so a
literal "RED because the feature doesn't exist" step does not apply. What
was verified instead: all five properties pass against the current
implementation (`python -m pytest tests/test_properties.py` → 6 passed),
and `ruff`/`mypy` stay clean. No mutation-testing pass was run to
demonstrate a property catching an injected defect — a manual edit to
`policy.py`'s role check plus a targeted test re-run was attempted and
denied by the harness's action classifier; the edit was reverted
immediately without any test execution against the mutated file. This
follow-up is recorded honestly rather than fabricated.

## Deferred follow-on dependency

Phase 4 (núcleo determinista) is closed. The next required SDD change is
either the parser/retrieval work (phase 5, P5.1–P5.4) or the approval
service (phase 6, P6.3).

## Parent lifecycle actions

- [ ] Start or reuse bounded review of the property-test diff, reliability
  as dominant lens, 184-line measurement as scope boundary.
  <!-- sdd-owner: parent -->
- [ ] Confirm phase 4 closure and the follow-on change's scope (phase 5 vs.
  phase 6) before any further work. <!-- sdd-owner: parent -->
