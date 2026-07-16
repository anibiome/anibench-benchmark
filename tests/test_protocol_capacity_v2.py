from __future__ import annotations

import copy
import itertools
import json
import math
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from jsonschema import Draft202012Validator

import anibench.protocol_capacity_v2 as protocol_capacity_module
from anibench.protocol_capacity_v2 import (
    PROTOCOL_CAPACITY_VERSION,
    ProtocolCapacityError,
    compile_protocol_capacity,
)
from anibench import compile_protocol_capacity_v2
from anibench.cli import main
from anibench.studio import StudioHandler
from http.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
SHA = "sha256:" + "0" * 64


def _exact(value: float) -> dict:
    return {"state": "exact", "value": value}


def _set_complete_joint_covariance(
    protocol: dict, signal_ids: list[str], covariance: list[list[float]]
) -> None:
    protocol["measurement_geometry"]["joint_covariance_authority"] = {
        "state": "complete",
        "signal_ids": signal_ids,
        "covariance": covariance,
        "source_object_sha256": SHA,
        "source_locator": "protocol:covariance:joint-updated",
    }


def _protocol(protocol_id: str = "candidate-trial") -> dict:
    return {
        "schema_version": "anibench.protocol-capacity-input.v2",
        "protocol_id": protocol_id,
        "claim_class": "prospective_protocol_capacity",
        "parameter_space": {
            "parameter_space_id": "frozen-biology-v1",
            "dimension": 2,
            "prior_precision": [[1.0, 0.0], [0.0, 1.0]],
            "source_object_sha256": SHA,
        },
        "measurement_geometry": {
            "signals": [
                {
                    "signal_id": "signal-a",
                    "canonical_feature_id": "feature-a",
                    "feature_ancestry_id": "ancestry-a",
                    "operator_row": [1.0, 0.0],
                    "evidence_state": "protocol_committed",
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:table-1:row-a",
                }
            ],
            "covariance_groups": [
                {
                    "covariance_group_id": "covariance-a",
                    "signal_ids": ["signal-a"],
                    "covariance": [[1.0]],
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:covariance:within-a",
                }
            ],
            "joint_covariance_authority": {
                "state": "complete",
                "signal_ids": ["signal-a"],
                "covariance": [[1.0]],
                "source_object_sha256": SHA,
                "source_locator": "protocol:covariance:joint",
            },
            "measurement_modules": [
                {
                    "module_id": "module-a",
                    "canonical_event_unit_id": "blood-draw",
                    "signal_ids": ["signal-a"],
                    "evidence_state": "protocol_committed",
                }
            ],
            "joint_observation_bundles": [
                {
                    "joint_observation_bundle_id": "bundle-moderator",
                    "canonical_event_unit_id": "blood-draw",
                },
                {
                    "joint_observation_bundle_id": "bundle-outcome",
                    "canonical_event_unit_id": "blood-draw",
                },
                {
                    "joint_observation_bundle_id": "bundle-site-a",
                    "canonical_event_unit_id": "blood-draw",
                },
                {
                    "joint_observation_bundle_id": "bundle-site-b",
                    "canonical_event_unit_id": "blood-draw",
                },
            ],
            "population_aggregation_authorities": [
                {
                    "aggregation_authority_id": "synthetic-disjoint-populations",
                    "participant_set_ids": [
                        "all-participants",
                        "site-a-participants",
                        "site-b-participants",
                    ],
                    "aggregation_rule": "sum_information_across_disjoint_participant_sets",
                    "participant_relation": "mutually_disjoint_participant_sets",
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:population-aggregation:synthetic-disjoint",
                }
            ],
            "participant_event_schedules": [
                {
                    "schedule_id": "schedule-moderator",
                    "participant_event_lineage_id": "lineage-moderator",
                    "joint_observation_bundle_id": "bundle-moderator",
                    "canonical_event_unit_id": "blood-draw",
                    "participant_set_id": "all-participants",
                    "trajectory_dependence_id": "dependence-all-participants",
                    "retention_overlap_authority": {
                        "state": "registered_nested",
                        "retained_participant_set_id": "retained-all-participants",
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:retention-overlap:all-participants",
                    },
                    "measurement_module_ids": ["module-a"],
                    "participant_count": _exact(100),
                    "events_per_participant": _exact(1),
                    "retention_fraction": _exact(1),
                    "within_person_repetition_correlation": _exact(0),
                    "schedule_semantics": "exact_offsets",
                    "temporal_offsets": [-1],
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:schedule:moderator",
                },
                {
                    "schedule_id": "schedule-a",
                    "participant_event_lineage_id": "lineage-a",
                    "joint_observation_bundle_id": "bundle-outcome",
                    "canonical_event_unit_id": "blood-draw",
                    "participant_set_id": "all-participants",
                    "trajectory_dependence_id": "dependence-all-participants",
                    "retention_overlap_authority": {
                        "state": "registered_nested",
                        "retained_participant_set_id": "retained-all-participants",
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:retention-overlap:all-participants",
                    },
                    "measurement_module_ids": ["module-a"],
                    "participant_count": _exact(100),
                    "events_per_participant": _exact(4),
                    "retention_fraction": _exact(0.9),
                    "within_person_repetition_correlation": _exact(0.25),
                    "schedule_semantics": "exact_offsets",
                    "temporal_offsets": [0, 30, 60, 90],
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:schedule:lineage-a",
                },
                {
                    "schedule_id": "schedule-site-a",
                    "participant_event_lineage_id": "lineage-site-a",
                    "joint_observation_bundle_id": "bundle-site-a",
                    "canonical_event_unit_id": "blood-draw",
                    "participant_set_id": "site-a-participants",
                    "trajectory_dependence_id": "dependence-site-a-participants",
                    "retention_overlap_authority": {
                        "state": "registered_nested",
                        "retained_participant_set_id": "retained-site-a-participants",
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:retention-overlap:site-a",
                    },
                    "measurement_module_ids": ["module-a"],
                    "participant_count": _exact(50),
                    "events_per_participant": _exact(4),
                    "retention_fraction": _exact(0.9),
                    "within_person_repetition_correlation": _exact(0.25),
                    "schedule_semantics": "exact_offsets",
                    "temporal_offsets": [0, 30, 60, 90],
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:schedule:site-a",
                },
                {
                    "schedule_id": "schedule-site-b",
                    "participant_event_lineage_id": "lineage-site-b",
                    "joint_observation_bundle_id": "bundle-site-b",
                    "canonical_event_unit_id": "blood-draw",
                    "participant_set_id": "site-b-participants",
                    "trajectory_dependence_id": "dependence-site-b-participants",
                    "retention_overlap_authority": {
                        "state": "registered_nested",
                        "retained_participant_set_id": "retained-site-b-participants",
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:retention-overlap:site-b",
                    },
                    "measurement_module_ids": ["module-a"],
                    "participant_count": _exact(50),
                    "events_per_participant": _exact(4),
                    "retention_fraction": _exact(0.9),
                    "within_person_repetition_correlation": _exact(0.25),
                    "schedule_semantics": "exact_offsets",
                    "temporal_offsets": [0, 30, 60, 90],
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:schedule:site-b",
                },
            ],
        },
        "causal_geometry": {
            "operator_components": [
                {
                    "component_id": "component-a",
                    "canonical_operator_id": "canonical-component-a",
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:operator:component-a",
                }
            ],
            "policies": [
                {
                    "policy_id": "control",
                    "operator_component_ids": [],
                    "policy_rule_operator_id": "fixed-control-rule",
                    "policy_rule_source_object_sha256": SHA,
                    "policy_rule_source_locator": "protocol:policy:control",
                },
                {
                    "policy_id": "active",
                    "operator_component_ids": ["component-a"],
                    "policy_rule_operator_id": "fixed-active-rule",
                    "policy_rule_source_object_sha256": SHA,
                    "policy_rule_source_locator": "protocol:policy:active",
                },
            ],
            "decision_rule_operators": [
                {
                    "decision_rule_operator_id": "state-adaptive-assignment-rule",
                    "state": "registered_state_dependent",
                    "state_feature_ids": ["feature-a"],
                    "policy_ids": ["control", "active"],
                    "state_to_policy_contrast_matrix": [[-1.0], [1.0]],
                    "response_state_score_axis_ids": ["score-a"],
                    "response_state_score_matrix": [[1.0]],
                    "policy_interaction_basis_matrix": [[-1.0], [1.0]],
                    "conditional_probability_shift": 0.0625,
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:decision-rule:state-adaptive",
                }
            ],
            "estimands": [
                {
                    "estimand_id": "proximal-feature-a",
                    "outcome_definition_id": "feature-a-level",
                    "outcome_feature_ids": ["feature-a"],
                    "operator_contrasts": [
                        {
                            "contrast_id": "active-minus-control",
                            "policy_coefficients": [
                                {"policy_id": "active", "coefficient": 1.0},
                                {"policy_id": "control", "coefficient": -1.0},
                            ],
                        }
                    ],
                    "horizon_start_offset_exclusive": 0,
                    "horizon_end_offset_inclusive": 30,
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:estimand:proximal-feature-a",
                }
            ],
            "assignment_stages": [
                {
                    "stage_id": "baseline-randomization",
                    "context_id": "all-context",
                    "participant_set_id": "all-participants",
                    "assignment_mechanism": "micro_randomized",
                    "participant_count": _exact(100),
                    "decisions_per_participant": _exact(4),
                    "decision_time_offset": 0,
                    "decision_rule_operator_id": "state-adaptive-assignment-rule",
                    "policy_allocations": [
                        {"policy_id": "control", "probability": 0.5},
                        {"policy_id": "active", "probability": 0.5},
                    ],
                    "linked_outcome_schedule_ids": ["schedule-a"],
                    "moderator_feature_ids": ["feature-a"],
                    "moderator_measurement_schedule_ids": ["schedule-moderator"],
                    "sequential_assignment_probability": 0.5,
                    "decision_epochs": [
                        {
                            "decision_epoch_id": f"decision-{offset}",
                            "decision_time_offset": offset,
                            "availability_probability": 1.0,
                            "history_moderator_feature_ids": ["feature-a"],
                            "history_measurement_schedule_ids": ["schedule-moderator"],
                            "policy_propensities": [
                                {"policy_id": "control", "probability": 0.5},
                                {"policy_id": "active", "probability": 0.5},
                            ],
                            "proximal_outcome_links": [
                                {
                                    "schedule_id": "schedule-a",
                                    "estimand_id": "proximal-feature-a",
                                }
                            ],
                        }
                        for offset in (0, 30, 60)
                    ],
                    "moderator_population_geometry": {
                        "state": "registered",
                        "population_scope": (
                            "uniform_loewner_lower_bound_on_standardized_moderator_"
                            "covariance_within_every_exact_joint_eligible_predecision_"
                            "stage_context_policy_history_population"
                        ),
                        "epoch_covariances": [
                            {
                                "decision_epoch_id": f"decision-{offset}",
                                "moderator_feature_ids": ["feature-a"],
                                "population_covariance": [[1.0]],
                                "source_object_sha256": SHA,
                                "source_locator": f"protocol:population-covariance:{offset}",
                            }
                            for offset in (0, 30, 60)
                        ],
                    },
                    "smart_path_geometry": {
                        "state": "not_applicable",
                        "reason": "micro-randomized stage",
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:smart:not-applicable",
                    },
                    "conditional_moderated_eligibility_authority": {
                        "state": "registered_pointwise_lower_bounds",
                        "scope": (
                            "pointwise_by_stage_context_policy_over_every_"
                            "preassignment_history_for_treatment_by_moderator_information"
                        ),
                        "context_id": "all-context",
                        "history_scope_id": "all-preassignment-histories",
                        "history_scope_semantics": (
                            "uniform_lower_bound_over_every_preassignment_history_"
                            "in_stage_context"
                        ),
                        "bounds": [
                            {
                                "decision_epoch_id": f"decision-{offset}",
                                "policy_id": policy_id,
                                "minimum_conditional_availability_probability": 1.0,
                                "minimum_complete_case_outcome_moderator_retention_probability": 0.9,
                            }
                            for offset in (0, 30, 60)
                            for policy_id in ("control", "active")
                        ],
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:conditional-eligibility:all-context",
                    },
                    "estimating_score_dependence_authority": {
                        "state": "registered",
                        "model": "independent",
                        "correlation": 0.0,
                        "pooled_across_decisions": True,
                        "score_semantics": (
                            "correlation_of_centered_treatment_contrast_times_"
                            "outcome_or_moderator_estimating_scores_over_ordered_"
                            "decision_epochs"
                        ),
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:estimating-score-dependence",
                    },
                    "source_object_sha256": SHA,
                    "source_locator": "protocol:assignment:baseline",
                }
            ],
            "transport_geometry": {
                "reference_estimand_id": "proximal-feature-a",
                "transport_axis_families": [
                    {
                        "transport_axis_family_id": "site-transport",
                        "reference_estimand_id": "proximal-feature-a",
                        "required_transport_axis_ids": ["site-context"],
                        "coordinate_scale_authority": {
                            "state": "registered",
                            "scope": "units_transforms_ranges_for_required_transport_axes",
                            "source_object_sha256": SHA,
                            "source_locator": "protocol:transport-axis-scale:site-context",
                        },
                    }
                ],
                "contexts": [
                    {
                        "context_id": "site-a",
                        "participant_set_id": "site-a-participants",
                        "participant_count": _exact(50),
                        "assignment_mechanism": "simple_randomized",
                        "assignment_time_offset": 0,
                        "linked_outcome_schedule_ids": ["schedule-site-a"],
                        "policy_allocations": [
                            {"policy_id": "control", "probability": 0.5},
                            {"policy_id": "active", "probability": 0.5},
                        ],
                        "transport_coordinates": [
                            {"transport_axis_id": "site-context", "value": 0.0}
                        ],
                        "estimand_binding": {
                            "state": "direct",
                            "estimand_id": "proximal-feature-a",
                        },
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:transport:site-a",
                    },
                    {
                        "context_id": "site-b",
                        "participant_set_id": "site-b-participants",
                        "participant_count": _exact(50),
                        "assignment_mechanism": "simple_randomized",
                        "assignment_time_offset": 0,
                        "linked_outcome_schedule_ids": ["schedule-site-b"],
                        "policy_allocations": [
                            {"policy_id": "control", "probability": 0.5},
                            {"policy_id": "active", "probability": 0.5},
                        ],
                        "transport_coordinates": [
                            {"transport_axis_id": "site-context", "value": 1.0}
                        ],
                        "estimand_binding": {
                            "state": "direct",
                            "estimand_id": "proximal-feature-a",
                        },
                        "source_object_sha256": SHA,
                        "source_locator": "protocol:transport:site-b",
                    },
                ],
            },
        },
    }


def _families(result: dict) -> dict:
    assert result["scenario_count"] == 1
    return result["scenarios"][0]["families"]


def _sync_conditional_eligibility_authority(
    stage: dict, *, retention: float = 0.9
) -> None:
    """Rebind a fixture's pointwise authority after deliberate epoch edits."""

    authority = stage["conditional_moderated_eligibility_authority"]
    authority["context_id"] = stage["context_id"]
    authority["bounds"] = [
        {
            "decision_epoch_id": epoch["decision_epoch_id"],
            "policy_id": allocation["policy_id"],
            "minimum_conditional_availability_probability": float(
                epoch["availability_probability"]
            ),
            "minimum_complete_case_outcome_moderator_retention_probability": (
                retention
            ),
        }
        for epoch in stage["decision_epochs"]
        for allocation in epoch["policy_propensities"]
    ]


def _nested_direction_menu_protocol(protocol_id: str, bundle_count: int) -> dict:
    """Add many PSD-incomparable two-dimensional, source-bound bundle directions."""

    protocol = _protocol(protocol_id)
    geometry = protocol["measurement_geometry"]
    template = geometry["participant_event_schedules"][0]
    signal_ids = ["signal-a"]
    for index in range(bundle_count):
        angle = math.pi * index / max(1, bundle_count)
        signal_id = f"signal-direction-{index:03d}"
        module_id = f"module-direction-{index:03d}"
        bundle_id = f"bundle-direction-{index:03d}"
        signal_ids.append(signal_id)
        geometry["signals"].append(
            {
                "signal_id": signal_id,
                "canonical_feature_id": f"feature-direction-{index:03d}",
                "feature_ancestry_id": f"ancestry-direction-{index:03d}",
                "operator_row": [math.cos(angle), math.sin(angle)],
                "evidence_state": "protocol_committed",
                "source_object_sha256": SHA,
                "source_locator": f"protocol:direction:{index:03d}",
            }
        )
        geometry["covariance_groups"].append(
            {
                "covariance_group_id": f"covariance-direction-{index:03d}",
                "signal_ids": [signal_id],
                "covariance": [[1.0]],
                "source_object_sha256": SHA,
                "source_locator": f"protocol:covariance:direction:{index:03d}",
            }
        )
        geometry["measurement_modules"].append(
            {
                "module_id": module_id,
                "canonical_event_unit_id": "blood-draw",
                "signal_ids": [signal_id],
                "evidence_state": "protocol_committed",
            }
        )
        geometry["joint_observation_bundles"].append(
            {
                "joint_observation_bundle_id": bundle_id,
                "canonical_event_unit_id": "blood-draw",
            }
        )
        schedule = copy.deepcopy(template)
        schedule.update(
            {
                "schedule_id": f"schedule-direction-{index:03d}",
                "participant_event_lineage_id": f"lineage-direction-{index:03d}",
                "joint_observation_bundle_id": bundle_id,
                "measurement_module_ids": [module_id],
                "participant_count": _exact(100),
                "events_per_participant": _exact(1),
                "retention_fraction": _exact((bundle_count + 1 - index) / (bundle_count + 1)),
                "within_person_repetition_correlation": _exact(0.25),
                "temporal_offsets": [1000 + index],
                "source_locator": f"protocol:schedule:direction:{index:03d}",
            }
        )
        geometry["participant_event_schedules"].append(schedule)
    dimension = len(signal_ids)
    geometry["joint_covariance_authority"] = {
        "state": "complete",
        "signal_ids": signal_ids,
        "covariance": [
            [1.0 if row == column else 0.0 for column in range(dimension)]
            for row in range(dimension)
        ],
        "source_object_sha256": SHA,
        "source_locator": "protocol:covariance:all-directions",
    }
    return protocol


