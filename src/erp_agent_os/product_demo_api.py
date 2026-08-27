"""Product-mode routes: Skills Catalog, Skill Studio, live Odoo Operations,
and unified Approvals/Audit.

Mounted onto the SAME FastAPI app as the comparative demo (`demo_api.py`)
by `register_product_routes`, so the whole product is one server on one
port -- SPEC v2 section 14 is explicit that a second connection path to
Odoo is exactly how a production write happens by accident, and that rule
extends to not standing up a second HTTP server either.

Two independent things are "not configured" here, and each fails its own
routes with 503 rather than crashing the app at import/boot time (a laptop
running only the comparative FakeERP tabs has neither):

- live Odoo (`ODOO_URL`/`ODOO_DB`/`ODOO_API_KEY`) -- required by
  `/product/operations/*`;
- an LLM provider (`OPENROUTER_API_KEY`) -- required by
  `/product/skill-studio/draft` and `/product/skill-studio/modify`
  (drafting/editing a contract from free text) and by
  `/product/operations/run` (extracting arguments from free text).

The Skills Catalog and Skill Studio's validate/approve/activate machinery
need neither: they run against the frozen in-memory `CATALOG` and a
throwaway sandbox `FakeERPAdapter`, so they work with no environment
configured at all.
"""

from __future__ import annotations

import hashlib
import os
import threading
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from erp_agent_os import odoo_handlers
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.odoo_client import (
    MissingCredentialsError,
    NotADevelopmentInstanceError,
    Odoo19Adapter,
    require_development_instance,
)
from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS
from erp_agent_os.openrouter_client import MissingApiKeyError, OpenRouterClient
from erp_agent_os.parser import structure_proposal
from erp_agent_os.registry import (
    SqlSkillRegistry,
    UnknownSkillError,
    create_registry_schema,
)
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.skill_admin import (
    SkillAdmin,
    SkillAdminError,
    diff_contract,
    draft_skill_contract,
    draft_skill_modification,
    evaluate_approval_conditions,
    synthesize_sample_arguments,
)
from erp_agent_os.skills import InvalidTransitionError
from erp_agent_os.system_c import SystemC

# Only these two of the 12 catalog skills have a real Odoo handler
# (odoo_handlers.py). The Skills Catalog and Operations panel must not
# imply the other 10 write anywhere real.
ODOO_WIRED_SKILLS = {"crm.create_opportunity", "crm.update_expected_revenue"}


class ProductNotConfiguredError(RuntimeError):
    """Raised when a product-mode route needs Odoo or an LLM key that
    isn't set. Caught once, at the route boundary, and turned into a 503
    -- never lets the whole app fail to boot for a laptop with no
    ODOO_URL/OPENROUTER_API_KEY configured."""


def _catalog_registry() -> SqlSkillRegistry:
    """The 12 frozen skills, seeded into a real (if in-process) registry
    so Skills Catalog can show state/version/history instead of the bare
    static list -- without touching `catalog.py` itself, which is
    hashed by the v1/v2.1 freeze manifests and must not change."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    create_registry_schema(engine)
    registry = SqlSkillRegistry(engine)
    registry.seed_from_catalog(CATALOG, actor="catalog-seed")
    return registry


@dataclass
class _LiveSystem:
    system: SystemC
    retriever: TfidfRetriever
    approval: ApprovalService
    audit: AuditStore
    llm: OpenRouterClient


class _ProductState:
    """Everything the product routes need, built once and reused.

    The catalog registry and the skill-proposal admin have no external
    dependency and are built eagerly. The live-Odoo system is built lazily
    on first use (`live()`), behind a lock so two concurrent requests
    don't race to construct two `Odoo19Adapter`s.
    """

    def __init__(self) -> None:
        self.registry = _catalog_registry()
        self.skill_admin = SkillAdmin()
        self._live: _LiveSystem | None = None
        self._live_lock = threading.Lock()

    def live(self) -> _LiveSystem:
        if self._live is not None:
            return self._live
        with self._live_lock:
            if self._live is not None:
                return self._live
            try:
                target = require_development_instance()
            except NotADevelopmentInstanceError as exc:
                raise ProductNotConfiguredError(str(exc)) from exc
            try:
                erp = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})
            except MissingCredentialsError as exc:
                raise ProductNotConfiguredError(str(exc)) from exc
            runtime: Runtime[Any] = Runtime(erp)
            for skill_id in ODOO_WIRED_SKILLS:
                handler_name = skill_id.split(".", 1)[1]
                handler = getattr(odoo_handlers, f"crm_{handler_name}")
                runtime.register(skill_id, CATALOG_BY_ID[skill_id].version, handler)
            retriever = TfidfRetriever(CATALOG)
            audit = AuditStore()
            approval = ApprovalService()
            try:
                llm = OpenRouterClient()
            except MissingApiKeyError as exc:
                raise ProductNotConfiguredError(str(exc)) from exc
            system = SystemC(erp, runtime, retriever, audit, approval)
            self._live = _LiveSystem(system, retriever, approval, audit, llm)
            del target  # only needed to raise; not part of the state
            return self._live

    @property
    def live_if_built(self) -> _LiveSystem | None:
        """`None` until the first successful `live()` call -- lets the
        unified Approvals/Audit views include ERP-execution rows without
        forcing a live Odoo connection just to answer "what happened so
        far", which would turn a read into a 503 for no reason."""
        return self._live


