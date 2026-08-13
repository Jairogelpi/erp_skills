import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from erp_agent_os.evidence import (
    EvidenceEntry,
    EvidenceRegistry,
    EvidenceStatus,
)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "evidence_registry.json"


def _load_audit_script():
    script_path = ROOT / "scripts" / "audit_evidence_status.py"
    spec = importlib.util.spec_from_file_location("audit_evidence_status", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "path": "data/example_results.json",
        "date": "2026-08-12",
        "source_commit": "abcdef0",
        "protocol_status": "exploratory",
        "reason": "Observed during development.",
        "implementation_observed": True,
        "test_data_observed": True,
        "permitted_claims": ["A scoped exploratory observation."],
        "prohibited_claims": ["A confirmatory estimate."],
    }
    entry.update(overrides)
    return entry


def _registry(*entries: dict[str, object], **overrides: object) -> dict[str, object]:
    registry: dict[str, object] = {
        "schema_version": "1.0",
        "legacy_cutoff_commit": "47ecd3f",
        "retained_annotation_audit_outputs": ["data/annotation_ai_audit.json"],
        "non_reportable_allowlist": [],
        "entries": list(entries),
    }
    registry.update(overrides)
    return registry


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_valid_confirmation_evidence(
    root: Path,
    *,
    freeze_overrides: dict[str, object] | None = None,
    validation_overrides: dict[str, object] | None = None,
) -> None:
    data = root / "data"
    data.mkdir(exist_ok=True)
    artifact_path = data / "example_results.json"
    artifact_path.write_text('{"complete": true}', encoding="utf-8")

    freeze: dict[str, object] = {
        "schema_version": "1.0",
        "status": "verified",
        "protocol_id": "erp-skills-bench-v2",
        "manifest_hash": "a" * 64,
        "run_config_hash": "b" * 64,
        "expected_observations": 1080,
    }
    freeze.update(freeze_overrides or {})
    freeze_path = data / "freeze_manifest_v2.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")

    validation: dict[str, object] = {
        "schema_version": "1.0",
        "artifact_path": "data/example_results.json",
        "artifact_sha256": _sha256(artifact_path),
        "freeze_manifest_path": "data/freeze_manifest_v2.json",
        "freeze_manifest_sha256": _sha256(freeze_path),
        "manifest_hash": "a" * 64,
        "run_config_hash": "b" * 64,
        "validation_status": "passed",
        "completed_observations": 1080,
        "expected_observations": 1080,
        "primary_endpoint_complete": True,
    }
    validation.update(validation_overrides or {})
    (data / "bench_v2_result_validation.json").write_text(
        json.dumps(validation), encoding="utf-8"
    )


def test_committed_registry_has_the_required_authoritative_classifications():
    registry = EvidenceRegistry.load(REGISTRY_PATH)

    expected = {
        "data/experiment_results.json": EvidenceStatus.EXPLORATORY,
        "data/experiment_results_real_parser.json": EvidenceStatus.EXPLORATORY,
        "data/experiment_results_groq_given_args.json": EvidenceStatus.SENSITIVITY,
        "data/retriever_comparison.json": EvidenceStatus.EXPLORATORY,
        "data/real_requests_eval.json": EvidenceStatus.EXPLORATORY,
        "data/real_requests_llm_eval.json": EvidenceStatus.EXPLORATORY,
        "data/injecagent_stress_test_results.json": EvidenceStatus.EXPLORATORY,
        "data/injection_resistance_results.json": EvidenceStatus.EXPLORATORY,
        "data/odoo_governed_demo_results.json": EvidenceStatus.DEMONSTRATION,
        "data/bench_v2_confirmatory_results.json": EvidenceStatus.PENDING,
        "data/catalog_aware_stress_results.json": EvidenceStatus.EXPLORATORY,
        "data/annotation_ai_audit.json": EvidenceStatus.PENDING,
    }

    assert {path: registry.status_for(path) for path in expected} == expected
    assert registry.legacy_cutoff_commit == "47ecd3f"


def test_registry_precedes_the_legacy_is_confirmatory_run_field():
    legacy = json.loads((ROOT / "data" / "experiment_results.json").read_text())
    assert legacy["manifest"]["is_confirmatory_run"] is True

    registry = EvidenceRegistry.load(REGISTRY_PATH)
    assert (
        registry.status_for("data/experiment_results.json")
        is EvidenceStatus.EXPLORATORY
    )
    with pytest.raises(ValueError, match="exploratory"):
        registry.require_confirmatory("data/experiment_results.json", root=ROOT)