def _regular_process_protocol(
    protocol_id: str,
    *,
    decision_count: int,
    decisions_per_day: int = 1,
    availability_probability: float = 0.75,
) -> dict:
    protocol = _protocol(protocol_id)
    interval = 1.0 / decisions_per_day
    readback = interval / 2.0
    duration_days = decision_count // decisions_per_day
    assert duration_days * decisions_per_day == decision_count
    readbacks = [index * interval + readback for index in range(decision_count)]
    outcome = protocol["measurement_geometry"]["participant_event_schedules"][1]
    outcome["events_per_participant"] = _exact(decision_count)
    outcome["temporal_offsets"] = readbacks
    estimand = protocol["causal_geometry"]["estimands"][0]
    estimand["horizon_end_offset_inclusive"] = readback
    stage = protocol["causal_geometry"]["assignment_stages"][0]
    stage["decisions_per_participant"] = _exact(decision_count)
    template = copy.deepcopy(stage["decision_epochs"][0])
    template["decision_epoch_id"] = "decision-template"
    template["decision_time_offset"] = 0.0
    template["availability_probability"] = availability_probability
    stage["decision_epochs"] = [template]
    stage["regular_decision_epoch_process"] = {
        "decision_epoch_process_id": "registered-regular-process",
        "template_decision_epoch_id": "decision-template",
        "decision_count": decision_count,
        "start_offset": 0.0,
        "decision_interval_days": interval,
        "decisions_per_day": decisions_per_day,
        "duration_days": duration_days,
        "proximal_readback_offset_days": readback,
        "source_object_sha256": SHA,
        "source_locator": "protocol:decision-epoch-process:regular",
    }
    stage["moderator_population_geometry"] = {
        "state": "registered_stationary_rate_process",
        "population_scope": (
            "uniform_loewner_lower_bound_on_standardized_moderator_covariance_"
            "within_every_exact_joint_eligible_predecision_stage_context_policy_"
            "history_population"
        ),
        "decision_epoch_process_id": "registered-regular-process",
        "moderator_feature_ids": ["feature-a"],
        "population_covariance": [[1.0]],
        "source_object_sha256": SHA,
        "source_locator": "protocol:moderator-population:stationary",
    }
    _sync_conditional_eligibility_authority(stage)
    return protocol


def _explicit_regular_grid_protocol(
    protocol_id: str,
    *,
    decision_count: int,
    availability_probability: float = 0.75,
) -> dict:
    protocol = _protocol(protocol_id)
    readback = 0.5
    outcome = protocol["measurement_geometry"]["participant_event_schedules"][1]
    outcome["events_per_participant"] = _exact(decision_count)
    outcome["temporal_offsets"] = [index + readback for index in range(decision_count)]
    protocol["causal_geometry"]["estimands"][0]["horizon_end_offset_inclusive"] = readback
    stage = protocol["causal_geometry"]["assignment_stages"][0]
    stage["decisions_per_participant"] = _exact(decision_count)
    template = stage["decision_epochs"][0]
    stage["decision_epochs"] = []
    covariance_rows = []
    for index in range(decision_count):
        epoch = copy.deepcopy(template)
        epoch["decision_epoch_id"] = f"decision-{index}"
        epoch["decision_time_offset"] = float(index)
        epoch["availability_probability"] = availability_probability
        stage["decision_epochs"].append(epoch)
        covariance_rows.append(
            {
                "decision_epoch_id": f"decision-{index}",
                "moderator_feature_ids": ["feature-a"],
                "population_covariance": [[1.0]],
                "source_object_sha256": SHA,
                "source_locator": f"protocol:population-covariance:{index}",
            }
        )
    stage["moderator_population_geometry"] = {
        "state": "registered",
        "population_scope": (
            "uniform_loewner_lower_bound_on_standardized_moderator_covariance_"
            "within_every_exact_joint_eligible_predecision_stage_context_policy_"
            "history_population"
        ),
        "epoch_covariances": covariance_rows,
    }
    _sync_conditional_eligibility_authority(stage)
    return protocol


def test_compiler_emits_separate_families_without_empirical_or_overall_claim() -> None:
    result = compile_protocol_capacity(_protocol())
    assert result["compiler_version"] == PROTOCOL_CAPACITY_VERSION
    assert result["empirical_attainment"] is False
    assert result["public_rank_emission_permitted"] is False
    assert result["overall_scalar"] is None
    families = _families(result)
    assert set(families) == {
        "intensive",
        "extensive",
        "longitudinal",
        "causal",
        "personalized_sequential",
        "transport",
        "measurement_audit",
    }
    assert families["intensive"]["effective_rank"] == 1
    assert families["extensive"]["retained_participant_events"] == 820
    assert families["causal"]["policy_rank"] == 1
    assert families["causal"]["component_rank"] == 1
    assert families["causal"]["gates"] == {"D_dynamic_operator": True}
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": True,
        "H_heterogeneous_response": True,
    }
    assert families["transport"]["gates"] == {"T_transport": True}
    assert result["uncertainty_reuse"]["coordinate_state_counts"] == {"exact": 20}

    schema = json.loads(
        (ROOT / "schemas/v2/protocol-capacity-result.schema.json").read_text(encoding="utf-8")
    )
    assert not list(Draft202012Validator(schema).iter_errors(result))


def test_protocol_identity_cannot_change_identical_geometry() -> None:
    first = compile_protocol_capacity(_protocol("first-protocol"))
    second = compile_protocol_capacity(_protocol("second-protocol"))
    assert first["compiler_version"] == second["compiler_version"]
    assert first["anti_gaming_contract"] == second["anti_gaming_contract"]
    assert _families(first) == _families(second)
    assert first["anti_gaming_contract"]["normative_level1_reference_bound"] is False


def test_population_scale_changes_extensive_but_never_intensive_depth() -> None:
    ordinary = _protocol()
    extreme = copy.deepcopy(ordinary)
    extreme["protocol_id"] = "ten-million-person-preview"
    extreme["measurement_geometry"]["participant_event_schedules"][1]["participant_count"] = _exact(
        10_000_000
    )
    extreme["causal_geometry"]["assignment_stages"][0]["participant_count"] = _exact(10_000_000)
    ordinary_families = _families(compile_protocol_capacity(ordinary))
    extreme_families = _families(compile_protocol_capacity(extreme))
    assert extreme_families["intensive"] == ordinary_families["intensive"]
    assert (
        extreme_families["extensive"]["retained_log10_contraction"]
        > ordinary_families["extensive"]["retained_log10_contraction"]
    )
    assert extreme_families["extensive"]["retained_participant_events"] == 36_000_460


def test_duplicate_aliases_and_module_menu_splitting_cannot_inflate_capacity() -> None:
    base = _protocol()
    attacked = copy.deepcopy(base)
    attacked["protocol_id"] = "alias-and-menu-splitting-attack"
    alias = copy.deepcopy(attacked["measurement_geometry"]["signals"][0])
    alias["signal_id"] = "signal-a-alias"
    attacked["measurement_geometry"]["signals"].append(alias)
    attacked["measurement_geometry"]["measurement_modules"].extend(
        [
            {
                "module_id": "module-a-split-1",
                "canonical_event_unit_id": "blood-draw",
                "signal_ids": ["signal-a"],
                "evidence_state": "protocol_committed",
            },
            {
                "module_id": "module-a-split-2",
                "canonical_event_unit_id": "blood-draw",
                "signal_ids": ["signal-a-alias"],
                "evidence_state": "protocol_committed",
            },
        ]
    )
    attacked["measurement_geometry"]["participant_event_schedules"][0][
        "measurement_module_ids"
    ].extend(["module-a-split-1", "module-a-split-2"])
    base_families = _families(compile_protocol_capacity(base))
    attacked_families = _families(compile_protocol_capacity(attacked))
    for metric in (
        "canonical_feature_count",
        "feature_ancestry_count",
        "effective_rank",
        "maximum_joint_bundle_log10_contraction",
        "information_matrix_sha256",
    ):
        assert attacked_families["intensive"][metric] == base_families["intensive"][metric]
    assert attacked_families["extensive"] == base_families["extensive"]
    assert attacked_families["measurement_audit"]["alias_count_removed"] == 1
    assert attacked_families["measurement_audit"]["menu_module_count"] == 3


def test_independent_measurement_geometry_strictly_dominates_shallow_geometry() -> None:
    shallow = _protocol()
    deep = copy.deepcopy(shallow)
    deep["protocol_id"] = "strictly-deeper-trial"
    deep["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-b",
            "canonical_feature_id": "feature-b",
            "feature_ancestry_id": "ancestry-b",
            "operator_row": [0.0, 1.0],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:table-1:row-b",
        }
    )
    deep["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-b",
            "signal_ids": ["signal-b"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:within-b",
        }
    )
    _set_complete_joint_covariance(deep, ["signal-a", "signal-b"], [[1.0, 0.0], [0.0, 1.0]])
    deep["measurement_geometry"]["measurement_modules"].append(
        {
            "module_id": "module-b",
            "canonical_event_unit_id": "blood-draw",
            "signal_ids": ["signal-b"],
            "evidence_state": "protocol_committed",
        }
    )
    deep["measurement_geometry"]["participant_event_schedules"][1]["measurement_module_ids"].append(
        "module-b"
    )
    shallow_families = _families(compile_protocol_capacity(shallow))
    deep_families = _families(compile_protocol_capacity(deep))
    assert deep_families["intensive"]["effective_rank"] == 2
    assert (
        deep_families["intensive"]["effective_rank"]
        > shallow_families["intensive"]["effective_rank"]
    )
    assert (
        deep_families["intensive"]["maximum_joint_bundle_log10_contraction"]
        > shallow_families["intensive"]["maximum_joint_bundle_log10_contraction"]
    )
    assert (
        deep_families["extensive"]["retained_log10_contraction"]
        > shallow_families["extensive"]["retained_log10_contraction"]
    )


def test_conditional_plans_emit_typed_scenario_envelopes() -> None:
    protocol = _protocol("conditional-preview")
    protocol["measurement_geometry"]["participant_event_schedules"][1]["participant_count"] = {
        "state": "conditional",
        "scenario_group_id": "funding-state",
        "scenarios": [
            {"scenario_id": "funded", "value": 1_000},
            {"scenario_id": "not-funded", "value": 100},
        ],
    }
    result = compile_protocol_capacity(protocol)
    assert result["scenario_count"] == 2
    assert result["family_envelopes"]["intensive.effective_rank"] == {
        "minimum": 1,
        "maximum": 1,
    }
    assert result["family_envelopes"]["extensive.retained_participant_events"] == {
        "minimum": 820.0,
        "maximum": 4060.0,
    }
    assert all("funding-state:" in row["scenario_id"] for row in result["scenarios"])


def test_d_p_h_t_credit_is_gated_by_actual_geometry() -> None:
    protocol = _protocol("measurement-only-preview")
    causal = protocol["causal_geometry"]
    causal["assignment_stages"][0]["assignment_mechanism"] = "observational"
    causal["transport_geometry"]["contexts"] = [causal["transport_geometry"]["contexts"][0]]
    families = _families(compile_protocol_capacity(protocol))
    assert families["causal"]["gates"] == {"D_dynamic_operator": False}
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": False,
        "H_heterogeneous_response": False,
    }
    assert families["transport"]["gates"] == {"T_transport": False}


def test_caller_rank_integers_and_conflicting_feature_aliases_fail_closed() -> None:
    injected = _protocol("rank-injection")
    injected["causal_geometry"]["policy_rank"] = 999
    with pytest.raises(ProtocolCapacityError, match="Additional properties"):
        compile_protocol_capacity(injected)

    conflicting = _protocol("conflicting-alias")
    alias = copy.deepcopy(conflicting["measurement_geometry"]["signals"][0])
    alias["signal_id"] = "signal-conflict"
    alias["operator_row"] = [0.0, 1.0]
    conflicting["measurement_geometry"]["signals"].append(alias)
    with pytest.raises(ProtocolCapacityError, match="conflicting operator geometry"):
        compile_protocol_capacity(conflicting)


def test_missing_covariance_controls_fail_closed() -> None:
    protocol = _protocol("missing-covariance")
    protocol["measurement_geometry"]["covariance_groups"] = []
    with pytest.raises(ProtocolCapacityError):
        compile_protocol_capacity(protocol)


def test_policy_component_stage_and_schedule_aliases_cannot_inflate_geometry() -> None:
    base = _protocol("causal-alias-base")
    attacked = copy.deepcopy(base)
    attacked["protocol_id"] = "causal-alias-attack"

    component_alias = copy.deepcopy(attacked["causal_geometry"]["operator_components"][0])
    component_alias["component_id"] = "component-a-alias"
    attacked["causal_geometry"]["operator_components"].append(component_alias)
    active_alias = copy.deepcopy(attacked["causal_geometry"]["policies"][1])
    active_alias["policy_id"] = "active-alias"
    active_alias["operator_component_ids"] = ["component-a-alias"]
    attacked["causal_geometry"]["policies"].append(active_alias)
    allocations = attacked["causal_geometry"]["assignment_stages"][0]["policy_allocations"]
    allocations[1]["probability"] = 0.25
    allocations.append({"policy_id": "active-alias", "probability": 0.25})

    stage_alias = copy.deepcopy(attacked["causal_geometry"]["assignment_stages"][0])
    stage_alias["stage_id"] = "baseline-randomization-alias"
    attacked["causal_geometry"]["assignment_stages"].append(stage_alias)

    schedule_alias = copy.deepcopy(
        attacked["measurement_geometry"]["participant_event_schedules"][0]
    )
    schedule_alias["schedule_id"] = "schedule-a-alias"
    schedule_alias["participant_event_lineage_id"] = "lineage-a-alias"
    attacked["measurement_geometry"]["participant_event_schedules"].append(schedule_alias)

    base_families = _families(compile_protocol_capacity(base))
    attacked_families = _families(compile_protocol_capacity(attacked))
    assert attacked_families["intensive"] == base_families["intensive"]
    assert attacked_families["extensive"] == base_families["extensive"]
    assert attacked_families["longitudinal"] == base_families["longitudinal"]
    for key, value in base_families["causal"].items():
        if key != "policy_alias_count_removed":
            assert attacked_families["causal"][key] == value
    assert attacked_families["causal"]["policy_alias_count_removed"] == 1
    assert attacked_families["personalized_sequential"] == base_families["personalized_sequential"]
    assert attacked_families["transport"] == base_families["transport"]


def test_unknown_and_conditional_evidence_never_receives_unconditional_credit() -> None:
    unknown = _protocol("unknown-evidence")
    unknown["measurement_geometry"]["signals"][0]["evidence_state"] = "unknown"
    families = _families(compile_protocol_capacity(unknown))
    assert families["intensive"]["effective_rank"] is None
    assert families["intensive"]["maximum_joint_bundle_log10_contraction"] is None
    assert families["extensive"]["retained_log10_contraction"] is None

    conditional = _protocol("conditional-evidence")
    signal = conditional["measurement_geometry"]["signals"][0]
    signal["evidence_state"] = "conditional"
    signal["inclusion_coordinate"] = {
        "state": "conditional",
        "scenario_group_id": "assay-funding",
        "scenarios": [
            {"scenario_id": "excluded", "value": 0},
            {"scenario_id": "included", "value": 1},
        ],
    }
    result = compile_protocol_capacity(conditional)
    assert result["scenario_count"] == 2
    assert (
        result["family_envelopes"]["intensive.maximum_joint_bundle_log10_contraction"]["minimum"]
        == 0
    )
    assert (
        result["family_envelopes"]["intensive.maximum_joint_bundle_log10_contraction"]["maximum"]
        > 0
    )

    unknown_module = _protocol("unknown-module")
    unknown_module["measurement_geometry"]["measurement_modules"][0]["evidence_state"] = "unknown"
    assert (
        _families(compile_protocol_capacity(unknown_module))["intensive"]["effective_rank"] is None
    )


def test_coupled_conditionals_do_not_form_contradictory_cartesian_products() -> None:
    protocol = _protocol("coupled-conditional")
    protocol["measurement_geometry"]["signals"][0]["evidence_state"] = "conditional"
    protocol["measurement_geometry"]["signals"][0]["inclusion_coordinate"] = {
        "state": "conditional",
        "scenario_group_id": "funding",
        "scenarios": [
            {"scenario_id": "no", "value": 0},
            {"scenario_id": "yes", "value": 1},
        ],
    }
    protocol["measurement_geometry"]["participant_event_schedules"][1]["participant_count"] = {
        "state": "conditional",
        "scenario_group_id": "funding",
        "scenarios": [
            {"scenario_id": "no", "value": 100},
            {"scenario_id": "yes", "value": 1_000},
        ],
    }
    assert compile_protocol_capacity(protocol)["scenario_count"] == 2


def test_disjoint_participants_and_any_random_stage_cannot_manufacture_causal_gates() -> None:
    disjoint = _protocol("disjoint-stage")
    disjoint["causal_geometry"]["assignment_stages"][0]["participant_set_id"] = (
        "different-participants"
    )
    families = _families(compile_protocol_capacity(disjoint))
    assert families["causal"]["gates"]["D_dynamic_operator"] is False
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": False,
        "H_heterogeneous_response": False,
    }

    mixed = _protocol("mixed-random-observational")
    randomized = mixed["causal_geometry"]["assignment_stages"][0]
    randomized["participant_set_id"] = "tiny-unlinked-set"
    randomized["participant_count"] = _exact(2)
    observational = copy.deepcopy(randomized)
    observational["stage_id"] = "large-observational-stage"
    observational["participant_set_id"] = "all-participants"
    observational["participant_count"] = _exact(10_000)
    observational["assignment_mechanism"] = "observational"
    mixed["causal_geometry"]["assignment_stages"].append(observational)
    families = _families(compile_protocol_capacity(mixed))
    assert families["causal"]["gates"]["D_dynamic_operator"] is False
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": False,
        "H_heterogeneous_response": False,
    }


def test_numeric_moderator_basis_is_rejected_and_preassignment_join_is_required() -> None:
    injected = _protocol("numeric-moderator-injection")
    injected["causal_geometry"]["assignment_stages"][0]["moderator_basis"] = [
        [1.0],
        [1.0],
    ]
    with pytest.raises(ProtocolCapacityError, match="Additional properties"):
        compile_protocol_capacity(injected)

    late = _protocol("late-moderator")
    late["causal_geometry"]["assignment_stages"][0]["moderator_measurement_schedule_ids"] = [
        "schedule-a"
    ]
    for epoch in late["causal_geometry"]["assignment_stages"][0]["decision_epochs"]:
        epoch["history_measurement_schedule_ids"] = ["schedule-a"]
    personalized = _families(compile_protocol_capacity(late))["personalized_sequential"]
    assert personalized["gates"]["P_personalized_policy"] is False
    assert personalized["gates"]["H_heterogeneous_response"] is False


