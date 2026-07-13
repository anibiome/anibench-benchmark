from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from anibench.level1_target_v3 import (
    BASELINE_MODIFIER_IDS,
    CAUSAL_RESPONSE_ESTIMAND_IDS,
    DIRECT_MUTABLE_OUTCOME_IDS,
    EXPOSURE_CONTEXT_IDS,
    FAMILY_IDS,
    HETEROGENEITY_OC_IDS,
    LONGITUDINAL_ESTIMAND_IDS,
    RELATIONAL_ESTIMAND_ROLES,
    TRANSPORT_ESTIMAND_IDS,
    V2_COORDINATE_REGISTRY_RAW_SHA256,
    V2_COORDINATE_IDENTITY_SHA256,
    V2_TARGET_PATH,
    V2_TARGET_RAW_SHA256,
    Level1V3AuthorityError,
    build_artifact_bytes,
    load_role_aware_authority,
    readback_role_aware_authority,
    validate_role_aware_authority,
    write_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "spec/v3/level1/role-aware-target-requirements.v3.json"
IMPACT_PATH = (
    ROOT
    / "spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json"
)
AUTHORITY_SCHEMA_PATH = (
    ROOT / "schemas/v3/level1-role-aware-target-authority.schema.json"
)
IMPACT_SCHEMA_PATH = (
    ROOT / "schemas/v3/level1-v2-to-v3-impact-receipt.schema.json"
)


def _json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _all_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [child for item in value.values() for child in _all_values(item)]
    if isinstance(value, list):
        return [child for item in value for child in _all_values(item)]
    return [value]


def _all_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            keys.append(key)
            keys.extend(_all_keys(item))
        return keys
    if isinstance(value, list):
        return [key for item in value for key in _all_keys(item)]
    return []


def test_v3_artifacts_validate_against_machine_readable_schemas() -> None:
    authority = _json(AUTHORITY_PATH)
    impact = _json(IMPACT_PATH)
    authority_schema = _json(AUTHORITY_SCHEMA_PATH)
    impact_schema = _json(IMPACT_SCHEMA_PATH)
    Draft202012Validator.check_schema(authority_schema)
    Draft202012Validator.check_schema(impact_schema)
    Draft202012Validator(authority_schema).validate(authority)
    Draft202012Validator(impact_schema).validate(impact)
    proof = validate_role_aware_authority(authority)
    assert proof == {
        "contract": "anibench.level1-role-aware-target-authority-validation.v3",
        "valid": True,
        "ordered_block_count": 6,
        "ordered_coordinate_count": 64,
        "role_partition_count": 7,
        "direct_mutable_outcome_count": 22,
        "relational_estimand_count": 40,
        "family_count": 6,
        "unresolved_gate_count": 11,
        "global_enrollment_state": "unresolved",
        "promotion_allowed": False,
    }


def test_v3_preserves_exact_v2_map_but_not_v2_role_semantics() -> None:
    authority = _json(AUTHORITY_PATH)
    v2_registry_path = ROOT / "spec/v2/level1/biological-coordinate-registry.json"
    v2_target_path = ROOT / "spec/v2/level1/normative-target-requirements.v2.json"
    assert _sha256(v2_registry_path) == V2_COORDINATE_REGISTRY_RAW_SHA256
    if v2_target_path.exists():
        assert _sha256(v2_target_path) == V2_TARGET_RAW_SHA256
    else:
        assert authority["relation_to_v2"]["v2_target"]["raw_sha256"] == (
            V2_TARGET_RAW_SHA256
        )

    v2_registry = _json(v2_registry_path)
    v2_rows = [
        (block["block_id"], block["symbol"], coordinate_id, name)
        for block in v2_registry["blocks"]
        for coordinate_id, name in block["coordinates"]
    ]
    v3_rows = [
        (
            block["block_id"],
            block["symbol"],
            coordinate["coordinate_id"],
            coordinate["name"],
        )
        for block in authority["scientific_map"]["blocks"]
        for coordinate in block["coordinates"]
    ]
    assert v3_rows == v2_rows
    assert len(v3_rows) == 64
    assert len(authority["scientific_map"]["blocks"]) == 6
    assert authority["scientific_map"]["ordered_coordinate_identity_sha256"] == (
        V2_COORDINATE_IDENTITY_SHA256
    )

    relation = authority["relation_to_v2"]
    assert relation["v2_coordinate_registry"]["raw_sha256"] == V2_COORDINATE_REGISTRY_RAW_SHA256
    assert relation["v2_target"]["raw_sha256"] == V2_TARGET_RAW_SHA256
    assert relation["state"] == "substantive_successor_candidate_not_promoted"


def test_estimation_roles_form_the_frozen_non_overlapping_partition() -> None:
    authority = _json(AUTHORITY_PATH)
    roles = {
        row["role_id"]: tuple(row["coordinate_ids"])
        for row in authority["estimation_role_authority"]["roles"]
    }
    assert roles == {
        "direct_mutable_outcome_basis": DIRECT_MUTABLE_OUTCOME_IDS,
        "baseline_modifier": BASELINE_MODIFIER_IDS,
        "exposure_context": EXPOSURE_CONTEXT_IDS,
        "longitudinal_state_space_estimand": LONGITUDINAL_ESTIMAND_IDS,
        "causal_response_estimand": CAUSAL_RESPONSE_ESTIMAND_IDS,
        "heterogeneity_operating_characteristic": HETEROGENEITY_OC_IDS,
        "transport_estimand": TRANSPORT_ESTIMAND_IDS,
    }
    membership = [coordinate_id for coordinate_ids in roles.values() for coordinate_id in coordinate_ids]
    assert len(membership) == 64
    assert len(set(membership)) == 64
    assert set(DIRECT_MUTABLE_OUTCOME_IDS) == {
        *(f"S{index:02d}" for index in range(2, 9)),
        *(f"S{index:02d}" for index in range(10, 17)),
        *(f"F{index:02d}" for index in range(1, 9)),
    }
    assert BASELINE_MODIFIER_IDS == ("S01",)
    assert EXPOSURE_CONTEXT_IDS == ("S09",)


def test_D_P_H_T_are_relational_and_never_direct_outcome_modifier_or_context_strata() -> None:
    authority = _json(AUTHORITY_PATH)
    role_rows = authority["estimation_role_authority"]["roles"]
    relational_ids = {
        coordinate_id
        for row in role_rows
        if row["role_id"] in RELATIONAL_ESTIMAND_ROLES
        for coordinate_id in row["coordinate_ids"]
    }
    expected_relational = {
        *LONGITUDINAL_ESTIMAND_IDS,
        *CAUSAL_RESPONSE_ESTIMAND_IDS,
        *HETEROGENEITY_OC_IDS,
        *TRANSPORT_ESTIMAND_IDS,
    }
    assert relational_ids == expected_relational
    assert not relational_ids & set(DIRECT_MUTABLE_OUTCOME_IDS)
    assert not relational_ids & set(BASELINE_MODIFIER_IDS)
    assert not relational_ids & set(EXPOSURE_CONTEXT_IDS)

    direct = set(authority["estimation_role_authority"]["direct_event_outcome_coordinate_ids"])
    modifiers = set(authority["estimation_role_authority"]["raw_modifier_coordinate_ids"])
    contexts = set(authority["estimation_role_authority"]["exposure_context_coordinate_ids"])
    assert not relational_ids & direct
    assert not relational_ids & modifiers
    assert not relational_ids & contexts


def test_raw_context_covariates_are_not_transport_estimands() -> None:
    boundary = _json(AUTHORITY_PATH)["raw_context_transport_boundary"]
    assert boundary["raw_context_covariates"]["ontology_location"] == (
        "source_specific_registry_outside_the_64_coordinate_map"
    )
    assert boundary["raw_context_covariates"]["within_map_latent_context_coordinate_ids"] == [
        "S09"
    ]
    assert boundary["transport_estimands"]["coordinate_ids"] == list(TRANSPORT_ESTIMAND_IDS)
    support = boundary["joint_support_authority"]
    assert support == {
        "fact_type": "unknown",
        "state": "unresolved",
        "value": None,
        "source_bound": False,
        "blocker_code": "MISSING_SOURCE_BOUND_JOINT_CONTEXT_SUPPORT",
        "matrix_or_bound_status": "not_provided_no_matrix_fabricated",
        "required_gate_id": "source_bound_joint_context_support",
    }


def test_every_family_has_distinct_unknown_operating_characteristics_and_enrollment() -> None:
    authority = _json(AUTHORITY_PATH)
    families = authority["family_operating_characteristic_authority"]["families"]
    assert [family["family_id"] for family in families] == list(FAMILY_IDS)
    for family in families:
        assert family["operating_characteristic_target"]["fact_type"] == "unknown"
        assert family["operating_characteristic_target"]["state"] == "unresolved"
        assert family["operating_characteristic_target"]["value"] is None
        assert family["family_enrollment_requirement"]["fact_type"] == "unknown"
        assert family["family_enrollment_requirement"]["state"] == "unresolved"
        assert family["family_enrollment_requirement"]["value"] is None
        assert family["required_gate_ids"]
        assert family["forbidden_substitutions"]

    family_by_id = {family["family_id"]: family for family in families}
    assert family_by_id["longitudinal"]["target_coordinate_roles"] == [
        "longitudinal_state_space_estimand"
    ]
    assert family_by_id["causal"]["target_coordinate_roles"] == [
        "causal_response_estimand"
    ]
    assert family_by_id["personalized_sequential"]["target_coordinate_roles"] == [
        "heterogeneity_operating_characteristic"
    ]
    assert family_by_id["transport"]["target_coordinate_roles"] == ["transport_estimand"]


def test_no_global_enrollment_scalar_or_rank_is_emitted() -> None:
    authority = _json(AUTHORITY_PATH)
    global_enrollment = authority["enrollment_authority"]["global_enrollment"]
    assert global_enrollment == {
        "fact_type": "unknown",
        "state": "unresolved",
        "value": None,
        "unit": "participants",
        "blocker_code": (
            "WITHHELD_PENDING_ALL_FAMILY_OPERATING_CHARACTERISTICS_AND_"
            "SOURCE_BOUND_JOINT_CONTEXT_SUPPORT"
        ),
    }
    assert not any(authority["enrollment_authority"]["release_condition"].values())
    vector = authority["noncompensatory_family_vector"]
    assert [row["family_id"] for row in vector["entries"]] == list(FAMILY_IDS)
    assert all(row["state"] == "unresolved" and row["value"] is None for row in vector["entries"])
    assert vector["aggregation"]["state"] == "forbidden"
    assert vector["aggregation"]["value"] is None
    assert vector["rank"]["state"] == "forbidden"
    assert vector["rank"]["value"] is None
    assert 1_544_148 not in _all_values(authority)
    forbidden_v2_fields = {
        "target_total_enrollment",
        "participants_per_context",
        "hypothesis_count",
        "hypothesis_universe",
        "stage_power",
        "required_enrollment_ceiling",
        "required_enrollment_raw",
        "level1_target_percent",
        "level1_uncapped_ratio",
        "completion_percent",
        "overall_scalar",
        "scalar_score",
        "score",
    }
    assert not forbidden_v2_fields & set(_all_keys(authority))
    assert authority["release_state"] == {
        "promotion_allowed": False,
        "public_rank_allowed": False,
        "global_enrollment_claim_allowed": False,
        "reason_code": "ROLE_AUTHORITY_FROZEN_OPERATING_CHARACTERISTICS_UNRESOLVED",
    }


def test_all_unresolved_gates_are_typed_and_promotion_blocking() -> None:
    authority = _json(AUTHORITY_PATH)
    gates = authority["typed_unresolved_gates"]
    assert len(gates) == 11
    assert len({gate["gate_id"] for gate in gates}) == 11
    assert all(
        gate["fact_type"] == "unknown"
        and gate["state"] == "unresolved"
        and gate["value"] is None
        and gate["promotion_blocking"] is True
        and gate["required_source_objects"]
        for gate in gates
    )
    gate_ids = {gate["gate_id"] for gate in gates}
    assert "source_bound_joint_context_support" in gate_ids
    assert "cross_family_reuse_and_covariance_authority" in gate_ids
    assert "independent_role_and_operating_characteristic_attestation" in gate_ids


def test_v2_to_v3_impact_receipt_is_substantive_and_hash_bound() -> None:
    impact = _json(IMPACT_PATH)
    assert impact["candidate_authority"]["raw_sha256"] == _sha256(AUTHORITY_PATH)
    assert impact["source_authority"]["v2_target"]["raw_sha256"] == V2_TARGET_RAW_SHA256
    assert impact["source_authority"]["v2_coordinate_registry"]["raw_sha256"] == (
        V2_COORDINATE_REGISTRY_RAW_SHA256
    )
    change_ids = {change["change_id"] for change in impact["substantive_changes"]}
    assert change_ids == {
        "direct_outcome_basis_narrowed",
        "modifier_roles_narrowed",
        "longitudinal_role_corrected",
        "causal_role_corrected",
        "heterogeneity_role_corrected",
        "transport_context_separated",
        "global_enrollment_withheld",
        "family_vector_explicitly_noncompensatory",
    }
    assert impact["machine_proof"]["v2_global_enrollment_inherited"] is False
    assert impact["machine_proof"]["fabricated_joint_support_matrix_emitted"] is False
    assert impact["machine_proof"]["numeric_rank_emitted"] is False
    assert impact["disposition"] == {
        "promotion_allowed": False,
        "stable_rank_allowed": False,
        "global_enrollment_allowed": False,
        "reason_code": "SUBSTANTIVE_V3_AUTHORITY_REQUIRES_SOURCE_BOUND_CLOSURE",
    }


def test_generated_artifacts_are_deterministic_and_exactly_checked_in(tmp_path: Path) -> None:
    if (ROOT / V2_TARGET_PATH).exists():
        generated = build_artifact_bytes(ROOT)
        for relative_path, payload in generated.items():
            assert (ROOT / relative_path).read_bytes() == payload

        first = tmp_path / "first"
        second = tmp_path / "second"
        first_hashes = write_artifacts(ROOT, first)
        second_hashes = write_artifacts(ROOT, second)
        assert first_hashes == second_hashes
        for relative_path in generated:
            assert (first / relative_path).read_bytes() == (second / relative_path).read_bytes()

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_level1_target_v3.py"),
            "--repo-root",
            str(ROOT),
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == {"mismatches": [], "valid": True}


def test_path_readback_matches_installed_package_safe_validator_contract() -> None:
    authority = load_role_aware_authority(AUTHORITY_PATH)
    assert authority["target_id"] == "anibench-human-trial-level1-role-aware-target-v3"
    readback = readback_role_aware_authority(AUTHORITY_PATH, IMPACT_PATH)
    assert readback == {
        "contract": "anibench.level1-role-aware-target-installed-readback.v1",
        "authority_raw_sha256": _sha256(AUTHORITY_PATH),
        "impact_receipt_raw_sha256": _sha256(IMPACT_PATH),
        "target_id": "anibench-human-trial-level1-role-aware-target-v3",
        "validation": {
            "contract": "anibench.level1-role-aware-target-authority-validation.v3",
            "valid": True,
            "ordered_block_count": 6,
            "ordered_coordinate_count": 64,
            "role_partition_count": 7,
            "direct_mutable_outcome_count": 22,
            "relational_estimand_count": 40,
            "family_count": 6,
            "unresolved_gate_count": 11,
            "global_enrollment_state": "unresolved",
            "promotion_allowed": False,
        },
        "promotion_allowed": False,
        "global_enrollment_state": "unresolved",
        "rank_state": "forbidden",
    }
    with pytest.raises(Level1V3AuthorityError, match="must be supplied together"):
        readback_role_aware_authority(AUTHORITY_PATH, None)


@pytest.mark.parametrize(
    "attack,match",
    [
        (
            lambda value: value["estimation_role_authority"]["roles"][0][
                "coordinate_ids"
            ].append("D01"),
            "overlapping roles",
        ),
        (
            lambda value: value["enrollment_authority"]["global_enrollment"].update(
                {"fact_type": "exact", "state": "resolved", "value": 1000}
            ),
            "global enrollment is prohibited",
        ),
        (
            lambda value: value["raw_context_transport_boundary"][
                "joint_support_authority"
            ].update({"fact_type": "exact", "state": "resolved", "value": []}),
            "joint context support must remain typed unresolved",
        ),
        (
            lambda value: value["release_state"].update({"promotion_allowed": True}),
            "cannot be promoted",
        ),
        (
            lambda value: value["noncompensatory_family_vector"]["rank"].update(
                {"state": "resolved", "value": 1}
            ),
            "rank must remain forbidden",
        ),
        (
            lambda value: value["scientific_map"]["blocks"][0]["coordinates"][0].update(
                {"name": "silently_rewritten_coordinate"}
            ),
            "coordinate IDs, names, order",
        ),
        (
            lambda value: value["family_operating_characteristic_authority"]["families"][
                4
            ]["target_coordinate_roles"].append("causal_response_estimand"),
            "family role or operating-characteristic contract changed",
        ),
    ],
)
def test_validator_rejects_role_enrollment_support_promotion_and_rank_attacks(
    attack: Any, match: str
) -> None:
    attacked = copy.deepcopy(_json(AUTHORITY_PATH))
    attack(attacked)
    with pytest.raises(Level1V3AuthorityError, match=match):
        validate_role_aware_authority(attacked)
