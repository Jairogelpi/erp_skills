# Proposal: Add core safety property tests (work unit 6, closes P4.6)

## Intent

Close CLAUDE.md §29's required property-based tests and roadmap P4.6, the
last item in phase 4 (núcleo determinista): R4 never registrable, an
idempotency key never produces two mutations, a disallowed model never
reaches the adapter store, every terminal execution has an audit event, and
a more restrictive policy input (denied role, inactive skill) never yields
a more permissive decision than a less restrictive one.

## Scope

- Add `hypothesis` as a locked dev dependency (`pyproject.toml`/`uv.lock`);
  it was already a planned quality tool per `openspec/config.yaml`.
- `tests/test_properties.py`: five `@given`-driven properties exercising
  `SkillDefinition`, `FakeERPAdapter`, `Runtime`, `AuditStore`, and
  `policy.decide` together, using a permissiveness ranking
  (`DENY < REQUIRE_APPROVAL < SIMULATE < ALLOW`) for the monotonicity
  checks.

## Non-goals

No new production module. No change to `adapters.py`, `skills.py`,
`policy.py`, `runtime.py`, or `audit.py` behavior — these tests verify
invariants already established by work units 2–5's own TDD cycles.

## Follow-on dependency

Phase 4 is now closed. The next required step is the recuperación/parser
work (phase 5, P5.1–P5.4) or the approval service (phase 6, P6.3) — both
build on the now-complete deterministic core.

## Success criteria

All five properties pass under Hypothesis's default example budget;
`python -m pytest` passes in full; `ruff check`, `ruff format --check`, and
`mypy src` remain clean.

## Forecast

`pyproject.toml`/`uv.lock` (34 lines, dependency lock only) + one new test
file (`test_properties.py`, 150 lines): **184 added lines**, below the
400-line budget. No split needed.
