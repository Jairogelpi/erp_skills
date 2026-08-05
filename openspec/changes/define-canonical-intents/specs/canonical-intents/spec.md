# Spec: canonical intents

Traces to CLAUDE.md §11 (24 canonical intents), §17 (variación
lingüística source data); roadmap P3.2.

## Requirements

### MUST: exactly 24 intents, unique ids, 2 per skill

`INTENTS` MUST contain exactly 24 entries with unique `intent_id`s, and
grouping by `skill_id` MUST yield exactly 2 intents per catalog skill.

### MUST: every intent resolves to a cataloged skill

Every `IntentSpec.skill_id` MUST be a key in `catalog.CATALOG_BY_ID`.

### MUST: templates render cleanly

For every intent, formatting `template` with one value per
`required_fields` entry (from its skill's `input_schema["required"]`)
MUST leave no unresolved `{...}` placeholder.
