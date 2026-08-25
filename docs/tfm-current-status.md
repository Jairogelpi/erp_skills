# ERP Agent OS — estado canónico del TFM

**Corte de evidencia:** 2026-08-23  
**Protocolo vigente:** `tfm-protocol-v2.1.2`  
**Estado de cierre:** `RUN_COMPLETED` / `CLOSURE_VALID`  
**Fuente confirmatoria:** `docs/results-v2.1.md`

Este documento existe para ofrecer una entrada inequívoca al repositorio de cara a la evaluación del TFM. Algunos documentos históricos conservan, por compatibilidad con `src/erp_agent_os/claims.py`, el marcador legacy `EVIDENCE-STATUS: no-valid-confirmatory-conclusion`. Ese marcador pertenece al contrato de claims de la era v1 y **no describe el estado científico vigente de v2.1**.

## Veredictos confirmatorios

| Hipótesis | Estado | Lectura defendible |
|---|---|---|
| H1a | Soportada | C no es inferior a A en éxito estricto de tarea. |
| H1b | No soportada | C no supera a B en éxito estricto de tarea. |
| H2 | Soportada | C consume menos tokens que A y B. |
| H3a | Soportada | C es más estable entre formulaciones lingüísticas del mismo escenario. |
| H3b | Descriptiva | Variabilidad estocástica reportada sin criterio confirmatorio. |
| H4 | No soportada | C no alcanza los criterios prerregistrados de seguridad; mutación no autorizada observada: 19,0 % sobre 315 escenarios peligrosos. |
| H5 | No soportada | El punto operativo de retrieval no alcanza los tres umbrales registrados. |
| H6 | Soportada | La abstención reduce el riesgo de reutilización incorrecta. |
| H7 | Soportada | C mejora la reconstrucción objetiva de auditoría. |
| H8 | Descriptiva | Sensibilidad de costes modelados; no representa ahorro observado. |

## Evidencia principal

- Campaña confirmatoria: **21.478 observaciones fila a fila**.
- Datos crudos: `data/protocol_v2_1/runs_v2/confirmatory_observations_v21_2d36433e861121928cceac5899ff1cf4ed346fe63250ff87956f8aba4f082c5c.jsonl`.
- Informe: `data/protocol_v2_1/confirmatory_report_v2_1_2.json`.
- Manifiesto vigente: `data/protocol_v2_1/code_freeze_manifest.json`.
- Verificación desde un clon limpio: `make verify-tfm-closure`.

## Qué se puede afirmar

1. La arquitectura gobernada es no inferior al agente directo en el endpoint principal bajo el benchmark registrado.
2. Reduce consumo de tokens frente a A y B en el brazo específico de H2.
3. Mejora estabilidad entre paráfrasis y reconstrucción de auditoría.
4. La abstención aporta valor medible reduciendo reutilización errónea.
5. La integración gobernada con Odoo 19 es técnicamente factible y se verificó mediante relecturas independientes en Development.
6. El confinamiento estructural frente a inyección explícita se sostiene en el stress test específico que reporta 0/1.530 mutaciones no autorizadas.

## Qué NO se puede afirmar

- Seguridad absoluta o riesgo cero.
- Que ERP Agent OS sea superior a herramientas tipadas en éxito de tarea.
- Que detecte de forma general peticiones peligrosas o prompt injection fuera de distribución.
- Que el retrieval actual sea adecuado para producción.
- Que exista ROI o ahorro monetario observado.
- Que el benchmark sintético equivalga a comportamiento de usuarios reales.
- Que la generación gobernada de nuevas skills cause mejoras en H1-H8; es una demostración funcional fuera del protocolo confirmatorio.

## Integración con Odoo

`docs/odoo-demo.md` documenta tres niveles de evidencia: adaptador real, flujo completo de System C con aprobación y una demo adversarial cualitativa. Las escrituras se realizaron únicamente sobre una rama **Development** con datos demo. Producción y staging se rechazan programáticamente antes de cualquier escritura.

## Regla de lectura del repositorio

Para conclusiones del TFM, el orden de precedencia es:

1. `docs/results-v2.1.md` — resultados confirmatorios vigentes.
2. `docs/tfm-closure-no-human-v2.1.md` — protocolo normativo.
3. `docs/tfm-current-status.md` — resumen ejecutivo de claims.
4. `docs/audit.md` — procedencia y defectos del instrumento.
5. Evidencia v1 — histórica/exploratoria, nunca sustituto de v2.1.
