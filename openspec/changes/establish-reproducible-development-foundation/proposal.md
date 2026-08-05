# Proposal: Establish reproducible development foundation

## Intent

Establish a small, portable, security-bounded developer foundation for **ERP Agent OS** before the already-planned `FakeERPAdapter` work. The foundation makes first-clone setup and quality checks reproducible without claiming that FakeERP, the skill contract, runtime, or any ERP behavior exists or is complete.

The public repository identity will be `https://github.com/Jairogelpi/erp_skills`; its GitHub repository name remains `erp_skills`, while the Python distribution remains `erp-agent-os`.

## Governing requirements

- `CLAUDE.md` §27 requires Python quality tooling plus Docker, Docker Compose, GitHub Actions, Makefile, and `.env.example`.
- `CLAUDE.md` §29 requires lint, static type checking, tests, coverage, build, dataset validation, smoke benchmark, and artifacts in CI; Ruff and mypy retain their distinct roles.
- `CLAUDE.md` §35 requires a repository that starts from zero, green CI, reproducibility, and no sensitive data.
- `CLAUDE.md` §42 mandates the construction order `dataset → FakeERP → skill contract`; this foundation is enabling infrastructure and must precede, not substitute for, the pending FakeERP unit.
- `docs/roadmap.md` P2.4 requires pinned versions, seeds/configuration/execution artifacts, and synthetic-data policy. P7.1–P7.5 require the reproducible toolchain, Ruff, mypy, CI, from-zero documentation, and data-sensitivity review.

## Scope

Deliver the foundation as these **three sequential OpenSpec implementation units**, each independently reviewed and forecast below 400 changed lines:

1. **Unit 1 — Python project and deterministic quality baseline**
   - Establish Python 3.12 project metadata for distribution `erp-agent-os` and deterministic dependency locking.
   - Configure Ruff (format/lint) and mypy (static types), plus their documented local entry points.
   - Add a robust `.gitignore` that excludes virtual environments, caches, build outputs, local environment files, secrets, coverage, editor files, and generated local artifacts while preserving `.env.example`.
   - Add a README foundation: repository/distribution naming, prerequisites, supported local workflow, reproducibility expectations, and explicit status that FakeERP/skills/runtime are not delivered.
   - Forecast: at most 350 changed lines.

2. **Unit 2 — Containerized first-clone workflow and CI**
   - Add a canonical Docker Compose startup path exposed through a Makefile, Dockerfile(s) only as needed, and `.env.example` containing placeholders only.
   - Document portable first-clone setup and the supported Make targets; Docker Compose is canonical even though Docker is unavailable on the current workstation, so container smoke validation is deferred to a Docker-capable environment and recorded honestly.
   - Add GitHub Actions that runs the applicable deterministic checks: installation from the lock, Ruff format/lint, mypy, tests/coverage when present, package build, and only those dataset/smoke checks whose implementation exists. Future CI steps required by §29 remain additive and must not be falsely represented as complete before their components exist.
   - Forecast: at most 390 changed lines.

3. **Unit 3 — Project-local development assistance**
   - Vendor Ponytail as an attributed, project-local skill pinned to a verified upstream source revision.
   - Add repository-scoped Codebase Memory MCP configuration, documentation, and a bootstrap command that installs it locally; do not commit an executable/binary.
   - Restrict Codebase Memory MCP to this repository, read-only access, and no tokens/secrets. Document disable/removal and the fact that it is optional developer assistance, not an application runtime dependency.
   - Forecast: at most 350 changed lines.

Each unit must record exact source versions/digests or immutable revisions where available and provide a verification command or documented verification procedure. Dependency locks and vendored/upstream materials must be reviewable, attributable, and reproducible rather than relying on mutable `latest` references.

## Affected areas

- Project metadata, dependency lock, Python quality configuration, and ignore rules.
- `README.md` and developer-facing reproducibility/security documentation.
- Makefile, Docker/Compose, and `.env.example` for first-clone startup.
- GitHub Actions workflow(s).
- Project-local Ponytail skill and attribution/verification material.
- Repository-scoped Codebase Memory MCP config plus bootstrap and operating documentation.

## Boundaries and non-goals

