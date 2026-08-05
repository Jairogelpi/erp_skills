# Proposal: Implement FakeERPAdapter (work unit 2)

## Intent

Deliver the second required foundation step per `openspec/project-context.md`
and roadmap P4.1: a deterministic, restorable synthetic ERP adapter. This
unblocks the skill contract, which depends on FakeERP existing first
(CLAUDE.md §42, D-10).

## Scope

- `FakeERPAdapter`: in-memory record store restricted to an explicit model
  allowlist passed at construction.
- Operations: `create`, `get`, `update` (no delete — out of scope per
  CLAUDE.md §11 exclusions).
- Exact `snapshot()`/`restore()` semantics so a confirmatory observation can
  reset state between paired repetitions (CLAUDE.md §19).
- Focused unit tests: roundtrip, disallowed-model rejection, unknown-record
  rejection, and restore reverting/decoupled-from-live mutation.

## Non-goals

Skill contract, runtime, policy engine, retrieval, LLM/parser, audit,
API, persistence, Odoo 19, experiment runner, and any populated benchmark
data remain excluded, per `openspec/project-context.md` and CLAUDE.md §11.

## Follow-on dependency

The skill contract (versioned schema, lifecycle transitions) is the next
SDD change and may reference this adapter's allowlist/operation shape as its
execution-target contract; it is not implemented here.

## Success criteria

`FakeERPAdapter` rejects any model outside its allowlist and any unknown
record id; `snapshot()`/`restore()` reverts a mutation exactly, with restored
state independent of the live store (no aliasing); focused tests pass with
`python -m pytest tests/test_fake_erp.py`; full suite passes with
`python -m pytest`.

## Forecast

One new source file (`src/erp_agent_os/adapters.py`, 63 lines) and one new
test file (`tests/test_fake_erp.py`, 41 lines): **104 added lines**, well
below the 400-line budget. No split needed.
