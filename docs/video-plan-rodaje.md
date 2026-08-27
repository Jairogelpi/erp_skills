# Plan de rodaje: qué grabar exactamente

> **SUPERSEDIDO por `docs/GUION-DEFINITIVO.md`** — fusiona este plan y
> `video-guion.md` en un único documento de rodaje, para que no puedan
> volver a divergir guion/plan/grabación entre sí. Se conserva aquí
> como referencia de preparación de entorno y tiempos medidos; para
> rodar, seguir `GUION-DEFINITIVO.md`.

Complementa `docs/video-guion.md` (la narración). Esto es la lista de
tomas: **qué comando, cuánto tarda de verdad, qué se ve en pantalla**.
Los tiempos están medidos en esta máquina, no estimados.

Regla: **todo lo que aparezca en pantalla es salida real**. Nada
recreado, nada maquetado para parecer una ejecución.

> Para entender **qué hace y qué prueba cada paso** de la demo —traza
> del código, mapa contra la especificación y guía de réplica— ver
> [`docs/demo-explicada.md`](demo-explicada.md).

---

## Preparación (una vez, antes de grabar)

**Terminal.** Fuente grande (18–20 pt), fondo oscuro, ventana ~100
columnas. En un vídeo a 1080p, una terminal a tamaño normal no se lee.

**Codificación, antes de tocar nada más.** En PowerShell sin fijarla,
los acentos y `§`/`—` salen como `�` — verificado el 23-08 grabando
`demo_completa.py`. Al principio de la sesión de grabación:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

Con eso puesto, la salida de `demo_completa.py` y `odoo_governed_demo.py`
sale exactamente como en el guion, sin mojibake.

**Odoo: obligatorio antes de la toma 5.** Este equipo tiene `ODOO_URL`
apuntando a **producción** como variable de usuario persistente, y el
guardián del código lo rechaza (correctamente). Antes de grabar, en la
misma terminal:

```sh
export ODOO_URL="https://acme-erp-dev-pruebas-36295186.dev.odoo.com"
export ODOO_DB="acme-erp-dev-pruebas-36295186"
export ODOO_USERNAME="<usuario-api>"
export ODOO_API_KEY="<la de .env>"
```

Verificar que responde antes de rodar, o la toma se cae en directo.

**Navegador.** Pestaña abierta en la vista de oportunidades (`crm.lead`)
de la rama de desarrollo, lista para refrescar en cámara.

**App unificada, para la toma de Skill Studio.** Antes de grabar:

```sh
export OPENROUTER_API_KEY="<la de .env>"
make demo-product
```

Esto corre `demo-preflight` primero (si falla, no se graba nada hasta
arreglarlo) y levanta backend (puerto 8000) + frontend (puerto 5173).
Abrir `http://localhost:5173`, pestaña **Skill Studio**, y **probar una
vez** "Generate skill proposal" antes de grabar — si la llamada al LLM
falla en directo, es mejor descubrirlo ahora que en la toma.

---

## Las siete tomas

### Toma 1 — El problema *(0:00–0:25)*

**Pantalla:** navegador, Odoo real. Oportunidad "Renovacion contrato
anual" de **Hoteles Camino (DEMO)** con 15.000 €. Corte seco. La misma
con 27.600 €.

**Qué afirma esta toma, y qué no.** Muestra **lo que está en juego**: un
registro de negocio real con un importe que puede cambiar. **No afirma
que un agente lo cambiara mal** — esa afirmación se hace en la toma 2,
donde el agente sin gobierno ejecuta de verdad y se ve la ejecución.
Presentar la toma 1 como «mira lo que hizo la IA» sería una recreación
disfrazada de prueba, exactamente lo que las notas de producción
prohíben. La locución del guion está escrita en términos de riesgo
(«sale esto: un importe cambiado»), no de incidente.

**Preparación del estado, en dos comandos:**

```sh
uv run python scripts/stage_video_shot1.py --before   # crea el registro a 15.000
#   ... grabar el plano del importe inicial ...
uv run python scripts/stage_video_shot1.py --after    # lo cambia a 27.600
#   ... refrescar y grabar el plano del importe cambiado ...
```

