# SPEC v2 vs estado real del repo — matriz de huecos

Fuente: `C:\Users\EQUIPO\Downloads\SPEC_ERP_AGENT_OS_DEMO_PRODUCTO_TFM_V2.md`.
Auditado contra el repo tal cual está el 2026-08-26 (849 tests, `ruff`/`mypy`
limpios, freeze v1 y v2.1 intactos).

**Hallazgo de partida, antes de la matriz:** no hay una demo, hay **tres**,
separadas y sin conectar entre sí:

| App | Backend | Frontend | ERP | Qué hace hoy |
|---|---|---|---|---|
| `demo_api.py` + `demo-ui/` | `demo_service.py` | React/Vite, un solo panel A/B/C | `FakeERPAdapter` únicamente | Home = comparación A/B/C. Rechaza `backend:"odoo"` explícitamente. |
| `scripts/product_demo_server.py` | `skill_admin.py` + `SystemC` real | `scripts/product_demo_frontend/index.html` (vanilla JS, un solo HTML de 1099 líneas) | `Odoo19Adapter` real, Development guard | Catálogo, texto libre → LLM real → pipeline gobernado → Odoo, **más CU-02 completo** (draft IA → editar → sandbox → aprobar → activar). Sin nav, todo en una página. |
| `scripts/odoo_governed_demo.py` | script CLI, no servidor | ninguno | `Odoo19Adapter` real | Guion fijo de 2 llamadas (R1 + R2 con aprobación), imprime a stdout. Es la base narrativa de la escena estrella. |

La SPEC v2 pide **una** app con navegación (`Operations | Skills | Skill
Studio | Approvals | Audit | Evidence`) donde A/B/C es una pestaña más, no la
home. Ninguna de las tres apps actuales tiene esa forma. La tarea principal
no es construir capacidades nuevas — casi todas existen en algún sitio — es
**unificar navegación** y coserlas.

---

## 1. Pantallas (SPEC §5)

| Pantalla SPEC | Estado | Dónde vive hoy | Nota |
|---|---|---|---|
| Home / Live Operations | 🟡 ADAPTAR | `product_demo_frontend/index.html` (panel "Enviar al pipeline gobernado") | Existe la lógica; falta el layout de home de la SPEC §6 (intent/skill/risk/policy en una fila, before/after/delta, timeline) |
| Skills Catalog | 🟡 ADAPTAR | `#catalog-list` en `product_demo_frontend/index.html`; `GET /api/skills` en `product_demo_server.py` | Ya lista las 12 skills con riesgo/roles/schema. Falta: filtros (dominio/riesgo/estado/versión/rol/modelo), estados DRAFT/VALIDATED/APPROVED/ACTIVE/DEPRECATED/RETIRED visibles (hoy solo pinta la lista fija de `CATALOG`, no lee del registry), acciones OPEN/HISTORY/COMPARE/NEW DRAFT/DEPRECATE |
| Skill Detail | 🔴 FALTA | — | No existe vista de detalle de una skill individual con historial de versiones |
| Skill Studio | 🟡 ADAPTAR | Panel "Administrar automatizaciones" en `product_demo_frontend/index.html` + `skill_admin.py` | Ya tiene CREATE FROM NATURAL LANGUAGE. **Falta por completo MODIFY EXISTING SKILL con diff** (SPEC §9, §16 preset `04 MODIFY SKILL`) |
| Draft Skill Editor | 🟢 EXISTE | `#contract-json` textarea + `buildParamForm` en `product_demo_frontend/index.html` | Editar el JSON crudo y el form de parámetros ya funciona |
| Validation / Sandbox | 🟢 EXISTE | `POST /api/proposals/test` → `skill_admin.propose()` → `run_in_sandbox` | Falta solo el checklist visual de 10 líneas que pide la SPEC (`✓ schema valid`, etc.) — hoy solo devuelve pasa/falla con un motivo |
| Approval Center | 🟡 ADAPTAR | `POST /api/approvals` (ejecución) en `product_demo_server.py`; `ApprovalService` (genérico) también usado por `skill_proposal.approve_and_activate` para activar skills | **La distinción SPEC §10 (ERP EXECUTION APPROVAL vs SKILL ACTIVATION APPROVAL) no existe como concepto de UI** — son dos flujos de código distintos (`ApprovalService.grant` vs `registry.approve`+`registry.activate`) pero no hay una pantalla que los liste juntos y los etiquete distinto |
| Live Odoo Execution | 🟢 EXISTE | `product_demo_server.py::handle_request` + `odoo_governed_demo.py` | Reread independiente ya implementado en ambos |
| Audit Trail | 🟡 ADAPTAR | `GET /api/audit` (lista plana) en `product_demo_server.py`; `demo_api.py::/demo/audit/{id}` y `/demo/timeline/{id}` (con H7 facts) en la otra app | Ninguna de las dos tiene los filtros de SPEC §11 (Request/Skill/Version/Actor/Decision/Model/Date/Approval/Postcondition); la vista con los 7 hechos H7 vive solo en la app FakeERP, no en la app Odoo real |
| Experimental Evidence | 🟢 EXISTE | `demo_results.py` + `GET /demo/evidence` + `EvidencePanel.tsx` | Lee de `data/protocol_v2_1/confirmatory_report_v2_1_2.json`, nunca recalcula — ya cumple la regla de la SPEC. Solo falta cablearlo en la app unificada |
| Security / Confinement | 🟢 EXISTE | `SafetyPanel.tsx` + `injection_resistance_test.py` (0/1530) + escena 5 de `demo_completa.py` | Datos ya están; falta conectarlos al flujo de Odoo real (hoy están en la app FakeERP) |
| A/B/C Comparison | 🟢 EXISTE, pero es la Home actual | `demo-ui/` entero | Hay que **degradarla** a pestaña secundaria, no construir nada nuevo |

