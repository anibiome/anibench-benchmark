"""Role-aware Level-1 v3 authority and deterministic migration receipt.

This module deliberately does not calculate a global enrollment target.  It
first freezes which of the 64 mesoscopic coordinates may be direct event
outcomes and which are relational estimands.  Family-specific operating
characteristics and source-bound joint context support must exist before an
enrollment calculation can be authorized.
"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any, Mapping, Sequence


class Level1V3AuthorityError(ValueError):
    """Raised when a proposed v3 authority violates a frozen invariant."""


V2_COORDINATE_REGISTRY_PATH = "spec/v2/level1/biological-coordinate-registry.json"
V2_TARGET_PATH = "spec/v2/level1/normative-target-requirements.v2.json"
V2_COORDINATE_REGISTRY_RAW_SHA256 = (
    "ccb477e1fd9dec1f9cd18152f622f31a511d52cc7418c435415ca67d25fe216b"
)
V2_TARGET_RAW_SHA256 = (
    "79a6c624abd51eff0a80a53fd0b150fa425e47d72dea8c1c06abd73b274f83f8"
)
V2_COORDINATE_IDENTITY_SHA256 = (
    "9368e8e34abf9cee80c25b86c7fa5de0d486864d868d3ae3b7863bbf35d9ea04"
)
V2_TARGET_ID = "anibench-human-trial-level1-abstract-target-v2"
V3_TARGET_ID = "anibench-human-trial-level1-role-aware-target-v3"
INSTALLED_V3_AUTHORITY_PARTS = (
    "spec",
    "v3",
    "level1",
    "role-aware-target-requirements.v3.json",
)
INSTALLED_V3_IMPACT_PARTS = (
    "spec",
    "v3",
    "level1",
    "migrations",
    "v2-to-v3-substantive-impact-receipt.json",
)

FAMILY_IDS = (
    "intensive",
    "extensive",
    "longitudinal",
    "causal",
    "personalized_sequential",
    "transport",
)

DIRECT_MUTABLE_OUTCOME_IDS = (
    *(f"S{index:02d}" for index in range(2, 9)),
    *(f"S{index:02d}" for index in range(10, 17)),
    *(f"F{index:02d}" for index in range(1, 9)),
)
BASELINE_MODIFIER_IDS = ("S01",)
EXPOSURE_CONTEXT_IDS = ("S09",)
LONGITUDINAL_ESTIMAND_IDS = tuple(f"D{index:02d}" for index in range(1, 13))
CAUSAL_RESPONSE_ESTIMAND_IDS = tuple(f"P{index:02d}" for index in range(1, 13))
HETEROGENEITY_OC_IDS = tuple(f"H{index:02d}" for index in range(1, 9))
TRANSPORT_ESTIMAND_IDS = tuple(f"T{index:02d}" for index in range(1, 9))

ROLE_COORDINATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("direct_mutable_outcome_basis", DIRECT_MUTABLE_OUTCOME_IDS),
    ("baseline_modifier", BASELINE_MODIFIER_IDS),
    ("exposure_context", EXPOSURE_CONTEXT_IDS),
    ("longitudinal_state_space_estimand", LONGITUDINAL_ESTIMAND_IDS),
    ("causal_response_estimand", CAUSAL_RESPONSE_ESTIMAND_IDS),
    ("heterogeneity_operating_characteristic", HETEROGENEITY_OC_IDS),
    ("transport_estimand", TRANSPORT_ESTIMAND_IDS),
)

RELATIONAL_ESTIMAND_ROLES = (
    "longitudinal_state_space_estimand",
    "causal_response_estimand",
    "heterogeneity_operating_characteristic",
    "transport_estimand",
)

ROLE_SEMANTICS = {
    "direct_mutable_outcome_basis": (
        "Latent mutable state or function direction permitted as an event-level outcome "
        "after a source-bound observation operator, scale, reliability model, and event "
        "linkage are verified. Coordinate presence alone is not measurement evidence."
    ),
    "baseline_modifier": (
        "Stable pre-assignment modifier direction. It may enter registered moderation "
        "models but is not a mutable event outcome or an effect estimand."
    ),
    "exposure_context": (
        "Time-indexed exposure or context direction. It may define context or adjustment "
        "variables but is not a transport estimand and is not a mutable outcome target."
    ),
    "longitudinal_state_space_estimand": (
        "A relational target derived from repeated direct outcomes through an explicit "
        "state-transition, observation, process-noise, and time-index model."
    ),
    "causal_response_estimand": (
        "A counterfactual or randomized response relation over direct outcomes and "
        "registered intervention operators; never a direct assay or event outcome."
    ),
    "heterogeneity_operating_characteristic": (
        "An operating-characteristic target for variation, calibration, or decision-rule "
        "performance across persons or contexts; never a raw moderator coordinate."
    ),
    "transport_estimand": (
        "A source-to-target population relation over direct outcomes under a registered "
        "joint context support authority; never a raw context covariate or stratum label."
    ),
}

GATE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "gate_id": "direct_outcome_observation_authority",
        "blocker_code": "MISSING_SOURCE_BOUND_OBSERVATION_OPERATORS",
        "required_source_objects": [
            "coordinate_to_observed_variable_operator_registry",
            "event_linkage_receipt",
            "scale_and_reliability_authority",
            "missingness_and_detection_limit_model",
        ],
    },
    {
        "gate_id": "intensive_operating_characteristics",
        "blocker_code": "MISSING_INTENSIVE_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "within_event_information_definition",
            "observer_covariance_or_identified_bound",
            "calibration_and_repeatability_receipt",
        ],
    },
    {
        "gate_id": "extensive_operating_characteristics",
        "blocker_code": "MISSING_EXTENSIVE_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "role_eligible_coordinate_coverage_rule",
            "cross_coordinate_redundancy_authority",
            "source_bound_identifiability_receipt",
        ],
    },
    {
        "gate_id": "longitudinal_state_space_operating_characteristics",
        "blocker_code": "MISSING_LONGITUDINAL_STATE_SPACE_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "state_transition_model",
            "observation_model",
            "process_and_measurement_noise_authority",
            "time_grid_and_sampling_process",
            "held_time_or_held_person_validation_plan",
        ],
    },
    {
        "gate_id": "causal_response_operating_characteristics",
        "blocker_code": "MISSING_CAUSAL_RESPONSE_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "counterfactual_estimand_registry",
            "assignment_or_identification_authority",
            "intervention_operator_registry",
            "multiplicity_and_error_control_plan",
            "attrition_interference_and_adherence_models",
        ],
    },
    {
        "gate_id": "heterogeneity_operating_characteristics",
        "blocker_code": "MISSING_HETEROGENEITY_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "preassignment_modifier_registry",
            "effect_variation_estimand_registry",
            "false_subgroup_and_calibration_operating_characteristics",
            "held_person_validation_plan",
        ],
    },
    {
        "gate_id": "personalized_sequential_operating_characteristics",
        "blocker_code": "MISSING_PERSONALIZED_SEQUENTIAL_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "decision_point_and_availability_process",
            "sequential_assignment_authority",
            "policy_value_regret_and_safety_estimands",
            "off_policy_or_randomized_evaluation_plan",
        ],
    },
    {
        "gate_id": "source_bound_joint_context_support",
        "blocker_code": "MISSING_SOURCE_BOUND_JOINT_CONTEXT_SUPPORT",
        "required_source_objects": [
            "raw_context_covariate_registry",
            "source_and_target_population_definitions",
            "joint_context_support_table_or_identified_bound",
            "sampling_and_selection_mechanism",
            "positivity_overlap_and_weight_diagnostics",
        ],
    },
    {
        "gate_id": "transport_operating_characteristics",
        "blocker_code": "MISSING_TRANSPORT_OPERATING_CHARACTERISTICS",
        "required_source_objects": [
            "transport_estimand_registry",
            "source_to_target_identification_assumptions",
            "shift_calibration_and_failure_operating_characteristics",
            "held_site_or_held_context_validation_plan",
        ],
    },
    {
        "gate_id": "cross_family_reuse_and_covariance_authority",
        "blocker_code": "MISSING_CROSS_FAMILY_REUSE_AND_COVARIANCE_AUTHORITY",
        "required_source_objects": [
            "participant_reuse_graph",
            "shared_event_and_outcome_dependency_model",
            "cross_family_covariance_or_conservative_bound",
            "family_specific_rounding_and_allocation_rule",
        ],
    },
    {
        "gate_id": "independent_role_and_operating_characteristic_attestation",
        "blocker_code": "MISSING_INDEPENDENT_ATTESTATION",
        "required_source_objects": [
            "independent_role_ontology_review",
            "independent_operating_characteristic_review",
            "hostile_gaming_and_sensitivity_receipt",
        ],
    },
)

FAMILY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "family_id": "intensive",
        "scientific_question": (
            "How much source-bound information about the direct mutable outcome basis is "
            "resolved within a participant-event?"
        ),
        "target_coordinate_roles": ["direct_mutable_outcome_basis"],
        "support_coordinate_roles": ["baseline_modifier", "exposure_context"],
        "required_gate_ids": [
            "direct_outcome_observation_authority",
            "intensive_operating_characteristics",
        ],
        "forbidden_substitutions": [
            "assay_or_modality_menu_size",
            "feature_count_without_observation_operator_and_covariance",
            "relational_estimand_count_as_event_information",
        ],
    },
    {
        "family_id": "extensive",
        "scientific_question": (
            "How broadly are role-eligible direct outcome and support directions identified "
            "without counting redundant observers as new biology?"
        ),
        "target_coordinate_roles": [
            "direct_mutable_outcome_basis",
            "baseline_modifier",
            "exposure_context",
        ],
        "support_coordinate_roles": [],
        "required_gate_ids": [
            "direct_outcome_observation_authority",
            "extensive_operating_characteristics",
        ],
        "forbidden_substitutions": [
            "raw_modality_count",
            "raw_feature_count",
            "D_P_H_or_T_coordinates_as_directly_measured_dimensions",
        ],
    },
    {
        "family_id": "longitudinal",
        "scientific_question": (
            "Which natural state-space dynamics are identifiable from repeated direct "
            "outcomes under the registered time and noise model?"
        ),
        "target_coordinate_roles": ["longitudinal_state_space_estimand"],
        "support_coordinate_roles": [
            "direct_mutable_outcome_basis",
            "baseline_modifier",
            "exposure_context",
        ],
        "required_gate_ids": [
            "direct_outcome_observation_authority",
            "longitudinal_state_space_operating_characteristics",
        ],
        "forbidden_substitutions": [
            "visit_count_without_time_process",
            "D_coordinate_as_event_outcome",
            "repeated_measurement_count_without_dependence_model",
        ],
    },
    {
        "family_id": "causal",
        "scientific_question": (
            "Which intervention-response relations are identified over direct outcomes "
            "under explicit assignment and counterfactual authority?"
        ),
        "target_coordinate_roles": ["causal_response_estimand"],
        "support_coordinate_roles": [
            "direct_mutable_outcome_basis",
            "baseline_modifier",
            "exposure_context",
        ],
        "required_gate_ids": [
            "direct_outcome_observation_authority",
            "causal_response_operating_characteristics",
        ],
        "forbidden_substitutions": [
            "P_coordinate_as_event_outcome",
            "intervention_menu_size",
            "association_without_identification_authority",
        ],
    },
    {
        "family_id": "personalized_sequential",
        "scientific_question": (
            "How well can response heterogeneity and sequential policies be learned, "
            "calibrated, and validated across held persons?"
        ),
        "target_coordinate_roles": ["heterogeneity_operating_characteristic"],
        "support_coordinate_roles": [
            "causal_response_estimand",
            "baseline_modifier",
            "exposure_context",
            "direct_mutable_outcome_basis",
        ],
        "required_gate_ids": [
            "direct_outcome_observation_authority",
            "causal_response_operating_characteristics",
            "heterogeneity_operating_characteristics",
            "personalized_sequential_operating_characteristics",
        ],
        "forbidden_substitutions": [
            "H_coordinate_as_raw_moderator",
            "subgroup_count",
            "in_sample_policy_value_without_held_person_validation",
        ],
    },
    {
        "family_id": "transport",
        "scientific_question": (
            "Which source-to-target relations are identified under source-bound joint "
            "context support and explicit population-shift authority?"
        ),
        "target_coordinate_roles": ["transport_estimand"],
        "support_coordinate_roles": [
            "direct_mutable_outcome_basis",
            "baseline_modifier",
            "exposure_context",
            "causal_response_estimand",
        ],
        "required_gate_ids": [
            "direct_outcome_observation_authority",
            "causal_response_operating_characteristics",
            "source_bound_joint_context_support",
            "transport_operating_characteristics",
        ],
        "forbidden_substitutions": [
            "T_coordinate_as_context_label_or_stratum",
            "site_count_without_joint_support",
            "marginal_context_coverage_as_joint_overlap",
        ],
    },
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_dumps(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _pretty_dumps(value: Any) -> str:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _load_source(path: Path, expected_raw_sha256: str) -> Mapping[str, Any]:
    payload = path.read_bytes()
    observed = _sha256_bytes(payload)
    if observed != expected_raw_sha256:
        raise Level1V3AuthorityError(
            f"source authority hash mismatch for {path}: expected "
            f"{expected_raw_sha256}, observed {observed}"
        )
    parsed = json.loads(payload)
    if not isinstance(parsed, Mapping):
        raise Level1V3AuthorityError(f"source authority must be an object: {path}")
    return parsed


def _flatten_coordinates(registry: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for block in registry.get("blocks", []):
        block_id = block.get("block_id")
        symbol = block.get("symbol")
        if not isinstance(block_id, str) or not isinstance(symbol, str):
            raise Level1V3AuthorityError("v2 coordinate block identity is malformed")
        for coordinate in block.get("coordinates", []):
            if not isinstance(coordinate, Sequence) or len(coordinate) != 2:
                raise Level1V3AuthorityError("v2 coordinate row is malformed")
            coordinate_id, name = coordinate
            if not isinstance(coordinate_id, str) or not isinstance(name, str):
                raise Level1V3AuthorityError("v2 coordinate identity is malformed")
            rows.append(
                {
                    "block_id": block_id,
                    "symbol": symbol,
                    "coordinate_id": coordinate_id,
                    "name": name,
                }
            )
    return rows


def _coordinate_role_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for role_id, coordinate_ids in ROLE_COORDINATES:
        for coordinate_id in coordinate_ids:
            if coordinate_id in lookup:
                raise Level1V3AuthorityError(
                    f"coordinate {coordinate_id} appears in multiple estimation roles"
                )
            lookup[coordinate_id] = role_id
    return lookup


def _unknown_gate(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": spec["gate_id"],
        "fact_type": "unknown",
        "state": "unresolved",
        "value": None,
        "blocker_code": spec["blocker_code"],
        "promotion_blocking": True,
        "required_source_objects": list(spec["required_source_objects"]),
    }


def _unknown_family_entry(family: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "family_id": family["family_id"],
        "fact_type": "unknown",
        "state": "unresolved",
        "value": None,
        "unit": "family_specific_operating_characteristic_target_attainment",
        "blocker_code": "BLOCKED_BY_FAMILY_REQUIRED_GATES",
        "blocked_by_gate_ids": list(family["required_gate_ids"]),
    }


def build_role_aware_authority(
    coordinate_registry: Mapping[str, Any],
    v2_target: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct the role-aware v3 candidate from hash-pinned v2 sources."""

    if v2_target.get("target_id") != V2_TARGET_ID:
        raise Level1V3AuthorityError("unexpected v2 target identity")

    flat = _flatten_coordinates(coordinate_registry)
    coordinate_ids = [row["coordinate_id"] for row in flat]
    if len(flat) != 64 or len(set(coordinate_ids)) != 64:
        raise Level1V3AuthorityError("v2 scientific map must contain 64 unique coordinates")

    role_lookup = _coordinate_role_lookup()
    if set(role_lookup) != set(coordinate_ids):
        missing = sorted(set(coordinate_ids) - set(role_lookup))
        extra = sorted(set(role_lookup) - set(coordinate_ids))
        raise Level1V3AuthorityError(
            f"estimation roles must partition the coordinate map; missing={missing}, extra={extra}"
        )

    blocks: list[dict[str, Any]] = []
    cursor = 0
    for source_block in coordinate_registry["blocks"]:
        coordinates: list[dict[str, str]] = []
        for coordinate_id, name in source_block["coordinates"]:
            coordinates.append(
                {
                    "coordinate_id": coordinate_id,
                    "name": name,
                    "estimation_role": role_lookup[coordinate_id],
                }
            )
            cursor += 1
        blocks.append(
            {
                "block_id": source_block["block_id"],
                "symbol": source_block["symbol"],
                "coordinates": coordinates,
            }
        )
    if cursor != 64:
        raise Level1V3AuthorityError("coordinate map traversal did not preserve all coordinates")

    roles = [
        {
            "role_id": role_id,
            "coordinate_ids": list(coordinate_ids_for_role),
            "semantics": ROLE_SEMANTICS[role_id],
            "is_direct_event_outcome_role": role_id == "direct_mutable_outcome_basis",
            "is_relational_estimand_role": role_id in RELATIONAL_ESTIMAND_ROLES,
        }
        for role_id, coordinate_ids_for_role in ROLE_COORDINATES
    ]

    gates = [_unknown_gate(spec) for spec in GATE_SPECS]
    families = [
        {
            **family,
            "operating_characteristic_target": {
                "fact_type": "unknown",
                "state": "unresolved",
                "value": None,
                "blocker_code": (
                    f"MISSING_{family['family_id'].upper()}_FAMILY_OPERATING_CHARACTERISTIC_TARGET"
                ),
            },
            "family_enrollment_requirement": {
                "fact_type": "unknown",
                "state": "unresolved",
                "value": None,
                "unit": "participants_or_participant_events_as_defined_by_future_authority",
                "blocker_code": (
                    f"MISSING_{family['family_id'].upper()}_FAMILY_ENROLLMENT_DERIVATION"
                ),
            },
        }
        for family in FAMILY_SPECS
    ]

    authority = {
        "contract": "anibench.level1-role-aware-target-authority.v3",
        "target_id": V3_TARGET_ID,
        "status": (
            "candidate_role_authority_pending_source_bound_operating_"
            "characteristics_and_independent_attestation"
        ),
        "reference_role": (
            "role_aware_level1_authority_not_a_trial_not_an_enrollment_target_"
            "and_not_a_rank"
        ),
        "relation_to_v2": {
            "state": "substantive_successor_candidate_not_promoted",
            "v2_target_id": V2_TARGET_ID,
            "v2_coordinate_registry": {
                "path": V2_COORDINATE_REGISTRY_PATH,
                "raw_sha256": V2_COORDINATE_REGISTRY_RAW_SHA256,
            },
            "v2_target": {
                "path": V2_TARGET_PATH,
                "raw_sha256": V2_TARGET_RAW_SHA256,
            },
            "inheritance_rule": (
                "coordinate_ids_names_order_and_six_blocks_are_preserved; v2 outcome, "
                "moderator, enrollment, context, and normalization semantics are not inherited"
            ),
        },
        "scientific_map": {
            "map_contract": "anibench.level1-role-aware-coordinate-map.v3",
            "ordered_coordinate_count": 64,
            "ordered_block_count": 6,
            "ordered_coordinate_identity_sha256": _sha256_bytes(
                _canonical_dumps(
                    [
                        [
                            row["block_id"],
                            row["symbol"],
                            row["coordinate_id"],
                            row["name"],
                        ]
                        for row in flat
                    ]
                ).encode("utf-8")
            ),
            "blocks": blocks,
        },
        "estimation_role_authority": {
            "partition_rule": (
                "every_frozen_coordinate_has_exactly_one_estimation_role_and_roles_do_not_overlap"
            ),
            "roles": roles,
            "direct_event_outcome_coordinate_ids": list(DIRECT_MUTABLE_OUTCOME_IDS),
            "raw_modifier_coordinate_ids": list(BASELINE_MODIFIER_IDS),
            "exposure_context_coordinate_ids": list(EXPOSURE_CONTEXT_IDS),
            "relational_estimand_coordinate_ids": [
                coordinate_id
                for role_id, role_coordinate_ids in ROLE_COORDINATES
                if role_id in RELATIONAL_ESTIMAND_ROLES
                for coordinate_id in role_coordinate_ids
            ],
            "forbidden_role_coercions": [
                "D_P_H_or_T_coordinate_to_direct_event_outcome",
                "D_P_H_or_T_coordinate_to_raw_moderator",
                "D_P_H_or_T_coordinate_to_raw_context_stratum",
                "S01_to_mutable_outcome",
                "S09_to_transport_estimand",
                "assay_feature_or_modality_to_coordinate_without_observation_operator",
            ],
        },
        "raw_context_transport_boundary": {
            "raw_context_covariates": {
                "ontology_location": "source_specific_registry_outside_the_64_coordinate_map",
                "within_map_latent_context_coordinate_ids": list(EXPOSURE_CONTEXT_IDS),
                "semantics": (
                    "Observed site, geography, age, sex, ancestry, socioeconomic, baseline "
                    "health, comorbidity, medication, environment, and access variables are "
                    "source-bound covariates. They do not become T coordinates by naming."
                ),
            },
            "transport_estimands": {
                "coordinate_ids": list(TRANSPORT_ESTIMAND_IDS),
                "semantics": (
                    "T coordinates are source-to-target relational estimands over direct "
                    "outcomes and policies, conditional on an identified joint context support "
                    "authority. They are not rows, labels, axes, or strata in a raw table."
                ),
            },
            "joint_support_authority": {
                "fact_type": "unknown",
                "state": "unresolved",
                "value": None,
                "source_bound": False,
                "blocker_code": "MISSING_SOURCE_BOUND_JOINT_CONTEXT_SUPPORT",
                "matrix_or_bound_status": "not_provided_no_matrix_fabricated",
                "required_gate_id": "source_bound_joint_context_support",
            },
        },
        "family_operating_characteristic_authority": {
            "family_ids": list(FAMILY_IDS),
            "family_semantics": (
                "Each family has its own estimand, unit, operating characteristics, and "
                "enrollment derivation. No family substitutes for or compensates another."
            ),
            "families": families,
        },
        "enrollment_authority": {
            "global_enrollment": {
                "fact_type": "unknown",
                "state": "unresolved",
                "value": None,
                "unit": "participants",
                "blocker_code": (
                    "WITHHELD_PENDING_ALL_FAMILY_OPERATING_CHARACTERISTICS_AND_"
                    "SOURCE_BOUND_JOINT_CONTEXT_SUPPORT"
                ),
            },
            "release_condition": {
                "all_family_specific_operating_characteristic_targets_resolved": False,
                "all_family_specific_enrollment_derivations_resolved": False,
                "source_bound_joint_context_support_resolved": False,
                "cross_family_reuse_and_covariance_resolved": False,
                "aggregation_rule_resolved": False,
            },
            "forbidden_derivations": [
                "inherit_v2_global_enrollment",
                "sum_family_numbers_without_disjointness_or_covariance_authority",
                "max_family_number_as_implicit_complete_reuse",
                "derive_sample_size_from_coordinate_count_or_modality_count",
                "emit_number_when_any_family_operating_characteristic_is_unknown",
            ],
        },
        "typed_unresolved_gates": gates,
        "noncompensatory_family_vector": {
            "ordered_family_ids": list(FAMILY_IDS),
            "entries": [_unknown_family_entry(family) for family in FAMILY_SPECS],
            "aggregation": {
                "state": "forbidden",
                "value": None,
                "reason_code": "NO_OVERALL_SCALAR_OR_CROSS_FAMILY_COMPENSATION",
            },
            "rank": {
                "state": "forbidden",
                "value": None,
                "reason_code": "NO_STABLE_RANK_WITH_UNRESOLVED_FAMILY_AUTHORITY",
            },
        },
        "release_state": {
            "promotion_allowed": False,
            "public_rank_allowed": False,
            "global_enrollment_claim_allowed": False,
            "reason_code": "ROLE_AUTHORITY_FROZEN_OPERATING_CHARACTERISTICS_UNRESOLVED",
        },
    }
    validate_role_aware_authority(authority)
    return authority


