"""24 canonical intents mapped onto the 12-skill catalog.

Scope per CLAUDE.md §11/§17: exactly 24 canonical intents across the 8
families, 2 per skill. Frozen alongside the catalog after freeze (roadmap
P9.1). Each `IntentSpec` carries a Spanish request template with
`{field}` placeholders matching its skill's required fields, and a value
pool per field for deterministic slot-filling.
"""

from dataclasses import dataclass

from erp_agent_os.catalog import CATALOG_BY_ID

_CUSTOMERS = [
    "Acme",
    "Globex",
    "Umbrella",
    "Initech",
    "Soylent Corp",
    "Wayne Enterprises",
    "Stark Industries",
    "Wonka Foods",
    "Tyrell Corp",
    "Cyberdyne",
    "Aperture Labs",
    "Massive Dynamic",
    "Vehement Capital",
    "Hooli",
    "Pied Piper",
    "Vandelay Industries",
    "Gringotts SL",
    "Nakatomi Trading",
    "Oceanic Airlines",
    "Prestige Worldwide",
    "Duff Logistica",
    "Genco Olive",
    "Bluth Company",
    "Sterling Cooper",
]
_PRODUCTS = [
    "Laptop Pro 14",
    "Monitor UltraWide",
    "Silla Ergonomica",
    "Teclado Mecanico",
    "Impresora Laser",
    "Router WiFi6",
    "Webcam 4K",
    "Auriculares Bluetooth",
    "Disco SSD 2TB",
    "Docking Station",
    "Tablet Grafica",
    "Escritorio Elevable",
    "Proyector LED",
    "Escaner Documental",
    "Switch de Red 24p",
    "Bateria Externa",
    "Microfono USB",
    "Lampara de Escritorio",
    "Altavoces Estereo",
    "Adaptador USB-C",
    "Servidor Rack 1U",
    "Camara IP",
    "Panel Acustico",
    "Soporte Monitor",
]
_SUPPLIERS = [
    "Distribuciones Norte",
    "Proveedora Sur",
    "ImportGlobal",
    "MayoristaCentro",
    "Suministros Ibericos",
    "TecnoMayor",
    "Almacenes del Este",
    "Logistica Atlantica",
    "Comercial Levante",
    "Grupo Cantabrico",
    "Distribuidora Meseta",
    "Insumos Baleares",
    "Canarias Supply",
    "Aragon Componentes",
    "Galicia Tecnica",
    "Andalucia Equipos",
    "Rioja Materiales",
    "Navarra Industrial",
    "Asturias Digital",
    "Murcia Provisiones",
    "Extremadura Stock",
    "Castilla Partes",
    "Valencia Import",
    "Euskadi Suministros",
]
_AMOUNTS = [
    "1500",
    "2750",
    "4200",
    "5000",
    "6800",
    "8300",
    "9950",
    "12000",
    "14500",
    "16200",
    "18000",
    "21400",
    "23700",
    "25000",
    "27600",
    "29100",
    "32000",
    "34800",
    "37500",
    "41000",
    "43200",
    "45000",
    "47800",
    "49500",
]
_QUANTITIES = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "12",
    "15",
    "18",
    "20",
    "24",
    "30",
    "36",
    "40",
    "48",
    "50",
    "60",
    "72",
    "80",
    "96",
]
_TITLES = [
    "llamar al cliente",
    "preparar la propuesta",
    "revisar el contrato",
    "enviar el seguimiento",
    "actualizar el CRM",
    "confirmar la reunion",
    "cerrar la incidencia",
    "validar el presupuesto",
    "archivar la oferta",
    "programar la demo",
    "revisar el inventario",
    "contactar al proveedor",
    "preparar el informe",
    "actualizar la ficha",
    "planificar la entrega",
    "revisar la factura",
    "coordinar el envio",
    "documentar el acuerdo",
    "escalar la peticion",
    "verificar el pago",
    "renovar el contrato",
    "ajustar el descuento",
    "notificar al equipo",
    "cerrar el trimestre",
]
_OPPORTUNITY_IDS = [f"OPP-{1001 + i}" for i in range(24)]
_ORDER_IDS = [f"ORD-{2001 + i}" for i in range(24)]
_QUOTE_IDS = [f"QUO-{3001 + i}" for i in range(24)]
_QUERIES = [
    "Acme",
    "acme@example.com",
    "+34 600 111 222",
    "Globex",
    "globex@example.com",
    "+34 600 333 444",
    "Umbrella",
    "umbrella@example.com",
    "Initech",
    "initech@example.com",
    "+34 600 555 666",
    "Tyrell Corp",
    "tyrell@example.com",
    "Cyberdyne",
    "cyberdyne@example.com",
    "+34 600 777 888",
    "Hooli",
    "hooli@example.com",
    "Pied Piper",
    "piedpiper@example.com",
    "+34 600 999 000",
    "Nakatomi Trading",
    "nakatomi@example.com",
    "Bluth Company",
]

_FIELD_POOLS: dict[str, list[str]] = {
    "customer_name": _CUSTOMERS,
    "product_name": _PRODUCTS,
    "supplier_name": _SUPPLIERS,
    "expected_revenue": _AMOUNTS,
    "quantity": _QUANTITIES,
    "title": _TITLES,
    "opportunity_id": _OPPORTUNITY_IDS,
    "order_id": _ORDER_IDS,
    "quote_id": _QUOTE_IDS,
    "query": _QUERIES,
}


