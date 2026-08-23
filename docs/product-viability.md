# De los resultados a un producto: qué sostiene la evidencia y qué no

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** (marcador exigido
> por el contrato automático `src/erp_agent_os/claims.py` — ver la nota
> siguiente antes de leerlo como el estado real)
>
> **Actualizado 2026-08-23.** La campaña confirmatoria v2.1
> (`docs/results-v2.1.md`) ya terminó y cambia lo que se puede afirmar
> ante un cliente en un punto central: **la detección activa de peligro
> sobre peticiones ambiguas no se sostiene** (H4, 19,0 % de mutación no
> autorizada sobre 315 casos reales). Lo que sí sigue de pie es más
> estrecho — confinamiento bajo modelo comprometido, coste, trazabilidad
> — y este documento se ha revisado para no vender la parte que ya no
> aguanta.

Documento de **transferencia**, no de investigación. Traduce los
resultados medidos (`docs/results-v2.1.md`, la campaña confirmatoria) a
qué se puede afirmar ante un cliente, qué producto sostienen y qué falta
construir.

Regla que gobierna todo lo que sigue: **cada afirmación comercial debe
apuntar a un número reproducible de este repositorio**. Lo que no
cumpla eso, no se dice.

---

## 1. Evidencia que aguanta un cliente

| Afirmación | Número que la sostiene | Dónde |
|---|---|---|
| **Aunque el modelo esté comprometido, no puede escribir fuera de contrato** | **0 / 1.530** mutaciones no autorizadas, con 510 payloads externos por tres canales, incluido un brazo que **concede el LLM entero al atacante** (510/510 `DENY`) | `docs/injecagent-stress-test.md`, `data/injection_resistance_results.json` |
| **Una llamada al LLM menos por petición** | Confirmatorio: C consume 468 y 648 tokens menos que A y B respectivamente por ejecución, IC95 completo por debajo de cero contra ambos | `docs/results-v2.1.md` §3, H2 |
| **Cada acción queda reconstruible** | Confirmatorio: +42,7 puntos porcentuales de reconstrucción completa de auditoría frente a A (*p*=2,85e-112), aunque con la salvedad de que A/B no tienen esa capacidad por diseño (§7 del mismo documento) | `docs/results-v2.1.md` §7, H7 |
| **El bloqueo funciona contra un ERP real, no solo en simulador** | Escritura R2 sin aprobación bloqueada contra Odoo 19, verificada por **relectura independiente**; tras conceder aprobación, la misma petición escribe | `docs/odoo-demo.md`, `data/odoo_governed_demo_results.json` |

**Retirada de esta tabla, con la campaña confirmatoria delante:** «la
decisión no depende del modelo» (*false allow* 0,111 con los tres
proveedores). Era una cifra de v1, nunca probada en la campaña
confirmatoria de v2.1 (un solo proveedor), y en todo caso la definición
estricta de *false allow* de v2.1 muestra que C falla el 19 % de las
veces sobre peticiones ambiguas — ver §2.

## 2. Evidencia que NO aguanta, y que por tanto no se usa

| Lo que sería tentador decir | Por qué no se dice |
|---|---|
| **«Detectamos peticiones peligrosas» / «somos más seguros que un agente sin gobierno»** | **Confirmatorio, no solo prudencia:** sobre 315 escenarios peligrosos reales, C deja pasar una mutación no autorizada en el **19,0 %** de los casos — casi 4× el umbral que se prerregistró. Localizado en 5 de 7 categorías de ataque; las otras 2 (permisos insuficientes, modificación masiva disfrazada) funcionan sin fallos. Este es el hallazgo que más debe pesar en cualquier conversación comercial |
| «Detectamos ataques de inyección de prompts» | **3,3 %** de detección fuera de distribución (InjecAgent, 510 casos externos). Es detección dentro de distribución, no una capacidad general |
| «8× más seguro» a secas | Era la cifra exploratoria de v1 (**n = 9** casos peligrosos, IC de Wilson [0,020, 0,435]). La campaña confirmatoria (n=315) mide lo contrario — ver arriba |
| «+15 pp de éxito de tarea» | La campaña confirmatoria de v2.1 muestra que C **no** supera a un baseline con herramientas tipadas en éxito de tarea (*p*=0,286) |
| «Ahorra X € al año» | H8 es **análisis de sensibilidad con tarifa declarada**, no gasto observado — los proveedores usados son gratuitos |
| «Más estable entre ejecuciones» sin matiz | Bajo repetición estocástica pura y temperatura baja, sí sale trivial (H3b). Lo que sí es confirmatorio es la estabilidad **entre formulaciones distintas** de la misma petición (H3a) |

