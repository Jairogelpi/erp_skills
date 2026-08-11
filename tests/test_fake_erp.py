"""Focused tests for the deterministic, restorable FakeERP adapter."""

import pytest

from erp_agent_os.adapters import (
    DuplicateRecordError,
    FakeERPAdapter,
    UnknownModelError,
    UnknownRecordError,
)


def test_create_and_get_roundtrip() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    record_id = erp.create("crm.lead", {"name": "Acme"})
    assert erp.get("crm.lead", record_id) == {"name": "Acme"}


def test_disallowed_model_rejected() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    with pytest.raises(UnknownModelError):
        erp.create("res.partner", {"name": "Acme"})


def test_unknown_record_rejected() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    with pytest.raises(UnknownRecordError):
        erp.get("crm.lead", "999")


def test_snapshot_restore_reverts_mutation() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    baseline = erp.snapshot()
    erp.create("crm.lead", {"name": "Acme"})
    erp.restore(baseline)
    with pytest.raises(UnknownRecordError):
        erp.get("crm.lead", "1")


def test_restore_is_independent_copy_not_alias() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    record_id = erp.create("crm.lead", {"name": "Acme"})
    snapshot = erp.snapshot()
    erp.update("crm.lead", record_id, {"name": "Mutated"})
    erp.restore(snapshot)
    assert erp.get("crm.lead", record_id) == {"name": "Acme"}


def test_create_with_explicit_record_id() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    erp.create("crm.lead", {"name": "Acme"}, record_id="OPP-1001")
    assert erp.get("crm.lead", "OPP-1001") == {"name": "Acme"}


def test_create_with_duplicate_explicit_record_id_rejected() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    erp.create("crm.lead", {"name": "Acme"}, record_id="OPP-1001")
    with pytest.raises(DuplicateRecordError):
        erp.create("crm.lead", {"name": "Other"}, record_id="OPP-1001")


def test_list_returns_all_records_for_model() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    erp.create("crm.lead", {"name": "Acme"})
    erp.create("crm.lead", {"name": "Globex"})
    assert {r["name"] for r in erp.list("crm.lead").values()} == {"Acme", "Globex"}


def test_list_result_is_independent_copy() -> None:
    erp = FakeERPAdapter(allowed_models={"crm.lead"})
    erp.create("crm.lead", {"name": "Acme"})
    listed = erp.list("crm.lead")
    listed.clear()
    assert len(erp.list("crm.lead")) == 1
