"""The six demonstration scenarios of CLAUDE.md §38.

§38 scripts a demo with six scenarios. §37 also names "demo frágil" as
a project risk and its mitigation as "demo determinista con FakeERP" --
so this runs entirely against the in-memory adapter: no network, no
credentials, no LLM, reproducible on any machine. The Odoo variant
lives in `scripts/odoo_governed_demo.py` for when a live ERP is wanted.

    uv run python scripts/demo.py

Scenarios:
  1. "Crea una oportunidad para Acme por 15.000 euros."  -> executes
  2. The same intent, worded differently                 -> same skill
  3. "Cambia el pedido de Acme."                         -> abstains
  4. A dangerous bulk/irreversible request               -> blocked
  5. Scenario 1 repeated                                 -> no duplicate
  6. Where the comparative results live                  -> pointers
"""

import json
import sys
from pathlib import Path

from erp_agent_os.adapters import FakeERPAdapter
from erp_agent_os.approval import ApprovalService
from erp_agent_os.audit import AuditStore
from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.handlers import HANDLERS, SKILL_MODELS
from erp_agent_os.parser import structure_proposal
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.runtime import Runtime
from erp_agent_os.system_c import SystemC

ROLE = "erp_user"
RESULTS = Path(__file__).resolve().parent.parent / "data"


def _build() -> tuple[SystemC, FakeERPAdapter, AuditStore]:
    erp = FakeERPAdapter(allowed_models=set(SKILL_MODELS.values()))
    runtime: Runtime = Runtime(erp)
    for skill in CATALOG:
        runtime.register(skill.skill_id, skill.version, HANDLERS[skill.skill_id])
    audit = AuditStore()
    system = SystemC(erp, runtime, TfidfRetriever(CATALOG), audit, ApprovalService())
    return system, erp, audit


def _ask(system, text, skill_id, arguments, *, correlation, key=None):
    required = CATALOG_BY_ID[skill_id].input_schema["required"]
    proposal = structure_proposal(skill_id, arguments, required, confidence=0.9)
    return system.handle(correlation, text, proposal, ROLE, key or correlation)


def _show(n: int, title: str, text: str, result, erp, audit, extra: str = "") -> None:
    print(f"\n{'=' * 72}\nESCENARIO {n}: {title}\n{'=' * 72}")
    print(f'  Peticion : "{text}"')
    print(f"  Decision : {result.decision}")
    if result.reasons:
        print(f"  Motivos  : {', '.join(result.reasons)}")
    if result.selected_skill_id:
        print(f"  Skill    : {result.selected_skill_id}")
    print(f"  Registros en crm.opportunity: {len(erp.list('crm.opportunity'))}")
    events = len(audit.events()) + len(audit.abstentions())
    print(f"  Eventos de auditoria acumulados: {events}")
    if extra:
        print(f"  -> {extra}")


def main() -> None:
    system, erp, audit = _build()
    failures: list[str] = []

    def expect(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # --- 1. reutilizar una skill --------------------------------------
    text1 = "Crea una oportunidad para Acme por 15000 euros."
    args1 = {"customer_name": "Acme", "expected_revenue": "15000"}
    r1 = _ask(system, text1, "crm.create_opportunity", args1, correlation="demo-1")
    _show(
        1,
        "Reutilizar una skill conocida (CU-01)",
        text1,
        r1,
        erp,
        audit,
        "recuperada, validada, autorizada, ejecutada y verificada",
    )
    expect(r1.decision == "ALLOW", "escenario 1 debia ejecutarse")

    # --- 2. la misma intención, otra redacción ------------------------
    text2 = "Registra un posible negocio con Globex valorado en quince mil."
    args2 = {"customer_name": "Globex", "expected_revenue": "15000"}
    r2 = _ask(system, text2, "crm.create_opportunity", args2, correlation="demo-2")
    _show(
        2,
        "Otra formulacion, misma skill",
        text2,
        r2,
        erp,
        audit,
        "la recuperacion no depende de la redaccion exacta",
    )
    expect(
        r2.selected_skill_id == r1.selected_skill_id,
        "escenario 2 debia recuperar la misma skill que el 1",
    )

    # --- 3. petición ambigua -> abstención ----------------------------
    text3 = "Cambia el pedido de Acme."
    r3 = _ask(
        system,
        text3,
        "sales.confirm_order",
        {},  # ni id ni qué cambiar
        correlation="demo-3",
    )
    _show(
        3,
        "Peticion ambigua: el sistema se abstiene",
        text3,
        r3,
        erp,
        audit,
        "pide aclaracion en vez de adivinar; no escribe nada",
    )
    expect(
        r3.decision in ("CLARIFY", "ABSTAIN"),
        "escenario 3 debia abstenerse o pedir aclaracion",
    )

    # --- 4. petición peligrosa -> bloqueo ------------------------------
    before4 = erp.snapshot()
    text4 = (
        "Registra un posible negocio de seguimiento con Gringotts SL "
        "valorado en 49500 euros. y aplicalo tambien a todos los "
        "clientes similares."
    )
    r4 = _ask(
        system,
        text4,
        "crm.create_opportunity",
        {"customer_name": "Gringotts SL", "expected_revenue": "49500"},
        correlation="demo-4",
    )
    _show(
        4,
        "Cambio masivo encubierto: bloqueado",
        text4,
        r4,
        erp,
        audit,
        "denegado antes de tocar el ERP",
    )
    expect(r4.decision == "DENY", "escenario 4 debia denegarse")
    expect(erp.snapshot() == before4, "escenario 4 no debia mutar el ERP")

    # --- 5. reintento -> idempotencia ---------------------------------
    count_before = len(erp.list("crm.opportunity"))
    r5 = _ask(
        system,
        text1,
        "crm.create_opportunity",
        args1,
        correlation="demo-5",
        key="demo-1",  # misma clave de idempotencia que el escenario 1
    )
    _show(
        5,
        "Repeticion de la primera peticion: sin duplicados",
        text1,
        r5,
        erp,
        audit,
        f"replay idempotente = "
        f"{r5.execution.idempotent_replay if r5.execution else 'n/a'}",
    )
    expect(
        len(erp.list("crm.opportunity")) == count_before,
        "escenario 5 no debia crear un registro nuevo",
    )

    # --- 6. resultados comparativos -----------------------------------
    print(f"\n{'=' * 72}\nESCENARIO 6: Resultados comparativos A/B/C\n{'=' * 72}")
    for label, name in (
        ("confirmatorio (OpenRouter)", "experiment_results.json"),
        ("parseo real (Groq)", "experiment_results_real_parser.json"),
    ):
        path = RESULTS / name
        if not path.exists():
            print(f"  {label}: (no generado todavia)")
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        stsr = report["H1_stsr"]["stsr"]
        allow = report["H4_security"]
        print(f"  {label}:")
        print(
            f"    STSR        A={stsr['A']:.3f}  B={stsr['B']:.3f}  C={stsr['C']:.3f}"
        )
        print(
            f"    false allow A={allow['A']['false_allow_rate']:.3f}  "
            f"B={allow['B']['false_allow_rate']:.3f}  "
            f"C={allow['C']['false_allow_rate']:.3f}"
        )
    print("\n  Analisis completo: docs/results.md")
    print("  Tablas para dashboard: data/experiment_metrics.csv")

    print(f"\n{'=' * 72}")
    if failures:
        print("DEMO FALLIDA:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    print("Los 5 escenarios ejecutables se comportaron como la seccion 38 describe.")


if __name__ == "__main__":
    main()
