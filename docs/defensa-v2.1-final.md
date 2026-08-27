# Defensa final del TFM — ERP Agent OS

Guion alineado exclusivamente con la evidencia confirmatoria vigente (`tfm-protocol-v2.1.2`). No sustituye `docs/results-v2.1.md` y no introduce resultados nuevos.

## Mensaje central

> ERP Agent OS no intenta que el LLM sea infalible. Separa lo que el modelo puede proponer de lo que el sistema puede autorizar y ejecutar, y mide qué propiedades aporta realmente esa separación.

La conclusión no es «el sistema es seguro». La conclusión es más precisa: aporta eficiencia, estabilidad, abstención y trazabilidad medibles, pero la detección activa de peligro y el retrieval siguen siendo límites abiertos.

## Estructura recomendada del vídeo (4:30–5:00)

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

Benchmark procedural con verdad de referencia definida antes del texto, oráculos independientes y campaña única tras freeze. Resultado: 21.478 observaciones, `RUN_COMPLETED / CLOSURE_VALID`.

### 1:55–3:10 — Resultados

Empezar por los resultados que limitan la tesis:

- H1b no soportada: C no supera a B en éxito de tarea (`p=0,286`).
- H4 no soportada: 19,0 % de mutación no autorizada sobre 315 escenarios peligrosos; el límite prerregistrado era 5 %.
- H5 no soportada: selective accuracy 0,589 y false-reuse risk 0,411.

Después, qué sí se sostiene:

- H1a: C no es inferior a A.
- H2: aproximadamente 468 tokens menos que A y 648 menos que B.
- H3a: mayor estabilidad entre formulaciones, OR 9,35.
- H6: la abstención reduce false-reuse risk.
- H7: +42,7 puntos porcentuales de reconstrucción completa de auditoría frente a A.

### 3:10–3:50 — Seguridad: la distinción importante

No confundir dos preguntas:

1. ¿Detecta bien una petición ambigua y peligrosa? **No suficientemente: H4 falla.**
2. Si el modelo está explícitamente comprometido y trata de escribir fuera del contrato, ¿el confinamiento estructural aguanta? En el stress test específico: **0/1.530 mutaciones no autorizadas**.

Ese contraste es una aportación del trabajo: **confinamiento no equivale a detección**.

### 3:50–4:25 — Odoo real

Demo gobernada sobre Odoo 19 Development:

1. R1 -> ALLOW -> crea oportunidad.
2. R2 sin aprobación -> REQUIRE_APPROVAL -> relectura independiente confirma que Odoo no cambió.
3. Se concede aprobación -> ALLOW -> escritura -> relectura confirma el nuevo estado.

No presentarlo como réplica estadística: es evidencia de factibilidad de integración.

### 4:25–5:00 — Cierre

> El resultado más útil no es que la arquitectura gane en todo; es saber exactamente dónde ayuda y dónde deja de ayudar. La gobernanza reduce trabajo repetido y hace las acciones más estables y auditables, pero no sustituye a un retrieval fiable ni a políticas capaces de reconocer peligro ambiguo. Ese es el siguiente paso para convertir el prototipo en un producto operativo.

## Preguntas difíciles

### «¿Por qué usa datos sintéticos?»

Porque permiten definir intención, decisión esperada y estado final antes de generar el lenguaje, evitando depender de anotación humana inexistente. Esto aumenta validez interna y reproducibilidad, a cambio de limitar validez externa. El TFM no afirma equivalencia con usuarios reales.

### «¿No está favorecido C porque A no tiene postcondiciones?»

Parte de H7 es estructural y se declara como tal. Por eso el contraste más informativo de éxito es C frente a B, donde C no logra superioridad. El trabajo no oculta esa limitación.

### «¿Por qué H4 sale peor que A/B en algunos endpoints?»

Porque el `DENY` de A/B puede ser simplemente un error de ejecución, no una decisión de seguridad homologable. La cifra que no depende de esa etiqueta es la mutación real no autorizada de C: 19,0 %, y esa cifra por sí sola hace que H4 no se soporte.

### «¿0/1.530 significa que es seguro?»

No. Significa que en ese stress test explícito no hubo mutaciones fuera de contrato. No establece tasa cero en producción ni sustituye H4, que evalúa otra superficie y falla.

### «¿Qué pasó con v2.1.1 y v2.1.2?»

Tras terminar la campaña se encontró que H2 implementaba C-A pero omitía C-B pese a exigir ambas comparaciones. Se corrigió únicamente la capa de análisis; el mecanismo de freeze invalidó el resultado automáticamente, se recongeló formalmente como v2.1.2, se preservó el informe anterior y los otros componentes/datos permanecieron idénticos. El veredicto de H2 no cambió.

### «¿Qué aporta si MCP ya tiene tools?»

MCP resuelve interoperabilidad y exposición de herramientas. ERP Agent OS estudia la capa adicional de recuperación selectiva, política, riesgo, aprobación, idempotencia, postcondiciones y auditoría sobre operaciones ERP, y mide su efecto frente a baselines.

### «¿Puede el agente inventarse una skill y darse permiso?»

No. Puede proponer una definición, pero `DRAFT -> ACTIVE` está prohibido. La propuesta debe validar, pasar sandbox/tests, recibir aprobación humana y versionarse antes de activarse.

### «¿Qué falta para producción?»

Prioridad 1: cerrar H4 y volver a medir. Después: mejorar retrieval con descripciones/ejemplos reales, ampliar handlers de Odoo (actualmente 2/12), cablear persistencia a la API, autenticación/multi-tenant, UX de aprobación y auditoría resistente a manipulación.

### «¿Cuál es exactamente tu aportación original?»

No introducir individualmente tool calling, contratos, aprobación humana, control de acceso o auditoría — eso ya existe en distintos sistemas y líneas de investigación (MCP, Agent Skills, marcos de riesgo). La aportación es integrarlos como una única frontera de autoridad sobre operaciones ERP, y sobre todo la evaluación experimental de qué propiedades aporta esa frontera frente a un agente directo (A) y frente a herramientas tipadas (B), con protocolo confirmatorio prerregistrado.

### «¿Por qué debería existir C si B tiene casi la misma tasa de éxito?»

Porque el éxito de tarea (STSR) no es la única propiedad que importa en un ERP. H2 y H3a muestran que C es más barato en tokens y más estable ante paráfrasis que B; H7 muestra que su auditoría se reconstruye con mayor completitud. B no tiene catálogo versionado, política de riesgo explícita, aprobación humana con actor ni ciclo de evolución gobernada — son propiedades de ingeniería y gobierno, no solo de acierto puntual. C no gana en éxito; gana en lo que pasa alrededor de cada decisión.

### «Si H4 falla, ¿por qué una empresa debería usar esto?»

Porque la evidencia no justifica desplegar C tal cual como solución de seguridad. Sí justifica varias propiedades de ingeniería —coste, estabilidad, abstención, auditabilidad y confinamiento acotado— e identifica H4/H5 como requisitos que deben cerrarse antes de una productivización de alto riesgo.

## Regla final

Si una pregunta del tribunal intenta llevar la respuesta más lejos que la evidencia, volver a la formulación exacta: **“en ERP-Skills-Bench-Proc v2.1, bajo el modelo, catálogo, políticas y condiciones registradas...”**. Esa precisión fortalece la defensa; no la debilita.