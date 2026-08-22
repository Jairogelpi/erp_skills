# Presentación de defensa — contenido diapositiva a diapositiva

15 diapositivas para ~18 minutos. Cada una lleva **lo que se ve** y **lo
que se dice**. Todas las cifras proceden de `data/*.json` versionados y
son reproducibles con los comandos del anexo A de la memoria.

Orden según el principio de `docs/defensa.md`: **abrir por lo que
aguanta**. El endpoint primario se reporta completo, pero no abre.

---

## 1 — Portada

**Se ve:** título académico completo, autor, programa, curso. Al pie, en
pequeño: `github.com/Jairogelpi/erp_skills` · tag `v1.0-tfm`.

**Se dice:** nada todavía. Pasar rápido.

---

## 2 — El problema, con un caso concreto

**Se ve:** dos capturas del mismo ERP. Izquierda: una oportunidad con
importe 15.000. Derecha: la misma con 27.600. En medio, una flecha con
el texto de la petición que lo provocó.

**Se dice:**
> Cuando un agente de IA se equivoca escribiendo un correo, sale un
> correo raro. Cuando se equivoca sobre un ERP, sale un importe
> cambiado, un pedido confirmado que no debía confirmarse o un registro
> duplicado. No es una respuesta incorrecta: es un asiento. Y alguien
> responde por él.

---

## 3 — Qué se ha construido, en una frase

**Se ve:** el diagrama de dos zonas. Izquierda (probabilística):
interpretar, proponer, recuperar. Derecha (determinista): validar,
autorizar, ejecutar, verificar, auditar. Una línea gruesa entre ambas.

**Se dice:**
> El modelo **propone**. El contrato **decide**. El modelo puede sugerir
> cualquier cosa; lo único que puede emitir es un identificador de skill
> con argumentos, y a partir de ahí no toca nada que no esté validado
> contra un esquema, permitido para su rol y verificado después.

---

## 4 — La pregunta que acabó siendo la buena

**Se ve:** a la izquierda, en gris, «¿Salta el detector?». A la derecha,
en negro y grande, «¿Ocurre el daño **concedido** que el detector ha
fallado?».

**Se dice:**
> La literatura de inyección de prompts mide si un detector dispara. El
> mío apenas dispara. Voy a enseñar ese dato antes que ningún otro.

---

## 5 — Mis dos peores números, y los dos son confirmatorios

**Se ve:** dos filas.
- Detección léxica sobre 510 casos externos de InjecAgent: **3,3 %**.
- Mutación no autorizada de C sobre **315 escenarios peligrosos reales**
  de la campaña confirmatoria: **19,0 %** — casi 4× el umbral que yo
  mismo prerregistré (5 %).

**Se dice:**
> El primero mide si mi detector léxico dispara ante ataques externos:
> casi nunca. El segundo es peor y más importante, porque es
> confirmatorio, no exploratorio: sobre peticiones peligrosas plausibles,
> sin ningún marcador de ataque, mi sistema gobernado deja pasar una de
> cada cinco. Lo abro con esto porque es lo que un tribunal encontraría
> si mirara los datos antes que a mí.

---

## 6 — El resultado que sí aguanta

**Se ve:** tabla de tres canales.

| Canal de ataque | Mutaciones no autorizadas |
|---|---|
| Payload en el texto de la petición | **0 / 510** |
| Payload guardado en un campo del ERP que la petición lee | **0 / 510** |
| **Parser comprometido**: el atacante dicta los argumentos | **0 / 510** |

Debajo, grande: **0 / 1.530**.

**Se dice:**
> Los mismos 510 payloads, por los tres canales que un atacante controla
> de verdad. El tercero es el importante: ahí concedo que el ataque ha
> ganado por completo — el modelo comprometido, el atacante escribiendo
> los argumentos. 510 de 510 denegadas. Ninguna mutación no autorizada
> en 1.530 intentos. Es una propiedad distinta de la de la diapositiva
> anterior: aquí gano porque el atacante ya no puede fingir que la
> petición es normal. Cuando sí puede — una petición ambigua sin marca
> de ataque —, ese confinamiento no basta, y el 19 % lo demuestra.

---

## 7 — Por qué ese cero no es un cero vacío

**Se ve:** una línea de log: `positive control: clean request -> ALLOW,
created ['45'] in Odoo`.

