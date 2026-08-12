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

**Revisión al 2026-08-12.** La clasificación protocolaria anterior queda
supersedida por `data/evidence_registry.json`: `data/experiment_results.json`
es una ejecución v1 exploratoria de 1.080 observaciones. El flag histórico del
manifiesto se conserva por trazabilidad y no altera esa clasificación.

ERP-Skills-Bench v2 es el único protocolo confirmatorio y está pendiente de
dataset, freeze y ejecución.

**Historial de proveedor:** Groq completó una corrida entera antes de que existieran H2/H7; al relanzar con la instrumentación nueva, la cuota diaria de Groq (agotada por intentos previos sin checkpoint) y luego la de Gemini (20 peticiones/día por modelo en todos los modelos probados) bloquearon el reintento. OpenRouter (`openai/gpt-oss-20b:free`) es el que completó la corrida que se reporta. Los tres clientes quedan en el repo, probados y seleccionables vía `--provider {groq,gemini,openrouter}`.

**Resultados medidos, ejecución v1 exploratoria** (unidad de inferencia = caso, n=120, no la ejecución):

| Métrica | A | B | C |
|---|---|---|---|
| STSR | 0,000 | 0,517 | **0,700** |
| False allow rate | 0,333 | 0,889 | **0,111** |
| Tokens medios/ejecución (H2) | 198,2 | 230,3 | **0,0** |
| Trazabilidad media (H7) | 0,19 | 0,36 | **0,80** |
| Top-1 recuperación | 0,000 | 0,890 | **0,780** |

C−A = +0,700 IC95 [+0,617, +0,783], Holm *p* = 2,71×10⁻¹⁹, OR 169. C−B = +0,183 IC95 [+0,058, +0,308], Holm *p* = 7,65×10⁻³, OR 2,07. Q de Cochran = 109,46 (gl 2). H1 (no inferioridad, margen −5 pp) **se acepta**.

> **⚠️ Esta ejecución entregaba a los tres sistemas un parseo perfecto de argumentos que nadie pagaba**, lo que inflaba a C (tokens = 0, porque su recuperación es TF-IDF y no necesitaba el LLM para nada). Ver la ejecución con `--real-parser` justo debajo: **el resultado principal cambia**.

**Ejecución con parseo real** (`data/experiment_results_real_parser.json`, Groq, `real_parser: true`) — los tres sistemas extraen los argumentos del texto crudo con el mismo LLM, prompt y lista de campos:

| Métrica | A | B | C |
|---|---|---|---|
| STSR | 0,000 | 0,483 | **0,633** |
| Tokens medios/ejecución | 185,1 | 265,3 | **67,6** |
| False allow rate | 0,889 | 0,889 | **0,111** |
| Trazabilidad media | 0,356 | 0,374 | **0,820** |

**C−B en STSR = +0,150 IC95 [+0,042, +0,258], Holm *p* = 0,0162.** Significativo, y con un efecto **menor** que el +0,183 que sostenía el parseo regalado. En tokens gana con holgura: C−B = −197,6 IC95 [−198,3, −196,9], **3,9× más barato**. Seguridad y trazabilidad no dependen del parseo: provienen del policy engine y de la auditoría.

**Historia exploratoria de esta cifra:** en la ejecución 3 histórica, al quitar el parseo regalado, C−B cayó a +0,075 (*p* = 0,212) y se publicó así, como no significativo. Una pregunta escéptica posterior reveló un sesgo contra C —una unidad monetaria sin normalizar que solo penalizaba al sistema que valida tipos—. El episodio motiva la congelación prospectiva v2.

**Lectura permitida:** v1 ofrece señales exploratorias sobre seguridad,
trazabilidad, tokens y STSR. La tesis cuantitativa queda pendiente de v2.

