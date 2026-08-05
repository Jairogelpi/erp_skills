# ERP Agent OS (`erp_skills`)

> **Foundation status:** this repository currently provides a deterministic Python
> quality baseline and its existing synthetic dataset scaffold. FakeERP, skills,
> and the application runtime are **not delivered**. After the dataset work,
> FakeERP remains the next required implementation step before any skill contract.

The public repository identity is **`erp_skills`**; the Python distribution name is
**`erp-agent-os`**. Committed material is synthetic-only: do not add private data,
real ERP credentials, tokens, secrets, or local environment files.

## Prerequisites

- CPython 3.12 (supported range: `>=3.12,<3.13`)
- [uv](https://docs.astral.sh/uv/) to install the reviewed lock and run tools
- A POSIX-compatible shell and GNU-compatible `make` for the Make targets below
  (on Windows, use a compatible shell/Make or run the shown `uv run` command).
- Docker Engine with Docker Compose v2 for the optional container workflow.

## Reproducible local workflow

Use the committed lock; do not replace it with an ad-hoc, unpinned install:

```sh
uv lock --check
uv sync --frozen --group dev
```

`uv sync --frozen --group dev` fails if the lock and metadata disagree rather than
silently resolving a different dependency set. To update tooling intentionally,
change an explicitly pinned declaration in `pyproject.toml`, regenerate `uv.lock`
with uv, review its resolved versions and artifact hashes, then rerun every check.
No normal setup path uses `latest`.

## Quality commands

```sh
make format        # Ruff applies formatting
make format-check  # Ruff verifies formatting
make lint          # Ruff lints
make typecheck     # mypy performs static type checking only
make test          # pytest runs tests
make coverage      # pytest reports package coverage
make build         # builds the distribution
```

Ruff is the repository formatter and linter. mypy is used only for static type
checking; it is not a formatter. Generated environments, caches, coverage, build
outputs, real `.env` files, credentials, and local MCP state are ignored by policy.
Ignore rules prevent ordinary accidental inclusion but do not remove a secret already
tracked elsewhere.

## Container first-clone workflow

After the locked local setup, a Docker-capable environment can use the canonical,
repository-relative Compose path:

```sh
make compose-config
make up
make logs
make down
```

`make up` runs `docker compose --env-file config/development.defaults up --build`.
The repository-relative `config/development.defaults` contains only the inert defaults
`ERP_AGENT_OS_MODE=development` and `ERP_AGENT_OS_PORT=8000`; it needs no
host-specific path, real `.env`, or secret. The development container runs a bounded
readiness message, not an application server. It uses
`python:3.12-slim@sha256:9e869b0816f5537709825b49e62dc86d1c2691eff19b05c1d4dc3a07992cc052`
(tag/digest retrieved 2026-08-05). Verify the source pin with
`docker buildx imagetools inspect python:3.12-slim`.

Docker Compose and GNU Make are unavailable on this workstation, so Compose
configuration, image build, `make up`, and `make down` are deferred to a
Docker-capable CI or reviewer environment; they are not locally passed.

## CI scope

The Linux Python 3.12 workflow installs pinned `uv` via immutable
`astral-sh/setup-uv` revision
`d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` (v5.4.2), validates the committed lock,
and runs only the implemented formatting, lint, type-check, coverage, and build
commands. Dataset validation, benchmark smoke, and artifact production remain
additive CLAUDE.md §29 checks and are not claimed as complete.

## Releases

Pushing a semantic version tag such as `v0.1.0` runs the same locked Python 3.12
quality, test, and build checks as CI. On success, GitHub creates a release for
that tag and attaches the wheel and source distribution from `dist/`; it does not
publish to PyPI or a container registry.

## Optional developer assistance

[Ponytail](.ponytail/UPSTREAM.md) is vendored with immutable provenance and a
SHA-256 manifest. Optional Codebase Memory MCP setup is documented in
[development assistance](docs/development-assistance.md). It is local,
token-free, read-mostly assistance—not an application runtime dependency—and
cannot be enabled until this checkout has Git initialized.

## Scope and portability

This Unit 2 foundation is portable across supported Python 3.12 environments with
uv. The Make targets need a POSIX-compatible shell/Make; native Windows Make is not
claimed without validation. This unit neither initializes Git nor commits, publishes,
configures remotes, or creates application capabilities. FakeERP, skills, and runtime
remain undelivered.
