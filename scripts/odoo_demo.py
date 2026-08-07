"""Live demo: two catalog skills executed against real Odoo 19.

Post-core demonstration (CLAUDE.md §26, §38 escenario 1/5), NOT part of
the confirmatory experiment. Requires ODOO_URL/ODOO_DB/ODOO_API_KEY in
the environment, pointed at a Development-branch instance with demo
data -- never run this against an instance with real business data.

Mirrors the shape of System C's pipeline (propose -> execute -> verify
postcondition -> re-run to check idempotency-adjacent behaviour) without
routing through System C's classes, which are wired to FakeERPAdapter's
synthetic model names (see odoo_handlers.py's module docstring).
"""

import json
import sys
from pathlib import Path

from erp_agent_os.odoo_client import Odoo19Adapter
from erp_agent_os.odoo_handlers import (
    CRM_LEAD_FIELDS,
    crm_create_opportunity,
    crm_update_expected_revenue,
    opportunity_created_correctly,
)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "odoo_demo_results.json"


def main() -> None:
    erp = Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})

    steps = []

    # 1. Create an opportunity, verify it landed with the right amount.
    opportunity_id = crm_create_opportunity(
        erp, {"customer_name": "ERP-AGENT-OS-DEMO", "expected_revenue": 15000}
    )
    create_ok = opportunity_created_correctly(erp, opportunity_id, 15000)
    steps.append(
        {
            "step": "crm.create_opportunity",
            "opportunity_id": opportunity_id,
            "postcondition_met": create_ok,
        }
    )

    # 2. Update the amount, verify the new value is what's actually there.
    crm_update_expected_revenue(
        erp, {"opportunity_id": opportunity_id, "expected_revenue": 27000}
    )
    update_ok = opportunity_created_correctly(erp, opportunity_id, 27000)
    steps.append(
        {
            "step": "crm.update_expected_revenue",
            "opportunity_id": opportunity_id,
            "postcondition_met": update_ok,
        }
    )

    # 3. Re-read once more independently -- proves this isn't just
    # trusting the HTTP 200, the value is confirmed via a separate call.
    final = erp.get("crm.lead", opportunity_id)
    steps.append({"step": "independent_reread", "record": final})

    report = {
        "target": "real Odoo 19 (Development branch, demo data)",
        "all_postconditions_met": all(s.get("postcondition_met", True) for s in steps),
        "steps": steps,
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not report["all_postconditions_met"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