**Doce defectos encontrados y corregidos por auditoría propia** (unidades 21–31, detalle completo en [`docs/audit.md`](audit.md)): fuga del test congelado; validador de fuga tautológico; dos conjuntos vacíos de STSR; pseudo-replicación; dos huecos en la suite estadística (mutation testing); caveat del manifiesto inconsistente con `is_confirmatory_run`; caveat con el nombre del proveedor hardcodeado; error de varianza de `Callable` al retipar contra `ErpAdapter`; dos clases de error homónimas entre `odoo_client` y `adapters`; y **el #12, caché de extracción compartido entre A/B/C**, que hacía que los tokens por sistema midieran orden de ejecución. Once correcciones **no cambiaron el signo de ninguna conclusión**; la doceava **sí** — es la que reformuló la tesis. Mutation testing acumulado: 40 mutantes, 40 muertos, cobertura de los 23 módulos con lógica de antes de esta sesión.

**Pendiente explícito:** completar ERP-Skills-Bench v2; H8 es análisis de sensibilidad, no gasto medido; H3 v1 no discrimina con temperatura 0; no hay segundo anotador humano disponible y no se reporta acuerdo humano; grabar y maquetar el vídeo.

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
- [-] **P6.4** Añadir pruebas de API, persistencia, pgvector y contratos de eventos/adaptador (D-08). Evidencia: `tests/test_api.py` (7 passed), `tests/test_persistence.py` (6 passed). **Pendiente declarado, igual que P6.2:** sin pruebas de pgvector real (no está cableado) ni contrato formal de eventos/adaptador aparte de los tests unitarios existentes.

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P6.1 | `CLAUDE.md` §§14, 27, 29; RF-01; D-08 | API autenticada y correlacionada | Pruebas API | ¿Límites/validación activos? |
| P6.2 | `CLAUDE.md` §§14, 27; RF-03/RF-15/RF-16 | Persistencia de catálogo, eventos y métricas | Integración DB/pgvector | ¿Datos sobreviven? |
| P6.3 | `CLAUDE.md` §§14, 16, 24; RF-10/RF-11 | Aprobación acotada; simulate/deny inmutables | Pruebas de autorización | ¿Sin mutación? |
| P6.4 | `CLAUDE.md` §29; D-08 | Contratos integrados comprobados | Suite integración | ¿Todos pasan? |

**Puerta:** API no amplía permisos ni expone datos; decisiones y trazas sobreviven al flujo integrado.  
**Evidencia:** integración, contratos, threat model actualizado y pruebas de autorización.

### 7. Calidad, CI y empaquetado reproducible `CONF`

- [x] **P7.1** Configurar pytest, cobertura, Hypothesis, pre-commit, Docker Compose, Makefile, `.env.example` sin secretos y GitHub Actions (RF-20, D-08). Evidencia: `pyproject.toml`, `Makefile`, `docker-compose.yml`/`compose.yaml`, `.env.example` (verificado sin secretos vía `git check-ignore`), `.github/workflows/`.
- [x] **P7.2** Ejecutar Ruff como formateador/linter; **Ruff formatea código, no verifica tipos**. Evidencia: `make format`/`make lint`, limpio en cada commit de esta sesión.
- [x] **P7.3** Ejecutar mypy como comprobación estática de tipos; **mypy verifica tipos, no formatea código**. Evidencia: `make typecheck`, "no issues found" en 33 archivos en el commit más reciente.
- [x] **P7.4** Configurar CI: instalación, Ruff, mypy, tests, cobertura, build, validación dataset, smoke benchmark y artefactos (§29). Evidencia: `.github/workflows/*.yml`, verde en cada push/PR de esta sesión (incluye `make coverage`, `make validate-dataset`, `make benchmark-smoke`).
- [x] **P7.5** Documentar arranque desde cero y confirmar ausencia de datos sensibles (D-08, §35). Evidencia: `README.md` Quickstart; dataset 100 % sintético (`docs/dataset-card.md`); `.env`/claves nunca commiteadas, verificado repetidamente con `git check-ignore -v`.

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

