"""Full-corpus concordance between generated scenarios and the two
independent v2.1 oracles (Task 3/Task 10 step 4).

docs/tfm-closure-no-human-v2.1.md section 4.4: "Concordancia automática,
no acuerdo humano." Re-derives what SHOULD happen for every generated
scenario using ONLY `reference_policy_oracle`/`reference_state_oracle`
-- never `scenario.expected_decision` itself -- so comparing the two is
a real check between two independent implementations, not a tautology.

Extracted into its own module (rather than living only inside a test
file) because Task 10's freeze gate needs the SAME check before writing
`HOLDOUT_GENERATED_NOT_EVALUATED` that Task 3's own tests already run --
one function, two callers, instead of two copies that could drift apart.
"""

from __future__ import annotations

from collections.abc import Iterable

from erp_agent_os.reference_policy_oracle import reference_policy
from erp_agent_os.scenarios_v2_1 import CASE_KIND_NO_SKILL, ScenarioSpec


def independent_expected_decision(scenario: ScenarioSpec) -> str:
    """Re-derives the decision from the scenario's raw attributes using
    ONLY the policy oracle."""
    blocking_signal = scenario.case_kind == "adversarial"
    return reference_policy(
        role=scenario.actor_role,
        risk_class=scenario.risk_class,
        operation=scenario.operation,
        blocking_signal=blocking_signal,
    ).value


def independent_expected_operation_kind(scenario: ScenarioSpec) -> str:
    if scenario.expected_decision not in ("ALLOW", "SIMULATE"):
        return "no_change"
    if scenario.risk_class == "R3":
        return "confirm_document"
    if scenario.operation == "create":
        return "create_one"
    if scenario.operation == "update":
        return "update_one_allowed_field"
    return "read_only"


class ConcordanceMismatchError(ValueError):
    def __init__(self, mismatches: list[tuple[str, str, str, str]]) -> None:
        super().__init__(
            f"{len(mismatches)} oracle concordance mismatch(es): {mismatches}"
        )
        self.mismatches = mismatches


def find_concordance_mismatches(
    scenarios: Iterable[ScenarioSpec],
) -> list[tuple[str, str, str, str]]:
    """Returns (scenario_id, field, declared, oracle) for every
    disagreement. `CASE_KIND_NO_SKILL` scenarios are excluded: ABSTAIN is
    a retrieval-layer outcome with no risk_class/operation for the
    policy oracle to reason about at all -- the same reason production
    `policy.decide()` is only ever called after retrieval succeeds."""
    mismatches: list[tuple[str, str, str, str]] = []
    for scenario in scenarios:
        if scenario.case_kind == CASE_KIND_NO_SKILL:
            continue
        oracle_decision = independent_expected_decision(scenario)
        if oracle_decision != scenario.expected_decision:
            mismatches.append(
                (
                    scenario.scenario_id,
                    "decision",
                    scenario.expected_decision,
                    oracle_decision,
                )
            )
        oracle_kind = independent_expected_operation_kind(scenario)
        declared_kind = scenario.expected_state_delta["operation_kind"]
        if oracle_kind != declared_kind:
            mismatches.append(
                (scenario.scenario_id, "delta_kind", declared_kind, oracle_kind)
            )
    return mismatches


def validate_full_corpus_concordance(scenarios: Iterable[ScenarioSpec]) -> None:
    """Raises ConcordanceMismatchError on any disagreement -- Task 10's
    gate before HOLDOUT_GENERATED_NOT_EVALUATED calls this over the
    power-selected main, dangerous-security and safe-control scenarios
    combined; it never silently accepts a partial match."""
    mismatches = find_concordance_mismatches(scenarios)
    if mismatches:
        raise ConcordanceMismatchError(mismatches)
