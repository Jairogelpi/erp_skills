"""FastAPI surface over System C.

Scope per CLAUDE.md §14 (API: FastAPI, demo auth, validation layer,
correlation ID, basic limits) and roadmap P6.1: expose `SystemC.handle`
over HTTP, plus read-only catalog/audit endpoints and an approval grant
endpoint feeding `policy.decide` via `ApprovalService`. No persistence
(PostgreSQL/pgvector, roadmap P6.2) — state is process-local, matching
every other module's in-memory scope so far.
"""

import time
import uuid
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.catalog import CATALOG
from erp_agent_os.handlers import HANDLERS, SKILL_MODELS
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import (
    IdempotencyConflictError,
    IdempotencyFingerprintError,
    Runtime,
)
from erp_agent_os.system_c import SystemC

# Demo-only credential (CLAUDE.md §14: "autenticación para la demo").
# Not a production secret store; never source this from a real deployment.
DEMO_API_KEY = "demo-key"

# Demo-only, in-memory, single-process rate limit (CLAUDE.md §14: "límites
# básicos"). Not distributed, not persisted, not a production rate limiter.
RATE_LIMIT_PER_MINUTE = 60


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self._limit = limit_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, *, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        window_start = now - 60
        hits = [t for t in self._hits[key] if t >= window_start]
        hits.append(now)
        self._hits[key] = hits
        return len(hits) <= self._limit


class ProposalPayload(BaseModel):
    intent: str
    arguments: dict[str, object]
    required_fields: list[str]
    confidence: float
    constraints: list[str] = []


class ExecuteRequest(BaseModel):
    query_text: str
    proposal: ProposalPayload
    role: str
    idempotency_key: str


class ExecuteResponse(BaseModel):
    correlation_id: str
    decision: str
    selected_skill_id: str | None
    reasons: list[str]
    verification_status: str
    postconditions_met: bool | None
    checks: list[dict[str, object]]


class ApprovalRequest(BaseModel):
    actor: str
    scope: str
    ttl_seconds: int


def create_app() -> FastAPI:
    app = FastAPI(title="ERP Agent OS API", version="0.1.0")

    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    runtime = Runtime(erp)
    for skill in CATALOG:
        runtime.register(skill.skill_id, skill.version, HANDLERS[skill.skill_id])
    retriever = TfidfRetriever(CATALOG)
    audit = AuditStore()
    approval = ApprovalService()
    system = SystemC(erp, runtime, retriever, audit, approval)
    limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)

    def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if x_api_key != DEMO_API_KEY:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid API key")

    def enforce_rate_limit(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if not limiter.check(x_api_key or "anonymous"):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded"
            )

    @app.post(
        "/requests",
        response_model=ExecuteResponse,
        dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
    )
    def execute(body: ExecuteRequest) -> ExecuteResponse:
        correlation_id = str(uuid.uuid4())
        proposal = structure_proposal(
            body.proposal.intent,
            body.proposal.arguments,
            body.proposal.required_fields,
            body.proposal.confidence,
            body.proposal.constraints,
        )
        try:
            result = system.handle(
                correlation_id,
                body.query_text,
                proposal,
                body.role,
                body.idempotency_key,
            )
        except IdempotencyConflictError:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "idempotency key conflicts with request",
            ) from None
        except IdempotencyFingerprintError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "request arguments cannot be fingerprinted",
            ) from None
        return ExecuteResponse(
            correlation_id=correlation_id,
            decision=result.decision,
            selected_skill_id=result.selected_skill_id,
            reasons=list(result.reasons),
            verification_status=result.verification_status.value,
            postconditions_met=result.postconditions_met,
            checks=[
                {
                    "check_id": check.check_id,
                    "passed": check.passed,
                    "detail": check.detail,
                }
                for check in result.check_results
            ],
        )

    @app.get(
        "/skills", dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)]
    )
    def list_skills() -> list[dict[str, object]]:
        return [
            {
                "skill_id": s.skill_id,
                "module": s.module,
                "risk_class": s.risk_class.value,
                "description": s.description,
            }
            for s in CATALOG
        ]

    @app.get("/audit/{correlation_id}", dependencies=[Depends(require_api_key)])
    def get_audit(correlation_id: str) -> dict[str, object]:
        events = audit.events(correlation_id)
        abstentions = audit.abstentions(correlation_id)
        return {
            "events": [
                {
                    "decision": event.decision,
                    "verification_status": event.verification_status,
                    "postconditions_met": event.postconditions_met,
                    "checks": [
                        {
                            "check_id": check.check_id,
                            "passed": check.passed,
                            "detail": check.detail,
                        }
                        for check in event.check_results
                    ],
                }
                for event in events
            ],
            "abstentions": len(abstentions),
            "abstention_events": [
                {
                    "reasons": list(event.reasons),
                    "verification_status": event.verification_status,
                    "postconditions_met": event.postconditions_met,
                    "checks": [
                        {
                            "check_id": check.check_id,
                            "passed": check.passed,
                            "detail": check.detail,
                        }
                        for check in event.check_results
                    ],
                }
                for event in abstentions
            ],
        }

    @app.post("/approvals", dependencies=[Depends(require_api_key)])
    def grant_approval(body: ApprovalRequest) -> dict[str, str]:
        granted = approval.grant(body.actor, body.scope, body.ttl_seconds)
        return {
            "actor": granted.actor,
            "scope": granted.scope,
            "expires_at": granted.expires_at.isoformat(),
        }

    return app


app = create_app()
