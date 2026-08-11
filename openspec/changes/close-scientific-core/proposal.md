# Proposal: Close the scientific core (work unit 21, §35 criteria 1-9)

## Intent

A self-audit found the engineering strong but the *measurement apparatus*
almost absent, and a real data-leakage defect in the frozen test. This
unit closes CLAUDE.md §35 acceptance criteria 1-9.

## Defect fixed first

The frozen test leaked: **10 identical request texts appeared in both
DEVELOPMENT and FINAL_TEST** (8.3% of the test split), 19 crossing splits
overall. Root cause: the earlier decision to make every case its own
paraphrase group rendered `validate_case_groups` **tautological** — a
group of size 1 cannot cross anything. The prior `design.md` justified it
as "a simpler valid reading" of §17; that was wrong, since §17 forbids
"ni formulación semánticamente equivalente" from crossing.

Fix: slot pools widened 4-8 → 24 values, deterministic non-repeating slot
assignment within an intent, duplicated `_style_directa` replaced,
`incomplete_instruction` truncation lengthened, and a new
`validate_no_split_leakage` checking normalized text *and*
(intent, arguments) — proven non-vacuous by a planted-leak test.

## Scope

- `metrics.py` — STSR as §20's five-way conjunction with per-conjunct
  attribution; false allow/block, detection recall/precision;
  Top-1/Top-3/MRR/coverage/selective accuracy/abstention; stability.
- `postconditions.py` — catalog postconditions resolved from decorative
  strings into executable checks (12/12 skills resolvable).
- `experiment.py` + `scripts/run_experiment.py` — paired runner:
  120 × 3 × 3 = 1.080 observations, randomized order, state rebuilt per
  observation, manifest recording the selector.
- `docs/results.md` — the analysis answering the research question.

## Comparison biases found and fixed before publishing numbers

1. System A scored 0 structurally because it was judged on `skill_id`
   identity it cannot express → its generic call is now mapped to the
   equivalent catalog skill by model+operation.
2. System A's tools had **English** descriptions against a Spanish
   corpus → the shared selector could not match, so A would have failed
   on language, not governance.

Both violated D-03 (equivalent tool coverage).

## Non-goals

Real LLM provider (needs credentials); token/latency/cost instrumentation
(H2/H8); automatic traceability scoring (H7); human annotation for kappa.

## Success criteria

Zero split leakage, provably. 1.080 paired observations. STSR, false
allow and retrieval metrics computed from real executions. Paired tests
with CIs, effect sizes and Holm correction reported. Every limitation
stated rather than buried.
