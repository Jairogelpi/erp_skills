# Guion de defensa y vídeo: qué contar y en qué orden

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** (marcador exigido por
> el contrato automático `src/erp_agent_os/claims.py`/`tests/test_claims.py`,
> escrito en la era v1 — **ver la nota siguiente antes de leerlo como el
> estado real**)
>
> Actualizado 2026-08-23: la campaña confirmatoria v2.1.2 ya terminó
> (`RUN_COMPLETED`/`CLOSURE_VALID`, 21.478 observaciones reales). El guion de
> abajo se escribió el 12-ago sobre señales exploratorias de v1 y sigue sin
> reescribirse con las cifras confirmatorias reales — dos de sus tres pilares
> (la demo de Odoo y el stress test de inyección 0/1.530) no dependen de la
> campaña y siguen de pie, pero el tramo "Los números" (2:45-3:40) cita false
> allow de v1 (0,111 con los tres proveedores), no el hallazgo confirmatorio
> de H4 de v2.1 (mutación no autorizada real del 19,0 %, casi 4× el umbral
> — ver `docs/results-v2.1.md` Parte A §4). **Ese tramo necesita reescribirse
> antes de grabar nada** — el estado canónico ya no es
> `docs/hypotheses-and-theses.md` en solitario, es `docs/results-v2.1.md`.

Documento de **presentación**, no de investigación. No introduce ningún
resultado nuevo ni reformula ninguna hipótesis: H1–H8 quedan como se
declararon en `CLAUDE.md` §6 y se reportan como se midieron. Lo único
que cambia aquí es **el orden**, y el criterio para ordenar es cuánto
resiste cada resultado al escrutinio, no cuánto favorece a la tesis.

---

## La regla que gobierna este guion

> Abrir por lo que aguanta, no por lo que suena bien.

Aplicada, esto significa **no abrir con el STSR**. Es el endpoint
primario y hay que reportarlo, pero como titular es débil por tres
razones que un tribunal verá antes que tú:

1. que un sistema diseñado para bloquear bloquee está cerca de la
   tautología;
2. el sistema A puntúa 0,000 **por construcción** —CRUD genérico no
   puede codificar postcondiciones—, así que el contraste informativo es
   C−B, no C−A;
3. la ventaja sobre B es modesta (+15 pp) y, medido después, **no
   transfiere a texto real**.

Decir esto tú primero cuesta treinta segundos y desarma las tres
objeciones. Que lo diga el tribunal cuesta la defensa.

---

## Arco narrativo (defensa larga)

### 1. El problema, en una frase concreta

No «los agentes pueden equivocarse», sino: *un agente con acceso al ERP
que interpreta mal una instrucción no da una respuesta incorrecta —
duplica un registro, cambia un importe o confirma un documento que no
debía confirmarse*. El coste no es una molestia, es un asiento contable.

### 2. La pregunta que hace este trabajo, y por qué es distinta

La literatura de robustez adversarial mide **si un detector dispara**.
Este trabajo acabó midiendo otra cosa, porque su propio detector resultó
casi inútil fuera de su distribución:

> Concedido el ataque por completo —el modelo comprometido, el atacante
> dictando los argumentos—, ¿ocurre alguna mutación no autorizada?

**Enseñar el dato flojo primero**: 3,3 % de detección sobre 510 casos
externos de InjecAgent. **Después el fuerte**: los mismos 510 payloads
por los tres canales que un atacante controla → **0 de 1.530**
mutaciones no autorizadas, con **510 de 510 denegadas** en el brazo que
entrega el LLM entero al atacante.

Y el control que hace que ese cero signifique algo: una petición limpia
debe llegar al handler y **crear un registro real**, o el experimento
aborta. Sin ese control, una credencial sin permiso de escritura habría
producido el mismo cero perfecto sin significar nada.

### 3. La demostración, en vivo y contra un ERP real

Tres pasos contra una instancia real de Odoo 19, con el mismo `Runtime`
y el mismo almacén de auditoría que corren las 1.080 observaciones:

1. crear una oportunidad (R1) → ejecuta y verifica la postcondición **por
   relectura independiente**;
