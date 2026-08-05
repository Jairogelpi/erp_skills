# Evaluación TFM — ERP Agent OS

**Versión:** 1.1  
**Fecha:** 2026-08-04  
**Estado:** evaluación académica alineada con `CLAUDE.md`, que es la especificación normativa de alcance y protocolo.

---

## Valoración

| Criterio | Valoración |
| --- | --- |
| Encaje técnico con el programa | Alto |
| Rigor experimental propuesto | Alto, condicionado a ejecutar y congelar el protocolo |
| Potencial de producto y portfolio | Alto, si no desplaza al núcleo científico |
| Riesgo de ejecución | Medio-alto por la amplitud confirmatoria |

La propuesta es un TFM de Data Science aplicado y no solo una integración de LLM con ERP: estudia, mediante comparación emparejada, el efecto de recuperar skills preexistentes, verificarlas y ejecutarlas en un runtime gobernado. La generación de skills queda correctamente fuera de la inferencia causal: solo será una demostración en sandbox con aprobación humana.

## Seguimiento operativo

La hoja de ruta en [`docs/roadmap.md`](docs/roadmap.md) y la [bitácora operativa canónica](CLAUDE.md#bitácora-operativa) son documentos de seguimiento, evidencia y coordinación de trabajo. No sustituyen ni modifican el protocolo normativo, el alcance ni las decisiones de `CLAUDE.md`.

## Protocolo que sostiene la evaluación

El alcance final es ambicioso pero definido: **8 familias ERP, 12 skills implementadas, 24 intenciones canónicas, 20 formulaciones por intención y 480 peticiones** (240 desarrollo, 120 validación y 120 test). El benchmark sintético debe separar grupos de paráfrasis/familia-intención sin fuga, admitir etiquetas `sin_skill/abstención` y reportar la distribución por módulo, riesgo y etiquetas de ruido (30 %) y adversariales (20 %), incluido cualquier solapamiento anotado.

La evaluación confirmatoria compara tres sistemas sobre `FakeERP` restaurable: A (agente directo), B (herramientas tipadas) y C (ERP Agent OS). Cada petición de test se ejecuta tres veces en los tres sistemas (1.080 ejecuciones), con modelo/proveedor, presupuestos, permisos, estados y evaluador controlados. El test se congela antes de ajustar catálogo, prompts, umbrales o pesos. `FakeERP`, los tres sistemas, benchmark, experiment runner y análisis estadístico son obligatorios; los detalles operativos y estadísticos están en `CLAUDE.md`.

El endpoint primario es Strict Task Success Rate, con comparación emparejada y margen de no inferioridad declarado. El protocolo también hace evaluables seguridad (incluidos recall, precision y false allow), recuperación y abstención (coverage, selective accuracy y false-reuse risk), estabilidad, tokens, y trazabilidad mediante rúbrica ponderada de evidencia. El valor económico será análisis de sensibilidad/escenarios con supuestos explícitos, no ahorro medido; tampoco se medirá satisfacción como resultado confirmatorio.

## Encaje con el máster

- **Python, SQL/NoSQL, Git y Linux:** API, runtime, catálogo y versionado de skills, trazas, pruebas y reproducibilidad.
- **NLP, modelos generativos y ML:** interpretación estructurada, embeddings, ranking de recuperación y calibración de abstención; el clasificador de riesgo es opcional y no debe rebajar políticas explícitas.
- **Estadística y Data Science aplicada:** benchmark anotado, diseño emparejado, intervalos, tamaños de efecto, análisis segmentado y discusión de validez.
- **BI y visualización:** figuras reproducibles y, posteriormente, dashboard Tableau para comunicar resultados; no sustituye las pruebas estadísticas.
- **Productivización y cloud:** contratos, permisos, idempotencia, observabilidad y contenedorización. No se justifica añadir Spark, CNN o RNN sin una pregunta adicional.

## Fortalezas científicas

1. La variable primaria exige estado final correcto y ausencia de efectos laterales, no solo texto o llamada válida.
2. La comparación A/B/C permite atribuir resultados con más precisión que un único baseline.
3. La seguridad, la recuperación selectiva y la trazabilidad tienen definiciones operacionales auditables.
4. La separación entre confirmatorio y exploratorio evita convertir ajustes posteriores o una demo de generación en evidencia causal.

## Riesgos residuales y prioridad de ejecución

El mayor riesgo es completar 12 skills y 480 casos bien anotados sin degradar el control experimental. Deben priorizarse, en este orden: esquema del dataset, `FakeERP`, contrato de skill, runtime y políticas, auditoría, sistemas A/B/C, experiment runner y estadística. La integración con Odoo 19, el dashboard Tableau, el clasificador de riesgo y otras mejoras son hitos post-core de demostración/extensión; no deben bloquear la evidencia confirmatoria.

También persisten amenazas propias de un benchmark sintético, un único proveedor/modelo y un ERP simulado. La memoria deberá informar resultados nulos, costes de latencia y límites de generalización sin extrapolar a ahorro empresarial real.

## Veredicto

La propuesta encaja con claridad en el máster y puede alcanzar solidez científica si se ejecuta el protocolo congelado descrito en `CLAUDE.md`. El núcleo defendible es: **benchmark + recuperación/ejecución gobernada + comparación A/B/C + análisis estadístico reproducible**. La demo de Odoo, Tableau y generación asistida de skills debe reforzar la comunicación, no ampliar o confundir el reclamo confirmatorio.
