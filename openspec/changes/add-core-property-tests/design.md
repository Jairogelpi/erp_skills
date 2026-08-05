# Design: core safety properties

## Approach

Five `hypothesis.given`-decorated tests in one file, each targeting a
single §29-listed property against the already-implemented modules
(work units 2–5). A local `_PERMISSIVENESS` rank dict encodes the ordering
`DENY < REQUIRE_APPROVAL < SIMULATE < ALLOW` for the two monotonicity
properties; it lives in the test file, not in `policy.py`, since it is a
test-only comparison helper, not a runtime concern.

## Alternatives considered

- **Add `permissiveness_rank` to `policy.py` as a public helper**: rejected.
  Nothing in the production code needs to compare decisions by
  permissiveness; adding it there would be speculative API surface for a
  test-only need (ponytail: no unrequested abstraction).
- **RED-first for these tests**: not applicable in the usual sense — these
  are property tests over invariants work units 2–5 already built and
  TDD'd individually (e.g., R4 rejection was RED/GREEN'd in work unit 3).
  Writing them here is regression/characterization coverage closing §29's
  explicit requirement, not first-implementation TDD. This is stated
  honestly in `tasks.md` rather than fabricating a RED step.
- **Property-test `AuditStore` and `Runtime` in isolation vs. together**:
  chose together for the "every terminal execution has an audit event"
  property, since that is precisely the seam between the two modules that
  §29 cares about (nothing silently drops an event).
- **Add `hypothesis` unpinned**: rejected. The repo's non-negotiable is a
  reproducible locked toolchain (`uv lock --check` / `uv sync --frozen`);
  hypothesis is pinned to `6.123.7` and resolved into `uv.lock` like every
  other dev dependency.

## Risks

- Hypothesis's default example budget (100 per property) is randomized
  per run; a property that is only violated by a narrow input range could
  intermittently pass. All five properties here are total (hold for every
  input in their domain), so this is a low risk, but it is a real property
  of Hypothesis worth naming.
- `test_idempotency_key_never_produces_two_mutations` reaches into
  `FakeERPAdapter`'s private `_records` dict rather than adding a public
  `count()` method — matches the existing test style in
  `tests/test_runtime.py`; no new public surface added for a test-only
  need.

## Test strategy

This unit *is* the test strategy: `tests/test_properties.py`, five
properties, `python -m pytest` and `python -m pytest tests/test_properties.py`
both green.
