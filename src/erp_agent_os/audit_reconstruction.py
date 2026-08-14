"""Objective seven-fact audit reconstruction for v2.1 (Task 6).

docs/tfm-closure-no-human-v2.1.md section 8, H7: the historical weighted
rubric (erp_agent_os.traceability, still exported here as a secondary
descriptive metric) is no longer the primary endpoint. `reconstruct()`
answers, per fact, a binary question from a RAW TRACE alone: can this
fact be recovered, and is it internally consistent? It never reads
scenario gold (there is no gold parameter at all) -- a missing fact
must stay missing, never filled in from what the scenario "should"
have produced.

Deliberately keyed by field name, not position: renaming a system
label inside the trace, or reordering the trace's own keys, cannot
change a result computed entirely through `Mapping.get(name)` lookups.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

FACT_NAMES: tuple[str, ...] = (
    "request_and_case_identity",
    "intent_and_arguments",
    "selected_action_or_skill",
    "policy_permission_decision",
    "exact_tool_skill_handler_version",
    "result_and_observed_effects",
    "verification_approval_or_block_evidence",
)

_NON_EXECUTING_DECISIONS = frozenset({"DENY", "ABSTAIN", "CLARIFY"})


@dataclass(frozen=True)
class FactStatus:
    present: bool
    contradictory: bool

    @property
    def recovered(self) -> bool:
        return self.present and not self.contradictory


@dataclass(frozen=True)
class AuditReconstructionResult:
    facts: dict[str, FactStatus]
    contradiction_count: int
    all_facts_success: bool

    def coverage(self) -> float:
        """Fraction of the seven facts present (whether or not
        contradictory) -- a secondary, descriptive statistic; the
        confirmatory endpoint is `all_facts_success`, not this."""
        return sum(1 for f in self.facts.values() if f.present) / len(self.facts)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set, frozenset)):
        return len(value) > 0
    return True


def _fact_identity(trace: Mapping[str, Any]) -> FactStatus:
    present = _present(trace.get("correlation_id")) and _present(
        trace.get("request_text")
    )
    case_id = trace.get("case_id")
    correlation_id = trace.get("correlation_id")
    contradictory = (
        _present(case_id)
        and _present(correlation_id)
        and str(case_id) != str(correlation_id)
        and trace.get("case_id_matches_correlation") is False
    )
    return FactStatus(present=present, contradictory=contradictory)


def _fact_intent(trace: Mapping[str, Any]) -> FactStatus:
    present = _present(trace.get("intent")) and _present(trace.get("arguments"))
    return FactStatus(present=present, contradictory=False)


def _fact_selection(trace: Mapping[str, Any]) -> FactStatus:
    abstained = trace.get("abstained") is True
    present = abstained or _present(trace.get("selected_skill_id"))
    contradictory = abstained and _present(trace.get("selected_skill_id"))
    return FactStatus(present=present, contradictory=contradictory)


def _fact_policy(trace: Mapping[str, Any]) -> FactStatus:
    present = _present(trace.get("policy_decision")) and _present(trace.get("role"))
    return FactStatus(present=present, contradictory=False)


def _fact_version(trace: Mapping[str, Any]) -> FactStatus:
    decision = trace.get("policy_decision")
    if decision in _NON_EXECUTING_DECISIONS or decision is None:
        # A skill/handler version is only meaningful once something was
        # actually selected for execution; absence here is not a defect
        # for a request that never reached that stage.
        return FactStatus(present=True, contradictory=False)
    present = _present(trace.get("skill_version")) and _present(trace.get("handler"))
    return FactStatus(present=present, contradictory=False)


def _fact_result(trace: Mapping[str, Any]) -> FactStatus:
    present = "execution_output" in trace and "observed_state_delta" in trace
    decision = trace.get("policy_decision")
    delta = trace.get("observed_state_delta")
    mutated = isinstance(delta, Mapping) and delta.get("operation_kind") not in (
        None,
        "no_change",
        "read_only",
    )
    contradictory = decision in _NON_EXECUTING_DECISIONS and mutated
    return FactStatus(present=present, contradictory=contradictory)


def _fact_verification(trace: Mapping[str, Any]) -> FactStatus:
    present = _present(trace.get("verification_status"))
    decision = trace.get("policy_decision")
    approval_evidence = trace.get("approval_evidence")
    final_allowed = trace.get("final_decision_allowed") is True
    # If policy required approval and the request was ultimately allowed,
    # there must be recorded approval evidence -- an ALLOW with no trace
    # of who approved it is exactly the gap H7 exists to catch.
    contradictory = (
        decision == "REQUIRE_APPROVAL"
        and final_allowed
        and not _present(approval_evidence)
    )
    return FactStatus(present=present, contradictory=contradictory)


_FACT_CHECKS: tuple[tuple[str, Any], ...] = (
    ("request_and_case_identity", _fact_identity),
    ("intent_and_arguments", _fact_intent),
    ("selected_action_or_skill", _fact_selection),
    ("policy_permission_decision", _fact_policy),
    ("exact_tool_skill_handler_version", _fact_version),
    ("result_and_observed_effects", _fact_result),
    ("verification_approval_or_block_evidence", _fact_verification),
)


def reconstruct(trace: Mapping[str, Any]) -> AuditReconstructionResult:
    """`trace` is a single raw observation's audit-relevant fields --
    never a scenario/gold object. Reads only by key; field order and
    any system-name label inside the trace are irrelevant to the
    result (verified in tests, not just assumed)."""
    facts = {name: check(trace) for name, check in _FACT_CHECKS}
    contradiction_count = sum(1 for status in facts.values() if status.contradictory)
    all_facts_success = all(status.recovered for status in facts.values())
    return AuditReconstructionResult(
        facts=facts,
        contradiction_count=contradiction_count,
        all_facts_success=all_facts_success,
    )