# --- request/response bodies -------------------------------------------


class DraftBody(BaseModel):
    description: str


class ModifyBody(BaseModel):
    contract: dict[str, Any]
    instruction: str


class TestBody(BaseModel):
    contract: dict[str, Any]
    sample_arguments: dict[str, Any] | None = None


class EvaluateApprovalBody(BaseModel):
    conditions: list[str]
    affected_count: int


class ApproveBody(BaseModel):
    skill_id: str
    version: str
    approver: str


class RunBody(BaseModel):
    text: str
    role: str = "erp_user"


class ApprovalGrantBody(BaseModel):
    scope: str
    ttl_seconds: int = 120


class DeprecateBody(BaseModel):
    actor: str


class QuarantineBody(BaseModel):
    actor: str
    reason: str


def _skill_view(registry: SqlSkillRegistry, skill_id: str) -> dict[str, Any]:
    versions = registry.versions(skill_id)
    if not versions:
        # registry.versions() returns [] rather than raising for an
        # unknown id (it is a plain SELECT, no existence check) -- raise
        # here so the route can answer 404 instead of an IndexError.
        raise UnknownSkillError(skill_id)
    latest = versions[-1]
    skill = registry.get(skill_id, latest)
    return {
        "skill_id": skill.skill_id,
        "version": latest,
        "versions": versions,
        "state": registry.state_of(skill_id, latest).value,
        "description": skill.description,
        "module": skill.module,
        "operation": skill.operation,
        "risk_class": skill.risk_class.value,
        "allowed_roles": list(skill.permissions.allowed_roles),
        "input_schema": skill.input_schema,
        "preconditions": list(skill.preconditions),
        "postconditions": list(skill.postconditions),
        "handler": skill.execution.handler,
        "idempotent": skill.execution.idempotent,
        "approval_required_when": list(skill.approval_required_when),
        "odoo_wired": skill.skill_id in ODOO_WIRED_SKILLS,
    }


