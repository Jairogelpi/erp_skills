import hashlib
from pathlib import Path

import pytest

from erp_agent_os.freeze_v2 import RunConfig, build_manifest, verify_manifest


def config(**changes):
    data = {
        "provider": "provider",
        "model": "selector",
        "model_version": "2026-08-01",
        "temperature": 0.0,
        "token_limit": 1000,
        "timeout_seconds": 30,
        "retry_budget": 1,
        "step_budget": 4,
        "role": "erp_user",
        "argument_prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
        "initial_state_factory_sha256": hashlib.sha256(b"state").hexdigest(),
        "seed": 20260812,
    }
    data.update(changes)
    return RunConfig(**data)


def test_manifest_hashes_every_declared_input_and_config(tmp_path: Path) -> None:
    (tmp_path / "dataset.jsonl").write_text("case\n", encoding="utf-8")
    (tmp_path / "policy.py").write_text("DENY = True\n", encoding="utf-8")
    manifest = build_manifest(
        tmp_path,
        run_config=config(),
        required_files=["dataset.jsonl", "policy.py"],
        git_commit="a" * 40,
    )
    assert set(manifest.files) == {"dataset.jsonl", "policy.py"}
    assert manifest.run_config_hash == config().sha256()
    verify_manifest(tmp_path, manifest, run_config=config(), require_clean_tag=False)


def test_any_input_or_configuration_change_breaks_freeze(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text("before", encoding="utf-8")
    manifest = build_manifest(
        tmp_path,
        run_config=config(),
        required_files=["dataset.jsonl"],
        git_commit="b" * 40,
    )
    path.write_text("after", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        verify_manifest(
            tmp_path, manifest, run_config=config(), require_clean_tag=False
        )
    path.write_text("before", encoding="utf-8")
    with pytest.raises(ValueError, match="configuration"):
        verify_manifest(
            tmp_path,
            manifest,
            run_config=config(temperature=0.2),
            require_clean_tag=False,
        )