- [x] **P8.1** Implementar A directo, B tipado sin retrieval/verificador y C completo, con cobertura de herramientas equivalente (D-06). Completado en unidades 14–20: `handlers.py` (12 handlers), `system_a.py`/`system_b.py`/`system_c.py`, `bench_runner.py` wiring de los 480 casos. Evidencia: `python -m pytest tests/test_system_a.py tests/test_system_b.py tests/test_system_c.py` → todos passed; brecha de detección adversarial (H4) diagnosticada honestamente y luego corregida (unidad 18, ADVERSARIAL 17,7%→57,3%→0,579 con LLM real en la unidad 30).
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

- [x] **P9.1** Congelar test, anotaciones, 12 skills, prompts, configuración y plan de análisis (D-01, D-04). Evidencia: `src/erp_agent_os/freeze.py`, `data/freeze_manifest.json` (hashes de split de test, dataset completo, catálogo y semilla); `make verify-freeze` **corre en CI** y rompe el build ante cualquier deriva; detección probada alterando cada componente uno a uno (`tests/test_freeze.py` → 12 passed). **Schema 1.1 (unidad 39) cierra el pendiente que este ítem arrastraba:** el manifiesto añade `prompt_hash` (prompt de selección, prompt de extracción y plantilla de usuario renderizada) y `provider_config_hash` (modelo, temperatura, reintentos, timeout y tope de tokens de los tres clientes reales). La extensión es **puramente aditiva** — los hashes de split, dataset y catálogo son byte-idénticos a los de schema 1.0, fijado por test, así que los resultados ya publicados siguen siendo comparables. Un manifiesto 1.0 no pasa en silencio: `verify_freeze` reporta los componentes nuevos como no congelados. Deriva verificada cambiando de verdad el modelo, la temperatura y un prompt.
- [x] **P9.2-v1** Ejecutar 120 test × 3 sistemas × 3 repeticiones = 1.080 observaciones exploratorias. Evidencia: `data/experiment_results.json`; `tests/test_experiment.py` verifica el conteo histórico.
- [ ] **P9.2-v2** Generar el dataset nuevo, congelar y ejecutar 1.080 observaciones independientes con restauración probada, sin cache entre unidades y checkpoint cifrado.
- [x] **P9.3** Calcular STSR, seguridad/false allow, recuperación y estabilidad (RF-16–18, D-04). Evidencia: `src/erp_agent_os/metrics.py` (STSR conjuntivo de 5 componentes, false allow, Top-1/Top-3/MRR/cobertura/exactitud selectiva, estabilidad, tokens desde la unidad 30); `traceability.py` (rúbrica H7, unidad 30); `tests/test_metrics.py`/`tests/test_traceability.py` → todos passed. Incluye `false_reuse_risk` (§20) y segmentación por módulo/riesgo/etiqueta (§21), tabuladas en `docs/results.md`. Latencia por ejecución **cerrada**: `ExecutionRecord.latency_seconds`, medida con `time.monotonic()` alrededor de cada observación y agregada por sistema (RF-16). Pendiente declarado de RF-16: coste real y tiempo de revisión humana — el primero es análisis de sensibilidad por decisión de §20, el segundo requeriría usuarios reales, excluidos por §11.
- [x] **P9.4** Aplicar McNemar/Q de Cochran, Holm, IC 95 % y tamaños de efecto (§21). Evidencia: `docs/results.md`; funciones en `statistics.py` verificadas contra valores críticos conocidos.
- [ ] **P9.5** Ejecutar ablaciones estratificadas de 60 casos y mantener visible el estado protocolario de cada resultado (D-06).
- [x] **P9.6** Exportar CSV/Parquet, notebooks, figuras reproducibles y análisis de sensibilidad de coste (RF-18, D-04). Evidencia: `scripts/export_results.py` → `data/experiment_metrics.csv` y `data/experiment_segments.csv` (una fila por sistema/métrica y por segmento módulo·riesgo·etiqueta), regenerables con `make export-results`; `scripts/make_figures.py` → cinco figuras PNG+SVG en `reports/figures/` (`h1_stsr`, `h4_false_allow`, `h2_tokens`, `h7_traceability`, `stsr_by_risk_class`), todas reconstruidas desde el JSON commiteado, ninguna capturada a mano. **Parcial declarado:** Parquet solo si `pandas`+`pyarrow` están presentes, y no se añaden como dependencia — RF-18 dice "CSV **o** Parquet" y §27 prohíbe dependencias sin necesidad demostrada. matplotlib vive en el grupo `figures`, no en `dev`, porque instalarlo en el entorno que analiza mypy provoca un crash interno de mypy 1.15 (`unresolved placeholder type None`) contra el override `follow_imports = "skip"` de numpy — reproducido por bisección y desaparecido al desinstalarlo.

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

