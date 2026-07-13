from __future__ import annotations

import copy
import json
import math
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from jsonschema import Draft202012Validator

from anibench.optimizer_protocol_v2 import (
    MAX_CANDIDATES,
    ProtocolOptimizerError,
    _objective_value,
    optimize_protocol,
)
from anibench import optimize_protocol_design_v2
from anibench.cli import main
from anibench.protocol_capacity_v2 import compile_protocol_capacity
from anibench.studio import StudioHandler
from test_protocol_capacity_v2 import _exact, _protocol


ROOT = Path(__file__).resolve().parents[1]
SHA = "sha256:" + "1" * 64


def _request() -> dict[str, Any]:
    return {
        "schema_version": "anibench.optimizer-protocol-input.v2",
        "optimizer_id": "hostile-protocol-optimizer-test",
        "base_protocol": _protocol(),
        "objectives": [
            {
                "objective_id": "intensive-depth",
                "family_path": "intensive.maximum_joint_bundle_log10_contraction",
                "envelope_bound": "minimum",
                "direction": "maximize",
            },
            {
                "objective_id": "retained-events",
                "family_path": "extensive.retained_participant_events",
                "envelope_bound": "minimum",
                "direction": "maximize",
            },
        ],
        "resource_constraints": [
            {
                "resource_id": "cost",
                "unit": "USD_2026",
                "base_amount": 100.0,
                "maximum_amount": 1000.0,
                "as_of": "2026-07-12",
                "source_object_sha256": SHA,
                "source_locator": "test:resource-envelope:cost",
            }
        ],
        "mutations": [
            {
                "mutation_id": "more-outcome-events",
                "description": "Double outcome-event density without changing depth per event.",
                "protocol_operations": [
                    {
                        "op": "replace",
                        "path": "/measurement_geometry/participant_event_schedules/1/events_per_participant",
                        "value": _exact(8),
                    },
                    {
                        "op": "replace",
                        "path": "/measurement_geometry/participant_event_schedules/1/temporal_offsets",
                        "value": [0, 15, 30, 45, 60, 75, 90, 105],
                    },
                ],
                "resource_deltas": [
                    {
                        "resource_id": "cost",
                        "unit": "USD_2026",
                        "amount": 400.0,
                        "as_of": "2026-07-12",
                        "source_object_sha256": SHA,
                        "source_locator": "test:cost-model:more-outcome-events",
                    }
                ],
                "source_object_sha256": SHA,
                "source_locator": "test:amendment:more-outcome-events",
            }
        ],
        "maximum_mutations_per_candidate": 1,
        "candidate_limit": 2,
    }


def _candidate(result: dict, candidate_id: str) -> dict:
    return next(row for row in result["candidates"] if row["candidate_id"] == candidate_id)


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for child in value.values():
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def test_every_candidate_is_recompiled_from_changed_protocol_geometry() -> None:
    request = _request()
    result = optimize_protocol(request)
    base = _candidate(result, "base")
    mutated = _candidate(result, "more-outcome-events")
    assert mutated["candidate_protocol_sha256"] != base["candidate_protocol_sha256"]
    assert mutated["capacity_result_sha256"] != base["capacity_result_sha256"]
    assert mutated["capacity_result"] == compile_protocol_capacity(
        {
            **copy.deepcopy(request["base_protocol"]),
            "measurement_geometry": {
                **copy.deepcopy(request["base_protocol"]["measurement_geometry"]),
                "participant_event_schedules": [
                    copy.deepcopy(
                        request["base_protocol"]["measurement_geometry"][
                            "participant_event_schedules"
                        ][0]
                    ),
                    {
                        **copy.deepcopy(
                            request["base_protocol"]["measurement_geometry"][
                                "participant_event_schedules"
                            ][1]
                        ),
                        "events_per_participant": _exact(8),
                        "temporal_offsets": [0, 15, 30, 45, 60, 75, 90, 105],
                    },
                    *copy.deepcopy(
                        request["base_protocol"]["measurement_geometry"][
                            "participant_event_schedules"
                        ][2:]
                    ),
                ],
            },
        }
    )
    base_values = {row["objective_id"]: row["value"] for row in base["objective_values"]}
    mutated_values = {row["objective_id"]: row["value"] for row in mutated["objective_values"]}
    assert mutated_values["intensive-depth"] == base_values["intensive-depth"]
    assert mutated_values["retained-events"] > base_values["retained-events"]
    assert result["pareto_frontier_candidate_ids"] == ["base", "more-outcome-events"]


