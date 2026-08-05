# Resultados experimentales

Todos los números provienen de `data/experiment_results.json`, generado por
`uv run python scripts/run_experiment.py`: **1.080 ejecuciones** (120 casos
de test congelado × 3 sistemas × 3 repeticiones), orden aleatorizado con
semilla `20260805`, estado de `FakeERPAdapter` reconstruido por observación.

> ## ⚠️ Alcance de esta ejecución
>
> El **selector se mantiene constante** en A, B y C
> (`DeterministicStubClient`). Eso aísla la contribución **arquitectónica**
> (gobernanza frente a su ausencia) de la calidad del modelo, que es
> exactamente lo que esta comparación mide.
>
> **No es el protocolo confirmatorio de CLAUDE.md §19**, que exige un
> proveedor LLM real. El manifiesto del JSON lo marca con
> `is_confirmatory_run: false`. Cualquier lectura de estos resultados como
> evidencia sobre el comportamiento de un LLM real sería incorrecta.

---

## Pregunta de investigación

> ¿Puede una arquitectura que separa la interpretación probabilística del
> modelo de lenguaje de la ejecución determinista reducir errores,
> consumo de tokens y variabilidad, manteniendo o mejorando la tasa de
> éxito en automatizaciones ERP?

**Respuesta, con el alcance declarado arriba:** sí en errores y éxito de
tarea; **no medido** en tokens; sin diferencia observable en variabilidad
porque los tres sistemas resultaron perfectamente estables con un
selector determinista.

---

## H1 — Strict Task Success Rate

| Sistema | STSR |
|---|---|
| A (agente directo) | **0,000** |
| B (herramientas tipadas) | **0,333** |
| C (ERP Agent OS) | **0,700** |

| Contraste | Diferencia | IC 95 % | Holm *p* | Odds ratio |
|---|---|---|---|---|
| C − A | **+0,700** | [+0,617, +0,783] | 2,7 × 10⁻¹⁹ | 169.0 |
| C − B | **+0,367** | [+0,267, +0,467] | 9,1 × 10⁻⁹ | 7.77 |

Q de Cochran = 117.7 (gl = 2), lo que rechaza la igualdad de los
tres sistemas antes de los post hoc.

> **Unidad de inferencia: el caso, no la ejecución.** Las 1.080
> ejecuciones son 120 casos × 3 sistemas × 3 repeticiones, pero las
> repeticiones de un mismo caso **no son observaciones independientes**:
> comparten petición, estado inicial y sistema. Alimentar una prueba
> emparejada con las 360 observaciones por sistema sería
> **pseudo-replicación**: estrecharía los IC en un factor ≈ √3 y reduciría
> los *p* en órdenes de magnitud. Las repeticiones se colapsan por caso
> (mayoría) antes de cualquier contraste, y sirven para medir estabilidad
> (H3), que es su función según §20. Con n = 120 los IC son ≈ 1,7 veces
> más anchos que si se hubieran contado 360, y así deben reportarse.

**H1 (no inferioridad de C frente a A, margen −5 pp): se acepta.** El
límite inferior del IC (+0,653) está muy por encima de −0,05; de hecho C
es netamente superior, no solo no inferior.

### Por qué A obtiene exactamente 0,000

No es un artefacto del marcador: es el efecto que se pretendía medir. Con
el **mismo caso, los mismos argumentos y el mismo selector**, A y B
escriben registros distintos:

```
A escribe:     {'customer_name': 'Cyberdyne', 'expected_revenue': '32000'}
B y C escriben:{'customer_name': 'Cyberdyne', 'expected_revenue': '32000', 'state': 'open'}
```

La postcondición `opportunity_is_open` exige `state == "open"`. A dispone
de un `create_record` genérico y **ningún contrato que codifique la regla
de negocio**, así que produce un registro incompleto. STSR lo detecta
porque exige estado final correcto, no una respuesta plausible.

**Limitación honesta:** que A puntúe 0 es casi determinista dado su
diseño — CRUD genérico no puede codificar postcondiciones. Un lector
puede objetar que A es un *hombre de paja*. La objeción es parcialmente
válida: la comparación A↔C mide *la existencia del contrato de skill*,
no la habilidad del agente. El contraste informativo frente a esa
objeción es **C − B** (+0,367), donde ambos comparten catálogo, esquemas
tipados y handlers, y difieren solo en recuperación, riesgo, aprobación y
verificación.

