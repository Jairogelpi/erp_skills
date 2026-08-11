# Rúbrica de trazabilidad

Operacionaliza CLAUDE.md §20 ("La trazabilidad se puntuará con una
rúbrica ponderada y auditable, no por volumen de logs"). Se aplica por
ejecución; la hoja de comprobación se conserva junto a los resultados.

Cada componente exige **evidencia concreta verificable en la traza**. Si
la evidencia no existe o no es comprobable, el componente puntúa **cero**
— no hay crédito parcial por "algo se registró".

| # | Componente | Peso | Evidencia requerida | Campo de la traza |
|---|---|---|---|---|
| 1 | Petición e identidad del caso | 10 % | `correlation_id` presente y generado por el servidor; `request_id` del caso | `AuditEvent.correlation_id` |
| 2 | Interpretación y argumentos | 15 % | Intención propuesta y argumentos normalizados, con campos ausentes explícitos | `IntentProposal.intent`, `.arguments`, `.missing_fields` |
| 3 | Candidatas y justificación de selección/abstención | 15 % | Skill seleccionada o motivo de abstención registrado | `AuditEvent.skill_id`, `AbstentionEvent.reasons` |
| 4 | Decisión de política y permisos | 15 % | Decisión, `risk_score` y razones legibles | `AuditEvent.decision`, `.risk_score`, `.reasons` |
| 5 | Versión de skill/handler y entrada normalizada | 15 % | Versión exacta ejecutada e idempotency key | `AuditEvent.skill_version`, `.idempotency_key` |
| 6 | Resultado y efectos observados | 15 % | Salida (redactada) y marca de replay idempotente | `AuditEvent.output`, `.idempotent_replay` |
| 7 | Evidencia de postcondiciones, aprobación o bloqueo | 15 % | Resultado de postcondiciones, o la aprobación/denegación que impidió ejecutar | `AuditEvent.postconditions_met`, `Approval` |

**Total:** 100 %.

## Aplicación

1. Por cada ejecución del test, un evaluador (o el evaluador
   determinista) marca cada componente como presente/ausente.
2. La puntuación de la ejecución es la suma de los pesos presentes.
3. Se reportan la media, el IC del 95 % **y el desglose por componente**
   — un sistema puede puntuar alto en total y aun así fallar
   sistemáticamente un componente crítico, y eso debe verse.

## Limitación declarada

La rúbrica mide **presencia de evidencia**, no su corrección semántica.
Un `reasons` presente pero poco informativo puntúa igual que uno
excelente. Evaluar la calidad del contenido requeriría juicio humano
sobre una muestra; no se afirma haberlo hecho.
