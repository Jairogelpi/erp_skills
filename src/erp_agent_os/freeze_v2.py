"""Prospective freeze manifest for ERP-Skills-Bench v2."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_ID = "erp-skills-bench-v2"
EXPECTED_OBSERVATIONS = 1080
FREEZE_TAG = "v2-protocol-freeze"


class RunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: str
    model: str
    model_version: str
    temperature: float
    token_limit: int = Field(gt=0)
    timeout_seconds: float = Field(gt=0)
    retry_budget: int = Field(ge=0)
    step_budget: int = Field(gt=0)
    role: str
    argument_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_state_factory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int

    def sha256(self) -> str:
        payload = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class FreezeManifestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str = "1.0"
    status: str = "verified"
    protocol_id: str = PROTOCOL_ID
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_observations: int = EXPECTED_OBSERVATIONS
    git_commit: str
    git_tag: str = FREEZE_TAG
    files: dict[str, str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_hash(files: dict[str, str], config_hash: str) -> str:
    payload = json.dumps(
        {"files": files, "run_config_hash": config_hash},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def build_manifest(
    root: Path, *, run_config: RunConfig, required_files: list[str], git_commit: str
) -> FreezeManifestV2:
    files: dict[str, str] = {}
    for relative in required_files:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"missing freeze input: {relative}")
        files[relative] = sha256_file(path)
    config_hash = run_config.sha256()
    return FreezeManifestV2(
        manifest_hash=manifest_hash(files, config_hash),
        run_config_hash=config_hash,
        git_commit=git_commit,
        files=files,
    )


def verify_manifest(
    root: Path,
    manifest: FreezeManifestV2,
    *,
    run_config: RunConfig,
    require_clean_tag: bool = True,
) -> None:
    actual = {relative: sha256_file(root / relative) for relative in manifest.files}
    if actual != manifest.files:
        raise ValueError("freeze input hash mismatch")
    if run_config.sha256() != manifest.run_config_hash:
        raise ValueError("run configuration hash mismatch")
    if manifest_hash(actual, manifest.run_config_hash) != manifest.manifest_hash:
        raise ValueError("manifest hash mismatch")
    if require_clean_tag:
        if git_output(root, "status", "--porcelain"):
            raise ValueError("v2 freeze verification requires a clean worktree")
        head = git_output(root, "rev-parse", "HEAD")
        tag = git_output(root, "rev-list", "-n", "1", FREEZE_TAG)
        if head != manifest.git_commit or tag != head:
            raise ValueError("v2 freeze tag/commit mismatch")


def load_run_config(path: Path) -> RunConfig:
    return RunConfig.model_validate_json(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, value: BaseModel | dict[str, Any]) -> None:
    payload = value.model_dump() if isinstance(value, BaseModel) else value
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
