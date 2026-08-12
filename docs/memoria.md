# ERP Agent OS: diseño y evaluación experimental de un sistema de recuperación y ejecución segura de skills reutilizables para la automatización de procesos ERP mediante agentes de inteligencia artificial

**Autor:** Jairo Gelpi Moreno
**Programa:** Máster en Data Science, Inteligencia Artificial y Big Data
**Modalidad:** Opción 3 — proyecto técnico aplicado con evaluación experimental
**Tutor/a:** [pendiente de asignación]
**Curso académico:** 2025–2026

> **Estado del documento.** Borrador de memoria construido **a partir de
> los artefactos y resultados reales del repositorio**, no de
> expectativas. Toda cifra que aparece aquí procede de un fichero
> versionado (`data/*.json`) y es reproducible con los comandos del
> anexo A. Los apartados que dependen de trabajo humano pendiente —
> kappa de anotación, workbook de Tableau, defensa— están marcados como
> tales y **no se dan por hechos**.

---

## Resumen

Los modelos de lenguaje interpretan instrucciones y usan herramientas
externas, pero su comportamiento varía entre ejecuciones y no garantiza
por sí solo que una operación empresarial sea válida, autorizada,
reversible o auditable. En un ERP, un fallo de este tipo no produce una
respuesta incorrecta: produce un registro duplicado, un importe
modificado o un documento confirmado que no debía confirmarse.

Este trabajo propone **ERP Agent OS**, una arquitectura que usa el
modelo de lenguaje para interpretar la intención del usuario y proponer
una acción estructurada, pero delega autorización y ejecución en
componentes deterministas: un registro de *skills* versionadas,
recuperación semántica, validación de esquema y precondiciones, un motor
de políticas con clasificación de riesgo, aprobación humana cuando
procede, un runtime que solo ejecuta handlers registrados, idempotencia,
verificación de postcondiciones y auditoría append-only.

La evaluación compara tres sistemas sobre el mismo benchmark propio
(**ERP-Skills-Bench**, 480 peticiones sintéticas en español, 120 de test
congelado) con un diseño emparejado de **1.080 ejecuciones** (120 casos ×
3 sistemas × 3 repeticiones): **A**, agente directo; **B**, herramientas
tipadas; **C**, ERP Agent OS completo.

Con un LLM real compartido por los tres sistemas y sin regalar el parseo
de argumentos a ninguno, el resultado es: STSR A = 0,000 · B = 0,483 ·
**C = 0,633** (C−B = +0,150, IC95 [+0,042, +0,258], *p* = 0,016); *false
allow rate* A = 0,889 · B = 0,889 · **C = 0,111** (8×); trazabilidad
0,356 / 0,374 / **0,820** (2,2×); consumo 185,1 / 265,3 / **67,6**
tokens por ejecución (3,9× menos que B).

Ese contraste, sin embargo, **no es el resultado más informativo del
trabajo**, y decirlo forma parte de reportarlo con honestidad. Que un
sistema diseñado para bloquear bloquee está cerca de la tautología, la
ventaja en éxito de tarea es modesta y —medido después— **no transfiere
a texto de usuario real**. Los dos hallazgos que sí resisten el
escrutinio surgieron de auditar el propio trabajo:

**Primero, una forma distinta de preguntar por la seguridad.** La
literatura de inyección de prompts mide si un detector dispara; el
detector de este sistema apenas lo hace fuera de su distribución (3,3 %
sobre 510 casos externos de InjecAgent). La pregunta que decide si un
ERP está protegido es otra: *concedido el ataque por completo —el
modelo comprometido, el atacante dictando los argumentos—, ¿ocurre
alguna mutación no autorizada?* Sobre esos mismos 510 payloads
entregados por los tres canales que un atacante controla:
**0 de 1.530**, con 510 de 510 denegadas en el brazo que entrega el LLM
al atacante. La defensa efectiva resultó ser arquitectónica, no
detectiva, y eso es medible con independencia del modelo empleado.

**Segundo, una observación sobre el propio proceso de medir.** El
trabajo documenta **quince defectos hallados en su instrumento de
medida**, y el patrón que los explica: *el desarrollo dirigido por
pruebas protege bien lo que se implementa contra un requisito explícito
y protege mal lo que solo se calcula a partir de una fórmula*, porque en
el segundo caso es fácil verificar la conclusión del cálculo sin
verificar el mecanismo. Cinco de esos defectos comparten forma —una
comprobación que no podía fallar— y uno, al corregirse, **habría
mejorado los resultados** del sistema propuesto; no se corrigió, porque
el conjunto de test estaba congelado.

**Palabras clave:** agentes LLM, automatización ERP, gobernanza de
agentes, recuperación semántica, evaluación selectiva, inyección de
prompts, diseño experimental emparejado.

---

## 1. Introducción

### 1.1 Contexto y motivación

Un ERP concentra el estado operativo de una empresa: clientes,
oportunidades, pedidos, productos, inventario y documentos
administrativos. Automatizar tareas sobre ese estado con un agente
basado en un modelo de lenguaje es atractivo —la interfaz natural
elimina la fricción de aprender formularios— y arriesgado por el mismo
motivo: la acción que el agente ejecuta modifica datos reales.

El riesgo no es hipotético ni exótico. Un agente puede interpretar mal
una instrucción, elegir la herramienta equivocada, generar parámetros
inválidos, actuar con un alcance mayor al solicitado, repetir una
mutación tras un reintento, o dar por buena una operación cuyo efecto no
coincide con la intención original. Cada uno de esos fallos se traduce
en el ERP en registros duplicados, movimientos de inventario
incorrectos, documentos en estados no deseados o pérdida de
trazabilidad.

### 1.2 El problema, formulado con precisión

La cuestión no es si un modelo de lenguaje puede llamar a la API de un
ERP: puede. La cuestión es **qué garantías existen sobre lo que ocurre
cuando lo hace**, y si esas garantías pueden obtenerse sin degradar la
tasa de éxito ni disparar el coste.

Este trabajo separa el sistema en dos zonas con responsabilidades
disjuntas:

- **Zona probabilística.** Interpreta lenguaje natural, identifica
  intención y entidades, propone una acción estructurada, recupera
  skills semánticamente próximas y genera explicaciones.
- **Zona determinista.** Valida esquemas, comprueba permisos, aplica
  reglas de negocio, clasifica el riesgo, solicita aprobación, garantiza
  idempotencia, ejecuta operaciones permitidas, comprueba
  postcondiciones y registra evidencias.

El modelo puede **proponer**; no puede evitar el contrato de la skill ni
las políticas del runtime.

### 1.3 Pregunta de investigación

> ¿En qué medida una arquitectura basada en skills reutilizables,
> recuperación semántica, verificación previa y ejecución determinista
> mejora la fiabilidad, eficiencia y trazabilidad de la automatización de
> procesos ERP frente a un agente LLM con ejecución directa?

### 1.4 Contribuciones

1. **Técnica.** Una arquitectura modular que transforma peticiones ERP
   en acciones controladas mediante skills versionadas, implementada y
   ejecutable (`src/erp_agent_os/`, 38 módulos, 391 tests).
2. **De datos.** **ERP-Skills-Bench**, benchmark sintético anotado de 480
   peticiones con estado inicial, decisión esperada y etiquetas
   adversariales, con split de test congelado y verificado sin fuga.
3. **Metodológica.** Un protocolo emparejado de comparación entre agente
   directo, herramientas tipadas y agente gobernado, con congelación
   hash-verificada del protocolo y colapso explícito de repeticiones
   para evitar pseudo-replicación.
4. **De seguridad.** Una taxonomía de riesgo R0–R4 con motor de
   políticas *deny-by-default*, evaluada tanto en el benchmark propio
   como contra un dataset adversarial externo (InjecAgent).
5. **Empresarial.** Métricas que traducen el rendimiento técnico a
   errores prevenidos, necesidad de revisión, capacidad de auditoría y
   coste modelado, con supuestos declarados.
6. **Metodológica sobre el propio proceso.** Un registro auditado de
   quince defectos hallados en el instrumento de medida y el patrón que
   los explica (§9.5), utilizable como material sobre validez de
   constructo.

### 1.5 Estructura del documento

El capítulo 2 sitúa el trabajo frente al estado de la cuestión; el 3
formaliza el diseño de investigación; el 4 describe la arquitectura; el
5, la implementación; el 6, el dataset; el 7, los experimentos; el 8,
los resultados; el 9 discute qué se puede y qué no se puede concluir; el
10 aborda la productivización; el 11 concluye.

