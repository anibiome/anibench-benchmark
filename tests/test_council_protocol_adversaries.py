"""Compiler-level anti-gaming regressions using declared synthetic geometry only.

Existing alias/lineage, redundant-policy, and population-authority tests are
reused by the council audit instead of duplicated here. No global rank oracle.
"""

from __future__ import annotations

import copy

import pytest
from test_protocol_capacity_v2 import (
    SHA,
    _exact,
    _families,
    _protocol,
    _set_complete_joint_covariance,
)

from anibench.protocol_capacity_v2 import ProtocolCapacityError, compile_protocol_capacity


def _one_population(participants: int) -> dict:
    protocol = _protocol("council-synthetic-one-population")
    geometry = protocol["measurement_geometry"]
    geometry["participant_event_schedules"] = geometry["participant_event_schedules"][:2]
    geometry["joint_observation_bundles"] = geometry["joint_observation_bundles"][:2]
    geometry.pop("population_aggregation_authorities")
    for schedule in geometry["participant_event_schedules"]:
        schedule["participant_count"] = _exact(participants)
    protocol["causal_geometry"]["assignment_stages"][0]["participant_count"] = _exact(participants)
    transport = protocol["causal_geometry"]["transport_geometry"]
    transport["contexts"] = transport["contexts"][:1]
    context = transport["contexts"][0]
    context["participant_set_id"] = "all-participants"
    context["participant_count"] = _exact(participants)
    context["linked_outcome_schedule_ids"] = ["schedule-a"]
    return protocol


def _second_direction(protocol: dict) -> None:
    geometry = protocol["measurement_geometry"]
    signal = copy.deepcopy(geometry["signals"][0])
    signal.update(
        signal_id="signal-b",
        canonical_feature_id="feature-b",
        feature_ancestry_id="ancestry-b",
        operator_row=[0.0, 1.0],
    )
    geometry["signals"].append(signal)
    geometry["covariance_groups"].append(
        {
            "covariance_group_id": "covariance-b",
            "signal_ids": ["signal-b"],
            "covariance": [[1.0]],
            "source_object_sha256": SHA,
            "source_locator": "synthetic:declared-second-direction",
        }
    )
    _set_complete_joint_covariance(protocol, ["signal-a", "signal-b"], [[1.0, 0.0], [0.0, 1.0]])
    geometry["measurement_modules"][0]["signal_ids"].append("signal-b")


def test_two_people_deep_and_large_shallow_retain_different_strengths_without_winner():
    deep = _one_population(2)
    _second_direction(deep)
    shallow = _one_population(100_000)
    deep_result = compile_protocol_capacity(deep)
    shallow_result = compile_protocol_capacity(shallow)
    df, sf = _families(deep_result), _families(shallow_result)
    assert df["intensive"]["effective_rank"] == 2
    assert sf["intensive"]["effective_rank"] == 1
    # Population cannot repair the absent second direction; more people can
    # nevertheless support more information along the direction actually seen.
    assert sf["extensive"]["posterior_direction_information"][1] == 0
    assert (
        sf["extensive"]["posterior_direction_information"][0]
        > df["extensive"]["posterior_direction_information"][0]
    )
    assert df["longitudinal"]["trajectory_ledger"][0]["participant_count_maximum"] == 2
    for result in (deep_result, shallow_result):
        assert result["overall_scalar"] is None
        assert result["public_rank_emission_permitted"] is False
        assert result["empirical_attainment"] is False


def test_two_people_thousand_correlated_measurements_do_not_become_independent_n():
    base = _one_population(2)
    for schedule in base["measurement_geometry"]["participant_event_schedules"]:
        schedule["retention_fraction"] = _exact(1)
        schedule["within_person_repetition_correlation"] = _exact(0.99)
    attack = copy.deepcopy(base)
    schedule = attack["measurement_geometry"]["participant_event_schedules"][1]
    schedule["temporal_offsets"] = list(range(1000))
    schedule["events_per_participant"] = _exact(1000)
    before = _families(compile_protocol_capacity(base))
    after = _families(compile_protocol_capacity(attack))
    assert (
        after["extensive"]["retained_participant_events"]
        > before["extensive"]["retained_participant_events"]
    )
    # N*m/(1+(m-1)*rho) is bounded by N/rho, despite 1001 offsets.
    assert after["extensive"]["posterior_direction_information"][0] < 2 / 0.99
    trajectory = after["longitudinal"]["trajectory_ledger"][0]
    assert trajectory["participant_count_maximum"] == 2
    assert trajectory["linked_retained_participant_support"] == 2
    assert trajectory["trajectory_effective_information_count"] == pytest.approx(
        2 * 1001 / (1 + 1000 * 0.99)
    )


def test_unobserved_synthetic_neural_direction_stays_zero_under_extreme_scale():
    # Coordinate 2 is stipulated neural in this toy target, not inferred from a
    # real modality or dataset. A [gain, 0] operator has no sensitivity to it.
    protocol = _one_population(1_000_000)
    protocol["parameter_space"]["parameter_space_id"] = "synthetic-somatic-neural-target"
    protocol["measurement_geometry"]["signals"][0]["operator_row"] = [1_000_000.0, 0.0]
    families = _families(compile_protocol_capacity(protocol))
    for family in ("intensive", "extensive"):
        assert families[family]["effective_rank"] == 1
        assert families[family]["posterior_direction_information"][1] == 0


def test_caller_independent_n_cannot_override_declared_participant_lineage():
    protocol = _one_population(2)
    compile_protocol_capacity(protocol)
    protocol["measurement_geometry"]["participant_event_schedules"][1][
        "independent_participant_count"
    ] = 2000
    with pytest.raises(ProtocolCapacityError, match="independent_participant_count"):
        compile_protocol_capacity(protocol)


def test_cost_is_not_a_capacity_input_even_at_extreme_budget():
    protocol = _one_population(2)
    compile_protocol_capacity(protocol)
    protocol["budget_usd"] = 1_000_000_000_000
    with pytest.raises(ProtocolCapacityError, match="budget_usd"):
        compile_protocol_capacity(protocol)