**Consecuencia de diseño, no solo de marketing:** el producto no puede
apoyarse en que el sistema *entienda* mejor. Debe apoyarse en que
*restrinja* mejor. Eso cambia qué se construye.

---

## 3. El producto que la evidencia sostiene

### Un plano de control entre el agente y el ERP. No un agente.

El cliente trae el agente que quiera —Claude, ChatGPT, n8n, uno propio—
y esta capa es **la única vía** por la que ese agente puede tocar el
ERP. No se compite con la calidad del modelo; se opera por debajo de
todos ellos.

El argumento de venta es literalmente el brazo experimental más fuerte:

> Suponga que su agente está completamente comprometido y el atacante
> dicta los argumentos. En **510 de 510** intentos, no escribió nada.

**Y el matiz que hay que dar en la misma frase, no en la letra
pequeña:** ese resultado es sobre ataques explícitos. Sobre una petición
simplemente ambigua y plausible —sin que nadie esté atacando nada—, la
capa deja pasar una de cada cinco. El producto vendible hoy es «confina
incluso lo peor», no «detecta lo peligroso» — son cosas distintas, y
conviene que lo sepa el cliente antes que su auditor de seguridad.

### Componentes, todos ya existentes en el prototipo

| Pieza | Estado hoy |
|---|---|
| Operaciones expuestas **solo** como skills con contrato (esquema, rol, riesgo, precondiciones, postcondiciones, idempotencia) | `catalog.py`, `skills.py`, `policy.py`, `runtime.py` |
| Bandeja de aprobación con actor, alcance y expiración | `approval.py` (lógica); **falta la UI** |
| Auditoría append-only exportable | `audit.py`, `persistence.py` |
| Modo simulación y vista previa de la mutación | `PolicyDecision.SIMULATE`, `runtime.preview_mutation` |
| Adaptador ERP real con allowlist de modelos y campos, sin borrado | `odoo_client.py` |

### Por qué vertical Odoo y no genérico

En vertical, **el coste del catálogo de skills deja de ser un lastre y
pasa a ser el foso**: cada skill mapeada es trabajo que un competidor
genérico no ha hecho, y es facturable como implantación. Además ya
existe el canal (instancia Odoo real, partner integrador) y las demos
corren contra Odoo 19 de verdad.

**Modelo sugerido: open-core.** Núcleo de gobernanza abierto —nadie
confía en un cortafuegos cerrado, y la auditabilidad *es* el producto—;
bandeja de aprobación, conectores y multi-tenant de pago.

### Alternativa considerada y descartada

La misma capa como *gate genérico para herramientas MCP*, sin ERP:
mercado mayor y mucho menos trabajo de mapeo, pero menos defendible y
con competencia. Se descarta porque el foso está justo en el trabajo
aburrido ya empezado, que un genérico no hará.

---

## 4. Lo que falta construir, sin adornos

