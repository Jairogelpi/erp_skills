"""Tests for scripts/run_experiment.py's own reporting logic.

scripts/ is not a package; loaded by path via importlib, the standard way
to unit-test a script file.
"""

import importlib.util
import pathlib

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "scripts" / "run_experiment.py"
)
_spec = importlib.util.spec_from_file_location("run_experiment_script", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
run_experiment_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_experiment_script)


def test_caveat_matches_is_confirmatory_true():
    # Regression: a prior version always published the "NOT confirmatory"
    # text, so a real-LLM run reported is_confirmatory_run=true next to a
    # caveat claiming the opposite -- found by reading the first real run.
    caveat = run_experiment_script._manifest_caveat(
        is_confirmatory=True, selector="GroqClient"
    )
    assert "IS the section 19 confirmatory protocol" in caveat
    assert "NOT the CLAUDE.md section 19" not in caveat


def test_caveat_matches_is_confirmatory_false():
    caveat = run_experiment_script._manifest_caveat(
        is_confirmatory=False, selector="DeterministicStubClient"
    )
    assert "NOT the CLAUDE.md section 19" in caveat
    assert "IS the section 19 confirmatory protocol" not in caveat


def test_caveat_names_the_actual_selector_used():
    # Regression: a prior version hardcoded "Groq free tier" in the
    # confirmatory branch regardless of which real provider was used --
    # a run made with OpenRouterClient published a caveat naming Groq.
    caveat = run_experiment_script._manifest_caveat(
        is_confirmatory=True, selector="OpenRouterClient"
    )
    assert "OpenRouterClient" in caveat
    assert "Groq" not in caveat
