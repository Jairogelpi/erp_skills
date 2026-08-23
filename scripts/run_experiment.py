"""Run the paired A/B/C experiment and produce the statistical report.

    uv run python scripts/run_experiment.py              # architecture-only, stub
    uv run python scripts/run_experiment.py --real-llm
        # real provider, exploratory on v1

Writes data/experiment_results.json. Every number in it comes from the
1.080 executions this script performs; nothing is asserted that was not
measured.

--real-llm requires GROQ_API_KEY (see .env.example) and makes real network
calls billed against your free-tier quota (System A and B each call the
LLM once per case per repetition; System C's retrieval is TF-IDF, not
LLM-based, so it makes none). Not used by default or in CI.
"""

import hashlib
import json
import logging
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.catalog import CATALOG
from erp_agent_os.dataset import DATASET_SCHEMA_VERSION, DatasetSplit
from erp_agent_os.evidence import (
    OBSERVATION_SCHEMA_VERSION,
    validate_observation_units,
    write_observations_jsonl,
)
from erp_agent_os.experiment import run_experiment
from erp_agent_os.freeze import load_manifest
from erp_agent_os.llm_client import DeterministicStubClient
from erp_agent_os.metrics import (
    collapse_latency,
    collapse_repetitions,
    collapse_tokens,
    collapse_traceability,
    filter_records_with_expected_skill,
    paraphrase_consistency,
    retrieval_metrics,
    security_metrics,
    segment_success,
    stability,
    token_metrics,
)
from erp_agent_os.prospective_evidence import load_finalized_holdout
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.retrieval_analysis import (
    DEFAULT_MARGIN,
    THRESHOLD_GRID,
    curve_configuration_hash,
    precision_coverage_curve,
)
from erp_agent_os.statistics import (
    cochran_q,
    cohens_dz,
    friedman_test,
    holm_correction,
    mcnemar,
    odds_ratio,
    paired_mean_difference,
    paired_proportion_difference,
    wilcoxon_signed_rank,
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
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _epistemic_status(*, dataset_generation: str, test_has_been_inspected: bool) -> str:
    if dataset_generation == "v1" and test_has_been_inspected:
        return "post_freeze_exploratory"
    return "prospectively_frozen_unseen"


def _validate_epistemic_status(
    status: str, *, dataset_generation: str, test_has_been_inspected: bool
) -> None:
    if status == "confirmatory" and (
        dataset_generation == "v1" or test_has_been_inspected
    ):
        raise ValueError(
            "confirmatory evidence requires a prospectively frozen unseen test"
        )


def _checkpoint_path(provider: str) -> Path:
    # One checkpoint file per provider: resuming a Gemini run from a
    # Groq checkpoint (or vice versa) would silently break D-03 (A/B/C
    # must share one provider within a run). Delete the file to force a
    # fresh run for that provider.
    return DATA_DIR / f"checkpoint_real_llm_{provider}.jsonl"


def _select_llm(real_llm: bool, provider: str, temperature: float | None = None):
    if not real_llm:
        return DeterministicStubClient()

    print(
        f"Real-LLM experimental run ({provider}): this makes network calls "
        "against your free-tier quota. System A and B each call the model "
        "once per case (repetitions reuse the first call, see "
        "CachingLLMClient); System C's retrieval does not call the LLM.",
        file=sys.stderr,
    )
    if provider == "gemini":
        from erp_agent_os.gemini_client import (  # optional dep path
            GeminiClient,
            GeminiConfig,
        )

        if temperature is None:
            return GeminiClient()
        return GeminiClient(GeminiConfig(temperature=temperature))
    if provider == "openrouter":
        from erp_agent_os.openrouter_client import (  # optional dep path
            OpenRouterClient,
            OpenRouterConfig,
        )

        if temperature is None:
            return OpenRouterClient()
        return OpenRouterClient(OpenRouterConfig(temperature=temperature))

    from erp_agent_os.groq_client import (  # local import: optional dep path
        GroqClient,
        GroqConfig,
    )

    if temperature is None:
        return GroqClient()
    return GroqClient(GroqConfig(temperature=temperature))


def _temperature_arg() -> float | None:
    """`--temperature X` opts into the EXPLORATORY H3 arm.

    CLAUDE.md §23 mandates a low temperature, and at 0.0 every system is
    deterministic by construction: H3 (stability across repetitions)
    comes out 1.000 for A, B and C and cannot discriminate. Raising the
    temperature is the only way to let that hypothesis fail, so a run
    that does it is **exploratory, never confirmatory** -- the manifest
    records the temperature and marks it, and §19's frozen protocol is
    unaffected because it keeps its own temperature-0 result.
    """
    if "--temperature" not in sys.argv:
        return None
    return float(sys.argv[sys.argv.index("--temperature") + 1])


def _manifest_caveat(
    *, provider_is_real_llm: bool, selector: str, epistemic_status: str
) -> str:
    """Explain what the run can establish without overstating its status."""
    if epistemic_status == "post_freeze_exploratory":
        provider = "real LLM" if provider_is_real_llm else "deterministic stub"
        return (
            f"{provider} selector ({selector}) shared across A/B/C. The v1 "
            "test split had already been inspected and the implementation was "
            "corrected afterwards, so this run is post-freeze exploratory and "
            "cannot support a confirmatory conclusion."
        )
    if not provider_is_real_llm:
        return (
            "Selector held constant across A/B/C, so this isolates the "
            "ARCHITECTURAL contribution. It is NOT the CLAUDE.md section 19 "
            "confirmatory protocol, which requires a real LLM provider."
        )
    return (
        f"Prospectively frozen real LLM selector ({selector}) shared identically "
        "across A/B/C, per CLAUDE.md D-03. This IS the section 19 "
        "confirmatory protocol, subject to all remaining protocol checks."
    )


def _code_hash() -> str:
    """Hash executable experiment code, including relative file names."""
    paths = sorted((PROJECT_ROOT / "src" / "erp_agent_os").rglob("*.py"))
    paths.append(Path(__file__).resolve())
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _continuous_analysis(vectors: dict[str, list[float]]) -> dict[str, object]:
    omnibus = friedman_test(vectors["A"], vectors["B"], vectors["C"])
    pair_names = (("C", "A"), ("C", "B"), ("B", "A"))
    tests = [wilcoxon_signed_rank(vectors[a], vectors[b]) for a, b in pair_names]
    adjusted = holm_correction([test.p_value for test in tests])
    pairs: dict[str, object] = {}
    for (first, second), test, holm_p in zip(pair_names, tests, adjusted, strict=True):
        interval = paired_mean_difference(vectors[first], vectors[second])
        pairs[f"{first}_minus_{second}"] = {
            "point": interval.point,
            "ci95": [interval.low, interval.high],
            "wilcoxon_statistic": test.statistic,
            "wilcoxon_p": test.p_value,
            "holm_p": holm_p,
            "cohens_dz": cohens_dz(vectors[first], vectors[second]),
            "rank_biserial": test.rank_biserial,
        }
    return {
        "friedman": {
            "statistic": omnibus.statistic,
            "df": omnibus.df,
            "p_value": omnibus.p_value,
        },
        "paired_posthoc": pairs,
    }


def _persist_observation_archive(
    records,
    test_cases,
    manifest,
    output_path: Path,
    *,
    epistemic_status: str,
    temperature: float | None,
    dataset_generation: str = "v1",
    freeze_hashes: dict[str, object] | None = None,
):
    validate_observation_units(
        records,
        request_ids={case.request_id for case in test_cases},
        systems={"A", "B", "C"},
        repetitions=manifest.n_repetitions,
    )
    frozen = asdict(load_manifest()) if freeze_hashes is None else freeze_hashes
    provenance = {
        "dataset_generation": dataset_generation,
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "epistemic_status": epistemic_status,
        "selector": manifest.selector,
        "provider_is_real_llm": manifest.is_confirmatory,
        "real_parser": manifest.real_parser,
        "temperature": temperature,
        "freeze_hashes": frozen,
        "code_hash": _code_hash(),
        "retrieval_curve_config_hash": curve_configuration_hash(),
    }
    return write_observations_jsonl(records, output_path, provenance=provenance)


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


def _output_arg() -> Path | None:
    """Explicit destination, so a run cannot silently replace another.

    Needed for the replication that separates provider from argument
    regime: an unparsed Groq run would otherwise overwrite the published
    OpenRouter confirmatory result, which is a *different* experiment,
    not a newer version of the same one.
    """
    if "--output" in sys.argv:
        return Path(sys.argv[sys.argv.index("--output") + 1])
    return None


def _path_arg(flag: str) -> Path | None:
    if flag not in sys.argv:
        return None
    try:
        return Path(sys.argv[sys.argv.index(flag) + 1])
    except IndexError as exc:
        raise ValueError(f"{flag} requires a path") from exc


def _validate_v2_configuration(
    *, real_llm: bool, real_parser: bool, temperature: float | None
) -> None:
    if not real_llm:
        raise ValueError("v2 one-shot evaluation requires a real LLM")
    if not real_parser:
        raise ValueError("v2 one-shot evaluation requires the shared real parser")
    if temperature is not None:
        raise ValueError(
            "v2 one-shot evaluation uses the frozen low-temperature configuration"
        )


def _v2_receipt_path(
    final_manifest_path: Path, final_manifest: dict[str, object]
) -> Path:
    hashes = final_manifest.get("hashes", {})
    if not isinstance(hashes, dict) or not isinstance(hashes.get("gold_sha256"), str):
        raise ValueError("v2 final manifest has no gold hash")
    return final_manifest_path.parent / (
        f"bench_v2_evaluation_receipt_{hashes['gold_sha256']}.json"
    )


def _assert_v2_unconsumed(receipt_path: Path) -> None:
    if receipt_path.exists():
        raise ValueError(
            "the sealed v2 holdout has already been consumed; any repetition "
            "must be declared exploratory and use a separately versioned workflow"
        )


def main() -> None:
    real_llm = "--real-llm" in sys.argv
    real_parser = "--real-parser" in sys.argv
    provider = _provider_arg()
    temperature = _temperature_arg()
    v2_gold_path = _path_arg("--v2-gold")
    v2_manifest_path = _path_arg("--v2-manifest")

    if temperature is not None and not real_llm:
        print(
            "--temperature requires --real-llm: the stub client has no "
            "sampling temperature, so the run would be identical.",
            file=sys.stderr,
        )
        raise SystemExit(2)

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

    if (v2_gold_path is None) != (v2_manifest_path is None):
        print("--v2-gold and --v2-manifest must be supplied together", file=sys.stderr)
        raise SystemExit(2)

    _configure_logging(real_llm)
    dataset_generation = "v1"
    test_has_been_inspected = True
    freeze_hashes: dict[str, object] | None = None
    receipt_path: Path | None = None
    if v2_gold_path is not None and v2_manifest_path is not None:
        try:
            _validate_v2_configuration(
                real_llm=real_llm,
                real_parser=real_parser,
                temperature=temperature,
            )
            final_manifest = json.loads(v2_manifest_path.read_text(encoding="utf-8"))
            cases = load_finalized_holdout(v2_gold_path, v2_manifest_path)
            receipt_path = _v2_receipt_path(v2_manifest_path, final_manifest)
            _assert_v2_unconsumed(receipt_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"v2 evaluation gate refused the run: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        dataset_generation = "v2"
        test_has_been_inspected = False
        freeze_hashes = final_manifest
    else:
        cases = generate_cases()
    test_cases = [c for c in cases if c.split is DatasetSplit.FINAL_TEST]

    checkpoint_path = _checkpoint_path(provider) if real_llm else None
    if dataset_generation == "v2" and checkpoint_path is not None:
        gold_hash = freeze_hashes["hashes"]["gold_sha256"]  # type: ignore[index]
        checkpoint_path = checkpoint_path.with_name(
            f"{checkpoint_path.stem}_v2_{str(gold_hash)[:12]}.jsonl"
        )
    if real_parser and checkpoint_path is not None:
        # A parsed run is a different experiment from an unparsed one;
        # resuming one from the other's checkpoint would silently mix
        # two argument regimes in a single result.
        checkpoint_path = checkpoint_path.with_name(
            checkpoint_path.stem + "_parsed.jsonl"
        )
    if temperature is not None and checkpoint_path is not None:
        # Same reasoning: a temperature arm is its own experiment.
        checkpoint_path = checkpoint_path.with_name(
            f"{checkpoint_path.stem}_t{temperature}.jsonl"
        )
    records, manifest = run_experiment(
        cases,
        _select_llm(real_llm, provider, temperature),
        checkpoint_path=checkpoint_path,
        real_parser=real_parser,
    )
    epistemic_status = _epistemic_status(
        dataset_generation=dataset_generation,
        test_has_been_inspected=test_has_been_inspected,
    )
    is_confirmatory_run = (
        manifest.is_confirmatory
        and epistemic_status == "prospectively_frozen_unseen"
        and temperature is None
    )
    if is_confirmatory_run:
        _validate_epistemic_status(
            "confirmatory",
            dataset_generation=dataset_generation,
            test_has_been_inspected=test_has_been_inspected,
        )
    output_path = _output_arg()
    if output_path is None:
        if dataset_generation == "v2":
            output_path = OUTPUT_PATH.with_name("experiment_results_v2.json")
        elif manifest.real_parser:
            output_path = OUTPUT_PATH.with_name("experiment_results_real_parser.json")
        else:
            output_path = OUTPUT_PATH

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
    token_collapsed = collapse_tokens(records, test_cases)
    token_units = sorted(token_collapsed["C"])
    token_vectors = {
        s: [token_collapsed[s][u] for u in token_units] for s in ("A", "B", "C")
    }
    cb_tokens = paired_mean_difference(token_vectors["C"], token_vectors["B"])
    ca_tokens = paired_mean_difference(token_vectors["C"], token_vectors["A"])
    h2_records = filter_records_with_expected_skill(test_cases, records)
    h2_per_system = defaultdict(list)
    for record in h2_records:
        h2_per_system[record.system].append(record)
    token_totals = {s: token_metrics(h2_per_system[s]) for s in ("A", "B", "C")}
    overall_token_totals = {
        s: token_metrics(per_system_records[s]) for s in ("A", "B", "C")
    }
    token_analysis = _continuous_analysis(token_vectors)

    trace_collapsed = collapse_traceability(records)
    trace_units = sorted(trace_collapsed["C"])
    trace_vectors = {
        s: [trace_collapsed[s][unit] for unit in trace_units] for s in ("A", "B", "C")
    }
    trace_analysis = _continuous_analysis(trace_vectors)

    latency_collapsed = collapse_latency(records)
    latency_units = sorted(latency_collapsed["C"])
    latency_vectors = {
        s: [latency_collapsed[s][unit] for unit in latency_units]
        for s in ("A", "B", "C")
    }
    latency_analysis = _continuous_analysis(latency_vectors)

    security = {
        s: security_metrics(test_cases, per_system_records[s]) for s in ("A", "B", "C")
    }
    retrieval = {
        s: retrieval_metrics(test_cases, per_system_records[s]) for s in ("A", "B", "C")
    }
    stab = {s: stability(per_system_records[s]) for s in ("A", "B", "C")}
    paraphrase = {
        s: paraphrase_consistency(test_cases, per_system_records[s])
        for s in ("A", "B", "C")
    }
    retrieval_curve = precision_coverage_curve(
        test_cases,
        TfidfRetriever(CATALOG),
        thresholds=THRESHOLD_GRID,
        margin=DEFAULT_MARGIN,
    )
    archive = _persist_observation_archive(
        records,
        test_cases,
        manifest,
        output_path,
        epistemic_status=epistemic_status,
        temperature=temperature,
        dataset_generation=dataset_generation,
        freeze_hashes=freeze_hashes,
    )

    report = {
        "manifest": {
            "selector": manifest.selector,
            "dataset_generation": dataset_generation,
            "provider_is_real_llm": manifest.is_confirmatory,
            "is_confirmatory_run": is_confirmatory_run,
            "epistemic_status": epistemic_status,
            "no_valid_confirmatory_conclusion": not is_confirmatory_run,
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
            "temperature": temperature,
            "is_exploratory_temperature_arm": temperature is not None,
            "argument_regime": (
                "LLM-extracted from request text, identical prompt and field "
                "list for A/B/C (removes the perfect-parse bias that made "
                "System C's token cost zero)"
                if manifest.real_parser
                else "ground-truth expected_arguments handed to every system "
                "(perfect parse, unpaid: flatters System C on H2 tokens)"
            ),
            "observation_archive": {
                "path": _display_path(archive.path),
                "sha256": archive.sha256,
                "schema_version": OBSERVATION_SCHEMA_VERSION,
                "row_count": archive.row_count,
            },
            "caveat": _manifest_caveat(
                provider_is_real_llm=manifest.is_confirmatory,
                selector=manifest.selector,
                epistemic_status=epistemic_status,
            ),
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
            "H1_criterion_met_in_this_exploratory_run": h1_non_inferior,
        },
        "H2_tokens": {
            "note": (
                "Only test cases with an expected real skill. Mean total "
                "tokens per case (repetitions collapsed, same "
                "unit as H1). 0 for any system/run using a client that "
                "made no real LLM call -- System C never does; A/B are 0 "
                "under the stub-selector run and real under --real-llm."
            ),
            "population": {
                "expected_skill_cases": len(token_units),
                "excluded_sin_skill_cases": len(test_cases) - len(token_units),
            },
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
            "inference": token_analysis,
        },
        "latency": {
            "note": (
                "Measured wall-clock latency under this exact provider, cache "
                "and rate-limit configuration; not a universal system property."
            ),
            "mean_seconds_per_execution": {
                s: sum(r.latency_seconds for r in per_system_records[s])
                / len(per_system_records[s])
                for s in ("A", "B", "C")
            },
            "inference": latency_analysis,
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
                for s, m in overall_token_totals.items()
            },
        },
        "H3_stability": stab,
        "H3b_paraphrase_consistency": {
            "note": (
                "The variability H3 cannot measure. H3 repeats identical "
                "text, which at the temperature=0 CLAUDE.md section 23 "
                "mandates is 1.000 for every system by construction. This "
                "measures whether different WORDINGS of the same intent "
                "get the same handling -- which discriminates at "
                "temperature 0 and is what actually matters in an ERP. "
                "NOISE and ADVERSARIAL cases are excluded: they are meant "
                "to be handled differently from their NORMAL siblings."
            ),
            "score": paraphrase,
        },
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
        "H6_abstention_curve": {
            "note": (
                "Precision-coverage curve on the sealed test. The fixed grid "
                "is reported and was not tuned on this holdout."
                if dataset_generation == "v2"
                else "Descriptive precision-coverage curve on the already-"
                "inspected v1 test. The fixed grid is reported, not tuned here."
            ),
            "thresholds": list(THRESHOLD_GRID),
            "margin": DEFAULT_MARGIN,
            "configuration_hash": curve_configuration_hash(),
            "points": [point.to_dict() for point in retrieval_curve],
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
            "mean_components": {
                s: {
                    component: sum(
                        (
                            r.traceability_components.get(component, 0.0)
                            if isinstance(r.traceability_components, dict)
                            else 0.0
                        )
                        for r in per_system_records[s]
                    )
                    / len(per_system_records[s])
                    for component in TRACEABILITY_WEIGHTS
                }
                for s in ("A", "B", "C")
            },
            "inference": trace_analysis,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if receipt_path is not None:
        receipt = {
            "schema_version": "1.0",
            "status": "v2_one_shot_evaluation_consumed",
            "gold_sha256": freeze_hashes["hashes"]["gold_sha256"],  # type: ignore[index]
            "report_path": _display_path(output_path),
            "report_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
            "observations_path": _display_path(archive.path),
            "observations_sha256": archive.sha256,
            "selector": manifest.selector,
            "real_parser": manifest.real_parser,
            "temperature": temperature,
            "code_hash": _code_hash(),
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
    # A completed run's checkpoint is spent; keeping it around would make
    # the *next* run silently resume stale cached calls instead of really
    # running.
    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint_path.unlink()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
