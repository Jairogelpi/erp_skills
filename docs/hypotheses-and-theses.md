# Hipótesis, evidencia y tesis defendibles de ERP Agent OS

Este documento resume las conclusiones vigentes de
`tfm-protocol-v2.1.2`. La fuente de resultados completa sigue siendo
`docs/results-v2.1.md`; el resumen ejecutivo de claims está en
`docs/tfm-current-status.md`.

## Población experimental

ERP-Skills-Bench-Proc v2.1 es un **benchmark sintético/procedural**.
La campaña confirmatoria contiene **21.478 observaciones experimentales
procedentes de ejecuciones observadas sobre escenarios sintéticos**.
El diseño proporciona verdad de referencia conocida por construcción y
control del estado inicial, pero no se presenta como una muestra
representativa de usuarios o empresas.

## Matriz confirmatoria

| Hipótesis | Pregunta | Resultado | Estado |
|---|---|---|---|
| H1a | ¿C mantiene éxito frente a A? | C−A = +25,3 pp; no inferioridad frente a margen -5 pp | **Soportada** |
| H1b | ¿C supera a B en éxito? | C−B = -1,5 pp; p=0,286 | **No soportada** |
| H2 | ¿C reduce consumo de inferencia? | ~468 tokens menos que A y ~648 menos que B | **Soportada** |
| H3a | ¿C es estable entre formulaciones? | OR 9,35; p=2,2×10^-18 | **Soportada** |
| H3b | ¿Qué variabilidad estocástica presenta? | Resultado reportado sin criterio direccional | **Descriptiva** |
| H4 | ¿Evita mutaciones no autorizadas en la población peligrosa? | 19,0 % sobre 315 escenarios peligrosos del benchmark; objetivo <5 % | **No soportada** |
| H5 | ¿El retrieval alcanza el punto operativo? | selective accuracy 0,589; false-reuse 0,411 | **No soportada** |
| H6 | ¿La abstención reduce reutilización incorrecta? | false-reuse -8,6 pp frente a ablación | **Soportada** |
| H7 | ¿La ejecución puede reconstruirse objetivamente? | +42,7 pp frente a A; p=2,85×10^-112 | **Soportada** |
| H8 | ¿Qué ocurre bajo distintos supuestos de coste? | rejilla de sensibilidad | **Descriptiva; no ahorro observado** |

## Tesis que sí resisten la evidencia

### T1 — Frontera de autoridad implementable

Es técnicamente viable separar interpretación probabilística de
autorización y ejecución determinista mediante contratos versionados,
policy/risk, aprobación, idempotencia, postcondiciones y auditoría.

### T2 — La gobernanza aporta propiedades medibles, pero no gana en todo

Bajo las condiciones registradas, C mantiene éxito frente a A, consume
menos tokens, es más estable entre formulaciones, se beneficia de la
abstención y produce una traza más reconstruible. **No** se demuestra
superioridad de éxito frente a B.

### T3 — Confinamiento y detección son problemas distintos

H4 no alcanza el criterio prerregistrado de seguridad activa: se observa
19,0 % de mutación no autorizada sobre 315 escenarios peligrosos del
benchmark confirmatorio.

Separadamente, el stress test externo basado en InjecAgent observa
**0/1.530 mutaciones no autorizadas fuera de contrato** bajo las
superficies de ataque evaluadas. Ese resultado sostiene una afirmación
acotada de confinamiento en dicho stress test; no prueba seguridad
general ni sustituye H4.

### T4 — El retrieval es un cuello de botella y la abstención es una
capacidad

H5 falla el punto operativo registrado. H6, en cambio, muestra que no
forzar una skill reduce el riesgo de reutilización incorrecta. En un
sistema con efectos persistentes, pedir aclaración puede ser preferible
a maximizar cobertura.

### T5 — La trazabilidad es operacionalmente interpretable

H7 mide reconstrucción de siete hechos observables de la ejecución. La
interpretabilidad relevante aquí no es explicar pesos internos del LLM,
sino poder reconstruir petición, skill/versión, argumentos, política,
aprobación, handler, postcondición y evidencia final.

### T6 — Integración ERP: factibilidad, no confirmación

La ruta gobernada se demostró sobre una instancia **Odoo 19 Development
con datos demo**: escritura R1, bloqueo R2 sin aprobación, relectura
independiente, aprobación y posterior escritura. La integración actual
mapea 2/12 skills. Esto demuestra factibilidad end-to-end, no una réplica
del experimento A/B/C ni validación en producción.

## Lo que no debe afirmarse

- «ERP Agent OS es seguro» o «riesgo cero».
- superioridad universal sobre agentes o tools tipadas;
- que las frecuencias del benchmark equivalgan a prevalencias en
  organizaciones;
- que H5 demuestre un retrieval listo para producción;
- ahorro económico observado;
- que 0/1.530 invalide o reinterprete H4;
- que la demo de Odoo sea producción;
- que la evolución gobernada de skills cause mejoras en H1–H8.

## Tesis final, en una frase

> Bajo ERP-Skills-Bench-Proc v2.1 y las condiciones registradas, separar
> interpretación probabilística de autoridad determinista aporta
> eficiencia, estabilidad, abstención útil y trazabilidad medibles, pero
> no demuestra superioridad sobre tools tipadas en éxito de tarea ni
> resuelve por sí sola la detección de peligro o el retrieval.
