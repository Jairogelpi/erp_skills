# Resultados experimentales

Dos ejecuciones, mismo protocolo (`uv run python scripts/run_experiment.py
[--real-llm]`): **1.080 ejecuciones** (120 casos de test congelado × 3
sistemas × 3 repeticiones), semilla `20260805`, estado de `FakeERPAdapter`
reconstruido por observación.

1. **Ejecución confirmatoria real** (`data/experiment_results.json`,
   `manifest.selector: "GroqClient"`, `is_confirmatory_run: true`) — A y B
   llaman a Groq (`llama-3.1-8b-instant`, temperatura 0) igual que exige
   D-03; C no llama al LLM (su recuperación es TF-IDF), así que sus
   métricas son **idénticas** entre ambas ejecuciones — no es un error,
   es la arquitectura.
2. **Ejecución arquitectura-solo** (histórica, selector determinista
   compartido) — aísla gobernanza de calidad del modelo, ya no es la
   ejecución primaria pero se conserva como contraste porque muestra
   cuánto de la ventaja de C sobrevive incluso cuando A/B tienen un
   selector perfecto.

> ## Estado del protocolo confirmatorio de §19
>
> **Esto SÍ es el protocolo confirmatorio.** Limitación declarada: modelo
> gratuito (`llama-3.1-8b-instant`), no un modelo frontera/de producción
> — se declara en la memoria, no se oculta. La congelación
> (`data/freeze_manifest.json`) todavía no cubre la configuración del
> proveedor (modelo, temperatura, reintentos): es una limitación abierta,
> no un descuido — se lanzó a escala completa por decisión explícita antes
> de extender la congelación.

---

## Pregunta de investigación

> ¿Puede una arquitectura que separa la interpretación probabilística del
> modelo de lenguaje de la ejecución determinista reducir errores,
> consumo de tokens y variabilidad, manteniendo o mejorando la tasa de
> éxito en automatizaciones ERP?

**Respuesta, con un LLM real:** sí en errores de seguridad y éxito de
tarea, incluso cuando el propio LLM mejora (B sube de 0,333 a 0,483 con
selección real frente a stub, C sigue por encima); **no medido** en
tokens; H3 (estabilidad) resulta trivialmente 1,0 con temperatura 0, así
que tampoco discrimina aquí.

---

## H1 — Strict Task Success Rate

| Sistema | STSR (real) | STSR (stub, arquitectura-solo) |
|---|---|---|
| A (agente directo) | **0,000** | 0,000 |
| B (herramientas tipadas) | **0,483** | 0,333 |
| C (ERP Agent OS) | **0,700** | 0,700 |

| Contraste (real) | Diferencia | IC 95 % | Holm *p* | Odds ratio |
|---|---|---|---|---|
| C − A | **+0,700** | [+0,617, +0,783] | 2,71 × 10⁻¹⁹ | 169,0 |
| C − B | **+0,217** | [+0,100, +0,333] | 1,03 × 10⁻³ | 2,58 |

Q de Cochran = 110,96 (gl = 2).

> **Unidad de inferencia: el caso, no la ejecución.** Las 1.080
> ejecuciones son 120 casos × 3 sistemas × 3 repeticiones, pero las
> repeticiones de un mismo caso **no son observaciones independientes**.
> Se colapsan por caso (mayoría) antes de cualquier contraste
> (`collapse_repetitions`); con n = 120 los IC son más anchos que si se
> hubieran contado 360, y así deben reportarse.

**H1 (no inferioridad de C frente a A, margen −5 pp): se acepta.** Límite
inferior del IC (+0,617) muy por encima de −0,05; C es netamente
superior.

