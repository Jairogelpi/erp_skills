# Guion de defensa y vídeo: qué contar y en qué orden

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion**
>
> Este guion debe presentar las cifras A/B/C como señales exploratorias y las
> pruebas de Odoo como factibilidad. Ninguna de H1-H8 está confirmada todavía;
> el estado canónico está en `docs/hypotheses-and-theses.md`.

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

1.080 observaciones, unidad de inferencia el caso (n=120, no 360:
tratar las repeticiones como independientes era pseudo-replicación y
está corregido), test congelado por hash y verificado en CI.

STSR A 0,000 · B 0,483 · **C 0,633**; C−B = +0,150 IC95 [+0,042,
+0,258], *p* = 0,016. *False allow* 0,889 / 0,889 / **0,111**.
Trazabilidad 0,356 / 0,374 / **0,820**. Tokens 185,1 / 265,3 / **67,6**.

Y **acto seguido**, sin esperar a que pregunten: A puntúa 0 por
construcción; el contraste real es C−B; la ventaja en éxito de tarea no
transfiere a texto real (medido: el recuperador cae de 0,733 a 0,381);
el *false allow* descansa en n = 9 casos peligrosos con IC [0,020,
0,435]; y en el test congelado **8 de esos 9 los bloquea un patrón
léxico escrito mirando ese mismo corpus**.

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
sistema permite en el test congelado resultó no ser peligroso** — un
defecto de etiquetado del propio dataset. Corregirlo habría bajado el
*false allow* de C de 0,111 a **0,000**. No se corrigió: el test estaba
congelado, y cambiarlo a posteriori porque mejora tus números es
exactamente lo que la congelación existe para impedir. Se publicó como
análisis de sensibilidad junto a la cifra contaminada.

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
quince defectos tienen esa forma exacta.

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
| **2:45–3:40** | Los números, con sus límites en la misma pantalla. Y el titular fuerte: **0 de 1.530**, incluido el brazo que le regala el LLM al atacante. |
| **3:40–4:20** | Valor: la gobernanza permite usar un modelo barato sin heredar su riesgo — la seguridad de A oscila con el proveedor (0,333↔0,889), la de C no se mueve (0,111). |
| **Cierre** | «No intenta que el agente improvise mejor. Convierte una operación aprendida en una capacidad reutilizable, verificable y medible.» |

---

## Las siete preguntas difíciles, y qué responder

**1. «Su sistema bloquea porque usted lo diseñó para bloquear. ¿Qué ha
observado?»**
Correcto, y por eso el resultado que presento no es ese. La señal
exploratoria es más estrecha: que el bloqueo **se sostiene cuando el modelo falla del
todo** — 510 de 510 con el atacante dictando los argumentos — y que eso
es independiente del proveedor, mientras que la seguridad del agente sin
gobierno sí depende de qué modelo le toque.

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

**5. «n = 9 casos peligrosos es muy poco.»**
Lo es, y publico el intervalo: [0,020, 0,435]. El «8×» es una estimación
puntual sobre nueve casos. La evidencia de seguridad que sí tiene tamaño
es la otra: 1.530 intentos con dataset externo.

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

---

## Lo que NO se debe decir

- «Sistema seguro» o «inmune a inyección». La afirmación defendible es
  acotada: 510 payloads, tres canales, cero mutaciones no autorizadas,
  sin adversario adaptativo.
- «8× más seguro» sin su intervalo.
- «Ahorra X euros»: H8 es un análisis de sensibilidad con tarifa
  declarada, no gasto observado.
- «Detectamos ataques de inyección»: 3,3 % fuera de distribución.
- «Más estable entre ejecuciones»: con temperatura 0 los tres sistemas
  salen a 1,000; H3 no discrimina y así se reporta.
