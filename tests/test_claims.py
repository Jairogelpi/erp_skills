import json
from pathlib import Path

from erp_agent_os.claims import REPORTING_DOCUMENTS, validate_claim_contract

ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    registry = json.loads(
        (ROOT / "data" / "evidence_registry.json").read_text(encoding="utf-8")
    )
    documents = {
        name: (ROOT / name).read_text(encoding="utf-8") for name in REPORTING_DOCUMENTS
    }
    return registry, documents


def test_current_claim_contract_is_consistent():
    registry, documents = _inputs()

    assert validate_claim_contract(registry, documents) == []


def test_missing_disclaimer_is_a_release_blocker():
    registry, documents = _inputs()
    documents["README.md"] = documents["README.md"].replace(
        "EVIDENCE-STATUS: no-valid-confirmatory-conclusion", "status missing"
    )

    errors = validate_claim_contract(registry, documents)

    assert any("README.md" in error and "EVIDENCE-STATUS" in error for error in errors)


def test_confirmed_hypothesis_status_is_a_release_blocker():
    registry, documents = _inputs()
    registry["hypotheses"]["H1"]["status"] = "confirmed"

    errors = validate_claim_contract(registry, documents)

    assert any("H1" in error and "confirmed" in error for error in errors)


def test_unregistered_result_citation_is_a_release_blocker():
    registry, documents = _inputs()
    documents["README.md"] += "\n`data/unregistered_result.json`\n"

    errors = validate_claim_contract(registry, documents)

    assert any("data/unregistered_result.json" in error for error in errors)
