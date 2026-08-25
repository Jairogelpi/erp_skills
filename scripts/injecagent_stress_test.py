"""External adversarial stress test of validation.py's lexical detectors.

CLAUDE.md §36 and docs/results.md both declare that
`detect_text_signals` is lexical and tuned to ERP-Skills-Bench v1's own
templated Spanish text -- "no se generaliza a adversarios adaptativos".
This script measures that limitation against a real, independently
published attack set instead of just asserting it.

Data: InjecAgent (Zhan et al. 2024, arXiv:2403.02691),
data/injecagent_test_cases_dh_base.json, 510 indirect-prompt-injection
cases (direct-harm base split), fetched from
https://github.com/uiuc-kang-lab/InjecAgent (MIT-licensed data). Not
this project's own benchmark, not ERP-domain, not Spanish -- deliberately
so: the point is testing outside ERP-Skills-Bench's own distribution.

Each case's "Attacker Instruction" is the indirect-injection payload
(text an attacker plants inside data a tool returns, hoping the agent
executes it as if it were a real instruction). This script runs that
text through the same `detect_text_signals()` System C actually calls,
and reports how many trigger a blocking finding. It does not run the
full InjecAgent harness (tool-calling simulation, LLM-in-the-loop) --
only the one component this project has and claims something about: the
lexical pre-execution detector.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from erp_agent_os.validation import blocking_findings, detect_text_signals

DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "injecagent_test_cases_dh_base.json"
)
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "injecagent_stress_test_results.json"
)


def main() -> None:
    cases = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    detected = 0
    by_attack_type: Counter[str] = Counter()
    detected_by_attack_type: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    examples_detected: list[dict[str, Any]] = []
    examples_missed: list[str] = []

    for case in cases:
        text = case["Attacker Instruction"]
        attack_type = case["Attack Type"]
        by_attack_type[attack_type] += 1

        findings = blocking_findings(detect_text_signals(text))
        if findings:
            detected += 1
            detected_by_attack_type[attack_type] += 1
            for f in findings:
                kind_counts[f.kind.value] += 1
            if len(examples_detected) < 3:
                examples_detected.append(
                    {"text": text, "findings": [f.kind.value for f in findings]}
                )
        elif len(examples_missed) < 3:
            examples_missed.append(text)

    n = len(cases)
    report = {
        "source": "InjecAgent (Zhan et al. 2024), test_cases_dh_base.json",
        "n_cases": n,
        "detected": detected,
        "detection_rate": detected / n,
        "by_attack_type": {
            attack: {
                "n": by_attack_type[attack],
                "detected": detected_by_attack_type[attack],
                "detection_rate": detected_by_attack_type[attack]
                / by_attack_type[attack],
            }
            for attack in by_attack_type
        },
        "finding_kinds_triggered": dict(kind_counts),
        "examples_detected": examples_detected,
        "examples_missed": examples_missed,
        "interpretation": (
            "detect_text_signals now has English patterns alongside the "
            "Spanish ones tuned to ERP-Skills-Bench v1 (added after this "
            "test first ran at 0%). The remaining low rate is not a "
            "language gap anymore -- it is that InjecAgent's payloads "
            "are polite, direct requests with no injection-style framing "
            "('Please delete...', 'Please transfer...'), so lexical "
            "patterns built around attack phrasing structurally cannot "
            "catch them; only 'delete...permanently'-style phrasing in "
            "the Data Security Harm split happened to match an "
            "IRREVERSIBLE pattern. See docs/injecagent-stress-test.md."
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
