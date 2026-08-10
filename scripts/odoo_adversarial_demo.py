"""Adversarial cases through the governed pipeline, against real Odoo 19.

H4 (false allow) is measured on `FakeERPAdapter` in the confirmatory
experiment. This script re-runs the *adversarial* subset of the frozen
test benchmark through the same System C pipeline pointed at a real
Odoo 19 instance, so the safety claim is demonstrated where a mistake
would have real consequences -- a real record created, a real amount
changed -- rather than only in a simulator.

Scope, stated up front: only the 15 adversarial cases whose expected
skill is one of the two mapped to real Odoo models
(`crm.create_opportunity`, `crm.update_expected_revenue`). The other 81
target skills with no Odoo handler. This is a subset by construction,
not a full replication of H4, and must not be reported as one.

For every case the script records, from an **independent** Odoo read
(not the system's own reported decision):
  - the policy decision System C reached;
  - whether the real Odoo record count changed;
  - for DENY/REQUIRE_APPROVAL cases, whether Odoo was left untouched --
    which is the property that actually matters: a blocked dangerous
    request must not have written anything.
"""

import json
import sys
from pathlib import Path

from erp_agent_os import odoo_handlers
from erp_agent_os.audit import AuditStore
from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.dataset import CaseLabel, DatasetSplit
from erp_agent_os.odoo_client import Odoo19Adapter
from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_c import SystemC

ROLE = "erp_user"
ODOO_MAPPED_SKILLS = {"crm.create_opportunity", "crm.update_expected_revenue"}
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "odoo_adversarial_results.json"
)


def _build_system(erp: Odoo19Adapter) -> tuple[SystemC, AuditStore]:
    runtime: Runtime = Runtime(erp)
    runtime.register(
        "crm.create_opportunity",
        CATALOG_BY_ID["crm.create_opportunity"].version,
        odoo_handlers.crm_create_opportunity,
    )
    runtime.register(
        "crm.update_expected_revenue",
        CATALOG_BY_ID["crm.update_expected_revenue"].version,
        odoo_handlers.crm_update_expected_revenue,
    )
    audit = AuditStore()
    return SystemC(erp, runtime, TfidfRetriever(CATALOG), audit), audit


def main() -> None:
    erp = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})

    cases = [
        c
        for c in generate_cases()
        if c.split is DatasetSplit.FINAL_TEST
        and CaseLabel.ADVERSARIAL in c.labels
        and c.expected_skill in ODOO_MAPPED_SKILLS
    ]
    if not cases:
        print("no adversarial cases map to the Odoo-backed skills", file=sys.stderr)
        raise SystemExit(1)

    results = []
    for case in cases:
        system, audit = _build_system(erp)
        required = CATALOG_BY_ID[case.expected_skill].input_schema["required"]
        proposal = structure_proposal(
            case.canonical_intent, case.expected_arguments, required, confidence=0.9
        )

        before = erp.list("crm.lead", limit=500)
        result = system.handle(
            case.request_id, case.request_text, proposal, ROLE, case.request_id
        )
        after = erp.list("crm.lead", limit=500)

        executed = result.decision == "ALLOW"
        odoo_changed = before != after
        blocked = result.decision in ("DENY", "REQUIRE_APPROVAL", "ABSTAIN", "CLARIFY")

        results.append(
            {
                "request_id": case.request_id,
                "error_type": case.error_type,
                "request_text": case.request_text,
                "expected_decision": case.expected_decision.value,
                "actual_decision": result.decision,
                "reasons": list(result.reasons),
                "odoo_records_changed": odoo_changed,
                # The property that matters: a blocked dangerous request
                # must leave the real ERP byte-identical.
                "blocked_and_odoo_untouched": blocked and not odoo_changed,
                "executed": executed,
                "audited": len(audit.events()) + len(audit.abstentions()) > 0,
            }
        )

    blocked_cases = [r for r in results if r["actual_decision"] != "ALLOW"]
    unsafe = [r for r in blocked_cases if r["odoo_records_changed"]]

    report = {
        "target": "real Odoo 19 (Development branch, demo data), System C pipeline",
        "scope": (
            "adversarial subset of the frozen test split whose expected skill "
            "is one of the 2 mapped to real Odoo models -- a subset, NOT a "
            "replication of the H4 result measured on FakeERPAdapter"
        ),
        "n_cases": len(results),
        "n_blocked": len(blocked_cases),
        "n_executed": len(results) - len(blocked_cases),
        "blocked_cases_that_still_wrote_to_odoo": len(unsafe),
        "every_blocked_case_left_odoo_untouched": not unsafe,
        "every_case_audited": all(r["audited"] for r in results),
        "cases": results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if unsafe:
        sys.exit(1)


if __name__ == "__main__":
    main()
