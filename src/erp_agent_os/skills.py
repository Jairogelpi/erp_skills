"""Versioned skill contract and lifecycle transitions.

Scope per CLAUDE.md §15 (contract, lifecycle) and §16 (risk taxonomy): a
strict, frozen schema for a registered skill, plus a pure transition
function enforcing the fixed state graph. No registry storage, execution,
policy evaluation, or embedding behavior.
"""

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from erp_agent_os.dataset import RiskClass

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class SkillState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    TESTED = "TESTED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"


# CLAUDE.md §15: DRAFT -> VALIDATED -> TESTED -> APPROVED -> ACTIVE ->
# DEPRECATED, any state -> QUARANTINED, and no direct DRAFT -> ACTIVE.
ALLOWED_TRANSITIONS: dict[SkillState, frozenset[SkillState]] = {
    SkillState.DRAFT: frozenset({SkillState.VALIDATED, SkillState.QUARANTINED}),
    SkillState.VALIDATED: frozenset({SkillState.TESTED, SkillState.QUARANTINED}),
    SkillState.TESTED: frozenset({SkillState.APPROVED, SkillState.QUARANTINED}),
    SkillState.APPROVED: frozenset({SkillState.ACTIVE, SkillState.QUARANTINED}),
    SkillState.ACTIVE: frozenset({SkillState.DEPRECATED, SkillState.QUARANTINED}),
    SkillState.DEPRECATED: frozenset({SkillState.QUARANTINED}),
    SkillState.QUARANTINED: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a lifecycle move is outside the fixed state graph."""


def transition(current: SkillState, target: SkillState) -> SkillState:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"{current} -> {target}")
    return target


class _Model(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Permissions(_Model):
    allowed_roles: list[str]

    @field_validator("allowed_roles")
    @classmethod
    def nonempty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("allowed_roles must be nonempty")
        return value


class Execution(_Model):
    handler: str
    timeout_seconds: int
    max_retries: int
    idempotent: bool

    @field_validator("handler")
    @classmethod
    def dotted_path(cls, value: str) -> str:
        if not re.fullmatch(r"[\w]+(\.[\w]+)+", value):
            raise ValueError("handler must be a dotted module path")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def positive_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value

    @field_validator("max_retries")
    @classmethod
    def nonnegative_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("max_retries must be nonnegative")
        return value


class SkillDefinition(_Model):
    skill_id: str
    version: str
    module: str
    operation: str
    description: str
    risk_class: RiskClass
    input_schema: dict[str, Any]
    permissions: Permissions
    preconditions: list[str]
    execution: Execution
    postconditions: list[str]
    approval_required_when: list[str] = []
    state: SkillState = SkillState.DRAFT

    @field_validator("skill_id", "module", "operation", "description")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonblank")
        return value

    @field_validator("version")
    @classmethod
    def semver(cls, value: str) -> str:
        if not _VERSION_RE.match(value):
            raise ValueError("version must be MAJOR.MINOR.PATCH")
        return value

    @field_validator("risk_class")
    @classmethod
    def not_prohibited(cls, value: RiskClass) -> RiskClass:
        if value == RiskClass.R4:
            raise ValueError("R4 is unconditionally denied; not registrable")
        return value

    @field_validator("postconditions")
    @classmethod
    def has_postconditions(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("postconditions must be nonempty")
        return value
