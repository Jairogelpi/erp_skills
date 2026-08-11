# Design: Systems A and B

## Alternatives considered

- **Call a real LLM now, using the user's own credentials from this
  session**: rejected. No API key exists in this repository or should be
  requested through chat and stored; CLAUDE.md's non-negotiables require
  provider configuration to be registered and reproducible, not ad hoc.
  The `LLMClient` Protocol is the seam a real client plugs into later.
- **Give System B partial risk awareness** (e.g., skip R2/R3 without
  approval): rejected. CLAUDE.md §18 is explicit that B has no "taxonomía
  completa" or "aprobación estructurada" — weakening B toward C's
  behavior would blur the comparison the experiment needs.
- **Share one `_execute` helper between A, B, and C's `Runtime`**:
  rejected. The whole point of comparing A/B/C is that they follow
  different paths to execution (ungoverned, typed-only, fully governed);
  collapsing shared execution code would make the systems structurally
  identical below a thin policy shim, undermining the comparison's
  construct validity.

## Risks

- `DeterministicStubClient`'s keyword overlap is a much weaker signal
  than TF-IDF (no IDF weighting, no normalization) — deliberately crude,
  since it exists only to exercise the plumbing, not to approximate LLM
  behavior.
- Both systems accept `arguments` as a direct parameter (like System C's
  wiring, work unit 15) rather than parsing `query_text` themselves —
  consistent with the whole codebase's current "no real LLM parser yet"
  boundary.

## Test strategy

`test_llm_client.py`: keyword-overlap tool selection, no-overlap decline.
`test_system_a.py`: direct execution with no governance, no-tool-
selected handling, disallowed-model error surfaced. `test_system_b.py`:
complete-arguments execution, missing-field rejection, no-matching-tool
handling, and the documented no-risk-tiering gap (an R2 skill executes
without approval).
