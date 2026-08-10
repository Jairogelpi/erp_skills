# Cobertura de la especificación: qué § está implementado y qué no

Auditoría sistemática de `CLAUDE.md` sección por sección, hecha a
petición explícita del usuario ("mira que no falte ningún §"). Lista lo
que está **implementado y verificado**, lo que está **parcial** y lo
que **falta**, sin redondear a favor.

## Implementado y verificado

| § / RF | Qué exige | Evidencia |
|---|---|---|
| §11 | 8 familias, 24 intenciones, 12 skills | `catalog.py`, `bench_intents.py`; conteos verificados por test |
| §15 | Contrato de skill versionado + ciclo de vida | `skills.py`, `transition()`, sin salto `DRAFT→ACTIVE` |
| §16 | Taxonomía R0–R4 | `policy.py`; R4 no registrable (property test) |
| §17 | 480 casos, splits 240/120/120, 30 % ruido, 20 % adversarial | `bench_generator.py`; conteos exactos por test; fuga verificada ausente |
| §18 | Sistemas A / B / C | `system_a.py`, `system_b.py`, `system_c.py` |
| §19 | 1.080 observaciones emparejadas, orden aleatorizado, estado restaurado, congelación | `experiment.py`, `freeze.py`, `make verify-freeze` en CI |
| §20 | STSR, false allow, recuperación, estabilidad, tokens, trazabilidad, reutilización | `metrics.py`, `traceability.py` |
| §21 | McNemar, Q de Cochran, bootstrap, Holm, tamaños de efecto | `statistics.py`, verificado contra valores críticos conocidos |
| §22 | **Comparación TF-IDF / embeddings / híbrido** | `scripts/compare_retrievers.py`, `docs/retriever-comparison.md` |
| §23 | Generación estructurada, temperatura baja, sin ejecución desde texto libre | `parser.py`, clientes LLM, `_parse_tool_call` |
| §24 | Policy engine deny-by-default, decisiones explicables y versionadas | `policy.py` |
| §25 | Idempotencia, postcondiciones verificadas | `runtime.py`, `postconditions.py` |
| §26 | Adaptador Odoo 19 limitado, allowlist, sin R4 | `odoo_client.py`, `docs/odoo-demo.md` |
| §29 | Property tests, cobertura ≥85 % global y ≥95 % policy/runtime | `test_properties.py`; cobertura 97 % |
| §29 | **12 escenarios E2E** (4 correctos, 3 ambiguos, 3 adversariales, 2 reintentos) | `tests/test_end_to_end.py`, con un test que fija los conteos |
| §29 | **Contract tests** (adaptador, esquema de skill, salida del LLM, eventos) | `tests/test_contracts.py`, 22 tests; la suite de adaptador está parametrizada por implementación |
| §30 | Controles de amenazas | `docs/threat-model.md`, medido con InjecAgent |
| §38 | **Guion de demostración de 6 escenarios** | `scripts/demo.py` — determinista sobre FakeERP (mitigación que §37 prescribe), se autoverifica y sale con error si algún escenario deja de comportarse como §38 describe |
| RF-03 | **Registro persistente de skills** con versiones, estados e historial | `registry.py` — delega el ciclo de vida en `skills.transition()`; historial append-only de transiciones con actor y motivo |
| RF-07 | Precondiciones de negocio ejecutables | `preconditions.py` — mecanismo completo; catálogo congelado aún sin poblar (ver abajo) |
| RF-11 | Vista previa de la mutación | `runtime.preview_mutation`, devuelta en `SIMULATE` |
| RF-16 | Latencia por observación | `ExecutionRecord.latency_seconds` |
| RF-18 | Exportación CSV (Parquet opcional) | `scripts/export_results.py` → `experiment_metrics.csv`, `experiment_segments.csv` |
| §12 CU-02 | **Proponer una skill**: validar → sandbox → aprobación humana → activar | `skill_proposal.py`; una skill generada nunca se autoactiva (§15). Capacidad de demostración, fuera del núcleo confirmatorio por decisión de §15 |
| RF-01–06, 08–10, 12–15, 17, 19, 20 | — | ver tabla de §14 en `openspec/project-context.md` |

## Parcial — declarado, no oculto

