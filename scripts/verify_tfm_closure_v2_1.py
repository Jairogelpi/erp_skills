#!/usr/bin/env python
"""Closure-gate verifier for the v2.1 confirmatory protocol (Task 12).

Four explicit, mutually distinct modes -- each checks a different point
in the campaign lifecycle, never assumes a later stage's guarantees:

    uv run python scripts/verify_tfm_closure_v2_1.py --pre-run
    uv run python scripts/verify_tfm_closure_v2_1.py --raw-only
    uv run python scripts/verify_tfm_closure_v2_1.py --failed-external
    uv run python scripts/verify_tfm_closure_v2_1.py --final

`--pre-run` requires the v2 supersession receipt, the power analysis
artifact, and every component/protocol/code hash to resolve cleanly --
and requires NO v2.1 receipts exist yet (DRAFT_PROTOCOL). It never
requires raw observations, because none can exist before a run starts.
Success prints the literal string `READY_TO_COMMIT_AND_CREATE_CODE_
FREEZE` (Task 12 step 5's own expected output), never a scientific
result -- this mode cannot see one, since no campaign has run.

`--raw-only` requires RUN_COMPLETED and exact planned-unit coverage.

`--failed-external` requires the terminal RUN_FAILED_EXTERNAL receipt,
stable code-freeze hashes, an existing checkpoint file, and every
partial row already checkpointed to be semantically complete -- but
explicitly does NOT require full coverage, and this script never
constructs or authorizes a confirmatory claim in this mode.

`--final` accepts either a complete RUN_COMPLETED report or a validated
RUN_FAILED_EXTERNAL state, and checks the resulting claim language too.

Every mode rejects any protocol.json declaring human_annotation_required
-- a config-level check, layered on top of Pydantic already refusing to
construct such a ProtocolV21 at all (belt and suspenders: this catches
a hand-edited or corrupted file before it is ever loaded that far).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from erp_agent_os.claims_v2_1 import (
    ClaimsV21Error,
    EvidenceState,
    assert_claim_text_is_authorized,
)
from erp_agent_os.evidence_v2_1 import ObservationV21, validate_arm_semantics
from erp_agent_os.freeze_v2_1 import (
    REPO_ROOT,
    CodeFreezeManifest,
    RunState,
    compute_component_hashes,
    current_state,
    load_receipts,
    load_selected_sample_sizes,
    verify_code_freeze,
)
from erp_agent_os.protocol_v2_1 import ProtocolV21Error, load_protocol

DEFAULT_PROTOCOL_PATH = REPO_ROOT / "config" / "protocol_v2_1.json"
DEFAULT_SUPERSESSION_DIR = REPO_ROOT / "data" / "protocol_v2_1"
DEFAULT_RECEIPT_LOG = REPO_ROOT / "data" / "protocol_v2_1" / "runs" / "receipts.jsonl"


@dataclass(frozen=True)
class ClosureCheckResult:
    ok: bool
    mode: str
    message: str
    reasons: tuple[str, ...] = ()


def _reject_human_annotation(protocol_path: Path) -> list[str]:
    """ProtocolV21's own Pydantic validator already refuses to
    CONSTRUCT a protocol with human_annotation_required=True -- there
    is no code path that returns a live `protocol` object with that
    flag set, so this function can never re-check the flag on one. Its
    real job is different: turn whatever `load_protocol` raises (a
    missing file, or Pydantic's own ValidationError for this exact
    flag, or any other schema violation) into a closure-blocking reason
    instead of an uncaught exception -- confirmed by a real load
    failure in this module's own tests, not assumed to be equivalent."""
    try:
        load_protocol(protocol_path)
    except ProtocolV21Error as exc:
        return [f"protocol failed to load: {exc}"]
    except Exception as exc:  # noqa: BLE001 - Pydantic's ValidationError, etc.
        if "human_annotation_required" in str(exc):
            return ["protocol declares human_annotation_required=True"]
        return [f"protocol failed to load: {exc}"]
    return []