| Hueco | Esfuerzo | Nota |
|---|---|---|
| **Cerrar la brecha de H4 en las 5 categorías que fallan** | **Alto, y previo a vender seguridad** | Sin esto, cualquier afirmación de seguridad activa (no solo confinamiento) es falsa. `duplication_or_retry` y `field_conflict` ni siquiera tienen su condición de peligro bien construida en el benchmark — hay que diseñarla antes de poder medir si se arregló |
| Autoría de skills sin escribir Python | **Alto** | Es el producto real. Hoy solo existe `skill_proposal.py`, en sandbox y con aprobación humana |
| 10 de 12 skills sin mapear a modelos reales de Odoo | Medio | Repetitivo e ineludible; es el coste que hay que medir (§5) |
| Multi-tenant, autenticación real, `SqlAuditStore` cableado a la API | Medio | Hoy la API usa clave de demo y almacén en memoria |
| UX de aprobación y de aclaración | **Alto** | **9,3 %** de peticiones abstienen y rebotan a un humano; esa cifra decide la adopción |
| Auditoría a prueba de manipulación (hash encadenado) | Bajo | Hoy es append-only **por superficie pública**, no criptográficamente. Sube mucho el valor si se vende cumplimiento |
| ~~Reevaluar recuperación con texto real~~ | **Hecho** | Medido en §7.2–7.4: TF-IDF se derrumbó (0,733 → 0,381) y la causa resultó ser las descripciones de una línea, no la técnica. Sustituido por un hueco nuevo: **el alta de skill debe pedir sinónimos y ejemplos reales**, no una frase — deja de ser un fichero suelto y pasa a ser un campo del contrato |

---

## 5. Los tres números que decidirían la apuesta

1. **Coste de añadir una skill nueva** con el cliente delante. Horas → el
   modelo de negocio cierra; días → no.
2. **Tiempo humano en resolver una abstención.** 30 segundos es un
   producto; 10 minutos es un juguete. Ninguna de las dos cosas se ha
   medido: `docs/spec-coverage.md` declara el tiempo de revisión humana
   fuera de alcance por §11.
3. ~~**Top-1 de recuperación con peticiones reales**, no plantilladas.~~
   **MEDIDO** (§7.2–7.4): el diseño actual da 0,455 en held-out; con
   descripciones enriquecidas, 0,886 a coste cero de tokens. La
   respuesta es «sirve, pero no con las descripciones del catálogo».

Los números 1 y 2 siguen sin medir: son trabajo de validación de
producto, no de investigación, y se declaran como tales. El 3 está
respondido y su respuesta cambió el diseño propuesto.

---

## 6. La conclusión transferible, en una frase

> El trabajo no demuestra que un agente gobernado haga mejor la tarea, ni
> que detecte mejor el peligro. Demuestra que **confina** incluso cuando
> el modelo falla o está comprometido del todo, con una llamada al LLM
> menos por petición y con una traza que permite reconstruir cada
> decisión — y demuestra, con la misma campaña, que ese confinamiento no
> sustituye a un buen juicio sobre lo ambiguo. Eso —confinamiento medido,
> no detección prometida— es lo que sostiene un producto.

---

## 7. Arnés para medir el número 3, ya construido

`scripts/eval_real_requests.py` evalúa los tres recuperadores sobre un
CSV de peticiones **reales** y compara el resultado con la referencia
del benchmark (Top-1 en validación: TF-IDF 0,733 · embeddings 0,658 ·
híbrido 0,675). Reutiliza **el mismo código de métricas** que
`compare_retrievers.py`, no una copia — una segunda implementación
derivaría y los dos números dejarían de ser comparables, que es
justamente lo que se quiere medir.

```sh
cp data/real_requests.template.csv data/real_requests.csv
# rellenar con peticiones reales, verbatim
uv run python scripts/eval_real_requests.py
```

Tres decisiones de diseño que existen para que el número no mienta:

- **Un id de skill mal escrito aborta el script**, en vez de contar como
  fallo de recuperación y deprimir la puntuación en silencio.
- **Avisa explícitamente por debajo de 30 peticiones**: con menos, el
  intervalo es tan ancho que la respuesta honesta es «aún no se sabe».
- **`data/real_requests.csv` está gitignorado**: puede contener nombres
  de clientes, teléfonos e importes. La salida agregada
  (`data/real_requests_eval.json`) no contiene texto de peticiones y sí
  es publicable.

