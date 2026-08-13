import csv
import json

import pytest

import erp_agent_os.prospective_evidence as prospective_evidence
from erp_agent_os.prospective_evidence import (
    FinalizedHoldout,
    HumanGateIncomplete,
    apply_adjudication_packet,
    finalize_v2_holdout,
    load_finalized_holdout,
    review_annotation_packets,
    seal_candidate_holdout,
    write_adjudication_packet,
    write_state_review_packets,
)
from erp_agent_os.prospective_v2 import generate_v2_candidates


def test_seal_writes_blinded_candidates_author_proposals_and_manifest(tmp_path):
    seal = seal_candidate_holdout(generate_v2_candidates(), tmp_path)

    candidate_text = seal.candidates_path.read_text(encoding="utf-8")
    author_text = seal.author_proposals_path.read_text(encoding="utf-8")
    manifest = json.loads(seal.manifest_path.read_text(encoding="utf-8"))

    assert '"expected_skill"' not in candidate_text
    assert '"expected_arguments"' not in candidate_text
    assert '"expected_skill"' in author_text
    assert manifest["status"] == "v2_candidates_sealed_awaiting_human_annotation"
    assert manifest["system_evaluation_allowed"] is False
    assert manifest["n_cases"] == 120
    assert manifest["hashes"]["candidates_sha256"] == seal.candidates_sha256
    assert manifest["hashes"]["experiment_code_sha256"]
    assert manifest["hashes"]["catalog_sha256"]
    assert manifest["hashes"]["prompt_sha256"]
    assert manifest["hashes"]["provider_config_sha256"]


def test_annotation_packets_are_blank_blinded_and_cover_every_case(tmp_path):
    seal = seal_candidate_holdout(generate_v2_candidates(), tmp_path)

    for index, packet_path in enumerate(seal.annotation_packets, start=1):
        with packet_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 120
        assert len({row["request_id"] for row in rows}) == 120
        assert {row["annotator_id"] for row in rows} == {f"annotator_{index}"}
        assert all(row["annotation_status"] == "" for row in rows)
        assert all(row["annotated_skill"] == "" for row in rows)
        assert "author_expected_skill" not in rows[0]


def test_resealing_never_overwrites_a_human_edited_packet(tmp_path):
    seal = seal_candidate_holdout(generate_v2_candidates(), tmp_path)
    packet = seal.annotation_packets[0]
    original = packet.read_text(encoding="utf-8")
    edited = original.replace(",,,", ",IN_PROGRESS,,", 1)
    packet.write_text(edited, encoding="utf-8")

    seal_candidate_holdout(generate_v2_candidates(), tmp_path)

    assert packet.read_text(encoding="utf-8") == edited


def _complete_packet(path, cases, *, change_first_decision=None):
    by_id = {case.request_id: case for case in cases}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        assert fieldnames is not None
        rows = list(reader)
    for index, row in enumerate(rows):
        case = by_id[row["request_id"]]
        row.update(
            annotated_intent=case.canonical_intent,
            annotated_skill=case.expected_skill,
            annotated_arguments_json=json.dumps(
                case.expected_arguments, ensure_ascii=False
            ),
            annotated_decision=(
                change_first_decision
                if index == 0 and change_first_decision
                else case.expected_decision.value
            ),
            annotated_risk_class=case.risk_class.value,
            annotated_error_type=case.error_type,
            annotated_case_label=next(iter(case.labels)).value,
            clarification_required=str(case.clarification_required).lower(),
            state_transition=(
                "MAY_CHANGE" if case.expected_decision.value == "ALLOW" else "UNCHANGED"
            ),
            annotation_status="COMPLETE",
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_blank_packets_fail_closed_instead_of_counting_as_human_review(tmp_path):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)

    with pytest.raises(HumanGateIncomplete, match="incomplete"):
        review_annotation_packets(cases, *seal.annotation_packets)


def test_two_complete_agreeing_packets_produce_kappa_one(tmp_path):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)
    for packet in seal.annotation_packets:
        _complete_packet(packet, cases)

    review = review_annotation_packets(cases, *seal.annotation_packets)

    assert review.n_cases == 120
    assert review.agreement_rate == 1.0
    assert review.decision_kappa == 1.0
    assert review.disagreements == ()
    assert len(review.consensus) == 120


