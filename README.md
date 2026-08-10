# ERP Agent OS

**Diseño y evaluación experimental de un sistema para recuperar, verificar y ejecutar skills reutilizables en procesos ERP mediante agentes de inteligencia artificial.**

Trabajo Fin de Máster — Jairo Gelpi Moreno · Máster en Data Science, IA y Big Data · Curso 2025–2026.

The public repository identity is **`erp_skills`**; the Python distribution name is
**`erp-agent-os`**. Committed material is synthetic-only: no private data, real ERP
credentials, tokens, secrets, or local environment files are ever tracked.

---

## What this is

ERP Agent OS separates the *probabilistic* interpretation of a natural-language ERP
request (intent, entities, arguments) from the *deterministic* authorization and
execution of that request (schema/risk validation, policy decision, idempotent
execution, postcondition verification, append-only audit). The full normative
specification — research question, hypotheses H1–H8, architecture, risk taxonomy,
benchmark protocol, and statistical plan — lives in [`CLAUDE.md`](CLAUDE.md); this
README covers how to run and verify what is built.

```text
request → Intent Parser → Skill Retriever → Policy Engine → Runtime → FakeERP
                              │                                  │
                        Confidence Gate                  Postcondition Verifier
                              │                                  │
                         abstain/clarify                   Audit Store
```

## What's implemented

