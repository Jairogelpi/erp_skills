# Guion de defensa — documento retirado

Este fichero se conserva únicamente para no romper enlaces históricos.
Su contenido anterior mezclaba cifras exploratorias de v1 con resultados
confirmatorios de v2.1 y utilizaba terminología ambigua sobre la naturaleza
del benchmark.

**No utilizar este documento para el vídeo, la memoria ni una eventual
defensa.**

Fuentes vigentes:

1. [`docs/defensa-v2.1-final.md`](defensa-v2.1-final.md) — guion de defensa alineado con `tfm-protocol-v2.1.2`.
2. [`docs/video-guion.md`](video-guion.md) — narración final del vídeo del TFM, objetivo 4:20 y máximo 5:00.
3. [`docs/results-v2.1.md`](results-v2.1.md) — resultados confirmatorios completos.
4. [`docs/tfm-current-status.md`](tfm-current-status.md) — resumen canónico de claims.
5. [`docs/tfm-benchmark-positioning.md`](tfm-benchmark-positioning.md) — encuadre metodológico y terminología del benchmark sintético/procedural.

## Regla de terminología

- `21.478 observaciones experimentales` o `21.478 ejecuciones observadas sobre escenarios sintéticos`.
- `315 escenarios peligrosos del benchmark confirmatorio`.
- `Odoo 19 Development con datos demo; demostración de factibilidad`.
- No afirmar seguridad general, superioridad sobre tools tipadas en éxito de tarea, ahorro monetario observado ni validación en producción.

## Claims vigentes

- H1a, H2, H3a, H6 y H7: soportadas.
- H1b, H4 y H5: no soportadas.
- H3b y H8: descriptivas.
- H4: 19,0 % de mutación no autorizada sobre 315 escenarios peligrosos del benchmark; objetivo prerregistrado <5 %.
- Stress test externo InjecAgent: 0/1.530 mutaciones no autorizadas fuera de contrato; resultado acotado que no sustituye H4 ni prueba seguridad general.

La frase central de la presentación final es: **el LLM propone; la arquitectura autoriza; el runtime ejecuta**.
