"""CU-02 for the product demo: propose, edit, test, approve, activate.

Backs the "Administrar automatizaciones" panel of product_demo_server.py.
Reuses the real governed lifecycle (erp_agent_os.skill_proposal,
erp_agent_os.registry, erp_agent_os.skills) -- this is not a toy
reimplementation for the UI.

**The hard line this module does not cross:** the LLM drafts a skill
*contract* (a JSON document -- schema, risk class, roles, pre/post
conditions) and the user can edit that contract in the frontend. It
never drafts or edits executable code. CLAUDE.md section 41's own
non-negotiable list is explicit: "El LLM no ejecutará código
arbitrario." Sandbox-testing a proposal (required to reach TESTED,
and required to reach TESTED before ACTIVE is even reachable --
skills.ALLOWED_TRANSITIONS has no shortcut) needs a real handler
function; the one used here (`generic_create_handler`) is hand-written
by a human, once, and works only for the natural "create a record with
these fields" shape. A proposal whose semantics don't fit that (an
update, a search, anything conditional) will honestly fail its own
postconditions in sandbox -- which is the correct signal that it needs
a hand-written handler, not a bug to work around.

**Never merges into the frozen 12-skill catalog.** Proposals live in
their own in-memory SQLite registry, entirely separate from
erp_agent_os.catalog.CATALOG (which is what actually runs against real
Odoo in this demo). Activating a proposal here means "governed and
ready for an engineer to wire a real handler" -- not "now writes to
Odoo". Saying otherwise would be exactly the false commercial claim
docs/product-viability.md's own rule exists to prevent.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.registry import SqlSkillRegistry, create_registry_schema
from erp_agent_os.skill_proposal import (
    ProposalRejected,
    approve_and_activate,
    propose_skill,
)
from erp_agent_os.skills import SkillDefinition

_DRAFT_SYSTEM_PROMPT = """\
Eres un asistente que redacta contratos de "skill" para un sistema ERP
gobernado. Devuelves EXCLUSIVAMENTE un JSON con esta forma exacta, sin
texto adicional, sin markdown:

{
  "skill_id": "modulo.nombre_snake_case",
  "version": "1.0.0",
  "module": "modulo",
  "operation": "create",
  "description": "una frase clara de qué hace",
  "risk_class": "R0" | "R1" | "R2" | "R3",
  "input_schema": {
    "type": "object",
    "required": ["campo1", "campo2"],
    "properties": {
      "campo1": {"type": "string"},
      "campo2": {"type": "number"}
    }
  },
  "permissions": {"allowed_roles": ["erp_user"]},
  "preconditions": ["descripcion_de_una_precondicion"],
  "execution": {
    "handler": "demo_proposals.generic_create",
    "timeout_seconds": 10,
    "max_retries": 1,
    "idempotent": true
  },
  "postconditions": ["exactly_one_new_record"],
  "approval_required_when": []
}

Reglas estrictas:
- "operation" debe ser "create" -- esta demo solo puede probar en
  sandbox capacidades que crean un registro nuevo con los campos
  indicados. Si la petición del usuario no encaja en "crear algo",
  redacta la versión "crear" más cercana y dilo en la descripción.
- "risk_class" nunca puede ser "R4".
- "execution.handler" es siempre literalmente "demo_proposals.generic_create"
  -- no inventes un handler nuevo, esta demo no ejecuta código generado.
- "postconditions" siempre incluye "exactly_one_new_record".
- No inventes campos fuera de los que el usuario describe.
- Escribe TODOS los valores de texto del JSON (skill_id, description,
  campos, preconditions...) SIN tildes ni eñes -- "limite" en vez de
  "límite", "creacion" en vez de "creación". Es una limitación conocida
  y verificada de este modelo a través de este proveedor: los caracteres
  acentuados a veces llegan corruptos en la respuesta. El texto sin
  tildes es español perfectamente legible, aunque informal.
"""


class SkillAdminError(RuntimeError):
    pass


def _repair_mojibake(text: str) -> str:
    """Undo a double-encoding: UTF-8 bytes for an accented character (e.g.
    "í" = 0xC3 0xAD) each mis-decoded as its own Latin-1 codepoint, giving
    "Ã­" instead of "í".

    Verified live and reproducibly against this exact model/provider:
    deepseek/deepseek-v4-flash on OpenRouter's free tier occasionally
    emits Spanish text this way -- confirmed against a real response
    ("límite" arrived as "lÃ­mite") -- not a bug in this
    client's HTTP handling (httpx decodes the transport bytes correctly;
    the corruption is already present in the JSON payload's string
    values). Safe by construction: pure ASCII round-trips through
    encode('latin-1').decode('utf-8') unchanged, and any text that is
    already correctly decoded (containing a real accented character)
    raises UnicodeDecodeError here and is returned untouched.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _llm_complete(system_prompt: str, user_prompt: str, *, api_key: str) -> str:
    """Minimal, self-contained completion call -- deliberately not reusing
    OpenRouterClient's private _completion(): that method is tuned for
    tool-selection/argument-extraction's own retry and pacing needs, and
    reaching into a private method here would couple this demo-only
    module to library internals it does not own."""
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "deepseek/deepseek-v4-flash",
            "temperature": 0.2,
            # Found live, not assumed: this model sometimes prefixes its
            # answer with an internal "reasoning" block before the actual
            # JSON (a separate response field OpenRouter still bills
            # against max_tokens), and a low budget was observed to either
            # exhaust itself entirely on that preamble (empty content,
            # finish_reason "length") or cut the JSON off mid-object.
            # 2000 leaves headroom for both the preamble and the full
            # contract this prompt asks for.
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"].get("content") or "{}"
    return _repair_mojibake(content)


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise SkillAdminError("el modelo no devolvió JSON")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise SkillAdminError(f"JSON del modelo inválido: {exc}") from exc