### Qué NO sirve como fuente de peticiones

Se descartó explícitamente usar el historial local de conversaciones con
un asistente de IA. Dos motivos, y el segundo es el que importa:

1. Contiene credenciales, datos financieros y conversaciones ajenas al
   proyecto.
2. **No es la población que se quiere medir.** Son instrucciones de
   programación dirigidas a un asistente técnico, no peticiones ERP
   escritas por personal de operaciones. Medir sobre esa muestra daría
   un número real, reproducible y **sin ningún significado** — la misma
   familia de error que este proyecto lleva dieciocho defectos corrigiendo:
   una medición que no puede fallar porque no mide lo que dice medir.

La fuente válida es la aburrida: pedir a 5–10 personas que escriban cómo
pedirían de verdad las cosas que hacen a diario, o recoger peticiones de
un canal real (correo, chat interno, partes de trabajo).

### 7.1 Cómo debe ser el CSV, y cómo recogerlo

**Formato.** UTF-8, cabecera obligatoria, una petición por fila:

```csv
request_text,expected_skill,notas
"apunta que los de Marisqueria El Puerto quieren algo para el catering de navidad, unos 4 mil",crm.create_opportunity,"comercial, whatsapp"
"mira si queda stock del difusor de bambu",inventory.check_availability,"tienda"
"cambiale el precio al ambientador de lavanda a 12,90",product.update_field,"tienda"
"pon 3 unidades mas en el presupuesto de Hotel Miramar",sales.add_quote_line,"oficina"
"cuando cobramos la factura de El Corte Ingles?",,"ninguna skill cubre cobros"
```

- `request_text` — **verbatim**. Con faltas, abreviaturas, sin acentos,
  a medias. Si la limpias, mides otra cosa.
- `expected_skill` — uno de los 12 ids de abajo, o **vacío** si ninguna
  encaja. Las filas vacías no son descartes: miden si el sistema se
  abstiene cuando debe.
- `notas` — libre, el script la ignora. Útil para saber de dónde salió
  cada fila.
- Comillas dobles si el texto lleva comas. Guardar como CSV UTF-8, no
  como XLSX.

**Los 12 ids del catálogo** (para anotar `expected_skill`):

| id | qué hace |
|---|---|
| `crm.create_opportunity` | Crea una oportunidad comercial |
| `crm.update_expected_revenue` | Cambia el importe esperado de una oportunidad |
| `crm.detect_duplicate_contact` | Detecta contactos duplicados |
| `contacts.search_contact` | Busca un contacto por nombre, email o teléfono |
| `sales.create_quote_draft` | Crea un presupuesto en borrador |
| `sales.add_quote_line` | Añade línea de producto/cantidad a un presupuesto |
| `sales.confirm_order` | Confirma un pedido de venta |
| `purchasing.create_purchase_draft` | Crea un pedido de compra en borrador |
| `product.update_field` | Cambia precio o descripción de un producto |
| `inventory.check_availability` | Consulta stock de un producto |
| `tasks.create_task` | Crea una tarea interna |
| `billing.create_draft_invoice` | Crea una factura en borrador |

**Cuántas.** El script avisa por debajo de 30. Objetivo **100–200**: con
120 peticiones, un Top-1 de 0,70 lleva un IC95 de aproximadamente
±0,08, suficiente para distinguir «aguanta» de «se derrumba».

**Composición.** Que se parezca a la realidad, no a un examen fácil:

- **~70 %** peticiones que alguna de las 12 skills sí cubre;
- **~30 %** que ninguna cubre (`expected_skill` vacío) — cobros,
  devoluciones, nóminas, informes, cualquier cosa fuera del catálogo.
  Sin estas filas no se puede medir el riesgo de reutilización errónea,
  que es el fallo que de verdad hace daño en producción.

**La regla que decide si la medición vale:**

