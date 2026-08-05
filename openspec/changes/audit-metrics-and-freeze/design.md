# Design: measurement integrity

## Why a vacuous check is worse than no check

Both defects here, and the split leak in work unit 21, share one shape: a
guard that returns success unconditionally. It is worse than an absent
guard because it manufactures confidence — the suite is green, the
reviewer sees a named test, and nobody looks again.

The rule adopted: **every guard must be proven to fail.**
`validate_no_split_leakage` is tested with a planted leak; `verify_freeze`
is tested by tampering with each of six components; each STSR conjunct
has a test constructing an input that makes it false.

## Alternatives considered

- **Compare full state equality for ALLOW too**: rejected. A permitted
  execution legitimately writes to its own target model; requiring total
  equality would make conjunct 5 fail for every success, which is the
  opposite vacuity.
- **Freeze by committing a copy of the dataset and diffing files**:
  rejected. The generator is the source of truth; a file copy would drift
  from it silently. Hashing what the generator produces catches a change
  in the generator itself, which is the actual risk.
- **Make `verify_freeze` a warning rather than a CI failure**: rejected.
  §19 is a hard boundary; a warning is ignorable, and the whole point is
  that post-freeze drift must be impossible to miss.
- **Delete `validate_case_groups`**: rejected. It still checks a real
  contract field, and removing it would break callers. Instead its
  docstring now states plainly that it is insufficient alone and names
  the validator to pair it with.

## Risks

- The freeze binds the dataset, catalog and seed but **not** prompts or
  provider configuration, because no real provider is wired yet. When an
  LLM client is added, the manifest must be extended or the freeze will
  be incomplete for the confirmatory run.
