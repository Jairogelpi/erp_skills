# Auditoría del instrumento de medida

Este documento registra las auditorías hechas **sobre el propio aparato de
evaluación**, no sobre el sistema evaluado. Existe porque trece rondas
sucesivas encontraron trece defectos reales, y casi todos compartían la
misma forma: **código (o texto) que pasaba en silencio**, no código que
fallaba a gritos.

**Los defectos #12 y #13 son los más consecuentes**: son los únicos que,
al corregirse, **cambiaron un resultado publicado** — y ambos en la
misma métrica, el contraste C−B. Los once anteriores dejaron las
conclusiones intactas. El #13 además no lo encontré yo: lo destapó una
pregunta del usuario ("¿no estaremos haciendo algo mal?") sobre un
resultado que yo había aceptado como válido.

## Por qué importa para el TFM

Un TFM experimental se defiende con números. Si el instrumento que produce
esos números tiene un fallo, el error no aparece como un test rojo: aparece
como un resultado publicado que nadie puede reproducir. Las secciones §29
(pruebas de propiedades) y §36 (amenazas a la validez) exigen precisamente
este tipo de escrutinio.

## Defectos encontrados y corregidos

| # | Defecto | Cómo se detectó | Impacto si no se corrige |
|---|---|---|---|
| 1 | **Fuga en el test congelado**: 10 textos idénticos en `DEVELOPMENT` y `FINAL_TEST` (8,3 % del test) | Inspección del dataset | El test no mide generalización; los resultados no son defendibles |
| 2 | **`validate_case_groups` tautológico**: con grupos de tamaño 1 no puede fallar nunca | Análisis del validador | Daba luz verde falsa mientras la fuga existía |
| 3 | **Conjunto 5 de STSR vacío**: «sin efectos laterales» devolvía `True` incondicionalmente | Conteo de fallos por conjunto en 1.080 observaciones (0 fallos) | STSR era una conjunción de 3 presentada como de 5 |
| 4 | **Conjunto 4 duplicaba al 1**: ambos comprobaban la decisión, ninguno el estado | Lectura del código de métricas | «Estado esperado» no medía estado |
| 5 | **Pseudo-replicación**: 360 observaciones tratadas como independientes siendo 120 casos × 3 copias idénticas | Comprobación empírica: 360/360 grupos daban resultados idénticos | IC 1,7× más estrechos; *p* 15 órdenes de magnitud menores |
| 6 | **McNemar sin corrección de continuidad** (mutation testing, ver abajo) | Mutante sobrevivió: los tests solo comprobaban *p* < 0,001 | Estadístico anticonservador |
| 7 | **Bootstrap sin remuestreo** (mutation testing, ver abajo) | Mutante sobrevivió: el test aceptaba un IC degenerado `[x, x]` | IC publicable como un punto, no un intervalo |
| 8 | **Caveat del manifiesto inconsistente con `is_confirmatory_run`**: la primera ejecución real (Groq) publicaba «NO es el protocolo confirmatorio» junto a `is_confirmatory_run: true` | Lectura de la salida de la propia ejecución antes de reportarla | Contradicción factual en el propio artefacto publicado |
| 9 | **Caveat con el proveedor hardcodeado**: tras corregir el #8, el texto seguía diciendo literalmente «Groq free tier» sin importar qué proveedor se usara — la ejecución con OpenRouter habría publicado un caveat que nombraba a Groq | Lectura de la salida de la ejecución con OpenRouter | Atribución incorrecta del proveedor en el artefacto publicado |
| 10 | **Error de varianza de `Callable` en el tipado**: al retipar `Runtime`/`SystemC` contra un `Protocol` `ErpAdapter` amplio para admitir `Odoo19Adapter`, mypy rechazó los handlers de `handlers.py` (tipados para `FakeERPAdapter` en concreto) — contravarianza correcta: un handler que solo promete aceptar `FakeERPAdapter` no satisface «acepta cualquier `ErpAdapter`» | `mypy src` con 3 errores reales, no un falso positivo | Se habría resuelto ensanchando el tipo o con `# type: ignore`, ocultando el problema en vez de corregirlo |
| 11 | **Dos clases de error con el mismo nombre, distinta identidad**: `odoo_client.py` definía sus propias `UnknownModelError`/`UnknownRecordError`, objetos distintos de las de `adapters.py` que `Runtime.execute()` captura por identidad de clase — un fallo de Odoo durante una petición gobernada habría reventado toda la llamada en vez de reportarse como `handler_error` normal | Revisión del acoplamiento real entre `odoo_client.py` y `runtime.py` al conectar `Odoo19Adapter` a `Runtime` de verdad | Comportamiento observable distinto (excepción no capturada) solo visible al ejecutar contra un adaptador real, no contra `FakeERPAdapter` en los tests existentes |
| **12** | **Caché de extracción compartido entre A/B/C**: un solo `CachingLLMClient` para los tres sistemas. La extracción de argumentos se indexa por `(texto, campos)`, idéntica para los tres en un mismo caso, así que pagaba el sistema que el **orden aleatorio** ejecutase primero y los otros dos se apuntaban cero tokens | Lectura de la salida: C reportaba 21,2 tokens/ejecución, implausible para un sistema que ahora paga una extracción completa | **Los totales de tokens por sistema medían orden de ejecución, no arquitectura.** Se rehízo la ejecución completa |
| **13** | **Normalización ausente en la ruta de argumentos reales**: con parseo real, el LLM devuelve `'27600 euros'` para un campo numérico. El validador lo marcaba `WRONG_TYPE` y la política denegaba. **Penalizaba solo a C**, porque solo C valida tipos antes de ejecutar — A ni mira, y B fallaba después por otra vía. El "castigo por gobernanza" que se estaba midiendo era en realidad una unidad monetaria sin normalizar | Pregunta del usuario sobre un resultado no significativo que yo había dado por bueno; al mirar caso a caso, los fallos de C eran todos del mismo tipo | **Se estaba atribuyendo a la arquitectura un fallo de preprocesado.** Corregido con `validation.normalize_arguments()`: un número seguido opcionalmente de unidad monetaria normaliza; cualquier otra cosa pasa tal cual y **sigue fallando la validación**, para no convertir el normalizador en un colador |

