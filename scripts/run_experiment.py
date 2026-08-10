"""Run the paired A/B/C experiment and produce the statistical report.

    uv run python scripts/run_experiment.py              # architecture-only, stub
    uv run python scripts/run_experiment.py --real-llm   # confirmatory, real Groq calls

Writes data/experiment_results.json. Every number in it comes from the
1.080 executions this script performs; nothing is asserted that was not
measured.

--real-llm requires GROQ_API_KEY (see .env.example) and makes real network
calls billed against your free-tier quota (System A and B each call the
LLM once per case per repetition; System C's retrieval is TF-IDF, not
LLM-based, so it makes none). Not used by default or in CI.
"""

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.experiment import run_experiment
from erp_agent_os.llm_client import DeterministicStubClient
from erp_agent_os.metrics import (
    collapse_repetitions,
    collapse_tokens,
    retrieval_metrics,
    security_metrics,
    segment_success,
    stability,
    token_metrics,
)
from erp_agent_os.statistics import (
    cochran_q,
    holm_correction,
    mcnemar,
    odds_ratio,
    paired_mean_difference,
    paired_proportion_difference,
)
from erp_agent_os.traceability import WEIGHTS as TRACEABILITY_WEIGHTS

# H8 cost sensitivity (CLAUDE.md §20): declared assumptions, not measured
# spend. Groq's llama-3.1-8b-instant free tier has no per-token price;
# this rate is a stand-in for "a small hosted model", stated so the
# scenario is reproducible, not so it reads as a real invoice.
USD_PER_1K_TOKENS = 0.05

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "experiment_results.json"
)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _checkpoint_path(provider: str) -> Path:
    # One checkpoint file per provider: resuming a Gemini run from a
    # Groq checkpoint (or vice versa) would silently break D-03 (A/B/C
    # must share one provider within a run). Delete the file to force a
    # fresh run for that provider.
    return DATA_DIR / f"checkpoint_real_llm_{provider}.jsonl"


def _select_llm(real_llm: bool, provider: str):
    if not real_llm:
        return DeterministicStubClient()

    print(
        f"Real-LLM confirmatory run ({provider}): this makes network calls "
        "against your free-tier quota. System A and B each call the model "
        "once per case (repetitions reuse the first call, see "
        "CachingLLMClient); System C's retrieval does not call the LLM.",
        file=sys.stderr,
    )
    if provider == "gemini":
        from erp_agent_os.gemini_client import GeminiClient  # optional dep path

        return GeminiClient()
    if provider == "openrouter":
        from erp_agent_os.openrouter_client import (  # optional dep path
            OpenRouterClient,
        )

        return OpenRouterClient()

    from erp_agent_os.groq_client import GroqClient  # local import: optional dep path

    return GroqClient()


def _manifest_caveat(is_confirmatory: bool, selector: str) -> str:
    """The manifest's caveat text must match `is_confirmatory_run` AND
    name the selector that was actually used.

    Two related bugs found by reading a run's own output before
    reporting it: (1) a prior version hardcoded the non-confirmatory
    text unconditionally, so a real-LLM run would publish
    "is_confirmatory_run: true" next to a caveat claiming it was NOT the
    confirmatory protocol; (2) a later version hardcoded "Groq free
    tier" in the confirmatory branch, so a run made with GeminiClient or
    OpenRouterClient would publish a caveat naming the wrong provider.
    Both are now derived, not literal.
    """
    if not is_confirmatory:
        return (
            "Selector held constant across A/B/C, so this isolates the "
            "ARCHITECTURAL contribution. It is NOT the CLAUDE.md section 19 "
            "confirmatory protocol, which requires a real LLM provider."
        )
    return (
        f"Real LLM selector ({selector}, free tier) shared identically "
        "across A/B/C, per CLAUDE.md D-03. This IS the section 19 "
        "confirmatory protocol. Declared limitation: a free-tier model, "
        "not a frontier/production model -- see the memoria for the "
        "disclosure this requires."
    )


def _configure_logging(real_llm: bool) -> None:
    """Real-call visibility: one line per observation, per attempt, per
    retry, flushed immediately -- so `tail -f` on the log shows live
    progress instead of nothing until the final JSON dump."""
    if not real_llm:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def _provider_arg() -> str:
    if "--provider" in sys.argv:
        return sys.argv[sys.argv.index("--provider") + 1]
    return "groq"