---

## 2. Backend / lógica (SPEC §9, §12, §13, §14, §22)

| Pieza SPEC | Estado | Dónde | Nota |
|---|---|---|---|
| `SkillProposal` model completo (§13) | 🟡 ADAPTAR | `skill_admin.draft_skill_contract` produce un dict ad-hoc, no un `pydantic.BaseModel` como el de la SPEC | Falta `proposal_id`, `status` como enum con `REJECTED`, `base_version`, `proposed_version`, `validation_results` estructurado. Hoy el "proposal" es literal el `SkillDefinition` registrado en `SqlSkillRegistry` — funciona pero no expone la forma exacta que pide §13 |
| CREATE FROM NATURAL LANGUAGE | 🟢 EXISTE | `skill_admin.draft_skill_contract` (LLM real, OpenRouter) → `SkillAdmin.propose` | Funciona end-to-end, con reparación de mojibake y sandbox real |
| MODIFY EXISTING SKILL + diff (§9, §16 preset `04`) | 🔴 FALTA | — | No hay prompt, ni endpoint, ni lógica de "toma el contrato ACTIVE X, aplica esta instrucción en lenguaje natural, produce un DRAFT nuevo con diff resaltado". Es la pieza nueva más grande de toda la SPEC |
| Validación con checklist de 10 ítems (§9) | 🟡 ADAPTAR | `run_in_sandbox` valida schema/handler/model/campos/postconditions/idempotencia todo junto, sin desglosar | Habría que hacer que `SandboxResult` devuelva una lista de checks individuales en vez de un booleano+string |
| DRAFT→VALIDATED→APPROVED→ACTIVE (§8, §9) | 🟡 ADAPTAR | `skills.ALLOWED_TRANSITIONS` real es `DRAFT→VALIDATED→TESTED→APPROVED→ACTIVE` (con `QUARANTINED` desde cualquiera) | La SPEC omite `TESTED`; no hace falta cambiar el motor (sería tocar código congelado en parte — `skills.py` **no** está en la lista de ficheros hasheados por freeze, así que es seguro tocarlo, pero no hay necesidad: basta con que la UI muestre `TESTED` como parte visual de "sandbox pasó" dentro del paso VALIDATED→APPROVED) |
| `approve_and_activate` (§9 "Pulsar APPROVE SKILL") | 🟢 EXISTE | `skill_proposal.approve_and_activate` | Ya exige `approver` nombrado, ya bloqueado si no pasó por TESTED |
| Modificar ACTIVE crea nueva versión DRAFT (§9, regla "Nunca: NL→mutate ACTIVE") | 🔴 FALTA | — | Consecuencia directa del hueco de "modificar" — no hay lógica de versionado incremental (`1.0.0`→`1.1.0`) ligada a una modificación |
| Distinción ERP execution approval vs skill activation approval (§10) | 🟡 ADAPTAR | Existen como dos servicios de código distintos (`ApprovalService` genérico vs `registry.approve`) | Falta unificar en una sola pantalla que las liste con esa etiqueta; el backend ya las mantiene separadas de hecho |
| Audit de evolución de skill (§22: `proposal_created`, `proposal_modified`, `validation_started`, ...) | 🔴 FALTA | `registry.history()` guarda `from_state/to_state/actor/reason/recorded_at` — cubre parcialmente (`skill_activated`≈transición a ACTIVE) pero no tiene los eventos finos que pide §22 (`proposal_modified`, `validation_started` como evento separado de `validation_passed`) | Se puede derivar la mayoría de eventos de §22 a partir de `skill_transitions` + un evento nuevo para `proposal_modified` (el "modify" que falta) |
| `POST /product/run` (§12) | 🟢 EXISTE (equivalente) | `POST /api/request` en `product_demo_server.py` | Ya reutiliza el guardián Development, tal como exige la SPEC |
| `GET /skills`, `/skills/{id}`, `/skills/{id}/versions` (§12) | 🟡 ADAPTAR | `GET /api/skills` existe (lista plana desde `CATALOG`, no desde el registry con versiones) | Falta versionado real: hoy `CATALOG` es la lista congelada, no hay endpoint que lea `SqlSkillRegistry.versions()`/`.history()` para las 12 skills base (el registry solo se usa para *proposals*, nunca se siembra con `seed_from_catalog` en ninguna de las apps) |
| `POST /skill-studio/proposals`, `/propose-change`, `/validate`, `/approve`, `/activate` (§12) | 🟡 ADAPTAR | Equivalentes parciales: `/api/proposals/draft`, `/api/proposals/test` (hace validate+register en un solo paso), `/api/proposals/approve` (hace approve+activate en un solo paso) | Nombres/forma distintos de la SPEC pero cubren lo mismo salvo `propose-change` (modificar), que no existe |
| `GET /evidence`, `/evidence/{hypothesis}` (§12) | 🟢 EXISTE (equivalente) | `GET /demo/evidence` en `demo_api.py` | Falta el filtro por hipótesis individual, hoy devuelve el bundle completo |
| `GET /audit/{request_id}`, `/audit/skill/{skill_id}` (§12) | 🟡 ADAPTAR | `GET /api/audit` (lista plana, sin filtro) en `product_demo_server.py`; `GET /demo/audit/{id}` (por request, con H7 facts) en `demo_api.py` | Ninguno filtra por skill_id |

