# Prospective v2 holdout and human-oracle plan

## Objective

Create a new 120-case Spanish ERP holdout that cannot be evaluated by A/B/C
until two independent human annotations and state-oracle reviews are complete.
The workflow must preserve hashes, prevent silent edits, and never represent
AI-generated labels as human agreement.

## Tasks

1. **Completed.** Add a deterministic v2 candidate generator with 24 intents, five cases per
   intent, 60 normal, 36 noise and 24 adversarial cases. Verify novelty against
   v1 text and `(intent, arguments)` pairs.
2. **Completed.** Add a prospective evidence module that writes content-addressed candidate
   and author-proposal archives plus two blank, blinded annotation packets.
3. **Completed.** Validate independent packets, compute decision agreement and Cohen's kappa,
   and generate an adjudication packet for disagreements. Reject blank,
   duplicated, extra or fabricated rows.
4. **Completed.** Add an experiment gate: no final v2 gold or A/B/C run without two complete
   annotations, resolved disagreements and two completed state reviews.
5. **Completed.** Generate and seal the candidate artifact without printing case content.
   Record the current experiment-code, catalog, prompt and provider hashes.
6. **Completed.** Document the human handoff and the exact commands. Mark the project as
   `v2_candidates_sealed_awaiting_human_annotation`, not confirmatory.
7. **Completed.** Run unit tests, full tests, formatting, lint, typing, freeze verification and
   claim validation.

## Non-negotiable scientific constraints

- Do not run A/B/C on v2 during this implementation.
- Do not fill `annotator_1` or `annotator_2` fields with model output.
- Author proposals are not an oracle and remain isolated from blinded packets.
- Any post-seal change to benchmark or experiment code invalidates the seal.
- A future finalizer must fail closed until all human gates are satisfied.
