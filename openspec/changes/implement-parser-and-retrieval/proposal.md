# Proposal: Implement intent parser contract and TF-IDF retrieval (work unit 7)

## Intent

Deliver the first slice of roadmap phase 5 (P5.1–P5.3) and CLAUDE.md §§22–23:
a strict structured-proposal schema (no LLM call, no execution) and a
TF-IDF retrieval baseline with role filtering and an abstention rule.
Phase 4 (núcleo determinista) is complete, unblocking this phase per D-10.

## Scope

- `parser.IntentProposal` + `structure_proposal(...)`: strict schema
  (`intent`, `arguments`, `missing_fields`, `confidence` bounded to
  `[0,1]`, `constraints`), and a pure function deriving `missing_fields`
  from a declared required-field list (blank or absent counts as missing).
- `retrieval.TfidfRetriever`: hand-rolled TF-IDF cosine similarity over
  `SkillDefinition.description` (stdlib only — `re`/`math`/`collections`,
  no ML dependency for this baseline), with role filtering via
  `permissions.allowed_roles`.
- `retrieval.should_abstain(...)`: abstains when required fields are
  missing, when there is no ranked candidate, when the top score is below
  a threshold, or when the top-two margin is too small (CLAUDE.md §22
  formula, minus `slot_compatibility`/`historical_reliability`, which need
  data this slice doesn't have yet).

## Non-goals

No LLM call (the parser takes an already-produced candidate, matching
CLAUDE.md §23's "ninguna ejecución desde texto libre" — text-to-candidate
generation is a separate, provider-facing concern). No embeddings model,
no hybrid ranker weights `w4`/`w5` (§22 points 2–3 — deferred pending a
model choice, since sentence-transformers needs a multi-hundred-MB
download this environment should not trigger unprompted). No wiring into
`Runtime`/`policy.decide` (that is system-C integration, P5.4).

## Follow-on dependency

System C integration (P5.4: parser → retriever → policy → runtime →
verification → audit, end to end) and the approval service (work unit 9,
already planned next) both build on this slice.

## Success criteria

`IntentProposal` rejects out-of-range confidence and unknown fields;
`structure_proposal` correctly marks blank and absent required fields as
missing and leaves fully-supplied fields off that list. `TfidfRetriever`
ranks a closer-matching description first, excludes skills the given role
cannot use, and `should_abstain` returns `True` for missing fields, no
candidates, a low top score, and a thin top-two margin, `False` otherwise.
`python -m pytest` passes in full.

## Forecast

Two new source files (`parser.py` 60, `retrieval.py` 96) and two new test
files (`test_parser.py` 48, `test_retrieval.py` 68): **272 added lines**,
below the 400-line budget. No split needed.
