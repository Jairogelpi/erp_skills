"""Advance the human-gated v2 workflow without ever simulating a reviewer."""

import json
import sys
from pathlib import Path

from erp_agent_os.prospective_evidence import (
    HumanGateIncomplete,
    apply_adjudication_packet,
    finalize_v2_holdout,
    review_annotation_packets,
    write_adjudication_packet,
    write_state_review_packets,
)
from erp_agent_os.prospective_v2 import generate_v2_candidates

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DESTINATION = PROJECT_ROOT / "data" / "prospective_v2"


def _path_arg(flag: str) -> Path | None:
    if flag not in sys.argv:
        return None
    try:
        return Path(sys.argv[sys.argv.index(flag) + 1])
    except IndexError as exc:
        raise SystemExit(f"{flag} requires a path") from exc


def _destination() -> Path:
    return _path_arg("--destination") or DEFAULT_DESTINATION


def _candidate_manifest(destination: Path) -> Path:
    explicit = _path_arg("--candidate-manifest")
    if explicit is not None:
        return explicit
    matches = sorted(destination.glob("bench_v2_candidate_seal_*.json"))
    if len(matches) != 1:
        raise HumanGateIncomplete(
            "expected exactly one candidate seal; pass --candidate-manifest explicitly"
        )
    return matches[0]


def _emit(status: str, **details: object) -> None:
    print(
        json.dumps(
            {"status": status, "system_evaluation_allowed": False, **details},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def main() -> None:
    destination = _destination()
    cases = generate_v2_candidates()
    manifest_path = _candidate_manifest(destination)
    annotation_paths = (
        destination / "bench_v2_annotation_annotator_1.csv",
        destination / "bench_v2_annotation_annotator_2.csv",
    )
    try:
        review = review_annotation_packets(cases, *annotation_paths)
    except HumanGateIncomplete as exc:
        _emit("awaiting_two_complete_independent_annotations", reason=str(exc))
        return

    if review.disagreements:
        adjudication_path = write_adjudication_packet(review, destination)
        try:
            review = apply_adjudication_packet(review, adjudication_path)
        except HumanGateIncomplete as exc:
            _emit(
                "awaiting_third_party_adjudication",
                disagreements=len(review.disagreements),
                decision_kappa=review.decision_kappa,
                adjudication_packet=adjudication_path.name,
                reason=str(exc),
            )
            return

    states = write_state_review_packets(cases, review, destination)
    try:
        final = finalize_v2_holdout(
            cases,
            review,
            states,
            destination,
            candidate_manifest_path=manifest_path,
        )
    except HumanGateIncomplete as exc:
        _emit(
            "awaiting_two_independent_state_reviews",
            semantic_agreement_rate=review.agreement_rate,
            decision_kappa=review.decision_kappa,
            state_proposals=states.proposals_path.name,
            state_review_packets=[path.name for path in states.review_packets],
            reason=str(exc),
        )
        return

    print(
        json.dumps(
            {
                "status": "prospectively_frozen_unseen_ready_for_one_shot_evaluation",
                "system_evaluation_allowed": True,
                "gold": final.gold_path.name,
                "final_manifest": final.manifest_path.name,
                "gold_sha256": final.gold_sha256,
                "next_action": (
                    "Run scripts/run_experiment.py exactly once with --real-llm, "
                    "--real-parser, --v2-gold and --v2-manifest."
                ),
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except HumanGateIncomplete as exc:
        print(f"v2 workflow refused to advance: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