def validate_role_aware_authority(authority: Mapping[str, Any]) -> dict[str, Any]:
    """Validate scientific and release invariants beyond JSON shape."""

    if authority.get("contract") != "anibench.level1-role-aware-target-authority.v3":
        raise Level1V3AuthorityError("unexpected v3 authority contract")
    if authority.get("target_id") != V3_TARGET_ID:
        raise Level1V3AuthorityError("unexpected v3 target identity")

    relation = authority["relation_to_v2"]
    if (
        relation["v2_target_id"] != V2_TARGET_ID
        or relation["v2_coordinate_registry"]["path"] != V2_COORDINATE_REGISTRY_PATH
        or relation["v2_coordinate_registry"]["raw_sha256"]
        != V2_COORDINATE_REGISTRY_RAW_SHA256
        or relation["v2_target"]["path"] != V2_TARGET_PATH
        or relation["v2_target"]["raw_sha256"] != V2_TARGET_RAW_SHA256
    ):
        raise Level1V3AuthorityError("v3 must remain bound to the frozen v2 source hashes")

    blocks = authority["scientific_map"]["blocks"]
    coordinates = [coordinate for block in blocks for coordinate in block["coordinates"]]
    coordinate_ids = [coordinate["coordinate_id"] for coordinate in coordinates]
    if len(blocks) != 6 or len(coordinates) != 64 or len(set(coordinate_ids)) != 64:
        raise Level1V3AuthorityError("v3 must preserve six blocks and 64 unique coordinates")
    observed_coordinate_identity_sha256 = _sha256_bytes(
        _canonical_dumps(
            [
                [
                    block["block_id"],
                    block["symbol"],
                    coordinate["coordinate_id"],
                    coordinate["name"],
                ]
                for block in blocks
                for coordinate in block["coordinates"]
            ]
        ).encode("utf-8")
    )
    if (
        observed_coordinate_identity_sha256 != V2_COORDINATE_IDENTITY_SHA256
        or authority["scientific_map"]["ordered_coordinate_identity_sha256"]
        != V2_COORDINATE_IDENTITY_SHA256
    ):
        raise Level1V3AuthorityError(
            "coordinate IDs, names, order, or six-block membership changed"
        )

    roles = authority["estimation_role_authority"]["roles"]
    role_membership: dict[str, str] = {}
    for role in roles:
        role_id = role["role_id"]
        for coordinate_id in role["coordinate_ids"]:
            if coordinate_id in role_membership:
                raise Level1V3AuthorityError(
                    f"coordinate {coordinate_id} appears in overlapping roles"
                )
            role_membership[coordinate_id] = role_id
    if set(role_membership) != set(coordinate_ids):
        raise Level1V3AuthorityError("estimation roles do not partition all 64 coordinates")
    for coordinate in coordinates:
        if role_membership[coordinate["coordinate_id"]] != coordinate["estimation_role"]:
            raise Level1V3AuthorityError("coordinate role annotation disagrees with role registry")

    expected_roles = {key: tuple(value) for key, value in ROLE_COORDINATES}
    observed_roles = {role["role_id"]: tuple(role["coordinate_ids"]) for role in roles}
    if observed_roles != expected_roles:
        raise Level1V3AuthorityError("v3 estimation role partition differs from frozen authority")
    for role in roles:
        role_id = role["role_id"]
        if role["is_direct_event_outcome_role"] is not (
            role_id == "direct_mutable_outcome_basis"
        ) or role["is_relational_estimand_role"] is not (
            role_id in RELATIONAL_ESTIMAND_ROLES
        ):
            raise Level1V3AuthorityError("estimation role type flags differ from frozen authority")

    relational_ids = {
        coordinate_id
        for role_id, ids in observed_roles.items()
        if role_id in RELATIONAL_ESTIMAND_ROLES
        for coordinate_id in ids
    }
    if relational_ids & set(DIRECT_MUTABLE_OUTCOME_IDS):
        raise Level1V3AuthorityError("relational estimands cannot be direct event outcomes")
    if relational_ids & set(BASELINE_MODIFIER_IDS):
        raise Level1V3AuthorityError("relational estimands cannot be raw modifiers")
    if relational_ids & set(EXPOSURE_CONTEXT_IDS):
        raise Level1V3AuthorityError("relational estimands cannot be raw context coordinates")

    boundary = authority["raw_context_transport_boundary"]
    if boundary["transport_estimands"]["coordinate_ids"] != list(TRANSPORT_ESTIMAND_IDS):
        raise Level1V3AuthorityError("transport estimand identity changed")
    joint_support = boundary["joint_support_authority"]
    if (
        joint_support["fact_type"] != "unknown"
        or joint_support["state"] != "unresolved"
        or joint_support["value"] is not None
        or joint_support["source_bound"] is not False
    ):
        raise Level1V3AuthorityError("joint context support must remain typed unresolved")

    families = authority["family_operating_characteristic_authority"]["families"]
    if [family["family_id"] for family in families] != list(FAMILY_IDS):
        raise Level1V3AuthorityError("six-family order or identity changed")
    for family, expected_family in zip(families, FAMILY_SPECS, strict=True):
        for key in (
            "family_id",
            "scientific_question",
            "target_coordinate_roles",
            "support_coordinate_roles",
            "required_gate_ids",
            "forbidden_substitutions",
        ):
            if family[key] != expected_family[key]:
                raise Level1V3AuthorityError(
                    f"family role or operating-characteristic contract changed: {key}"
                )
        operating_target = family["operating_characteristic_target"]
        enrollment = family["family_enrollment_requirement"]
        if operating_target["state"] != "unresolved" or operating_target["value"] is not None:
            raise Level1V3AuthorityError("family operating characteristics must be unresolved")
        if enrollment["state"] != "unresolved" or enrollment["value"] is not None:
            raise Level1V3AuthorityError("family enrollment must be unresolved")

    global_enrollment = authority["enrollment_authority"]["global_enrollment"]
    if (
        global_enrollment["fact_type"] != "unknown"
        or global_enrollment["state"] != "unresolved"
        or global_enrollment["value"] is not None
    ):
        raise Level1V3AuthorityError(
            "global enrollment is prohibited until all operating characteristics resolve"
        )
    if any(authority["enrollment_authority"]["release_condition"].values()):
        raise Level1V3AuthorityError("enrollment release conditions are not yet resolved")

    gates = authority["typed_unresolved_gates"]
    expected_gate_ids = [gate["gate_id"] for gate in GATE_SPECS]
    if [gate["gate_id"] for gate in gates] != expected_gate_ids:
        raise Level1V3AuthorityError("typed unresolved gate identity or order changed")
    if any(
        gate["fact_type"] != "unknown"
        or gate["state"] != "unresolved"
        or gate["value"] is not None
        or gate["promotion_blocking"] is not True
        for gate in gates
    ):
        raise Level1V3AuthorityError("all current v3 gates must remain typed unresolved")
    for gate, expected_gate in zip(gates, GATE_SPECS, strict=True):
        if (
            gate["blocker_code"] != expected_gate["blocker_code"]
            or gate["required_source_objects"] != expected_gate["required_source_objects"]
        ):
            raise Level1V3AuthorityError("typed gate source requirements changed")

    vector = authority["noncompensatory_family_vector"]
    if [row["family_id"] for row in vector["entries"]] != list(FAMILY_IDS):
        raise Level1V3AuthorityError("noncompensatory vector family order changed")
    if any(row["state"] != "unresolved" or row["value"] is not None for row in vector["entries"]):
        raise Level1V3AuthorityError("family vector must preserve unknown values")
    for row, family in zip(vector["entries"], FAMILY_SPECS, strict=True):
        if row["blocked_by_gate_ids"] != family["required_gate_ids"]:
            raise Level1V3AuthorityError("family vector gate binding changed")
    if vector["aggregation"] != {
        "state": "forbidden",
        "value": None,
        "reason_code": "NO_OVERALL_SCALAR_OR_CROSS_FAMILY_COMPENSATION",
    }:
        raise Level1V3AuthorityError("overall scalar aggregation must remain forbidden")
    if vector["rank"]["state"] != "forbidden" or vector["rank"]["value"] is not None:
        raise Level1V3AuthorityError("rank must remain forbidden")

    release_state = authority["release_state"]
    if any(
        release_state[key] is not False
        for key in (
            "promotion_allowed",
            "public_rank_allowed",
            "global_enrollment_claim_allowed",
        )
    ):
        raise Level1V3AuthorityError("v3 candidate cannot be promoted while gates are unresolved")

    return {
        "contract": "anibench.level1-role-aware-target-authority-validation.v3",
        "valid": True,
        "ordered_block_count": len(blocks),
        "ordered_coordinate_count": len(coordinates),
        "role_partition_count": len(roles),
        "direct_mutable_outcome_count": len(DIRECT_MUTABLE_OUTCOME_IDS),
        "relational_estimand_count": len(relational_ids),
        "family_count": len(families),
        "unresolved_gate_count": len(gates),
        "global_enrollment_state": "unresolved",
        "promotion_allowed": False,
    }


