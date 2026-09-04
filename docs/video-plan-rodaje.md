# Plan de rodaje: qué grabar exactamente

Complementa `docs/video-guion.md` (la narración). Este documento fija
qué comando usar, qué se ve en pantalla y qué evidencia sostiene cada
toma. El vídeo final del TFM debe durar **como máximo 5:00**.

Regla: **no presentar una recreación como evidencia experimental**. Si
una escena está preparada para ilustrar un riesgo, debe quedar descrita
como tal; si se muestra un resultado, debe proceder del comando o del
artefacto versionado correspondiente.

> Para entender **qué hace y qué prueba cada paso** de la demo —traza
> del código, mapa contra la especificación y guía de réplica— ver
> [`docs/demo-explicada.md`](demo-explicada.md).

---

## Preparación (una vez, antes de grabar)

**Terminal.** Fuente grande (18–20 pt), fondo oscuro, ventana ~100
columnas. En un vídeo a 1080p, una terminal a tamaño normal no se lee.

**Codificación.** Antes de grabar en PowerShell:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

**Odoo: obligatorio antes de la toma 4.** La demo solo debe apuntar a
una **rama Development con datos demo**. El guardián del código debe
rechazar producción, staging y destinos no declarados. No mostrar en el
vídeo valores reales de API keys, usuarios o secretos.

Ejemplo conceptual de preparación:

```sh
export ODOO_URL="<url-development>"
export ODOO_DB="<db-development>"
export ODOO_USERNAME="<usuario-api-demo>"
export ODOO_API_KEY="<secreto-no-visible-en-video>"
```

**Navegador.** Pestaña abierta en la vista de oportunidades (`crm.lead`)
de la rama Development, con datos demo y lista para refrescar en cámara.

---

## Las seis tomas

### Toma 1 — El problema *(0:00–0:30)*

**Pantalla:** navegador, Odoo 19 Development. Oportunidad
"Renovacion contrato anual" de **Hoteles Camino (DEMO)** con 15.000 €.
Corte seco. La misma con 27.600 €.

**Qué afirma esta toma, y qué no.** Muestra **lo que está en juego**
mediante un registro demo persistente. **No afirma que un agente haya
producido ese cambio concreto**. El estado se prepara deliberadamente
con `scripts/stage_video_shot1.py`; presentarlo como «mira lo que hizo
la IA» sería atribuir causalidad que la toma no demuestra.

**Preparación del estado:**

```sh
uv run python scripts/stage_video_shot1.py --before
# grabar el estado inicial
uv run python scripts/stage_video_shot1.py --after
# refrescar y grabar el estado cambiado
```

El cliente se llama **"Hoteles Camino (DEMO)"** a propósito: si el vídeo
se comparte, nadie debe confundirlo con un cliente real.

---

### Toma 2 — El agente sin gobierno ejecuta *(0:30–1:00)*

**Pantalla:** terminal.

```sh
uv run python scripts/demo_completa.py --pausa
```

Para este tramo bastan las escenas que muestran el contraste A/C. La
evidencia de esta toma pertenece al entorno experimental controlado;
no presentarla como una escritura sobre producción ni como una
frecuencia observada en una empresa real.

---

### Toma 3 — La arquitectura *(1:00–1:45)*

**Pantalla:** diagrama de las dos zonas. Es una diapositiva explicativa,
no evidencia experimental.

Mostrar:

```text
petición
  -> interpretación probabilística
  -> retrieval / abstención
  -> contrato de skill
  -> policy + riesgo + aprobación
  -> runtime determinista
  -> adaptador ERP
  -> postcondiciones
  -> auditoría
```

Frase central: **«el LLM propone; la arquitectura autoriza; el runtime
ejecuta»**.

---

### Toma 4 — Odoo 19 Development *(1:45–2:45)* · TOMA PRINCIPAL

**Pantalla:** terminal a pantalla partida con el navegador de Odoo.

```sh
uv run python scripts/odoo_governed_demo.py --rodaje
```

**Qué se ve, en orden:**

1. Crear oportunidad (R1) → `ALLOW`. Refrescar Odoo: el registro demo
   está persistido.