def test_entries_and_registry_are_immutable_and_lookup_is_exact():
    registry = EvidenceRegistry.model_validate(_registry(_entry()))
    entry = registry.entry_for("data/example_results.json")

    with pytest.raises(ValidationError):
        entry.reason = "Retrospectively promoted."  # type: ignore[misc]
    with pytest.raises(ValidationError):
        registry.legacy_cutoff_commit = "changed"  # type: ignore[misc]
    with pytest.raises(KeyError):
        registry.status_for("./data/example_results.json")


def test_registry_rejects_duplicate_paths_and_unknown_statuses():
    with pytest.raises(ValidationError, match="duplicate evidence path"):
        EvidenceRegistry.model_validate(_registry(_entry(), _entry()))

    with pytest.raises(ValidationError, match="protocol_status"):
        EvidenceRegistry.model_validate(_registry(_entry(protocol_status="historical")))

    with pytest.raises(ValidationError, match="extra_forbidden"):
        EvidenceRegistry.model_validate(_registry(_entry(unreviewed_field=True)))


def test_optional_confirmation_paths_accept_explicit_null():
    entry = EvidenceEntry.model_validate(
        _entry(freeze_manifest_path=None, result_validation_path=None)
    )
    assert entry.freeze_manifest_path is None
    assert entry.result_validation_path is None

    with pytest.raises(ValidationError, match="freeze_manifest_path"):
        EvidenceEntry.model_validate(
            _entry(
                protocol_status="confirmatory",
                freeze_manifest_path=None,
                result_validation_path=None,
            )
        )


@pytest.mark.parametrize(
    "missing_field",
    ["freeze_manifest_path", "result_validation_path"],
)
def test_confirmatory_entry_requires_both_validation_evidence_fields(missing_field):
    values = _entry(
        protocol_status="confirmatory",
        freeze_manifest_path="data/freeze_manifest_v2.json",
        result_validation_path="data/bench_v2_result_validation.json",
    )
    del values[missing_field]

    with pytest.raises(ValidationError, match=missing_field):
        EvidenceEntry.model_validate(values)


def test_confirmation_guard_requires_the_declared_evidence_files(tmp_path):
    entry = _entry(
        protocol_status="confirmatory",
        freeze_manifest_path="data/freeze_manifest_v2.json",
        result_validation_path="data/bench_v2_result_validation.json",
    )
    registry = EvidenceRegistry.model_validate(_registry(entry))
    (tmp_path / "data").mkdir()

    with pytest.raises(ValueError, match="freeze_manifest_v2.json"):
        registry.require_confirmatory("data/example_results.json", root=tmp_path)

    _write_valid_confirmation_evidence(tmp_path)
    (tmp_path / "data" / "bench_v2_result_validation.json").unlink()
    with pytest.raises(ValueError, match="bench_v2_result_validation.json"):
        registry.require_confirmatory("data/example_results.json", root=tmp_path)

    _write_valid_confirmation_evidence(tmp_path)
    assert registry.require_confirmatory(
        "data/example_results.json", root=tmp_path
    ) == registry.entry_for(
        "data/example_results.json",
    )


def test_confirmation_guard_rejects_empty_or_malformed_evidence(tmp_path):
    entry = _entry(
        protocol_status="confirmatory",
        freeze_manifest_path="data/freeze_manifest_v2.json",
        result_validation_path="data/bench_v2_result_validation.json",
    )
    registry = EvidenceRegistry.model_validate(_registry(entry))
    _write_valid_confirmation_evidence(tmp_path)

    freeze = tmp_path / "data" / "freeze_manifest_v2.json"
    freeze.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid freeze evidence"):
        registry.require_confirmatory("data/example_results.json", root=tmp_path)

    _write_valid_confirmation_evidence(tmp_path)
    validation = tmp_path / "data" / "bench_v2_result_validation.json"
    validation.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid result validation evidence"):
        registry.require_confirmatory("data/example_results.json", root=tmp_path)


