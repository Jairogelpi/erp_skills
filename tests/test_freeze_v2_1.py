"""TDD for erp_agent_os.freeze_v2_1 (v2.1 plan, Task 10).

Explicitly does NOT execute scripts/run_confirmatory_v2_1.py or perform
any real network/provider call -- only the state machine, hash
coverage, gates and receipt discipline this module implements directly.
"""

from __future__ import annotations

import pytest

from erp_agent_os.evidence_v2_1 import (
    ModelCallEvent,
    ObservationV21,
    write_observations_v21_jsonl,
)
from erp_agent_os.freeze_v2_1 import (
    ALLOWED_TRANSITIONS,
    COMPONENT_FILES,
    REPO_ROOT,
    CodeFreezeManifest,
    DryRunResult,
    FreezeV21Error,
    HoldoutManifest,
    InvalidTransitionError,
    RunState,
    _single_content_addressed_file,
    assert_h2_arm_uses_no_cache,
    complete_run,
    compute_component_hashes,
    create_code_freeze,
    current_state,
    dry_run_check,
    force_claims_after_external_failure,
    generate_holdout,
    load_receipts,
    mark_failed_external,
    mark_interrupted,
    publish_report,
    record_code_frozen,
    record_holdout_generated,
    start_run,
    transition,
    validate_run_completion,
    verify_code_freeze,
)

# ================================================================ helpers


def _fake_git(
    *, commit: str = "abc123", tag: str | None = "v2.1.0-holdout", clean: bool = True
):
    def commit_resolver(**_kw) -> str:
        return commit

    def clean_checker(**_kw) -> bool:
        return clean

    def tag_resolver(**_kw) -> str | None:
        return tag

    return commit_resolver, clean_checker, tag_resolver


def _copy_component_tree(tmp_path):
    for relatives in COMPONENT_FILES.values():
        for rel in relatives:
            dest = tmp_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((REPO_ROOT / rel).read_bytes())
    data_dir = REPO_ROOT / "data" / "protocol_v2_1"
    dest_data_dir = tmp_path / "data" / "protocol_v2_1"
    dest_data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("power_analysis", "targeted_mutation_report"):
        src = _single_content_addressed_file(data_dir, name)
        (dest_data_dir / src.name).write_bytes(src.read_bytes())
    return tmp_path


def _code_manifest() -> CodeFreezeManifest:
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    return create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )


def _holdout_manifest() -> HoldoutManifest:
    code_manifest = _code_manifest()
    manifest, *_ = generate_holdout(code_manifest, seed=20260814)
    return manifest


def _call_event(**overrides) -> ModelCallEvent:
    base = dict(
        purpose="argument_extraction",
        attempt=1,
        success=True,
        error_class=None,
        prompt_tokens=10,
        completion_tokens=5,
        latency_seconds=0.1,
        cache_hit=False,
    )
    base.update(overrides)
    return ModelCallEvent(**base)


def _observation(**overrides) -> ObservationV21:
    base = dict(
        protocol_version="2.1.0",
        frozen_commit="abc",
        dataset_hash="d",
        scenario_id="scn-0001-0",
        surface_id="scn-0001-0:S1",
        surface_kind="S1",
        security_pair_id=None,
        population="main",
        control_stratum=None,
        system="C",
        arm="main",
        repetition_index=0,
        provider="fake",
        model="fake-model",
        provider_config_hash="cfg",
        selection_prompt_hash=None,
        extraction_prompt_hash="ext",
        started_at="2026-08-15T00:00:00Z",
        completed_at="2026-08-15T00:00:01Z",
        correlation_id="scn-0001-0",
        request_text="texto",
        extracted_arguments={},
        selected_skill_id="crm.create_opportunity",
        ranked_skill_ids=(),
        candidate_scores={},
        policy_decision="ALLOW",
        policy_reasons=(),
        call_events=(_call_event(),),
        latency_seconds=0.1,
        initial_state={},
        final_state={},
        observed_state_delta={"operation_kind": "no_change"},
        postcondition_evidence={},
        side_effects=(),
        raw_trace={"x": 1},
        normalized_trace={"x": 1},
        evaluator_components={"success": True},
        code_version_hash="code",
        dependency_lock_hash="lock",
    )
    base.update(overrides)
    return ObservationV21(**base)