@dataclass(frozen=True)
class IntentSpec:
    intent_id: str
    skill_id: str
    family: str
    template: str
    fixed_fields: dict[str, str]  # field -> constant value (e.g. product.field)

    @property
    def required_fields(self) -> list[str]:
        schema = CATALOG_BY_ID[self.skill_id].input_schema
        required: list[str] = schema["required"]
        return required

    def field_pool(self, field: str) -> list[str]:
        if field in self.fixed_fields:
            return [self.fixed_fields[field]]
        return _FIELD_POOLS[field]


INTENTS: list[IntentSpec] = [
    IntentSpec(
        "crm.create_opportunity.new",
        "crm.create_opportunity",
        "crm",
        "Crea una oportunidad para {customer_name} por {expected_revenue} euros.",
        {},
    ),
    IntentSpec(
        "crm.create_opportunity.followup",
        "crm.create_opportunity",
        "crm",
        "Registra un posible negocio de seguimiento con {customer_name} "
        "valorado en {expected_revenue} euros.",
        {},
    ),
    IntentSpec(
        "crm.update_expected_revenue.adjust",
        "crm.update_expected_revenue",
        "crm",
        "Actualiza el importe esperado de la oportunidad {opportunity_id} "
        "a {expected_revenue} euros.",
        {},
    ),
    IntentSpec(
        "crm.update_expected_revenue.correct",
        "crm.update_expected_revenue",
        "crm",
        "Corrige el importe esperado de la oportunidad {opportunity_id} "
        "a {expected_revenue} euros.",
        {},
    ),
    IntentSpec(
        "crm.detect_duplicate_contact.check",
        "crm.detect_duplicate_contact",
        "crm",
        "Comprueba si {customer_name} ya existe como contacto antes de crearlo.",
        {},
    ),
    IntentSpec(
        "crm.detect_duplicate_contact.merge_check",
        "crm.detect_duplicate_contact",
        "crm",
        "Revisa si hay contactos duplicados para {customer_name}.",
        {},
    ),
    IntentSpec(
        "contacts.search_contact.by_name",
        "contacts.search_contact",
        "contacts",
        "Busca el contacto {query}.",
        {},
    ),
    IntentSpec(
        "contacts.search_contact.lookup",
        "contacts.search_contact",
        "contacts",
        "Encuentra la ficha de contacto de {query}.",
        {},
    ),
    IntentSpec(
        "sales.create_quote_draft.new",
        "sales.create_quote_draft",
        "sales",
        "Crea un presupuesto en borrador para {customer_name}.",
        {},
    ),
    IntentSpec(
        "sales.create_quote_draft.for_lead",
        "sales.create_quote_draft",
        "sales",
        "Prepara un presupuesto inicial para el cliente {customer_name}.",
        {},
    ),
    IntentSpec(
        "sales.add_quote_line.add_product",
        "sales.add_quote_line",
        "sales",
        "Añade {quantity} unidades de {product_name} al presupuesto {quote_id}.",
        {},
    ),
    IntentSpec(
        "sales.add_quote_line.add_service",
        "sales.add_quote_line",
        "sales",
        "Incluye {quantity} de {product_name} en el presupuesto {quote_id}.",
        {},
    ),
    IntentSpec(
        "sales.confirm_order.validate",
        "sales.confirm_order",
        "sales",
        "Valida el pedido {order_id}.",
        {},
    ),
    IntentSpec(
        "sales.confirm_order.finalize",
        "sales.confirm_order",
        "sales",
        "Confirma definitivamente el pedido {order_id}.",
        {},
    ),
    IntentSpec(
        "purchasing.create_purchase_draft.new",
        "purchasing.create_purchase_draft",
        "purchasing",
        "Crea un pedido de compra en borrador para el proveedor {supplier_name}.",
        {},
    ),
    IntentSpec(
        "purchasing.create_purchase_draft.restock",
        "purchasing.create_purchase_draft",
        "purchasing",
        "Genera una orden de compra a {supplier_name} para reponer stock.",
        {},
    ),
    IntentSpec(
        "product.update_field.price",
        "product.update_field",
        "product",
        "Actualiza el {field} del producto {product_name} a {value}.",
        {"field": "precio", "value": "99.90"},
    ),
    IntentSpec(
        "product.update_field.description",
        "product.update_field",
        "product",
        "Cambia el {field} de la ficha de {product_name} a {value}.",
        {"field": "descripcion", "value": "Nueva descripción del producto"},
    ),
    IntentSpec(
        "inventory.check_availability.single",
        "inventory.check_availability",
        "inventory",
        "Consulta la disponibilidad de {product_name}.",
        {},
    ),
    IntentSpec(
        "inventory.check_availability.reorder",
        "inventory.check_availability",
        "inventory",
        "¿Cuánto stock queda de {product_name}?",
        {},
    ),
    IntentSpec(
        "tasks.create_task.followup",
        "tasks.create_task",
        "tasks",
        "Crea una tarea para {title}.",
        {},
    ),
    IntentSpec(
        "tasks.create_task.reminder",
        "tasks.create_task",
        "tasks",
        "Recuérdame {title}.",
        {},
    ),
    IntentSpec(
        "billing.create_draft_invoice.from_order",
        "billing.create_draft_invoice",
        "billing",
        "Crea una factura en borrador para {customer_name}.",
        {},
    ),
    IntentSpec(
        "billing.create_draft_invoice.manual",
        "billing.create_draft_invoice",
        "billing",
        "Genera una factura borrador a nombre de {customer_name}.",
        {},
    ),
]

INTENTS_BY_ID: dict[str, IntentSpec] = {intent.intent_id: intent for intent in INTENTS}
