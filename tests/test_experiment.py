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


def test_future_records_preserve_auditable_evidence():
    records, _ = run_experiment(CASES, DeterministicStubClient(), repetitions=1)
    by_system = {
        system: next(r for r in records if r.system == system) for system in "ABC"
    }

    for record in records:
        assert record.initial_state
        assert record.final_state
        assert isinstance(record.normalized_arguments, dict)
        assert record.role == "erp_user"
        assert record.traceability_components != "not_available"
        assert len(record.traceability_components) == 7

    assert by_system["A"].candidate_scores == "not_available"
    assert by_system["A"].permission_evidence == "not_available"
    assert by_system["B"].candidate_scores == "not_available"
    assert isinstance(by_system["C"].candidate_scores, dict)
    assert by_system["C"].permission_evidence != "not_available"


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


def test_checkpoint_resume_reproduces_the_same_records_as_a_fresh_run(tmp_path):
    baseline, _ = run_experiment(CASES, DeterministicStubClient(), seed=7)

    checkpoint = tmp_path / "checkpoint.jsonl"
    run_experiment(CASES, DeterministicStubClient(), seed=7, checkpoint_path=checkpoint)
    all_lines = checkpoint.read_text(encoding="utf-8").splitlines()
    assert len(all_lines) == 1080

    # Simulate an interrupted run: only the first half survived.
    checkpoint.write_text("\n".join(all_lines[:400]) + "\n", encoding="utf-8")

    resumed, manifest = run_experiment(
        CASES, DeterministicStubClient(), seed=7, checkpoint_path=checkpoint
    )

    assert manifest.n_observations == 1080
    assert len(resumed) == 1080
    resumed_sorted = sorted(
        resumed, key=lambda r: (r.request_id, r.system, r.repetition)
    )
    baseline_sorted = sorted(
        baseline, key=lambda r: (r.request_id, r.system, r.repetition)
    )
    assert [(r.request_id, r.system, r.decision) for r in resumed_sorted] == [
        (r.request_id, r.system, r.decision) for r in baseline_sorted
    ]
    # Resuming completed the rest: the checkpoint file now has all 1.080.
    assert len(checkpoint.read_text(encoding="utf-8").splitlines()) == 1080


def test_each_system_pays_its_own_argument_extraction():
    # Regression for a real measurement bug: a single CachingLLMClient
    # was shared by A, B and C. Extraction is keyed on
    # (query_text, fields) -- identical across the three systems for the
    # same case -- so whichever system the randomized order ran first
    # paid, and the other two were credited 0 tokens. Per-system token
    # totals then measured execution order, not architecture.
    class _ExtractingStub(DeterministicStubClient):
        def extract_arguments(self, query_text, fields):
            from erp_agent_os.llm_client import ArgumentExtraction

            return ArgumentExtraction({f: "x" for f in fields}, 100, 10)

    records, _ = run_experiment(
        CASES, _ExtractingStub(), seed=7, real_parser=True, repetitions=2
    )

    per_system = {"A": 0, "B": 0, "C": 0}
    for record in records:
        per_system[record.system] += record.prompt_tokens

    # Every system must have paid for extraction on every case. With the
    # shared cache, two of the three came out at (or near) zero.
    assert all(total > 0 for total in per_system.values()), per_system
    # And each pays the same extraction bill: same cases, same fields,
    # same prompt (CLAUDE.md D-03).
    assert per_system["A"] == per_system["B"] == per_system["C"], per_system


def test_repetitions_reuse_the_first_real_llm_call_for_the_same_case():
    class _CountingStub(DeterministicStubClient):
        def __init__(self):
            self.calls = 0

        def propose_action(self, query_text, tools):
            self.calls += 1
            return super().propose_action(query_text, tools)

    llm = _CountingStub()
    run_experiment(CASES, llm, seed=7)

    # 120 cases, each queried once for A and once for B regardless of the
    # 3 repetitions -- caching cuts real calls to a third.
    assert llm.calls == 120 * 2
