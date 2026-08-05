# Proposal: Implement Systems A and B baselines (work unit 17, closes P8.1 baselines)

## Intent

User-directed: "haz A B y C par poder comparar". System C (`SystemC`) has
been complete since work unit 9. This delivers the two baselines
CLAUDE.md §18 requires for the confirmatory comparison: A (direct agent,
ungoverned) and B (typed tools, no retrieval/risk/approval/verification).

## Scope

- `llm_client.LLMClient` (Protocol) + `ToolSpec`/`ToolCall`: the shared
  interface both baselines use to ask "which tool, given this text."
  `DeterministicStubClient`: a keyword-overlap stand-in for tests/local
  plumbing, explicitly documented as **not** valid for producing
  confirmatory A/B/C results (CLAUDE.md D-03 requires the same
  model/provider across all three systems).
- `system_a.SystemA`: generic `create_record`/`update_record`/
  `get_record` tools operating directly on `FakeERPAdapter` — no skill
  registry, no risk tiering, no approval, no audit. Deliberately
  ungoverned, per §18's description of System A.
- `system_b.SystemB`: reuses the 12-skill catalog's `input_schema` and
  `handlers` (same tool surface as C) but the LLM picks the tool
  directly — no TF-IDF/embedding ranking, no abstention, no risk-tiered
  policy decision, no postcondition check.

## Non-goals

No real LLM provider wiring (needs API credentials the user must supply
via environment, never committed here). No A/B/C comparison runner using
a real model (would need that credential). No 1.080-execution
confirmatory protocol (roadmap P8.2–P9) — that needs the frozen
test/config manifest this unit does not attempt.

## Follow-on dependency

A real `LLMClient` implementation (e.g. wrapping the Anthropic SDK,
reading `ANTHROPIC_API_KEY` from environment) is required before any
actual A/B/C comparison can run. Once that exists, an experiment runner
(roadmap P8.2–P8.3) drives all three systems over the frozen benchmark.

## Success criteria

`SystemA` executes a proposed tool call directly (no governance) and
surfaces adapter/argument errors without crashing. `SystemB` executes
only when all required fields per the catalog schema are present, with
no risk-based gating (an R2 skill executes immediately given complete
arguments — the documented governance gap vs. System C). Both share the
same `LLMClient` interface as a pluggable seam. `python -m pytest` passes
in full.

## Forecast

Three new source files (`llm_client.py` 50, `system_a.py` 59,
`system_b.py` 61) and three new test files (`test_llm_client.py` 18,
`test_system_a.py` 44, `test_system_b.py` 61): **293 added lines**,
below the 400-line budget.
