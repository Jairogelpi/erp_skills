# Proposal: Freeze ERP-Skills-Bench dataset schema

## Intent

Create the first, reviewable work unit of the ERP Agent OS foundation: a frozen, synthetic benchmark-case contract. This split was chosen after the prior combined dataset/FakeERP/skills slice measured 448 lines against the 400-line review budget.

## Scope

- Minimal Python package and pytest scaffold.
- Version `1.0` Pydantic `BenchmarkCase` and `SplitPlan` contracts.
- Strict required annotations, explicit `sin_skill/abstención`, finite labels/risk/decision enums, label-overlap invariant, fixed 240/120/120 split allocation, and pure paraphrase-group leakage validation.
- Focused unit tests for those dataset boundaries.

## Non-goals

FakeERP, skill definitions/lifecycle, runtime, policy, retrieval, LLM behavior, generated benchmark data, external ERP/Odoo, services, persistence, APIs, and experiments are excluded.

## Follow-on dependency

A follow-on SDD change must implement FakeERP first, then the skill contract, using the removed adapter/skill specifications as its planning inputs. This work unit intentionally provides no adapter or skill interfaces.

## Success criteria

Complete cases validate only with the frozen annotations; the abstention sentinel is explicit; label and split/group invariants reject invalid inputs; focused tests pass with `python -m pytest`.

## Forecast

This work unit retains five implementation/test files plus `pyproject.toml`: **188 added lines**, below the 400-line budget. No commit is created by apply.
