from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas" / "v2"
SHA = "0" * 64


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMAS = {
    name: _load_json(SCHEMA_ROOT / name)
    for name in (
        "uncertainty.schema.json",
        "event-manifest.schema.json",
        "intervention-design.schema.json",
        "reference-registry.schema.json",
    )
}
REGISTRY = Registry().with_resources(
    [(schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS.values()]
)


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        SCHEMAS[name],
        registry=REGISTRY,
        format_checker=FormatChecker(),
    )


def _ref(coordinate_id: str) -> dict[str, str]:
    return {"uncertainty_coordinate_id": coordinate_id}


def _receipt() -> dict:
    return {
        "source_receipt_id": "source-01",
        "sha256": SHA,
        "locator": "protocol:section-1",
        "authority": "protocol",
    }


def _common_coordinate(state: str, **values) -> dict:
    return {
        "state": state,
        "unit": values.pop("unit", "fraction"),
        "evidence_class": "protocol_document_extracted",
        "source_receipt_ids": ["source-01"],
        **values,
    }


def uncertainty_fixture() -> dict:
    coordinates = {
        "participant-count": _common_coordinate("exact", unit="people", value=200),
        "event-count": _common_coordinate("exact", unit="events_per_person", value=12),
        "observation-span": _common_coordinate("interval", unit="day", lower=350, upper=380, lower_inclusive=True, upper_inclusive=True, nominal=365),
        "target-count-a": _common_coordinate("exact", unit="targets", value=1000),
        "target-count-b": _common_coordinate("unknown", unit="targets", unknown_reason="platform not frozen", admissible_lower=1, score_semantics="interval_only_no_point_imputation"),
        "quality": _common_coordinate("distribution", distribution={"family": "beta", "alpha": 9, "beta": 1}, support={"lower": 0, "upper": 1}, sampling_seed=20260712),
        "completeness": _common_coordinate("exact", value=0.9),
        "standardization": _common_coordinate("exact", value=1),
        "measurement-error": _common_coordinate("interval", unit="standardized_noise", lower=0.1, upper=0.3, lower_inclusive=True, upper_inclusive=True),
        "identity-linkage": _common_coordinate("exact", value=1),
        "time-linkage": _common_coordinate("exact", value=1),
        "joint-event-count": _common_coordinate("exact", unit="events", value=1800),
        "specimen-lineage-linkage": _common_coordinate("exact", value=1),
        "compatible-window": _common_coordinate("exact", unit="day", value=1),
        "dose-a": _common_coordinate("interval", unit="protocol_intensity", lower=0.5, upper=1, lower_inclusive=True, upper_inclusive=True),
        "washout-a": _common_coordinate("exact", unit="day", value=7),
        "assignment-p-a": _common_coordinate("exact", value=0.5),
        "assignment-p-b": _common_coordinate("exact", value=0.5),
        "sequential-positivity": _common_coordinate("exact", value=1),
        "carryover-control": _common_coordinate("exact", value=0.9),
        "missingness": _common_coordinate("distribution", distribution={"family": "beta", "alpha": 1, "beta": 19}, support={"lower": 0, "upper": 1}, sampling_seed=20260712),
        "structurally-absent": _common_coordinate("absent", structural_reason="no fourth-stage assignment in protocol", score_semantics="structural_zero"),
    }
    return {
        "schema_version": "anibench.uncertainty-model.v2",
        "contract_version": "2.0.0-alpha.1",
        "uncertainty_model_id": "uncertainty-test-v2",
        "parameter_space_sha256": SHA,
        "source_manifest_sha256": SHA,
        "created_at": "2026-07-12T00:00:00Z",
        "coordinates": coordinates,
        "source_receipts": [_receipt()],
        "assumptions": ["Test fixture only."],
        "public_score_emission_permitted": False,
    }