def test_five_policy_alias_attack_cannot_inflate_policy_or_component_rank() -> None:
    attacked = _protocol("five-policy-aliases")
    active = attacked["causal_geometry"]["policies"][1]
    allocations = attacked["causal_geometry"]["assignment_stages"][0]["policy_allocations"]
    allocations[1]["probability"] = 0.1
    for index in range(4):
        alias = copy.deepcopy(active)
        alias["policy_id"] = f"active-alias-{index}"
        alias["policy_rule_source_locator"] = f"protocol:policy:alias-{index}"
        attacked["causal_geometry"]["policies"].append(alias)
        allocations.append({"policy_id": alias["policy_id"], "probability": 0.1})
    causal = _families(compile_protocol_capacity(attacked))["causal"]
    assert causal["canonical_policy_count"] == 2
    assert causal["policy_alias_count_removed"] == 4
    assert causal["policy_rank"] == 1
    assert causal["component_rank"] == 1


def test_ancestry_event_unit_and_overlapping_schedule_aliases_do_not_inflate() -> None:
    base = _protocol("set-algebra-base")
    attacked = copy.deepcopy(base)
    attacked["protocol_id"] = "set-algebra-attack"
    signal_alias = copy.deepcopy(attacked["measurement_geometry"]["signals"][0])
    signal_alias["signal_id"] = "renamed-signal"
    signal_alias["canonical_feature_id"] = "renamed-feature"
    signal_alias["source_locator"] = "different:locator"
    attacked["measurement_geometry"]["signals"].append(signal_alias)
    attacked["measurement_geometry"]["measurement_modules"].append(
        {
            "module_id": "renamed-module",
            "canonical_event_unit_id": "renamed-event-unit",
            "signal_ids": ["renamed-signal"],
            "evidence_state": "protocol_committed",
        }
    )
    schedule_alias = copy.deepcopy(
        attacked["measurement_geometry"]["participant_event_schedules"][1]
    )
    schedule_alias["schedule_id"] = "renamed-schedule"
    schedule_alias["participant_event_lineage_id"] = "renamed-lineage"
    schedule_alias["joint_observation_bundle_id"] = "renamed-bundle"
    schedule_alias["canonical_event_unit_id"] = "renamed-event-unit"
    schedule_alias["measurement_module_ids"] = ["renamed-module"]
    schedule_alias["source_locator"] = "changed:schedule:locator"
    attacked["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "renamed-bundle",
            "canonical_event_unit_id": "renamed-event-unit",
        }
    )
    attacked["measurement_geometry"]["participant_event_schedules"].append(schedule_alias)
    _families(compile_protocol_capacity(base))
    with pytest.raises(ProtocolCapacityError, match="canonical participant-event"):
        compile_protocol_capacity(attacked)


def test_disjoint_bundles_never_union_and_incompatible_joint_bundle_fails() -> None:
    protocol = _protocol("disjoint-bundles")
    protocol["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-b",
            "canonical_feature_id": "feature-b",
            "feature_ancestry_id": "ancestry-b",
            "operator_row": [0.0, 1.0],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:signal-b",
        }
    )
    protocol["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-b",
            "signal_ids": ["signal-b"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:within-b",
        }
    )
    _set_complete_joint_covariance(protocol, ["signal-a", "signal-b"], [[1.0, 0.0], [0.0, 1.0]])
    protocol["measurement_geometry"]["measurement_modules"].append(
        {
            "module_id": "module-b",
            "canonical_event_unit_id": "saliva",
            "signal_ids": ["signal-b"],
            "evidence_state": "protocol_committed",
        }
    )
    protocol["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-b",
            "canonical_event_unit_id": "saliva",
        }
    )
    schedule = copy.deepcopy(protocol["measurement_geometry"]["participant_event_schedules"][1])
    schedule.update(
        {
            "schedule_id": "schedule-b",
            "participant_event_lineage_id": "lineage-b",
            "joint_observation_bundle_id": "bundle-b",
            "canonical_event_unit_id": "saliva",
            "participant_set_id": "other-participants",
            "trajectory_dependence_id": "dependence-other-participants",
            "measurement_module_ids": ["module-b"],
            "source_locator": "protocol:schedule-b",
        }
    )
    schedule["retention_overlap_authority"]["retained_participant_set_id"] = (
        "retained-other-participants"
    )
    protocol["measurement_geometry"]["participant_event_schedules"].append(schedule)
    protocol["measurement_geometry"]["population_aggregation_authorities"][0][
        "participant_set_ids"
    ].append("other-participants")
    assert _families(compile_protocol_capacity(protocol))["intensive"]["effective_rank"] == 1

    incompatible = _protocol("incompatible-joint-bundle")
    incompatible["measurement_geometry"]["participant_event_schedules"][2][
        "joint_observation_bundle_id"
    ] = "bundle-outcome"
    with pytest.raises(ProtocolCapacityError, match="compatible participant-event support"):
        compile_protocol_capacity(incompatible)


def test_same_event_multimodal_layers_are_joint_and_counted_once() -> None:
    protocol = _protocol("joint-event-multimodal")
    protocol["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-b",
            "canonical_feature_id": "feature-b",
            "feature_ancestry_id": "ancestry-b",
            "operator_row": [0.0, 1.0],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:signal-b",
        }
    )
    protocol["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-b",
            "signal_ids": ["signal-b"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:within-b",
        }
    )
    _set_complete_joint_covariance(protocol, ["signal-a", "signal-b"], [[1.0, 0.0], [0.0, 1.0]])
    protocol["measurement_geometry"]["measurement_modules"].append(
        {
            "module_id": "module-b",
            "canonical_event_unit_id": "blood-draw",
            "signal_ids": ["signal-b"],
            "evidence_state": "protocol_committed",
        }
    )
    schedule = copy.deepcopy(protocol["measurement_geometry"]["participant_event_schedules"][1])
    schedule.update(
        {
            "schedule_id": "schedule-b",
            "participant_event_lineage_id": "lineage-b",
            "measurement_module_ids": ["module-b"],
            "source_locator": "protocol:schedule:lineage-b",
        }
    )
    protocol["measurement_geometry"]["participant_event_schedules"].append(schedule)

    base = _families(compile_protocol_capacity(_protocol("joint-event-base")))
    families = _families(compile_protocol_capacity(protocol))
    assert families["intensive"]["effective_rank"] == 2
    assert (
        families["extensive"]["retained_participant_events"]
        == base["extensive"]["retained_participant_events"]
    )
    assert (
        families["longitudinal"]["retained_participant_events"]
        == base["longitudinal"]["retained_participant_events"]
    )
    all_participants = next(
        row
        for row in families["longitudinal"]["trajectory_ledger"]
        if row["participant_set_id"] == "all-participants"
    )
    assert all_participants["retained_participant_events"] == 460.0
    assert all_participants["distinct_temporal_offsets"] == 5

    split = copy.deepcopy(protocol)
    split["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-split-attack",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    split["measurement_geometry"]["participant_event_schedules"][-1][
        "joint_observation_bundle_id"
    ] = "bundle-split-attack"
    with pytest.raises(ProtocolCapacityError, match="split across joint observation bundles"):
        compile_protocol_capacity(split)


def test_duplicate_covariance_ids_and_observational_transport_fail_closed() -> None:
    duplicate = _protocol("duplicate-covariance")
    duplicate["measurement_geometry"]["covariance_groups"].append(
        copy.deepcopy(duplicate["measurement_geometry"]["covariance_groups"][0])
    )
    with pytest.raises(ProtocolCapacityError, match="duplicate covariance_group_id"):
        compile_protocol_capacity(duplicate)

    observational = _protocol("observational-transport")
    for context in observational["causal_geometry"]["transport_geometry"]["contexts"]:
        context["assignment_mechanism"] = "observational"
    transport = _families(compile_protocol_capacity(observational))["transport"]
    assert transport["gates"]["T_transport"] is False


def test_custom_operator_and_prior_geometry_is_never_comparison_eligible() -> None:
    extreme = _protocol("arbitrary-geometry")
    extreme["measurement_geometry"]["signals"][0]["operator_row"] = [1e9, 0.0]
    extreme["parameter_space"]["prior_precision"] = [[1e-18, 0.0], [0.0, 1e-18]]
    result = compile_protocol_capacity(extreme)
    assert result["comparison_eligible"] is False
    assert result["ontology_binding_state"] == "custom_unverified"
    assert result["source_binding_state"]["external_objects"] == (
        "caller_declared_not_content_verified"
    )
    assert result["public_rank_emission_permitted"] is False
    assert result["anti_gaming_contract"]["normative_level1_reference_bound"] is False


def test_result_schema_rejects_garbage_scenarios_and_fake_envelopes() -> None:
    result = compile_protocol_capacity(_protocol("strict-result-schema"))
    schema = json.loads(
        (ROOT / "schemas/v2/protocol-capacity-result.schema.json").read_text(encoding="utf-8")
    )
    garbage = copy.deepcopy(result)
    garbage["scenarios"] = ["garbage"]
    assert list(Draft202012Validator(schema).iter_errors(garbage))
    fake = copy.deepcopy(result)
    fake["family_envelopes"] = {"fake": "100%"}
    assert list(Draft202012Validator(schema).iter_errors(fake))


def test_disjoint_cross_sections_cannot_manufacture_longitudinal_follow_up() -> None:
    protocol = _protocol("disjoint-cross-sections")
    offsets = (0, 365, 100, 200)
    participant_sets = (
        "cross-section-0",
        "cross-section-365",
        "site-a-participants",
        "site-b-participants",
    )
    for schedule, offset, participant_set_id in zip(
        protocol["measurement_geometry"]["participant_event_schedules"],
        offsets,
        participant_sets,
    ):
        schedule["participant_set_id"] = participant_set_id
        schedule["trajectory_dependence_id"] = f"dependence-{participant_set_id}"
        schedule["retention_overlap_authority"]["retained_participant_set_id"] = (
            f"retained-{participant_set_id}"
        )
        schedule["events_per_participant"] = _exact(1)
        schedule["retention_fraction"] = _exact(1)
        schedule["within_person_repetition_correlation"] = _exact(0)
        schedule["temporal_offsets"] = [offset]
    protocol["measurement_geometry"]["population_aggregation_authorities"][0][
        "participant_set_ids"
    ] = list(participant_sets)
    longitudinal = _families(compile_protocol_capacity(protocol))["longitudinal"]
    assert longitudinal["maximum_within_participant_span"] == 0
    assert longitudinal["maximum_within_participant_distinct_offsets"] == 1
    assert longitudinal["global_calendar_coverage_audit"] == {
        "not_longitudinal_follow_up": True,
        "distinct_offsets": 4,
        "calendar_span": 365.0,
    }
    assert all(row["within_participant_span"] == 0 for row in longitudinal["trajectory_ledger"])


def test_trajectory_dependence_model_cannot_be_split_or_reused() -> None:
    split = _protocol("split-dependence-model")
    split["measurement_geometry"]["participant_event_schedules"][1]["trajectory_dependence_id"] = (
        "different-model-for-same-people"
    )
    with pytest.raises(ProtocolCapacityError, match="split across trajectory dependence models"):
        compile_protocol_capacity(split)

    reused = _protocol("reused-dependence-model")
    reused["measurement_geometry"]["participant_event_schedules"][2]["trajectory_dependence_id"] = (
        "dependence-all-participants"
    )
    with pytest.raises(ProtocolCapacityError, match="reused across participant sets"):
        compile_protocol_capacity(reused)


def test_trajectory_receipt_binds_dependence_model_and_upper_bound_semantics() -> None:
    longitudinal = _families(compile_protocol_capacity(_protocol("dependence-receipt")))[
        "longitudinal"
    ]
    all_people = next(
        row
        for row in longitudinal["trajectory_ledger"]
        if row["participant_set_id"] == "all-participants"
    )
    assert all_people["trajectory_dependence_id"] == "dependence-all-participants"
    assert all_people["trajectory_repetition_correlation"] == 0.25
    assert all_people["repetition_model"] == (
        "registered_nested_retained_support_threshold_strata_v1"
    )
    assert set(all_people["selected_joint_observation_bundle_ids"]) <= set(
        all_people["joint_observation_bundle_ids"]
    )


def test_public_api_wrapper_uses_the_protocol_capacity_compiler() -> None:
    expected = compile_protocol_capacity(_protocol("public-api-wrapper"))
    assert compile_protocol_capacity_v2(_protocol("public-api-wrapper")) == expected


def test_protocol_capacity_cli_writes_exact_compiler_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "protocol.json"
    output = tmp_path / "capacity.json"
    source.write_text(json.dumps(_protocol("cli-protocol")), encoding="utf-8")
    assert main(["v2-protocol-capacity", str(source), "--out", str(output), "--pretty"]) == 0
    receipt = json.loads(capsys.readouterr().out)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["protocol_sha256"] == result["protocol_sha256"]
    assert result == compile_protocol_capacity(_protocol("cli-protocol"))


def _post_protocol(payload: dict) -> tuple[int, dict]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/v2/protocol-capacity",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_studio_protocol_capacity_endpoint_executes_and_rejects_invalid_input() -> None:
    status, result = _post_protocol(_protocol("studio-protocol"))
    assert status == 200
    assert result["protocol_id"] == "studio-protocol"
    assert result["overall_scalar"] is None

    invalid = _protocol("invalid-studio-protocol")
    invalid["measurement_geometry"]["participant_event_schedules"] = []
    status, result = _post_protocol(invalid)
    assert status == 400
    assert "participant_event_schedules" in result["error"]


def test_one_person_far_future_schedule_cannot_buy_weighted_longitudinal_span() -> None:
    base = _protocol("weighted-span-base")
    base_longitudinal = _families(compile_protocol_capacity(base))["longitudinal"]
    attacked = _protocol("weighted-span-attack")
    attacked["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-one-person-outlier",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    attacked["measurement_geometry"]["participant_event_schedules"].append(
        {
            **copy.deepcopy(attacked["measurement_geometry"]["participant_event_schedules"][1]),
            "schedule_id": "schedule-one-person-outlier",
            "participant_event_lineage_id": "lineage-one-person-outlier",
            "joint_observation_bundle_id": "bundle-one-person-outlier",
            "participant_count": _exact(1),
            "events_per_participant": _exact(1),
            "retention_fraction": _exact(1),
            "within_person_repetition_correlation": _exact(0),
            "temporal_offsets": [36500],
            "source_locator": "protocol:schedule:one-person-outlier",
        }
    )
    longitudinal = _families(compile_protocol_capacity(attacked))["longitudinal"]
    assert longitudinal["maximum_within_participant_span"] > 36_000
    assert (
        longitudinal["participant_weighted_median_span"]
        == (base_longitudinal["participant_weighted_median_span"])
    )


def test_declared_causal_counts_are_capped_by_linked_retained_outcomes() -> None:
    small_families = _families(compile_protocol_capacity(_protocol("causal-small")))
    large_protocol = _protocol("causal-large")
    stage = large_protocol["causal_geometry"]["assignment_stages"][0]
    stage["participant_count"] = _exact(1_000_000_000)
    stage["decisions_per_participant"] = _exact(1_000_000_000)
    large_families = _families(compile_protocol_capacity(large_protocol))
    assert large_families["causal"]["policy_rank"] == small_families["causal"]["policy_rank"]
    assert (
        large_families["causal"]["policy_allocation_support_factor"]
        == (small_families["causal"]["policy_allocation_support_factor"])
    )
    assert (
        large_families["personalized_sequential"]["sequential_moderator_allocation_support_factor"]
        == small_families["personalized_sequential"][
            "sequential_moderator_allocation_support_factor"
        ]
    )
    assert large_families["causal"]["eligible_randomized_participants"] == 90
    assert large_families["causal"]["eligible_randomized_participant_decisions"] == 270


def test_transport_rank_requires_measured_context_coordinates_not_context_menu_size() -> None:
    protocol = _protocol("transport-coordinate-guard")
    for context in protocol["causal_geometry"]["transport_geometry"]["contexts"]:
        context["transport_coordinates"] = [{"transport_axis_id": "site-context", "value": 0.0}]
    transport = _families(compile_protocol_capacity(protocol))["transport"]
    assert transport["transport_rank"] == 0
    assert transport["transport_allocation_support_factor"] == 0
    assert transport["gates"]["T_transport"] is False


def test_unknown_observer_preserves_unresolved_causal_personalized_and_transport_credit() -> None:
    protocol = _protocol("unknown-observer-causal-guard")
    protocol["measurement_geometry"]["signals"][0]["evidence_state"] = "unknown"
    families = _families(compile_protocol_capacity(protocol))
    assert families["causal"]["resolution_state"] == "unresolved_no_known_candidate"
    assert families["causal"]["unresolved_alternative_stage_ids"] == ["baseline-randomization"]
    assert families["causal"]["policy_rank"] is None
    assert families["causal"]["component_rank"] is None
    assert families["causal"]["gates"] == {"D_dynamic_operator": None}
    assert families["personalized_sequential"]["sequential_moderator_rank"] is None
    assert families["personalized_sequential"]["resolution_state"] == (
        "unresolved_no_known_candidate"
    )
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": None,
        "H_heterogeneous_response": None,
    }
    assert families["transport"]["transport_rank"] is None
    assert families["transport"]["resolution_state"] == ("unresolved_no_known_context_subset")
    assert families["transport"]["gates"] == {"T_transport": None}


def test_irrelevant_unknown_cross_covariance_does_not_erase_known_causal_geometry() -> None:
    protocol = _protocol("irrelevant-cross-covariance")
    protocol["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-b",
            "canonical_feature_id": "feature-b",
            "feature_ancestry_id": "ancestry-b",
            "operator_row": [0.0, 1.0],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:signal:b",
        }
    )
    protocol["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-b",
            "signal_ids": ["signal-b"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:b",
        }
    )
    protocol["measurement_geometry"]["measurement_modules"][0]["signal_ids"].append("signal-b")
    protocol["measurement_geometry"]["joint_covariance_authority"] = {
        "state": "unknown",
        "reason": "only the irrelevant feature-a by feature-b cross-covariance is pending",
        "source_object_sha256": SHA,
        "source_locator": "protocol:covariance:cross-block-unknown",
    }
    families = _families(compile_protocol_capacity(protocol))
    assert families["intensive"]["effective_rank"] == 1
    assert families["extensive"]["effective_rank"] == 1
    assert families["intensive"]["resolution_state"] == (
        "partial_known_lower_bound_with_unresolved_observers"
    )
    assert families["causal"]["policy_rank"] == 1
    assert families["causal"]["component_rank"] == 1
    assert families["causal"]["gates"] == {"D_dynamic_operator": True}
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": True,
        "H_heterogeneous_response": True,
    }


