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
    assert first["schema_version"] == "anibench.level1-role-aware-assessment.v3-candidate1"
    assert first["overall_scalar"] is None
    assert first["public_rank_emission_permitted"] is False
    assert first["comparison_eligible"] is False
    assert first["promotion_allowed"] is False
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
        assert family["level1_target_attainment"]["state"] == "unresolved"
        assert family["level1_target_attainment"]["value"] is None
        assert family["level1_target_attainment"]["required_gate_ids"]
        for metric in family["native_metrics"]:
            assert metric["source_object_sha256"] == first["protocol_capacity_result_sha256"]
            assert metric["source_locator"].startswith("/scenarios/0/families/")


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