2. cambiar el importe (R2) sin aprobación → `REQUIRE_APPROVAL`, y una
   relectura independiente confirma que Odoo **no cambió**;
3. conceder la aprobación y repetir → ahora sí escribe.

El detalle que lo hace evidencia y no demo: la comprobación no se fía de
lo que el sistema dice de sí mismo, vuelve a leer el ERP por separado.

### 4. El experimento, con sus límites por delante

**Hay dos campañas, y hay que nombrarlas por separado.** La confirmatoria
real es v2.1 (`tfm-protocol-v2.1.2`): 21.478 observaciones, protocolo y
potencia congelados **antes** de generar el holdout, evaluación única. La
de 1.080 observaciones (v1) es un piloto exploratorio — sigue citándose
porque ahí salieron varios hallazgos que v2.1 confirma o corrige, no
porque sus números sean el resultado.

**v2.1, confirmatorio:** STSR de C no inferior a A (+25,3 pp, holgado); C
**no** supera a B en éxito de tarea (p=0,286, igual que en v1); tokens de C
más baratos que A y que B (−468 y −648, IC95 completo por debajo de cero);
estabilidad entre paráfrasis confirmada por primera vez de verdad
(p=2,2e-18); trazabilidad confirmada (+42,7 pp sobre A, p=2,85e-112, con la
salvedad de que A/B no tienen esa capacidad por diseño).

**Y el dato que cambia el discurso de seguridad, sin suavizarlo:** sobre
315 escenarios peligrosos reales (no 9), C deja pasar una mutación real no
autorizada en el **19,0 %** de los casos — casi 4× el umbral prerregistrado
del 5 %. Localizado: en 5 de 7 categorías de ataque falla entre el 18 % y
el 31 % de las veces; en las otras 2 (permisos insuficientes, modificación
masiva disfrazada) falla el 0 %. No es un artefacto de los defectos que
contaminaban la campaña anterior — se verificó que el número apenas cambia
(19,6 % → 19,0 %) al corregirlos.

Y **acto seguido**, sin esperar a que pregunten: A puntúa 0 por
construcción; el contraste real es C−B; la ventaja en éxito de tarea no
transfiere a texto real (medido: el recuperador cae de 0,733 a 0,381, y
la propia H5 confirmatoria de v2.1 falla los tres umbrales de recuperación
que exige el protocolo); y el `DENY` que A y B sí emiten con más frecuencia
que C **no es una decisión de seguridad** — es una etiqueta de error de
ejecución (`"ALLOW" if result.error is None else "DENY"`), así que "A
deniega más que C" no significa "A es más seguro", significa "A se cae más
a menudo al intentar ejecutar peticiones mal formadas".

### 5. Lo que hice cuando los datos me quitaron la razón

Tres veces la medición honesta empeoró el resultado, y las tres se
publicaron antes de encontrar el matiz que las mejoraba:

- se descubrió que el parseo de argumentos estaba **regalado** a los
  tres sistemas, lo que inflaba a C; al quitarlo, la ventaja sobre B
  **dejó de ser significativa** (*p* = 0,212) y así se publicó;
- una pregunta escéptica reveló después que ese resultado tenía un sesgo
  **contra** C (una unidad monetaria sin normalizar); corregido, volvió a
  ser significativo pero **menor** que el original;
- se midió si la recuperación sobrevivía a texto real: no sobrevive, y
  eso acota el resultado principal del trabajo.

Y un caso que conviene contar entero: **el único caso peligroso que el
sistema permite en el test congelado de v1 resultó no ser peligroso** — un
defecto de etiquetado del propio dataset. Corregirlo habría bajado el
*false allow* de C de 0,111 a **0,000**. No se corrigió: el test estaba
congelado, y cambiarlo a posteriori porque mejora tus números es
exactamente lo que la congelación existe para impedir. Se publicó como
análisis de sensibilidad junto a la cifra contaminada.