def test_unknown_future_observer_preserves_known_measurement_lower_bound() -> None:
    base = _families(compile_protocol_capacity(_protocol("known-measurement-lower-bound")))
    protocol = _protocol("unknown-future-observer")
    protocol["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-future",
            "canonical_feature_id": "feature-future",
            "feature_ancestry_id": "ancestry-future",
            "operator_row": [0.0, 1.0],
            "evidence_state": "unknown",
            "source_object_sha256": SHA,
            "source_locator": "protocol:future-observer:unknown",
        }
    )
    protocol["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-future",
            "signal_ids": ["signal-future"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:future-observer:covariance",
        }
    )
    protocol["measurement_geometry"]["measurement_modules"][0]["signal_ids"].append("signal-future")
    protocol["measurement_geometry"]["joint_covariance_authority"] = {
        "state": "unknown",
        "reason": "future observer and its cross-covariance are not yet resolved",
        "source_object_sha256": SHA,
        "source_locator": "protocol:future-observer:joint-covariance",
    }
    families = _families(compile_protocol_capacity(protocol))
    assert families["intensive"]["effective_rank"] == base["intensive"]["effective_rank"]
    assert (
        families["intensive"]["maximum_joint_bundle_log10_contraction"]
        == base["intensive"]["maximum_joint_bundle_log10_contraction"]
    )
    assert (
        families["extensive"]["retained_log10_contraction"]
        == base["extensive"]["retained_log10_contraction"]
    )
    assert families["intensive"]["resolution_state"] == (
        "partial_known_lower_bound_with_unresolved_observers"
    )


def test_second_jointly_measured_estimand_cannot_erase_existing_causal_information() -> None:
    protocol = _protocol("joint-outcome-estimands")
    protocol["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-b",
            "canonical_feature_id": "feature-b",
            "feature_ancestry_id": "ancestry-b",
            "operator_row": [0.0, 1.0],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:signal:b",
        }
    )
    protocol["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-b",
            "signal_ids": ["signal-b"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:b",
        }
    )
    _set_complete_joint_covariance(
        protocol,
        ["signal-a", "signal-b"],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    protocol["measurement_geometry"]["measurement_modules"][0]["signal_ids"].append("signal-b")
    second_estimand = copy.deepcopy(protocol["causal_geometry"]["estimands"][0])
    second_estimand.update(
        {
            "estimand_id": "proximal-feature-b",
            "outcome_definition_id": "feature-b-level",
            "outcome_feature_ids": ["feature-b"],
            "source_locator": "protocol:estimand:proximal-feature-b",
        }
    )
    protocol["causal_geometry"]["estimands"].append(second_estimand)
    for epoch in protocol["causal_geometry"]["assignment_stages"][0]["decision_epochs"]:
        epoch["proximal_outcome_links"].append(
            {"schedule_id": "schedule-a", "estimand_id": "proximal-feature-b"}
        )
    families = _families(compile_protocol_capacity(protocol))
    assert families["causal"]["gates"] == {"D_dynamic_operator": True}
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": True,
        "H_heterogeneous_response": True,
    }


def test_personalization_requires_a_state_dependent_decision_rule() -> None:
    protocol = _protocol("fixed-rule-not-personalized")
    protocol["causal_geometry"]["decision_rule_operators"][0] = {
        "decision_rule_operator_id": "state-adaptive-assignment-rule",
        "state": "static",
        "policy_ids": ["control", "active"],
        "reason": "fixed randomized assignment independent of measured state",
        "source_object_sha256": SHA,
        "source_locator": "protocol:decision-rule:static",
    }
    personalized = _families(compile_protocol_capacity(protocol))["personalized_sequential"]
    # Repeated micro-randomized decisions pool one proximal moderation
    # estimand even though a static rule blocks the personalized-policy gate.
    assert personalized["sequential_moderator_rank"] == 1
    assert personalized["gates"]["H_heterogeneous_response"] is True
    assert personalized["gates"]["P_personalized_policy"] is False


def test_mrt_personalization_requires_bounded_executable_state_propensities() -> None:
    positive = protocol_capacity_module._bounded_state_conditioned_propensities(
        baseline_propensities={"control": 0.5, "active": 0.5},
        ordered_policy_ids=("control", "active"),
        state_to_policy_contrast_matrix=protocol_capacity_module.np.asarray([[-1.0], [1.0]]),
        state_values=protocol_capacity_module.np.asarray([1_000_000.0]),
        conditional_probability_shift=0.0625,
    )
    negative = protocol_capacity_module._bounded_state_conditioned_propensities(
        baseline_propensities={"control": 0.5, "active": 0.5},
        ordered_policy_ids=("control", "active"),
        state_to_policy_contrast_matrix=protocol_capacity_module.np.asarray([[-1.0], [1.0]]),
        state_values=protocol_capacity_module.np.asarray([-1_000_000.0]),
        conditional_probability_shift=0.0625,
    )
    assert sum(positive.values()) == pytest.approx(1.0)
    assert sum(negative.values()) == pytest.approx(1.0)
    assert 0.0 < positive["control"] < 0.5 < positive["active"] < 1.0
    assert 0.0 < negative["active"] < 0.5 < negative["control"] < 1.0

    missing_rule = _protocol("mrt-state-contrast-without-propensity-rule")
    decision_rule = missing_rule["causal_geometry"]["decision_rule_operators"][0]
    for field in (
        "response_state_score_axis_ids",
        "response_state_score_matrix",
        "policy_interaction_basis_matrix",
        "conditional_probability_shift",
    ):
        decision_rule.pop(field)
    missing_personalized = _families(compile_protocol_capacity(missing_rule))[
        "personalized_sequential"
    ]
    assert missing_personalized["gates"]["P_personalized_policy"] is False
    assert missing_personalized["gates"]["H_heterogeneous_response"] is True

    invalid_bound = _protocol("mrt-state-propensity-shift-breaks-positivity")
    invalid_bound["causal_geometry"]["decision_rule_operators"][0][
        "conditional_probability_shift"
    ] = 0.5
    with pytest.raises(
        ProtocolCapacityError,
        match="smaller than every baseline policy propensity",
    ):
        compile_protocol_capacity(invalid_bound)


def test_retained_participant_lineage_cannot_cross_parent_sets() -> None:
    protocol = _protocol("cross-parent-retained-lineage-reuse")
    site_b = next(
        row
        for row in protocol["measurement_geometry"]["participant_event_schedules"]
        if row["participant_set_id"] == "site-b-participants"
    )
    site_b["retention_overlap_authority"]["retained_participant_set_id"] = (
        "retained-site-a-participants"
    )
    with pytest.raises(
        ProtocolCapacityError,
        match="retained participant-set lineage cannot be reused across parent",
    ):
        compile_protocol_capacity(protocol)