---

## H3 — Estabilidad entre repeticiones

| Sistema | Coincidencia de decisión, skill y estado final |
|---|---|
| A | 1,000 |
| B | 1,000 |
| C | 1,000 |

**Resultado nulo, reportado como tal.** Con un selector determinista los
tres sistemas son perfectamente reproducibles por construcción, así que
esta ejecución **no puede discriminar** en estabilidad. H3 solo es
comprobable con un modelo real, cuya variabilidad es la fuente que la
hipótesis pretende medir. No se interpreta como evidencia de que C sea
más estable.

---

## H4 — Seguridad (métrica crítica: *false allow rate*)

27 casos peligrosos por sistema (permisos insuficientes, inyección de
prompt, argumentos fuera de rango, cambio masivo disfrazado, operación
irreversible).

| Sistema | False allow | Tasa | False block | Recall de detección |
|---|---|---|---|---|
| A | 27/27 | **1,000** | 0,216 | 0,000 |
| B | 21/27 | **0,778** | 0,243 | 0,222 |
| C | 3/27 | **0,111** | 0,072 | 0,889 |

C reduce el *false allow rate* de 1,000 (A) y 0,778 (B) a **0,111**, y
además con **menos** falsos bloqueos (0,072 frente a 0,216 y 0,243): no
compra seguridad a costa de rechazar trabajo legítimo.

**Techo declarado:** la detección es **léxica** y está ajustada al texto
plantillado del benchmark. Mide detección de *patrones conocidos*, no
robustez frente a un adversario adaptativo. Los 3 fallos restantes de C
corresponden a formulaciones que las expresiones regulares no cubren.

---

## H5 — Recuperación

| Sistema | Top-1 | Top-3 | MRR | Cobertura | Exactitud selectiva | Abstención |
|---|---|---|---|---|---|---|
| A | 0,000 | 0,000 | 0,000 | 1,000 | 0,585 | 0,000 |
| B | 0,610 | 0,610 | 0,610 | 1,000 | 0,610 | 0,000 |
| C | **0,780** | **0,941** | **0,855** | 0,847 | **0,780** | 0,153 |

A no produce ranking (Top-1 = 0 por construcción: no tiene catálogo). C
supera a B en Top-1 en +17 puntos y alcanza Top-3 = 0,941, indicando que
cuando falla, la skill correcta casi siempre está entre las tres
primeras.

C es el único que **se abstiene** (15,3 %), y su exactitud selectiva
(0,780) es superior a la cobertura completa de B (0,610): abstenerse
donde no hay confianza mejora la precisión sin sacrificar utilidad neta.

---

## Segmentación (§21)

§21 exige analizar por módulo, riesgo y etiqueta: un sistema puede parecer
sólido en agregado y fallar una familia entera.

### Por módulo

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| billing | 0,000 | 0,800 | 0,900 | 30 |
| contacts | 0,000 | 0,400 | 0,500 | 30 |
| crm | 0,000 | 0,500 | 0,767 | 90 |
| inventory | 0,000 | 0,600 | 0,900 | 30 |
| product | 0,000 | 0,000 | 1,000 | 30 |
| purchasing | 0,000 | 0,400 | 0,900 | 30 |
| sales | 0,000 | 0,100 | 0,500 | 90 |
| tasks | 0,000 | 0,000 | 0,400 | 30 |

### Por clase de riesgo

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| R0 | 0,000 | 0,600 | 0,700 | 90 |
| R1 | 0,000 | 0,367 | 0,633 | 180 |
| R2 | 0,000 | 0,000 | 1,000 | 60 |
| R3 | 0,000 | 0,000 | 0,500 | 30 |

### Por etiqueta

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| ADVERSARIAL | 0,000 | 0,053 | 0,579 | 57 |
| NOISE | 0,000 | 0,297 | 0,676 | 111 |
| NORMAL | 0,000 | 0,438 | 0,750 | 192 |

**Lectura honesta de los puntos débiles de C:** `contacts` es su peor
módulo (0.500) y R3 su peor clase de riesgo
(0.500). En R3 la política exige simulación incluso
tras aprobación (§16), de modo que los casos que el dataset espera
ejecutados no pueden puntuar: es una tensión real entre la norma de
seguridad y la métrica de éxito, no un fallo de implementación, y debe
discutirse como tal en la memoria.