def test_noop_or_non_geometry_mutation_cannot_change_compiled_outputs() -> None:
    request = _request()
    request["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/1/events_per_participant",
            "value": _exact(4),
        }
    ]
    with pytest.raises(ProtocolOptimizerError, match="does not alter protocol geometry"):
        optimize_protocol(request)

    request = _request()
    request["mutations"][0]["protocol_operations"][0]["path"] = "/protocol_id"
    with pytest.raises(ProtocolOptimizerError):
        optimize_protocol(request)


def test_alias_mutation_changes_protocol_hash_but_cannot_inflate_family_capacity() -> None:
    request = _request()
    signal_alias = copy.deepcopy(request["base_protocol"]["measurement_geometry"]["signals"][0])
    signal_alias["signal_id"] = "signal-a-alias"
    request["mutations"] = [
        {
            "mutation_id": "split-menu-alias",
            "description": "Attempt to inflate capacity by relabeling one feature.",
            "protocol_operations": [
                {"op": "add", "path": "/measurement_geometry/signals/-", "value": signal_alias},
                {
                    "op": "add",
                    "path": "/measurement_geometry/measurement_modules/-",
                    "value": {
                        "module_id": "alias-module",
                        "canonical_event_unit_id": "blood-draw",
                        "signal_ids": ["signal-a-alias"],
                        "evidence_state": "protocol_committed",
                    },
                },
                {
                    "op": "add",
                    "path": "/measurement_geometry/participant_event_schedules/0/measurement_module_ids/-",
                    "value": "alias-module",
                },
            ],
            "resource_deltas": [
                {
                    "resource_id": "cost",
                    "unit": "USD_2026",
                    "amount": 1.0,
                    "as_of": "2026-07-12",
                    "source_object_sha256": SHA,
                    "source_locator": "test:hostile:alias-menu-split-cost",
                }
            ],
            "source_object_sha256": SHA,
            "source_locator": "test:hostile:alias-menu-split",
        }
    ]
    result = optimize_protocol(request)
    base = _candidate(result, "base")
    attacked = _candidate(result, "split-menu-alias")
    assert attacked["candidate_protocol_sha256"] != base["candidate_protocol_sha256"]
    assert attacked["family_envelopes"] == base["family_envelopes"]
    assert result["pareto_frontier_candidate_ids"] == ["base"]
    deltas = result["mutation_effects"][0]["objective_deltas_from_base"]
    assert {row["delta"] for row in deltas} == {0.0}


def test_unknown_global_covariance_preserves_known_single_bundle_lower_bound() -> None:
    request = _request()
    request["base_protocol"]["measurement_geometry"]["joint_covariance_authority"] = {
        "state": "unknown",
        "reason": "joint signal covariance is not registered",
        "source_object_sha256": SHA,
        "source_locator": "test:unknown-joint-covariance",
    }

    result = optimize_protocol(request)
    assert result["feasible_candidate_count"] == 2
    assert result["pareto_frontier_candidate_ids"] == ["base", "more-outcome-events"]
    for candidate in result["candidates"]:
        objective = next(
            row for row in candidate["objective_values"] if row["objective_id"] == "intensive-depth"
        )
        assert objective["value_state"] == "resolved"
        assert objective["value"] > 0
        intensive = candidate["capacity_result"]["scenarios"][0]["families"]["intensive"]
        assert intensive["resolution_state"] == "resolved"
        assert all(
            row["observer_resolution_state"] == "resolved"
            for row in intensive["bundle_ledger"]
        )
    delta = next(
        row
        for row in result["mutation_effects"][0]["objective_deltas_from_base"]
        if row["objective_id"] == "intensive-depth"
    )
    assert delta == {
        "objective_id": "intensive-depth",
        "delta_state": "resolved",
        "delta": 0.0,
    }


def test_partially_resolved_compiler_envelope_is_unknown_not_orderable_extremum() -> None:
    capacity = {
        "family_envelopes": {
            "intensive.maximum_joint_bundle_log10_contraction": {
                "resolution_state": "unresolved",
                "minimum": 1.25,
                "maximum": 2.5,
                "resolved_scenario_count": 1,
                "total_scenario_count": 2,
            }
        }
    }
    objective = {
        "family_path": "intensive.maximum_joint_bundle_log10_contraction",
        "envelope_bound": "maximum",
    }

    assert _objective_value(capacity, objective) == {
        "value_state": "unknown",
        "value": None,
        "reason": (
            "compiler envelope 'intensive.maximum_joint_bundle_log10_contraction' is "
            "unresolved for one or more scenarios; the optimizer cannot substitute or "
            "order an unknown coordinate"
        ),
        "compiler_resolution_state": "unresolved",
        "resolved_scenario_count": 1,
        "total_scenario_count": 2,
    }


