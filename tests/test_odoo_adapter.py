import httpx

from erp_agent_os.adapters import ErpAdapter
from erp_agent_os.odoo_client import Odoo19Adapter


def test_odoo_adapter_structurally_supports_full_list_and_record_reread():
    calls: list[tuple[str, dict]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = __import__("json").loads(request.content)
        calls.append((request.url.path, body))
        if request.url.path.endswith("/search_read"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 42,
                        "expected_revenue": 15000.0,
                        "name": "Oportunidad: Acme",
                        "type": "opportunity",
                    }
                ],
            )
        return httpx.Response(
            200,
            json=[
                {
                    "id": 42,
                    "expected_revenue": 15000.0,
                    "name": "Oportunidad: Acme",
                    "type": "opportunity",
                }
            ],
        )

    adapter = Odoo19Adapter(
        allowed_fields={
            "crm.lead": frozenset({"expected_revenue", "name", "type"})
        },
        url="https://local.invalid",
        database="fixture",
        api_key="fixture-key",
    )
    adapter._client.close()
    adapter._client = httpx.Client(
        base_url="https://local.invalid", transport=httpx.MockTransport(respond)
    )

    assert isinstance(adapter, ErpAdapter)
    listed = adapter.list("crm.lead")
    reread = adapter.get("crm.lead", "42")

    assert listed == {"42": reread}
    assert calls == [
        (
            "/json/2/crm.lead/search_read",
            {
                "domain": [],
                "fields": ["expected_revenue", "name", "type"],
                "limit": 100,
            },
        ),
        (
            "/json/2/crm.lead/read",
            {
                "ids": [42],
                "fields": ["expected_revenue", "name", "type"],
            },
        ),
    ]
