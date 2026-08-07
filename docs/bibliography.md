# Bibliografía

Referencias iniciales del TFM (CLAUDE.md §40), agrupadas por función en
el argumento. Las citas están tal como aparecen en la especificación
normativa; las URL de arXiv se dan por identificador para que sean
verificables.

## Agentes y uso de herramientas

- Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning
  and Acting in Language Models*. arXiv:2210.03629.
- Schick, T., Dwivedi-Yu, J., Dessì, R., et al. (2023). *Toolformer:
  Language Models Can Teach Themselves to Use Tools*. arXiv:2302.04761.

## Evaluación y benchmarks

- Liu, X., Yu, H., Zhang, H., et al. (2023). *AgentBench: Evaluating LLMs
  as Agents*. arXiv:2308.03688.
- Li, M., Zhao, Y., Yu, B., et al. (2023). *API-Bank: A Comprehensive
  Benchmark for Tool-Augmented LLMs*. arXiv:2304.08244.
- Yao, S., Shinn, N., Razavi, P., y Narasimhan, K. (2024). *τ-bench: A
  Benchmark for Tool-Agent-User Interaction in Real-World Domains*.
  arXiv:2406.12045.

Uso en este trabajo: AgentBench y API-Bank justifican construir un
benchmark propio con estados verificables en lugar de puntuar solo la
salida textual, y motivan la métrica STSR (estado final correcto, no
respuesta plausible). τ-bench es el pariente conceptual más cercano al
Policy Engine de ERP Agent OS: mide si un agente sigue reglas de negocio
explícitas (aerolínea, retail) en vez de solo completar la tarea, igual
que STSR exige "permisos respetados" como conjunto propio, no implícito
en el éxito. No cubre dominio ERP ni usa datos de este trabajo; se cita
como posicionamiento frente al estado del arte, no como fuente de datos.

## Seguridad y robustez adversarial de agentes

- Zhan, Q., Liang, Z., Ying, Z., y Kang, D. (2024). *InjecAgent:
  Benchmarking Indirect Prompt Injections in Tool-Integrated Large
  Language Model Agents*. arXiv:2403.02691.
- Andriushchenko, M., Souly, A., Dziemian, M., et al. (2024). *AgentHarm:
  A Benchmark for Measuring Harmfulness of LLM Agents*.
  arXiv:2410.09024.

Uso en este trabajo: `docs/results.md` declara que la detección
adversarial de `validation.py` es léxica y está ajustada al texto
plantillado de ERP-Skills-Bench — "no se generaliza a adversarios
adaptativos". InjecAgent (inyección indirecta vía datos de herramienta,
el vector de amenaza más cercano al de este proyecto) se usó como
prueba de estrés externa sobre el Policy Engine; ver `docs/injecagent-stress-test.md`
para el resultado, reportado tal cual salió, favorable o no. AgentHarm
se cita como referencia de diseño de benchmarks de daño en agentes, sin
ejecución contra este sistema por presupuesto de tiempo del TFM.

## Recuperación semántica

- Reimers, N., y Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings
  using Siamese BERT-Networks*. arXiv:1908.10084.

Uso: base del recuperador de embeddings (`embeddings.py`) y del modelo
multilingüe `paraphrase-multilingual-MiniLM-L12-v2`.

## Gobernanza y riesgo

- Autio, C., Schwartz, R., Dunietz, J., et al. (2024). *Artificial
  Intelligence Risk Management Framework: Generative Artificial
  Intelligence Profile*. NIST AI 600-1.
- Especificación oficial de Model Context Protocol.

Uso: la taxonomía R0–R4 y los principios de consentimiento, autorización
explícita y cautela en el uso de herramientas se alinean con ambos.

## Documentación técnica

- Documentación oficial de Odoo 19 (API externa JSON-2).
- Documentación oficial de PostgreSQL y pgvector.

## Metodología estadística

Bibliografía metodológica sobre diseños emparejados, bootstrap,
evaluación selectiva y tamaños de efecto. Las pruebas concretas
implementadas (McNemar, Q de Cochran, bootstrap percentil, Holm, Cliff's
delta) están en `src/erp_agent_os/statistics.py` con verificación contra
valores críticos conocidos en `tests/test_statistics.py`.

---

**Nota de honestidad:** esta lista es la bibliografía *inicial* declarada
en la especificación. Una revisión sistemática del estado de la cuestión
(cobertura de la literatura de agentes gobernados, comparación con
trabajos previos de verificación de acciones LLM) es trabajo de redacción
de la memoria y **no se ha realizado todavía**.
