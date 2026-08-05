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

## Progress

Work units 1–10 are implemented and tested: dataset schema/scaffold,
`FakeERPAdapter`, versioned skill contract, deterministic runtime + policy
engine, append-only audit store, core safety property tests, an intent
parser + TF-IDF/embeddings/hybrid retrieval with abstention
(`src/erp_agent_os/{parser,retrieval,embeddings}.py`), an approval service
(`src/erp_agent_os/approval.py`), and end-to-end System C integration
(`src/erp_agent_os/system_c.py`). Phase 4 is closed; phase 5 (P5.1–P5.4)
is closed; P6.3 is done. `sentence-transformers` was added as a main
dependency with explicit user authorization to download
`paraphrase-multilingual-MiniLM-L12-v2`.

**Catalog populated (user-directed priority, delivered this session):**
`src/erp_agent_os/catalog.py` (12 skills, 8 families),
`src/erp_agent_os/bench_intents.py` (24 canonical intents),
`src/erp_agent_os/bench_generator.py` + `data/bench_v1.jsonl` (480 cases,
240/120/120 split, 144 noise/96 adversarial, zero paraphrase-group
leakage by construction). See `docs/dataset-card.md` for composition and
explicit known limitations. **Execution wiring done (user-directed priority, this session):**
`src/erp_agent_os/handlers.py` (12 handlers) +
`src/erp_agent_os/bench_runner.py` run all 480 cases through real
`SystemC` execution; `data/bench_v1_wiring_report.json` reports match
rates (NORMAL 87.5%, NOISE 72.2%, ADVERSARIAL 17.7%) — the ADVERSARIAL
gap is a disclosed finding (no prompt-injection/range/bulk-scope
detection yet), not a bug, directly relevant to H4. `FakeERPAdapter` and
`Runtime` were hardened (explicit `record_id`, `list()`, caught handler
exceptions) as a discovered prerequisite. **API layer done (this session):** `src/erp_agent_os/api.py`
(FastAPI) exposes `POST /requests` (server-generated correlation id),
`GET /skills`, `GET /audit/{id}`, `POST /approvals`, all behind a demo
API key and an in-memory rate limiter. **Not yet done:** persistence
(PostgreSQL/pgvector, roadmap P6.2 — state is process-local),
second-annotator review/kappa (pending human step), a real LLM parser
(uses `expected_arguments` as ground truth), input-schema/range
validation, and a distinct `CLARIFY` decision path. Next: persistence,
then A/B systems (roadmap P8.1 remainder). Odoo 19 adapter, dashboard,
and experiment runner remain out of scope until then.

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
