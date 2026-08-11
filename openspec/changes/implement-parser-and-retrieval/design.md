# Design: intent parser contract and TF-IDF retrieval

## Alternatives considered

- **Call a real LLM to produce the proposal**: rejected for this unit.
  CLAUDE.md §23 requires "ninguna ejecución desde texto libre" and a
  registered, low-temperature, retry-limited call with provider config
  logged — that is provider-integration work (needs a chosen provider,
  API key handling, cost tracking) belonging to system C integration
  (P5.4/phase 8), not the schema itself. `structure_proposal` accepts an
  already-produced `(intent, arguments, confidence)` triple, which is
  exactly the shape any future LLM call must still be validated against.
- **Use scikit-learn `TfidfVectorizer`**: rejected. Adding scikit-learn
  (and its numpy/scipy transitive deps) for ~90 lines of stdlib-doable
  cosine-similarity math is unjustified weight; §22 lists TF-IDF as
  baseline #1 specifically to compare against, and a hand-rolled version
  is simpler to audit for this slice. Revisit only if profiling on the
  full 480-case benchmark shows it matters.
- **Implement embeddings/hybrid ranking now**: rejected. `sentence-
  transformers` needs a model download this environment should not
  trigger unprompted, and the hybrid formula's `w4`/`w5` terms
  (`slot_compatibility`, `historical_reliability`) need data (skill
  catalog, execution history) that doesn't exist yet. Documented as
  explicitly deferred, not silently dropped.
- **Fold `should_abstain` into `TfidfRetriever`**: rejected. Abstention
  also depends on `missing_fields`, which comes from the parser, not the
  retriever; keeping it a free function avoids giving the retriever a
  parser-shaped dependency.

## Risks

- TF-IDF over `description` text only (not full skill metadata) is a
  narrow retrieval signal; module/operation-match boosts (`w2`/`w3`) are
  deferred to when system-C integration needs them alongside the parsed
  intent's own module/operation guess.
- No caching of `_idf`/`_vectors` across `TfidfRetriever` instances; at
  benchmark scale (12 skills) this is irrelevant.

## Test strategy

`tests/test_parser.py`: missing-field derivation (blank/absent/present),
confidence bounds, extra-field rejection. `tests/test_retrieval.py`:
closer-description ranks first, role filter excludes, and all four
abstention branches (missing fields, low score, thin margin, confident
no-abstain case).