def check_pre_run(
    *,
    repo_root: Path = REPO_ROOT,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    supersession_dir: Path = DEFAULT_SUPERSESSION_DIR,
    receipt_log: Path = DEFAULT_RECEIPT_LOG,
) -> ClosureCheckResult:
    reasons: list[str] = []

    supersession_matches = sorted(supersession_dir.glob("v2_supersession_*.json"))
    if len(supersession_matches) != 1:
        reasons.append(
            f"expected exactly one v2_supersession_*.json in {supersession_dir}, "
            f"found {len(supersession_matches)}"
        )

    try:
        load_selected_sample_sizes(repo_root=repo_root)
    except Exception as exc:  # noqa: BLE001 - report, do not crash the gate
        reasons.append(f"power analysis artifact invalid: {exc}")

    try:
        compute_component_hashes(repo_root=repo_root)
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"component hash coverage incomplete: {exc}")

    state = current_state(receipt_log)
    if state is not RunState.DRAFT_PROTOCOL:
        reasons.append(
            f"expected no v2.1 receipts yet (DRAFT_PROTOCOL), found state={state.value}"
        )

    reasons.extend(_reject_human_annotation(protocol_path))

    ok = not reasons
    message = "READY_TO_COMMIT_AND_CREATE_CODE_FREEZE" if ok else "NOT_READY"
    return ClosureCheckResult(
        ok=ok, mode="pre-run", message=message, reasons=tuple(reasons)
    )


def check_raw_only(
    *,
    receipt_log: Path = DEFAULT_RECEIPT_LOG,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
) -> ClosureCheckResult:
    reasons: list[str] = []
    state = current_state(receipt_log)
    if state is not RunState.RUN_COMPLETED:
        reasons.append(f"expected RUN_COMPLETED, found state={state.value}")
    else:
        receipts = load_receipts(receipt_log)
        last = receipts[-1]
        if last.n_completed_units != last.n_planned_units:
            reasons.append(
                f"unit coverage mismatch: planned={last.n_planned_units} "
                f"completed={last.n_completed_units}"
            )
    reasons.extend(_reject_human_annotation(protocol_path))

    ok = not reasons
    return ClosureCheckResult(
        ok=ok,
        mode="raw-only",
        message="RAW_COVERAGE_OK" if ok else "NOT_READY",
        reasons=tuple(reasons),
    )


def _load_checkpoint_observations(path: Path) -> list[ObservationV21]:
    """Checkpoint files hold {"key": ..., "observation": {...}} rows --
    erp_agent_os.experiment_v2_1's own per-arm checkpoint format, not
    the content-addressed archive schema (which is only ever written
    once a whole arm finishes)."""
    if not path.exists():
        return []
    observations = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        observations.append(ObservationV21(**row["observation"]))
    return observations


def check_failed_external(
    *,
    code_manifest: CodeFreezeManifest,
    repo_root: Path = REPO_ROOT,
    receipt_log: Path = DEFAULT_RECEIPT_LOG,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    checkpoint_paths: tuple[Path, ...] = (),
) -> ClosureCheckResult:
    reasons: list[str] = []
    state = current_state(receipt_log)
    if state is not RunState.RUN_FAILED_EXTERNAL:
        reasons.append(f"expected RUN_FAILED_EXTERNAL, found state={state.value}")

    drift = verify_code_freeze(code_manifest, repo_root=repo_root)
    if drift:
        reasons.append(f"code hashes drifted: {sorted(drift)}")

    receipts = load_receipts(receipt_log)
    last = receipts[-1] if receipts else None
    if last is not None and last.checkpoint_path is not None:
        checkpoint = Path(last.checkpoint_path)
        if not checkpoint.exists():
            reasons.append(f"checkpoint file missing: {checkpoint}")

    all_partial_rows: list[ObservationV21] = []
    for path in checkpoint_paths:
        all_partial_rows.extend(_load_checkpoint_observations(path))
    for observation in all_partial_rows:
        try:
            validate_arm_semantics(observation)
        except Exception as exc:  # noqa: BLE001
            reasons.append(
                f"semantically incomplete partial row {observation.scenario_id}/"
                f"{observation.system}/{observation.arm}: {exc}"
            )

    reasons.extend(_reject_human_annotation(protocol_path))

    ok = not reasons
    return ClosureCheckResult(
        ok=ok,
        mode="failed-external",
        message="FAILED_EXTERNAL_VALIDATED" if ok else "NOT_VALID",
        reasons=tuple(reasons),
    )


