# Comparación de recuperadores (CLAUDE.md §22)

§22 especifica tres recuperadores y su comparación:

1. baseline léxico — **TF-IDF** con similitud coseno;
2. **embeddings** de frases (`paraphrase-multilingual-MiniLM-L12-v2`);
3. **ranking híbrido** (`w1·similitud + w2·módulo + w3·operación`).

Los tres estaban implementados y probados desde hace varias unidades,
pero **la comparación nunca se había ejecutado**: el experimento
confirmatorio usa TF-IDF y nadie había medido si los otros dos eran
mejores. Este documento cierra ese hueco.

## Disciplina de ajuste (§19, §22)

§22 es explícito: *"Los pesos se ajustarán solamente con los conjuntos
de desarrollo y validación"*. El script reporta **development** y
**validation** por defecto; tocar `FINAL_TEST` exige `--test` y existe
solo para reportar una configuración **ya elegida** en otro sitio.
Elegir recuperador por su puntuación en test sería ajustar sobre el
test, lo que invalida el resultado confirmatorio (§19). **No se ha
hecho.**

## Por qué hubo que calibrar la abstención antes de comparar

La primera pasada dio un resultado engañoso:

| | Top-1 dev | Cobertura dev |
|---|---|---|
| TF-IDF | 0,696 | 0,867 |
| Embeddings | 0,517 | 0,583 |
| Híbrido | 0,417 | 0,450 |

Los embeddings parecían mucho peores — pero la causa no era la calidad
de la recuperación, sino que **la regla de abstención está calibrada
para la escala de TF-IDF** (umbral 0,15, margen 0,05). Las similitudes
coseno de un modelo de frases viven en un rango mucho más estrecho y
todas juntas, así que la regla del margen (`top1 − top2 < 0,05`)
disparaba casi siempre y el recuperador se abstenía en la mitad de las
consultas. Comparar así mide la regla, no los recuperadores.

Se calibró `(umbral, margen)` por recuperador **solo en DEVELOPMENT**,
maximizando Top-1 sobre el split completo (no exactitud selectiva: un
recuperador puede maximizar esa métrica trivialmente abstiéndose en
todo lo difícil):

| Recuperador | umbral | margen |
|---|---|---|
| TF-IDF | 0,20 | 0,00 |
| Embeddings | 0,20 | 0,00 |
| Híbrido | 0,10 | 0,00 |

## Resultado, con calibración justa

### Development (240 casos, split de ajuste)

| Recuperador | Top-1 | Top-3 | MRR | Cobertura | Exact. selectiva |
|---|---|---|---|---|---|
| **TF-IDF** | **0,767** | **0,917** | **0,843** | 0,996 | **0,770** |
| Embeddings | 0,713 | 0,875 | 0,808 | 0,996 | 0,715 |
| Híbrido | 0,713 | 0,879 | 0,811 | 1,000 | 0,713 |

### Validation (120 casos, split de selección)

| Recuperador | Top-1 | Top-3 | MRR | Cobertura | Exact. selectiva |
|---|---|---|---|---|---|
| **TF-IDF** | **0,733** | **0,917** | **0,820** | 1,000 | **0,733** |
| Embeddings | 0,658 | 0,858 | 0,764 | 0,975 | 0,675 |
| Híbrido | 0,675 | 0,883 | 0,785 | 1,000 | 0,675 |

**TF-IDF gana en todas las métricas, en ambos splits, incluso después
de calibrar cada recuperador de forma individualizada y favorable.**

## Interpretación honesta

**Por qué pierde el modelo de embeddings.** ERP-Skills-Bench v1 es
texto generado por plantillas en español, con solape léxico alto entre
la petición y la descripción de la skill ("crea una oportunidad" ↔
"Crea una oportunidad comercial…"). Eso es exactamente la señal que
TF-IDF explota y que un modelo de frases multilingüe comprime en un
vector denso, perdiendo la coincidencia exacta de términos. **No es un
resultado sobre embeddings en general**: es un resultado sobre este
benchmark, y la limitación pertenece al benchmark (§36, validez
externa) tanto como al método.

**Por qué el híbrido no mejora al embedding puro.** Los boosts de
módulo y operación (`w2`, `w3`) solo actúan si el llamador pasa
`module`/`operation`, y en esta evaluación no se pasan — igual que en
System C, que no los infiere. Con ambos a cero, el híbrido colapsa
prácticamente al recuperador vectorial que envuelve, y eso es lo que
se observa (0,713 vs 0,713 en dev). `w4` (compatibilidad de slots) y
`w5` (fiabilidad histórica) siguen sin implementarse, declarado desde
la unidad que creó el módulo.

**Consecuencia para el experimento confirmatorio: ninguna, y eso es
bueno.** El recuperador que el experimento ya usaba (TF-IDF) es el que
gana la comparación en dev/validación. No hay que re-ejecutar nada y,
sobre todo, no se ha elegido nada mirando el test.

**Hallazgo secundario, con una tensión que no se resuelve a favor del
número bonito.** Calibrar subió TF-IDF de 0,696 a 0,767 en dev: el
margen por defecto (0,05) estaba **costando** ~7 puntos de Top-1. Pero
el óptimo encontrado es `margen = 0`, que elimina casi toda la
abstención (cobertura 0,996–1,000). La abstención es parte de la tesis
(H6: abstenerse reduce la reutilización errónea), así que maximizar
Top-1 y maximizar el valor de la abstención son **objetivos en
conflicto**. El experimento confirmatorio conserva el margen por
defecto, más conservador; la curva precisión-cobertura que §20 pide
queda como trabajo declarado, no como una elección silenciosa de la
configuración que más favorece.

## Reproducción

```sh
uv run python scripts/compare_retrievers.py           # dev + validation
uv run python scripts/compare_retrievers.py --test    # añade FINAL_TEST
```

Determinista salvo por el modelo de embeddings, que se descarga en la
primera ejecución. Salida completa en `data/retriever_comparison.json`.

---

## Actualización posterior: este resultado no sobrevive al texto real

**Lo de arriba sigue siendo cierto para lo que midió** —ERP-Skills-Bench,
splits de desarrollo y validación— pero una prueba posterior con
peticiones reales lo acota severamente
(`docs/product-viability.md` §7.2–7.4):

| | Benchmark (validación) | Texto real |
|---|---|---|
| TF-IDF | 0,733 | **0,381** |
| Embeddings | 0,658 | 0,381 |
| Híbrido | 0,675 | 0,274 |

La victoria de TF-IDF **era un artefacto del corpus plantillado**, donde
la petición y la descripción de la skill comparten vocabulario porque
ambas salen de la misma mano. Con texto de usuario esa señal desaparece
y la ventaja se evapora.

**Y el diagnóstico fino invierte la conclusión otra vez:** el problema
no es TF-IDF como técnica, sino las **descripciones de una línea** del
catálogo. Con descripciones enriquecidas (sinónimos y formulaciones
reales, en `data/skill_profiles.json`, sin tocar el catálogo congelado),
TF-IDF pasa de 0,455 a **0,886** de Top-1 en una mitad held-out — por
encima de un router basado en LLM, y a coste cero de tokens.

**Qué significa para esta página:** la comparación entre recuperadores
sigue siendo válida y sigue justificando la elección hecha en el
experimento confirmatorio, pero **no debe citarse como evidencia de que
TF-IDF sea el mejor recuperador en general**. Es el mejor sobre este
corpus, con estas descripciones. Cambiar cualquiera de las dos cosas
cambia el resultado.
