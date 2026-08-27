# Vídeo — guion literal

Narración palabra por palabra, con lo que se ve en pantalla, qué comando
se ejecuta y **qué hace ese comando** en cada toma — no solo el titular
emocional. Límite duro de la competición: **5:00**, no se puede superar.

Regla heredada de `docs/defensa.md`: **el dato flojo antes que el
fuerte**. En ese orden el fuerte se cree.

Todo lo que aparece en pantalla es salida real de un comando o de la
app unificada (`make demo-product`). Nada recreado.

---

## 0:00 – 0:35 · Intro: de dónde viene esto

**Pantalla:** cámara al autor, o diapositiva simple con el título del
proyecto.

> Llevo tiempo trabajando con agentes de inteligencia artificial
> conectados a sistemas ERP. Y he visto de primera mano lo que pasa
> cuando algo sale mal: un importe que cambia solo, un pedido confirmado
> que no debía confirmarse, un registro duplicado que nadie detecta
> hasta que se cuadran cuentas.
>
> Cada vez más empresas conectan agentes de IA directamente a su ERP —
> SAP, Salesforce, Odoo. Para este TFM elegí Odoo: es de código
> abierto, tiene una API real y documentada, y permite comprobar
> exactamente qué pasa dentro cuando algo se ejecuta. Nada de lo que van
> a ver es una simulación.

---

## 0:35 – 0:55 · El problema

**Pantalla:** Odoo real. Una oportunidad con importe 15.000 €. Corte. La
misma con 27.600 €.

> Esta es una oportunidad real en Odoo: quince mil euros. Y esta es la
> misma, después de que un agente sin control la tocara: veintisiete mil
> seiscientos.
>
> No es una respuesta incorrecta de un chat. Es un asiento contable. Y
> alguien tiene que responder por él.

---

## 0:55 – 1:35 · El agente sin gobierno: qué hace este comando

**Pantalla:** terminal. Se ejecuta un comando que aísla una sola escena
de la demo — sin red, sin Odoo, todo en memoria — para que se vea rápido
y sin ruido de las otras diez.

> Este comando monta dos sistemas en memoria: uno con herramientas pero
> sin ningún control, y el mío, gobernado. A los dos les pido lo mismo —
> actualizar un importe a veintisiete mil euros. Es una operación de
> riesgo medio.
>
> El sistema sin gobierno la ejecuta directamente: nadie autorizó nada,
> no queda constancia. El mío se detiene y pide aprobación. Solo cuando
> yo, con mi nombre, la concedo, escribe.
>
> Mismo código, mismos argumentos. Lo único que cambió es que un humano
> autorizó el alcance.

---

## 1:35 – 2:00 · La arquitectura

**Pantalla:** diagrama de dos zonas. A la izquierda interpretar,
proponer, recuperar. A la derecha validar, autorizar, ejecutar,
verificar, auditar.

> Esto es lo que lo hace posible. El modelo de lenguaje solo
> **propone**: interpreta la petición y sugiere una acción. A la
> derecha, código determinista decide: valida el esquema, comprueba el
> rol, clasifica el riesgo, ejecuta solo handlers registrados y
> **verifica el estado final**.
>
> El modelo nunca toca la base de datos directamente. Solo puede emitir
> el identificador de una capacidad conocida, con argumentos validados
> contra un contrato.

---

## 2:00 – 2:35 · Skill Studio: una capacidad nueva, sin tocar código

**Pantalla:** la app unificada, pestaña **Skill Studio**. Se escribe una
petición que el catálogo actual no cubre. Se pulsa «Generate skill
proposal»: el modelo devuelve el contrato en un **formulario legible**
— riesgo, roles como chips, condición de aprobación con un probador
integrado. Al validar, aparece el registro real creado en el sandbox
(releído, no solo el «OK» del handler). Etiqueta persistente en
pantalla: `POST-CORE DEMO`. Se aprueba con un nombre humano. El estado
pasa a `ACTIVE`.

> El catálogo de capacidades no es fijo por accidente: es gobernado por
> diseño. Cuando falta una, el modelo puede **proponer** un contrato —
> nunca activarlo, y en un formulario que cualquiera puede leer, no en
> JSON. Puedo probar en vivo si una condición de aprobación se
> cumpliría, y al validar, ver el registro real que se creó en un
> almacén de pruebas — no me fío de que el sistema diga «correcto», lo
> compruebo. Al final, lo apruebo yo, con mi nombre, y queda en el
> historial.
>
> Fíjense en la etiqueta arriba: "post-core demo". Esta pantalla no
> forma parte de las ocho hipótesis que mido con datos — es una
> demostración de producto. Pero el principio es el mismo de todo el
> proyecto: el modelo propone, un humano con nombre decide.
>
> Esto que van a ver ahora en Odoo real — cambiar el importe de una
> oportunidad — es exactamente el destino final de una skill nacida
> así en Skill Studio, una vez un ingeniero le conecta el handler.

---

## 2:35 – 3:20 · Demostración contra Odoo real

**Pantalla:** la app unificada, pestaña **Operations** — mismo
navegador que las escenas anteriores, sin terminal. Tres peticiones en
texto libre, una por paso. Cortes al navegador de Odoo para ver el
registro.

> Esto es Odoo real, no un simulador. Voy a hacer tres cosas, aquí
> mismo en el navegador.
>
> Primero, crear una oportunidad: riesgo bajo, se ejecuta, y vuelve a
> leer Odoo para comprobar que el registro existe con el importe
> pedido.
>
> Segundo, cambiar ese importe: riesgo medio, requiere aprobación. Se
> detiene. Y no me creo lo que el sistema dice de sí mismo — leo Odoo
> otra vez, por separado. El importe sigue siendo el original.
>
> Tercero, concedo la aprobación y repito la petición. Ahora sí escribe.
> Esto es lo que ahora mido con datos — empezando por el más duro.

