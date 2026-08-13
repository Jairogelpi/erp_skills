import re
from collections import Counter

import pytest

from erp_agent_os.bench_intents import INTENTS
from erp_agent_os.bench_v2 import (
    BenchV2Error,
    EdgeKind,
    RecordedAuthor,
    ScenarioKind,
    build_author_prompt,
    generate_v2,
    validate_v2,
)
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.validation import blocking_findings, validate_arguments


class RecordingAuthor:
    provider = "author-provider"
    model = "author-model"

    def __init__(self):
        self.prompts = []

    def author(self, *, prompt: str) -> str:
        self.prompts.append(prompt)
        return f"Petición v2 única número {len(self.prompts)} para ERP."


def generated():
    author = RecordingAuthor()
    cases, provenance = generate_v2(
        author=author,
        selector_provider="selector-provider",
        selector_model="selector-model",
    )
    return author, cases, provenance


def test_exact_contract_120_five_per_intent_and_scenarios() -> None:
    _, cases, provenance = generated()
    assert len(cases) == 120
    assert Counter(case.intent_id for case in cases) == {
        intent.intent_id: 5 for intent in INTENTS
    }
    for intent in INTENTS:
        bucket = [case for case in cases if case.intent_id == intent.intent_id]
        assert Counter(case.scenario for case in bucket) == {
            ScenarioKind.ORDINARY: 3,
            ScenarioKind.NOISY: 1,
            ScenarioKind.GOVERNED_EDGE: 1,
        }
    assert sum(provenance.edge_counts.values()) == 24


def test_author_prompt_has_only_intent_entities_and_transformation() -> None:
    author, _, _ = generated()
    prompts = "\n".join(author.prompts)
    for forbidden in (
        "expected_skill",
        "expected_decision",
        "threshold",
        "ranking",
        "System C",
        "postconditions",
        "oracle",
    ):
        assert forbidden not in prompts
    assert "Intención canónica" in prompts
    assert "Entidades sintéticas seguras" in prompts


def test_oracle_is_compiled_not_authored() -> None:
    author, cases, _ = generated()
    assert all(
        "ALLOW" not in prompt and "DENY" not in prompt for prompt in author.prompts
    )
    assert {case.expected_decision for case in cases} >= {
        "ALLOW",
        "DENY",
        "REQUIRE_APPROVAL",
        "CLARIFY",
        "ABSTAIN",
        "SIMULATE",
    }


def test_range_denial_cases_target_a_field_the_real_validator_actually_bounds() -> (
    None
):
    """The RANGE_DENIAL oracle claims DENY/dangerous. That claim is only true
    if erp_agent_os.validation actually rejects the compiled arguments —
    otherwise the case silently mislabels a real ALLOW as an expected DENY in
    the confirmatory dangerous-case set (the same defect class as v1's #14).
    """
    _, cases, _ = generated()
    range_denial_cases = [
        case for case in cases if case.edge_kind is EdgeKind.RANGE_DENIAL
    ]
    assert range_denial_cases, "fixture drifted: no RANGE_DENIAL cases generated"
    for case in range_denial_cases:
        assert case.expected_skill is not None
        skill = CATALOG_BY_ID[case.expected_skill]
        findings = validate_arguments(skill, case.expected_arguments)
        assert blocking_findings(findings), (
            f"{case.request_id} ({case.intent_id}) expects DENY from a range "
            f"violation, but validate_arguments finds nothing wrong with "
            f"{case.expected_arguments!r} against {skill.skill_id}'s schema"
        )


def test_author_and_selector_must_differ() -> None:
    with pytest.raises(BenchV2Error, match="must differ"):
        generate_v2(
            author=RecordedAuthor(provider="same", model="same", texts=[]),
            selector_provider="same",
            selector_model="same",
        )


def test_validator_rejects_exact_v1_hash_and_duplicates() -> None:
    _, cases, provenance = generated()
    with pytest.raises(BenchV2Error, match="v1"):
        validate_v2(cases, provenance, v1_hashes={cases[0].request_sha256})
    duplicate = list(cases)
    duplicate[1] = duplicate[0]
    with pytest.raises(BenchV2Error, match="unique"):
        validate_v2(duplicate, provenance, v1_hashes=set())


def test_generation_is_deterministic_for_same_author_responses() -> None:
    texts = [f"Texto independiente {i}" for i in range(120)]
    first, p1 = generate_v2(
        author=RecordedAuthor(provider="a", model="m", texts=texts),
        selector_provider="b",
        selector_model="n",
    )
    second, p2 = generate_v2(
        author=RecordedAuthor(provider="a", model="m", texts=texts),
        selector_provider="b",
        selector_model="n",
    )
    assert first == second
    assert p1 == p2


def test_prompt_builder_does_not_accept_oracle_fields() -> None:
    signature = str(build_author_prompt.__annotations__)
    assert not re.search(r"expected|decision|skill", signature, re.IGNORECASE)
