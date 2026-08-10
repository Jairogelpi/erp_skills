"""Reproducible figures for the results chapter (§27, §31, §32).

§27 names Matplotlib for "las figuras reproducibles del núcleo" and
§32 lists experimental results among the deliverables; §31 describes a
Tableau dashboard as a post-core delivery. This script covers the first
two: every figure is regenerated from the committed JSON, so no chart
in the memoria is a screenshot nobody can reproduce.

The Tableau workbook itself is manual work this does not replace --
`scripts/export_results.py` produces the CSV tables it would read.

    uv sync --group figures
    uv run python scripts/make_figures.py

Writes PNG + SVG into `reports/figures/`. Both formats on purpose: PNG
for slides, SVG because a vector figure survives being scaled into a
printed memoria.

**matplotlib lives in its own dependency group, not in the defaults.**
Installing it into the environment mypy analyses triggers an internal
mypy 1.15 crash while serializing its cache, against this project's
numpy `follow_imports = "skip"` override. Isolating it keeps
`make typecheck` working in CI and still makes the figures
reproducible on demand -- the committed PNG/SVG files are the
deliverable either way.
"""

import json
import sys
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")  # headless: CI has no display
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - exercised by the missing-dep path
    print(
        "matplotlib is not installed. It is kept out of the default "
        "dependencies on purpose (see this module's docstring).\n"
        "Install it for this task with:  uv sync --group figures",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIGURES = ROOT / "reports" / "figures"

SYSTEMS = ("A", "B", "C")
COLOURS = {"A": "#b0b0b0", "B": "#7aa6c2", "C": "#2b6a8f"}
RUNS = (
    ("confirmatorio", "experiment_results.json"),
    ("parseo real", "experiment_results_real_parser.json"),
)


def _load() -> dict[str, dict]:
    reports = {}
    for label, name in RUNS:
        path = DATA / name
        if path.exists():
            reports[label] = json.loads(path.read_text(encoding="utf-8"))
    if not reports:
        raise SystemExit("no experiment results found; run the experiment first")
    return reports


def _save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"{name}.{suffix}", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.png / {name}.svg")


def _grouped_bars(ax, reports, extract, ylabel, title):
    labels = list(reports)
    width = 0.8 / len(labels)
    for offset, label in enumerate(labels):
        values = [extract(reports[label], s) for s in SYSTEMS]
        positions = [i + offset * width for i in range(len(SYSTEMS))]
        bars = ax.bar(positions, values, width, label=label, alpha=0.9)
        for bar, value in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.3f}" if value < 10 else f"{value:.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax.set_xticks([i + width * (len(labels) - 1) / 2 for i in range(len(SYSTEMS))])
    ax.set_xticklabels([f"Sistema {s}" for s in SYSTEMS])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)


def figure_stsr(reports) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _grouped_bars(
        ax,
        reports,
        lambda r, s: r["H1_stsr"]["stsr"][s],
        "STSR",
        "H1 — Strict Task Success Rate",
    )
    ax.set_ylim(0, 1)
    _save(fig, "h1_stsr")


def figure_security(reports) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _grouped_bars(
        ax,
        reports,
        lambda r, s: r["H4_security"][s]["false_allow_rate"],
        "False allow rate",
        "H4 — Ejecuciones inseguras permitidas (menor es mejor)",
    )
    ax.set_ylim(0, 1)
    _save(fig, "h4_false_allow")


def figure_tokens(reports) -> None:
    usable = {
        label: report
        for label, report in reports.items()
        if any(
            report.get("H2_tokens", {})
            .get("totals", {})
            .get(s, {})
            .get("mean_tokens_per_execution")
            for s in SYSTEMS
        )
    }
    if not usable:
        print("  (sin datos de tokens: omitida h2_tokens)")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    _grouped_bars(
        ax,
        usable,
        lambda r, s: r["H2_tokens"]["totals"][s]["mean_tokens_per_execution"],
        "Tokens por ejecución",
        "H2 — Coste en tokens (menor es mejor)",
    )
    _save(fig, "h2_tokens")


def figure_traceability(reports) -> None:
    usable = {
        label: report
        for label, report in reports.items()
        if report.get("H7_traceability")
    }
    if not usable:
        print("  (sin datos de trazabilidad: omitida h7_traceability)")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    _grouped_bars(
        ax,
        usable,
        lambda r, s: r["H7_traceability"]["mean_score"][s],
        "Puntuación de rúbrica (0–1)",
        "H7 — Trazabilidad",
    )
    ax.set_ylim(0, 1)
    _save(fig, "h7_traceability")


def figure_segmentation(reports) -> None:
    """STSR by risk class -- where the governance gap actually lives."""
    label, report = next(iter(reports.items()))
    strata = sorted(report["segmentation"]["risk_class"]["C"])
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.8 / len(SYSTEMS)
    for offset, system in enumerate(SYSTEMS):
        values = [
            report["segmentation"]["risk_class"][system][k]["stsr"] for k in strata
        ]
        positions = [i + offset * width for i in range(len(strata))]
        ax.bar(
            positions, values, width, label=f"Sistema {system}", color=COLOURS[system]
        )
    ax.set_xticks([i + width for i in range(len(strata))])
    ax.set_xticklabels(strata)
    ax.set_ylim(0, 1)
    ax.set_ylabel("STSR")
    ax.set_xlabel("Clase de riesgo")
    ax.set_title(f"STSR por clase de riesgo ({label})")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "stsr_by_risk_class")


def main() -> None:
    reports = _load()
    print(f"figuras desde: {', '.join(reports)}")
    figure_stsr(reports)
    figure_security(reports)
    figure_tokens(reports)
    figure_traceability(reports)
    figure_segmentation(reports)
    print(f"\nescritas en {FIGURES}")


if __name__ == "__main__":
    main()
