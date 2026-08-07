"""Live demo: System C's FULL governed pipeline against real Odoo 19.

Unlike scripts/odoo_demo.py (which calls odoo_handlers directly, no
governance), this script routes real Odoo mutations through the actual
System C pipeline: retrieval -> risk-tiered policy decision -> approval
gate -> runtime execution -> audit trail. It demonstrates the central
claim of ERP Agent OS (CLAUDE.md section 44) against a real ERP, not
just FakeERPAdapter: "recupera una capacidad conocida, valida su
contrato, aplica políticas, ejecuta de forma determinista y verifica
el resultado."

Post-core demonstration (CLAUDE.md section 26), NOT part of the
confirmatory experiment -- see docs/odoo-demo.md for what this proves
and does not prove.

Two calls on purpose:
1. crm.create_opportunity (R1): auto-executes, real Odoo write.
2. crm.update_expected_revenue (R2): the Policy Engine requires
   approval BEFORE touching Odoo -- the first attempt, without
   approval, is proven to leave Odoo untouched (independent re-read),
   then approval is granted and the retry actually writes.
"""

import json
import sys
from pathlib import Path

from erp_agent_os import odoo_handlers
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditEvent, AuditStore
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.odoo_client import Odoo19Adapter
from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_c import SystemC

ROLE = "erp_user"
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "odoo_governed_demo_results.json"
)


def _serialize_audit_event(event: AuditEvent) -> dict:
    return {
        "correlation_id": event.correlation_id,
        "skill_id": event.skill_id,
        "skill_version": event.skill_version,
        "role": event.role,
        "decision": event.decision,
        "risk_score": event.risk_score,
        "reasons": list(event.reasons),
        "idempotency_key": event.idempotency_key,
        "idempotent_replay": event.idempotent_replay,
        "postconditions_met": event.postconditions_met,
        "output": event.output,
    }


def main() -> None:
    erp = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})
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
    retriever = TfidfRetriever(CATALOG)
    audit = AuditStore()
    approval = ApprovalService()
    system = SystemC(erp, runtime, retriever, audit, approval)

    steps = []

    # --- Step 1: R1, auto-executes ---------------------------------
    create_text = "Crea una oportunidad para Odoo Demo Corp por 15000 euros."
    create_proposal = structure_proposal(
        "crm.create_opportunity.new",
        {"customer_name": "Odoo Demo Corp", "expected_revenue": 15000},
        ["customer_name", "expected_revenue"],
        0.9,
    )
    create_result = system.handle(
        "demo-r1", create_text, create_proposal, ROLE, "demo-r1-key"
    )
    opportunity_id = create_result.selected_skill_id and create_result.execution.output
    steps.append(
        {
            "step": "1_create_opportunity_R1",
            "query": create_text,
            "decision": create_result.decision,
            "opportunity_id": opportunity_id,
        }
    )

    if create_result.decision != "ALLOW" or not opportunity_id:
        _fail(steps, "R1 create did not auto-execute as expected")

    before_update = erp.get("crm.lead", opportunity_id)
    steps.append({"step": "1b_odoo_state_after_create", "record": before_update})

    # --- Step 2: R2 WITHOUT approval, must NOT touch Odoo -----------
    update_text = (
        f"Actualiza el importe esperado de la oportunidad {opportunity_id} a 27000."
    )
    update_proposal = structure_proposal(
        "crm.update_expected_revenue.change",
        {"opportunity_id": opportunity_id, "expected_revenue": 27000},
        ["opportunity_id", "expected_revenue"],
        0.9,
    )
    blocked_result = system.handle(
        "demo-r2-blocked", update_text, update_proposal, ROLE, "demo-r2-key-1"
    )
    after_blocked_attempt = erp.get("crm.lead", opportunity_id)
    odoo_untouched = (
        after_blocked_attempt["expected_revenue"] == before_update["expected_revenue"]
    )
    steps.append(
        {
            "step": "2_update_without_approval_R2",
            "query": update_text,
            "decision": blocked_result.decision,
            "odoo_left_untouched": odoo_untouched,
            "odoo_state": after_blocked_attempt,
        }
    )

    if blocked_result.decision != "REQUIRE_APPROVAL" or not odoo_untouched:
        _fail(steps, "R2 update executed against Odoo without approval")

    # --- Step 3: grant approval, retry, must NOW touch Odoo ----------
    approval.grant(
        actor="demo-approver", scope="crm.update_expected_revenue", ttl_seconds=60
    )
    approved_result = system.handle(
        "demo-r2-approved", update_text, update_proposal, ROLE, "demo-r2-key-2"
    )
    after_approved = erp.get("crm.lead", opportunity_id)
    revenue_updated = after_approved["expected_revenue"] == 27000.0
    steps.append(
        {
            "step": "3_update_with_approval_R2",
            "decision": approved_result.decision,
            "odoo_state_after": after_approved,
            "revenue_correctly_updated": revenue_updated,
        }
    )

    if approved_result.decision != "ALLOW" or not revenue_updated:
        _fail(steps, "R2 update with approval did not update Odoo correctly")

    all_ok = odoo_untouched and revenue_updated

    report = {
        "target": (
            "real Odoo 19 (Development branch, demo data), full System C pipeline"
        ),
        "all_checks_passed": all_ok,
        "steps": steps,
        "full_audit_trail": [_serialize_audit_event(e) for e in audit.events()],
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    if not all_ok:
        sys.exit(1)


def _fail(steps: list, message: str) -> None:
    print(json.dumps({"FAILED": message, "steps": steps}, indent=2, default=str))
    sys.exit(1)


if __name__ == "__main__":
    main()
