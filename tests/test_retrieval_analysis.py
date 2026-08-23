from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.catalog import CATALOG
from erp_agent_os.dataset import DatasetSplit
from erp_agent_os.retrieval import TfidfRetriever
from erp_agent_os.retrieval_analysis import (
    DEFAULT_MARGIN,
    THRESHOLD_GRID,
    precision_coverage_curve,
)


def test_precision_coverage_curve_uses_declared_grid_and_all_test_cases():
    cases = [c for c in generate_cases() if c.split is DatasetSplit.FINAL_TEST]

    curve = precision_coverage_curve(cases, TfidfRetriever(CATALOG))

    assert [point.threshold for point in curve] == list(THRESHOLD_GRID)
    assert all(point.n_cases == 120 for point in curve)
    assert all(point.margin == DEFAULT_MARGIN for point in curve)


def test_coverage_cannot_increase_when_threshold_rises():
    cases = [c for c in generate_cases() if c.split is DatasetSplit.FINAL_TEST]

    curve = precision_coverage_curve(cases, TfidfRetriever(CATALOG))
    coverage = [point.coverage for point in curve]

    assert coverage == sorted(coverage, reverse=True)


def test_curve_reports_false_reuse_and_correct_abstention_explicitly():
    cases = [c for c in generate_cases() if c.split is DatasetSplit.FINAL_TEST]

    point = precision_coverage_curve(
        cases, TfidfRetriever(CATALOG), thresholds=(0.15,)
    )[0]

    assert point.accepted + point.abstained == point.n_cases
    assert 0.0 <= point.selective_accuracy <= 1.0
    assert 0.0 <= point.false_reuse_risk <= 1.0
    assert 0.0 <= point.correct_abstention_rate <= 1.0
    assert point.n_abstention_expected > 0
