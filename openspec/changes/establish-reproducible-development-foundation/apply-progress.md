# Apply progress: Unit 1 — Python project and deterministic quality baseline

## Status

- **Apply slice:** Unit 1 only, for `establish-reproducible-development-foundation`.
- **Status consumed:** `changeName=establish-reproducible-development-foundation`, `applyState=ready`, `actionContext.mode=repo-local`, workspace/allowed root `/c/Users/EQUIPO/Desktop/epistemologi`.
- **Delivery boundary:** `size:exception` approved for the atomic metadata-plus-universal-lock boundary. The actual 467 changed lines across the five Unit 1 implementation files exceeds the normal 400-line review budget because `uv.lock` alone has 271 lines of resolved package and artifact-hash data. No Unit 2 or Unit 3 material was started.
- **Action-context warnings:** none. The workspace has no Git metadata; no Git lifecycle operation was performed and there is no staging area.

## Completed implementation tasks

All seven Unit 1 implementation-owned task rows are visibly marked `- [x]` in `tasks.md`:

1. RED baseline and absent-entry-point inspection.
2. Python 3.12 metadata, exact dev pins, separate Ruff/mypy configuration, and reviewed `uv.lock`.
3. Quality-only Make targets and ignore policy.
4. README foundation guidance and honest delivery status.
5. Locked validation, lock-drift rejection, and resolved-pin/hash inspection.
6. Documentation/configuration normalization and ignore-policy inspection.
7. Rollback-boundary confirmation.

Parent-owned lifecycle/review rows remain unchanged and unchecked. Unit 2 and Unit 3 rows remain unchanged and unchecked.

## Files changed

- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `README.md`
- `Makefile`
- `openspec/changes/establish-reproducible-development-foundation/tasks.md` (Unit 1 checkboxes only)
- `openspec/changes/establish-reproducible-development-foundation/apply-progress.md`

No `src/` or `tests/` file was changed. No application capability was added.

## Verification evidence

| Command / check | Result | Evidence |
| --- | --- | --- |
| `python -m pytest` (RED baseline) | passed | 5 passed in 1.51s using pre-existing environment. |
| `uv lock --check` before Unit 1 | failed as expected | Exit 2: no `uv.lock` existed. |
| `uv sync --frozen --group dev` before Unit 1 | failed as expected | Exit 2: frozen sync refused absent lock. |
| `make format-check`, `make lint`, `make typecheck`, `make test`, `make coverage`, `make build` before Unit 1 | unavailable as expected | `make` is not installed on this Windows workstation (exit 127). |
| `uv lock` | passed | Resolved 18 packages with `uv 0.11.19`; generated a 271-line universal lock with artifacts/hashes. |
| `uv lock --check` after Unit 1 | passed | Lock is fresh. |
| intentional metadata version drift + `uv lock --check` | failed as expected | Exit 1, then exact metadata restoration produced a passing lock check; no unlocked fallback was used. |
| `uv sync --frozen --group dev` | passed | Installed locked environment: build 1.2.2.post1, mypy 1.15.0, pytest 8.3.5, pytest-cov 6.0.0, Ruff 0.11.13, and locked transitives. |
| `uv run ruff format --check .` | passed | 3 Python files already formatted. |
| `uv run ruff check .` | passed | All checks passed. |
| `uv run mypy src` | passed | Success: no issues in 2 source files. |
| `uv run pytest` | passed | 5 passed (final run: 0.54s). |
| `uv run pytest --cov=erp_agent_os --cov-report=term-missing` | passed | 5 passed; 99% total coverage. |
| `uv run python -m build` | passed | Produced sdist and wheel; generated build artifacts were removed afterward. |
| `python -m pytest` (final) | passed | 5 passed in 2.16s using the pre-existing environment. |
| manual ignore-policy inspection | passed | Required exclusion rules and `!.env.example` retention are present. Git's ignore matcher could not be used because there is intentionally no Git metadata. |

