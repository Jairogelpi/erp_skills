# Auditoría del instrumento de medida

Este documento registra las auditorías hechas **sobre el propio aparato de
evaluación**, no sobre el sistema evaluado. Existe porque cinco rondas
sucesivas encontraron cinco defectos reales, y todos compartían la misma
forma: **código que pasaba en silencio**, no código que fallaba a gritos.

## Por qué importa para el TFM

Un TFM experimental se defiende con números. Si el instrumento que produce
esos números tiene un fallo, el error no aparece como un test rojo: aparece
como un resultado publicado que nadie puede reproducir. Las secciones §29
(pruebas de propiedades) y §36 (amenazas a la validez) exigen precisamente
este tipo de escrutinio.

## Defectos encontrados y corregidos

| # | Defecto | Cómo se detectó | Impacto si no se corrige |
|---|---|---|---|
| 1 | **Fuga en el test congelado**: 10 textos idénticos en `DEVELOPMENT` y `FINAL_TEST` (8,3 % del test) | Inspección del dataset | El test no mide generalización; los resultados no son defendibles |
| 2 | **`validate_case_groups` tautológico**: con grupos de tamaño 1 no puede fallar nunca | Análisis del validador | Daba luz verde falsa mientras la fuga existía |
| 3 | **Conjunto 5 de STSR vacío**: «sin efectos laterales» devolvía `True` incondicionalmente | Conteo de fallos por conjunto en 1.080 observaciones (0 fallos) | STSR era una conjunción de 3 presentada como de 5 |
| 4 | **Conjunto 4 duplicaba al 1**: ambos comprobaban la decisión, ninguno el estado | Lectura del código de métricas | «Estado esperado» no medía estado |
| 5 | **Pseudo-replicación**: 360 observaciones tratadas como independientes siendo 120 casos × 3 copias idénticas | Comprobación empírica: 360/360 grupos daban resultados idénticos | IC 1,7× más estrechos; *p* 15 órdenes de magnitud menores |

Las conclusiones del experimento **sobrevivieron a las cinco correcciones
sin cambiar de signo**. Eso es evidencia de robustez, no de que las
correcciones fueran innecesarias: una métrica que acierta por accidente
sigue estando rota.

## Mutation testing

Se rompió el código deliberadamente y se comprobó si la suite lo detecta.
Un mutante que **sobrevive** señala un hueco: hay lógica que ningún test
verifica.

**Resultado: 23 mutantes inyectados, 23 muertos** tras cerrar los dos huecos
que la primera pasada reveló.

Mutantes probados, por módulo:

- **`policy`** — chequeo de rol desactivado · hallazgos bloqueantes ignorados · R3 permitido en vez de simulado
- **`runtime`** — caché de idempotencia puenteada · handler no registrado tolerado
- **`skills`** — R4 aceptada · salto `DRAFT→ACTIVE` permitido
- **`adapters`** — allowlist de modelos desactivada
- **`metrics`** — conjunción STSR debilitada a `OR` · ignora efectos laterales · ignora estado esperado · ignora permisos · `false_allow` nunca contado · colapso de repeticiones sin mayoría · `false_reuse` siempre cero · exactitud selectiva inflada a 1 · segmentación falseada
- **`dataset`** — validador de fuga anulado
- **`freeze`** — detector de deriva anulado
- **`validation`** — patrones de inyección eliminados
- **`postconditions`** — postcondición desconocida pasa en silencio
- **`statistics`** — Holm anulada · McNemar sin corrección de continuidad · bootstrap sin remuestreo
- **`agreement`** — kappa sin corrección por azar

### Los dos huecos que reveló

| Mutante superviviente | Por qué no lo detectaba nadie | Impacto |
|---|---|---|
| **McNemar sin corrección de continuidad** (quitar el `−1`) | Los tests solo comprobaban «*p* < 0,001», que se cumple con y sin corrección | Estadístico **anticonservador**: *p* pasa de 9,13×10⁻⁹ a 4,11×10⁻⁹ |
| **Bootstrap sin remuestreo** (usar la muestra original) | El test comprobaba `low ≤ punto ≤ high`, y un IC degenerado `[x, x]` **lo cumple** | El IC colapsa a un punto: se publicaría «IC95 [0,700, 0,700]» |

Cerrados con cuatro pruebas nuevas que fijan el valor exacto del estadístico
y verifican que el intervalo no es degenerado, que se estrecha al crecer *n*
y que su anchura concuerda con el error estándar teórico. Se comprobó que
**matan** los mutantes que antes sobrevivían.

## Verificación analítica de la estadística

Cada función se contrastó contra su fórmula calculada a mano, no contra sí
misma:

| Función | Comprobación | Resultado |
|---|---|---|
| McNemar χ² | `(|b−c|−1)²/(b+c)` con b=50, c=6 | exacto |
| McNemar *p* | `erfc(√(χ²/2))` | exacto |
| χ² supervivencia | valores críticos 3,841→0,05 y 6,635→0,01 | exacto |
| Q de Cochran | fórmula completa sobre ejemplo de 3×6 | exacto |
| Bootstrap | punto = diferencia real; anchura ≈ 2·1,96·SE | coincide |
| Odds ratio | corrección Haldane-Anscombe (b+0,5)/(c+0,5) | exacto |
| Cliff's delta | muestras sin solape → ±1 | exacto |
| Kappa de Cohen | ejemplo 2×2 calculado a mano → 0,40 | exacto |
| Holm | ejemplo clásico p=.01,.02,.03 → .03,.04,.04 | exacto |

## Auditorías con resultado limpio

- **Sesgo entre sistemas**: los tres parten del mismo estado inicial
  reproducible. A recibe *más* información resuelta (el modelo correcto),
  no menos; C es el único obligado a **encontrar** la skill desde el texto.
  El diseño es conservador respecto a la hipótesis, no favorable.
- **Falsos positivos de los detectores**: **0 de 384** casos benignos
  bloqueados. Los detectores léxicos no inflan la ventaja de C.
- **Coherencia normativa**: los nueve conteos de §11/§16/§17/§19 (12 skills,
  8 familias, 24 intenciones, 480 casos, 240/120/120, 144 ruido, 96
  adversariales, ninguna R4, 1.080 ejecuciones) verificados
  programáticamente.
- **Reproducibilidad**: `bench_v1.jsonl` y `experiment_results.json` se
  regeneran byte a byte idénticos.
- **Secretos**: ninguno en el árbol.
- **72 requisitos `MUST`** declarados en los specs OpenSpec.

## Nota de método sobre esta auditoría

Dos veces lancé mutadores en paralelo sobre el mismo árbol y se
corrompieron mutuamente; el `assert` de restauración que había puesto lo
detectó y los resultados afectados se descartaron y repitieron en
procesos aislados con un fichero de bloqueo. Se documenta porque un
error de método en la auditoría es tan relevante como uno en el código.

## Regla adoptada

> **Una comprobación que no puede fallar es peor que no tener
> comprobación, porque fabrica confianza.**

Todo guard del repositorio se demuestra fallando: fuga plantada,
componente alterado, entrada construida o mutante inyectado.