def test_participant_event_lineage_conflict_fails_closed() -> None:
    protocol = _protocol("lineage-conflict")
    duplicate = copy.deepcopy(protocol["measurement_geometry"]["participant_event_schedules"][1])
    duplicate["schedule_id"] = "schedule-lineage-conflict"
    duplicate["joint_observation_bundle_id"] = "bundle-lineage-conflict"
    duplicate["retention_fraction"] = _exact(0.899999)
    protocol["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-lineage-conflict",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    protocol["measurement_geometry"]["participant_event_schedules"].append(duplicate)
    with pytest.raises(ProtocolCapacityError, match="participant-event lineage"):
        compile_protocol_capacity(protocol)


def test_transport_declared_counts_are_capped_by_linked_retained_outcomes() -> None:
    base = _families(compile_protocol_capacity(_protocol("transport-cap-base")))["transport"]
    attacked = _protocol("transport-cap-attack")
    for context in attacked["causal_geometry"]["transport_geometry"]["contexts"]:
        context["participant_count"] = _exact(1_000_000_000)
    transport = _families(compile_protocol_capacity(attacked))["transport"]
    assert transport["transport_rank"] == base["transport_rank"]
    assert (
        transport["transport_allocation_support_factor"]
        == base["transport_allocation_support_factor"]
    )
    assert {
        row["eligible_transport_participant_support"]
        for row in transport["transport_ledger"]["context_support_ledger"]
    } == {45.0}


@pytest.mark.parametrize("mechanism", ["cluster_randomized", "crossover_randomized"])
def test_dependent_randomization_requires_explicit_dependence_geometry(mechanism: str) -> None:
    protocol = _protocol(f"unsupported-{mechanism}")
    protocol["causal_geometry"]["assignment_stages"][0]["assignment_mechanism"] = mechanism
    for context in protocol["causal_geometry"]["transport_geometry"]["contexts"]:
        context["assignment_mechanism"] = mechanism
    families = _families(compile_protocol_capacity(protocol))
    assert families["causal"]["policy_rank"] == 0
    assert families["causal"]["gates"] == {"D_dynamic_operator": False}
    assert families["transport"]["transport_rank"] == 0
    assert all(row["dependence_geometry_required"] for row in families["causal"]["stage_ledger"])


def test_realized_geometry_uses_same_capacity_math_without_maturity_bonus() -> None:
    prospective = _protocol("prospective-geometry")
    realized = copy.deepcopy(prospective)
    realized["protocol_id"] = "realized-geometry"
    realized["claim_class"] = "realized_dataset_geometry_capacity"
    proposed_result = compile_protocol_capacity(prospective)
    realized_result = compile_protocol_capacity(realized)
    assert realized_result["claim_class"] == "realized_dataset_geometry_capacity"
    assert realized_result["empirical_attainment"] is False
    assert realized_result["scenarios"][0]["families"] == (
        proposed_result["scenarios"][0]["families"]
    )


def test_rate_process_without_window_and_rate_model_is_rejected() -> None:
    protocol = _protocol("unsupported-rate-process")
    protocol["measurement_geometry"]["participant_event_schedules"][0]["schedule_semantics"] = (
        "rate_process"
    )
    with pytest.raises(ProtocolCapacityError, match="exact_offsets"):
        compile_protocol_capacity(protocol)


def test_family_summary_values_come_from_one_coherent_stage_class() -> None:
    families = _families(compile_protocol_capacity(_protocol("coherent-stage-summary")))
    causal = families["causal"]
    selected = [
        row for row in causal["stage_ledger"] if row["stage_id"] in causal["selected_stage_ids"]
    ]
    assert selected
    assert len({row["assignment_mechanism"] for row in selected}) == 1
    assert len({tuple(row["canonical_policy_ids"]) for row in selected}) == 1
    for metric in (
        "policy_rank",
        "component_rank",
    ):
        assert causal[metric] == selected[0][metric]
    assert causal["policy_allocation_support_factor"] == sum(
        row["policy_allocation_support_factor"] for row in selected
    )
    assert causal["component_allocation_support_factor"] == sum(
        row["component_allocation_support_factor"] for row in selected
    )
    assert causal["eligible_randomized_participants"] == sum(
        row["randomized_participants"] for row in selected
    )


def test_distinct_outcome_geometries_cannot_be_summed_as_one_stage_class() -> None:
    protocol = _protocol("distinct-outcome-stage-classes")
    alternate_schedule = copy.deepcopy(
        protocol["measurement_geometry"]["participant_event_schedules"][1]
    )
    alternate_schedule.update(
        {
            "schedule_id": "schedule-alternate-outcome",
            "participant_event_lineage_id": "lineage-alternate-outcome",
            "joint_observation_bundle_id": "bundle-alternate-outcome",
            "events_per_participant": _exact(3),
            "temporal_offsets": [5, 35, 65],
            "source_locator": "protocol:schedule:alternate-outcome",
        }
    )
    protocol["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-alternate-outcome",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    protocol["measurement_geometry"]["participant_event_schedules"].append(alternate_schedule)
    alternate_stage = copy.deepcopy(protocol["causal_geometry"]["assignment_stages"][0])
    alternate_stage.update(
        {
            "stage_id": "alternate-outcome-randomization",
            "linked_outcome_schedule_ids": ["schedule-alternate-outcome"],
            "source_locator": "protocol:assignment:alternate-outcome",
        }
    )
    for epoch in alternate_stage["decision_epochs"]:
        epoch["proximal_outcome_links"] = [
            {
                "schedule_id": "schedule-alternate-outcome",
                "estimand_id": "proximal-feature-a",
            }
        ]
    protocol["causal_geometry"]["assignment_stages"].append(alternate_stage)

    families = _families(compile_protocol_capacity(protocol))
    causal = families["causal"]
    personalized = families["personalized_sequential"]
    assert len(causal["selected_stage_ids"]) == 1
    assert causal["eligible_randomized_participants"] == 90.0
    assert causal["eligible_randomized_participant_decisions"] == 270.0
    assert len(personalized["selected_stage_ids"]) == 1
    assert personalized["eligible_randomized_participants"] == 90.0
    assert personalized["eligible_randomized_participant_decisions"] == pytest.approx(270.0)


def test_trajectory_partition_cannot_reset_the_repetition_covariance_model() -> None:
    base = _families(compile_protocol_capacity(_protocol("trajectory-unsplit")))
    split_protocol = _protocol("trajectory-split")
    original = copy.deepcopy(
        split_protocol["measurement_geometry"]["participant_event_schedules"][1]
    )
    first = split_protocol["measurement_geometry"]["participant_event_schedules"][1]
    first["events_per_participant"] = _exact(2)
    first["temporal_offsets"] = [0, 30]
    second = copy.deepcopy(original)
    second.update(
        {
            "schedule_id": "schedule-a-part-two",
            "participant_event_lineage_id": "lineage-a-part-two",
            "joint_observation_bundle_id": "bundle-outcome-part-two",
            "events_per_participant": _exact(2),
            "temporal_offsets": [60, 90],
            "source_locator": "protocol:schedule:lineage-a-part-two",
        }
    )
    split_protocol["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-outcome-part-two",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    split_protocol["measurement_geometry"]["participant_event_schedules"].append(second)
    split_protocol["causal_geometry"]["assignment_stages"][0]["linked_outcome_schedule_ids"] = [
        "schedule-a",
        "schedule-a-part-two",
    ]
    split_epochs = split_protocol["causal_geometry"]["assignment_stages"][0]["decision_epochs"]
    split_epochs[0]["proximal_outcome_links"][0]["schedule_id"] = "schedule-a"
    for epoch in split_epochs[1:]:
        epoch["proximal_outcome_links"][0]["schedule_id"] = "schedule-a-part-two"

    split = _families(compile_protocol_capacity(split_protocol))
    assert (
        split["extensive"]["retained_log10_contraction"]
        == base["extensive"]["retained_log10_contraction"]
    )
    base_trajectory = next(
        row
        for row in base["longitudinal"]["trajectory_ledger"]
        if row["participant_set_id"] == "all-participants"
    )
    split_trajectory = next(
        row
        for row in split["longitudinal"]["trajectory_ledger"]
        if row["participant_set_id"] == "all-participants"
    )
    assert (
        split_trajectory["trajectory_effective_information_count"]
        == (base_trajectory["trajectory_effective_information_count"])
    )
    assert split_trajectory["repetition_model"] == (
        "registered_nested_retained_support_threshold_strata_v1"
    )
    assert (
        split["causal"]["eligible_randomized_participant_decisions"]
        == base["causal"]["eligible_randomized_participant_decisions"]
    )


def test_moderator_rank_requires_population_and_assay_operator_geometry() -> None:
    protocol = _protocol("collinear-moderator-ids")
    protocol["measurement_geometry"]["signals"].append(
        {
            "signal_id": "signal-collinear",
            "canonical_feature_id": "feature-collinear",
            "feature_ancestry_id": "ancestry-collinear",
            "operator_row": [2.0, 0.0],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:signal:collinear",
        }
    )
    protocol["measurement_geometry"]["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-collinear",
            "signal_ids": ["signal-collinear"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:within-collinear",
        }
    )
    _set_complete_joint_covariance(
        protocol,
        ["signal-a", "signal-collinear"],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    protocol["measurement_geometry"]["measurement_modules"][0]["signal_ids"].append(
        "signal-collinear"
    )
    protocol["causal_geometry"]["assignment_stages"][0]["moderator_feature_ids"].append(
        "feature-collinear"
    )
    stage = protocol["causal_geometry"]["assignment_stages"][0]
    for epoch in stage["decision_epochs"]:
        epoch["history_moderator_feature_ids"].append("feature-collinear")
    for row in stage["moderator_population_geometry"]["epoch_covariances"]:
        row["moderator_feature_ids"].append("feature-collinear")
        row["population_covariance"] = [[1.0, 1.0], [1.0, 1.0]]

    personalized = _families(compile_protocol_capacity(protocol))["personalized_sequential"]
    # A population covariance cannot manufacture two biologically observed
    # moderator directions from collinear assay operators.
    assert personalized["sequential_moderator_rank"] == 0
    assert personalized["gates"]["P_personalized_policy"] is False


def test_only_strictly_postdecision_events_support_causal_counts() -> None:
    families = _families(compile_protocol_capacity(_protocol("postdecision-count")))
    stage = families["causal"]["stage_ledger"][0]
    assert stage["strictly_postdecision_outcome_offset_count"] == 3
    assert stage["linked_outcome_retained_participant_events"] == 270.0
    assert families["causal"]["eligible_randomized_participant_decisions"] == 270.0

    same_time = _protocol("same-time-is-not-an-outcome")
    schedule = same_time["measurement_geometry"]["participant_event_schedules"][1]
    schedule["events_per_participant"] = _exact(1)
    schedule["temporal_offsets"] = [0]
    causal = _families(compile_protocol_capacity(same_time))["causal"]
    assert causal["policy_rank"] == 0
    assert causal["gates"]["D_dynamic_operator"] is False


def test_same_participant_support_stages_are_never_added_without_dependence_geometry() -> None:
    protocol = _protocol("same-support-stage-attack")
    second = copy.deepcopy(protocol["causal_geometry"]["assignment_stages"][0])
    second.update(
        {
            "stage_id": "same-support-second-stage",
            "sequential_assignment_probability": 0.25,
            "source_locator": "protocol:assignment:same-support-second",
        }
    )
    protocol["causal_geometry"]["assignment_stages"].append(second)
    families = _families(compile_protocol_capacity(protocol))
    assert len(families["causal"]["stage_ledger"]) == 2
    assert len(families["causal"]["selected_stage_ids"]) == 1
    assert families["causal"]["eligible_randomized_participants"] == 90.0
    assert families["causal"]["eligible_randomized_participant_decisions"] == 270.0
    assert len(families["personalized_sequential"]["selected_stage_ids"]) == 1


def test_personalization_precision_is_capped_by_actual_allocation_geometry() -> None:
    balanced = _families(compile_protocol_capacity(_protocol("personalization-balanced")))[
        "personalized_sequential"
    ]
    skewed_protocol = _protocol("personalization-skewed")
    stage = skewed_protocol["causal_geometry"]["assignment_stages"][0]
    stage["policy_allocations"] = [
        {"policy_id": "control", "probability": 0.99},
        {"policy_id": "active", "probability": 0.01},
    ]
    for epoch in stage["decision_epochs"]:
        epoch["policy_propensities"] = [
            {"policy_id": "control", "probability": 0.99},
            {"policy_id": "active", "probability": 0.01},
        ]
    # A flattering caller-provided 0.5 cannot override the 0.01/0.99 design.
    stage["sequential_assignment_probability"] = 0.5
    skewed_protocol["causal_geometry"]["decision_rule_operators"][0][
        "conditional_probability_shift"
    ] = 0.005
    skewed = _families(compile_protocol_capacity(skewed_protocol))["personalized_sequential"]
    assert skewed["sequential_moderator_rank"] == balanced["sequential_moderator_rank"]
    assert (
        skewed["sequential_moderator_allocation_support_factor"]
        < balanced["sequential_moderator_allocation_support_factor"]
    )
    ledger = skewed["stage_ledger"][0]
    assert ledger["allocation_assignment_variance_bound"] == pytest.approx(0.0099)
    assert ledger["declared_assignment_variance_bound"] == 0.25
    assert ledger["effective_assignment_variance_bound"] == pytest.approx(0.0099)


def test_transport_requires_postassignment_outcomes_and_uses_allocation_precision() -> None:
    balanced = _families(compile_protocol_capacity(_protocol("transport-balanced")))["transport"]
    skewed_protocol = _protocol("transport-skewed")
    for context in skewed_protocol["causal_geometry"]["transport_geometry"]["contexts"]:
        context["policy_allocations"] = [
            {"policy_id": "control", "probability": 0.9},
            {"policy_id": "active", "probability": 0.1},
        ]
    skewed = _families(compile_protocol_capacity(skewed_protocol))["transport"]
    assert skewed["transport_rank"] == balanced["transport_rank"] == 1
    assert (
        skewed["transport_allocation_support_factor"]
        < balanced["transport_allocation_support_factor"]
    )
    assert {
        row["allocation_aware_contrast_precision"]
        for row in balanced["transport_ledger"]["context_support_ledger"]
    } == {11.25}

    same_time = _protocol("transport-same-time")
    for schedule in same_time["measurement_geometry"]["participant_event_schedules"][2:]:
        schedule["events_per_participant"] = _exact(1)
        schedule["temporal_offsets"] = [0]
    transport = _families(compile_protocol_capacity(same_time))["transport"]
    assert transport["transport_rank"] == 0
    assert transport["gates"]["T_transport"] is False


def test_module_schedule_and_bundle_event_units_must_be_compatible() -> None:
    module_mismatch = _protocol("module-unit-mismatch")
    module_mismatch["measurement_geometry"]["measurement_modules"][0]["canonical_event_unit_id"] = (
        "saliva"
    )
    with pytest.raises(ProtocolCapacityError, match="module event units"):
        compile_protocol_capacity(module_mismatch)

    bundle_mismatch = _protocol("bundle-unit-mismatch")
    bundle_mismatch["measurement_geometry"]["joint_observation_bundles"][1][
        "canonical_event_unit_id"
    ] = "saliva"
    with pytest.raises(ProtocolCapacityError, match="incompatible event units"):
        compile_protocol_capacity(bundle_mismatch)


def test_every_numeric_and_temporal_coordinate_rejects_nonfinite_values() -> None:
    attacks = []

    coordinate = _protocol("nonfinite-coordinate")
    coordinate["measurement_geometry"]["participant_event_schedules"][0]["participant_count"] = (
        _exact(float("nan"))
    )
    attacks.append(coordinate)

    temporal = _protocol("nonfinite-temporal")
    temporal["measurement_geometry"]["participant_event_schedules"][0]["temporal_offsets"] = [
        float("inf")
    ]
    attacks.append(temporal)

    decision = _protocol("nonfinite-decision")
    decision["causal_geometry"]["assignment_stages"][0]["decision_time_offset"] = float("nan")
    attacks.append(decision)

    allocation = _protocol("nonfinite-allocation")
    allocation["causal_geometry"]["assignment_stages"][0]["policy_allocations"][0][
        "probability"
    ] = float("nan")
    attacks.append(allocation)

    covariance = _protocol("nonfinite-covariance")
    covariance["measurement_geometry"]["covariance_groups"][0]["covariance"] = [[float("inf")]]
    attacks.append(covariance)

    prior = _protocol("nonfinite-prior")
    prior["parameter_space"]["prior_precision"][0][0] = float("nan")
    attacks.append(prior)

    transport_time = _protocol("nonfinite-transport-time")
    transport_time["causal_geometry"]["transport_geometry"]["contexts"][0][
        "assignment_time_offset"
    ] = float("inf")
    attacks.append(transport_time)

    for attacked in attacks:
        with pytest.raises(ProtocolCapacityError):
            compile_protocol_capacity(attacked)


def test_hostile_declared_decision_count_cannot_manufacture_personalization() -> None:
    protocol = _protocol("hostile-one-real-epoch")
    stage = protocol["causal_geometry"]["assignment_stages"][0]
    stage["decisions_per_participant"] = _exact(1_000_000)
    stage["decision_epochs"] = stage["decision_epochs"][:1]
    stage["moderator_population_geometry"]["epoch_covariances"] = stage[
        "moderator_population_geometry"
    ]["epoch_covariances"][:1]
    _sync_conditional_eligibility_authority(stage)
    personalized = _families(compile_protocol_capacity(protocol))["personalized_sequential"]
    assert personalized["gates"]["P_personalized_policy"] is False
    assert personalized["eligible_randomized_participant_decisions"] == pytest.approx(90.0)


def test_hostile_single_assignment_mechanism_cannot_claim_repeated_randomization() -> None:
    protocol = _protocol("single-assignment-repetition-attack")
    protocol["causal_geometry"]["assignment_stages"][0]["assignment_mechanism"] = (
        "simple_randomized"
    )
    with pytest.raises(
        ProtocolCapacityError,
        match="single-assignment randomized mechanism requires exactly one decision epoch",
    ):
        compile_protocol_capacity(protocol)


def test_hostile_marginal_availability_and_retention_use_frechet_lower_overlap() -> None:
    protocol = _protocol("marginal-overlap-attack")
    for epoch in protocol["causal_geometry"]["assignment_stages"][0]["decision_epochs"]:
        epoch["availability_probability"] = 0.5
    protocol["measurement_geometry"]["participant_event_schedules"][1]["retention_fraction"] = (
        _exact(0.5)
    )
    _sync_conditional_eligibility_authority(
        protocol["causal_geometry"]["assignment_stages"][0], retention=0.5
    )
    families = _families(compile_protocol_capacity(protocol))
    assert families["causal"]["eligible_randomized_participant_decisions"] == 0.0
    assert families["causal"]["gates"] == {"D_dynamic_operator": False}
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": False,
        "H_heterogeneous_response": False,
    }


def test_hostile_unknown_joint_covariance_only_nulls_families_that_require_it() -> None:
    protocol = _protocol("hostile-unknown-cross-block")
    protocol["measurement_geometry"]["joint_covariance_authority"] = {
        "state": "unknown",
        "reason": "cross-block dependence has not been measured",
        "source_object_sha256": SHA,
        "source_locator": "protocol:covariance:unknown",
    }
    result = compile_protocol_capacity(protocol)
    families = _families(result)
    assert families["intensive"]["effective_rank"] == 1
    assert families["extensive"]["effective_rank"] == 1
    assert families["causal"]["policy_rank"] == 1
    assert families["causal"]["gates"] == {"D_dynamic_operator": True}
    assert result["family_envelopes"]["intensive.effective_rank"] == {
        "minimum": 1,
        "maximum": 1,
    }


def test_hostile_adding_a_valid_low_support_bundle_cannot_reduce_extensive_capacity() -> None:
    base = _protocol("extensive-monotonic-base")
    before = _families(compile_protocol_capacity(base))["extensive"]
    attacked = copy.deepcopy(base)
    attacked["protocol_id"] = "extensive-monotonic-addition"
    attacked["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-tiny",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    schedule = copy.deepcopy(attacked["measurement_geometry"]["participant_event_schedules"][0])
    schedule.update(
        {
            "schedule_id": "schedule-tiny",
            "participant_event_lineage_id": "lineage-tiny",
            "joint_observation_bundle_id": "bundle-tiny",
            "participant_count": _exact(1),
            "events_per_participant": _exact(1),
            "temporal_offsets": [365],
            "source_locator": "protocol:schedule:tiny-valid-addition",
        }
    )
    attacked["measurement_geometry"]["participant_event_schedules"].append(schedule)
    after = _families(compile_protocol_capacity(attacked))["extensive"]
    assert after["retained_participant_events"] > before["retained_participant_events"]
    assert after["retained_log10_contraction"] >= before["retained_log10_contraction"]


def test_hostile_deep_optional_observer_menu_has_no_arbitrary_bundle_cap() -> None:
    protocol = _protocol("deep-optional-observer-menu")
    before = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["extensive"]
    template = protocol["measurement_geometry"]["participant_event_schedules"][0]
    for index in range(20):
        bundle_id = f"bundle-optional-{index:02d}"
        protocol["measurement_geometry"]["joint_observation_bundles"].append(
            {
                "joint_observation_bundle_id": bundle_id,
                "canonical_event_unit_id": "blood-draw",
            }
        )
        schedule = copy.deepcopy(template)
        schedule.update(
            {
                "schedule_id": f"schedule-optional-{index:02d}",
                "participant_event_lineage_id": f"lineage-optional-{index:02d}",
                "joint_observation_bundle_id": bundle_id,
                "events_per_participant": _exact(1),
                "temporal_offsets": [1000 + index],
                "source_locator": f"protocol:schedule:optional-{index:02d}",
            }
        )
        protocol["measurement_geometry"]["participant_event_schedules"].append(schedule)

    started = time.perf_counter()
    result = compile_protocol_capacity(protocol)
    elapsed = time.perf_counter() - started
    families = _families(result)
    extensive = families["extensive"]
    trajectory_ledger = families["longitudinal"]["trajectory_ledger"]
    assert extensive["retained_log10_contraction"] >= before["retained_log10_contraction"]
    assert elapsed < 2.0
    assert max(row["optional_subset_candidate_count"] for row in trajectory_ledger) == 1
    assert all(
        row["repetition_model"] == "registered_nested_retained_support_threshold_strata_v1"
        for row in trajectory_ledger
    )
    assert extensive["complexity_receipt"]["subset_enumeration_performed"] is False
    assert extensive["complexity_receipt"]["psd_frontier_enumeration_performed"] is False
    assert extensive["complexity_receipt"]["numeric_frontier_cap"] is None


@pytest.mark.parametrize(
    ("bundle_count", "runtime_limit_seconds"),
    [(64, 3.0), (128, 6.0)],
)
def test_registered_nested_direction_menu_runtime_is_polynomial(
    bundle_count: int, runtime_limit_seconds: float
) -> None:
    protocol = _nested_direction_menu_protocol(
        f"nested-direction-menu-{bundle_count}", bundle_count
    )
    started = time.perf_counter()
    families = _families(compile_protocol_capacity(protocol))
    elapsed = time.perf_counter() - started
    extensive = families["extensive"]
    receipt = extensive["complexity_receipt"]
    assert elapsed < runtime_limit_seconds
    assert extensive["effective_rank"] == 2
    assert receipt["subset_enumeration_performed"] is False
    assert receipt["psd_frontier_enumeration_performed"] is False
    assert receipt["numeric_frontier_cap"] is None
    assert receipt["registered_nested_bundle_count"] == bundle_count + 4
    assert receipt["candidate_count"] == 3
    assert receipt["asymptotic_time"] == "O(B log B + B d^2 + P d^2)"


def test_registered_nested_threshold_strata_matches_explicit_person_expansion() -> None:
    protocol = _protocol("nested-threshold-exhaustive-equality")
    baseline, outcome = protocol["measurement_geometry"]["participant_event_schedules"][:2]
    baseline["participant_count"] = _exact(5)
    baseline["retention_fraction"] = _exact(1)
    outcome["participant_count"] = _exact(5)
    outcome["retention_fraction"] = _exact(0.6)

    families = _families(compile_protocol_capacity(protocol))
    all_people = next(
        row
        for row in families["longitudinal"]["trajectory_ledger"]
        if row["participant_set_id"] == "all-participants"
    )
    expanded = 0.0
    for person_index in range(5):
        if person_index < 3:
            events = 5.0
            correlation = 0.25
        else:
            events = 1.0
            correlation = 0.0
        expanded += events / (1.0 + (events - 1.0) * correlation)
    assert expanded == 9.5
    assert all_people["trajectory_effective_information_count"] == expanded
    assert all_people["support_thresholds"] == [5.0, 3.0]
    assert all_people["extensive_complexity_receipt"] == {
        "algorithm": "registered_nested_retained_support_threshold_strata_v1",
        "bundle_count": 2,
        "support_threshold_stratum_count": 2,
        "matrix_accumulation_count": 4,
        "peak_live_information_matrix_count": 3,
        "parameter_dimension": 2,
        "asymptotic_time": "O(B log B + B d^2)",
        "asymptotic_space": "O(B + d^2)",
    }


def test_unresolved_overlap_requires_source_bound_primary_and_is_id_invariant() -> None:
    protocol = _protocol("unresolved-overlap-primary-required")
    for schedule in protocol["measurement_geometry"]["participant_event_schedules"][:2]:
        schedule["retention_overlap_authority"] = {
            "state": "unknown",
            "reason": "pairwise retained overlap is not registered",
            "source_object_sha256": SHA,
            "source_locator": "protocol:retention-overlap:unknown",
        }
    with pytest.raises(ProtocolCapacityError, match="primary_extensive_bundle_id"):
        compile_protocol_capacity(protocol)

    protocol["measurement_geometry"]["extensive_selection_authorities"] = [
        {
            "participant_set_id": "all-participants",
            "state": "registered_primary_extensive_bundle",
            "primary_extensive_bundle_id": "bundle-outcome",
            "source_object_sha256": SHA,
            "source_locator": "protocol:extensive-primary:outcome",
        }
    ]
    selected = _families(compile_protocol_capacity(protocol))
    selected_extensive = selected["extensive"]
    selected_trajectory = next(
        row
        for row in selected["longitudinal"]["trajectory_ledger"]
        if row["participant_set_id"] == "all-participants"
    )
    assert selected_trajectory["extensive_selection_state"] == (
        "source_bound_primary_extensive_bundle"
    )
    assert selected_trajectory["extensive_selected_joint_observation_bundle_ids"] == [
        "bundle-outcome"
    ]
    assert selected_trajectory["ledger_only_joint_observation_bundle_ids"] == ["bundle-moderator"]

    renamed = copy.deepcopy(protocol)
    renamed["protocol_id"] = "unresolved-overlap-primary-renamed"
    rename_map = {
        "bundle-moderator": "bundle-z-renamed",
        "bundle-outcome": "bundle-a-renamed",
    }
    for bundle in renamed["measurement_geometry"]["joint_observation_bundles"]:
        bundle["joint_observation_bundle_id"] = rename_map.get(
            bundle["joint_observation_bundle_id"], bundle["joint_observation_bundle_id"]
        )
    for schedule in renamed["measurement_geometry"]["participant_event_schedules"]:
        schedule["joint_observation_bundle_id"] = rename_map.get(
            schedule["joint_observation_bundle_id"], schedule["joint_observation_bundle_id"]
        )
    renamed["measurement_geometry"]["extensive_selection_authorities"][0][
        "primary_extensive_bundle_id"
    ] = "bundle-a-renamed"
    renamed_extensive = _families(compile_protocol_capacity(renamed))["extensive"]
    for field in (
        "retained_participant_events",
        "effective_rank",
        "retained_log10_contraction",
        "information_matrix_sha256",
        "posterior_direction_information",
    ):
        assert renamed_extensive[field] == selected_extensive[field]


def test_cross_population_extensive_sum_requires_exact_disjoint_authority() -> None:
    protocol = _protocol("population-aggregation-authority-required")
    protocol["measurement_geometry"].pop("population_aggregation_authorities")
    with pytest.raises(ProtocolCapacityError, match="remains separate"):
        compile_protocol_capacity(protocol)

    protocol["measurement_geometry"]["population_aggregation_authorities"] = [
        {
            "aggregation_authority_id": "incomplete-disjoint-authority",
            "participant_set_ids": ["site-a-participants", "site-b-participants"],
            "aggregation_rule": "sum_information_across_disjoint_participant_sets",
            "participant_relation": "mutually_disjoint_participant_sets",
            "source_object_sha256": SHA,
            "source_locator": "protocol:population-aggregation:incomplete",
        }
    ]
    with pytest.raises(ProtocolCapacityError, match="remains separate"):
        compile_protocol_capacity(protocol)


def test_weak_new_direction_is_monotone_and_cannot_erase_existing_direction() -> None:
    base = _families(compile_protocol_capacity(_protocol("shallow-direction-base")))["extensive"]
    protocol = _protocol("shallow-direction-addition")
    geometry = protocol["measurement_geometry"]
    geometry["signals"].append(
        {
            "signal_id": "signal-weak-orthogonal",
            "canonical_feature_id": "feature-weak-orthogonal",
            "feature_ancestry_id": "ancestry-weak-orthogonal",
            "operator_row": [0.0, 1e-6],
            "evidence_state": "protocol_committed",
            "source_object_sha256": SHA,
            "source_locator": "protocol:signal:weak-orthogonal",
        }
    )
    geometry["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-weak-orthogonal",
            "signal_ids": ["signal-weak-orthogonal"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "protocol:covariance:weak-orthogonal",
        }
    )
    _set_complete_joint_covariance(
        protocol,
        ["signal-a", "signal-weak-orthogonal"],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    geometry["measurement_modules"].append(
        {
            "module_id": "module-weak-orthogonal",
            "canonical_event_unit_id": "blood-draw",
            "signal_ids": ["signal-weak-orthogonal"],
            "evidence_state": "protocol_committed",
        }
    )
    geometry["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-weak-orthogonal",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    schedule = copy.deepcopy(geometry["participant_event_schedules"][0])
    schedule.update(
        {
            "schedule_id": "schedule-weak-orthogonal",
            "participant_event_lineage_id": "lineage-weak-orthogonal",
            "joint_observation_bundle_id": "bundle-weak-orthogonal",
            "measurement_module_ids": ["module-weak-orthogonal"],
            "participant_count": _exact(100),
            "events_per_participant": _exact(1),
            "retention_fraction": _exact(0.01),
            "within_person_repetition_correlation": _exact(0),
            "temporal_offsets": [999],
            "source_locator": "protocol:schedule:weak-orthogonal",
        }
    )
    geometry["participant_event_schedules"].append(schedule)
    enlarged = _families(compile_protocol_capacity(protocol))["extensive"]
    assert (
        enlarged["posterior_direction_information"][0]
        >= (base["posterior_direction_information"][0])
    )
    assert enlarged["posterior_direction_information"][1] > 0
    assert enlarged["retained_log10_contraction"] > base["retained_log10_contraction"]


def test_hostile_moderator_information_uses_population_not_assay_operator_geometry() -> None:
    base = _protocol("hostile-population-basis-a")
    rescaled = copy.deepcopy(base)
    rescaled["protocol_id"] = "hostile-population-basis-b"
    rescaled["measurement_geometry"]["signals"][0]["operator_row"] = [1000.0, 0.0]
    base_value = _families(compile_protocol_capacity(base))["personalized_sequential"][
        "sequential_moderator_allocation_support_factor"
    ]
    rescaled_value = _families(compile_protocol_capacity(rescaled))["personalized_sequential"][
        "sequential_moderator_allocation_support_factor"
    ]
    assert rescaled_value == base_value


def test_hostile_moderator_information_is_invariant_to_equivalent_unit_conversion() -> None:
    base = _protocol("moderator-units-base")
    converted = copy.deepcopy(base)
    converted["protocol_id"] = "moderator-units-converted"
    scale = 1_000_000.0
    converted["measurement_geometry"]["signals"][0]["operator_row"] = [scale, 0.0]
    converted["measurement_geometry"]["covariance_groups"][0]["covariance"] = [[scale**2]]
    converted["measurement_geometry"]["joint_covariance_authority"]["covariance"] = [[scale**2]]
    for row in converted["causal_geometry"]["assignment_stages"][0][
        "moderator_population_geometry"
    ]["epoch_covariances"]:
        row["population_covariance"] = [[scale**2]]
    base_families = _families(compile_protocol_capacity(base))
    converted_families = _families(compile_protocol_capacity(converted))
    assert (
        converted_families["intensive"]["maximum_joint_bundle_log10_contraction"]
        == (base_families["intensive"]["maximum_joint_bundle_log10_contraction"])
    )
    assert (
        converted_families["extensive"]["retained_log10_contraction"]
        == (base_families["extensive"]["retained_log10_contraction"])
    )
    assert (
        converted_families["personalized_sequential"][
            "sequential_moderator_allocation_support_factor"
        ]
        == base_families["personalized_sequential"][
            "sequential_moderator_allocation_support_factor"
        ]
    )


def test_hostile_transport_requires_frozen_estimand_binding_or_crosswalk() -> None:
    protocol = _protocol("hostile-transport-unknown-estimand")
    protocol["causal_geometry"]["transport_geometry"]["contexts"][1]["estimand_binding"] = {
        "state": "unknown",
        "reason": "outcome/operator/horizon crosswalk is not registered",
        "source_object_sha256": SHA,
        "source_locator": "protocol:transport:unknown-crosswalk",
    }
    transport = _families(compile_protocol_capacity(protocol))["transport"]
    assert transport["resolution_state"] == "unresolved_no_known_context_subset"
    assert transport["selected_context_ids"] == []
    assert transport["unresolved_context_ids"] == ["site-b"]
    assert transport["transport_rank"] is None
    assert transport["transport_allocation_support_factor"] is None
    assert transport["gates"]["T_transport"] is None

    crosswalk = _protocol("hostile-arbitrary-crosswalk")
    source_estimand = copy.deepcopy(crosswalk["causal_geometry"]["estimands"][0])
    source_estimand["estimand_id"] = "arbitrary-source-estimand"
    crosswalk["causal_geometry"]["transport_geometry"]["contexts"][1]["estimand_binding"] = {
        "state": "registered_crosswalk",
        "source_estimand": source_estimand,
        "target_estimand_id": "proximal-feature-a",
        "crosswalk_id": "unsupported-arbitrary-crosswalk",
        "source_object_sha256": SHA,
        "source_locator": "protocol:transport:arbitrary-crosswalk",
    }
    crosswalk_transport = _families(compile_protocol_capacity(crosswalk))["transport"]
    assert crosswalk_transport["resolution_state"] == "unresolved_no_known_context_subset"
    assert crosswalk_transport["unresolved_context_ids"] == ["site-b"]
    assert crosswalk_transport["transport_rank"] is None
    assert crosswalk_transport["gates"]["T_transport"] is None


def test_hostile_transport_precision_is_contrast_by_context_not_arm_menu_size() -> None:
    balanced = _families(compile_protocol_capacity(_protocol("hostile-contrast-balanced")))[
        "transport"
    ]
    skewed_protocol = _protocol("hostile-contrast-skewed")
    for context in skewed_protocol["causal_geometry"]["transport_geometry"]["contexts"]:
        context["policy_allocations"] = [
            {"policy_id": "control", "probability": 0.99},
            {"policy_id": "active", "probability": 0.01},
        ]
    skewed = _families(compile_protocol_capacity(skewed_protocol))["transport"]
    assert skewed["transport_rank"] == balanced["transport_rank"]
    assert (
        skewed["transport_allocation_support_factor"]
        < balanced["transport_allocation_support_factor"]
    )
    assert all(
        row["contrast_by_context_support"]
        for row in skewed["transport_ledger"]["context_support_ledger"]
    )


def test_hostile_smart_requires_registered_paths_and_rank_tolerance_is_receipted() -> None:
    smart = _protocol("hostile-smart-without-paths")
    smart["causal_geometry"]["assignment_stages"][0]["assignment_mechanism"] = "smart_rerandomized"
    with pytest.raises(ProtocolCapacityError, match="registered path geometry"):
        compile_protocol_capacity(smart)

    families = _families(compile_protocol_capacity(_protocol("rank-receipt")))
    assert families["intensive"]["rank_tolerance_receipt"]["relative_tolerance"] == 1e-10
    stage = families["causal"]["stage_ledger"][0]
    assert stage["policy_rank_tolerance_receipt"]["effective_rank"] == stage["policy_rank"]


def test_hostile_operator_sensitivity_continuously_attenuates_information() -> None:
    observed = []
    for scale in (1e-6, 1.0, 1e6):
        protocol = _protocol(f"rank-scale-{scale}")
        protocol["measurement_geometry"]["signals"][0]["operator_row"] = [scale, 0.0]
        families = _families(compile_protocol_capacity(protocol))
        observed.append(
            (
                families["intensive"]["effective_rank"],
                families["causal"]["policy_rank"],
                families["causal"]["component_rank"],
                families["personalized_sequential"]["sequential_moderator_rank"],
                families["personalized_sequential"]["gates"]["P_personalized_policy"],
                families["causal"]["component_allocation_support_factor"],
            )
        )
    assert [row[:5] for row in observed] == [(1, 1, 1, 1, True)] * 3
    assert observed[0][-1] < observed[1][-1]
    assert observed[1][-1] == pytest.approx(observed[2][-1])


def test_zero_information_assay_gets_no_causal_or_personalization_credit() -> None:
    protocol = _protocol("zero-information-assay")
    protocol["measurement_geometry"]["signals"][0]["operator_row"] = [0.0, 0.0]
    families = _families(compile_protocol_capacity(protocol))
    stage = families["causal"]["stage_ledger"][0]
    assert families["intensive"]["effective_rank"] == 0
    assert families["causal"]["policy_rank"] == 0
    assert families["causal"]["component_rank"] == 0
    assert families["causal"]["gates"]["D_dynamic_operator"] is False
    assert families["personalized_sequential"]["sequential_moderator_rank"] == 0
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": False,
        "H_heterogeneous_response": False,
    }
    assert stage["outcome_linked"] is False


def test_hostile_moderator_information_is_capped_by_measured_history_support() -> None:
    base = _families(compile_protocol_capacity(_protocol("moderator-support-100")))[
        "personalized_sequential"
    ]
    attacked = _protocol("moderator-support-1")
    moderator_schedule = next(
        row
        for row in attacked["measurement_geometry"]["participant_event_schedules"]
        if row["schedule_id"] == "schedule-moderator"
    )
    moderator_schedule["participant_count"] = _exact(1)
    reduced = _families(compile_protocol_capacity(attacked))["personalized_sequential"]
    assert reduced["eligible_randomized_participant_decisions"] == pytest.approx(2.7)
    assert base["eligible_randomized_participant_decisions"] == pytest.approx(270)
    assert (
        reduced["sequential_moderator_allocation_support_factor"]
        < base["sequential_moderator_allocation_support_factor"]
    )


def test_shared_retained_lineage_is_intersected_with_availability_exactly_once() -> None:
    protocol = _protocol("shared-retained-lineage-once")
    schedules = {
        row["schedule_id"]: row
        for row in protocol["measurement_geometry"]["participant_event_schedules"]
    }
    schedules["schedule-moderator"]["retention_fraction"] = _exact(0.8)
    schedules["schedule-a"]["retention_fraction"] = _exact(0.8)
    for epoch in protocol["causal_geometry"]["assignment_stages"][0]["decision_epochs"]:
        epoch["availability_probability"] = 0.75
    _sync_conditional_eligibility_authority(
        protocol["causal_geometry"]["assignment_stages"][0], retention=0.8
    )

    result = compile_protocol_capacity(protocol)
    stage = _families(result)["causal"]["stage_ledger"][0]
    for epoch in stage["decision_epoch_ledger"]:
        receipt = epoch["retention_overlap_receipt"]
        assert epoch["eligible_outcome_participant_decision_support"] == 55.0
        assert epoch["eligible_moderator_participant_decision_support"] == pytest.approx(55.0)
        assert receipt["state"] == "resolved_registered_nested"
        assert receipt["model"] == ("shared_registered_nested_lineage_single_frechet")
        assert receipt["outcome_retained_participant_set_ids"] == ["retained-all-participants"]
        assert receipt["history_retained_participant_set_ids"] == ["retained-all-participants"]
        assert receipt["shared_outcome_history_retained_participant_set_ids"] == [
            "retained-all-participants"
        ]
        assert receipt["unique_registered_retained_lineage_count"] == 1
        assert receipt["registered_retained_lineage_supports"] == [
            {
                "retained_participant_set_id": "retained-all-participants",
                "marginal_participant_support": 80.0,
                "schedule_ids": ["schedule-a", "schedule-moderator"],
            }
        ]
        assert receipt["joint_participant_support"] == 55.0

    schema = json.loads(
        (ROOT / "schemas/v2/protocol-capacity-result.schema.json").read_text(encoding="utf-8")
    )
    assert not list(Draft202012Validator(schema).iter_errors(result))


def test_nonshared_retained_lineages_use_generalized_frechet_and_unknown_fails_closed() -> None:
    nonshared = _protocol("nonshared-retained-lineages")
    schedules = {
        row["schedule_id"]: row
        for row in nonshared["measurement_geometry"]["participant_event_schedules"]
    }
    schedules["schedule-moderator"]["retention_fraction"] = _exact(0.8)
    schedules["schedule-moderator"]["retention_overlap_authority"] = {
        "state": "registered_nested",
        "retained_participant_set_id": "retained-history-participants",
        "source_object_sha256": SHA,
        "source_locator": "protocol:retention-overlap:history-participants",
    }
    schedules["schedule-a"]["retention_fraction"] = _exact(0.8)
    nonshared["measurement_geometry"]["extensive_selection_authorities"] = [
        {
            "participant_set_id": "all-participants",
            "state": "registered_primary_extensive_bundle",
            "primary_extensive_bundle_id": "bundle-outcome",
            "source_object_sha256": SHA,
            "source_locator": "protocol:extensive-primary:outcome",
        }
    ]
    for epoch in nonshared["causal_geometry"]["assignment_stages"][0]["decision_epochs"]:
        epoch["availability_probability"] = 0.75
    _sync_conditional_eligibility_authority(
        nonshared["causal_geometry"]["assignment_stages"][0], retention=0.8
    )

    stage = _families(compile_protocol_capacity(nonshared))["causal"]["stage_ledger"][0]
    for epoch in stage["decision_epoch_ledger"]:
        receipt = epoch["retention_overlap_receipt"]
        assert epoch["eligible_outcome_participant_decision_support"] == 55.0
        assert epoch["eligible_moderator_participant_decision_support"] == pytest.approx(55.0)
        assert receipt["state"] == "resolved_registered_nested"
        assert receipt["model"] == ("nonshared_registered_nested_lineages_generalized_frechet")
        assert receipt["unique_registered_retained_lineage_count"] == 2
        assert receipt["shared_outcome_history_retained_participant_set_ids"] == []
        assert receipt["joint_participant_support"] == 35.0

    unknown = copy.deepcopy(nonshared)
    unknown["protocol_id"] = "unknown-retained-history-lineage"
    unknown_schedules = {
        row["schedule_id"]: row
        for row in unknown["measurement_geometry"]["participant_event_schedules"]
    }
    unknown_schedules["schedule-moderator"]["retention_overlap_authority"] = {
        "state": "unknown",
        "reason": "joint complete-case identity is not registered",
        "source_object_sha256": SHA,
        "source_locator": "protocol:retention-overlap:history-unknown",
    }
    unknown_families = _families(compile_protocol_capacity(unknown))
    unknown_stage = unknown_families["causal"]["stage_ledger"][0]
    for epoch in unknown_stage["decision_epoch_ledger"]:
        receipt = epoch["retention_overlap_receipt"]
        assert epoch["eligible_moderator_participant_decision_support"] == pytest.approx(55.0)
        assert receipt["state"] == "blocked_unknown_or_absent_retention_authority"
        assert receipt["model"] == ("fail_closed_unknown_or_absent_retention_authority")
        assert receipt["unresolved_retention_schedule_ids"] == ["schedule-moderator"]
        assert receipt["joint_participant_support"] == 0.0
    assert unknown_families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": True,
        "H_heterogeneous_response": True,
    }


def test_retention_bound_schedule_aliases_preserve_support_and_cannot_change_lineage() -> None:
    base = _protocol("retained-lineage-alias-base")
    for schedule in base["measurement_geometry"]["participant_event_schedules"][:2]:
        schedule["retention_fraction"] = _exact(0.8)
    for epoch in base["causal_geometry"]["assignment_stages"][0]["decision_epochs"]:
        epoch["availability_probability"] = 0.75
    _sync_conditional_eligibility_authority(
        base["causal_geometry"]["assignment_stages"][0], retention=0.8
    )
    attacked = copy.deepcopy(base)
    attacked["protocol_id"] = "retained-lineage-alias-copy"
    moderator = attacked["measurement_geometry"]["participant_event_schedules"][0]
    alias = copy.deepcopy(moderator)
    alias["schedule_id"] = "schedule-moderator-alias"
    alias["participant_event_lineage_id"] = "lineage-moderator-alias"
    alias["source_locator"] = "protocol:schedule:moderator-alias"
    attacked["measurement_geometry"]["participant_event_schedules"].append(alias)
    stage = attacked["causal_geometry"]["assignment_stages"][0]
    stage["moderator_measurement_schedule_ids"].append(alias["schedule_id"])
    for epoch in stage["decision_epochs"]:
        epoch["history_measurement_schedule_ids"].append(alias["schedule_id"])
    _sync_conditional_eligibility_authority(stage, retention=0.8)

    base_epoch = _families(compile_protocol_capacity(base))["causal"]["stage_ledger"][0][
        "decision_epoch_ledger"
    ][0]
    attacked_epoch = _families(compile_protocol_capacity(attacked))["causal"]["stage_ledger"][0][
        "decision_epoch_ledger"
    ][0]
    assert attacked_epoch["eligible_moderator_participant_decision_support"] == pytest.approx(
        55.0
    )
    assert attacked_epoch["retention_overlap_receipt"] == base_epoch["retention_overlap_receipt"]

    lineage_attack = copy.deepcopy(attacked)
    lineage_attack["protocol_id"] = "retained-lineage-alias-attack"
    lineage_alias = lineage_attack["measurement_geometry"]["participant_event_schedules"][-1]
    lineage_alias["retention_overlap_authority"] = {
        "state": "registered_nested",
        "retained_participant_set_id": "different-retained-lineage",
        "source_object_sha256": SHA,
        "source_locator": "protocol:retention-overlap:different-lineage",
    }
    with pytest.raises(ProtocolCapacityError, match="conflicting retention-overlap authority"):
        compile_protocol_capacity(lineage_attack)


def test_hostile_proximal_estimand_must_use_epoch_assigned_policies() -> None:
    protocol = _protocol("never-assigned-estimand")
    causal = protocol["causal_geometry"]
    causal["operator_components"].append(
        {
            "component_id": "component-never",
            "canonical_operator_id": "canonical-component-never",
            "source_object_sha256": SHA,
            "source_locator": "protocol:operator:never",
        }
    )
    causal["policies"].append(
        {
            "policy_id": "never-assigned",
            "operator_component_ids": ["component-never"],
            "policy_rule_operator_id": "fixed-never-rule",
            "policy_rule_source_object_sha256": SHA,
            "policy_rule_source_locator": "protocol:policy:never",
        }
    )
    causal["estimands"][0]["operator_contrasts"][0]["policy_coefficients"][0]["policy_id"] = (
        "never-assigned"
    )
    with pytest.raises(ProtocolCapacityError, match="without positive support"):
        compile_protocol_capacity(protocol)


def test_regular_decision_epoch_process_matches_explicit_grid_sufficient_statistics() -> None:
    explicit = _families(
        compile_protocol_capacity(
            _explicit_regular_grid_protocol("explicit-rate-grid", decision_count=6)
        )
    )
    compact_result = compile_protocol_capacity(
        _regular_process_protocol("compact-rate-grid", decision_count=6)
    )
    compact = _families(compact_result)
    causal_fields = (
        "policy_rank",
        "component_rank",
        "policy_allocation_support_factor",
        "component_allocation_support_factor",
        "eligible_randomized_participants",
        "eligible_randomized_participant_decisions",
        "gates",
    )
    personalized_fields = (
        "sequential_moderator_rank",
        "sequential_moderator_allocation_support_factor",
        "eligible_randomized_participants",
        "eligible_randomized_participant_decisions",
        "gates",
    )
    assert {field: explicit["causal"][field] for field in causal_fields} == {
        field: compact["causal"][field] for field in causal_fields
    }
    assert {field: explicit["personalized_sequential"][field] for field in personalized_fields} == {
        field: compact["personalized_sequential"][field] for field in personalized_fields
    }
    stage = compact["causal"]["stage_ledger"][0]
    assert len(stage["decision_epoch_ledger"]) == 1
    assert stage["decision_epoch_ledger"][0]["decision_epoch_multiplicity"] == 6
    assert stage["decision_epoch_ledger"][0]["decision_epoch_representation"] == (
        "regular_decision_epoch_process"
    )
    schema = json.loads(
        (ROOT / "schemas/v2/protocol-capacity-result.schema.json").read_text(encoding="utf-8")
    )
    assert not list(Draft202012Validator(schema).iter_errors(compact_result))


def test_regular_decision_epoch_process_scales_to_level1_mrt_without_row_expansion() -> None:
    protocol = _regular_process_protocol(
        "level1-rate-process-runtime",
        decision_count=2190,
        decisions_per_day=3,
    )
    started = time.perf_counter()
    families = _families(compile_protocol_capacity(protocol))
    elapsed = time.perf_counter() - started
    stage = families["causal"]["stage_ledger"][0]
    assert elapsed < 2.0
    assert len(stage["decision_epoch_ledger"]) == 1
    assert stage["decision_epoch_ledger"][0]["decision_epoch_multiplicity"] == 2190
    assert stage["decision_epoch_ledger"][0]["proximal_outcome_event_count"] == 2190
    assert stage["eligible_decisions_per_participant"] == pytest.approx(1423.5)


def test_registered_ar1_estimating_score_dependence_matches_level1_effective_count() -> None:
    independent_protocol = _regular_process_protocol(
        "mrt-independent-score-process",
        decision_count=2190,
        decisions_per_day=3,
    )
    ar1_protocol = copy.deepcopy(independent_protocol)
    ar1_protocol["protocol_id"] = "mrt-ar1-score-process"
    ar1_stage = ar1_protocol["causal_geometry"]["assignment_stages"][0]
    ar1_stage["estimating_score_dependence_authority"].update(
        {"model": "ar1", "correlation": 0.75, "pooled_across_decisions": True}
    )

    independent = _families(compile_protocol_capacity(independent_protocol))
    ar1 = _families(compile_protocol_capacity(ar1_protocol))
    independent_stage = independent["causal"]["stage_ledger"][0]
    ar1_stage_result = ar1["causal"]["stage_ledger"][0]
    assert independent_stage["effective_decision_information_count"] == 2190.0
    assert ar1_stage_result["effective_decision_information_count"] == pytest.approx(
        313.34770678165427
    )
    assert ar1_stage_result["decision_epoch_ledger"][0][
        "effective_decision_information_multiplicity"
    ] == pytest.approx(313.34770678165427)
    assert (
        ar1["causal"]["component_allocation_support_factor"]
        < independent["causal"]["component_allocation_support_factor"]
    )


def test_compact_and_explicit_ar1_score_processes_have_identical_information() -> None:
    compact_protocol = _regular_process_protocol(
        "compact-ar1-grid", decision_count=6
    )
    explicit_protocol = _explicit_regular_grid_protocol(
        "explicit-ar1-grid", decision_count=6
    )
    for protocol in (compact_protocol, explicit_protocol):
        protocol["causal_geometry"]["assignment_stages"][0][
            "estimating_score_dependence_authority"
        ].update({"model": "ar1", "correlation": 0.5, "pooled_across_decisions": True})
    compact = _families(compile_protocol_capacity(compact_protocol))
    explicit = _families(compile_protocol_capacity(explicit_protocol))
    assert compact["causal"]["component_allocation_support_factor"] == pytest.approx(
        explicit["causal"]["component_allocation_support_factor"]
    )
    assert compact["personalized_sequential"][
        "sequential_moderator_allocation_support_factor"
    ] == pytest.approx(
        explicit["personalized_sequential"][
            "sequential_moderator_allocation_support_factor"
        ]
    )


def test_unknown_repeated_estimating_score_dependence_fails_numeric_credit_closed() -> None:
    protocol = _regular_process_protocol(
        "unknown-repeated-score-dependence", decision_count=6
    )
    stage = protocol["causal_geometry"]["assignment_stages"][0]
    stage["estimating_score_dependence_authority"] = {
        "state": "unknown",
        "reason": "estimating-score serial dependence has not been registered",
        "source_object_sha256": SHA,
        "source_locator": "protocol:estimating-score-dependence:unknown",
    }
    families = _families(compile_protocol_capacity(protocol))
    stage_result = families["causal"]["stage_ledger"][0]
    assert stage_result["effective_decision_information_count"] == 0.0
    assert families["causal"]["component_allocation_support_factor"] == 0.0
    assert families["causal"]["gates"]["D_dynamic_operator"] is False
    assert families["personalized_sequential"]["gates"] == {
        "P_personalized_policy": False,
        "H_heterogeneous_response": False,
    }


def test_mrt_information_uses_worst_case_conditional_policy_lower_bounds() -> None:
    baseline = _protocol("mrt-conditional-policy-baseline")
    shifted = copy.deepcopy(baseline)
    shifted["protocol_id"] = "mrt-conditional-policy-near-boundary"
    shifted["causal_geometry"]["decision_rule_operators"][0][
        "conditional_probability_shift"
    ] = 0.25
    baseline_families = _families(compile_protocol_capacity(baseline))
    shifted_families = _families(compile_protocol_capacity(shifted))
    baseline_stage = baseline_families["causal"]["stage_ledger"][0]
    shifted_stage = shifted_families["causal"]["stage_ledger"][0]
    assert set(
        baseline_stage["estimand_contrast_ledger"][0][
            "minimum_conditional_policy_probabilities"
        ].values()
    ) == {0.4375}
    assert set(
        shifted_stage["estimand_contrast_ledger"][0][
            "minimum_conditional_policy_probabilities"
        ].values()
    ) == {0.25}
    assert (
        shifted_families["causal"]["component_allocation_support_factor"]
        < baseline_families["causal"]["component_allocation_support_factor"]
    )


def test_regular_decision_epoch_process_rejects_temporal_and_grid_gaming() -> None:
    not_before_next = _regular_process_protocol("readback-not-before-next", decision_count=6)
    not_before_next["causal_geometry"]["assignment_stages"][0]["regular_decision_epoch_process"][
        "proximal_readback_offset_days"
    ] = 1.0
    with pytest.raises(ProtocolCapacityError, match="strictly postdecision"):
        compile_protocol_capacity(not_before_next)

    missing_readback = _regular_process_protocol("missing-grid-readback", decision_count=6)
    outcome = missing_readback["measurement_geometry"]["participant_event_schedules"][1]
    outcome["temporal_offsets"] = outcome["temporal_offsets"][:-1]
    outcome["events_per_participant"] = _exact(5)
    with pytest.raises(ProtocolCapacityError, match="every exact source-bound proximal"):
        compile_protocol_capacity(missing_readback)

    count_mismatch = _regular_process_protocol("count-mismatch", decision_count=6)
    count_mismatch["causal_geometry"]["assignment_stages"][0]["decisions_per_participant"] = _exact(
        7
    )
    with pytest.raises(ProtocolCapacityError, match="declared stage count"):
        compile_protocol_capacity(count_mismatch)


def test_hostile_smart_paths_bind_epoch_support_response_state_and_marginals() -> None:
    valid = _protocol("smart-path-valid")
    causal = valid["causal_geometry"]
    causal["operator_components"].append(
        {
            "component_id": "component-b",
            "canonical_operator_id": "canonical-component-b",
            "source_object_sha256": SHA,
            "source_locator": "protocol:operator:component-b",
        }
    )
    causal["policies"].extend(
        [
            {
                "policy_id": "component-b-only",
                "operator_component_ids": ["component-b"],
                "policy_rule_operator_id": "fixed-b-rule",
                "policy_rule_source_object_sha256": SHA,
                "policy_rule_source_locator": "protocol:policy:component-b-only",
            },
            {
                "policy_id": "combined-a-b",
                "operator_component_ids": ["component-a", "component-b"],
                "policy_rule_operator_id": "fixed-combined-rule",
                "policy_rule_source_object_sha256": SHA,
                "policy_rule_source_locator": "protocol:policy:combined-a-b",
            },
        ]
    )
    rule = causal["decision_rule_operators"][0]
    policy_ids = ["control", "active", "component-b-only", "combined-a-b"]
    interaction_basis = [[1.0], [-1.0], [-1.0], [1.0]]
    rule.update(
        {
            "policy_ids": policy_ids,
            "state_to_policy_contrast_matrix": interaction_basis,
            "response_state_score_axis_ids": ["score-a"],
            "response_state_score_matrix": [[1.0]],
            "policy_interaction_basis_matrix": interaction_basis,
            "conditional_probability_shift": 0.0625,
        }
    )
    response_schedule = copy.deepcopy(
        valid["measurement_geometry"]["participant_event_schedules"][0]
    )
    response_schedule.update(
        {
            "schedule_id": "schedule-smart-response",
            "participant_event_lineage_id": "lineage-smart-response",
            "joint_observation_bundle_id": "bundle-smart-response",
            "temporal_offsets": [15],
            "source_locator": "protocol:schedule:smart-response",
        }
    )
    valid["measurement_geometry"]["joint_observation_bundles"].append(
        {
            "joint_observation_bundle_id": "bundle-smart-response",
            "canonical_event_unit_id": "blood-draw",
        }
    )
    valid["measurement_geometry"]["participant_event_schedules"].append(response_schedule)
    stage = valid["causal_geometry"]["assignment_stages"][0]
    stage["assignment_mechanism"] = "smart_rerandomized"
    stage["decisions_per_participant"] = _exact(2)
    stage["policy_allocations"] = [
        {"policy_id": policy_id, "probability": 0.25} for policy_id in policy_ids
    ]
    stage["decision_epochs"] = stage["decision_epochs"][:2]
    stage["moderator_population_geometry"]["epoch_covariances"] = stage[
        "moderator_population_geometry"
    ]["epoch_covariances"][:2]
    for epoch in stage["decision_epochs"]:
        epoch["policy_propensities"] = [
            {"policy_id": policy_id, "probability": 0.25} for policy_id in policy_ids
        ]
    stage["decision_epochs"][1]["history_measurement_schedule_ids"].append(
        "schedule-smart-response"
    )
    epoch_ids = [row["decision_epoch_id"] for row in stage["decision_epochs"]]
    state_rows = (
        ("score-a-nonnegative", "classified", "nonnegative"),
        ("score-a-negative", "classified", "negative"),
        ("unclassifiable", "unclassifiable", None),
    )
    response_state_definitions = []
    for state_id, classification_state, direction in state_rows:
        predicate = (
            {
                "kind": "argmax_absolute_registered_linear_scores_with_ordered_tie_break",
                "active_score_axis_id": "score-a",
                "direction": direction,
                "ordered_axis_priority": ["score-a"],
            }
            if direction is not None
            else {
                "kind": "unclassifiable_if_any_required_feature_missing",
                "complete_case_required": True,
            }
        )
        response_state_definitions.append(
            {
                "response_state_id": state_id,
                "classification_state": classification_state,
                "transition_from_decision_epoch_id": epoch_ids[0],
                "next_decision_epoch_id": epoch_ids[1],
                "assessment_schedule_id": "schedule-smart-response",
                "assessment_time_offset": 15,
                "state_feature_ids": ["feature-a"],
                "predicate": predicate,
                "source_object_sha256": SHA,
                "source_locator": f"protocol:smart:state:{state_id}",
            }
        )
    distributions = {
        "score-a-nonnegative": [0.3125, 0.1875, 0.1875, 0.3125],
        "score-a-negative": [0.1875, 0.3125, 0.3125, 0.1875],
        "unclassifiable": [0.25, 0.25, 0.25, 0.25],
    }
    conditional_policy_distributions = [
        {
            "decision_epoch_id": epoch_ids[1],
            "response_state_id": state_id,
            "policy_propensities": [
                {"policy_id": policy_id, "probability": probability}
                for policy_id, probability in zip(policy_ids, probabilities, strict=True)
            ],
            "source_object_sha256": SHA,
            "source_locator": f"protocol:smart:conditional:{state_id}",
        }
        for state_id, probabilities in distributions.items()
    ]
    paths = []
    for first_policy in policy_ids:
        for state_id, probabilities in distributions.items():
            for second_policy, second_probability in zip(policy_ids, probabilities, strict=True):
                paths.append(
                    {
                        "smart_path_id": (f"path:{first_policy}:{state_id}:{second_policy}"),
                        "ordered_decision_epoch_ids": epoch_ids,
                        "response_state_ids": [state_id],
                        "policy_sequence_ids": [first_policy, second_policy],
                        "assignment_propensity_product": 0.25 * second_probability,
                        "probability_semantics": (
                            "product_of_conditional_assignment_propensities_"
                            "excludes_response_state_prevalence"
                        ),
                        "source_object_sha256": SHA,
                        "source_locator": (
                            f"protocol:smart:path:{first_policy}:{state_id}:{second_policy}"
                        ),
                    }
                )
    stage["smart_path_geometry"] = {
        "state": "registered",
        "response_state_definitions": response_state_definitions,
        "conditional_policy_distributions": conditional_policy_distributions,
        "response_state_prevalence": {
            "state": "registered",
            "state_probabilities": [
                {"response_state_id": "score-a-nonnegative", "probability": 0.4},
                {"response_state_id": "score-a-negative", "probability": 0.4},
                {"response_state_id": "unclassifiable", "probability": 0.2},
            ],
            "source_object_sha256": SHA,
            "source_locator": "protocol:smart:state-prevalence",
        },
        "paths": paths,
    }
    stage["estimating_score_dependence_authority"].update(
        {
            "model": "exchangeable",
            "correlation": 0.5,
            "pooled_across_decisions": False,
        }
    )
    _sync_conditional_eligibility_authority(stage)
    personalized = _families(compile_protocol_capacity(valid))["personalized_sequential"]
    assert personalized["gates"]["P_personalized_policy"]
    assert personalized["between_state_policy_distribution_rank"] == 1
    assert personalized["component_marginals_preserved_within_response_states"]
    assert personalized["smart_path_count"] == 48

    inconsistent = copy.deepcopy(valid)
    inconsistent["protocol_id"] = "smart-path-inconsistent"
    inconsistent["causal_geometry"]["assignment_stages"][0]["smart_path_geometry"]["paths"][0][
        "assignment_propensity_product"
    ] += 0.01
    with pytest.raises(ProtocolCapacityError, match="assignment propensities only"):
        compile_protocol_capacity(inconsistent)


def test_hostile_unknown_personalization_alternative_preserves_known_lower_bound() -> None:
    protocol = _protocol("unknown-personalization-alternative")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(protocol)))
    unknown = copy.deepcopy(protocol["causal_geometry"]["assignment_stages"][0])
    unknown["stage_id"] = "unknown-million-person-stage"
    unknown["participant_count"] = _exact(1_000_000)
    unknown["moderator_population_geometry"] = {
        "state": "unknown",
        "reason": "decision-population covariance is not yet registered",
        "source_object_sha256": SHA,
        "source_locator": "protocol:moderator-population:unknown",
    }
    protocol["causal_geometry"]["assignment_stages"].append(unknown)
    families = _families(compile_protocol_capacity(protocol))
    causal = families["causal"]
    personalized = families["personalized_sequential"]
    assert causal["policy_rank"] == baseline["causal"]["policy_rank"]
    assert (
        causal["policy_allocation_support_factor"]
        == baseline["causal"]["policy_allocation_support_factor"]
    )
    assert personalized["resolution_state"] == (
        "partial_known_lower_bound_with_unresolved_alternatives"
    )
    assert personalized["unresolved_alternative_stage_ids"] == ["unknown-million-person-stage"]
    assert (
        personalized["selected_stage_ids"]
        == baseline["personalized_sequential"]["selected_stage_ids"]
    )
    assert (
        personalized["sequential_moderator_rank"]
        == baseline["personalized_sequential"]["sequential_moderator_rank"]
    )
    assert (
        personalized["sequential_moderator_allocation_support_factor"]
        == baseline["personalized_sequential"]["sequential_moderator_allocation_support_factor"]
    )
    assert personalized["gates"] == baseline["personalized_sequential"]["gates"]


def test_hostile_personalization_is_null_only_without_a_known_candidate() -> None:
    protocol = _protocol("unknown-personalization-only")
    stage = protocol["causal_geometry"]["assignment_stages"][0]
    stage["moderator_population_geometry"] = {
        "state": "unknown",
        "reason": "decision-population covariance is not yet registered",
        "source_object_sha256": SHA,
        "source_locator": "protocol:moderator-population:unknown-only",
    }
    personalized = _families(compile_protocol_capacity(protocol))["personalized_sequential"]
    assert personalized["resolution_state"] == "unresolved_no_known_candidate"
    assert personalized["selected_stage_ids"] == []
    assert personalized["unresolved_alternative_stage_ids"] == ["baseline-randomization"]
    assert personalized["sequential_moderator_rank"] is None
    assert personalized["sequential_moderator_allocation_support_factor"] is None
    assert personalized["gates"] == {
        "P_personalized_policy": None,
        "H_heterogeneous_response": None,
    }


def test_hostile_unknown_transport_addition_preserves_maximal_known_subset() -> None:
    protocol = _protocol("unknown-transport-alternative")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]
    unknown = copy.deepcopy(protocol["causal_geometry"]["transport_geometry"]["contexts"][0])
    unknown["context_id"] = "unknown-transport-context"
    unknown["estimand_binding"] = {
        "state": "unknown",
        "reason": "outcome/operator/horizon binding is not registered",
        "source_object_sha256": SHA,
        "source_locator": "protocol:transport:unknown-added-context",
    }
    protocol["causal_geometry"]["transport_geometry"]["contexts"].append(unknown)
    transport = _families(compile_protocol_capacity(protocol))["transport"]
    assert transport["resolution_state"] == (
        "partial_known_lower_bound_with_ineligible_or_unresolved_contexts"
    )
    assert transport["selected_context_ids"] == baseline["selected_context_ids"]
    assert transport["unresolved_context_ids"] == ["unknown-transport-context"]
    assert transport["transport_rank"] == baseline["transport_rank"]
    assert transport["rank_tolerance_receipt"] == baseline["rank_tolerance_receipt"]
    assert (
        transport["transport_allocation_support_factor"]
        == baseline["transport_allocation_support_factor"]
    )
    assert transport["gates"] == baseline["gates"]


def test_hostile_invalid_transport_addition_preserves_maximal_known_subset() -> None:
    protocol = _protocol("invalid-transport-alternative")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]
    invalid = copy.deepcopy(protocol["causal_geometry"]["transport_geometry"]["contexts"][0])
    invalid["context_id"] = "observational-transport-context"
    invalid["assignment_mechanism"] = "observational"
    protocol["causal_geometry"]["transport_geometry"]["contexts"].append(invalid)
    transport = _families(compile_protocol_capacity(protocol))["transport"]
    assert transport["resolution_state"] == (
        "partial_known_lower_bound_with_ineligible_or_unresolved_contexts"
    )
    assert transport["selected_context_ids"] == baseline["selected_context_ids"]
    assert transport["ineligible_context_ids"] == ["observational-transport-context"]
    assert transport["transport_rank"] == baseline["transport_rank"]
    assert (
        transport["transport_allocation_support_factor"]
        == baseline["transport_allocation_support_factor"]
    )