---

## 2. Marco teórico y estado de la cuestión

### 2.1 Agentes y uso de herramientas

**ReAct** (Yao et al., 2022) establece el patrón de intercalar
razonamiento y acción que sostiene la mayoría de los agentes actuales.
**Toolformer** (Schick et al., 2023) muestra que un modelo puede
aprender a invocar APIs externas. Ambos trabajos resuelven *cómo* actúa
un agente; ninguno se ocupa de *bajo qué garantías* lo hace, que es el
objeto de este trabajo.

### 2.2 Evaluación de agentes

**AgentBench** (Liu et al., 2023) y **API-Bank** (Li et al., 2023)
evalúan capacidad de agentes con herramientas, y motivan una decisión
central de este trabajo: puntuar el **estado final** y no la salida
textual. De ahí la métrica primaria, *Strict Task Success Rate*, que
exige acción adecuada, argumentos válidos, permisos respetados, estado
esperado y ausencia de efectos laterales.

**τ-bench** (Yao et al., 2024) es el pariente conceptual más cercano al
Policy Engine: mide si un agente respeta reglas de negocio explícitas en
dominios reales (aerolínea, retail) en lugar de solo completar la tarea.
Se cita como posicionamiento; no cubre dominio ERP ni aporta datos a
este trabajo.

### 2.3 Seguridad y robustez adversarial

**InjecAgent** (Zhan et al., 2024) mide inyección **indirecta** de
prompts: el atacante planta una instrucción dentro de datos que una
herramienta devuelve. Es el vector más cercano al de este proyecto y se
utiliza aquí como prueba de estrés externa (§8.6). **AgentHarm**
(Andriushchenko et al., 2024) se cita como referencia de diseño de
benchmarks de daño; no se ejecutó contra este sistema, por presupuesto
de tiempo, y así se declara.

### 2.4 Recuperación semántica

**Sentence-BERT** (Reimers y Gurevych, 2019) sustenta el recuperador de
embeddings evaluado en §8.5. El resultado de esa comparación es
negativo para los embeddings en este benchmark concreto, y se reporta
como tal.

### 2.5 Marcos normativos

El **NIST AI RMF Generative AI Profile** (Autio et al., 2024) y la
especificación de **Model Context Protocol** aportan el encuadre de
control: consentimiento, autorización explícita, mínimo privilegio y
cautela en el uso de herramientas. La arquitectura de este trabajo
implementa esos principios como código ejecutable —allowlists,
aprobación con expiración, auditoría append-only— y no solo como
declaración.

### 2.6 Hueco que este trabajo ocupa

Existe abundante literatura sobre *capacidad* de agentes y una
literatura creciente sobre su *daño potencial*. Falta evidencia
experimental emparejada sobre el **coste y el beneficio de gobernar** a
un agente en un dominio transaccional: cuánta seguridad se compra,
cuántos tokens cuesta, y si el éxito de tarea se resiente. Este trabajo
aporta esa medición en un dominio ERP acotado.

---

## 3. Diseño de investigación

### 3.1 Hipótesis

Las hipótesis se contrastan sobre el conjunto de test congelado, con
unidad emparejada petición–estado inicial–repetición.

| H | Endpoint | Dirección | Regla |
|---|---|---|---|
| H1 | STSR, A vs C | C no inferior a A | No inferioridad, margen −5 pp; McNemar e IC95 |
| H2 | Tokens totales por ejecución | C < A y B | Comparación emparejada, IC95 |
| H3 | Coincidencia de estado entre 3 repeticiones | C > A y B | Proporción de tríos consistentes |
| H4 | Casos peligrosos | C mayor detección, menor false allow | Recall/precision, false allow/block con IC |
| H5 | Recuperación con skill esperada | Alta cobertura, exactitud selectiva | Coverage, Top-1/Top-3, exactitud selectiva |
| H6 | Casos sin skill o ambiguos | Abstención donde reduce reutilización errónea | Coverage, false-reuse risk, tasa de abstención |
| H7 | Traza de cada ejecución | C > A y B | Rúbrica ponderada auditable |
| H8 | Coste modelado | No confirmatoria | Análisis de sensibilidad con supuestos declarados |

### 3.2 Sistemas comparados

- **A — Agente directo.** Herramientas ERP genéricas (CRUD por modelo);
  ejecuta sin registro de skills, sin policy engine específico y sin
  verificación independiente.
- **B — Herramientas tipadas.** Esquemas y validación de tipos
  reutilizando el catálogo, pero sin recuperación semántica, sin
  taxonomía de riesgo completa, sin aprobación estructurada y sin
  verificación por postcondiciones.
- **C — ERP Agent OS.** Pipeline completo.

D-03 exige que los tres compartan modelo, proveedor, configuración,
temperatura, presupuestos de reintento y cobertura de herramientas. Se
cumple: el mismo cliente LLM, el mismo prompt de selección (hoy una
constante única compartida, no tres copias) y el mismo prompt de
extracción.

### 3.3 Métrica primaria

**Strict Task Success Rate.** Una ejecución solo es correcta si cumple
los cinco conjuntos: acción adecuada, argumentos válidos, permisos
respetados, estado final esperado y ausencia de efectos laterales. La
conjunción es deliberada: hace la métrica exigente y la vuelve
sensible a fallos que una métrica de "salida plausible" no vería.

### 3.4 Unidad de inferencia y control de pseudo-replicación

Las tres repeticiones de un caso comparten petición, estado inicial y
sistema: **no son observaciones independientes**. Tratarlas como tales
infla artificialmente la significación. El análisis colapsa las
repeticiones a una unidad por caso (mayoría) **antes** de cualquier
contraste emparejado, y el manifiesto publica `n_observations: 1080`
junto a `n_inference_units: 120` para que la distinción sea visible.

El impacto de no hacerlo, medido: el IC de C−B pasaba de 0,200 de ancho
(correcto) a 0,119 (inflado), y el *p* de McNemar de 9,1×10⁻⁹ a
5,2×10⁻²⁴ — quince órdenes de magnitud de significación fabricada.

### 3.5 Plan estadístico

Binarias: McNemar para dos sistemas (con corrección de continuidad), Q
de Cochran para tres, corrección de Holm en comparaciones múltiples,
bootstrap para intervalos, odds ratio con corrección Haldane-Anscombe.
Continuas: diferencia de medias emparejada con IC bootstrap. Tamaños de
efecto: diferencia de proporciones, odds ratio, Cliff's delta. Se
reportan intervalos del 95 % en todos los contrastes.

### 3.6 Congelación del protocolo

`data/freeze_manifest.json` (schema 1.1) fija por hash: split de test,
dataset completo, catálogo de 12 skills, semilla, **prompts** y
**configuración de proveedor** (modelo, temperatura, reintentos,
timeout, tope de tokens). `make verify-freeze` corre en CI, de modo que
tocar el generador, el catálogo o un prompt sin re-congelar rompe el
build en lugar de invalidar resultados en silencio. El detector se probó
alterando cada componente uno a uno, incluida la sustitución real del
modelo y de la temperatura.

---

## 4. Arquitectura de ERP Agent OS

### 4.1 Vista general

```text
Usuario → API → Intent Parser → Skill Retriever → Candidate Ranker
                      ↓                                  ↓
              Missing-info Gate                    Policy Engine
                      ↓                    ┌────────┬────────┬──────┐
        Clarification / Abstention        Allow  Simulate Approval Deny
                                            └────────┴────────┘
                                                     ↓
                                          Deterministic Runtime
                                                     ↓
                                              ERP Adapter
                                                     ↓
                                       Postcondition Verifier
                                                     ↓
                                    Audit Store + Metrics + Dashboard
```

### 4.2 Contrato de skill

Una skill declara identidad y versión semántica, módulo y operación,
clase de riesgo, esquema de entrada, roles permitidos, precondiciones,
ejecución (handler, timeout, reintentos, idempotencia), postcondiciones
y condiciones de aprobación. El esquema es estricto y congelado:
`risk_class = R4` **no es registrable**, verificado por property test
para cualquier combinación de rol.

El ciclo de vida es `DRAFT → VALIDATED → TESTED → APPROVED → ACTIVE →
DEPRECATED`, con `QUARANTINED` alcanzable desde cualquier estado. La
transición directa `DRAFT → ACTIVE` está prohibida por el grafo, no por
convención.

