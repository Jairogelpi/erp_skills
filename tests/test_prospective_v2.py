from collections import Counter

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import CaseLabel, DatasetSplit
from erp_agent_os.prospective_v2 import generate_v2_candidates


def test_v2_has_declared_size_intents_and_label_balance():
    cases = generate_v2_candidates()

    labels = Counter(label for case in cases for label in case.labels)
    assert len(cases) == 120
    assert len({case.canonical_intent for case in cases}) == 24
    assert set(Counter(case.canonical_intent for case in cases).values()) == {5}
    assert labels == {
        CaseLabel.NORMAL: 60,
        CaseLabel.NOISE: 36,
        CaseLabel.ADVERSARIAL: 24,
    }
    assert all(case.split is DatasetSplit.FINAL_TEST for case in cases)


def test_v2_is_deterministic_and_has_unique_ids_and_texts():
    first = generate_v2_candidates()
    second = generate_v2_candidates()

    assert first == second
    assert len({case.request_id for case in first}) == 120
    assert len({case.request_text.casefold() for case in first}) == 120
    assert all(case.request_id.startswith("v2-r") for case in first)


def test_v2_does_not_reuse_v1_text_or_intent_argument_pairs():
    v1 = generate_cases()
    v2 = generate_v2_candidates()
    old_texts = {case.request_text.casefold() for case in v1}
    old_semantics = {
        (case.canonical_intent, repr(sorted(case.expected_arguments.items())))
        for case in v1
        if case.expected_arguments
        and all(value not in ("", None) for value in case.expected_arguments.values())
    }

    assert not old_texts & {case.request_text.casefold() for case in v2}
    assert not old_semantics & {
        (case.canonical_intent, repr(sorted(case.expected_arguments.items())))
        for case in v2
        if case.expected_arguments
        and all(value not in ("", None) for value in case.expected_arguments.values())
    }


def test_v2_candidates_are_not_mistaken_for_adjudicated_gold():
    cases = generate_v2_candidates()

    assert all(case.initial_state == {"oracle_pending": True} for case in cases)
    assert all(case.expected_final_state == {"oracle_pending": True} for case in cases)
    assert any(case.clarification_required for case in cases)
    assert any(case.expected_skill.startswith("sin_skill") for case in cases)
