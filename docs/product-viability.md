# De los resultados a un producto: qué sostiene la evidencia y qué no

> **EVIDENCE-STATUS: no-valid-confirmatory-conclusion** — marcador legacy exigido por `src/erp_agent_os/claims.py`; no describe el estado científico vigente de `tfm-protocol-v2.1.2`.

Documento de transferencia. Traduce la evidencia vigente de `tfm-protocol-v2.1.2` a afirmaciones de producto sin ampliar el alcance de los resultados. La fuente confirmatoria sigue siendo `docs/results-v2.1.md`.

## 1. Evidencia que sí puede sostener una conversación de producto

| Afirmación defendible | Evidencia | Límite |
|---|---|---|
| La arquitectura puede confinar operaciones a contratos explícitos bajo el stress test evaluado | InjecAgent: **0/1.530 mutaciones no autorizadas fuera de contrato** sobre 510 payloads × 3 superficies | No prueba seguridad general ni sustituye H4 |
| C consume menos tokens que A y B | H2: ~468 menos que A y ~648 menos que B por ejecución en el brazo registrado | Tokens ≠ ahorro monetario observado |
| C produce una ejecución más reconstruible para auditoría | H7: +42,7 pp frente a A; p=2,85×10^-112 | Parte de la ventaja es estructural porque A/B no producen todos los hechos |
| La abstención reduce reutilización incorrecta | H6: false-reuse -8,6 pp frente a la ablación | No convierte el retrieval actual en adecuado |
| La integración gobernada es factible sobre Odoo | Demo en **Odoo 19 Development con datos demo**, con bloqueo/aprobación/relectura | 2/12 skills; no producción ni réplica confirmatoria |

## 2. Evidencia que limita el producto

### Seguridad activa

H4 queda **no soportada**. C observa un **19,0 % de mutaciones no autorizadas sobre 315 escenarios peligrosos del benchmark confirmatorio**, frente al objetivo prerregistrado <5 %.

Consecuencia: no vender «detección de peticiones peligrosas», «seguridad general» ni «riesgo cero». El resultado de InjecAgent es sobre confinamiento en un stress test explícito y debe permanecer separado.

### Éxito de tarea

H1b no demuestra superioridad frente a tools tipadas: C−B = -1,5 pp; p=0,286. No vender «más precisión» o «más éxito que las tools tipadas».

### Retrieval

H5 no alcanza el punto operativo: selective accuracy 0,589 y false-reuse 0,411. El alta y descripción de skills, la calibración y la UX de aclaración siguen siendo trabajo prioritario.

### Coste

H8 es un análisis descriptivo de sensibilidad. No mide euros ahorrados en una organización. No presentar escenarios modelados como ROI observado.

## 3. Producto que sí encaja con lo medido

La lectura empresarial más defendible es un **plano de control entre un agente y el ERP**, no un nuevo agente que compita por «entender mejor».

```text
agente / LLM
   -> propuesta estructurada
   -> contrato de skill
   -> policy + riesgo + aprobación
   -> runtime determinista
   -> adaptador ERP
   -> postcondición independiente
   -> auditoría
```

El valor potencial está en centralizar la autoridad empresarial fuera del prompt: contratos versionados, permisos, aprobación, idempotencia, postcondiciones y evidencia reconstruible.

## 4. Estado del prototipo

| Capacidad | Estado | Antes de producción |
|---|---|---|
| Contratos/policy/riesgo/idempotencia/postcondiciones | Implementado en prototipo | endurecimiento y cobertura de políticas |
| Aprobación | lógica implementada | identidad, delegación, UX |
| Auditoría | append-only por superficie del prototipo | persistencia, integridad, retención |
| Odoo 19 | 2/12 skills mapeadas en Development con datos demo | ampliar catálogo, permisos y errores reales del ERP |
| Evolución de skills | propuesta + validación/sandbox + aprobación | gobierno operacional y autoría segura |
| Plataforma | prototipo reproducible | auth, multi-tenant, secretos, observabilidad, SLO, recuperación |

## 5. Prioridades de productivización

1. Corregir las categorías que fallan en H4 y volver a medir sobre una población prospectiva no reutilizada para el desarrollo.
2. Mejorar retrieval y la UX de abstención/aclaración.
3. Ampliar el mapeo de Odoo más allá de 2/12 skills.
4. Autenticación, autorización empresarial, gestión de secretos y aislamiento multi-tenant.
5. Persistencia e integridad de auditoría, retención y exportación.
6. Observabilidad, SLO, recuperación/rollback y respuesta a fallos.
7. Validación con usuarios/organizaciones y métricas económicas antes de formular claims de adopción o ROI.

## 6. Terminología de transferencia

La campaña confirmatoria contiene **21.478 observaciones experimentales procedentes de ejecuciones observadas sobre un benchmark sintético/procedural**. Estas frecuencias no se presentan como prevalencias de usuarios o empresas.

Para H4: **315 escenarios peligrosos del benchmark confirmatorio**.

Para Odoo: **Odoo 19 Development con datos demo; demostración de factibilidad**.

## 7. Conclusión de producto

> El trabajo no demuestra que ERP Agent OS haga mejor la tarea que un baseline con tools tipadas ni que detecte de forma general el peligro. Sí demuestra, bajo las condiciones registradas, propiedades medibles de eficiencia, estabilidad, abstención y trazabilidad, además de un confinamiento fuerte en el stress test externo específico y una ruta de factibilidad sobre Odoo. Esa es la frontera comercial que la evidencia permite defender hoy.