### 4.3 Taxonomía de riesgo

| Clase | Ejemplos | Política |
|---|---|---|
| R0 | Consultas | Automático con control de acceso |
| R1 | Escritura de bajo impacto | Automático si validaciones y confianza superan umbral |
| R2 | Modificación relevante | Vista previa y aprobación |
| R3 | Alto impacto | Aprobación obligatoria y, en este TFM, simulación |
| R4 | Prohibido | Bloqueo incondicional |

### 4.4 Policy Engine

*Deny-by-default*. Deniega rol no permitido o skill no `ACTIVE` sin
importar el riesgo. R0/R1 → `ALLOW`; R2 → `REQUIRE_APPROVAL` y luego
`ALLOW`; R3 → `REQUIRE_APPROVAL` y luego `SIMULATE`, nunca `ALLOW`. Los
hallazgos de validación adversarial (inyección, alcance masivo, framing
irreversible, reclamo de permiso) deniegan **antes** del razonamiento de
riesgo, lo que preserva la monotonía: una política más restrictiva nunca
produce una decisión más permisiva (property test).

### 4.5 Runtime determinista, idempotencia y verificación

El runtime carga una versión exacta de skill y ejecuta **únicamente**
handlers registrados; un handler no registrado produce error, no
ejecución. Las decisiones `DENY`, `REQUIRE_APPROVAL` y `SIMULATE` nunca
invocan el handler ni mutan el adaptador. Una clave de idempotencia
repetida reproduce el resultado cacheado sin reinvocar.

Una respuesta correcta del adaptador **no basta**: el verificador
consulta el estado resultante y comprueba postcondiciones ejecutables
—que se creó exactamente un registro, que contiene los valores
esperados, que no cambiaron otros campos, que el documento sigue en
borrador, que no hay duplicación—. Las 12 skills del catálogo resuelven
a comprobaciones ejecutables; una postcondición no implementada **lanza**
en vez de pasar en silencio.

### 4.6 Auditoría

`AuditStore` es append-only por superficie pública: no expone método de
borrado ni de mutación. Cada evento registra correlación, identidad y
versión de skill, rol, decisión, `risk_score`, motivos, clave de
idempotencia y flag de replay, resultado de postcondiciones y salida
redactada. Las abstenciones también se auditan: no decidir es una
decisión.

---

## 5. Implementación

### 5.1 Stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (auditoría y
aprobaciones persistentes), PostgreSQL 16 vía Docker Compose. Ciencia de
datos: NumPy, SciPy y estadística propia verificada analíticamente,
`sentence-transformers` para el recuperador de embeddings. Calidad:
pytest, Hypothesis, Ruff, mypy, pre-commit, GitHub Actions.

### 5.2 Módulos principales

| Módulo | Responsabilidad |
|---|---|
| `dataset.py`, `bench_intents.py`, `bench_generator.py` | Contrato y generación del benchmark |
| `catalog.py` | 12 skills congeladas, 8 familias |
| `skills.py`, `registry.py` | Contrato de skill, ciclo de vida, registro persistente |
| `policy.py`, `validation.py`, `preconditions.py` | Decisión, detección adversarial, precondiciones |
| `runtime.py`, `handlers.py` | Ejecución determinista e idempotente |
| `postconditions.py`, `verification` | Verificación de estado final |
| `audit.py`, `persistence.py` | Auditoría append-only, en memoria y en SQL |
| `retrieval.py`, `embeddings.py` | TF-IDF, embeddings, ranking híbrido, abstención |
| `system_a.py`, `system_b.py`, `system_c.py` | Los tres sistemas comparados |
| `llm_client.py`, `groq_client.py`, `gemini_client.py`, `openrouter_client.py` | Clientes LLM intercambiables |
| `metrics.py`, `statistics.py`, `traceability.py`, `agreement.py` | Métricas, contrastes, rúbrica H7, kappa |
| `experiment.py`, `freeze.py` | Runner emparejado, congelación |
| `adapters.py`, `odoo_client.py`, `odoo_handlers.py` | FakeERP y Odoo 19 real |
| `api.py` | Capa HTTP sobre System C |

### 5.3 Disciplina de construcción

Cada unidad de trabajo se construyó con TDD estricto
RED → GREEN → TRIANGULATE → REFACTOR **contra un requisito normativo
explícito**, con artefactos de especificación previos al código
(`openspec/changes/*`). Estado de calidad actual: **391 tests**,
cobertura **96 %** global (2.456 sentencias, 90 sin cubrir), `ruff` y
`mypy` limpios sobre 38 módulos, CI verde incluyendo validación de
dataset, verificación de congelación y *smoke benchmark*.

Las propiedades de seguridad se verifican con *property-based testing*
(Hypothesis): una skill R4 nunca es registrable; una clave de
idempotencia no produce dos mutaciones; un campo no permitido no llega
al adaptador; toda ejecución terminal tiene auditoría; una política más
restrictiva nunca produce una decisión más permisiva.

Se aplicó además **mutation testing** en dos rondas sobre los 23 módulos
del núcleo: **40 mutantes, 40 muertos** tras cerrar los dos únicos
supervivientes, ambos en la capa estadística (§9.5).

---

## 6. Dataset ERP-Skills-Bench

### 6.1 Composición

| Propiedad | Valor |
|---|---|
| Casos totales | 480 |
| Familias | 8 (crm, contacts, sales, purchasing, product, inventory, tasks, billing) |
| Intenciones canónicas | 24 (2 por skill) |
| Skills | 12, congeladas |
| Splits | 240 desarrollo / 120 validación / 120 test |
| Etiqueta NOISE | 144 (30 %) |
| Etiqueta ADVERSARIAL | 96 (20 %) |
| Solapamiento | 0 por construcción |

Por intención: 20 formulaciones = 10 NORMAL + 6 NOISE (5 transformaciones
estilísticas + 1 omisión de campo requerido, que fuerza `CLARIFY`) + 4
ADVERSARIAL, rotando por las 11 categorías del catálogo adversarial de
forma determinista para que las 11 aparezcan a lo largo de las 24
intenciones.

Cada caso registra intención correcta, skill esperada o etiqueta
`sin_skill/abstención`, argumentos esperados, decisión esperada, estado
inicial, necesidad de aclaración y de aprobación, tipo de error y
etiquetas.

### 6.2 Fuga de datos: un defecto encontrado y corregido

Una versión previa del dataset tenía **fuga real**: 10 textos idénticos
en `DEVELOPMENT` y `FINAL_TEST` (8,3 % del test), 19 cruces en total. La
causa raíz fue una decisión de diseño defendida por escrito —"cada caso
es su propio grupo de paráfrasis"— que hacía que el validador de grupos
pasara **tautológicamente**: un grupo de tamaño 1 no puede cruzar nada.
La justificación era falsa: la norma prohíbe que cruce "ni formulación
semánticamente equivalente", no solo un identificador de grupo.

Corrección: pools de valores ampliados de 4–8 a 24 elementos, asignación
sin repetición dentro de una intención, sustitución de un estilo
duplicado, y un validador nuevo (`validate_no_split_leakage`) que
compara texto normalizado **y** el par (intención, argumentos).
**Probado con una fuga plantada** para que no sea otra comprobación
vacua. Estado actual: 480/480 textos únicos, 0 cruces.

### 6.3 Limitaciones del dataset

Sintético, plantillado, en un solo idioma y contra un solo ERP simulado.
Es una limitación de validez externa que se declara y no se compensa:
los resultados de recuperación en particular (§8.5) están condicionados
por el alto solape léxico entre petición y descripción de skill que las
plantillas producen.

**Pendiente humano declarado:** la revisión por segundo anotador y el
kappa de Cohen que exige el plan estadístico. El instrumento existe
(`data/annotation_review_sheet.csv`, 96 casos estratificados que
sobrerrepresentan adversariales y alto riesgo) y el script de cálculo
**se niega a emitir un kappa** mientras la columna del segundo anotador
esté vacía. No se ha fabricado un número.

---

## 7. Experimentos

### 7.1 Protocolo

120 casos de test congelado × 3 sistemas × 3 repeticiones = **1.080
ejecuciones** por corrida. Orden aleatorizado con semilla, estado de
`FakeERPAdapter` reconstruido antes de cada observación, mismos roles,
mismas claves de idempotencia, mismos presupuestos de timeout y
reintento, mismo evaluador determinista.