| § / RF | Qué falta exactamente |
|---|---|
| RF-07 | El **evaluador existe y está probado** (`preconditions.py`), pero **el catálogo congelado declara cero precondiciones**. No es un olvido: poblarlas cambiaría las decisiones de System C, y el resultado confirmatorio describe el sistema tal como se comportaba al congelar el split. Activarlas exige su propia ejecución, igual que `--real-parser` o el brazo de temperatura. Un test fija que hoy están vacías, para que encenderlas sea un cambio visible. |
| RF-16 | Latencia ✅, tokens ✅, errores ✅. **Coste real y tiempo de revisión humana no**: el coste es análisis de sensibilidad (§20 lo permite explícitamente) y el tiempo de revisión requeriría usuarios reales, excluidos por §11. |
| RF-18 | CSV ✅. **Parquet solo si `pandas`+`pyarrow` están instalados**, y no se han añadido como dependencia: RF-18 dice "CSV **o** Parquet" y §27 cierra con la regla de no introducir dependencias sin necesidad demostrada. |
| §31 | Los **insumos** del dashboard existen: tablas CSV (`export_results.py`) y cinco figuras reproducibles PNG/SVG (`make_figures.py`). **El workbook de Tableau en sí es trabajo manual** que este repositorio no puede generar. |
| §19 | La congelación (`data/freeze_manifest.json`) cubre split de test, dataset, catálogo y semilla, pero **no la configuración del proveedor LLM** (modelo, temperatura, reintentos). Limitación declarada desde que existe el primer cliente real. |
| §6 H3 | El brazo exploratorio de temperatura está **implementado** (`--temperature`) pero **no ejecutado**: con temperatura 0, que §23 exige, H3 sale 1,000 en los tres sistemas por construcción. `metrics.paraphrase_consistency` (H3b) sí discrimina y está probado, pero la corrida con LLM real que lo mediría tampoco se ha lanzado. |
| §26 | El **demo adversarial contra Odoo real** (`scripts/odoo_adversarial_demo.py`) está escrito pero **bloqueado**: el usuario de API de la instancia no pertenece al grupo Sales, así que `crm.lead` devuelve `AccessError`. Irónicamente, es el principio de mínimo privilegio funcionando. |
| §17/§21 | **Kappa de anotación pendiente.** El instrumento existe (`data/annotation_review_sheet.csv`, 96 casos estratificados) y `scripts/compute_agreement.py` se niega a emitir un número sin anotación humana. Es un paso humano, no automatizable. |

## No aplicable o fuera de alcance por decisión

- §27 (stack), §28 (estructura de repositorio), §33 (índice de memoria),
  §34 (fases), §39–44: especifican forma, no comportamiento
  verificable por test.
- §32 entregables 8–12 (dashboard, demo grabada, vídeo, presentación,
  memoria): trabajo de entrega, no de código.

## Estado: todo el software especificado está implementado

Cerrados en dos tandas: primero RF-18, RF-16, §29 (escenarios E2E),
RF-11 y RF-07 (mecanismo); después RF-03, CU-02, §29 (contract tests),
§31 (insumos) y §38. **No queda ningún requisito de software sin
implementar.**

Lo que queda son cuatro cosas que **no son código**, y una que depende
de un permiso externo:

| Pendiente | Naturaleza | Quién |
|---|---|---|
| Kappa de anotación | Juicio humano sobre 96 casos; el instrumento está listo y se niega a inventar el número | Autor |
| Workbook de Tableau | Trabajo manual sobre las tablas ya exportadas | Autor |
| Memoria, vídeo, presentación | Redacción y entrega (§32, §33) | Autor |
| Demo adversarial en Odoo | Requiere que el usuario de API entre en el grupo Sales de la instancia | Administrador de Odoo |
| Extender la congelación a la config del proveedor | Código pequeño, pero re-congelar invalida comparaciones ya publicadas | Decisión de método |

Y dos ejecuciones que existen como capacidad pero no se han lanzado,
por coste de cuota y porque ninguna cambia una conclusión publicada:
el brazo exploratorio de temperatura (H3) y una corrida real que mida
H3b (consistencia entre paráfrasis).

## Hallazgo con efecto sobre cómo se lee H4

Escribir los escenarios E2E destapó una propiedad de orden del
pipeline: **la abstención cortocircuita antes que el detector
adversarial**. Un ataque cuya redacción el recuperador no empareja con
confianza sale como `ABSTAIN`, no `DENY`. El resultado de seguridad es
idéntico —no se ejecuta nada— pero el sistema no lo *identificó* como
peligroso: no lo entendió.

**Medido, no estimado.** Sobre los 9 casos peligrosos del split de test:

| Desenlace | n | % |
|---|---|---|
| `DENY` — detección genuina | 7 | 77,8 % |
| `ABSTAIN` — no comprensión | 1 | 11,1 % |
| `ALLOW` — false allow | 1 | 11,1 % |

Así que el recall de detección de 0,889 se descompone en **0,778 de
detección real y 0,111 de abstención**. El caveat es real y está
acotado: un caso de nueve. Asertado en
`tests/test_end_to_end.py::test_pipeline_ordering_abstention_precedes_adversarial_detection`
y recogido en `docs/results.md`.