@pytest.mark.parametrize("field", ["base_amount", "maximum_amount"])
def test_negative_resource_constraint_fails(field: str) -> None:
    request = _request()
    request["resource_constraints"][0][field] = -1
    with pytest.raises(ProtocolOptimizerError):
        optimize_protocol(request)


def test_negative_mutation_resource_delta_fails() -> None:
    request = _request()
    request["mutations"][0]["resource_deltas"][0]["amount"] = -0.01
    with pytest.raises(ProtocolOptimizerError):
        optimize_protocol(request)


def test_sub_ulp_resource_delta_cannot_hide_large_geometry_gain() -> None:
    request = _request()
    request["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/1/participant_count",
            "value": _exact(1_000_000_000),
        }
    ]
    request["mutations"][0]["resource_deltas"][0]["amount"] = 1e-300

    with pytest.raises(
        ProtocolOptimizerError,
        match="below representable resolution at the current total",
    ):
        optimize_protocol(request)


def test_positive_resource_delta_at_one_ulp_is_preserved_in_pareto_ledger() -> None:
    request = _request()
    increment = math.nextafter(100.0, math.inf) - 100.0
    request["mutations"][0]["resource_deltas"][0]["amount"] = increment

    result = optimize_protocol(request)
    base = _candidate(result, "base")
    mutated = _candidate(result, "more-outcome-events")
    assert base["resource_totals"][0]["total_amount"] == 100.0
    assert mutated["resource_totals"][0]["total_amount"] == math.nextafter(100.0, math.inf)
    assert float(mutated["resource_totals"][0]["total_amount_decimal"]) > 100.0
    assert result["pareto_frontier_candidate_ids"] == ["base", "more-outcome-events"]


def test_resource_accumulation_overflow_is_rejected() -> None:
    request = _request()
    request["resource_constraints"][0]["base_amount"] = 1e308
    request["resource_constraints"][0]["maximum_amount"] = 1.7e308
    request["mutations"][0]["resource_deltas"][0]["amount"] = 1e308

    with pytest.raises(ProtocolOptimizerError, match="overflows resource 'cost'"):
        optimize_protocol(request)


def test_combined_mutations_cannot_cross_into_a_coarser_ulp_for_free() -> None:
    request = _request()
    base_amount = math.nextafter(128.0, -math.inf)
    # Each 1e-14 delta independently moves the serialized total from the
    # predecessor of 128 to 128.  After the first delta, the second falls below
    # the wider ULP above the power-of-two boundary and must not disappear.
    increment = 1e-14
    request["resource_constraints"][0]["base_amount"] = base_amount
    request["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/1/participant_count",
            "value": _exact(101),
        }
    ]
    request["mutations"][0]["resource_deltas"][0]["amount"] = increment
    second = copy.deepcopy(request["mutations"][0])
    second["mutation_id"] = "more-baseline-participants"
    second["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/0/participant_count",
            "value": _exact(101),
        }
    ]
    request["mutations"].append(second)
    request["maximum_mutations_per_candidate"] = 2
    request["candidate_limit"] = 4

    with pytest.raises(
        ProtocolOptimizerError,
        match="below representable resolution at the current total 128.0",
    ):
        optimize_protocol(request)


def test_order_sensitive_sibling_list_edits_fail_closed() -> None:
    request = _request()
    template = request["mutations"][0]
    alias_a = copy.deepcopy(request["base_protocol"]["measurement_geometry"]["signals"][0])
    alias_a["signal_id"] = "signal-alias-a"
    alias_b = copy.deepcopy(alias_a)
    alias_b["signal_id"] = "signal-alias-b"
    first = copy.deepcopy(template)
    first["mutation_id"] = "insert-signal-at-zero"
    first["protocol_operations"] = [
        {
            "op": "add",
            "path": "/measurement_geometry/signals/0",
            "value": alias_a,
        }
    ]
    second = copy.deepcopy(template)
    second["mutation_id"] = "insert-signal-at-one"
    second["protocol_operations"] = [
        {
            "op": "add",
            "path": "/measurement_geometry/signals/1",
            "value": alias_b,
        }
    ]
    request["mutations"] = [first, second]
    request["maximum_mutations_per_candidate"] = 2
    request["candidate_limit"] = 4

    with pytest.raises(ProtocolOptimizerError, match="order-sensitive sibling list edits"):
        optimize_protocol(request)


@pytest.mark.parametrize("token", ["01", "+1", "-0", "1.0"])
def test_noncanonical_json_pointer_array_tokens_fail_closed(token: str) -> None:
    request = _request()
    request["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": (
                f"/measurement_geometry/participant_event_schedules/{token}/events_per_participant"
            ),
            "value": _exact(8),
        }
    ]
    with pytest.raises(ProtocolOptimizerError, match="noncanonical JSON pointer array"):
        optimize_protocol(request)


