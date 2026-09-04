# Las demos, explicadas: qué prueban y qué no prueban

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** — marcador legacy exigido por `src/erp_agent_os/claims.py`; no describe el estado científico vigente de `tfm-protocol-v2.1.2`.

Este documento describe las demostraciones utilizadas para comunicar ERP Agent OS. No introduce resultados nuevos. Para cifras confirmatorias, usar `docs/results-v2.1.md`; para claims de entrega, usar `docs/tfm-current-status.md`.

## 1. Tres clases de evidencia que no deben mezclarse

### A. Comparación confirmatoria A/B/C

- Entorno experimental controlado.
- ERP-Skills-Bench-Proc v2.1: benchmark sintético/procedural.
- **21.478 observaciones experimentales** procedentes de ejecuciones observadas sobre escenarios sintéticos.
- Mismo modelo/proveedor, tarea, rol, estado inicial y evaluador para los comparadores según el protocolo.
- Objetivo: medir H1–H8 con validez interna y reproducibilidad.

### B. Stress test externo InjecAgent

- 510 payloads externos.
- Tres superficies de entrega controladas por el atacante en el test.
- Resultado: **0/1.530 mutaciones no autorizadas fuera de contrato**.
- Interpretación permitida: evidencia de confinamiento bajo ese modelo de ataque explícito.
- Interpretación prohibida: «el sistema es seguro», «riesgo cero» o que el stress test sustituye H4.

### C. Odoo 19 Development

- Instancia real del software Odoo 19, **rama Development con datos demo**.
- Objetivo: demostrar factibilidad de integración end-to-end.
- No forma parte de la inferencia estadística A/B/C.
- No es producción.
- Cobertura actual: 2/12 skills mapeadas.

## 2. Demo comparativa A/B/C

Comando:

```sh
make demo-preflight
make demo-product
```

La API comparativa se mantiene sobre el adaptador experimental. Esto es deliberado: permite reiniciar el mismo estado y comparar A, B y C sin ruido de red ni diferencias de una instancia externa.

Invariantes de presentación:

1. No construir una puntuación global artificial.
2. Si A/B no producen policy, aprobación, versión de skill o postcondición, mostrar ausencia de esa capacidad; no inferirla.
3. Puntuar el efecto/estado final, no lo convincente que resulte el texto del agente.
4. Mantener la ruta Odoo fuera de esta API comparativa.

## 3. Demo gobernada sobre Odoo 19 Development

Comando:

```sh
uv run python scripts/odoo_governed_demo.py
```

Secuencia:

```text
R1
 -> ALLOW
 -> escritura
 -> relectura independiente
 -> postcondición verificada

R2 sin aprobación
 -> REQUIRE_APPROVAL
 -> relectura independiente
 -> estado sin cambio

aprobación concedida
 -> ALLOW
 -> escritura
 -> nueva relectura
 -> cambio verificado
```

La relectura independiente es esencial. Una respuesta API satisfactoria no se toma como prueba suficiente del estado final.

### Qué demuestra

- que la arquitectura puede alcanzar un ERP externo mediante un adaptador;
- que una operación permitida puede persistirse;
- que una decisión no ejecutable puede dejar el ERP sin cambios;
- que la misma operación puede ejecutarse tras aprobación;
- que las postcondiciones se pueden comprobar leyendo de nuevo el ERP.

### Qué no demuestra

- superioridad estadística frente a A/B;
- cobertura completa de Odoo;
- readiness de producción;
- comportamiento con datos de clientes;
- seguridad general.

## 4. Resultado de seguridad que debe acompañar cualquier demo

La demo no debe hacer desaparecer el principal resultado negativo.

**H4:** en **315 escenarios peligrosos del benchmark confirmatorio**, C observa un **19,0 % de mutaciones no autorizadas**, frente al criterio prerregistrado <5 %. H4 queda no soportada.

El stress test InjecAgent responde otra pregunta. El 0/1.530 muestra que, en las superficies explícitas evaluadas, no se observó escritura fuera del contrato. **Confinamiento y detección no son equivalentes.**

## 5. Resultado completo que puede mostrarse en la demo

| Hipótesis | Estado | Mensaje corto permitido |
|---|---|---|
| H1a | Soportada | C no es inferior a A en STSR. |
| H1b | No soportada | C no supera a B en STSR. |
| H2 | Soportada | C consume menos tokens que A y B. |
| H3a | Soportada | C es más estable entre formulaciones. |
| H3b | Descriptiva | Variabilidad estocástica reportada. |
| H4 | No soportada | 19,0 % en 315 escenarios peligrosos del benchmark; objetivo <5 %. |
| H5 | No soportada | Retrieval por debajo del punto operativo. |
| H6 | Soportada | La abstención reduce false-reuse. |
| H7 | Soportada | Mayor reconstrucción de auditoría, con salvedad estructural. |
| H8 | Descriptiva | Sensibilidad económica modelada; no ahorro observado. |

## 6. Escena inicial de 15.000 -> 27.600 €

`scripts/stage_video_shot1.py` prepara deliberadamente ambos estados para ilustrar el tipo de efecto persistente que motiva el TFM. Esa escena no es una ejecución experimental de un agente y no debe narrarse como si el agente hubiera causado ese cambio concreto.

La evidencia de ejecución está en los comandos y artefactos identificados en las secciones anteriores.

## 7. Terminología para vídeo y memoria

Usar:

- «observaciones experimentales»;
- «ejecuciones observadas sobre escenarios sintéticos»;
- «315 escenarios peligrosos del benchmark confirmatorio»;
- «Odoo 19 Development con datos demo»;
- «demostración de factibilidad»;
- «consume menos tokens».

No usar lenguaje que sugiera que la población sintética procede de usuarios/empresas, que la demo se ejecuta en producción o que H8 mide un ahorro monetario observado.
