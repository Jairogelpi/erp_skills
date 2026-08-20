"""Machine-readable protocol contract for TFM Closure v2.1.

docs/tfm-closure-no-human-v2.1.md is the normative spec; this module
turns its acceptance criteria, arm settings and analysis rules into a
strict, versioned, `extra="forbid"` schema so nothing confirmatory can
be decided by an implicit constant buried in analysis code -- every
threshold in sections 8/10/12 of the spec is a field here, not a magic
number chosen after seeing the holdout.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ProtocolV21Error(RuntimeError):
    """Raised for protocol-loading problems outside Pydantic's own
    field-level validation (e.g. a missing config file)."""


class _Model(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class H1Protocol(_Model):
    """Section 8, H1a/H1b."""

    non_inferiority_margin: float
    superiority_null_margin: float
    minimum_relevant_difference: float

    @field_validator("non_inferiority_margin")
    @classmethod
    def margin_is_negative(cls, value: float) -> float:
        if value >= 0:
            raise ValueError("non_inferiority_margin must be negative")
        return value

    @field_validator("minimum_relevant_difference")
    @classmethod
    def relevant_difference_is_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("minimum_relevant_difference must be positive")
        return value


class H2Protocol(_Model):
    """Section 8, H2: never cached, never mixed with another arm's tokens."""

    cache_policy: str

    @field_validator("cache_policy")
    @classmethod
    def must_not_cache(cls, value: str) -> str:
        if value != "no_cache":
            raise ValueError("H2 must never use a cached/shared response")
        return value


class H3Protocol(_Model):
    """Section 6.4/8, H3a primary + H3b secondary."""

    h3b_min_calls: int
    h3b_sample_size: int

    @field_validator("h3b_min_calls")
    @classmethod
    def at_least_three_calls(cls, value: int) -> int:
        if value < 3:
            raise ValueError("H3b requires at least three independent calls")
        return value


class H4Protocol(_Model):
    """Section 8, H4: security."""

    unauthorized_mutation_upper_bound: float
    minimum_relevant_difference: float
    n_categories: int

    @field_validator("n_categories")
    @classmethod
    def seven_categories(cls, value: int) -> int:
        # Was 8; r4_operation retired 2026-08-20 (docs/results-v2.1.md
        # section 4 / docs/tfm-closure-no-human-v2.1.md's dated
        # amendment) -- verified against the real campaign that its
        # dangerous/safe pair was byte-identical in every
        # system-observable field, so no system could ever have told
        # them apart. security_scenarios_v2_1.H4_ATTACK_CATEGORIES is
        # the single source of truth this must stay equal to.
        if value != 7:
            raise ValueError("H4 declares exactly seven attack categories")
        return value


class H5Protocol(_Model):
    """Section 8, H5: operational thresholds, all three required jointly."""

    selective_accuracy_min: float
    false_reuse_max: float
    coverage_min: float


class H7Protocol(_Model):
    """Section 8, H7: binary all-seven-facts audit reconstruction."""

    n_facts: int

    @field_validator("n_facts")
    @classmethod
    def seven_facts(cls, value: int) -> int:
        if value != 7:
            raise ValueError("H7 declares exactly seven audit facts")
        return value


class H8CostGrid(_Model):
    """Section 8, H8: the complete frozen sensitivity grid."""

    inference_price_eur_per_million_tokens: list[float]
    review_cost_eur_per_hour: list[float]
    review_minutes: list[float]
    error_cost_eur: list[float]

    @field_validator(
        "inference_price_eur_per_million_tokens",
        "review_cost_eur_per_hour",
        "review_minutes",
        "error_cost_eur",
    )
    @classmethod
    def exactly_three_levels(cls, value: list[float]) -> list[float]:
        if len(value) != 3:
            raise ValueError("each H8 grid dimension declares exactly 3 levels")
        return value


class PowerSettings(_Model):
    """Section 10: power/multiplicity."""

    alpha_family: float
    power_target: float
    min_monte_carlo_replicates: int

    @field_validator("power_target")
    @classmethod
    def power_at_least_80(cls, value: float) -> float:
        if value < 0.80:
            raise ValueError("power_target must be >= 0.80")
        return value

    @field_validator("min_monte_carlo_replicates")
    @classmethod
    def at_least_100k_replicates(cls, value: int) -> int:
        if value < 100_000:
            raise ValueError("min_monte_carlo_replicates must be >= 100000")
        return value


class ProtocolV21(_Model):
    """Root contract. `holm_families` names, for every hypothesis family
    that pools multiple comparisons under one Holm correction, the exact
    comparisons in that family -- e.g. {"h1b": ["c_vs_a", "c_vs_b"],
    "h4": ["false_allow_c_vs_a", "false_allow_c_vs_b",
    "detection_recall_c_vs_a", "detection_recall_c_vs_b"]}."""

    protocol_version: str
    h1: H1Protocol
    h2: H2Protocol
    h3: H3Protocol
    h4: H4Protocol
    h5: H5Protocol
    h7: H7Protocol
    h8: H8CostGrid
    power: PowerSettings
    holm_families: dict[str, list[str]]
    human_annotation_required: bool = False

    @field_validator("human_annotation_required")
    @classmethod
    def never_requires_human_annotation(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "human_annotation_required must never be true for v2.1 "
                "(docs/tfm-closure-no-human-v2.1.md section 1)"
            )
        return value

    @model_validator(mode="after")
    def holm_families_cover_h1b_and_h4(self) -> ProtocolV21:
        required = {"h1b", "h4"}
        missing = required - set(self.holm_families)
        if missing:
            raise ValueError(f"holm_families is missing required families: {missing}")
        for name in required:
            if len(self.holm_families[name]) < 2:
                raise ValueError(
                    f"holm_families[{name!r}] must list at least two comparisons"
                )
        return self


def load_protocol(path: Path) -> ProtocolV21:
    if not path.is_file():
        raise ProtocolV21Error(f"protocol config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ProtocolV21(**payload)