> **Quien escribe las peticiones NO debe haber visto el catálogo.**

Si la persona conoce las 12 skills, formulará hacia ellas sin darse
cuenta y el Top-1 saldrá inflado — se estaría remidiendo el sesgo de
plantilla que este experimento existe para detectar. La consigna a dar
es genérica: *«imagina que puedes pedirle cosas del ERP escribiendo un
mensaje: escribe 15 que pedirías en una semana normal, tal como las
dirías»*. La anotación de `expected_skill` la hace después alguien que
sí conoce el catálogo.

**Fuentes válidas**, por orden de calidad: peticiones ya existentes en
un canal real (correo interno, WhatsApp de trabajo, partes, tickets) >
5–10 personas escribiendo 15 cada una a ciegas > una sola persona
inventando 100, que es la peor y la más tentadora.

### 7.2 Resultado medido: la recuperación NO sobrevive al texto real

120 peticiones en registro coloquial (84 cubiertas por el catálogo, 36
fuera de él), evaluadas con la regla de abstención del pipeline
gobernado (umbral 0,15, margen 0,05).

**Sobre las 84 contestables** — directamente comparable con el
benchmark, misma métrica y mismo código:

| Recuperador | Top-1 real | IC95 | Benchmark (validación) | Caída |
|---|---|---|---|---|
| **TF-IDF** | **0,381** | [0,284, 0,488] | 0,733 | **−0,352** |
| Embeddings | 0,381 | [0,284, 0,488] | 0,658 | −0,277 |
| Híbrido | 0,274 | [0,190, 0,377] | 0,675 | −0,401 |

**Sobre las 36 fuera de catálogo** — donde lo correcto es abstenerse
siempre:

| Recuperador | Se abstiene bien | Exactitud selectiva |
|---|---|---|
| TF-IDF | **0,389** | 0,542 |
| Embeddings | 0,556 | 0,681 |
| Híbrido | **0,750** | 0,742 |

### Qué significa esto, sin suavizar

**1. El resultado de `docs/retriever-comparison.md` era un artefacto del
corpus plantillado.** TF-IDF ganaba porque la petición y la descripción
de la skill compartían vocabulario. Con texto real esa ventaja
desaparece: empata con embeddings y **pierde claramente en las dos
métricas que importan en producción** —saber cuándo callarse y acertar
cuando habla—. En texto real, TF-IDF se lanza a elegir una skill en el
**61 %** de las peticiones que ninguna skill cubre.

**2. El orden se invierte.** Por exactitud selectiva y por abstención
correcta: **híbrido > embeddings > TF-IDF**, exactamente al revés que en
el benchmark. El híbrido acierta el 74 % de las veces que se
compromete... pero solo se compromete en el 37 % de los casos: dos de
cada tres peticiones reales rebotarían a un humano.

**3. Ninguna de las tres configuraciones actuales es utilizable en
producto tal cual.** Con la mejor combinación disponible hoy, la mayoría
de las peticiones reales acaban en skill equivocada o en abstención.

**4. La muestra es optimista, y aun así se derrumba.** El fichero tiene
exactamente 7 peticiones por skill, lo que revela que quien las escribió
**tenía el catálogo delante** — el sesgo que §7.1 advierte que infla el
resultado. Que colapse *pese a* ese sesgo hace el hallazgo más fuerte,
no más débil. Con peticiones recogidas a ciegas de tráfico real cabe
esperar algo igual o peor.

### Qué NO significa

No invalida el TFM. Las conclusiones del trabajo son sobre **gobernanza
frente a ausencia de gobernanza** en su propio benchmark, y la limitación
del corpus plantillado ya estaba declarada en §36 y en
`docs/retriever-comparison.md`. Esto la **confirma empíricamente**, que
es distinto de contradecirla. Las propiedades que sostienen el producto
—resistencia a inyección, una llamada al LLM menos, invariancia al
proveedor, trazabilidad— no dependen del recuperador.

### Consecuencia para el producto