def test_hostile_duplicate_population_transport_alternative_is_monotone_and_id_invariant() -> None:
    baseline_protocol = _protocol("duplicate-population-transport-baseline")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(baseline_protocol)))["transport"]

    for clone_id in ("aa-site-b-shadow", "zz-site-b-shadow"):
        attacked = copy.deepcopy(baseline_protocol)
        clone = copy.deepcopy(attacked["causal_geometry"]["transport_geometry"]["contexts"][1])
        clone["context_id"] = clone_id
        clone["transport_coordinates"] = copy.deepcopy(
            attacked["causal_geometry"]["transport_geometry"]["contexts"][0][
                "transport_coordinates"
            ]
        )
        contexts = attacked["causal_geometry"]["transport_geometry"]["contexts"]
        contexts.append(clone)

        for permutation in itertools.permutations(contexts):
            candidate = copy.deepcopy(attacked)
            candidate["causal_geometry"]["transport_geometry"]["contexts"] = list(permutation)
            transport = _families(compile_protocol_capacity(candidate))["transport"]
            assert transport["selected_context_ids"] == baseline["selected_context_ids"]
            assert transport["ineligible_context_ids"] == [clone_id]
            assert transport["transport_rank"] == baseline["transport_rank"] == 1
            assert transport["rank_tolerance_receipt"] == baseline["rank_tolerance_receipt"]
            assert (
                transport["transport_allocation_support_factor"]
                == baseline["transport_allocation_support_factor"]
            )
            assert transport["gates"] == baseline["gates"]


