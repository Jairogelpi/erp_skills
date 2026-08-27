"""FastAPI surface for the comparative product demo.

Separate from `api.py` (the RF-01 governed API over System C alone):
this one exists to run A, B and C side by side and to serve the frozen
confirmatory evidence. It is a presentation layer and says so -- it adds
no capability to any system and never recomputes a statistic.

CORS is open to localhost dev ports only. This is a laptop demo, not a
deployed service.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from erp_agent_os import demo_results
from erp_agent_os.demo_models import (
    ApprovalRequestBody,
    ApprovalResponse,
    AuditComparisonResponse,
    DemoRunResponse,
    ParaphraseResponse,
    ParaphraseRow,
    ScenarioPreset,
    TimelineEvent,
    TimelineResponse,
)
from erp_agent_os.demo_service import DemoRun, DemoService, presets
from erp_agent_os.product_demo_api import register_product_routes

DEMO_DISCLAIMER = (
    "Demo behavior is illustrative. Statistical claims come from the "
    "frozen v2.1.2 confirmatory campaign."
)


class RunRequestBody(BaseModel):
    request: str | None = None
    scenario: str = "approval"
    backend: str = "fake"


def _response(run: DemoRun) -> DemoRunResponse:
    return DemoRunResponse(
        request_id=run.request_id,
        scenario=run.scenario.id,
        request_text=run.scenario.request_text,
        backend="fake",
        systems=run.results,
        approval_granted=run.approval_granted,
    )


def create_demo_app() -> FastAPI:
    app = FastAPI(
        title="ERP Agent OS — comparative demo",
        description=DEMO_DISCLAIMER,
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    service = DemoService()
    # Skills Catalog, Skill Studio, live Odoo Operations, unified
    # Approvals/Audit -- same app, same port, so there is exactly one
    # server to reason about (SPEC v2 §14: no second Odoo connection
    # path). Everything Odoo/LLM-dependent in there builds lazily and
    # answers 503 rather than crashing this app's own boot.
    register_product_routes(app)

    def _get(request_id: str) -> DemoRun:
        try:
            return service.get(request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown request_id") from exc

    @app.get("/demo/presets", response_model=list[ScenarioPreset])
    def get_presets() -> list[ScenarioPreset]:
        return presets()

    @app.post("/demo/run", response_model=DemoRunResponse)
    def run(body: RunRequestBody) -> DemoRunResponse:
        if body.backend != "fake":
            # Live Odoo is reachable through the existing governed demo
            # script, which carries the development-instance guard. It is
            # deliberately not re-implemented here: a second, parallel
            # connection path is exactly how a production write happens
            # by accident.
            raise HTTPException(
                status_code=400,
                detail="only the reproducible FakeERP backend is served by this API",
            )
        try:
            return _response(service.run(body.scenario, body.request))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown scenario") from exc

    @app.post("/demo/approval/{request_id}", response_model=ApprovalResponse)
    def approve(request_id: str, body: ApprovalRequestBody) -> ApprovalResponse:
        run_obj = _get(request_id)
        run_obj, grant = service.approve(request_id, body.actor)
        return ApprovalResponse(
            request_id=request_id,
            actor=grant.actor,
            scope=grant.scope,
            granted_at=grant.granted_at.isoformat(),
            expires_at=grant.expires_at.isoformat(),
        )

    @app.post("/demo/rerun/{request_id}", response_model=DemoRunResponse)
    def rerun(request_id: str) -> DemoRunResponse:
        _get(request_id)
        return _response(service.rerun(request_id))

    @app.get("/demo/erp-state/{request_id}")
    def erp_state(request_id: str) -> dict[str, Any]:
        run_obj = _get(request_id)
        return {
            "request_id": request_id,
            "systems": {
                name: {
                    "before": result.erp.before,
                    "after": result.erp.after,
                    "changed": result.erp.changed,
                    "summary": result.erp.summary,
                    "field_changes": result.erp.field_changes,
                }
                for name, result in run_obj.results.items()
            },
            "verified_by": "independent ERP re-read",
        }

    @app.post("/demo/paraphrases/{request_id}", response_model=ParaphraseResponse)
    def paraphrases(request_id: str) -> ParaphraseResponse:
        run_obj = _get(request_id)
        if not run_obj.scenario.paraphrases:
            raise HTTPException(
                status_code=400, detail="this scenario declares no paraphrases"
            )
        _, variants, per_system = service.paraphrases(request_id)
        rows = []
        for name in ("A", "B", "C"):
            results = per_system[name]  # type: ignore[index]
            caps = [r.selected_capability for r in results]
            rows.append(
                ParaphraseRow(
                    system=name,  # type: ignore[arg-type]
                    outcomes=[r.erp.summary for r in results],
                    capabilities=caps,
                    # Same final ERP effect across every phrasing -- the
                    # property H3a measures, evaluated on this run only.
                    consistent=len({r.erp.summary for r in results}) == 1,
                )
            )
        return ParaphraseResponse(
            request_id=request_id,
            variants=variants,
            rows=rows,
            disclaimer=(
                "Three phrasings in this demo run. H3a's confirmatory result "
                "comes from 1,192 scenarios in the frozen campaign."
            ),
        )

    @app.get("/demo/audit/{request_id}", response_model=AuditComparisonResponse)
    def audit(request_id: str) -> AuditComparisonResponse:
        run_obj = _get(request_id)
        names = list(run_obj.results["C"].audit.facts.keys())
        return AuditComparisonResponse(
            request_id=request_id,
            fact_names=names,
            rows={
                name: result.audit.facts  # type: ignore[misc]
                for name, result in run_obj.results.items()
            },
            coverage={
                name: result.audit.coverage  # type: ignore[misc]
                for name, result in run_obj.results.items()
            },
        )

    @app.get("/demo/timeline/{request_id}", response_model=TimelineResponse)
    def timeline(request_id: str) -> TimelineResponse:
        run_obj = _get(request_id)
        return TimelineResponse(
            request_id=request_id,
            events=[
                TimelineEvent(at=at, label=label, detail=detail)
                for at, label, detail in run_obj.timeline
            ],
        )

    @app.get("/demo/evidence")
    def evidence() -> dict[str, Any]:
        try:
            bundle = demo_results.load_evidence()
        except demo_results.EvidenceUnavailableError as exc:
            # 503, not a placeholder payload: the UI must be able to say
            # "evidence unavailable" rather than render invented numbers.
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "protocol_tag": bundle.protocol_tag,
            "protocol_version": bundle.protocol_version,
            "frozen_commit": bundle.frozen_commit,
            "frozen_at": bundle.frozen_at,
            "campaign_state": bundle.campaign_state,
            "observation_count": bundle.observation_count,
            "archive_hash": bundle.archive_hash,
            "cards": [asdict(card) for card in bundle.cards],
            "capability_matrix": [asdict(row) for row in bundle.capability_matrix],
            "confinement": bundle.confinement,
            "disclaimer": DEMO_DISCLAIMER,
        }

    return app


app = create_demo_app()
