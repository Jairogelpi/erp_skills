"""H8 cost sensitivity grid (Task 9B).

docs/tfm-closure-no-human-v2.1.md section 8, H8: "Continúa siendo un
análisis de escenarios, no una hipótesis de ahorro observado." This
module computes a deterministic cost breakdown for every (system, grid
point) combination and publishes ALL of them -- never only the point
most favorable to C, and never a directional pass/fail verdict, because
H8 is not a hypothesis test.

**Measured vs. hypothetical, kept structurally separate.** Section 8 is
explicit about which inputs are real ("reintentos y tokens: valores
realmente observados en la campaña") and which are assumed ("coste
horario hipotético de revisión... tiempo hipotético de revisión...
coste hipotético por error"). `MeasuredComponents` holds only counts
read directly off real `ObservationV21` rows (tokens, retries, how many
scenarios required approval, how many failed the evaluator);
`CostGridPoint` holds only the four hypothetical unit prices from
config/protocol_v2_1.json's h8 block. `CostBreakdown` combines them but
never blurs which is which -- `MEASURED_FIELD_NAMES`/
`HYPOTHETICAL_FIELD_NAMES` name the split explicitly, and no field on
any dataclass here is ever named `observed_savings` (there is no
"savings" claim to make -- CLAUDE.md section 20: "Nunca se escribirá
que se ahorraron euros reales").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from erp_agent_os.evidence_v2_1 import ObservationV21, System
from erp_agent_os.protocol_v2_1 import H8CostGrid

MEASURED_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "n_scenarios",
        "total_tokens",
        "n_retries",
        "n_review_required",
        "n_observed_errors",
    }
)
HYPOTHETICAL_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "inference_price_eur_per_million_tokens",
        "review_cost_eur_per_hour",
        "review_minutes",
        "error_cost_eur",
    }
)


class CostScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class CostGridPoint:
    """One combination of the four hypothetical unit prices section 8
    fixes before the holdout. Every field name here is also listed in
    HYPOTHETICAL_FIELD_NAMES -- nothing on this dataclass is measured."""

    inference_price_eur_per_million_tokens: float
    review_cost_eur_per_hour: float
    review_minutes: float
    error_cost_eur: float


def build_cost_grid(config: H8CostGrid) -> tuple[CostGridPoint, ...]:
    """The full Cartesian product of config's four dimensions -- 3x3x3x3
    = 81 points, per config/protocol_v2_1.json's h8 block, each already
    validated to have exactly 3 levels by protocol_v2_1.H8CostGrid
    itself. No filtering, no "representative subset": every combination
    section 8 requires published, published."""
    return tuple(
        CostGridPoint(
            inference_price_eur_per_million_tokens=inference_price,
            review_cost_eur_per_hour=review_hourly,
            review_minutes=review_minutes,
            error_cost_eur=error_cost,
        )
        for inference_price, review_hourly, review_minutes, error_cost in product(
            config.inference_price_eur_per_million_tokens,
            config.review_cost_eur_per_hour,
            config.review_minutes,
            config.error_cost_eur,
        )
    )


@dataclass(frozen=True)
class MeasuredComponents:
    """Counts read directly off real ObservationV21 rows for one system
    -- nothing here is assumed or hypothesized. Every field name here is
    also listed in MEASURED_FIELD_NAMES."""

    system: System
    n_scenarios: int
    total_tokens: int
    n_retries: int
    n_review_required: int
    n_observed_errors: int


def measure_components(
    observations: Sequence[ObservationV21], *, system: System
) -> MeasuredComponents:
    """`n_retries` counts attempts BEYOND the first, per call, summed
    across every row -- a row whose call_events has 3 entries for one
    logical call (2 failures + 1 success) contributes 2 retries, never
    the raw event count, which would conflate "how many calls happened"
    with "how many had to be retried". `n_review_required` uses the
    REAL governed decision (REQUIRE_APPROVAL), not a hypothetical
    review policy. `n_observed_errors` is the real STSR outcome
    (evaluator_components["success"] is False), never postulated."""
    rows = [o for o in observations if o.system == system]
    if not rows:
        raise CostScenarioError(f"no observations for system {system!r}")

    total_tokens = sum(
        event.prompt_tokens + event.completion_tokens
        for row in rows
        for event in row.call_events
    )
    n_retries = sum(max(0, len(row.call_events) - 1) for row in rows)
    n_review_required = sum(
        1 for row in rows if row.policy_decision == "REQUIRE_APPROVAL"
    )
    n_observed_errors = sum(
        1 for row in rows if not row.evaluator_components.get("success", False)
    )
    return MeasuredComponents(
        system=system,
        n_scenarios=len(rows),
        total_tokens=total_tokens,
        n_retries=n_retries,
        n_review_required=n_review_required,
        n_observed_errors=n_observed_errors,
    )


@dataclass(frozen=True)
class CostBreakdown:
    """One (system, grid point) combination's cost, with every
    component broken out separately -- a report can show inference/
    review/error cost individually, not just a single opaque total.
    Deliberately has no verdict/pass-fail field: H8 is a sensitivity
    analysis, not a hypothesis test (section 8's own framing)."""

    system: System
    grid_point: CostGridPoint
    n_scenarios: int
    total_tokens: int
    n_retries: int
    n_review_required: int
    n_observed_errors: int
    inference_cost_eur: float
    review_cost_eur: float
    error_cost_eur: float
    total_cost_eur: float


def compute_cost_breakdown(
    measured: MeasuredComponents, grid_point: CostGridPoint
) -> CostBreakdown:
    inference_cost = (
        measured.total_tokens / 1_000_000
    ) * grid_point.inference_price_eur_per_million_tokens
    review_cost = (
        measured.n_review_required
        * (grid_point.review_minutes / 60.0)
        * grid_point.review_cost_eur_per_hour
    )
    error_cost = measured.n_observed_errors * grid_point.error_cost_eur
    return CostBreakdown(
        system=measured.system,
        grid_point=grid_point,
        n_scenarios=measured.n_scenarios,
        total_tokens=measured.total_tokens,
        n_retries=measured.n_retries,
        n_review_required=measured.n_review_required,
        n_observed_errors=measured.n_observed_errors,
        inference_cost_eur=inference_cost,
        review_cost_eur=review_cost,
        error_cost_eur=error_cost,
        total_cost_eur=inference_cost + review_cost + error_cost,
    )


def compute_cost_sensitivity(
    observations: Sequence[ObservationV21],
    config: H8CostGrid,
    *,
    systems: Sequence[System] = ("A", "B", "C"),
) -> tuple[CostBreakdown, ...]:
    """Every system x every grid point -- 3 x 81 = 243 breakdowns by
    default, none omitted, none singled out as "the result"."""
    grid = build_cost_grid(config)
    results: list[CostBreakdown] = []
    for system in systems:
        measured = measure_components(observations, system=system)
        for point in grid:
            results.append(compute_cost_breakdown(measured, point))
    return tuple(results)


def validate_cost_grid_coverage(
    results: Sequence[CostBreakdown], config: H8CostGrid, *, systems: Sequence[System]
) -> None:
    """Step 1: reject missing OR selectively filtered scenarios -- every
    system must carry the exact 81-point grid, no more, no fewer, and
    no duplicate grid point within a system."""
    expected_grid = set(build_cost_grid(config))
    for system in systems:
        system_points = [r.grid_point for r in results if r.system == system]
        if len(system_points) != len(set(system_points)):
            raise CostScenarioError(f"system {system!r} has duplicate grid points")
        actual = set(system_points)
        missing = expected_grid - actual
        extra = actual - expected_grid
        if missing:
            raise CostScenarioError(
                f"system {system!r} is missing {len(missing)} grid point(s)"
            )
        if extra:
            raise CostScenarioError(
                f"system {system!r} has {len(extra)} grid point(s) outside the "
                "registered grid"
            )
