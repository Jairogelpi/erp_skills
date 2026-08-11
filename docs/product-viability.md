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
