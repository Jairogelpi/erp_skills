#!/usr/bin/env python
"""Cross-platform evaluator launcher for ERP Agent OS.

This is the recommended path for a tutor or reviewer who wants to verify the
repository and open the comparative web demo without relying on GNU make or
shell-specific background-process syntax.

No LLM API key and no Odoo credentials are required for the comparative demo.
It runs against the reproducible FakeERP backend and reads the frozen v2.1.2
confirmatory evidence committed to the repository.

Examples:

    uv run python scripts/professor_demo.py --check
    uv run python scripts/professor_demo.py --full-check
    uv run python scripts/professor_demo.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_DIR = ROOT / "demo-ui"
API_URL = "http://127.0.0.1:8000/demo/evidence"
UI_URL = "http://127.0.0.1:5173"
PROXY_EVIDENCE_URL = f"{UI_URL}/demo/evidence"


class PrerequisiteError(RuntimeError):
    """Raised when the local machine cannot run the reviewer workflow."""


def _run(command: list[str], *, cwd: Path = ROOT) -> None:
    printable = " ".join(command)
    print(f"\n> {printable}")
    subprocess.run(command, cwd=cwd, check=True)


def _required_command(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise PrerequisiteError(f"Required command not found on PATH: {name}")
    return path


def _node_major(node: str) -> int:
    completed = subprocess.run(
        [node, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    version = completed.stdout.strip().lstrip("v")
    try:
        return int(version.split(".", 1)[0])
    except ValueError as exc:
        raise PrerequisiteError(
            f"Could not parse Node.js version: {version!r}"
        ) from exc


def _check_prerequisites() -> str:
    if sys.version_info[:2] != (3, 12):
        raise PrerequisiteError(
            "ERP Agent OS is frozen for Python 3.12. "
            f"Current interpreter: {sys.version.split()[0]}. "
            "Run `uv python install 3.12` and then use `uv run ...`."
        )

    node = _required_command("node")
    npm = _required_command("npm")
    major = _node_major(node)
    if major < 18:
        raise PrerequisiteError(
            f"Node.js 18+ is required for the demo UI; found Node {major}. "
            "Node 20 LTS is recommended."
        )

    if not (UI_DIR / "package-lock.json").is_file():
        raise PrerequisiteError("demo-ui/package-lock.json is missing")

    print(f"Python: {sys.version.split()[0]} [OK]")
    print(f"Node.js: {major}.x [OK]")
    print("npm: found [OK]")
    return npm


def _run_demo_preflight() -> None:
    _run([sys.executable, str(ROOT / "scripts" / "demo_preflight.py")])


def _install_and_build_frontend(npm: str) -> None:
    # npm ci uses package-lock.json exactly and removes any stale node_modules
    # state, which is preferable for a clean evaluator machine.
    _run([npm, "ci"], cwd=UI_DIR)
    _run([npm, "run", "typecheck"], cwd=UI_DIR)
    _run([npm, "run", "build"], cwd=UI_DIR)


def _run_full_scientific_check() -> None:
    _run([sys.executable, "-m", "pytest"])
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_tfm_closure_v2_1.py"),
            "--final",
            "--receipt-log",
            "data/protocol_v2_1/runs_v2/receipts_2.jsonl",
            "--code-manifest-path",
            "data/protocol_v2_1/code_freeze_manifest.json",
            "--report-path",
            "data/protocol_v2_1/confirmatory_report_v2_1_2.json",
        ]
    )


def _wait_until_ready(url: str, *, timeout_seconds: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 400:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.25)
    return False


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _launch(npm: str, *, open_browser: bool, smoke_only: bool = False) -> int:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path if not existing else os.pathsep.join([src_path, existing])
    )

    print("\nStarting comparative demo...")
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "erp_agent_os.demo_api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        env=env,
    )
    ui = subprocess.Popen(
        [
            npm,
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--strictPort",
        ],
        cwd=UI_DIR,
        env=env,
    )

    try:
        if not _wait_until_ready(API_URL):
            raise RuntimeError(
                "Demo API did not become ready on 127.0.0.1:8000. "
                "Check whether the port is already in use."
            )
        if not _wait_until_ready(UI_URL):
            raise RuntimeError(
                "Demo UI did not become ready on 127.0.0.1:5173. "
                "Check whether the port is already in use."
            )
        if not _wait_until_ready(PROXY_EVIDENCE_URL):
            raise RuntimeError(
                "The Vite UI started, but its /demo proxy could not reach the API."
            )

        if smoke_only:
            print("  [PASS] Demo API HTTP readiness")
            print("  [PASS] Demo UI HTTP readiness")
            print("  [PASS] UI -> API proxy")
            return 0

        print("\nDEMO READY")
        print(f"Open: {UI_URL}")
        print("No API key or Odoo credentials are being used.")
        print("Press Ctrl+C in this terminal to stop both processes.\n")
        if open_browser:
            webbrowser.open(UI_URL)

        while True:
            api_code = api.poll()
            ui_code = ui.poll()
            if api_code is not None:
                raise RuntimeError(f"Demo API exited unexpectedly with code {api_code}")
            if ui_code is not None:
                raise RuntimeError(f"Demo UI exited unexpectedly with code {ui_code}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping demo...")
        return 0
    finally:
        _terminate(ui)
        _terminate(api)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="verify prerequisites, frozen evidence, demo behavior and frontend build",
    )
    group.add_argument(
        "--full-check",
        action="store_true",
        help="run --check plus the full pytest suite and v2.1.2 closure verifier",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="start the demo without opening the default browser",
    )
    args = parser.parse_args()

    try:
        npm = _check_prerequisites()
        _run_demo_preflight()
        _install_and_build_frontend(npm)
        if args.check or args.full_check:
            if _launch(npm, open_browser=False, smoke_only=True) != 0:
                return 1
        if args.full_check:
            _run_full_scientific_check()
    except (PrerequisiteError, subprocess.CalledProcessError) as exc:
        print(f"\nREVIEWER CHECK FAILED: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"\nREVIEWER CHECK FAILED: {exc}", file=sys.stderr)
        return 1

    if args.check or args.full_check:
        print("\nREVIEWER CHECK PASSED")
        print("The comparative demo can be launched with:")
        print("  uv run python scripts/professor_demo.py")
        return 0

    try:
        return _launch(npm, open_browser=not args.no_browser)
    except RuntimeError as exc:
        print(f"\nDEMO FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
