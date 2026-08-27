"""Product-mode routes mounted on the unified demo app.

No ODOO_URL/OPENROUTER_API_KEY is set in CI, so this exercises exactly
what a laptop with neither configured should see: the catalog and Skill
Studio's sandbox/registry work with no environment at all, and every
Odoo/LLM-dependent route answers 503 rather than crashing the app.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from erp_agent_os.catalog import CATALOG
from erp_agent_os.demo_api import create_demo_app

_VALID_CONTRACT = {
    "skill_id": "demo.create_thing",
    "version": "1.0.0",
    "module": "demo",
    "operation": "create",
    "description": "Create a thing",
    "risk_class": "R1",
    "input_schema": {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    },
    "permissions": {"allowed_roles": ["erp_user"]},
    "preconditions": [],
    "execution": {
        "handler": "demo_proposals.generic_create",
        "timeout_seconds": 10,
        "max_retries": 1,
        "idempotent": True,
    },
    "postconditions": ["exactly_one_new_record"],
    "approval_required_when": [],
    "state": "DRAFT",
}


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ODOO_URL", raising=False)
    monkeypatch.delenv("ODOO_DB", raising=False)
    monkeypatch.delenv("ODOO_API_KEY", raising=False)
    return TestClient(create_demo_app())


# --- Skills Catalog / Skill Detail: no external dependency ----------------


def test_catalog_lists_all_twelve_skills_with_state(client):
    body = client.get("/product/skills").json()
    assert len(body) == len(CATALOG)
    assert {row["skill_id"] for row in body} == {s.skill_id for s in CATALOG}
    assert all(row["state"] == "ACTIVE" for row in body)
    assert all(row["versions"] == ["1.0.0"] for row in body)


def test_skill_detail_includes_registration_history(client):
    skill_id = CATALOG[0].skill_id
    body = client.get(f"/product/skills/{skill_id}").json()
    assert body["skill_id"] == skill_id
    assert body["history"]
    assert body["history"][0]["to"] == "ACTIVE"


def test_skill_detail_404s_for_an_unknown_skill(client):
    response = client.get("/product/skills/does.not_exist")
    assert response.status_code == 404


# --- suspend (quarantine) / retire (deprecate), never delete --------------


def test_quarantine_moves_an_active_skill_out_of_service(client):
    skill_id = CATALOG[0].skill_id
    response = client.post(
        f"/product/skills/{skill_id}/quarantine",
        json={"actor": "tutor", "reason": "suspicious behaviour"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "QUARANTINED"


def test_quarantine_requires_a_named_actor(client):
    skill_id = CATALOG[0].skill_id
    response = client.post(
        f"/product/skills/{skill_id}/quarantine",
        json={"actor": "", "reason": "x"},
    )
    assert response.status_code == 422


def test_quarantined_skill_cannot_be_quarantined_again(client):
    # ALLOWED_TRANSITIONS has QUARANTINED -> {} (terminal): the second
    # call must fail cleanly, not silently succeed or 500.
    skill_id = CATALOG[0].skill_id
    client.post(
        f"/product/skills/{skill_id}/quarantine",
        json={"actor": "tutor", "reason": "first"},
    )
    response = client.post(
        f"/product/skills/{skill_id}/quarantine",
        json={"actor": "tutor", "reason": "second"},
    )
    assert response.status_code == 422


def test_deprecate_moves_an_active_skill_to_deprecated(client):
    skill_id = CATALOG[1].skill_id
    response = client.post(
        f"/product/skills/{skill_id}/deprecate", json={"actor": "tutor"}
    )
    assert response.status_code == 200
    assert response.json()["state"] == "DEPRECATED"


def test_deprecate_requires_a_named_actor(client):
    skill_id = CATALOG[1].skill_id
    response = client.post(f"/product/skills/{skill_id}/deprecate", json={"actor": ""})
    assert response.status_code == 422


def test_deprecating_a_deprecated_skill_is_rejected_not_silently_reapplied(client):
    skill_id = CATALOG[1].skill_id
    client.post(f"/product/skills/{skill_id}/deprecate", json={"actor": "tutor"})
    response = client.post(
        f"/product/skills/{skill_id}/deprecate", json={"actor": "tutor"}
    )
    assert response.status_code == 422


def test_quarantine_404s_for_an_unknown_skill(client):
    response = client.post(
        "/product/skills/does.not_exist/quarantine",
        json={"actor": "tutor", "reason": "x"},
    )
    assert response.status_code == 404


# --- Skill Studio: sandbox/registry work with no LLM key ------------------


def test_test_and_approve_reaches_active_with_no_llm_configured(client):
    test_response = client.post(
        "/product/skill-studio/test", json={"contract": _VALID_CONTRACT}
    )
    assert test_response.status_code == 200
    assert test_response.json()["state"] == "TESTED"

    approve_response = client.post(
        "/product/skill-studio/approve",
        json={
            "skill_id": _VALID_CONTRACT["skill_id"],
            "version": _VALID_CONTRACT["version"],
            "approver": "tutor",
        },
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["state"] == "ACTIVE"

    proposals = client.get("/product/skill-studio/proposals").json()
    assert any(p["skill_id"] == _VALID_CONTRACT["skill_id"] for p in proposals)


def test_approve_without_a_named_approver_is_rejected(client):
    client.post("/product/skill-studio/test", json={"contract": _VALID_CONTRACT})
    response = client.post(
        "/product/skill-studio/approve",
        json={
            "skill_id": _VALID_CONTRACT["skill_id"],
            "version": _VALID_CONTRACT["version"],
            "approver": "",
        },
    )
    assert response.status_code == 422


def test_a_rejected_r4_proposal_never_reaches_the_registry(client):
    bad = dict(_VALID_CONTRACT, risk_class="R4")
    response = client.post("/product/skill-studio/test", json={"contract": bad})
    assert response.status_code == 422


# --- draft/modify need an LLM key; operations need Odoo --------------------


def test_draft_503s_without_an_llm_key(client):
    response = client.post("/product/skill-studio/draft", json={"description": "algo"})
    assert response.status_code == 503


def test_modify_503s_without_an_llm_key(client):
    response = client.post(
        "/product/skill-studio/modify",
        json={"contract": _VALID_CONTRACT, "instruction": "algo"},
    )
    assert response.status_code == 503


def test_operations_run_503s_without_odoo_configured(client):
    response = client.post(
        "/product/operations/run", json={"text": "crea una oportunidad"}
    )
    assert response.status_code == 503


def test_approvals_grant_503s_without_odoo_configured(client):
    response = client.post("/product/approvals", json={"scope": "some.skill"})
    assert response.status_code == 503


# --- unified Approvals/Audit degrade gracefully with no live system -------


def test_approvals_list_is_empty_but_not_an_error_before_odoo_is_configured(client):
    response = client.get("/product/approvals")
    assert response.status_code == 200
    assert response.json() == []


def test_audit_list_reflects_skill_studio_activity_with_no_live_system(client):
    client.post("/product/skill-studio/test", json={"contract": _VALID_CONTRACT})
    client.post(
        "/product/skill-studio/approve",
        json={
            "skill_id": _VALID_CONTRACT["skill_id"],
            "version": _VALID_CONTRACT["version"],
            "approver": "tutor",
        },
    )
    rows = client.get("/product/audit").json()
    kinds = {row["kind"] for row in rows}
    assert kinds == {"skill_evolution"}
    to_states = [
        row["to_state"]
        for row in rows
        if row["skill_id"] == _VALID_CONTRACT["skill_id"]
    ]
    assert "ACTIVE" in to_states


def test_approvals_list_includes_skill_activation_after_approving(client):
    client.post("/product/skill-studio/test", json={"contract": _VALID_CONTRACT})
    client.post(
        "/product/skill-studio/approve",
        json={
            "skill_id": _VALID_CONTRACT["skill_id"],
            "version": _VALID_CONTRACT["version"],
            "approver": "tutor",
        },
    )
    rows = client.get("/product/approvals").json()
    assert any(
        row["kind"] == "skill_activation" and row["to_state"] == "ACTIVE"
        for row in rows
    )
