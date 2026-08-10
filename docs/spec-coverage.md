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
| §30 | Controles de amenazas | `docs/threat-model.md`, medido con InjecAgent |
| RF-07 | Precondiciones de negocio ejecutables | `preconditions.py` — mecanismo completo; catálogo congelado aún sin poblar (ver abajo) |
| RF-11 | Vista previa de la mutación | `runtime.preview_mutation`, devuelta en `SIMULATE` |
| RF-16 | Latencia por observación | `ExecutionRecord.latency_seconds` |
| RF-18 | Exportación CSV (Parquet opcional) | `scripts/export_results.py` → `experiment_metrics.csv`, `experiment_segments.csv` |
| RF-01–06, 08–10, 12–15, 17, 19, 20 | — | ver tabla de §14 en `openspec/project-context.md` |

## Parcial — declarado, no oculto

| § / RF | Qué falta exactamente |
|---|---|
| RF-03 | El ciclo de vida existe (`SkillState`, `transition()`) pero **no hay un registro persistente** que consulte/apruebe/deprecar/ponga en cuarentena skills en tiempo de ejecución: el catálogo es una lista fija en código. |
| RF-07 | El **evaluador existe y está probado** (`preconditions.py`), pero **el catálogo congelado declara cero precondiciones**. No es un olvido: poblarlas cambiaría las decisiones de System C, y el resultado confirmatorio describe el sistema tal como se comportaba al congelar el split. Activarlas exige su propia ejecución, igual que `--real-parser` o el brazo de temperatura. Un test fija que hoy están vacías, para que encenderlas sea un cambio visible. |
| RF-16 | Latencia ✅, tokens ✅, errores ✅. **Coste real y tiempo de revisión humana no**: el coste es análisis de sensibilidad (§20 lo permite explícitamente) y el tiempo de revisión requeriría usuarios reales, excluidos por §11. |
| RF-18 | CSV ✅. **Parquet solo si `pandas`+`pyarrow` están instalados**, y no se han añadido como dependencia: RF-18 dice "CSV **o** Parquet" y §27 cierra con la regla de no introducir dependencias sin necesidad demostrada. |
| §12 CU-02 | Proponer una skill nueva (sandbox + tests + aprobación + versionado) **no implementado**. §15 ya lo declara fuera de la comparación confirmatoria, así que no bloquea el núcleo. |
| §29 | **Contract tests** como categoría propia (contrato de adaptador, esquema de skill, salida del LLM, eventos) no existen como suite; hay tests equivalentes repartidos. |
| §31 | **Dashboard** (Tableau) no empezado — post-core declarado. |
| §38 | **Guion de demostración de 6 escenarios** no existe como script único; los escenarios 1, 2 y 5 están cubiertos por `scripts/odoo_governed_demo.py` y el benchmark. |

## No aplicable o fuera de alcance por decisión

- §27 (stack), §28 (estructura de repositorio), §33 (índice de memoria),
  §34 (fases), §39–44: especifican forma, no comportamiento
  verificable por test.
- §32 entregables 8–12 (dashboard, demo grabada, vídeo, presentación,
  memoria): trabajo de entrega, no de código.

## Estado tras cerrar las cinco prioridades

Las cinco de la lista original están cerradas: RF-18 (export), RF-16
(latencia), §29 (los doce escenarios E2E), RF-11 (vista previa) y RF-07
(evaluador de precondiciones, con el catálogo deliberadamente sin
poblar y esa decisión fijada por test).

Lo que queda, por orden de coste/beneficio:

1. **§29 contract tests como suite propia** — el contenido existe
   repartido; agruparlo es trabajo de organización, no de diseño.
2. **RF-03 registro persistente de skills** — grande; el catálogo fijo
   en código cubre el núcleo confirmatorio, que es lo que sostiene las
   hipótesis.
3. **§12 CU-02 generación de skills** — grande, y §15 ya lo excluye
   explícitamente de la comparación confirmatoria.
4. **§31 dashboard** y **§38 guion de demo de 6 escenarios** —
   post-core declarados; `export_results.py` ya deja las tablas que el
   dashboard necesitaría.

Un hallazgo de la unidad que cerró §29, registrado aquí porque afecta a
cómo se lee H4: **la abstención cortocircuita antes que el detector
adversarial**, así que un ataque cuya redacción el recuperador no
empareja con confianza sale como `ABSTAIN`, no `DENY`. El resultado de
seguridad es el mismo —no se ejecuta nada— pero el sistema no lo
*identificó* como peligroso, simplemente no lo entendió. Parte del
comportamiento seguro atribuido a detección es, en realidad, no
comprensión. Está asertado en
`tests/test_end_to_end.py::test_pipeline_ordering_abstention_precedes_adversarial_detection`.
