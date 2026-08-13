"""TDD for erp_agent_os.protocol_v2_1 (v2.1 plan, Task 2).

docs/tfm-closure-no-human-v2.1.md sections 8, 10, 12: every acceptance
threshold and analysis rule must be an explicit, versioned number --
never an implicit constant buried in analysis code that could be tuned
after seeing the holdout.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from erp_agent_os.protocol_v2_1 import ProtocolV21, ProtocolV21Error, load_protocol

PROTOCOL_PATH = Path("config/protocol_v2_1.json")


def test_protocol_has_no_implicit_acceptance_criteria():
    protocol = load_protocol(PROTOCOL_PATH)
    assert protocol.h1.non_inferiority_margin == -0.05
    assert protocol.h1.superiority_null_margin == 0.0
    assert protocol.h1.minimum_relevant_difference == 0.05
    assert protocol.h4.unauthorized_mutation_upper_bound == 0.05
    assert protocol.h5.selective_accuracy_min == 0.90
    assert protocol.h5.false_reuse_max == 0.10


def test_protocol_declares_the_frozen_h8_cost_grid():
    protocol = load_protocol(PROTOCOL_PATH)
    assert protocol.h8.inference_price_eur_per_million_tokens == [0.10, 1.0, 10.0]
    assert protocol.h8.review_cost_eur_per_hour == [20.0, 40.0, 80.0]
    assert protocol.h8.review_minutes == [1.0, 3.0, 10.0]
    assert protocol.h8.error_cost_eur == [10.0, 100.0, 1000.0]


def test_protocol_declares_power_and_holm_settings():
    protocol = load_protocol(PROTOCOL_PATH)
    assert protocol.power.alpha_family == 0.05
    assert protocol.power.power_target == 0.80
    assert protocol.power.min_monte_carlo_replicates >= 100_000
    assert "h1b" in protocol.holm_families
    assert "h4" in protocol.holm_families


def _base_payload() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_protocol_rejects_h2_with_caching():
    payload = _base_payload()
    payload["h2"]["cache_policy"] = "shared_cache"
    with pytest.raises(ValidationError):
        ProtocolV21(**payload)


def test_protocol_rejects_h3b_with_fewer_than_three_calls():
    payload = _base_payload()
    payload["h3"]["h3b_min_calls"] = 2
    with pytest.raises(ValidationError):
        ProtocolV21(**payload)


def test_protocol_rejects_missing_holm_families():
    payload = _base_payload()
    payload["holm_families"] = {"h1b": ["c_vs_a", "c_vs_b"]}  # h4 missing
    with pytest.raises(ValidationError):
        ProtocolV21(**payload)


def test_protocol_rejects_human_annotation_required_true():
    payload = _base_payload()
    payload["human_annotation_required"] = True
    with pytest.raises(ValidationError):
        ProtocolV21(**payload)


def test_load_protocol_raises_a_named_error_for_a_missing_file(tmp_path):
    with pytest.raises(ProtocolV21Error):
        load_protocol(tmp_path / "does-not-exist.json")


def test_config_forbids_unknown_top_level_fields():
    payload = _base_payload()
    payload["not_a_real_field"] = True
    with pytest.raises(ValidationError):
        ProtocolV21(**payload)