def build_v2_to_v3_impact_receipt(
    authority: Mapping[str, Any], authority_raw_sha256: str
) -> dict[str, Any]:
    """Build a machine-readable receipt for the substantive ontology break."""

    proof = validate_role_aware_authority(authority)
    return {
        "contract": "anibench.level1-v2-to-v3-substantive-impact-receipt.v1",
        "migration_class": "substantive_non_numeric_role_and_estimand_ontology_change",
        "source_authority": {
            "v2_coordinate_registry": {
                "path": V2_COORDINATE_REGISTRY_PATH,
                "raw_sha256": V2_COORDINATE_REGISTRY_RAW_SHA256,
            },
            "v2_target": {
                "path": V2_TARGET_PATH,
                "target_id": V2_TARGET_ID,
                "raw_sha256": V2_TARGET_RAW_SHA256,
            },
        },
        "candidate_authority": {
            "path": "spec/v3/level1/role-aware-target-requirements.v3.json",
            "target_id": V3_TARGET_ID,
            "raw_sha256": authority_raw_sha256,
            "promotion_allowed": False,
        },
        "preserved": {
            "ordered_block_count": 6,
            "ordered_coordinate_count": 64,
            "coordinate_ids_names_order_and_block_membership": True,
            "six_noncompensatory_family_ids": list(FAMILY_IDS),
        },
        "substantive_changes": [
            {
                "change_id": "direct_outcome_basis_narrowed",
                "v2_path": "/measurement_target/powered_outcome_direction_ids",
                "v2_semantics": "all_64_coordinates_treated_as_powered_outcome_directions",
                "v3_semantics": (
                    "only_S02_through_S08_S10_through_S16_and_F01_through_F08_are_"
                    "direct_mutable_event_outcome_basis_directions"
                ),
                "impact": "v2_power_and_enrollment_derivations_are_not_inherited",
            },
            {
                "change_id": "modifier_roles_narrowed",
                "v2_path": "/moderator_target/coordinate_ids",
                "v2_semantics": "mixed_S_D_P_H_F_T_coordinates_as_moderators",
                "v3_semantics": (
                    "S01_is_baseline_modifier_and_S09_is_exposure_context; D_P_H_T_are_"
                    "relational_estimands_not_raw_moderators"
                ),
                "impact": "v2_moderator_hypothesis_universe_is_not_inherited",
            },
            {
                "change_id": "longitudinal_role_corrected",
                "v2_path": "/measurement_target/powered_outcome_direction_ids/D01-D12",
                "v2_semantics": "D_coordinates_entered_direct_outcome_multiplicity",
                "v3_semantics": "D01-D12_are_longitudinal_state_space_estimands",
                "impact": "requires_state_space_operating_characteristic_authority",
            },
            {
                "change_id": "causal_role_corrected",
                "v2_path": "/measurement_target/powered_outcome_direction_ids/P01-P12",
                "v2_semantics": "P_coordinates_entered_direct_outcome_multiplicity",
                "v3_semantics": "P01-P12_are_counterfactual_or_randomized_response_estimands",
                "impact": "requires_family_specific_causal_operating_characteristics",
            },
            {
                "change_id": "heterogeneity_role_corrected",
                "v2_path": "/measurement_target/powered_outcome_direction_ids/H01-H08",
                "v2_semantics": "H_coordinates_entered_direct_outcome_multiplicity",
                "v3_semantics": "H01-H08_are_heterogeneity_operating_characteristic_targets",
                "impact": "requires_false_subgroup_calibration_and_held_person_validation",
            },
            {
                "change_id": "transport_context_separated",
                "v2_path": "/transport_target/context_coordinate_rule",
                "v2_semantics": "abstract_context_displacements_defined_on_T_axes",
                "v3_semantics": (
                    "raw_context_covariates_are_source_specific_and_outside_the_64_map; "
                    "T01-T08_are_transport_estimands_requiring_joint_support"
                ),
                "impact": "no_transport_or_enrollment_number_without_source_bound_joint_support",
            },
            {
                "change_id": "global_enrollment_withheld",
                "v2_path": "/population_trajectory_target/target_total_enrollment",
                "v2_semantics": "single_global_reference_enrollment_was_numeric",
                "v3_semantics": (
                    "global_enrollment_is_typed_unknown_until_every_family_operating_"
                    "characteristic_joint_support_and_reuse_covariance_authority_resolve"
                ),
                "impact": "v2_numeric_enrollment_is_archival_v2_only_and_not_a_v3_value",
            },
            {
                "change_id": "family_vector_explicitly_noncompensatory",
                "v2_path": "/normalization",
                "v2_semantics": "family_normalization_existed_with_numeric_target_components",
                "v3_semantics": (
                    "six_typed_family_entries_remain_unknown_and_no_scalar_or_rank_exists"
                ),
                "impact": "promotion_allowed_false_until_family_specific_authorities_exist",
            },
        ],
        "invalidated_v2_derivation_outputs_for_v3": [
            "/population_trajectory_target/participants_per_context",
            "/population_trajectory_target/target_total_enrollment",
            "/population_trajectory_target/enrollment_derivation",
            "/measurement_target/outcome_direction_multiplicity_rule",
            "/moderator_target/coordinate_ids",
            "/transport_target/context_coordinate_rule",
            "/normalization/family_value_at_target_percent",
        ],
        "machine_proof": {
            **proof,
            "coordinate_roles_are_pairwise_disjoint": True,
            "coordinate_role_union_equals_frozen_map": True,
            "D_P_H_T_excluded_from_direct_outcome_basis": True,
            "D_P_H_T_excluded_from_raw_modifier_and_context_roles": True,
            "raw_context_covariates_separate_from_T_estimands": True,
            "v2_global_enrollment_inherited": False,
            "numeric_rank_emitted": False,
            "fabricated_joint_support_matrix_emitted": False,
        },
        "open_gates": [gate["gate_id"] for gate in authority["typed_unresolved_gates"]],
        "disposition": {
            "promotion_allowed": False,
            "stable_rank_allowed": False,
            "global_enrollment_allowed": False,
            "reason_code": "SUBSTANTIVE_V3_AUTHORITY_REQUIRES_SOURCE_BOUND_CLOSURE",
        },
    }


