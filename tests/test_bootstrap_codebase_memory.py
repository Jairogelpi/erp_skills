"""Focused checks for checkout-local Codebase Memory configuration."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "bootstrap-codebase-memory.py"
TEMPLATE = Path(__file__).parents[1] / ".mcp" / "codebase-memory.template.json"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("bootstrap_codebase_memory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def template(root: Path) -> Path:
    path = root / ".mcp" / "codebase-memory.template.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(TEMPLATE.read_text(), encoding="utf-8")
    return path


def test_template_requires_immutable_pin_and_checkout_bounds(tmp_path):
    bootstrap = load_bootstrap()
    path = template(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["x-provenance"]["upstream_commit"] = "main"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(bootstrap.BootstrapError, match="immutable"):
        bootstrap.render_template(path, tmp_path)

    template(tmp_path)
    server = json.loads(bootstrap.render_template(path, tmp_path))["mcpServers"][
        "codebase-memory"
    ]
    assert server["cwd"] == server["env"]["CBM_ALLOWED_ROOT"] == str(tmp_path)
    assert (
        Path(server["env"]["CBM_CACHE_DIR"])
        .resolve()
        .is_relative_to((tmp_path / ".mcp" / "local").resolve())
    )
    assert "token" not in json.dumps(server).lower()


def test_bootstrap_rejects_root_mismatch_and_missing_git(tmp_path, monkeypatch):
    bootstrap = load_bootstrap()
    template(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    monkeypatch.setattr(bootstrap, "git_toplevel", lambda _: other_root)
    with pytest.raises(bootstrap.BootstrapError, match="repository root"):
        bootstrap.bootstrap(tmp_path)

    monkeypatch.undo()
    with pytest.raises(bootstrap.BootstrapError, match="Git is not initialized"):
        bootstrap.bootstrap(tmp_path)