def event_fixture() -> dict:
    return {
        "schema_version": "anibench.event-manifest.v2",
        "contract_version": "2.0.0-alpha.1",
        "event_manifest_id": "event-test-v2",
        "study_id": "study-test-v2",
        "lane": "design",
        "parameter_space_id": "anibench-joint-biological-reconstruction-v2-draft",
        "parameter_space_sha256": SHA,
        "uncertainty_model_id": "uncertainty-test-v2",
        "uncertainty_model_sha256": SHA,
        "intervention_design_id": "intervention-test-v2",
        "intervention_design_sha256": SHA,
        "source_manifest_sha256": SHA,
        "created_at": "2026-07-12T00:00:00Z",
        "participant_sets": [
            {
                "participant_set_id": "all-retained",
                "parent_participant_set_id": None,
                "definition": "All retained participants in the protocol design.",
                "count": _ref("participant-count"),
                "sampling_frame": "retained",
                "strata": [],
                "source_receipt_ids": ["source-01"],
            }
        ],
        "time_bases": [
            {
                "time_basis_id": "randomization-time",
                "origin": "randomization",
                "calendar_unit": "day",
                "schedule_semantics": "windowed_offsets",
                "offset_coordinate_ids": ["observation-span"],
                "source_receipt_ids": ["source-01"],
            }
        ],
        "measurement_modules": [
            {
                "measurement_module_id": "module-a",
                "modality_registry_id": "proteome",
                "information_role": "biological_anchor",
                "feature_ancestry_id": "ancestry-proteome-panel",
                "specimen_or_signal": "plasma",
                "tissues_or_compartments": ["circulation"],
                "cell_resolution": "bulk",
                "platform_id": None,
                "target_count": _ref("target-count-a"),
                "technical_quality": _ref("quality"),
                "completeness": _ref("completeness"),
                "standardization": _ref("standardization"),
                "measurement_error_scale": _ref("measurement-error"),
                "covariance_group_id": "covariance-ab",
                "batch_group_id": None,
                "event_type_ids": ["deep-followup"],
                "source_receipt_ids": ["source-01"],
            },
            {
                "measurement_module_id": "module-b",
                "modality_registry_id": "metabolome",
                "information_role": "biological_anchor",
                "feature_ancestry_id": "ancestry-metabolome-panel",
                "specimen_or_signal": "plasma",
                "tissues_or_compartments": ["circulation"],
                "cell_resolution": "bulk",
                "platform_id": None,
                "target_count": _ref("target-count-b"),
                "technical_quality": _ref("quality"),
                "completeness": _ref("completeness"),
                "standardization": _ref("standardization"),
                "measurement_error_scale": _ref("measurement-error"),
                "covariance_group_id": "covariance-ab",
                "batch_group_id": None,
                "event_type_ids": ["deep-followup"],
                "source_receipt_ids": ["source-01"],
            },
        ],
        "event_types": [
            {
                "event_type_id": "deep-followup",
                "event_role": "followup",
                "participant_set_id": "all-retained",
                "time_basis_id": "randomization-time",
                "events_per_participant": _ref("event-count"),
                "observation_span": _ref("observation-span"),
                "measurement_module_ids": ["module-a", "module-b"],
                "assignment_stage_id": "stage-micro",
                "identity_linkage": _ref("identity-linkage"),
                "time_linkage": _ref("time-linkage"),
                "source_receipt_ids": ["source-01"],
            }
        ],
        "joint_event_hyperedges": [
            {
                "hyperedge_id": "joint-ab",
                "participant_set_ids": ["all-retained"],
                "event_type_ids": ["deep-followup"],
                "measurement_module_ids": ["module-a", "module-b"],
                "joint_participant_count": _ref("participant-count"),
                "joint_event_count": _ref("joint-event-count"),
                "identity_linkage": _ref("identity-linkage"),
                "temporal_compatibility": _ref("time-linkage"),
                "specimen_lineage_linkage": _ref("specimen-lineage-linkage"),
                "compatible_time_window": _ref("compatible-window"),
                "intersection_semantics": "protocol_planned",
                "ancestry_group_id": "joint-lineage-ab",
                "source_receipt_ids": ["source-01"],
            }
        ],
        "covariance_groups": [
            {
                "covariance_group_id": "covariance-ab",
                "member_measurement_module_ids": ["module-a", "module-b"],
                "covariance_semantics": "protocol_prior",
                "covariance_asset_sha256": SHA,
                "source_receipt_ids": ["source-01"],
            }
        ],
        "source_receipts": [_receipt()],
        "semantic_constraints": ["All quantitative fields resolve through uncertainty-test-v2."],
        "public_score_emission_permitted": False,
    }


