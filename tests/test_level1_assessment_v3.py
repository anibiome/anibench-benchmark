from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from anibench.level1_assessment_v3 import assess_protocol_capacity_role_aware


ROOT = Path(__file__).resolve().parents[1]


def _input() -> dict:
    return json.loads((ROOT / "web/protocol-capacity-example.json").read_text())


def test_role_aware_assessment_is_deterministic_six_family_and_noncompensatory() -> None:
    first = assess_protocol_capacity_role_aware(_input())
    second = assess_protocol_capacity_role_aware(copy.deepcopy(_input()))
    assert first == second
    assert first["schema_version"] == "anibench.level1-role-aware-assessment.v3-candidate2"
    assert first["overall_scalar"] is None
    assert first["public_rank_emission_permitted"] is False
    assert first["comparison_eligible"] is False
    assert first["promotion_allowed"] is False
    assert first["geometry_authority_state"] == "custom_unverified"
    assert first["implementation_receipt"]["package_name"] == "anibench"
    assert len(first["implementation_receipt"]["source_modules"]) == 5
    assert first["implementation_receipt"]["source_bundle_sha256"].startswith("sha256:")
    assert first["implementation_receipt"]["runtime_environment"]["numpy_version"]
    assert {
        "causal_v2.py",
        "information_v2.py",
        "level1_assessment_v3.py",
        "level1_target_v3.py",
        "protocol_capacity_v2.py",
    }.issubset(
        {row["module"] for row in first["implementation_receipt"]["source_modules"]}
    )
    families = first["scenarios"][0]["families"]
    assert [row["family_id"] for row in families] == [
        "intensive",
        "extensive",
        "longitudinal",
        "causal",
        "personalized_sequential",
        "transport",
    ]
    for family in families:
        assert family["blocker_codes"] == []
        assert family["level1_target_attainment"]["state"] == "unresolved"
        assert family["level1_target_attainment"]["value"] is None
        assert family["level1_target_attainment"]["required_gate_ids"]
        for metric in family["native_metrics"]:
            assert metric["source_object_sha256"] == first["protocol_capacity_result_sha256"]
            assert metric["source_locator"].startswith("/scenarios/0/families/")
        if family["family_id"] != "transport":
            assert family["metric_groups"] == []


def test_role_aware_assessment_preserves_multi_axis_transport_vector() -> None:
    protocol = _input()
    transport = protocol["causal_geometry"]["transport_geometry"]
    extra = copy.deepcopy(transport["transport_axis_families"][0])
    extra["transport_axis_family_id"] = "secondary-site-transport"
    extra["required_transport_axis_ids"] = ["environment-context"]
    extra["coordinate_scale_authority"]["source_locator"] = (
        "illustrative:transport-axis-scale:environment-context"
    )
    transport["transport_axis_families"].append(extra)
    for index, context in enumerate(transport["contexts"]):
        context["transport_coordinates"].append(
            {"transport_axis_id": "environment-context", "value": float(index)}
        )

    result = assess_protocol_capacity_role_aware(protocol)
    family = next(
        row for row in result["scenarios"][0]["families"] if row["family_id"] == "transport"
    )
    assert family["design_resolution_state"] == "resolved_axis_family_vector"
    assert [metric["value"] for metric in family["native_metrics"]] == [None, None]
    assert [group["group_id"] for group in family["metric_groups"]] == [
        "secondary-site-transport",
        "site-transport",
    ]
    for group in family["metric_groups"]:
        assert group["design_resolution_state"] == "resolved"
        assert [metric["state"] for metric in group["native_metrics"]] == [
            "computed_unverified_geometry",
            "computed_unverified_geometry",
        ]
        assert all(
            "/axis_family_frontier/" in metric["source_locator"]
            for metric in group["native_metrics"]
        )


def test_custom_geometry_is_never_labeled_resolved_level1() -> None:
    result = assess_protocol_capacity_role_aware(_input())
    assert result["geometry_authority_state"] == "custom_unverified"
    for family in result["scenarios"][0]["families"]:
        for metric in family["native_metrics"]:
            if metric["value"] is not None:
                assert metric["state"] == "computed_unverified_geometry"
                assert metric["geometry_authority_state"] == "custom_unverified"
        for group in family["metric_groups"]:
            for metric in group["native_metrics"]:
                if metric["value"] is not None:
                    assert metric["state"] == "computed_unverified_geometry"
                    assert metric["geometry_authority_state"] == "custom_unverified"


def test_one_person_far_future_schedule_cannot_inflate_eval_longitudinal_primary() -> None:
    base = _input()
    attacked = copy.deepcopy(base)
    attacked["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-one-person-outlier",
            "canonical_event_unit_id": "participant-state-visit",
        }
    )
    outlier = copy.deepcopy(
        attacked["measurement_geometry"]["participant_event_schedules"][1]
    )
    outlier.update(
        {
            "schedule_id": "schedule-one-person-outlier",
            "participant_event_lineage_id": "lineage-one-person-outlier",
            "joint_observation_bundle_id": "bundle-one-person-outlier",
            "participant_count": {"state": "exact", "value": 1},
            "events_per_participant": {"state": "exact", "value": 1},
            "retention_fraction": {"state": "exact", "value": 1},
            "within_person_repetition_correlation": {"state": "exact", "value": 0},
            "temporal_offsets": [36500],
            "source_locator": "illustrative:schedule:one-person-outlier",
        }
    )
    attacked["measurement_geometry"]["participant_event_schedules"].append(outlier)

    def primary(payload: dict) -> list[object]:
        result = assess_protocol_capacity_role_aware(payload)
        family = next(
            row
            for row in result["scenarios"][0]["families"]
            if row["family_id"] == "longitudinal"
        )
        return [metric["value"] for metric in family["native_metrics"][:2]]

    assert primary(attacked) == primary(base)


def test_dependent_randomization_is_typed_unknown_not_zero_capacity() -> None:
    protocol = _input()
    protocol["causal_geometry"]["assignment_stages"][0]["assignment_mechanism"] = (
        "cluster_randomized"
    )
    for context in protocol["causal_geometry"]["transport_geometry"]["contexts"]:
        context["assignment_mechanism"] = "cluster_randomized"

    result = assess_protocol_capacity_role_aware(protocol)
    families = {
        row["family_id"]: row for row in result["scenarios"][0]["families"]
    }
    for family_id in ("causal", "personalized_sequential", "transport"):
        family = families[family_id]
        assert family["blocker_codes"] == [
            "DEPENDENT_RANDOMIZATION_GEOMETRY_UNSUPPORTED"
        ]
        assert family["design_resolution_state"] == (
            "unresolved_unsupported_dependence_geometry"
        )
        assert all(metric["value"] is None for metric in family["native_metrics"])
        assert all(
            metric["value"] is None
            for group in family["metric_groups"]
            for metric in group["native_metrics"]
        )


def test_role_aware_assessment_validates_against_schema() -> None:
    schema = json.loads(
        (ROOT / "schemas/v3/level1-role-aware-assessment.schema.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(assess_protocol_capacity_role_aware(_input()))


def test_role_aware_assessment_contains_no_v2_completion_or_global_enrollment_claim() -> None:
    text = json.dumps(assess_protocol_capacity_role_aware(_input()), sort_keys=True)
    for forbidden in (
        "level1_target_percent",
        "level1_uncapped_ratio",
        "target_total_enrollment",
        "193536",
        "1544148",
    ):
        assert forbidden not in text