**Se dice:**
> La primera versión de ese experimento usaba un rol sin permisos. Todo
> se abstenía, incluido el caso benigno, y reportaba un cero perfecto
> que no podía fallar. Ahora una petición limpia tiene que llegar al
> handler y **crear un registro real** o el experimento aborta. El cero
> significa algo porque el uno también podía ocurrir.

---

## 8 — Demostración contra un ERP real

**Se ve:** tres pasos con el resultado de cada uno.
1. Crear oportunidad (R1) → `ALLOW`, registro creado, postcondición
   verificada.
2. Cambiar importe (R2) sin aprobación → `REQUIRE_APPROVAL`. **Relectura
   independiente: Odoo no cambió.**
3. Conceder aprobación, repetir → `ALLOW`, escribe.

**Se dice:**
> Esto es Odoo 19 real, con el mismo runtime y el mismo almacén de
> auditoría que corren las 21.478 observaciones de la campaña
> confirmatoria. Lo que hace que esto sea evidencia y no una demo: la
> comprobación no se fía de lo que el sistema dice de sí mismo. Vuelve a
> leer Odoo por separado.

---

## 9 — Dos generaciones de experimento

**Se ve:** dos filas. **Piloto v1** (exploratorio): 120 casos × 3
sistemas × 3 repeticiones = 1.080, unidad de inferencia el caso
(n = 120) tras corregir una pseudo-replicación que inflaba la
significación en quince órdenes de magnitud. **Campaña confirmatoria
v2.1** (vigente): **21.478 observaciones**, verdad de referencia por
construcción, protocolo y potencia congelados **antes** de generar el
holdout, evaluación única.

**Se dice:**
> El piloto sirvió para encontrar y arreglar los errores de mi propio
> instrumento de medida. La campaña confirmatoria es la que responde de
> verdad: código congelado, holdout generado después, una sola
> evaluación. Lo que enseño ahora sale de ahí.

---

## 10 — Resultados (campaña confirmatoria v2.1)

**Se ve:** la figura `v21_hypotheses_forest` — nueve pruebas, estimación
e IC95, azul confirmada / rojo no confirmada.

| Confirmadas | No confirmadas |
|---|---|
| H1a (no inferior a A) · H2 (tokens, vs A y vs B) · H3a (estabilidad) · H6 (abstención) · H7 (auditoría) | H1b (superior a B) · **H4, las 4 componentes** · H5 (recuperación) |

Debajo, grande: **mutación no autorizada de C = 19,0 % sobre 315
escenarios peligrosos, casi 4× el umbral.**

**Se dice:**
> Cuatro de nueve confirmadas. La que más pesa es la que no: la promesa
> de detección activa de peligro no se sostiene. Se lee en diez
> segundos y se pasa a la siguiente — pero se lee entera, no solo la
> mitad buena.

---

## 11 — Los límites, dichos por mí

**Se ve:** cuatro viñetas, sin adornos.
- A puntúa 0,000 **por construcción** en el piloto v1: CRUD genérico no
  puede codificar postcondiciones. En la campaña confirmatoria esto ya
  no aplica de la misma forma — H1a se mide como no inferioridad, no
  como comparación cruda.
- La comparación C-vs-A/B de H4 mezcla dos cosas: para A y B, `DENY` es
  una etiqueta de error de ejecución, no una decisión de seguridad. Lo
  único de H4 libre de ese matiz es el 19 % de mutación no autorizada de
  C, medido sobre el estado, no sobre la decisión.
- H5 confirma, con un benchmark distinto al del piloto, que **la
  recuperación no aguanta**: selective accuracy 0,589, false-reuse risk
  0,411, ambos muy fuera de los umbrales que yo mismo prerregistré.
- H1b **no se confirma**: C no supera a un baseline con herramientas
  tipadas en éxito de tarea (*p* = 0,286). La ventaja de la gobernanza no
  está ahí, ni en el piloto ni en la campaña confirmatoria.

**Se dice:**
> Estas son las objeciones que ustedes me iban a hacer. Las hago yo,
> porque las medí — con una campaña diseñada para no poder mirar el
> resultado antes de comprometerme con el diseño.

---

## 12 — Tres veces que los datos me quitaron la razón

