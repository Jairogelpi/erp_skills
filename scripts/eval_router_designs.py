"""Five routing designs on real text, calibrated on dev, judged held-out.

`docs/product-viability.md` §7.2-7.3 left three follow-ups. This script
runs all three at once, because they are the same experiment:

  1. **Enriched skill text** -- synonyms and real phrasings instead of
     the catalog's one-line description. Costs zero tokens.
  2. **Domain-membership gate** before routing -- the failure neither
     router handles: TF-IDF commits to a skill on 61 % of requests no
     skill covers, the LLM on 83 %.
  3. **Token cost of replacing the router** -- the trade-off is now
     quantifiable: +0.369 Top-1 in exchange for putting back the
     tool-selection call the architecture removed.

**Discipline.** The 120 real requests are split 50/50 by sha256 of the
request text. Enriched profiles were written reading ONLY the dev half;
the gate threshold is swept ONLY on dev. Every number reported for
decision-making is on the **held-out** half. Reporting the dev number as
the result would be fitting to the sample -- the same mistake this
project has corrected repeatedly.

The frozen catalog is never modified: its hash is in
`data/freeze_manifest.json`, and changing it would invalidate every
published experimental result. Enrichment lives in
`data/skill_profiles.json`, used only here.

    uv run python scripts/eval_router_designs.py

Reuses the cached LLM decisions in `data/real_requests_llm_eval.json`
(no new provider calls) and measures token cost on a small live sample.
"""

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erp_agent_os.catalog import CATALOG, CATALOG_BY_ID
from erp_agent_os.retrieval import TfidfRetriever

ROOT = Path(__file__).resolve().parent.parent
REQUESTS = ROOT / "data" / "real_requests.csv"
PROFILES = ROOT / "data" / "skill_profiles.json"
LLM_CACHE = ROOT / "data" / "real_requests_llm_eval.json"
OUTPUT = ROOT / "data" / "router_designs_eval.json"
ROLE = "erp_user"


@dataclass(frozen=True)
class Request:
    text: str
    expected: str | None
    half: str