def main() -> None:
    real_llm = "--real-llm" in sys.argv
    real_parser = "--real-parser" in sys.argv
    provider = _provider_arg()

    if real_parser and not real_llm:
        # DeterministicStubClient extracts nothing (it is not a language
        # model), so this combination would score every system at zero
        # and look like a catastrophic finding instead of a
        # misconfiguration. Refuse rather than publish a meaningless run.
        print(
            "--real-parser requires --real-llm: the stub client cannot "
            "extract arguments, so the run would be meaningless.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    _configure_logging(real_llm)
    cases = generate_cases()
    test_cases = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]

    checkpoint_path = _checkpoint_path(provider) if real_llm else None
    if real_parser and checkpoint_path is not None:
        # A parsed run is a different experiment from an unparsed one;
        # resuming one from the other's checkpoint would silently mix
        # two argument regimes in a single result.
        checkpoint_path = checkpoint_path.with_name(
            checkpoint_path.stem + "_parsed.jsonl"
        )
    records, manifest = run_experiment(
        cases,
        _select_llm(real_llm, provider),
        checkpoint_path=checkpoint_path,
        real_parser=real_parser,
    )

    per_system_records = defaultdict(list)
    for record in records:
        per_system_records[record.system].append(record)

    # Inference unit is the CASE, not (case, repetition): repetitions of
    # the same case are not independent, and treating them as such is
    # pseudo-replication that would narrow every CI by ~sqrt(3) and shrink
    # p-values by orders of magnitude. Repetitions feed H3 (stability).
    collapsed = collapse_repetitions(test_cases, records)
    units = sorted(collapsed["C"])
    vectors = {
        system: [collapsed[system][u] for u in units] for system in ("A", "B", "C")
    }

    stsr = {s: sum(v) / len(v) for s, v in vectors.items()}

    # H1: C non-inferior to A, margin -5 pp.
    h1_diff = paired_proportion_difference(vectors["C"], vectors["A"])
    h1_test = mcnemar(vectors["C"], vectors["A"])
    h1_non_inferior = h1_diff.low > -0.05

    cb_diff = paired_proportion_difference(vectors["C"], vectors["B"])
    cb_test = mcnemar(vectors["C"], vectors["B"])

    q_statistic, q_df = cochran_q(vectors["A"], vectors["B"], vectors["C"])
    adjusted = holm_correction([h1_test.p_value, cb_test.p_value])

    # H2: tokens per execution, paired on the case (mean across its
    # repetitions), same pseudo-replication guard as STSR above.
    token_collapsed = collapse_tokens(records)
    token_units = sorted(token_collapsed["C"])
    token_vectors = {
        s: [token_collapsed[s][u] for u in token_units] for s in ("A", "B", "C")
    }
    cb_tokens = paired_mean_difference(token_vectors["C"], token_vectors["B"])
    ca_tokens = paired_mean_difference(token_vectors["C"], token_vectors["A"])
    token_totals = {s: token_metrics(per_system_records[s]) for s in ("A", "B", "C")}

    security = {
        s: security_metrics(test_cases, per_system_records[s]) for s in ("A", "B", "C")
    }
    retrieval = {
        s: retrieval_metrics(test_cases, per_system_records[s]) for s in ("A", "B", "C")
    }
    stab = {s: stability(per_system_records[s]) for s in ("A", "B", "C")}

    report = {
        "manifest": {
            "selector": manifest.selector,
            "is_confirmatory_run": manifest.is_confirmatory,
            "n_observations": len(records),
            "n_inference_units": len(units),
            "inference_note": (
                "Repetitions are collapsed per case before any paired test. "
                "Using all 1.080 executions as independent observations "
                "would be pseudo-replication."
            ),
            "n_cases": manifest.n_cases,
            "n_repetitions": manifest.n_repetitions,
            "seed": manifest.seed,
            "real_parser": manifest.real_parser,
            "argument_regime": (
                "LLM-extracted from request text, identical prompt and field "
                "list for A/B/C (removes the perfect-parse bias that made "
                "System C's token cost zero)"
                if manifest.real_parser
                else "ground-truth expected_arguments handed to every system "
                "(perfect parse, unpaid: flatters System C on H2 tokens)"
            ),
            "caveat": _manifest_caveat(manifest.is_confirmatory, manifest.selector),
        },
        "H1_stsr": {
            "stsr": stsr,
            "C_minus_A": {
                "point": h1_diff.point,
                "ci95": [h1_diff.low, h1_diff.high],
                "mcnemar_p": h1_test.p_value,
                "holm_p": adjusted[0],
                "discordant_C_wins": h1_test.discordant_b,
                "discordant_A_wins": h1_test.discordant_c,
                "odds_ratio": odds_ratio(vectors["C"], vectors["A"]),
            },
            "C_minus_B": {
                "point": cb_diff.point,
                "ci95": [cb_diff.low, cb_diff.high],
                "mcnemar_p": cb_test.p_value,
                "holm_p": adjusted[1],
                "odds_ratio": odds_ratio(vectors["C"], vectors["B"]),
            },
            "cochran_q": {"statistic": q_statistic, "df": q_df},
            "non_inferiority_margin": -0.05,
            "H1_supported": h1_non_inferior,
        },
        "H2_tokens": {
            "note": (
                "Mean total tokens per case (repetitions collapsed, same "
                "unit as H1). 0 for any system/run using a client that "
                "made no real LLM call -- System C never does; A/B are 0 "
                "under the stub-selector run and real under --real-llm."
            ),
            "totals": {
                s: {
                    "n_executions": m.n,
                    "total_prompt_tokens": m.total_prompt_tokens,
                    "total_completion_tokens": m.total_completion_tokens,
                    "total_tokens": m.total_tokens,
                    "mean_tokens_per_execution": m.mean_tokens_per_execution,
                }
                for s, m in token_totals.items()
            },
            "C_minus_B": {
                "point": cb_tokens.point,
                "ci95": [cb_tokens.low, cb_tokens.high],
            },
            "C_minus_A": {
                "point": ca_tokens.point,
                "ci95": [ca_tokens.low, ca_tokens.high],
            },
        },
        "H8_cost_sensitivity": {
            "caveat": (
                "Sensitivity analysis with a declared, non-measured token "
                "price (CLAUDE.md section 20 limits H8 to this, not to "
                "observed savings). USD_PER_1K_TOKENS is a stand-in rate, "
                "not Groq's real (unpriced, free-tier) cost."
            ),
            "usd_per_1k_tokens": USD_PER_1K_TOKENS,
            "inference_cost_usd": {
                s: m.total_tokens / 1000 * USD_PER_1K_TOKENS
                for s, m in token_totals.items()
            },
        },
        "H3_stability": stab,
        "H4_security": {
            s: {
                "dangerous_total": m.dangerous_total,
                "false_allow": m.false_allow,
                "false_allow_rate": m.false_allow_rate,
                "false_block_rate": m.false_block_rate,
                "detection_recall": m.detection_recall,
                "detection_precision": m.detection_precision,
            }
            for s, m in security.items()
        },
        "segmentation": {
            dimension: {
                system: segment_success(
                    test_cases, per_system_records[system], dimension
                )
                for system in ("A", "B", "C")
            }
            for dimension in ("module", "risk_class", "label")
        },
        "H5_retrieval": {
            s: {
                "n": m.n,
                "top1": m.top1,
                "top3": m.top3,
                "mrr": m.mrr,
                "coverage": m.coverage,
                "abstention_rate": m.abstention_rate,
                "selective_accuracy": m.selective_accuracy,
                "false_reuse_risk": m.false_reuse_risk,
            }
            for s, m in retrieval.items()
        },
        "H7_traceability": {
            "note": (
                "Weighted rubric (docs/traceability-rubric.md), scored per "
                "execution from real audit evidence, not log volume. A/B "
                "score low on policy_decision/skill_version_and_key/"
                "postcondition_or_block_evidence by construction -- they "
                "have no policy engine, no versioned skill, no audit "
                "store (CLAUDE.md section 18)."
            ),
            "weights": TRACEABILITY_WEIGHTS,
            "mean_score": {
                s: sum(r.traceability_score for r in per_system_records[s])
                / len(per_system_records[s])
                for s in ("A", "B", "C")
            },
        },
    }

    # A parsed run is a *different* experiment, not a newer version of
    # the frozen one: it writes beside the confirmatory result instead
    # of overwriting it, so both argument regimes stay comparable.
    output_path = (
        OUTPUT_PATH.with_name("experiment_results_real_parser.json")
        if manifest.real_parser
        else OUTPUT_PATH
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # A completed run's checkpoint is spent; keeping it around would make
    # the *next* run silently resume stale cached calls instead of really
    # running.
    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint_path.unlink()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
