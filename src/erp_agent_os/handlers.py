"""Handlers for the 12 catalog skills, wired to `FakeERPAdapter`.

Scope per roadmap P8.1 groundwork: one function per skill, matching its
`Execution.handler` dotted path and postconditions. FakeERP model names
are chosen per skill (documented per handler); registering these against
a `Runtime` is what makes `SystemC` actually execute a request instead of
raising `UnregisteredHandlerError`.

Simplification, disclosed: `sales.add_quote_line` records only the most
recently added line on the quote record (no line-item array) — sufficient
to demonstrate wiring; a real quote-lines collection is future work.
"""

from typing import Any

from erp_agent_os.adapters import FakeERPAdapter

Args = dict[str, Any]

# skill_id -> FakeERP model name this handler reads/writes.
SKILL_MODELS: dict[str, str] = {
    "crm.create_opportunity": "crm.opportunity",
    "crm.update_expected_revenue": "crm.opportunity",
    "crm.detect_duplicate_contact": "contacts.contact",
    "contacts.search_contact": "contacts.contact",
    "sales.create_quote_draft": "sales.quote",
    "sales.add_quote_line": "sales.quote",
    "sales.confirm_order": "sales.order",
    "purchasing.create_purchase_draft": "purchasing.order",
    "product.update_field": "product.product",
    "inventory.check_availability": "product.product",
    "tasks.create_task": "tasks.task",
    "billing.create_draft_invoice": "billing.invoice",
}


def crm_create_opportunity(erp: FakeERPAdapter, args: Args) -> str:
    return erp.create(
        "crm.opportunity",
        {
            "customer_name": args["customer_name"],
            "expected_revenue": args["expected_revenue"],
            "state": "open",
        },
    )


def crm_update_expected_revenue(erp: FakeERPAdapter, args: Args) -> str:
    erp.update(
        "crm.opportunity",
        args["opportunity_id"],
        {"expected_revenue": args["expected_revenue"]},
    )
    return args["opportunity_id"]


def crm_detect_duplicate_contact(erp: FakeERPAdapter, args: Args) -> Args:
    matches = [
        record_id
        for record_id, record in erp.list("contacts.contact").items()
        if record.get("customer_name") == args["customer_name"]
    ]
    return {"duplicates_found": len(matches), "matching_ids": matches}


def contacts_search_contact(erp: FakeERPAdapter, args: Args) -> Args:
    query = args["query"]
    matches = [
        record_id
        for record_id, record in erp.list("contacts.contact").items()
        if query
        in {record.get("customer_name"), record.get("email"), record.get("phone")}
    ]
    return {"results": matches}


def sales_create_quote_draft(erp: FakeERPAdapter, args: Args) -> str:
    return erp.create(
        "sales.quote", {"customer_name": args["customer_name"], "state": "draft"}
    )


def sales_add_quote_line(erp: FakeERPAdapter, args: Args) -> str:
    erp.update(
        "sales.quote",
        args["quote_id"],
        {
            "last_line_product": args["product_name"],
            "last_line_quantity": args["quantity"],
        },
    )
    return args["quote_id"]


def sales_confirm_order(erp: FakeERPAdapter, args: Args) -> str:
    erp.update("sales.order", args["order_id"], {"state": "confirmed"})
    return args["order_id"]


def purchasing_create_purchase_draft(erp: FakeERPAdapter, args: Args) -> str:
    return erp.create(
        "purchasing.order", {"supplier_name": args["supplier_name"], "state": "draft"}
    )


def product_update_field(erp: FakeERPAdapter, args: Args) -> str:
    erp.update("product.product", args["product_name"], {args["field"]: args["value"]})
    return args["product_name"]


def inventory_check_availability(erp: FakeERPAdapter, args: Args) -> Args:
    record = erp.get("product.product", args["product_name"])
    return {"available_units": record.get("stock", 0)}


def tasks_create_task(erp: FakeERPAdapter, args: Args) -> str:
    return erp.create("tasks.task", {"title": args["title"], "state": "open"})


def billing_create_draft_invoice(erp: FakeERPAdapter, args: Args) -> str:
    return erp.create(
        "billing.invoice", {"customer_name": args["customer_name"], "state": "draft"}
    )


HANDLERS = {
    "crm.create_opportunity": crm_create_opportunity,
    "crm.update_expected_revenue": crm_update_expected_revenue,
    "crm.detect_duplicate_contact": crm_detect_duplicate_contact,
    "contacts.search_contact": contacts_search_contact,
    "sales.create_quote_draft": sales_create_quote_draft,
    "sales.add_quote_line": sales_add_quote_line,
    "sales.confirm_order": sales_confirm_order,
    "purchasing.create_purchase_draft": purchasing_create_purchase_draft,
    "product.update_field": product_update_field,
    "inventory.check_availability": inventory_check_availability,
    "tasks.create_task": tasks_create_task,
    "billing.create_draft_invoice": billing_create_draft_invoice,
}
