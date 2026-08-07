from unittest.mock import MagicMock

from erp_agent_os.odoo_handlers import (
    crm_create_opportunity,
    crm_update_expected_revenue,
    opportunity_created_correctly,
)


def test_crm_create_opportunity_sends_real_odoo_field_names():
    erp = MagicMock()
    erp.create.return_value = "42"

    result = crm_create_opportunity(
        erp, {"customer_name": "Acme", "expected_revenue": 15000}
    )

    assert result == "42"
    erp.create.assert_called_once_with(
        "crm.lead",
        {
            "name": "Oportunidad: Acme",
            "partner_name": "Acme",
            "expected_revenue": 15000,
            "type": "opportunity",
        },
    )


def test_crm_update_expected_revenue_targets_the_right_record():
    erp = MagicMock()

    result = crm_update_expected_revenue(
        erp, {"opportunity_id": "42", "expected_revenue": 20000}
    )

    assert result == "42"
    erp.update.assert_called_once_with("crm.lead", "42", {"expected_revenue": 20000})


def test_opportunity_created_correctly_verifies_type_and_amount():
    erp = MagicMock()
    erp.get.return_value = {"type": "opportunity", "expected_revenue": 15000.0}

    assert opportunity_created_correctly(erp, "42", 15000) is True


def test_opportunity_created_correctly_fails_on_amount_mismatch():
    erp = MagicMock()
    erp.get.return_value = {"type": "opportunity", "expected_revenue": 999.0}

    assert opportunity_created_correctly(erp, "42", 15000) is False


def test_opportunity_created_correctly_fails_if_not_typed_as_opportunity():
    erp = MagicMock()
    erp.get.return_value = {"type": "lead", "expected_revenue": 15000.0}

    assert opportunity_created_correctly(erp, "42", 15000) is False