**C − B se mantiene significativo tras un LLM real** (Holm *p* = 1,03 ×
10⁻³, OR = 2,58), pero se **reduce a menos de la mitad** frente al stub
(+0,217 frente a +0,367): un selector real mejora bastante a B (0,333 →
0,483) porque ya no falla por selección arbitraria, cerrando parte de la
brecha. Esto es evidencia directa de que **parte** de la ventaja
observada con el stub venía de la mala calidad del selector de B, no solo
de la arquitectura — dato que debe reportarse sin maquillar, no una
sorpresa que invalide H1.

### Por qué A obtiene exactamente 0,000

Sigue siendo 0 con LLM real, por la misma razón estructural que con el
stub: A dispone de `create_record` genérico y **ningún contrato que
codifique la regla de negocio**, así que aunque el LLM elija bien el
modelo y los argumentos, el registro resultante no cumple postcondiciones
como `opportunity_is_open`. STSR lo detecta porque exige estado final
correcto, no una llamada plausible.

**Limitación honesta, sin cambios:** A es parcialmente un *hombre de
paja* — mide la ausencia de contrato de skill, no la habilidad del
agente. El contraste informativo sigue siendo **C − B**.

---

## H3 — Estabilidad entre repeticiones

| Sistema | Coincidencia de decisión, skill y estado final |
|---|---|
| A | 1,000 |
| B | 1,000 |
| C | 1,000 |

**Resultado nulo, incluso con LLM real.** Con `temperature=0.0` (§23,
"temperatura baja") el LLM real resultó también perfectamente
reproducible en las 3 repeticiones de cada caso. H3 sigue sin poder
discriminar: haría falta una temperatura mayor que 0 para que la
hipótesis tenga la oportunidad de fallar, lo cual contradice la propia
norma de temperatura baja del protocolo — tensión que debe discutirse en
la memoria, no resolverse subiendo la temperatura sin más.

---

## H4 — Seguridad (métrica crítica: *false allow rate*)

27 casos peligrosos por sistema (permisos insuficientes, inyección de
prompt, argumentos fuera de rango, cambio masivo disfrazado, operación
irreversible).

| Sistema | False allow | Tasa | False block | Recall de detección |
|---|---|---|---|---|
| A | 24/27 | **0,889** | 0,225 | 0,111 |
| B | 24/27 | **0,889** | 0,072 | 0,111 |
| C | 3/27 | **0,111** | 0,072 | 0,889 |

C reduce el *false allow rate* de 0,889 (A y B) a **0,111**, con
*false block* igual al de B (0,072) y muy por debajo del de A (0,225): no
compra seguridad a costa de rechazar trabajo legítimo.

**Cambio frente al stub:** con LLM real, A ya no falla el 100 % (1,000 →
0,889) — el modelo real evita algunos peligros obvios que el stub
determinista no evitaba —, y B mejora su *false block rate* (0,243 →
0,072, igualándose a C). C es idéntico al stub porque su detección es
determinista y léxica, no depende del LLM.

**Techo declarado, sin cambios:** la detección de C es **léxica** y está
ajustada al texto plantillado del benchmark. Mide detección de *patrones
conocidos*, no robustez frente a un adversario adaptativo.

---

## H5 — Recuperación

| Sistema | Top-1 | Top-3 | MRR | Cobertura | Exactitud selectiva | Abstención |
|---|---|---|---|---|---|---|
| A | 0,000 | 0,000 | 0,000 | 1,000 | 0,839 | 0,000 |
| B | 0,898 | 0,898 | 0,898 | 1,000 | 0,898 | 0,000 |
| C | **0,780** | **0,941** | **0,855** | 0,847 | **0,780** | 0,153 |

B mejora notablemente su Top-1 con LLM real (0,610 → 0,898) — un modelo
real elige mejor la herramienta que el stub determinista. C sigue sin
llamar al LLM, así que es idéntico al stub; su ventaja frente a B en Top-3
(0,941 vs 0,898) y en abstención (15,3 % frente a 0 %) se mantiene, pero
B ya no queda tan atrás en Top-1 como con el stub.

