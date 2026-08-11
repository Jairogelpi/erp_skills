import pytest
from pydantic import ValidationError

from erp_agent_os.parser import IntentProposal, structure_proposal


def test_missing_fields_derived_from_required_list():
    proposal = structure_proposal(
        intent="crm.create_opportunity",
        arguments={"customer_name": "Acme", "expected_revenue": "  "},
        required_fields=["customer_name", "expected_revenue", "email"],
        confidence=0.9,
    )
    assert proposal.missing_fields == ["expected_revenue", "email"]


def test_all_required_fields_present_yields_no_missing():
    proposal = structure_proposal(
        intent="crm.create_opportunity",
        arguments={"customer_name": "Acme"},
        required_fields=["customer_name"],
        confidence=0.9,
    )
    assert proposal.missing_fields == []


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_out_of_range_rejected(confidence):
    with pytest.raises(ValidationError):
        IntentProposal(
            intent="x",
            arguments={},
            missing_fields=[],
            confidence=confidence,
            constraints=[],
        )


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        IntentProposal(
            intent="x",
            arguments={},
            missing_fields=[],
            confidence=0.5,
            constraints=[],
            extra="not allowed",
        )
