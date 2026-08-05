# Deterministic Python Quality Baseline Specification

## Purpose

Provide the first sequential foundation unit: a reproducible Python 3.12 quality baseline for ERP Agent OS, without delivering FakeERP, skills, or runtime behavior. This unit implements the reproducibility intent of `CLAUDE.md` §§27, 29, and 35 and roadmap P2.4/P7.1–P7.5 while preserving the construction order in `CLAUDE.md` §42.

## Requirements

### Requirement: Deterministic Python project identity and dependencies

The system MUST define Python 3.12 project metadata whose distribution name is `erp-agent-os`, while documenting that the public repository name is `erp_skills`. The project MUST use a reviewable dependency lock that pins resolved dependency versions. The project MUST document a verification command or procedure that proves installation uses the lock. Any nontrivial bootstrap dependency MUST identify an immutable source version or digest where available; normal setup MUST NOT rely on mutable `latest` references.

#### Scenario: Fresh checkout installs the reviewed dependency set

- GIVEN a supported environment with Python 3.12 and a fresh checkout
- WHEN a developer follows the documented locked-install procedure
- THEN the procedure uses the committed lock and identifies the resolved dependency versions without requiring an unpinned mutable dependency reference

### Requirement: Distinct executable quality checks

The system MUST configure and document local entry points for Ruff formatting, Ruff linting, and mypy static type checking. Ruff MUST be the formatter and linter. mypy MUST be described and invoked only as a static type checker and MUST NOT be described as a formatter. The quality configuration MUST be compatible with the locked project dependencies.

#### Scenario: Developer runs quality entry points

- GIVEN the locked project environment is installed
- WHEN a developer invokes the documented formatting, linting, and type-checking entry points
- THEN Ruff performs formatting and linting, and mypy performs static type checking as separate checks

### Requirement: Local-artifact and secret exclusion

The system MUST ignore virtual environments, caches, build outputs, local environment files, secrets, coverage output, editor files, and generated local artifacts. The ignore policy MUST retain `.env.example` for review while excluding real `.env` files. The baseline MUST NOT commit secrets, tokens, private data, real ERP credentials, or generated binaries.

#### Scenario: Environment template remains reviewable without real credentials

- GIVEN a developer prepares local environment configuration
- WHEN the developer adds a real `.env` file and retains `.env.example`
- THEN the real `.env` file is excluded by the repository policy and `.env.example` remains eligible for version control with non-secret placeholders only

### Requirement: Honest foundation documentation and construction boundary

The repository documentation MUST state prerequisites, supported local workflow, reproducibility expectations, repository/distribution naming, and the absence of sensitive data in committed foundation material. It MUST state that FakeERP, skills, and runtime are not delivered by this unit and MUST NOT claim their completion. It MUST preserve `CLAUDE.md` §42's required dataset → FakeERP → skill-contract order; this foundation MUST precede but MUST NOT substitute for the separately planned FakeERP work.

#### Scenario: Reader determines delivered scope

- GIVEN a reader consults the foundation documentation
- WHEN the reader checks the status and next construction dependency
- THEN the reader can determine that only the quality foundation is delivered and that FakeERP remains the next required implementation unit before the skill contract
