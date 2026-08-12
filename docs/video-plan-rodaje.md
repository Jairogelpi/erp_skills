# Plan de rodaje: qué grabar exactamente

Complementa `docs/video-guion.md` (la narración). Esto es la lista de
tomas: **qué comando, cuánto tarda de verdad, qué se ve en pantalla**.
Los tiempos están medidos en esta máquina, no estimados.

Regla: **todo lo que aparezca en pantalla es salida real**. Nada
recreado, nada maquetado para parecer una ejecución.

---

## Preparación (una vez, antes de grabar)

**Terminal.** Fuente grande (18–20 pt), fondo oscuro, ventana ~100
columnas. En un vídeo a 1080p, una terminal a tamaño normal no se lee.

**Odoo: obligatorio antes de la toma 4.** Este equipo tiene `ODOO_URL`
apuntando a **producción** como variable de usuario persistente, y el
guardián del código lo rechaza (correctamente). Antes de grabar, en la
misma terminal:

```sh
export ODOO_URL="https://esenssi-aromas-dev-pruebas-limpio-36154343.dev.odoo.com"
export ODOO_DB="esenssi-aromas-dev-pruebas-limpio-36154343"
export ODOO_USERNAME="jairogelpi@gmail.com"
export ODOO_API_KEY="<la de .env>"
```

Verificar que responde antes de rodar, o la toma se cae en directo.

**Navegador.** Pestaña abierta en la vista de oportunidades (`crm.lead`)
de la rama de desarrollo, lista para refrescar en cámara.

---

## Las seis tomas

### Toma 1 — El problema *(0:00–0:30)*

**Pantalla:** navegador, Odoo real. Una oportunidad con importe. Corte
seco a la misma con otro importe.

**Cómo:** dos capturas de la interfaz de Odoo, no terminal. Es la única
toma donde se ve producto y no consola, y por eso abre.

**Duración de rodaje:** 2 minutos.

---

### Toma 2 — El agente sin gobierno ejecuta *(0:30–1:00)*

**Pantalla:** terminal.

```sh
uv run python scripts/demo.py
```

**Qué mostrar:** el **escenario 4** de la salida — petición con "aplícalo
también a todos los clientes similares" → `DENY`, motivo
`BULK_SCOPE`. Y para el contraste del guion, el sistema A ejecutando lo
mismo (usar la salida de `data/experiment_results.json` si no se quiere
montar la llamada en vivo).

**Duración real del comando: 14 segundos.** Cabe entero en cámara, sin
cortes.

---

### Toma 3 — La arquitectura *(1:00–1:45)*

**Pantalla:** diagrama de las dos zonas. **No es una toma de pantalla**,
es una diapositiva.

**Cómo:** el diagrama del README (`request → Intent Parser → …`)
redibujado limpio, o el de `docs/architecture.md`. Animación mínima: que
aparezca primero la zona izquierda, luego la línea, luego la derecha.

**Duración de rodaje:** es montaje, no rodaje.

---

### Toma 4 — Odoo real *(1:45–2:45)* · **LA TOMA IMPORTANTE**

**Pantalla:** terminal a pantalla partida con el navegador de Odoo.

```sh
uv run python scripts/odoo_governed_demo.py
```

**Qué se ve, en orden:**

1. Crear oportunidad (R1) → `ALLOW`. **Refrescar Odoo en el navegador**:
   el registro está ahí.
2. Cambiar importe (R2) sin aprobación → `REQUIRE_APPROVAL`. **Refrescar
   Odoo**: el importe **no ha cambiado**.
3. Conceder aprobación, repetir → `ALLOW`. **Refrescar Odoo**: ahora sí.

**Regla de rodaje, no negociable: una sola toma continua.** Un corte
entre el bloqueo y el refresco del navegador destruye todo el valor
probatorio — el espectador ya no sabe si entre plano y plano pasó algo.
Si sale mal, se repite entera.

**Duración de rodaje:** 10–15 minutos con repeticiones. Es la toma que
más cuesta y la que más vale.

---

### Toma 5 — Los números *(2:45–3:40)*

**Pantalla:** dos tablas seguidas.

Primero **el dato flojo**, de `data/injecagent_stress_test_results.json`:
0 % → 3,3 %.

Después **el fuerte**:

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

### Toma 6 — Valor y límite *(3:40–4:20)*

**Pantalla:** dos cifras enfrentadas, diapositiva.

- Agente sin gobierno: false allow **0,333** (OpenRouter) ↔ **0,889**
  (Groq).
- Sistema gobernado: **0,111** con los tres.

Y debajo, el límite: la ventaja en éxito de tarea **no transfiere** a
texto real (0,733 → 0,381 de recuperación).

**Duración de rodaje:** montaje.

---

## Presupuesto realista

| Bloque | Tiempo |
|---|---|
| Preparación de entorno y navegador | 20 min |
| Tomas 2 y 5 (terminal) | 30 min |
| **Toma 4 (Odoo, una sola toma)** | **45 min** con repeticiones |
| Diapositivas 1, 3, 6 | 60 min |
| Locución sobre `docs/video-guion.md` | 45 min |
| Montaje | 90 min |
| **Total** | **~5 horas** |

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
