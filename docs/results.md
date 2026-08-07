# Resultados experimentales

Dos ejecuciones, mismo protocolo (`uv run python scripts/run_experiment.py
[--real-llm --provider {groq,gemini,openrouter}]`): **1.080 ejecuciones**
(120 casos de test congelado × 3 sistemas × 3 repeticiones), semilla
`20260805`, estado de `FakeERPAdapter` reconstruido por observación.

1. **Ejecución confirmatoria real** (`data/experiment_results.json`,
   `manifest.selector: "OpenRouterClient"`, `is_confirmatory_run: true`)
   — A y B llaman a OpenRouter (`openai/gpt-oss-20b:free`, temperatura 0)
   igual que exige D-03; C no llama al LLM (su recuperación es TF-IDF),
   así que sus métricas son **idénticas** entre esta ejecución y la
   arquitectura-solo — no es un error, es la arquitectura.
2. **Ejecución arquitectura-solo** (histórica, selector determinista
   compartido) — aísla gobernanza de calidad del modelo. Se conserva
   como contraste porque muestra cuánto de la ventaja de C sobrevive
   incluso cuando A/B tienen un selector perfecto.

> ## Estado del protocolo confirmatorio de §19
>
> **Esto SÍ es el protocolo confirmatorio.** Limitación declarada: modelo
> gratuito (`openai/gpt-oss-20b:free` vía OpenRouter), no un modelo
> frontera/de producción — se declara en la memoria, no se oculta.
>
> **Historial de proveedor, por transparencia.** El primer intento
> confirmatorio usó Groq (`llama-3.1-8b-instant`) y **completó** una
> corrida entera (documentada en una entrada anterior de la bitácora).
> Al añadir instrumentación de tokens (H2) y trazabilidad (H7) hubo que
> relanzar, y la cuota diaria de Groq (500k tokens) se agotó por los
> reintentos previos a tener checkpoint. Se probó Gemini (dos modelos
> distintos, ambos con tope de **20 peticiones/día por modelo** en esta
> cuenta — inviable para las ~240 llamadas reales necesarias). La
> ejecución que finalmente completó con la instrumentación nueva usó
> **OpenRouter**. Es la que se reporta aquí como la vigente; los números
> de la corrida Groq anterior (sin H2/H7) quedan superados, no se citan.
>
> La congelación (`data/freeze_manifest.json`) todavía no cubre la
> configuración del proveedor (modelo, temperatura, reintentos) — es
> una limitación abierta, no un descuido.

---

## Pregunta de investigación

> ¿Puede una arquitectura que separa la interpretación probabilística del
> modelo de lenguaje de la ejecución determinista reducir errores,
> consumo de tokens y variabilidad, manteniendo o mejorando la tasa de
> éxito en automatizaciones ERP?

**Respuesta, con un LLM real:** sí en errores de seguridad y éxito de
tarea, incluso cuando el propio LLM mejora (B sube a 0,517 con este
selector real frente a 0,333 con el stub, C sigue por encima); **sí
medido por primera vez** en tokens (H2) — C consume 0 frente a ~200-230
de A/B; H3 (estabilidad) resulta trivialmente 1,0 con temperatura 0, así
que no discrimina aquí.

---

## H1 — Strict Task Success Rate

| Sistema | STSR (real, OpenRouter) | STSR (stub, arquitectura-solo) |
|---|---|---|
| A (agente directo) | **0,000** | 0,000 |
| B (herramientas tipadas) | **0,517** | 0,333 |
| C (ERP Agent OS) | **0,700** | 0,700 |

| Contraste (real) | Diferencia | IC 95 % | Holm *p* | Odds ratio |
|---|---|---|---|---|
| C − A | **+0,700** | [+0,617, +0,783] | 2,71 × 10⁻¹⁹ | 169,0 |
| C − B | **+0,183** | [+0,058, +0,308] | 7,65 × 10⁻³ | 2,07 |

Q de Cochran = 109,46 (gl = 2).

> **Unidad de inferencia: el caso, no la ejecución.** Las 1.080
> ejecuciones son 120 casos × 3 sistemas × 3 repeticiones, pero las
> repeticiones de un mismo caso **no son observaciones independientes**.
> Se colapsan por caso (mayoría) antes de cualquier contraste
> (`collapse_repetitions`).

