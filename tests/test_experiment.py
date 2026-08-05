from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.experiment import _fresh_erp, run_experiment
from erp_agent_os.llm_client import DeterministicStubClient

CASES = generate_cases()
TEST_CASES = [c for c in CASES if c.split is DatasetSplit.FINAL_TEST]


def test_experiment_produces_1080_paired_observations():
    records, manifest = run_experiment(CASES, DeterministicStubClient())

    assert len(records) == 1080
    assert manifest.n_observations == 1080
    assert manifest.n_cases == 120
    assert manifest.n_repetitions == 3


def test_every_case_is_run_by_all_three_systems_the_same_number_of_times():
    records, _ = run_experiment(CASES, DeterministicStubClient())

    counts: dict[tuple[str, str], int] = {}
    for record in records:
        key = (record.request_id, record.system)
        counts[key] = counts.get(key, 0) + 1

    assert len(counts) == 120 * 3
    assert set(counts.values()) == {3}


def test_manifest_marks_stub_run_as_non_confirmatory():
    _, manifest = run_experiment(CASES, DeterministicStubClient())

    # A stub selector must never be mistaken for the section 19 protocol.
    assert manifest.is_confirmatory is False
    assert manifest.selector == "DeterministicStubClient"


def test_initial_state_is_identical_and_isolated_per_observation():
    case = next(
        c for c in TEST_CASES if c.canonical_intent.startswith("crm.update_expected")
    )
    first = _fresh_erp(case)
    second = _fresh_erp(case)

    assert first.snapshot() == second.snapshot()

    first.create("tasks.task", {"leak": True})
    assert first.snapshot() != second.snapshot()


def test_experiment_is_deterministic_for_a_fixed_seed():
    first, _ = run_experiment(CASES, DeterministicStubClient(), seed=7)
    second, _ = run_experiment(CASES, DeterministicStubClient(), seed=7)

    assert [(r.request_id, r.system, r.decision) for r in first] == [
        (r.request_id, r.system, r.decision) for r in second
    ]
