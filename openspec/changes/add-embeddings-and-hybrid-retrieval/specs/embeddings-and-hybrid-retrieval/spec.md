# Spec: embeddings retriever and hybrid ranker

Traces to CLAUDE.md §22 (recuperación semántica, points 2–3); roadmap P5.2.

## Requirements

### MUST: injectable embedder, no forced network access

`EmbeddingRetriever` MUST accept an `embed: EmbedFn | None` and MUST only
construct a real `SentenceTransformer` when `embed` is omitted.

**Scenario:** constructing with a stub `embed` never imports
`sentence_transformers`.

### MUST: role-filtered ranking

`EmbeddingRetriever.rank(query, role=...)` MUST exclude any skill whose
`permissions.allowed_roles` does not contain the given role.

### MUST: hybrid combines vector score with module/operation boosts

`HybridRetriever.rank(query, module=..., operation=...)` MUST compute each
candidate's score as `weights.vector_similarity * vector_score +
weights.module_match * (1.0 if skill.module == module else 0.0) +
weights.operation_match * (1.0 if skill.operation == operation else 0.0)`,
using only skills the upstream vector retriever's role filter already
returned.

**Scenario:** two tied-vector-score skills, weights with `module_match=1.0`
and `vector_similarity=0.0`; the skill matching the given `module` ranks
first regardless of the tie.

### MUST: hybrid never re-includes a role-filtered-out skill

A skill excluded by the vector retriever's role filter MUST NOT appear in
`HybridRetriever.rank`'s output, even if it would otherwise match
`module`/`operation`.