def build_artifact_bytes(repo_root: Path) -> dict[str, bytes]:
    """Return deterministic v3 artifact bytes without mutating the repository."""

    registry = _load_source(
        repo_root / V2_COORDINATE_REGISTRY_PATH,
        V2_COORDINATE_REGISTRY_RAW_SHA256,
    )
    v2_target = _load_source(repo_root / V2_TARGET_PATH, V2_TARGET_RAW_SHA256)
    authority = build_role_aware_authority(registry, v2_target)
    authority_bytes = _pretty_dumps(authority).encode("utf-8")
    impact = build_v2_to_v3_impact_receipt(authority, _sha256_bytes(authority_bytes))
    return {
        "spec/v3/level1/role-aware-target-requirements.v3.json": authority_bytes,
        (
            "spec/v3/level1/migrations/"
            "v2-to-v3-substantive-impact-receipt.json"
        ): _pretty_dumps(impact).encode("utf-8"),
    }


def write_artifacts(repo_root: Path, output_root: Path | None = None) -> dict[str, str]:
    """Write generated artifacts and return their raw SHA-256 map."""

    destination_root = output_root or repo_root
    artifacts = build_artifact_bytes(repo_root)
    hashes: dict[str, str] = {}
    for relative_path, payload in artifacts.items():
        destination = destination_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        hashes[relative_path] = _sha256_bytes(payload)
    return hashes


