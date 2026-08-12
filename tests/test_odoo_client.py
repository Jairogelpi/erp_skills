from unittest.mock import MagicMock

import httpx
import pytest

from erp_agent_os.odoo_client import (
    MissingCredentialsError,
    Odoo19Adapter,
    OdooApiError,
    UnknownFieldError,
    UnknownModelError,
)

ALLOWED = {"res.partner": frozenset({"name", "email"})}


def _adapter(**overrides) -> Odoo19Adapter:
    kwargs = dict(
        allowed_fields=ALLOWED,
        url="https://example.odoo.com",
        database="mydb",
        api_key="test-key",
    )
    kwargs.update(overrides)
    return Odoo19Adapter(**kwargs)


def _fake_response(body, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status, json=body, request=httpx.Request("POST", "https://example.odoo.com")
    )


def test_missing_credentials_raises_not_falls_back(monkeypatch):
    monkeypatch.delenv("ODOO_URL", raising=False)
    monkeypatch.delenv("ODOO_DB", raising=False)
    monkeypatch.delenv("ODOO_API_KEY", raising=False)
    with pytest.raises(MissingCredentialsError):
        Odoo19Adapter(allowed_fields=ALLOWED)


def test_unknown_model_rejected_before_any_http_call():
    adapter = _adapter()
    adapter._client.post = MagicMock()
    with pytest.raises(UnknownModelError):
        adapter.get("crm.lead", "1")
    adapter._client.post.assert_not_called()


def test_unallowlisted_field_rejected_on_create_before_any_http_call():
    adapter = _adapter()
    adapter._client.post = MagicMock()
    with pytest.raises(UnknownFieldError):
        adapter.create("res.partner", {"name": "Acme", "secret_field": "x"})
    adapter._client.post.assert_not_called()


def test_unallowlisted_field_rejected_on_update_before_any_http_call():
    adapter = _adapter()
    adapter._client.post = MagicMock()
    with pytest.raises(UnknownFieldError):
        adapter.update("res.partner", "1", {"vat_number": "ES123"})
    adapter._client.post.assert_not_called()


def test_create_sends_only_allowlisted_fields_and_returns_id():
    adapter = _adapter()
    adapter._client.post = MagicMock(return_value=_fake_response([42]))

    record_id = adapter.create("res.partner", {"name": "Acme", "email": "a@acme.test"})

    assert record_id == "42"
    call = adapter._client.post.call_args
    assert call.args[0] == "/json/2/res.partner/create"
    assert call.kwargs["json"] == {
        "vals_list": [{"name": "Acme", "email": "a@acme.test"}]
    }


def test_get_reads_only_allowlisted_fields_and_strips_id():
    adapter = _adapter()
    adapter._client.post = MagicMock(
        return_value=_fake_response(
            [{"id": 42, "name": "Acme", "email": "a@acme.test"}]
        )
    )

    record = adapter.get("res.partner", "42")

    assert record == {"name": "Acme", "email": "a@acme.test"}
    call = adapter._client.post.call_args
    assert call.kwargs["json"] == {"ids": [42], "fields": ["email", "name"]}


def test_get_missing_record_raises_key_error():
    adapter = _adapter()
    adapter._client.post = MagicMock(return_value=_fake_response([]))
    with pytest.raises(KeyError):
        adapter.get("res.partner", "999")


def test_list_returns_records_keyed_by_id_without_id_field():
    adapter = _adapter()
    adapter._client.post = MagicMock(
        return_value=_fake_response(
            [
                {"id": 1, "name": "Acme", "email": "a@acme.test"},
                {"id": 2, "name": "Beta", "email": "b@beta.test"},
            ]
        )
    )

    records = adapter.list("res.partner")

    assert records == {
        "1": {"name": "Acme", "email": "a@acme.test"},
        "2": {"name": "Beta", "email": "b@beta.test"},
    }
    assert adapter._client.post.call_args.kwargs["json"] == {
        "domain": [],
        "fields": ["email", "name"],
        "limit": 100,
        "offset": 0,
        "order": "id asc",
    }


def test_unbounded_list_paginates_until_every_record_is_returned():
    adapter = _adapter()
    source = [
        {"id": record_id, "name": f"Partner {record_id}", "email": None}
        for record_id in range(1, 206)
    ]

    def page(_path, *, json):
        offset = json["offset"]
        limit = json["limit"]
        return _fake_response(source[offset : offset + limit])

    adapter._client.post = MagicMock(side_effect=page)

    records = adapter.list("res.partner")

    assert len(records) == 205
    assert list(records) == [str(record_id) for record_id in range(1, 206)]
    offsets = [
        call.kwargs["json"]["offset"]
        for call in adapter._client.post.call_args_list
    ]
    assert offsets == [0, 100, 200]
    assert all(
        call.kwargs["json"]["order"] == "id asc"
        for call in adapter._client.post.call_args_list
    )


def test_bounded_list_returns_exact_limit_across_pages():
    adapter = _adapter()
    source = [
        {"id": record_id, "name": f"Partner {record_id}", "email": None}
        for record_id in range(1, 206)
    ]

    def page(_path, *, json):
        offset = json["offset"]
        limit = json["limit"]
        return _fake_response(source[offset : offset + limit])

    adapter._client.post = MagicMock(side_effect=page)

    records = adapter.list("res.partner", limit=150)

    assert len(records) == 150
    assert [call.kwargs["json"] for call in adapter._client.post.call_args_list] == [
        {
            "domain": [],
            "fields": ["email", "name"],
            "limit": 100,
            "offset": 0,
            "order": "id asc",
        },
        {
            "domain": [],
            "fields": ["email", "name"],
            "limit": 50,
            "offset": 100,
            "order": "id asc",
        },
    ]