def _split(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return "dev" if int(digest, 16) % 2 == 0 else "held"


def _load_requests() -> list[Request]:
    valid = set(CATALOG_BY_ID)
    out: list[Request] = []
    with REQUESTS.open(encoding="utf-8-sig", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            text = (row.get("request_text") or "").strip()
            skill = (row.get("expected_skill") or "").strip()
            if not text:
                continue
            if skill and skill not in valid:
                raise SystemExit(f"row {line_number}: unknown skill id {skill!r}")
            out.append(Request(text, skill or None, _split(text)))
    return out


def _enriched_retriever() -> TfidfRetriever:
    """TF-IDF over enriched text, without mutating the frozen catalog.

    `SkillDefinition` is frozen, so the enriched description is applied
    with `dataclasses.replace`-style copies used *only* by this local
    retriever instance.
    """
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]
    enriched = []
    for skill in CATALOG:
        extra = profiles.get(skill.skill_id, "")
        enriched.append(
            skill.model_copy(update={"description": f"{skill.description} {extra}"})
        )
    return TfidfRetriever(enriched)


def _top_score(ranked: list[Any]) -> float:
    return float(ranked[0].score) if ranked else 0.0


def _evaluate(
    requests: list[Request],
    route: Any,
    label: str,
) -> dict[str, Any]:
    """`route(text) -> skill_id | None`. None means "I do not handle this"."""
    answerable = [r for r in requests if r.expected]
    out_of_catalog = [r for r in requests if not r.expected]

    hits = sum(1 for r in answerable if route(r.text) == r.expected)
    refusals = sum(1 for r in out_of_catalog if route(r.text) is None)
    return {
        "design": label,
        "n_answerable": len(answerable),
        "n_out_of_catalog": len(out_of_catalog),
        "top1": round(hits / len(answerable), 3) if answerable else 0.0,
        "correct_refusal": (
            round(refusals / len(out_of_catalog), 3) if out_of_catalog else 0.0
        ),
        "overall": round((hits + refusals) / len(requests), 3) if requests else 0.0,
    }


def _sweep_gate(requests: list[Request], retriever: TfidfRetriever) -> float:
    """Pick the domain-gate threshold on DEV only, maximising overall.

    Overall (right route + right silence) is the objective on purpose: a
    threshold chosen to maximise Top-1 alone would push the gate to zero
    and reintroduce exactly the over-commitment being fixed.
    """
    best_threshold, best_score = 0.0, -1.0
    for step in range(0, 61):
        threshold = step / 100
        score = _evaluate(
            requests,
            lambda text, t=threshold: _gated_tfidf(text, retriever, t),
            "sweep",
        )["overall"]
        if score > best_score:
            best_threshold, best_score = threshold, score
    return best_threshold


def _gated_tfidf(text: str, retriever: TfidfRetriever, threshold: float) -> str | None:
    ranked = retriever.rank(text, role=ROLE)
    if not ranked or _top_score(ranked) < threshold:
        return None
    return str(ranked[0].skill.skill_id)


def _measure_selection_tokens(sample: list[Request], provider: str) -> dict[str, Any]:
    """Real token cost of one tool-selection call, on real requests."""
    from erp_agent_os.system_b import TYPED_TOOLS

    if provider == "groq":
        from erp_agent_os.groq_client import GroqClient

        client: Any = GroqClient()
    else:
        from erp_agent_os.openrouter_client import OpenRouterClient

        client = OpenRouterClient()

    prompt = completion = 0
    for request in sample:
        call = client.propose_action(request.text, TYPED_TOOLS)
        prompt += call.prompt_tokens
        completion += call.completion_tokens
    n = len(sample)
    return {
        "n_sampled": n,
        "provider": type(client).__name__,
        "mean_prompt_tokens": round(prompt / n, 1),
        "mean_completion_tokens": round(completion / n, 1),
        "mean_total_tokens_per_selection": round((prompt + completion) / n, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--token-sample",
        type=int,
        default=0,
        help="measure real selection-call tokens on N held-out requests (0 = skip)",
    )
    parser.add_argument("--provider", default="groq", choices=("groq", "openrouter"))
    args = parser.parse_args()

    requests = _load_requests()
    dev = [r for r in requests if r.half == "dev"]
    held = [r for r in requests if r.half == "held"]

    plain = TfidfRetriever(list(CATALOG))
    enriched = _enriched_retriever()

    cached = {
        detail["request"]: detail["chosen"]
        for detail in json.loads(LLM_CACHE.read_text(encoding="utf-8"))["details"]
        if "request" in detail
    }
    llm_by_index = [
        d["chosen"]
        for d in json.loads(LLM_CACHE.read_text(encoding="utf-8"))["details"]
    ]
    if not cached:
        # The cache stored decisions positionally, in CSV order.
        cached = {r.text: llm_by_index[i] for i, r in enumerate(requests)}

    def route_plain(text: str) -> str | None:
        return _gated_tfidf(text, plain, 0.15)

    def route_enriched(text: str) -> str | None:
        return _gated_tfidf(text, enriched, 0.15)

    def route_llm(text: str) -> str | None:
        return cached.get(text)

    gate = _sweep_gate(dev, enriched)

    def route_gate_then_llm(text: str) -> str | None:
        if _gated_tfidf(text, enriched, gate) is None:
            return None
        return cached.get(text)

    def route_gate_then_enriched(text: str) -> str | None:
        return _gated_tfidf(text, enriched, gate)

    designs = [
        ("D1 TF-IDF catalogo (C actual)", route_plain, 0.0),
        ("D2 TF-IDF enriquecido", route_enriched, 0.0),
        ("D3 router LLM (B actual)", route_llm, None),
        ("D4 filtro dominio + router LLM", route_gate_then_llm, None),
        ("D5 filtro dominio + TF-IDF enriq.", route_gate_then_enriched, 0.0),
    ]

    report: dict[str, Any] = {
        "discipline": (
            "profiles written from the dev half only; gate threshold swept on "
            "dev only; every decision number below is held-out"
        ),
        "n_dev": len(dev),
        "n_held_out": len(held),
        "domain_gate_threshold_from_dev": gate,
        "dev": [],
        "held_out": [],
    }
    for label, route, _tokens in designs:
        report["dev"].append(_evaluate(dev, route, label))
        report["held_out"].append(_evaluate(held, route, label))

    if args.token_sample:
        report["token_cost"] = _measure_selection_tokens(
            held[: args.token_sample], args.provider
        )

    OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"umbral del filtro de dominio, calibrado en dev: {gate:.2f}\n")
    print(f"HELD-OUT ({len(held)} peticiones, nunca miradas al construir nada)\n")
    print(f"{'diseño':36} {'Top-1':>7} {'rechaza':>8} {'global':>7}")
    for row in report["held_out"]:
        print(
            f"{row['design']:36} {row['top1']:>7.3f} "
            f"{row['correct_refusal']:>8.3f} {row['overall']:>7.3f}"
        )
    if "token_cost" in report:
        tc = report["token_cost"]
        print(
            f"\ncoste real de una llamada de seleccion "
            f"({tc['provider']}, n={tc['n_sampled']}): "
            f"{tc['mean_total_tokens_per_selection']} tokens"
        )
    print(f"\nescrito en {OUTPUT}")


if __name__ == "__main__":
    main()
