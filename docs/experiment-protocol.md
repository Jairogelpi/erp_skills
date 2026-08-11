# Protocolo experimental

Operacionaliza CLAUDE.md §§6, 19–21 (P1.3/P1.4 de la hoja de ruta). Este
documento se congela antes de ejecutar el test final; cualquier cambio
posterior es exploratorio y se etiqueta como tal.

## 1. Diseño

- **Unidad emparejada:** `request_id` × estado inicial de `FakeERP` ×
  repetición. A, B y C ejecutan la misma unidad con restauración completa
  del estado antes de cada observación.
- **Tamaño:** 120 casos de test × 3 sistemas × 3 repeticiones = **1.080
  ejecuciones**.
- **Aleatorización:** orden de ejecución aleatorizado con semilla
  registrada; el manifiesto de congelación guarda la semilla.
- **Endpoint primario:** Strict Task Success Rate (STSR) — acción
  correcta ∧ argumentos válidos ∧ permisos respetados ∧ estado final
  esperado ∧ sin efectos laterales.

## 2. Variables de control (idénticas en A/B/C)

Modelo, proveedor, versión y configuración; temperatura; límite de
tokens; timeout; presupuesto de reintentos; máximo de pasos; roles y
permisos; evaluador determinista; estados sintéticos; claves de
idempotencia; política de restauración. Las diferencias arquitectónicas
necesarias (C tiene recuperación y verificación; A y B no) se versionan
y se reportan explícitamente.

> **Estado actual:** existen tres `LLMClient` reales intercambiables
> (`groq_client.py`, `gemini_client.py`, `openrouter_client.py`),
> seleccionables vía `scripts/run_experiment.py --real-llm --provider
> {groq,gemini,openrouter}`. El `DeterministicStubClient` sigue sin
> satisfacer esta sección — se usa solo para la línea base de
> aislamiento arquitectónico (`is_confirmatory_run: false`), nunca para
> resultados confirmatorios. La ejecución confirmatoria completada
> (`data/experiment_results.json`, `manifest.selector:
> "OpenRouterClient"`) usó `openai/gpt-oss-20b:free` vía OpenRouter,
> tras que Groq y Gemini agotaran sus cuotas gratuitas respectivas
> (detalle en `docs/results.md`). D-03 exige un único proveedor
> **dentro** de una ejecución, no un proveedor fijo entre ejecuciones.

## 3. Contrastes por hipótesis

| H | Endpoint | Prueba | Efecto | Función |
|---|---|---|---|---|
| H1 | STSR, C vs A | No inferioridad, margen −5 pp; McNemar | Diferencia de proporciones + IC bootstrap | `mcnemar`, `paired_proportion_difference` |
| H2 | Tokens totales | Bootstrap emparejado sobre la media por caso | Diferencia de medias + IC | `paired_mean_difference` |
| H3 | Consistencia entre 3 repeticiones | Q de Cochran → post hoc, Holm | Diferencia de proporciones | `cochran_q`, `holm_correction` |
| H4 | False allow / detección preejecución | McNemar sobre casos peligrosos | Odds ratio emparejado | `mcnemar`, `odds_ratio` |
| H5 | Top-1/Top-3, coverage, selective accuracy | Descriptivo + IC bootstrap | — | `paired_proportion_difference` |
| H6 | Abstención y false-reuse risk | Curva precisión-cobertura | — | — |
| H7 | Rúbrica de trazabilidad (0–1 por ejecución) | Descriptivo: media por sistema | — | `traceability.score_governed_execution`/`score_ungoverned_execution` |
| H8 | Coste modelado | Análisis de sensibilidad, no confirmatorio | — | — |

Todas las funciones están implementadas y testeadas en
`src/erp_agent_os/statistics.py` / `tests/test_statistics.py`. **H2 y H7
se ejecutaron por primera vez con datos reales en la unidad 30** (§
bitácora de `CLAUDE.md`); H7 se reporta hoy como descriptivo (media por
sistema), sin la prueba emparejada con tamaño de efecto que la tabla
original preveía — pendiente si el presupuesto de tiempo lo permite,
señalado aquí en vez de reclamarlo hecho.

## 4. Regla de decisión

- IC del 95 % en todos los contrastes.
- Corrección de Holm en toda familia post hoc.
- H1 se acepta si el límite inferior del IC de la diferencia C−A supera
  −5 puntos porcentuales.
- Los resultados nulos o desfavorables se publican igual (CLAUDE.md
  §35.18). No se reinterpretan post hoc como exploratorios favorables.

## 5. Potencia

Con 120 casos emparejados y α = 0,05 bilateral, McNemar tiene potencia
≈ 0,80 para detectar una diferencia cuando los pares discordantes son
≈ 25 y el desequilibrio entre ellos es ≈ 70/30. **Este cálculo asume
independencia entre paráfrasis**, supuesto que el diseño mitiga (cada
caso es su propio grupo) pero no elimina: las formulaciones de una misma
intención comparten plantilla y vocabulario. Si la tasa observada de
pares discordantes es muy inferior, el estudio quedará infrapotenciado
para esa hipótesis y así debe reportarse, en lugar de presentar el
resultado no significativo como evidencia de equivalencia.

## 6. Amenazas a la validez

Ver [`docs/threat-model.md`](threat-model.md) §Validez. En resumen, las
que este protocolo no puede eliminar:

- **Constructo:** los detectores adversariales de `validation.py` son
  léxicos y están ajustados al texto plantillado del benchmark; miden
  "detección de patrones conocidos", no robustez general.
- **Externa:** un único ERP simulado, datos sintéticos, un solo idioma,
  un solo modelo. No se extrapola a despliegues reales.
- **Interna:** el parser no es todavía un LLM real; usar
  `expected_arguments` como parseo perfecto elimina una fuente de error
  que un sistema real sí tendría, y favorece a los tres sistemas por
  igual pero no de forma neutral respecto a C (cuya recuperación depende
  del texto, no de los argumentos).
- **Estadística:** comparaciones múltiples (mitigadas con Holm),
  dependencia residual entre paráfrasis, y distribuciones no normales en
  tokens/latencia (mitigadas usando pruebas no paramétricas).

## 6b. Rúbrica de trazabilidad

Ver [`docs/traceability-rubric.md`](traceability-rubric.md): siete
componentes ponderados, cada uno exigiendo evidencia verificable en la
traza; la ausencia puntúa cero. No se mide por volumen de logs.

## 7. Congelación

Antes del test se congelan y se registran con hash: partición de test,
anotaciones, catálogo de 12 skills, prompts, configuración de proveedor,
semillas y este plan de análisis. El manifiesto vive junto a los
resultados y no se reescribe.