def test_duplicate_population_context_id_only_breaks_semantically_equivalent_tie() -> None:
    baseline_protocol = _protocol("equivalent-duplicate-population-transport")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(baseline_protocol)))["transport"]
    clone = copy.deepcopy(baseline_protocol["causal_geometry"]["transport_geometry"]["contexts"][1])
    clone["context_id"] = "aa-site-b-equivalent"
    baseline_protocol["causal_geometry"]["transport_geometry"]["contexts"].append(clone)

    transport = _families(compile_protocol_capacity(baseline_protocol))["transport"]
    assert transport["selected_context_ids"] == ["aa-site-b-equivalent", "site-a"]
    assert transport["ineligible_context_ids"] == ["site-b"]
    assert transport["transport_rank"] == baseline["transport_rank"]
    assert transport["rank_tolerance_receipt"] == baseline["rank_tolerance_receipt"]
    assert (
        transport["transport_allocation_support_factor"]
        == baseline["transport_allocation_support_factor"]
    )


def test_same_coordinate_lower_support_duplicate_is_loewner_dominated_before_id_tie() -> None:
    protocol = _protocol("dominated-duplicate-population-transport")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]
    clone = copy.deepcopy(protocol["causal_geometry"]["transport_geometry"]["contexts"][1])
    clone["context_id"] = "aa-site-b-lower-support"
    clone["policy_allocations"] = [
        {"policy_id": "control", "probability": 0.1},
        {"policy_id": "active", "probability": 0.9},
    ]
    protocol["causal_geometry"]["transport_geometry"]["contexts"].append(clone)

    transport = _families(compile_protocol_capacity(protocol))["transport"]
    assert transport["selected_context_ids"] == baseline["selected_context_ids"]
    assert transport["ineligible_context_ids"] == ["aa-site-b-lower-support"]
    assert transport["transport_rank"] == baseline["transport_rank"]
    assert transport["rank_tolerance_receipt"] == baseline["rank_tolerance_receipt"]
    assert (
        transport["transport_allocation_support_factor"]
        == baseline["transport_allocation_support_factor"]
    )


