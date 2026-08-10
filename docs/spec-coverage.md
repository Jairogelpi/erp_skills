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
| §30 | Controles de amenazas | `docs/threat-model.md`, medido con InjecAgent |
| RF-01–06, 08–10, 12–15, 17, 19, 20 | — | ver tabla de §14 en `openspec/project-context.md` |

## Parcial — declarado, no oculto

| § / RF | Qué falta exactamente |
|---|---|
| RF-03 | El ciclo de vida existe (`SkillState`, `transition()`) pero **no hay un registro persistente** que consulte/apruebe/deprecar/ponga en cuarentena skills en tiempo de ejecución: el catálogo es una lista fija en código. |
| RF-07 | `preconditions` es un campo del contrato de skill, **siempre vacío en el catálogo y sin evaluador**. Las precondiciones de negocio no se comprueban. |
| RF-11 | «Vista previa de las mutaciones»: `SIMULATE` **no muta**, que es la mitad del requisito, pero **no muestra qué cambiaría**. No hay diff previo. |
| RF-16 | Tokens ✅ y errores ✅ medidos; **latencia, coste real y tiempo de revisión no**. El coste es análisis de sensibilidad (§20 lo permite), la latencia simplemente falta. |
| RF-18 | Exportación a **CSV/Parquet de resultados no implementada**. Hay CSV para la hoja de anotación, no para los resultados del experimento. |
| §12 CU-02 | Proponer una skill nueva (sandbox + tests + aprobación + versionado) **no implementado**. §15 ya lo declara fuera de la comparación confirmatoria, así que no bloquea el núcleo. |
| §29 | **Los 12 escenarios end-to-end** (4 correctos, 3 ambiguos, 3 adversariales, 2 reintentos) no existen como suite dedicada. Su contenido está cubierto de forma dispersa por `test_system_c.py`, `test_properties.py` y el benchmark, pero no como los 12 escenarios que §29 enumera. |
| §29 | **Contract tests** como categoría propia (contrato de adaptador, esquema de skill, salida del LLM, eventos) no existen como suite; hay tests equivalentes repartidos. |
| §31 | **Dashboard** (Tableau) no empezado — post-core declarado. |
| §38 | **Guion de demostración de 6 escenarios** no existe como script único; los escenarios 1, 2 y 5 están cubiertos por `scripts/odoo_governed_demo.py` y el benchmark. |

## No aplicable o fuera de alcance por decisión

- §27 (stack), §28 (estructura de repositorio), §33 (índice de memoria),
  §34 (fases), §39–44: especifican forma, no comportamiento
  verificable por test.
- §32 entregables 8–12 (dashboard, demo grabada, vídeo, presentación,
  memoria): trabajo de entrega, no de código.

## Prioridad sugerida si hay tiempo

1. **RF-18 (exportar CSV/Parquet)** — trivial, es un RF explícito.
2. **RF-16 latencia** — trivial, cierra media métrica de §20.
3. **§29 los 12 escenarios E2E** — moderado, es un requisito enumerado.
4. **RF-11 vista previa** — moderado, mejora la demo y CU-01 paso 8.
5. **RF-07 precondiciones** — moderado; hoy el campo existe vacío.

RF-03 (registro persistente) y CU-02 (generación de skills) son los más
grandes y los que menos aportan al núcleo confirmatorio, que es lo que
sostiene las hipótesis.
