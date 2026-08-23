import hashlib
import json
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.observed_states import (
    build_observed_state_rows,
    write_observed_state_archive,
)


def test_observed_states_cover_all_cases_without_pretending_to_be_oracle():
    rows = build_observed_state_rows(generate_cases())

    assert len(rows) == 480
    assert len({row["request_id"] for row in rows}) == 480
    assert all(row["evidence_role"] == "system_observation_not_oracle" for row in rows)
    assert all(row["oracle_status"] == "pending_independent_review" for row in rows)
    assert "pending_execution_wiring" not in json.dumps(rows)


def test_observed_state_export_is_deterministic_and_does_not_mutate_benchmark(tmp_path):
    benchmark = Path(__file__).resolve().parents[1] / "data" / "bench_v1.jsonl"
    before = hashlib.sha256(benchmark.read_bytes()).hexdigest()
    cases = generate_cases()[:12]

    first = write_observed_state_archive(cases, tmp_path)
    second = write_observed_state_archive(cases, tmp_path)

    assert first == second
    assert first.exists()
    assert hashlib.sha256(benchmark.read_bytes()).hexdigest() == before
