"""Does enriched routing text generalize to authors who never saw the catalog?

`docs/product-viability.md` §7.4 found that enriching a skill's one-line
description lifts TF-IDF routing from 0.455 to 0.886 Top-1 on real text,
at zero token cost. That result carried one honest caveat that no amount
of re-analysis could remove: **all 120 requests came from one person in
one sitting with the catalog visible**, so the enrichment was only ever
shown to generalize within that author's own style.

This script removes that caveat by borrowing a corpus that has what ours
lacks: many authors, identified. MASSIVE (Amazon, 2022, CC-BY-4.0),
Spanish `es-ES` split -- 16.521 utterances, 60 intents, **20 identified
crowdworkers**. The design mirrors the ERP setup:

  - **catalog**: the 10 intents of the calendar / email / lists
    scenarios, standing in for a small business skill catalog;
  - **out of catalog**: the other 50 intents, where the right answer is
    "I do not handle this";
  - **authors split in two disjoint halves**: enrichment is built ONLY
    from utterances of the dev authors, and every reported number comes
    ONLY from held-out authors. No person appears on both sides.

The enrichment is built **mechanically** (append k real example
utterances to the description) rather than hand-written, which both
removes the author's judgement from the result and answers the product
question directly: how many collected examples per skill does routing
need? The output is a curve over k = 0, 1, 3, 5, 10, 20.

Non-ERP domain by construction: this tests the **mechanism** (thin
description -> poor lexical routing; examples -> better), not the ERP
product. Stated as such wherever it is cited.

    uv run python scripts/eval_enrichment_across_authors.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from erp_agent_os.catalog import CATALOG
from erp_agent_os.retrieval import TfidfRetriever

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "massive_es.jsonl"
OUTPUT = ROOT / "data" / "enrichment_across_authors.json"
ROLE = "erp_user"
SEED = 20260811
K_VALUES = (0, 1, 3, 5, 10, 20)

CATALOG_SCENARIOS = ("calendar", "email", "lists")

# One-line descriptions, deliberately written the way a developer writes
# a catalog entry: from what the operation *does*, without having seen
# how users ask for it. That is exactly the state ERP Agent OS's own
# catalog is in, and the condition this experiment is testing.
THIN: dict[str, str] = {
    "calendar_set": "Crea un evento en el calendario.",
    "calendar_query": "Consulta los eventos del calendario.",
    "calendar_remove": "Elimina un evento del calendario.",
    "email_query": "Consulta los correos recibidos.",
    "email_sendemail": "Envia un correo electronico.",
    "email_querycontact": "Consulta los datos de un contacto.",
    "email_addcontact": "Añade un contacto nuevo.",
    "lists_query": "Consulta una lista.",
    "lists_createoradd": "Crea una lista o añade un elemento.",
    "lists_remove": "Elimina un elemento de una lista.",
}


def _load() -> list[dict[str, Any]]:
    if not CORPUS.exists():
        raise SystemExit(
            f"missing {CORPUS}. Download MASSIVE es-ES first (see module docstring)."
        )
    return [
        json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()
    ]


def _skill_for(intent: str, description: str) -> Any:
    """A real SkillDefinition carrying a stand-in description.

    Copies a genuine catalog entry so the retriever sees exactly the
    object type it sees in production; only identity and description
    change.
    """
    return CATALOG[0].model_copy(
        update={"skill_id": f"massive.{intent}", "description": description}
    )


def _build_retriever(intents: list[str], examples: dict[str, list[str]], k: int) -> Any:
    skills = []
    for intent in intents:
        text = THIN[intent]
        if k:
            text = text + " " + " ".join(examples[intent][:k])
        skills.append(_skill_for(intent, text))
    return TfidfRetriever(skills)


def main() -> None:
    rows = _load()
    workers = sorted({row["worker_id"] for row in rows})
    rng = random.Random(SEED)
    rng.shuffle(workers)
    dev_workers = set(workers[: len(workers) // 2])
    held_workers = set(workers) - dev_workers

    catalog_intents = sorted(THIN)
    in_catalog = set(catalog_intents)

    dev_rows = [r for r in rows if r["worker_id"] in dev_workers]
    held_rows = [r for r in rows if r["worker_id"] in held_workers]

    # Examples come only from dev authors, in a fixed shuffled order so
    # k=1 is a prefix of k=3 and the curve is nested rather than noisy.
    examples: dict[str, list[str]] = defaultdict(list)
    for row in dev_rows:
        if row["intent"] in in_catalog:
            examples[row["intent"]].append(row["utt"])
    for intent in examples:
        rng.shuffle(examples[intent])

    held_in = [r for r in held_rows if r["intent"] in in_catalog]
    held_out = [r for r in held_rows if r["intent"] not in in_catalog]
    # Cap the out-of-catalog side so it does not dominate the runtime;
    # sampled with the same seed, reported with its own n.
    held_out = rng.sample(held_out, min(len(held_out), 1500))

    report: dict[str, Any] = {
        "source": "MASSIVE es-ES (Amazon, 2022, CC-BY-4.0)",
        "design": (
            "authors split in two disjoint halves; enrichment built only from "
            "dev-author utterances, every number below from held-out authors"
        ),
        "n_authors_total": len(workers),
        "n_authors_dev": len(dev_workers),
        "n_authors_held_out": len(held_workers),
        "catalog_intents": catalog_intents,
        "n_held_out_in_catalog": len(held_in),
        "n_held_out_out_of_catalog": len(held_out),
        "curve": [],
    }

    print(
        f"{len(workers)} autores ({len(dev_workers)} dev / {len(held_workers)} "
        f"held-out, sin solape)\n"
        f"held-out: {len(held_in)} frases de las {len(catalog_intents)} intenciones "
        f"del catalogo, {len(held_out)} fuera\n"
    )
    print(
        f"{'k ejemplos':>11} {'sin puerta':>9} {'umbral':>7} {'Top-1':>8} "
        f"{'rechaza bien':>14} {'global':>8}"
    )

    # The abstention threshold is calibrated per k on DEV AUTHORS only.
    # Reusing the ERP catalog's 0.15 would measure how well that constant
    # happens to fit this corpus, not how the enrichment behaves -- and
    # enrichment shifts the whole score distribution, so a fixed
    # threshold penalises exactly the arm being tested.
    dev_in = [r for r in dev_rows if r["intent"] in in_catalog]
    dev_out = rng.sample(
        [r for r in dev_rows if r["intent"] not in in_catalog],
        min(len([r for r in dev_rows if r["intent"] not in in_catalog]), 1500),
    )

    for k in K_VALUES:
        retriever = _build_retriever(catalog_intents, examples, k)

        def scored(rows_: list[dict[str, Any]]) -> list[tuple[str | None, float]]:
            out = []
            for row in rows_:
                ranked = retriever.rank(row["utt"], role=ROLE)
                if ranked:
                    out.append((str(ranked[0].skill.skill_id), float(ranked[0].score)))
                else:
                    out.append((None, 0.0))
            return out

        dev_in_scored, dev_out_scored = scored(dev_in), scored(dev_out)
        best_threshold, best_overall = 0.0, -1.0
        for step in range(0, 61):
            threshold = step / 100
            ok = sum(
                1
                for (sid, score), row in zip(dev_in_scored, dev_in, strict=True)
                if score >= threshold and sid == f"massive.{row['intent']}"
            ) + sum(1 for _sid, score in dev_out_scored if score < threshold)
            overall_dev = ok / (len(dev_in) + len(dev_out))
            if overall_dev > best_overall:
                best_threshold, best_overall = threshold, overall_dev

        held_in_scored, held_out_scored = scored(held_in), scored(held_out)
        # Routing accuracy with the gate removed: isolates "does enriched
        # text route better" from "where is the gate set", which the
        # calibrated threshold otherwise mixes together.
        raw_hits = sum(
            1
            for (sid, _score), row in zip(held_in_scored, held_in, strict=True)
            if sid == f"massive.{row['intent']}"
        )
        hits = sum(
            1
            for (sid, score), row in zip(held_in_scored, held_in, strict=True)
            if score >= best_threshold and sid == f"massive.{row['intent']}"
        )
        refusals = sum(1 for _sid, score in held_out_scored if score < best_threshold)

        top1 = hits / len(held_in)
        refusal = refusals / len(held_out)
        overall = (hits + refusals) / (len(held_in) + len(held_out))
        report["curve"].append(
            {
                "k_examples_per_intent": k,
                "threshold_from_dev_authors": best_threshold,
                "routing_accuracy_no_gate": round(raw_hits / len(held_in), 3),
                "top1": round(top1, 3),
                "correct_refusal": round(refusal, 3),
                "overall": round(overall, 3),
            }
        )
        print(
            f"{k:>11} {raw_hits / len(held_in):>9.3f} {best_threshold:>7.2f} "
            f"{top1:>8.3f} {refusal:>14.3f} {overall:>8.3f}"
        )

    OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nescrito en {OUTPUT}")


if __name__ == "__main__":
    main()
