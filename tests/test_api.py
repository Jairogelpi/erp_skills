from fastapi.testclient import TestClient

from erp_agent_os.api import DEMO_API_KEY, create_app

HEADERS = {"x-api-key": DEMO_API_KEY}


def client() -> TestClient:
    return TestClient(create_app())


def test_missing_api_key_rejected():
    c = client()
    response = c.get("/skills")
    assert response.status_code == 401


def test_list_skills_returns_twelve():
    c = client()
    response = c.get("/skills", headers=HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 12


def test_execute_normal_request_allows_and_returns_correlation_id():
    c = client()
    body = {
        "query_text": "Crea una tarea para llamar al cliente.",
        "proposal": {
            "intent": "tasks.create_task.followup",
            "arguments": {"title": "llamar al cliente"},
            "required_fields": ["title"],
            "confidence": 0.9,
        },
        "role": "erp_user",
        "idempotency_key": "key-1",
    }
    response = c.post("/requests", json=body, headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "ALLOW"
    assert payload["selected_skill_id"] == "tasks.create_task"
    assert payload["correlation_id"]


def test_execute_missing_field_clarifies():
    c = client()
    body = {
        "query_text": "Crea una tarea",
        "proposal": {
            "intent": "tasks.create_task.followup",
            "arguments": {},
            "required_fields": ["title"],
            "confidence": 0.9,
        },
        "role": "erp_user",
        "idempotency_key": "key-1",
    }
    response = c.post("/requests", json=body, headers=HEADERS)
    assert response.json()["decision"] == "CLARIFY"


def test_audit_endpoint_reflects_prior_execution():
    c = client()
    body = {
        "query_text": "Crea una tarea para llamar al cliente.",
        "proposal": {
            "intent": "tasks.create_task.followup",
            "arguments": {"title": "llamar al cliente"},
            "required_fields": ["title"],
            "confidence": 0.9,
        },
        "role": "erp_user",
        "idempotency_key": "key-1",
    }
    response = c.post("/requests", json=body, headers=HEADERS)
    correlation_id = response.json()["correlation_id"]
    response = c.get(f"/audit/{correlation_id}", headers=HEADERS)
    assert response.json()["events"] == ["ALLOW"]


def test_grant_approval_returns_expiry():
    c = client()
    response = c.post(
        "/approvals",
        json={
            "actor": "manager1",
            "scope": "crm.update_expected_revenue",
            "ttl_seconds": 60,
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["actor"] == "manager1"


def test_rate_limit_enforced_after_limit_exceeded():
    from erp_agent_os.api import RATE_LIMIT_PER_MINUTE

    c = client()
    for _ in range(RATE_LIMIT_PER_MINUTE):
        c.get("/skills", headers=HEADERS)
    response = c.get("/skills", headers=HEADERS)
    assert response.status_code == 429