def check_final(
    *,
    code_manifest: CodeFreezeManifest,
    repo_root: Path = REPO_ROOT,
    receipt_log: Path = DEFAULT_RECEIPT_LOG,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    checkpoint_paths: tuple[Path, ...] = (),
    report_path: Path | None = None,
) -> ClosureCheckResult:
    state = current_state(receipt_log)

    if state is RunState.RUN_FAILED_EXTERNAL:
        result = check_failed_external(
            code_manifest=code_manifest,
            repo_root=repo_root,
            receipt_log=receipt_log,
            protocol_path=protocol_path,
            checkpoint_paths=checkpoint_paths,
        )
        return ClosureCheckResult(
            ok=result.ok, mode="final", message=result.message, reasons=result.reasons
        )

    if state is not RunState.RUN_COMPLETED:
        return ClosureCheckResult(
            ok=False,
            mode="final",
            message="NOT_READY",
            reasons=(
                f"expected RUN_COMPLETED or RUN_FAILED_EXTERNAL, found {state.value}",
            ),
        )

    raw = check_raw_only(receipt_log=receipt_log, protocol_path=protocol_path)
    reasons = list(raw.reasons)

    if report_path is not None:
        reasons.extend(_validate_report_claims(report_path))
    else:
        reasons.append(
            "--report-path is required to validate claim language for a completed run"
        )

    ok = not reasons
    return ClosureCheckResult(
        ok=ok,
        mode="final",
        message="CLOSURE_VALID" if ok else "NOT_VALID",
        reasons=tuple(reasons),
    )


def _validate_report_claims(report_path: Path) -> list[str]:
    if not report_path.exists():
        return [f"report not found: {report_path}"]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    reasons: list[str] = []
    for hypothesis, entry in payload.get("hypotheses", {}).items():
        claim = entry.get("claim", {})
        try:
            evidence_state = EvidenceState(claim["evidence_state"])
        except (KeyError, ValueError) as exc:
            reasons.append(f"{hypothesis}: invalid evidence_state: {exc}")
            continue
        try:
            assert_claim_text_is_authorized(
                claim.get("claim_text", ""), evidence_state=evidence_state
            )
        except ClaimsV21Error as exc:
            reasons.append(f"{hypothesis}: {exc}")
    return reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pre-run", action="store_true")
    mode.add_argument("--raw-only", action="store_true")
    mode.add_argument("--failed-external", action="store_true")
    mode.add_argument("--final", action="store_true")
    parser.add_argument("--protocol-path", type=Path, default=DEFAULT_PROTOCOL_PATH)
    parser.add_argument("--receipt-log", type=Path, default=DEFAULT_RECEIPT_LOG)
    parser.add_argument("--code-manifest-path", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, action="append", default=[])
    parser.add_argument("--report-path", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.pre_run:
        result = check_pre_run(
            protocol_path=args.protocol_path, receipt_log=args.receipt_log
        )
    elif args.raw_only:
        result = check_raw_only(
            receipt_log=args.receipt_log, protocol_path=args.protocol_path
        )
    else:
        if args.code_manifest_path is None:
            print("--code-manifest-path is required for --failed-external/--final")
            return 2
        code_manifest = CodeFreezeManifest(
            **json.loads(args.code_manifest_path.read_text(encoding="utf-8"))
        )
        if args.failed_external:
            result = check_failed_external(
                code_manifest=code_manifest,
                receipt_log=args.receipt_log,
                protocol_path=args.protocol_path,
                checkpoint_paths=tuple(args.checkpoint),
            )
        else:
            result = check_final(
                code_manifest=code_manifest,
                receipt_log=args.receipt_log,
                protocol_path=args.protocol_path,
                checkpoint_paths=tuple(args.checkpoint),
                report_path=args.report_path,
            )

    print(result.message)
    for reason in result.reasons:
        print(f"  - {reason}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
