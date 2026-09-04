# Hipótesis, evidencia y tesis defendibles de ERP Agent OS

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** — marcador legacy exigido por `src/erp_agent_os/claims.py`; no describe el estado científico vigente de `tfm-protocol-v2.1.2`.

Este documento resume las conclusiones vigentes de `tfm-protocol-v2.1.2`. La fuente de resultados completa sigue siendo `docs/results-v2.1.md`; el resumen ejecutivo de claims está en `docs/tfm-current-status.md`.

## Población experimental

ERP-Skills-Bench-Proc v2.1 es un **benchmark sintético/procedural**. La campaña confirmatoria contiene **21.478 observaciones experimentales procedentes de ejecuciones observadas sobre escenarios sintéticos**. El diseño proporciona verdad de referencia conocida por construcción y control del estado inicial, pero no se presenta como una muestra representativa de usuarios o empresas.

## Hipótesis confirmatorias

### H1 — Éxito estricto de tarea

- **H1a soportada:** C no es inferior a A; C−A = +25,3 pp frente a margen -5 pp.
- **H1b no soportada:** C no supera a B; C−B = -1,5 pp; p=0,286.

### H2 — Consumo de tokens

**Soportada.** C consume aproximadamente 468 tokens menos que A y 648 menos que B por ejecución en el brazo registrado.

### H3 — Estabilidad

- **H3a soportada:** OR 9,35; p=2,2×10^-18 entre formulaciones lingüísticas.
- **H3b descriptiva:** variabilidad estocástica reportada sin criterio direccional confirmatorio.

### H4 — Seguridad activa

**No soportada.** C observa un **19,0 % de mutaciones no autorizadas sobre 315 escenarios peligrosos del benchmark confirmatorio**, frente al objetivo prerregistrado <5 %. El resultado no debe resumirse como «A/B son más seguros» porque parte de sus `DENY` procede de errores de ejecución.

### H5 — Retrieval selectivo

**No soportada.** Selective accuracy 0,589 y false-reuse 0,411; el punto operativo registrado no se alcanza.

### H6 — Abstención

**Soportada.** La abstención reduce false-reuse en 8,6 puntos porcentuales frente a la ablación sin abstención.

### H7 — Reconstrucción de auditoría

**Soportada.** C mejora +42,7 pp frente a A; p=2,85×10^-112. La salvedad estructural se declara: A/B no producen todos los hechos de gobernanza que C registra. Se interpreta como trazabilidad/explicabilidad operacional.

### H8 — Sensibilidad económica

**Descriptiva.** Rejilla de escenarios modelados; no constituye ahorro monetario observado.

## Tesis que sí resisten la evidencia

### T1 — Frontera de autoridad implementable

Es técnicamente viable separar interpretación probabilística de autorización y ejecución determinista mediante contratos versionados, policy/risk, aprobación, idempotencia, postcondiciones y auditoría.

### T2 — La gobernanza aporta propiedades medibles, pero no gana en todo

Bajo las condiciones registradas, C mantiene éxito frente a A, consume menos tokens, es más estable entre formulaciones, se beneficia de la abstención y produce una traza más reconstruible. **No** se demuestra superioridad de éxito frente a B.

### T3 — Confinamiento y detección son problemas distintos

H4 no alcanza el criterio prerregistrado de seguridad activa. Separadamente, el stress test externo basado en InjecAgent observa **0/1.530 mutaciones no autorizadas fuera de contrato** bajo las superficies de ataque evaluadas. Ese resultado sostiene una afirmación acotada de confinamiento en dicho stress test; no prueba seguridad general ni sustituye H4.

### T4 — El retrieval es un cuello de botella y la abstención es una capacidad

H5 falla el punto operativo registrado. H6, en cambio, muestra que no forzar una skill reduce el riesgo de reutilización incorrecta.

### T5 — La trazabilidad es operacionalmente interpretable

H7 mide reconstrucción de hechos observables de la ejecución. La interpretabilidad relevante aquí no es explicar pesos internos del LLM, sino poder reconstruir petición, skill/versión, argumentos, política, aprobación, handler, postcondición y evidencia final.

### T6 — Integración ERP: factibilidad, no confirmación

La ruta gobernada se demostró sobre una instancia **Odoo 19 Development con datos demo**: escritura R1, bloqueo R2 sin aprobación, relectura independiente, aprobación y posterior escritura. La integración actual mapea 2/12 skills. Esto demuestra factibilidad end-to-end, no una réplica del experimento A/B/C ni validación en producción.

## Lo que no debe afirmarse

- «ERP Agent OS es seguro» o «riesgo cero».
- superioridad universal sobre agentes o tools tipadas;
- que las frecuencias del benchmark equivalgan a prevalencias en organizaciones;
- que H5 demuestre un retrieval listo para producción;
- ahorro económico observado;
- que 0/1.530 invalide o reinterprete H4;
- que la demo de Odoo sea producción;
- que la evolución gobernada de skills cause mejoras en H1–H8.

## Tesis final, en una frase

> Bajo ERP-Skills-Bench-Proc v2.1 y las condiciones registradas, separar interpretación probabilística de autoridad determinista aporta eficiencia, estabilidad, abstención útil y trazabilidad medibles, pero no demuestra superioridad sobre tools tipadas en éxito de tarea ni resuelve por sí sola la detección de peligro o el retrieval.
