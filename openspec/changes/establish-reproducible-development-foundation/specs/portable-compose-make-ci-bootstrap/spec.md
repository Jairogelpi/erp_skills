# Portable Compose Make CI Bootstrap Specification

## Purpose

Provide the second sequential foundation unit: a portable, from-zero container startup and continuous-integration contract. This unit advances `CLAUDE.md` §§27, 29, and 35 and roadmap P7.1/P7.4/P7.5 without claiming unavailable application components are complete.

## Requirements

### Requirement: Canonical portable Compose startup

The system MUST provide Docker Compose as the canonical startup path and MUST expose that path through documented Make targets. The Compose invocation exposed by those targets MUST consume the tracked `config/development.defaults` file through `--env-file config/development.defaults`. Compose files and Make targets MUST NOT require host-specific absolute paths. Documentation MUST state supported prerequisites and the first-clone procedure. Dockerfiles MUST be included only when required by the Compose startup path.

#### Scenario: Developer follows first-clone startup guidance

- GIVEN a fresh clone on a Docker-capable supported environment
- WHEN a developer follows the documented Make-driven startup procedure
- THEN the procedure invokes the repository's Compose configuration with `--env-file config/development.defaults` and without requiring a host-specific absolute path

### Requirement: Inert non-secret development defaults and deferred Docker honesty

The system MUST provide the tracked `config/development.defaults` file as an inert defaults file containing placeholders only. It MUST NOT include secrets, tokens, real ERP credentials, private data, or committed local environment files. The system MUST NOT require or provide `.env.example` for this workflow. This replacement is a safety-policy compatibility amendment: `config/development.defaults` preserves reviewable, non-secret first-clone configuration while avoiding the native policy restriction that blocks `.env.example`. When Docker is unavailable in an execution environment, documentation and validation records MUST identify container smoke validation as deferred to a Docker-capable CI or reviewer environment. The system MUST NOT represent deferred Docker execution as having passed locally.

#### Scenario: Developer uses the inert tracked defaults

- GIVEN a fresh clone and the tracked `config/development.defaults` file
- WHEN the developer invokes the documented Make-driven Compose startup procedure
- THEN Compose consumes that file through `--env-file`, and the file contains placeholders only with no secret or credential value

#### Scenario: Safety policy blocks `.env.example`

- GIVEN the native safety policy blocks creation of `.env.example`
- WHEN the bootstrap unit provides first-clone environment defaults
- THEN it uses the tracked inert `config/development.defaults` file without weakening the placeholders-only or no-secret requirements

#### Scenario: Workstation lacks Docker

- GIVEN Docker is unavailable on the current workstation
- WHEN the bootstrap unit is validated
- THEN non-container validation may be recorded and the container smoke check is explicitly recorded as deferred rather than passed

### Requirement: Honest deterministic CI coverage

The system MUST define GitHub Actions checks that install from the committed dependency lock, run Ruff formatting verification and linting, run mypy static type checking, run tests and coverage when tests exist, and build the package. CI MUST run dataset validation, benchmark smoke checks, and artifact production only when their corresponding implementations exist. CI documentation MUST identify those absent future checks as additive requirements of `CLAUDE.md` §29 rather than falsely claiming completion.

#### Scenario: CI runs before dataset and benchmark implementations exist

- GIVEN the dataset validation and benchmark smoke components are not implemented
- WHEN CI executes for this foundation
- THEN CI runs the implemented locked-install, Ruff, mypy, applicable test/coverage, and build checks without reporting dataset, benchmark, or artifact checks as completed

### Requirement: Scope and publication boundary

The bootstrap MUST document reproducibility and no-sensitive-data expectations required by roadmap P2.4 and P7.5. It MUST NOT implement or claim completion of FakeERP, the skill contract, runtime, dataset validation, benchmark execution, or application artifacts. Git initialization, commits, remote configuration, credentials, and public GitHub publication MUST remain separate user-authorized lifecycle actions and MUST NOT be performed or implied by this unit.

#### Scenario: Reviewer assesses delivery boundaries

- GIVEN a reviewer reads the bootstrap documentation and CI configuration
- WHEN the reviewer checks for delivery and lifecycle claims
- THEN the reviewer finds no claim that FakeERP or later components are complete and no claim that Git initialization or publication occurred
