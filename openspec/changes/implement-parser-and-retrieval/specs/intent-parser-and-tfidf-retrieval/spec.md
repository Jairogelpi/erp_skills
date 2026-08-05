# Spec: intent parser contract and TF-IDF retrieval

Traces to CLAUDE.md §22 (recuperación semántica), §23 (generación
estructurada); roadmap P5.1–P5.3; RF-01–02, RF-04–05.

## Requirements

### MUST: structured proposal schema

`IntentProposal` MUST reject `confidence` outside `[0, 1]` and MUST reject
any field not in its declared schema (`extra="forbid"`).

### MUST: correct missing-field derivation

`structure_proposal` MUST include in `missing_fields` every required field
that is absent from `arguments` or present but blank (whitespace-only),
and MUST exclude every required field with a non-blank value.

**Scenario:** required `["a", "b"]`; arguments `{"a": "x", "b": "  "}` →
`missing_fields == ["b"]`.

### MUST: role-filtered ranking

`TfidfRetriever.rank(query, role=...)` MUST exclude any skill whose
`permissions.allowed_roles` does not contain the given role, and MUST NOT
filter when `role` is omitted.

### MUST: abstention on four conditions

`should_abstain` MUST return `True` when `missing_fields` is nonempty, when
`ranked` is empty, when the top-ranked score is below `threshold`, or when
the score gap between the top two candidates is below `margin`. It MUST
return `False` only when none of those hold.

**Scenario:** nonempty `missing_fields` with an otherwise strong ranked
result still abstains.