def intervention_fixture() -> dict:
    component_ids = ["component-a", "component-b", "component-c", "component-d"]
    components = [
        {
            "operator_component_id": component_id,
            "family_id": f"family-{component_id[-1]}",
            "mechanism_or_target_ids": [],
            "dose_or_intensity": _ref("dose-a"),
            "route": None,
            "schedule_description": "Protocol-defined decision-stage exposure.",
            "washout_duration": _ref("washout-a"),
            "exposure_ascertainment": "device_logged",
            "adherence_ascertainment": "device_logged",
            "source_receipt_ids": ["source-01"],
        }
        for component_id in component_ids
    ]
    return {
        "schema_version": "anibench.intervention-design.v2",
        "contract_version": "2.0.0-alpha.1",
        "intervention_design_id": "intervention-test-v2",
        "study_id": "study-test-v2",
        "event_manifest_id": "event-test-v2",
        "event_manifest_sha256": SHA,
        "uncertainty_model_id": "uncertainty-test-v2",
        "uncertainty_model_sha256": SHA,
        "source_protocol_sha256": SHA,
        "created_at": "2026-07-12T00:00:00Z",
        "operator_components": components,
        "policies": [
            {
                "policy_id": "policy-adaptive",
                "label": "Adaptive whole policy",
                "comparator_role": "none",
                "operator_component_ids": component_ids,
                "adaptive": True,
                "policy_rule_asset_sha256": SHA,
                "source_receipt_ids": ["source-01"],
            },
            {
                "policy_id": "policy-control",
                "label": "Active comparator policy",
                "comparator_role": "active",
                "operator_component_ids": [],
                "adaptive": False,
                "policy_rule_asset_sha256": SHA,
                "source_receipt_ids": ["source-01"],
            },
        ],
        "assignment_stages": [
            {
                "assignment_stage_id": "stage-micro",
                "assignment_unit": "participant_time",
                "decision_event_type_id": "deep-followup",
                "eligibility_participant_set_id": "all-retained",
                "eligibility_rule_asset_sha256": SHA,
                "alternative_ids": component_ids,
                "assignment_mechanism": "micro_randomized",
                "assignment_probability_coordinate_ids": ["assignment-p-a", "assignment-p-b"],
                "sequential_positivity": _ref("sequential-positivity"),
                "repeated_within_person": True,
                "carryover_control": _ref("carryover-control"),
                "censoring_rule_asset_sha256": SHA,
                "source_receipt_ids": ["source-01"],
            }
        ],
        "estimands": [
            {
                "estimand_id": "estimand-policy",
                "estimand_family": "whole_policy_effect",
                "population_participant_set_id": "all-retained",
                "treatment_condition_ids": ["policy-adaptive", "policy-control"],
                "outcome_support_id": "outcome-deep",
                "summary_measure": "Difference in registered state movement.",
                "intercurrent_event_strategy": "Treatment policy strategy.",
                "multiplicity_family_id": None,
                "source_receipt_ids": ["source-01"],
            },
            {
                "estimand_id": "estimand-component",
                "estimand_family": "component_effect",
                "population_participant_set_id": "all-retained",
                "treatment_condition_ids": component_ids,
                "outcome_support_id": "outcome-deep",
                "summary_measure": "Component contrast in registered state movement.",
                "intercurrent_event_strategy": "While-on-treatment strategy.",
                "multiplicity_family_id": "multiplicity-components",
                "source_receipt_ids": ["source-01"],
            },
            {
                "estimand_id": "estimand-sequential",
                "estimand_family": "sequential_policy_value",
                "population_participant_set_id": "all-retained",
                "treatment_condition_ids": component_ids,
                "outcome_support_id": "outcome-deep",
                "summary_measure": "Sequential policy value contrast.",
                "intercurrent_event_strategy": "Dynamic treatment strategy.",
                "multiplicity_family_id": "multiplicity-sequential",
                "source_receipt_ids": ["source-01"],
            },
        ],
        "outcome_support": [
            {
                "outcome_support_id": "outcome-deep",
                "event_type_ids": ["deep-followup"],
                "measurement_module_ids": ["module-a", "module-b"],
                "participant_set_id": "all-retained",
                "missingness_coordinate_id": "missingness",
                "source_receipt_ids": ["source-01"],
            }
        ],
        "contrast_matrices": {
            "policy": [
                {
                    "matrix_role": "whole_policy",
                    "contrast_matrix_id": "matrix-policy",
                    "estimand_ids": ["estimand-policy"],
                    "policy_ids": ["policy-adaptive", "policy-control"],
                    "row_ids": ["adaptive-v-control"],
                    "column_ids": ["policy-adaptive", "policy-control"],
                    "values": [[1, -1]],
                    "coefficient_normalization": "sum_to_zero",
                    "source_receipt_ids": ["source-01"],
                }
            ],
            "component": [
                {
                    "matrix_role": "component",
                    "contrast_matrix_id": "matrix-component",
                    "estimand_ids": ["estimand-component"],
                    "operator_component_ids": component_ids,
                    "assignment_stage_ids": ["stage-micro"],
                    "row_ids": ["a-v-d", "b-v-d", "c-v-d"],
                    "column_ids": component_ids,
                    "values": [[1, 0, 0, -1], [0, 1, 0, -1], [0, 0, 1, -1]],
                    "coefficient_normalization": "sum_to_zero",
                    "source_receipt_ids": ["source-01"],
                }
            ],
            "sequential": [
                {
                    "matrix_role": "sequential",
                    "contrast_matrix_id": "matrix-sequential",
                    "estimand_ids": ["estimand-sequential"],
                    "assignment_stage_ids": ["stage-micro"],
                    "path_feature_ids": ["path-a", "path-b", "path-c", "path-d"],
                    "row_ids": ["path-a-v-d", "path-b-v-d", "path-c-v-d"],
                    "column_ids": ["path-a", "path-b", "path-c", "path-d"],
                    "values": [[1, 0, 0, -1], [0, 1, 0, -1], [0, 0, 1, -1]],
                    "coefficient_normalization": "sum_to_zero",
                    "source_receipt_ids": ["source-01"],
                }
            ],
        },
        "contrast_rank_source": "explicit_matrix_not_arm_count",
        "source_receipts": [_receipt()],
        "semantic_constraints": ["Matrix dimensions and references are checked before information construction."],
        "public_score_emission_permitted": False,
    }


