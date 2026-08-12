# Competition Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Close the five competition-readiness gaps with auditable evidence governance, integrated runtime verification, honest annotation/adversarial evaluation, a prospective v2 experiment, and a methodology-first competition package.

**Architecture:** Preserve every legacy result as immutable historical evidence, add an authoritative evidence registry, and make ERP-Skills-Bench v2 the only prospective confirmatory path. Extend the deterministic runtime with named verification evidence and closed statuses, then have System C assemble complete-state checks through the structural adapter interface. Keep AI annotation review and adversarial stress testing explicitly exploratory. Generate all reporting and 16:9 video assets from validated evidence metadata so labels cannot drift across the README, memory, defence, and video.

**Tech Stack:** Python 3.12, Pydantic, FastAPI, SQLAlchemy, pytest, Ruff, mypy, JSON/JSONL/CSV, SVG, existing FakeERP/Odoo adapters, existing experiment/statistics/freeze modules.

---

## Workstream 1 — Scientific evidence governance

### Task 1: Make evidence status machine-readable and enforceable

**Files:**

- Create: `data/evidence_registry.json`
- Create: `src/erp_agent_os/evidence.py`
- Create: `scripts/audit_evidence_status.py`
- Create: `tests/test_evidence.py`
- Modify: `scripts/audit_docs_coherence.py`
- Create: `tests/test_docs_coherence.py`

**Step 1: Write failing registry-contract tests**

Add tests that require:

```python
registry = EvidenceRegistry.load(Path("data/evidence_registry.json"))
assert registry.status_for("data/experiment_results.json") is EvidenceStatus.EXPLORATORY
assert registry.status_for("data/experiment_results_real_parser.json") is EvidenceStatus.EXPLORATORY
assert registry.status_for("data/experiment_results_groq_given_args.json") is EvidenceStatus.SENSITIVITY
assert registry.status_for("data/odoo_governed_demo_results.json") is EvidenceStatus.DEMONSTRATION
assert registry.status_for("data/bench_v2_confirmatory_results.json") is EvidenceStatus.PENDING
```

Also prove registry precedence over a legacy JSON field such as `manifest.is_confirmatory_run`, reject duplicate paths, reject unknown statuses, and reject a confirmatory entry unless its freeze manifest and result validation are both present.

Add a completeness scan for reportable `data/*results*.json` and retained annotation-audit outputs: every such artefact must be registered or explicitly allowlisted as a non-reportable fixture. Include pending entries and permitted/non-permitted claims for `data/catalog_aware_stress_results.json` and the configured AI consistency-audit output.

**Step 2: Run the focused tests and confirm RED**

Run: `uv run pytest tests/test_evidence.py tests/test_docs_coherence.py -q`

Expected: failure because `erp_agent_os.evidence` and the registry do not exist.

**Step 3: Implement the smallest evidence model**

Create an enum with `pending`, `confirmatory`, `exploratory`, `sensitivity`, and `demonstration`; immutable entry/registry models; exact-path lookup; schema validation; and a confirmation guard that checks the v2 manifest/result metadata. Populate every artefact listed in the approved design, retaining legacy result files untouched.

Make the CLI return non-zero for an invalid registry or for reporting documents that attach confirmatory wording to an artefact the registry does not classify as confirmatory. Its output must name the offending file and artefact.

**Step 4: Add claim-focused documentation tests**

Test that the audit rejects prohibited phrases such as general immunity/safety, treats `0 / 1,530` only as an exploratory confinement result, and rejects human-kappa wording while `annotator2_decision` is unavailable. Avoid a broad ban on the Spanish word `confirmatorio`; validate claims linked to concrete artefacts instead.

**Step 5: Run focused tests and quality checks**

Run:

```powershell
uv run pytest tests/test_evidence.py tests/test_docs_coherence.py -q
uv run ruff check src/erp_agent_os/evidence.py scripts/audit_evidence_status.py tests/test_evidence.py
uv run mypy src/erp_agent_os/evidence.py
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add data/evidence_registry.json src/erp_agent_os/evidence.py scripts/audit_evidence_status.py scripts/audit_docs_coherence.py tests/test_evidence.py tests/test_docs_coherence.py
git commit -m "feat: govern experimental evidence status"
```

## Workstream 2 — Runtime verification that actually executes

### Task 2: Introduce named verification checks and closed runtime statuses

