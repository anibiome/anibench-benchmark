"""Contract, scientific counterexamples and independent numerical boundaries."""
from __future__ import annotations

import importlib.util
import itertools
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from anibench.cli import main
from anibench.paired_question_v1 import (
    INPUT_SCHEMA,
    digest,
    evaluate_paired_question,
    matrix,
    ols_risk,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paired_example", ROOT / "examples/paired_question/make_example.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def payload():
    return module.example()


def rebind(payload):
    for name in ("scenario", "design"):
        payload[name]["question_sha256"] = digest(payload["question"])


def test_example_and_installed_schema_agree(payload):
    schema = json.loads((ROOT / "schemas/paired_question/v1/input.schema.json").read_text())
    assert schema == INPUT_SCHEMA
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    result = evaluate_paired_question(payload)
    learning = result["conditional_functional_learning"]
    assert learning["baseline_function_and_molecular"]["expected_test_mse"] < learning["baseline_function"]["expected_test_mse"]
    assert learning["observed_held_out_prediction"]["state"] == "not_evaluated"
    assert result["public_rank_emission_permitted"] is False


def test_duplicates_metadata_and_planned_status_do_not_inflate(payload):
    base = evaluate_paired_question(payload)
    changed = deepcopy(payload)
    changed["design"]["observations"] *= 3
    changed["design"]["metadata"] = {"name": "Different identity", "cost": 1e10, "ethics": "approved"}
    changed["design"]["lifecycle"] = "planned"
    changed["design"]["support"]["collection_verified"] = None
    result = evaluate_paired_question(changed)
    assert result["calculation_sha256"] == base["calculation_sha256"]
    assert result["input_sha256"] != base["input_sha256"]
    assert result["canonical_acquisitions"] == base["canonical_acquisitions"]


@pytest.mark.parametrize("linked,expected", [(False, "not_supported"), (None, "unknown")])
def test_cross_domain_linkage_gates_only_relevant_questions(payload, linked, expected):
    base = evaluate_paired_question(payload)
    payload["design"]["support"]["cross_domain_linkage"] = linked
    result = evaluate_paired_question(payload)
    assert result["results"]["molecular_function_change_relation"]["state"] == expected
    assert result["conditional_functional_learning"]["baseline_function_and_molecular"]["state"] == expected
    assert result["results"]["function_state"] == base["results"]["function_state"]


@pytest.mark.parametrize("closed,expected", [(True, "not_supported"), (False, "unknown"), (None, "unknown")])
def test_absent_versus_unreported_function(payload, closed, expected):
    payload["design"]["closed_acquisition_inventory"] = closed
    payload["design"]["observations"] = [x for x in payload["design"]["observations"] if x["coordinate_id"] != "grip_force"]
    result = evaluate_paired_question(payload)
    assert result["results"]["function_state"]["state"] == expected


def test_observed_exposure_is_not_a_controlled_effect(payload):
    payload["design"]["support"]["controlled_assignment_identified"] = False
    result = evaluate_paired_question(payload)
    assert result["results"]["exposure_aligned_function_change"]["state"] != "not_supported"
    assert result["results"]["controlled_function_effect"]["state"] == "not_supported"


def test_two_people_cannot_buy_population_precision_with_spending(payload):
    base = evaluate_paired_question(payload)
    payload["design"]["n_independent_complete"] = 2
    payload["design"]["controlled_arm_counts"] = [1, 1]
    payload["design"]["metadata"]["cost"] = 100_000_000
    result = evaluate_paired_question(payload)
    assert result["results"]["function_state"] == base["results"]["function_state"]
    assert result["results"]["function_mean_change"]["worst_variance_ratio"] == pytest.approx(128 * base["results"]["function_mean_change"]["worst_variance_ratio"])
    assert result["conditional_functional_learning"]["baseline_function_and_molecular"]["state"] == "no_finite_expected_risk"


def test_false_dominates_unknown_support(payload):
    payload["scenario"]["measurement_error_covariance"] = None
    payload["design"]["support"]["operator_valid"] = False
    result = evaluate_paired_question(payload)
    assert result["results"]["molecular_state"]["state"] == "not_supported"


def test_realized_requires_verified_collection(payload):
    payload["design"]["lifecycle"] = "realized"
    payload["design"]["support"]["collection_verified"] = None
    assert evaluate_paired_question(payload)["results"]["function_state"]["state"] == "unknown"


@pytest.mark.parametrize("bad", [True, "1", float("nan"), float("inf")])
def test_nonnumeric_covariance_is_rejected(payload, bad):
    payload["scenario"]["biological_covariance"][0][0] = bad
    with pytest.raises(ValueError):
        evaluate_paired_question(payload)


@pytest.mark.parametrize("branch", ["question", "scenario", "design"])
def test_unknown_scientific_fields_rejected(payload, branch):
    payload[branch]["make_score_higher"] = True
    with pytest.raises(ValueError, match="schema"):
        evaluate_paired_question(payload)


def test_conflicting_physical_reuse_rejected(payload):
    payload["design"]["observations"][1]["physical_id"] = payload["design"]["observations"][0]["physical_id"]
    with pytest.raises(ValueError, match="Conflicting physical"):
        evaluate_paired_question(payload)


def test_unbound_question_rejected(payload):
    payload["question"]["occasions_days"][1] = 1
    with pytest.raises(ValueError, match="bind"):
        evaluate_paired_question(payload)


def test_tolerance_broadcast_rejected(payload):
    payload["question"]["tolerances"]["molecular_state"] = [1.0]
    rebind(payload)
    with pytest.raises(ValueError, match="tolerance"):
        evaluate_paired_question(payload)


def test_subnormal_error_is_not_erased(payload):
    tiny = np.nextafter(0.0, 1.0)
    assert matrix([[tiny]], 1, "tiny")[0, 0] == tiny
    payload["scenario"]["measurement_error_covariance"] = (np.eye(6) * tiny).tolist()
    payload["question"]["tolerances"]["function_state"] = [1e-162]
    rebind(payload)
    result = evaluate_paired_question(payload)["results"]["function_state"]
    assert result["state"] == "not_attained"
    assert result["worst_variance_ratio"] == pytest.approx(4.940656458412465)


def scale_units(payload, scale):
    for key in ("biological_covariance", "measurement_error_covariance"):
        payload["scenario"][key] = (np.asarray(payload["scenario"][key]) * scale**2).tolist()
    for key, values in payload["question"]["tolerances"].items():
        factor = scale**2 if key == "change_cross_covariance" else scale
        payload["question"]["tolerances"][key] = [x * factor for x in values]
    for coordinate in payload["question"]["coordinates"]:
        coordinate["unit"] = f"rescaled-{scale}-{coordinate['unit']}"
    rebind(payload)


def test_ordinary_unit_conversion_preserves_adequacy(payload):
    baseline = evaluate_paired_question(payload)
    scale_units(payload, 1000)
    result = evaluate_paired_question(payload)
    for key, row in baseline["results"].items():
        assert result["results"][key]["worst_variance_ratio"] == pytest.approx(row["worst_variance_ratio"])


def test_extreme_unit_underflow_cannot_create_attainment(payload):
    payload["design"]["n_independent_complete"] = 4
    payload["design"]["controlled_arm_counts"] = [2, 2]
    baseline = evaluate_paired_question(payload)["results"]["molecular_function_change_relation"]
    assert baseline["state"] == "not_attained"
    scale_units(payload, 1e-100)
    result = evaluate_paired_question(payload)["results"]["molecular_function_change_relation"]
    assert result["state"] == "unknown"
    assert result["adequacy_percent"] == {"lower": 0, "upper": 100}


def test_ols_overflow_is_unknown_and_small_n_is_not_universal_failure():
    assert ols_risk(np.diag([1.0, 1e308]), [0], 1, 4)["state"] == "unknown"
    assert ols_risk(np.eye(2), [0], 1, 3)["state"] == "no_finite_expected_risk"
    assert ols_risk(np.eye(2), [], 1, 3)["expected_test_mse"] == pytest.approx(4 / 3)


def test_invalid_covariance_cannot_pass_through_nonfinite_eigenvalues():
    with pytest.raises(ValueError):
        matrix([[1e-308, 1], [1, 1e-308]], 2, "invalid")


def test_mean_and_contrast_underflow_cannot_create_attainment(payload):
    tiny = np.nextafter(0.0, 1.0)
    for key in ("biological_covariance", "measurement_error_covariance"):
        payload["scenario"][key] = (np.eye(6) * tiny).tolist()
    for key in ("function_mean_change", "controlled_function_effect"):
        payload["question"]["tolerances"][key] = [1e-164]
    rebind(payload)
    result = evaluate_paired_question(payload)
    for key in ("function_mean_change", "exposure_aligned_function_change", "controlled_function_effect"):
        assert result["results"][key]["state"] == "unknown"
    payload["design"]["support"]["controlled_assignment_identified"] = False
    assert evaluate_paired_question(payload)["results"]["controlled_function_effect"]["state"] == "not_supported"


def test_cli_private_input_and_existing_output_preserved(payload, tmp_path, capsys):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload))
    original = source.read_bytes()
    assert main(["paired-question", str(source), "--out", str(source)]) == 2
    assert source.read_bytes() == original
    output = tmp_path / "result.json"
    assert main(["paired-question", str(source), "--out", str(output)]) == 0
    result = output.read_bytes()
    assert main(["paired-question", str(source), "--out", str(output)]) == 2
    assert output.read_bytes() == result
    assert json.loads(result)["receipt_sha256"] == evaluate_paired_question(payload)["receipt_sha256"]
    captured = capsys.readouterr()
    assert str(source) not in captured.err
    assert str(output) not in captured.err


def bayes_mse(rows, inputs):
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[i] for i in inputs), []).append(row[2])
    return sum(sum((np.asarray(values) - np.mean(values))**2) for values in groups.values()) / len(rows)


def test_nonlinear_complementarity_cannot_be_inferred_from_covariance():
    linked = np.asarray([(a, b, a * b) for a, b in itertools.product((-1, 1), repeat=2)])
    unrelated = np.asarray(list(itertools.product((-1, 1), repeat=3)))
    np.testing.assert_allclose(np.cov(linked, rowvar=False, bias=True), np.cov(unrelated, rowvar=False, bias=True))
    assert bayes_mse(linked, [0]) == bayes_mse(linked, [1]) == 1
    assert bayes_mse(linked, [0, 1]) == 0
    assert bayes_mse(unrelated, [0, 1]) == 1
