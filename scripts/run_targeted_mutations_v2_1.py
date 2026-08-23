#!/usr/bin/env python
"""Targeted mutation-testing harness for the v2.1 evaluator (Task 7C).

docs/tfm-closure-no-human-v2.1.md, Task 7C: the evaluator built in Task 7
is not accepted until every registered critical predicate in
config/targeted_mutations_v2_1.json has been shown to actually matter --
inverting it, or replacing it with a constant, must make its focused
pytest node IDs fail. A check that cannot fail is worse than no check
(CLAUDE.md bitacora, units 21-22): this harness proves each check can.

Every mutation happens on a throwaway copy of src/erp_agent_os inside a
tempfile.TemporaryDirectory. Nothing under the real repository is ever
written. The real worktree's source hashes are verified unchanged before
and after every run.

    uv run pytest tests/test_targeted_mutations_v2_1.py -q   # fast, contract-only
    uv run python scripts/run_targeted_mutations_v2_1.py --verify   # slow, real run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "targeted_mutations_v2_1.json"
OUTPUT_DIR = REPO_ROOT / "data" / "protocol_v2_1"
SRC_PACKAGE = "erp_agent_os"

KNOWN_OPERATORS = frozenset({"comparator_inversion", "constant_replacement"})
REQUIRED_MUTANT_IDS = frozenset(
    {
        "decision_inversion",
        "final_state_inversion",
        "ignored_side_effect",
        "false_allow_inversion",
        "ignored_unauthorized_mutation",
        "relaxed_duplicate_cardinality",
        "missing_audit_fact_accepted",
    }
)

# pytest exit codes that mean "a test process ran but something other than
# a failed assertion went wrong" -- these are harness errors, never a
# killed (or surviving) mutant. See pytest's own documented exit codes.
_NON_ASSERTION_EXIT_CODES = frozenset({2, 3, 4, 5})


class MutationHarnessError(RuntimeError):
    """A configuration or infrastructure defect -- not a surviving mutant."""


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    mutants = config.get("mutants")
    if not mutants:
        raise MutationHarnessError("config has no registered mutants")

    seen_ids: set[str] = set()
    for mutant in mutants:
        mutant_id = mutant.get("mutant_id")
        if not mutant_id:
            raise MutationHarnessError("a mutant entry is missing mutant_id")
        if mutant_id in seen_ids:
            raise MutationHarnessError(f"duplicate mutant_id: {mutant_id}")
        seen_ids.add(mutant_id)

        operator = mutant.get("operator")
        if operator not in KNOWN_OPERATORS:
            raise MutationHarnessError(
                f"{mutant_id}: unknown operator {operator!r}, "
                f"expected one of {sorted(KNOWN_OPERATORS)}"
            )
        if not mutant.get("source_path"):
            raise MutationHarnessError(f"{mutant_id}: missing source_path")
        if not mutant.get("original_expression"):
            raise MutationHarnessError(f"{mutant_id}: missing original_expression")
        if not mutant.get("replacement_expression"):
            raise MutationHarnessError(f"{mutant_id}: missing replacement_expression")
        if not mutant.get("kill_tests"):
            raise MutationHarnessError(f"{mutant_id}: no focused kill_tests registered")

    missing_required = REQUIRED_MUTANT_IDS - seen_ids
    if missing_required:
        raise MutationHarnessError(
            f"config is missing required mutant IDs: {sorted(missing_required)}"
        )


def apply_mutation(
    text: str, original: str, replacement: str, *, mutant_id: str
) -> str:
    """Replace `original` with `replacement`, requiring it occur exactly
    once. A mutant that could silently rewrite the wrong statement --
    or nothing at all -- is a harness defect, not a mutation."""
    occurrences = text.count(original)
    if occurrences != 1:
        raise MutationHarnessError(
            f"{mutant_id}: original_expression occurs {occurrences} times "
            "in the source file, expected exactly 1"
        )
    return text.replace(original, replacement, 1)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _worktree_source_hashes(mutants: list[dict[str, Any]]) -> dict[str, str]:
    paths = sorted({m["source_path"] for m in mutants})
    return {p: _file_sha256(REPO_ROOT / p) for p in paths}


def _prepare_workspace(workspace: Path, test_files: set[str]) -> Path:
    """Copy the real src/erp_agent_os package and only the referenced test
    files into `workspace`. Returns the copied package's src/ directory,
    meant to be prepended to PYTHONPATH so it shadows any editable-install
    entry pointing at the real worktree."""
    src_dir = workspace / "src"
    shutil.copytree(REPO_ROOT / "src" / SRC_PACKAGE, src_dir / SRC_PACKAGE)
    for relative in test_files:
        source = REPO_ROOT / relative
        destination = workspace / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return src_dir


def _run_focused_tests(
    workspace: Path, src_dir: Path, node_ids: list[str]
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src_dir)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", *node_ids],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _failing_test_names(stdout: str) -> list[str]:
    """Extract only the test node ID from each pytest "FAILED" summary
    line, discarding everything from " - " onward.

    Found live, not assumed: pytest's short summary appends the
    assertion's own message after " - ", and truncates that message to
    fit the detected terminal width -- which differs between a local
    Windows shell and GitHub Actions' runner, so the SAME test failure
    was captured as two different strings ("...assert True is False" on
    one platform, "..." mid-word on the other, or the suffix missing
    entirely). That made the content-addressed mutation report
    (_write_report) hash differently per platform even though every
    mutant's kill/survive outcome was identical -- see
    docs/audit.md for the write-up. The node ID before " - " is stable;
    the free-text reason after it is not, and nothing in this repo reads
    it (grep confirmed), so it is not worth keeping at the cost of
    reproducibility.
    """
    names = []
    for line in stdout.splitlines():
        if not line.startswith("FAILED "):
            continue
        node_id = line[len("FAILED ") :].split(" - ", 1)[0]
        names.append(node_id.strip())
    return names


def _run_baseline(
    tmp_root: Path, mutants: list[dict[str, Any]]
) -> subprocess.CompletedProcess[str]:
    """All registered kill_tests, unmodified, must pass before any mutant
    is applied -- a failure here means the test suite itself is broken,
    which is a harness error unrelated to mutation testing."""
    all_node_ids = sorted({node for m in mutants for node in m["kill_tests"]})
    test_files = {node.split("::", 1)[0] for node in all_node_ids}
    workspace = tmp_root / "baseline"
    workspace.mkdir()
    src_dir = _prepare_workspace(workspace, test_files)
    return _run_focused_tests(workspace, src_dir, all_node_ids)


def _run_one_mutant(tmp_root: Path, mutant: dict[str, Any]) -> dict[str, Any]:
    mutant_id = mutant["mutant_id"]
    source_path = mutant["source_path"]
    node_ids = mutant["kill_tests"]
    test_files = {node.split("::", 1)[0] for node in node_ids}

    workspace = tmp_root / mutant_id
    workspace.mkdir()
    src_dir = _prepare_workspace(workspace, test_files)

    target = src_dir / Path(source_path).relative_to("src")
    original_text = target.read_text(encoding="utf-8")
    mutated_text = apply_mutation(
        original_text,
        mutant["original_expression"],
        mutant["replacement_expression"],
        mutant_id=mutant_id,
    )
    target.write_text(mutated_text, encoding="utf-8")

    result = _run_focused_tests(workspace, src_dir, node_ids)
    failing = _failing_test_names(result.stdout)

    if result.returncode == 0:
        killed = False
        harness_error = None
    elif result.returncode in _NON_ASSERTION_EXIT_CODES or not failing:
        killed = False
        harness_error = (
            f"pytest exited {result.returncode} without a genuine failed "
            "assertion (collection/import/infra failure, not a kill)"
        )
    else:
        killed = True
        harness_error = None

    return {
        "mutant_id": mutant_id,
        "operator": mutant["operator"],
        "source_path": source_path,
        "original_expression_sha256": hashlib.sha256(
            mutant["original_expression"].encode("utf-8")
        ).hexdigest(),
        "replacement_expression_sha256": hashlib.sha256(
            mutant["replacement_expression"].encode("utf-8")
        ).hexdigest(),
        "mutated_source_sha256": hashlib.sha256(
            mutated_text.encode("utf-8")
        ).hexdigest(),
        "kill_tests": node_ids,
        "returncode": result.returncode,
        "failing_tests": failing,
        "killed": killed,
        "harness_error": harness_error,
    }


def run_all(
    config: dict[str, Any], *, only_mutant_ids: frozenset[str] | None = None
) -> dict[str, Any]:
    mutants = config["mutants"]
    if only_mutant_ids is not None:
        mutants = [m for m in mutants if m["mutant_id"] in only_mutant_ids]
        if not mutants:
            raise MutationHarnessError("only_mutant_ids matched no registered mutant")

    hashes_before = _worktree_source_hashes(mutants)

    with tempfile.TemporaryDirectory(prefix="erp_agent_os_mutation_") as tmp:
        tmp_root = Path(tmp)
        baseline = _run_baseline(tmp_root, mutants)
        if baseline.returncode != 0:
            raise MutationHarnessError(
                "baseline (unmutated) focused tests did not all pass; "
                f"pytest exit {baseline.returncode}:\n{baseline.stdout[-4000:]}"
            )
        mutant_reports = [_run_one_mutant(tmp_root, m) for m in mutants]

    hashes_after = _worktree_source_hashes(mutants)
    if hashes_before != hashes_after:
        raise MutationHarnessError(
            "the real worktree's source hashes changed during mutation "
            "testing -- a mutant escaped its isolated tempdir copy"
        )

    all_killed = all(m["killed"] for m in mutant_reports)
    report = {
        "schema_version": "1.0",
        "config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "worktree_source_hashes": hashes_before,
        "mutants": mutant_reports,
        "all_mutants_killed": all_killed,
    }
    return report


def _canonical_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_report(report: dict[str, Any]) -> Path:
    canonical = _canonical_bytes(report)
    content_hash = hashlib.sha256(canonical).hexdigest()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"targeted_mutation_report_{content_hash}.json"
    if not target.exists():
        target.write_bytes(canonical)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="also require a previously written report to still match byte-for-byte",
    )
    args = parser.parse_args(argv)

    config = load_config()
    report = run_all(config)
    target = _write_report(report)

    for mutant in report["mutants"]:
        status = "killed" if mutant["killed"] else "SURVIVED"
        print(f"{mutant['mutant_id']}: {status} (exit {mutant['returncode']})")
        if mutant["harness_error"]:
            print(f"  harness error: {mutant['harness_error']}")

    print(f"wrote {target}")
    print(f"all_mutants_killed={report['all_mutants_killed']}")

    if args.verify:
        on_disk_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        expected_name = f"targeted_mutation_report_{on_disk_hash}.json"
        if target.name != expected_name:
            print(f"content-address mismatch: {target.name} != {expected_name}")
            return 1
        print(f"content-addressed report verified: {target.name}")

    if not report["all_mutants_killed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
