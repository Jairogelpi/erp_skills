# Hipótesis, evidencia y tesis defendibles de ERP Agent OS

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion**
>
> Corte de evidencia: 14 de agosto de 2026. Actualmente existen señales
> exploratorias, pruebas de factibilidad y resultados descriptivos, pero
> ninguna de H1-H8 puede declararse confirmada. El registro canónico y
> legible por máquina es `data/evidence_registry.json`. El protocolo de cierre
> v2.1 sin anotadores humanos está especificado, pero aún no implementado,
> congelado ni ejecutado.

## Respuesta corta: ¿tenemos los datos?

Tenemos una parte importante de los datos, pero no todavía la evidencia
confirmatoria completa.

- Sí tenemos tres resúmenes A/B/C de 1.080 ejecuciones, métricas de éxito,
  tokens, seguridad, recuperación, estabilidad y trazabilidad.
- Sí tenemos el benchmark sintético de 480 peticiones, el catálogo de 12
  skills, el manifiesto de congelación, pruebas externas de inyección y demos
  contra Odoo 19 de staging.
- Sí tenemos desde ahora un ejecutor que conserva las observaciones futuras
  fila a fila, con hash, estados, argumentos, política, versión, handler,
  postcondiciones y los siete componentes de trazabilidad.
- No tenemos las 1.080 filas crudas de las ejecuciones históricas: solo se
  guardaron sus agregados. No deben reconstruirse artificialmente.
- El test v1 fue inspeccionado y después se corrigieron el parser, el runtime y
  el análisis. Por eso una nueva ejecución sobre v1 sigue siendo exploratoria.
- El archivo de estados observados de v1 es evidencia del sistema, no verdad de
  referencia, y no se completará mediante anotadores humanos.
- El holdout humano v2 de 120 peticiones sigue sin haber sido ejecutado por
  A/B/C. Queda retirado y deberá recibir un artefacto formal de supersesión
  append-only antes de cualquier nueva campaña.
- La especificación `docs/tfm-closure-no-human-v2.1.md` reemplaza la anotación
  por escenarios con verdad por construcción, dos oráculos independientes por
  dependencias, concordancia integral, tests metamórficos y un evaluador con
  mutaciones dirigidas. Esto es diseño normativo pendiente, no resultado.

Los ficheros históricos `data/experiment_results.json`,
`data/experiment_results_groq_given_args.json` y
`data/experiment_results_real_parser.json` contienen un campo antiguo
`is_confirmatory_run: true`. Esa etiqueta queda invalidada por esta auditoría:
son resúmenes agregados post-inspección y se usan solo como evidencia
exploratoria.

## Las ocho hipótesis operacionales

### H1 — Éxito estricto de tarea

**Hipótesis.** C no es inferior a A en STSR, con margen de −5 puntos
porcentuales, sobre 120 casos de test y tres repeticiones.

**Señal observada.** En el último resumen con parser real: A = 0,000; B =
0,483; C = 0,633. C−A = +0,633, IC95 [0,550, 0,717]. C−B = +0,150,
IC95 [0,042, 0,258], McNemar/Holm p = 0,016.

**Veredicto.** No confirmada; señal exploratoria favorable. El margen se
supera en el agregado disponible, pero faltan las filas históricas, el test
dejó de ser no visto y el estado esperado no tiene adjudicación independiente.

### H2 — Consumo de tokens

**Hipótesis.** C usa menos tokens totales que A y B en las peticiones con una
skill esperada.

**Señal observada.** Medias históricas por ejecución: A = 185,1; B = 265,269;
C = 67,622 tokens.

**Veredicto.** No confirmada; señal exploratoria favorable. El cálculo
histórico incluyó 120 casos, aunque la población declarada excluye dos casos
`sin_skill`. El ejecutor ya filtra correctamente los 118 casos, colapsa las
repeticiones y aplica Friedman, Wilcoxon emparejado, Holm, IC95 y tamaños de
efecto, pero falta repetirlo sobre un test prospectivo.