La recuperación por similitud léxica sobre descripciones de skill **no
es el diseño correcto** para texto real. Antes de construir producto hay
que resolver el enrutado, y las opciones razonables son: clasificación
de intención entrenada sobre peticiones reales, recuperación con
descripciones enriquecidas (sinónimos, ejemplos de uso reales por skill),
o delegar la selección al LLM —que es justo lo que hace el sistema B, con
Top-1 de 0,898 en el benchmark— asumiendo el coste en tokens que la tesis
ahorraba. **Ese trade-off ahora es medible y hay que medirlo antes de
elegir.**

### 7.3 La pregunta que quedaba: ¿es TF-IDF o es el catálogo?

Si el selector LLM también se derrumbaba con texto real, el problema
sería el catálogo de 12 skills y la comparación C vs B del TFM se
mantendría intacta. Si aguantaba, el problema es TF-IDF y hay que decir
que la ventaja de C sobre B **no transfiere**.

Se midió: el mismo `TYPED_TOOLS` y el mismo prompt que usa el sistema B
en el experimento emparejado, sobre las mismas 120 peticiones, con Groq
real (`data/real_requests_llm_eval.json`).

| | TF-IDF | Selector LLM |
|---|---|---|
| Top-1 (84 contestables) | 0,381 | **0,750** [0,648, 0,830] |
| Caída respecto a su propio benchmark | −0,352 (0,733) | **−0,148** (0,898) |
| Rechaza bien lo que no cubre (36 casos) | **0,389** | 0,167 |
| Compromiso erróneo fuera de catálogo | 22/36 = 0,611 | **30/36 = 0,833** |
| Global (acierto + silencio correcto), 120 | 46/120 = 0,383 | **69/120 = 0,575** |

**Respuesta: es TF-IDF.** El selector LLM pierde 15 puntos con texto
real; TF-IDF pierde 35. No es que las peticiones reales sean
intrínsecamente difíciles: es que la similitud léxica sobre
descripciones de skill deja de funcionar cuando el usuario no habla como
el catálogo.

### Pero el LLM gana enrutando y pierde callándose

En las 36 peticiones que **ninguna** skill cubre, el LLM inventa una
herramienta en **30**. Enruta «cuándo cobramos la factura de El Corte
Inglés» a `billing.create_draft_invoice` (9 veces elige esa),
«dame de baja al usuario de pedro» a `contacts.search_contact` (8 veces
esa). TF-IDF también falla ahí, pero menos (22 de 36).

En un ERP esa es **la dirección peligrosa del error**: no enrutar mal
entre dos skills parecidas, sino ejecutar algo cuando la respuesta
correcta era «esto no lo hago yo».

### Lo que esto implica para el producto, y no es lo que parecía

La conclusión no es «cambia TF-IDF por el LLM y listo». Es que **cada
componente falla en un eje distinto y ninguno de los dos es aceptable
solo**:

- el LLM enruta casi el doble de bien, pero se calla cinco veces menos;
- TF-IDF se calla más, pero se equivoca al enrutar el 62 % de las veces.

El diseño que la evidencia sugiere es **combinarlos**: selector LLM para
enrutar, más una comprobación independiente de que la petición
**pertenece al dominio** antes de dejarle elegir. Y sobre todo: con un
router LLM que se compromete en el 83 % de lo que no cubre, **la capa de
gobernanza pasa a importar más, no menos** — es lo único que queda entre
un enrutado inventado y una escritura en el ERP. La validación de
esquema, los permisos por rol y las postcondiciones no dependen del
router y siguen intactas.

### 7.4 Los tres siguientes pasos, medidos: no era TF-IDF, eran las descripciones

Los tres pendientes de §7.3 son el mismo experimento, así que se
ejecutaron juntos (`scripts/eval_router_designs.py`).

