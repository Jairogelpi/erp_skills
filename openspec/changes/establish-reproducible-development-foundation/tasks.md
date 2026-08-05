# Tasks: Establish reproducible development foundation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | Unit 1: ≤350; Unit 2: ≤390; Unit 3: ≤350 |
| 400-line budget risk | Low |
| Chained PRs recommended | Yes |
| Suggested split | Unit 1 → Unit 2 → Unit 3 |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Low

## Delivery constraints

- Apply exactly one unit at a time in the stated order. Do not combine units or begin a later unit until its predecessor is accepted; split the unit again before apply if its actual forecast reaches 400 changed lines.
- Strict TDD evidence is recorded as **RED → GREEN → TRIANGULATE → REFACTOR**. Before Unit 1 tooling exists, the only current test command is `python -m pytest`; `uv lock --check`, `uv sync --frozen --group dev`, and all `make` checks are planned commands and cannot run yet.
- Do not initialize Git, stage/commit/push, configure a remote or credentials, publish, upload/release artifacts, or implement FakeERP, skills, runtime, or later components.

## Unit 1 — Python project and deterministic quality baseline (depends on existing dataset scaffold; ≤350 changed lines)

**Start/finish boundary:** start from the existing scaffold; finish only `pyproject.toml`, `uv.lock`, `.gitignore`, `README.md`, and quality-only `Makefile` targets. No `src/` or `tests/` changes.

- [x] **RED:** Run the current baseline `python -m pytest` and record its result; inspect the absent/unconfigured project entry points so the planned `uv lock --check`, `uv sync --frozen --group dev`, `make format-check`, `make lint`, `make typecheck`, `make test`, `make coverage`, and `make build` are explicitly recorded as unavailable before their Unit 1 tooling exists. <!-- sdd-owner: implementation -->
- [x] **GREEN:** Create `pyproject.toml` for Python `>=3.12,<3.13` and distribution `erp-agent-os`; declare bounded existing runtime dependency plus exact dev-group pins for Ruff, mypy, pytest, pytest-cov, and build; configure Ruff (formatter/linter, Python 3.12) and mypy (static checker for `src`) separately, then generate and review committed universal `uv.lock` with resolved versions/artifact hashes. <!-- sdd-owner: implementation -->
- [x] **GREEN:** Add quality-only targets in `Makefile`: `format`, `format-check`, `lint`, `typecheck`, `test`, `coverage`, and `build`, mapping exactly to the design's `uv run` commands; update `.gitignore` to exclude environments, caches, coverage, build/wheel/test/log artifacts, IDE/OS files, real `.env` variants, credentials/keys, and local MCP state while retaining `.env.example`, MCP template, Ponytail provenance, and documentation. <!-- sdd-owner: implementation -->
- [x] **GREEN:** Write the Unit 1 `README.md` foundation guidance: `erp_skills` repository versus `erp-agent-os` distribution identity, Python 3.12/uv prerequisites, `uv sync --frozen --group dev` workflow, reproducibility/no-sensitive-data policy, quality commands, portability limits, and honest status that FakeERP, skills, and runtime remain undelivered and FakeERP remains next. <!-- sdd-owner: implementation -->
- [x] **TRIANGULATE:** After Unit 1 exists, run `uv lock --check`, `uv sync --frozen --group dev`, `make format-check`, `make lint`, `make typecheck`, `make test`, `make coverage`, `make build`, and `python -m pytest`; verify frozen sync fails on intentionally detected lock/metadata drift without an unlocked fallback, and inspect `uv.lock` for exact resolved pins/hashes rather than `latest`. <!-- sdd-owner: implementation -->
- [x] **REFACTOR:** Remove duplicated/misleading command documentation and normalize configuration without changing behavior; re-run the locked checks above and manually verify `.env.example` remains unignored while real `.env`, secrets, generated output, and local MCP state are excluded. <!-- sdd-owner: implementation -->
- [x] **Rollback boundary:** Confirm reverting only `pyproject.toml`, `uv.lock`, `.gitignore`, `README.md`, and quality-only `Makefile` restores the pre-foundation scaffold without touching dataset material or implying FakeERP/skill progress. <!-- sdd-owner: implementation -->

## Unit 2 — Containerized first-clone workflow and CI (depends on accepted Unit 1 lock and commands; ≤390 changed lines)

**Start/finish boundary:** extend only `Makefile`, `Dockerfile`, `compose.yaml`, `.env.example`, `README.md`, `.github/workflows/ci.yml`, and `.dockerignore` only if needed and added to this boundary before implementation. Consume, but do not modify, Unit 1 metadata/lock absent a separately reviewed declared dependency change.