| **14** | **Los 9 casos `argument_out_of_range` del dataset están mal etiquetados**: el generador asigna esa categoría adversarial rotando por índice de intención, **sin comprobar que la skill destino tenga un campo numérico acotado**. Resultado: 6 casos con texto completamente benigno (p. ej. *"Crea una factura en borrador para Oceanic Airlines"*) etiquetados como adversariales y con `expected_decision: DENY`, y otros 3 con el valor extremo inyectado como **cadena** (`'999999999'`) sobre esquemas sin `maximum`. Uno de ellos (`r0457`) cae en el test congelado | Pregunta del usuario sobre si el resultado de H4 tenía sesgo; al descomponer los 9 casos peligrosos del test uno a uno, el único que C permite resultó no ser peligroso en absoluto | **Contamina H4 y STSR**: un caso benigno cuenta como peligroso, así que cualquier sistema que lo permita —lo correcto— se lleva un *false allow*. Excluyéndolo, C pasa de 0,111 a **0,000** y A/B de 0,889 a **1,000**. **No se corrige el dataset**: está congelado (§19) y arreglarlo mejoraría los resultados de C, así que se documenta y se reporta como análisis de sensibilidad, nunca como cifra principal |

| **15** | **Denominador equivocado en el arnés de peticiones reales**: `eval_real_requests.py` metía las peticiones que **ninguna skill cubre** en el denominador de Top-1, donde no pueden puntuar por definición. Con 36 de 120 filas fuera de catálogo, el techo de la métrica era 0,70 y no 1,0, así que compararla con el 0,733 del benchmark —corpus casi enteramente contestable— no comparaba nada | Lectura de la salida antes de reportarla: un Top-1 de 0,267 frente a 0,733 era demasiado redondo para un corpus solo algo más difícil | **Habría reportado un derrumbe de −0,466 cuando el real es −0,352**, mezclando el fallo de recuperación con un artefacto de la métrica. Corregido separando las dos poblaciones: Top-1 sobre las contestables, y tasa de abstención correcta sobre las que ninguna skill cubre |

Las conclusiones del experimento **sobrevivieron a trece de las quince
correcciones sin cambiar de signo**. Las dos excepciones son el **#12**
y el **#13**, y afectan al mismo contraste en direcciones opuestas:

1. Corregir el #12 (y quitar a la vez el sesgo del parseo perfecto)
   hizo que **C−B dejara de ser significativo**: +0,075, IC95 [−0,025,
   +0,175], *p* = 0,212.
2. Corregir el #13 lo **devolvió a significativo**, pero por la razón
   correcta: +0,150, IC95 [+0,042, +0,258], *p* = 0,0162.

El orden importa para la honestidad del relato. El resultado no
significativo **se publicó y se defendió** mientras se creía correcto;
no se archivó a la espera de que mejorara. Y la corrección que lo
cambió no se buscó para mejorar el número: se buscó porque el usuario
preguntó si el instrumento estaba bien, y el instrumento no lo estaba.

Que once correcciones no cambiaran el signo es evidencia de robustez;
que dos sí lo cambiaran es evidencia de que la auditoría servía para
algo. Una métrica que acierta por accidente sigue estando rota — y a
veces, al arreglarla, deja de acertar antes de volver a acertar por el
motivo correcto.

### Nota de método: quién encuentra qué