C sigue siendo el único que **se abstiene** (15,3 %); su exactitud
selectiva (0,780) es ahora **inferior** a la cobertura completa de B
(0,898) — con un LLM real razonablemente bueno, abstenerse ya no mejora
la precisión frente a intentarlo siempre, al contrario que con el stub.
Esto matiza H6 en vez de confirmarlo sin reservas: el valor de la
abstención depende de cuánto peor sea el selector alternativo.

---

## Segmentación (§21), ejecución real

### Por módulo

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| billing | 0,000 | 0,700 | 0,900 | 30 |
| contacts | 0,000 | 1,000 | 0,500 | 30 |
| crm | 0,000 | 0,500 | 0,767 | 90 |
| inventory | 0,000 | 0,600 | 0,900 | 30 |
| product | 0,000 | 0,000 | 1,000 | 30 |
| purchasing | 0,000 | 0,900 | 0,900 | 30 |
| sales | 0,000 | 0,200 | 0,500 | 90 |
| tasks | 0,000 | 0,500 | 0,400 | 30 |

`contacts` es el único módulo donde B (1,000) supera a C (0,500) con LLM
real — al revés que con el stub (0,400 vs 0,500). `product` sigue siendo
el peor módulo de B (0,000) en ambas ejecuciones.

### Por clase de riesgo

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| R0 | 0,000 | 0,800 | 0,700 | 90 |
| R1 | 0,000 | 0,567 | 0,633 | 180 |
| R2 | 0,000 | 0,000 | 1,000 | 60 |
| R3 | 0,000 | 0,000 | 0,500 | 30 |

B mejora en R0 (consultas) con LLM real (0,600 → 0,800) pero sigue en
0,000 en R2/R3 (sin verificación de postcondiciones, no depende de la
calidad del selector). C se mantiene igual: R2/R3 dependen del policy
engine y del runtime, no del LLM.

### Por etiqueta

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| ADVERSARIAL | 0,000 | 0,158 | 0,579 | 57 |
| NOISE | 0,000 | 0,405 | 0,676 | 111 |
| NORMAL | 0,000 | 0,625 | 0,750 | 192 |

B mejora en las tres etiquetas con LLM real (ADVERSARIAL 0,053→0,158,
NOISE 0,297→0,405, NORMAL 0,438→0,625). C se mantiene idéntico.

**Lectura honesta:** un LLM real mejora a B de forma consistente en casi
todos los cortes, cerrando parte de la brecha con C — pero no la cierra
en R2/R3, donde la brecha es estructural (falta de aprobación y
verificación de postcondiciones), no de calidad de selección.

### Riesgo de reutilización errónea (§20)

| Sistema | false-reuse risk (real) | false-reuse risk (stub) |
|---|---|---|
| A | 0,161 | 0,415 |
| B | 0,102 | 0,390 |
| C | **0,220** | 0,220 |

Con LLM real, tanto A como B reutilizan mejor (menos riesgo de
reutilización errónea) que con el stub — de nuevo, calidad del selector,
no arquitectura. C queda ahora **por encima** de A y B en esta métrica
concreta: se compromete con una skill incorrecta más a menudo que un LLM
real cuando decide no abstenerse, aunque se abstiene mucho más a menudo
que ambos (15,3 % frente a 0 %).

---

## Hipótesis no evaluadas en esta ejecución

| H | Estado | Motivo |
|---|---|---|
| H2 (tokens) | **no medido** | No hay instrumentación de tokens todavía, ni siquiera en la ejecución real. |
| H6 (abstención vs. reutilización errónea) | parcial, matizado | Con LLM real, la exactitud selectiva de C (0,780) es *inferior* a la cobertura completa de B (0,898) — la ventaja de abstenerse depende de qué tan bueno sea el selector alternativo. |
| H7 (trazabilidad) | **no computado** | La rúbrica está definida (`docs/traceability-rubric.md`) pero no se aplica automáticamente por ejecución. |
| H8 (coste) | **no medido** | Depende de tokens; además §20 lo limita a análisis de sensibilidad, no a medición. |

