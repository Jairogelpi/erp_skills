"""TDD for erp_agent_os.oracle_concordance_v2_1 (shared by Task 3's own
tests and Task 10's freeze gate)."""

from __future__ import annotations

import pytest

from erp_agent_os.oracle_concordance_v2_1 import (
    ConcordanceMismatchError,
    find_concordance_mismatches,
    validate_full_corpus_concordance,
)
from erp_agent_os.scenarios_v2_1 import generate_scenarios
from erp_agent_os.security_scenarios_v2_1 import generate_security_population


def test_validate_full_corpus_concordance_accepts_the_real_generated_corpus():
    main = generate_scenarios()
    dangerous, safe = generate_security_population()
    validate_full_corpus_concordance((*main, *dangerous, *safe))  # does not raise


def test_find_concordance_mismatches_detects_a_planted_disagreement():
    """The mismatch check must be able to fail -- planting a scenario
    whose declared decision contradicts the independent oracle proves
    it, rather than assuming an always-empty mismatch list means the
    check works."""
    main = generate_scenarios()
    tampered = main[0].__class__(
        **{**main[0].__dict__, "expected_decision": "DENY_WRONG_ON_PURPOSE"}
    )
    mismatches = find_concordance_mismatches([tampered])
    assert mismatches
    assert mismatches[0][0] == tampered.scenario_id
    assert mismatches[0][1] == "decision"


def test_validate_full_corpus_concordance_raises_on_a_planted_mismatch():
    main = generate_scenarios()
    tampered = main[0].__class__(
        **{**main[0].__dict__, "expected_decision": "DENY_WRONG_ON_PURPOSE"}
    )
    with pytest.raises(ConcordanceMismatchError):
        validate_full_corpus_concordance([tampered])
