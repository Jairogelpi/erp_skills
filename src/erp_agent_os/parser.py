"""Structured intent proposal contract (no execution, no free-text exec).

Scope per CLAUDE.md §23 (generación estructurada) and RF-01–02: a strict
schema for a proposed intent/arguments/confidence, plus a pure function
that derives `missing_fields` from a declared required-field list. No LLM
call, no execution, no inference of sensitive data.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


def _is_blank(value: Any) -> bool:
    return isinstance(value, str) and not value.strip()


class IntentProposal(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    intent: str
    arguments: dict[str, Any]
    missing_fields: list[str]
    confidence: float
    constraints: list[str] = []

    @field_validator("intent")
    @classmethod
    def nonblank_intent(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("intent must be nonblank")
        return value

    @field_validator("confidence")
    @classmethod
    def bounded_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        return value


def structure_proposal(
    intent: str,
    arguments: dict[str, Any],
    required_fields: list[str],
    confidence: float,
    constraints: list[str] | None = None,
) -> IntentProposal:
    missing = [
        field
        for field in required_fields
        if field not in arguments or _is_blank(arguments[field])
    ]
    return IntentProposal(
        intent=intent,
        arguments=arguments,
        missing_fields=missing,
        confidence=confidence,
        constraints=constraints or [],
    )
