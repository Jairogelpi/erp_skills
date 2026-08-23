"""Seal the prospective v2 candidates without exposing their proposed labels."""

import json
import sys
from pathlib import Path

from erp_agent_os.prospective_evidence import seal_candidate_holdout
from erp_agent_os.prospective_v2 import generate_v2_candidates

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DESTINATION = PROJECT_ROOT / "data" / "prospective_v2"


def _destination_arg() -> Path:
    if "--destination" not in sys.argv:
        return DEFAULT_DESTINATION
    try:
        return Path(sys.argv[sys.argv.index("--destination") + 1])
    except IndexError as exc:
        raise SystemExit("--destination requires a path") from exc


def main() -> None:
    destination = _destination_arg()
    seal = seal_candidate_holdout(generate_v2_candidates(), destination)
    result = {
        "status": "v2_candidates_sealed_awaiting_human_annotation",
        "system_evaluation_allowed": False,
        "candidate_manifest": seal.manifest_path.name,
        "blinded_candidates": seal.candidates_path.name,
        "annotation_packets": [path.name for path in seal.annotation_packets],
        "candidates_sha256": seal.candidates_sha256,
        "next_action": (
            "Give the two CSV packets to two independent human annotators; "
            "do not give them the author-proposals archive."
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