The Make targets map exactly to the successful `uv run` commands above, but cannot be executed locally until GNU-compatible `make` is installed. This is a workstation prerequisite limitation, not an unlocked fallback.

## TDD Cycle Evidence

| Task | Test File / layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- |
| Unit 1 structural quality baseline | Existing `tests/test_dataset.py` / existing unit suite | `python -m pytest`: 5/5 | Baseline passed; missing lock caused `uv lock --check` and frozen sync to fail as expected; Make was absent | Metadata, lock, Make, ignore policy, and README created; locked direct commands passed | Fresh lock passed; deliberate metadata drift made `uv lock --check` fail (exit 1), restoration passed; quality/test/build commands passed | Configuration/docs normalized; repeated locked checks passed; no source/test refactor required |

- **Tests added:** none. The approved Unit 1 exact boundary prohibits `src/` and `tests/` changes; this is structural/configuration work.
- **Triangulation:** structural task; exercised both valid locked state and invalid lock/metadata drift state.
- **Approval tests:** none; no existing production behavior was refactored.
- **Pure functions created:** none.

## Design deviations

- None in project behavior or scope.
- The approval-recorded `size:exception` was required because the metadata-plus-complete lock is atomic and totals 467 changed lines, exceeding the normal 400-line budget.
- Direct `uv run` commands provided local evidence for the Make recipes because GNU Make is unavailable. README accurately lists Make as a prerequisite; no claim is made that Make was locally validated.

## Remaining and deferred work

- Unit 2 and Unit 3 implementation tasks remain unchecked and were not started.
- Parent-owned lifecycle actions remain unchecked: independent unit review, Docker-capable evidence after Unit 2, and any separately authorized Git/publication review.
- Install GNU-compatible `make` on a suitable supported environment to execute the documented Make wrappers verbatim.

## Rollback

Reverting only `pyproject.toml`, `uv.lock`, `.gitignore`, `README.md`, and `Makefile` restores the pre-foundation scaffold. It does not touch dataset material and does not imply FakeERP, skills, or runtime progress.

## Build reliability follow-up

An independent verifier reported that `uv run python -m build` exceeded its 120-second bound while building the wheel. Investigation found that the project declared the PEP 517 backend as the mutable range `setuptools>=69`. The `build` tool creates a separate isolated environment for both sdist and wheel and installs that requirement with pip; consequently, the selected backend and network/cache work could vary. A diagnostic pin to `setuptools==69.5.1` confirmed an additional wheel-stage installation of `wheel` and completed in 114 seconds, leaving too little margin.

The build-system requirement is now the immutable `setuptools==80.9.0`. This version includes the wheel build command, eliminating the additional `wheel` installation seen with the older backend. The lock was refreshed and checked. From clean ignored build outputs, the required command was bounded with `timeout 120 uv run python -m build`; it passed in **82 seconds**, producing both the sdist and wheel. Generated `build/`, `dist/`, `src/erp_agent_os.egg-info/`, coverage output, and `.coverage` were removed after validation.

Follow-up full locked validation passed: `uv lock --check`, `uv sync --frozen --group dev`, direct equivalents of the unavailable Make wrappers (`uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`, `uv run pytest`, `uv run pytest --cov=erp_agent_os --cov-report=term-missing`), bounded `uv run python -m build`, and `python -m pytest`. Make remains unavailable locally because GNU-compatible Make is not installed; this follow-up does not claim the wrappers themselves ran.

### Follow-up TDD evidence

| Task | Safety net / RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- |
| Unit 1 build reliability | `python -m pytest`: 5/5; clean bounded build exposed isolated `setuptools>=69` installation and variable duration | Exact backend pin added; full locked checks passed | `setuptools==69.5.1` required an extra `wheel` installation and took 114s; `setuptools==80.9.0` removed that step and passed in 82s | Kept the existing exact Make recipe and only made the backend immutable; generated outputs cleaned |