2. Cambiar importe (R2) sin aprobación → `REQUIRE_APPROVAL`. Refrescar
   Odoo: el importe no ha cambiado.
3. Conceder aprobación, repetir → `ALLOW`. Refrescar Odoo: ahora sí.

Cada paso debe acompañarse de la relectura independiente. Esta toma
prueba **factibilidad end-to-end en una instancia Odoo 19 Development
con datos demo**; no forma parte del contraste confirmatorio A/B/C y no
es validación en producción.

**Regla de rodaje:** mantener continua la secuencia bloqueo → refresco →
aprobación → nueva escritura siempre que sea posible, para que la
relectura sea comprensible y no dependa de una afirmación verbal.

---

### Toma 5 — Los números *(2:45–3:40)*

**Pantalla:** dos fuentes de evidencia diferenciadas.

Primero, resultado confirmatorio:
`reports/figures/v21_h4_categories.png` — **19,0 % de mutación no
autorizada sobre 315 escenarios peligrosos del benchmark confirmatorio
sintético**, frente al objetivo prerregistrado <5 %. H4 queda **no
soportada**.

Después, stress test externo:

```sh
uv run python scripts/injection_resistance_test.py
```

Resultado acotado: **0/1.530 mutaciones no autorizadas fuera de contrato**
sobre 510 payloads de InjecAgent entregados por tres superficies. No
presentarlo como prueba de seguridad general ni como sustituto de H4.

Si la ejecución completa no cabe en el vídeo, mostrar el artefacto
versionado `data/injection_resistance_results.json` y decir que se trata
del resultado almacenado, no de una salida recreada.

---

### Toma 6 — Valor y límite *(3:40–4:20)*

**Pantalla:** `reports/figures/v21_hypotheses_forest.png`.

Claims permitidos y alineados con la memoria:

- **H1a soportada:** C no es inferior a A en STSR (+25,3 pp; margen -5 pp).
- **H1b no soportada:** no se demuestra superioridad de C sobre B
  (C−B = -1,5 pp; p=0,286).
- **H2 soportada:** C consume ~468 tokens menos que A y ~648 menos que B
  por ejecución en el brazo H2.
- **H3a soportada:** mayor estabilidad entre formulaciones (OR 9,35;
  p=2,2×10^-18).
- **H4 no soportada:** 19,0 % de mutación no autorizada sobre 315
  escenarios peligrosos del benchmark; objetivo <5 %.
- **H5 no soportada:** selective accuracy 0,589; false-reuse 0,411.
- **H6 soportada:** la abstención reduce false-reuse en 8,6 pp.
- **H7 soportada:** reconstrucción completa de auditoría +42,7 pp frente
  a A (p=2,85×10^-112), con la salvedad estructural descrita en memoria.
- **H8 descriptiva:** sensibilidad económica modelada; **no** ahorro
  monetario observado.

No resumir H4 como «más/menos seguro que A o B» sin la salvedad de que
parte de las denegaciones de los comparadores son errores de ejecución y
no detección de seguridad homologable. La formulación final debe ser:
**«H4 no alcanza el criterio prerregistrado de seguridad activa»**.

---

## Control final antes de exportar el vídeo

1. Duración final **≤5:00**.
2. Formato **MP4**.
3. Objetivo de tamaño recomendado por la guía: **≤50 MB cuando sea
   razonablemente posible**.
4. Voz del autor incluida; no es necesario aparecer en cámara.
5. No aparecen credenciales, tokens, correos, teléfonos ni datos
   identificables.
6. No se dice «observaciones reales», «escenarios reales», «peticiones
   peligrosas reales», «seguro», «inmune», «validado en producción» ni
   «ahorra X euros».
7. Para el benchmark: «observaciones experimentales / ejecuciones
   observadas sobre escenarios sintéticos».
8. Para H4: «315 escenarios peligrosos del benchmark confirmatorio».
9. Para Odoo: «Odoo 19 Development con datos demo; demostración de
   factibilidad».
10. El cierre coincide con la tesis de la memoria: **el LLM propone; la
    arquitectura autoriza; el runtime ejecuta**.