def register_product_routes(app: FastAPI) -> None:
    state = _ProductState()

    # --- Skills Catalog / Skill Detail (§7, §8) -------------------------

    @app.get("/product/skills")
    def list_skills() -> list[dict[str, Any]]:
        return [_skill_view(state.registry, s.skill_id) for s in CATALOG]

    @app.get("/product/skills/{skill_id}")
    def skill_detail(skill_id: str) -> dict[str, Any]:
        try:
            view = _skill_view(state.registry, skill_id)
        except UnknownSkillError as exc:
            raise HTTPException(404, "unknown skill") from exc
        latest = view["version"]
        view["history"] = [
            {
                "from": h["from_state"],
                "to": h["to_state"],
                "actor": h["actor"],
                "reason": h["reason"],
                "recorded_at": h["recorded_at"].isoformat(),
            }
            for h in state.registry.history(skill_id, latest)
        ]
        return view

    # --- Catalog lifecycle: suspend / retire, never delete --------------
    # No delete anywhere in this project, by design (CLAUDE.md §11): not
    # here, not FakeERPAdapter, not Odoo19Adapter, not the audit store.
    # Quarantine is the emergency stop (reachable from any state);
    # deprecate is the planned retirement (only from ACTIVE). Neither can
    # be undone in this session -- skills.ALLOWED_TRANSITIONS has no path
    # back to ACTIVE from either, on purpose (§15: no shortcuts).

    @app.post("/product/skills/{skill_id}/quarantine")
    def quarantine_skill(skill_id: str, body: QuarantineBody) -> dict[str, Any]:
        if not body.actor.strip():
            raise HTTPException(422, "quarantine requires a named human actor")
        latest = state.registry.versions(skill_id)
        if not latest:
            raise HTTPException(404, "unknown skill")
        try:
            state.registry.quarantine(
                skill_id, latest[-1], actor=body.actor, reason=body.reason
            )
        except InvalidTransitionError as exc:
            raise HTTPException(422, str(exc)) from exc
        return skill_detail(skill_id)

    @app.post("/product/skills/{skill_id}/deprecate")
    def deprecate_skill(skill_id: str, body: DeprecateBody) -> dict[str, Any]:
        if not body.actor.strip():
            raise HTTPException(422, "deprecation requires a named human actor")
        latest = state.registry.versions(skill_id)
        if not latest:
            raise HTTPException(404, "unknown skill")
        try:
            state.registry.deprecate(skill_id, latest[-1], actor=body.actor)
        except InvalidTransitionError as exc:
            raise HTTPException(
                422,
                f"cannot deprecate from this state: {exc}. Only an ACTIVE "
                "skill can be retired.",
            ) from exc
        return skill_detail(skill_id)

    # --- Skill Studio: create / modify / validate / approve (§9) -------
    # A separate lane from the frozen catalog above: proposals never touch
    # CATALOG or Odoo. See skill_admin.py's module docstring for why.

    @app.post("/product/skill-studio/draft")
    def draft(body: DraftBody) -> dict[str, Any]:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(503, "OPENROUTER_API_KEY is not set")
        try:
            contract = draft_skill_contract(body.description, api_key=api_key)
        except SkillAdminError as exc:
            raise HTTPException(422, str(exc)) from exc
        sample = synthesize_sample_arguments(contract.get("input_schema", {}))
        return {"contract": contract, "sample_arguments": sample}

    @app.post("/product/skill-studio/modify")
    def modify(body: ModifyBody) -> dict[str, Any]:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(503, "OPENROUTER_API_KEY is not set")
        try:
            new_contract = draft_skill_modification(
                body.contract, body.instruction, api_key=api_key
            )
        except SkillAdminError as exc:
            raise HTTPException(422, str(exc)) from exc
        diff = diff_contract(body.contract, new_contract)
        sample = synthesize_sample_arguments(new_contract.get("input_schema", {}))
        return {"contract": new_contract, "diff": diff, "sample_arguments": sample}

    @app.post("/product/skill-studio/evaluate-approval")
    def evaluate_approval(body: EvaluateApprovalBody) -> dict[str, Any]:
        # Isolated on purpose: this never touches policy.py, System C,
        # Runtime or CATALOG -- see evaluate_approval_conditions'
        # docstring. It only answers "would this free-text condition, as
        # written, trigger for this many affected records".
        if body.affected_count < 0:
            raise HTTPException(422, "affected_count must be non-negative")
        return evaluate_approval_conditions(body.conditions, body.affected_count)

    @app.post("/product/skill-studio/test")
    def test_proposal(body: TestBody) -> dict[str, Any]:
        sample = body.sample_arguments or synthesize_sample_arguments(
            body.contract.get("input_schema", {})
        )
        try:
            return state.skill_admin.propose(body.contract, sample)
        except SkillAdminError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/product/skill-studio/approve")
    def approve_proposal(body: ApproveBody) -> dict[str, Any]:
        if not body.approver.strip():
            raise HTTPException(422, "activation requires a named human approver")
        try:
            return state.skill_admin.approve(
                body.skill_id, body.version, approver=body.approver
            )
        except SkillAdminError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/product/skill-studio/proposals")
    def list_proposals() -> list[dict[str, Any]]:
        return state.skill_admin.list_proposals()

    # --- Live Odoo operations (§14) -------------------------------------

    @app.post("/product/operations/run")
    def run_operation(body: RunBody) -> dict[str, Any]:
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "empty request text")
        try:
            live = state.live()
        except ProductNotConfiguredError as exc:
            raise HTTPException(503, str(exc)) from exc

        correlation_id = str(uuid.uuid4())
        idempotency_key = hashlib.sha256(f"{text}|{body.role}".encode()).hexdigest()[
            :16
        ]

        candidates = live.retriever.rank(text, role=body.role)
        candidate_view = [
            {"skill_id": c.skill.skill_id, "score": round(c.score, 4)}
            for c in candidates[:5]
        ]
        if not candidates:
            live.audit.record_abstention(correlation_id, ["no candidate for this role"])
            return {
                "correlation_id": correlation_id,
                "decision": "ABSTAIN",
                "candidates": candidate_view,
                "reasons": ["no candidate for this role"],
            }

        top = candidates[0].skill
        if top.skill_id not in ODOO_WIRED_SKILLS:
            return {
                "correlation_id": correlation_id,
                "decision": "NOT_WIRED",
                "selected_skill_id": top.skill_id,
                "candidates": candidate_view,
                "reasons": [],
                "note": (
                    f"'{top.skill_id}' is the best candidate, but only "
                    f"{sorted(ODOO_WIRED_SKILLS)} have a real Odoo handler "
                    "in this demo."
                ),
            }

        required = top.input_schema["required"]
        extraction = live.llm.extract_arguments(text, required) if required else None
        arguments = dict(extraction.arguments) if extraction else {}
        proposal = structure_proposal(
            f"{top.module}.{top.skill_id.split('.', 1)[1]}",
            arguments,
            required,
            confidence=0.9,
        )
        result = live.system.handle(
            correlation_id, text, proposal, body.role, idempotency_key
        )
        response: dict[str, Any] = {
            "correlation_id": correlation_id,
            "decision": result.decision,
            "selected_skill_id": result.selected_skill_id,
            "reasons": list(result.reasons),
            "candidates": candidate_view,
            "extracted_arguments": arguments,
        }
        if result.decision in ("CLARIFY", "ABSTAIN") or result.execution is None:
            return response
        response["execution"] = {
            "output": result.execution.output,
            "idempotent_replay": result.execution.idempotent_replay,
            "handler_error": result.execution.handler_error,
        }
        if result.decision == "ALLOW" and result.execution.output:
            fresh = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})
            response["independent_reread"] = fresh.get(
                "crm.lead", str(result.execution.output)
            )
        return response

    # --- Approvals, unified (§10) ---------------------------------------
    # Two kinds, kept distinct in the response so a viewer never confuses
    # "this ERP write may proceed" with "this skill may enter production":
    # ERP execution approvals come from the live ApprovalService; skill
    # activation approvals are reconstructed from the registries' own
    # append-only transition history (to_state == APPROVED or ACTIVE).

    @app.post("/product/approvals")
    def grant_execution_approval(body: ApprovalGrantBody) -> dict[str, Any]:
        try:
            live = state.live()
        except ProductNotConfiguredError as exc:
            raise HTTPException(503, str(exc)) from exc
        granted = live.approval.grant("demo-presenter", body.scope, body.ttl_seconds)
        return {
            "kind": "erp_execution",
            "actor": granted.actor,
            "scope": granted.scope,
            "granted_at": granted.granted_at.isoformat(),
            "expires_at": granted.expires_at.isoformat(),
        }

    @app.get("/product/approvals")
    def list_approvals() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if state.live_if_built is not None:
            rows.extend(
                {
                    "kind": "erp_execution",
                    "actor": g.actor,
                    "scope": g.scope,
                    "granted_at": g.granted_at.isoformat(),
                    "expires_at": g.expires_at.isoformat(),
                }
                for g in state.live_if_built.approval.grants
            )
        for skill_id, version in state.skill_admin.proposal_ids:
            history = state.skill_admin.registry.history(skill_id, version)
            for h in history:
                if h["to_state"] in ("APPROVED", "ACTIVE"):
                    rows.append(
                        {
                            "kind": "skill_activation",
                            "actor": h["actor"],
                            "scope": f"{skill_id}@{version}",
                            "granted_at": h["recorded_at"].isoformat(),
                            "to_state": h["to_state"],
                        }
                    )
        rows.sort(key=lambda r: r["granted_at"])
        return rows

    # --- Audit, unified (§11, §22) ---------------------------------------

    @app.get("/product/audit")
    def unified_audit() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if state.live_if_built is not None:
            rows.extend(
                {
                    "kind": "erp_request",
                    "correlation_id": e.correlation_id,
                    "skill_id": e.skill_id,
                    "decision": e.decision,
                    "risk_score": e.risk_score,
                    "reasons": list(e.reasons),
                    "recorded_at": e.recorded_at.isoformat(),
                }
                for e in state.live_if_built.audit.events()
            )
        for skill_id, version in state.skill_admin.proposal_ids:
            history = state.skill_admin.registry.history(skill_id, version)
            rows.extend(
                {
                    "kind": "skill_evolution",
                    "skill_id": skill_id,
                    "version": version,
                    "from_state": h["from_state"],
                    "to_state": h["to_state"],
                    "actor": h["actor"],
                    "reason": h["reason"],
                    "recorded_at": h["recorded_at"].isoformat(),
                }
                for h in history
            )
        rows.sort(key=lambda r: r["recorded_at"])
        return rows
