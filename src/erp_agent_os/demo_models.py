"""Wire models for the comparative product demo.

One normalized shape for all three systems. A and B genuinely do not
produce a risk class, a policy decision, an approval record, a skill
version or a postcondition result -- CLAUDE.md §18 defines them by that
absence. Those fields are therefore `None` here and rendered as "—" in
the UI rather than hidden: the missing rows *are* the comparison, and
filling them in with plausible defaults would erase the finding.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SystemName = Literal["A", "B", "C"]


class ErpDelta(BaseModel):
    """Before/after of the adapter, plus what actually changed.

    `changed` is computed by comparing two independent reads of the
    store, never by trusting what the system reported doing -- the same
    rule §25 imposes on postconditions, applied to the demo's own
    display.
    """

    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    changed: bool
    summary: str
    created_ids: list[str] = Field(default_factory=list)
    field_changes: list[dict[str, Any]] = Field(default_factory=list)


class AuditFacts(BaseModel):
    """The seven reconstruction facts scored by H7's rubric."""

    facts: dict[str, bool] = Field(default_factory=dict)
    coverage: float


class DemoSystemResult(BaseModel):
    system: SystemName
    label: str

    intent: str | None = None
    selected_capability: str | None = None
    skill_version: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)

    retrieval_confidence: float | None = None
    risk_class: str | None = None
    policy_decision: str | None = None
    policy_reasons: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)

    approval_required: bool | None = None
    approval_status: str | None = None

    execution_status: str
    handler: str | None = None
    error: str | None = None

    erp: ErpDelta
    postcondition_verified: bool | None = None
    postcondition_detail: list[str] = Field(default_factory=list)

    tokens: int | None = None
    audit_id: str | None = None
    audit: AuditFacts

    # Fields this architecture structurally cannot produce, so the UI
    # can render "—" and say why instead of leaving a blank cell.
    unavailable: list[str] = Field(default_factory=list)


class DemoRunResponse(BaseModel):
    request_id: str
    scenario: str
    request_text: str
    backend: Literal["fake", "odoo"]
    systems: dict[SystemName, DemoSystemResult]
    # True once an approval has been granted for this run, so the UI
    # knows whether to offer the Approve button or the re-run.
    approval_granted: bool = False


class ApprovalRequestBody(BaseModel):
    actor: str = "demo-admin"


class ApprovalResponse(BaseModel):
    request_id: str
    actor: str
    scope: str
    granted_at: str
    expires_at: str


class ParaphraseRow(BaseModel):
    system: SystemName
    outcomes: list[str]
    capabilities: list[str | None]
    consistent: bool


class ParaphraseResponse(BaseModel):
    request_id: str
    variants: list[str]
    rows: list[ParaphraseRow]
    # Named so no reader can mistake three demo phrasings for the
    # 1,192-scenario confirmatory population behind H3a.
    disclaimer: str


class AuditComparisonResponse(BaseModel):
    request_id: str
    fact_names: list[str]
    rows: dict[SystemName, dict[str, bool]]
    coverage: dict[SystemName, float]


class TimelineEvent(BaseModel):
    at: str
    label: str
    detail: str | None = None


class TimelineResponse(BaseModel):
    request_id: str
    events: list[TimelineEvent]


class ScenarioPreset(BaseModel):
    id: str
    label: str
    request_text: str
    description: str