@pytest.mark.parametrize("schema", SCHEMAS.values())
def test_v2_schema_is_valid_draft_202012(schema: dict) -> None:
    Draft202012Validator.check_schema(schema)


def test_uncertainty_contract_accepts_all_five_states() -> None:
    fixture = uncertainty_fixture()
    _validator("uncertainty.schema.json").validate(fixture)
    assert {row["state"] for row in fixture["coordinates"].values()} == {
        "exact",
        "interval",
        "distribution",
        "absent",
        "unknown",
    }


def test_uncertainty_unknown_cannot_smuggle_point_imputation() -> None:
    fixture = uncertainty_fixture()
    fixture["coordinates"]["target-count-b"]["nominal"] = 1000
    with pytest.raises(ValidationError):
        _validator("uncertainty.schema.json").validate(fixture)


def test_structural_absence_is_not_encoded_as_unknown_or_exact_zero() -> None:
    fixture = uncertainty_fixture()
    absent = fixture["coordinates"]["structurally-absent"]
    assert absent["state"] == "absent"
    assert absent["score_semantics"] == "structural_zero"
    assert "value" not in absent
    _validator("uncertainty.schema.json").validate(fixture)


def test_distribution_family_has_exact_parameter_contract() -> None:
    fixture = uncertainty_fixture()
    fixture["coordinates"]["quality"]["distribution"]["mean"] = 0.9
    with pytest.raises(ValidationError):
        _validator("uncertainty.schema.json").validate(fixture)


def test_event_manifest_requires_participant_event_hyperedges_for_jointness() -> None:
    fixture = event_fixture()
    _validator("event-manifest.schema.json").validate(fixture)
    edge = fixture["joint_event_hyperedges"][0]
    assert edge["measurement_module_ids"] == ["module-a", "module-b"]
    assert edge["intersection_semantics"] == "protocol_planned"


def test_event_hyperedge_cannot_claim_jointness_with_one_module() -> None:
    fixture = event_fixture()
    fixture["joint_event_hyperedges"][0]["measurement_module_ids"] = ["module-a"]
    with pytest.raises(ValidationError):
        _validator("event-manifest.schema.json").validate(fixture)


