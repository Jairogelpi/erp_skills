# Experimental Evidence Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve inspectable future experiment observations, correct the analysis population, complete the automatable H6/H7 evidence, publish observed benchmark states without claiming they are ground truth, and document every hypothesis and defensible thesis.

**Architecture:** Add lossless, atomic, content-addressed JSONL archives for future runs. Historical summaries remain aggregate-only: deleted rows are never reconstructed. Future observations preserve interpretation, retrieval, policy, version, state, postcondition, and traceability evidence. Observed implementation output stays separate from an independent oracle, while human annotation and a prospectively frozen unseen-test replication remain pending.

**Tech Stack:** Python 3.12, dataclasses, Pydantic, pytest, existing ERP Agent OS experiment/metrics/statistics modules.

---

### Task 1: Preserve raw execution observations

**Files:**
- Create: `src/erp_agent_os/evidence.py`
- Modify: `src/erp_agent_os/experiment.py`
- Modify: `scripts/run_experiment.py`
- Create: `tests/test_evidence.py`
- Modify: `tests/test_run_experiment_script.py`
- Modify: `tests/test_experiment.py`

- [ ] **Step 1: Write failing observation round-trip and path/hash tests**

Test that an enriched `ExecutionRecord` survives JSONL serialization exactly, that a full run has 1,080 unique `(request_id, system, repetition)` units, and that the returned SHA-256 matches its bytes.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest tests/test_evidence.py -q`

Expected: FAIL because `erp_agent_os.evidence` does not exist.

- [ ] **Step 3: Implement minimal evidence serialization**

Expose `execution_record_to_dict`, `execution_record_from_dict`, `write_observations_jsonl`, `load_observations_jsonl`, and `observations_path_for`. Write atomically, refuse conflicting overwrites, and use a content-addressed filename.

- [ ] **Step 4: Reuse the public serializer for checkpoints**

Replace private duplicate conversion in `experiment.py` while retaining backward-compatible checkpoint loading.

- [ ] **Step 5: Make every completed experiment publish raw observations**

Write `<report-stem>_observations_<sha256>.jsonl` before deleting the spent checkpoint. Record schema, row count, SHA-256, dataset/catalog/prompt/provider/code hashes, argument regime, and epistemic status. Any new v1 run is `post_freeze_exploratory`; only an unseen prospectively frozen test may be confirmatory.

- [ ] **Step 5b: Capture auditable H7 evidence**

Preserve normalized arguments, candidate IDs/scores, role, policy and permission reasons, selected skill version and handler, initial/final state, named postcondition outcomes, and the seven traceability component scores. Do not infer these later from aggregates.

- [ ] **Step 5c: Validate semantic completeness, not only serialization**

End-to-end tests assert applicable fields are populated, unavailable A/B evidence is explicitly `not_available`, complete state/check/component evidence is present, and no new v1 report can contain an operative `is_confirmatory_run: true`. Every new v1 manifest must say `post_freeze_exploratory`.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `uv run pytest tests/test_evidence.py tests/test_experiment.py tests/test_run_experiment_script.py -q`

Expected: PASS.

### Task 2: Correct H2 and complete case-level continuous evidence

**Files:**
- Modify: `src/erp_agent_os/dataset.py`
- Modify: `src/erp_agent_os/bench_generator.py`
- Modify: `src/erp_agent_os/metrics.py`
- Modify: `src/erp_agent_os/statistics.py`
- Modify: `scripts/run_experiment.py`
- Modify: `tests/test_metrics.py`
- Modify: `tests/test_statistics.py`

- [ ] **Step 1: Write failing tests for the H2 population**

Assert that `sin_skill/abstención` cases are excluded from H2 token collapse and totals.

- [ ] **Step 2: Run the H2 test and verify RED**

Run: `uv run pytest tests/test_metrics.py -q`

Expected: FAIL because `collapse_tokens` currently includes every case.

- [ ] **Step 3: Implement the H2 population fix**

Move the abstention sentinel to `dataset.py`, pass cases into `collapse_tokens`, and filter report totals to requests with an expected skill.

- [ ] **Step 4: Write failing tests for traceability/latency collapse and paired effects**

Assert one mean value per system/case, paired confidence intervals, defined zero-variance behavior, preserved rubric components, and valid three-system omnibus inputs.

- [ ] **Step 5: Run focused tests and verify RED**

Run: `uv run pytest tests/test_metrics.py tests/test_statistics.py -q`

Expected: FAIL because the new helpers do not exist.

- [ ] **Step 6: Implement minimal continuous-analysis helpers**

Add case-level traceability and latency collapse plus paired effect sizes. Report a three-system omnibus result, Holm-corrected paired post-hoc comparisons, bootstrap ICs, assumption rationale, and H7 rubric components. Keep overall token totals separate from the H2 expected-skill population.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run: `uv run pytest tests/test_metrics.py tests/test_statistics.py tests/test_run_experiment_script.py -q`

Expected: PASS.

### Task 3: Add the H6 precision–coverage artifact

**Files:**
- Create: `src/erp_agent_os/retrieval_analysis.py`
- Modify: `scripts/run_experiment.py`
- Create: `tests/test_retrieval_analysis.py`

- [ ] **Step 1: Write failing precision–coverage tests**

Use a tiny deterministic retriever fixture to prove increasing the threshold cannot increase coverage and that wrong automatic reuse raises false-reuse risk.

- [ ] **Step 2: Run focused test and verify RED**

Run: `uv run pytest tests/test_retrieval_analysis.py -q`

Expected: FAIL because the analysis module does not exist.

- [ ] **Step 3: Implement a retrieval-only threshold sweep**

Compute threshold, coverage, abstention rate, selective accuracy, false-reuse risk, and correct abstention on no-skill cases. Declare and hash the grid before evaluation. Label final-test output descriptive and never retune from it.

- [ ] **Step 4: Add H6 to future experiment reports**

Use a predeclared grid and the frozen margin; include an explicit scope note that missing-field and policy gates are outside this retrieval-only curve.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `uv run pytest tests/test_retrieval_analysis.py tests/test_run_experiment_script.py -q`

Expected: PASS.

### Task 4: Publish observed implementation states without rewriting v1

**Files:**
- Create: `src/erp_agent_os/observed_states.py`
- Create: `scripts/export_benchmark_states.py`
- Create: `tests/test_observed_states.py`
- Create after verification: `data/observed_states_v1_<sha256>.jsonl`

- [ ] **Step 1: Write failing state-materialization tests**

Assert deterministic seeded initial states, unchanged observed final states for blocked cases, and `oracle_status=observed_implementation_output_not_ground_truth` on every row.

- [ ] **Step 2: Run focused test and verify RED**

Run: `uv run pytest tests/test_observed_states.py -q`

Expected: FAIL because the state observer does not exist.

- [ ] **Step 3: Implement deterministic state observation**

Reuse `FakeERPAdapter`, handlers, normalized expected arguments, and the experiment's reference seeding only to expose current implementation output. Never call it expected truth and never alter `data/bench_v1.jsonl`. Include schema and dataset/catalog/code hashes.

- [ ] **Step 4: Export the supplemental state artifact**

Run: `uv run python scripts/export_benchmark_states.py`

Expected: 480 JSONL rows keyed by `request_id`, no `pending_execution_wiring` values, and the non-oracle label on every row.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `uv run pytest tests/test_observed_states.py tests/test_bench_generator.py tests/test_experiment.py -q`

Expected: PASS.

### Task 5: Document hypotheses, theses, and remaining human/replication gates

**Files:**
- Create: `docs/hypotheses-and-theses.md`
- Create: `data/evidence_registry.json`
- Create: `scripts/validate_evidence_claims.py`
- Create: `tests/test_evidence_registry.py`
- Modify when legacy claims are found: `README.md`
- Modify when legacy claims are found: `docs/memoria.md`
- Modify when legacy claims are found: `docs/defensa.md`
- Modify when legacy claims are found: `docs/results.md`
- Modify when legacy claims are found: `docs/demo-explicada.md`
- Modify when legacy claims are found: `docs/product-viability.md`
- Modify when legacy claims are found: relevant presentation/video Markdown found by the validator
- Modify: `docs/experiment-protocol.md`
- Modify: `docs/results.md`

- [ ] **Step 1: Add H1–H8 evidence cards**

For every hypothesis record population, endpoint, result, status, supported claim, prohibited overclaim, epistemic class, source artifact, and remaining work. Encode the same contract in `data/evidence_registry.json`.

- [ ] **Step 2: Add defensible project theses**

Separate confirmatory, corrected/exploratory, external-validity, security, and Odoo feasibility conclusions.

- [ ] **Step 3: Record non-automatable gates**

State that 96 second-annotator decisions, an independent declarative state oracle, and a prospectively frozen unseen-test LLM replication remain pending and cannot be synthesized. Historical summaries are aggregate-only; a new v1 run is exploratory because v1 has been inspected.

- [ ] **Step 4: Add automated claim/status validation**

Validate the registry and scan `docs/results.md`, `README.md`, and available memory/defence/presentation documents. Enforce: H3 non-discriminable, H5/H6 descriptive or partial, H8 scenario-only, post-freeze corrected runs exploratory, historical summaries aggregate-only, and human annotation unperformed.

The validator must also enforce the current global conclusion: **no valid confirmatory conclusion exists yet**. It must require registry coverage for every result artifact cited by any reporting document, not merely one source per hypothesis.

- [ ] **Step 5: Run documentation checks**

Run: `rg -n "H1|H2|H3|H4|H5|H6|H7|H8|tesis" docs/hypotheses-and-theses.md`

Expected: registry validates and no prohibited status claim is found.

### Task 6: Full verification

**Files:**
- Verify only.

- [ ] **Step 1: Run complete test suite**

Run: `uv run pytest -q`

Expected: PASS.

- [ ] **Step 2b: Verify frozen assets were not rewritten**

Run freeze verification before and after artifact generation. Confirm the v1 dataset/catalog/config hashes still match `data/freeze_manifest.json`; this proves integrity, not confirmatory status for post-freeze reruns.

- [ ] **Step 2: Run static quality checks**

Run: `uv run ruff check .`

Run: `uv run mypy src`

Expected: PASS.

- [ ] **Step 3: Run a disposable stub experiment**

Run: `uv run python scripts/run_experiment.py --output C:/tmp/erp-agent-os-evidence-check.json`

Expected: exploratory summary plus a 1,080-row content-addressed archive; hash matches and validation finds no missing or duplicate units.

- [ ] **Step 4: Audit workspace changes**

Run: `git diff --check` and `git status --short`.

Expected: no whitespace errors; only intended files changed plus pre-existing untracked files.

- [ ] **Step 5: Run evidence-claim validation as a release gate**

Run: `uv run python scripts/validate_evidence_claims.py`

Expected: PASS, with every cited result artifact registered and no contradictory confirmatory claim.
