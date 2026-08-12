import hashlib
from pathlib import Path

import pytest

from erp_agent_os.bench_v2 import RecordedAuthor, generate_v2
from erp_agent_os.experiment_v2 import (
    TRACE_COMPONENTS,
    InfrastructureRunError,
    V2Observation,
    analyze_observations,
    generate_checkpoint_key,
    load_encrypted_checkpoint,
    read_encrypted_checkpoint,
    run_protocol,
    validate_observations,
    write_encrypted_checkpoint,
)
from erp_agent_os.freeze_v2 import RunConfig


def config():
    return RunConfig(
        provider="provider",
        model="selector",
        model_version="2026-08-01",
        temperature=0,
        token_limit=1000,
        timeout_seconds=30,
        retry_budget=1,
        step_budget=4,
        role="erp_user",
        argument_prompt_sha256=hashlib.sha256(b"prompt").hexdigest(),
        initial_state_factory_sha256=hashlib.sha256(b"state").hexdigest(),
        seed=20260812,
    )


def cases():
    values = [f"Petición prospectiva independiente {i}" for i in range(120)]
    generated, _ = generate_v2(
        author=RecordedAuthor(provider="author", model="author-v1", texts=values),
        selector_provider="provider",
        selector_model="selector",
    )
    return generated


def observations():
    cfg = config()
    rows = []
    for case_index, case in enumerate(cases()):
        for system in ("A", "B", "C"):
            for repetition in (1, 2, 3):
                success = system == "C" or (system == "B" and case_index % 2 == 0)
                rows.append(
                    V2Observation(
                        request_id=case.request_id,
                        system=system,
                        repetition=repetition,
                        run_config_hash=cfg.sha256(),
                        initial_state_hash=hashlib.sha256(
                            f"initial-{case.request_id}".encode()
                        ).hexdigest(),
                        final_state_hash=hashlib.sha256(
                            f"final-{case.request_id}-{success}".encode()
                        ).hexdigest(),
                        model_call_ids=(
                            f"call-{case.request_id}-{system}-{repetition}",
                        ),
                        model_calls=1,
                        retries=0,
                        input_tokens=10,
                        output_tokens=5,
                        latency_ms=20,
                        stsr=success,
                        dangerous=case.dangerous,
                        should_allow=case.expected_decision == "ALLOW",
                        allowed=success and case.expected_decision == "ALLOW",
                        trace_score=1.0 if system == "C" else 0.4,
                        trace_components=(
                            {name: True for name in TRACE_COMPONENTS}
                            if system == "C"
                            else {
                                name: name
                                in {
                                    "request_identity",
                                    "interpretation_arguments",
                                    "result_effects",
                                }
                                for name in TRACE_COMPONENTS
                            }
                        ),
                        retrieval_eligible=True,
                        retrieval_top1=success,
                        retrieval_top3=True,
                        retrieval_reused=system == "C",
                        retrieval_correct=success,
                    )
                )
    return rows


def test_checkpoint_is_encrypted_and_requires_separate_key(tmp_path: Path) -> None:
    path = tmp_path / "private.bin"
    key = generate_checkpoint_key()
    write_encrypted_checkpoint(path, observations()[:2], key=key)
    assert b"request_id" not in path.read_bytes()
    assert len(read_encrypted_checkpoint(path, key=key)) == 2
    with pytest.raises(ValueError, match="key"):
        read_encrypted_checkpoint(path, key=generate_checkpoint_key())


def test_runner_records_sanitized_infrastructure_failure(tmp_path: Path) -> None:
    checkpoint = tmp_path / "failed.bin"
    key = generate_checkpoint_key()

    def fail(*_args):
        raise ConnectionError("SECRET provider response")

    with pytest.raises(InfrastructureRunError):
        run_protocol(
            cases(),
            config=config(),
            execute=fail,
            checkpoint_path=checkpoint,
            checkpoint_key=key,
        )
    envelope = load_encrypted_checkpoint(checkpoint, key=key)
    assert envelope.status == "infrastructure_failed"
    assert envelope.failure is not None
    assert envelope.failure.exception_type == "ConnectionError"
    assert "SECRET" not in checkpoint.read_bytes().decode(errors="ignore")


def test_acceptance_requires_1080_unique_independent_observations() -> None:
    rows = observations()
    validate_observations(
        rows,
        case_ids={case.request_id for case in cases()},
        config_hash=config().sha256(),
    )
    with pytest.raises(ValueError, match="1,080"):
        validate_observations(
            rows[:-1],
            case_ids={case.request_id for case in cases()},
            config_hash=config().sha256(),
        )
    duplicate_call = rows[1].model_copy(
        update={"model_call_ids": rows[0].model_call_ids}
    )
    tampered = [rows[0], duplicate_call, *rows[2:]]
    with pytest.raises(ValueError, match="cached"):
        validate_observations(
            tampered,
            case_ids={case.request_id for case in cases()},
            config_hash=config().sha256(),
        )


def test_acceptance_requires_restored_state_and_exact_call_evidence() -> None:
    rows = observations()
    rows[1] = rows[1].model_copy(
        update={"initial_state_hash": hashlib.sha256(b"different").hexdigest()}
    )
    with pytest.raises(ValueError, match="restored initial state"):
        validate_observations(
            rows,
            case_ids={case.request_id for case in cases()},
            config_hash=config().sha256(),
        )

    rows = observations()
    rows[0] = rows[0].model_copy(update={"model_calls": 2})
    with pytest.raises(ValueError, match="call evidence"):
        validate_observations(
            rows,
            case_ids={case.request_id for case in cases()},
            config_hash=config().sha256(),
        )


def test_primary_and_all_secondary_endpoints_are_always_present() -> None:
    result = analyze_observations(
        observations(), case_ids={case.request_id for case in cases()}, config=config()
    )
    assert result.primary.contrast == "C-B"
    assert result.primary.paired_difference == 0.5
    assert result.primary.supported is True
    for summary in result.systems.values():
        assert summary.false_allow.n >= 0
        assert summary.false_block.n >= 0
        assert summary.mean_input_tokens.value == 10
        assert summary.mean_output_tokens.value == 5
        assert summary.mean_total_tokens.value == 15
        assert set(summary.trace_component_rates) == set(TRACE_COMPONENTS)
        assert summary.retrieval_coverage.status in {"estimated", "not_estimable"}
    assert set(result.secondary.token_differences) == {"C-A", "C-B"}
    assert result.secondary.token_differences["C-B"].n == 120


def test_run_config_hash_mismatch_is_rejected() -> None:
    rows = observations()
    rows[0] = rows[0].model_copy(update={"run_config_hash": "0" * 64})
    with pytest.raises(ValueError, match="configuration"):
        validate_observations(
            rows,
            case_ids={case.request_id for case in cases()},
            config_hash=config().sha256(),
        )