- [x] **P10.1** Construir Odoo19Adapter limitado sobre JSON-2, sandbox, API key fuera del repo, allowlists, timeout y redacción; prohibir R4 (§26). Evidencia: `src/erp_agent_os/odoo_client.py` (mismo contrato que `FakeERPAdapter`, allowlist de modelos y campos aplicado antes de cualquier HTTP, sin `delete`, timeout, logs redactados); `python -m pytest tests/test_odoo_client.py` → 12 passed. Verificado en vivo contra una instancia Odoo 19 real (Odoo.sh, rama Development con datos demo): `docs/odoo-demo.md`, 2 skills mapeadas (`crm.create_opportunity`/`crm.update_expected_revenue` → `crm.lead`). **Cerrada la brecha de gobernanza:** `Runtime`/`SystemC`/`postconditions.py` retipados contra un `Protocol` `ErpAdapter` y `Runtime` genérico (`adapters.py`), corrigiendo un error real de mypy sobre varianza en `Callable`, no solo silenciado — `Odoo19Adapter` es ahora un sustituto estáticamente tipado de `FakeERPAdapter`, no solo compatible por duck typing accidental. `scripts/odoo_governed_demo.py` ejecuta el pipeline completo (retrieval→política de riesgo→aprobación→runtime→auditoría) contra Odoo real: R1 autoejecuta, R2 bloquea de verdad (relectura independiente confirma que Odoo no cambió sin aprobación), tras aprobar sí escribe — traza de auditoría completa capturada. **Pendiente declarado:** solo 2 de 12 skills mapeadas a Odoo real; sin manejo elegante de retrieval hacia las 10 skills sin handler registrado (fallaría con `UnregisteredHandlerError`, aceptable para demo acotada).
- [-] **P10.2** Construir dashboard Tableau desde exportaciones; mantener Matplotlib/Plotly y estadística reproducible como fuente analítica (§27, §31). **Insumos completos, workbook pendiente:** las tablas CSV (`scripts/export_results.py`) y las cinco figuras reproducibles (`scripts/make_figures.py`) cubren las cinco vistas que §31 enumera — resumen ejecutivo, recuperación, seguridad, eficiencia y estabilidad. El workbook de Tableau en sí es trabajo manual que este repositorio no genera; se marca `[-]`, no `[x]`. La estadística sigue viviendo en `statistics.py`/`docs/results.md`, no en Tableau (D-07: el dashboard no sustituye el análisis).
- [x] **P10.3** Implementar generación candidata solo sandbox, validación, tests, aprobación humana y versionado; excluirla de A/B/C (§15). Evidencia: `src/erp_agent_os/skill_proposal.py` — `propose_skill()` valida el contrato, ejecuta la skill en un `FakeERPAdapter` desechable, comprueba sus postcondiciones y **se detiene en `TESTED`**; `approve_and_activate()` exige un aprobador nombrado y es la única vía a `ACTIVE`. `registry.py` persiste versión, estado e historial append-only de transiciones. Un test fija que ninguna skill propuesta entra en `CATALOG`, de modo que A/B/C no pueden verla (§15: la generación es capacidad de demostración, no se atribuye causalmente a los resultados). Nota de implementación: el sandbox invoca el handler **directamente**, no a través de `Runtime`, porque el policy engine deniega correctamente toda skill no `ACTIVE` — probar dentro del runtime sería imposible por construcción.
- [x] **P10.4** Preparar demo determinista FakeERP de seis escenarios; Odoo solo si no fragiliza la demo (§38). Evidencia: `scripts/demo.py` (`make demo`) — los seis escenarios de §38 sobre `FakeERPAdapter`, sin red y sin LLM, que es exactamente la mitigación que §37 prescribe para "demo frágil". Se **autoverifica**: cada escenario asevera el desenlace que §38 describe (ejecuta, recupera la misma skill desde otra formulación, se abstiene, bloquea/simula, no duplica al repetir) y el script sale con código de error si alguno deja de comportarse así, de modo que una regresión rompe la demo en CI en vez de descubrirse en la defensa.

