"""Prepara el estado de Odoo para el plano 1 del vídeo (docs/video-plan-rodaje.md).

El plano 1 muestra **lo que está en juego**: un registro de negocio real
con un importe, y ese mismo registro con otro importe. No afirma que un
agente lo cambiara mal — esa afirmación se hace en el plano 2, donde el
agente sin gobierno ejecuta de verdad y se ve.

Esa distinción importa: el plano 1 es un plano de contexto, y presentarlo
como «mira lo que hizo la IA» sería una recreación disfrazada de prueba,
justo lo que las notas de producción prohíben.

Uso:

    # antes de rodar, con la rama de desarrollo levantada
    uv run python scripts/stage_video_shot1.py --before
    #   ... se graba el plano del importe inicial ...
    uv run python scripts/stage_video_shot1.py --after
    #   ... se graba el plano del importe cambiado ...

Escribe SOLO en una rama de desarrollo: `require_development_instance()`
rechaza producción y staging antes de tocar nada.
"""

import argparse
import sys

from erp_agent_os.odoo_client import Odoo19Adapter, require_development_instance
from erp_agent_os.odoo_handlers import CRM_LEAD_FIELDS

# Cliente ficticio y reconocible en pantalla: nadie lo confundirá con un
# cliente real de la empresa si el vídeo se publica.
CUSTOMER = "Hoteles Camino (DEMO)"
AMOUNT_BEFORE = 15000
AMOUNT_AFTER = 27600


def _adapter() -> Odoo19Adapter:
    url = require_development_instance()
    print(f"instancia: {url}")
    return Odoo19Adapter(allowed_fields={"crm.lead": CRM_LEAD_FIELDS})


def _find(erp: Odoo19Adapter) -> tuple[str, dict] | None:
    for record_id, record in erp.list("crm.lead", limit=500).items():
        if record.get("partner_name") == CUSTOMER:
            return record_id, record
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--before", action="store_true", help="crea el registro inicial")
    group.add_argument("--after", action="store_true", help="cambia el importe")
    group.add_argument("--status", action="store_true", help="solo consulta")
    args = parser.parse_args()

    erp = _adapter()
    existing = _find(erp)

    if args.status:
        if existing:
            record_id, record = existing
            print(
                f"id={record_id}  {CUSTOMER}  importe={record.get('expected_revenue')}"
            )
        else:
            print(f"no existe ningun registro de {CUSTOMER!r}")
        return

    if args.before:
        if existing:
            record_id, _ = existing
            erp.update("crm.lead", record_id, {"expected_revenue": AMOUNT_BEFORE})
            print(f"id={record_id} reiniciado a {AMOUNT_BEFORE}")
        else:
            record_id = erp.create(
                "crm.lead",
                {
                    "name": "Renovacion contrato anual",
                    "partner_name": CUSTOMER,
                    "expected_revenue": AMOUNT_BEFORE,
                    "type": "opportunity",
                },
            )
            print(f"id={record_id} creado con importe {AMOUNT_BEFORE}")
        print("\n-> abre la oportunidad en Odoo y graba el plano del importe inicial")
        return

    if not existing:
        print(
            "no hay registro que cambiar: ejecuta primero --before",
            file=sys.stderr,
        )
        raise SystemExit(1)
    record_id, _ = existing
    erp.update("crm.lead", record_id, {"expected_revenue": AMOUNT_AFTER})
    after = erp.get("crm.lead", record_id)
    # Relectura independiente, igual que en las demos: no basta con que
    # la escritura devuelva OK.
    print(f"id={record_id} importe ahora {after.get('expected_revenue')}")
    print("\n-> refresca Odoo y graba el plano del importe cambiado")


if __name__ == "__main__":
    main()
