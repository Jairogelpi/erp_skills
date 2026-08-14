"""TDD for scripts/verify_tfm_closure_v2_1.py (v2.1 plan, Task 12 step 1)."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

from erp_agent_os.evidence_v2_1 import ModelCallEvent, ObservationV21
from erp_agent_os.freeze_v2_1 import (
    COMPONENT_FILES,
    REPO_ROOT,
    RunReceipt,
    append_receipt,
    create_code_freeze,
    mark_failed_external,
)

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "verify_tfm_closure_v2_1.py"
)
_spec = importlib.util.spec_from_file_location("verify_tfm_closure_v2_1", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
closure = importlib.util.module_from_spec(_spec)
sys.modules["verify_tfm_closure_v2_1"] = closure
_spec.loader.exec_module(closure)


def _fake_git():
    return (lambda **_: "abc123"), (lambda **_: True), (lambda **_: "v2.1.0-test")


def _copy_component_tree(tmp_path):
    for relatives in COMPONENT_FILES.values():
        for rel in relatives:
            dest = tmp_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((REPO_ROOT / rel).read_bytes())
    data_dir = REPO_ROOT / "data" / "protocol_v2_1"
    dest_data_dir = tmp_path / "data" / "protocol_v2_1"
    dest_data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("power_analysis", "targeted_mutation_report", "v2_supersession"):
        matches = sorted(data_dir.glob(f"{name}_*.json"))
        assert len(matches) == 1, f"expected exactly one {name}_*.json fixture"
        src = matches[0]
        (dest_data_dir / src.name).write_bytes(src.read_bytes())
    return tmp_path


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
        arm="h2_tokens",
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


# ==================================================================== pre-run


def test_pre_run_passes_on_a_clean_untouched_tree(tmp_path):
    tree = _copy_component_tree(tmp_path)
    result = closure.check_pre_run(
        repo_root=tree,
        protocol_path=tree / "config" / "protocol_v2_1.json",
        supersession_dir=tree / "data" / "protocol_v2_1",
        receipt_log=tmp_path / "no_such_receipts.jsonl",
    )
    assert result.ok is True
    assert result.message == "READY_TO_COMMIT_AND_CREATE_CODE_FREEZE"
    assert result.reasons == ()


def test_pre_run_fails_when_supersession_artifact_is_missing(tmp_path):
    tree = _copy_component_tree(tmp_path)
    for path in (tree / "data" / "protocol_v2_1").glob("v2_supersession_*.json"):
        path.unlink()
    result = closure.check_pre_run(
        repo_root=tree,
        protocol_path=tree / "config" / "protocol_v2_1.json",
        supersession_dir=tree / "data" / "protocol_v2_1",
        receipt_log=tmp_path / "no_such_receipts.jsonl",
    )
    assert result.ok is False
    assert any("v2_supersession" in r for r in result.reasons)


def test_pre_run_fails_when_power_analysis_artifact_is_missing(tmp_path):
    tree = _copy_component_tree(tmp_path)
    for path in (tree / "data" / "protocol_v2_1").glob("power_analysis_*.json"):
        path.unlink()
    result = closure.check_pre_run(
        repo_root=tree,
        protocol_path=tree / "config" / "protocol_v2_1.json",
        supersession_dir=tree / "data" / "protocol_v2_1",
        receipt_log=tmp_path / "no_such_receipts.jsonl",
    )
    assert result.ok is False
    assert any("power" in r for r in result.reasons)


def test_pre_run_fails_when_a_component_file_is_missing(tmp_path):
    tree = _copy_component_tree(tmp_path)
    (tree / "src" / "erp_agent_os" / "catalog.py").unlink()
    result = closure.check_pre_run(
        repo_root=tree,
        protocol_path=tree / "config" / "protocol_v2_1.json",
        supersession_dir=tree / "data" / "protocol_v2_1",
        receipt_log=tmp_path / "no_such_receipts.jsonl",
    )
    assert result.ok is False
    assert any("component hash coverage" in r for r in result.reasons)


def test_pre_run_fails_when_v2_1_receipts_already_exist(tmp_path):
    tree = _copy_component_tree(tmp_path)
    receipt_log = tmp_path / "receipts.jsonl"
    append_receipt(
        receipt_log,
        RunReceipt(
            state="CODE_FROZEN",
            holdout_manifest_hash="",
            provider="",
            provider_config_hash="x",
            recorded_at="2026-08-15T00:00:00Z",
        ),
    )
    result = closure.check_pre_run(
        repo_root=tree,
        protocol_path=tree / "config" / "protocol_v2_1.json",
        supersession_dir=tree / "data" / "protocol_v2_1",
        receipt_log=receipt_log,
    )
    assert result.ok is False
    assert any("DRAFT_PROTOCOL" in r for r in result.reasons)


def test_pre_run_rejects_a_protocol_declaring_human_annotation_required(tmp_path):
    tree = _copy_component_tree(tmp_path)
    protocol_path = tree / "config" / "protocol_v2_1.json"
    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
    payload["human_annotation_required"] = True
    protocol_path.write_text(json.dumps(payload), encoding="utf-8")
    result = closure.check_pre_run(
        repo_root=tree,
        protocol_path=protocol_path,
        supersession_dir=tree / "data" / "protocol_v2_1",
        receipt_log=tmp_path / "no_such_receipts.jsonl",
    )
    assert result.ok is False
    assert any("human_annotation_required" in r for r in result.reasons)


# ==================================================================== raw-only


def test_raw_only_passes_on_exact_coverage(tmp_path):
    receipt_log = tmp_path / "receipts.jsonl"
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_COMPLETED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            n_planned_units=10,
            n_completed_units=10,
        ),
    )
    result = closure.check_raw_only(
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
    )
    assert result.ok is True
    assert result.message == "RAW_COVERAGE_OK"


def test_raw_only_fails_on_a_coverage_mismatch(tmp_path):
    receipt_log = tmp_path / "receipts.jsonl"
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_COMPLETED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            n_planned_units=10,
            n_completed_units=7,
        ),
    )
    result = closure.check_raw_only(
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
    )
    assert result.ok is False
    assert any("coverage mismatch" in r for r in result.reasons)


def test_raw_only_fails_when_not_run_completed(tmp_path):
    receipt_log = tmp_path / "receipts.jsonl"
    result = closure.check_raw_only(
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
    )
    assert result.ok is False


# ================================================================ failed-external


def test_failed_external_passes_with_stable_hashes_and_complete_partial_rows(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    checkpoint_path.write_text("", encoding="utf-8")
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_STARTED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            checkpoint_path=str(checkpoint_path),
            n_planned_units=10,
        ),
    )
    mark_failed_external(
        receipt_log, error_class="Outage", error_message="down", n_completed_units=3
    )

    observation = _observation()
    checkpoint_path.write_text(
        json.dumps({"key": "k1", "observation": observation.model_dump(mode="json")})
        + "\n",
        encoding="utf-8",
    )

    result = closure.check_failed_external(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
        checkpoint_paths=(checkpoint_path,),
    )
    assert result.ok is True
    assert result.message == "FAILED_EXTERNAL_VALIDATED"


def test_failed_external_fails_when_state_is_not_run_failed_external(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    result = closure.check_failed_external(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
    )
    assert result.ok is False
    assert any("RUN_FAILED_EXTERNAL" in r for r in result.reasons)


def test_failed_external_fails_on_a_semantically_incomplete_partial_row(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    checkpoint_path.write_text("", encoding="utf-8")
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_STARTED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            checkpoint_path=str(checkpoint_path),
            n_planned_units=10,
        ),
    )
    mark_failed_external(
        receipt_log, error_class="Outage", error_message="down", n_completed_units=1
    )

    incomplete = _observation(call_events=())  # h2_tokens row with no call_events
    checkpoint_path.write_text(
        json.dumps({"key": "k1", "observation": incomplete.model_dump(mode="json")})
        + "\n",
        encoding="utf-8",
    )

    result = closure.check_failed_external(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
        checkpoint_paths=(checkpoint_path,),
    )
    assert result.ok is False
    assert any("semantically incomplete" in r for r in result.reasons)


# ======================================================================= final


def test_final_delegates_to_failed_external_when_that_is_the_terminal_state(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    checkpoint_path.write_text("", encoding="utf-8")
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_STARTED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            checkpoint_path=str(checkpoint_path),
            n_planned_units=10,
        ),
    )
    mark_failed_external(
        receipt_log, error_class="Outage", error_message="down", n_completed_units=0
    )

    result = closure.check_final(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
    )
    assert result.mode == "final"
    assert result.ok is True  # no checkpoint rows to invalidate it


def test_final_requires_a_report_path_for_a_completed_run(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_COMPLETED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            n_planned_units=5,
            n_completed_units=5,
        ),
    )
    result = closure.check_final(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
    )
    assert result.ok is False
    assert any("report-path" in r for r in result.reasons)


def test_final_validates_claim_language_in_the_report(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_COMPLETED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            n_planned_units=5,
            n_completed_units=5,
        ),
    )
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "hypotheses": {
                    "h1b": {
                        "claim": {
                            "evidence_state": "confirmatory_not_supported",
                            "claim_text": "H1b queda demostrado.",  # unauthorized
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    result = closure.check_final(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
        report_path=report_path,
    )
    assert result.ok is False
    assert any("h1b" in r for r in result.reasons)


def test_final_passes_with_a_clean_completed_report(tmp_path):
    commit_resolver, clean_checker, tag_resolver = _fake_git()
    code_manifest = create_code_freeze(
        git_commit_resolver=commit_resolver,
        worktree_clean_checker=clean_checker,
        tag_resolver=tag_resolver,
    )
    receipt_log = tmp_path / "receipts.jsonl"
    append_receipt(
        receipt_log,
        RunReceipt(
            state="RUN_COMPLETED",
            holdout_manifest_hash="h",
            provider="groq",
            provider_config_hash="cfg",
            recorded_at="2026-08-15T00:00:00Z",
            n_planned_units=5,
            n_completed_units=5,
        ),
    )
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "hypotheses": {
                    "h1b": {
                        "claim": {
                            "evidence_state": "confirmatory_not_supported",
                            "claim_text": "C no superó a B en esta métrica.",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    result = closure.check_final(
        code_manifest=code_manifest,
        receipt_log=receipt_log,
        protocol_path=REPO_ROOT / "config" / "protocol_v2_1.json",
        report_path=report_path,
    )
    assert result.ok is True
    assert result.message == "CLOSURE_VALID"