---

## 3. Odoo modes (SPEC §14)

| Requisito | Estado |
|---|---|
| Modo comparativo con `FakeERPAdapter` | 🟢 EXISTE — `demo_service.py`, rechaza `backend:"odoo"` |
| Modo live con `Odoo19Adapter` | 🟢 EXISTE — `product_demo_server.py`, `odoo_governed_demo.py`, guardián `require_development_instance()` ya probado (unidad 40 de CLAUDE.md, con el casi-accidente de producción) |
| Badge `LIVE ODOO 19 — DEVELOPMENT INSTANCE` | 🟡 ADAPTAR — `product_demo_frontend` tiene `#target-label` que ya muestra el host verificado, falta el badge con el texto exacto |
| "Skill recién activada, solo si existe handler real" | 🟢 YA ES ASÍ — `ODOO_WIRED_SKILLS = {crm.create_opportunity, crm.update_expected_revenue}`, y `handle_request` devuelve `NOT_WIRED` explícito para el resto, nunca simula |
| No crear segunda vía de conexión a Odoo | ⚠️ RIESGO YA PRESENTE, no violado — hay tres puntos de conexión a Odoo (`product_demo_server.py`, `odoo_governed_demo.py`, `odoo_demo.py` sin gobernanza) pero los tres reutilizan `require_development_instance()`. Al unificar en una sola app, colapsar a un único punto de conexión |

---

## 4. Preflight (SPEC §15)

`scripts/demo_preflight.py` existe pero cubre el checklist de la app FakeERP
(`confirmatory report`, `A/B/C boot`, `FakeERP writable`, `audit`), **no**
cubre ninguno de los ítems Odoo/Skill Studio que pide la SPEC:

🔴 FALTAN en preflight: `Odoo Development host`, `Odoo credentials`, `CRM
permissions`, `positive write control`, `independent reread`, `skill
registry`, `proposal creation`, `DRAFT cannot execute`, `validation
pipeline`, `human approval required`, `approved proposal can become ACTIVE`,
`version history recorded`.

La mayoría de estas comprobaciones **ya existen como tests** (`test_odoo_client.py`,
`test_registry.py`, `test_skill_proposal.py`) — el hueco es exponerlas como
pasos de un preflight ejecutable antes de grabar, no escribir la lógica desde
cero.

---

## 5. Presets (SPEC §16)

| Preset | Estado |
|---|---|
| `01 NORMAL` | 🟢 EXISTE — preset "approval"-adjacent en `demo_service.presets()`; falta el equivalente contra Odoo real (hoy los presets solo existen en la app FakeERP) |
| `02 APPROVAL` | 🟢 EXISTE — mismo caso que `odoo_governed_demo.py` ya ejecuta contra Odoo real; falta convertirlo en preset seleccionable desde UI en vez de script fijo |
| `03 NEW SKILL` | 🟡 ADAPTAR — el flujo funciona en `product_demo_frontend`, pero no hay un texto de petición "enlatado" como preset, el campo es libre |
| `04 MODIFY SKILL` | 🔴 FALTA — depende del hueco de "modificar" de la sección 2 |
| `05 SECURITY` | 🟢 EXISTE — `injection_resistance_test.py` tiene el payload exacto (`compromised_parser` arm); falta exponerlo como preset ejecutable en vivo desde la UI |
| `06 EVIDENCE` | 🟢 EXISTE — es literalmente abrir el panel de evidencia |

