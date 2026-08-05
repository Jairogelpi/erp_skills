from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.handlers import HANDLERS, SKILL_MODELS


def test_every_catalog_skill_has_a_handler():
    assert set(HANDLERS) == set(CATALOG_BY_ID)


def test_every_catalog_skill_has_a_model_mapping():
    assert set(SKILL_MODELS) == set(CATALOG_BY_ID)


def test_create_opportunity_then_update_revenue_roundtrip():
    erp = FakeERPAdapter(allowed_models={"crm.opportunity"})
    record_id = HANDLERS["crm.create_opportunity"](
        erp, {"customer_name": "Acme", "expected_revenue": "12000"}
    )
    HANDLERS["crm.update_expected_revenue"](
        erp, {"opportunity_id": record_id, "expected_revenue": "18000"}
    )
    assert erp.get("crm.opportunity", record_id)["expected_revenue"] == "18000"


def test_search_contact_finds_seeded_record():
    erp = FakeERPAdapter(allowed_models={"contacts.contact"})
    erp.create("contacts.contact", {"customer_name": "Acme", "email": "a@acme.com"})
    result = HANDLERS["contacts.search_contact"](erp, {"query": "Acme"})
    assert len(result["results"]) == 1


def test_check_availability_reads_seeded_stock():
    erp = FakeERPAdapter(allowed_models={"product.product"})
    erp.create("product.product", {"stock": 42}, record_id="Laptop Pro 14")
    result = HANDLERS["inventory.check_availability"](
        erp, {"product_name": "Laptop Pro 14"}
    )
    assert result["available_units"] == 42
