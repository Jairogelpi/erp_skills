"""Executable postcondition checks (CLAUDE.md §25, RF-14).

The catalog declares postconditions as identifiers (`"quote_is_draft"`).
This module maps each identifier to a callable that actually inspects
`FakeERPAdapter` after execution, so the verification engine verifies
something instead of accepting an HTTP-style "it returned fine".

Each check is built as a closure over the pre-execution snapshot, because
most postconditions are differential ("exactly one new record", "no other
field changed") and cannot be evaluated from the final state alone.
"""

from collections.abc import Callable
from typing import Any

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.handlers import SKILL_MODELS
from erp_agent_os.skills import SkillDefinition

Check = Callable[[FakeERPAdapter, Any], bool]


class UnknownPostconditionError(KeyError):
    """Raised when a skill declares a postcondition with no implementation."""


def _records(snapshot: dict[str, Any], model: str) -> dict[str, Any]:
    return snapshot["records"].get(model, {})


def _exactly_one_new(model: str, before: dict[str, Any]) -> Check:
    baseline = len(_records(before, model))

    def check(erp: FakeERPAdapter, output: Any) -> bool:
        return len(erp.list(model)) == baseline + 1

    return check


def _state_is(model: str, expected_state: str) -> Check:
    def check(erp: FakeERPAdapter, output: Any) -> bool:
        record_id = output if isinstance(output, str) else None
        if record_id is None:
            return False
        try:
            return erp.get(model, record_id).get("state") == expected_state
        except KeyError:
            return False

    return check


def _field_matches(model: str, field: str, arguments: dict[str, Any]) -> Check:
    def check(erp: FakeERPAdapter, output: Any) -> bool:
        record_id = output if isinstance(output, str) else None
        if record_id is None:
            return False
        try:
            record = erp.get(model, record_id)
        except KeyError:
            return False
        expected = arguments.get(field)
        if expected is None:
            return False
        return str(record.get(field)) == str(expected)

    return check


def _no_other_fields_changed(
    model: str, before: dict[str, Any], allowed: set[str]
) -> Check:
    baseline = _records(before, model)

    def check(erp: FakeERPAdapter, output: Any) -> bool:
        record_id = output if isinstance(output, str) else None
        if record_id is None or record_id not in baseline:
            # A newly created record trivially changed nothing else.
            return True
        old = baseline[record_id]
        try:
            new = erp.get(model, record_id)
        except KeyError:
            return False
        touched = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
        return touched <= allowed

    return check


def _output_has_key(key: str) -> Check:
    def check(erp: FakeERPAdapter, output: Any) -> bool:
        return isinstance(output, dict) and key in output

    return check


def _count_unchanged(model: str, before: dict[str, Any]) -> Check:
    baseline = len(_records(before, model))

    def check(erp: FakeERPAdapter, output: Any) -> bool:
        return len(erp.list(model)) == baseline

    return check


def build_checks(
    skill: SkillDefinition, arguments: dict[str, Any], before: dict[str, Any]
) -> tuple[Check, ...]:
    """Resolve a skill's declared postconditions into executable checks."""
    model = SKILL_MODELS[skill.skill_id]
    checks: list[Check] = []

    for name in skill.postconditions:
        if name.startswith("exactly_one_new_"):
            checks.append(_exactly_one_new(model, before))
        elif name in ("opportunity_is_open", "task_is_open"):
            checks.append(_state_is(model, "open"))
        elif name in (
            "quote_is_draft",
            "quote_still_draft",
            "purchase_order_is_draft",
            "invoice_is_draft",
        ):
            checks.append(_state_is(model, "draft"))
        elif name == "order_is_confirmed":
            checks.append(_state_is(model, "confirmed"))
        elif name == "expected_revenue_matches_input":
            checks.append(_field_matches(model, "expected_revenue", arguments))
        elif name == "field_matches_input":
            field = str(arguments.get("field", ""))
            checks.append(_field_matches(model, field, arguments))
        elif name == "no_other_fields_changed":
            allowed = {"expected_revenue", str(arguments.get("field", ""))}
            checks.append(_no_other_fields_changed(model, before, allowed))
        elif name == "no_line_changed":
            checks.append(_no_other_fields_changed(model, before, {"state"}))
        elif name == "duplicate_report_returned":
            checks.append(_output_has_key("duplicates_found"))
        elif name == "search_results_returned":
            checks.append(_output_has_key("results"))
        elif name == "availability_returned":
            checks.append(_output_has_key("available_units"))
        else:
            raise UnknownPostconditionError(
                f"{skill.skill_id} declares postcondition {name!r} with no "
                "executable implementation"
            )

    return tuple(checks)


def read_only_checks(
    skill: SkillDefinition, before: dict[str, Any]
) -> tuple[Check, ...]:
    """For R0 read skills: assert the store was not mutated at all."""
    return (_count_unchanged(SKILL_MODELS[skill.skill_id], before),)
