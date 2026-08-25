"""The demo's evidence layer must report the frozen campaign, not restate it.

The failure this file exists to catch is a figure that looks right on
screen but is not the one in `confirmatory_report_v2_1_2.json` -- a
hardcoded constant, a stale copy, or a verdict re-derived here from a
threshold instead of read from the report.
"""

from __future__ import annotations

import json
import math

import pytest

from erp_agent_os import demo_results


def _report() -> dict:
    return json.loads(demo_results.REPORT_PATH.read_text(encoding="utf-8"))


def test_every_card_estimate_equals_the_report_value():
    report = _report()
    for card in demo_results.load_evidence().cards:
        recorded = report["hypotheses"][card.key]["result"]["estimate"]
        if card.estimate is None:
            assert not math.isfinite(recorded)
        else:
            assert card.estimate == recorded, card.key


def test_supported_flag_comes_from_the_reports_evidence_state():
    """Not from re-testing the estimate against a threshold here.

    The accept/reject decision belongs to the frozen analysis code; a
    second, independent decision rule in the presentation layer could
    disagree with the published one and nobody would notice.
    """
    report = _report()
    for card in demo_results.load_evidence().cards:
        state = report["hypotheses"][card.key]["claim"]["evidence_state"]
        assert card.supported is (state == "confirmatory_supported"), card.key


def test_the_four_not_supported_hypotheses_are_reported_as_such():
    """H1b, H4 and H5 are negative results and must present as negative.

    Softening them in the UI would be the single most tempting and most
    dishonest change available to this demo.
    """
    by_key = {c.key: c for c in demo_results.load_evidence().cards}
    assert by_key["h1b"].supported is False
    assert by_key["h4_unauthorized_mutation"].supported is False
    assert by_key["h5"].supported is False
    assert by_key["h1a"].supported is True
    assert by_key["h7"].supported is True


def test_observation_count_is_read_from_the_archive_manifest():
    archive = demo_results._archive_manifest()
    bundle = demo_results.load_evidence()
    assert bundle.observation_count == archive["row_count"]
    # A line count would be off by one: the first line is the manifest.
    with archive["path"].open(encoding="utf-8") as handle:
        assert json.loads(handle.readline())["type"] == "manifest"


def test_json_safe_removes_non_finite_floats():
    """NaN and -inf are valid Python and invalid JSON.

    The report genuinely contains both, so leaving them in the payload
    would make `JSON.parse` reject the whole response in the browser.
    """
    payload = {
        "p": float("nan"),
        "ci": [float("-inf"), float("inf"), 0.5],
        "nested": {"x": float("nan")},
    }
    cleaned = demo_results.json_safe(payload)
    assert cleaned == {"p": None, "ci": [None, None, 0.5], "nested": {"x": None}}
    json.dumps(cleaned, allow_nan=False)  # raises if anything survived


def test_a_non_finite_value_actually_reaches_json_safe_in_the_real_report():
    """Guards the guard: if the report ever stopped containing NaN/-inf,
    the sanitiser would be dead code and this file would be testing
    nothing about the real artifact."""
    raw = json.dumps(_report())
    assert "NaN" in raw or "Infinity" in raw


def test_missing_report_raises_instead_of_serving_placeholders(monkeypatch, tmp_path):
    monkeypatch.setattr(demo_results, "REPORT_PATH", tmp_path / "absent.json")
    with pytest.raises(demo_results.EvidenceUnavailableError):
        demo_results.load_evidence()


def test_capability_matrix_rows_cite_a_hypothesis_and_carry_no_score():
    bundle = demo_results.load_evidence()
    keys = {card.key for card in bundle.cards}
    assert bundle.capability_matrix
    for row in bundle.capability_matrix:
        assert row.source_hypothesis in keys, row.dimension
        # No row may carry a numeric score: §36's construct-validity
        # warning applies directly to collapsing eight hypotheses with
        # different units into one number.
        for value in (row.system_a, row.system_b, row.system_c):
            assert not value.replace(".", "").isdigit(), row.dimension
