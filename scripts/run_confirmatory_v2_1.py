#!/usr/bin/env python
"""One-shot v2.1 confirmatory campaign runner (Task 10).

NOT executed as part of implementing this module -- docs/tfm-closure-
no-human-v2.1.md's own plan says so explicitly ("Do not execute
scripts/run_confirmatory_v2_1.py during implementation"), and running
it for real requires a CODE_FROZEN manifest that in turn requires an
annotated git tag, which does not exist yet in this repository.

    uv run python scripts/run_confirmatory_v2_1.py --dry-run --provider groq
    uv run python scripts/run_confirmatory_v2_1.py --provider groq

`--dry-run` verifies hashes, unit counts and provider configuration and
prints a report -- it never generates a holdout, never writes a
receipt, and never calls a real provider (`erp_agent_os.freeze_v2_1.
dry_run_check` is structurally incapable of any of the three).

A real run chains the main and H4 security arms, in that order, each
with its own checkpoint file so an interruption during one arm never
discards progress already checkpointed in the other
(erp_agent_os.experiment_v2_1's `_run_plan` guarantees per-arm resume;
this script only sequences two arms on top of it). `complete_run`
requires `len(observations)` to match the EXACT `n_planned_units`
`start_run` declared up front -- computed here from the real,
power-selected sample sizes (`load_selected_sample_sizes`), not
estimated after the fact.

H2/H3a/H3b/H6 are deliberately NOT chained here yet: each has its own
scenario subset or repetition count (H2 only scenarios with an expected
skill, H3a three surfaces per scenario, H3b a stratified 60-scenario
sample, H6 the ablation-relabeled main arm) that erp_agent_os.
experiment_v2_1 does not yet expose a "plan size without executing"
helper for. Wiring them in without an exact, provable unit count would
make `complete_run`'s own evidence gate either wrong or trivially
disabled -- worse than leaving them for a follow-up that adds the
missing helper first.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from erp_agent_os.evidence_v2_1 import ObservationV21, write_observations_v21_jsonl
from erp_agent_os.experiment_v2_1 import ArmRunContext, run_h4_arm, run_main_arm
from erp_agent_os.freeze_v2_1 import (
    REPO_ROOT,
    CodeFreezeManifest,
    FreezeV21Error,
    complete_run,
    current_state,
    dry_run_check,
    generate_holdout,
    load_selected_sample_sizes,
    mark_failed_external,
    mark_interrupted,
    record_holdout_generated,
    start_run,
)
from erp_agent_os.llm_client import LLMClient

DEFAULT_CODE_MANIFEST_PATH = (
    REPO_ROOT / "data" / "protocol_v2_1" / "code_freeze_manifest.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "protocol_v2_1" / "runs"

Provider = Literal["groq", "gemini", "openrouter"]


def _load_code_manifest(path: Path) -> CodeFreezeManifest:
    if not path.exists():
        raise FreezeV21Error(
            f"no CODE_FROZEN manifest at {path}; run "
            "scripts/freeze_protocol_v2_1.py first"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CodeFreezeManifest(**payload)


def _build_client(provider: Provider) -> tuple[LLMClient, str, dict[str, object]]:
    """Returns (client, model, provider_config_dict). Imports the real
    provider module lazily so `--dry-run` never needs the SDK or API key
    of a provider it is not about to call."""
    if provider == "groq":
        from erp_agent_os.groq_client import GroqClient, GroqConfig

        config = GroqConfig()
        return GroqClient(config), config.model, config.__dict__
    if provider == "gemini":
        from erp_agent_os.gemini_client import GeminiClient, GeminiConfig

        config = GeminiConfig()
        return GeminiClient(config), config.model, config.__dict__
    if provider == "openrouter":
        from erp_agent_os.openrouter_client import OpenRouterClient, OpenRouterConfig

        config = OpenRouterConfig()
        return OpenRouterClient(config), config.model, config.__dict__
    raise FreezeV21Error(f"unknown provider: {provider!r}")


def _build_context(
    code_manifest: CodeFreezeManifest,
    provider: Provider,
    model: str,
    provider_config: dict,
) -> ArmRunContext:
    return ArmRunContext(
        protocol_version="2.1.0",
        frozen_commit=code_manifest.git_commit,
        dataset_hash=code_manifest.manifest_hash,
        provider=provider,
        model=model,
        provider_config=provider_config,
        code_version_hash=code_manifest.manifest_hash,
        dependency_lock_hash=code_manifest.component_hashes.get("lockfile", ""),
        timeout_seconds=float(provider_config.get("timeout_seconds", 30)),
    )


def _write_arm_archive(
    observations: list[ObservationV21], output_dir: Path, arm_name: str
) -> Path:
    archive = write_observations_v21_jsonl(
        observations,
        output_dir / f"{arm_name}.json",
        provenance={"arm": arm_name},
    )
    return archive.path


def _planned_unit_count(sizes: dict[str, int]) -> int:
    """main (x3 systems) + h4 dangerous+safe (x3 systems each) -- the
    EXACT total for the two arms this script actually chains (see
    module docstring for why H2/H3a/H3b/H6 are not included yet)."""
    return (
        sizes["n_main"] * 3
        + sizes["n_security_dangerous"] * 3
        + sizes["n_security_safe"] * 3
    )


def _run_dry(args: argparse.Namespace) -> int:
    code_manifest = _load_code_manifest(args.code_manifest_path)
    client, model, provider_config = _build_client(args.provider)
    del client  # dry-run never calls the provider
    context = _build_context(code_manifest, args.provider, model, provider_config)

    sizes = load_selected_sample_sizes()
    n_planned = _planned_unit_count(sizes)

    result = dry_run_check(
        code_manifest=code_manifest,
        provider=args.provider,
        provider_config_hash=context.provider_config_hash,
        expected_provider=args.provider,
        expected_provider_config_hash=context.provider_config_hash,
        n_planned_units=n_planned,
    )
    print(
        json.dumps({"ok": result.ok, "mismatches": list(result.mismatches)}, indent=2)
    )
    return 0 if result.ok else 1


def _run_real(args: argparse.Namespace) -> int:
    code_manifest = _load_code_manifest(args.code_manifest_path)
    receipt_log = args.receipt_log
    state = current_state(receipt_log)

    if state.value == "CODE_FROZEN":
        holdout, main, dangerous, safe = generate_holdout(code_manifest, seed=args.seed)
        record_holdout_generated(receipt_log, holdout)
    else:
        raise FreezeV21Error(
            f"expected receipt log state CODE_FROZEN to generate a fresh holdout, "
            f"got {state.value} -- this script does not re-derive an already-"
            "generated holdout from the log alone in this version"
        )

    client, model, provider_config = _build_client(args.provider)
    context = _build_context(code_manifest, args.provider, model, provider_config)

    checkpoint_dir = args.output_dir / "checkpoints"
    n_planned = len(main) * 3 + len(dangerous) * 3 + len(safe) * 3
    start_run(
        receipt_log,
        holdout,
        provider=args.provider,
        provider_config_hash=context.provider_config_hash,
        checkpoint_path=checkpoint_dir / "main.jsonl",
        n_planned_units=n_planned,
    )

    llm_by_system = {"A": client, "B": client, "C": client}
    all_observations: list[ObservationV21] = []
    try:
        all_observations += run_main_arm(
            main, llm_by_system, context, checkpoint_path=checkpoint_dir / "main.jsonl"
        )
        all_observations += run_h4_arm(
            dangerous,
            safe,
            llm_by_system,
            context,
            checkpoint_path=checkpoint_dir / "h4.jsonl",
        )
    except KeyboardInterrupt:
        mark_interrupted(
            receipt_log,
            error_class="KeyboardInterrupt",
            error_message="interrupted by operator",
            n_completed_units=len(all_observations),
        )
        print("interrupted; resumable via the same checkpoint files")
        return 130
    except Exception as exc:  # noqa: BLE001 - any external failure is terminal here
        mark_failed_external(
            receipt_log,
            error_class=type(exc).__name__,
            error_message=str(exc),
            n_completed_units=len(all_observations),
        )
        print(f"RUN_FAILED_EXTERNAL: {type(exc).__name__}: {exc}")
        return 1

    archive_path = _write_arm_archive(all_observations, args.output_dir, "confirmatory")
    complete_run(receipt_log, observations=all_observations, archive_path=archive_path)
    print(f"RUN_COMPLETED: {len(all_observations)} observations at {archive_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--provider", choices=("groq", "gemini", "openrouter"), required=True
    )
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument(
        "--code-manifest-path", type=Path, default=DEFAULT_CODE_MANIFEST_PATH
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--receipt-log", type=Path, default=DEFAULT_OUTPUT_DIR / "receipts.jsonl"
    )
    args = parser.parse_args(argv)

    try:
        if args.dry_run:
            return _run_dry(args)
        return _run_real(args)
    except FreezeV21Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