def test_invalid_pointer_escapes_and_normalized_overlap_attack_fail_closed() -> None:
    invalid_escape = _request()
    invalid_escape["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/~2",
            "value": {},
        }
    ]
    with pytest.raises(ProtocolOptimizerError, match="noncanonical escape"):
        optimize_protocol(invalid_escape)

    overlap = _request()
    second = copy.deepcopy(overlap["mutations"][0])
    second["mutation_id"] = "normalized-overlap"
    second["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/01/events_per_participant",
            "value": _exact(16),
        }
    ]
    overlap["mutations"].append(second)
    overlap["maximum_mutations_per_candidate"] = 2
    overlap["candidate_limit"] = 4
    with pytest.raises(ProtocolOptimizerError, match="noncanonical JSON pointer array"):
        optimize_protocol(overlap)


def test_base_is_a_reserved_mutation_identifier() -> None:
    request = _request()
    request["mutations"][0]["mutation_id"] = "base"
    with pytest.raises(ProtocolOptimizerError, match="reserved"):
        optimize_protocol(request)


def test_resource_sources_are_dated_and_never_promoted_to_verified() -> None:
    request = _request()
    request["resource_constraints"][0]["as_of"] = "not-a-date"
    with pytest.raises(ProtocolOptimizerError, match="ISO calendar date"):
        optimize_protocol(request)

    result = optimize_protocol(_request())
    assert result["source_binding_state"] == {
        "protocol_geometry": "compiler_bound_protocol_hash",
        "resource_constraints": "caller_declared_not_content_verified",
        "mutation_evidence": "caller_declared_not_content_verified",
    }


def test_resource_infeasible_candidate_is_excluded_from_pareto_frontier() -> None:
    request = _request()
    request["resource_constraints"][0]["maximum_amount"] = 499.0
    result = optimize_protocol(request)
    assert _candidate(result, "base")["constraint_eligible"] is True
    assert _candidate(result, "more-outcome-events")["constraint_eligible"] is False
    assert result["pareto_frontier_candidate_ids"] == ["base"]


def test_conditional_protocol_mutation_emits_recompiled_scenario_envelope() -> None:
    request = _request()
    request["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/1/participant_count",
            "value": {
                "state": "conditional",
                "scenario_group_id": "outcome-cohort-size",
                "scenarios": [
                    {"scenario_id": "funded", "value": 200},
                    {"scenario_id": "minimum", "value": 100},
                ],
            },
        }
    ]
    result = optimize_protocol(request)
    candidate = _candidate(result, "more-outcome-events")
    envelope = candidate["family_envelopes"]["extensive.retained_participant_events"]
    assert candidate["scenario_count"] == 2
    assert envelope["maximum"] > envelope["minimum"]
    assert candidate["capacity_result"]["scenario_count"] == 2


def test_candidate_cap_is_fail_closed_before_enumeration() -> None:
    request = _request()
    template = request["mutations"][0]
    request["mutations"] = []
    for index in range(14):
        mutation = copy.deepcopy(template)
        mutation["mutation_id"] = f"candidate-{index:02d}"
        mutation["protocol_operations"] = [
            {
                "op": "replace",
                "path": "/measurement_geometry/participant_event_schedules/1/events_per_participant",
                "value": _exact(index + 5),
            }
        ]
        request["mutations"].append(mutation)
    request["maximum_mutations_per_candidate"] = 14
    request["candidate_limit"] = MAX_CANDIDATES
    assert sum(math.comb(14, size) for size in range(15)) == 16_384
    with pytest.raises(ProtocolOptimizerError, match="expands to 16384 candidates"):
        optimize_protocol(request)


def test_zero_mutation_depth_is_a_typed_deterministic_base_only_audit() -> None:
    request = _request()
    request["maximum_mutations_per_candidate"] = 0
    request["candidate_limit"] = 1

    first = optimize_protocol(request)
    second = optimize_protocol(request)
    assert first == second
    assert first["candidate_count"] == 1
    assert first["feasible_candidate_count"] == 1
    assert [row["candidate_id"] for row in first["candidates"]] == ["base"]
    assert first["pareto_frontier_candidate_ids"] == ["base"]
    assert first["mutation_effects"] == [
        {
            "mutation_id": "more-outcome-events",
            "source_object_sha256": SHA,
            "source_locator": "test:amendment:more-outcome-events",
            "effect_state": "not_evaluated_search_depth_zero",
            "candidate_generated": False,
            "reason": (
                "maximum_mutations_per_candidate is zero; only the base protocol "
                "is inside the declared search space"
            ),
            "resource_deltas": request["mutations"][0]["resource_deltas"],
        }
    ]
    schema = json.loads(
        (ROOT / "schemas/v2/optimizer-protocol-result.schema.json").read_text(encoding="utf-8")
    )
    assert not list(Draft202012Validator(schema).iter_errors(first))


