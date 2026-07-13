from __future__ import annotations

import json
import threading
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from jsonschema import Draft202012Validator

from anibench import compile_trial_design_v2
from anibench.cli import main
from anibench.design_v2 import DesignInputError, compile_design, validate_design_input
from anibench.studio import StudioHandler


ROOT = Path(__file__).resolve().parents[1]
COORDINATE_TABLE = ROOT / "data" / "source_projections" / "v2" / "SOURCE_COORDINATE_TABLE.csv"


def _fixture() -> dict[str, Any]:
    return {
        "contract": "anibench.design-input.v2-candidate1",
        "assessment_lane": "design_preview",
        "study_id": "future-deep-trial",
        "name": "Future deep personalized trial",
        "population": {
            "value": 200,
            "state": "exact",
            "semantics": "planned_enrollment",
        },
        "duration": {
            "value": 365,
            "state": "exact",
            "semantics": "intervention_duration_days",
        },
        "policy_arms": 2,
        "randomized_policy": True,
        "concurrent_control": True,
        "adaptive_reassignment": True,
        "within_policy_randomized": False,
        "operator_families": ["nutrition", "exercise", "supplement"],
        "measurement_modules": [
            {
                "module_id": "metabolomics",
                "label": "Metabolomics",
                "evidence_state": "exact",
                "events_per_participant": 3,
            },
            {
                "module_id": "wearable",
                "label": "Wearable summaries",
                "evidence_state": "conditional",
                "events_per_participant": 365,
            },
        ],
    }


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, (*path, str(index)))


def test_design_compiler_emits_only_typed_self_declared_and_derived_coordinates() -> None:
    fixture = _fixture()
    result = compile_design(fixture)
    assert result == compile_trial_design_v2(fixture)
    assert result["contract"] == "anibench.design-assessment.v2-candidate1"
    assert result["claim_state"] == "implementation_candidate_biological_promotion_gated"
    assert result["promotion_allowed"] is False
    assert result["assessment_lane"] == {
        "value": "design_preview",
        "evidence_class": "self_declared",
        "source_json_pointers": ["/assessment_lane"],
    }
    assert result["coordinates"]["population"]["value"] == 200
    assert result["coordinates"]["population"]["semantics"] == "planned_enrollment"
    assert result["coordinates"]["duration"]["unit"] == "days"
    assert result["coordinates"]["causal_architecture"]["concurrent_control"]["value"] is True
    assert result["derived_coordinates"]["measurement_module_state_counts"] == {
        "exact": 1,
        "conditional": 1,
        "unknown": 0,
        "formula": "count(measurement_modules by evidence_state)",
        "source_json_pointers": ["/measurement_modules"],
        "evidence_class": "derived_from_self_declared_input",
    }


def test_participant_event_totals_require_typed_operands_and_carry_formula_pointers() -> None:
    result = compile_design(_fixture())
    totals = result["derived_coordinates"]["participant_event_totals_by_module"]
    assert totals[0] == {
        "module_id": "metabolomics",
        "value": 600,
        "state": "exact",
        "unit": "participant_events",
        "evidence_class": "derived_from_self_declared_input",
        "formula": {
            "expression": "population.value * measurement_modules[i].events_per_participant",
            "operands": [
                "/population/value",
                "/measurement_modules/0/events_per_participant",
            ],
            "state_operands": [
                "/population/state",
                "/measurement_modules/0/evidence_state",
            ],
        },
    }
    assert totals[1]["value"] == 73_000
    assert totals[1]["state"] == "conditional"
    aggregate = result["derived_coordinates"]["participant_module_observation_total"]
    assert aggregate["value"] == 73_600
    assert aggregate["state"] == "conditional"
    assert aggregate["unit"] == "participant_module_observations"
    assert aggregate["semantics"] == (
        "workload_count_across_modules_not_unique_joint_events_or_information"
    )

    unknown = _fixture()
    unknown["population"] = {
        "value": None,
        "state": "unknown",
        "semantics": "analyzable_population",
    }
    unknown_result = compile_design(unknown)
    assert unknown_result["derived_coordinates"]["participant_event_totals_by_module"] == []
    assert "participant_module_observation_total" not in unknown_result["derived_coordinates"]

    missing_events = _fixture()
    missing_events["measurement_modules"][0]["events_per_participant"] = None
    missing_result = compile_design(missing_events)
    totals = missing_result["derived_coordinates"]["participant_event_totals_by_module"]
    assert [row["module_id"] for row in totals] == ["wearable"]
    assert "participant_module_observation_total" not in missing_result["derived_coordinates"]


@pytest.mark.parametrize("field", ["population", "duration"])
def test_unknown_typed_coordinates_must_be_null(field: str) -> None:
    payload = _fixture()
    payload[field]["state"] = "unknown"
    with pytest.raises(DesignInputError, match=f"/{field}/value: must be null"):
        validate_design_input(payload)


def test_semantic_validation_rejects_impossible_or_ambiguous_design_claims() -> None:
    payload = _fixture()
    payload["policy_arms"] = 1
    with pytest.raises(DesignInputError, match="randomized_policy"):
        compile_design(payload)

    payload = _fixture()
    payload["measurement_modules"][0]["evidence_state"] = "unknown"
    with pytest.raises(DesignInputError, match="must be null when evidence_state is unknown"):
        compile_design(payload)

    payload = _fixture()
    payload["operator_families"] = ["Nutrition", "nutrition"]
    with pytest.raises(DesignInputError, match="unique after case folding"):
        compile_design(payload)

    payload = _fixture()
    payload["invented_default"] = 1
    with pytest.raises(DesignInputError, match="Additional properties are not allowed"):
        compile_design(payload)