def draft_skill_contract(description: str, *, api_key: str) -> dict[str, Any]:
    """LLM drafts a skill CONTRACT (schema only, never code) from a plain
    description. The caller (the frontend) is expected to let a human
    review and edit this before it goes anywhere near propose_contract."""
    content = _llm_complete(_DRAFT_SYSTEM_PROMPT, description, api_key=api_key)
    payload = _extract_json(content)
    payload.setdefault("execution", {})
    payload["execution"]["handler"] = "demo_proposals.generic_create"
    payload.setdefault("state", "DRAFT")
    return payload


def synthesize_sample_arguments(input_schema: dict[str, Any]) -> dict[str, Any]:
    """Fabricate one plausible value per required field, so the sandbox
    test (CU-02 step 4, "se ejecutan sus tests") has something to run
    against without asking a human to type throwaway test data by hand.

    Deliberately dumb and type-driven (never touches the LLM): a
    fabricated value only has to satisfy the schema's own type, because
    what the sandbox test is actually checking is "does the handler
    honor its declared postconditions", not "is this realistic data".
    """
    properties = input_schema.get("properties", {})
    sample: dict[str, Any] = {}
    for field in input_schema.get("required", []):
        field_type = properties.get(field, {}).get("type", "string")
        if field_type == "number" or field_type == "integer":
            sample[field] = 1
        elif field_type == "boolean":
            sample[field] = True
        else:
            sample[field] = "valor de prueba"
    return sample


def generic_create_handler(erp: FakeERPAdapter, args: dict[str, Any]) -> str:
    """The one hand-written, human-authored sandbox handler this module
    ever executes. Creates a record with exactly the arguments given, in
    a throwaway sandbox model named after the proposal -- never a real
    adapter (run_in_sandbox constructs and discards a fresh
    FakeERPAdapter per call, this function never sees Odoo)."""
    return erp.create("demo_proposals", dict(args))


class SkillAdmin:
    """Owns the in-memory proposals registry for one server process."""

    def __init__(self) -> None:
        # Found live, not assumed: plain `sqlite://` opens a NEW, empty
        # in-memory database on every connection, and FastAPI runs each
        # sync endpoint in its own worker thread -- the schema created
        # here would vanish before the next request ("no such table:
        # registered_skills"). StaticPool pins every connection, from
        # every thread, to the one physical in-memory database, which is
        # the documented SQLAlchemy pattern for a shared in-memory SQLite
        # DB across threads (see registry.py's own test fixture for the
        # simpler single-threaded case, where this is not needed).
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        create_registry_schema(engine)
        self._registry = SqlSkillRegistry(engine)
        self._proposals: list[tuple[str, str]] = []  # (skill_id, version)

    def propose(
        self, payload: dict[str, Any], sample_arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """CU-02 steps 1-5, delegated whole to skill_proposal.propose_skill:
        validate -> sandbox-test -> register at DRAFT -> VALIDATED ->
        TESTED. Raises SkillAdminError (never a raw exception) if the
        contract is malformed or the sandbox test genuinely fails --
        both are real outcomes the frontend must show honestly, not
        paper over."""
        try:
            skill = propose_skill(
                self._registry,
                payload,
                generic_create_handler,
                sample_arguments,
                "demo_proposals",
            )
        except ProposalRejected as exc:
            raise SkillAdminError(str(exc)) from exc

        self._proposals.append((skill.skill_id, skill.version))
        return self._describe(skill.skill_id, skill.version)

    def approve(self, skill_id: str, version: str, *, approver: str) -> dict[str, Any]:
        # skill_proposal.approve_and_activate does APPROVED -> ACTIVE in
        # one call (CU-02 steps 6-7); the lifecycle graph itself is what
        # refuses this if the proposal never reached TESTED.
        try:
            approve_and_activate(self._registry, skill_id, version, approver=approver)
        except ProposalRejected as exc:
            raise SkillAdminError(str(exc)) from exc
        return self._describe(skill_id, version)

    def list_proposals(self) -> list[dict[str, Any]]:
        return [self._describe(sid, ver) for sid, ver in self._proposals]

    def _describe(self, skill_id: str, version: str) -> dict[str, Any]:
        skill: SkillDefinition = self._registry.get(skill_id, version)
        state = self._registry.state_of(skill_id, version)
        history = self._registry.history(skill_id, version)
        return {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "description": skill.description,
            "risk_class": skill.risk_class.value,
            "state": state.value,
            # Full schema (types, not just names) so the frontend can render
            # a labelled, typed field per parameter -- a business user
            # reading "Nombre del cliente (texto)" instead of the raw key
            # "customer_name" and the raw JSON.
            "input_schema": skill.input_schema,
            "history": [
                {
                    "from": h["from_state"],
                    "to": h["to_state"],
                    "actor": h["actor"],
                    "reason": h["reason"],
                }
                for h in history
            ],
        }
