# Defensa final del TFM — ERP Agent OS

Guion alineado exclusivamente con la evidencia confirmatoria vigente (`tfm-protocol-v2.1.2`). No sustituye `docs/results-v2.1.md` y no introduce resultados nuevos.

## Mensaje central

> ERP Agent OS no intenta que el LLM sea infalible. Separa lo que el modelo puede proponer de lo que el sistema puede autorizar y ejecutar, y mide qué propiedades aporta realmente esa separación.

La conclusión no es «el sistema es seguro». La conclusión es más precisa: aporta eficiencia, estabilidad, abstención y trazabilidad medibles, pero la detección activa de peligro y el retrieval siguen siendo límites abiertos.

## Estructura recomendada del vídeo (4:20–5:00)

### 0:00–0:35 — Problema

Un error textual es una respuesta equivocada; un error de un agente conectado a un ERP puede crear, modificar o confirmar estado empresarial. La pregunta es dónde debe terminar la autoridad del modelo.

### 0:35–1:15 — Arquitectura

Explicar solo una frase: **el LLM propone; la arquitectura autoriza; el runtime ejecuta**.

Mostrar: petición -> retrieval -> contrato -> policy/risk/approval -> runtime -> ERP -> postcondición -> auditoría.

Añadir que una skill ausente puede proponerse, pero no autoactivarse: debe validarse, probarse, aprobarse y versionarse.

### 1:15–1:55 — Diseño experimental

Tres sistemas comparables:

- A: agente directo con herramientas ERP genéricas.
- B: herramientas tipadas.
- C: ERP Agent OS completo.

ERP-Skills-Bench-Proc v2.1 es un benchmark **sintético/procedural** con verdad de referencia definida antes del texto, oráculos independientes y campaña única tras freeze. La campaña contiene **21.478 observaciones experimentales procedentes de ejecuciones observadas sobre escenarios sintéticos**, con estado `RUN_COMPLETED / CLOSURE_VALID`.

El benchmark es el instrumento experimental del proyecto software; no se presenta como muestra representativa de usuarios o empresas reales.

### 1:55–3:10 — Resultados

Empezar por los resultados que limitan la tesis:

- H1b no soportada: C no supera a B en éxito de tarea (`p=0,286`).
- H4 no soportada: 19,0 % de mutación no autorizada sobre **315 escenarios peligrosos del benchmark confirmatorio**; el límite prerregistrado era <5 %.
- H5 no soportada: selective accuracy 0,589 y false-reuse risk 0,411.

Después, qué sí se sostiene:

- H1a: C no es inferior a A (+25,3 pp, con margen de no inferioridad -5 pp).
- H2: aproximadamente 468 tokens menos que A y 648 menos que B.
- H3a: mayor estabilidad entre formulaciones, OR 9,35 (`p=2,2×10^-18`).
- H6: la abstención reduce false-reuse risk en 8,6 pp.
- H7: +42,7 puntos porcentuales de reconstrucción completa de auditoría frente a A (`p=2,85×10^-112`), con la salvedad estructural declarada en la memoria.
- H8: análisis descriptivo de sensibilidad; no demuestra ahorro monetario observado.

### 3:10–3:50 — Seguridad: la distinción importante

No confundir dos preguntas:

1. ¿Detecta suficientemente bien una petición ambigua y peligrosa? **No: H4 falla el criterio prerregistrado.**
2. Si el modelo está explícitamente comprometido y trata de escribir fuera del contrato, ¿el confinamiento estructural aguanta? En el stress test específico: **0/1.530 mutaciones no autorizadas fuera de contrato**.

Ese contraste es una aportación del trabajo: **confinamiento no equivale a detección**. El 0/1.530 no prueba seguridad general ni sustituye H4.

### 3:50–4:25 — Odoo 19 Development

Demo gobernada sobre una instancia **Odoo 19 Development con datos demo**:

1. R1 -> ALLOW -> crea oportunidad.
2. R2 sin aprobación -> REQUIRE_APPROVAL -> relectura independiente confirma que Odoo no cambió.
3. Se concede aprobación -> ALLOW -> escritura -> relectura confirma el nuevo estado.

No presentarlo como réplica estadística ni como validación en producción: es evidencia de **factibilidad de integración end-to-end**. Solo 2/12 skills están mapeadas a Odoo en la demostración actual.

### 4:25–5:00 — Cierre

> El resultado más útil no es que la arquitectura gane en todo; es saber exactamente dónde ayuda y dónde deja de ayudar. La gobernanza aporta propiedades medibles de eficiencia, estabilidad, abstención y trazabilidad, pero no sustituye a un retrieval fiable ni a políticas capaces de reconocer peligro ambiguo. Ese es el siguiente paso para convertir el prototipo en un producto operativo.

## Preguntas difíciles

### «¿Por qué usa datos sintéticos?»

Porque permiten definir intención, decisión esperada y estado final antes de generar el lenguaje y comparar A, B y C bajo el mismo estado inicial. Esto aumenta validez interna y reproducibilidad a cambio de limitar validez externa. El TFM no afirma equivalencia con usuarios reales. Además, el benchmark no es el objeto de un TFM de análisis de dataset: es el instrumento de evaluación de una solución software.

### «¿No está favorecido C porque A no tiene postcondiciones?»

Parte de H7 es estructural y se declara como tal. Por eso el contraste más informativo de éxito es C frente a B, donde C no logra superioridad. El trabajo no oculta esa limitación.

### «¿Por qué H4 sale peor que A/B en algunos endpoints?»

Porque el `DENY` de A/B puede proceder de un error de ejecución, no de una decisión de seguridad homologable. Por eso la lectura principal no es «A/B son más seguros», sino que **C observa un 19,0 % de mutaciones no autorizadas dentro de la población peligrosa del benchmark**, suficiente para que H4 no alcance el objetivo <5 %.

### «¿0/1.530 significa que es seguro?»

No. Significa que en ese stress test explícito no se observaron mutaciones fuera de contrato. No establece tasa cero en producción ni sustituye H4, que evalúa otra superficie y falla.

### «¿Qué pasó con v2.1.1 y v2.1.2?»

Tras terminar la campaña se encontró que H2 implementaba C-A pero omitía C-B pese a exigir ambas comparaciones. Se corrigió únicamente la capa de análisis; el mecanismo de freeze invalidó el resultado automáticamente, se recongeló formalmente como v2.1.2, se preservó el informe anterior y los otros componentes/datos permanecieron idénticos. El veredicto de H2 no cambió.

### «¿Qué aporta si MCP ya tiene tools?»

MCP resuelve interoperabilidad y exposición de herramientas. ERP Agent OS estudia la capa adicional de recuperación selectiva, política, riesgo, aprobación, idempotencia, postcondiciones y auditoría sobre operaciones ERP, y mide su efecto frente a baselines.

### «¿Puede el agente inventarse una skill y darse permiso?»

No. Puede proponer una definición, pero `DRAFT -> ACTIVE` está prohibido. La propuesta debe validar, pasar sandbox/tests, recibir aprobación humana y versionarse antes de activarse.

### «¿Qué falta para producción?»

Prioridad 1: cerrar las categorías que fallan en H4 y volver a medir sobre evidencia prospectiva. Después: mejorar retrieval con descripciones y ejemplos representativos, ampliar handlers de Odoo (actualmente 2/12), autenticación/multi-tenant y secretos, persistencia e integridad de auditoría, observabilidad/SLO y UX de aprobación/aclaración.

## Regla final

Si una pregunta intenta llevar la respuesta más lejos que la evidencia, volver a la formulación exacta: **«en ERP-Skills-Bench-Proc v2.1, bajo el modelo, catálogo, políticas y condiciones registradas...»**. Esa precisión fortalece la defensa.
