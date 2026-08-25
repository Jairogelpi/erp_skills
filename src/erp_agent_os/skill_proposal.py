"""Proposing a new skill: sandbox, tests, human approval (CU-02, §15).

CLAUDE.md §12 CU-02 describes the flow: no candidate is trustworthy
enough -> the LLM proposes a structured definition -> it is validated ->
it is tried **only in sandbox** -> its tests run -> an administrator
approves it -> it is versioned and activated. §15 adds the rule that
makes the whole thing safe:

    "Una skill nunca se activará automáticamente tras su primera
    generación."

**This is a demonstration capability, not part of the experiment.** §15
is explicit that skill generation sits outside the confirmatory A/B/C
comparison and outside its metrics: the catalog of twelve is fixed
before the test split freezes, so nothing here can influence H1-H8. It
exists because CU-02 is a specified use case, and because "the system
can propose a skill but cannot deploy one by itself" is the property
worth demonstrating.

What is enforced here, and tested:

- a proposal enters as `DRAFT` and **cannot** reach `ACTIVE` without
  passing through VALIDATED -> TESTED -> APPROVED (the lifecycle graph
  in `skills.py` decides, not this module);
- **R4 is unregistrable** -- the skill schema itself rejects it, so a
  proposal for a prohibited operation dies at validation;
- the sandbox is a throwaway `FakeERPAdapter`; a proposal is never
  tried against a real adapter;
- approval requires a named human actor, recorded in the registry's
  append-only history.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.postconditions import UnknownPostconditionError, build_checks
from erp_agent_os.registry import SqlSkillRegistry
from erp_agent_os.skills import SkillDefinition, SkillState

Handler = Callable[[FakeERPAdapter, dict[str, Any]], Any]


class ProposalRejected(RuntimeError):
    """Raised when a proposed skill fails validation or its sandbox tests."""


@dataclass(frozen=True)
class SandboxResult:
    passed: bool
    detail: str
    output: Any = None


def validate_proposal(payload: dict[str, Any]) -> SkillDefinition:
    """Turn an LLM's JSON proposal into a validated skill, or refuse it.

    The strict schema in `skills.py` does the work: unknown fields,
    missing fields, an R4 risk class or an empty role list all raise
    here, before anything is registered or executed.

    Validated through JSON rather than the dict directly, because that
    is the shape a proposal actually arrives in -- an LLM emits JSON
    with string enums (`"risk_class": "R1"`), and the contract's strict
    mode only decodes those from JSON, not from a Python dict.
    """
    try:
        skill = SkillDefinition.model_validate_json(json.dumps(payload))
    except Exception as exc:  # any schema failure is surfaced as a rejection
        raise ProposalRejected(f"schema validation failed: {exc}") from exc
    if skill.state is not SkillState.DRAFT:
        raise ProposalRejected(
            f"a proposal must enter as DRAFT, got {skill.state.value}"
        )
    return skill


def run_in_sandbox(
    skill: SkillDefinition,
    handler: Handler,
    sample_arguments: dict[str, Any],
    model: str,
) -> SandboxResult:
    """Execute the candidate once against a throwaway in-memory ERP.

    Never touches a real adapter: the sandbox is constructed here and
    discarded when this returns, so a proposal cannot reach production
    data even if its handler is wrong.

    **The handler is invoked directly, not through `Runtime`, and that
    is deliberate.** The policy engine denies any skill that is not
    `ACTIVE` (correctly -- that is what stops an unapproved skill from
    running in production), so a `DRAFT` candidate routed through it
    would always be refused and could never be tested. Sandbox testing
    therefore answers a different question -- "does this handler do what
    its contract promises?" -- and is safe precisely because the adapter
    it runs against is discarded here. Production authorization stays
    entirely with the policy engine, which will still refuse this skill
    until a human approves and activates it.
    """
    erp = FakeERPAdapter(allowed_models={model})
    before = erp.snapshot()
    try:
        output = handler(erp, sample_arguments)
    except Exception as exc:  # noqa: BLE001 - a crash is a failed test
        return SandboxResult(False, f"handler raised {type(exc).__name__}: {exc}")

    if output is None:
        return SandboxResult(False, "handler produced no output")

    # A handler that runs but does not satisfy its own declared
    # postconditions has not passed: §15 makes postconditions part of
    # the contract, not documentation.
    try:
        checks = build_checks(skill, sample_arguments, before, model)
    except UnknownPostconditionError as exc:
        return SandboxResult(False, f"undeclared postcondition: {exc}")
    if not all(check(erp, output) for check in checks):
        return SandboxResult(False, "postconditions not satisfied in sandbox")

    return SandboxResult(True, "sandbox execution and postconditions passed", output)


def propose_skill(
    registry: SqlSkillRegistry,
    payload: dict[str, Any],
    handler: Handler,
    sample_arguments: dict[str, Any],
    model: str,
) -> SkillDefinition:
    """CU-02 steps 1-5: propose, validate, sandbox-test, register.

    Stops at TESTED **on purpose**. Approval and activation need a human
    (`approve_and_activate`), because §15 forbids a generated skill from
    becoming ACTIVE on its own.
    """
    skill = validate_proposal(payload)

    sandbox = run_in_sandbox(skill, handler, sample_arguments, model)
    if not sandbox.passed:
        raise ProposalRejected(f"sandbox tests failed: {sandbox.detail}")

    registry.register(skill, actor="proposer")
    registry.transition_to(
        skill.skill_id,
        skill.version,
        SkillState.VALIDATED,
        actor="proposer",
        reason="schema validated",
    )
    registry.transition_to(
        skill.skill_id,
        skill.version,
        SkillState.TESTED,
        actor="sandbox",
        reason=sandbox.detail,
    )
    return skill


def approve_and_activate(
    registry: SqlSkillRegistry, skill_id: str, version: str, *, approver: str
) -> SkillState:
    """CU-02 steps 6-7: a named human approves, then it activates.

    `approver` is required and recorded: "who allowed this into
    production" must be answerable from the registry's history alone.
    """
    if not approver.strip():
        raise ProposalRejected("activation requires a named human approver")
    registry.approve(skill_id, version, actor=approver)
    return registry.activate(skill_id, version, actor=approver)
