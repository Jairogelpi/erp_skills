import csv
import importlib.util
from pathlib import Path

from erp_agent_os.evidence import EvidenceRegistry

ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = ROOT / "scripts" / "audit_docs_coherence.py"
_spec = importlib.util.spec_from_file_location("audit_docs_coherence", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
audit_docs_coherence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_docs_coherence)


def _empty_annotation_sheet(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["request_id", "annotator1_decision", "annotator2_decision"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "request_id": "REQ-001",
                "annotator1_decision": "ALLOW",
                "annotator2_decision": "",
            }
        )


def _violations(tmp_path: Path, text: str):
    doc = tmp_path / "report.md"
    doc.write_text(text, encoding="utf-8")
    sheet = tmp_path / "annotation_review_sheet.csv"
    _empty_annotation_sheet(sheet)
    registry = EvidenceRegistry.load(ROOT / "data" / "evidence_registry.json")
    return audit_docs_coherence.find_claim_violations(
        registry, [doc], annotation_sheet=sheet
    )


def test_rejects_confirmatory_wording_attached_to_a_legacy_artifact(tmp_path):
    violations = _violations(
        tmp_path,
        "data/experiment_results.json es nuestra ejecución confirmatoria final.",
    )

    assert len(violations) == 1
    assert "report.md" in violations[0]
    assert "data/experiment_results.json" in violations[0]


def test_rejects_confirmatory_wording_in_the_same_paragraph_as_legacy_artifact(
    tmp_path,
):
    violations = _violations(
        tmp_path,
        (
            "Fuente: data/experiment_results.json\n"
            "Esta es la ejecución confirmatoria final."
        ),
    )

    assert len(violations) == 1
    assert "data/experiment_results.json" in violations[0]

    assert not _violations(
        tmp_path,
        (
            "La metodología prospectiva se describe aquí.\n"
            "La ejecución confirmatoria final usará datos nuevos.\n\n"
            "## Evidencia histórica\n\n"
            "Fuente: data/experiment_results.json"
        ),
    )


def test_does_not_ban_unrelated_methodological_use_of_confirmatory(tmp_path):
    assert not _violations(
        tmp_path,
        "El protocolo confirmatorio futuro requiere congelación prospectiva.",
    )


def test_rejects_general_immunity_or_safety_claims(tmp_path):
    violations = _violations(
        tmp_path,
        "El sistema es inmune a prompt injection y garantiza seguridad total.",
    )

    assert any("general safety or immunity" in item for item in violations)


def test_rejects_concrete_claim_of_safety_against_any_prompt_injection(tmp_path):
    violations = _violations(
        tmp_path,
        "ERP Agent OS es seguro frente a cualquier ataque de prompt injection.",
    )

    assert any("general safety or immunity" in item for item in violations)
    assert not _violations(
        tmp_path,
        (
            "No afirmamos que ERP Agent OS sea seguro frente a cualquier ataque "
            "de prompt injection."
        ),
    )


def test_accepts_an_explicit_disclaimer_of_general_safety(tmp_path):
    assert not _violations(
        tmp_path,
        "Este resultado no prueba inmunidad ni seguridad general frente a ataques.",
    )


def test_accepts_prohibited_wording_listed_in_a_do_not_say_section(tmp_path):
    assert not _violations(
        tmp_path,
        "## Lo que NO se debe decir\n\n- Sistema seguro o inmune a inyección.",
    )


def test_zero_of_1530_requires_scoped_exploratory_three_channel_wording(tmp_path):
    violations = _violations(
        tmp_path,
        "Hubo 0/1530 mutaciones; por tanto el sistema resiste cualquier ataque.",
    )
    assert any("0/1530" in item for item in violations)

    assert not _violations(
        tmp_path,
        (
            "El 0 / 1.530 es un resultado exploratorio de confinamiento en el "
            "arnés de tres canales probado, no evidencia de inmunidad general."
        ),
    )


def test_rejects_human_kappa_claim_while_second_annotation_is_empty(tmp_path):
    violations = _violations(
        tmp_path,
        "El kappa humano interanotador fue 0,82.",
    )

    assert any("human kappa" in item for item in violations)


def test_rejects_ordinary_cohen_kappa_between_annotators_claim(tmp_path):
    violations = _violations(
        tmp_path,
        "El kappa de Cohen entre anotadores fue 0,82.",
    )

    assert any("human kappa" in item for item in violations)
    assert not _violations(
        tmp_path,
        "El kappa de Cohen entre anotadores no se calculó; sigue pendiente.",
    )


def test_accepts_an_explicit_statement_that_human_kappa_is_unavailable(tmp_path):
    assert not _violations(
        tmp_path,
        "El kappa humano sigue pendiente porque no hay segundo anotador disponible.",
    )
