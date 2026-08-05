# Project-local Ponytail and Codebase Memory MCP Specification

## Purpose

Provide the third sequential foundation unit: optional project-local developer assistance that is attributable, reproducible, security-bounded, and not an application runtime dependency. This unit supports the reproducibility and no-sensitive-data obligations of `CLAUDE.md` §§27, 35, and 42 and roadmap P2.4/P7.1/P7.5.

## Requirements

### Requirement: Attributed immutable Ponytail vendoring

The system MUST vendor Ponytail as an attributed project-local skill. The vendored material MUST identify its upstream origin, applicable license or attribution information, immutable upstream revision, and a documented verification command or procedure. The normal developer workflow MUST NOT download or execute unverified mutable upstream content.

#### Scenario: Reviewer verifies vendored Ponytail provenance

- GIVEN a reviewer inspects the project-local Ponytail material
- WHEN the reviewer follows its documented verification procedure
- THEN the reviewer can identify its upstream origin, applicable attribution or license, immutable revision, and the method to verify the vendored content

### Requirement: Opt-in repository-scoped read-only Codebase Memory MCP

The system MUST provide an explicit bootstrap command and configuration for Codebase Memory MCP that installs or configures it only for the current checkout. The configuration MUST be optional, read-only, token-free, and restricted so that it cannot operate on another repository. The repository MUST NOT commit an executable or binary for Codebase Memory MCP, create globally installed MCP state, or grant repository-external write access.

#### Scenario: Developer opts into MCP for this checkout

- GIVEN a developer has not enabled Codebase Memory MCP
- WHEN the developer invokes the documented bootstrap command from this repository
- THEN the resulting configuration is local to this checkout, read-only, token-free, and scoped to this repository only

### Requirement: Reversible optional developer assistance

The system MUST document Codebase Memory MCP as optional developer assistance rather than an application runtime dependency. Documentation MUST provide disable and removal procedures. Disabling or removing the MCP configuration MUST NOT affect the application, Compose startup, quality checks, FakeERP planning, or the required dataset → FakeERP → skill-contract order in `CLAUDE.md` §42.

#### Scenario: Developer removes MCP assistance

- GIVEN a developer previously enabled the optional MCP configuration
- WHEN the developer follows the documented disable or removal procedure
- THEN the local MCP assistance is removed or disabled and no application capability is represented as changed

### Requirement: Security-bounded foundation scope

The project-local assistance unit MUST preserve source pinning and MUST NOT commit secrets, tokens, private data, real ERP credentials, or generated binaries. It MUST NOT implement or claim completion of FakeERP, skills, runtime, policy engine, API, database, benchmark, retrieval, LLM integration, Odoo, dashboard, or experimental results. Git initialization and public publication MUST remain separate user-authorized lifecycle actions.

#### Scenario: Reviewer checks optional-assistance boundaries

- GIVEN a reviewer examines the Ponytail and MCP documentation and configuration
- WHEN the reviewer evaluates security and delivery scope
- THEN the reviewer finds immutable provenance, no secrets or binaries, repository-only read-only MCP access, and no completion claim for FakeERP or later project components
