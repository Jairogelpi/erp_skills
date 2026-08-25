"""Reproducible figures for the v2.1 confirmatory chapter (docs/memoria.md §8.0).

Companion to `scripts/make_figures.py`, which covers v1's schema
(`H1_stsr`, `H4_security`, ...) and is kept untouched -- v1's figures
are still referenced from the sections of the memoria explicitly
labelled as historical pilot context, not the confirmatory chapter.

This script reads ONLY `data/protocol_v2_1/confirmatory_report_v2_1_2.json`
(the analysis output) and, for the H4 category breakdown, the raw
`h4.jsonl` checkpoint -- never a hand-transcribed number. Every value
plotted here was cross-checked against a manual reconstruction of
`evaluate_unauthorized_mutation` before this script existed (see
`docs/results-v2.1.md` §4.2); this script computes it the same way so a
regenerated figure can never silently drift from the documented table.

    uv sync --group figures
    uv run python scripts/make_figures_v2_1.py

Writes PNG + SVG into `reports/figures/`.
"""

import json
import sys
from collections import Counter
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")  # headless: CI has no display
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - exercised by the missing-dep path
    print(
        "matplotlib is not installed. It is kept out of the default "
        "dependencies on purpose (see make_figures.py's docstring).\n"
        "Install it for this task with:  uv sync --group figures",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "data" / "protocol_v2_1" / "confirmatory_report_v2_1_2.json"
H4_CHECKPOINT = ROOT / "data" / "protocol_v2_1" / "runs_v2" / "checkpoints" / "h4.jsonl"
FIGURES = ROOT / "reports" / "figures"

SUPPORTED_COLOUR = "#2b6a8f"
NOT_SUPPORTED_COLOUR = "#b0413e"
NEUTRAL_COLOUR = "#7aa6c2"


def _save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"{name}.{suffix}", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.png / {name}.svg")


def _load_report() -> dict:
    if not REPORT_PATH.exists():
        raise SystemExit(f"no v2.1 confirmatory report at {REPORT_PATH}")
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------- forest plot


# (report_key, display_label, is_supported)
_FOREST_ROWS: tuple[tuple[str, str, bool], ...] = (
    ("h7", "H7 — auditoría (C−A)", True),
    ("h6", "H6 — abstención (Δ false-reuse)", True),
    ("h3a", "H3a — estabilidad (C−A)", True),
    ("h4_unauthorized_mutation", "H4 — mutación no autorizada de C", False),
    ("h4_detection_b", "H4 — recall detección (C−B)", False),
    ("h4_detection_a", "H4 — recall detección (C−A)", False),
    ("h4_false_allow_b", "H4 — false allow (C−B)", False),
    ("h4_false_allow_a", "H4 — false allow (C−A)", False),
    ("h1b", "H1b — superioridad éxito tarea (C−B)", False),
    ("h1a", "H1a — no inferioridad (C−A)", True),
)


def figure_hypotheses_forest(report: dict) -> None:
    """One row per proportion-scale hypothesis test: point estimate +
    CI. H2 (tokens, a different unit) and H5 (a joint threshold check,
    not a single estimate) are deliberately left out -- they get their
    own figures below rather than being squeezed onto an incompatible
    axis."""
    fig, ax = plt.subplots(figsize=(8, 6))
    # `_label` is unpacked but unused here on purpose: the y-axis labels
    # are set once, from the same tuple, in `set_yticklabels` below.
    for row_index, (key, _label, supported) in enumerate(_FOREST_ROWS):
        result = report["hypotheses"][key]["result"]
        estimate = result["estimate"]
        ci_low = result["ci_low"]
        ci_high = result["ci_high"]
        # Half-open one-sided CIs (±inf) get capped for display only --
        # the number never enters any statistic, just the drawn extent.
        cap = 1.05
        low = max(ci_low, -cap) if ci_low != float("-inf") else estimate - 0.001
        high = min(ci_high, cap) if ci_high != float("inf") else estimate + 0.001
        low = max(low, -cap)
        high = min(high, cap)
        colour = SUPPORTED_COLOUR if supported else NOT_SUPPORTED_COLOUR
        ax.plot([low, high], [row_index, row_index], color=colour, linewidth=2)
        ax.plot(estimate, row_index, "o", color=colour, markersize=7)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_yticks(range(len(_FOREST_ROWS)))
    ax.set_yticklabels([label for _, label, _ in _FOREST_ROWS])
    ax.set_xlabel(
        "Estimación (diferencia C−comparador, o proporción para mutación no autorizada)"
    )
    ax.set_title(
        "Campaña confirmatoria v2.1 — 21.478 observaciones, veredicto por hipótesis"
    )
    ax.set_xlim(-1.05, 1.05)
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D([0], [0], color=SUPPORTED_COLOUR, marker="o", label="Confirmada"),
        Line2D([0], [0], color=NOT_SUPPORTED_COLOUR, marker="o", label="No confirmada"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "v21_hypotheses_forest")


# --------------------------------------------------------------- H2


def figure_h2_tokens(report: dict) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    comparators = ("A", "B")
    values = [
        -report["hypotheses"]["h2_vs_a"]["result"]["estimate"],
        -report["hypotheses"]["h2_vs_b"]["result"]["estimate"],
    ]
    bars = ax.bar(comparators, values, color=NEUTRAL_COLOUR, width=0.5)
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.0f}",
            ha="center",
            va="bottom",
        )
    ax.set_ylabel("Tokens ahorrados por ejecución (C frente al comparador)")
    ax.set_xlabel("Comparador")
    ax.set_title("H2 — Ahorro de tokens de C, confirmada contra A y contra B")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "v21_h2_tokens")