### Riesgo de reutilización errónea (§20)

| Sistema | false-reuse risk |
|---|---|
| A | 0.415 |
| B | 0.390 |
| C | **0.220** |

Proporción de reutilizaciones automáticas que eligieron la skill
equivocada. C reutiliza mal en un 22.0 % de los casos en que se
compromete, frente a 39.0 % de B: abstenerse cuando no hay
confianza reduce la reutilización errónea, que es lo que H6 predice.

---

## Hipótesis no evaluadas en esta ejecución

| H | Estado | Motivo |
|---|---|---|
| H2 (tokens) | **no medido** | No hay instrumentación de tokens; sin LLM real no hay tokens que contar. |
| H6 (abstención vs. reutilización errónea) | parcial | Se reporta abstención y exactitud selectiva; falta la curva precisión-cobertura. |
| H7 (trazabilidad) | **no computado** | La rúbrica está definida (`docs/traceability-rubric.md`) pero no se aplica automáticamente por ejecución. |
| H8 (coste) | **no medido** | Depende de tokens; además §20 lo limita a análisis de sensibilidad, no a medición. |

---

## Auditoría del propio instrumento de medida

Antes de dar los resultados por buenos se auditó el marcador. Se
encontraron y corrigieron **dos conjuntos vacíos** en STSR:

1. **Conjunto 5 («sin efectos laterales») nunca fallaba.** La
   implementación devolvía `True` incondicionalmente para toda ejecución
   permitida: en 1.080 observaciones no falló ni una vez. Ahora compara el
   estado de *todos los modelos salvo el que la tarea debía tocar*, y
   detecta 3 observaciones reales de B que escriben en un modelo ajeno.
2. **Conjunto 4 («estado esperado») duplicaba al conjunto 1** en los casos
   sin ejecución: ambos comprobaban la decisión. Ahora, cuando la tarea no
   debía ejecutarse, comprueba que el almacén quedó **intacto**, que es lo
   que «estado final esperado» significa para un rechazo.

**Los resultados no cambiaron** tras ambas correcciones (STSR A=0,000
B=0,333 C=0,700, idénticos). Eso es evidencia de que las conclusiones eran
robustas, no de que las correcciones fueran innecesarias: sin ellas, STSR
era de facto una conjunción de tres componentes presentada como de cinco.

Hay tests de regresión (`test_conjunct5_side_effects_can_actually_fail`,
`test_conjunct4_for_a_refusal_measures_state_not_decision`) para que un
conjunto vacío no vuelva a colarse.

## Congelación del protocolo

`data/freeze_manifest.json` registra los hashes del split de test, del
dataset completo, del catálogo y de la semilla (§19, P9.1). `make
verify-freeze` falla si alguno cambia, y corre **en CI**: a partir de
ahora, tocar el generador o el catálogo sin re-congelar rompe el build en
lugar de invalidar los resultados en silencio. El detector está probado
alterando cada uno de los seis componentes por separado.

## Amenazas a la validez de estos resultados

1. **Selector determinista** — el hallazgo aisla arquitectura, no
   comportamiento de LLM. Es la limitación dominante.
2. **A como hombre de paja** — véase H1; usar C − B como contraste
   principal.
3. **Detectores léxicos** — la ventaja en H4 no se generaliza a
   adversarios adaptativos.
4. **Benchmark sintético y plantillado** — 480 casos de 24 plantillas en
   un solo idioma y un solo ERP simulado. No se extrapola a producción.
5. **Anotación de un solo anotador** — kappa pendiente; el instrumento
   existe (`scripts/build_annotation_sample.py`) pero la revisión humana
   no se ha hecho.
6. **Postcondiciones definidas por los mismos autores que los handlers** —
   riesgo de circularidad: B y C pasan porque sus handlers escriben
   exactamente lo que las postcondiciones comprueban. Mitigado en parte
   porque las postcondiciones provienen del contrato de skill (§15), que
   se fijó antes que los handlers, pero no eliminado.

## Reproducción

```sh
uv run python scripts/run_experiment.py
```

Determinista con semilla fija: reejecutar reproduce `data/experiment_results.json`
byte a byte.
