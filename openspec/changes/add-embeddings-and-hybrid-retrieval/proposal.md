# Proposal: Add embeddings retriever and hybrid ranker (work unit 10, closes P5.2)

## Intent

Complete roadmap P5.2 and CLAUDE.md §22 points 2–3: an embeddings-based
retriever and a hybrid ranker combining vector similarity with
module/operation-match boosts. TF-IDF (point 1) and abstention were
already done in work unit 7; System C integration (P5.4) is also done.
The user explicitly authorized downloading a sentence-embeddings model for
this unit.

## Scope

- `sentence-transformers==5.6.1` added as a **main** dependency (not dev):
  `EmbeddingRetriever` is production retrieval code, not a dev tool.
- `embeddings.EmbeddingRetriever`: lazy-loads `SentenceTransformer`
  (`paraphrase-multilingual-MiniLM-L12-v2`) only when no `embed` function
  is injected — tests inject a deterministic stub, so the suite never
  needs network access.
- `retrieval.HybridRetriever`/`HybridWeights`: combines any vector
  retriever (structural `VectorRetriever` protocol — TF-IDF or embeddings)
  with `module_match`/`operation_match` boosts (§22 formula `w1`–`w3`).
  `w4` (`slot_compatibility`) and `w5` (`historical_reliability`) remain
  explicitly omitted — no argument-schema compatibility scorer or
  execution-history data exists yet.

## Non-goals

No weight tuning against dev/validation data (§22: "Los pesos se ajustarán
solamente con los conjuntos de desarrollo y validación" — that needs the
populated skill catalog, which doesn't exist yet). No wiring
`HybridRetriever`/`EmbeddingRetriever` into `SystemC` (still uses
`TfidfRetriever`; swapping requires the module/operation guess `SystemC`
doesn't currently derive from `IntentProposal`). No real-model smoke test
in the pytest suite (documented separately, not CI-blocking).

## Follow-on dependency

Wiring `SystemC` to accept any `VectorRetriever` (TF-IDF, embeddings, or
hybrid) and weight calibration on dev/validation data are next, once the
skill catalog (roadmap P3.2–P3.5) exists to calibrate against.

## Success criteria

`EmbeddingRetriever` ranks a closer-matching stub-embedded description
first and filters by role; the real `SentenceTransformer` model loads and
is importable (verified once, outside the test suite). `HybridRetriever`
lets a `module_match` boost override a tied vector score, falls back to
vector-only ranking when `module`/`operation` are omitted, and respects
the upstream vector retriever's role filter. `python -m pytest` passes in
full; `ruff`/`mypy` stay clean (mypy config updated to skip re-checking
`torch`/`transformers`/`sentence_transformers` internals for tractable
run time).

## Forecast

Hand-authored diff: `embeddings.py` (49) + `retrieval.py` net addition
(159 − 96 = 63) + `test_embeddings.py` (75) + `test_retrieval.py` net
addition (101 − 68 = 33) = **220 added lines**, below the 400-line budget.

Separately, `pyproject.toml`/`uv.lock` show **814 insertions** from
resolving `sentence-transformers` and its transitive dependency tree
(torch, transformers, numpy, scipy, scikit-learn, ~70 packages). This is
machine-generated, hash-pinned lock content, not hand-authored/reviewable
line-by-line in the same sense as source diff — flagged explicitly here
rather than folded into the 400-line figure or hidden.
