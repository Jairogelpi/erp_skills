# Plan de rodaje — vídeo de competición 4:30

## Entregable

- Duración objetivo: 4:30; rechazo interno de cualquier exportación > 4:50.
- 1920×1080, 25 o 30 fps, H.264, audio AAC 48 kHz.
- YouTube en oculto; entregar el enlace en el fichero solicitado por UCM.
- Narrativa: método primero; la demo es evidencia visual y no sustituye el
  experimento.

## Material que debe estar preparado

1. `reports/video/01-method.svg` — diseño v2.
2. `reports/video/02-architecture.svg` — zona probabilística/determinista.
3. `reports/video/03-odoo-proof.svg` — secuencia de prueba Odoo.
4. `reports/video/04-results.svg` — v2 pendiente y v1 exploratorio.
5. `reports/video/05-limitations.svg` — límites y resultado negativo.
6. Instancia Odoo de desarrollo con datos sintéticos y estado conocido.
7. Cuenta/rol de demo sin secretos visibles.

## Orden de rodaje

### Toma 1 — Cámara, 0:00–0:50

Grabar riesgo y pregunta de investigación. Plano medio, mirada a cámara,
teleprompter a la altura del objetivo. Dos versiones completas; conservar la
más natural, no montar una frase palabra a palabra.

### Toma 2 — Voz y gráficos, 0:50–2:30

Narrar método, freeze y arquitectura sobre los SVG. Capturar audio continuo con
cinco segundos de silencio ambiente al inicio y final.

### Toma 3 — Odoo continua, 2:30–3:05

Grabar en una única toma:

1. estado inicial visible;
2. R1 ejecutada y relectura;
3. R2 sin aprobación, decisión `REQUIRE_APPROVAL` y relectura sin cambio;
4. aprobación;
5. R2 ejecutada y relectura final.

El rótulo `DEMOSTRACIÓN ODOO · NO RESULTADO EXPERIMENTAL` permanece visible.
Si falla cualquier paso, reiniciar el estado y repetir toda la toma; no pegar
resultados de sesiones distintas.

### Toma 4 — Voz y resultados, 3:05–4:05

Grabar primero la frase `V2 está pendiente`. Después mostrar solo estimaciones
v1 con la etiqueta `EXPLORATORIO`. El 3,3 % ocupa un plano propio. El 0/1.530
solo aparece junto a `STRESS EXPLORATORIO · CONFINAMIENTO POR TRES CANALES ·
NO ADAPTATIVO`.

### Toma 5 — Cámara y cierre, 4:05–4:30

Límites a cámara; cambio a fondo limpio para el cierre literal:

> El modelo propone. El contrato decide.

## Plan de edición

| Tramo | Imagen | Audio | Rótulo obligatorio |
|---|---|---|---|
| 0:00–0:25 | Odoo/riesgo | cámara | `RIESGO ERP` |
| 0:25–0:50 | A/B/C | cámara | `PREGUNTA DE INVESTIGACIÓN` |
| 0:50–1:25 | 01-method | voz | `V2 · 120×3×3` |
| 1:25–1:55 | freeze | voz | `UNA SOLA MIRADA` |
| 1:55–2:30 | 02-architecture | voz | `POSTCONDICIONES EJECUTADAS` |
| 2:30–3:05 | Odoo continua | voz/directo | `DEMOSTRACIÓN` |
| 3:05–3:40 | 04-results | voz | `V2 PENDIENTE` / `EXPLORATORIO` |
| 3:40–4:05 | límites adversariales | voz | `3,3 %` y alcance del cero |
| 4:05–4:22 | 05-limitations | cámara | `LÍMITES` |
| 4:22–4:30 | logo | cámara | frase final |

## Checklist antes de exportar

- [ ] Cronómetro desde primer sonido hasta último fotograma ≤ 4:50.
- [ ] Ningún número v1 aparece sin `EXPLORATORIO` en el mismo plano.
- [ ] `V2 PENDIENTE` sigue visible si no existe resultado validado.
- [ ] Odoo lleva etiqueta `DEMOSTRACIÓN`.
- [ ] El 3,3 % se presenta como resultado negativo.
- [ ] El 0/1.530 lleva `STRESS EXPLORATORIO · CONFINAMIENTO POR TRES CANALES`
  y `NO ADAPTATIVO`.
- [ ] No se afirma acuerdo humano; no hay segundo anotador disponible.
- [ ] Sin claves, correos, nombres reales, URL privada o notificaciones.
- [ ] Subtítulos revisados manualmente, contraste y tamaño legibles en móvil.
- [ ] Audio sin clipping, ruido o música por encima de la voz.
- [ ] Vídeo visto completo desde el enlace oculto de YouTube.
