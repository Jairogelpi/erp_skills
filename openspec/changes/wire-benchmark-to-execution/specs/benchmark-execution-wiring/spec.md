# Spec: benchmark execution wiring

Traces to CLAUDE.md §14 (architecture), §17 (dataset), §29 (property
tests spirit — report gaps honestly); roadmap P8.1 groundwork.

## Requirements

### MUST: every catalog skill has a handler

`handlers.HANDLERS` MUST have exactly one entry per `catalog.CATALOG_BY_ID`
key, and `handlers.SKILL_MODELS` MUST cover the same set.

### MUST: isolated execution per case

`bench_runner.run_case` MUST construct a fresh `FakeERPAdapter` (and
therefore fresh `Runtime`/`AuditStore`) per case — no state leaks between
cases.

### MUST: deliberate non-seeding for unknown-reference cases

When `case.error_type == "unknown_record_id"`, `run_case` MUST NOT seed
the case's reference field, so a handler that looks it up fails visibly
(`handler_error` set) rather than silently succeeding against a record
seeded specifically to make the test pass.

### MUST: summary reports exact totals and does not hide mismatches

`summarize` MUST report `total` per label matching the dataset's exact
counts (240/144/96) and `matched`/`rate` reflecting the real comparison —
no relaxed or partial matching that would inflate the reported rate.