El cliente se llama **"Hoteles Camino (DEMO)"** a propósito: si el vídeo
se publica, nadie puede confundirlo con un cliente real de la empresa.

**Encuadre:** la ficha de la oportunidad con el campo de ingreso
esperado visible y grande. No grabar la lista, grabar la ficha — el
número tiene que leerse sin esfuerzo.

**Duración de rodaje:** 5 minutos (2 planos + los dos comandos).

---

### Toma 2 — El agente sin gobierno ejecuta *(0:25–0:50)*

**Pantalla:** terminal.

```sh
uv run python scripts/demo.py
```

**Qué mostrar:** mejor aún, usar la **demo completa**, que ya trae el
contraste construido:

```sh
uv run python scripts/demo_completa.py --pausa
```

Para este tramo bastan las **escenas 2 y 8**: A escribe sin permiso y A
duplica al repetir la petición, mientras C para y C reconoce la clave.
El contraste está en pantalla, sin montaje.

Alternativa más corta: `scripts/demo.py`, escenario 4 — petición con
"aplícalo también a todos los clientes similares" → `DENY`, motivo
`BULK_SCOPE`.

**Duración real del comando: 14 segundos.** Cabe entero en cámara, sin
cortes.

---

### Toma 3 — La arquitectura *(0:50–1:15)*

**Pantalla:** diagrama de las dos zonas. **No es una toma de pantalla**,
es una diapositiva.

**Cómo:** el diagrama del README (`request → Intent Parser → …`)
redibujado limpio, o el de `docs/architecture.md`. Animación mínima: que
aparezca primero la zona izquierda, luego la línea, luego la derecha.

**Prompt para generarlo con una IA de imagen/diagrama**, exacto,
completo, sin de más — solo lo que la narración de esta toma nombra:

```
Diagrama técnico limpio, estilo diapositiva profesional, fondo blanco,
horizontal, sin decoración ni iconos genéricos de robots/IA.

Dos zonas rectangulares del mismo tamaño, lado a lado, separadas por
una línea vertical gruesa en el centro.

ZONA IZQUIERDA, título "MODELO DE LENGUAJE — PROPONE" en la parte
superior. Dentro, tres cajas apiladas verticalmente conectadas por
flechas hacia abajo, con estos textos exactos:
1. "Interpretar la petición"
2. "Recuperar capacidades conocidas"
3. "Proponer una acción"

ZONA DERECHA, título "CÓDIGO DETERMINISTA — DECIDE" en la parte
superior. Dentro, cinco cajas apiladas verticalmente conectadas por
flechas hacia abajo, con estos textos exactos:
1. "Validar esquema"
2. "Comprobar rol"
3. "Clasificar riesgo"
4. "Ejecutar (solo handlers registrados)"
5. "Verificar estado final"

Una única flecha horizontal cruza la línea central desde la caja
"Proponer una acción" (zona izquierda) hasta la caja "Validar esquema"
(zona derecha), etiquetada "identificador de skill + argumentos".
Ninguna otra flecha cruza la línea central.

Arriba de todo, una caja de entrada pequeña con el texto "Petición del
usuario" con una flecha hacia la caja "Interpretar la petición".

Abajo de todo, a la derecha, una caja de salida pequeña con el texto
"ERP" con una flecha desde "Verificar estado final".

No añadir ningún otro elemento, icono, color decorativo, logotipo ni
texto que no esté listado arriba. Paleta: gris oscuro para el texto,
azul para la zona izquierda, verde para la zona derecha, ambos en tono
pastel/sobrio, apto para 1920x1080.
```

Si la IA de imagen no respeta texto exacto (es un problema conocido de
los generadores de imagen con texto largo), la alternativa fiable es
pedir el mismo contenido como diagrama Mermaid (`graph TB`) y
renderizarlo, o dibujarlo a mano en Keynote/Figma con esas mismas cajas
y textos literales.

**Duración de rodaje:** es montaje, no rodaje.

---

### Toma 4 — Skill Studio *(1:15–1:50)*