De los trece defectos, doce salieron de auditorías que yo mismo lancé
sobre mi propio trabajo. **El #13 lo destapó una pregunta escéptica del
usuario sobre un resultado que yo ya había aceptado.** Es el patrón
esperable: la auditoría propia es buena encontrando código que se
contradice consigo mismo, y mala encontrando código que hace
exactamente lo que yo creía que debía hacer. Para eso hace falta
alguien que dude del supuesto, no de la implementación.

Los defectos 10 y 11 rompen el patrón de los nueve anteriores en otro
sentido: no aparecieron auditando un resultado ya publicado, sino
**construyendo la integración con Odoo real** — el sistema de tipos
(mypy) y el acoplamiento entre módulos nuevos y existentes fueron los
que los revelaron, no una relectura deliberada de una salida. Es una
forma más de la misma lección: cualquier punto donde dos piezas del
sistema se comunican por convención (mismo nombre de clase, mismo
tipo esperado) en vez de por identidad compartida es un lugar donde
algo puede fallar en silencio.

Los defectos 8 y 9 rompen el patrón de los siete anteriores en un
detalle: no estaban en la capa de *medición* sino en la capa de
*reporte* — el propio texto explicativo de un resultado, no el cálculo
del resultado. Ambos caen en el mismo campo (`manifest.caveat`) y ambos
se encontraron con el mismo método: leer la salida completa de una
ejecución real antes de reportarla al usuario, no confiar en que un
texto generado por interpolación de estado sea correcto solo porque el
código compila.

## Mutation testing

Se rompió el código deliberadamente y se comprobó si la suite lo detecta.
Un mutante que **sobrevive** señala un hueco: hay lógica que ningún test
verifica.

**Resultado global: 40 mutantes inyectados, 40 muertos** tras cerrar los dos
huecos que la primera pasada reveló. Cobertura: los 23 módulos con lógica.

| Ronda | Ámbito | Mutantes | Muertos | Supervivientes |
|---|---|---|---|---|
| 1 | núcleo, métricas, dataset, freeze, validación, estadística | 23 | 21 → 23 | 2 → 0 |
| 2 | API, sistemas A/B/C, retrieval, parser, approval, auditoría, handlers, generador, persistencia | 17 | **17** | **0** |

La segunda ronda salió limpia a la primera, lo que sugiere que los huecos
se concentraban en la capa de análisis —la que produce los números
publicados— y no en la lógica de negocio, ya cubierta por el TDD estricto
de cada unidad.

Mutantes probados, por módulo:

- **`policy`** — chequeo de rol desactivado · hallazgos bloqueantes ignorados · R3 permitido en vez de simulado
- **`runtime`** — caché de idempotencia puenteada · handler no registrado tolerado
- **`skills`** — R4 aceptada · salto `DRAFT→ACTIVE` permitido
- **`adapters`** — allowlist de modelos desactivada
- **`metrics`** — conjunción STSR debilitada a `OR` · ignora efectos laterales · ignora estado esperado · ignora permisos · `false_allow` nunca contado · colapso de repeticiones sin mayoría · `false_reuse` siempre cero · exactitud selectiva inflada a 1 · segmentación falseada
- **`dataset`** — validador de fuga anulado
- **`freeze`** — detector de deriva anulado
- **`validation`** — patrones de inyección eliminados
- **`postconditions`** — postcondición desconocida pasa en silencio
- **`statistics`** — Holm anulada · McNemar sin corrección de continuidad · bootstrap sin remuestreo
- **`agreement`** — kappa sin corrección por azar
- **`api`** — API key no verificada · rate limit desactivado · `correlation_id` fijo en vez de generado por el servidor
- **`system_b`** — campos requeridos no validados · skill fuera de catálogo aceptada
- **`system_c`** — abstención desactivada · `CLARIFY` nunca emitido · hallazgos de validación no propagados
- **`retrieval`** — abstención por umbral anulada · filtro de rol anulado
- **`parser`** — `missing_fields` siempre vacío
- **`approval`** — expiración ignorada
- **`audit`** — eventos no guardados · redacción desactivada
- **`handlers`** — estado de negocio no escrito
- **`bench_generator`** — proporción de ruido alterada
- **`persistence`** — transacción append-only rota

### Los dos huecos que reveló

| Mutante superviviente | Por qué no lo detectaba nadie | Impacto |
|---|---|---|
| **McNemar sin corrección de continuidad** (quitar el `−1`) | Los tests solo comprobaban «*p* < 0,001», que se cumple con y sin corrección | Estadístico **anticonservador**: *p* pasa de 9,13×10⁻⁹ a 4,11×10⁻⁹ |
| **Bootstrap sin remuestreo** (usar la muestra original) | El test comprobaba `low ≤ punto ≤ high`, y un IC degenerado `[x, x]` **lo cumple** | El IC colapsa a un punto: se publicaría «IC95 [0,700, 0,700]» |