def test_replay_is_deterministic_and_custom_unverified_gate_propagates() -> None:
    first = optimize_protocol(_request())
    second = optimize_protocol(_request())
    assert first == second
    assert first["comparison_eligible"] is False
    assert first["public_rank_emission_permitted"] is False
    assert first["overall_scalar"] is None
    assert all(row["comparison_eligible"] is False for row in first["candidates"])
    assert all(row["ontology_binding_state"] == "custom_unverified" for row in first["candidates"])
    assert len({row["replay_sha256"] for row in first["candidates"]}) == first["candidate_count"]

    schema = json.loads(
        (ROOT / "schemas/v2/optimizer-protocol-result.schema.json").read_text(encoding="utf-8")
    )
    assert not list(Draft202012Validator(schema).iter_errors(first))


def test_old_optimizer_contract_and_hidden_aggregation_are_rejected() -> None:
    request = _request()
    request["suite_patch"] = {"anything": "forbidden"}
    with pytest.raises(ProtocolOptimizerError):
        optimize_protocol(request)

    result = optimize_protocol(_request())
    keys = _walk_keys(result)
    assert "suite_patch" not in keys
    assert "weights" not in keys
    assert "score" not in keys
    assert "rank" not in keys
    assert result["anti_gaming_contract"] == {
        "all_candidates_recompiled_from_protocol_geometry": True,
        "direct_family_result_patch_accepted": False,
        "weighted_aggregate_emitted": False,
        "stable_rank_emitted": False,
        "exact_decimal_resource_accumulation": True,
        "nonrepresentable_positive_resource_delta_accepted": False,
        "order_sensitive_sibling_list_edits_accepted": False,
        "noncanonical_json_pointer_array_tokens_accepted": False,
        "normalized_overlapping_mutations_accepted": False,
        "reserved_base_mutation_id_accepted": False,
        "custom_unverified_comparison_eligibility_propagated": True,
        "candidate_cap": 10000,
    }


def test_mutation_requires_positive_sourced_resources_and_resources_enter_pareto() -> None:
    request = _request()
    request["mutations"][0]["resource_deltas"] = []
    with pytest.raises(ProtocolOptimizerError):
        optimize_protocol(request)

    request = _request()
    request["mutations"][0]["protocol_operations"] = [
        {
            "op": "replace",
            "path": "/measurement_geometry/participant_event_schedules/1/source_locator",
            "value": "test:only-a-source-label-change",
        }
    ]
    result = optimize_protocol(request)
    assert result["pareto_frontier_candidate_ids"] == ["base"]


def test_opposing_duplicate_objectives_on_one_family_envelope_are_rejected() -> None:
    request = _request()
    request["objectives"].append(
        {
            "objective_id": "retained-events-opposite",
            "family_path": "extensive.retained_participant_events",
            "envelope_bound": "minimum",
            "direction": "minimize",
        }
    )
    with pytest.raises(ProtocolOptimizerError, match="opposing duplicate objectives"):
        optimize_protocol(request)


def test_public_api_wrapper_replays_the_protocol_native_optimizer() -> None:
    assert optimize_protocol_design_v2(_request()) == optimize_protocol(_request())


def test_protocol_optimizer_cli_writes_exact_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "optimizer.json"
    output = tmp_path / "optimizer-result.json"
    source.write_text(json.dumps(_request()), encoding="utf-8")
    assert main(["v2-optimize-protocol", str(source), "--out", str(output), "--pretty"]) == 0
    receipt = json.loads(capsys.readouterr().out)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["optimizer_request_sha256"] == result["optimizer_request_sha256"]
    assert result == optimize_protocol(_request())


def _post_optimizer(payload: dict) -> tuple[int, dict]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/v2/optimize-protocol",
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


def test_studio_optimizer_endpoint_executes_and_rejects_old_contract() -> None:
    status, result = _post_optimizer(_request())
    assert status == 200
    assert result["pareto_frontier_candidate_ids"] == ["base", "more-outcome-events"]

    invalid = _request()
    invalid["suite_patch"] = {"extensive": "fake"}
    status, result = _post_optimizer(invalid)
    assert status == 400
    assert "Additional properties" in result["error"]