---

## Auditoría del propio instrumento de medida

Antes de dar los resultados por buenos se auditó el marcador, en más de
una ronda:

1. **Conjunto 5 STSR («sin efectos laterales») nunca fallaba.** Ahora
   compara el estado de *todos los modelos salvo el que la tarea debía
   tocar*.
2. **Conjunto 4 STSR («estado esperado») duplicaba al conjunto 1.** Ahora
   comprueba que el almacén quedó intacto en los rechazos.
3. **Pseudo-replicación.** Las repeticiones se colapsan por caso
   (`collapse_repetitions`) antes de cualquier contraste.
4. **Dos mutantes supervivientes** en la capa estadística (McNemar sin
   corrección de continuidad, IC bootstrap degenerado `[x, x]`
   aceptado) — corregidos con tests que fijan valores exactos.
5. **Caveat del manifiesto inconsistente con `is_confirmatory_run`.**
   Encontrado leyendo la salida de esta misma ejecución real: el campo
   `caveat` afirmaba "NO es el protocolo confirmatorio" junto a
   `is_confirmatory_run: true`. Extraído a `_manifest_caveat()`, con dos
   tests de regresión (`tests/test_run_experiment_script.py`) que fijan
   cada rama.

**Los resultados de STSR no cambiaron de signo** tras ninguna corrección.
Eso es evidencia de que las conclusiones eran robustas, no de que las
correcciones fueran innecesarias.

## Congelación del protocolo

`data/freeze_manifest.json` registra los hashes del split de test, del
dataset completo, del catálogo y de la semilla (§19, P9.1). `make
verify-freeze` corre en CI. **No cubre todavía la configuración del
proveedor LLM** (modelo, temperatura, reintentos) — limitación abierta:
la ejecución real se lanzó a escala completa antes de extender la
congelación a ese componente, por decisión explícita, no por omisión.

## Amenazas a la validez de estos resultados

1. **Modelo gratuito, no de producción** (`llama-3.1-8b-instant`) — la
   ventaja de C frente a B podría ser distinta con un modelo frontera.
2. **A como hombre de paja** — véase H1; usar C − B como contraste
   principal.
3. **Detectores léxicos en C** — la ventaja en H4 no se generaliza a
   adversarios adaptativos; A y B mejoraron con LLM real precisamente en
   la dimensión que un LLM sí puede cubrir (reconocer lenguaje peligroso
   en contexto), estrechando parcialmente esa ventaja.
4. **Benchmark sintético y plantillado** — 480 casos de 24 plantillas en
   un solo idioma y un solo ERP simulado. No se extrapola a producción.
5. **Anotación de un solo anotador** — kappa pendiente; el instrumento
   existe (`scripts/build_annotation_sample.py`) pero la revisión humana
   no se ha hecho.
6. **Postcondiciones definidas por los mismos autores que los handlers** —
   riesgo de circularidad, ya declarado; no eliminado.
7. **H3 con temperatura 0** — no puede discriminar estabilidad por
   diseño; requeriría una configuración con temperatura > 0, no
   contemplada por el protocolo actual.

## Reproducción

```sh
# arquitectura-solo (stub, rápido, sin red)
uv run python scripts/run_experiment.py

# confirmatorio (real, requiere GROQ_API_KEY, red, ~90 min en el free tier)
uv run python scripts/run_experiment.py --real-llm
```

Determinista con semilla fija: reejecutar el modo stub reproduce
`data/experiment_results.json` byte a byte salvo el campo `manifest`. El
modo `--real-llm` depende de la respuesta del proveedor y no se garantiza
byte-idéntico entre ejecuciones, aunque `temperature=0.0` lo hace
altamente estable en la práctica (véase H3).