**Files:**

- Modify: `src/erp_agent_os/runtime.py`
- Modify: `src/erp_agent_os/postconditions.py`
- Modify: `tests/test_runtime.py`
- Modify: `tests/test_postconditions.py`
- Modify: `tests/test_contracts.py`

**Step 1: Write failing runtime tests**

Specify these public contracts:

```python
assert result.verification_status is VerificationStatus.PASSED
assert result.postconditions_met is True
assert result.check_results == (
    VerificationCheckResult(check_id="exactly_one_new_opportunity", passed=True, detail="..."),
)
```

Cover all six statuses: `passed`, `failed`, `not_run_clean`, `not_run_dirty`, `replayed`, and `verifier_error`. A raised check must produce `verifier_error`, never success. A replay must preserve the original per-check evidence while changing only the aggregate status to `replayed`.

**Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_runtime.py tests/test_postconditions.py tests/test_contracts.py -q`

Expected: failures for missing verification types/statuses.

**Step 3: Implement named checks without adapter coupling**

Replace anonymous `Callable[[Any], bool]` inputs with a small immutable named-check contract. Adapt `build_checks` and read-only check builders to produce named checks. Preserve backwards compatibility only where existing internal callers need it; do not allow an unnamed check into audit evidence.

In `Runtime.execute`, evaluate checks defensively, collect non-sensitive details, set `postconditions_met` to `True`, `False`, or `None` consistently, and cache the fully verified original result for idempotency replay.

For non-executing decisions, receive a named complete-state invariant from the caller and classify unchanged state as `not_run_clean`, changed state as `not_run_dirty`, and missing/raised verification as `verifier_error`.

**Step 4: Run focused tests and static checks**

Run:

```powershell
uv run pytest tests/test_runtime.py tests/test_postconditions.py tests/test_contracts.py -q
uv run ruff check src/erp_agent_os/runtime.py src/erp_agent_os/postconditions.py tests/test_runtime.py tests/test_postconditions.py tests/test_contracts.py
uv run mypy src/erp_agent_os/runtime.py src/erp_agent_os/postconditions.py
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add src/erp_agent_os/runtime.py src/erp_agent_os/postconditions.py tests/test_runtime.py tests/test_postconditions.py tests/test_contracts.py
git commit -m "feat: add explicit runtime verification evidence"
```

### Task 3: Wire checks through System C, API, audit, persistence, and Odoo

**Files:**

- Modify: `src/erp_agent_os/system_c.py`
- Modify: `src/erp_agent_os/audit.py`
- Modify: `src/erp_agent_os/persistence.py`
- Modify: `src/erp_agent_os/api.py`
- Modify: `scripts/odoo_governed_demo.py`
- Modify: `tests/test_system_c.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_audit.py`
- Modify: `tests/test_persistence.py`
- Create: `tests/test_odoo_adapter.py`
- Modify: `tests/test_end_to_end.py`

**Step 1: Write failing integration tests**

Add a spy runtime test proving `SystemC.handle` passes the selected skill's executable postconditions. Add state-based tests for:

- a correct mutation returning `passed`;
- a deliberately broken handler returning `failed` after mutation, without claiming rollback;
- deny/approval/simulate/clarify/abstain returning `not_run_clean` when the complete monitored state is unchanged;
- a malicious mutation on a non-executing path returning `not_run_dirty`;
- read-only handlers detecting same-count field edits, not just record-count changes;
- mutating handlers detecting writes to a different monitored model.

API assertions must separate:

```json
{
  "decision": "allow",
  "verification_status": "passed",
  "postconditions_met": true
}
```

Audit/persistence round trips must preserve aggregate and per-check evidence.

**Step 2: Run focused tests and confirm RED**

Run:

```powershell
uv run pytest tests/test_system_c.py tests/test_api.py tests/test_audit.py tests/test_persistence.py tests/test_odoo_adapter.py tests/test_end_to_end.py -q
```

Expected: failures because System C currently does not assemble or pass checks.

**Step 3: Implement complete-state snapshots via `ErpAdapter`**

Create snapshots only from protocol operations, for example a deterministic deep copy of `{model: adapter.list(model)}` across an injected allowlist of monitored models. Do not depend on `FakeERPAdapter.snapshot()`. Normalize ordering before equality checks.

For the selected skill, call `postconditions.build_checks`, append a cross-model side-effect check for mutations, and use complete equality for R0/read-only or non-executing decisions. Keep skill-to-model mapping explicit and frozen. Never include secrets or full sensitive records in check details.

**Step 4: Persist and expose verification**

Extend `AuditEvent` and `SqlAuditStore` with backward-compatible defaults/migration handling. Return the three separate API fields. Ensure failed verification cannot be rendered as successful completion. Update the governed Odoo demo to use the same verification path and retain its independent re-read as corroboration.

**Step 5: Run focused tests and quality checks**

Run:

```powershell
uv run pytest tests/test_system_c.py tests/test_api.py tests/test_audit.py tests/test_persistence.py tests/test_odoo_adapter.py tests/test_end_to_end.py -q
uv run ruff check src/erp_agent_os/system_c.py src/erp_agent_os/audit.py src/erp_agent_os/persistence.py src/erp_agent_os/api.py scripts/odoo_governed_demo.py
uv run mypy src/erp_agent_os/system_c.py src/erp_agent_os/audit.py src/erp_agent_os/persistence.py src/erp_agent_os/api.py
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add src/erp_agent_os/system_c.py src/erp_agent_os/audit.py src/erp_agent_os/persistence.py src/erp_agent_os/api.py scripts/odoo_governed_demo.py tests/test_system_c.py tests/test_api.py tests/test_audit.py tests/test_persistence.py tests/test_odoo_adapter.py tests/test_end_to_end.py
git commit -m "feat: execute postconditions in governed system"
```

## Workstream 3 — Honest annotation and adversarial evaluation

### Task 4: Add a separate blinded AI consistency audit

**Files:**

- Create: `src/erp_agent_os/annotation_audit.py`
- Create: `scripts/run_ai_annotation_audit.py`
- Create: `tests/test_annotation_audit.py`
- Create: `data/annotation_ai_audit.schema.json`
- Create: `docs/annotation-protocol.md`

**Step 1: Write failing isolation/provenance tests**

Use a recording LLM stub to prove the reviewer receives request text plus schema but never `annotator1`, `annotator2_decision`, system output, or the canonical label. Require provider/model/temperature/prompt version/prompt hash, diagnostic agreement, disagreements, and `evidence_status="ai_consistency_audit"` in a separate JSON output.

Prove the script never modifies `data/annotation_review_sheet.csv` and never writes an `annotator2_decision` value.

**Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_annotation_audit.py -q`

