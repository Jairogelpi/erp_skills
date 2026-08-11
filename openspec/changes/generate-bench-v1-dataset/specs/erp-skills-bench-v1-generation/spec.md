# Spec: ERP-Skills-Bench v1 generation

Traces to CLAUDE.md §17 (dataset composition, splits, labels); roadmap
P3.3–P3.5.

## Requirements

### MUST: exact counts

`generate_cases()` MUST return exactly 480 cases, exactly 240 in
`DEVELOPMENT`, exactly 120 in `VALIDATION`, exactly 120 in `FINAL_TEST`,
exactly 144 carrying `CaseLabel.NOISE`, exactly 96 carrying
`CaseLabel.ADVERSARIAL`, and cases spanning all 24 canonical intents.

### MUST: no paraphrase-group leakage

`dataset.validate_case_groups(generate_cases())` MUST NOT raise.

### MUST: valid expected_skill

Every case's `expected_skill` MUST be either a key in
`catalog.CATALOG_BY_ID` or the literal abstention sentinel
`"sin_skill/abstención"`.

### MUST: deterministic

`generate_cases(seed)` MUST return an identical result for repeated calls
with the same `seed` (default `SEED = 20260805`).

### MUST: unique request ids

All `request_id` values across the 480 cases MUST be unique.
