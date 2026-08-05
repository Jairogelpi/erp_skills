# Design: Reproducible development foundation

## Scope and sequencing

This design delivers only the developer foundation described by this change. It is divided into three separately applied, independently reviewable units, each forecast below 400 changed lines. Unit 2 depends on the committed lock and commands from Unit 1; Unit 3 depends on the ignore policy and documentation convention established by Unit 1, but neither unit implements FakeERP, a skill contract, runtime, policy, API, database, benchmark population, or ERP behavior. The mandatory implementation order remains dataset → FakeERP → skill contract; this enabling work does not satisfy or reorder it.

| Unit | Dependency | Forecast | Outcome |
| --- | --- | ---: | --- |
| 1. Python project and deterministic quality baseline | Existing package/dataset scaffold | ≤350 | Locked Python 3.12 developer environment and separate quality contracts |
| 2. Containerized first-clone workflow and CI | Unit 1 lock and commands | ≤390 | Compose-via-Make path and CI for checks that exist |
| 3. Project-local developer assistance | Units 1–2 documentation/security conventions | ≤350 | Attributed Ponytail plus optional, local read-only MCP assistance |

A unit that forecasts above its limit must be split before implementation; a later unit must not be combined with an earlier one to evade that review boundary.

## Unit 1 — project, lock, and quality baseline

### Exact file boundary

Create or modify only:

- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `README.md`
- `Makefile` (quality-only targets; the Compose targets arrive in Unit 2)

The existing `src/erp_agent_os/` and `tests/` files are not changed by this unit.

### Dependency and command contract

Use `uv` as the lock manager because it supports Python 3.12, produces a committed, reviewable universal lock, and has a frozen install mode. `pyproject.toml` retains the distribution identity `erp-agent-os`, requires Python `>=3.12,<3.13`, and declares the existing runtime dependency with a bounded compatible range. It declares exact-version development tools in a `dev` dependency group: Ruff, mypy, pytest, pytest-cov, and build. `uv.lock` records the fully resolved versions, package artifacts, and hashes; implementation regenerates it only through the chosen `uv` version and reviews all resolution changes.

The documented install and CI contract is `uv sync --frozen --group dev`, which must fail rather than silently resolve if the lock and metadata disagree. `uv lock --check` verifies lock freshness. Tool and bootstrap version updates are intentional changes: update the declaration, regenerate the lock, review the resolved artifact hashes, then rerun all implemented checks. No normal path uses `latest`.

Make owns stable developer entry points:

| Target | Command role | Failure behavior |
| --- | --- | --- |
| `make format` | `uv run ruff format .` applies formatting | exits nonzero if Ruff cannot run/write |
| `make format-check` | `uv run ruff format --check .` verifies formatting | nonzero on unformatted files |
| `make lint` | `uv run ruff check .` lints | nonzero on lint findings/tool error |
| `make typecheck` | `uv run mypy src` statically type-checks | nonzero on type errors/tool error |
| `make test` | `uv run pytest` executes existing tests | nonzero on failures/collection errors |
| `make coverage` | `uv run pytest --cov=erp_agent_os --cov-report=term-missing` | nonzero on test/coverage tool failure |
| `make build` | `uv run python -m build` builds distribution artifacts | nonzero on invalid package/build failure |

Ruff is the only formatter and linter; mypy is only the static type checker and is never called a formatter. Ruff/mypy settings live in `pyproject.toml`; Ruff targets Python 3.12 and excludes generated/cache locations, while mypy targets `src` and avoids claiming full coverage of unimplemented modules.

`.gitignore` replaces the current runtime-only rule with explicit patterns for virtual environments, Python/tool caches, coverage, build and wheel metadata, test artifacts, local logs/generated artifacts, IDE/OS files, `.env` and variants, credentials/key patterns, and local MCP state. It explicitly retains tracked `config/development.defaults`, the MCP template, Ponytail provenance, and source documentation. It is a preventative policy, not a guarantee that a secret already tracked elsewhere is removed.

README supplies the repository (`erp_skills`) versus distribution (`erp-agent-os`) names, Python 3.12/uv prerequisites, locked-install sequence, quality commands, synthetic/no-sensitive-data rule, supported portability statement, and an honest status banner: FakeERP, skills, and runtime remain undelivered and FakeERP is still next. It also states that lock or environment failures must be repaired by using supported Python/uv and the committed lock, not by an ad-hoc unpinned install.

## Unit 2 — Compose, environment template, and CI

### Exact file boundary

Create or modify only:

- `Makefile`
- `Dockerfile`
- `compose.yaml`
- `config/development.defaults`
- `README.md`
- `.github/workflows/ci.yml`

It consumes but does not modify Unit 1's `pyproject.toml` or `uv.lock` unless an independently reviewed lock update is required by a declared container/bootstrap dependency.

