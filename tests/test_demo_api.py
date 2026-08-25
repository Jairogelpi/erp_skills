"""HTTP surface of the comparative demo."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from erp_agent_os.demo_api import create_demo_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_demo_app())


def test_evidence_payload_is_strictly_valid_json(client):
    """No NaN/Infinity literals may reach the browser.

    Python's json module emits them happily; `JSON.parse` rejects the
    entire response, so one unsanitised p-value would blank the whole
    evidence panel.
    """
    response = client.get("/demo/evidence")
    assert response.status_code == 200

    def reject(literal: str) -> None:
        raise AssertionError(f"non-JSON literal in payload: {literal}")

    json.loads(response.text, parse_constant=reject)


def test_evidence_reports_the_frozen_campaign_identity(client):
    body = client.get("/demo/evidence").json()
    assert body["protocol_tag"] == "tfm-protocol-v2.1.2"
    assert body["campaign_state"] == "RUN_COMPLETED"
    assert body["observation_count"] > 0
    assert body["disclaimer"]


def test_run_returns_all_three_systems(client):
    body = client.post("/demo/run", json={"scenario": "approval"}).json()
    assert set(body["systems"]) == {"A", "B", "C"}
    assert body["systems"]["C"]["policy_decision"] == "REQUIRE_APPROVAL"


def test_approval_then_rerun_flips_the_decision(client):
    run = client.post("/demo/run", json={"scenario": "approval"}).json()
    request_id = run["request_id"]
    approval = client.post(
        f"/demo/approval/{request_id}", json={"actor": "Demo Administrator"}
    )
    assert approval.status_code == 200
    assert approval.json()["actor"] == "Demo Administrator"

    rerun = client.post(f"/demo/rerun/{request_id}").json()
    assert rerun["systems"]["C"]["policy_decision"] == "ALLOW"
    assert rerun["systems"]["C"]["postcondition_verified"] is True


def test_erp_state_exposes_before_after_for_every_system(client):
    run = client.post("/demo/run", json={"scenario": "approval"}).json()
    state = client.get(f"/demo/erp-state/{run['request_id']}").json()
    assert state["verified_by"] == "independent ERP re-read"
    for name in ("A", "B", "C"):
        assert "before" in state["systems"][name]
        assert "after" in state["systems"][name]


def test_audit_comparison_shows_seven_facts_per_system(client):
    run = client.post("/demo/run", json={"scenario": "approval"}).json()
    audit = client.get(f"/demo/audit/{run['request_id']}").json()
    assert len(audit["fact_names"]) == 7
    assert set(audit["rows"]) == {"A", "B", "C"}
    # The governed system reconstructs at least as much as the others --
    # the property H7 measures, on this one run.
    assert audit["coverage"]["C"] >= audit["coverage"]["A"]


def test_paraphrases_carry_a_disclaimer_separating_them_from_h3a(client):
    run = client.post("/demo/run", json={"scenario": "approval"}).json()
    body = client.post(f"/demo/paraphrases/{run['request_id']}").json()
    assert len(body["variants"]) == 3
    assert "1,192" in body["disclaimer"]


def test_unknown_request_id_is_404_not_a_blank_run(client):
    assert client.post("/demo/rerun/does-not-exist").status_code == 404
    assert client.get("/demo/audit/does-not-exist").status_code == 404


def test_live_odoo_backend_is_refused_by_this_api(client):
    """A second connection path to a real ERP is how a production write
    happens by accident; the guarded script stays the only one."""
    response = client.post("/demo/run", json={"scenario": "normal", "backend": "odoo"})
    assert response.status_code == 400


def test_presets_are_served_for_the_ui_buttons(client):
    presets = client.get("/demo/presets").json()
    assert {p["id"] for p in presets} >= {"normal", "approval", "security"}
