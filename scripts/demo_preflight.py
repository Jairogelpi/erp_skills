#!/usr/bin/env python
"""Pre-flight for the comparative product demo.

Run this before presenting. It checks the things that would fail in
front of an audience, and it distinguishes two very different failures:

* the **confirmatory evidence** being unreadable, which is fatal --
  without it the screen would have to show invented statistics, and this
  script exits non-zero rather than let that happen;
* **live Odoo** being unavailable, which is not fatal -- the demo falls
  back to the reproducible FakeERP backend and says so.

    uv run python scripts/demo_preflight.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from erp_agent_os import demo_results
from erp_agent_os.demo_service import SCENARIOS, DemoService

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def _line(status: str, label: str, detail: str = "") -> None:
    print(f"  {status} {label}" + (f" — {detail}" if detail else ""))


def check_evidence() -> list[str]:
    """Fatal checks: the numbers on screen must come from real artifacts."""
    errors: list[str] = []
    try:
        bundle = demo_results.load_evidence()
    except demo_results.EvidenceUnavailableError as exc:
        _line(FAIL, "Confirmatory report", str(exc))
        return [str(exc)]

    _line(PASS, "Confirmatory report", demo_results.REPORT_PATH.name)
    _line(PASS, "Protocol", f"{bundle.protocol_tag} ({bundle.protocol_version})")
    _line(PASS, "Campaign state", bundle.campaign_state)
    _line(PASS, "Evidence rows", f"{bundle.observation_count:,} observations")

    if bundle.campaign_state != "RUN_COMPLETED":
        errors.append(f"campaign is {bundle.campaign_state}, not RUN_COMPLETED")

    supported = sum(1 for c in bundle.cards if c.supported)
    _line(
        PASS,
        "Hypothesis cards",
        f"{len(bundle.cards)} loaded, {supported} supported, "
        f"{len(bundle.cards) - supported} not supported",
    )
    # A demo where every hypothesis came back positive would mean the
    # negative results (H1b, H4, H5) had been dropped somewhere between
    # the report and the screen.
    if supported == len(bundle.cards):
        errors.append("no negative results present — the report's own are missing")

    if bundle.confinement:
        _line(
            PASS,
            "Confinement stress test",
            f"{bundle.confinement['unauthorized_mutations']}"
            f"/{bundle.confinement['total_attempts']} unauthorized mutations",
        )
    else:
        _line(WARN, "Confinement stress test", "artifact absent, panel will be hidden")
    return errors


def check_systems() -> list[str]:
    """Boots all three architectures and runs the headline scene."""
    errors: list[str] = []
    service = DemoService()
    try:
        run = service.run("approval")
    except Exception as exc:  # noqa: BLE001 - see below
        # Blind on purpose, and only here: a preflight whose whole job is
        # to report what would break must survive *any* boot failure and
        # name it, rather than crash with a traceback minutes before a
        # presentation. The exception type is printed, so nothing is
        # swallowed.
        _line(FAIL, "System boot", f"{type(exc).__name__}: {exc}")
        return [str(exc)]

    for name in ("A", "B", "C"):
        result = run.results[name]
        _line(PASS, f"System {name} boot", result.label)

    governed = run.results["C"]
    if governed.policy_decision != "REQUIRE_APPROVAL":
        errors.append(
            f"approval scene decided {governed.policy_decision}, expected "
            "REQUIRE_APPROVAL"
        )
    elif governed.erp.changed:
        errors.append("approval scene mutated the ERP before approval")
    else:
        _line(PASS, "Approval gate", "R2 held, ERP unchanged on independent re-read")

    # Positive control: the gate must be a gate, not a wall. If approving
    # did not let the write through, "nothing was mutated" would be
    # vacuous rather than a demonstration of control.
    service.approve(run.request_id, "preflight")
    after = service.rerun(run.request_id)
    if after.results["C"].policy_decision == "ALLOW" and after.results["C"].erp.changed:
        _line(PASS, "Positive control", "approved request writes and verifies")
    else:
        errors.append("approved request did not execute — the gate is a wall")

    if run.results["A"].erp.changed and run.results["B"].erp.changed:
        _line(PASS, "FakeERP writable", "A and B mutated the seeded record")
    else:
        errors.append("ungoverned systems did not write — FakeERP may be read-only")

    if governed.audit.facts:
        _line(
            PASS, "Audit available", f"{len(governed.audit.facts)} reconstruction facts"
        )
    else:
        errors.append("audit reconstruction produced no facts")

    _line(PASS, "Scenario presets", ", ".join(SCENARIOS))
    return errors


def check_skill_studio() -> list[str]:
    """Fatal checks: CU-02's registry/sandbox/lifecycle machinery, exercised
    exactly the way the video's "propose a new skill" scene does, entirely
    against in-memory state -- no Odoo, no LLM key, needed for any of it."""
    errors: list[str] = []
    from erp_agent_os.skill_admin import (
        SkillAdmin,
        SkillAdminError,
        synthesize_sample_arguments,
    )

    draft: dict[str, Any] = {
        "skill_id": "preflight.check_skill",
        "version": "1.0.0",
        "module": "preflight",
        "operation": "create",
        "description": "Preflight smoke skill",
        "risk_class": "R1",
        "input_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
        "permissions": {"allowed_roles": ["erp_user"]},
        "preconditions": [],
        "execution": {
            "handler": "demo_proposals.generic_create",
            "timeout_seconds": 10,
            "max_retries": 1,
            "idempotent": True,
        },
        "postconditions": ["exactly_one_new_record"],
        "approval_required_when": [],
        "state": "DRAFT",
    }

    admin = SkillAdmin()
    try:
        described = admin.propose(
            draft, synthesize_sample_arguments(draft["input_schema"])
        )
    except SkillAdminError as exc:
        _line(FAIL, "Proposal creation", str(exc))
        return [str(exc)]
    _line(PASS, "Skill registry", "seeded and reachable")
    _line(PASS, "Proposal creation", "validated and sandbox-tested")
    _line(PASS, "Validation pipeline", "schema + sandbox postconditions checked")

    if described["state"] != "TESTED":
        errors.append(f"proposal reached {described['state']}, expected TESTED")
    else:
        _line(PASS, "DRAFT cannot execute", "proposal stops at TESTED, not ACTIVE")

    try:
        admin.approve(draft["skill_id"], draft["version"], approver="")
        errors.append("approval succeeded with no named approver")
    except SkillAdminError:
        _line(PASS, "Human approval required", "empty approver is rejected")

    approved = admin.approve(draft["skill_id"], draft["version"], approver="preflight")
    if approved["state"] == "ACTIVE":
        _line(PASS, "Approved proposal can become ACTIVE", approved["state"])
    else:
        errors.append(f"approved proposal ended at {approved['state']}, not ACTIVE")

    if approved["history"]:
        _line(
            PASS, "Version history recorded", f"{len(approved['history'])} transitions"
        )
    else:
        errors.append("no transition history recorded for the approved proposal")

    return errors


def check_odoo() -> bool:
    """Non-fatal. Returns True when live mode is usable."""
    url = os.environ.get("ODOO_URL", "")
    if not url:
        _line(WARN, "Odoo live mode", "ODOO_URL unset")
        return False
    from erp_agent_os.odoo_client import (
        NotADevelopmentInstanceError,
        require_development_instance,
    )

    try:
        require_development_instance(url)
    except NotADevelopmentInstanceError as exc:
        # The specific type, not a bare Exception: this warning must mean
        # "the configured host is production or staging", which is the
        # one thing the guard exists to catch. Any other failure should
        # surface as itself.
        _line(WARN, "Odoo development host", str(exc))
        return False
    _line(PASS, "Odoo development host", url)

    if not os.environ.get("ODOO_API_KEY"):
        _line(WARN, "Odoo credentials", "ODOO_API_KEY unset")
        return False
    _line(PASS, "Odoo credentials", "present")

    # Read-only: proves CRM is installed and reachable with these
    # credentials without writing anything. The write-side proof
    # (positive write control + independent re-read) is
    # scripts/odoo_governed_demo.py, run once before recording -- not
    # duplicated here, so preflight does not create demo records on
    # every run.
    from erp_agent_os.odoo_client import Odoo19Adapter
    from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS

    try:
        Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS}).list(
            "crm.lead", limit=1
        )
    except Exception as exc:  # noqa: BLE001 - see check_systems' own rule
        _line(WARN, "CRM permissions", f"{type(exc).__name__}: {exc}")
        return False
    _line(PASS, "CRM permissions", "crm.lead readable with these credentials")
    _line(
        PASS,
        "Positive write control / independent re-read",
        "run scripts/odoo_governed_demo.py once before recording",
    )
    return True


def main() -> int:
    print("\nERP Agent OS — demo preflight\n")
    print(" Confirmatory evidence")
    errors = check_evidence()
    print("\n Systems")
    errors += check_systems()
    print("\n Skill Studio")
    errors += check_skill_studio()
    print("\n Live Odoo (optional)")
    odoo_ready = check_odoo()

    print()
    if errors:
        print("DEMO NOT READY")
        for error in errors:
            print(f"  - {error}")
        return 1
    if odoo_ready:
        print("DEMO READY")
    else:
        print("DEMO READY — FAKE ERP MODE")
        print("  Live Odoo unavailable; the comparative backend is unaffected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
