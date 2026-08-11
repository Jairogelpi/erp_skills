"""Deny-by-default policy engine.

Scope per CLAUDE.md §16 (risk taxonomy) and §24 (policy engine): a pure
function mapping (skill, role, approval) to an immutable decision. No
persistence, approval-service state, or execution.
"""

from dataclasses import dataclass, field
from enum import Enum

from erp_agent_os.dataset import RiskClass
from erp_agent_os.skills import SkillDefinition, SkillState
from erp_agent_os.validation import Finding, blocking_findings

POLICY_VERSION = "2026.1"

# CLAUDE.md §16: R0/R1 execute automatically when allowed; R2 needs
# approval; R3 needs approval and prefers simulation even once approved;
# R4 is rejected at the SkillDefinition schema and never reaches here.
_RISK_SCORE: dict[RiskClass, float] = {
    RiskClass.R0: 0.0,
    RiskClass.R1: 0.2,
    RiskClass.R2: 0.5,
    RiskClass.R3: 0.8,
}


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    SIMULATE = "SIMULATE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


@dataclass(frozen=True)
class PolicyOutcome:
    decision: PolicyDecision
    risk_score: float
    reasons: list[str] = field(default_factory=list)
    policy_version: str = POLICY_VERSION


def decide(
    skill: SkillDefinition,
    role: str,
    *,
    approval_granted: bool = False,
    findings: list[Finding] | None = None,
) -> PolicyOutcome:
    risk_score = _RISK_SCORE[skill.risk_class]

    if role not in skill.permissions.allowed_roles:
        return PolicyOutcome(PolicyDecision.DENY, risk_score, ["role not permitted"])

    if skill.state is not SkillState.ACTIVE:
        return PolicyOutcome(PolicyDecision.DENY, risk_score, ["skill not active"])

    # Validation/adversarial findings deny before any risk-tier reasoning:
    # a more restrictive input can never yield a more permissive decision
    # (CLAUDE.md §24, deny by default; §29 monotonicity property).
    blocking = blocking_findings(findings or [])
    if blocking:
        return PolicyOutcome(
            PolicyDecision.DENY,
            risk_score,
            [f"{f.kind.value}: {f.detail}" for f in blocking],
        )

    if skill.risk_class in (RiskClass.R0, RiskClass.R1):
        return PolicyOutcome(PolicyDecision.ALLOW, risk_score, ["low risk"])

    if skill.risk_class is RiskClass.R2:
        if approval_granted:
            return PolicyOutcome(PolicyDecision.ALLOW, risk_score, ["approved"])
        return PolicyOutcome(
            PolicyDecision.REQUIRE_APPROVAL, risk_score, ["R2 requires approval"]
        )

    # RiskClass.R3: approval is required, but execution stays simulated
    # even once approved (CLAUDE.md §16: "preferentemente simulación").
    if approval_granted:
        return PolicyOutcome(
            PolicyDecision.SIMULATE, risk_score, ["approved; R3 simulates"]
        )
    return PolicyOutcome(
        PolicyDecision.REQUIRE_APPROVAL, risk_score, ["R3 requires approval"]
    )
