"""Tests for scripts/run_experiment.py's own reporting logic."""

import importlib.util
import pathlib

import pytest

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.evidence import load_observations_jsonl
from erp_agent_os.experiment import run_experiment
from erp_agent_os.llm_client import DeterministicStubClient

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "scripts" / "run_experiment.py"
)
_spec = importlib.util.spec_from_file_location("run_experiment_script", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
run_experiment_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_experiment_script)


def test_caveat_matches_prospectively_frozen_real_run():
    caveat = run_experiment_script._manifest_caveat(
        provider_is_real_llm=True,
        selector="GroqClient",
        epistemic_status="prospectively_frozen_unseen",
    )
    assert "IS the section 19 confirmatory protocol" in caveat
    assert "NOT the CLAUDE.md section 19" not in caveat


def test_caveat_matches_stub_run():
    caveat = run_experiment_script._manifest_caveat(
        provider_is_real_llm=False,
        selector="DeterministicStubClient",
        epistemic_status="prospectively_frozen_unseen",
    )
    assert "NOT the CLAUDE.md section 19" in caveat
    assert "IS the section 19 confirmatory protocol" not in caveat


def test_current_v1_runs_are_always_post_freeze_exploratory():
    status = run_experiment_script._epistemic_status(
        dataset_generation="v1", test_has_been_inspected=True
    )
    assert status == "post_freeze_exploratory"


def test_unseen_v2_is_prospective():
    status = run_experiment_script._epistemic_status(
        dataset_generation="v2", test_has_been_inspected=False
    )
    assert status == "prospectively_frozen_unseen"


def test_inspected_v1_cannot_be_marked_confirmatory():
    with pytest.raises(ValueError, match="unseen"):
        run_experiment_script._validate_epistemic_status(
            "confirmatory", dataset_generation="v1", test_has_been_inspected=True
        )


def test_caveat_names_the_actual_selector_used():
    caveat = run_experiment_script._manifest_caveat(
        provider_is_real_llm=True,
        selector="OpenRouterClient",
        epistemic_status="prospectively_frozen_unseen",
    )
    assert "OpenRouterClient" in caveat
    assert "Groq" not in caveat


def test_post_freeze_caveat_forbids_confirmatory_claim_even_with_real_llm():
    caveat = run_experiment_script._manifest_caveat(
        provider_is_real_llm=True,
        selector="OpenRouterClient",
        epistemic_status="post_freeze_exploratory",
    )

    assert "post-freeze exploratory" in caveat
    assert "cannot support a confirmatory conclusion" in caveat


@pytest.mark.parametrize(
    ("real_llm", "real_parser", "temperature", "message"),
    [
        (False, True, None, "real LLM"),
        (True, False, None, "real parser"),
        (True, True, 0.2, "temperature"),
    ],
)
def test_v2_confirmatory_gate_rejects_nonprotocol_configuration(
    real_llm, real_parser, temperature, message
):
    with pytest.raises(ValueError, match=message):
        run_experiment_script._validate_v2_configuration(
            real_llm=real_llm,
            real_parser=real_parser,
            temperature=temperature,
        )


def test_v2_confirmatory_gate_accepts_real_low_temperature_parsed_run():
    run_experiment_script._validate_v2_configuration(
        real_llm=True, real_parser=True, temperature=None
    )


def test_v2_receipt_is_bound_to_gold_hash_and_refuses_reuse(tmp_path):
    final_manifest = {
        "hashes": {"gold_sha256": "a" * 64},
        "system_evaluation_allowed": True,
    }
    receipt = run_experiment_script._v2_receipt_path(
        tmp_path / "freeze.json", final_manifest
    )
    assert receipt.name == f"bench_v2_evaluation_receipt_{'a' * 64}.json"
    receipt.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="already been consumed"):
        run_experiment_script._assert_v2_unconsumed(receipt)


def test_future_run_persists_exact_raw_units_and_provenance(tmp_path):
    cases = generate_cases()
    test_cases = [case for case in cases if case.split is DatasetSplit.FINAL_TEST]
    records, manifest = run_experiment(cases, DeterministicStubClient(), repetitions=1)

    archive = run_experiment_script._persist_observation_archive(
        records,
        test_cases,
        manifest,
        tmp_path / "report.json",
        epistemic_status="post_freeze_exploratory",
        temperature=None,
    )
    loaded = load_observations_jsonl(archive.path)

    assert archive.row_count == 360
    assert len(loaded.records) == 360
    assert loaded.provenance["freeze_hashes"]["test_split_hash"]
    assert loaded.provenance["code_hash"]
    assert loaded.provenance["epistemic_status"] == "post_freeze_exploratory"