| Component | Module | Status |
|---|---|---|
| Deterministic ERP adapter (snapshot/restore, allowlisted) | `adapters.py` | ✅ |
| Versioned skill contract + lifecycle | `skills.py` | ✅ |
| Deny-by-default policy engine (R0–R4) | `policy.py` | ✅ |
| Runtime (registered handlers, idempotency, caught handler errors) | `runtime.py` | ✅ |
| Append-only audit store (redaction, abstention events) | `audit.py` | ✅ |
| Structured intent proposal | `parser.py` | ✅ |
| TF-IDF + embeddings + hybrid retrieval, abstention | `retrieval.py`, `embeddings.py` | ✅ |
| Approval service (actor/scope/expiry) | `approval.py` | ✅ |
| **System C** — governed pipeline, end to end | `system_c.py` | ✅ |
| **System B** — typed tools, no retrieval/risk/approval | `system_b.py` | ✅ |
| **System A** — direct agent, ungoverned | `system_a.py` | ✅ |
| Pre-execution validation + adversarial detection | `validation.py` | ⚠️ lexical only |
| 12-skill catalog (8 families) | `catalog.py` | ✅ |
| 24 canonical intents | `bench_intents.py` | ✅ |
| ERP-Skills-Bench v1 — 480 generated, executed cases | `bench_generator.py`, `bench_runner.py` | ✅ |
| FastAPI layer (demo auth, correlation id, rate limit) | `api.py` | ✅ |
| Durable audit/approval storage (SQLAlchemy, Postgres in compose) | `persistence.py` | ⚠️ not wired into the API yet |
| Executable statistical plan (McNemar, Cochran Q, bootstrap, Holm) | `statistics.py` | ✅ |
| Metrics: STSR, false allow, Top-1/Top-3/MRR, stability | `metrics.py` | ✅ |
| Executable postconditions (verification engine) | `postconditions.py` | ✅ |
| Paired A/B/C experiment runner (1.080 observations) | `experiment.py` | ✅ |
| Freeze manifest + drift detection (CI-enforced) | `freeze.py` | ✅ |
| Inter-annotator agreement instrument (Cohen's kappa) | `agreement.py` | ⚠️ human annotation pending |
| Real LLM clients for A/B/C (Groq, Gemini, OpenRouter — all free tier) | `groq_client.py`, `gemini_client.py`, `openrouter_client.py` | ✅ |
| Checkpoint/resume + call caching for real-LLM runs | `experiment.py`, `llm_client.CachingLLMClient` | ✅ |
| Token instrumentation (H2) and traceability rubric (H7) | `metrics.py`, `traceability.py` | ✅ |
| Confirmatory run with a real LLM (CLAUDE.md §19) | `scripts/run_experiment.py --real-llm --provider {groq,gemini,openrouter}` | ✅ executed, 1.080 observations |
| External adversarial stress test (InjecAgent, out-of-distribution) | `scripts/injecagent_stress_test.py` | ✅ measured, 0%→3.3% (see below) |
| **Odoo 19 adapter** (post-core, JSON-2 API, allowlisted, no delete) | `odoo_client.py` | ✅ live-verified |
| Odoo 19 demo through the **full governed pipeline** (System C, real approval gate) | `odoo_handlers.py`, `scripts/odoo_governed_demo.py` | ✅ live-verified |

305 tests, `ruff`/`mypy` clean, CI green.

### Real LLM clients

Three interchangeable `LLMClient` implementations exist —
`groq_client.py`, `gemini_client.py`, `openrouter_client.py` — because
free-tier quotas turned out to be the practical bottleneck, not the
architecture: Groq's daily token quota got exhausted by earlier
interrupted runs, and every Gemini model tested on this project's key
carried a 20-requests-per-day cap. CLAUDE.md D-03 requires A, B, and C to
share the same model/provider/config *within one run* — it does not
mandate a specific provider. The confirmatory run reported below used
OpenRouter (`openai/gpt-oss-20b:free`).

```sh
cp .env.example .env   # fill in GROQ_API_KEY / GEMINI_API_KEY / OPENROUTER_API_KEY
uv run python scripts/run_experiment.py --real-llm --provider openrouter
```

Without `--real-llm` the experiment uses `DeterministicStubClient`
(architecture-isolation baseline, `is_confirmatory_run: false`); both
manifests state the flag explicitly so results can never be silently
misread as the other kind. Each `--real-llm` run checkpoints progress
per-provider (`data/checkpoint_real_llm_<provider>.jsonl`, gitignored)
and reuses one real call across a case's 3 repetitions
(`CachingLLMClient`) instead of calling the LLM 3×, since
`temperature=0.0` was empirically confirmed reproducible across three
independent real runs (H3 = 1.0 every time).

### Measured result: the confirmatory A/B/C experiment (real LLM)

**1.080 executions** (120 frozen-test cases × 3 systems × 3 repetitions),
randomized order, `FakeERPAdapter` rebuilt per observation, A/B/C sharing
one real OpenRouter selector (`openai/gpt-oss-20b:free`, temperature 0).
Full analysis — including the stub-selector baseline kept for comparison
— in [`docs/results.md`](docs/results.md); raw output in
`data/experiment_results.json` (`is_confirmatory_run: true`).

| Metric | A (ungoverned) | B (typed only) | **C (ERP Agent OS)** |
|---|---|---|---|
| **STSR** (primary endpoint) | 0.000 | 0.517 | **0.700** |
| **False allow rate** (critical) | 0.333 | 0.889 | **0.111** |
| Mean tokens/execution (H2) | 198.2 | 230.3 | **0.0** |
| Traceability score, 0–1 (H7) | 0.19 | 0.36 | **0.80** |
| Retrieval Top-1 | 0.000 | 0.890 | **0.780** |
| Retrieval Top-3 / MRR | — | 0.890 | **0.941 / 0.855** |

- **C − A** = +0.700, 95% CI [+0.617, +0.783], Holm *p* = 2.71×10⁻¹⁹, OR 169
- **C − B** = +0.183, 95% CI [+0.058, +0.308], Holm *p* = 7.65×10⁻³, OR 2.07
- Cochran's Q = 109.46 (df 2). **H1 (non-inferiority, −5 pp margin): accepted.**
- **Inference unit is the case (n = 120), not the execution.** Repetitions of a case are not independent; using all 360 per system would be pseudo-replication, narrowing every CI by ≈√3.

> **⚠️ This run handed every system a perfect, unpaid argument parse.**
> Removing that bias changes the headline result — see the next section.
> These numbers remain valid for what they measure (tool selection with
> arguments given), but the C − B superiority they show does not survive
> honest parsing.

### The result that changed: honest argument parsing

`--real-parser` makes all three systems extract arguments from the raw
request text with the same LLM, same prompt, same field list, instead of
being handed `case.expected_arguments` for free. Full analysis in
[`docs/results.md`](docs/results.md); raw output in
`data/experiment_results_real_parser.json`.

| Metric | A | B | **C** |
|---|---|---|---|
| STSR | 0.000 | 0.483 | **0.558** |
| Mean tokens/execution | 185.1 | 265.2 | **67.6** |
| False allow rate | 0.889 | 0.889 | **0.111** |
| Traceability (0–1) | 0.356 | 0.374 | **0.820** |

- **C − B on STSR = +0.075, 95% CI [−0.025, +0.175], Holm *p* = 0.212 — not significant.** The CI crosses zero. C fell 0.700 → 0.558 once it had to parse for real; B barely moved (0.517 → 0.483) because it already did its own tool selection. **H1 still holds as non-inferiority** (CI lower bound −0.025 is above the −5 pp margin), but not as superiority.
- **C − B on tokens = −197.6, 95% CI [−198.3, −196.9]** — C is **3.9× cheaper**. All three pay the same extraction; A and B *additionally* pay an LLM tool-selection call, which C replaces with TF-IDF retrieval at zero cost.
- Safety and traceability are **unchanged** across all runs: they come from the policy engine and audit store, not from argument quality.

**The defensible claim, restated honestly:**

> Governance does **not** buy more task success over a typed-tools
> baseline. It buys **8× fewer unsafe executions, 2.2× better
> traceability, and 3.9× fewer tokens — at no measurable cost in task
> success.**

That is a narrower claim than the perfect-parse runs suggested, and the
one the evidence actually supports.

> **⚠️ Scope.** Free-tier model (`openai/gpt-oss-20b:free`), not a
> frontier/production model — disclosed, not hidden. The freeze manifest
> does not yet cover provider config (model, temperature, retries), a
> disclosed trade-off. Other limits in [`docs/results.md`](docs/results.md):
> A scores 0 on STSR largely by construction (generic CRUD cannot encode
> postconditions), so **C − B is the informative contrast**; the
> adversarial detectors are lexical; H8 (cost) is a declared-rate
> sensitivity analysis, not measured spend; H3 cannot discriminate even
> with a real LLM because `temperature=0.0` makes it perfectly
> reproducible by design.

### External adversarial stress test: InjecAgent

`validation.py`'s lexical detectors are declared as "tuned to
ERP-Skills-Bench's own templated Spanish text" — this was measured, not
just asserted, against InjecAgent (Zhan et al. 2024), 510 real
out-of-distribution indirect-injection cases in English:

| Pass | Detector | Detection rate |
|---|---|---|
| 1 | Spanish-only | 0.0% |
| 2 | Spanish + English patterns added | 3.3% (17/510) |

Going bilingual multiplied detection, it did not close the gap: most
InjecAgent payloads are polite, direct requests with no attack-style
framing at all ("Please delete my clinical documents...") — invisible
to any lexical detector by construction, not a vocabulary gap. Full
result and honest interpretation in
[`docs/injecagent-stress-test.md`](docs/injecagent-stress-test.md).

```sh
uv run python scripts/injecagent_stress_test.py
```

### Odoo 19 demo (post-core, real instance)

`FakeERPAdapter` remains mandatory for the confirmatory experiment
(CLAUDE.md §26/D-07); `odoo_client.py` is a post-core demonstration
that the same skill contract executes against a real ERP. Two demos,
both live-verified against a real Odoo.sh Development-branch instance
(demo data, confirmed before writing anything — see
[`docs/odoo-demo.md`](docs/odoo-demo.md) for the full safety story):

1. **Adapter only** (`scripts/odoo_demo.py`): create → verify
   postcondition → update → independent re-read, against real Odoo.
2. **Full governed pipeline** (`scripts/odoo_governed_demo.py`): the
   *same* `Runtime`/`SystemC`/`ApprovalService`/`AuditStore` classes
   the confirmatory core runs 1.080 times, pointed at `Odoo19Adapter`
   instead of `FakeERPAdapter`. An R1 skill auto-executes; an R2 skill
   is blocked with `REQUIRE_APPROVAL` and proven — via an independent
   Odoo read, not the system's own say-so — to leave Odoo untouched
   until approval is granted, then executes correctly. Full audit
   trail captured for all three steps.

```sh
cp .env.example .env   # fill in ODOO_URL / ODOO_DB / ODOO_API_KEY
uv run python scripts/odoo_governed_demo.py
```

`Odoo19Adapter` is a **statically-typed** drop-in for `FakeERPAdapter`
(`ErpAdapter` Protocol in `adapters.py`, `Runtime` generic over the
adapter type) — not just duck-type-compatible at runtime. Only 2 of 12
catalog skills are mapped to real Odoo models, declared as future work.

## Prerequisites

- CPython 3.12 (`>=3.12,<3.13`)
- [uv](https://docs.astral.sh/uv/) to install the reviewed lock and run tools
- A POSIX-compatible shell and GNU-compatible `make` for the Make targets below
  (on Windows: Git Bash, WSL, or run the underlying `uv run` commands directly)
- Docker Engine with Docker Compose v2 for the optional container workflow

## Quickstart

```sh
git clone https://github.com/Jairogelpi/erp_skills.git
cd erp_skills
uv lock --check
uv sync --frozen --group dev
make test
```

The first `uv sync` downloads `sentence-transformers`'s dependency tree (torch,
transformers, ~700MB) — needed for the embeddings retriever. This is a one-time
cost per environment.

## Reproducible local workflow

Use the committed lock; never replace it with an ad-hoc, unpinned install:

```sh
uv lock --check
uv sync --frozen --group dev
```

`uv sync --frozen --group dev` fails if the lock and metadata disagree rather than
silently resolving a different dependency set. To update a dependency intentionally:
change its pinned declaration in `pyproject.toml`, regenerate `uv.lock` with `uv
lock`, review the resolved versions/hashes, then rerun every check below. No normal
path uses `latest`.

## Quality commands

```sh
make format           # Ruff applies formatting
make format-check      # Ruff verifies formatting
make lint               # Ruff lints
make typecheck           # mypy performs static type checking only
make test                 # pytest runs the full suite
make coverage             # pytest reports package coverage
make validate-dataset     # runs the catalog/intents/generator test suites
make benchmark-smoke      # regenerates data/bench_v1.jsonl + the wiring report
make verify-freeze        # fails if the frozen test split or catalog drifted
make experiment           # runs the 1.080-execution paired A/B/C experiment
make build                # builds sdist + wheel
```

## Second-annotator review (pending human step)

```sh
uv run python scripts/build_annotation_sample.py   # blank review sheet, 96 cases
# a second annotator fills the `annotator2_decision` column, then:
uv run python scripts/compute_agreement.py         # Cohen's kappa
```

The sample is deterministic and stratified so adversarial/high-risk cases are
over-represented. `compute_agreement.py` **refuses to print a number** while the
second-annotator column is empty — this step is honestly pending (CLAUDE.md
§17/§21, roadmap P3.4), not silently skipped.

Ruff is the formatter and linter; mypy is static type checking only (not a
formatter). mypy is configured to skip re-checking `torch`/`transformers`/
`sentence_transformers` internals — without that override a full run took minutes
instead of seconds.

## Run the API locally

```sh
uv run uvicorn erp_agent_os.api:app --reload
```

```sh
curl -H "X-API-Key: demo-key" http://127.0.0.1:8000/skills
```

The demo API key is a placeholder constant in `api.py`, explicitly not a production
credential (CLAUDE.md §14: "autenticación para la demo"). State is in-memory only —
restarting the process clears audit history and approvals; see `docs/roadmap.md` for
the persistence gap (P6.2).

## Regenerate the benchmark

```sh
uv run python scripts/export_bench_v1.py            # data/bench_v1.jsonl (480 cases)
uv run python scripts/run_bench_wiring_report.py     # data/bench_v1_wiring_report.json
```

Both are deterministic (fixed seed) — re-running overwrites with byte-identical
content. See [`docs/dataset-card.md`](docs/dataset-card.md) for composition, split
methodology, and honest findings from wiring the dataset to real execution.

## Container workflow

```sh
make compose-config
make up
make logs
make down
```

`make up` runs `docker compose --env-file config/development.defaults up --build`.
`config/development.defaults` contains only inert defaults
(`ERP_AGENT_OS_MODE=development`, `ERP_AGENT_OS_PORT=8000`) — no secret, no
host-specific path. The container currently runs a bounded readiness message, not the
FastAPI server; wiring `uvicorn` into the container image is future work. Pinned base
image:
`python:3.12-slim@sha256:9e869b0816f5537709825b49e62dc86d1c2691eff19b05c1d4dc3a07992cc052`
(retrieved 2026-08-05) — verify with `docker buildx imagetools inspect python:3.12-slim`.

## CI/CD

[![CI](https://github.com/Jairogelpi/erp_skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Jairogelpi/erp_skills/actions/workflows/ci.yml)

The Linux/Python 3.12 workflow (`.github/workflows/ci.yml`), on every push and pull
request: installs the locked toolchain via pinned `astral-sh/setup-uv`, validates
`uv.lock` against `pyproject.toml`, then runs format-check, lint, typecheck,
coverage, **dataset validation**, **benchmark smoke** (regenerates and uploads
`data/bench_v1.jsonl` + the wiring report as build artifacts), and a package build.
Every third-party GitHub Action is pinned to an immutable commit SHA, not a mutable
tag. Pushing a `v*` tag (`.github/workflows/release.yml`) runs the same checks and,
on success, attaches the built wheel/sdist to a GitHub Release — it does not publish
to PyPI or a container registry.

## Repository layout

```text
src/erp_agent_os/     application code (adapters, skills, policy, runtime, audit,
                       parser, retrieval, systems A/B/C, catalog, benchmark
                       generator/runner, handlers, API)
tests/                 pytest suite, one file per module, 100+ tests
scripts/                export_bench_v1.py, run_bench_wiring_report.py
data/                   generated benchmark + wiring report (regenerable, not
                        hand-edited)
docs/                   dataset-card.md, roadmap.md, development-assistance.md
openspec/changes/       SDD trail: proposal/spec/design/tasks/apply-progress
                        per work unit, with TDD evidence and disclosed budget
                        exceptions where a unit exceeded the 400-line review
                        target
CLAUDE.md               the normative specification and the append-only
                        bitácora operativa (build log)
```

## Optional developer assistance

[Ponytail](.ponytail/UPSTREAM.md) is vendored with immutable provenance and a
SHA-256 manifest. Codebase Memory MCP setup and the always-index convention are
documented in [`docs/development-assistance.md`](docs/development-assistance.md).
Both are local, read-mostly assistance — not application runtime dependencies.

## Scope and non-negotiables

Full detail in [`CLAUDE.md`](CLAUDE.md#41-decisiones-no-negociables). In short:
`FakeERPAdapter` is the confirmatory core (Odoo 19 is a post-core extension);
R4-risk operations are unconditionally denied; skills are versioned with an
enforced lifecycle (no direct `DRAFT → ACTIVE`); the test split freezes before the
confirmatory experiment; synthetic data only, no secrets ever committed.