- No FakeERP, skill schema/lifecycle, runtime, policy engine, API, database, benchmark population, retrieval, LLM integration, Odoo, dashboard, or experimental-system completion.
- No claim that §29's future dataset validation, benchmark smoke, or artifact production runs before those components exist.
- No Git initialization, commit, remote configuration, credential setup, or GitHub publication in this change. These are separate, user-authorized lifecycle actions after all three foundation units are accepted.
- No committed secrets, tokens, private data, real ERP credentials, generated binaries, globally installed MCP state, or repository-external write access.
- No guarantee that Docker executes on this workstation; portability is designed/documented here and container execution is validated where Docker is available.
- No change to the normative FakeERP-before-skill order in `CLAUDE.md` §42.

## Security and portability requirements

- `.env.example` contains non-secret placeholders only; real `.env` files remain ignored.
- Compose and Make targets must run without host-specific absolute paths and document supported prerequisites.
- The Codebase Memory MCP bootstrap must be explicit, opt-in, local to this checkout, read-only, token-free, and unable by configuration to operate on another repository.
- Ponytail and every nontrivial bootstrap dependency must name its upstream origin, license/attribution information where applicable, immutable pin, and verification method.
- The foundation must not download or execute unverified mutable upstream content as part of normal startup.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Docker cannot be exercised locally | Keep Compose canonical; validate syntax/local non-container targets here and record Docker smoke as deferred to a Docker-capable CI or reviewer environment. |
| Pinned tooling becomes stale | Pin immutable versions/revisions and make updates intentional, reviewed changes with re-verification. |
| MCP expands repository or data exposure | Repository-scoped read-only configuration, no tokens, opt-in bootstrap, and explicit disable/removal docs. |
| Vendored Ponytail obscures provenance or licensing | Attribute upstream, pin an immutable revision, include verification instructions, and preserve applicable license material. |
| Foundation scope accidentally implies implementation progress | README and every unit explicitly state that FakeERP, skills, and runtime remain pending; preserve the §42 sequence. |
| Three units exceed review budget | Treat each unit as a separate approved SDD change and split again before apply if its forecast exceeds 400 lines. |

## Rollback

The units are additive and independently reversible. Revert the accepted unit in reverse order: remove MCP/Ponytail integration first, then CI/container workflow, then project-quality baseline. Removing Codebase Memory MCP only removes optional developer assistance and must not affect the application. Do not remove the existing dataset scaffold or alter FakeERP/skill planning as part of rollback.

## Success criteria

1. A fresh clone has documented, portable, deterministic setup and a canonical `make`-driven Docker Compose startup path.
2. The repository uses a deterministic dependency lock; Ruff formatting/linting and mypy type checking are separately configured and invocable.
3. `.gitignore`, `.env.example`, documentation, Compose, and CI prevent ordinary leakage of secrets/local artifacts and make the no-sensitive-data boundary clear.
4. CI runs only implemented checks honestly, with expansion points aligned to `CLAUDE.md` §29.
5. Ponytail is project-local, attributed, upstream-pinned, and verifiable.
6. Codebase Memory MCP has a documented bootstrap command and repository-only, read-only, token-free configuration; no binary is committed.
7. All three units remain under 400 changed lines and are accepted before the separately authorized Git initialization and first public publication.
8. The repository continues to make no claim that FakeERP, skills, or runtime work is complete; subsequent implementation resumes with the already-planned FakeERP work in the required order.

## Proposal question round

The supplied decisions resolve the essential product choices for this proposal: public/repository/distribution naming, Compose-via-Make canonical startup, MCP security model, Ponytail provenance, three-unit delivery sequence, and a separate publication boundary. Before implementation, the user may correct these assumptions or request a second product-question round focused on: (1) which developer operating systems must be explicitly supported in the first-clone guide; (2) whether CI must validate only Linux initially or also other runners; (3) the acceptable upstream/license policy for Ponytail; and (4) whether the first public release needs a license/CITATION decision as a separate lifecycle action. These are proposal-level scope clarifications, not authorization to begin the next SDD phase.

## Next dependency

After this proposal is reviewed and approved, proceed only to this change's specification phase. After all three foundation implementation units are accepted and the user separately authorizes publication, resume the existing FakeERP work before any skill-contract, runtime, or generic FakeERP-adjacent expansion.
