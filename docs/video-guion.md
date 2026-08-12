# Vídeo de 4 minutos — guion literal

Narración palabra por palabra, con lo que se ve en pantalla y los
tiempos de los tramos de `CLAUDE.md` §39. ~620 palabras ≈ 4:00 a ritmo
normal en español.

Regla heredada de `docs/defensa.md`: **el dato flojo antes que el
fuerte**. En ese orden el fuerte se cree.

Todo lo que aparece en pantalla es salida real de un comando del
repositorio. Nada recreado.

---

## 0:00 – 0:30 · El problema

**Pantalla:** Odoo real. Una oportunidad con importe 15.000 €. Corte. La
misma con 27.600 €.

> Cuando un agente de inteligencia artificial se equivoca escribiendo un
> correo, sale un correo raro. Cuando se equivoca sobre un ERP, sale
> esto: un importe cambiado. O un pedido confirmado que no debía
> confirmarse. O un cliente duplicado.
>
> No es una respuesta incorrecta. Es un asiento. Y alguien responde por
> él.

---

## 0:30 – 1:00 · El error de un agente sin gobierno

**Pantalla:** terminal. Se escribe una petición con una instrucción
inyectada al final. El sistema A la ejecuta. Se ve el registro escrito
en el almacén.

> Este es un agente con herramientas y sin gobierno. Le pido algo
> normal, y dentro del texto viene escondida otra instrucción.
>
> La ejecuta. No porque el modelo sea malo: porque nada entre el modelo
> y la base de datos tenía autoridad para decir que no.

---

## 1:00 – 1:45 · La arquitectura

**Pantalla:** diagrama de dos zonas. A la izquierda interpretar,
proponer, recuperar. A la derecha validar, autorizar, ejecutar,
verificar, auditar.

> ERP Agent OS parte el sistema en dos.
>
> A la izquierda, el modelo de lenguaje: interpreta y **propone**. A la
> derecha, código determinista: valida el esquema, comprueba el rol,
> clasifica el riesgo, pide aprobación si hace falta, ejecuta solo
> handlers registrados y **verifica el estado final** antes de dar nada
> por bueno.
>
> El modelo puede proponer lo que quiera. Lo único que puede emitir es
> el identificador de una capacidad conocida, con argumentos que se
> validan contra un contrato. No hay camino desde el texto libre hasta
> la base de datos.

---

## 1:45 – 2:45 · Demostración contra Odoo real

**Pantalla:** `uv run python scripts/odoo_governed_demo.py`, salida
real. Tres bloques, uno por paso. Cortes a la interfaz de Odoo para ver
el registro.

> Esto es Odoo 19 real. No un simulador.
>
> Primero, crear una oportunidad. Riesgo bajo: se ejecuta, y el sistema
> vuelve a leer Odoo para comprobar que el registro existe con el
> importe que se pidió.
>
> Segundo, cambiar ese importe. Eso es riesgo medio: **requiere
> aprobación**. El sistema se detiene. Y aquí está lo importante — no me
> creo lo que el sistema dice de sí mismo: leo Odoo otra vez, por
> separado. El importe sigue siendo el original. No escribió nada.
>
> Tercero, concedo la aprobación y repito la misma petición. Ahora sí
> escribe.

---

## 2:45 – 3:40 · Los números

**Pantalla:** primero la tabla de detección (0 % → 3,3 %). Después, la
tabla de los tres canales con el 0 / 1.530 destacado.

> Ahora los datos, empezando por mi peor número.
>
> Cogí quinientos diez ataques reales de inyección de un benchmark
> externo y los pasé por mis detectores. Detectan el tres coma tres por
> ciento. Es un mal resultado y lo reporto como tal.
>
> Así que hice otra pregunta. En vez de «¿salta el detector?»:
> **concedido que el ataque ha ganado — el modelo comprometido, el
> atacante escribiendo directamente los argumentos —, ¿se llega a
> escribir algo?**
>
> Los mismos quinientos diez ataques, por los tres canales que un
> atacante controla de verdad. **Cero mutaciones no autorizadas en mil
> quinientas treinta.** Quinientas diez de quinientas diez denegadas en
> el caso en que le regalo el modelo entero al atacante.
>
> La defensa no era el detector. Era la arquitectura.

---

## 3:40 – 4:20 · Valor, y el límite

**Pantalla:** dos cifras enfrentadas. False allow del agente sin
gobierno: 0,333 con un proveedor, 0,889 con otro. Del sistema gobernado:
0,111 con los tres.

> Esto tiene una consecuencia práctica. La seguridad de un agente sin
> gobierno **depende de qué modelo le toque**: entre dos proveedores se
> mueve del treinta y tres al ochenta y nueve por ciento de fallos
> peligrosos. La del sistema gobernado no se mueve: once por ciento con
> los tres.
>
> Es decir, la gobernanza te permite usar un modelo barato sin heredar
> su riesgo.
>
> Y el límite, porque también lo medí: la ventaja en tasa de éxito
> frente a un baseline de herramientas tipadas es modesta, y **no
> sobrevive** al texto real de usuario. Está escrito en los resultados,
> no escondido en una nota al pie.

---

## Cierre

**Pantalla:** frase única sobre fondo limpio.

> ERP Agent OS no intenta que el agente improvise mejor cada vez.
> Convierte una operación aprendida en una capacidad reutilizable,
> verificable y medible.
>
> El modelo propone. El contrato decide. Y cuando el modelo falla del
> todo, el contrato sigue decidiendo.

---

> **Plan de rodaje en `docs/video-plan-rodaje.md`**: qué comando por
> toma, cuánto tarda cada uno medido en esta máquina, y la preparación
> de entorno que la toma de Odoo necesita antes de rodar.

## Notas de producción

- **Todo lo que se ve debe ser salida real.** Los comandos son
  `scripts/odoo_governed_demo.py`, `scripts/injection_resistance_test.py`
  y `scripts/run_experiment.py`. Si algo no se puede grabar en vivo, se
  muestra el JSON de `data/` — no se recrea una captura.
- **No decir «seguro» ni «inmune».** La afirmación es acotada: 510
  payloads, tres canales, cero mutaciones no autorizadas, sin adversario
  adaptativo.
- **No decir «ahorra X euros»**: el análisis de coste es de
  sensibilidad, con tarifa declarada.
- El tramo 2:45–3:40 es el que decide el vídeo. Si hay que recortar,
  recortar de 1:00–1:45, no de ahí.
- Grabar la demo de Odoo **de una sola toma**. Un corte en medio hace
  que la relectura independiente pierda todo su valor probatorio.
