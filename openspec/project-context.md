# ERP Agent OS — SDD project context

## Authority and scope

`../CLAUDE.md` is the normative product and experimental specification. This
context does not replace or reinterpret it. The first implementation slice is
limited to:

1. freezing the ERP-Skills-Bench dataset schema;
2. implementing a resettable, deterministic `FakeERPAdapter`; and
3. implementing the versioned skill contract.

Do not implement the runtime, policy engine, retrieval, LLM/parser, audit,
API, Odoo 19 adapter, dashboard, or experiment runner in this slice.

## Non-negotiable constraints inherited from CLAUDE.md

- Use synthetic data only.
- `FakeERPAdapter` is mandatory for the confirmatory core; Odoo 19 is
  post-core.
- The benchmark has 24 canonical intents, 480 requests, 8 ERP families, and
  fixed development/validation/test splits of 240/120/120.
- Test cases must retain request identity, expected intent or abstention,
  expected arguments and decision, initial and expected final state,
  clarification/approval expectations, and adversarial/error labels.
- A confirmatory run restores the same FakeERP initial state for each paired
  `request_id`–state–repetition observation.
- Skills are versioned and stateful. Execution is restricted to registered
  handlers; no arbitrary generated code is executable.
- R4 operations are unconditionally denied. No physical deletion, payments,
  production access, or bulk automatic changes are in scope.

## First-slice planning outcomes

The proposal/spec/design/tasks for the slice must make the dataset schema
explicit and machine-validatable before code depends on it. FakeERP must have
an explicit adapter contract, deterministic seed/snapshot/restore semantics,
and observable state needed to evaluate strict task success. The skill
contract must express identity/version, module and operation, risk, input
schema, permissions, preconditions, registered handler metadata,
idempotency/retry settings, postconditions, approval conditions, and lifecycle
state. Tests should be written first with `pytest`, including contract tests
for the dataset, adapter, and skill schema.

## Current repository and tooling baseline

The repository currently contains the normative specification (`CLAUDE.md`),
an aligned evaluation note (`evaluacion_tfm.md`), and runtime metadata only.
It has no application source tree, dependency manifest, test suite, test
configuration, or Git repository metadata. `pytest` is the intended runner
from the normative stack, but project-local runner availability is not yet
established.
