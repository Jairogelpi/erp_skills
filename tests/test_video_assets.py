import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "make_video_assets", ROOT / "scripts" / "make_video_assets.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ASSETS = MODULE.ASSETS
make_assets = MODULE.make_assets
headline_metrics = MODULE.headline_metrics


def test_video_assets_are_self_contained_1080p_and_evidence_labeled(
    tmp_path: Path,
) -> None:
    make_assets(tmp_path)
    assert {path.name for path in tmp_path.glob("*.svg")} == set(ASSETS)
    for name in ASSETS:
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert 'width="1920"' in text
        assert 'height="1080"' in text
        assert 'viewBox="0 0 1920 1080"' in text
        assert 'href="http://' not in text and 'href="https://' not in text
        assert "ERP AGENT OS" in text

    results = (tmp_path / "04-results.svg").read_text(encoding="utf-8")
    assert "V2 PENDIENTE" in results
    assert "EXPLORATORIO" in results
    assert "0,483" in results and "0,633" in results

    limits = (tmp_path / "05-limitations.svg").read_text(encoding="utf-8")
    assert "3,3 %" in limits
    assert "NO ADAPTATIVO" in limits


def test_generated_assets_are_deterministic(tmp_path: Path) -> None:
    make_assets(tmp_path)
    first = {name: (tmp_path / name).read_bytes() for name in ASSETS}
    make_assets(tmp_path)
    assert first == {name: (tmp_path / name).read_bytes() for name in ASSETS}


def test_results_card_numbers_are_read_from_the_source_json_not_hardcoded(
    tmp_path: Path,
) -> None:
    """The design requires headline numbers to come from the evidence/result
    artefact so a future correction to the JSON (this project has corrected
    published numbers multiple times) cannot leave the video silently stale.
    A fake JSON with distinguishable values proves real wiring, not just
    that today's hardcoded strings happen to match today's JSON.
    """
    fake_results = {
        "H1_stsr": {"stsr": {"A": 0.0, "B": 0.111, "C": 0.222}},
        "H2_tokens": {
            "totals": {
                "B": {"mean_tokens_per_execution": 333.4},
                "C": {"mean_tokens_per_execution": 55.6},
            }
        },
        "H4_security": {
            "B": {"false_allow_rate": 0.777},
            "C": {"false_allow_rate": 0.088},
        },
    }
    fake_path = tmp_path / "fake_results.json"
    fake_path.write_text(json.dumps(fake_results), encoding="utf-8")

    metrics = headline_metrics(fake_path)
    results_svg = MODULE._results(metrics)

    for expected in ("0,111", "0,222", "333,4", "55,6", "0,777", "0,088"):
        assert expected in results_svg
    # And it must not silently fall back to the real repository numbers.
    real_metrics = headline_metrics()
    assert real_metrics != metrics
