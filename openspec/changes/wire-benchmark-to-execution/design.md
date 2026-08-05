# Design: benchmark execution wiring

## Approach

`run_case` looks up the case's canonical intent → skill → required
fields, builds a fresh sandbox, seeds referenced entities (unless the
case is testing a missing reference), runs `SystemC.handle` with the
case's own `expected_arguments` as the "parsed" proposal, and compares
`SystemCResult.decision` to `case.expected_decision.value` by strict
string equality.

## Alternatives considered

- **Relax the comparison to treat `ABSTAIN`/`CLARIFY` as equivalent**:
  rejected. The dataset intentionally distinguishes them; silently
  merging them in the comparison would hide a real system gap (no
  `CLARIFY` signal exists yet) rather than reveal it, contradicting
  CLAUDE.md §35.18's "no ocultar resultados negativos."
- **Skip seeding entirely and let every update/read handler fail**:
  rejected. Would make NORMAL/NOISE cases fail for a reason unrelated to
  the thing being tested (system correctness), producing a meaningless
  report. Seeding models "this entity already exists," which is the
  correct precondition for every case except the one adversarial category
  that's specifically about a missing entity.
- **Rewrite `data/bench_v1.jsonl`'s placeholder states with this run's
  literal captured snapshots**: rejected. The seeding strategy (which
  entities get a baseline record, with which fields) is a property of
  *this* runner's methodology, not an inherent property of the
  annotation; baking one run's incidental seed values into the dataset
  file would conflate "what a correct system should produce" with "what
  this particular sandbox happened to contain." The dataset card documents
  the wiring results and match rates instead.
- **Use TF-IDF only (not the hybrid/embeddings retriever) for this
  discovery run**: kept intentionally, to establish the baseline the
  future A/B/C piloto will compare against; also avoids re-downloading/
  re-encoding the embedding model 480× for a discovery script.

## Risks

- The ADVERSARIAL match-rate finding (17.7%) will look alarming out of
  context; the dataset card's "Honest findings" section exists precisely
  to give it context (expected, given no security-specific checks exist
  yet) rather than let a reader mistake it for a wiring bug.
- `expected_arguments`-as-ground-truth-proposal means this run does not
  yet exercise real NLP failure modes (misheard entities, genuinely
  ambiguous phrasing beyond what TF-IDF ranking already reveals).

## Test strategy

`tests/test_handlers.py`: catalog coverage, a create→update roundtrip, a
search hit, an availability read. `tests/test_bench_runner.py`: exact
outcome count, a NORMAL case matches and mutates, an R2 case reaches the
handler only once approved, an unseeded reference surfaces
`handler_error` on an auto-executing (R0) skill, `summarize`'s bucket
totals are exact, and the ADVERSARIAL rate is asserted to be lower than
NORMAL's (locking in the honest finding as a regression check, not just a
one-off report).
