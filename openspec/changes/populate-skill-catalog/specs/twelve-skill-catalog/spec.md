# Spec: twelve-skill catalog

Traces to CLAUDE.md §11 (8 families, exactly 12 skills); roadmap P3.2.

## Requirements

### MUST: exactly 12 skills, 8 families covered

`CATALOG` MUST contain exactly 12 entries, and the set of `module` values
across them MUST equal all 8 CLAUDE.md §11 families.

### MUST: no R4, all ACTIVE, unique ids

No entry's `risk_class` MUST be `R4`; every entry's `state` MUST be
`ACTIVE`; all `skill_id` values MUST be unique.
