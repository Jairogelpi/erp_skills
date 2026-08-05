# Modelo de amenazas y validez

Operacionaliza CLAUDE.md §30 (amenazas y controles) y §36 (amenazas a la
validez). Distingue lo que el sistema **controla y está probado** de lo
que **no**.

## Amenazas y controles

| Amenaza | Control implementado | Prueba | Estado |
|---|---|---|---|
| Prompt injection | Detección léxica en `validation.py`; deny antes del razonamiento de riesgo | `test_validation.py`, benchmark adversarial | ⚠️ **parcial** — léxico, ajustado al corpus plantillado |
| Tool injection / skill no registrada | `Runtime` solo ejecuta handlers registrados; `UnregisteredHandlerError` | `test_runtime.py`, property test | ✅ |
| Skill maliciosa | Ciclo de vida versionado; sin salto `DRAFT→ACTIVE`; R4 no registrable | `test_skills.py`, property test | ✅ |
| Elevación de privilegios | Deny-by-default por rol; allowlist de roles por skill | `test_policy.py`, property test de monotonía | ✅ |
| Sobrealcance (cambio masivo) | Detección léxica de alcance masivo | benchmark adversarial | ⚠️ **parcial** |
| Exfiltración | Redacción configurable de campos en la auditoría | `test_audit.py` | ⚠️ **parcial** — solo claves declaradas |
| Replay / duplicación | Clave de idempotencia; replay devuelve el resultado cacheado | `test_runtime.py`, property test | ✅ |
| Alteración de auditoría | Append-only por superficie pública (sin update/delete) en memoria y en SQL | `test_audit.py`, `test_persistence.py` | ✅ |
| Parámetros fuera de rango | Validación numérica de rango/tipo | `test_validation.py` | ⚠️ **parcial** — solo campos con límite declarado |
| Dependencia comprometida | `uv.lock` con hashes; acciones de CI ancladas a SHA inmutable | CI | ✅ |
| Operación irreversible / R4 | R4 rechazada en el esquema; detección léxica de framing irreversible | property test, benchmark | ⚠️ **parcial** en el framing textual |

**Controles no implementados:** sandbox de ejecución de código (no
aplica: no se ejecuta código generado), rate limiting distribuido
(el actual es en memoria y monoproceso), autenticación real (la clave de
API es de demo), y cifrado en reposo.

## Amenazas a la validez

### Validez interna
- El parser no es todavía un LLM real: se usa `expected_arguments` como
  "parseo perfecto". Elimina una fuente de error que un sistema real sí
  tendría.
- Estados restaurados por observación (controlado, probado).
- Caché de idempotencia por proceso: no persiste entre reinicios.

### Validez externa
- Un único ERP simulado (`FakeERPAdapter`), datos 100 % sintéticos, un
  solo idioma (español), un solo dominio de 12 skills. No se extrapola a
  despliegues reales ni a otros ERPs.

### Validez de constructo
- **La más importante:** los detectores adversariales son **léxicos** y
  están ajustados al texto **plantillado** del benchmark. La tasa de
  detección medida es "detección de patrones conocidos", no robustez
  frente a un adversario adaptativo. Reportarla como lo segundo sería
  deshonesto.
- La rúbrica de trazabilidad mide presencia de evidencia, no su calidad
  semántica.
- STSR exige estado final correcto, lo que mitiga (no elimina) el riesgo
  de confundir "salida válida" con "tarea correcta".

### Validez estadística
- Comparaciones múltiples → corrección de Holm.
- Dependencia residual entre paráfrasis de una misma intención.
- Distribuciones no normales en tokens/latencia → pruebas no
  paramétricas.
- Potencia limitada si los pares discordantes son pocos; ver
  [`experiment-protocol.md`](experiment-protocol.md) §5.

## Política de datos

Solo datos sintéticos. Sin credenciales, tokens ni datos reales en el
repositorio. `.gitignore` cubre `.env`, claves, y estado local de MCP;
las reglas previenen inclusión accidental ordinaria pero no eliminan un
secreto ya publicado en otro sitio.