**Disciplina.** Las 120 peticiones se parten 50/50 por sha256 del texto.
Los perfiles enriquecidos se escribieron leyendo **solo la mitad dev**;
el umbral del filtro de dominio se barrió **solo en dev**. Todo lo que
se reporta para decidir es **held-out**. El catálogo congelado no se
toca: el enriquecimiento vive en `data/skill_profiles.json`, usado solo
aquí.

**Held-out (60 peticiones: 44 contestables, 16 fuera de catálogo):**

| Diseño | Top-1 (IC95) | Rechaza bien (IC95) | Global | Tokens |
|---|---|---|---|---|
| D1 TF-IDF catálogo (C actual) | 0,455 [0,317, 0,599] | 0,062 [0,011, 0,283] | 0,350 | **0** |
| D2 TF-IDF **enriquecido** | **0,886** [0,760, 0,950] | 0,000 [0,000, 0,194] | 0,650 | **0** |
| D3 router LLM (B actual) | 0,818 [0,680, 0,905] | 0,250 [0,102, 0,495] | 0,667 | 592 |
| D4 filtro dominio + router LLM | 0,795 [0,655, 0,888] | **0,375** [0,185, 0,614] | 0,683 | 592 |
| D5 filtro dominio + TF-IDF enriq. | 0,864 [0,733, 0,936] | 0,250 [0,102, 0,495] | **0,700** | **0** |

**1. El diagnóstico anterior era incompleto.** §7.3 concluyó «es TF-IDF».
Con más precisión: **no era la técnica, eran las descripciones de una
línea del catálogo**. Enriquecerlas con sinónimos y formas reales de
decir lo mismo lleva a TF-IDF de 0,455 a **0,886** en held-out — por
encima del router LLM (0,818) — **sin gastar un solo token**.

**2. El filtro de dominio funciona, y hace falta.** El enriquecimiento
tiene un efecto secundario: al hacer que todo se parezca a algo, D2 deja
de abstenerse por completo (0,000). Anteponer un umbral calibrado en dev
(0,22) recupera la abstención (0,250) a cambio de 2 puntos de Top-1, y
da el mejor resultado global de los cinco. Para el router LLM sube el
rechazo correcto de 0,250 a 0,375.

**3. El coste de sustituir el router está medido: 592 tokens por
petición.** Y hay una comprobación independiente que salió sola: el
experimento congelado da 197,6 tokens/ejecución para la llamada de
selección de B, y con 3 repeticiones cacheadas por caso eso implica
197,6 × 3 = **592,8** tokens por llamada real. La medición directa sobre
texto real da **591,7**. Dos vías independientes, 0,2 % de diferencia.

**La conclusión de producto se invierte respecto a §7.3:** no hay que
elegir entre enrutar bien y ahorrar tokens. Escribir descripciones
decentes —trabajo humano, una vez por skill— da enrutado igual o mejor
que el LLM a coste cero, y **preserva la ventaja arquitectónica de una
llamada menos** en vez de devolverla.

### Lo que estos números NO permiten afirmar

- **Los intervalos se solapan.** D2 (0,886), D5 (0,864) y D3 (0,818) no
  son distinguibles con n = 44 contestables. Lo que sí es una diferencia
  dura y no estadística: D2 y D5 cuestan **0 tokens** y D3 cuesta 592.
- **El held-out no es independiente de verdad.** Las 120 peticiones las
  escribió una sola persona en una sesión, con el catálogo delante. Que
  el enriquecimiento generalice de una mitad a la otra dice que
  generaliza **dentro del estilo de ese autor**, no que vaya a funcionar
  con usuarios distintos. La prueba que falta es enriquecer con las
  peticiones de unas personas y evaluar con las de otras.
- **El umbral 0,22 está calibrado sobre 60 peticiones.** Es un punto de
  partida, no un valor de producción.
- **Nada de esto toca el experimento congelado del TFM**, que sigue
  midiendo lo que decía medir con las descripciones originales.

### 7.5 ¿Generaliza el enriquecimiento a autores que nunca vieron el catálogo?