### H3 — Estabilidad entre repeticiones

**Hipótesis.** C obtiene mayor coincidencia del estado final entre sus tres
repeticiones que A y B.

**Señal observada.** A = B = C = 1,000.

**Veredicto.** No evaluable con el diseño actual. A temperatura 0 y con caché,
los tres sistemas son deterministas; el endpoint carece de varianza. El dato no
demuestra igualdad ni superioridad. Antes del siguiente congelado hay que
rediseñar el brazo de estabilidad o aceptar formalmente que H3 queda sin
contraste.

### H4 — Seguridad y detección previa

**Hipótesis.** C detecta más casos peligrosos antes de ejecutar y obtiene menor
`false allow` que A y B.

**Señal observada.** `False allow`: A = 0,889; B = 0,889; C = 0,111. En C,
recall de detección = 0,889 y precision = 0,500. Las 27 observaciones peligrosas
del resumen son tres repeticiones de solo nueve casos únicos.

**Veredicto.** No confirmada; señal exploratoria favorable y con incertidumbre
alta. Además, el detector léxico solo detectó 17/510 casos externos de
InjecAgent (3,3 %). El ensayo de confinamiento registró 0/1.530 mutaciones no
autorizadas, pero es un stress test agregado, no una confirmación de H4.

### H5 — Recuperación de skills

**Hipótesis.** El recuperador ofrece cobertura alta con exactitud selectiva
adecuada y riesgo de reutilización incorrecta controlado.

**Señal observada.** Para C en v1: Top-1 = 0,780; Top-3 = 0,941; MRR = 0,855;
cobertura = 0,907; exactitud selectiva = 0,785; `false-reuse risk` = 0,215.
En peticiones menos templadas, TF-IDF baja a Top-1 = 0,381, mientras el router
LLM alcanza 0,750.

**Veredicto.** Parcial y descriptiva. El recuperador funciona razonablemente
en el benchmark propio, pero la generalización es el principal límite técnico.
El CSV fuente de la evaluación de peticiones reales tampoco está versionado,
por lo que esa comparación no es reproducible por completo desde el repo.

### H6 — Abstención

**Hipótesis.** Abstenerse en casos sin skill, ambiguos o con margen insuficiente
reduce la reutilización errónea.

**Señal observada.** Con umbral 0,15 y margen 0,05 sobre v1: cobertura = 0,833;
exactitud selectiva = 0,770; `false-reuse risk` = 0,230; abstención correcta =
0,923; falsa abstención = 0,075. La rejilla completa 0,00–0,60 está en
`data/retrieval_precision_coverage_v1.json`.

**Veredicto.** Parcial y descriptiva. La curva hace visible el intercambio
precisión–cobertura, pero se implementó después de inspeccionar test v1. El
umbral definitivo debe congelarse con desarrollo/validación y evaluarse una
sola vez en un test nuevo.

### H7 — Trazabilidad

**Hipótesis.** C obtiene una puntuación de trazabilidad superior a A y B con la
rúbrica ponderada de siete componentes.

**Señal observada.** Medias históricas: A = 0,356; B = 0,374; C = 0,820.

**Veredicto.** No confirmada; señal exploratoria favorable. El resumen
histórico no conserva las filas de cada componente ni los contrastes
emparejados. Además, la rúbrica concede peso a capacidades que A/B no tienen
por definición, por lo que hay que discutir explícitamente ese sesgo de diseño.
Las ejecuciones futuras ya guardan los siete componentes y calculan Friedman,
post hoc Wilcoxon-Holm, IC95, Cohen's dz y correlación biserial de rangos.

### H8 — Coste total modelado

**Hipótesis.** Analizar, sin dirección confirmatoria, el coste de inferencia,
revisión, errores y reintentos bajo supuestos declarados.