def test_list_does_not_mutate_transport_response_records():
    adapter = _adapter()
    response_records = [{"id": 1, "name": "Acme", "email": "a@acme.test"}]
    adapter._call = MagicMock(return_value=response_records)

    adapter.list("res.partner")

    assert response_records == [
        {"id": 1, "name": "Acme", "email": "a@acme.test"}
    ]


@pytest.mark.parametrize(
    "response_body",
    [
        {"records": "not-a-list", "secret": "do not expose"},
        [{"name": "missing id", "secret": "do not expose"}],
    ],
)
def test_list_rejects_malformed_response_without_leaking_it(response_body):
    adapter = _adapter()
    adapter._client.post = MagicMock(return_value=_fake_response(response_body))

    with pytest.raises(OdooApiError) as error:
        adapter.list("res.partner")

    assert str(error.value) == "malformed Odoo list response"
    assert "secret" not in str(error.value)


def test_list_rejects_non_json_response_without_leaking_it():
    adapter = _adapter()
    adapter._client.post = MagicMock(
        return_value=httpx.Response(
            200,
            content=b"secret invalid response",
            request=httpx.Request("POST", "https://example.odoo.com"),
        )
    )

    with pytest.raises(OdooApiError) as error:
        adapter.list("res.partner")

    assert str(error.value) == "malformed Odoo list response"
    assert "secret" not in str(error.value)


def test_list_rejects_nonprogressing_duplicate_page():
    adapter = _adapter()
    page = [
        {"id": record_id, "name": f"Partner {record_id}", "email": None}
        for record_id in range(1, 101)
    ]
    adapter._client.post = MagicMock(
        side_effect=[_fake_response(page), _fake_response(page)]
    )

    with pytest.raises(OdooApiError) as error:
        adapter.list("res.partner")

    assert str(error.value) == "Odoo list pagination did not advance"
    assert adapter._client.post.call_count == 2


def test_update_sends_only_allowlisted_fields():
    adapter = _adapter()
    adapter._client.post = MagicMock(return_value=_fake_response(True))

    adapter.update("res.partner", "42", {"email": "new@acme.test"})

    call = adapter._client.post.call_args
    assert call.args[0] == "/json/2/res.partner/write"
    assert call.kwargs["json"] == {"ids": [42], "vals": {"email": "new@acme.test"}}


def test_error_response_raises_odoo_api_error():
    adapter = _adapter()
    adapter._client.post = MagicMock(
        return_value=_fake_response(
            {"name": "werkzeug.exceptions.Unauthorized", "message": "Invalid apikey"},
            status=401,
        )
    )
    with pytest.raises(OdooApiError, match="Invalid apikey"):
        adapter.get("res.partner", "1")


def test_no_unlink_method_exists_at_all():
    # Structural, not conventional: irreversible deletion is not
    # reachable through this adapter's public surface (CLAUDE.md R4).
    assert not hasattr(Odoo19Adapter, "unlink")
    assert not hasattr(Odoo19Adapter, "delete")


def test_unknown_model_and_record_errors_are_the_same_classes_runtime_catches():
    # Runtime.execute() imports UnknownModelError/UnknownRecordError
    # from adapters.py and catches them by class identity. If
    # Odoo19Adapter defined lookalike classes with the same name
    # instead of reusing these, Runtime would not catch them and an
    # Odoo failure would crash System C's whole request instead of
    # surfacing as a normal handler_error -- this is what makes
    # Odoo19Adapter a genuine drop-in for FakeERPAdapter, not just a
    # duck-typed one that happens to break error handling.
    from erp_agent_os.adapters import UnknownModelError as AdaptersUnknownModelError
    from erp_agent_os.adapters import UnknownRecordError as AdaptersUnknownRecordError
    from erp_agent_os.odoo_client import UnknownModelError as OdooUnknownModelError

    assert OdooUnknownModelError is AdaptersUnknownModelError

    adapter = _adapter()
    adapter._client.post = MagicMock(return_value=_fake_response([]))
    with pytest.raises(AdaptersUnknownRecordError):
        adapter.get("res.partner", "999")


def test_write_demos_refuse_production_and_staging(monkeypatch):
    # Not hypothetical: this project's dev machine has ODOO_URL set to
    # the business's *production* instance as a persistent user-level
    # environment variable, and the adapter reads os.environ directly.
    # A demo run with no arguments would have written test opportunities
    # into a live ERP.
    from erp_agent_os.odoo_client import (
        NotADevelopmentInstanceError,
        require_development_instance,
    )

    dev = "https://esenssi-aromas-dev-pruebas-limpio-36154343.dev.odoo.com"
    assert require_development_instance(dev) == dev

    for refused in (
        "https://esenssi-aromas.odoo.com",  # production
        # Odoo.sh staging lives under .dev.odoo.com but is a clone of
        # production data, so it must be refused too.
        "https://esenssi-aromas-staging-35351235.dev.odoo.com",
        "",
    ):
        with pytest.raises(NotADevelopmentInstanceError):
            require_development_instance(refused)


def test_guard_falls_back_to_the_environment_when_no_url_is_passed(monkeypatch):
    from erp_agent_os.odoo_client import (
        NotADevelopmentInstanceError,
        require_development_instance,
    )

    monkeypatch.setenv("ODOO_URL", "https://esenssi-aromas.odoo.com")
    with pytest.raises(NotADevelopmentInstanceError):
        require_development_instance()

    monkeypatch.setenv("ODOO_URL", "https://x-1234.dev.odoo.com")
    assert require_development_instance() == "https://x-1234.dev.odoo.com"
