# Demo real: skills contra Odoo 19 (post-core)

CLAUDE.md §26 marca la integración con Odoo 19 como extensión
**posterior al núcleo**: `FakeERPAdapter` es obligatorio para el
experimento confirmatorio, Odoo es una demostración de que la
arquitectura funciona contra un ERP real, no un sustituto del
protocolo estadístico. Esta página documenta esa demostración, hecha
en respuesta a la pregunta del usuario "¿podríamos probar y medir el
producto real y su utilidad sobre Odoo?".

## Qué se construyó

- **`Odoo19Adapter`** (`src/erp_agent_os/odoo_client.py`): misma
  interfaz pública que `FakeERPAdapter` (`create`/`get`/`update`/`list`)
  contra la API externa JSON-2 real de Odoo 19. Allowlist de modelos y
  campos aplicado **antes** de cualquier llamada HTTP (un campo no
  listado nunca llega ni sale de Odoo por este adaptador, aunque el
  llamador lo pida). Sin `delete`/`unlink` — estructuralmente, no por
  convención (R4). Timeout en cada llamada. Logs redactados (nunca
  valores de campo). Credenciales solo por entorno
  (`MissingCredentialsError` si faltan, nunca un stub silencioso).
- **`odoo_handlers.py`**: dos skills del catálogo (`crm.create_opportunity`,
  `crm.update_expected_revenue`) reimplementadas con nombres de modelo
  y campo **reales** de Odoo (`crm.lead`, no la fantasía `crm.opportunity`
  de `FakeERPAdapter`), verificados leyendo registros demo reales antes
  de escribir el código, no adivinados.
- **`scripts/odoo_demo.py`**: ejecuta el ciclo completo — crear,
  verificar postcondición, actualizar, verificar de nuevo con una
  **relectura independiente** (no confiar en el 200 OK de la respuesta
  de escritura) — contra una instancia Odoo 19 real.

## Dónde se ejecutó

Rama **Development** de Odoo.sh (`esenssi-aromas-dev-pruebas-limpio-...`),
con datos demo estándar de Odoo confirmados antes de escribir nada
("Acme Corporation", "@example.com", "Azure Interior" — no producción
clonada). La instancia de staging original (`esenssi-aromas-staging-...`)
tenía datos con apariencia real y **nunca se usó para escritura**, solo
para una lectura de prueba de conectividad — decisión tomada
explícitamente antes de continuar, no una omisión.

## Resultado

```json
{
  "target": "real Odoo 19 (Development branch, demo data)",
  "all_postconditions_met": true,
  "steps": [
    {"step": "crm.create_opportunity", "opportunity_id": "45", "postcondition_met": true},
    {"step": "crm.update_expected_revenue", "opportunity_id": "45", "postcondition_met": true},
    {"step": "independent_reread", "record": {
      "expected_revenue": 27000.0,
      "name": "Oportunidad: ERP-AGENT-OS-DEMO",
      "partner_name": "ERP-AGENT-OS-DEMO",
      "type": "opportunity"
    }}
  ]
}
```

Las dos postcondiciones se cumplen: el registro se creó como
`type: "opportunity"` con el importe exacto pedido, y tras la
actualización el importe leído de vuelta (independientemente, en una
llamada `get` separada de la que hizo la escritura) coincide con el
nuevo valor.

## Qué demuestra, honestamente

- La **abstracción de adaptador funciona**: el mismo patrón de "skill
  propone → adaptador ejecuta → se verifica la postcondición" que usa
  System C contra `FakeERPAdapter` se ejecuta sin cambios conceptuales
  contra un ERP real con su propio esquema de datos.
- La verificación de postcondiciones **no es teatro**: se relee el
  estado independientemente en vez de confiar en la respuesta HTTP de
  la escritura, igual que exige §25.
- El control de campos allowlisted funciona en la práctica, no solo en
  tests con mocks (`test_odoo_client.py` ya lo prueba con HTTP simulado;
  aquí se confirma contra la API real).

## Qué NO demuestra, para no inflar el resultado

- **No es una réplica del experimento confirmatorio.** Es una
  ejecución cualitativa de 2 skills, no 1.080 observaciones
  estadísticas. No produce STSR, IC ni *p*-valores propios; no
  sustituye ni compite con `docs/results.md`.
- **Solo 2 de las 12 skills del catálogo** están mapeadas a Odoo real
  (`crm.create_opportunity`, `crm.update_expected_revenue`). Las otras
  10 seguirían necesitando su propio mapeo de modelo/campo real,
  trabajo no hecho aquí por presupuesto de tiempo del TFM — declarado,
  no ocultado.
- **No pasa por el Policy Engine ni por System C.** `odoo_handlers.py`
  se llama directamente desde el script de demo, sin retrieval, sin
  clasificación de riesgo, sin aprobación. Integrar `Odoo19Adapter`
  como backend intercambiable de `Runtime`/`SystemC` (en vez de
  `FakeERPAdapter`) es trabajo adicional no hecho — el paso natural
  siguiente si se quisiera una demo end-to-end con gobernanza real
  incluida, no solo el adaptador aislado.
- El registro de prueba (`id=45`, "ERP-AGENT-OS-DEMO") **queda en la
  base de datos demo**: el adaptador no tiene `delete` por diseño (R4),
  así que no hay limpieza automática. Se puede borrar manualmente desde
  la UI de Odoo si se desea.

## Reproducción

```sh
# .env necesita ODOO_URL / ODOO_DB / ODOO_API_KEY apuntando a una
# instancia Development con datos demo -- NUNCA a una con datos reales.
uv run python scripts/odoo_demo.py
```

No es determinista byte a byte entre ejecuciones (cada corrida crea un
`id` nuevo en Odoo), pero sí determinista en estructura: siempre debe
reportar `all_postconditions_met: true` contra una instancia sana.
