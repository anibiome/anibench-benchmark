from __future__ import annotations

import json

import pytest

from anibench.intake import snapshot_clinicaltrials_study
from scripts.run_ctgov_50_stress_test import (
    StressTestError,
    audit_study_snapshot,
    extract_registry_record,
    sparse_design_input,
)


def _study(
    *,
    nct_id: str = "NCT01234567",
    enrollment_count: int | None = 120,
    enrollment_type: str | None = "ACTUAL",
    allocation: str | None = "RANDOMIZED",
    arm_count: int | None = 2,
) -> dict:
    design: dict = {"studyType": "INTERVENTIONAL", "designInfo": {}}
    if enrollment_count is not None or enrollment_type is not None:
        design["enrollmentInfo"] = {}
        if enrollment_count is not None:
            design["enrollmentInfo"]["count"] = enrollment_count
        if enrollment_type is not None:
            design["enrollmentInfo"]["type"] = enrollment_type
    if allocation is not None:
        design["designInfo"]["allocation"] = allocation
    protocol: dict = {
        "identificationModule": {"nctId": nct_id, "briefTitle": "Fixture trial"},
        "statusModule": {"overallStatus": "COMPLETED"},
        "designModule": design,
        "outcomesModule": {"outcomes": [{"measure": "Outcome that must not become biology"}]},
        "armsInterventionsModule": {
            "interventions": [{"name": "Intervention that must not become an operator"}]
        },
    }
    if arm_count is not None:
        protocol["armsInterventionsModule"]["armGroups"] = [
            {"label": f"Arm {index + 1}"} for index in range(arm_count)
        ]
    return {"protocolSection": protocol}


def _snapshot(payload: dict):
    body = json.dumps(payload).encode("utf-8")

    def opener(_request, *, timeout):
        assert timeout > 0
        return body

    return snapshot_clinicaltrials_study(
        payload["protocolSection"]["identificationModule"]["nctId"],
        opener=opener,
        retrieved_at="2026-07-14T12:00:00Z",
    )


@pytest.mark.parametrize(
    ("enrollment_type", "expected_state"),
    (("ACTUAL", "exact"), ("ESTIMATED", "conditional"), (None, "unknown")),
)
def test_population_state_preserves_registry_enrollment_semantics(
    enrollment_type: str | None, expected_state: str
) -> None:
    record = extract_registry_record(_snapshot(_study(enrollment_type=enrollment_type)))
    design, _mapping = sparse_design_input(record)
    assert design["population"]["state"] == expected_state
    if expected_state == "unknown":
        assert design["population"]["value"] is None
    else:
        assert design["population"]["value"] == 120


def test_registry_names_do_not_create_measurement_or_operator_geometry() -> None:
    record = extract_registry_record(_snapshot(_study()))
    design, mapping = sparse_design_input(record)
    assert design["operator_families"] == []
    assert design["measurement_modules"] == [
        {
            "module_id": "registry-measurement-geometry-unresolved",
            "label": "Registry outcomes require source review before biological encoding",
            "evidence_state": "unknown",
            "events_per_participant": None,
        }
    ]
    assert mapping["operator_families"] == "not_inferred_from_intervention_menu"
    assert mapping["measurement_modules"] == "not_inferred_from outcome names or counts"


def test_randomized_allocation_without_resolved_arm_geometry_stays_unknown() -> None:
    record = extract_registry_record(_snapshot(_study(allocation="RANDOMIZED", arm_count=None)))
    design, _mapping = sparse_design_input(record)
    assert design["policy_arms"] is None
    assert design["randomized_policy"] is None


def test_nonrandomized_allocation_maps_to_false_without_inventing_control() -> None:
    record = extract_registry_record(_snapshot(_study(allocation="NON_RANDOMIZED", arm_count=1)))
    design, _mapping = sparse_design_input(record)
    assert design["randomized_policy"] is False
    assert design["concurrent_control"] is None


def test_audit_fails_closed_on_identity_mismatch() -> None:
    snapshot = _snapshot(_study(nct_id="NCT01234567"))
    with pytest.raises(StressTestError, match="identity mismatch"):
        audit_study_snapshot(
            snapshot,
            expected_nct_id="NCT76543210",
            stratum_id="fixture",
            search_source={"source_uri": "fixture", "raw_content_sha256": "0" * 64},
        )


def test_sparse_audit_emits_no_score_rank_information_or_imputation() -> None:
    snapshot = _snapshot(_study())
    result = audit_study_snapshot(
        snapshot,
        expected_nct_id="NCT01234567",
        stratum_id="fixture",
        search_source={"source_uri": "fixture", "raw_content_sha256": "0" * 64},
    )
    assert result["passed"] is True
    assert result["intake_score_eligible"] is False
    assert result["compiler_probe"]["promotion_allowed"] is False
    assert result["compiler_probe"]["emission_policy"] == {
        "composite_coordinate_emitted": False,
        "ordinal_position_emitted": False,
        "biological_information_inference_emitted": False,
        "missing_value_imputation_used": False,
    }