def test_disagreement_creates_blinded_adjudication_and_blocks_consensus(tmp_path):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)
    _complete_packet(seal.annotation_packets[0], cases)
    _complete_packet(seal.annotation_packets[1], cases, change_first_decision="DENY")

    review = review_annotation_packets(cases, *seal.annotation_packets)
    adjudication = write_adjudication_packet(review, tmp_path)
    with adjudication.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(review.disagreements) == 1
    assert len(rows) == 1
    assert rows[0]["adjudication_status"] == ""
    assert rows[0]["request_text"]
    assert review.semantic_gate_passed is False


def _complete_adjudication(path, annotation):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        assert fieldnames is not None
        rows = list(reader)
    assert len(rows) == 1
    rows[0].update(
        adjudicator_id="adjudicator_1",
        adjudicated_intent=annotation.intent,
        adjudicated_skill=annotation.skill,
        adjudicated_arguments_json=json.dumps(annotation.arguments, ensure_ascii=False),
        adjudicated_decision=annotation.decision,
        adjudicated_risk_class=annotation.risk_class,
        adjudicated_error_type=annotation.error_type,
        adjudicated_case_label=annotation.case_label,
        clarification_required=str(annotation.clarification_required).lower(),
        state_transition=annotation.state_transition,
        adjudication_status="COMPLETE",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_completed_third_party_adjudication_releases_semantic_gate(tmp_path):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)
    _complete_packet(seal.annotation_packets[0], cases)
    _complete_packet(seal.annotation_packets[1], cases, change_first_decision="DENY")
    review = review_annotation_packets(cases, *seal.annotation_packets)
    adjudication = write_adjudication_packet(review, tmp_path)
    first_disagreement = review.disagreements[0]
    _complete_adjudication(adjudication, review.annotations[first_disagreement][0])

    adjudicated = apply_adjudication_packet(review, adjudication)

    assert adjudicated.semantic_gate_passed is True
    assert adjudicated.agreement_rate == review.agreement_rate
    assert adjudicated.consensus[first_disagreement].decision == "ALLOW"


def test_incomplete_adjudication_fails_closed(tmp_path):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)
    _complete_packet(seal.annotation_packets[0], cases)
    _complete_packet(seal.annotation_packets[1], cases, change_first_decision="DENY")
    review = review_annotation_packets(cases, *seal.annotation_packets)
    adjudication = write_adjudication_packet(review, tmp_path)

    with pytest.raises(HumanGateIncomplete, match="incomplete adjudication"):
        apply_adjudication_packet(review, adjudication)


def _accept_state_packet(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        assert fieldnames is not None
        rows = list(reader)
    for row in rows:
        row["state_verdict"] = "ACCEPT"
        row["state_review_status"] = "COMPLETE"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_final_holdout_is_blocked_until_two_state_reviewers_accept(tmp_path):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)
    for packet in seal.annotation_packets:
        _complete_packet(packet, cases)
    semantic_review = review_annotation_packets(cases, *seal.annotation_packets)
    states = write_state_review_packets(cases, semantic_review, tmp_path)

    with pytest.raises(HumanGateIncomplete, match="state review"):
        finalize_v2_holdout(
            cases,
            semantic_review,
            states,
            tmp_path,
            candidate_manifest_path=seal.manifest_path,
        )


def test_two_human_state_acceptances_enable_content_addressed_gold(
    tmp_path, monkeypatch
):
    cases = generate_v2_candidates()
    seal = seal_candidate_holdout(cases, tmp_path)
    for packet in seal.annotation_packets:
        _complete_packet(packet, cases)
    semantic_review = review_annotation_packets(cases, *seal.annotation_packets)
    states = write_state_review_packets(cases, semantic_review, tmp_path)
    for packet in states.review_packets:
        _accept_state_packet(packet)

    finalized = finalize_v2_holdout(
        cases,
        semantic_review,
        states,
        tmp_path,
        candidate_manifest_path=seal.manifest_path,
    )
    loaded = load_finalized_holdout(finalized.gold_path, finalized.manifest_path)
    manifest = json.loads(finalized.manifest_path.read_text(encoding="utf-8"))

    assert isinstance(finalized, FinalizedHoldout)
    assert len(loaded) == 120
    assert all(case.initial_state != {"oracle_pending": True} for case in loaded)
    assert all(case.expected_final_state != {"oracle_pending": True} for case in loaded)
    assert manifest["system_evaluation_allowed"] is True
    assert manifest["decision_kappa"] == 1.0

    monkeypatch.setattr(
        prospective_evidence, "_experiment_code_hash", lambda: "changed"
    )
    with pytest.raises(HumanGateIncomplete, match="code changed"):
        load_finalized_holdout(finalized.gold_path, finalized.manifest_path)