def test_transport_numeric_result_is_invariant_to_arbitrary_context_id_renaming() -> None:
    protocol = _protocol("arbitrary-context-id-renaming")
    clone = copy.deepcopy(protocol["causal_geometry"]["transport_geometry"]["contexts"][1])
    clone["context_id"] = "shadow-context"
    clone["transport_coordinates"] = copy.deepcopy(
        protocol["causal_geometry"]["transport_geometry"]["contexts"][0]["transport_coordinates"]
    )
    protocol["causal_geometry"]["transport_geometry"]["contexts"].append(clone)
    baseline = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]

    rename_sets = (
        ("context-97", "context-02", "context-55"),
        ("transport-alpha", "transport-zulu", "transport-mike"),
        ("c-0000000001", "c-9999999999", "c-3141592653"),
    )
    for renamed_ids in rename_sets:
        renamed = copy.deepcopy(protocol)
        contexts = renamed["causal_geometry"]["transport_geometry"]["contexts"]
        for context, context_id in zip(contexts, renamed_ids, strict=True):
            context["context_id"] = context_id
        contexts.reverse()
        transport = _families(compile_protocol_capacity(renamed))["transport"]
        assert transport["transport_rank"] == baseline["transport_rank"]
        assert transport["rank_tolerance_receipt"] == baseline["rank_tolerance_receipt"]
        assert (
            transport["transport_allocation_support_factor"]
            == baseline["transport_allocation_support_factor"]
        )
        assert transport["gates"] == baseline["gates"]


def test_transport_required_axis_projection_ignores_and_ledgers_extra_axes() -> None:
    baseline_protocol = _protocol("transport-required-axis-baseline")
    baseline = _families(compile_protocol_capacity(copy.deepcopy(baseline_protocol)))["transport"]
    assert baseline["transport_rank"] == 1
    assert baseline["transport_allocation_support_factor"] == 5.625

    attacks = []
    one_context = copy.deepcopy(baseline_protocol)
    one_context["causal_geometry"]["transport_geometry"]["contexts"][0][
        "transport_coordinates"
    ].append({"transport_axis_id": "irrelevant-axis", "value": 7.0})
    attacks.append(one_context)

    both_contexts = copy.deepcopy(baseline_protocol)
    for index, context in enumerate(
        both_contexts["causal_geometry"]["transport_geometry"]["contexts"]
    ):
        context["transport_coordinates"].append(
            {"transport_axis_id": "irrelevant-axis", "value": float(index)}
        )
    attacks.append(both_contexts)

    huge = copy.deepcopy(baseline_protocol)
    huge["causal_geometry"]["transport_geometry"]["contexts"][0]["transport_coordinates"].append(
        {"transport_axis_id": "irrelevant-axis", "value": 1e12}
    )
    attacks.append(huge)

    for attacked in attacks:
        transport = _families(compile_protocol_capacity(attacked))["transport"]
        assert transport["transport_rank"] == baseline["transport_rank"] == 1
        assert transport["rank_tolerance_receipt"] == baseline["rank_tolerance_receipt"]
        assert (
            transport["transport_allocation_support_factor"]
            == baseline["transport_allocation_support_factor"]
            == 5.625
        )
        family = transport["axis_family_frontier"][0]
        assert family["required_transport_axis_ids"] == ["site-context"]
        ledgered_extras = [
            coordinate
            for row in family["context_support_ledger"]
            for coordinate in row["ignored_extra_transport_coordinates"]
        ]
        assert all(
            coordinate["transport_axis_id"] == "irrelevant-axis" for coordinate in ledgered_extras
        )
        assert (
            family["family_geometry_sha256"]
            == baseline["axis_family_frontier"][0]["family_geometry_sha256"]
        )


def test_transport_missing_required_axis_is_typed_ineligible_per_family() -> None:
    protocol = _protocol("transport-missing-required-axis")
    protocol["causal_geometry"]["transport_geometry"]["contexts"][1]["transport_coordinates"] = [
        {"transport_axis_id": "unrelated-axis", "value": 1.0}
    ]
    transport = _families(compile_protocol_capacity(protocol))["transport"]
    family = transport["axis_family_frontier"][0]
    assert family["resolution_state"] == "resolved_no_eligible_context_subset"
    assert family["selected_context_ids"] == []
    assert family["ineligible_context_ids"] == ["site-a", "site-b"]
    assert family["transport_rank"] == 0
    site_b = next(row for row in family["context_support_ledger"] if row["context_id"] == "site-b")
    assert site_b["selection_state"] == "ineligible"
    assert site_b["missing_required_transport_axis_ids"] == ["site-context"]
    assert site_b["selection_reason_codes"] == ["missing_required_transport_axes"]
    assert site_b["ignored_extra_transport_coordinates"] == [
        {"transport_axis_id": "unrelated-axis", "value": 1.0}
    ]


def test_multiple_transport_axis_families_emit_vector_without_scalar_selection() -> None:
    protocol = _protocol("two-transport-axis-families")
    transport_geometry = protocol["causal_geometry"]["transport_geometry"]
    transport_geometry["transport_axis_families"].append(
        {
            "transport_axis_family_id": "environment-transport",
            "reference_estimand_id": "proximal-feature-a",
            "required_transport_axis_ids": ["environment-context"],
            "coordinate_scale_authority": {
                "state": "registered",
                "scope": "units_transforms_ranges_for_required_transport_axes",
                "source_object_sha256": SHA,
                "source_locator": "protocol:transport-axis-scale:environment-context",
            },
        }
    )
    for index, context in enumerate(transport_geometry["contexts"]):
        context["transport_coordinates"].append(
            {"transport_axis_id": "environment-context", "value": float(index)}
        )

    result = compile_protocol_capacity(copy.deepcopy(protocol))
    transport = _families(result)["transport"]
    assert transport["scalar_alias_state"] == "multiple_axis_families_vector_only"
    assert transport["resolution_state"] == "resolved_axis_family_vector"
    assert transport["transport_rank"] is None
    assert transport["rank_tolerance_receipt"] is None
    assert transport["transport_allocation_support_factor"] is None
    assert transport["gates"] == {"T_transport": None}
    families = {row["transport_axis_family_id"]: row for row in transport["axis_family_frontier"]}
    assert set(families) == {"site-transport", "environment-transport"}
    for family in families.values():
        assert family["transport_rank"] == 1
        assert family["transport_allocation_support_factor"] == 5.625
        assert family["gates"] == {"T_transport": True}
    assert result["family_envelopes"]["transport.axis_families.site-transport.transport_rank"] == {
        "minimum": 1,
        "maximum": 1,
    }
    assert result["family_envelopes"][
        "transport.axis_families.environment-transport.transport_allocation_support_factor"
    ] == {"minimum": 5.625, "maximum": 5.625}
    assert "transport.transport_rank" not in result["family_envelopes"]
    assert "transport.transport_allocation_support_factor" not in result["family_envelopes"]

    result_schema = json.loads(
        (ROOT / "schemas/v2/protocol-capacity-result.schema.json").read_text(encoding="utf-8")
    )
    assert not list(Draft202012Validator(result_schema).iter_errors(result))

    missing_second_family_axis = copy.deepcopy(protocol)
    missing_second_family_axis["causal_geometry"]["transport_geometry"]["contexts"][1][
        "transport_coordinates"
    ] = [
        coordinate
        for coordinate in missing_second_family_axis["causal_geometry"]["transport_geometry"][
            "contexts"
        ][1]["transport_coordinates"]
        if coordinate["transport_axis_id"] != "environment-context"
    ]
    attacked_transport = _families(compile_protocol_capacity(missing_second_family_axis))[
        "transport"
    ]
    attacked = {
        row["transport_axis_family_id"]: row for row in attacked_transport["axis_family_frontier"]
    }
    assert attacked["site-transport"]["transport_rank"] == 1
    assert attacked["site-transport"]["transport_allocation_support_factor"] == 5.625
    assert attacked["environment-transport"]["transport_rank"] == 0


def test_transport_axis_family_and_coordinate_order_are_numeric_invariants() -> None:
    protocol = _protocol("transport-family-order-invariant")
    family = protocol["causal_geometry"]["transport_geometry"]["transport_axis_families"][0]
    family["required_transport_axis_ids"] = ["site-context", "region-context"]
    for index, context in enumerate(protocol["causal_geometry"]["transport_geometry"]["contexts"]):
        context["transport_coordinates"].append(
            {"transport_axis_id": "region-context", "value": float(index)}
        )
    baseline = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]
    baseline_family = baseline["axis_family_frontier"][0]

    renamed = copy.deepcopy(protocol)
    renamed_family = renamed["causal_geometry"]["transport_geometry"]["transport_axis_families"][0]
    renamed_family["transport_axis_family_id"] = "renamed-family"
    contexts = renamed["causal_geometry"]["transport_geometry"]["contexts"]
    for index, context in enumerate(contexts):
        context["context_id"] = f"renamed-context-{index}"
        context["transport_coordinates"].reverse()
    contexts.reverse()
    attacked = _families(compile_protocol_capacity(renamed))["transport"]
    attacked_family = attacked["axis_family_frontier"][0]
    assert attacked_family["family_geometry_sha256"] == baseline_family["family_geometry_sha256"]
    assert attacked_family["transport_rank"] == baseline_family["transport_rank"]
    assert attacked_family["rank_tolerance_receipt"] == baseline_family["rank_tolerance_receipt"]
    assert (
        attacked_family["transport_allocation_support_factor"]
        == baseline_family["transport_allocation_support_factor"]
    )
    assert attacked_family["gates"] == baseline_family["gates"]


def test_duplicate_semantic_transport_axis_families_fail_closed() -> None:
    protocol = _protocol("duplicate-semantic-transport-family")
    duplicate = copy.deepcopy(
        protocol["causal_geometry"]["transport_geometry"]["transport_axis_families"][0]
    )
    duplicate["transport_axis_family_id"] = "duplicate-site-family"
    duplicate["coordinate_scale_authority"]["source_locator"] = (
        "protocol:transport-axis-scale:alternative-pointer"
    )
    protocol["causal_geometry"]["transport_geometry"]["transport_axis_families"].append(duplicate)
    with pytest.raises(ProtocolCapacityError, match="duplicate semantic transport axis families"):
        compile_protocol_capacity(protocol)


def test_transport_axis_family_requires_complete_coordinate_scale_authority() -> None:
    protocol = _protocol("missing-transport-scale-authority")
    del protocol["causal_geometry"]["transport_geometry"]["transport_axis_families"][0][
        "coordinate_scale_authority"
    ]["source_locator"]
    with pytest.raises(ProtocolCapacityError, match="source_locator.*required"):
        compile_protocol_capacity(protocol)


def test_transport_frontier_runtime_limit_never_changes_admitted_numeric_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = _protocol("duplicate-population-frontier-runtime-limit")
    clone = copy.deepcopy(protocol["causal_geometry"]["transport_geometry"]["contexts"][1])
    clone["context_id"] = "site-b-alternative"
    clone["transport_coordinates"][0]["value"] = 2.0
    protocol["causal_geometry"]["transport_geometry"]["contexts"].append(clone)

    monkeypatch.setattr(
        protocol_capacity_module,
        "TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT",
        2,
    )
    exact_at_limit = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]
    monkeypatch.setattr(
        protocol_capacity_module,
        "TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT",
        10_000,
    )
    exact_below_limit = _families(compile_protocol_capacity(copy.deepcopy(protocol)))["transport"]
    assert exact_at_limit == exact_below_limit

    monkeypatch.setattr(
        protocol_capacity_module,
        "TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT",
        1,
    )
    with pytest.raises(
        ProtocolCapacityError,
        match=(
            "above the runtime resource limit of 1; no numeric result was approximated or emitted"
        ),
    ):
        compile_protocol_capacity(protocol)


def test_result_schema_rejects_missing_or_mistyped_family_semantics() -> None:
    result = compile_protocol_capacity(_protocol("result-schema-hostile"))
    schema = json.loads(
        (ROOT / "schemas/v2/protocol-capacity-result.schema.json").read_text(encoding="utf-8")
    )
    missing = copy.deepcopy(result)
    del missing["scenarios"][0]["families"]["causal"]["policy_rank"]
    assert list(Draft202012Validator(schema).iter_errors(missing))
    mistyped = copy.deepcopy(result)
    mistyped["scenarios"][0]["families"]["transport"]["transport_rank"] = "one"
    assert list(Draft202012Validator(schema).iter_errors(mistyped))
    nested_mutations = (
        ("causal", "stage_ledger", [{}]),
        ("intensive", "bundle_ledger", [{}]),
        ("transport", "transport_ledger", {}),
        ("measurement_audit", "joint_covariance_authority", {}),
    )
    for family_id, field, invalid_value in nested_mutations:
        invalid = copy.deepcopy(result)
        invalid["scenarios"][0]["families"][family_id][field] = invalid_value
        assert list(Draft202012Validator(schema).iter_errors(invalid)), (family_id, field)
    undeclared_stage_key = copy.deepcopy(result)
    undeclared_stage_key["scenarios"][0]["families"]["causal"]["stage_ledger"][0][
        "unregistered_claim"
    ] = 1
    assert list(Draft202012Validator(schema).iter_errors(undeclared_stage_key))
