"""TDD for scripts/run_targeted_mutations_v2_1.py (v2.1 plan, Task 7C).

Fast, contract-only tests. The real seven-mutant run against the full
evaluator is a deliberately separate, slower command
(scripts/run_targeted_mutations_v2_1.py --verify), the same split
run_power_v2_1.py already established between its fast test module and
its own real full-scale script.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "run_targeted_mutations_v2_1.py"
)
_spec = importlib.util.spec_from_file_location(
    "run_targeted_mutations_v2_1_script", _SCRIPT_PATH
)
assert _spec is not None and _spec.loader is not None
mutations = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mutations)


def _valid_mutant(**overrides) -> dict:
    base = {
        "mutant_id": "example",
        "operator": "constant_replacement",
        "source_path": "src/erp_agent_os/evaluator_v2_1.py",
        "original_expression": "    x = 1",
        "replacement_expression": "    x = 2",
        "kill_tests": ["tests/test_example.py::test_x"],
    }
    base.update(overrides)
    return base


def test_real_config_loads_and_validates():
    config = mutations.load_config()
    ids = {m["mutant_id"] for m in config["mutants"]}
    assert ids == mutations.REQUIRED_MUTANT_IDS


def test_config_requires_all_seven_registered_mutant_ids():
    config = {"mutants": [_valid_mutant()]}
    with pytest.raises(mutations.MutationHarnessError, match="missing required"):
        mutations.validate_config(config)


def test_config_rejects_duplicate_mutant_ids():
    required_ids = sorted(mutations.REQUIRED_MUTANT_IDS)
    config = {
        "mutants": [_valid_mutant(mutant_id=mid) for mid in required_ids]
        + [_valid_mutant(mutant_id=required_ids[0])]
    }
    with pytest.raises(mutations.MutationHarnessError, match="duplicate"):
        mutations.validate_config(config)


def test_config_rejects_unknown_operator():
    config = {
        "mutants": [
            _valid_mutant(mutant_id=mid, operator="teleport_the_whole_file")
            for mid in sorted(mutations.REQUIRED_MUTANT_IDS)
        ]
    }
    with pytest.raises(mutations.MutationHarnessError, match="unknown operator"):
        mutations.validate_config(config)


def test_config_rejects_missing_source_expression():
    required_ids = sorted(mutations.REQUIRED_MUTANT_IDS)
    config = {
        "mutants": [
            _valid_mutant(
                mutant_id=mid,
                original_expression="" if mid == required_ids[0] else "x",
            )
            for mid in required_ids
        ]
    }
    with pytest.raises(mutations.MutationHarnessError, match="original_expression"):
        mutations.validate_config(config)


def test_config_requires_focused_kill_tests():
    required_ids = sorted(mutations.REQUIRED_MUTANT_IDS)
    config = {
        "mutants": [
            _valid_mutant(
                mutant_id=mid,
                kill_tests=[] if mid == required_ids[0] else ["t"],
            )
            for mid in required_ids
        ]
    }
    with pytest.raises(mutations.MutationHarnessError, match="kill_tests"):
        mutations.validate_config(config)


def test_config_with_no_mutants_at_all_is_rejected():
    with pytest.raises(mutations.MutationHarnessError, match="no registered mutants"):
        mutations.validate_config({"mutants": []})


def test_apply_mutation_requires_exactly_one_occurrence():
    with pytest.raises(mutations.MutationHarnessError, match="occurs 0 times"):
        mutations.apply_mutation("a\nb\nc\n", "not present", "z", mutant_id="m")

    with pytest.raises(mutations.MutationHarnessError, match="occurs 2 times"):
        mutations.apply_mutation("dup\ndup\n", "dup", "z", mutant_id="m")


def test_apply_mutation_replaces_the_single_occurrence():
    result = mutations.apply_mutation("a\nb\nc\n", "b", "B", mutant_id="m")
    assert result == "a\nB\nc\n"


def test_running_one_real_mutant_end_to_end_is_killed():
    """A genuine, slow-ish integration check that the isolated tempdir
    mechanism actually works, restricted to the cheapest registered
    mutant so it stays fast enough for the normal test suite. The full
    seven-mutant run belongs to `--verify`, not this module."""
    config = mutations.load_config()
    report = mutations.run_all(
        config, only_mutant_ids=frozenset({"ignored_side_effect"})
    )
    assert report["all_mutants_killed"] is True
    assert len(report["mutants"]) == 1
    assert report["mutants"][0]["killed"] is True
    assert report["mutants"][0]["harness_error"] is None