**H1 (no inferioridad de C frente a A, margen −5 pp): se acepta.** Límite
inferior del IC (+0,617) muy por encima de −0,05; C es netamente
superior.

**C − B sigue significativo, pero es el margen más estrecho medido hasta
ahora** (Holm *p* = 7,65 × 10⁻³, OR = 2,07). Con cada selector real
probado, B mejora (0,333 stub → 0,483 Groq → 0,517 OpenRouter): la
calidad del selector explica una parte creciente de la ventaja
observada con el stub, y el contraste que sobrevive de verdad a esa
mejora es el estructural — R2/R3, donde B se queda en 0,000
pase lo que pase (ver segmentación).

### Por qué A obtiene exactamente 0,000

Sigue siendo 0 con LLM real, por la misma razón estructural en las tres
ejecuciones: A dispone de `create_record` genérico y **ningún contrato
que codifique la regla de negocio**, así que aunque el LLM elija bien el
modelo y los argumentos, el registro resultante no cumple postcondiciones
como `opportunity_is_open`. STSR lo detecta porque exige estado final
correcto, no una llamada plausible.

---

## H2 — Tokens (medido por primera vez con datos reales)

| Sistema | Tokens totales | Media por ejecución |
|---|---|---|
| A | 71.364 | 198,2 |
| B | 82.925 | 230,3 |
| C | **0** | **0,0** |