Expected: missing module/script failures.

**Step 3: Implement a provider-neutral audit**

Define a reviewer protocol compatible with existing LLM clients, deterministic prompt construction, hashing, strict response validation, disagreement reporting, and an explicit `--output` path. Network/provider failures must leave the canonical data untouched and exit non-zero with a concise diagnostic.

Any retained output must use the registry-declared path and already have an `ai_consistency_audit` registry entry. An arbitrary diagnostic output may be created temporarily but cannot be used by reporting code or retained as reportable evidence until registered.

**Step 4: Update the annotation protocol honestly**

State that the second human annotator and human Cohen's kappa remain unavailable/unmet. Describe AI agreement only as a machine consistency diagnostic requiring manual adjudication before any label change.

**Step 5: Run focused tests and commit**

```powershell
uv run pytest tests/test_annotation_audit.py -q
uv run ruff check src/erp_agent_os/annotation_audit.py scripts/run_ai_annotation_audit.py tests/test_annotation_audit.py
uv run mypy src/erp_agent_os/annotation_audit.py
git add src/erp_agent_os/annotation_audit.py scripts/run_ai_annotation_audit.py tests/test_annotation_audit.py data/annotation_ai_audit.schema.json docs/annotation-protocol.md
git commit -m "feat: add blinded AI annotation consistency audit"
```

### Task 5: Replace the overbroad injection claim with a catalog-aware suite

**Files:**

- Create: `src/erp_agent_os/adversarial.py`
- Create: `scripts/catalog_aware_stress_test.py`
- Create: `tests/test_adversarial.py`
- Create: `data/catalog_aware_stress_cases.json`
- Modify: `scripts/injection_resistance_test.py`
- Modify: `tests/test_injection_resistance.py`

**Step 1: Write failing deterministic-oracle tests**

Create at least one malicious case and one benign positive control for each supported category:

