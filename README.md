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
| Inter-annotator agreement instrument (Cohen's kappa) | `agreement.py` | ⚠️ human annotation pending |
| Real LLM client for A/B/C | — | ⏳ needs provider credentials |
| Piloto, congelación, experimento confirmatorio (1.080 ejecuciones) | — | ⏳ not started |

156 tests, 97% coverage (`policy.py` 100%), `ruff`/`mypy` clean, CI green.

### Measured result, reported as-is

Running all 480 benchmark cases through System C's **real** execution, before and
after adding `validation.py`:

| Label | Before | After |
|---|---|---|
| NORMAL | 87.5% | 87.5% |
| NOISE | 72.2% | **88.9%** |
| ADVERSARIAL | 17.7% | **57.3%** |

**The ceiling is stated, not buried:** those detectors are *lexical* and tuned to
this benchmark's template-generated adversarial text. They measure detection of
known patterns, not robustness against an adaptive adversary. 41 adversarial cases
still mismatch; every remaining category is enumerated in
[`docs/dataset-card.md`](docs/dataset-card.md). See
[`docs/threat-model.md`](docs/threat-model.md) for which controls are implemented,
partial, or absent, and [`CLAUDE.md`](CLAUDE.md#bitácora-operativa) for the
append-only build log.

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
