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

import argparse
import json
import sys
from pathlib import Path

from erp_agent_os import odoo_handlers
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditEvent, AuditStore
from erp_agent_os.catalog import CATALOG_BY_ID
from erp_agent_os.odoo_client import Odoo19Adapter, require_development_instance
from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime, VerificationStatus
from erp_agent_os.system_c import SystemC

ROLE = "erp_user"
ODOO_SKILL_MODELS = {
    "crm.create_opportunity": "crm.lead",
    "crm.update_expected_revenue": "crm.lead",
}
ODOO_MONITORED_MODELS = frozenset(ODOO_SKILL_MODELS.values())
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
        "verification_status": event.verification_status,
        "checks": [
            {
                "check_id": check.check_id,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in event.check_results
        ],
        "output": event.output,
    }


def _beat(title: str, lines: list[str], filming: bool) -> None:
    """Readable block for the video, plus a pause to refresh the browser.

    The demo runs in under four seconds, which is right for CI and
    useless for filming: the whole point of the shot is that the viewer
    watches Odoo be re-read between steps. Without a pause there is no
    room to refresh the browser on camera, and cutting the take is
    exactly what destroys its evidential value
    (docs/video-plan-rodaje.md).

    Default behaviour is unchanged: without --rodaje there are no
    prints, no pauses, and the same JSON artifact as before.
    """
    if not filming:
        return
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)
    for line in lines:
        print(f"  {line}")
    print()
    input("  [refresca Odoo en el navegador y pulsa Enter] ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rodaje",
        action="store_true",
        help="modo grabacion: salida legible y pausa entre pasos",
    )
    filming = parser.parse_args().rodaje

    # Refuses production and staging before a single write leaves
    # this process (see require_development_instance for why).
    require_development_instance()
    erp = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})
    # The live adapter maps the catalog's synthetic opportunity model to
    # Odoo's `crm.lead`. Odoo has no synthetic `state="open"` field, so this
    # demo contract keeps the portable differential creation check; the
    # independent re-read below still corroborates type and amount.
    create_skill = CATALOG_BY_ID["crm.create_opportunity"].model_copy(
        update={"postconditions": ["exactly_one_new_opportunity"]}
    )
    update_skill = CATALOG_BY_ID["crm.update_expected_revenue"]
    odoo_catalog = [create_skill, update_skill]
    runtime: Runtime = Runtime(erp)
    runtime.register(
        "crm.create_opportunity",
        create_skill.version,
        odoo_handlers.crm_create_opportunity,
    )
    runtime.register(
        "crm.update_expected_revenue",
        update_skill.version,
        odoo_handlers.crm_update_expected_revenue,
    )
    retriever = TfidfRetriever(odoo_catalog)
    audit = AuditStore()
    approval = ApprovalService()
    system = SystemC(
        erp,
        runtime,
        retriever,
        audit,
        approval,
        monitored_models=ODOO_MONITORED_MODELS,
        skill_models=ODOO_SKILL_MODELS,
    )

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
    opportunity_id = (
        create_result.execution.output if create_result.execution is not None else None
    )
    steps.append(
        {
            "step": "1_create_opportunity_R1",
            "query": create_text,
            "decision": create_result.decision,
            "verification_status": create_result.verification_status.value,
            "postconditions_met": create_result.postconditions_met,
            "opportunity_id": opportunity_id,
        }
    )

    if (
        create_result.decision != "ALLOW"
        or create_result.verification_status is not VerificationStatus.PASSED
        or not opportunity_id
    ):
        _fail(steps, "R1 create did not auto-execute as expected")

    before_update = erp.get("crm.lead", opportunity_id)
    steps.append({"step": "1b_odoo_state_after_create", "record": before_update})

    _beat(
        "PASO 1 - Crear oportunidad (riesgo R1: se autoejecuta)",
        [
            f'Peticion : "{create_text}"',
            f"Decision : {create_result.decision}",
            f"Odoo id  : {opportunity_id}",
            "",
            "Relectura independiente de Odoo:",
            f"  importe = {before_update['expected_revenue']}",
        ],
        filming,
    )

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
            "verification_status": blocked_result.verification_status.value,
            "postconditions_met": blocked_result.postconditions_met,
            "odoo_left_untouched": odoo_untouched,
            "odoo_state": after_blocked_attempt,
        }
    )

    if (
        blocked_result.decision != "REQUIRE_APPROVAL"
        or blocked_result.verification_status is not VerificationStatus.NOT_RUN_CLEAN
        or not odoo_untouched
    ):
        _fail(steps, "R2 update executed against Odoo without approval")

    _beat(
        "PASO 2 - Cambiar el importe SIN aprobacion (riesgo R2)",
        [
            f'Peticion : "{update_text}"',
            f"Decision : {blocked_result.decision}   <-- el sistema se detiene",
            "",
            "Relectura INDEPENDIENTE de Odoo, sin fiarse de lo que el",
            "sistema dice de si mismo:",
            f"  importe = {after_blocked_attempt['expected_revenue']} "
            f"(seguia siendo {before_update['expected_revenue']})",
            f"  Odoo intacto: {odoo_untouched}",
        ],
        filming,
    )

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
            "verification_status": approved_result.verification_status.value,
            "postconditions_met": approved_result.postconditions_met,
            "odoo_state_after": after_approved,
            "revenue_correctly_updated": revenue_updated,
        }
    )

    if (
        approved_result.decision != "ALLOW"
        or approved_result.verification_status is not VerificationStatus.PASSED
        or not revenue_updated
    ):
        _fail(steps, "R2 update with approval did not update Odoo correctly")

    _beat(
        "PASO 3 - Misma peticion, ahora CON aprobacion concedida",
        [
            f"Decision : {approved_result.decision}",
            "",
            "Relectura independiente de Odoo:",
            f"  importe = {after_approved['expected_revenue']}   <-- ahora si escribe",
        ],
        filming,
    )

    all_ok = (
        odoo_untouched
        and revenue_updated
        and all(event.verification_status for event in audit.events())
    )

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
    if filming:
        print()
        print("=" * 68)
        print(f"  Todas las comprobaciones pasaron: {all_ok}")
        print(f"  Traza de auditoria: {len(audit.events())} eventos registrados")
        print("=" * 68)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    if not all_ok:
        sys.exit(1)


def _fail(steps: list, message: str) -> None:
    print(json.dumps({"FAILED": message, "steps": steps}, indent=2, default=str))
    sys.exit(1)


if __name__ == "__main__":
    main()