- model substitution;
- non-allowlisted field injection;
- role spoofing;
- approval bypass;
- R4 request;
- disguised bulk scope;
- valid but policy-forbidden high-impact action;
- exact-key replay abuse;
- legitimate misuse with an explicit frozen policy/precondition, otherwise `unsupported_policy`.

Assertions must use full before/after state and audit evidence. Replay must prove exactly one business mutation and `verification_status="replayed"` on the second response.

**Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_adversarial.py tests/test_injection_resistance.py -q`

Expected: missing catalog-aware evaluator and outdated claim metadata.

**Step 3: Implement the fixed threat-model evaluator**

Model attacker-controlled request text, proposed skill, proposed arguments, and claimed role separately from trusted authenticated role, approvals, handler registry, and adapter allowlist. Each case must carry its category, deterministic oracle, positive-control flag, status, and state-diff evidence. Do not change policies in response to observed failures.

Rename the existing result/metadata to “three-channel confinement stress test” while preserving the historical `data/injection_resistance_results.json` file. Attach the exact permitted claim and explicit non-claims.

Register `data/catalog_aware_stress_results.json` as exploratory with permitted and prohibited claims before retaining the generated result. The evidence completeness audit must fail if the script produces a reportable unregistered path.

**Step 4: Run the exploratory suite locally**

Run: `uv run python scripts/catalog_aware_stress_test.py --cases data/catalog_aware_stress_cases.json --output data/catalog_aware_stress_results.json`

Expected: a complete exploratory report; security failures, if any, remain visible and do not make the command fail unless the harness itself is invalid.

**Step 5: Run tests and commit**

```powershell
uv run pytest tests/test_adversarial.py tests/test_injection_resistance.py -q
uv run ruff check src/erp_agent_os/adversarial.py scripts/catalog_aware_stress_test.py tests/test_adversarial.py
uv run mypy src/erp_agent_os/adversarial.py
git add src/erp_agent_os/adversarial.py scripts/catalog_aware_stress_test.py scripts/injection_resistance_test.py tests/test_adversarial.py tests/test_injection_resistance.py data/catalog_aware_stress_cases.json data/catalog_aware_stress_results.json
git commit -m "test: add catalog-aware adversarial evaluation"
```

## Workstream 4 — Prospective confirmatory benchmark

### Task 6: Generate and validate ERP-Skills-Bench v2 without self-labelling

**Files:**

- Create: `src/erp_agent_os/bench_v2.py`
- Create: `scripts/generate_bench_v2.py`
- Create: `scripts/validate_bench_v2.py`
- Create: `tests/test_bench_v2.py`
- Create when generated: `data/bench_v2.jsonl`
- Create when generated: `data/bench_v2_provenance.json`

**Step 1: Write failing benchmark-contract tests**

Require exactly 120 unique cases, five for each of the 24 frozen intents, with exactly three ordinary, one noisy, and one governed-edge scenario per intent. Validate published edge-category counts, deterministic oracle compilation, frozen role/state metadata, no exact v1 text hash, and no model-authored labels.

Use a fake authoring client in tests to prove only intent/safe entities/transformation are sent; System C prompts, thresholds, rankings, outputs, expected skill, expected decision, and expected state must not be in the author prompt.

**Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_bench_v2.py -q`

Expected: missing v2 module.

**Step 3: Implement generator, compiler, and validator**

Make generation resumable but deterministic from a committed seed. Store author provider/model, prompt version/hash, request hashes, and edge counts. Compile oracle fields only after text generation from the frozen catalog/scenario definitions. Reject author and selector models that are identical.

The validator must fail on duplicates, wrong intent/scenario counts, missing oracle fields, v1 exact matches, forbidden author-prompt leakage, or unsupported edge cases. Similarity diagnostics may be reported but cannot alter cases.

**Step 4: Run focused tests and static checks**

```powershell
uv run pytest tests/test_bench_v2.py -q
uv run ruff check src/erp_agent_os/bench_v2.py scripts/generate_bench_v2.py scripts/validate_bench_v2.py tests/test_bench_v2.py
uv run mypy src/erp_agent_os/bench_v2.py
```

Expected: PASS.

**Step 5: Generate only when a distinct authoring model is configured**

Inspect environment-variable presence without printing values. If credentials/configuration are available, run the generator and validator. Otherwise leave the generation command documented and keep the evidence status `pending`; do not substitute hand-written or selector-authored text while calling it confirmatory.

