from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

from erp_agent_os.annotation_audit import (
    AnnotationAuditError,
    BlindedAuditItem,
    load_review_rows,
    prompt_hash,
    run_blinded_audit,
)

SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "run_ai_annotation_audit.py"
)
SPEC = importlib.util.spec_from_file_location("run_ai_annotation_audit_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT_MODULE)
main = SCRIPT_MODULE.main


class RecordingReviewer:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[str, dict[str, object]]] = []

    def review(self, *, prompt: str, response_schema: dict[str, object]):
        self.calls.append((prompt, response_schema))
        return next(self.responses)


def _write_sheet(path: Path) -> bytes:
    path.write_text(
        "request_id,request_text,canonical_intent,risk_class,labels,annotator1_decision,annotator2_decision,notes\n"
        "r1,Crea una tarea,internal.create_task,R1,NORMAL,ALLOW,,secret note\n"
        "r2,Borra todo,forbidden.delete,R4,ADVERSARIAL,DENY,,other secret\n",
        encoding="utf-8",
    )
    return path.read_bytes()


def test_reviewer_is_blind_and_join_happens_after_calls(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.csv"
    _write_sheet(sheet)
    items, canonical = load_review_rows(sheet)
    reviewer = RecordingReviewer(
        [
            {"label": "ALLOW", "confidence": 0.9, "reason": "low impact"},
            {"label": "ALLOW", "confidence": 0.7, "reason": "misread"},
        ]
    )
    report = run_blinded_audit(
        items=items,
        canonical_labels=canonical,
        reviewer=reviewer,
        provider="stub",
        model="reviewer-v1",
    )
    prompts = "\n".join(call[0] for call in reviewer.calls)
    for forbidden in (
        "canonical_intent",
        "annotator1",
        "annotator2_decision",
        "secret note",
        "system output",
    ):
        assert forbidden not in prompts
    assert report.agreement_rate == 0.5
    assert report.disagreement_request_ids == ("r2",)
    assert report.human_inter_annotator_agreement is False
    assert report.manual_adjudication_required is True


def test_prompt_hash_is_deterministic() -> None:
    assert prompt_hash() == prompt_hash()
    assert len(prompt_hash()) == 64


def test_invalid_response_fails_without_output(tmp_path: Path) -> None:
    reviewer = RecordingReviewer([{"label": "ROOT", "confidence": 2, "reason": "x"}])
    with pytest.raises(AnnotationAuditError, match="no audit was written"):
        run_blinded_audit(
            items=[BlindedAuditItem(request_id="r1", request_text="hola")],
            canonical_labels={"r1": "ALLOW"},
            reviewer=reviewer,
            provider="stub",
            model="stub",
        )


def test_atomic_write_preserves_existing_output_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "report.json"
    output.write_text("old", encoding="utf-8")
    sheet = tmp_path / "sheet.csv"
    _write_sheet(sheet)
    items, canonical = load_review_rows(sheet)
    reviewer = RecordingReviewer(
        [{"label": "ALLOW", "confidence": 1, "reason": "ok"}, RuntimeError("secret")]
    )
    with pytest.raises(AnnotationAuditError):
        run_blinded_audit(
            items=items,
            canonical_labels=canonical,
            reviewer=reviewer,
            provider="stub",
            model="stub",
        )
    assert output.read_text(encoding="utf-8") == "old"


def test_cli_writes_registered_output_and_never_changes_sheet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet = tmp_path / "sheet.csv"
    original = _write_sheet(sheet)
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            {
                "r1": {"label": "ALLOW", "confidence": 1, "reason": "ok"},
                "r2": {"label": "DENY", "confidence": 1, "reason": "risk"},
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "annotation_ai_audit.json"
    monkeypatch.setattr(SCRIPT_MODULE, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(SCRIPT_MODULE, "REGISTRY", Path("data/evidence_registry.json"))
    assert (
        main(
            [
                "--input",
                str(sheet),
                "--responses",
                str(responses),
                "--output",
                str(output),
                "--provider",
                "offline",
                "--model",
                "recorded-v1",
            ]
        )
        == 0
    )
    assert sheet.read_bytes() == original
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_status"] == "ai_consistency_audit"
    assert "annotator2_decision" not in output.read_text(encoding="utf-8")


def test_cli_rejects_unregistered_retained_path(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.csv"
    _write_sheet(sheet)
    responses = tmp_path / "responses.json"
    responses.write_text("{}", encoding="utf-8")
    assert (
        main(
            [
                "--input",
                str(sheet),
                "--responses",
                str(responses),
                "--output",
                str(tmp_path / "unregistered.json"),
                "--provider",
                "offline",
                "--model",
                "recorded-v1",
            ]
        )
        == 1
    )


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.csv"
    sheet.write_text(
        "request_id,request_text,annotator1_decision\nr1,a,ALLOW\nr1,b,DENY\n",
        encoding="utf-8",
    )
    with pytest.raises(AnnotationAuditError, match="duplicate"):
        load_review_rows(sheet)


def test_schema_file_matches_required_machine_diagnostic_contract() -> None:
    schema = json.loads(
        Path("data/annotation_ai_audit.schema.json").read_text(encoding="utf-8")
    )
    required = set(schema["required"])
    assert {
        "evidence_status",
        "diagnostic_only",
        "manual_adjudication_required",
    } <= required


def test_canonical_sheet_has_no_machine_second_annotator_values() -> None:
    with Path("data/annotation_review_sheet.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        assert all(
            not row["annotator2_decision"].strip() for row in csv.DictReader(handle)
        )
