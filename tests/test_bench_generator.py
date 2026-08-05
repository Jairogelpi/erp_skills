import pytest

from erp_agent_os.bench_generator import ABSTENTION_SENTINEL, generate_cases
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.dataset import (
    CaseLabel,
    DatasetSplit,
    validate_case_groups,
    validate_no_split_leakage,
)


def test_generates_exactly_480_cases():
    cases = generate_cases()
    assert len(cases) == 480


def test_split_allocation_is_240_120_120():
    cases = generate_cases()
    counts = {split: 0 for split in DatasetSplit}
    for case in cases:
        counts[case.split] += 1
    assert counts[DatasetSplit.DEVELOPMENT] == 240
    assert counts[DatasetSplit.VALIDATION] == 120
    assert counts[DatasetSplit.FINAL_TEST] == 120


def test_noise_and_adversarial_counts_match_spec():
    cases = generate_cases()
    noise = sum(1 for c in cases if CaseLabel.NOISE in c.labels)
    adversarial = sum(1 for c in cases if CaseLabel.ADVERSARIAL in c.labels)
    assert noise == 144
    assert adversarial == 96


def test_no_paraphrase_group_crosses_splits():
    # Contract check only. This assertion is WEAK by construction: every
    # case is its own group, so it cannot fail. The real leakage gate is
    # test_no_identical_text_or_semantics_crosses_splits below, which is
    # proven non-vacuous by a planted leak.
    cases = generate_cases()
    validate_case_groups(cases)


def test_validate_case_groups_still_detects_a_genuine_group_crossing():
    # Even though it is insufficient for this dataset, the mechanism must
    # work: a real shared group id spanning two splits has to raise.
    cases = generate_cases()
    dev = next(c for c in cases if c.split is DatasetSplit.DEVELOPMENT)
    twin = dev.model_copy(
        update={
            "request_id": "twin",
            "split": DatasetSplit.FINAL_TEST,
            "paraphrase_group_id": dev.paraphrase_group_id,
        }
    )
    with pytest.raises(ValueError, match="crosses splits"):
        validate_case_groups([dev, twin])


def test_expected_skill_is_cataloged_or_abstention():
    cases = generate_cases()
    for case in cases:
        assert (
            case.expected_skill in CATALOG_BY_ID
            or case.expected_skill == ABSTENTION_SENTINEL
        )


def test_request_ids_are_unique():
    cases = generate_cases()
    ids = [c.request_id for c in cases]
    assert len(ids) == len(set(ids))


def test_generation_is_deterministic():
    assert generate_cases() == generate_cases()


def test_24_canonical_intents_represented():
    cases = generate_cases()
    intents = {c.canonical_intent for c in cases}
    assert len(intents) == 24


def test_no_identical_text_or_semantics_crosses_splits():
    # Real leakage check: `validate_case_groups` is vacuous when every case
    # is its own group, so this asserts the two things that matter.
    validate_no_split_leakage(generate_cases())


def test_leakage_validator_actually_catches_a_planted_leak():
    cases = generate_cases()
    dev = next(c for c in cases if c.split is DatasetSplit.DEVELOPMENT)
    planted = dev.model_copy(
        update={"request_id": "planted", "split": DatasetSplit.FINAL_TEST}
    )
    with pytest.raises(ValueError, match="multiple splits"):
        validate_no_split_leakage([*cases, planted])


def test_every_request_text_is_unique():
    cases = generate_cases()
    texts = [c.request_text for c in cases]
    assert len(set(texts)) == len(texts) == 480