---

## 6. Datos / presets en Odoo (SPEC §25)

`docs/odoo-demo.md` documenta ya un cliente `Acme Corporation` (demo estándar
de Odoo), no `Hotel Miramar` como pide la SPEC. **Decisión pendiente para el
usuario**: o se renombra el escenario en la SPEC a los datos reales de la
instancia Development actual, o se crean registros nuevos con esos nombres
antes de grabar. No es trabajo de código, es preparación de datos — más
rápido ajustar la SPEC a los datos que ya existen y están verificados como
demo estándar (evita el riesgo, ya materializado una vez en unidad 32/40, de
escribir sobre datos que no se han verificado como sintéticos).

---

## 7. Claims / disclaimers / diseño visual (SPEC §18, §21, §23, §24)

| Requisito | Estado |
|---|---|
| Pie metodológico permanente | 🟢 EXISTE — `DEMO_DISCLAIMER` en `demo_api.py`; falta añadir la tercera línea sobre Skill Studio siendo post-core (`skill_admin.py` lo dice en docstring, no en la UI) |
| Badge `POST-CORE FUNCTIONAL DEMO` en Skill Studio | 🔴 FALTA en la UI (el principio está aplicado en el backend/docstrings, no renderizado) |
| Claims prohibidos no usados | 🟢 VERIFICADO — ningún componente actual usa "secure"/"safer"/"overall score"; `demo_results.py` deliberadamente no calcula un score agregado |
| Colores semánticos (verde/ámbar/rojo/neutral) | 🟡 ADAPTAR — `styles.css` de `demo-ui` ya usa semántica por decisión (ALLOW/DENY/etc.), pero `product_demo_frontend` tiene su propia paleta ad-hoc sin unificar con la primera |
| Resolución 1920×1080 | N/A — es cuestión de grabación, no de código |

---

## 8. Resumen ejecutivo

**Ya existe y solo hay que coser (🟢):** motor de gobernanza completo
(policy/runtime/postconditions/audit), CU-02 real con LLM (crear skill desde
lenguaje natural, sandbox, aprobar, activar), ejecución real contra Odoo
Development con reread independiente, aprobación de ejecución R2, panel de
evidencia congelada que nunca recalcula, panel de seguridad con el
0/1530 de confinamiento, comparación A/B/C completa.

**Existe pero hay que adaptar (🟡):** todo lo que hoy vive repartido en tres
apps distintas necesita convertirse en pestañas de una sola app; el catálogo
necesita leer del `SqlSkillRegistry` en vez de la lista fija para mostrar
versiones/estados; el checklist de validación necesita desglosarse en items;
Approval Center necesita una pantalla que muestre los dos tipos de
aprobación con esa etiqueta explícita.

**Falta construir de cero (🔴):** el único hueco funcional real es
**"modificar una skill existente en lenguaje natural con diff visible"**
(preset `04 MODIFY SKILL`, sección §9 "Modificar por lenguaje natural" de la
SPEC) — no existe prompt, ni endpoint, ni versionado incremental para eso.
Es, con diferencia, la pieza que más se parece a "escena estrella nueva" de
todo el documento. Todo lo demás marcado 🔴 (Skill Detail como pantalla
propia, eventos finos de audit de evolución, checklist de preflight
ampliado) es trabajo de UI/wiring sobre lógica que ya existe en el backend,
no lógica nueva.

**Orden de trabajo recomendado**, de menor a mayor riesgo de reescribir algo
que ya funciona:
1. Unificar navegación (una app, pestañas) reutilizando los tres backends tal cual, sin tocar su lógica.
2. Sembrar el registry con `seed_from_catalog(CATALOG)` al arrancar, para que Skills Catalog muestre estado/versión real en vez de la lista fija.
3. Construir "modify skill" (el único hueco funcional) reutilizando el mismo patrón de `draft_skill_contract` + un prompt nuevo que reciba el contrato ACTIVE + la instrucción, y calcule el diff en el backend (no en el frontend) para que sea reproducible.
4. Ampliar `demo_preflight.py` con los ítems Odoo/Skill Studio que faltan.
5. Retocar textos/badges (`POST-CORE FUNCTIONAL DEMO`, disclaimer de tres líneas, paleta unificada) — el trabajo más barato, dejarlo para el final.