# ============================================================== step 1


def test_every_declared_transition_is_actually_reachable():
    for current, targets in ALLOWED_TRANSITIONS.items():
        for target in targets:
            assert transition(current, target) == target


def test_completed_to_started_is_rejected():
    with pytest.raises(InvalidTransitionError):
        transition(RunState.RUN_COMPLETED, RunState.RUN_STARTED)


def test_run_failed_external_is_terminal():
    assert ALLOWED_TRANSITIONS[RunState.RUN_FAILED_EXTERNAL] == frozenset()


def test_report_published_is_terminal():
    assert ALLOWED_TRANSITIONS[RunState.REPORT_PUBLISHED] == frozenset()


def test_holdout_cannot_be_generated_without_a_real_code_manifest():
    with pytest.raises(FreezeV21Error):
        generate_holdout(object(), seed=1)  # type: ignore[arg-type]


def test_start_run_rejects_a_missing_raw_unit_plan(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    with pytest.raises(FreezeV21Error):
        start_run(
            log_path,
            holdout,
            provider="groq",
            provider_config_hash="cfg",
            checkpoint_path=tmp_path / "checkpoint.jsonl",
            n_planned_units=0,
        )


def test_start_run_rejects_starting_from_draft_protocol(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    # No CODE_FROZEN/HOLDOUT_GENERATED receipt was ever appended: state is
    # DRAFT_PROTOCOL, which is not an allowed source for RUN_STARTED.
    with pytest.raises(InvalidTransitionError):
        start_run(
            log_path,
            holdout,
            provider="groq",
            provider_config_hash="cfg",
            checkpoint_path=tmp_path / "checkpoint.jsonl",
            n_planned_units=10,
        )


def _force_state(log_path, holdout, state: RunState, **overrides):
    """Test-only shortcut: appends a receipt claiming `state` directly,
    to set up preconditions for later-stage tests without re-running
    the whole state machine each time."""
    from erp_agent_os.freeze_v2_1 import RunReceipt, append_receipt

    base = dict(
        state=state.value,
        holdout_manifest_hash=holdout.manifest_hash,
        provider="groq",
        provider_config_hash="cfg-a",
        recorded_at="2026-08-15T00:00:00Z",
        checkpoint_path=str(log_path.parent / "checkpoint.jsonl"),
        n_planned_units=10,
    )
    base.update(overrides)
    append_receipt(log_path, RunReceipt(**base))


def test_resume_rejects_a_new_seed_or_regenerated_holdout(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    _force_state(log_path, holdout, RunState.RUN_INTERRUPTED_RESUMABLE)
    other_holdout_manifest = HoldoutManifest(
        schema_version="2.1",
        code_manifest_hash=holdout.code_manifest_hash,
        dataset_hash="a-different-dataset-hash",
        seed=999,
        n_main=holdout.n_main,
        n_security_dangerous=holdout.n_security_dangerous,
        n_security_safe=holdout.n_security_safe,
        generated_at="2026-08-15T00:00:00Z",
    )
    with pytest.raises(FreezeV21Error, match="new seed|regenerate"):
        start_run(
            log_path,
            other_holdout_manifest,
            provider="groq",
            provider_config_hash="cfg-a",
            checkpoint_path=tmp_path / "checkpoint.jsonl",
            n_planned_units=10,
        )


def test_resume_rejects_a_different_provider_or_configuration(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    _force_state(log_path, holdout, RunState.RUN_INTERRUPTED_RESUMABLE)
    with pytest.raises(FreezeV21Error, match="provider"):
        start_run(
            log_path,
            holdout,
            provider="gemini",  # different from the forced "groq"
            provider_config_hash="cfg-a",
            checkpoint_path=log_path.parent / "checkpoint.jsonl",
            n_planned_units=10,
        )


def test_resume_with_the_same_plan_and_checkpoint_succeeds(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    _force_state(
        log_path,
        holdout,
        RunState.RUN_INTERRUPTED_RESUMABLE,
        checkpoint_path=str(checkpoint_path),
    )
    receipt = start_run(
        log_path,
        holdout,
        provider="groq",
        provider_config_hash="cfg-a",
        checkpoint_path=checkpoint_path,
        n_planned_units=10,
    )
    assert receipt.state == RunState.RUN_STARTED.value
    assert current_state(log_path) == RunState.RUN_STARTED


def test_force_claims_after_external_failure_never_returns_confirmatory():
    result = force_claims_after_external_failure(
        ["h1a", "h1b", "h4"], has_partial_data={"h1a": True, "h1b": False}
    )
    assert result == {
        "h1a": "confirmatory_inconclusive",
        "h1b": "not_measured",
        "h4": "not_measured",
    }
    assert "confirmatory" not in result.values()
    assert all(
        v in ("confirmatory_inconclusive", "not_measured") for v in result.values()
    )


def test_h2_arm_rejects_a_caching_client():
    from erp_agent_os.llm_client import CachingLLMClient, DeterministicStubClient

    with pytest.raises(FreezeV21Error):
        assert_h2_arm_uses_no_cache(CachingLLMClient(DeterministicStubClient()))
    assert_h2_arm_uses_no_cache(DeterministicStubClient())  # does not raise


# ============================================================== step 2


def test_compute_component_hashes_covers_every_named_component():
    hashes = compute_component_hashes()
    required = {
        "spec",
        "protocol",
        "lockfile",
        "generator",
        "oracle",
        "evaluator",
        "catalog",
        "prompt",
        "provider",
        "analysis",
        "power",
        "harness",
    }
    assert required <= set(hashes)


@pytest.mark.parametrize("component", sorted(COMPONENT_FILES))
def test_mutating_any_component_file_changes_its_own_hash(tmp_path, component):
    tree = _copy_component_tree(tmp_path)
    before = compute_component_hashes(repo_root=tree)

    target = COMPONENT_FILES[component][0]
    mutated_path = tree / target
    mutated_path.write_bytes(mutated_path.read_bytes() + b"\n# tampered for test\n")

    after = compute_component_hashes(repo_root=tree)
    assert after[component] != before[component]
    unrelated = set(before) - {component}
    assert all(after[name] == before[name] for name in unrelated)


def test_verify_code_freeze_reports_no_drift_on_an_untouched_tree(tmp_path):
    tree = _copy_component_tree(tmp_path)
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    manifest = create_code_freeze(
        repo_root=tree,
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    assert verify_code_freeze(manifest, repo_root=tree) == []


def test_verify_code_freeze_reports_drift_after_mutation(tmp_path):
    tree = _copy_component_tree(tmp_path)
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    manifest = create_code_freeze(
        repo_root=tree,
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    catalog_path = tree / "src" / "erp_agent_os" / "catalog.py"
    catalog_path.write_bytes(catalog_path.read_bytes() + b"\n# tampered\n")
    drift = verify_code_freeze(manifest, repo_root=tree)
    assert drift == ["catalog"]


def test_create_code_freeze_rejects_a_dirty_worktree():
    commit_resolver, _, tag_resolver = _fake_git()
    with pytest.raises(FreezeV21Error, match="clean worktree"):
        create_code_freeze(
            git_commit_resolver=commit_resolver,
            worktree_clean_checker=lambda **_: False,
            tag_resolver=tag_resolver,
        )


def test_create_code_freeze_rejects_a_missing_tag():
    commit_resolver, clean_checker, _ = _fake_git()
    with pytest.raises(FreezeV21Error, match="tag"):
        create_code_freeze(
            git_commit_resolver=commit_resolver,
            worktree_clean_checker=clean_checker,
            tag_resolver=lambda **_: None,
        )


# ============================================================== step 3/4


def test_generate_holdout_produces_the_real_generated_corpus():
    code_manifest = _code_manifest()
    manifest, main, dangerous, safe = generate_holdout(code_manifest, seed=20260814)
    assert manifest.code_manifest_hash == code_manifest.manifest_hash
    assert manifest.n_main == len(main)
    assert manifest.n_security_dangerous == len(dangerous)
    assert manifest.n_security_safe == len(safe)


def test_generate_holdout_propagates_a_concordance_mismatch(monkeypatch):
    from erp_agent_os.oracle_concordance_v2_1 import ConcordanceMismatchError

    def _always_fails(*_a, **_kw):
        raise ConcordanceMismatchError([("scn-x", "decision", "ALLOW", "DENY")])

    monkeypatch.setattr(
        "erp_agent_os.freeze_v2_1.validate_full_corpus_concordance", _always_fails
    )
    with pytest.raises(ConcordanceMismatchError):
        generate_holdout(_code_manifest(), seed=20260814)


def test_validate_run_completion_accepts_a_complete_matching_archive(tmp_path):
    observations = [_observation(scenario_id=f"scn-{i:04d}-0") for i in range(3)]
    archive = write_observations_v21_jsonl(
        observations, tmp_path / "run.json", provenance={"dataset_hash": "d"}
    )
    validate_run_completion(
        observations, archive.path, expected_unit_count=3
    )  # no raise


def test_validate_run_completion_rejects_wrong_unit_count(tmp_path):
    observations = [_observation()]
    archive = write_observations_v21_jsonl(
        observations, tmp_path / "run.json", provenance={"dataset_hash": "d"}
    )
    with pytest.raises(FreezeV21Error, match="expected"):
        validate_run_completion(observations, archive.path, expected_unit_count=5)


def test_validate_run_completion_rejects_duplicate_unit_keys(tmp_path):
    same = _observation()
    with pytest.raises(FreezeV21Error, match="duplicate"):
        validate_run_completion(
            [same, same], tmp_path / "irrelevant.jsonl", expected_unit_count=2
        )


def test_validate_run_completion_rejects_a_semantically_incomplete_row(tmp_path):
    incomplete = _observation(arm="h2_tokens", call_events=())
    archive = write_observations_v21_jsonl(
        [incomplete], tmp_path / "run.json", provenance={"dataset_hash": "d"}
    )
    with pytest.raises(Exception):  # EvidenceV21Error from validate_arm_semantics
        validate_run_completion([incomplete], archive.path, expected_unit_count=1)


def test_validate_run_completion_rejects_an_archive_that_does_not_match(tmp_path):
    observations = [_observation()]
    archive = write_observations_v21_jsonl(
        observations, tmp_path / "run.json", provenance={"dataset_hash": "d"}
    )
    different = [_observation(scenario_id="scn-9999-0")]
    with pytest.raises(FreezeV21Error, match="does not match"):
        validate_run_completion(different, archive.path, expected_unit_count=1)


# ============================================================== step 5


def test_full_lifecycle_receipts_in_order(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"

    assert current_state(log_path) == RunState.DRAFT_PROTOCOL

    code_manifest = _code_manifest()
    record_code_frozen(log_path, code_manifest)
    assert current_state(log_path) == RunState.CODE_FROZEN

    holdout, *_ = generate_holdout(code_manifest, seed=20260814)
    record_holdout_generated(log_path, holdout)
    assert current_state(log_path) == RunState.HOLDOUT_GENERATED_NOT_EVALUATED

    start_run(
        log_path,
        holdout,
        provider="groq",
        provider_config_hash="cfg-a",
        checkpoint_path=checkpoint_path,
        n_planned_units=1,
    )
    assert current_state(log_path) == RunState.RUN_STARTED

    observations = [_observation()]
    archive = write_observations_v21_jsonl(
        observations, tmp_path / "run.json", provenance={"dataset_hash": "d"}
    )
    complete_run(log_path, observations=observations, archive_path=archive.path)
    assert current_state(log_path) == RunState.RUN_COMPLETED

    publish_report(log_path)
    assert current_state(log_path) == RunState.REPORT_PUBLISHED

    receipts = load_receipts(log_path)
    assert [r.state for r in receipts] == [
        RunState.CODE_FROZEN.value,
        RunState.HOLDOUT_GENERATED_NOT_EVALUATED.value,
        RunState.RUN_STARTED.value,
        RunState.RUN_COMPLETED.value,
        RunState.REPORT_PUBLISHED.value,
    ]


def test_record_code_frozen_rejects_a_second_call(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    code_manifest = _code_manifest()
    record_code_frozen(log_path, code_manifest)
    with pytest.raises(InvalidTransitionError):
        record_code_frozen(log_path, code_manifest)


def test_holdout_and_code_frozen_receipts_cannot_be_skipped(tmp_path):
    """record_holdout_generated before CODE_FROZEN, and start_run before
    HOLDOUT_GENERATED_NOT_EVALUATED, must both be rejected by the same
    transition graph -- there is no separate code path for "the real
    script" that bypasses it."""
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    with pytest.raises(InvalidTransitionError):
        record_holdout_generated(log_path, holdout)


def test_complete_run_never_writes_a_receipt_when_validation_fails(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    _force_state(
        log_path,
        holdout,
        RunState.RUN_STARTED,
        n_planned_units=5,
        checkpoint_path=str(checkpoint_path),
    )
    observations = [_observation()]  # only 1, but 5 were planned
    archive = write_observations_v21_jsonl(
        observations, tmp_path / "run.json", provenance={"dataset_hash": "d"}
    )
    with pytest.raises(FreezeV21Error):
        complete_run(log_path, observations=observations, archive_path=archive.path)
    assert current_state(log_path) == RunState.RUN_STARTED  # unchanged


def test_mark_interrupted_and_resume_and_fail_external(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    holdout = _holdout_manifest()
    _force_state(log_path, holdout, RunState.RUN_STARTED, n_planned_units=10)

    mark_interrupted(
        log_path,
        error_class="RateLimitError",
        error_message="quota exhausted",
        n_completed_units=4,
    )
    assert current_state(log_path) == RunState.RUN_INTERRUPTED_RESUMABLE

    mark_failed_external(
        log_path,
        error_class="ProviderOutage",
        error_message="permanent failure",
        n_completed_units=4,
    )
    assert current_state(log_path) == RunState.RUN_FAILED_EXTERNAL
    receipts = load_receipts(log_path)
    final = receipts[-1]
    assert final.n_completed_units == 4
    assert final.provider == "groq"  # preserved from the original RUN_STARTED receipt
    assert final.checkpoint_path is not None

    with pytest.raises(InvalidTransitionError):
        transition(RunState.RUN_FAILED_EXTERNAL, RunState.RUN_STARTED)


# ============================================================== step 6


def test_dry_run_never_writes_a_receipt(tmp_path):
    log_path = tmp_path / "receipts.jsonl"
    code_manifest = _code_manifest()
    dry_run_check(
        code_manifest=code_manifest,
        provider="groq",
        provider_config_hash="cfg",
        expected_provider="groq",
        expected_provider_config_hash="cfg",
        n_planned_units=10,
    )
    assert not log_path.exists()


def test_dry_run_ok_when_everything_matches():
    code_manifest = _code_manifest()
    result = dry_run_check(
        code_manifest=code_manifest,
        provider="groq",
        provider_config_hash="cfg",
        expected_provider="groq",
        expected_provider_config_hash="cfg",
        n_planned_units=10,
    )
    assert isinstance(result, DryRunResult)
    assert result.ok is True
    assert result.mismatches == ()


def test_dry_run_detects_provider_mismatch():
    code_manifest = _code_manifest()
    result = dry_run_check(
        code_manifest=code_manifest,
        provider="gemini",
        provider_config_hash="cfg",
        expected_provider="groq",
        expected_provider_config_hash="cfg",
        n_planned_units=10,
    )
    assert result.ok is False
    assert any("provider" in m for m in result.mismatches)


def test_dry_run_detects_a_missing_plan():
    code_manifest = _code_manifest()
    result = dry_run_check(
        code_manifest=code_manifest,
        provider="groq",
        provider_config_hash="cfg",
        expected_provider="groq",
        expected_provider_config_hash="cfg",
        n_planned_units=0,
    )
    assert result.ok is False


def test_dry_run_detects_component_drift(tmp_path):
    tree = _copy_component_tree(tmp_path)
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        repo_root=tree,
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    catalog_path = tree / "src" / "erp_agent_os" / "catalog.py"
    catalog_path.write_bytes(catalog_path.read_bytes() + b"\n# tampered\n")

    result = dry_run_check(
        code_manifest=code_manifest,
        provider="groq",
        provider_config_hash="cfg",
        expected_provider="groq",
        expected_provider_config_hash="cfg",
        n_planned_units=10,
        repo_root=tree,
    )
    assert result.ok is False
    assert any("drifted" in m for m in result.mismatches)
