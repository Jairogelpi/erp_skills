import importlib.util
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
