# De los resultados a un producto: qué sostiene la evidencia y qué no

Documento de **transferencia**, no de investigación. Traduce los
resultados medidos (`docs/results.md`) a qué se puede afirmar ante un
cliente, qué producto sostienen y qué falta construir.

Regla que gobierna todo lo que sigue: **cada afirmación comercial debe
apuntar a un número reproducible de este repositorio**. Lo que no
cumpla eso, no se dice.

---

## 1. Evidencia que aguanta un cliente

| Afirmación | Número que la sostiene | Dónde |
|---|---|---|
| **Aunque el modelo esté comprometido, no puede escribir fuera de contrato** | **0 / 1.530** mutaciones no autorizadas, con 510 payloads externos por tres canales, incluido un brazo que **concede el LLM entero al atacante** (510/510 `DENY`) | `docs/injecagent-stress-test.md`, `data/injection_resistance_results.json` |
| **Una llamada al LLM menos por petición** | 67,6 tokens/ejecución frente a 265,3 del baseline tipado; el incremento por parsear es +67,68/+67,67/+67,62 en A/B/C, luego el gasto **total** de C *es* la extracción y nada más | `docs/results.md` § Ejecución 5 |
| **La decisión no depende del modelo** | *False allow* de C = 0,111 con los tres proveedores probados; el de A oscila 0,333 ↔ 0,889 según proveedor | `docs/results.md` § Ejecución 5 |
| **El bloqueo funciona contra un ERP real, no solo en simulador** | Escritura R2 sin aprobación bloqueada contra Odoo 19, verificada por **relectura independiente**; tras conceder aprobación, la misma petición escribe | `docs/odoo-demo.md`, `data/odoo_governed_demo_results.json` |
| **Cada acción queda reconstruible** | Rúbrica de trazabilidad 0,820 frente a 0,356 / 0,374 | `docs/results.md` § H7 |

## 2. Evidencia que NO aguanta, y que por tanto no se usa

| Lo que sería tentador decir | Por qué no se dice |
|---|---|
| «Detectamos ataques de inyección de prompts» | **3,3 %** de detección fuera de distribución. Y en el test propio, **8 de 9** casos peligrosos los bloquea un patrón léxico escrito mirando ese mismo corpus. Es detección dentro de distribución, no una capacidad general |
| «8× más seguro» a secas | **n = 9** casos peligrosos. IC de Wilson para C: [0,020, **0,435**]. Es una estimación puntual, no una medición precisa |
| «+15 pp de éxito de tarea» | Efecto modesto sobre un baseline concreto, n = 120 unidades de inferencia. Verdadero, pero no es el argumento |
| «Ahorra X € al año» | H8 es **análisis de sensibilidad con tarifa declarada**, no gasto observado — los proveedores usados son gratuitos |
| «Más estable entre ejecuciones» | H3 sale 1,000 en los tres sistemas porque la temperatura 0 los hace deterministas. No discrimina nada |

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
| Autoría de skills sin escribir Python | **Alto** | Es el producto real. Hoy solo existe `skill_proposal.py`, en sandbox y con aprobación humana |
| 10 de 12 skills sin mapear a modelos reales de Odoo | Medio | Repetitivo e ineludible; es el coste que hay que medir (§5) |
| Multi-tenant, autenticación real, `SqlAuditStore` cableado a la API | Medio | Hoy la API usa clave de demo y almacén en memoria |
| UX de aprobación y de aclaración | **Alto** | **9,3 %** de peticiones abstienen y rebotan a un humano; esa cifra decide la adopción |
| Auditoría a prueba de manipulación (hash encadenado) | Bajo | Hoy es append-only **por superficie pública**, no criptográficamente. Sube mucho el valor si se vende cumplimiento |
| Reevaluar recuperación con texto real | Bajo | **Hacer antes de prometer nada**: TF-IDF ganó sobre texto plantillado (`docs/retriever-comparison.md`) y ahí puede derrumbarse |

---

## 5. Los tres números que decidirían la apuesta

1. **Coste de añadir una skill nueva** con el cliente delante. Horas → el
   modelo de negocio cierra; días → no.
2. **Tiempo humano en resolver una abstención.** 30 segundos es un
   producto; 10 minutos es un juguete. Ninguna de las dos cosas se ha
   medido: `docs/spec-coverage.md` declara el tiempo de revisión humana
   fuera de alcance por §11.
3. **Top-1 de recuperación con peticiones reales**, no plantilladas.

Ninguno de los tres está medido en este TFM. Son trabajo de validación
de producto, no de investigación, y se declaran como tales.

---

## 6. La conclusión transferible, en una frase

> El trabajo no demuestra que un agente gobernado haga mejor la tarea.
> Demuestra que hace **la misma** tarea sin poder salirse del contrato
> aunque el modelo falle o esté comprometido, con una llamada al LLM
> menos por petición y con una traza que permite reconstruir cada
> decisión. Eso —y no el éxito de tarea— es lo que sostiene un producto.

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
   familia de error que este proyecto lleva catorce defectos corrigiendo:
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
