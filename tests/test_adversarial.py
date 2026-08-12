import importlib.util
import json
from pathlib import Path

from pydantic import TypeAdapter

from erp_agent_os.adversarial import (
    AttackCategory,
    RecordedThreatCase,
    ThreatCase,
    ThreatObservation,
    evaluate_case,
    evaluate_suite,
)


def observation(**changes):
    data = {
        "decision": "DENY",
        "before": {"crm.lead": {}},
        "after": {"crm.lead": {}},
        "changed_records": 0,
        "business_mutations": 0,
    }
    data.update(changes)
    return ThreatObservation(**data)


def case(category, **changes):
    data = {"case_id": f"case-{category}", "category": category, "description": "x"}
    data.update(changes)
    return ThreatCase(**data)


def test_each_attack_category_has_a_state_based_oracle() -> None:
    for category in AttackCategory:
        result = evaluate_case(case(category), observation())
        assert result.category is category
        assert result.status in {"passed", "finding", "unsupported_policy"}


def test_field_injection_is_reported_as_finding() -> None:
    result = evaluate_case(
        case(
            AttackCategory.FIELD_INJECTION,
            expected_model="crm.lead",
            allowed_fields={"name"},
        ),
        observation(
            decision="ALLOW",
            before={"crm.lead": {}},
            after={"crm.lead": {"1": {"name": "A", "is_admin": True}}},
            changed_records=1,
            business_mutations=1,
        ),
    )
    assert result.status == "finding"
    assert "is_admin" in result.findings[0]


def test_role_spoof_and_approval_bypass_require_no_state_change() -> None:
    changed = observation(
        decision="ALLOW",
        before={"crm.lead": {}},
        after={"crm.lead": {"1": {"name": "A"}}},
        changed_records=1,
        business_mutations=1,
    )
    spoof = evaluate_case(
        case(
            AttackCategory.ROLE_SPOOFING,
            authenticated_role="outsider",
            claimed_role="erp_user",
        ),
        changed,
    )
    bypass = evaluate_case(case(AttackCategory.APPROVAL_BYPASS), changed)
    assert spoof.passed is False
    assert bypass.passed is False


def test_replay_oracle_requires_one_mutation_replay_and_evidence() -> None:
    result = evaluate_case(
        case(AttackCategory.REPLAY_ABUSE),
        observation(
            decision="ALLOW",
            changed_records=1,
            business_mutations=1,
            second_verification_status="replayed",
            replay_evidence_preserved=True,
        ),
    )
    assert result.passed is True


def test_unsupported_misuse_is_not_counted_as_pass_or_failure() -> None:
    result = evaluate_case(
        case(AttackCategory.LEGITIMATE_MISUSE, policy_supported=False), observation()
    )
    assert result.status == "unsupported_policy"
    assert result.passed is None


def test_committed_suite_has_attack_and_positive_control_per_category() -> None:
    raw = json.loads(
        Path("data/catalog_aware_stress_cases.json").read_text(encoding="utf-8")
    )
    cases = TypeAdapter(list[RecordedThreatCase]).validate_python(raw)
    for category in AttackCategory:
        bucket = [item for item in cases if item.case.category is category]
        assert any(not item.case.positive_control for item in bucket)
        assert any(item.case.positive_control for item in bucket)
    report = evaluate_suite(cases)
    assert report.findings >= 1
    assert report.unsupported_policy == 1


def test_script_writes_registered_exploratory_result(tmp_path, monkeypatch) -> None:
    path = Path("scripts/catalog_aware_stress_test.py")
    spec = importlib.util.spec_from_file_location("catalog_stress_script", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "catalog_aware_stress_results.json"
    monkeypatch.setattr(module, "DEFAULT_OUTPUT", output)
    assert (
        module.main(
            ["--cases", "data/catalog_aware_stress_cases.json", "--output", str(output)]
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_status"] == "exploratory"
    assert payload["findings"] >= 1
