#!/usr/bin/env python
"""One-shot v2.1 confirmatory campaign runner (Task 10, extended).

NOT executed as part of implementing this module -- running it for
real requires a real LLM provider API key and spends real quota/money;
that is an operator decision, made explicitly, not something this
commit does on its own.

    uv run python scripts/run_confirmatory_v2_1.py --dry-run --provider groq
    uv run python scripts/run_confirmatory_v2_1.py --provider groq

`--dry-run` verifies hashes, the EXACT unit count across all six arms,
and provider configuration, and prints a report -- it never writes a
receipt or calls a real provider (`erp_agent_os.freeze_v2_1.
dry_run_check` is structurally incapable of either). Generating the
scenario/security population in memory to COUNT the exact plan is a
pure, side-effect-free operation (the same `generate_scenarios`/
`generate_security_population` calls `generate_holdout` makes) -- it
writes nothing and transitions no state, so it does not "consume" the
holdout in the sense section 12 means (a HoldoutManifest committed to
a receipt log).

A real run chains ALL SIX arms -- main, H2, H3a, H3b, H4, H6 -- so
every one of H1-H8 has a real execution path; leaving any of them
unconnected would mean spending real quota on a campaign that still
cannot answer every hypothesis it was supposed to. Each arm gets its
own checkpoint file, so an interruption during one arm never discards
progress already checkpointed in another. `complete_run` requires
`len(observations)` to match the EXACT `n_planned_units` `start_run`
declared up front -- computed via `erp_agent_os.experiment_v2_1`'s own
`build_*_plan` functions (the SAME code that later executes the plan),
never estimated or guessed at.

H3b (section 6.4, secondary) runs on a stratified sample of the main
corpus (`erp_agent_os.scenarios_v2_1.select_h3b_stratified_sample`,
`h3b_sample_size` from the frozen protocol -- 60 by default), not the
full 1000+-scenario main corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from erp_agent_os.evidence_v2_1 import ObservationV21, write_observations_v21_jsonl
from erp_agent_os.experiment_v2_1 import (
    ArmRunContext,
    build_h2_arm_plan,
    build_h3a_arm_plan,
    build_h3b_arm_plan,
    build_h4_arm_plan,
    build_h6_ablation_plan,
    build_main_arm_plan,
    run_h2_arm,
    run_h3a_arm,
    run_h3b_arm,
    run_h4_arm,
    run_h6_ablation,
    run_main_arm,
)
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
from erp_agent_os.protocol_v2_1 import ProtocolV21, load_protocol
from erp_agent_os.scenarios_v2_1 import ScenarioSpec, select_h3b_stratified_sample
from erp_agent_os.security_scenarios_v2_1 import generate_security_population

DEFAULT_CODE_MANIFEST_PATH = (
    REPO_ROOT / "data" / "protocol_v2_1" / "code_freeze_manifest.json"
)
DEFAULT_PROTOCOL_PATH = REPO_ROOT / "config" / "protocol_v2_1.json"
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


ScenarioTuple = tuple[ScenarioSpec, ...]


def _generate_all_scenarios(
    seed: int,
) -> tuple[ScenarioTuple, ScenarioTuple, ScenarioTuple]:
    """Pure and side-effect-free: writes nothing, transitions no state.
    Safe to call from --dry-run purely to COUNT the exact plan; the
    real run instead gets these three lists from `generate_holdout`,
    which additionally runs the concordance gate and commits a
    HoldoutManifest -- this helper does neither.

    Sample sizes come from `load_selected_sample_sizes` (the frozen
    power analysis' "selected" block, e.g. n_main=1184), never the bare
    `generate_scenarios`/`generate_security_population` defaults (the
    section 6.1 floor, n_main=120) -- using the defaults here would
    silently under-power the campaign relative to what was frozen,
    exactly the gap this function exists to close."""
    from erp_agent_os.scenarios_v2_1 import generate_scenarios

    sizes = load_selected_sample_sizes()
    main = generate_scenarios(seed=seed, n_main=sizes["n_main"])
    dangerous, safe = generate_security_population(
        n_dangerous=sizes["n_security_dangerous"]
    )
    return main, dangerous, safe


def _h3b_sample(
    main: Sequence[ScenarioSpec], protocol: ProtocolV21
) -> tuple[ScenarioSpec, ...]:
    return select_h3b_stratified_sample(main, sample_size=protocol.h3.h3b_sample_size)


def _exact_planned_unit_count(
    main: Sequence[ScenarioSpec],
    dangerous: Sequence[ScenarioSpec],
    safe: Sequence[ScenarioSpec],
    protocol: ProtocolV21,
) -> int:
    """The EXACT total across all six arms, computed with the SAME
    `build_*_plan` functions that later execute them -- there is no
    second, independent counting formula that could drift from what
    actually runs."""
    h3b_sample = _h3b_sample(main, protocol)
    return (
        len(build_main_arm_plan(main))
        + len(build_h2_arm_plan(main))
        + len(build_h3a_arm_plan(main))
        + len(build_h3b_arm_plan(h3b_sample, repetitions=protocol.h3.h3b_min_calls))
        + len(build_h4_arm_plan(dangerous, safe))
        + len(build_h6_ablation_plan(main))
    )


def _run_dry(args: argparse.Namespace) -> int:
    code_manifest = _load_code_manifest(args.code_manifest_path)
    protocol = load_protocol(args.protocol_path)
    client, model, provider_config = _build_client(args.provider)
    del client  # dry-run never calls the provider
    context = _build_context(code_manifest, args.provider, model, provider_config)

    main, dangerous, safe = _generate_all_scenarios(args.seed)
    n_planned = _exact_planned_unit_count(main, dangerous, safe, protocol)

    result = dry_run_check(
        code_manifest=code_manifest,
        provider=args.provider,
        provider_config_hash=context.provider_config_hash,
        expected_provider=args.provider,
        expected_provider_config_hash=context.provider_config_hash,
        n_planned_units=n_planned,
    )
    print(
        json.dumps(
            {
                "ok": result.ok,
                "mismatches": list(result.mismatches),
                "n_planned_units": n_planned,
                "n_main": len(main),
                "n_security_dangerous": len(dangerous),
                "n_security_safe": len(safe),
                "n_h3b_sample": protocol.h3.h3b_sample_size,
            },
            indent=2,
        )
    )
    return 0 if result.ok else 1


def _run_real(args: argparse.Namespace) -> int:
    code_manifest = _load_code_manifest(args.code_manifest_path)
    protocol = load_protocol(args.protocol_path)
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
    n_planned = _exact_planned_unit_count(main, dangerous, safe, protocol)
    start_run(
        receipt_log,
        holdout,
        provider=args.provider,
        provider_config_hash=context.provider_config_hash,
        checkpoint_path=checkpoint_dir / "main.jsonl",
        n_planned_units=n_planned,
    )

    llm_by_system = {"A": client, "B": client, "C": client}
    h3b_sample = _h3b_sample(main, protocol)
    all_observations: list[ObservationV21] = []
    try:
        all_observations += run_main_arm(
            main, llm_by_system, context, checkpoint_path=checkpoint_dir / "main.jsonl"
        )
        all_observations += run_h2_arm(
            main, llm_by_system, context, checkpoint_path=checkpoint_dir / "h2.jsonl"
        )
        all_observations += run_h3a_arm(
            main, llm_by_system, context, checkpoint_path=checkpoint_dir / "h3a.jsonl"
        )
        all_observations += run_h3b_arm(
            h3b_sample,
            llm_by_system,
            context,
            checkpoint_path=checkpoint_dir / "h3b.jsonl",
            repetitions=protocol.h3.h3b_min_calls,
        )
        all_observations += run_h4_arm(
            dangerous,
            safe,
            llm_by_system,
            context,
            checkpoint_path=checkpoint_dir / "h4.jsonl",
        )
        all_observations += run_h6_ablation(
            main, client, context, checkpoint_path=checkpoint_dir / "h6.jsonl"
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
    parser.add_argument("--protocol-path", type=Path, default=DEFAULT_PROTOCOL_PATH)
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
