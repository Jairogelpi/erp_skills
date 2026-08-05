# Spec: measurement and paired experiment

Traces to CLAUDE.md §17, §19, §20, §21; roadmap P8.1-P8.3, P9.2-P9.4.

## Requirements

### MUST: no formulation crosses splits

`validate_no_split_leakage` MUST reject a dataset where any normalized
request text, or any (canonical_intent, expected_arguments) pair, appears
in more than one split. It MUST be proven non-vacuous by a test that
plants a leak and asserts the validator raises.

### MUST: STSR is conjunctive and attributable

`stsr_breakdown` MUST evaluate all five §20 conjuncts separately and
succeed only if all hold, so a failure can be attributed to a conjunct.

### MUST: false allow is measured on dangerous cases only

`security_metrics` MUST compute false allow over cases whose `error_type`
is in `DANGEROUS_ERROR_TYPES`, and false block over benign cases the
system refused.

### MUST: selective accuracy cannot be inflated by abstaining

`retrieval_metrics` MUST report coverage and abstention alongside
selective accuracy, and MUST NOT credit an abstained case as correct.

### MUST: the experiment is paired and isolated

`run_experiment` MUST produce `n_cases × 3 × repetitions` observations,
rebuild `FakeERPAdapter` per observation, randomize order under a
recorded seed, and record in its manifest whether the selector makes the
run confirmatory.

### MUST: baselines are judged by equivalent criteria

System A MUST be scored on the catalog skill equivalent to its generic
tool call, and by the same postconditions as B and C. Its tool
descriptions MUST be in the corpus language.
