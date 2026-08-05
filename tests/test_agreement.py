import pytest

from erp_agent_os.agreement import cohens_kappa, stratified_review_sample
from erp_agent_os.bench_generator import generate_cases


def test_perfect_agreement_is_kappa_one():
    labels = ["ALLOW", "DENY", "CLARIFY", "ALLOW"]
    assert cohens_kappa(labels, labels).kappa == 1.0


def test_chance_level_agreement_is_near_zero():
    # Two annotators alternating independently over two equally-frequent
    # categories: observed agreement 0.5, expected 0.5 -> kappa 0.
    first = ["A", "A", "B", "B"]
    second = ["A", "B", "A", "B"]
    assert cohens_kappa(first, second).kappa == pytest.approx(0.0)


def test_known_worked_example():
    # 2x2 confusion: both-yes=20, both-no=15, disagreements 5 and 10.
    # observed = 35/50 = .70 ; expected = .5*.6 + .5*.4 = .50
    # kappa = (.70-.50)/(1-.50) = .40
    first = ["Y"] * 20 + ["Y"] * 5 + ["N"] * 10 + ["N"] * 15
    second = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
    result = cohens_kappa(first, second)

    assert result.observed_agreement == pytest.approx(0.70)
    assert result.expected_agreement == pytest.approx(0.50)
    assert result.kappa == pytest.approx(0.40)
    assert result.interpretation() == "fair"


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        cohens_kappa(["A"], ["A", "B"])


def test_rejects_empty_sample():
    with pytest.raises(ValueError):
        cohens_kappa([], [])


def test_sample_is_deterministic_and_covers_all_labels():
    cases = generate_cases()
    sample = stratified_review_sample(cases)

    assert sample == stratified_review_sample(cases)
    labels = {
        "ADVERSARIAL"
        if any(label.value == "ADVERSARIAL" for label in c.labels)
        else "NOISE"
        if any(label.value == "NOISE" for label in c.labels)
        else "NORMAL"
        for c in sample
    }
    assert labels == {"NORMAL", "NOISE", "ADVERSARIAL"}


def test_sample_oversamples_adversarial_relative_to_corpus():
    cases = generate_cases()
    sample = stratified_review_sample(cases)

    def adversarial_share(items):
        hits = sum(
            1 for c in items if any(label.value == "ADVERSARIAL" for label in c.labels)
        )
        return hits / len(items)

    # 20% of the corpus is adversarial; the review sample must weight it
    # more heavily, since that is where mis-annotation hurts most.
    assert adversarial_share(sample) > adversarial_share(cases)
