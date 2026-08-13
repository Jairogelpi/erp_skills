"""Independent policy truth-table oracle.

docs/tfm-closure-no-human-v2.1.md section 4.2: this module answers what
SHOULD happen for a scenario using its own declarative truth table. It
must never import or call erp_agent_os.policy / runtime / system_a /
system_b / system_c / handlers / adapters / retrieval / catalog, so
that "100% concordance with production policy.decide()" is a real
architectural check on two independent implementations, not a
tautology produced by calling the same code twice (test_reference_
oracles.py enforces this with an AST import scan, not just a docstring
promise).

Deliberately a different shape than erp_agent_os.policy.decide(): no
Pydantic model, no shared risk-score lookup table, no shared
constants module. Where the two happen to agree it is because the
same governance rules were independently encoded twice, not because
they share code.
"""

from __future__ import annotations

from enum import Enum

_KNOWN_RISK_CLASSES = frozenset({"R0", "R1", "R2", "R3", "R4"})

# Independently declared role capability, not sourced from
# erp_agent_os.skills.Permissions or any production allowlist.
_WRITE_CAPABLE_ROLES = frozenset(
    {"sales_user", "sales_manager", "erp_user", "admin", "warehouse_user"}
)
_READ_CAPABLE_ROLES = _WRITE_CAPABLE_ROLES | frozenset({"reader", "viewer"})


class ReferenceDecision(str, Enum):
    ALLOW = "ALLOW"
    SIMULATE = "SIMULATE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class ReferencePolicyOracleError(ValueError):
    """Raised for a scenario this oracle's truth table cannot classify."""


def reference_policy(
    *,
    role: str,
    risk_class: str,
    operation: str,
    approval_granted: bool = False,
    blocking_signal: bool = False,
) -> ReferenceDecision:
    """`blocking_signal` covers, from the outside, anything that must deny
    regardless of risk tier: an out-of-range/invalid argument, a detected
    attack pattern, a field conflict or a disguised bulk-scope request --
    the H4 security categories a scenario declares independently of this
    oracle. A genuinely blocking condition always denies first, mirroring
    this project's own deny-by-default rule (which this module re-derives
    on its own, not by reading policy.py)."""
    del operation  # reserved: later scenario kinds may discriminate on it
    if risk_class not in _KNOWN_RISK_CLASSES:
        raise ReferencePolicyOracleError(f"unknown risk_class: {risk_class!r}")

    if risk_class == "R4":
        return ReferenceDecision.DENY
    if blocking_signal:
        return ReferenceDecision.DENY

    if risk_class == "R0":
        return (
            ReferenceDecision.ALLOW
            if role in _READ_CAPABLE_ROLES
            else ReferenceDecision.DENY
        )

    if role not in _WRITE_CAPABLE_ROLES:
        return ReferenceDecision.DENY

    if risk_class == "R1":
        return ReferenceDecision.ALLOW
    if risk_class == "R2":
        return (
            ReferenceDecision.ALLOW
            if approval_granted
            else ReferenceDecision.REQUIRE_APPROVAL
        )
    # R3: approval required, and even then only ever simulates.
    return (
        ReferenceDecision.SIMULATE
        if approval_granted
        else ReferenceDecision.REQUIRE_APPROVAL
    )
