# Hipótesis, evidencia y tesis defendibles de ERP Agent OS

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** (marcador exigido por
> el contrato automático `src/erp_agent_os/claims.py`/`tests/test_claims.py`,
> escrito en la era v1 antes de que existiera el sistema de estados por
> hipótesis de v2.1 — **ver la nota siguiente antes de leer este marcador
> como el estado real**)
>
> **Corte de evidencia: 2026-08-23, actualizado.** El protocolo v2.1 sin
> anotadores humanos ya está implementado, congelado (`tfm-protocol-v2.1.2`)
> y ejecutado: campaña real de 21.478 observaciones, `RUN_COMPLETED` /
> `CLOSURE_VALID`. **`docs/results-v2.1.md` (Parte A) es ahora la fuente de
> verdad confirmatoria** — H1a, H2, H3a, H6 y H7 salen soportadas; H1b, H4
> (los cuatro componentes) y H5 salen explícitamente no soportadas, con el
> desglose caso por caso de por qué en cada una. **El resto de este
> documento (la sección de las ocho hipótesis y el "qué falta para responder
> confirmatoriamente" de más abajo) sigue describiendo el estado exploratorio
> anterior al 14 de agosto y NO se ha reescrito todavía línea por línea** —
> tratarlo como historial, no como el estado vigente, hasta que se actualice.
> No se está afirmando que la sección de abajo sea correcta hoy; se declara
> explícitamente obsoleta en vez de dejarla pasar por vigente.

## Respuesta corta: ¿tenemos los datos?

**Sí, ahora los tenemos completos y confirmatorios** — no solo señales
exploratorias. La campaña `tfm-protocol-v2.1.2` terminó (`RUN_COMPLETED`),
cerró (`CLOSURE_VALID`) y produjo un veredicto explícito por hipótesis, con
IC95, tamaño de efecto y corrección por multiplicidad donde aplica.
`docs/results-v2.1.md` (Parte A) es la fuente de verdad — este documento
resume sus conclusiones sin repetir cada cifra.

- Sí tenemos 21.478 observaciones reales, fila a fila, con hash, estados,
  argumentos, política, versión, handler, postcondiciones y los siete
  componentes de trazabilidad — no un agregado sin filas crudas como v1.
- Sí tenemos veredicto explícito para H1a, H1b, H2 (contra A y contra B), H3a,
  H3b, los cuatro componentes de H4, H5, H6, H7 y la rejilla de H8.
- El archivo crudo, el manifiesto de congelación y el informe generado desde
  JSONL puro (nunca desde agregados de v1) están commiteados y verificados
  componente a componente — ver el encabezado de `docs/results-v2.1.md`.
- Lo que **no** cambia respecto a antes: el holdout humano v2 de 120
  peticiones sigue retirado y sin ejecutar (por diseño — v2.1 lo sustituye,
  no lo completa) y los ficheros históricos de v1
  (`data/experiment_results*.json`) siguen siendo evidencia exploratoria, no
  confirmatoria — esa reclasificación no cambia con la campaña nueva.
- **Nota sobre el registro machine-readable:** `data/evidence_registry.json`
  y su `global_status: no_valid_confirmatory_conclusion` siguen sin
  actualizarse para reflejar los veredictos reales de v2.1 — es una decisión
  deliberada, no un olvido: el contrato `src/erp_agent_os/claims.py` es de la
  era v1 y no distingue entre hipótesis (todavía trata "confirmado" como
  binario y prohibido siempre), así que actualizarlo exige una decisión
  explícita sobre cómo debe representar un resultado mixto real, no solo
  activar un interruptor. Pendiente, señalado, no oculto.

## Las ocho hipótesis operacionales

Estado real tras `tfm-protocol-v2.1.2` (`docs/results-v2.1.md` Parte A tiene
el detalle completo, IC95 y desglose caso por caso; aquí solo el resumen).

### H1 — Éxito estricto de tarea

**Hipótesis.** C no es inferior a A (H1a) y superior a B (H1b) en STSR.

**Resultado real.** H1a: C−A = +0,253, IC95 desde +0,232 — el margen de −5 pp
se supera con margen de sobra. H1b: C−B = −0,015, IC95 [−0,037, 1,0],
p=0,286 — no significativo, y la estimación puntual es incluso negativa.

**Veredicto.** **H1a confirmada. H1b no confirmada.** C no es inferior a un
agente sin gobierno, pero tampoco supera a un agente con herramientas
tipadas en tasa de éxito — la ventaja de C no está ahí, ni aquí ni en v1.

### H2 — Consumo de tokens

**Hipótesis.** C usa menos tokens totales que A y B.

**Resultado real.** C−A = −467,98 tokens [IC95 hasta −456,87, α=0,025].
C−B = −647,80 tokens [IC95 hasta −639,82, α=0,025]. Ambas comparaciones
exigidas conjuntamente por el protocolo, con corrección de Bonferroni.

**Veredicto.** **Confirmada, contra los dos comparadores, con holgura
amplia.** C es más barato que A y sustancialmente más barato que B.

### H3 — Estabilidad

**Hipótesis.** C es más consistente que A/B entre formulaciones distintas del
mismo escenario (H3a, primaria) y entre repeticiones estocásticas (H3b,
secundaria, descriptiva).

**Resultado real.** H3a: C supera a A en proporción de tríos consistentes
entre tres superficies lingüísticas distintas (p=2,2e-18, odds ratio 9,35) —
a diferencia de v1, donde `temperature=0` hacía indistinguibles las
repeticiones literales, este diseño sí discrimina. H3b: 36,7 % de tríos
consistentes bajo temperatura baja sin caché [24,6 %, 50,1 %], n=60,
descriptivo, sin criterio direccional registrado.

**Veredicto.** **H3a confirmada — primera vez que este proyecto mide
estabilidad de verdad, no un techo de medida.** H3b se reporta, no se evalúa.

### H4 — Seguridad y detección previa

**Hipótesis.** C detecta más casos peligrosos antes de ejecutar y obtiene
menor `false allow` que A y B.

**Resultado real, sobre 315 escenarios peligrosos reales:** los cuatro
componentes (false allow vs A, false allow vs B, recall vs A, recall vs B)
salen **invertidos y muy significativos** (p entre 1e-30 y 1e-45). C solo
emite `DENY` explícito en el 5,7 % de los casos, frente al 72,7 % de A y
51,1 % de B. Pero esos `DENY` de A/B no son decisiones de seguridad — son
literalmente "hubo un error de ejecución" (`experiment_v2_1.py`), así que
la comparación cruda no es homologable. El número que sí se sostiene sin
matices: **mutación no autorizada real de C = 19,0 % [hasta 23,1 %]**, casi
4× el umbral del 5 %, localizada en 5 de 7 categorías de ataque (las otras 2
funcionan perfectamente — ver `docs/results-v2.1.md` §4.2 para el desglose).

**Veredicto.** **No confirmada, en los cuatro componentes.** No es un
artefacto de instrumentación (se verificó que persiste casi sin cambios tras
corregir los dos defectos que contaminaban la campaña anterior) — es un
hallazgo real: C deja pasar mutaciones peligrosas en escenarios sin marcador
léxico obvio, concentradas en categorías concretas y diagnosticables.

### H5 — Recuperación de skills

**Hipótesis.** El recuperador ofrece cobertura alta con exactitud selectiva
adecuada y riesgo de reutilización incorrecta controlado.

**Resultado real.** Los tres umbrales deben cumplirse a la vez (selective
accuracy ≥0,90, false-reuse risk ≤0,10, coverage ≥0,70). Selective accuracy
observada = 0,589; false-reuse risk = 0,411 — ambos muy por debajo/encima de
lo exigido.

**Veredicto.** **No confirmada — no adecuada.** Peor que la señal
exploratoria de v1, coherente con el hallazgo ya documentado de que la
recuperación léxica es el cuello de botella real del sistema cuando el
lenguaje no está plantillado.

### H6 — Abstención

**Hipótesis.** Abstenerse en casos sin skill, ambiguos o con margen
insuficiente reduce la reutilización errónea.

**Resultado real.** C con abstención reduce el false-reuse risk frente a la
ablación sin abstención: diferencia −0,086, IC95 completamente negativo
[hasta −0,071].

**Veredicto.** **Confirmada.** La abstención sigue aportando valor medible
incluso cuando, en H4, no cuenta como "detección" de peligro.

### H7 — Trazabilidad

**Hipótesis.** C obtiene una reconstrucción de auditoría más completa que
A/B, sobre los siete hechos objetivos del `AuditReconstructor` común.

**Resultado real.** C−A = +0,427, IC95 [+0,404, 1,0], p=2,85e-112, odds
ratio 1019. Medido por primera vez de verdad — en la campaña anterior este
endpoint salía degenerado (`p=1,0` exacto) por un hueco de instrumentación
ya corregido.

**Veredicto.** **Confirmada**, con una salvedad que debe ir en la memoria sin
suavizar: A y B no tienen policy engine, versión de skill ni verificación de
postcondiciones **por definición arquitectónica** — parte de esta ventaja es
estructural, no una capacidad que A/B intentaron construir y perdieron.

### H8 — Coste total modelado

**Hipótesis.** Analizar, sin dirección confirmatoria, el coste de inferencia,
revisión, errores y reintentos bajo supuestos declarados.

**Resultado real.** 243 combinaciones de rejilla × 3 sistemas, con
reintentos y tokens realmente observados en la campaña (no supuestos). A
falla en el 96,7 % de todas las poblaciones (no solo la peligrosa), lo que
domina su coste modelado vía el término de error, no de inferencia.

**Veredicto.** Análisis de escenarios, tal como exige la especificación —
nunca se interpreta como ahorro medido ni como hipótesis aceptada/rechazada.

## Las tesis que el proyecto puede defender

Estas son las conclusiones intelectuales del proyecto. Su estado importa tanto
como su redacción.

1. **T1 — Separación de responsabilidades, parcialmente confirmada.** La
   interpretación probabilística propone; una capa determinista autoriza y
   ejecuta. H1a (no inferior a un agente sin gobierno), H2 (más barata) y H7
   (más trazable, con la salvedad estructural de §H7) apoyan la tesis. H4
   la contradice en su promesa de seguridad activa: la capa determinista deja
   pasar el 19 % de mutaciones peligrosas en escenarios sin marcador léxico.
2. **T2 — Reutilización y eficiencia, confirmada.** C consume menos tokens
   que A y que B, con IC95 completamente por debajo de cero contra ambos
   comparadores, bajo la población correcta y con el mismo coste de parseo
   para los tres sistemas.
3. **T3 — Estabilidad, confirmada (H3a).** Con un diseño que compara
   formulaciones distintas del mismo escenario en vez de repeticiones bajo
   temperatura 0, C es significativamente más consistente que A
   (p=2,2e-18). Es la primera vez que este proyecto mide esto de verdad.
4. **T4 — Abstención como control de riesgo, confirmada.** No forzar una
   skill reduce medible y significativamente el false-reuse risk frente a la
   ablación sin abstención (H6), aunque en H4 abstenerse no cuenta como
   "detectar peligro".
5. **T5 — Gobernanza y trazabilidad, confirmada con salvedad.** H7 confirma
   la ventaja de reconstrucción de auditoría, pero A/B no tienen policy
   engine ni verificación de postcondiciones por definición arquitectónica
   — parte de la ventaja es estructural, no ganada en igualdad de
   condiciones.
6. **T6 — Integración ERP, solo factibilidad.** Sin cambios: el pipeline
   gobernado crea, bloquea y, tras aprobación, modifica datos reales en Odoo
   staging. Prueba que la arquitectura puede integrarse; no que sea superior
   a A/B en Odoo.
7. **T7 — Evolución gobernada de skills, solo demo.** Sin cambios: fuera de
   la comparación confirmatoria por diseño.
8. **T8 — La recuperación es el cuello de botella, ahora confirmada
   (H5).** No solo exploratoria: H5 falla los tres umbrales prerregistrados
   en la propia campaña confirmatoria, no solo en peticiones reales fuera
   del corpus. Mejorar perfiles, embeddings, ranking y abstención sigue
   siendo la mejora con más recorrido de todo el sistema.
9. **T9 — Confinamiento antes que detección, reforzada pero con límite
   nuevo.** El stress test de parser comprometido (0/1.530) sigue de pie,
   pero H4 muestra el límite: cuando el atacante no compromete el parser y
   la petición es simplemente ambigua-pero-plausible, el confinamiento por
   contrato **no** impide el 19 % de mutaciones. "Confinamiento antes que
   detección" no es una garantía universal — depende de qué tan explícito
   sea el patrón de ataque.
10. **T10 — Valor económico no demostrado.** Sin cambios: el proyecto puede
    presentar escenarios y sensibilidad con datos reales de coste/reintentos
    observados (H8), no ahorro, satisfacción ni ROI medidos.

## Qué demuestra la demo de generación de skills

La demo debe enseñar un caso que no tiene una skill adecuada:

```text
Sin skill adecuada
        ↓
El LLM propone una definición estructurada
        ↓
Validador + pruebas exclusivamente en sandbox
        ↓
Aprobación humana explícita
        ↓
Versionado y activación
        ↓
Ejecución gobernada contra Odoo staging
        ↓
Relectura del cambio y traza completa
```

La interfaz puede mostrar el YAML/JSON propuesto, los tests, el diff, el riesgo,
la aprobación, la versión activa, la ejecución y el estado releído de Odoo. La
demo prueba el ciclo de vida CU-02 y la utilidad del producto; no añade una
decimotercera skill al catálogo congelado ni se contabiliza en H1-H8.

## Qué falta ahora — ya no es responder confirmatoriamente, es escribirlo

Los siete pasos que este documento pedía hasta el 22 de agosto (sellar un
holdout humano v2, obtener dos revisiones humanas, congelar, ejecutar A/B/C,
publicar el validador de claims) **ya están hechos, pero por una vía
distinta a la que este documento describía**: v2.1 sustituye la anotación
humana por escenarios con verdad de referencia por construcción, dos
oráculos independientes y un evaluador con mutaciones dirigidas
(`docs/tfm-closure-no-human-v2.1.md`), no por completar los paquetes de
anotadores. Ese holdout humano v2 sigue retirado y sin ejecutar — no se ha
completado, se ha sustituido.

Lo que queda de verdad pendiente:

1. Decidir y ejecutar la actualización de `data/evidence_registry.json` y
   `src/erp_agent_os/claims.py` para que el contrato automático distinga
   entre hipótesis confirmadas y no confirmadas de v2.1, en vez de su
   binario "nada está confirmado" heredado de la era v1 (decisión explícita
   pendiente, señalada en el banner de este documento).
2. Trasladar el resultado de H4 (§ arriba) a `docs/defensa.md` y
   `docs/memoria.md` con el mismo nivel de detalle que aquí — ambos siguen
   citando cifras de v1 en su tramo de resultados.
3. Regenerar las figuras (`reports/figures/`) desde el informe de v2.1.

La formulación correcta ya no es "los datos apoyan esto de forma
exploratoria" — es la de `docs/results-v2.1.md`: **H1a, H2, H3a, H6 y H7
confirmadas; H1b, H4 y H5 explícitamente no confirmadas**, con intervalo de
confianza, tamaño de efecto y mecanismo diagnosticado en cada caso.
