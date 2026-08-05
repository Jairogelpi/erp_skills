"""Render or remove checkout-local Codebase Memory MCP configuration."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PLACEHOLDER = "__REPOSITORY_ROOT__"
PIN = re.compile(r"[0-9a-f]{40}\Z")


class BootstrapError(Exception):
    """An unsafe local MCP setup was refused."""


def git_toplevel(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise BootstrapError(
            "Git is not initialized for this checkout; initialize Git before "
            "enabling Codebase Memory MCP."
        )
    return Path(result.stdout.strip()).resolve()


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    return True


def render_template(template: Path, root: Path) -> str:
    try:
        data = json.loads(template.read_text(encoding="utf-8"))
        server = data["mcpServers"]["codebase-memory"]
        provenance = data["x-provenance"]
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as error:
        raise BootstrapError("invalid Codebase Memory MCP template") from error
    if not isinstance(provenance.get("upstream_commit"), str) or not PIN.fullmatch(
        provenance["upstream_commit"]
    ):
        raise BootstrapError("template requires an immutable upstream commit pin")

    def substitute(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(PLACEHOLDER, str(root))
        if isinstance(value, dict):
            return {key: substitute(item) for key, item in value.items()}
        return value

    rendered = substitute(data)
    server = rendered["mcpServers"]["codebase-memory"]
    env = server.get("env", {})
    paths = [Path(server.get("cwd", "")), Path(env.get("CBM_ALLOWED_ROOT", ""))]
    if any(path.resolve() != root for path in paths):
        raise BootstrapError("template repository root does not match this checkout")
    cache = Path(env.get("CBM_CACHE_DIR", ""))
    command = Path(server.get("command", ""))
    local = root / ".mcp" / "local"
    if not all(inside(path, local) for path in (cache, command)):
        raise BootstrapError("template attempts an external local-state write")
    if "token" in json.dumps(rendered).lower():
        raise BootstrapError("template must be token-free")
    return json.dumps(rendered, indent=2) + "\n"


def bootstrap(cwd: Path) -> Path:
    root = git_toplevel(cwd)
    if cwd.resolve() != root:
        raise BootstrapError("run bootstrap from the repository root")
    template = root / ".mcp" / "codebase-memory.template.json"
    target = root / ".mcp" / "local" / "codebase-memory.json"
    if not inside(template, root) or not inside(target, root):
        raise BootstrapError("unsafe repository path")
    content = render_template(template, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(target)
    return target


def remove(cwd: Path) -> None:
    root = git_toplevel(cwd)
    if cwd.resolve() != root:
        raise BootstrapError("run removal from the repository root")
    local = root / ".mcp" / "local"
    if not inside(local, root):
        raise BootstrapError("unsafe repository path")
    if local.exists():
        shutil.rmtree(local)


def main(arguments: list[str]) -> int:
    try:
        if arguments == ["--remove"]:
            remove(Path.cwd())
            print("Removed checkout-local Codebase Memory state.")
        elif not arguments:
            print(bootstrap(Path.cwd()))
        else:
            raise BootstrapError("usage: bootstrap-codebase-memory.py [--remove]")
    except BootstrapError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
