"""Three deterministic surface renderers for ERP-Skills-Bench-Proc v2.1.

docs/tfm-closure-no-human-v2.1.md section 5.3: three formulations per
scenario -- S1 controlled-Spanish template, S2 grammar/order/noise
variation, S3 frozen lexical composition from a synonym bank. None of
them determines gold: they only verbalize a ScenarioSpec whose truth
already exists (scenarios_v2_1.build_gold). No free LLM in the
confirmatory arm (S3 is a deterministic composition, not a generative
paraphrase).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from erp_agent_os.bench_intents import INTENTS, IntentSpec
from erp_agent_os.scenarios_v2_1 import CASE_KIND_NO_SKILL, ScenarioSpec

INTENTS_BY_ID: dict[str, IntentSpec] = {intent.intent_id: intent for intent in INTENTS}

_POLITE_PREFIXES = ("Por favor, ", "Necesito que ", "¿Puedes ")
_ABBREVIATIONS = {"euros": "€", "expected": "esperado"}

_NO_SKILL_TEMPLATES: dict[str, str] = {
    "crm": "¿Cuándo fue la última vez que hablamos con este cliente?",
    "contacts": "Envíale un mensaje de cumpleaños al contacto.",
    "sales": "Calcula la comisión del comercial de esta cuenta.",
    "purchasing": "Negocia un descuento por volumen con el proveedor.",
    "product": "Diseña una nueva ficha de producto desde cero.",
    "inventory": "Programa una auditoría física del almacén.",
    "tasks": "Reasigna todas las tareas abiertas del equipo.",
    "billing": "Explica por qué subió el IVA este trimestre.",
}


class SurfaceKind(str, Enum):
    S1_TEMPLATE = "S1"
    S2_GRAMMAR = "S2"
    S3_COMPOSITION = "S3"


class SurfaceRejectedError(ValueError):
    """Raised when a rendered surface violates a protected-slot rule."""


@dataclass(frozen=True)
class Surface:
    scenario_id: str
    kind: str
    text: str


def _slot_values(scenario: ScenarioSpec) -> list[str]:
    return [str(value) for value in scenario.arguments.values()]


def _render_s1(scenario: ScenarioSpec, intent: IntentSpec) -> str:
    return intent.template.format(**scenario.arguments)


def _render_s2(scenario: ScenarioSpec, intent: IntentSpec) -> str:
    base = intent.template.format(**scenario.arguments)
    prefix = _POLITE_PREFIXES[hash(scenario.scenario_id) % len(_POLITE_PREFIXES)]
    text = prefix + base[0].lower() + base[1:]
    for original, replacement in _ABBREVIATIONS.items():
        text = text.replace(original, replacement)
    return text


_S3_OPENERS: dict[str, str] = {
    "create": "Da de alta lo siguiente en el sistema",
    "update": "Modifica el registro correspondiente con estos datos",
    "read": "Consulta la información siguiente",
    "none": "",
}


def _render_s3(scenario: ScenarioSpec, intent: IntentSpec) -> str:
    # Deliberately does NOT include canonical_intent, family or any other
    # skill-identifying token: scenario.expected_skill is a prefix of
    # canonical_intent (e.g. "crm.create_opportunity" is a prefix of
    # "crm.create_opportunity.new"), so embedding it here would leak the
    # gold skill id straight into the request text a system is evaluated
    # against -- caught by validate_surface's own leak check on the first
    # run of this renderer, not assumed safe.
    del intent
    opener = _S3_OPENERS.get(scenario.operation, "")
    slot_phrase = "; ".join(
        f"{field}: {value}" for field, value in scenario.arguments.items()
    )
    return f"{opener} ({slot_phrase})" if opener else slot_phrase


def render_surface(scenario: ScenarioSpec, kind: SurfaceKind) -> Surface:
    if scenario.case_kind == CASE_KIND_NO_SKILL:
        text = _NO_SKILL_TEMPLATES[scenario.family]
        if kind is SurfaceKind.S2_GRAMMAR:
            text = "Por favor, " + text[0].lower() + text[1:]
        elif kind is SurfaceKind.S3_COMPOSITION:
            text = f"Solicitud fuera de catálogo: {text}"
        return Surface(scenario.scenario_id, kind.value, text)

    intent = INTENTS_BY_ID[scenario.canonical_intent]
    renderer = {
        SurfaceKind.S1_TEMPLATE: _render_s1,
        SurfaceKind.S2_GRAMMAR: _render_s2,
        SurfaceKind.S3_COMPOSITION: _render_s3,
    }[kind]
    return Surface(scenario.scenario_id, kind.value, renderer(scenario, intent))


def render_all(scenario: ScenarioSpec) -> tuple[Surface, Surface, Surface]:
    return (
        render_surface(scenario, SurfaceKind.S1_TEMPLATE),
        render_surface(scenario, SurfaceKind.S2_GRAMMAR),
        render_surface(scenario, SurfaceKind.S3_COMPOSITION),
    )


def validate_surface(
    scenario: ScenarioSpec, surface: Surface, *, v1_texts: frozenset[str] = frozenset()
) -> None:
    """Rejects a surface that loses/alters a protected slot, leaks the
    skill ID or the expected decision word, or duplicates v1/development
    text. Raises SurfaceRejectedError; never silently accepts."""
    if scenario.case_kind != CASE_KIND_NO_SKILL:
        for value in _slot_values(scenario):
            if value not in surface.text:
                raise SurfaceRejectedError(
                    f"{surface.kind} for {scenario.scenario_id} lost protected "
                    f"slot value {value!r}"
                )
    if scenario.expected_skill and scenario.expected_skill in surface.text:
        raise SurfaceRejectedError(
            f"{surface.kind} for {scenario.scenario_id} leaks the skill id"
        )
    for forbidden_word in ("ALLOW", "DENY", "REQUIRE_APPROVAL", "SIMULATE", "ABSTAIN"):
        if re.search(rf"\b{forbidden_word}\b", surface.text):
            raise SurfaceRejectedError(
                f"{surface.kind} for {scenario.scenario_id} leaks the expected "
                f"decision {forbidden_word!r}"
            )
    normalized = surface.text.strip().casefold()
    if normalized in v1_texts:
        raise SurfaceRejectedError(
            f"{surface.kind} for {scenario.scenario_id} duplicates v1/development text"
        )


def primary_surface_kind(scenario_id: str, ordinal: int) -> SurfaceKind:
    """Deterministic S1/S2/S3 rotation, stratified per intent by
    `ordinal` (the scenario's position within its own intent's slots),
    so each intent's small set of scenarios is spread across renderers
    rather than always picking the same one."""
    del scenario_id
    return (
        SurfaceKind.S1_TEMPLATE,
        SurfaceKind.S2_GRAMMAR,
        SurfaceKind.S3_COMPOSITION,
    )[ordinal % 3]