---

## 3:20 – 4:10 · Los números

**Pantalla:** primero la figura `v21_h4_categories` (19,0 % de mutación
no autorizada, umbral del 5 % marcado). Después, la tabla de los tres
canales con el 0 / 1.530 destacado.

> Ahora los datos, empezando por el peor, y este es confirmatorio, no un
> piloto: sobre trescientas quince peticiones peligrosas reales, mi
> sistema deja pasar una mutación no autorizada en una de cada cinco.
> Casi cuatro veces el umbral que fijé antes de ver el resultado.
>
> Así que hice otra pregunta, sobre otro tipo de ataque: **concedido que
> el ataque ha ganado por completo — el modelo comprometido, el
> atacante escribiendo directamente los argumentos —, ¿se llega a
> escribir algo?**
>
> Quinientos diez ataques externos, por los tres canales que un atacante
> controla de verdad. **Cero mutaciones no autorizadas en mil quinientas
> treinta.**
>
> Son dos preguntas distintas, con dos respuestas distintas. El
> confinamiento aguanta cuando el modelo falla del todo. No sustituye a
> un buen juicio sobre lo ambiguo, y eso también lo mido.

---

## 4:10 – 4:45 · Valor, y el límite

**Pantalla:** la figura `v21_hypotheses_forest` — nueve pruebas,
confirmadas en azul, no confirmadas en rojo.

> Todo esto lo comparé contra tres sistemas, no solo el que vieron
> antes: un agente directo sin ningún control, uno con herramientas
> tipadas pero sin catálogo ni auditoría, y el mío, gobernado — el
> mismo contraste de antes, ahora con los tres a la vez.
>
> Construí un banco de pruebas propio para esto: cuatrocientas ochenta
> peticiones, sobre doce capacidades reales, en ocho áreas de un ERP.
> La campaña final son veintiún mil cuatrocientas setenta y ocho
> observaciones, con el protocolo congelado **antes** de generar el
> conjunto de prueba — para no poder ajustar nada después de ver el
> resultado.
>
> Medido ahí: mi sistema es más barato en tokens, más estable entre
> formulaciones distintas de la misma petición, y su auditoría se
> reconstruye con más completitud.
>
> Y el límite, con la misma claridad: no supera en tasa de éxito a un
> agente con herramientas tipadas, y no reduce el riesgo de seguridad
> frente a ninguno de los dos comparadores. Está en los resultados, no
> escondido en una nota al pie.

---

## Cierre (4:45 – 5:05)

**Pantalla:** frase única sobre fondo limpio.

> Y esto no se queda en un experimento. El producto real es un sitio
> donde cualquier empresario, en lenguaje natural, trabaja con un
> agente de inteligencia artificial sobre su ERP, crea automatizaciones
> nuevas sin escribir código, y se aprovecha de todo lo que acabo de
> enseñar: control, verificación y auditoría reales.
>
> ERP Agent OS no intenta hacer infalible al modelo. Intenta que una
> operación empresarial no dependa únicamente de que el modelo acierte.
> El modelo propone; la organización conserva la autoridad.

---

> **Este documento quedó SUPERSEDIDO por `docs/GUION-DEFINITIVO.md`**,
> que fusiona narración + comando + plan de rodaje en un único fichero
> de rodaje (evita que guion, plan y grabación diverjan, que es
> precisamente lo que pasaba antes de fusionarlos). Se conserva aquí
> como referencia histórica de la narración palabra por palabra; para
> grabar, usar solo `GUION-DEFINITIVO.md`.

---

> **Plan de rodaje en `docs/video-plan-rodaje.md`**: qué comando/pantalla
> por toma, cuánto tarda cada una medido en esta máquina, y la
> preparación de entorno que las tomas de Odoo y Skill Studio necesitan
> antes de rodar.

## Notas de producción

- **Todo lo que se ve debe ser salida real.** Comandos:
  `scripts/odoo_governed_demo.py`, `scripts/injection_resistance_test.py`,
  `scripts/run_experiment.py`; escena 2 aislada vía
  `python -c "...escena_2_aprobacion(pausa=False)"`; app real:
  `make demo-product` (Skill Studio). Si algo no se puede grabar en
  vivo, se muestra el JSON de `data/` — no se recrea una captura.
- **Skill Studio necesita `OPENROUTER_API_KEY`** para el draft en vivo.
  Probar la llamada una vez antes de grabar — tarda ~15-20s medido, no
  segundos. Si falla en directo, repetir la toma, no maquetar el
  contrato.
- **No decir «seguro» ni «inmune».** La afirmación es acotada: 510
  payloads, tres canales, cero mutaciones no autorizadas, sin adversario
  adaptativo.
- **No decir «ahorra X euros»**: el análisis de coste es de
  sensibilidad, con tarifa declarada.
- El tramo 3:20–4:10 (los números) es el que decide el vídeo. Si el
  montaje se pasa de 5:00, recortar de la intro o del cierre antes que
  de ahí.
- Grabar la demo de Odoo **de una sola toma**. Un corte en medio hace
  que la relectura independiente pierda todo su valor probatorio.
- Skill Studio también se graba de una sola toma, pero es una sola
  pantalla sin refrescos de navegador — riesgo de rodaje menor que la
  toma de Odoo.