Y el episodio equivalente en v2.1, más reciente: al escribir esta memoria
se encontró que el análisis de H2 solo comparaba C contra A, nunca contra
B, pese a que el protocolo exige ambas. Se corrigió — y el resultado no
cambió (C sigue ganando a los dos con holgura) —, pero corregir el
código de análisis después de ver un resultado exige el mismo cuidado que
corregir el dataset: se documentó, se recongeló formalmente con tag y
commit propios, y se conservó el informe anterior sin borrar. Y al
investigar por qué H4 seguía saliendo mal tras arreglar sus dos defectos
conocidos, apareció el hallazgo del párrafo anterior sobre el `DENY` de
A/B — no se buscaba, apareció al desconfiar de un número sorprendente en
vez de darlo por bueno.

### 6. Lo que dejo utilizable

**Un enunciado metodológico, con evidencia detrás:** *el desarrollo
dirigido por pruebas protege bien lo que se implementa contra un
requisito explícito y protege mal lo que solo se calcula a partir de una
fórmula*. De 40 mutantes inyectados en 23 módulos, los **dos** únicos
supervivientes estaban en la capa estadística — la que produce los
números publicados —, porque sus tests verificaban la *conclusión* del
cálculo (¿es significativo?, ¿está en rango?) y no el *mecanismo*.

**Una regla operativa:** *una comprobación que no puede fallar es peor
que no tener comprobación*, porque fabrica confianza. Cinco de los
dieciocho defectos tienen esa forma exacta.

**Un hallazgo aplicable a quien monte algo parecido:** la descripción de
una línea por skill es el cuello de botella del enrutado, no el
algoritmo. Diez formulaciones reales por skill suben la precisión un
74 % relativo, generalizan a autores que nunca vieron el catálogo
(verificado con 20 anotadores identificados de un corpus externo) y
cuestan **cero tokens**.

---

## Guion del vídeo (3–5 min, tramos de §39)

| Tramo | Contenido |
|---|---|
| **0:00–0:30** | El problema con un caso concreto: no «la IA falla», sino un importe cambiado en un ERP real y quién responde por él. |
| **0:30–1:00** | El error de un agente sin gobierno: petición con instrucción inyectada → System A la ejecuta. Mostrar el registro escrito. |
| **1:00–1:45** | La arquitectura en una frase: el modelo **propone**, el contrato **decide**. Diagrama de las dos zonas. |
| **1:45–2:45** | Demo real contra Odoo 19: R1 ejecuta; R2 se bloquea y **se verifica leyendo Odoo por separado**; con aprobación, escribe. |
| **2:45–3:40** | Los números, empezando por el más flojo: sobre 315 peticiones peligrosas reales, C deja pasar el **19 %** de mutaciones no autorizadas — casi 4× el umbral. Después el que sí aguanta: **0 de 1.530** mutaciones cuando el atacante controla el modelo entero (inyección explícita, no ambigüedad plausible). Dos propiedades distintas, dicho así en voz alta. |
| **3:40–4:20** | Valor con el límite integrado: la gobernanza confina incluso cuando el modelo está comprometido — eso no depende del proveedor —, pero no sustituye a un buen juicio sobre peticiones ambiguas sin marcador de ataque. Eso sigue siendo una brecha real, medida, no oculta. |
| **Cierre** | «No intenta que el agente improvise mejor. Convierte una operación aprendida en una capacidad reutilizable, verificable y medible.» |

---

## Las siete preguntas difíciles, y qué responder

**1. «Su sistema bloquea porque usted lo diseñó para bloquear. ¿Qué ha
observado?»**
Que no bloquea tanto como debería, de hecho: sobre 315 peticiones
peligrosas reales de la campaña confirmatoria, deja pasar el 19 %. Lo que
sí se sostiene, y es confirmatorio, es más estrecho: el confinamiento
**aguanta cuando el modelo falla del todo** — 510 de 510 con el atacante
dictando los argumentos — independiente del proveedor. Detección y
confinamiento son propiedades distintas, y solo la segunda está probada.

**2. «A obtiene 0,000. ¿No está amañada la comparación?»**
A puntúa 0 por construcción: STSR exige estado final verificado y unas
herramientas CRUD genéricas no pueden codificar postcondiciones. Por eso
el contraste que reporto como informativo es **C−B**, donde ambos
comparten catálogo, esquemas y handlers y solo difieren en gobernanza.