def _readback_bytes(
    source: str | Path | None,
    installed_parts: tuple[str, ...],
) -> bytes:
    if source is not None:
        return Path(source).read_bytes()
    installed = resources.files("anibench").joinpath(*installed_parts)
    try:
        return installed.read_bytes()
    except FileNotFoundError:
        # Editable checkouts keep forced-inclusion resources at repository
        # root; built distributions keep the same paths below ``anibench``.
        repository_copy = Path(__file__).resolve().parents[2].joinpath(*installed_parts)
        return repository_copy.read_bytes()


def load_role_aware_authority(source: str | Path | None = None) -> dict[str, Any]:
    """Load and validate v3 from a path or the installed package resource.

    ``source=None`` is safe for wheels and zip-style import resources: it does
    not assume a repository checkout or coerce the resource to a filesystem
    path.  Packagers must include ``INSTALLED_V3_AUTHORITY_PARTS``.
    """

    payload = _readback_bytes(source, INSTALLED_V3_AUTHORITY_PARTS)
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise Level1V3AuthorityError("v3 installed authority must be a JSON object")
    validate_role_aware_authority(parsed)
    return parsed


def readback_role_aware_authority(
    authority_source: str | Path | None = None,
    impact_source: str | Path | None = None,
) -> dict[str, Any]:
    """Return hash-bound validation proof from paths or installed resources.

    The impact receipt is the hash authority for the candidate JSON.  This
    prevents an installed wheel from silently serving a different role map.
    Both arguments should be omitted for installed-package readback or supplied
    together for an explicit repository/read-only snapshot.
    """

    if (authority_source is None) != (impact_source is None):
        raise Level1V3AuthorityError(
            "authority_source and impact_source must be supplied together"
        )
    authority_payload = _readback_bytes(
        authority_source,
        INSTALLED_V3_AUTHORITY_PARTS,
    )
    impact_payload = _readback_bytes(impact_source, INSTALLED_V3_IMPACT_PARTS)
    authority = json.loads(authority_payload)
    impact = json.loads(impact_payload)
    if not isinstance(authority, dict) or not isinstance(impact, dict):
        raise Level1V3AuthorityError("v3 readback resources must be JSON objects")
    proof = validate_role_aware_authority(authority)
    if impact.get("contract") != "anibench.level1-v2-to-v3-substantive-impact-receipt.v1":
        raise Level1V3AuthorityError("unexpected v3 impact receipt contract")
    observed_sha256 = _sha256_bytes(authority_payload)
    expected_sha256 = impact.get("candidate_authority", {}).get("raw_sha256")
    if observed_sha256 != expected_sha256:
        raise Level1V3AuthorityError(
            "v3 authority bytes do not match the installed impact receipt"
        )
    if impact.get("candidate_authority", {}).get("promotion_allowed") is not False:
        raise Level1V3AuthorityError("v3 impact receipt must preserve promotion_allowed=false")
    return {
        "contract": "anibench.level1-role-aware-target-installed-readback.v1",
        "authority_raw_sha256": observed_sha256,
        "impact_receipt_raw_sha256": _sha256_bytes(impact_payload),
        "target_id": authority["target_id"],
        "validation": proof,
        "promotion_allowed": False,
        "global_enrollment_state": authority["enrollment_authority"][
            "global_enrollment"
        ]["state"],
        "rank_state": authority["noncompensatory_family_vector"]["rank"]["state"],
    }
