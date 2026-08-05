# Hoja de ruta operativa — ERP Agent OS

Este documento convierte la especificación normativa de [`../CLAUDE.md`](../CLAUDE.md) **y las prioridades/riesgos de evaluación de [`../evaluacion_tfm.md`](../evaluacion_tfm.md)** en trabajo trazable y gobernado. Sirve para planificar, ejecutar y aceptar unidades de trabajo; no modifica el alcance, las hipótesis ni el protocolo normativo. La bitácora canónica, append-only, está en [`../CLAUDE.md#bitácora-operativa`](../CLAUDE.md#bitácora-operativa).

## Ruta rápida

1. Localizá el requisito o decisión normativa en la matriz de trazabilidad.
2. Abrí o actualizá un cambio OpenSpec acotado, con su evidencia RDD y TDD.
3. Completá una fase solo cuando sus dependencias y su puerta de calidad estén en verde.
4. Añadí una entrada fechada a la bitácora canónica; no reescribas entradas anteriores.

## Reglas de operación

- `CLAUDE.md` es la fuente normativa de alcance, protocolo y decisiones; `evaluacion_tfm.md` aporta prioridades académicas y riesgos de ejecución. Cada fase debe mantener trazabilidad a ambas fuentes cuando la prioridad de evaluación aplique. Esta hoja no las sustituye.
- Aplicar RDD: ningún ítem implementable comienza sin ID normativo, resultado esperado, evidencia y puerta de aceptación explícita.
- Aplicar SDD/OpenSpec: un cambio aprobado por unidad, artefactos `proposal`, `spec`, `design`, `tasks`, `apply-progress` y verificación; no avanzar de fase sin cerrar la anterior.
- Aplicar TDD estricto configurado: RED → GREEN → TRIANGULATE → REFACTOR, con comandos y resultados observados. No marcar evidencia que no exista.
- Proteger el protocolo confirmatorio: no ajustar test, catálogo, prompts, umbrales, pesos ni plan de análisis tras la congelación; cualquier modificación posterior es exploratoria y se etiqueta.
- Mantener el núcleo en `FakeERPAdapter`; Odoo 19, Tableau y generación de skills son extensiones post-core y nunca bloquean el experimento confirmatorio.
- Mantener datos sintéticos, sin secretos ni datos reales; no publicar resultados inventados ni convertir escenarios económicos en ahorro medido.
- Mantener unidades revisables de hasta 400 líneas cambiadas; dividir antes de aplicar si la previsión excede el límite.

## Estados y evidencia

| Marca | Significado | Regla |
| --- | --- | --- |
| `[ ]` | pendiente | no hay evidencia aceptada |
| `[-]` | en curso | no habilita dependientes |
| `[x]` | completado | evidencia enlazada y puerta superada |
| `[!]` | bloqueado | registrar causa, dueño y desbloqueo |
| `EXT` | extensión post-core | no puede bloquear CONF |
| `CONF` | requisito confirmatorio | debe cerrarse antes del experimento final |

**Estado al 2026-08-05.** Unidades 1–21. **El experimento emparejado está ejecutado**: 1.080 observaciones (120 casos de test × 3 sistemas × 3 repeticiones), `data/experiment_results.json`, análisis en [`results.md`](results.md).

**Resultados medidos** (selector determinista constante en A/B/C — aísla arquitectura, **no** es el protocolo confirmatorio §19 que exige LLM real):

| Métrica | A | B | C |
|---|---|---|---|
| STSR | 0,000 | 0,333 | **0,700** |
| False allow rate | 1,000 | 0,778 | **0,111** |
| Top-1 recuperación | 0,000 | 0,610 | **0,780** |

C−A = +0,700 IC95 [+0,653, +0,747], Holm *p* = 5,2×10⁻⁵⁶, OR 505. C−B = +0,367 IC95 [+0,306, +0,425], Holm *p* = 5,2×10⁻²⁴, OR 8,14. Q de Cochran = 353,1 (gl 2). H1 (no inferioridad, margen −5 pp) **se acepta**.

**Defecto corregido en esta fase:** el test congelado tenía **fuga** — 10 textos idénticos en DEVELOPMENT y FINAL_TEST (8,3 % del test). Causa: `validate_case_groups` era tautológico con grupos de tamaño 1. Arreglado ampliando pools a 24 valores, eliminando estilos duplicados/no-op y añadiendo `validate_no_split_leakage` (verificado con fuga plantada). Ahora 480/480 textos únicos, 0 cruces.

**Auditoría del instrumento (unidad 22):** se encontraron **dos conjuntos vacíos** en STSR — «sin efectos laterales» devolvía `True` incondicionalmente (no falló ni una vez en 1.080 observaciones) y «estado esperado» duplicaba la comprobación de decisión. Corregidos; los resultados **no cambiaron**, lo que confirma que las conclusiones eran robustas aunque la métrica no medía lo que declaraba. Protocolo congelado y verificado en CI.

**Pendiente explícito:** H2/H8 (tokens y coste) sin instrumentar; H7 (rúbrica) definida pero no computada automáticamente; H3 no discriminable con selector determinista; kappa de anotación pendiente (paso humano); memoria, demo, dashboard y vídeo sin empezar.

## Mapa de requisitos y decisiones normativas

| ID | Fuente normativa | Resultado verificable esperado | Fase |
| --- | --- | --- | --- |
| RF-01–02 | §13 | entrada NL e interpretación tipada con intención, entidades, argumentos, confianza y ausencias | 5 |
| RF-03 | §13, §15 | registro/versionado y ciclo DRAFT→VALIDATED→TESTED→APPROVED→ACTIVE; cuarentena | 4 |
| RF-04–05 | §13, §22 | recuperación híbrida y abstención por umbral, margen, slots o política | 5 |
| RF-06–08 | §13 | validación de esquema, negocio y permisos por rol/operación/modelo/campo | 4 |
| RF-09–11 | §13, §16, §24 | riesgo R0–R4, decisión allow/simulate/approval/deny y preview | 4 |
| RF-12–15 | §13, §25 | handlers allowlisted, idempotencia, postcondiciones y auditoría completa | 4 |
| RF-16–18 | §13, §20–21 | métricas, benchmarks reproducibles y exportación CSV/Parquet | 8–9 |
| RF-19–20 | §13, §27–29 | simulación y ejecución integral con Docker Compose | 4, 10 |
| D-01 | §11, §17 | 8 familias, 24 intenciones, 12 skills, 480 casos; 240/120/120 sin fuga | 3 |
| D-02 | §17 | 30 % ruido, 20 % adversarial, solapamiento explícito y segundo anotador | 3 |
| D-03 | §14, §19 | FakeERP restaurable y A/B/C con condiciones equivalentes | 4, 8 |
| D-04 | §6, §19–21 | STSR, H1–H8, IC 95 %, tamaños de efecto y análisis emparejado | 2, 9 |
| D-05 | §15, §23–25 | LLM propone; runtime determinista valida; deny-by-default; no código arbitrario | 4–5 |
| D-06 | §18–19 | A directo, B tipado, C gobernado; ablaciones solo exploratorias | 8 |
| D-07 | §26, §31–32 | Odoo 19 limitado, Tableau y demo son post-core | 10–11 |
| D-08 | §29–30, §35–37 | pruebas, cobertura, CI, amenazas, reproducibilidad y datos no sensibles | 7, 10 |
| D-09 | §32–33, §38–40 | memoria, demo, vídeo, defensa y bibliografía con resultados honestos | 11–12 |
| D-10 | §41–42 | decisiones no negociables y orden: dataset→FakeERP→skills→runtime/policy→auditoría→A/B/C→experimento | todas |

La cobertura de los objetivos específicos (§8), contribuciones (§9), amenazas a la validez (§36), riesgos (§37), entregables (§32) y criterios de aceptación (§35) se operacionaliza en las fases siguientes. Cada tarea nueva debe citar al menos un ID de esta tabla y, cuando corresponda, su sección normativa exacta.

## Prioridades de evaluación → fases y gates

| Prioridad/riesgo de `evaluacion_tfm.md` | Fases/gates que lo materializan |
| --- | --- |
| Rigor experimental: comparación emparejada, STSR, estadística reproducible | 1 (protocolo), 8 (piloto A/B/C), 9 (freeze, 1.080 ejecuciones y análisis); gates de freeze y experimento |
| Control de alcance: 12 skills/480 casos y orden post-core | 1–4 y 7; gate de unidad ≤400 líneas y dependencia dataset→FakeERP→skills |
| Equidad de baselines: mismo modelo, presupuesto, roles, estados y evaluador | 8; gate de comparadores equivalentes y trazas normalizadas |
| Congelación: no ajustar test, catálogo, prompts, umbrales, pesos o análisis | 3, 8–9; gate de manifest inmutable y clasificación CONF/EXT |
| Extensiones no desplazan el núcleo | 10; corte CONF/EXT y gate de extensión no causal/no bloqueante |

## Dependencias y corte confirmatorio/extensión

```text
Cierre científico → Dataset congelable → FakeERP → Contrato de skill
  → Runtime + policy + auditoría → A/B/C + parser/retrieval
  → Piloto/calibración → congelación → experimento → estadística/artefactos
  → memoria y defensa
                                   └→ EXT: Odoo 19 / Tableau / demo ampliada
```

| Bloque CONF | Depende de | No puede avanzar sin |
| --- | --- | --- |
| Dataset | cierre científico | esquema, anotación y particiones sin fuga |
| Núcleo | dataset | FakeERP restaurable antes de skills; contratos y tests |
| A/B/C | núcleo | mismas condiciones, evaluador y trazas comparables |
| Piloto/freeze | A/B/C y benchmark | calibración solo dev/validación y plan congelado |
| Experimento/estadística | freeze | 1.080 observaciones controladas y artefactos reproducibles |
| Memoria/defensa | análisis | resultados, límites y entregables verificables |

| EXT (no bloqueante para CONF) | Condición de inicio | Límite |
| --- | --- | --- |
| Odoo 19 | núcleo confirmatorio estable | sandbox, JSON-2, mínimo privilegio, sin R4 ni datos reales |
| Tableau/dashboard | resultados exportados | comunica, no sustituye estadística reproducible |
| generación de skills | catálogo confirmatorio congelado | sandbox y aprobación humana; fuera de A/B/C |
| demo ampliada | demo FakeERP estable | no atribuir resultados causales a extensiones |

## Plan por fases y listas de aceptación

### 1. Cierre científico `CONF`

- [x] **P1.1** Consolidar pregunta, hipótesis H1–H8, métricas, alcance/exclusiones y decisiones no negociables en `CLAUDE.md` (§§5–6, 11, 19–21, 41).
- [x] **P1.2** Fijar el orden de construcción y la separación núcleo/extensiones (§§26, 31, 34, 42).
- [x] **P1.3** Definir bibliografía, plan de análisis ejecutable, rúbrica de trazabilidad y hoja de acuerdo de anotación (D-04, D-09). Evidencia: `docs/bibliography.md`, `docs/experiment-protocol.md`, `docs/traceability-rubric.md`; plan **ejecutable** en `src/erp_agent_os/statistics.py` (McNemar, Q de Cochran, bootstrap, Holm, Cliff's delta) verificado contra valores críticos conocidos en `tests/test_statistics.py` → 13 passed. Instrumento de acuerdo: `src/erp_agent_os/agreement.py` + `scripts/build_annotation_sample.py`. Nota: la revisión sistemática del estado de la cuestión sigue pendiente, declarada en `docs/bibliography.md`.
- [x] **P1.4** Registrar amenazas a validez, potencia y supuestos de coste antes de medir (D-04, D-08). Evidencia: `docs/threat-model.md` (controles marcados implementado/PARCIAL/ausente + amenazas a validez interna/externa/constructo/estadística); `docs/experiment-protocol.md` §5 (potencia, con el supuesto de independencia entre paráfrasis declarado como limitación, no ocultado).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P1.1 | `CLAUDE.md` §§5–6, 11, 19–21, 41; evaluación: rigor | Protocolo e hipótesis operacionales consolidados | `CLAUDE.md` v1.1 | ¿Consta el protocolo? |
| P1.2 | `CLAUDE.md` §§26, 31, 34, 42; evaluación: alcance/extensiones | Orden y corte CONF/EXT fijados | `CLAUDE.md` §§26, 31, 42 | ¿Corte documentado? |
| P1.3 | `CLAUDE.md` §§6, 20–21, 33; D-04/D-09 | Plan, rúbrica, acuerdo y bibliografía utilizables | Artefactos aprobados | ¿Los cuatro existen? |
| P1.4 | `CLAUDE.md` §§20, 36–37; D-04/D-08; evaluación: riesgos | Amenazas, potencia y costes declarados antes de medir | Protocolo/acta OpenSpec | ¿Están versionados? |

**Puerta:** H1–H8 tienen endpoint, población, regla, IC y efecto; las decisiones de congelación están versionadas.  
**Evidencia:** protocolo, bibliografía, rúbrica, plan de análisis y acta OpenSpec aprobados.

### 2. Gobierno SDD/RDD y reproducibilidad base `CONF`

- [x] **P2.1** Configurar SDD con TDD estricto, límite de 400 líneas y dependencia dataset→FakeERP→skills (`openspec/config.yaml`).
- [x] **P2.2** Dividir la primera unidad por superar 400 líneas (448→188) y documentar la dependencia diferida (`openspec/changes/bootstrap-dataset-fakeerp-skill-contract/`).
- [ ] **P2.3** Crear plantilla de cambio OpenSpec que incluya IDs RDD, no-objetivos, presupuesto de líneas y evidencia de validación (D-08, D-10).
- [ ] **P2.4** Definir versiones fijadas, semillas, configuración de proveedor/modelo, artefactos de ejecución y política de datos sintéticos (D-03, D-08).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P2.1 | `CLAUDE.md` §§29, 42; D-10; evaluación: alcance | Configuración impone TDD, presupuesto y orden | `openspec/config.yaml` | ¿Configura los tres? |
| P2.2 | `CLAUDE.md` §§17, 42; D-10; evaluación: alcance | Unidad inicial ≤400 y dependencia diferida | Cambio OpenSpec citado | ¿188 líneas documentadas? |
| P2.3 | `CLAUDE.md` §§29, 35; D-08/D-10 | Plantilla exige RDD y validación | Plantilla OpenSpec | ¿Incluye cuatro campos? |
| P2.4 | `CLAUDE.md` §§19, 27, 29; D-03/D-08; evaluación: rigor | Ejecución reproducible y sintética | Lock/manifiesto | ¿Configuración registrada? |

**Puerta:** cada cambio futuro tiene trazabilidad y previsión de revisión; ningún resultado depende de configuración no registrada.  
**Evidencia:** artefactos OpenSpec completos, lock/configuración, manifiesto de ejecución y revisión aprobada.

### 3. ERP-Skills-Bench `CONF`

- [x] **P3.1** Congelar el contrato de casos v1.0, etiquetas, abstención explícita, plan 240/120/120 y validación de fuga de grupos (RF-17, D-01–02). Evidencia: `openspec/changes/bootstrap-dataset-fakeerp-skill-contract/specs/erp-skills-bench/spec.md`; `python -m pytest` → 5 passed.
- [x] **P3.2** Diseñar las 24 intenciones en 8 familias y el mapeo a exactamente 12 skills (D-01). Evidencia: `openspec/changes/populate-skill-catalog/`, `openspec/changes/define-canonical-intents/`; `src/erp_agent_os/{catalog,bench_intents}.py`; `python -m pytest tests/test_catalog.py tests/test_bench_intents.py` → 10 passed.
- [x] **P3.3** Anotar 480 casos sintéticos con estado inicial/final placeholder, decisión, error, riesgo y aclaración (D-01–02). Evidencia: `openspec/changes/generate-bench-v1-dataset/`; `src/erp_agent_os/bench_generator.py`; `data/bench_v1.jsonl` (480 líneas); `python -m pytest tests/test_bench_generator.py` → 8 passed. Nota: `initial_state`/`expected_final_state` son placeholders (`pending_execution_wiring`), no snapshots reales de `FakeERPAdapter` — el wiring de ejecución es trabajo de fase 8 (P8.1–P8.3), documentado explícitamente en `docs/dataset-card.md`, no reclamado como completo.
- [-] **P3.4** Validar 144 casos de ruido, 96 adversariales (conteos exactos verificados por test) y sus solapamientos (0 por construcción); revisar muestra por segundo anotador y resolver discrepancias (D-02, §21). **Instrumento entregado:** `src/erp_agent_os/agreement.py` (kappa de Cohen, verificado contra ejemplo calculado a mano), `scripts/build_annotation_sample.py` (muestra estratificada de 96 casos que sobremuestrea adversariales/alto riesgo, `data/annotation_review_sheet.csv`) y `scripts/compute_agreement.py` (que **rechaza emitir un número** mientras la columna del segundo anotador esté vacía). **Pendiente:** la anotación humana en sí — paso que esta sesión no puede ni debe fabricar.
- [x] **P3.5** Publicar dataset card, esquema, validadores y manifiesto de split (RF-17–18). Evidencia: `docs/dataset-card.md`; `scripts/export_bench_v1.py`; split 240/120/120 y ausencia de fuga de grupo verificados por test (`validate_case_groups`).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P3.1 | `CLAUDE.md` §17; RF-17; D-01/D-02; evaluación: freeze | Contrato v1.0 y split sin fuga | Spec citada; `python -m pytest` → 5 passed | ¿Contrato y tests existen? |
| P3.2 | `CLAUDE.md` §11, §17; D-01; evaluación: alcance | 24/8/12 definidos | Catálogo versionado | ¿Cuenta exacta? |
| P3.3 | `CLAUDE.md` §17; D-01/D-02; evaluación: rigor | 480 casos con etiquetas completas | Dataset validado | ¿480 válidos? |
| P3.4 | `CLAUDE.md` §§17, 21; D-02 | Conteos, solapamiento y acuerdo resueltos | Informe/kappa | ¿144/96 y revisión? |
| P3.5 | `CLAUDE.md` §§17, 20; RF-17/RF-18; evaluación: freeze | Dataset documentado y congelable | Card, validadores, manifiesto | ¿Artefactos publicados? |

**Puerta:** 480 casos válidos, sin fuga semántica, catálogo confirmatorio trazable — **cumplido y verificado por test**. Revisión de anotación por segundo revisor y kappa — **pendiente, paso humano no completado**; la fase 3 no se declara íntegramente cerrada hasta esa evidencia.  
**Evidencia:** validación automatizada (`tests/test_bench_generator.py`), dataset card (`docs/dataset-card.md`), `data/bench_v1.jsonl`. Kappa/acuerdo: pendiente.

### 4. Núcleo determinista, seguridad y auditoría `CONF`

- [x] **P4.1** Implementar FakeERP con estado sintético restaurable, allowlist y contrato de adaptador antes del contrato de skill (D-03, D-10). Evidencia: `openspec/changes/implement-fake-erp-adapter/`; `python -m pytest` → 12 passed.
- [x] **P4.2** Implementar contrato versionado de skill, estados y cuarentena; impedir DRAFT→ACTIVE (RF-03, D-05). Evidencia: `openspec/changes/implement-skill-contract/`; `python -m pytest` → 19 passed.
- [x] **P4.3** Implementar validadores, permisos de mínimo privilegio, R0–R4, preview y decisiones inmutables deny-by-default (RF-06–11, D-05). Evidencia: `openspec/changes/implement-runtime-policy-engine/`; `src/erp_agent_os/policy.py`; `python -m pytest tests/test_policy.py` → 5 passed. Nota: R4 ya rechazado en el schema de skill (unidad 3); `decide` nunca lo recibe.
- [x] **P4.4** Implementar runtime de handlers registrados, claves de idempotencia y verificador de postcondiciones observable (RF-12–14). Evidencia: `src/erp_agent_os/runtime.py`; `python -m pytest tests/test_runtime.py` → 5 passed. Pendiente parcial: reintentos limitados y derivación de clave de idempotencia por fórmula §25 quedan para la capa de parser/API que invoque el runtime.
- [x] **P4.5** Implementar auditoría append-only, correlación y redacción (RF-15, D-08). Evidencia: `openspec/changes/implement-audit-store/`; `src/erp_agent_os/audit.py`; `python -m pytest tests/test_audit.py` → 5 passed. Modo simulación ya cubierto por `PolicyDecision.SIMULATE` (unidad 4, no muta `FakeERPAdapter`). Métricas (RF-16) diferidas a fase 8–9.
- [x] **P4.6** Probar propiedades: no ejecución no aprobada/R4, no doble mutación, campos prohibidos no llegan al adaptador, auditoría terminal y monotonía restrictiva (§29). Evidencia: `openspec/changes/add-core-property-tests/`; `tests/test_properties.py`; `python -m pytest tests/test_properties.py` → 6 passed. Nota: verificación de mutación (inyectar defecto y confirmar fallo) intentada y denegada por el clasificador del harness; revertida sin ejecutar tests contra el archivo mutado — registrado en `apply-progress.md`, no reclamado como completo.

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P4.1 | `CLAUDE.md` §§14, 19, 42; D-03/D-10; evaluación: rigor | FakeERP restaurable y allowlisted | Contrato + prueba de restauración | ¿Restaura estado? |
| P4.2 | `CLAUDE.md` §15; RF-03; D-05 | Ciclo versionado sin salto DRAFT→ACTIVE | Tests de transición | ¿Salto rechazado? |
| P4.3 | `CLAUDE.md` §§16, 24; RF-06–RF-11; D-05 | Policy restrictiva, preview e inmutabilidad | Tests policy | ¿Deny por defecto? |
| P4.4 | `CLAUDE.md` §25; RF-12–RF-14 | Ejecución registrada, idempotente y verificada | Tests runtime/contrato | ¿Postcondición requerida? |
| P4.5 | `CLAUDE.md` §§14, 29–30; RF-15/RF-16/RF-19; D-08 | Trazas redactadas y simulación sin mutación | Tests/trazas | ¿Auditoría terminal? |
| P4.6 | `CLAUDE.md` §29; evaluación: rigor | Propiedades críticas protegidas | Suite de propiedades | ¿Todas pasan? |

**Puerta:** FakeERP se restaura por observación; no hay ejecución libre; controles críticos y contratos superan tests unitarios, contrato, integración y propiedades.  
**Evidencia:** RED/GREEN/triangulación, cobertura (global ≥85 %, policy/runtime ≥95 %), trazas de bloqueo/approval/idempotencia.

### 5. Recuperación, IA y sistema C `CONF`

- [x] **P5.1** Implementar parser estructurado con esquema, ausencias y separación instrucción/dato (RF-01–02, D-05). Evidencia: `openspec/changes/implement-parser-and-retrieval/`; `src/erp_agent_os/parser.py`. Nota: llamada real a LLM (baja temperatura, registro de configuración de proveedor) diferida a P5.4/fase 8 — `structure_proposal` valida el triple (intent, arguments, confidence) que cualquier llamada futura deberá producir.
- [x] **P5.2** Implementar TF-IDF, embeddings y ranking híbrido con filtro de rol y boosts de módulo/operación (RF-04, §22). Evidencia: `openspec/changes/add-embeddings-and-hybrid-retrieval/`; `src/erp_agent_os/embeddings.py`, `retrieval.HybridRetriever`; `python -m pytest tests/test_embeddings.py tests/test_retrieval.py` → 11 passed. Modelo `paraphrase-multilingual-MiniLM-L12-v2` descargado con autorización explícita del usuario. Pendiente explícito: `w4`/`w5` (slot_compatibility/historical_reliability) — requieren scorer de compatibilidad de argumentos e historial de ejecución que aún no existen; ajuste de pesos solo procede con catálogo dev/validación poblado (P3.2–P3.5).
- [x] **P5.3** Implementar abstención por score, margen o slots faltantes, sin inferir datos sensibles (RF-05, D-05). Evidencia: `should_abstain()`; `python -m pytest tests/test_retrieval.py` → cubre las cuatro ramas. Nota: rama de "conflicto de política" se evalúa en `policy.decide` (unidad 4), no aquí.
- [x] **P5.4** Integrar C solo mediante policy→runtime→adapter→postcondiciones→auditoría (D-03, D-05). Evidencia: `openspec/changes/integrate-system-c/`; `src/erp_agent_os/system_c.py`; `python -m pytest tests/test_system_c.py` → 6 passed. `AuditStore` extendido con `AbstentionEvent`/`record_abstention` para cubrir la decisión terminal de abstención (§25).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P5.1 | `CLAUDE.md` §§14, 23; RF-01/RF-02; D-05 | Propuesta tipada y configuración registrada | Tests de esquema | ¿Rechaza texto libre? |
| P5.2 | `CLAUDE.md` §22; RF-04; evaluación: rigor | Tres recuperadores y filtros comparables | Matriz de recuperación | ¿Filtros aplicados? |
| P5.3 | `CLAUDE.md` §§17, 22–23; RF-05; D-05 | Abstención segura ante cuatro condiciones | Casos ambiguos/adversariales | ¿No infiere sensibles? |
| P5.4 | `CLAUDE.md` §§14, 19; D-03/D-05 | C atraviesa exclusivamente el pipeline gobernado | Traza integral | ¿No hay bypass? |

**Puerta:** recuperación y abstención se evalúan en dev/validación; el LLM no evita contratos ni políticas.  
**Evidencia:** tests de esquema/contrato, matriz de recuperación, casos ambiguos/adversariales y trazas completas.

### 6. API e integración `CONF`

- [x] **P6.1** Exponer FastAPI con autenticación de demo, validación, correlation ID y límites básicos (RF-01, D-08). Evidencia: `openspec/changes/implement-api-layer/`; `src/erp_agent_os/api.py`; `python -m pytest tests/test_api.py` → 7 passed. `POST /requests` genera correlation_id en servidor (nunca del cliente); rate limit y API-key aplicados a las 4 rutas (bug de cobertura parcial encontrado y corregido durante TDD, no solo declarado).
- [-] **P6.2** Integrar PostgreSQL/pgvector, almacenamiento de skills/versiones, eventos y métricas (RF-03, RF-15–16). Evidencia: `src/erp_agent_os/persistence.py` (SQLAlchemy Core, append-only sin update/delete, probado contra SQLite en memoria → 6 passed); `compose.yaml` provisiona PostgreSQL 16 (imagen pgvector, digest anclado) con healthcheck. **Pendiente declarado:** pgvector NO se usa (la recuperación embebe en proceso sobre 12 skills); falta cablear `SqlAuditStore` en la API en lugar del store en memoria.
- [x] **P6.3** Implementar aprobación con actor, alcance, instante y expiración (RF-10–11). Evidencia: `openspec/changes/implement-approval-service/`; `src/erp_agent_os/approval.py`; `python -m pytest tests/test_approval.py` → 5 passed. simulate/deny sin mutación ya garantizado por `Runtime.execute` (unidad 4). Pendiente: wiring API (P6.1) que traduzca `ApprovalService.is_valid` en `approval_granted` para `policy.decide`.
- [ ] **P6.4** Añadir pruebas de API, persistencia, pgvector y contratos de eventos/adaptador (D-08).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P6.1 | `CLAUDE.md` §§14, 27, 29; RF-01; D-08 | API autenticada y correlacionada | Pruebas API | ¿Límites/validación activos? |
| P6.2 | `CLAUDE.md` §§14, 27; RF-03/RF-15/RF-16 | Persistencia de catálogo, eventos y métricas | Integración DB/pgvector | ¿Datos sobreviven? |
| P6.3 | `CLAUDE.md` §§14, 16, 24; RF-10/RF-11 | Aprobación acotada; simulate/deny inmutables | Pruebas de autorización | ¿Sin mutación? |
| P6.4 | `CLAUDE.md` §29; D-08 | Contratos integrados comprobados | Suite integración | ¿Todos pasan? |

**Puerta:** API no amplía permisos ni expone datos; decisiones y trazas sobreviven al flujo integrado.  
**Evidencia:** integración, contratos, threat model actualizado y pruebas de autorización.

### 7. Calidad, CI y empaquetado reproducible `CONF`

- [ ] **P7.1** Configurar pytest, cobertura, Hypothesis, pre-commit, Docker Compose, Makefile, `.env.example` sin secretos y GitHub Actions (RF-20, D-08).
- [ ] **P7.2** Ejecutar Ruff como formateador/linter; **Ruff formatea código, no verifica tipos**.
- [ ] **P7.3** Ejecutar mypy como comprobación estática de tipos; **mypy verifica tipos, no formatea código**.
- [ ] **P7.4** Configurar CI: instalación, Ruff, mypy, tests, cobertura, build, validación dataset, smoke benchmark y artefactos (§29).
- [ ] **P7.5** Documentar arranque desde cero y confirmar ausencia de datos sensibles (D-08, §35).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P7.1 | `CLAUDE.md` §§27, 29; RF-20; D-08 | Toolchain y Compose sin secretos | Configuración + smoke | ¿Arranca sin secretos? |
| P7.2 | `CLAUDE.md` §29; D-08 | Formato/lint Ruff ejecutable | Log Ruff | ¿Ruff pasa? |
| P7.3 | `CLAUDE.md` §29; D-08 | Tipos mypy ejecutable | Log mypy | ¿mypy pasa? |
| P7.4 | `CLAUDE.md` §29; evaluación: rigor | CI ejecuta nueve controles | Log CI | ¿CI verde? |
| P7.5 | `CLAUDE.md` §§29, 35; D-08 | Reconstrucción y revisión de datos documentadas | Guía + revisión | ¿Cero datos sensibles? |

**Puerta:** CI verde y repositorio reconstruible desde cero; cobertura exigida cumplida.  
**Evidencia:** logs CI, imagen/Compose smoke, informes de cobertura y comandos reproducibles.

### 8. Sistemas A/B/C y piloto `CONF`

- [x] **P8.1** Implementar A directo, B tipado sin retrieval/verificador y C completo, con cobertura de herramientas equivalente (D-06). **Groundwork de C completado** (unidades 14–15): `handlers.py` (12 handlers) + `bench_runner.py` wiring de los 480 casos a `SystemC` real. Evidencia: `openspec/changes/{harden-adapter-and-runtime-errors,wire-benchmark-to-execution}/`; `python scripts/run_bench_wiring_report.py` → `data/bench_v1_wiring_report.json` (NORMAL 87.5%, NOISE 72.2%, ADVERSARIAL 17.7% de coincidencia con `expected_decision`). Pendiente explícito: sistemas A y B (agente directo, herramientas tipadas) no existen todavía; brecha de detección adversarial (H4) documentada como hallazgo honesto, no corregida en esta unidad.
- [x] **P8.2** Controlar modelo/proveedor/versión, temperatura, tokens, timeout, reintentos, pasos, roles, evaluador, estado e idempotencia (D-03). Evidencia: `ExperimentManifest` registra selector y semilla; el mismo `LLMClient` y el mismo estado inicial se usan en A/B/C; `tests/test_experiment.py` verifica aislamiento y determinismo. Pendiente: control de tokens/temperatura (requiere LLM real).
- [x] **P8.3** Ejecutar piloto con orden aleatorizado, restauración completa y trazas normalizadas (D-03–04). Evidencia: `scripts/run_experiment.py` → 1.080 observaciones, orden aleatorizado sembrado, `FakeERPAdapter` reconstruido por observación.
- [ ] **P8.4** Ajustar únicamente en desarrollo/validación; documentar umbrales, pesos y diferencias arquitectónicas (D-04).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P8.1 | `CLAUDE.md` §§18–19; D-06; evaluación: baseline justo | A/B/C definidos con herramientas equivalentes | Contratos de sistemas | ¿Cobertura equivalente? |
| P8.2 | `CLAUDE.md` §19; D-03; evaluación: baseline justo | Variables de control comunes | Manifiesto de configuración | ¿Todas fijadas? |
| P8.3 | `CLAUDE.md` §§19–20; D-03/D-04; evaluación: rigor | Piloto aleatorizado y restaurable | Logs/trazas piloto | ¿Estados restaurados? |
| P8.4 | `CLAUDE.md` §§17, 19, 22; D-04; evaluación: freeze | Calibración solo no-test documentada | Registro de ajustes | ¿Sin ajuste en test? |

**Puerta:** piloto reproducible, comparadores equivalentes y desviaciones justificadas.  
**Evidencia:** manifiesto de configuración, logs piloto, pruebas de restauración y revisión metodológica.

### 9. Congelación, experimento y estadística `CONF`

- [x] **P9.1** Congelar test, anotaciones, 12 skills, prompts, configuración y plan de análisis (D-01, D-04). Evidencia: `src/erp_agent_os/freeze.py`, `data/freeze_manifest.json` (hashes de split de test, dataset completo, catálogo y semilla); `make verify-freeze` **corre en CI** y rompe el build ante cualquier deriva; detección probada alterando los seis componentes uno a uno (`tests/test_freeze.py` → 7 passed). Pendiente declarado: el manifiesto **no** cubre prompts ni configuración de proveedor porque aún no hay cliente LLM real; deberá extenderse antes del protocolo confirmatorio.
- [x] **P9.2** Ejecutar 120 test × 3 sistemas × 3 repeticiones = 1.080 observaciones, con estados restaurados y orden aleatorio (§19). Evidencia: `data/experiment_results.json`; `tests/test_experiment.py` verifica el conteo exacto y que cada caso corre 3 veces en cada sistema.
- [x] **P9.3** Calcular STSR, seguridad/false allow, recuperación y estabilidad (RF-16–18, D-04). Evidencia: `src/erp_agent_os/metrics.py` (STSR conjuntivo de 5 componentes, false allow, Top-1/Top-3/MRR/cobertura/exactitud selectiva, estabilidad); `tests/test_metrics.py` → 12 passed. Pendiente: tokens, latencia, coste y trazabilidad automática.
- [x] **P9.4** Aplicar McNemar/Q de Cochran, Holm, IC 95 % y tamaños de efecto (§21). Evidencia: `docs/results.md`; funciones en `statistics.py` verificadas contra valores críticos conocidos.
- [ ] **P9.5** Ejecutar ablaciones estratificadas de 60 casos como exploratorias; separar resultados confirmatorios y exploratorios (D-06).
- [ ] **P9.6** Exportar CSV/Parquet, notebooks, figuras reproducibles y análisis de sensibilidad de coste (RF-18, D-04).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P9.1 | `CLAUDE.md` §§17, 19; D-01/D-04; evaluación: freeze | Manifest inmutable post-piloto | Freeze manifest | ¿Seis elementos congelados? |
| P9.2 | `CLAUDE.md` §19; evaluación: rigor/equidad | 1.080 observaciones pareadas restauradas | Logs normalizados | ¿Cuenta y orden válidos? |
| P9.3 | `CLAUDE.md` §§6, 20; RF-16–RF-18; D-04 | Métricas definidas calculadas | Datos/resultados | ¿Incluye STSR/false allow? |
| P9.4 | `CLAUDE.md` §§6, 21; D-04 | Inferencia, IC y efectos según supuestos | Notebook ejecutable | ¿Método/IC/efecto reportados? |
| P9.5 | `CLAUDE.md` §§18–19; D-06; evaluación: freeze | Ablaciones de 60 aisladas como exploratorias | Informe etiquetado | ¿Separación explícita? |
| P9.6 | `CLAUDE.md` §§20–21; RF-18; D-04 | Artefactos exportables y sensibilidad honesta | CSV/Parquet/notebook/figuras | ¿Se reconstruyen? |

**Puerta:** no hay fuga ni ajustes post-freeze; resultados trazan a ejecuciones y análisis versionados.  
**Evidencia:** freeze manifest, datos crudos redactados, notebook ejecutable, IC/efectos y registro de resultados nulos.

### 10. Extensiones y demostración `EXT`

- [ ] **P10.1** Construir Odoo19Adapter limitado sobre JSON-2, sandbox, API key fuera del repo, allowlists, timeout y redacción; prohibir R4 (§26).
- [ ] **P10.2** Construir dashboard Tableau desde exportaciones; mantener Matplotlib/Plotly y estadística reproducible como fuente analítica (§27, §31).
- [ ] **P10.3** Implementar generación candidata solo sandbox, validación, tests, aprobación humana y versionado; excluirla de A/B/C (§15).
- [ ] **P10.4** Preparar demo determinista FakeERP de seis escenarios; Odoo solo si no fragiliza la demo (§38).

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P10.1 | `CLAUDE.md` §26; D-07; evaluación: extensión post-core | Adaptador sandbox sin R4 ni secreto en repo | Contrato + smoke | ¿No permite R4? |
| P10.2 | `CLAUDE.md` §§27, 31; D-07; evaluación: no desplazar estadística | Dashboard reconstruible desde exportaciones | Dashboard + figuras | ¿No sustituye notebook? |
| P10.3 | `CLAUDE.md` §15; D-05; evaluación: no causal | Propuesta sandbox aprobada y fuera de A/B/C | Tests + registro | ¿Excluida de A/B/C? |
| P10.4 | `CLAUDE.md` §38; D-07; evaluación: extensión no bloqueante | Demo FakeERP de seis escenarios estable | Guion/grabación | ¿Funciona sin Odoo? |

**Puerta:** extensión no altera datos/artefactos confirmatorios ni reclama causalidad.  
**Evidencia:** contratos Odoo, smoke sandbox, dashboard reconstruible y guion/demo grabada.

### 11. Entregables, memoria y defensa `CONF`

- [ ] **P11.1** Redactar memoria con método, arquitectura, dataset, resultados, discusión, validez, seguridad y límites (D-09).
- [ ] **P11.2** Entregar repositorio público, CITATION, dataset card, threat model, catálogo, experimentos, notebook, figuras y resultados negativos (§32, §35).
- [ ] **P11.3** Preparar vídeo 3–5 min y presentación/ensayo: resultados observados, no promesas (§32, §39).
- [ ] **P11.4** Verificar los 20 criterios de aceptación del §35 uno a uno antes de cerrar.

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P11.1 | `CLAUDE.md` §§32–33, 36; D-09; evaluación: límites | Memoria cubre método, resultados y validez | Manuscrito versionado | ¿Incluye límites? |
| P11.2 | `CLAUDE.md` §§32, 35; D-09; evaluación: rigor | Entregables y negativos publicables | Checklist/enlaces | ¿Todos accesibles? |
| P11.3 | `CLAUDE.md` §§32, 39; D-09; evaluación: honestidad | Vídeo/defensa muestran observaciones | Grabación/ensayo | ¿Sin promesas no medidas? |
| P11.4 | `CLAUDE.md` §35; D-09 | 20 criterios verificados individualmente | Checklist final | ¿20/20 cerrados? |

**Puerta:** la pregunta está respondida con evidencia y todos los entregables son reproducibles, honestos y sin datos sensibles.  
**Evidencia:** checklist final, enlaces/versiones de artefactos, ensayo de defensa y revisión de publicación.

## Puertas SDD por unidad

| Momento | Obligatorio antes de pasar |
| --- | --- |
| Propuesta | problema, IDs RDD, alcance/no-objetivos, dependencias y presupuesto ≤400 líneas |
| Especificación | requisitos `MUST` y escenarios aceptables trazados a `CLAUDE.md` |
| Diseño | contratos, riesgos, alternativas y estrategia de pruebas |
| Tareas | checklist con RED/GREEN/TRIANGULATE/REFACTOR, comando y criterio de salida |
| Apply | evidencia observada, diffs acotados y tareas actualizadas sin falsos `[x]` |
| Verificación | tests focalizados primero, calidad autorizada, riesgos y trazabilidad revisados |
| Freeze | manifiesto inmutable, hashes/versiones/semillas/configuración y clasificación CONF/EXT |

## Plantilla RDD por ítem

```markdown
- [ ] <acción verificable>
  - Normativa: <RF-xx / D-xx; CLAUDE.md §n>
  - Resultado esperado: <comportamiento o artefacto observable>
  - Dependencias: <IDs/fase>
  - Evidencia: <test, traza, documento, métrica o comando>
  - Puerta de aceptación: <condición binaria para marcar [x]>
  - Estado/fecha/responsable: <pendiente | en curso | bloqueado | completado>
```

Ningún `[x]` es válido sin enlace a evidencia concreta. Si cambia el requisito normativo, registrar primero la decisión en `CLAUDE.md`; luego actualizar la tabla y los cambios OpenSpec afectados.

## Plantilla de evidencia TDD estricta y comandos

```markdown
| Ciclo | Cambio mínimo | Comando exacto | Resultado observado | Enlace |
| --- | --- | --- | --- | --- |
| RED | test de comportamiento que falla por la ausencia/defecto | `python -m pytest <test>` | fallo esperado | <ruta/log> |
| GREEN | implementación mínima | `python -m pytest <test>` | pasa | <ruta/log> |
| TRIANGULATE | caso alternativo, límite o negativo | `python -m pytest <test>` | pasa | <ruta/log> |
| REFACTOR | mejora sin cambio semántico | `python -m pytest <test>` | pasa | <ruta/log> |
```

Comandos previstos (ejecutar solo los aplicables y registrar salida):

```bash
python -m pytest tests/<focal>.py
python -m pytest
python -m pytest --cov
ruff format --check .        # Ruff comprueba formato; `ruff format .` aplica formato
ruff check .                 # Ruff analiza lint
mypy src                     # mypy comprueba tipos estáticamente
```

## Registro de riesgos

| Riesgo | Señal temprana | Mitigación/gate | Dueño |
| --- | --- | --- | --- |
| alcance > capacidad | unidad >400 líneas o nuevas familias | dividir; conservar 12/24/480 | planificación |
| fuga de benchmark | grupo en varios splits | validador de grupos y freeze manifest | datos |
| sesgo A/B/C | diferencias de prompt/configuración | manifiesto común y restauración | experimento |
| seguridad superficial | allow sin prueba o bypass | propiedades, deny-by-default y auditoría | núcleo |
| datos/sensibles | fixture o log real | sintético, redacción, revisión publicación | datos/API |
| coste o proveedor | piloto inestable/caro | presupuesto, configuración registrada, escenarios | experimento |
| validez limitada | resultados solo sintéticos | discusión explícita, sin extrapolación | memoria |
| demo frágil | dependencia Odoo o red | demo FakeERP determinista | demo |
| análisis post hoc | cambio después de freeze | clasificar exploratorio, no reabrir CONF | estadística |

## Protocolo de actualización durable

1. Añadir (nunca editar retrospectivamente) una entrada UTC `YYYY-MM-DD HH:MM UTC` en `CLAUDE.md` → **Bitácora operativa**.
2. La entrada debe contener **qué**, **por qué**, **orden/dependencias**, **evidencia** y **siguiente paso**, más IDs RDD y enlaces a OpenSpec cuando existan.
3. Actualizar aquí únicamente estado, enlace de evidencia, dependencia y riesgo del ítem afectado. No duplicar el relato completo de la bitácora.
4. Para bloqueos, usar `[!]`, causa, dueño y condición exacta de desbloqueo. Para extensiones, usar `EXT` y confirmar que no desplazan `CONF`.
5. Al congelar o publicar resultados, registrar hash/versión/semilla/configuración y la clasificación confirmatoria o exploratoria.

## Registro inicial de hoja de ruta

### 2026-08-04 11:51 UTC — planificación y unidad 1

**Estado:** planificación normativa completada; esquema/scaffold del dataset completado; el resto pendiente.  
**Referencia canónica:** ver la entrada fechada en [`CLAUDE.md#bitácora-operativa`](../CLAUDE.md#bitácora-operativa) para el relato append-only, evidencia y siguiente paso.  
**No completado:** `FakeERPAdapter`, contrato de skill, runtime, policy, A/B/C, benchmark poblado, experimento, Odoo y dashboard.
