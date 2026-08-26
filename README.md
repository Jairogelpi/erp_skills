# ERP Agent OS

**Control plane for AI agents operating ERP systems.**

ERP Agent OS separates probabilistic language interpretation from deterministic enterprise authorization and execution. A language model may propose an operation; versioned contracts, policy, risk, approvals, runtime checks and postconditions decide whether that operation is allowed to reach the ERP.

> **Thesis principle:** the LLM proposes; the architecture authorizes; the runtime executes.

Trabajo Fin de Máster — Jairo Gelpi Moreno · Máster en Data Science, IA y Big Data · Curso 2025–2026.

[![CI](https://github.com/Jairogelpi/erp_skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Jairogelpi/erp_skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](pyproject.toml)

---

## Current scientific status

The current confirmatory source of truth is [`docs/results-v2.1.md`](docs/results-v2.1.md).

- Protocol: **`tfm-protocol-v2.1.2`**.
- Campaign state: **`RUN_COMPLETED / CLOSURE_VALID`**.
- Campaign size: **21,478 real observations**.
- Provider/model: OpenRouter · **`deepseek/deepseek-v4-flash`**.
- Compared systems: **A** direct agent, **B** typed tools, **C** ERP Agent OS.
- Confirmatory support: **H1a, H2, H3a, H6, H7**.
- Not supported: **H1b, H4, H5**.
- H8: modeled sensitivity analysis only; no empirical savings claim.

| Question | Current result | Interpretation |
|---|---|---|
| **Task success vs A (H1a)** | C − A = **+25.3 pp**, non-inferiority supported | C preserves task success relative to the direct-agent baseline. |
| **Task success vs B (H1b)** | C − B = **−1.5 pp**, *p*=0.286 | **No demonstrated superiority over typed tools.** |
| **Tokens (H2)** | C uses **467.98 fewer than A** and **647.80 fewer than B** | Efficiency advantage supported against both baselines. |
| **Paraphrase stability (H3a)** | **OR 9.35**, *p*=2.2×10⁻18 | C is more stable across linguistic surfaces. |
| **Active safety (H4)** | **19.0% unauthorized mutation**, target <5% | **Not supported. Governance is not perfect danger recognition.** |
| **Selective retrieval (H5)** | selective accuracy **0.589**, false reuse **0.411** | Retrieval remains a limiting subsystem. |
| **Abstention (H6)** | false reuse **−8.6 pp** | Explicit abstention improves selective behavior. |
| **Audit reconstruction (H7)** | C − A = **+42.7 pp**, *p*=2.85×10⁻112 | C produces substantially more reconstructible execution evidence. |

The most important negative result is H4. The architecture must **not** be described as generally “safe” or as a system that reliably recognizes dangerous intent. The experiment found a 19.0% unauthorized-mutation rate across 315 dangerous scenarios, almost four times the preregistered target.

That finding is deliberately kept separate from the external compromised-model stress test: across 510 InjecAgent payloads delivered through three attacker-controlled surfaces, **0/1,530 outside-contract unauthorized mutations were observed**. This is evidence about **confinement under explicit compromise**, not proof of general safety and not a replacement for H4.

---

## What the research contributes

Most agent stacks focus on helping a model choose and call a tool. ERP Agent OS studies a different boundary: **who has authority to mutate enterprise state after the model has proposed an action?**

```text
Natural-language request
        │
        ▼
Probabilistic interpretation
(intent / entities / arguments)
        │
        ▼
Skill retrieval ──► abstain / clarify
        │
        ▼
Versioned skill contract
        │
        ▼
Schema + preconditions + role + risk
        │
        ▼
Policy decision
ALLOW / DENY / REQUIRE_APPROVAL / SIMULATE
        │
        ▼
Deterministic runtime
        │
        ▼
ERP mutation
        │
        ▼
Independent postcondition verification
        │
        ▼
Append-only audit evidence
```

A **skill** is not merely a prompt or a Python function. It is a versioned operational contract containing identity, intent, argument schema, permissions, risk, handler binding, idempotency, approval rules and postconditions.

A missing capability can be proposed and tested, but the model cannot self-authorize it:

```text
need → proposal → validation → sandbox tests → risk review
     → human approval → version → ACTIVE
```

---

## A / B / C comparison

| Capability | A — Direct agent | B — Typed tools | C — ERP Agent OS |
|---|---:|---:|---:|
| Natural-language interpretation | ✓ | ✓ | ✓ |
| Executable ERP operation | ✓ | ✓ | ✓ |
| Typed arguments | limited | ✓ | ✓ |
| Versioned skill contract | — | — | ✓ |
| Explicit risk class | — | — | ✓ |
| Deterministic policy decision | — | — | ✓ |
| Human approval gate | — | — | ✓ |
| Abstention / clarification gate | — | — | ✓ |
| Postcondition verification | — | — | ✓ |
| Append-only governance evidence | — | — | ✓ |

The dashes are intentional. The repository does **not** infer governance fields that A or B do not produce. Likewise, it does not manufacture an overall “A=42 / C=91” score: every quantitative comparison maps to a declared experimental endpoint.

---

## Comparative product demo

The repository contains a presentation-oriented web demo that runs the same request through A, B and C, shows the resulting ERP state, and places the frozen confirmatory evidence beside the live behavior.

```sh
make demo-preflight
make demo-product
```

The demo is deliberately constrained by four invariants:

1. **No synthetic overall score.** Capability rows map to H1–H7; heterogeneous endpoints are never collapsed into an invented number.
2. **Missing capability remains missing.** If A/B do not produce policy, approval, skill version or postcondition evidence, the UI renders `—`.
3. **The comparative API is FakeERP-only.** It rejects an `odoo` backend. Real ERP writes remain on the single guarded Odoo demonstration path instead of creating a second write surface for presentation convenience.
4. **Non-mutation requires a positive control.** The preflight first proves that an unapproved R2 operation is retained, then approves and re-executes the same operation to prove that the environment can really write. “Nothing changed” is not accepted as evidence if the system could not have written in the first place.

Full design: [`docs/product-demo.md`](docs/product-demo.md).

---

## Odoo 19 feasibility demo

The confirmatory benchmark uses the controlled ERP adapter to preserve identical initial state and reproducibility. Odoo is a **separate post-core feasibility demonstration**, not a second confirmatory backend.

The guarded route is:

```sh
cp .env.example .env
# set ODOO_URL / ODOO_DB / ODOO_API_KEY for a Development instance only
uv run python scripts/odoo_governed_demo.py
```

The demo is restricted to an **Odoo 19 Development branch with demo data**. The guard rejects production, staging and an unspecified destination before writing.

The governed scenario demonstrates:

```text
R1 request
→ ALLOW
→ write
→ independent reread
→ postcondition verified

R2 request without approval
→ REQUIRE_APPROVAL
→ independent reread
→ ERP unchanged

approval granted
→ same R2 request
→ ALLOW
→ write
→ independent reread
→ change verified
```

Only **2 of the 12 catalog skills** are mapped to real Odoo models. That is explicitly a feasibility boundary, not hidden product completeness.

See [`docs/odoo-demo.md`](docs/odoo-demo.md).

---

## Reproducibility

### Requirements

- CPython `>=3.12,<3.13`
- [`uv`](https://docs.astral.sh/uv/)
- Git
- POSIX-compatible shell / GNU-compatible `make` for Make targets
- Docker + Compose only for the optional container workflow

### Install and verify

```sh
git clone https://github.com/Jairogelpi/erp_skills.git
cd erp_skills
uv lock --check
uv sync --frozen --group dev
make format-check
make lint
make typecheck
make test
make verify-tfm-closure
```

The v2.1 closure verifier checks the frozen campaign artifacts and final report rather than silently re-running or replacing them.

### Useful targets

```sh
make test                 # full pytest suite
make coverage             # coverage report
make validate-dataset     # catalog / intents / generator checks
make verify-freeze        # legacy freeze verification
make verify-tfm-closure   # current v2.1.2 closure verification
make demo-preflight       # product-demo evidence + positive control
make demo-product         # comparative demo API + UI
make demo                 # deterministic core demo
make compare-retrievers   # retrieval experiments
make figures              # reproducible figures
make build                # sdist + wheel
```

The project uses pinned/reviewed dependencies through `uv.lock`, Ruff for format/lint, mypy for static checking, pytest/Hypothesis for tests, and CI on Python 3.12.

---

## Research evidence and provenance

The project intentionally distinguishes evidence classes instead of flattening them into one claim:

- **Confirmatory:** v2.1.2 campaign and its preregistered endpoints.
- **Exploratory / historical:** v1 pilot, parser corrections, router studies and post-hoc analyses.
- **External stress:** InjecAgent injection/confinement evaluation.
- **Feasibility:** real Odoo 19 Development demo.
- **Product exploration:** skill-enrichment and real-request retrieval studies.
- **Scenario-only:** H8 cost sensitivity.

The full audit trail records defects found during development and analysis rather than deleting superseded results. See [`docs/audit.md`](docs/audit.md), [`docs/tfm-current-status.md`](docs/tfm-current-status.md) and [`docs/tfm-submission-readiness.md`](docs/tfm-submission-readiness.md).

### Historical evidence

The repository preserves the v1 pilot and other superseded artifacts for provenance. They are useful for understanding how the instrument changed, but **they are not the current confirmatory result**. Current claims must come from [`docs/results-v2.1.md`](docs/results-v2.1.md).

The following legacy marker is retained because the original machine-checkable claim contract requires its exact presence in reporting documents:

> `EVIDENCE-STATUS: no-valid-confirmatory-conclusion`

That marker describes the old registry contract, **not** the current scientific status shown at the top of this README. It is preserved to avoid rewriting provenance-sensitive historical checks. See `src/erp_agent_os/claims.py` and the current-status document for the distinction.

---

## Data, privacy and security scope

Committed project material is synthetic or public research material. The repository must not contain real ERP credentials, API tokens, customer data or local environment secrets.

- ERP-Skills-Bench is synthetic.
- Odoo demonstrations use Development/demo data only.
- External benchmark provenance and license conditions are documented with the corresponding study artifacts.
- `.env` and credential material are excluded from version control.

For the research threat model and limitations, see [`docs/threat-model.md`](docs/threat-model.md).

For vulnerability reporting and the difference between research findings and product-security claims, see [`SECURITY.md`](SECURITY.md).

---

## Repository map

```text
src/erp_agent_os/   architecture and runtime implementation
scripts/            experiments, verification and demos
tests/              unit, property, contract and end-to-end tests
data/               benchmark and frozen evidence artifacts
docs/               thesis, protocol, results, audits and demos
demo-ui/            comparative product-demo frontend
reports/            generated figures / reporting artifacts
CLAUDE.md            normative specification + append-only build log
```

Recommended entry points:

- [`docs/results-v2.1.md`](docs/results-v2.1.md) — current confirmatory results.
- [`docs/tfm-current-status.md`](docs/tfm-current-status.md) — one-page current status.
- [`docs/tfm-closure-no-human-v2.1.md`](docs/tfm-closure-no-human-v2.1.md) — protocol.
- [`docs/audit.md`](docs/audit.md) — instrument and implementation audit history.
- [`docs/product-demo.md`](docs/product-demo.md) — A/B/C comparative demo.
- [`docs/odoo-demo.md`](docs/odoo-demo.md) — guarded Odoo feasibility demonstration.
- [`docs/product-viability.md`](docs/product-viability.md) — commercial claims that do and do not survive the evidence.

---

## Scope / known limitations

This is a research prototype, not a production ERP security product.

Current boundaries include:

- H1b: no demonstrated task-success superiority over typed tools.
- H4: active danger recognition did not meet the preregistered safety target.
- H5: selective retrieval did not meet its preregistered adequacy thresholds.
- Odoo mapping covers 2/12 catalog skills.
- Durable persistence exists as a component but is not the basis of a production multi-tenant control plane.
- H8 models cost scenarios; it does not measure realized monetary savings.

These limitations are part of the result, not backlog items hidden from the evaluation.

---

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). GitHub can generate a formatted citation directly from that file.

Current software/research release metadata:

```text
ERP Agent OS
version 0.1.0
protocol tfm-protocol-v2.1.2
Jairo Gelpi Moreno, 2026
```

---

## License

This repository is released under the **MIT License**. See [`LICENSE`](LICENSE).

The MIT license covers this repository's software and associated documentation. Third-party datasets, papers and external benchmark material retain their own licenses and attribution requirements; their inclusion or use here does not relicense them under MIT.

---

## Responsible use

ERP Agent OS is designed to study governed execution, not to justify unattended production access to financial, HR, inventory or other high-impact ERP operations. Anyone adapting the project to a real organization should independently validate authorization, identity, tenant isolation, approval semantics, audit retention, data protection, rollback and operational security before enabling writes.
