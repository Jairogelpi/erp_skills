from erp_agent_os.bench_generator import ABSTENTION_SENTINEL, generate_cases
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.dataset import CaseLabel, DatasetSplit, validate_case_groups


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
    cases = generate_cases()
    validate_case_groups(cases)  # raises ValueError on leakage


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