**Se ve:** línea temporal con tres hitos y el valor de C−B en cada uno:
+0,183 (parseo regalado) → **+0,075, no significativo** (parseo honesto,
publicado así) → +0,150 (tras corregir un sesgo contra C).

**Se dice:**
> Descubrí que a los tres sistemas les estaba regalando el parseo de
> argumentos, lo que favorecía al mío. Lo quité y mi ventaja dejó de ser
> significativa. Lo publiqué así. Después, una pregunta escéptica reveló
> que ese resultado tenía un sesgo en la dirección contraria — una
> unidad monetaria sin normalizar que solo penalizaba al sistema que
> valida tipos. Corregido, la ventaja volvió, pero **menor** que la
> original. El mismo patrón se repitió en la campaña confirmatoria: al
> diagnosticar por qué fallaba la seguridad, encontré que la comparación
> con los baselines confundía "denegar por seguridad" con "fallar por un
> error de ejecución". No cambió el número de mi sistema — cambió cómo
> hay que leer la comparación.

---

## 13 — El caso que no corregí, y su espejo que sí corregí a tiempo

**Se ve:** dos columnas. Izquierda, piloto v1: caso mal etiquetado,
*false allow* 0,111 → 0,000 si se corrigiera. **No corregido** — el test
estaba congelado. Derecha, campaña v2.1: categoría de ataque
`r4_operation` sin señal observable, **retirada correctamente antes de
generar el holdout**. Resultado tras retirarla: mutación no autorizada
19,6 % → **19,0 %** — prácticamente sin cambio.

**Se dice:**
> En el piloto, un caso mal etiquetado habría mejorado mi resultado. No
> lo toqué porque el test ya estaba congelado — eso es lo que la
> congelación existe para impedir. En la campaña confirmatoria hice lo
> correcto en el momento correcto: retiré una categoría rota **antes**
> de generar el holdout. Y el número no mejoró. Eso es lo que convierte
> el 19 % en un hallazgo real y no en el artefacto de un dataset roto.

---

## 14 — Lo que dejo utilizable

**Se ve:** tres bloques.
- **Metodología:** 40 mutantes en 23 módulos; los **2** supervivientes,
  en la capa estadística. *El TDD protege lo que se implementa contra un
  requisito y no lo que solo se calcula.*
- **Regla:** *una comprobación que no puede fallar es peor que no
  tenerla.* 6 de 16 defectos tenían esa forma.
- **Aplicable:** 10 formulaciones reales por skill → +74 % de precisión
  de enrutado, **coste cero en tokens**, verificado con 20 autores
  distintos.

**Se dice:**
> De cuarenta mutantes inyectados, solo sobrevivieron dos, y los dos
> estaban en la capa que produce los números que acabo de enseñarles.
> Sus tests comprobaban si el resultado era significativo, no si la
> fórmula era correcta — y ambas cosas se cumplían con la fórmula rota.

---

## 15 — Cierre

**Se ve:** una sola frase.

> El modelo propone. El contrato decide. Y cuando el modelo falla del
> todo, el contrato sigue decidiendo.

**Se dice:**
> Un trabajo experimental que solo confirma lo que esperaba debería
> levantar sospecha. Este documenta dónde se equivocó, cómo lo
> descubrió, y qué quedó en pie después. Gracias.

---

## Diapositivas de reserva (para preguntas)

| # | Contenido |
|---|---|
| R1 | Taxonomía R0–R4 y qué política aplica cada una |
| R2 | Contrato de skill completo (YAML de ejemplo) |
| R3 | Rúbrica de trazabilidad: los 7 componentes y sus pesos |
| R4 | Los cinco diseños de enrutado con sus intervalos |
| R5 | Segmentación por módulo, riesgo y etiqueta |
| R6 | Los 16 defectos, tabla completa |
| R7 | Comparación de recuperadores: TF-IDF vs embeddings vs híbrido |
| R8 | Sensibilidad al proveedor: false allow de A 0,333 ↔ 0,889 (piloto v1) |
| R9 | Los 11 controles de `demo_completa.py`, con el contraste A vs C |
| R10 | CU-02: el sistema propone una skill pero se detiene en TESTED |
| R11 | H4 por categoría: 5 de 7 fallan (18–31 %), 2 en 0 % — `v21_h4_categories` |
| R12 | El `DENY` de A/B no es una decisión de seguridad: `"ALLOW" if result.error is None else "DENY"` |
