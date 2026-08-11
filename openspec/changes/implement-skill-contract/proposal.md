# Proposal: Implement versioned skill contract (work unit 3)

## Intent

Deliver the third required foundation step per roadmap P4.2 and CLAUDE.md
§15: a strict, versioned skill schema and its fixed lifecycle state graph.
FakeERP (work unit 2) is complete, satisfying the D-10 build order.

## Scope

- `SkillDefinition`: frozen Pydantic model matching the §15 contract
  fields (identity/version, module/operation, risk class, input schema,
  permissions, preconditions, execution metadata, postconditions, approval
  trigger expressions).
- `SkillState` enum and `ALLOWED_TRANSITIONS` graph:
  `DRAFT → VALIDATED → TESTED → APPROVED → ACTIVE → DEPRECATED`, any state
  `→ QUARANTINED`, no direct `DRAFT → ACTIVE`.
- Pure `transition(current, target)` validator.
- Focused tests: valid skill defaults to `DRAFT`; direct `DRAFT → ACTIVE`
  rejected; every state can quarantine; full lifecycle path accepted; R4
  risk, empty postconditions, and malformed version all rejected.

## Non-goals

Skill registry/persistence, runtime execution, policy engine, retrieval,
LLM/parser, audit, API, and the 12-skill catalog population remain excluded
(CLAUDE.md §11, project-context.md).

## Follow-on dependency

Runtime + policy engine (roadmap P4.3–P4.4) is the next SDD change; it
consumes `SkillDefinition.execution`/`permissions`/`risk_class` and the
`FakeERPAdapter` allowlist together, but is not implemented here.

## Success criteria

`SkillDefinition` rejects R4 risk, empty postconditions, and non-semver
versions; `transition` rejects any move outside the fixed graph, including
`DRAFT → ACTIVE`, and accepts the full documented path plus quarantine from
every state; `python -m pytest tests/test_skills.py` and the full suite pass.

## Forecast

One new source file (`src/erp_agent_os/skills.py`, 137 lines) and one new
test file (`tests/test_skills.py`, 77 lines): **214 added lines**, below the
400-line budget. No split needed.
