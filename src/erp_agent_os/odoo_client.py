"""Odoo 19 external JSON-2 API adapter (CLAUDE.md §26, post-core demo).

Scope: this is the post-core Odoo 19 demonstration adapter, NOT part of
the confirmatory core. `FakeERPAdapter` remains mandatory for the
confirmatory A/B/C experiment (§14); this module exists only to
demonstrate the same skill contract executing against a real ERP.

Same public method surface as `FakeERPAdapter` (`create`/`get`/`update`/
`list`) so a skill handler written against one works against the other
without change -- but no `snapshot`/`restore`: those exist on
`FakeERPAdapter` only to reset state between confirmatory-experiment
repetitions, and would be actively dangerous to offer against a real
database (nothing should ever roll back live production-adjacent data
via this adapter).

Controls per §26:
- **allowlist of models AND fields**: unlisted fields are stripped from
  both write payloads and read responses before this adapter's caller
  ever sees them -- an unlisted field cannot reach or leave Odoo through
  this adapter, even if a caller tries to pass one.
- **no delete**: the method surface has no `unlink` call at all,
  structurally, not just by convention.
- **timeout**: every HTTP call is bounded.
- **redacted logging**: `logger.info` never includes field values, only
  model/method/record-id/field-name shape.
- **API key from environment only**: never read from or written to a
  committed file (see `MissingApiKeyError`, mirrors `groq_client.py`).
"""

import logging
import os
from typing import Any

import httpx

from erp_agent_os.adapters import UnknownModelError, UnknownRecordError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 20

# Re-exported so callers of this module never need to import adapters.py
# too: Runtime.execute() catches these by class identity (see
# runtime.py), so raising the *same* classes here -- not lookalikes with
# the same name -- is what makes Odoo19Adapter a genuine drop-in
# replacement for FakeERPAdapter, not just a duck-typed one that happens
# to break error handling.
__all__ = [
    "MissingCredentialsError",
    "OdooApiError",
    "Odoo19Adapter",
    "UnknownFieldError",
    "UnknownModelError",
    "UnknownRecordError",
]


class MissingCredentialsError(RuntimeError):
    """Raised when ODOO_URL/ODOO_DB/ODOO_API_KEY are not all set."""


class UnknownFieldError(ValueError):
    """Raised when a write includes a field outside that model's allowlist."""


class OdooApiError(RuntimeError):
    """Raised when Odoo's JSON-2 API returns a 4xx/5xx error body."""


class Odoo19Adapter:
    """Allowlisted read/create/update against a real Odoo 19 instance.

    `allowed_fields` maps model -> the only field names this adapter
    will ever send or return for that model. A model present in
    `allowed_fields` but absent from a call's own filtering is still
    fully allowlisted; there is no way to request an unlisted field.
    """

    def __init__(
        self,
        allowed_fields: dict[str, frozenset[str]],
        *,
        url: str | None = None,
        database: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        url = url or os.environ.get("ODOO_URL")
        database = database or os.environ.get("ODOO_DB")
        api_key = api_key or os.environ.get("ODOO_API_KEY")
        if not url or not database or not api_key:
            raise MissingCredentialsError(
                "ODOO_URL, ODOO_DB and ODOO_API_KEY must all be set "
                "(e.g. in a local .env file, never committed) before "
                "constructing Odoo19Adapter."
            )
        self._allowed_fields = {
            model: frozenset(fields) for model, fields in allowed_fields.items()
        }
        self._client = httpx.Client(
            base_url=url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Odoo-Database": database,
                "Content-Type": "application/json",
                "User-Agent": "erp-agent-os",
            },
            timeout=timeout_seconds,
        )

    def _require_model(self, model: str) -> frozenset[str]:
        if model not in self._allowed_fields:
            raise UnknownModelError(model)
        return self._allowed_fields[model]

    def _require_allowed(self, model: str, fields: dict[str, Any]) -> None:
        allowed = self._require_model(model)
        extra = set(fields) - allowed
        if extra:
            raise UnknownFieldError(f"{model}: fields not allowlisted: {sorted(extra)}")

    def _call(self, model: str, method: str, body: dict[str, Any]) -> Any:
        logger.info(
            "odoo call model=%s method=%s ids=%s", model, method, body.get("ids")
        )
        response = self._client.post(f"/json/2/{model}/{method}", json=body)
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise OdooApiError(f"{model}/{method} failed: {detail}")
        return response.json()

    def create(self, model: str, fields: dict[str, Any]) -> str:
        self._require_allowed(model, fields)
        result = self._call(model, "create", {"vals_list": [fields]})
        return str(result[0])

    def get(self, model: str, record_id: str) -> dict[str, Any]:
        allowed = self._require_model(model)
        result = self._call(
            model, "read", {"ids": [int(record_id)], "fields": sorted(allowed)}
        )
        if not result:
            raise UnknownRecordError(record_id)
        record = dict(result[0])
        record.pop("id", None)
        return record

    def list(self, model: str, *, limit: int = 100) -> dict[str, dict[str, Any]]:
        allowed = self._require_model(model)
        result = self._call(
            model,
            "search_read",
            {"domain": [], "fields": sorted(allowed), "limit": limit},
        )
        out: dict[str, dict[str, Any]] = {}
        for record in result:
            record_id = str(record.pop("id"))
            out[record_id] = record
        return out

    def update(self, model: str, record_id: str, fields: dict[str, Any]) -> None:
        self._require_allowed(model, fields)
        self._call(model, "write", {"ids": [int(record_id)], "vals": fields})