@pytest.mark.parametrize(
    ("validation_overrides", "message"),
    [
        ({"validation_status": "failed"}, "validation_status"),
        ({"completed_observations": 1079}, "completed_observations"),
        ({"primary_endpoint_complete": False}, "primary_endpoint_complete"),
        ({"artifact_path": "data/other_results.json"}, "artifact_path"),
        ({"artifact_sha256": "c" * 64}, "artifact_sha256"),
        ({"freeze_manifest_sha256": "c" * 64}, "freeze_manifest_sha256"),
        ({"manifest_hash": "c" * 64}, "manifest_hash"),
        ({"run_config_hash": "c" * 64}, "run_config_hash"),
    ],
)
def test_confirmation_guard_rejects_failed_incomplete_or_mismatched_validation(
    tmp_path, validation_overrides, message
):
    entry = _entry(
        protocol_status="confirmatory",
        freeze_manifest_path="data/freeze_manifest_v2.json",
        result_validation_path="data/bench_v2_result_validation.json",
    )
    registry = EvidenceRegistry.model_validate(_registry(entry))
    _write_valid_confirmation_evidence(
        tmp_path, validation_overrides=validation_overrides
    )

    with pytest.raises(ValueError, match=message):
        registry.require_confirmatory("data/example_results.json", root=tmp_path)


def test_committed_registry_covers_every_reportable_artifact():
    registry = EvidenceRegistry.load(REGISTRY_PATH)
    assert registry.unregistered_reportable_paths(ROOT) == ()


def test_completeness_scan_finds_results_and_respects_explicit_fixture_allowlist(
    tmp_path,
):
    data = tmp_path / "data"
    data.mkdir()
    (data / "new_results.json").write_text("{}", encoding="utf-8")

    registry = EvidenceRegistry.model_validate(_registry(_entry()))
    assert registry.unregistered_reportable_paths(tmp_path) == (
        "data/new_results.json",
    )

    allowlisted = EvidenceRegistry.model_validate(
        _registry(_entry(), non_reportable_allowlist=["data/new_results.json"])
    )
    assert allowlisted.unregistered_reportable_paths(tmp_path) == ()


def test_pending_adversarial_and_ai_audits_declare_claim_boundaries():
    registry = EvidenceRegistry.load(REGISTRY_PATH)

    for path in (
        "data/catalog_aware_stress_results.json",
        "data/annotation_ai_audit.json",
    ):
        entry = registry.entry_for(path)
        assert entry.permitted_claims
        assert entry.prohibited_claims


def test_evidence_cli_fails_and_names_document_and_artifact(tmp_path, capsys):
    audit_script = _load_audit_script()
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(_registry(_entry(path="data/experiment_results.json"))),
        encoding="utf-8",
    )
    report = tmp_path / "report.md"
    report.write_text(
        "data/experiment_results.json is the final confirmatory run.",
        encoding="utf-8",
    )

    exit_code = audit_script.main(
        [
            "--root",
            str(tmp_path),
            "--registry",
            str(registry_path),
            str(report),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code != 0
    assert "report.md" in output
    assert "data/experiment_results.json" in output


def test_evidence_cli_enforces_confirmation_evidence_for_confirmatory_entries(
    tmp_path, capsys
):
    audit_script = _load_audit_script()
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            _registry(
                _entry(
                    path="data/future_results.json",
                    protocol_status="confirmatory",
                    freeze_manifest_path="data/freeze_manifest_v2.json",
                    result_validation_path="data/future_result_validation.json",
                )
            )
        ),
        encoding="utf-8",
    )

    exit_code = audit_script.main(
        ["--root", str(tmp_path), "--registry", str(registry_path)]
    )

    output = capsys.readouterr().out
    assert exit_code != 0
    assert "data/future_results.json" in output
    assert "data/freeze_manifest_v2.json" in output
    assert "data/future_result_validation.json" in output


def test_evidence_cli_handles_explicit_null_confirmation_paths(capsys, tmp_path):
    audit_script = _load_audit_script()
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            _registry(
                _entry(
                    protocol_status="confirmatory",
                    freeze_manifest_path=None,
                    result_validation_path=None,
                )
            )
        ),
        encoding="utf-8",
    )

    exit_code = audit_script.main(
        ["--root", str(tmp_path), "--registry", str(registry_path)]
    )

    output = capsys.readouterr().out
    assert exit_code != 0
    assert "INVALID REGISTRY" in output
    assert "freeze_manifest_path" in output