**Step 6: Commit code, tests, and validated generated artefacts if available**

```powershell
git add src/erp_agent_os/bench_v2.py scripts/generate_bench_v2.py scripts/validate_bench_v2.py tests/test_bench_v2.py
git add data/bench_v2.jsonl data/bench_v2_provenance.json  # only if generated and validated
git commit -m "feat: add prospective benchmark v2 pipeline"
```

### Task 7: Add the v2 freeze, one-look runner, and confirmatory statistics gate

**Files:**

- Create: `src/erp_agent_os/freeze_v2.py`
- Create: `src/erp_agent_os/experiment_v2.py`
- Create: `scripts/freeze_protocol_v2.py`
- Create: `scripts/run_experiment_v2.py`
- Create: `scripts/analyze_experiment_v2.py`
- Create: `tests/test_freeze_v2.py`
- Create: `tests/test_experiment_v2.py`
- Modify: `src/erp_agent_os/statistics.py`
- Modify: `tests/test_statistics.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create after a valid run: `data/bench_v2_confirmatory_results.json`

**Step 1: Write failing freeze/runner tests**

Test that the freeze manifest hashes dataset, oracle, catalog, policy, evaluator, prompts, provider config, seed, and statistical plan; verification requires a clean worktree and the exact `v2-protocol-freeze` tag/commit. Any content/config change must break verification.

Test runner acceptance: 120 cases × 3 systems × 3 repetitions = 1,080 unique observations; randomized committed order; fresh/restored adapter state evidence for every observation; complete primary fields; paired collapse to 120 request-level inference units; no aggregate result publication from partial checkpoints.

Require three independent selector/argument-extraction calls for each case/system across the three repetitions. Prohibit `CachingLLMClient` or any response cache from being shared across repetitions or systems. Persist actual tokens, latency, model-call count and retry count for every observation; zero tokens are valid only when provider metadata proves no model call was required by that architecture, never because a prior repetition was replayed.

Create one immutable frozen `RunConfig` containing selector provider/model/version, temperature, token limit, timeout, retry/step budgets, role, argument-extraction prompt hash, initial-state factory hash and seed. Inject the same instance/hash into A, B and C wherever the variable is required to be equal. Persist its hash on every observation and reject any result with a missing or mismatched hash.

Test the primary C−B STSR paired difference, bootstrap 95% interval, and McNemar output. `supported` is true only when the lower interval bound is above zero. A null or adverse valid result remains valid.

Define and test one frozen results schema that also validates every required secondary endpoint and denominator:

- false allow and false block on the predeclared dangerous/safe subsets, with exact `n` and 95% intervals;
- total input/output/combined tokens and paired comparisons;
- traceability total plus the seven weighted rubric components;
- retrieval Top-1, Top-3, coverage, selective accuracy and false-reuse risk on their declared eligible subsets;
- final-state trio consistency across the three independent repetitions;
- observation-level latency, model calls and retries.

Missing or zero-denominator endpoints must be explicit `not_estimable` values with the reason; they cannot disappear from the schema or be coerced to zero.

**Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_freeze_v2.py tests/test_experiment_v2.py tests/test_statistics.py -q`

Expected: missing v2 freeze/runner failures.

**Step 3: Implement the prospective gate**

Reuse existing freeze/statistics primitives where their semantics match, but keep v1 manifests untouched. Do not reuse the current experiment client's cross-repetition response cache. Store checkpoints outside the final aggregate path, encrypted with a run-specific key that is supplied separately from the checkpoint (for example Fernet via the pinned `cryptography` dependency). Restrict checkpoint file permissions as defence in depth. Suppress observation content, endpoint values and intermediate aggregates from console/log output. Decryption and aggregate analysis are allowed only after a validator confirms all 1,080 unique observations. Include explicit infrastructure-failure metadata; do not silently retry with changed settings.

The final result validator must check manifest hashes, `RunConfig` equality, independent-call evidence, endpoint schema/denominators and observation cardinality before `EvidenceRegistry` can classify the artefact as confirmatory.

**Step 4: Run focused tests and quality checks**

