# Contributing

Thanks for contributing to ERP Agent OS.

This repository is both a software project and a research artifact. Changes therefore have two responsibilities: they must be technically correct **and** they must not silently change the meaning of published evidence.

## Development setup

```sh
git clone https://github.com/Jairogelpi/erp_skills.git
cd erp_skills
uv lock --check
uv sync --frozen --group dev
```

Before submitting a change, run as appropriate:

```sh
make format-check
make lint
make typecheck
make test
make verify-tfm-closure
```

For changes affecting the comparative demo:

```sh
make demo-preflight
```

## Evidence integrity

The current confirmatory campaign is frozen and reported under `tfm-protocol-v2.1.2`. Do not edit frozen experiment inputs, raw observations, manifests or analysis components merely to improve a result or to make a historical artifact look cleaner.

If a genuine defect is discovered:

1. document the defect;
2. identify whether it affects implementation, measurement, analysis or reporting;
3. preserve the superseded artifact when provenance matters;
4. make the correction explicitly;
5. re-run only the checks legitimately affected by the change;
6. update claims conservatively;
7. never retroactively relabel exploratory evidence as confirmatory.

The canonical current results are in `docs/results-v2.1.md`. Historical v1 results remain useful for provenance but must not override the current v2.1.2 findings.

## Claims policy

Contributions must not introduce claims stronger than the evidence.

In particular, do not claim that ERP Agent OS:

- is generally safe;
- reliably detects dangerous requests;
- beats typed tools on task success;
- guarantees zero unauthorized mutations;
- saves a measured monetary amount;
- is production-ready for unattended ERP writes.

The current experiment supports narrower claims around token efficiency, paraphrase stability, abstention and audit reconstruction, while H4 and H5 remain important negative results.

## Demo integrity

The comparative product demo follows four non-negotiable rules:

- no invented composite A/B/C score;
- no inferred governance fields for baselines that do not produce them;
- FakeERP-only comparative API;
- positive write control before treating non-mutation as meaningful.

Real Odoo execution must continue to use the existing guarded Development-only path.

## Tests

Add tests for behavior changes. Prefer tests that can fail for the intended reason rather than tests that merely restate the implementation.

For statistical or validation code, test the mechanism as well as the final conclusion. The project's audit history contains examples where conclusion-only tests allowed defects in the calculation itself to survive.

## Style

- Python 3.12.
- Ruff is the formatter and linter.
- mypy covers `src` and `scripts` according to `pyproject.toml`.
- Keep public types explicit where they clarify contracts.
- Keep research terminology consistent with the thesis: skill, policy decision, risk class, approval, postcondition, audit evidence, abstention and unauthorized mutation.

## Pull requests

A good pull request explains:

- what changed;
- why it changed;
- which requirement, defect or use case it addresses;
- what tests were added or run;
- whether any frozen/research artifact is touched;
- whether any public claim or documentation must change.

Small, reviewable changes are preferred over large mixed refactors.

## Third-party material

Do not copy external datasets, benchmark material, figures or code into this repository without checking their license and attribution requirements. See `THIRD_PARTY_NOTICES.md`.
