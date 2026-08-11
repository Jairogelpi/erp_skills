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
        "prompt_hash",
        "provider_config_hash",
    ):
        tampered = json.loads(baseline.to_json())
        current = tampered[component]
        tampered[component] = current + 1 if isinstance(current, int) else "tampered"

        path = tmp_path / f"{component}.json"
        path.write_text(json.dumps(tampered), encoding="utf-8")

        assert verify_freeze(path) == [component], f"{component} drift not detected"


def test_a_schema_1_0_manifest_reports_the_new_components_as_unfrozen(tmp_path):
    # Loading an old manifest must not pass silently: schema 1.0 never
    # froze prompts or provider configuration, so a model or temperature
    # change could ride along unnoticed under it.
    old = json.loads(compute_manifest().to_json())
    old["schema_version"] = "1.0"
    del old["prompt_hash"]
    del old["provider_config_hash"]

    path = tmp_path / "schema_1_0.json"
    path.write_text(json.dumps(old), encoding="utf-8")

    assert verify_freeze(path) == [
        "prompt_hash (not frozen by schema 1.0)",
        "provider_config_hash (not frozen by schema 1.0)",
    ]


def test_changing_the_model_or_temperature_breaks_the_freeze(monkeypatch, tmp_path):
    # The point of freezing provider configuration (CLAUDE.md §19): a run
    # with a different model or temperature is a different protocol, and
    # must be detected rather than promised. Verified by actually
    # swapping each one and asserting the hash moves.
    import dataclasses

    import erp_agent_os.groq_client as groq_client

    baseline = compute_manifest()
    path = tmp_path / "baseline.json"
    path.write_text(baseline.to_json(), encoding="utf-8")

    # Patch the factory, not the class attribute: a dataclass binds its
    # defaults into __init__ at class-creation time, so setting
    # GroqConfig.model would leave GroqConfig() unchanged and the test
    # would pass while proving nothing.
    original = groq_client.GroqConfig

    for field, value in (("model", "some-other-model"), ("temperature", 0.7)):
        monkeypatch.setattr(
            groq_client,
            "GroqConfig",
            lambda field=field, value=value: dataclasses.replace(
                original(), **{field: value}
            ),
        )
        assert verify_freeze(path) == ["provider_config_hash"], field
        monkeypatch.undo()


def test_changing_a_prompt_breaks_the_freeze(monkeypatch, tmp_path):
    import erp_agent_os.freeze as freeze_module

    baseline = compute_manifest()
    path = tmp_path / "baseline.json"
    path.write_text(baseline.to_json(), encoding="utf-8")

    monkeypatch.setattr(
        freeze_module, "SELECTION_SYSTEM_PROMPT", "Do whatever you like."
    )
    assert verify_freeze(path) == ["prompt_hash"]


def test_all_real_clients_send_the_same_selection_prompt():
    # CLAUDE.md D-03: A, B and C must share prompts in everything
    # comparable. This used to be three copy-pasted literals agreeing by
    # convention; now it is one constant, and this pins it.
    from erp_agent_os import gemini_client, groq_client, openrouter_client
    from erp_agent_os.llm_client import SELECTION_SYSTEM_PROMPT

    assert groq_client._SYSTEM_PROMPT is SELECTION_SYSTEM_PROMPT
    assert gemini_client._SYSTEM_PROMPT is SELECTION_SYSTEM_PROMPT
    assert openrouter_client._SYSTEM_PROMPT is SELECTION_SYSTEM_PROMPT


def test_extending_the_freeze_did_not_move_the_dataset_or_catalog_hashes():
    # Schema 1.1 must be purely additive: results published against the
    # 1.0 manifest stay comparable only if these three are byte-identical
    # to what 1.0 recorded. Values below are the committed 1.0 hashes.
    manifest = compute_manifest()
    assert (
        manifest.test_split_hash
        == "a7ae907e9952474ef77255c40ada71b7c5c9834b88ec4baf0434e3160b6574eb"
    )
    assert (
        manifest.full_dataset_hash
        == "ef8e9acd48315fc1eb2c6d31631bfca4b115c9c392561ad3a4f18d68c79af9d1"
    )
    assert (
        manifest.catalog_hash
        == "4c3315cb261571b0bdd47a7aadb8b33f42854e048626818582595f4b80019ff7"
    )


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