def test_gates_and_upgrade_sets_are_structural_and_not_ordered_preferences() -> None:
    payload = _fixture()
    payload["assessment_lane"] = "registered"
    payload["duration"]["state"] = "conditional"
    payload["randomized_policy"] = None
    payload["concurrent_control"] = False
    payload["adaptive_reassignment"] = None
    payload["operator_families"] = []
    payload["measurement_modules"][0]["events_per_participant"] = 1
    result = compile_design(payload)
    gate_ids = {gate["gate_id"] for gate in result["open_gates"]}
    assert "resolve_duration_conditional" in gate_ids
    assert "resolve_randomized_policy" in gate_ids
    assert "declare_operator_families" in gate_ids
    assert "bind_assessment_lane_source_receipt" in gate_ids
    upgrades = result["structural_multiobjective_design_upgrades"]
    assert set(upgrades) == {
        "causal_identifiability",
        "temporal_resolution",
        "measurement_observability",
        "personalization_learning",
        "population_precision",
        "operator_identifiability",
    }
    assert result["upgrade_ordering_semantics"] == (
        "objective_group_then_identifier_not_preference"
    )


@pytest.mark.parametrize("lane", ["accessible", "demonstrated"])
def test_later_evidence_lanes_are_typed_without_changing_declared_geometry(lane: str) -> None:
    baseline = compile_design(_fixture())
    payload = _fixture()
    payload["assessment_lane"] = lane
    result = compile_design(payload)
    assert result["assessment_lane"]["value"] == lane
    assert result["coordinates"] == baseline["coordinates"]
    assert result["derived_coordinates"] == baseline["derived_coordinates"]
    assert "bind_assessment_lane_source_receipt" in {
        gate["gate_id"] for gate in result["open_gates"]
    }


def test_output_contains_no_biological_information_estimate_or_ordinal_value() -> None:
    result = compile_design(_fixture())
    forbidden_keys = {"score", "scores", "rank", "ranks", "tier", "percentile"}
    for path, _value in _walk(result):
        if path:
            assert path[-1].casefold() not in forbidden_keys
    assert result["emission_policy"] == {
        "composite_coordinate_emitted": False,
        "ordinal_position_emitted": False,
        "biological_information_inference_emitted": False,
        "missing_value_imputation_used": False,
    }


def test_v2_design_cli_stdout_and_file_output(tmp_path: Path, capsys: Any) -> None:
    source = tmp_path / "design.json"
    source.write_text(json.dumps(_fixture()), encoding="utf-8")
    assert main(["v2-design", str(source), "--pretty"]) == 0
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["contract"] == "anibench.design-assessment.v2-candidate1"

    output = tmp_path / "assessment.json"
    assert main(["v2-design", str(source), "--out", str(output)]) == 0
    written = json.loads(capsys.readouterr().out)
    assert written["written"] == str(output)
    assert json.loads(output.read_text())["study"]["study_id"] == "future-deep-trial"


def test_source_atlas_builder_is_exposed_without_duplicating_implementation(
    tmp_path: Path, capsys: Any
) -> None:
    output = tmp_path / "atlas"
    assert (
        main(
            [
                "build-v2-source-atlas",
                "--coordinate-table",
                str(COORDINATE_TABLE),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    response = json.loads(capsys.readouterr().out)
    assert response["written"] == str(output / "SOURCE_ATLAS_BUILD_RECEIPT.json")
    assert (output / "SOURCE_ATLAS_BUILD_RECEIPT.json").is_file()


def _post_design(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/v2/design",
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


def test_studio_v2_design_endpoint_compiles_and_rejects_invalid_inputs() -> None:
    status, result = _post_design(_fixture())
    assert status == 200
    assert result["contract"] == "anibench.design-assessment.v2-candidate1"

    invalid = deepcopy(_fixture())
    invalid["population"]["state"] = "unknown"
    status, result = _post_design(invalid)
    assert status == 400
    assert "/population/value" in result["error"]


def test_design_input_json_schema_accepts_the_canonical_fixture() -> None:
    schema = json.loads((ROOT / "schemas/v2/design-input.schema.json").read_text())
    assert schema["properties"]["contract"]["const"] == ("anibench.design-input.v2-candidate1")
    validate_design_input(_fixture())


def test_runtime_output_matches_the_exact_assessment_schema() -> None:
    schema = json.loads((ROOT / "schemas/v2/design-assessment.schema.json").read_text())
    Draft202012Validator(schema).validate(compile_design(_fixture()))

    partial = _fixture()
    partial["population"] = {
        "value": None,
        "state": "unknown",
        "semantics": "analyzable_population",
    }
    partial["policy_arms"] = None
    partial["randomized_policy"] = None
    partial["concurrent_control"] = None
    partial["measurement_modules"][0]["events_per_participant"] = None
    Draft202012Validator(schema).validate(compile_design(partial))


def test_openapi_binds_the_real_design_route_to_exact_json_schemas() -> None:
    text = (ROOT / "openapi/anibench-v2-candidate.yaml").read_text()
    assert "/api/v2/design:" in text
    assert "compileTrialDesignCandidate" in text
    assert "../schemas/v2/design-input.schema.json" in text
    assert "../schemas/v2/design-assessment.schema.json" in text