§7.4 llevaba un caveat que ningún reanálisis podía quitar: **las 120
peticiones las escribió una sola persona, en una sesión, con el catálogo
delante**. El enriquecimiento solo estaba demostrado *dentro del estilo
de ese autor*.

Se cierra tomando prestado un corpus que tiene lo que al nuestro le
falta: muchos autores, identificados. **MASSIVE** (Amazon, 2022,
CC-BY-4.0), partición española `es-ES`: 16.521 frases, 60 intenciones,
**20 crowdworkers identificados**. El diseño replica el montaje ERP:

- **catálogo**: las 10 intenciones de los escenarios calendar / email /
  lists, como sustituto de un catálogo de negocio pequeño;
- **fuera de catálogo**: las otras 50, donde lo correcto es «esto no lo
  hago yo»;
- **autores partidos en dos mitades disjuntas**: el enriquecimiento se
  construye solo con frases de los autores dev, y **todo lo reportado
  procede de autores held-out**. Ninguna persona aparece en los dos
  lados.

El enriquecimiento se construye **mecánicamente** —añadir *k* frases de
ejemplo reales a la descripción— en vez de a mano. Eso quita el juicio
del autor del resultado y responde a la pregunta de producto: **¿cuántos
ejemplos por skill hacen falta?**

**Resultado (autores held-out: 2.493 frases del catálogo, 1.500 fuera):**

| k ejemplos | Enrutado sin puerta | Umbral (calibrado en dev) | Top-1 con puerta | Rechaza bien | Global |
|---|---|---|---|---|---|
| 0 (descripción fina) | **0,365** | 0,55 | 0,176 | 0,897 | 0,447 |
| 1 | 0,426 | 0,53 | 0,169 | 0,976 | 0,472 |
| 3 | 0,525 | 0,43 | 0,293 | 0,947 | 0,539 |
| 5 | 0,591 | 0,38 | 0,354 | 0,885 | 0,553 |
| 10 | **0,634** | 0,36 | 0,402 | 0,861 | 0,575 |
| 20 | 0,629 | 0,32 | 0,428 | 0,842 | **0,583** |

**1. El efecto generaliza entre autores disjuntos.** La precisión de
enrutado sube de 0,365 a **0,634** (+0,269, un 74 % relativo) sin que
ninguna de las personas cuyas frases se evalúan haya aportado un solo
ejemplo. El hallazgo de §7.4 no era un artefacto de tener un único
autor.

**2. Saturación en torno a 10 ejemplos por skill.** k=10 da 0,634 y
k=20 da 0,629 — dentro del ruido. Es la respuesta operativa a «cuánto
hay que recoger»: **unas diez formulaciones reales por skill**, no
cientos. Eso convierte el enriquecimiento en una tarea de horas, no de
semanas.

**3. Detalle accionable que solo aparece al calibrar honestamente:** el
umbral óptimo **baja** al enriquecer (0,55 → 0,32), porque las
descripciones más ricas suben la puntuación de todo. Un umbral fijo
—como el 0,15 del pipeline actual— quedaría mal puesto en cuanto se
cambien las descripciones. **La puerta hay que recalibrarla cada vez que
cambia el catálogo**, y eso debe ser parte del flujo de alta de skill,
no una constante en el código.

### Lo que este experimento NO demuestra

- **No es dominio ERP.** Calendario, correo y listas. Prueba el
  **mecanismo** (descripción fina → enrutado pobre; ejemplos reales →
  mejor), no el producto.
- **Los niveles absolutos son bajos** (0,634 de enrutado): frases muy
  cortas y ambiguas, y 50 intenciones fuera de catálogo compitiendo. No
  son cifras utilizables en producción, y no se presentan como tales:
  lo que se mide es el **delta**.
- **El enriquecimiento aquí es mecánico** (pegar frases de ejemplo) y en
  §7.4 era manual (sinónimos escritos). Son dos operacionalizaciones
  distintas de la misma idea; coinciden en dirección, no son
  comparables en magnitud.