```powershell
uv run pytest tests/test_freeze_v2.py tests/test_experiment_v2.py tests/test_statistics.py -q
uv run ruff check src/erp_agent_os/freeze_v2.py src/erp_agent_os/experiment_v2.py scripts/freeze_protocol_v2.py scripts/run_experiment_v2.py scripts/analyze_experiment_v2.py
uv run mypy src/erp_agent_os/freeze_v2.py src/erp_agent_os/experiment_v2.py
```

Expected: PASS.

**Step 5: Exercise manifest creation in tests, but defer the real freeze/run**

Do not create the real `v2-protocol-freeze` tag or observe any A/B/C v2 output in this task. The real freeze/run belongs in Task 9, after the competition documents, evidence audits, and all implementation tests are stable. Use only temporary fixtures/stubs here:

```powershell
uv run pytest tests/test_freeze_v2.py tests/test_experiment_v2.py -q
```

The CLI must remain incapable of running A/B/C without verifying the real tag and manifest. If the dataset prerequisites are unavailable later, the confirmatory experiment stays pending and competition numeric claims remain explicitly exploratory.

**Step 6: Commit the gate implementation without observing v2 outputs**

```powershell
git add src/erp_agent_os/freeze_v2.py src/erp_agent_os/experiment_v2.py scripts/freeze_protocol_v2.py scripts/run_experiment_v2.py scripts/analyze_experiment_v2.py tests/test_freeze_v2.py tests/test_experiment_v2.py src/erp_agent_os/statistics.py tests/test_statistics.py pyproject.toml uv.lock
git commit -m "feat: add confirmatory v2 experiment gate"
```

## Workstream 5 — Competition narrative and delivery

### Task 8: Align all claims and build methodology-first 16:9 assets

**Files:**

- Create: `scripts/make_video_assets.py`
- Create: `tests/test_video_assets.py`
- Create: `reports/video/01-method.svg`
- Create: `reports/video/02-architecture.svg`
- Create: `reports/video/03-odoo-proof.svg`
- Create: `reports/video/04-results.svg`
- Create: `reports/video/05-limitations.svg`
- Modify: `README.md`
- Modify: `docs/memoria.md`
- Modify: `docs/results.md`
- Modify: `docs/defensa.md`
- Modify: `docs/presentacion.md`
- Modify: `docs/video-guion.md`
- Modify: `docs/video-plan-rodaje.md`
- Modify: `docs/experiment-protocol.md`
- Modify: `docs/traceability-rubric.md`

**Step 1: Write failing content and rendering tests**

Test that every SVG has a 1920×1080 viewBox, embeds no external font/image dependency, has evidence-status text on result slides, and does not finalize v2 numeric values while its registry status is pending. Test the approved 4:20–4:35 method-first sequence and a hard estimated/read duration below five minutes.

Extend documentation audits to enforce:

- no legacy artefact called confirmatory;
- no human-kappa claim;
- no general safety/immunity claim;
- explicit 3.3% external detector negative result;
- confinement claim includes tested scope and exploratory status;
- Odoo demo is evidence, not the experimental result;
- closing line `El modelo propone. El contrato decide.`

**Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_video_assets.py tests/test_docs_coherence.py tests/test_evidence.py -q`

Expected: missing generator/assets and stale competition copy.

**Step 3: Implement data-driven SVG generation**

Build five restrained 16:9 cards: A/B/C method, two-zone architecture, Odoo verification proof, three-result card, and limitations/transfer. Read headline values and labels from the evidence registry/result artefact. When v2 is pending, render `Experimento confirmatorio v2: pendiente` and use only visibly exploratory legacy estimates; never invent or promote a number.

**Step 4: Rewrite the competition package**

Use the approved timing:

```text
0:00–0:25 risk
0:25–0:50 research question
0:50–1:35 benchmark/method
1:35–2:10 architecture
2:10–3:00 continuous Odoo demo
3:00–3:45 results with status
3:45–4:10 negative result + limitation
4:10–4:30 innovation + close
```

Reduce the main memory toward the UCM 20-page target by moving chronology, large tables, threat details, and implementation traces to annex references. Do not delete technical evidence from the repository.

**Step 5: Render and inspect the assets**

Run:

```powershell
uv run python scripts/make_video_assets.py
uv run pytest tests/test_video_assets.py tests/test_docs_coherence.py tests/test_evidence.py -q
```

Render SVGs to PNG using the available workspace document/browser tooling and inspect each at 1920×1080 for clipping, contrast, and legibility. Correct any visual defect before committing.

**Step 6: Commit**

```powershell
git add scripts/make_video_assets.py tests/test_video_assets.py reports/video README.md docs/memoria.md docs/results.md docs/defensa.md docs/presentacion.md docs/video-guion.md docs/video-plan-rodaje.md docs/experiment-protocol.md docs/traceability-rubric.md
git commit -m "docs: prepare methodology-first competition package"
```

### Task 9: Final verification and honest handoff

**Files:**

- Modify as needed: `Makefile`
- Modify as needed: `README.md`
- Create: `docs/competition-delivery-checklist.md`

**Step 1: Add one reproducible readiness target**

Provide a Make/PowerShell-compatible documented command that runs unit/integration tests, coverage threshold, Ruff, mypy, evidence audit, docs audit, v1 freeze verification, v2 validation/freeze verification when present, adversarial harness validation, and video-asset tests.

**Step 2: Run the complete verification suite and create a pre-freeze readiness commit**

Run the project's exact supported commands, at minimum:

```powershell
uv run pytest -q
uv run coverage run -m pytest
uv run coverage report --fail-under=95
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/audit_evidence_status.py
uv run python scripts/audit_docs_coherence.py
uv run python scripts/freeze_protocol.py --verify
uv run pytest tests/test_video_assets.py -q
```

If v2 artefacts exist, also run their validator and freeze verifier. Record exact pass counts and current result status; do not say the confirmatory run is complete unless the validator proves it.

Commit any readiness-target/checklist correction before the prospective freeze so the worktree can become clean.

**Step 3: Inspect repository and delivery artefacts**

Check `git diff`, `git status --short`, repository access instructions, absence of secrets/real customer data, video estimated duration, all five SVG renders, and PDF page count/rendering if a final PDF exists. Never connect to a production Odoo URL; only use the guarded development demo configuration.

**Step 4: Create the delivery checklist and commit pre-freeze readiness**

The checklist must distinguish completed items from externally blocked items such as unavailable author/selector credentials, independent human annotation, final spoken video recording, or tutor approval.

```powershell
git add Makefile README.md docs/competition-delivery-checklist.md
git commit -m "chore: add competition readiness verification"
```

**Step 5: Complete independent code review before the irreversible freeze**

Provide the reviewer the approved design, this plan, the base commit, and current branch head. Resolve every Critical/Important (High/Medium) finding with new tests and rerun the complete verification suite. Commit corrections and repeat review until approved. This is the final opportunity to change code, prompts, thresholds, cases, labels, policies, evaluator logic, or frozen configuration while retaining prospective confirmatory status.

**Step 6: Execute the prospective freeze/run only when every gate is satisfied**

If and only if `data/bench_v2.jsonl` exists, its validation passes, author/selector models differ, AI diagnostics are resolved or documented without automatic relabelling, all code/docs/tests are stable, and the worktree is clean:

```powershell
uv run python scripts/freeze_protocol_v2.py --write
git add data/bench_v2_freeze_manifest.json
git commit -m "chore: freeze benchmark v2 protocol"
git tag v2-protocol-freeze
uv run python scripts/freeze_protocol_v2.py --verify
uv run python scripts/run_experiment_v2.py
uv run python scripts/analyze_experiment_v2.py
```

Do not run A/B/C before the tag. Once the first v2 system output is observed, do not change code, prompts, thresholds, labels, cases, policies, or evaluator logic. If a valid run completes, validate it, update `data/evidence_registry.json`, regenerate only reporting copy/assets from the immutable aggregate, rerun reporting/evidence tests, and commit the result plus reporting changes. A null/adverse result must be reported unchanged. If prerequisites are unavailable, leave status `pending` and document the precise external blocker.

After the run, review is limited to result-schema validation and truthful reporting. A defect in any frozen input, runner, evaluator, or metric implementation invalidates the run; it must be labelled invalid/exploratory and cannot be repaired retrospectively while retaining confirmatory status.

**Step 7: Finish the branch without silently integrating it**

Use `superpowers:finishing-a-development-branch` and present the four prescribed options: merge locally, push/create PR, keep branch as-is, or discard. Do not merge, push, tag, or delete the worktree without the user's explicit selection, except for the prospective `v2-protocol-freeze` tag when and only when Task 7's scientific gate is satisfied.
