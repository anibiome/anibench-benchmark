from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from anibench.api import score_joint_information_v2
from anibench.information_v2 import canonical_matrix_sha256
from anibench.v2 import V2RunError, score_information_run


ROOT = Path(__file__).resolve().parents[1]


def digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def run_payload() -> dict:
    information = [[4.0, 0.0], [0.0, 4.0]]
    prior = [[1.0, 0.0], [0.0, 1.0]]
    reference = [[4.0, 0.0], [0.0, 4.0]]
    basis = [[1.0, 0.0], [0.0, 1.0]]
    return {
        "contract": "anibench.information-run.v2-candidate1",
        "benchmark_suite_version": "anibench.v2-candidate1",
        "lane": "design_preview",
        "parameter_space_hash": digest("parameter"),
        "prior_metric_hash": digest("prior"),
        "reference_level_hash": digest("caller-selected-reference"),
        "event_manifest_hash": digest("events"),
        "intervention_design_hash": digest("intervention"),
        "uncertainty_model_hash": digest("uncertainty"),
        "reference_authority_id": "caller-fake-authority",
        "matrix_hashes": {
            "information_matrix_sha256": canonical_matrix_sha256(information),
            "prior_precision_matrix_sha256": canonical_matrix_sha256(prior),
            "reference_information_matrix_sha256": canonical_matrix_sha256(reference),
            "reference_direction_basis_sha256": canonical_matrix_sha256(basis),
        },
        "information_matrix": information,
        "prior_precision": prior,
        "reference_information": reference,
        "reference_direction_basis": basis,
        "source_objects": [{"object_id": "source:fixture", "sha256": digest("source")}],
    }


def test_caller_selected_reference_emits_absolute_replay_only() -> None:
    payload = run_payload()
    packet = score_joint_information_v2(payload)
    assert packet == score_information_run(payload)
    assert packet["contract"] == "anibench.information-replay-packet.v2-candidate1"
    assert packet["promotion_allowed"] is False
    assert packet["claim_state"] == "implementation_candidate_biological_promotion_gated"
    assert packet["reference_metrics"] is None
    assert packet["illustrative_reference_metrics"] is None
    assert packet["identity_verification"]["recognized_illustrative_fixture"] is False
    assert packet["identity_verification"]["promotable_level_1_reference_verified"] is False
    assert packet["claim_permissions"]["level_1_completion_claim_allowed"] is False
    assert packet["claim_permissions"]["public_completion_claim_allowed"] is False
    assert packet["claim_permissions"]["public_score_allowed"] is False
    assert packet["claim_permissions"]["public_rank_allowed"] is False
    assert (
        packet["caller_declared_identity"]["event_manifest_hash"] == payload["event_manifest_hash"]
    )
    serialized = json.dumps(packet, sort_keys=True)
    assert "level1_completion_percent" not in serialized
    assert '"illustrative_completion_percent": 100' not in serialized


def test_only_exact_local_mechanics_fixture_gets_illustrative_metrics() -> None:
    fixture = json.loads(
        (ROOT / "spec/v2/mechanics-fixtures/illustrative-reference-2d.json").read_text(
            encoding="utf-8"
        )
    )
    packet = score_information_run(fixture)
    illustrative = packet["illustrative_reference_metrics"]
    assert packet["reference_metrics"] is None
    assert packet["identity_verification"]["recognized_illustrative_fixture"] is True
    assert packet["identity_verification"]["recognized_reference_authority_id"] == (
        "illustrative-mechanics-2d-v1"
    )
    assert illustrative["claim_class"] == (
        "illustrative_mechanics_fixture_not_biological_reference"
    )
    assert illustrative["promotion_allowed"] is False
    assert illustrative["public_completion_claim_allowed"] is False
    assert illustrative["illustrative_completion_percent"] < 100
    assert packet["claim_permissions"]["level_1_completion_claim_allowed"] is False


def test_copying_fixture_matrices_with_fake_hash_identity_cannot_gain_recognition() -> None:
    fixture = json.loads(
        (ROOT / "spec/v2/mechanics-fixtures/illustrative-reference-2d.json").read_text(
            encoding="utf-8"
        )
    )
    attacked = copy.deepcopy(fixture)
    attacked["event_manifest_hash"] = digest("fake-events")
    packet = score_information_run(attacked)
    assert packet["reference_metrics"] is None
    assert packet["illustrative_reference_metrics"] is None
    assert packet["identity_verification"]["recognized_illustrative_fixture"] is False
    assert packet["claim_permissions"]["public_completion_claim_allowed"] is False


def test_v2_run_rejects_unbound_malformed_or_hash_mismatched_matrices() -> None:
    missing = run_payload()
    missing.pop("source_objects")
    with pytest.raises(V2RunError):
        score_information_run(missing)

    malformed = run_payload()
    malformed["information_matrix"] = [[1.0, 0.0]]
    malformed["matrix_hashes"]["information_matrix_sha256"] = canonical_matrix_sha256([[1.0]])
    with pytest.raises(ValueError, match="square matrix"):
        score_information_run(malformed)

    mismatch = run_payload()
    mismatch["matrix_hashes"]["information_matrix_sha256"] = digest("fake-matrix")
    with pytest.raises(V2RunError, match="does not match server-computed"):
        score_information_run(mismatch)

    zero_hash = run_payload()
    zero_hash["parameter_space_hash"] = "sha256:" + "0" * 64
    with pytest.raises(V2RunError, match="does not match"):
        score_information_run(zero_hash)


def test_reference_basis_semantics_are_enforced_before_replay() -> None:
    payload = run_payload()
    payload["reference_direction_basis"] = [[1.0, 1.0], [0.0, 1.0]]
    payload["matrix_hashes"]["reference_direction_basis_sha256"] = canonical_matrix_sha256(
        payload["reference_direction_basis"]
    )
    with pytest.raises(ValueError, match="column-orthonormal"):
        score_information_run(payload)