Residual risk: the standards-compliant isolated build still obtains the exact backend through pip, so an unusually slow or unavailable package index/cache can consume the 120-second verifier bound. It now has a fixed version and observed 38-second margin, but offline/restricted-network reliability requires a prewarmed/cache-controlled build environment or a separately approved build-command change.

---

# Apply progress: Unit 2 — partial / blocked

## Status and delivery boundary

- **Status consumed:** parent-selected `changeName=establish-reproducible-development-foundation`, Unit 2 `applyState=ready`, `actionContext.mode=repo-local`, allowed workspace root `/c/Users/EQUIPO/Desktop/epistemologi`.
- **Delivery path:** authorized `auto-chain`, Unit 2 slice only; no Git metadata exists and no Git lifecycle action was performed.
- **Workload:** 133 implementation diff lines so far (excluding change-local task/evidence artifacts), below the 400-line limit. No size exception is requested.
- **Action-context warnings:** none.

## Completed task and persistence

- The Unit 2 implementation-owned RED row is visibly marked `- [x]` in `tasks.md`.
- Unit 3 rows and every parent-owned lifecycle row remain untouched and unchecked.

## RED evidence

| Check | Result | Evidence |
| --- | --- | --- |
| `make -n up`, `make -n down`, `make -n logs`, `make -n compose-config` before targets | unavailable / expected absence | GNU Make is unavailable (`command not found`, exit 127) for each command. |
| `docker --version`, `docker compose version` | unavailable | Docker is unavailable (`command not found`, exit 127); no container command was run or passed. |
| `python -m pytest` safety net | passed | 5 passed in 1.86s before configuration changes. |

## Partial implementation (not task-complete)

Created `Dockerfile`, `compose.yaml`, `.dockerignore`, and CI workflow; extended `Makefile` and `README.md`. The Docker source is `python:3.12-slim@sha256:9e869b0816f5537709825b49e62dc86d1c2691eff19b05c1d4dc3a07992cc052`, retrieved 2026-08-05 from Docker Hub's manifest endpoint; its recorded verification command is `docker buildx imagetools inspect python:3.12-slim`. CI pins `astral-sh/setup-uv` to `d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` (v5.4.2) and uv 0.11.19; CI has only current checks and no `continue-on-error` or unlocked fallback.

Creation of the required inert `.env.example` is blocked by the execution environment's sensitive-file writer policy even after explicit supervisor approval. The file does not exist, so the Unit 2 environment/Make/README GREEN row, CI GREEN row, TRIANGULATE, REFACTOR, and rollback row must remain unchecked. No policy bypass was attempted.

## Validation observed

| Command / check | Result | Evidence |
| --- | --- | --- |
| `uv lock --check` | passed | Lock freshness confirmed. |
| `uv sync --frozen --group dev` | passed | Locked environment checked. |
| `uv run ruff format --check .`; `uv run ruff check .`; `uv run mypy src`; `uv run pytest`; coverage | passed | Formatting, linting, type checking, 5 tests, and 99% coverage passed. |
| `timeout 120 uv run python -m build` | failed | Timed out (exit 124) during isolated wheel build / `ensurepip`; generated outputs were cleaned by the shell trap sequence only after command termination. |
| `python -m pytest` final | not run | The command chain stopped at the bounded build failure. |
| YAML parse + static Compose/CI assertions | passed | `compose.yaml` and workflow parsed with PyYAML; static checks found frozen install, digest, unprivileged user, relative context, no forbidden socket/privileged/host-network/volume configuration, ordered CI commands, and no `continue-on-error`. |
| Docker Compose config, `make up`, `make down` | deferred | Docker and GNU Make unavailable; never passed. |

## TDD Cycle Evidence

| Task | Test File / layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- |
| Unit 2 structural bootstrap | Existing `tests/test_dataset.py` / unit suite | `python -m pytest`: 5/5 | Make/Docker absence observed before target/config creation | Partial static configuration only; incomplete because `.env.example` could not be persisted | Static YAML/container/CI contract checks passed; Docker and Make execution deferred | Not reached; Unit 2 remains blocked |