| ID | Fuente normativa | Resultado observable esperado | Evidencia concreta | Gate binario |
| --- | --- | --- | --- | --- |
| P10.1 | `CLAUDE.md` §26; D-07; evaluación: extensión post-core | Adaptador sandbox sin R4 ni secreto en repo | Contrato + smoke | ¿No permite R4? |
| P10.2 | `CLAUDE.md` §§27, 31; D-07; evaluación: no desplazar estadística | Dashboard reconstruible desde exportaciones | Dashboard + figuras | ¿No sustituye notebook? |
| P10.3 | `CLAUDE.md` §15; D-05; evaluación: no causal | Propuesta sandbox aprobada y fuera de A/B/C | Tests + registro | ¿Excluida de A/B/C? |
| P10.4 | `CLAUDE.md` §38; D-07; evaluación: extensión no bloqueante | Demo FakeERP de seis escenarios estable | Guion/grabación | ¿Funciona sin Odoo? |

**Puerta:** extensión no altera datos/artefactos confirmatorios ni reclama causalidad.  
**Evidencia:** contratos Odoo, smoke sandbox, dashboard reconstruible y guion/demo grabada.

### 11. Entregables, memoria y defensa `CONF`

- [-] **P11.1** Redactar memoria con método, arquitectura, dataset, resultados, discusión, validez, seguridad y límites (D-09). Evidencia: `docs/memoria.md`, **borrador completo de los 13 capítulos del índice de §33**, construido desde los artefactos reales — cada cifra procede de un `data/*.json` versionado y es reproducible con los comandos del anexo A. Incluye resultados negativos sin suavizar, las tres tensiones no resueltas a favor del número bonito (R3 vs STSR, abstención vs Top-1, temperatura vs H3) y el capítulo metodológico sobre los quince defectos del instrumento de medida. **Pendiente:** revisión del tutor, kappa de anotación para cerrar §6.3, y el formato final de entrega (el borrador es Markdown, no el documento maquetado).
- [ ] **P11.2** Entregar repositorio público, CITATION, dataset card, threat model, catálogo, experimentos, notebook, figuras y resultados negativos (§32, §35).
- [-] **P11.3** Preparar vídeo 3–5 min y presentación/ensayo: resultados observados, no promesas (§32, §39). Evidencia: `docs/video-guion.md` (guion literal por tramos de §39, con notas de producción que prohíben recrear capturas y exigen grabar la demo de Odoo en una sola toma) y `docs/presentacion.md` (15 diapositivas con lo que se ve y lo que se dice, más 8 de reserva para preguntas). Estrategia y las siete preguntas difíciles en `docs/defensa.md`. **Pendiente:** grabar y maquetar.
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