C − B = −230,3 IC95 [−235,1, −225,96]; C − A = −198,2 IC95 [−204,3,
−192,2]. C no consume tokens porque su recuperación es TF-IDF, no LLM —
es una diferencia arquitectónica limpia, no un artefacto de medición.
Nota honesta: esto no significa "C es gratis" en sentido absoluto — el
parser de intención (`structure_proposal`) en el pipeline de producción
completo requeriría su propia llamada a LLM, que aquí se toma como ya
resuelta (§5.4 del roadmap, work unit 7: "IntentProposal tomada como ya
producida").

---

## H3 — Estabilidad entre repeticiones

| Sistema | Coincidencia de decisión, skill y estado final |
|---|---|
| A | 1,000 |
| B | 1,000 |
| C | 1,000 |

**Resultado nulo, en las tres ejecuciones con LLM real probadas
(Groq, ahora OpenRouter).** Con `temperature=0.0` (§23) el LLM real
resultó también perfectamente reproducible. H3 sigue sin poder
discriminar: haría falta temperatura > 0, lo cual contradice la propia
norma de temperatura baja del protocolo.

---

## H4 — Seguridad (métrica crítica: *false allow rate*)

27 casos peligrosos por sistema.

| Sistema | False allow | Tasa | False block | Recall de detección |
|---|---|---|---|---|
| A | 9/27 | **0,333** | 0,468 | 0,667 |
| B | 24/27 | **0,889** | 0,018 | 0,111 |
| C | 3/27 | **0,111** | 0,072 | 0,889 |

C reduce el *false allow rate* a **0,111**, muy por debajo de B (0,889).

**Dato que cambia según el proveedor, reportado sin maquillar:** con
Groq, A tenía false-allow 0,889 (igual de malo que B); con OpenRouter,
A baja a 0,333 y su *recall* de detección sube a 0,667 — casi al nivel
de C. Esto no es una mejora de C ni de B: es que este modelo concreto,
sin ningún policy engine, reconoce mejor lenguaje peligroso en el propio
texto de la petición. Es una diferencia real entre modelos, no un
defecto de medición, y hace más frágil cualquier afirmación de que "A es
sistemáticamente inseguro" — depende del LLM subyacente. La ventaja
estructural de C (recall 0,889, sin depender de qué LLM esté detrás)
sigue siendo el argumento más sólido, no el fallo garantizado de A.

---

## H5 — Recuperación

| Sistema | Top-1 | Top-3 | MRR | Cobertura | Exactitud selectiva | Abstención |
|---|---|---|---|---|---|---|
| A | 0,000 | 0,000 | 0,000 | 1,000 | 0,305 | 0,000 |
| B | 0,890 | 0,890 | 0,890 | 1,000 | 0,890 | 0,000 |
| C | **0,780** | **0,941** | **0,855** | 0,847 | **0,780** | 0,153 |

B mantiene un Top-1 alto (0,890) con este selector real, similar a lo
visto con Groq. C sigue sin llamar al LLM, así que es idéntico en todas
las ejecuciones reales.

**A: exactitud selectiva cayó a 0,305 (false-reuse risk 0,695)** con
este modelo — mucho peor que con Groq (0,839 / 0,161). A no tiene
recuperación real (elige entre 3 herramientas genéricas, no 12 skills),
así que esta métrica mide sobre todo si el modelo mapea bien el tipo de
operación (`create`/`update`/`get`) al modelo de datos correcto — y este
modelo lo hace peor que Groq en ese mapeo concreto. Diferencia de
calidad de modelo, no de arquitectura.

---

## H7 — Trazabilidad (medido por primera vez con datos reales)

| Sistema | Puntuación media (0–1) |
|---|---|
| A | 0,19 |
| B | 0,36 |
| C | **0,80** |

Rúbrica ponderada de 7 componentes (`docs/traceability-rubric.md`,
`src/erp_agent_os/traceability.py`), calculada por ejecución a partir de
evidencia real de auditoría, no volumen de logs. A y B puntúan bajo en
*policy_decision*, *skill_version_and_key* y
*postcondition_or_block_evidence* **por construcción**: no tienen policy
engine, no tienen skills versionadas, no tienen almacén de auditoría
(§18). Es la brecha de gobernanza documentada hecha medible, no un
defecto del calculador.

---

## H8 — Coste (análisis de sensibilidad, no ahorro medido)

Con la tarifa declarada de 0,05 USD/1.000 tokens (supuesto explícito,
no precio real de ningún proveedor gratuito):

| Sistema | Coste de inferencia estimado |
|---|---|
| A | $3,57 |
| B | $4,15 |
| C | **$0,00** |

Sobre 120 casos × 3 repeticiones. Se reporta como escenario, no como
ahorro observado (§20 lo exige así explícitamente).

---

## Segmentación (§21), ejecución real (OpenRouter)

### Por módulo

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| billing | 0,000 | 0,600 | 0,900 | 30 |
| contacts | 0,000 | 1,000 | 0,500 | 30 |
| crm | 0,000 | 0,533 | 0,767 | 90 |
| inventory | 0,000 | 0,600 | 0,900 | 30 |
| product | 0,000 | 0,000 | 1,000 | 30 |
| purchasing | 0,000 | 0,900 | 0,900 | 30 |
| sales | 0,000 | 0,200 | 0,500 | 90 |
| tasks | 0,000 | 0,900 | 0,400 | 30 |

`contacts` sigue siendo el único módulo donde B (1,000) supera a C
(0,500). `tasks` es nuevo: B sube a 0,900 con este selector (era 0,000
con el stub, 0,500 con Groq) — muy sensible a la calidad del LLM
concreto.

### Por clase de riesgo

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| R0 | 0,000 | 0,800 | 0,700 | 90 |
| R1 | 0,000 | 0,633 | 0,633 | 180 |
| R2 | 0,000 | 0,000 | 1,000 | 60 |
| R3 | 0,000 | 0,000 | 0,500 | 30 |

**El patrón más importante del TFM se confirma una tercera vez con un
tercer proveedor:** B se queda en 0,000 en R2 y R3 **sin importar qué
LLM esté detrás** — no es un problema de calidad de selección, es la
ausencia estructural de aprobación y verificación de postcondiciones.
C es el único que ejecuta correctamente operaciones de alto riesgo.

### Por etiqueta

| Estrato | A | B | C | n (por sistema) |
|---|---|---|---|---|
| ADVERSARIAL | 0,000 | 0,158 | 0,579 | 57 |
| NOISE | 0,000 | 0,405 | 0,676 | 111 |
| NORMAL | 0,000 | 0,688 | 0,750 | 192 |

### Riesgo de reutilización errónea (§20)

| Sistema | false-reuse risk |
|---|---|
| A | 0,695 |
| B | 0,110 |
| C | 0,220 |

---

## Hipótesis, estado final

| H | Estado |
|---|---|
| H1 | **Confirmada**, C−A y C−B significativos en las tres ejecuciones reales probadas |
| H2 | **Medida por primera vez**: C=0, A/B ~200-230 tokens/ejecución |
| H3 | **Nula por diseño**: temperatura=0 exigida por §23 impide discriminar |
| H4 | **Confirmada**: C recall 0,889 estable entre proveedores; A/B varían según el LLM |
| H5 | **Parcial**: C gana en Top-3/abstención; Top-1/exactitud selectiva dependen del LLM de A/B |
| H6 | **Matizada**: el valor de abstenerse depende de qué tan bueno sea el selector alternativo |
| H7 | **Medida por primera vez**: C=0,80 frente a A=0,19/B=0,36, brecha de gobernanza confirmada |
| H8 | **Análisis de sensibilidad**, no ahorro medido, tal como exige §20 |

---

## Auditoría del propio instrumento de medida

Nueve defectos encontrados y corregidos por auditoría propia a lo largo
del proyecto (detalle completo en `docs/audit.md` y la bitácora de
`CLAUDE.md`). Los dos más recientes, ambos en la capa de *reporte*, no
de medición:

8. **Caveat del manifiesto inconsistente con `is_confirmatory_run`** en
   la primera ejecución real (Groq): el texto decía "NO es el protocolo
   confirmatorio" junto a `is_confirmatory_run: true`.
9. **Caveat con el proveedor hardcodeado**: tras corregir el defecto 8,
   el texto seguía diciendo literalmente "Groq free tier" sin importar
   qué proveedor se usara — la ejecución con OpenRouter habría publicado
   un caveat que nombraba a Groq. Corregido pasando el selector real al
   texto en vez de un literal.

Ambos se encontraron **leyendo la salida de la propia ejecución antes de
reportarla**, no por un test que fallara solo. Los resultados numéricos
no cambiaron con ninguna de las dos correcciones — solo el texto
explicativo era incorrecto.

## Amenazas a la validez de estos resultados

1. **Modelo gratuito, no de producción** (`openai/gpt-oss-20b:free`) —
   la ventaja de C frente a B podría ser distinta con un modelo frontera.
2. **Sensibilidad al proveedor concreto**, ahora evidenciada
   empíricamente: false-allow de A pasó de 0,889 (Groq) a 0,333
   (OpenRouter); exactitud selectiva de A pasó de 0,839 a 0,305. Ninguna
   conclusión sobre A o B debe leerse como propiedad del *baseline*
   independiente del modelo que lo ejecuta — solo las propiedades de C
   (recall 0,889, R2/R3 en 1,000/0,500) se mantuvieron estables entre
   los tres proveedores probados.
3. **A como hombre de paja** — véase H1; usar C − B como contraste
   principal.
4. **Detectores léxicos en C** — la ventaja en H4 no se generaliza a
   adversarios adaptativos.
5. **Benchmark sintético y plantillado** — 480 casos de 24 plantillas en
   un solo idioma y un solo ERP simulado.
6. **Anotación de un solo anotador** — kappa pendiente.
7. **Postcondiciones definidas por los mismos autores que los handlers**
   — riesgo de circularidad, ya declarado.
8. **H3 con temperatura 0** — no puede discriminar estabilidad por
   diseño.

## Reproducción

```sh
# arquitectura-solo (stub, rápido, sin red)
uv run python scripts/run_experiment.py

# confirmatorio (real, requiere una API key, red)
uv run python scripts/run_experiment.py --real-llm --provider groq
uv run python scripts/run_experiment.py --real-llm --provider gemini
uv run python scripts/run_experiment.py --real-llm --provider openrouter
```

Cada ejecución `--real-llm` usa un checkpoint propio por proveedor
(`data/checkpoint_real_llm_<provider>.jsonl`, gitignorado) que permite
reanudar sin re-gastar cuota si se interrumpe; se borra automáticamente
al completar. Las repeticiones de un mismo caso reutilizan la primera
llamada real (`CachingLLMClient`), verificado empíricamente reproducible
con temperatura 0 (H3 = 1,0 en las tres ejecuciones reales).
