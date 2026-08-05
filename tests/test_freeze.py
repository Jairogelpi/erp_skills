import json

import pytest

from erp_agent_os.freeze import (
    MANIFEST_PATH,
    compute_manifest,
    load_manifest,
    verify_freeze,
    write_manifest,
)


def test_committed_manifest_matches_the_current_artefacts():
    # The frozen protocol must still be intact in the repository as
    # committed. If this fails, someone changed the test split, the
    # catalog or the seed without re-freezing -- which silently
    # invalidates every result computed against the old freeze.
    assert verify_freeze() == []


def test_manifest_is_deterministic():
    assert compute_manifest() == compute_manifest()


def test_manifest_records_the_expected_split_sizes():
    manifest = load_manifest()
    assert manifest.n_test_cases == 120
    assert manifest.n_total_cases == 480


def test_drift_is_detected_for_every_frozen_component(tmp_path):
    # A drift detector that cannot fail is worthless. Plant a change in
    # each component and assert it is reported by name.
    baseline = compute_manifest()

    for component in (
        "seed",
        "test_split_hash",
        "full_dataset_hash",
        "catalog_hash",
        "n_test_cases",
        "n_total_cases",
    ):
        tampered = json.loads(baseline.to_json())
        current = tampered[component]
        tampered[component] = current + 1 if isinstance(current, int) else "tampered"

        path = tmp_path / f"{component}.json"
        path.write_text(json.dumps(tampered), encoding="utf-8")

        assert verify_freeze(path) == [component], f"{component} drift not detected"


def test_missing_manifest_is_an_explicit_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        verify_freeze(tmp_path / "absent.json")


def test_write_manifest_roundtrips(tmp_path):
    path = tmp_path / "freeze.json"
    written = write_manifest(path)
    assert load_manifest(path) == written


def test_manifest_path_points_at_the_committed_file():
    assert MANIFEST_PATH.name == "freeze_manifest.json"
    assert MANIFEST_PATH.exists()
