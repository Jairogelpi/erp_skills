"""Contrasta las cifras publicadas en los .md contra los data/*.json."""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


vigente = load("experiment_results_real_parser.json")
openrouter = load("experiment_results.json")
groq_dados = load("experiment_results_groq_given_args.json")
inject = load("injection_resistance_results.json")

print("=" * 70)
print("VERDAD (data/*.json)")
print("=" * 70)
print("VIGENTE (Groq, parseo real + normalizacion):")
print(
    "  STSR         :", {k: round(v, 3) for k, v in vigente["H1_stsr"]["stsr"].items()}
)
cb = vigente["H1_stsr"]["C_minus_B"]
ic = [round(x, 3) for x in cb["ci95"]]
print(f"  C-B          : {cb['point']:.3f} IC{ic} p={cb['holm_p']:.4f}")
print(
    "  false allow  :",
    {k: round(v["false_allow_rate"], 3) for k, v in vigente["H4_security"].items()},
)
print(
    "  tokens/ejec  :",
    {
        k: round(v["mean_tokens_per_execution"], 1)
        for k, v in vigente["H2_tokens"]["totals"].items()
    },
)
print(
    "  trazabilidad :",
    {k: round(v, 3) for k, v in vigente["H7_traceability"]["mean_score"].items()},
)
print(
    "  H5 C top1    :",
    round(vigente["H5_retrieval"]["C"]["top1"], 3),
    "| abstencion:",
    round(vigente["H5_retrieval"]["C"]["abstention_rate"], 3),
)
print()
print(
    "OpenRouter (parseo regalado):",
    {k: round(v, 3) for k, v in openrouter["H1_stsr"]["stsr"].items()},
    "| false allow A:",
    round(openrouter["H4_security"]["A"]["false_allow_rate"], 3),
)
print(
    "Groq argumentos dados      :",
    {k: round(v, 3) for k, v in groq_dados["H1_stsr"]["stsr"].items()},
    "| false allow A:",
    round(groq_dados["H4_security"]["A"]["false_allow_rate"], 3),
)
print("Inyeccion                  :", inject["total_unauthorized_mutations"], "/ 1530")

# ---------------------------------------------------------------- doc scan
print()
print("=" * 70)
print("CIFRAS SOSPECHOSAS EN LA DOCUMENTACION")
print("=" * 70)

docs = [*sorted((ROOT / "docs").glob("*.md")), ROOT / "README.md", ROOT / "CLAUDE.md"]

# cifras que ya no son vigentes y no deberian aparecer sin contexto de "superado"
OBSOLETAS = {
    "0,558": "STSR de C en la ejecucion 3 (superada por 0,633)",
    "+0,075": "C-B no significativo de la ejecucion 3 (superado por +0,150)",
    "0,212": "p de la ejecucion 3",
    "trece defectos": "son quince",
    "catorce defectos": "son quince",
    "384 tests": "son 393",
    "274 passed": "son 393",
    "298 passed": "son 393",
    "305 passed": "son 393",
    "342 passed": "son 393",
    "386 passed": "son 393",
    "391 passed": "son 393",
    "cuatro corridas": "son cinco",
    "las tres ejecuciones": "son cinco",
}

CONTEXTO_OK = (
    "superad",
    "ejecución 3",
    "ejecucion 3",
    "anterior",
    "previa",
    "histórica",
    "historica",
    "quedan superados",
    "bitácora",
    "bitacora",
)

for doc in docs:
    texto = doc.read_text(encoding="utf-8")
    hallazgos = []
    for aguja, motivo in OBSOLETAS.items():
        for m in re.finditer(re.escape(aguja), texto):
            ini = max(0, m.start() - 260)
            ventana = texto[ini : m.end() + 160].lower()
            if any(c.lower() in ventana for c in CONTEXTO_OK):
                continue
            linea = texto[: m.start()].count("\n") + 1
            hallazgos.append(f"    L{linea}: '{aguja}' -> {motivo}")
    if hallazgos:
        print(f"\n  {doc.relative_to(ROOT)}")
        for h in sorted(set(hallazgos)):
            print(h)

print()
print("(CLAUDE.md es bitacora append-only: sus entradas antiguas son historia,")
print(" no contradiccion. Se revisa aparte.)")