- [x] **RED:** From the Unit 1 baseline, run `make -n up`, `make -n down`, `make -n logs`, and `make -n compose-config` before adding Compose targets and record their expected absence; record whether Docker/Compose is available—do not run or pass Docker smoke when unavailable. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Add repository-relative `Dockerfile` and `compose.yaml` with Python 3.12 image tag plus immutable digest, recorded retrieval date/verification command, frozen lock installation, compatible unprivileged user, no privileged/network/socket/external bind mount, and a bounded development command; add `.dockerignore` if needed to prevent context leakage. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Extend `Makefile` with canonical `up` (`docker compose --env-file .env.example up --build`), `down`, `logs`, and `compose-config`; add placeholder-only `.env.example`; update `README.md` with first-clone prerequisites, portable Compose-via-Make workflow, supported targets, and Docker-unavailable deferral wording. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Add `.github/workflows/ci.yml` for Linux/Python 3.12 triggers, pinned `uv`, `uv lock --check`, `uv sync --frozen --group dev`, then `make format-check`, `make lint`, `make typecheck`, `make coverage`, and `make build`; explicitly label dataset validation, benchmark smoke, and artifact production as additive checks absent until implemented, with no unlocked fallback or `continue-on-error`. <!-- sdd-owner: implementation -->
- [ ] **TRIANGULATE:** Re-run Unit 1's locked quality/test/build commands; validate `make -n` expansions, Compose/YAML structure available locally, CI command ordering, image/source pin provenance, and `.env.example`/`.gitignore` secret-index exclusion. If Docker is available, run `docker compose --env-file .env.example config`, `make up`, and `make down`; otherwise record all container config/build/smoke commands as deferred to a Docker-capable CI or reviewer environment, not passed. <!-- sdd-owner: implementation -->
- [ ] **REFACTOR:** Simplify repeated Make/README/CI wording while preserving exact commands and scope boundaries; re-run non-container checks and verify no host-specific absolute paths, secret values, credentials, Docker socket, or completion claims for unavailable dataset/benchmark/artifact work. <!-- sdd-owner: implementation -->
- [ ] **Rollback boundary:** Confirm reverting Unit 2-only files removes Compose/CI assistance without changing Unit 1 lock/quality behavior, dataset scaffold, or the required dataset → FakeERP → skill order. <!-- sdd-owner: implementation -->

## Unit 3 — Project-local development assistance (depends on accepted Units 1–2 conventions; ≤350 changed lines)

**Start/finish boundary:** create only `.ponytail/ponytail.md`, `.ponytail/UPSTREAM.md`, applicable `.ponytail/LICENSE`, `.mcp/codebase-memory.template.json`, `scripts/bootstrap-codebase-memory.py`, `docs/development-assistance.md`, and required `README.md`, `.gitignore`, and `Makefile` edits; add `tests/test_bootstrap_codebase_memory.py` only if bootstrap parsing/path logic requires it. Never commit executables, binaries, indexes, local state, tokens, or global MCP configuration.

- [ ] **RED:** Add focused failing tests in `tests/test_bootstrap_codebase_memory.py` when the bootstrap has testable parsing/path logic (otherwise document the configuration-only RED inspection): outside-root invocation, mutable/unknown pin, invalid template, allowed-root mismatch/symlink escape, attempted external output, and failed install/hash must return nonzero and leave no enabled local configuration. Run each focal test with `python -m pytest tests/test_bootstrap_codebase_memory.py`. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Select verified Ponytail upstream and license, resolve a full immutable commit SHA, and vendor `.ponytail/ponytail.md` with compact attribution plus `.ponytail/UPSTREAM.md` recording canonical URL, full SHA, release/tag, retrieval date, SPDX/license, copied files, and SHA-256 per file; include required license notice only. Document offline `sha256sum`/PowerShell verification and opt-in `git fetch <canonical-url> <full-sha>` / `git rev-parse FETCH_HEAD` network re-verification. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Implement token-free `.mcp/codebase-memory.template.json`, a checkout-local `scripts/bootstrap-codebase-memory.py`, and `make bootstrap-codebase-memory`/`make remove-codebase-memory`; require immutable server pin/digest and recorded license, canonical current repository root equality for working/allowed roots, explicit read-only flags, ignored `.mcp/local/` output, atomic write/cleanup, and no global config, external writes, mutable download, or enabled partial file on failure. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Document optional assistance, precise bootstrap/import instruction, provenance verification, prerequisites, repository-local/read-only/token-free limits, secret warning, failure behavior, and disable/removal procedure in `docs/development-assistance.md` and `README.md`; preserve the statement that this is not runtime/FakeERP/skill work. <!-- sdd-owner: implementation -->
- [ ] **TRIANGULATE:** Run `python -m pytest tests/test_bootstrap_codebase_memory.py` when present and `python -m pytest`; exercise bootstrap success with a fixture/template plus each failure path (outside root, mutable/mismatched pin, invalid template, root mismatch/symlink escape, attempted external write, and hash/install failure), confirming nonzero failure, atomic cleanup, no global state, and `make remove-codebase-memory` removes only ignored local MCP state/tool environment. Verify Ponytail hashes against `UPSTREAM.md` and verify no secret/token/index/binary is tracked or admitted by `.gitignore`. <!-- sdd-owner: implementation -->
- [ ] **REFACTOR:** Reduce duplicate security/provenance wording and keep all paths/configuration canonical without weakening fail-closed checks; re-run bootstrap tests, source-pin/hash verification, Unit 1 locked checks, and removal verification. <!-- sdd-owner: implementation -->
- [ ] **Rollback boundary:** Confirm removing Unit 3 material/local state leaves Compose startup, CI, quality checks, the dataset scaffold, and the dataset → FakeERP → skill order unchanged. <!-- sdd-owner: implementation -->

## Parent review and lifecycle gates

- [ ] Review each completed unit independently against its exact file and changed-line boundary; reject/split any unit at or above 400 changed lines and require evidence for the stated RED → GREEN → TRIANGULATE → REFACTOR cycle. <!-- sdd-owner: parent -->
- [ ] After Unit 2, obtain Docker-capable evidence for `docker compose --env-file .env.example config`, `make up`, and `make down` if local Docker smoke was deferred; do not mark those commands passed from non-Docker review. <!-- sdd-owner: parent -->
- [ ] Before any separately authorized Git/publication lifecycle action, review source pins/provenance, secret/index exclusion, MCP failure-path evidence, deferred Docker status, and the unchanged FakeERP/skill/runtime boundary. <!-- sdd-owner: parent -->