- **Tests added:** none. The approved Unit 2 boundary is structural/configuration-only and excludes `tests/`.
- **Triangulation:** structural only; both absent local Docker/Make and static valid YAML/configuration paths were exercised.
- **Pure functions created / approval tests:** none.

## Remaining exact unchecked Unit 2 rows

- [ ] **GREEN:** Add repository-relative `Dockerfile` and `compose.yaml` with Python 3.12 image tag plus immutable digest, recorded retrieval date/verification command, frozen lock installation, compatible unprivileged user, no privileged/network/socket/external bind mount, and a bounded development command; add `.dockerignore` if needed to prevent context leakage. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Extend `Makefile` with canonical `up` (`docker compose --env-file .env.example up --build`), `down`, `logs`, and `compose-config`; add placeholder-only `.env.example`; update `README.md` with first-clone prerequisites, portable Compose-via-Make workflow, supported targets, and Docker-unavailable deferral wording. <!-- sdd-owner: implementation -->
- [ ] **GREEN:** Add `.github/workflows/ci.yml` for Linux/Python 3.12 triggers, pinned `uv`, `uv lock --check`, `uv sync --frozen --group dev`, then `make format-check`, `make lint`, `make typecheck`, `make coverage`, and `make build`; explicitly label dataset validation, benchmark smoke, and artifact production as additive checks absent until implemented, with no unlocked fallback or `continue-on-error`. <!-- sdd-owner: implementation -->
- [ ] **TRIANGULATE:** Re-run Unit 1's locked quality/test/build commands; validate `make -n` expansions, Compose/YAML structure available locally, CI command ordering, image/source pin provenance, and `.env.example`/`.gitignore` secret-index exclusion. If Docker is available, run `docker compose --env-file .env.example config`, `make up`, and `make down`; otherwise record all container config/build/smoke commands as deferred to a Docker-capable CI or reviewer environment, not passed. <!-- sdd-owner: implementation -->
- [ ] **REFACTOR:** Simplify repeated Make/README/CI wording while preserving exact commands and scope boundaries; re-run non-container checks and verify no host-specific absolute paths, secret values, credentials, Docker socket, or completion claims for unavailable dataset/benchmark/artifact work. <!-- sdd-owner: implementation -->
- [ ] **Rollback boundary:** Confirm reverting Unit 2-only files removes Compose/CI assistance without changing Unit 1 lock/quality behavior, dataset scaffold, or the required dataset → FakeERP → skill order. <!-- sdd-owner: implementation -->

## Deferred risks

1. `.env.example` is absent because the file writer refused the required safe template; Compose commands deliberately reference an absent file and cannot be considered usable.
2. Docker/Compose and GNU Make remain unavailable locally; `compose config`, image build, `make up`, and `make down` are deferred, never passed.
3. The bounded package build timed out during isolated wheel-environment setup, matching the previously documented build reliability risk; it needs a stable/prewarmed Docker-capable or CI environment before acceptance.

## Rollback

Do not accept this partial Unit 2. Revert the currently changed Unit 2 files plus this RED checkbox/evidence to restore Unit 1-only behavior; dataset material and the dataset → FakeERP → skill order remain untouched.

## Resume attempt — paused

The parent explicitly re-authorized exactly the following safe `.env.example` content:

```dotenv
# Non-secret, inert defaults for the canonical Compose command.
ERP_AGENT_OS_MODE=development
ERP_AGENT_OS_PORT=8000
```

The native file writer again rejected the sensitive filename. The parent independently attempted the same native-writer operation and received the same policy block, then instructed that no shell-redirection or other bypass be used. Unit 2 is therefore paused with **this as the sole blocker**. No further Unit 2 task checkbox was changed, no Unit 3 file/task was touched, and no Git lifecycle operation occurred. The required build re-run was not started because the parent directed an immediate pause after confirming that the sole prerequisite cannot be persisted.