### Container/data flow

`make up` delegates to `docker compose --env-file config/development.defaults up --build`; `make down` delegates to `docker compose --env-file config/development.defaults down`; `make logs` delegates to `docker compose --env-file config/development.defaults logs`; and `make compose-config` delegates to `docker compose --env-file config/development.defaults config`. The Compose service builds from the repository-relative `Dockerfile`, mounts no host-specific absolute path, accepts only non-secret default values, and runs a bounded development command rather than claiming an application server exists. A `.dockerignore` added only if needed to prevent build-context leakage is within this unit's file budget and must be added to the boundary before implementation.

The Dockerfile uses a Python 3.12 base image pinned by immutable digest, with the readable tag retained only as an annotation. It copies dependency metadata/lock before source, performs the same frozen installation contract, and runs as an unprivileged user where compatible with the development workflow. The implementation records the selected image tag, digest, retrieval date, and verification command in a comment or README. Compose uses only relative paths, `${VAR:-default}`/example variables, and named resources; no credentials, host network, privileged mode, Docker socket, or repository-external bind mount is allowed.

`config/development.defaults` is tracked and contains comments plus inert placeholders only (for example a local development mode and non-secret port); it contains no token, password, ERP endpoint, real credential, or private data. It is the canonical defaults input, so a real `.env` is neither required nor read by the supported commands; any local sensitive override remains ignored and must be supplied outside this tracked file. The tracked path deliberately avoids the `.env` filename family because the native sensitive-path safety policy treats that path family as sensitive and can restrict ordinary writes or review even for inert content. `config/development.defaults` therefore preserves a source-controlled, explicitly non-sensitive defaults contract while remaining compatible with that policy; it is not a secret-bearing configuration path.

### CI contract

The workflow runs on a supported Linux Python 3.12 runner and triggers on pushes and pull requests after Git exists; it does not initialize Git, create remotes, or publish. It installs a pinned `uv` release, checks `uv.lock`, uses `uv sync --frozen --group dev`, then executes `make format-check`, `make lint`, `make typecheck`, `make coverage`, and `make build`. Build artifacts remain CI workspace artifacts unless a later implemented artifact/publication change explicitly uploads or releases them.

Dataset validation, benchmark smoke, and artifact-production jobs are intentionally absent until their corresponding implementation and command exist. README and workflow comments identify them as additive §29 checks, not passed checks. CI failure stops the job at the failed command and exposes its log; it never falls back to unlocked installation or `continue-on-error` for a required check.

### Docker-unavailable validation

On this workstation Docker is not treated as installed or exercised. Unit 2 validates repository-local, non-container work: YAML/Compose structural inspection where the Compose CLI is unavailable, `make -n` expansion, `config/development.defaults` placeholder/ignore review, locked Python quality/test/build commands, and workflow syntax/review. The validation record explicitly says `make up`/image build/container smoke are **deferred**, not passed. A Docker-capable CI or reviewer later runs `docker compose --env-file config/development.defaults config` followed by `make up` and `make down`; failures block any claim of a working container path.

## Unit 3 — Ponytail provenance and optional Codebase Memory MCP

### Exact file boundary

Create only the following project-local assistance material (with generated local state excluded by Unit 1):

- `.ponytail/ponytail.md`
- `.ponytail/UPSTREAM.md`
- `.ponytail/LICENSE` (when required by the verified upstream license)
- `.mcp/codebase-memory.template.json`
- `scripts/bootstrap-codebase-memory.py`
- `docs/development-assistance.md`
- `README.md`
- `.gitignore`
- `Makefile`

No executable, downloaded package, binary, local database/index, token, or user/global MCP client configuration is committed. If a verified upstream license requires additional notices, add only that notice file and revise this boundary before implementation.

### Ponytail provenance/pinning process

Before vendoring, the implementer selects the canonical upstream repository and license, resolves a signed/tagged release to its full immutable commit SHA, downloads content at that exact revision, and records in `UPSTREAM.md`: upstream URL, full SHA, release/tag if any, retrieval date, license/SPDX identifier, copied file list, and SHA-256 for every vendored file. `ponytail.md` begins with a compact attribution and points to the manifest/license.

Verification is offline-first: `sha256sum` (or `Get-FileHash -Algorithm SHA256` on PowerShell) is compared to `UPSTREAM.md`. Network re-verification is opt-in and uses `git fetch <canonical-url> <full-sha>` followed by `git rev-parse FETCH_HEAD`, then compares the retrieved file hash with the manifest. A changed tag, branch, release label, missing license, mismatch, or unavailable revision rejects vendoring; nothing is replaced from a mutable branch or `latest` reference. Ponytail remains documentation/skill material only, not an application dependency or executable startup hook.

