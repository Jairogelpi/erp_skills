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

## Qué NO demuestra esta primera demo (`odoo_demo.py`)

- **No es una réplica del experimento confirmatorio.** Es una
  ejecución cualitativa, no 1.080 observaciones estadísticas. No
  produce STSR, IC ni *p*-valores propios; no sustituye ni compite con
  `docs/results.md`.
- **No pasa por el Policy Engine ni por System C.** `odoo_handlers.py`
  se llama directamente, sin retrieval, sin clasificación de riesgo,
  sin aprobación.

Este segundo hueco se cerró en la siguiente demo, abajo.

## Segunda demo: gobernanza real, no solo el adaptador (`odoo_governed_demo.py`)

Después de la primera demo, se cerró la brecha más importante:
`Odoo19Adapter` se conectó como backend real de `Runtime` y `SystemC`
(el mismo código de gobernanza que usa el experimento confirmatorio,
solo que apuntando a Odoo en vez de `FakeERPAdapter`) — no un script
aislado que solo llama al adaptador. Esto requirió dos cambios de
tipado en `runtime.py`/`system_c.py`/`postconditions.py`/`adapters.py`
(un `Protocol` `ErpAdapter` y `Runtime` genérico sobre el tipo de
adaptador, corrigiendo un error real de mypy sobre varianza de tipos
en `Callable`, no solo silenciado) para que `Odoo19Adapter` fuera un
sustituto **estáticamente tipado** de `FakeERPAdapter`, no solo
compatible en tiempo de ejecución por duck typing accidental.

### Guion de la demo

1. **`crm.create_opportunity` (R1)** — se autoejecuta, escribe en Odoo real.
2. **`crm.update_expected_revenue` (R2), sin aprobación** — el Policy
   Engine devuelve `REQUIRE_APPROVAL` **antes** de tocar Odoo. Se
   verifica con una relectura independiente que el registro real
   **no cambió**.
3. Se concede aprobación (`ApprovalService.grant`), se repite la misma
   petición — ahora sí ejecuta y escribe en Odoo real.

### Resultado real

```json
{
  "all_checks_passed": true,
  "steps": [
    {"step": "1_create_opportunity_R1", "decision": "ALLOW", "opportunity_id": "47"},
    {"step": "2_update_without_approval_R2", "decision": "REQUIRE_APPROVAL",
     "odoo_left_untouched": true},
    {"step": "3_update_with_approval_R2", "decision": "ALLOW",
     "revenue_correctly_updated": true}
  ],
  "full_audit_trail": [
    {"skill_id": "crm.create_opportunity", "decision": "ALLOW",
     "risk_score": 0.2, "reasons": ["low risk"]},
    {"skill_id": "crm.update_expected_revenue", "decision": "REQUIRE_APPROVAL",
     "risk_score": 0.5, "reasons": ["R2 requires approval"]},
    {"skill_id": "crm.update_expected_revenue", "decision": "ALLOW",
     "risk_score": 0.5, "reasons": ["approved"]}
  ]
}
```

(Ver `data/odoo_governed_demo_results.json` para la salida completa,
incluidos los estados de Odoo antes/después de cada paso.)

### Por qué esto sí es una demostración fuerte

- **El bloqueo es real, no simulado**: el paso 2 prueba, con una
  llamada `get` independiente contra Odoo real (no contra el propio
  adaptador que acaba de decidir bloquear), que el importe **no
  cambió** mientras la aprobación no existía. Es exactamente el tipo
  de evidencia que responde a H4 (false allow) pero contra un ERP real
  en vez de `FakeERPAdapter`.
- **La traza de auditoría es real**, generada por el mismo `AuditStore`
  del núcleo confirmatorio — decisión, `risk_score`, motivo, versión de
  skill, resultado — por cada uno de los tres pasos.
- **El mismo código, no una reimplementación**: `Runtime`, `SystemC`,
  `ApprovalService`, `TfidfRetriever` y `AuditStore` son literalmente
  las mismas clases que se ejecutan 1.080 veces en el experimento
  confirmatorio — solo cambia qué adaptador reciben.

### Qué sigue sin demostrar, para no inflar el resultado

- **Solo 2 de las 12 skills del catálogo** están mapeadas a Odoo real.
  Las otras 10 seguirían necesitando su propio mapeo de modelo/campo,
  trabajo no hecho por presupuesto de tiempo del TFM — declarado, no
  ocultado.
- El retrieval usa `TfidfRetriever` sobre el catálogo completo de 12
  skills, pero como solo 2 tienen handler registrado, una petición mal
  enrutada a una de las otras 10 fallaría con
  `UnregisteredHandlerError` en vez de degradar con gracia — aceptable
  para una demo de alcance acotado, no para producción.
- Los registros de prueba (`id=46`, `id=47`, "Odoo Demo Corp")
  **quedan en la base de datos demo**: el adaptador no tiene `delete`
  por diseño (R4). Se pueden borrar manualmente desde la UI de Odoo.

## Reproducción

```sh
# .env necesita ODOO_URL / ODOO_DB / ODOO_API_KEY apuntando a una
# instancia Development con datos demo -- NUNCA a una con datos reales.
uv run python scripts/odoo_demo.py             # adaptador aislado
uv run python scripts/odoo_governed_demo.py    # System C completo
```

No son deterministas byte a byte entre ejecuciones (cada corrida crea
un `id` nuevo en Odoo), pero sí en estructura: siempre deben reportar
`all_postconditions_met`/`all_checks_passed: true` contra una instancia
sana.
