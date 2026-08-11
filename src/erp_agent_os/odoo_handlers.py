"""Handlers for a minimal subset of catalog skills against real Odoo 19.

Scope: post-core demonstration only (CLAUDE.md §26), NOT part of the
confirmatory core or the 12-skill catalog's `handlers.py` (which targets
`FakeERPAdapter`'s synthetic model names). This module exists to show
the same skill contract shape -- validated arguments in, a real ERP
mutation, a verifiable postcondition -- executing against a real Odoo
instance instead of the in-memory fake.

Only two skills are mapped, deliberately: `crm.create_opportunity` and
`crm.update_expected_revenue`, onto Odoo 19's real `crm.lead` model
(Odoo represents both leads and opportunities in one model,
distinguished by `type`). This is not a claim that all 12 catalog
skills were ported -- CLAUDE.md §26 lists `res.partner`, `crm.lead`,
`product.product`, `sale.order`, `sale.order.line`, `project.task` and
inventory queries as the *initial* model set for exactly this reason:
full coverage is future work, not required for the confirmatory
experiment.
"""

from typing import Any

from erp_agent_os.odoo_client import Odoo19Adapter

Args = dict[str, Any]

# Real Odoo 19 field names, confirmed by reading demo records on a live
# Development-branch instance before writing this module.
CRM_LEAD_FIELDS = frozenset({"name", "partner_name", "expected_revenue", "type"})


def crm_create_opportunity(erp: Odoo19Adapter, args: Args) -> str:
    return erp.create(
        "crm.lead",
        {
            "name": f"Oportunidad: {args['customer_name']}",
            "partner_name": args["customer_name"],
            "expected_revenue": args["expected_revenue"],
            "type": "opportunity",
        },
    )


def crm_update_expected_revenue(erp: Odoo19Adapter, args: Args) -> str:
    erp.update(
        "crm.lead",
        args["opportunity_id"],
        {"expected_revenue": args["expected_revenue"]},
    )
    return args["opportunity_id"]


def opportunity_created_correctly(
    erp: Odoo19Adapter, opportunity_id: str, expected_revenue: float
) -> bool:
    """Postcondition check, same spirit as postconditions.py's checks:
    the record exists, is typed as an opportunity, and the amount the
    skill was asked to set is exactly what landed in Odoo -- not "a
    200 OK", an independently re-read value."""
    record = erp.get("crm.lead", opportunity_id)
    return record["type"] == "opportunity" and record["expected_revenue"] == float(
        expected_revenue
    )