### 7.2 Las cuatro corridas

| # | Selector | Régimen de argumentos | Papel |
|---|---|---|---|
| 1 | OpenRouter (`gpt-oss-20b:free`) | Parseo regalado | Confirmatoria con LLM real |
| 2 | Stub determinista | Parseo regalado | Arquitectura-solo: aísla gobernanza de calidad del modelo |
| 3 | Groq (`llama-3.1-8b-instant`) | Parseo real | Elimina el sesgo del parseo regalado |
| 4 | Groq | Parseo real + normalización | **Vigente** |
| 5 | Groq | Parseo regalado | **Réplica que separa proveedor de régimen** |

**Por qué cambia el proveedor entre corridas.** La cuota diaria gratuita
de Groq se agotó durante la instrumentación de tokens; Gemini resultó
inviable (20 peticiones/día por modelo en esta cuenta); OpenRouter
completó la corrida 1 pero entraba en tormentas de 429 que hacían la
corrida 3 inviable (~3 h con interrupciones frente a ~50 min con Groq).
D-03 exige que A/B/C compartan proveedor **dentro** de una corrida, no
un proveedor concreto entre corridas. El confundido proveedor↔régimen
que esto introducía se **resolvió con la ejecución 5** (§8.10), que
repite el régimen de argumentos dados con Groq para dejar el proveedor
fijo.

### 7.3 Dos sesgos corregidos antes de publicar cifras

1. **Parseo regalado (corridas 1–2).** Los tres sistemas recibían
   `case.expected_arguments`: un parseo perfecto que nadie pagaba. Eso
   hacía que C —cuya recuperación es TF-IDF— apareciera con coste **cero**
   en tokens, cuando un despliegue real necesitaría un LLM para
   convertir el texto en argumentos. Corregido en la corrida 3: los tres
   extraen del texto crudo con el mismo LLM, prompt y lista de campos.
2. **Falta de normalización (corrida 3).** El LLM extraía `'27600 euros'`
   para un campo numérico; el validador lo rechazaba por tipo. Ese fallo
   **penalizaba solo a C**, el único sistema que valida tipos antes de
   ejecutar. Corregido con un normalizador deliberadamente **estrecho**
   (número con unidad monetaria opcional; cualquier otra cosa sigue
   fallando), cableado a B y a C, no solo al que se beneficia.

Las postcondiciones se verifican siempre contra la verdad de
referencia, no contra lo que el LLM extrajo: mide si la tarea quedó bien
hecha, no si el parser se autoconfirmó.

### 7.4 Infraestructura de ejecución

