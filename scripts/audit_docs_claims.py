"""Segunda auditoria: afirmaciones contradictorias entre documentos."""

import pathlib
import re
import subprocess

from erp_agent_os.catalog import CATALOG

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = [*sorted((ROOT / "docs").glob("*.md")), ROOT / "README.md"]

print("=" * 70)
print("1. AFIRMACIONES QUE DEBEN APARECER CON SU MATIZ")
print("=" * 70)

# afirmacion -> matiz que SIEMPRE debe acompañarla
PARES = [
    (
        "TF-IDF gana",
        ("texto real", "plantillad", "corpus", "actualiz"),
        "TF-IDF gana solo sobre el corpus plantillado",
    ),
    (
        "8×",
        ("n = 9", "n=9", "IC", "intervalo", "0,435", "estimación puntual"),
        "el 8x descansa en n=9",
    ),
    (
        "0,889 a 0,111",
        ("léxic", "lexic", "n = 9", "distribución", "distribucion"),
        "false allow lleva su matiz de deteccion lexica",
    ),
]

for aguja, matices, nota in PARES:
    for doc in DOCS:
        texto = doc.read_text(encoding="utf-8")
        for m in re.finditer(re.escape(aguja), texto):
            ventana = texto[max(0, m.start() - 700) : m.end() + 700].lower()
            if not any(x.lower() in ventana for x in matices):
                linea = texto[: m.start()].count("\n") + 1
                print(
                    f"  {doc.relative_to(ROOT)}:{linea} — '{aguja}' sin matiz ({nota})"
                )

print()
print("=" * 70)
print("2. EL CODIGO DICE LO MISMO QUE LOS DOCUMENTOS")
print("=" * 70)

# numero de escenas de la demo
demo = (ROOT / "scripts" / "demo_completa.py").read_text(encoding="utf-8")
n_escenas = len(re.findall(r"^def escena_\d+", demo, re.M))
print(f"  escenas en demo_completa.py: {n_escenas}")
for doc in DOCS:
    texto = doc.read_text(encoding="utf-8")
    for m in re.finditer(r"(\d+)\s+(?:controles|escenas)", texto):
        if int(m.group(1)) != n_escenas:
            linea = texto[: m.start()].count("\n") + 1
            print(f"    !! {doc.relative_to(ROOT)}:{linea} dice {m.group(0)}")

# numero de skills
#
# Counted from the imported catalog, not by grepping the source for
# "SkillDefinition(". That literal appears exactly ONCE -- inside the
# private `_skill(...)` factory every entry goes through -- so the old
# heuristic printed "1" for a 12-skill catalog and could never have
# detected the catalog changing size, which is the only thing it was
# there to check. CLAUDE.md section 11 fixes the count at 12.
n_skills = len(CATALOG)
print(f"  skills en catalog.py: {n_skills}")
# Deliberately NOT scanned against the docs the way the scene and test
# counts are. "N skills" appears in Spanish prose that is not a claim
# about catalog size at all -- "2 de las 12 skills mapeadas a Odoo",
# "las 10 skills sin handler registrado" -- so a regex over it reports
# drift that does not exist. A check that cries wolf is worse than no
# check; the authoritative count above is what this section owes.

# tests
res = subprocess.run(
    ["uv", "run", "python", "-m", "pytest", "--collect-only", "-q"],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
collected = re.search(r"(\d+) tests? collected", res.stdout)
n_tests = int(collected.group(1)) if collected else None
print(f"  tests recolectados: {n_tests}")
for doc in DOCS:
    texto = doc.read_text(encoding="utf-8")
    for claim in re.finditer(r"(\d{3})\s+(?:tests|passed)", texto):
        if n_tests and int(claim.group(1)) != n_tests:
            linea = texto[: claim.start()].count("\n") + 1
            print(f"    !! {doc.relative_to(ROOT)}:{linea} dice {claim.group(0)}")

print()
print("=" * 70)
print("3. ENLACES ROTOS ENTRE DOCUMENTOS")
print("=" * 70)
for doc in DOCS:
    texto = doc.read_text(encoding="utf-8")
    for m in re.finditer(r"\]\(([^)#]+\.md)[^)]*\)", texto):
        destino = m.group(1)
        cand = (doc.parent / destino).resolve()
        if not cand.exists():
            cand2 = (ROOT / destino).resolve()
            if not cand2.exists():
                linea = texto[: m.start()].count("\n") + 1
                print(f"  {doc.relative_to(ROOT)}:{linea} -> {destino} NO EXISTE")
    for m in re.finditer(r"`(scripts/[\w_]+\.py)`", texto):
        if not (ROOT / m.group(1)).exists():
            linea = texto[: m.start()].count("\n") + 1
            print(f"  {doc.relative_to(ROOT)}:{linea} -> {m.group(1)} NO EXISTE")
print("  (sin salida = todos los enlaces resuelven)")