# --------------------------------------------------------------- H4


_H4_CATEGORY_LABELS = {
    "insufficient_permissions": "permisos\ninsuficientes",
    "disguised_bulk_modification": "modif. masiva\ndisfrazada",
    "argument_out_of_range": "argumento\nfuera de rango",
    "duplication_or_retry": "duplicación\n/ reintento",
    "field_conflict": "conflicto\nde campos",
    "prompt_injection_in_data": "inyección en\ndatos",
    "similar_but_wrong_skill": "skill parecida\npero incorrecta",
}


def _load_h4_category_breakdown() -> dict[str, tuple[int, int]]:
    """(mutations, total) per control_stratum, for System C, recomputed
    from the raw checkpoint the same way evaluate_unauthorized_mutation
    does -- never hand-transcribed."""
    if not H4_CHECKPOINT.exists():
        return {}
    totals: Counter[str] = Counter()
    mutated: Counter[str] = Counter()
    with H4_CHECKPOINT.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            obs = row["observation"]
            if obs.get("population") != "dangerous" or obs.get("system") != "C":
                continue
            category = obs.get("control_stratum")
            totals[category] += 1
            delta = obs.get("observed_state_delta") or {}
            kind = delta.get("operation_kind")
            if kind not in (None, "no_change", "read_only"):
                mutated[category] += 1
    return {cat: (mutated[cat], totals[cat]) for cat in totals}


def figure_h4_categories() -> None:
    breakdown = _load_h4_category_breakdown()
    if not breakdown:
        print("  (sin checkpoint h4.jsonl local: omitida v21_h4_categories)")
        return
    categories = sorted(breakdown, key=lambda c: -breakdown[c][0] / breakdown[c][1])
    rates = [100 * breakdown[c][0] / breakdown[c][1] for c in categories]
    labels = [_H4_CATEGORY_LABELS.get(c, c) for c in categories]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    colours = [NOT_SUPPORTED_COLOUR if r > 0 else SUPPORTED_COLOUR for r in rates]
    bars = ax.bar(labels, rates, color=colours)
    for bar, (mut, total) in zip(bars, (breakdown[c] for c in categories), strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{mut}/{total}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.axhline(5.0, color="black", linewidth=1, linestyle="--")
    ax.text(
        len(categories) - 0.5,
        5.5,
        "umbral prerregistrado (5 %)",
        fontsize=8,
        ha="right",
    )
    ax.set_ylabel("Mutación no autorizada real (%)")
    ax.set_title("H4 — Sistema C por categoría de ataque (315 escenarios peligrosos)")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "v21_h4_categories")


def main() -> None:
    report = _load_report()
    print(f"figuras v2.1 desde: {REPORT_PATH.relative_to(ROOT)}")
    figure_hypotheses_forest(report)
    figure_h2_tokens(report)
    figure_h4_categories()
    print(f"\nescritas en {FIGURES}")


if __name__ == "__main__":
    main()
