"""Frozen 12-skill catalog spanning the 8 confirmed ERP families.

Scope per CLAUDE.md §11 (8 families, exactly 12 skills) and §15 (skill
contract). This catalog is the confirmatory skill set: no addition,
removal, or field edit after freeze (CLAUDE.md §19, roadmap P9.1). Family
slugs match `SkillDefinition.module`: crm, contacts, sales, purchasing,
product, inventory, tasks, billing.
"""

from erp_agent_os.dataset import RiskClass
from erp_agent_os.skills import Execution, Permissions, SkillDefinition, SkillState

_ROLE = "erp_user"


def _skill(
    skill_id: str,
    module: str,
    operation: str,
    description: str,
    risk_class: RiskClass,
    required_fields: list[str],
    postconditions: list[str],
) -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        version="1.0.0",
        module=module,
        operation=operation,
        description=description,
        risk_class=risk_class,
        input_schema={"type": "object", "required": required_fields},
        permissions=Permissions(allowed_roles=[_ROLE]),
        preconditions=[],
        execution=Execution(
            handler=f"erp_agent_os.skills.{module}.{operation}",
            timeout_seconds=10,
            max_retries=1,
            idempotent=True,
        ),
        postconditions=postconditions,
        state=SkillState.ACTIVE,
    )


CATALOG: list[SkillDefinition] = [
    _skill(
        "crm.create_opportunity",
        "crm",
        "create",
        "Crea una oportunidad comercial en estado inicial para un cliente "
        "con un importe esperado.",
        RiskClass.R1,
        ["customer_name", "expected_revenue"],
        ["exactly_one_new_opportunity", "opportunity_is_open"],
    ),
    _skill(
        "crm.update_expected_revenue",
        "crm",
        "update",
        "Actualiza el importe esperado de una oportunidad comercial existente.",
        RiskClass.R2,
        ["opportunity_id", "expected_revenue"],
        ["expected_revenue_matches_input", "no_other_fields_changed"],
    ),
    _skill(
        "crm.detect_duplicate_contact",
        "crm",
        "read",
        "Detecta contactos duplicados por nombre o email antes de crear uno nuevo.",
        RiskClass.R0,
        ["customer_name"],
        ["duplicate_report_returned"],
    ),
    _skill(
        "contacts.search_contact",
        "contacts",
        "read",
        "Busca un contacto por nombre, email o teléfono.",
        RiskClass.R0,
        ["query"],
        ["search_results_returned"],
    ),
    _skill(
        "sales.create_quote_draft",
        "sales",
        "create",
        "Crea un presupuesto de venta en estado borrador para un cliente.",
        RiskClass.R1,
        ["customer_name"],
        ["exactly_one_new_quote", "quote_is_draft"],
    ),
    _skill(
        "sales.add_quote_line",
        "sales",
        "update",
        "Añade una línea de producto y cantidad a un presupuesto en borrador.",
        RiskClass.R1,
        ["quote_id", "product_name", "quantity"],
        ["exactly_one_new_line", "quote_still_draft"],
    ),
    _skill(
        "sales.confirm_order",
        "sales",
        "update",
        "Confirma un pedido de venta, moviéndolo de borrador a estado confirmado.",
        RiskClass.R3,
        ["order_id"],
        ["order_is_confirmed", "no_line_changed"],
    ),
    _skill(
        "purchasing.create_purchase_draft",
        "purchasing",
        "create",
        "Crea un pedido de compra en estado borrador para un proveedor.",
        RiskClass.R1,
        ["supplier_name"],
        ["exactly_one_new_purchase_order", "purchase_order_is_draft"],
    ),
    _skill(
        "product.update_field",
        "product",
        "update",
        "Actualiza un campo permitido (precio o descripción) de una ficha de producto.",
        RiskClass.R2,
        ["product_name", "field", "value"],
        ["field_matches_input", "no_other_fields_changed"],
    ),
    _skill(
        "inventory.check_availability",
        "inventory",
        "read",
        "Consulta la disponibilidad de stock de un producto.",
        RiskClass.R0,
        ["product_name"],
        ["availability_returned"],
    ),
    _skill(
        "tasks.create_task",
        "tasks",
        "create",
        "Crea una tarea interna de seguimiento.",
        RiskClass.R1,
        ["title"],
        ["exactly_one_new_task", "task_is_open"],
    ),
    _skill(
        "billing.create_draft_invoice",
        "billing",
        "create",
        "Crea una factura en estado borrador para un cliente a partir de un pedido.",
        RiskClass.R1,
        ["customer_name"],
        ["exactly_one_new_invoice", "invoice_is_draft"],
    ),
]

CATALOG_BY_ID: dict[str, SkillDefinition] = {skill.skill_id: skill for skill in CATALOG}

FAMILIES: tuple[str, ...] = (
    "crm",
    "contacts",
    "sales",
    "purchasing",
    "product",
    "inventory",
    "tasks",
    "billing",
)
