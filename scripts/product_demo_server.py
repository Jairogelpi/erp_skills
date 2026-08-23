"""Live product demo: real frontend, real backend, real Odoo.

Not a simulation and not FakeERPAdapter -- every request typed into the
frontend runs through the SAME governed pipeline (SystemC -> Runtime ->
Odoo19Adapter) that scripts/odoo_governed_demo.py already proved works,
wired to real argument extraction (OpenRouterClient, the same client the
v2.1 confirmatory campaign used) instead of hand-built proposals, so
arbitrary typed text works, not just the two hardcoded demo queries.

Explicit choice, made by the user after being told the alternative
(FakeERPAdapter by default, Odoo opt-in): this server targets real Odoo
on every request, unconditionally. The one guardrail that is NOT
negotiable regardless of that choice: require_development_instance()
still runs before a single write leaves this process, exactly as in
odoo_governed_demo.py -- it refuses production and staging hosts. This
server also binds to 127.0.0.1 only (see main()), never 0.0.0.0, so it
is not reachable from the network while it runs.

Only 2 of the 12 catalog skills have real Odoo handlers
(odoo_handlers.py): crm.create_opportunity, crm.update_expected_revenue.
A request that resolves to any other skill is reported honestly as
"not wired to real Odoo yet" rather than silently failing or faking a
result -- see _handle_request's final branch.

    export ODOO_URL=... ODOO_DB=... ODOO_API_KEY=... OPENROUTER_API_KEY=...
    uv run python scripts/product_demo_server.py
    # open http://127.0.0.1:8420
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from erp_agent_os import odoo_handlers
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.odoo_client import Odoo19Adapter, require_development_instance
from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS
from erp_agent_os.openrouter_client import MissingApiKeyError, OpenRouterClient
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_c import SystemC

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("product_demo")

FRONTEND_DIR = Path(__file__).resolve().parent / "product_demo_frontend"

# Only these two have a real Odoo handler wired up (odoo_handlers.py).
# The catalog has 12; the frontend must not imply the other 10 write
# anywhere real.
ODOO_WIRED_SKILLS = {"crm.create_opportunity", "crm.update_expected_revenue"}


class RequestBody(BaseModel):
    text: str
    role: str = "erp_user"


class ApprovalBody(BaseModel):
    scope: str
    ttl_seconds: int = 120


def _build_system() -> tuple[SystemC, TfidfRetriever, ApprovalService, AuditStore]:
    # Refuses production and staging before a single write leaves this
    # process -- see require_development_instance's own docstring for
    # the near-miss that made this mandatory, not optional.
    target = require_development_instance()
    logger.info("target Odoo instance (verified development): %s", target)

    erp = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})
    runtime: Runtime = Runtime(erp)
    for skill_id in ODOO_WIRED_SKILLS:
        handler_name = skill_id.split(".", 1)[1]
        handler = getattr(odoo_handlers, f"crm_{handler_name}")
        runtime.register(skill_id, CATALOG_BY_ID[skill_id].version, handler)

    retriever = TfidfRetriever(CATALOG)
    audit = AuditStore()
    approval = ApprovalService()
    system = SystemC(erp, runtime, retriever, audit, approval)
    return system, retriever, approval, audit


def _extraction_client() -> OpenRouterClient:
    try:
        return OpenRouterClient()
    except MissingApiKeyError as exc:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. This server extracts arguments "
            "from free text with a real LLM call -- export it (same key "
            "the v2.1 confirmatory campaign used) before starting."
        ) from exc


def create_app() -> FastAPI:
    system, retriever, approval, audit = _build_system()
    llm = _extraction_client()

    app = FastAPI(title="ERP Agent OS — product demo")
    # Same-origin only in practice (frontend is served by this app), but
    # CORS is opened for localhost so the frontend can also be opened as
    # a plain file:// during development without a fetch failure.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8420", "null"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/skills")
    def list_skills() -> list[dict[str, Any]]:
        return [
            {
                "skill_id": s.skill_id,
                "description": s.description,
                "risk_class": s.risk_class.value,
                "required_fields": s.input_schema["required"],
                "allowed_roles": list(s.permissions.allowed_roles),
                "odoo_wired": s.skill_id in ODOO_WIRED_SKILLS,
            }
            for s in CATALOG
        ]

    @app.post("/api/request")
    def handle_request(body: RequestBody) -> dict[str, Any]:
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "empty request text")

        correlation_id = str(uuid.uuid4())
        # Deterministic on (text, role) so literally resubmitting the
        # same request demonstrates idempotent replay live, the same
        # property demo_completa.py's scene 8 shows against FakeERP.
        idempotency_key = hashlib.sha256(f"{text}|{body.role}".encode()).hexdigest()[
            :16
        ]

        candidates = retriever.rank(text, role=body.role)
        candidate_view = [
            {"skill_id": c.skill.skill_id, "score": round(c.score, 4)}
            for c in candidates[:5]
        ]

        if not candidates:
            audit.record_abstention(correlation_id, ["no candidate for this role"])
            return {
                "correlation_id": correlation_id,
                "stage": "retrieval",
                "decision": "ABSTAIN",
                "candidates": candidate_view,
                "reasons": ["no candidate for this role"],
            }

        top = candidates[0].skill

        # SystemC.handle() calls Runtime.execute() for any skill that
        # clears retrieval, and Runtime.execute() looks up a registered
        # handler unconditionally (found live: it raised
        # UnregisteredHandlerError, an unhandled 500, for a real R0
        # request that matched an un-wired skill). Only 2 of 12 skills
        # have a real Odoo handler (ODOO_WIRED_SKILLS) -- checking here,
        # before calling handle() at all, is what keeps this demo from
        # crashing live on an honest, ordinary request.
        if top.skill_id not in ODOO_WIRED_SKILLS:
            return {
                "correlation_id": correlation_id,
                "decision": "NOT_WIRED",
                "selected_skill_id": top.skill_id,
                "candidates": candidate_view,
                "reasons": [],
                "note": (
                    f"'{top.skill_id}' es la mejor candidata, pero solo "
                    f"{sorted(ODOO_WIRED_SKILLS)} tienen handler real de "
                    "Odoo en esta demo -- no se llama a extracción, "
                    "política ni ejecución para evitar simular un "
                    "resultado que no se produjo de verdad."
                ),
            }

        required = top.input_schema["required"]
        extraction = llm.extract_arguments(text, required) if required else None
        arguments = dict(extraction.arguments) if extraction else {}
        proposal = structure_proposal(
            f"{top.module}.{top.skill_id.split('.', 1)[1]}",
            arguments,
            required,
            confidence=0.9,
        )

        result = system.handle(
            correlation_id, text, proposal, body.role, idempotency_key
        )

        response: dict[str, Any] = {
            "correlation_id": correlation_id,
            "decision": result.decision,
            "selected_skill_id": result.selected_skill_id,
            "reasons": list(result.reasons),
            "candidates": candidate_view,
            "extracted_arguments": arguments,
            "extraction_tokens": (
                {
                    "prompt": extraction.prompt_tokens,
                    "completion": extraction.completion_tokens,
                }
                if extraction
                else None
            ),
            "odoo_wired": result.selected_skill_id in ODOO_WIRED_SKILLS
            if result.selected_skill_id
            else None,
        }

        if result.decision == "CLARIFY" or result.decision == "ABSTAIN":
            return response

        if result.execution is None:
            return response  # REQUIRE_APPROVAL / DENY: nothing executed

        response["execution"] = {
            "output": result.execution.output,
            "idempotent_replay": result.execution.idempotent_replay,
            "handler_error": result.execution.handler_error,
        }

        # Never trust the pipeline's own say-so: re-read Odoo independently,
        # with a fresh adapter instance, the same discipline
        # odoo_governed_demo.py and the manual check earlier this session
        # both used.
        if result.decision == "ALLOW" and result.execution.output:
            fresh = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})
            response["independent_reread"] = fresh.get(
                "crm.lead", str(result.execution.output)
            )

        return response

    @app.post("/api/approvals")
    def grant_approval(body: ApprovalBody) -> dict[str, str]:
        granted = approval.grant("demo-presenter", body.scope, body.ttl_seconds)
        return {
            "actor": granted.actor,
            "scope": granted.scope,
            "expires_at": granted.expires_at.isoformat(),
        }

    @app.get("/api/audit")
    def full_audit() -> list[dict[str, Any]]:
        return [
            {
                "correlation_id": e.correlation_id,
                "skill_id": e.skill_id,
                "decision": e.decision,
                "risk_score": e.risk_score,
                "reasons": list(e.reasons),
                "recorded_at": e.recorded_at.isoformat(),
            }
            for e in audit.events()
        ]

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    return app


def main() -> None:
    import uvicorn

    app = create_app()
    print("ERP Agent OS — product demo")
    print("http://127.0.0.1:8420  (localhost only, not reachable from the network)")
    uvicorn.run(app, host="127.0.0.1", port=8420, log_level="warning")


if __name__ == "__main__":
    main()