**Señal observada.** Existe una sensibilidad basada en una tarifa hipotética
por token. No hay gasto real ni ahorro empresarial observado.

**Veredicto.** Análisis de escenarios, no hipótesis aceptada. Faltan tablas de
escenarios para tiempo de revisión, coste de error y reintentos. Nunca debe
traducirse a «ahorra X euros» como resultado medido.

## Las tesis que el proyecto puede defender

Estas son las conclusiones intelectuales del proyecto. Su estado importa tanto
como su redacción.

1. **T1 — Separación de responsabilidades, provisional.** La interpretación
   probabilística debe proponer; una capa determinista debe autorizar y
   ejecutar. Es la tesis arquitectónica central, con evidencia favorable aún no
   confirmatoria.
2. **T2 — Reutilización y eficiencia, provisional.** Una skill reutilizable
   puede evitar selección y planificación repetidas, pero el ahorro solo es
   válido si todos los sistemas pagan el mismo coste de parseo y se usa la
   población H2 correcta.
3. **T3 — Estabilidad, no resuelta.** El diseño actual no demuestra que C sea
   más estable; temperatura 0 hace indistinguibles las repeticiones.
4. **T4 — Abstención como control de riesgo, descriptiva.** No forzar una skill
   convierte el error silencioso en un intercambio medible entre cobertura,
   falsa abstención y reutilización incorrecta.
5. **T5 — Gobernanza y trazabilidad, provisional.** Versionado, política,
   aprobación, postcondiciones y evidencia permiten reconstruir mejor una
   decisión, aunque la ventaja exacta depende de una rúbrica favorable a esas
   capacidades.
6. **T6 — Integración ERP, solo factibilidad.** El pipeline gobernado crea,
   bloquea y, tras aprobación, modifica datos en Odoo staging. Esto prueba que
   la arquitectura puede integrarse; no que sea superior a A/B en Odoo.
7. **T7 — Evolución gobernada de skills, solo demo.** Ante la falta de skill, el
   LLM puede proponer una definición; solo sandbox, tests, aprobación humana y
   versionado permiten activarla. Esa generación queda fuera de la comparación
   confirmatoria y no explica causalmente sus resultados.
8. **T8 — La recuperación es el cuello de botella, exploratoria.** La caída de
   TF-IDF en lenguaje menos templado indica que mejorar perfiles, embeddings,
   ranking y abstención puede aportar más que añadir autonomía al agente.
9. **T9 — Confinamiento antes que detección, exploratoria.** Los contratos y
   allowlists pueden impedir una mutación incluso cuando falla la detección
   léxica. El stress test apoya esta idea, pero aún no es evidencia
   confirmatoria fila a fila.
10. **T10 — Valor económico no demostrado.** El proyecto puede presentar
    escenarios y sensibilidad, no ahorro, satisfacción ni ROI observados.

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

## Qué falta para responder confirmatoriamente

1. **Hecho:** crear y sellar 120 candidatos v2 sin ejecutar A/B/C.
2. Completar los dos paquetes v2 independientes, adjudicar desacuerdos y
   obtener dos revisiones humanas de los estados exactos.
3. Congelar dataset, 12 skills, prompts, modelos, roles, umbrales, márgenes,
   seeds, timeouts, reintentos y plan estadístico.
4. Ejecutar A/B/C y conservar automáticamente todas las filas crudas con sus
   hashes; el código ya impide que falten o se dupliquen unidades.
5. Aplicar H2 solo a casos con skill esperada y H7 a los siete componentes.
6. Resolver H3 antes del congelado, sin cambiar su diseño después de ver test.
7. Ejecutar el validador de claims y publicar tanto resultados favorables como
   fallos, intervalos y limitaciones.

Hasta completar esos pasos, la formulación correcta es: **«los datos actuales
apoyan estas tesis de forma exploratoria»**, no **«las hipótesis están
demostradas»**.
