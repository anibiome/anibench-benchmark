from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from anibench.cli import main
from anibench.contracts_v2 import (
    ContractValidationError,
    validate_contract_bundle,
    validate_contract_bundle_strict,
)
from test_v2_contracts import event_fixture, intervention_fixture, uncertainty_fixture


def _report(
    *,
    event: dict[str, Any] | None = None,
    intervention: dict[str, Any] | None = None,
    uncertainty: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_contract_bundle(
        event or event_fixture(),
        intervention or intervention_fixture(),
        uncertainty or uncertainty_fixture(),
    )


def _error_ids(report: dict[str, Any]) -> set[str]:
    return {row["check_id"] for row in report["errors"]}


def test_valid_bundle_executes_semantics_defers_nonexact_and_computes_matrix_rank() -> None:
    report = _report()
    assert report["semantic_valid"] is True
    assert report["exact_semantic_complete"] is False
    assert report["validation_state"] == "valid_with_deferred_checks"
    states = {row["coordinate_state"] for row in report["deferred_semantic_checks"]}
    assert {"interval", "unknown", "distribution"} <= states
    target_count = [
        row
        for row in report["deferred_semantic_checks"]
        if row["coordinate_id"] == "target-count-b"
    ]
    assert target_count and target_count[0]["coordinate_state"] == "unknown"

    ranks = {row["contrast_matrix_id"]: row for row in report["computed_contrast_ranks"]}
    assert ranks["matrix-policy"]["rank"] == 1
    assert ranks["matrix-component"]["rank"] == 3
    assert ranks["matrix-sequential"]["rank"] == 3
    assert all(row["rank_source"] == "server_computed_from_matrix_values" for row in ranks.values())
    assert report["validation_policy"] == {
        "schema_only_acceptance_permitted": False,
        "nonexact_coordinates_treated_as_exact": False,
        "arm_count_used_as_contrast_rank": False,
    }


@pytest.mark.parametrize(
    ("collection", "id_field"),
    [
        ("participant_sets", "participant_set_id"),
        ("time_bases", "time_basis_id"),
        ("measurement_modules", "measurement_module_id"),
        ("event_types", "event_type_id"),
        ("joint_event_hyperedges", "hyperedge_id"),
        ("covariance_groups", "covariance_group_id"),
        ("source_receipts", "source_receipt_id"),
    ],
)
def test_event_collection_ids_must_be_unique(collection: str, id_field: str) -> None:
    event = event_fixture()
    event[collection].append(deepcopy(event[collection][0]))
    report = _report(event=event)
    assert report["semantic_valid"] is False
    assert "unique_ids" in _error_ids(report)
    assert any(id_field in row["message"] for row in report["errors"])


def test_intervention_id_and_hash_are_an_atomic_null_pair() -> None:
    event = event_fixture()
    event["intervention_design_sha256"] = None
    report = _report(event=event)
    assert "intervention_binding_null_pair" in _error_ids(report)

    event = event_fixture()
    event["intervention_design_id"] = None
    report = _report(event=event)
    assert "intervention_binding_null_pair" in _error_ids(report)


def test_every_coordinate_reference_must_resolve() -> None:
    event = event_fixture()
    event["measurement_modules"][0]["target_count"] = {
        "uncertainty_coordinate_id": "missing-coordinate"
    }
    report = _report(event=event)
    assert "uncertainty_coordinate_resolution" in _error_ids(report)
    assert any(
        row["path"].endswith("/measurement_modules/0/target_count") for row in report["errors"]
    )

    intervention = intervention_fixture()
    intervention["outcome_support"][0]["missingness_coordinate_id"] = "missing"
    report = _report(intervention=intervention)
    assert "uncertainty_coordinate_resolution" in _error_ids(report)


def test_joint_participant_and_event_counts_cannot_exceed_exact_marginals() -> None:
    event = event_fixture()
    uncertainty = uncertainty_fixture()
    uncertainty["coordinates"]["joint-participant-count"] = deepcopy(
        uncertainty["coordinates"]["participant-count"]
    )
    uncertainty["coordinates"]["joint-participant-count"]["value"] = 201
    event["joint_event_hyperedges"][0]["joint_participant_count"] = {
        "uncertainty_coordinate_id": "joint-participant-count"
    }
    report = _report(event=event, uncertainty=uncertainty)
    assert "joint_participant_marginal_bound" in _error_ids(report)

    uncertainty = uncertainty_fixture()
    uncertainty["coordinates"]["joint-event-count"]["value"] = 2401
    report = _report(uncertainty=uncertainty)
    assert "joint_event_marginal_bound" in _error_ids(report)


def test_nonexact_marginals_defer_comparison_instead_of_using_nominal() -> None:
    uncertainty = uncertainty_fixture()
    uncertainty["coordinates"]["participant-count"] = {
        "state": "interval",
        "unit": "people",
        "evidence_class": "protocol_document_extracted",
        "source_receipt_ids": ["source-01"],
        "lower": 150,
        "upper": 250,
        "lower_inclusive": True,
        "upper_inclusive": True,
        "nominal": 200,
    }
    report = _report(uncertainty=uncertainty)
    assert "joint_participant_marginal_bound" not in _error_ids(report)
    deferred = [
        row
        for row in report["deferred_semantic_checks"]
        if row["coordinate_id"] == "participant-count"
    ]
    assert deferred
    assert all(row["coordinate_state"] == "interval" for row in deferred)


def test_one_physical_measurement_lineage_cannot_enter_one_joint_event_twice() -> None:
    event = event_fixture()
    event["measurement_modules"][1]["feature_ancestry_id"] = event["measurement_modules"][0][
        "feature_ancestry_id"
    ]
    report = _report(event=event)
    assert "joint_measurement_lineage_uniqueness" in _error_ids(report)


def test_covariance_event_and_module_links_must_resolve_and_be_reciprocal() -> None:
    event = event_fixture()
    event["measurement_modules"][0]["covariance_group_id"] = "missing-covariance"
    report = _report(event=event)
    assert "reference_resolution" in _error_ids(report)

    event = event_fixture()
    event["covariance_groups"][0]["member_measurement_module_ids"] = ["module-a"]
    report = _report(event=event)
    assert "covariance_membership_reciprocity" in _error_ids(report)

    event = event_fixture()
    event["event_types"][0]["measurement_module_ids"] = ["module-a"]
    report = _report(event=event)
    assert "event_module_reciprocity" in _error_ids(report)
    assert "hyperedge_event_module_support" in _error_ids(report)


@pytest.mark.parametrize(
    ("family", "mutation", "expected_check"),
    [
        (
            "component",
            lambda matrix: matrix["values"].append([0, 0, 0, 0]),
            "contrast_matrix_row_dimension",
        ),
        (
            "component",
            lambda matrix: matrix["values"].__setitem__(0, [1, 0, -1]),
            "contrast_matrix_column_dimension",
        ),
        (
            "policy",
            lambda matrix: matrix["column_ids"].reverse(),
            "contrast_matrix_column_binding",
        ),
        (
            "policy",
            lambda matrix: matrix["policy_ids"].__setitem__(0, "missing-policy"),
            "reference_resolution",
        ),
    ],
)
def test_contrast_matrix_dimensions_and_declared_ids_are_executable_semantics(
    family: str, mutation: Any, expected_check: str
) -> None:
    intervention = intervention_fixture()
    mutation(intervention["contrast_matrices"][family][0])
    report = _report(intervention=intervention)
    assert expected_check in _error_ids(report)


def test_assignment_stage_probability_and_alternative_semantics_are_checked() -> None:
    intervention = intervention_fixture()
    intervention["assignment_stages"][0]["alternative_ids"][0] = "missing-alternative"
    report = _report(intervention=intervention)
    assert "reference_resolution" in _error_ids(report)

    intervention = intervention_fixture()
    intervention["assignment_stages"][0]["decision_event_type_id"] = "missing-event"
    report = _report(intervention=intervention)
    assert "reference_resolution" in _error_ids(report)

    uncertainty = uncertainty_fixture()
    uncertainty["coordinates"]["assignment-p-a"]["value"] = 0.7
    report = _report(uncertainty=uncertainty)
    assert "assignment_probability_sum" in _error_ids(report)

    intervention = intervention_fixture()
    intervention["assignment_stages"][0]["assignment_probability_coordinate_ids"] = []
    report = _report(intervention=intervention)
    assert "randomized_assignment_probability_required" in _error_ids(report)


def test_nonexact_assignment_probability_is_deferred_not_summed_as_a_point() -> None:
    uncertainty = uncertainty_fixture()
    uncertainty["coordinates"]["assignment-p-a"] = {
        "state": "interval",
        "unit": "fraction",
        "evidence_class": "protocol_document_extracted",
        "source_receipt_ids": ["source-01"],
        "lower": 0.4,
        "upper": 0.6,
        "lower_inclusive": True,
        "upper_inclusive": True,
        "nominal": 0.5,
    }
    report = _report(uncertainty=uncertainty)
    assert "assignment_probability_sum" not in _error_ids(report)
    assert any(
        row["coordinate_id"] == "assignment-p-a" and row["coordinate_state"] == "interval"
        for row in report["deferred_semantic_checks"]
    )


@pytest.mark.parametrize(
    ("collection", "field", "bad_value"),
    [
        ("estimands", "population_participant_set_id", "missing-participants"),
        ("estimands", "outcome_support_id", "missing-outcome"),
        ("estimands", "treatment_condition_ids", ["missing-treatment"]),
        ("outcome_support", "event_type_ids", ["missing-event"]),
        ("outcome_support", "measurement_module_ids", ["missing-module"]),
        ("outcome_support", "participant_set_id", "missing-participants"),
    ],
)
def test_estimand_and_outcome_references_resolve(
    collection: str, field: str, bad_value: Any
) -> None:
    intervention = intervention_fixture()
    intervention[collection][0][field] = bad_value
    report = _report(intervention=intervention)
    assert "reference_resolution" in _error_ids(report)


def test_bundle_identity_bindings_are_checked() -> None:
    intervention = intervention_fixture()
    intervention["event_manifest_id"] = "other-event"
    report = _report(intervention=intervention)
    assert "event_manifest_binding" in _error_ids(report)

    intervention = intervention_fixture()
    intervention["uncertainty_model_id"] = "other-uncertainty"
    report = _report(intervention=intervention)
    assert "uncertainty_model_binding" in _error_ids(report)

    intervention = intervention_fixture()
    intervention["study_id"] = "other-study"
    report = _report(intervention=intervention)
    assert "study_binding" in _error_ids(report)


def test_source_receipt_references_resolve() -> None:
    event = event_fixture()
    event["measurement_modules"][0]["source_receipt_ids"] = ["missing-receipt"]
    report = _report(event=event)
    assert "reference_resolution" in _error_ids(report)

    uncertainty = uncertainty_fixture()
    uncertainty["coordinates"]["participant-count"]["source_receipt_ids"] = ["missing-receipt"]
    report = _report(uncertainty=uncertainty)
    assert "reference_resolution" in _error_ids(report)


def test_strict_validator_raises_with_the_full_machine_report() -> None:
    event = event_fixture()
    event["event_types"][0]["participant_set_id"] = "missing"
    with pytest.raises(ContractValidationError) as caught:
        validate_contract_bundle_strict(event, intervention_fixture(), uncertainty_fixture())
    assert caught.value.report["semantic_valid"] is False
    assert caught.value.report["errors"]


def _write_bundle(tmp_path: Path, event: dict[str, Any]) -> tuple[Path, Path, Path]:
    event_path = tmp_path / "event.json"
    intervention_path = tmp_path / "intervention.json"
    uncertainty_path = tmp_path / "uncertainty.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    intervention_path.write_text(json.dumps(intervention_fixture()), encoding="utf-8")
    uncertainty_path.write_text(json.dumps(uncertainty_fixture()), encoding="utf-8")
    return event_path, intervention_path, uncertainty_path


def test_contract_validation_cli_returns_machine_report_and_nonzero_on_error(
    tmp_path: Path, capsys: Any
) -> None:
    event_path, intervention_path, uncertainty_path = _write_bundle(tmp_path, event_fixture())
    arguments = [
        "v2-validate-contracts",
        "--event-manifest",
        str(event_path),
        "--intervention-design",
        str(intervention_path),
        "--uncertainty",
        str(uncertainty_path),
    ]
    assert main(arguments) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["validation_state"] == "valid_with_deferred_checks"
    assert report["computed_contrast_ranks"]

    invalid = event_fixture()
    invalid["measurement_modules"][0]["covariance_group_id"] = "missing"
    event_path.write_text(json.dumps(invalid), encoding="utf-8")
    assert main(arguments) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["validation_state"] == "invalid"
    assert report["errors"]
