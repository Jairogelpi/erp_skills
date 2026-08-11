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
