#!/usr/bin/env python
"""Run the real, full-scale (>=100,000 replicate) v2.1 power simulation.

TFM Closure Without Human Annotation v2.1, Task 5
(docs/tfm-closure-no-human-v2.1.md section 10).

This is a deliberately separate, slower command from `pytest tests/
test_power_v2_1.py`, which uses a reduced replicate count for CI speed.
The registered sample sizes this script selects are meant to be frozen
into config/protocol_v2_1.json exactly once, before the holdout is
generated -- not recomputed silently later.

    uv run python scripts/run_power_v2_1.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from erp_agent_os.power_v2_1 import (
    MIN_MC_REPLICATES,
    simulate_h1a_power,
    simulate_h1b_power,
    simulate_h4_power,
)

OUTPUT_DIR = Path("data/protocol_v2_1")


def run() -> dict:
    h1a = simulate_h1a_power()
    h1b = simulate_h1b_power()
    h4 = simulate_h4_power()

    n_main = max(120, h1a.n, h1b.n)
    n_security_dangerous = max(84, h4.n)  # 7 categories * 12 (r4_operation retired)

    return {
        "schema_version": "1.0",
        "min_mc_replicates": MIN_MC_REPLICATES,
        "h1a": {
            "n": h1a.n,
            "simulated_power": h1a.simulated_power,
            "power_ci95_low": h1a.power_ci95_low,
            "seed": h1a.seed,
        },
        "h1b": {
            "n": h1b.n,
            "simulated_power": h1b.simulated_power,
            "power_ci95_low": h1b.power_ci95_low,
            "seed": h1b.seed,
        },
        "h4": {
            "n": h4.n,
            "simulated_power": h4.simulated_power,
            "power_ci95_low": h4.power_ci95_low,
            "seed": h4.seed,
        },
        "selected": {
            "n_main": n_main,
            "n_security_dangerous": n_security_dangerous,
            "n_security_safe": n_security_dangerous,
        },
    }


def main() -> int:
    report = run()
    canonical = json.dumps(report, indent=2, sort_keys=True) + "\n"
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"power_analysis_{content_hash}.json"
    if not target.exists():
        target.write_text(canonical, encoding="utf-8")
    print(f"wrote {target}")
    print(f"selected n_main={report['selected']['n_main']}")
    print(f"selected n_security_dangerous={report['selected']['n_security_dangerous']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