def test_event_manifest_rejects_row_level_participant_identity() -> None:
    fixture = event_fixture()
    fixture["participant_sets"][0]["participant_id"] = "person-001"
    with pytest.raises(ValidationError):
        _validator("event-manifest.schema.json").validate(fixture)


def test_intervention_contract_accepts_component_and_sequential_rank_above_arms_minus_one() -> None:
    fixture = intervention_fixture()
    _validator("intervention-design.schema.json").validate(fixture)
    assert len(fixture["policies"]) == 2
    component_values = np.asarray(fixture["contrast_matrices"]["component"][0]["values"])
    sequential_values = np.asarray(fixture["contrast_matrices"]["sequential"][0]["values"])
    assert np.linalg.matrix_rank(component_values) == 3 > len(fixture["policies"]) - 1
    assert np.linalg.matrix_rank(sequential_values) == 3 > len(fixture["policies"]) - 1
    assert fixture["contrast_rank_source"] == "explicit_matrix_not_arm_count"


def test_intervention_contract_requires_all_three_contrast_families() -> None:
    fixture = intervention_fixture()
    del fixture["contrast_matrices"]["sequential"]
    with pytest.raises(ValidationError):
        _validator("intervention-design.schema.json").validate(fixture)


def test_intervention_matrix_rejects_undeclared_fields_and_implicit_rank() -> None:
    fixture = intervention_fixture()
    fixture["contrast_matrices"]["component"][0]["arm_count_rank"] = 1
    with pytest.raises(ValidationError):
        _validator("intervention-design.schema.json").validate(fixture)


def test_parameter_space_is_structural_and_contains_no_reference_numbers() -> None:
    parameter_space = _load_json(ROOT / "spec" / "v2" / "parameter-space.json")
    assert parameter_space["status"] == "structural_contract_no_reference_numbers"
    assert parameter_space["reference_level_contract"]["reference_numbers_present"] is False
    assert parameter_space["prior_metric_contract"]["status"] == "required_not_yet_frozen"
    assert parameter_space["public_score_emission_permitted"] is False
    assert [row["block_id"] for row in parameter_space["parameter_blocks"]] == [
        "state_observation",
        "natural_dynamics",
        "perturbation_response",
        "person_context_heterogeneity",
        "functional_lived_state",
        "population_transport",
    ]
    assert parameter_space["current_eval_family_authority"]["family_ids"] == [
        "intensive",
        "extensive",
        "longitudinal",
        "causal",
        "personalized_sequential",
        "transport",
    ]
    assert "benchmark_families" not in parameter_space


def test_local_reference_registry_has_no_promotable_level_1_authority() -> None:
    registry = _load_json(ROOT / "spec" / "v2" / "reference-registry.json")
    _validator("reference-registry.schema.json").validate(registry)
    assert registry["status"] == "no_promotable_level_1_reference"
    assert registry["promotable_level_1_reference"] is None
    assert registry["public_completion_claim_allowed"] is False
    fixture_row = registry["illustrative_mechanics_fixtures"][0]
    fixture_path = ROOT / fixture_row["fixture_path"]
    fixture = _load_json(fixture_path)
    canonical = json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode()
    assert fixture_row["fixture_raw_sha256"] == (
        "sha256:" + hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    )
    assert fixture_row["fixture_payload_sha256"] == (
        "sha256:" + hashlib.sha256(canonical).hexdigest()
    )
    assert fixture_row["promotion_allowed"] is False
    assert fixture_row["public_completion_claim_allowed"] is False


def test_v2_contracts_bind_version_and_hash_fields_and_emit_no_score() -> None:
    uncertainty = uncertainty_fixture()
    event = event_fixture()
    intervention = intervention_fixture()
    for payload in (uncertainty, event, intervention):
        assert payload["contract_version"].startswith("2.")
        assert payload["public_score_emission_permitted"] is False
        assert "score" not in payload
    for payload, fields in (
        (uncertainty, ("parameter_space_sha256", "source_manifest_sha256")),
        (event, ("parameter_space_sha256", "uncertainty_model_sha256", "source_manifest_sha256")),
        (intervention, ("event_manifest_sha256", "uncertainty_model_sha256", "source_protocol_sha256")),
    ):
        assert all(len(payload[field]) == 64 for field in fields)