**Pantalla:** navegador, `http://localhost:5173`, pestaña **Skill
Studio** de la app unificada (`make demo-product`, ver preparación
arriba).

**Qué grabar, en una sola toma continua:**

1. Petición no cubierta: ya está precargada como texto por defecto de
   la pestaña ("marcar prioridad alta a las oportunidades abiertas de
   un cliente..."), no hace falta escribirla en cámara — solo pulsar el
   botón.
2. Pulsar **Generate skill proposal**. Esperar la respuesta real del
   LLM — el contrato aparece con riesgo, roles y regla de aprobación.
   El callout `AI MAY PROPOSE · AI MAY NOT ACTIVATE` está siempre visible
   en esta pestaña, no hace falta encuadrarlo aparte.
3. Pulsar **Validate + sandbox test**: el panel de la derecha muestra
   `✓ schema valid` / `✓ sandbox tests passed`.
4. Escribir un nombre en el campo de aprobador y pulsar **Approve
   skill**: el estado pasa a `ACTIVE`.

**Qué no grabar aquí:** la modificación por lenguaje natural (segundo
modo de la pestaña, con el diff CURRENT → PROPOSED) es real y
reproducible en directo, pero no cabe en el presupuesto de 35 segundos
de esta toma — se menciona solo en la locución. Si el vídeo final tiene
margen, es la primera candidata a añadir, no a recortar de otro sitio.

**Riesgo de rodaje:** depende de una llamada real a OpenRouter (paso 2).
Por eso la preparación exige probarla una vez antes de grabar. Si falla
en directo, cortar a `data/` no es una opción limpia aquí (no hay un
JSON de esta escena pensado para pantalla) — mejor repetir la toma.

**Duración real medida (2026-08-26, contra el Odoo local/Tailscale y
`deepseek/deepseek-v4-flash` vía OpenRouter):** la llamada de draft tarda
**~15-20 segundos**, no 2-4 — verificado en directo, no estimado. Deja
hueco en el corte de vídeo para esa espera (o corta a la locución
mientras carga) en vez de cronometrar la toma a 35 segundos secos.

---

### Toma 5 — Odoo real *(1:50–2:40)* · **LA TOMA IMPORTANTE**

**Cambio de plan (verificado en vivo el 27-08):** no se usa el script
CLI. Se hace en el navegador, pestaña **Operations** de la app
unificada — misma pantalla que las tomas anteriores, sin cortar a
terminal. Los tres pasos se probaron por API contra el Odoo real antes
de grabar y funcionaron exactamente así.

**Pantalla:** navegador a pantalla partida — pestaña Operations a un
lado, Odoo al otro (o dos ventanas).

**Qué se ve, en orden:**

1. Escribir `Crea una oportunidad para Distribuciones Norte por 12000
   euros.` → **Run** → `ALLOW`. **Refrescar Odoo**: el registro está
   ahí, 12.000€.
2. Escribir `Actualiza el importe esperado de la oportunidad <id> a
   20000 euros.` (el id sale en el resultado del paso 1) → **Run** →
   `REQUIRE_APPROVAL`, no ejecuta. **Refrescar Odoo**: sigue en
   12.000€.
3. Pulsar **Approve & execute** → concede aprobación y repite sola →
   `ALLOW`. **Refrescar Odoo**: ahora 20.000€.

Cada paso muestra la relectura independiente en el propio panel
("independent_reread"), así que el espectador ve **el número que el
sistema leyó de Odoo**, no solo la decisión que dice haber tomado.

**Riesgo nuevo frente al script:** el paso 2 depende de una llamada
real al LLM para extraer el id de la oportunidad del texto — en la
prueba funcionó a la primera, pero no es determinista al 100% como sí
lo era el script. Probar el texto exacto una vez antes de grabar, igual
que con Skill Studio.

**Regla de rodaje, no negociable: una sola toma continua.** Un corte
entre el bloqueo y el refresco del navegador destruye todo el valor
probatorio — el espectador ya no sabe si entre plano y plano pasó algo.
Si sale mal, se repite entera.

**Alternativa de respaldo si falla en directo:** `scripts/
odoo_governed_demo.py --rodaje` sigue funcionando exactamente igual
(verificado, más determinista) — cambiar a terminal solo si Operations
falla dos veces seguidas en el mismo día de rodaje.

**Duración de rodaje:** 10–15 minutos con repeticiones. Es la toma que
más cuesta y la que más vale.

---

### Toma 6 — Los números *(2:40–3:35)*

**Pantalla:** dos figuras seguidas.

Primero **el dato flojo, y es confirmatorio**: `reports/figures/v21_h4_categories.png`
(o regenerarla en vivo con `uv run python scripts/make_figures_v2_1.py`)
— 19,0 % de mutación no autorizada sobre 315 escenarios peligrosos
reales, casi 4× el umbral del 5 %. El dato antiguo de InjecAgent
(0 % → 3,3 %) mide otra cosa (detección léxica fuera de distribución) y
puede citarse de pasada, no como titular.

Después **el fuerte**, que sigue de pie:

```sh
uv run python scripts/injection_resistance_test.py
```

**Aviso práctico:** son 1.530 casos y **no cabe en el tramo de vídeo**.
Dos opciones honestas:
- grabar el arranque (el control positivo: `clean request -> ALLOW,
  created ['45']`) y cortar al resumen final de la misma ejecución;
- o mostrar `data/injection_resistance_results.json` en pantalla.

Lo que **no** se puede hacer es maquetar una tabla bonita y presentarla
como si fuera la salida.

**Duración de rodaje:** 5 minutos si se muestra el JSON; ~20 si se graba
la ejecución completa y se corta.

---

### Toma 7 — Valor y límite *(3:35–4:10)*

**Pantalla:** `reports/figures/v21_hypotheses_forest.png` — las nueve
pruebas de la campaña confirmatoria, confirmada/no confirmada.

- Valor confirmado: tokens más baratos (H2, vs A y vs B), más estable
  entre formulaciones (H3a), auditoría más completa (H7).
- Límite confirmado: no supera en éxito de tarea a un baseline con
  herramientas tipadas (H1b) ni reduce el riesgo de seguridad frente a
  ninguno de los dos comparadores (H4).

**Nota:** la cifra antigua de sensibilidad al proveedor (false allow
0,333 ↔ 0,889) es del piloto v1 con selector LLM real y **no** se probó
en la campaña confirmatoria v2.1 (un solo proveedor). No usarla aquí sin
esa salvedad — puede citarse como diapositiva de reserva (R8), no en el
tramo principal.

**Duración de rodaje:** montaje.

---

## Presupuesto realista

| Bloque | Tiempo |
|---|---|
| Preparación de entorno, navegador y `make demo-product` | 25 min |
| Tomas 2 y 6 (terminal) | 30 min |
| Toma 4 (Skill Studio, una sola toma) | 20 min con repeticiones |
| **Toma 5 (Odoo, una sola toma)** | **45 min** con repeticiones |
| Diapositivas 1, 3, 7 | 60 min |
| Locución sobre `docs/video-guion.md` | 45 min |
| Montaje | 90 min |
| **Total** | **~5,5 horas** |

---

## Errores que arruinan el vídeo

1. **Cortar la toma de Odoo.** Convierte la prueba en una afirmación.
2. **Terminal ilegible.** Si no se lee el `REQUIRE_APPROVAL`, la toma no
   existe.
3. **Empezar por los resultados A/B/C.** El guion abre por el problema y
   por el peor número propio, a propósito.
4. **Recrear una salida.** Si un comando no se puede grabar en vivo, se
   muestra el JSON versionado — no se dibuja una tabla que finja serlo.
5. **Decir «seguro» o «inmune».** La afirmación es acotada: 510
   payloads, tres canales, cero mutaciones no autorizadas, sin
   adversario adaptativo.
6. **No probar Skill Studio antes de grabar.** Depende de una llamada
   real al LLM (paso 2 de la toma 4); sin verificarla antes, la toma se
   puede caer en directo por una razón ajena al producto.