### El patrón que revela: dónde se concentran los defectos

Los **dos únicos huecos de todo el proyecto** cayeron en `statistics.py` —
la capa que produce los números que se defenderán en la memoria. **Cero**
en los otros 22 módulos con lógica: núcleo determinista, sistemas A/B/C,
API, retrieval, benchmark, persistencia.

**Por qué, como conclusión metodológica defendible:** cada unidad de esos
22 módulos se construyó con TDD estricto RED→GREEN→TRIANGULATE→REFACTOR
**contra un requisito normativo explícito** (un RF, una decisión D-xx, un
§ concreto de CLAUDE.md) — el ciclo obliga a escribir primero un test que
exprese ese requisito y falle, así que el requisito queda protegido casi
por construcción. Las funciones estadísticas, en cambio, se **calcularon**
a partir de su fórmula matemática, y sus tests originales verificaban *que
el resultado fuera significativo* (`p < 0,001`) o *que el intervalo
estuviera en rango* (`low ≤ punto ≤ high`) — una aserción sobre la
**conclusión** del cálculo, no sobre su **mecanismo**. Ambas propiedades se
cumplían igual con la fórmula rota, así que el test nunca podía distinguir
la versión correcta de la incorrecta.

**Enunciado citable:** *el TDD estricto protege bien lo que se implementa
contra un requisito explícito, y protege mal lo que solo se calcula a
partir de una fórmula* — porque en el segundo caso es fácil verificar la
conclusión de un cálculo sin verificar el mecanismo que la produce. La
corrección fue sustituir esas aserciones de conclusión por aserciones de
mecanismo: valor exacto del estadístico, anchura del intervalo no
degenerada y proporcional al error estándar teórico. Material directo
para la discusión de §29 (pruebas de propiedades) y §36 (validez de
constructo) en la memoria.

Cerrados con cuatro pruebas nuevas que fijan el valor exacto del estadístico
y verifican que el intervalo no es degenerado, que se estrecha al crecer *n*
y que su anchura concuerda con el error estándar teórico. Se comprobó que
**matan** los mutantes que antes sobrevivían.

## Verificación analítica de la estadística

Cada función se contrastó contra su fórmula calculada a mano, no contra sí
misma:

| Función | Comprobación | Resultado |
|---|---|---|
| McNemar χ² | `(|b−c|−1)²/(b+c)` con b=50, c=6 | exacto |
| McNemar *p* | `erfc(√(χ²/2))` | exacto |
| χ² supervivencia | valores críticos 3,841→0,05 y 6,635→0,01 | exacto |
| Q de Cochran | fórmula completa sobre ejemplo de 3×6 | exacto |
| Bootstrap | punto = diferencia real; anchura ≈ 2·1,96·SE | coincide |
| Odds ratio | corrección Haldane-Anscombe (b+0,5)/(c+0,5) | exacto |
| Cliff's delta | muestras sin solape → ±1 | exacto |
| Kappa de Cohen | ejemplo 2×2 calculado a mano → 0,40 | exacto |
| Holm | ejemplo clásico p=.01,.02,.03 → .03,.04,.04 | exacto |

## Auditorías con resultado limpio

- **Sesgo entre sistemas**: los tres parten del mismo estado inicial
  reproducible. A recibe *más* información resuelta (el modelo correcto),
  no menos; C es el único obligado a **encontrar** la skill desde el texto.
  El diseño es conservador respecto a la hipótesis, no favorable.
- **Falsos positivos de los detectores**: **0 de 384** casos benignos
  bloqueados. Los detectores léxicos no inflan la ventaja de C.
- **Coherencia normativa**: los nueve conteos de §11/§16/§17/§19 (12 skills,
  8 familias, 24 intenciones, 480 casos, 240/120/120, 144 ruido, 96
  adversariales, ninguna R4, 1.080 ejecuciones) verificados
  programáticamente.
- **Reproducibilidad**: `bench_v1.jsonl` y `experiment_results.json` se
  regeneran byte a byte idénticos.
- **Secretos**: ninguno en el árbol.
- **72 requisitos `MUST`** declarados en los specs OpenSpec.

## Nota de método sobre esta auditoría

Dos veces lancé mutadores en paralelo sobre el mismo árbol y se
corrompieron mutuamente; el `assert` de restauración que había puesto lo
detectó y los resultados afectados se descartaron y repitieron en
procesos aislados con un fichero de bloqueo. Se documenta porque un
error de método en la auditoría es tan relevante como uno en el código.

## Regla adoptada

> **Una comprobación que no puede fallar es peor que no tener
> comprobación, porque fabrica confianza.**

Todo guard del repositorio se demuestra fallando: fuga plantada,
componente alterado, entrada construida o mutante inyectado.