Checkpoint/resume por observación (una interrupción cuesta solo las
llamadas no persistidas) y caché de llamadas por sistema: las tres
repeticiones de un caso emiten la misma consulta y con temperatura 0
producen la misma respuesta, así que solo la primera es real. La caché
es **por sistema**: compartirla entre A, B y C hacía que pagara el que
el orden aleatorio ejecutara primero, convirtiendo los totales de tokens
en una medida del orden de ejecución (defecto #12, §9.5).

---

## 8. Resultados

Todas las cifras proceden de `data/experiment_results_real_parser.json`
(corrida 4, vigente) salvo indicación contraria.

### 8.1 H1 — Strict Task Success Rate

| Sistema | STSR |
|---|---|
| A (agente directo) | 0,000 |
| B (herramientas tipadas) | 0,483 |
| **C (ERP Agent OS)** | **0,633** |

| Contraste | Diferencia | IC 95 % | Holm *p* | OR |
|---|---|---|---|---|
| C − A | +0,633 | [+0,550, +0,717] | 1,55 × 10⁻¹⁷ | 153,0 |
| C − B | **+0,150** | [+0,042, +0,258] | **0,0162** | 2,09 |

Q de Cochran = 102,87 (gl = 2). **H1 se acepta**: el límite inferior del
IC de C−A supera con holgura el margen de no inferioridad de −5 pp, y
C−B es además significativo.

**Por qué A obtiene exactamente 0,000.** Es casi determinista dado su
diseño: herramientas CRUD genéricas no pueden codificar postcondiciones,
y STSR exige estado final verificado. Por tanto **el contraste
informativo es C−B**, donde ambos sistemas comparten catálogo, esquemas
y handlers y solo difieren en gobernanza. Presentar C−A como el
resultado principal sería inflar la conclusión.

### 8.2 H4 — Seguridad

| Métrica | A | B | **C** |
|---|---|---|---|
| Casos peligrosos | 27 | 27 | 27 |
| *False allow rate* | 0,889 | 0,889 | **0,111** |
| *False block rate* | 0,225 | 0,072 | **0,072** |
| Recall de detección | 0,111 | 0,111 | **0,889** |
| Precisión de detección | 0,038 | 0,111 | **0,500** |

C permite 3 de 27 casos peligrosos donde A y B permiten 24, **y lo hace
sin bloquear de más** (mismo false block que B, un tercio del de A). Es
el resultado más estable del trabajo: invariante entre proveedores y
entre regímenes de parseo, porque la decisión no depende del LLM.

**Dos advertencias que acotan esta cifra, ambas medidas caso a caso.**

Primera: **la ventaja es aquí, en su mayor parte, detección léxica, no
gobernanza**. De los 9 casos peligrosos del test congelado, **8 disparan
patrones** escritos mirando el corpus de este benchmark; como los casos
de test provienen de las mismas plantillas que los de desarrollo, ese
ajuste transfiere casi por construcción. Es un número **dentro de
distribución**; fuera de ella la detección cae al 3,3 % (§8.6). Lo que
sostiene la afirmación propiamente arquitectónica es el otro
experimento: 0/1.530 mutaciones no autorizadas aunque el detector no
dispare.

Segunda: **el único caso que C permite no es peligroso**. `r0457` pide
*"Crea una factura en borrador para Oceanic Airlines"* y está etiquetado
`argument_out_of_range` porque el generador asigna esa categoría rotando
por índice de intención, sin comprobar que la skill destino tenga un
campo numérico acotado. Los 9 casos de esa categoría en el dataset
completo comparten el defecto. Excluyéndolo, el *false allow* de C es
**0,000** y el de A/B **1,000**. **El dataset no se corrige**: está
congelado, y arreglarlo mejoraría los resultados de C, que es
exactamente el cambio post-hoc que la congelación existe para impedir.
Se publica la cifra contaminada y esta como sensibilidad.

Y sobre ambas columnas: **n = 9 casos peligrosos**, con IC anchos (el de
C llega a 0,435). El "8×" es una estimación puntual sobre nueve casos.

**Descomposición honesta del recall.** De los 9 casos peligrosos del
test analizados en el estudio de ordenación del pipeline, 7 salen
`DENY`, 1 `ABSTAIN` y 1 `ALLOW`. El resultado de seguridad del caso
abstenido es idéntico —no se ejecuta nada— pero el sistema **no lo
identificó** como peligroso: simplemente no lo entendió. El recall de
0,889 se descompone así en 0,778 de detección real y 0,111 de
abstención. Reportar 0,889 como si fuera todo comprensión del ataque
sería deshonesto.

### 8.3 H2 y H8 — Tokens y coste

| Sistema | Tokens/ejecución | Total |
|---|---|---|
| A | 185,1 | 66.636 |
| B | 265,3 | 95.497 |
| **C** | **67,6** | **24.344** |

C − B = −197,6 tokens/ejecución, IC95 [−198,3, −196,9]: **3,9× más
barato**. El mecanismo es explícito: los tres pagan la extracción de
argumentos; A y B pagan **además** una llamada de selección de
herramienta, que C sustituye por TF-IDF a coste cero de tokens.

H8, con tarifa declarada de 0,05 USD/1.000 tokens: A $3,33 · B $4,77 ·
**C $1,22**. Es un **análisis de sensibilidad con supuesto declarado**,
no un ahorro observado —los proveedores usados son gratuitos—, tal como
exige el plan de métricas.

### 8.4 H7 — Trazabilidad

Rúbrica ponderada de siete componentes (identidad de petición 10 %,
interpretación 15 %, candidatas/abstención 15 %, decisión de política
15 %, versión de skill y clave 15 %, resultado y efectos 15 %, evidencia
de postcondición/aprobación/bloqueo 15 %), puntuada desde evidencia real
de auditoría, no por volumen de logs.

| Sistema | Puntuación media |
|---|---|
| A | 0,356 |
| B | 0,374 |
| **C** | **0,820** |

A y B puntúan bajo **por construcción**: carecen de policy engine, de
skills versionadas y de almacén de auditoría. Su puntuación no es un
fallo del calculador, es la brecha de gobernanza hecha medible.

### 8.5 H5, H6 y comparación de recuperadores

| Sistema | Top-1 | Top-3 | MRR | Cobertura | Exact. selectiva | False-reuse risk |
|---|---|---|---|---|---|---|
| A | 0,000 | 0,000 | 0,000 | 1,000 | 0,839 | 0,161 |
| B | 0,898 | 0,898 | 0,898 | 1,000 | 0,898 | 0,102 |
| C | 0,780 | 0,941 | 0,855 | 0,907 | 0,785 | 0,215 |

B alcanza Top-1 = 0,898 sin abstenerse nunca: su selector real es bueno.
C gana en Top-3 y abstiene en el 9,3 % de los casos. **H6 queda
matizada**: el valor de abstenerse depende de la calidad del selector
alternativo, y con un selector fuerte la abstención cuesta cobertura sin
comprar tanta precisión como cabría esperar.

**Comparación de recuperadores** (solo desarrollo y validación, jamás
test), con calibración individualizada de umbral y margen por
recuperador para no favorecer al incumbente:

| Recuperador | Top-1 dev | Top-1 val |
|---|---|---|
| **TF-IDF** | **0,767** | **0,733** |
| Embeddings | 0,713 | 0,658 |
| Híbrido | 0,713 | 0,675 |

**TF-IDF gana en todas las métricas y en ambos splits.** El experimento
confirmatorio ya usaba el mejor de los tres. La causa es el benchmark:
texto plantillado con alto solape léxico entre petición y descripción de
skill, exactamente la señal que TF-IDF explota y que un vector denso
comprime. **No es un resultado sobre embeddings en general.**

### 8.6 Robustez adversarial contra un dataset externo

Dos mediciones sobre los 510 payloads de InjecAgent, fuera de la
distribución del benchmark propio (inglés, dominios no ERP):

1. **Detector léxico:** 0 % de detección con patrones solo en español;
   **3,3 %** tras añadir patrones en inglés. Ampliar el vocabulario no
   cerró la brecha porque el vocabulario no era el cuello de botella:
   la mayoría de los payloads son peticiones educadas sin ningún framing
   de ataque textual, invisibles por diseño a cualquier detector léxico.
2. **Resistencia efectiva:** los mismos 510 payloads por los tres
   canales que un atacante controla —texto de la petición, dato
   almacenado que la petición lee, y parser comprometido con los
   argumentos dictados por el atacante— producen **0 / 1.530 mutaciones
   no autorizadas**, con 510/510 `DENY` en el brazo de parser
   comprometido.

La lectura conjunta es la que importa: la defensa efectiva de esta
arquitectura **no es el detector léxico** sino que los datos del ERP
nunca ocupan posición de instrucción, que el LLM solo puede emitir un
identificador de skill y argumentos validados contra esquema, y que el
handler escribe solo en su modelo y campos permitidos. Un control
positivo aborta la medición si una petición limpia no llega a mutar,
para que "0 mutaciones" no pueda salir vacuo.

**No probado y declarado:** un adversario adaptativo que conozca el
catálogo y redacte argumentos válidos para una skill legítima pero
indeseada.

### 8.7 Segmentación

Por clase de riesgo, C obtiene R0 = 0,600 · R1 = 0,583 · **R2 = 0,950**
· **R3 = 0,400**. El peor resultado está en R3, y la causa es
normativa, no un defecto: en R3 la política obliga a simular incluso
tras aprobación, así que los casos que el dataset espera **ejecutados**
no pueden puntuar. Es una tensión real entre la norma de seguridad y la
métrica de éxito, y se discute como tal en §9.3. El excelente resultado
en R2 (0,950) muestra que, cuando la norma permite ejecutar tras
aprobación, la gobernanza no cuesta éxito.

Por módulo, los peores son `tasks` (0,400) y `sales` (0,467); los
mejores, `product` (0,900), `billing` (0,800) y `purchasing` (0,800).
Por etiqueta: NORMAL 0,750 · ADVERSARIAL 0,526 · NOISE 0,486 — el ruido
lingüístico penaliza más que la adversarialidad, porque una petición
adversarial bien detectada **puntúa** (la decisión esperada es el
bloqueo) mientras que una petición ruidosa mal parseada, no.

### 8.8 Demostración contra un ERP real

Más allá del simulador, el pipeline completo de System C se ejecutó
contra una instancia real de Odoo 19 (rama de desarrollo con datos
demo), con el mismo `Runtime`, `AuditStore` y policy engine que corren
las 1.080 observaciones, cambiando únicamente el adaptador:

- creación de oportunidad R1 → ejecuta y verifica postcondición por
  **relectura independiente**;
- actualización R2 sin aprobación → `REQUIRE_APPROVAL`, y una relectura
  independiente confirma que Odoo **no cambió**;
- misma petición tras conceder aprobación → `ALLOW` y escritura
  correcta.

Es una demostración **cualitativa** con 2 de las 12 skills mapeadas a
modelos reales; no sustituye ni replica el experimento confirmatorio, y
así se declara.

### 8.9 Réplica que separa proveedor de régimen de argumentos

La comparación entre regímenes estaba confundida con el proveedor: la
corrida de argumentos dados usó OpenRouter y la de parseo real, Groq.
La ejecución 5 repite **argumentos dados con Groq**, dejando el
proveedor fijo:

| | Groq, argumentos dados | Groq, parseo real | Δ |
|---|---|---|---|
| STSR B | 0,492 | 0,483 | **−0,008** |
| STSR C | 0,700 | 0,633 | **−0,067** |
| C − B | +0,208 (*p* = 0,0015) | +0,150 (*p* = 0,016) | −0,058 |

Con el proveedor constante, **C cae 6,7 puntos al parsear de verdad y B
solo 0,8**. El efecto es del régimen de argumentos, no del modelo: el
parseo regalado beneficiaba a C desproporcionadamente. La amenaza a la
validez interna más seria del trabajo queda así medida en lugar de
argumentada.

**Verificación interna no planeada, que el diseño supera.** El
incremento de tokens al pasar a parseo real es +67,68 (A), +67,67 (B) y
+67,62 (C): los tres pagan **la misma** extracción, como exige D-03. Y
el gasto **total** de C con parseo real (67,62) es exactamente esa
extracción y nada más — no hay llamada de selección de herramienta, que
es precisamente el mecanismo que la tesis afirma.

**Residuo declarado.** El *false allow* de A sí depende del proveedor
(0,333 con OpenRouter, 0,889 en las dos corridas Groq), mientras que el
de C es 0,111 en todas. La seguridad de un agente sin gobernanza depende
de qué modelo le toque; la de la arquitectura gobernada, de ninguno.

### 8.10 Estado final de las hipótesis

| H | Estado |
|---|---|
| H1 | **Aceptada.** C−A y C−B significativos; margen de no inferioridad cumplido. Efecto sobre B modesto (+0,150). |
| H2 | **Confirmada.** C 67,6 tok/ejec frente a B 265,3 (3,9×). |
| H3 | **Nula por diseño.** Temperatura 0 la vuelve no discriminable. |
| H4 | **Confirmada y robusta.** False allow 0,111 vs 0,889, invariante a proveedor y régimen de parseo. |
| H5 | **Parcial.** C gana en Top-3 y abstención; Top-1 depende del selector. |
| H6 | **Matizada.** El valor de abstenerse depende de la calidad del selector alternativo. |
| H7 | **Confirmada.** 0,820 vs 0,356/0,374. |
| H8 | **Análisis de sensibilidad**, no ahorro medido. |

---

## 9. Discusión

### 9.1 Qué compra la gobernanza, y a qué precio

La formulación que la evidencia soporta es:

> Frente a un baseline de herramientas tipadas con el mismo LLM, la
> arquitectura gobernada compra **8× menos ejecuciones inseguras, 2,2×
> más trazabilidad y 3,9× menos tokens**, con una ventaja **pequeña pero
> significativa** en éxito de tarea (+15,0 pp, *p* = 0,016).

Es deliberadamente más estrecha que la que sostenían las corridas con
parseo regalado (+18,3 pp) y más fuerte que la de la corrida 3 (+7,5 pp,
no significativa). La historia de esas tres cifras es, en sí misma, un
resultado: **cuánta ventaja aparente de una arquitectura puede provenir
de cómo se monta la comparación**.

El precio de la gobernanza, medido: latencia adicional del pipeline
determinista (parseo, recuperación, política, verificación), un 9,3 % de
abstenciones que exigen intervención, y el coste de mantener catálogo,
handlers y postcondiciones.

### 9.2 Cuándo un agente directo sigue siendo preferible

Cuando el dominio no tiene efectos de escritura (consultas puras),
cuando la variedad de operaciones es demasiado alta para mantener un
catálogo, o cuando el coste de un error es bajo y el de la abstención
alto. La evidencia de este trabajo no dice que gobernar sea siempre
mejor; dice qué se compra y qué se paga.

### 9.3 Tres tensiones que no se resuelven a favor del número bonito

1. **R3: seguridad contra métrica de éxito.** La política obliga a
   simular en alto impacto, y eso hace estructuralmente imposible
   puntuar los casos R3 que el dataset espera ejecutados. Bajar la
   política para subir STSR habría sido optimizar la métrica, no el
   sistema.
2. **Abstención contra Top-1.** Calibrar el margen de abstención a cero
   sube Top-1 unos 7 puntos, pero elimina casi toda la abstención, que
   es parte de la tesis (H6). El experimento conserva el margen
   conservador.
3. **Temperatura contra H3.** La norma exige temperatura baja, y la
   temperatura 0 hace la estabilidad entre repeticiones trivialmente
   perfecta en los tres sistemas. H3, tal como está formulada, **no puede
   discriminar**. Se propone y se implementa una reformulación medible
   (H3b: coincidencia de estado entre **paráfrasis distintas** de la
   misma intención), cuya medición con LLM real queda declarada como
   pendiente.

### 9.4 Amenazas a la validez

**Interna.** El confundido proveedor↔régimen de parseo (Groq en las
corridas 3–4, OpenRouter en la 1) **queda resuelto** por la ejecución 5
(§8.9): con el proveedor fijo, C cae 6,7 puntos al parsear de verdad y B
solo 0,8, de modo que el efecto es atribuible al régimen y no al modelo.
Residuo declarado: el *false allow* de A depende del proveedor (0,333
con OpenRouter, 0,889 con Groq), aunque el de C es invariante.

**Externa.** Benchmark sintético y plantillado, un solo idioma, un solo
ERP simulado, modelos de nivel gratuito (no frontera). Las dos demos
contra Odoo real son evidencia parcial de transferencia, no
sustitutivo.

**La limitación externa más grave, ahora medida y no solo declarada.**
Se evaluaron 120 peticiones en registro coloquial, ajenas al generador
del benchmark. El recuperador TF-IDF de C cae de 0,733 a **0,381** de
Top-1; el selector LLM que usa B —mismo prompt, mismas herramientas,
mismo proveedor— cae solo de 0,898 a **0,750**. Como el enrutado es la
entrada de todo el pipeline de C, **la ventaja de +15 pp en STSR sobre B
no puede sostenerse fuera del corpus plantillado**: con texto real cabe
esperar que se estreche o se invierta. Los números del experimento
congelado siguen siendo correctos para lo que midieron; lo que esta
medición acota es hasta dónde se pueden extrapolar.

**Refinamiento posterior, que acota la gravedad de la limitación.** Un
tercer experimento (`docs/product-viability.md` §7.4, con mitad de
calibración y mitad held-out) muestra que la causa no es TF-IDF como
técnica sino las **descripciones de una línea** del catálogo:
enriquecerlas con sinónimos y formulaciones reales —en un fichero
aparte, sin tocar el catálogo congelado— lleva el Top-1 de 0,455 a
**0,886** en la mitad held-out, por encima del router LLM (0,818) y sin
coste alguno en tokens. La brecha de enrutado con texto real es, por
tanto, plausiblemente **corregible sin renunciar a la ventaja
arquitectónica**. Con n = 44 los intervalos se solapan y el corpus
procede de un solo autor, así que es una indicación fuerte y no una
demostración. Ninguno de los números del experimento congelado cambia:
midió el catálogo tal como estaba.

El mismo experimento arroja un matiz que corta en dirección contraria:
en las 36 peticiones que **ninguna** skill cubre, el selector LLM se
compromete con una herramienta en 30 (83 %) frente a 22 de TF-IDF
(61 %). El LLM enruta mejor y **se calla mucho peor**, que en un ERP es
la dirección peligrosa del error. De ahí que la capa de gobernanza
—validación de esquema, permisos, riesgo y postcondiciones, ninguno de
los cuales depende del router— resulte **más** necesaria, no menos, si
se sustituye la recuperación léxica por un router basado en LLM.

**De constructo.** Los detectores adversariales son léxicos y están
ajustados al texto del benchmark: medido con InjecAgent, 3,3 % de
detección fuera de distribución. La rúbrica de trazabilidad mide
presencia de evidencia, no calidad semántica. Las postcondiciones las
definieron los mismos autores que los handlers: riesgo de circularidad,
declarado.

**Estadística.** 120 unidades de inferencia; comparaciones múltiples
corregidas con Holm; pseudo-replicación explícitamente evitada (§3.4).

### 9.5 Dónde se concentran los defectos: un hallazgo sobre el proceso

Trece defectos encontrados y corregidos en el propio instrumento de
medida. Los más graves:

| # | Defecto | Consecuencia |
|---|---|---|
| — | Fuga de test (10 textos idénticos entre splits) | Validador tautológico; test contaminado |
| — | Conjunto 5 de STSR devolvía `True` incondicionalmente | Métrica de 5 componentes que era de 3 |
| — | Conjunto 4 duplicaba al conjunto 1 | Ídem |
| — | Pseudo-replicación (360 observaciones tratadas como independientes) | 15 órdenes de magnitud de significación fabricada |
| — | McNemar sin corrección de continuidad | Estadístico anticonservador |
| — | Bootstrap sin remuestreo | IC degenerado que el test aceptaba |
| #12 | Caché de LLM compartida entre sistemas | Los totales de tokens medían el orden de ejecución |
| #13 | Falta de normalización de argumentos | Sesgo asimétrico **contra** C |
| #14 | Los 9 casos `argument_out_of_range` del dataset, mal etiquetados | Un caso benigno cuenta como peligroso y contamina H4 |
| #15 | Denominador equivocado en el arnés de validación de producto | Habría reportado un derrumbe de −0,466 cuando el real es −0,352 |

Dos patrones, ambos utilizables como material metodológico:

**Primero: una comprobación que no puede fallar es peor que no tener
comprobación**, porque fabrica confianza. Cinco de los defectos tienen
exactamente esa forma. La regla adoptada tras el tercero —todo guard
nuevo debe demostrarse fallando, con fuga plantada, componente alterado
o entrada construida— es la que hizo detectables los siguientes.

**Segundo: el TDD estricto protege bien lo que se implementa contra un
requisito explícito, y protege mal lo que solo se calcula a partir de
una fórmula.** Los dos únicos supervivientes de 40 mutantes cayeron en
`statistics.py`, la capa que produce los números publicados. Sus tests
originales verificaban *la conclusión* del cálculo (¿es significativo?,
¿está en rango?) en vez de *el mecanismo* (¿es exactamente esta fórmula,
con esta corrección?), y ambas propiedades se cumplían igual con la
fórmula rota. La corrección consistió en sustituir aserciones de
conclusión por aserciones de mecanismo: valor exacto del estadístico,
anchura de intervalo no degenerada y proporcional al error estándar
teórico.

**Tercero, y el más incómodo: de quince defectos, trece salieron de
auditorías propias; dos los destapó una pregunta escéptica sobre
resultados que ya habían sido aceptados y publicados** (el #13, sobre un
resultado no significativo dado por bueno, y el #14, al preguntar si la
métrica de seguridad tenía sesgo). Es el patrón esperable: la
autoauditoría encuentra bien el código que se contradice consigo mismo,
y mal el código que hace exactamente lo que su autor creía que debía
hacer. Para eso hace falta alguien que dude del supuesto, no de la
implementación.

Un matiz sobre el #14 que merece registrarse: al corregirlo, el
resultado **mejoraría** para la tesis (el *false allow* de C pasaría de
0,111 a 0,000). Aun así el dataset no se corrigió, porque está congelado
y ese es exactamente el cambio post-hoc que la congelación existe para
impedir. Se publicó como análisis de sensibilidad junto a la cifra
contaminada.

### 9.6 Resultados negativos, reportados como tales

- La ventaja de C sobre B en éxito de tarea **no sobrevivió** al primer
  intento de parseo honesto (corrida 3, no significativa). Se publicó
  así mientras se creía correcta.
- Los **embeddings pierden** frente a TF-IDF en este benchmark, y el
  ranking híbrido no mejora al embedding puro.
- **H3 es no discriminable** por diseño.
- La **detección léxica no generaliza**: 3,3 % fuera de distribución.
- C es el sistema con **peor false-reuse risk** (0,215) en la corrida
  vigente, por encima de B (0,102).

---

## 10. Productivización

**API.** FastAPI sobre System C con autenticación de demo por cabecera,
`correlation_id` generado siempre en servidor (nunca aceptado del
cliente, para que la correlación de auditoría no se pueda falsear),
limitador de tasa en memoria y cuatro rutas: enviar petición, consultar
catálogo, consultar auditoría por correlación y conceder aprobación.

**Persistencia.** Auditoría y aprobaciones sobre SQLAlchemy Core, sin
`update` ni `delete` en la superficie, con PostgreSQL 16 provisionado
por Docker Compose. Declarado: **pgvector no se usa** — la recuperación
opera en proceso sobre 12 skills y añadirlo sería infraestructura sin
necesidad demostrada.

**Adaptador Odoo 19.** Sobre la API JSON-2, con allowlist de modelos y
campos aplicada **antes** de cualquier HTTP, sin operación de borrado
(estructural, no convención), timeout, logs redactados y credenciales
solo por entorno. Es intercambiable con `FakeERPAdapter` a través de un
`Protocol` común, lo que permitió ejecutar el pipeline gobernado
completo contra un ERP real sin duplicar lógica.

**Reproducibilidad.** `Makefile` con objetivos para tests, cobertura,
validación de dataset, verificación de congelación, benchmark de humo,
experimento, exportación a CSV y figuras. CI ejecuta instalación, lint,
type-check, tests, cobertura, validación de dataset, smoke benchmark,
verificación de congelación y subida de artefactos.

**Insumos de dashboard.** Tablas CSV y cinco figuras reproducibles
PNG/SVG regeneradas desde el JSON versionado. El workbook de Tableau es
trabajo manual pendiente y se declara como tal.

**Valor empresarial.** Con supuestos declarados: menor coste de
inferencia (3,9× frente a B), menor coste esperado de error (8× menos
ejecuciones inseguras), y capacidad de auditoría que permite reconstruir
por qué se tomó cada decisión. No se presenta como ahorro medido ni como
satisfacción de usuario, que no se han observado.

### 10.1 Transferencia a producto: qué sostiene la evidencia

El análisis completo está en
[`docs/product-viability.md`](product-viability.md). Su tesis central es
que **la evidencia que aguanta ante un tribunal y la que aguanta ante un
cliente no son la misma**, y que confundirlas produciría afirmaciones
comerciales falsas.

**Sostiene un producto:** que ninguna inyección consiga una mutación no
autorizada por ninguno de los tres canales de ataque (0/1.530, incluido
el brazo que concede el LLM entero al atacante); que la arquitectura
elimine una llamada al LLM por petición, demostrado por aritmética; que
la decisión sea invariante al proveedor mientras la de un agente sin
gobernanza no lo es; que el bloqueo se sostenga contra un ERP real
verificado por relectura independiente; y la trazabilidad de 0,820.

**No sostiene nada comercial:** la detección léxica de ataques (3,3 %
fuera de distribución, y 8 de 9 casos del test bloqueados por patrones
escritos sobre ese mismo corpus), el «8×» sin su intervalo (n = 9, IC
[0,020, 0,435]), la ventaja de éxito de tarea (+15 pp, modesta), y
cualquier cifra de ahorro (H8 es sensibilidad, no gasto medido).

La consecuencia es de diseño, no solo de discurso: **el producto no
puede apoyarse en que el sistema entienda mejor, sino en que restrinja
mejor**. Eso lo sitúa como plano de control bajo cualquier agente, no
como agente competidor.

De los tres huecos que decidirían su viabilidad, **el tercero sí se
midió** y su respuesta cambió el diseño propuesto. Sobre 120 peticiones
en registro coloquial, partidas en mitad de calibración y mitad
held-out:

| Diseño de enrutado | Top-1 held-out | Rechaza bien | Tokens |
|---|---|---|---|
| TF-IDF con descripciones del catálogo | 0,455 | 0,062 | 0 |
| TF-IDF con descripciones **enriquecidas** | **0,886** | 0,000 | 0 |
| Router LLM (el del sistema B) | 0,818 | 0,250 | 592 |
| Filtro de dominio + TF-IDF enriquecido | 0,864 | 0,250 | **0** |

La lectura es que **el cuello de botella no era el algoritmo de
recuperación sino la descripción de una línea por skill**. Enriquecerla
con sinónimos y formulaciones reales iguala o supera al router LLM sin
gastar un token, lo que preserva la ventaja arquitectónica en lugar de
devolverla. Consecuencia concreta para el producto: el alta de una skill
debe pedir sinónimos y ejemplos de uso reales como **campo del
contrato**, no una frase descriptiva.

**El hallazgo se verificó además con autores distintos**, que es la
prueba que el corpus propio no permitía hacer. Sobre MASSIVE es-ES
(Amazon, CC-BY-4.0: 16.521 frases, 60 intenciones, **20 crowdworkers
identificados**), partiendo por persona y no por frase —el
enriquecimiento se construye solo con frases de la mitad de los autores
y se evalúa solo sobre la otra mitad, sin solape— la precisión de
enrutado sube de **0,365 a 0,634** con diez ejemplos por intención, y
satura ahí (k=20 da 0,629). Dos consecuencias operativas: bastan **unas
diez formulaciones reales por skill**, y el umbral de abstención óptimo
**baja** al enriquecer (0,55 → 0,32), de modo que una constante fija
queda mal puesta en cuanto cambian las descripciones. El dominio de ese
corpus no es ERP, así que la prueba es del **mecanismo**, no del
producto.

Los otros dos huecos —coste de añadir una skill y tiempo humano por
abstención— **siguen sin medir**, y se declaran como validación de
producto pendiente. El detalle completo, con intervalos y con lo que
estos números no permiten afirmar, está en
[`docs/product-viability.md`](product-viability.md) §7.

---

## 11. Conclusiones

### 11.1 Respuesta a la pregunta principal

Una arquitectura que separa la interpretación probabilística de la
ejecución determinista **sí** reduce errores de seguridad de forma
contundente (8× menos *false allow*, sin aumentar los falsos bloqueos),
**sí** reduce el consumo de tokens (3,9× frente a herramientas tipadas,
sustituyendo la llamada de selección por recuperación léxica), y **mejora
modestamente** el éxito de tarea (+15,0 pp, IC95 [+4,2, +25,8]). La
variabilidad entre ejecuciones no es medible con la formulación original
de H3 porque la temperatura exigida por la norma la vuelve trivial.

### 11.2 Respuestas a las preguntas secundarias

1. **Precisión de recuperación ante paráfrasis:** Top-1 = 0,780,
   Top-3 = 0,941, MRR = 0,855 en test, con TF-IDF superando a embeddings
   y a ranking híbrido en dev y validación.
2. **Errores que previene el verificador:** ejecuciones bajo rol no
   autorizado, argumentos fuera de tipo o rango, operaciones con framing
   irreversible o de alcance masivo, y mutaciones cuyo estado final no
   coincide con la postcondición declarada.
3. **Reducción de tokens por reutilización:** 3,9× frente a herramientas
   tipadas; el mecanismo es la sustitución de la llamada de selección.
4. **Variabilidad:** no discriminable con temperatura 0; se propone H3b
   sobre paráfrasis como reformulación medible.
5. **Latencia adicional de la gobernanza:** instrumentada por ejecución;
   el sobrecoste es el del pipeline determinista, no de llamadas extra
   al modelo.
6. **Qué se automatiza sin aprobación:** R0 y R1; R2 exige aprobación y
   R3 permanece en simulación.
7. **Cuándo abstenerse:** score bajo, margen insuficiente entre
   candidatas, campos requeridos ausentes o conflicto de política.
8. **Umbral, cobertura y riesgo:** calibrar el margen a cero sube Top-1
   unos 7 puntos y elimina casi toda la abstención — objetivos en
   conflicto, resueltos a favor de la configuración conservadora.
9. **Componente que más aporta:** el policy engine con validación
   previa; es el responsable del resultado de seguridad y de
   trazabilidad, invariante a proveedor y a régimen de parseo.
10. **Cuándo preferir un agente directo:** dominios sin escritura,
    catálogos inviables de mantener, o coste de error bajo frente a
    coste de abstención alto.

### 11.3 Trabajo futuro

Ejecución del brazo exploratorio de temperatura y de la medición de H3b
con LLM real; poblado de precondiciones del catálogo con su propia
corrida; detección semántica de intención frente a la petición original,
que es lo que el resultado de InjecAgent señala como límite estructural
del enfoque léxico; mapeo del resto del catálogo a modelos reales de
Odoo; kappa de anotación; evaluación con anotadores y usuarios reales.
(La réplica de ambos regímenes de parseo en un mismo proveedor, que
figuraba aquí, **se ejecutó**: §7.2 y §9.4.)

**La línea más prometedora, y la que este trabajo deja abierta con
evidencia preliminar a favor:** convertir la descripción de la skill en
un artefacto de primera clase del contrato —sinónimos, formulaciones
reales, ejemplos de uso— en lugar de una frase de una línea. La medición
de §10.1 sugiere que ahí está la mayor parte de la brecha de enrutado
con texto real, y que cerrarla **no cuesta tokens**. Queda por
demostrar con peticiones de autores distintos, que es la prueba de
generalización que el corpus disponible no permite hacer.

### 11.4 Cierre

El valor de este trabajo no está en presentar ERP Agent OS como solución
universal. Hay muchos prototipos que conectan un modelo de lenguaje con
un ERP, y la arquitectura empleada —skills versionadas, políticas,
auditoría, postcondiciones— no es novedosa por sí misma.

Lo que este trabajo aporta es de otro tipo. Aporta **una forma más
exigente de preguntar por la seguridad de un agente**: no si un detector
dispara, sino si el daño ocurre cuando se concede que el detector ha
fallado y el modelo está comprometido. Bajo esa pregunta, la respuesta
fue 0 de 1.530, con un dataset externo y un brazo que entrega el modelo
al atacante.

Y aporta **el registro de haberse equivocado en público**. Tres veces la
medición honesta produjo un resultado peor que la intuición de partida,
y las tres se publicaron antes de encontrar el matiz que las mejoraba.
Quince defectos del instrumento quedaron documentados con su fecha, su
causa y qué habría pasado sin corregirlos; dos de ellos los destapó una
pregunta escéptica sobre resultados ya aceptados, y uno se dejó sin
corregir precisamente porque corregirlo habría favorecido a la
hipótesis.

Un trabajo experimental que solo confirma lo que esperaba debe levantar
sospecha. Este documenta dónde se equivocó, cómo lo descubrió y qué
quedó en pie después. Eso —más que cualquiera de sus cifras— es lo que
pretende dejar utilizable para quien venga detrás.

---

## 12. Bibliografía

- Andriushchenko, M., Souly, A., Dziemian, M., et al. (2024). *AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents*. arXiv:2410.09024.
- Autio, C., Schwartz, R., Dunietz, J., et al. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile*. NIST AI 600-1.
- Li, M., Zhao, Y., Yu, B., et al. (2023). *API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs*. arXiv:2304.08244.
- Liu, X., Yu, H., Zhang, H., et al. (2023). *AgentBench: Evaluating LLMs as Agents*. arXiv:2308.03688.
- Reimers, N., y Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. arXiv:1908.10084.
- Schick, T., Dwivedi-Yu, J., Dessì, R., et al. (2023). *Toolformer: Language Models Can Teach Themselves to Use Tools*. arXiv:2302.04761.
- Yao, S., Shinn, N., Razavi, P., y Narasimhan, K. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*. arXiv:2406.12045.
- Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv:2210.03629.
- Zhan, Q., Liang, Z., Ying, Z., y Kang, D. (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents*. arXiv:2403.02691.
- Documentación oficial de Odoo 19 (API externa JSON-2).
- Especificación oficial de Model Context Protocol.
- Documentación oficial de PostgreSQL y pgvector.

**Nota de honestidad:** no se ha realizado una revisión sistemática de
literatura con protocolo de búsqueda documentado. La bibliografía es la
lista razonada de la especificación normativa, ampliada con las tres
referencias incorporadas durante la ejecución (τ-bench, InjecAgent,
AgentHarm). Esta limitación se declara en lugar de presentarla como
revisión sistemática.

---

## 13. Anexos

### Anexo A. Reproducción

```sh
uv sync
uv run python -m pytest                       # 391 tests
uv run python scripts/freeze_protocol.py --verify

# Experimento (arquitectura-solo, sin red)
uv run python scripts/run_experiment.py

# Experimento confirmatorio con LLM real y parseo real
uv run python scripts/run_experiment.py --real-llm --real-parser \
    --provider groq

# Comparación de recuperadores (dev + validación, nunca test)
uv run python scripts/compare_retrievers.py

# Robustez adversarial
uv run python scripts/injecagent_stress_test.py
uv run python scripts/injection_resistance_test.py

# Demos contra Odoo 19 real (requiere instancia de desarrollo)
uv run python scripts/odoo_governed_demo.py
uv run python scripts/odoo_adversarial_demo.py

# Exportación y figuras
uv run python scripts/export_results.py
make figures
```

### Anexo B. Artefactos de datos

| Fichero | Contenido |
|---|---|
| `data/bench_v1.jsonl` | 480 casos del benchmark |
| `data/freeze_manifest.json` | Hashes del protocolo congelado (schema 1.1) |
| `data/experiment_results.json` | Corrida confirmatoria (OpenRouter, parseo regalado) |
| `data/experiment_results_real_parser.json` | **Corrida vigente** (Groq, parseo real + normalización) |
| `data/experiment_results_groq_given_args.json` | Réplica que separa proveedor de régimen (Groq, argumentos dados) |
| `data/retriever_comparison.json` | TF-IDF vs embeddings vs híbrido |
| `data/injecagent_stress_test_results.json` | Detección léxica, 510 payloads |
| `data/injection_resistance_results.json` | Resistencia por canal, 1.530 casos |
| `data/odoo_governed_demo_results.json` | Pipeline gobernado contra Odoo real |
| `data/odoo_adversarial_results.json` | Casos adversariales contra Odoo real |
| `data/real_requests_eval.json` | Recuperadores sobre 120 peticiones reales (validación de producto) |
| `data/real_requests_llm_eval.json` | Router LLM sobre las mismas peticiones, 120 llamadas reales |
| `data/router_designs_eval.json` | Cinco diseños de enrutado, calibrados en dev y juzgados held-out |
| `data/skill_profiles.json` | Descripciones enriquecidas, **fuera** del catálogo congelado |
| `data/annotation_review_sheet.csv` | Muestra estratificada para el segundo anotador (**pendiente**) |
| `data/real_requests.csv` | Peticiones reales — **gitignorado**, puede contener datos de clientes |

### Anexo C. Documentación técnica complementaria

`docs/results.md` (resultados completos con las cinco corridas),
`docs/dataset-card.md`, `docs/experiment-protocol.md`,
`docs/threat-model.md`, `docs/traceability-rubric.md`,
`docs/retriever-comparison.md`, `docs/injecagent-stress-test.md`,
`docs/odoo-demo.md`, `docs/audit.md` (registro completo de los quince
defectos), `docs/spec-coverage.md` (cobertura §-por-§ de la
especificación normativa), `docs/product-viability.md` (transferencia a
producto: qué afirmación comercial sostiene cada número y cuál no),
`docs/defensa.md` (guion de defensa y vídeo: en qué orden contar los
resultados y cómo responder las siete preguntas difíciles).

### Anexo D. Trabajo pendiente declarado

1. **Kappa de anotación** — instrumento generado, paso humano pendiente.
2. **Workbook de Tableau** — insumos generados, montaje manual.
3. **Ejecución del brazo de temperatura y medición de H3b con LLM real.**
4. **Vídeo de competición y presentación de defensa.**
