# ERP-Skills-Bench Dataset Specification (work unit 1)

## Purpose

Freeze a versioned synthetic benchmark-case contract so evaluation inputs and split boundaries remain reproducible. This change is limited to the dataset schema/scaffold work unit.

## Requirements

### Requirement: Frozen case schema

The system MUST accept benchmark cases only at schema version `1.0` with required request identity/text, canonical intent, paraphrase group, split, expected skill, expected arguments and decision, initial/expected-final state, clarification/approval annotations, error type, risk class, module, and labels. `expected_skill` MUST be nonblank or exactly `sin_skill/abstención`; it MUST NOT be omitted or null. `error_type` MUST be explicit.

#### Scenario: Explicit abstention case is valid

- GIVEN a complete version `1.0` case
- WHEN expected skill is `sin_skill/abstención`
- THEN validation accepts it as an explicit annotation

### Requirement: Label overlap invariant

The system MUST represent finite normal, noise, and adversarial labels. `NORMAL` MUST occur iff neither abnormal label occurs. `NOISE` and `ADVERSARIAL` MAY coexist.

#### Scenario: Overlap and exclusion

- GIVEN labels `NOISE` and `ADVERSARIAL`
- THEN validation succeeds
- GIVEN labels `NORMAL` and `NOISE`
- THEN validation fails

### Requirement: Frozen split and group invariants

The system MUST accept only a `1.0` plan with 240 development, 120 validation, and 120 final-test cases totaling 480, and MUST reject a paraphrase group assigned to multiple splits.

## Deferred dependency

FakeERP and skill-contract specifications are not part of this work unit; they require a follow-on SDD change.
