# Memoria del TFM — nota de versión final

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** — marcador legacy exigido por `src/erp_agent_os/claims.py`; no describe el estado científico vigente de `tfm-protocol-v2.1.2`.

La memoria oficial de entrega se genera y entrega como PDF independiente
con el nombre:

`Jairo_Gelpi_Moreno_TFM_ERP_Agent_OS_FINAL.pdf`

Este fichero Markdown **ya no se utiliza como memoria canónica**. La
versión anterior se conserva íntegramente en el historial de Git, pero se
retira de `main` para evitar que un borrador histórico con formulaciones y
resultados superseded se confunda con el documento final que recibe el
tutor.

## Fuentes canónicas del repositorio

1. `docs/results-v2.1.md` — resultados confirmatorios completos.
2. `docs/tfm-closure-no-human-v2.1.md` — protocolo normativo.
3. `docs/tfm-current-status.md` — matriz vigente de claims.
4. `docs/tfm-benchmark-positioning.md` — encuadre metodológico del benchmark sintético/procedural.
5. `docs/defensa-v2.1-final.md` — explicación final de resultados y límites.
6. `docs/video-guion.md` — guion final del vídeo de máximo 5 minutos.

## Encuadre del TFM

ERP Agent OS es un **proyecto técnico aplicado con desarrollo de una solución software y evaluación experimental**. ERP-Skills-Bench-Proc v2.1 es un instrumento de medida sintético/procedural; no es el objeto del TFM como ejercicio de análisis de dataset.

La campaña confirmatoria contiene **21.478 observaciones experimentales procedentes de ejecuciones observadas sobre escenarios sintéticos**. Su diseño maximiza control experimental, igualdad de estado inicial y reproducibilidad, a cambio de limitar validez externa. No se presentan estas frecuencias como prevalencias de usuarios o empresas.

## Claims vigentes

| Hipótesis | Estado | Resultado central |
|---|---|---|
| H1a | Soportada | C no es inferior a A; +25,3 pp frente a margen -5 pp |
| H1b | No soportada | C−B = -1,5 pp; p=0,286 |
| H2 | Soportada | C consume ~468 tokens menos que A y ~648 menos que B |
| H3a | Soportada | OR 9,35; p=2,2×10^-18 |
| H3b | Descriptiva | variabilidad reportada sin criterio direccional |
| H4 | No soportada | 19,0 % de mutación no autorizada sobre 315 escenarios peligrosos del benchmark; objetivo <5 % |
| H5 | No soportada | selective accuracy 0,589; false-reuse 0,411 |
| H6 | Soportada | false-reuse -8,6 pp con abstención |
| H7 | Soportada | reconstrucción completa +42,7 pp frente a A; p=2,85×10^-112 |
| H8 | Descriptiva | sensibilidad económica modelada; no ahorro observado |

## Evidencia externa y operacional

- **InjecAgent:** 0/1.530 mutaciones no autorizadas fuera de contrato en el stress test específico. Es evidencia de confinamiento en ese diseño de ataque, no prueba de seguridad general y no sustituye H4.
- **Odoo 19:** demostración de factibilidad end-to-end exclusivamente en **Development con datos demo**. La ruta gobernada muestra escritura R1, bloqueo R2 sin aprobación, relectura independiente, aprobación y nueva escritura. Cobertura actual: 2/12 skills.

## Regla de interpretación

La conclusión final no es que la arquitectura sea universalmente superior o segura. Bajo las condiciones registradas, la gobernanza aporta propiedades medibles de eficiencia, estabilidad, abstención y trazabilidad, mientras que la detección activa de peligro y el retrieval siguen siendo límites abiertos.

La memoria PDF de entrega incorpora esta formulación y constituye el documento que debe evaluarse junto con el repositorio y el vídeo.