### MCP bootstrap/configuration contract

The committed template is declarative, token-free, and contains a repository-root placeholder rather than a user path. It defines a Codebase Memory MCP server launch through a package/version (or immutable source revision) chosen during implementation and recorded in `docs/development-assistance.md` with its license and verification digest. It passes only the resolved current checkout root and explicit read-only/server flags. It has no write, shell, network-ingest, parent-directory, home-directory, or global configuration target.

`make bootstrap-codebase-memory` invokes the Python bootstrap from the checkout root. The bootstrap must: resolve the physical repository root; reject invocation outside that root; reject a root containing a path traversal/symlink escape for its generated configuration; validate that the configured server pin is immutable; write the rendered configuration only under ignored `.mcp/local/`; and print the client-specific import/enable instruction rather than editing a user/global MCP file. It creates no global tool state and does not download/execute mutable content. If the selected MCP launcher needs an install, it is installed into an ignored checkout-local tool environment using a locked/pinned artifact with recorded hash, never into a global environment.

The configuration's server working directory and allowed root must be the same canonical repository path. Read-only is defense in depth: the template supplies server read-only flags and the bootstrap denies a configuration whose allowed root differs from the checkout. The tool may read committed and local files visible in this checkout, so the documentation warns users not to put secrets in it despite `.gitignore`; it has no token mechanism and is optional developer assistance, never a runtime dependency.

Failure is fail-closed: absent Python/tool prerequisites, an unknown or mutable server version, an invalid template, a path mismatch, an attempted external write, or an install/hash failure leaves no enabled configuration and returns nonzero. The script uses atomic write/cleanup so a failed run does not leave a partially enabled file. Disable/remove is `make remove-codebase-memory`, which deletes only ignored `.mcp/local/` configuration and local tool environment; it does not alter source, Compose, quality checks, or planned FakeERP work.

## Cross-unit threats, portability, and validation

| Threat/failure | Control and evidence |
| --- | --- |
| Lock drift or unsupported interpreter | Python 3.12 bounded metadata, committed `uv.lock`, `uv lock --check`, and frozen sync; failure is nonzero rather than resolution fallback. |
| Tool-role confusion | Separate Make/CI commands and README wording; review verifies Ruff formats/lints and mypy type-checks only. |
| Secrets or local artifacts enter review/build context | Comprehensive ignore rules, inert tracked `config/development.defaults`, Docker context review, no committed MCP state/binaries, and manual secret scan before publication. |
| Docker absent locally | Do not execute or pass container smoke; record it deferred and require Docker-capable `compose config/up/down` evidence. |
| Host portability breakage | Python 3.12, uv, GNU-compatible Make, Docker Compose v2 documented; paths are relative. Windows users use a POSIX-compatible shell/Make or invoke documented underlying commands. Native Windows Docker/Make behavior is not claimed without validation. |
| CI overclaims unavailable features | CI contains only installed quality/test/build checks; no dataset/benchmark/artifact success badge or job until implementations exist. |
| Supply-chain/provenance substitution | Lock hashes, image digest, exact tool pins, Ponytail SHA-256/commit manifest, and fail-closed MCP bootstrap. |
| MCP reads/writes outside scope | Canonical-root equality, read-only flags, checkout-local ignored output, no global config, and removal procedure. |

Unit-level validation is performed after each unit without adding application tests solely for configuration. Unit 1 runs frozen sync, lock check, each quality command, existing pytest suite, and build. Unit 2 reruns those checks plus Make dry-run/Compose syntax checks available locally and reviews CI/environment/container paths; Docker smoke is deferred when unavailable. Unit 3 hashes Ponytail against its manifest; exercises bootstrap rejection for outside-root, mutable/mismatched pin, and invalid output path; exercises successful local rendering with a fixture/template; confirms remove only removes ignored local state; then reruns Unit 1 quality/test/build commands. Tests added for bootstrap behavior are limited to `tests/test_bootstrap_codebase_memory.py` if the script's parsing/path logic warrants them; no test claims an external MCP server works without its verified dependency.

## Rollout, rollback, and publication boundary

Apply and accept Unit 1, then Unit 2, then Unit 3. Record observed commands, exact selected pins/digests, and Docker deferral status in the corresponding later apply evidence; do not mark a deferred command passed. Roll back in reverse order: remove optional MCP/Ponytail material, then Compose/CI workflow, then quality/lock baseline. Each rollback must leave existing dataset scaffold intact and must not alter the dataset → FakeERP → skill-contract dependency.

This change does not initialize Git, stage or commit files, add a remote, configure credentials, create a release, upload artifacts, or publish to GitHub/PyPI. Git initialization and public publication are separately authorized lifecycle actions after all three units have been accepted and their provenance, secret review, and Docker-capable validation evidence are available.
