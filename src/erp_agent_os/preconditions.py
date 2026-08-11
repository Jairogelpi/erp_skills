"""Executable business preconditions (RF-07, CLAUDE.md §15).

The skill contract declares `preconditions` as identifiers, exactly as
it declares postconditions -- §15's own example lists
`customer_name_not_empty`, `expected_revenue_within_role_limit` and
`no_equivalent_open_opportunity`. `postconditions.py` resolves its
identifiers to callables; this module does the same for preconditions,
which had no evaluator at all: the field existed and was never read.

**Why the frozen catalog still declares none.** Populating
`preconditions` would change System C's decisions, and the confirmatory
experiment (§19) documents the system as it behaved when the test split
was frozen. Turning them on after seeing test results would mean the
published numbers describe a system that no longer exists. The
mechanism is therefore implemented and tested here, and switching it on
is declared work that requires its own run -- the same discipline
applied to `--real-parser` and the exploratory temperature arm.

Unknown identifiers raise rather than passing silently: a precondition
nobody implemented must not read as a precondition that held. That is
the same rule `postconditions.py` follows, and it exists because a
check that cannot fail is worse than no check.
"""

from collections.abc import Callable
from typing import Any

from erp_agent_os.adapters import ErpAdapter
from erp_agent_os.skills import SkillDefinition

# A precondition sees the adapter (to inspect current ERP state) and the
# validated arguments, and answers "may this proceed?".
Precondition = Callable[[ErpAdapter, dict[str, Any]], bool]

# Role-scoped ceilings for `expected_revenue_within_role_limit`.
# Deliberately data, not code: §24 wants policy expressed declaratively.
ROLE_REVENUE_LIMITS: dict[str, float] = {
    "erp_user": 50_000.0,
    "sales_user": 50_000.0,
    "sales_manager": 100_000.0,
}


class UnknownPreconditionError(KeyError):
    """Raised when a skill declares a precondition with no implementation."""


def _non_empty(field: str) -> Precondition:
    def check(erp: ErpAdapter, args: dict[str, Any]) -> bool:
        value = args.get(field)
        return value is not None and bool(str(value).strip())

    return check


def _revenue_within_role_limit(role: str) -> Precondition:
    limit = ROLE_REVENUE_LIMITS.get(role, 0.0)

    def check(erp: ErpAdapter, args: dict[str, Any]) -> bool:
        raw = args.get("expected_revenue")
        if raw is None:
            return False
        try:
            return float(str(raw)) <= limit
        except ValueError:
            # Malformed input is not "within the limit"; validation
            # reports the type problem separately.
            return False

    return check


def _no_equivalent_open_record(model: str, field: str) -> Precondition:
    def check(erp: ErpAdapter, args: dict[str, Any]) -> bool:
        wanted = str(args.get(field, "")).strip().lower()
        if not wanted:
            return False
        for record in erp.list(model).values():
            same = str(record.get(field, "")).strip().lower() == wanted
            if same and record.get("state") == "open":
                return False
        return True

    return check


def build_preconditions(
    skill: SkillDefinition, role: str, model: str
) -> tuple[Precondition, ...]:
    """Resolve a skill's declared preconditions into executable checks."""
    checks: list[Precondition] = []
    for name in skill.preconditions:
        if name.endswith("_not_empty"):
            checks.append(_non_empty(name.removesuffix("_not_empty")))
        elif name == "expected_revenue_within_role_limit":
            checks.append(_revenue_within_role_limit(role))
        elif name.startswith("no_equivalent_open_"):
            checks.append(_no_equivalent_open_record(model, "customer_name"))
        else:
            raise UnknownPreconditionError(
                f"{skill.skill_id} declares precondition {name!r} with no "
                "executable implementation"
            )
    return tuple(checks)


def unmet_preconditions(
    skill: SkillDefinition,
    role: str,
    model: str,
    erp: ErpAdapter,
    args: dict[str, Any],
) -> list[str]:
    """Names of the declared preconditions that do not hold."""
    checks = build_preconditions(skill, role, model)
    return [
        name
        for name, check in zip(skill.preconditions, checks, strict=True)
        if not check(erp, args)
    ]