**3. «¿Su ventaja transfiere fuera del benchmark?»**
En seguridad y trazabilidad, sí: no dependen del texto ni del modelo. En
éxito de tarea, **no**, y lo medí: el recuperador cae de 0,733 a 0,381
con peticiones reales. Está escrito como amenaza a la validez, no
escondido en una nota.

**4. «Su detección de inyección es del 3,3 %. ¿No es un fracaso?»**
Del detector, sí, y lo reporto como tal. Del sistema, no: la defensa
efectiva no es el detector sino que los datos del ERP nunca ocupan
posición de instrucción y que el modelo solo puede emitir un
identificador de skill con argumentos validados. Por eso el ataque no
consigue mutar nada aunque el detector no dispare.

**5. «¿Cuánto pesa realmente su resultado de seguridad?»**
En v1 pesaba poco: n=9 casos peligrosos, IC [0,020, 0,435]. Por eso se
construyó v2.1 con un benchmark de seguridad de 315 escenarios,
congelado antes de verlos. Con esa n, el resultado es nítido y va **en
contra** de C, no a favor: 19 % de mutación no autorizada, muy por
encima del umbral. Es un resultado peor, pero con muchísima más
autoridad estadística que el 8× de v1.

**6. «El benchmark es sintético y usted lo generó.»**
Sí, y por eso lo sometí a tres pruebas externas: InjecAgent para
robustez adversarial, peticiones reales para recuperación, y un corpus
multiautor de 20 anotadores identificados para comprobar si el arreglo
generaliza a gente que nunca vio el catálogo.

**7. «¿Por qué un modelo gratuito?»**
Restricción declarada, no oculta. Y hay un dato a favor de la tesis
justo ahí: las métricas de gobernanza de C son **idénticas** con los tres
proveedores probados, mientras que el *false allow* del agente sin
gobierno se mueve entre 0,333 y 0,889 según el modelo. La gobernanza es
precisamente lo que permite no depender del modelo.

**8. «Si su sistema falla el 19 % en seguridad, ¿qué queda de la tesis?»**
Lo que queda es medible, y no es "seguro": es más barato (H2), más
estable entre formulaciones (H3a), más trazable (H7) y no peor en tarea
que un agente sin gobierno (H1a) — cuatro de nueve pruebas confirmatorias
se sostienen. La promesa de detección activa de peligro, no. Diagnostiqué
dónde exactamente: dos de siete categorías de ataque funcionan
perfectamente, cinco no. Una tesis que dijera "esto es seguro" sería
falsa; una que dice "esto es más barato, más trazable y más estable, y
tiene un hueco de seguridad localizado y medido" es la que puedo
defender con los datos delante.

---

## Lo que NO se debe decir

- «Sistema seguro» o «inmune a inyección». La afirmación defendible es
  acotada: 510 payloads, tres canales, cero mutaciones no autorizadas,
  sin adversario adaptativo — y aun así, sobre peticiones peligrosas
  plausibles sin marcador de ataque, el sistema falla el 19 %.
- «8× más seguro» — ni con el intervalo de v1 (n=9) ni con ningún otro:
  la campaña confirmatoria de v2.1 (n=315) mide lo contrario en esa
  población.
- «Detectamos peticiones peligrosas» o «C es más seguro que un agente sin
  gobierno»: H4 confirmatoria dice explícitamente lo contrario en las
  cuatro comparaciones. Lo que sí se sostiene es «el confinamiento
  aguanta incluso con el modelo comprometido», que es una afirmación más
  estrecha y distinta.
- «Ahorra X euros»: H8 es un análisis de sensibilidad con tarifa
  declarada, no gasto observado.
- «Detectamos ataques de inyección»: 3,3 % fuera de distribución.
- «Más estable entre ejecuciones» sin precisar: bajo temperatura 0 y
  repeticiones literales (H3b), los tres sistemas salen a 1,000 y no
  discrimina — la afirmación que sí se sostiene es H3a (estabilidad
  **entre formulaciones distintas** del mismo escenario), confirmada.
