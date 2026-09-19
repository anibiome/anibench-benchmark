# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Synthetic target mechanics and claim-boundary tests; no calibrated biological tasks."""

import copy

import numpy as np
import pytest

from anibench.finite_tasks_v1 import FiniteTaskError, evaluate_finite_task, finite_task_sha256
from anibench.information_v2 import (
    EventContribution,
    event_information,
    posterior_reference_diagnostic,
)


@pytest.fixture
def submission():
    task = {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": "synthetic-two-functionals",
        "task_version": "1",
        "source_sha256": "sha256:" + "a" * 64,
        "model_sha256": "sha256:" + "b" * 64,
        "target_population": "synthetic population",
        "estimand": "two declared Gaussian linear functionals",
        "horizon": "one modeled occasion",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["unit A", "unit B"],
        "prior_precision": [[1, 0], [0, 1]],
        "required_support": [
            {"domain_id": "molecular", "role": "observation"},
            {"domain_id": "neural", "role": "observation"},
        ],
        "functionals": [
            {
                "functional_id": "first",
                "coefficients": [1, 0],
                "unit": "unit A",
                "variance_limit": 0.5,
            },
            {
                "functional_id": "second",
                "coefficients": [0, 1],
                "unit": "unit B",
                "variance_limit": 0.5,
            },
        ],
    }
    return {
        "contract": "anibench.finite-task-request.v1",
        "task": task,
        "task_sha256": finite_task_sha256(task),
        "evidence": {
            "identifiability": True,
            "collection_verified": None,
            "support": [{**row, "supported": True} for row in task["required_support"]],
        },
        "geometry": {"model_sha256": task["model_sha256"], "information_matrix": [[1, 0], [0, 1]]},
    }


def freeze(submission):
    submission["task_sha256"] = finite_task_sha256(submission["task"])
    return submission


def test_planned_precision_requires_no_outcome_or_learning_evidence(submission):
    submission["evidence"]["collection_verified"] = False
    result = evaluate_finite_task(submission)
    assert result["attainment"] == "attained"
    assert [row["posterior_variance"] for row in result["functionals"]] == [0.5, 0.5]
    assert result["empirical_learning_plateau"] is None
    assert result["public_saturation_claim_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["task_sha256"] == submission["task_sha256"]


def test_realized_records_require_collection_verification(submission):
    submission["task"]["claim_lane"] = "realized_record"
    freeze(submission)
    assert evaluate_finite_task(submission)["attainment"] == "unknown"
    submission["evidence"]["collection_verified"] = False
    assert evaluate_finite_task(submission)["attainment"] == "not_attained"
    submission["evidence"]["collection_verified"] = True
    assert evaluate_finite_task(submission)["attainment"] == "attained"


def test_finite_marginals_do_not_claim_all_directions(submission):
    sigma = np.array([[0.5, 0.49], [0.49, 0.5]])
    info = np.linalg.inv(sigma) - np.eye(2)
    submission["geometry"]["information_matrix"] = info.tolist()
    result = evaluate_finite_task(submission)
    assert result["attainment"] == "attained"
    assert result["all_direction_attainment"] is None
    assert (
        posterior_reference_diagnostic(info, np.eye(2), np.eye(2))[
            "all_direction_reference_attainment"
        ]
        is False
    )


def test_nonidentity_prior_and_parameter_reexpression(submission):
    prior = np.array([[2.0, 0.4], [0.4, 3.0]])
    info = np.array([[4.0, 0.2], [0.2, 1.0]])
    submission["task"]["prior_precision"] = prior.tolist()
    submission["geometry"]["information_matrix"] = info.tolist()
    before = evaluate_finite_task(freeze(submission))
    transform = np.array([[3.0, 0.3], [-0.2, 0.1]])
    submission["task"]["prior_precision"] = (transform.T @ prior @ transform).tolist()
    submission["geometry"]["information_matrix"] = (transform.T @ info @ transform).tolist()
    for functional in submission["task"]["functionals"]:
        functional["coefficients"] = (transform.T @ functional["coefficients"]).tolist()
    after = evaluate_finite_task(freeze(submission))
    assert after["task_sha256"] != before["task_sha256"]
    assert after["attainment"] == before["attainment"]
    assert [r["posterior_variance"] for r in after["functionals"]] == pytest.approx(
        [r["posterior_variance"] for r in before["functionals"]]
    )


def test_functional_units_scale_variance_and_limit_together(submission):
    before = evaluate_finite_task(submission)
    submission["task"]["functionals"][0].update(
        coefficients=[1000, 0], unit="milli-unit A", variance_limit=500000
    )
    after = evaluate_finite_task(freeze(submission))
    assert after["attainment"] == before["attainment"]
    assert after["functionals"][0]["posterior_variance"] == pytest.approx(500000)


@pytest.mark.parametrize("support, expected", [(None, "unknown"), (False, "not_attained")])
def test_missing_neural_domain_not_compensated_by_depth(submission, support, expected):
    submission["geometry"]["information_matrix"] = [[1e8, 0], [0, 1e8]]
    submission["evidence"]["support"][1]["supported"] = support
    assert evaluate_finite_task(submission)["attainment"] == expected


def test_diagnostic_observation_does_not_supply_perturbation(submission):
    submission["task"]["required_support"][1]["role"] = "perturbation"
    assert evaluate_finite_task(freeze(submission))["attainment"] == "unknown"
    submission["evidence"]["support"].append(
        {"domain_id": "neural", "role": "perturbation", "supported": False}
    )
    assert evaluate_finite_task(submission)["attainment"] == "not_attained"
    submission["evidence"]["support"][-1]["supported"] = True
    assert evaluate_finite_task(submission)["attainment"] == "attained"


def test_extraneous_absent_domain_does_not_veto_narrow_task(submission):
    submission["task"]["required_support"] = submission["task"]["required_support"][:1]
    submission["evidence"]["support"][1]["supported"] = False
    assert evaluate_finite_task(freeze(submission))["attainment"] == "attained"


def test_unknown_geometry_and_false_dominates_unknown(submission):
    submission["geometry"] = None
    result = evaluate_finite_task(submission)
    assert result["attainment"] == "unknown"
    assert all(f["posterior_variance"] is None for f in result["functionals"])
    submission["evidence"]["support"][1]["supported"] = False
    assert evaluate_finite_task(submission)["attainment"] == "not_attained"


def test_tiny_deep_and_large_shallow_preserve_task_tradeoffs(submission):
    def geometry(count, operator):
        return event_information(
            EventContribution("synthetic", operator, ((1.0, 0.0), (0.0, 1.0)), count, "synthetic")
        ).tolist()

    submission["geometry"]["information_matrix"] = geometry(2, ((100.0, 0.0), (0.0, 10.0)))
    tiny = evaluate_finite_task(submission)
    submission["geometry"]["information_matrix"] = geometry(1000000, ((1.0, 0.0), (0.0, 0.0)))
    shallow = evaluate_finite_task(submission)
    assert tiny["attainment"] == "attained"
    assert shallow["attainment"] == "not_attained"
    assert (
        shallow["functionals"][0]["posterior_variance"]
        < tiny["functionals"][0]["posterior_variance"]
    )
    assert (
        tiny["functionals"][1]["posterior_variance"]
        < shallow["functionals"][1]["posterior_variance"]
    )
    assert "overall_rank" not in tiny


def test_target_hash_and_model_binding(submission):
    tampered = copy.deepcopy(submission)
    tampered["task"]["functionals"][0]["variance_limit"] = 100
    with pytest.raises(FiniteTaskError, match="hash"):
        evaluate_finite_task(tampered)
    submission["geometry"]["model_sha256"] = "sha256:" + "c" * 64
    with pytest.raises(FiniteTaskError, match="model identity"):
        evaluate_finite_task(submission)


@pytest.mark.parametrize("bad", [0, 1, "true", [], {}])
def test_boolean_checks_are_strict(submission, bad):
    submission["evidence"]["identifiability"] = bad
    with pytest.raises(FiniteTaskError):
        evaluate_finite_task(submission)


@pytest.mark.parametrize("bad", [True, 0, -1, float("nan"), float("inf")])
def test_variance_limit_invalid(submission, bad):
    submission["task"]["functionals"][0]["variance_limit"] = bad
    with pytest.raises(FiniteTaskError):
        evaluate_finite_task(freeze(submission))


@pytest.mark.parametrize(
    "bad",
    [[[1, 0], [0, -1]], [[True, 0], [0, 1]], [[1]], [[1, 1], [0, 1]], [[1, 0], [0, float("inf")]]],
)
def test_geometry_invalid_not_unknown(submission, bad):
    submission["geometry"]["information_matrix"] = bad
    with pytest.raises(FiniteTaskError):
        evaluate_finite_task(submission)


def test_zero_functional_duplicate_ids_and_unsupported_lane(submission):
    for mutate in [
        lambda t: t["functionals"][0].update(coefficients=[0, 0]),
        lambda t: t["functionals"][1].update(functional_id="first"),
        lambda t: t.update(claim_lane="empirical_learning"),
        lambda t: t.update(comparison_scope="all_directions"),
    ]:
        changed = copy.deepcopy(submission)
        mutate(changed["task"])
        with pytest.raises(FiniteTaskError):
            evaluate_finite_task(freeze(changed))


def test_prior_validated_even_when_geometry_unknown(submission):
    submission["geometry"] = None
    submission["task"]["prior_precision"] = [[0, 0], [0, 0]]
    with pytest.raises(FiniteTaskError):
        evaluate_finite_task(freeze(submission))


def test_near_singular_noise_is_valid_conditional_geometry(submission):
    rho = 0.999999
    info = event_information(
        EventContribution(
            "synthetic", ((1.0, 0.0), (1.0, 0.0)), ((1.0, rho), (rho, 1.0)), 1, "synthetic"
        )
    )
    submission["geometry"]["information_matrix"] = info.tolist()
    result = evaluate_finite_task(submission)
    assert result["functionals"][0]["posterior_variance"] == pytest.approx(1 / (1 + 2 / (1 + rho)))
    assert result["functionals"][1]["posterior_variance"] == pytest.approx(1)
    assert result["attainment"] == "not_attained"


def test_zero_observations_and_noise_degradation(submission):
    submission["geometry"]["information_matrix"] = [[0, 0], [0, 0]]
    assert evaluate_finite_task(submission)["attainment"] == "not_attained"
    submission["geometry"]["information_matrix"] = [[4, 0], [0, 4]]
    precise = evaluate_finite_task(submission)
    submission["geometry"]["information_matrix"] = [[0.25, 0], [0, 0.25]]
    noisy = evaluate_finite_task(submission)
    assert precise["attainment"] == "attained"
    assert noisy["attainment"] == "not_attained"
    assert (
        noisy["functionals"][0]["posterior_variance"]
        > precise["functionals"][0]["posterior_variance"]
    )


def test_duplicate_support_and_extra_fields_rejected(submission):
    submission["evidence"]["support"].append(copy.deepcopy(submission["evidence"]["support"][0]))
    with pytest.raises(FiniteTaskError, match="unique"):
        evaluate_finite_task(submission)
    submission["evidence"]["support"].pop()
    submission["evidence"]["treatment_succeeded"] = True
    with pytest.raises(FiniteTaskError, match="schema"):
        evaluate_finite_task(submission)


def test_result_schema_for_all_three_states(submission):
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "schemas/finite_precision/v1/evaluation-result.schema.json").read_text()
    )
    for info, expected in [
        ([[1, 0], [0, 1]], "attained"),
        ([[0, 0], [0, 0]], "not_attained"),
        (None, "unknown"),
    ]:
        candidate = copy.deepcopy(submission)
        candidate["geometry"] = (
            None
            if info is None
            else {"model_sha256": candidate["task"]["model_sha256"], "information_matrix": info}
        )
        result = evaluate_finite_task(candidate)
        Draft202012Validator(schema).validate(result)
        assert result["attainment"] == expected


def test_strong_prior_zero_information_is_explicit_not_acquired_precision(submission):
    submission["task"]["prior_precision"] = [[100, 0], [0, 100]]
    submission["geometry"]["information_matrix"] = [[0, 0], [0, 0]]
    baseline = evaluate_finite_task(freeze(submission))
    assert baseline["attainment"] == "attained"
    for functional in baseline["functionals"]:
        assert functional["prior_variance"] == pytest.approx(0.01)
        assert functional["posterior_variance"] == pytest.approx(0.01)
        assert functional["prior_only_precision_attainment"] is True
        assert functional["variance_reduction"] == 0
    submission["geometry"]["information_matrix"] = [[100, 0], [0, 100]]
    acquired = evaluate_finite_task(submission)
    for functional in acquired["functionals"]:
        assert functional["prior_variance"] == pytest.approx(0.01)
        assert functional["posterior_variance"] == pytest.approx(0.005)
        assert functional["variance_reduction"] == pytest.approx(0.005)
    submission["geometry"] = None
    unknown = evaluate_finite_task(submission)
    assert unknown["attainment"] == "unknown"
    assert unknown["functionals"][0]["prior_only_precision_attainment"] is True
    assert unknown["functionals"][0]["variance_reduction"] is None


@pytest.mark.parametrize("where", ["prior", "information"])
def test_ragged_matrices_raise_public_error(submission, where):
    if where == "prior":
        submission["task"]["prior_precision"] = [[1, 0], [1]]
    else:
        submission["geometry"]["information_matrix"] = [[1, 0], [1]]
    with pytest.raises(FiniteTaskError):
        evaluate_finite_task(freeze(submission))


def test_receipt_binds_implementation_and_schema_bytes(submission):
    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = evaluate_finite_task(submission)
    receipt = result["implementation"]
    assert receipt["numpy_version"] == np.__version__
    for filename, digest in receipt["sha256"].items():
        directory = root / (
            "src/anibench" if filename.endswith(".py") else "schemas/finite_precision/v1"
        )
        assert digest == "sha256:" + hashlib.sha256((directory / filename).read_bytes()).hexdigest()
    assert set(receipt["sha256"]) == {
        "finite_tasks_v1.py",
        "information_v2.py",
        "evaluation-input.schema.json",
        "evaluation-result.schema.json",
    }


def test_packaged_synthetic_example_provenance_is_recomputable():
    import hashlib
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "examples/finite_tasks"
    source = folder / "synthetic-provenance.json"
    provenance = json.loads(source.read_text())
    candidate = json.loads((folder / "synthetic-request.json").read_text())
    assert provenance["source_kind"] == "synthetic_no_real_study"
    assert provenance["biological_calibration"] is False
    assert (
        candidate["task"]["source_sha256"]
        == "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    )
    model = json.dumps(provenance["model"], sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert (
        candidate["geometry"]["model_sha256"]
        == "sha256:" + hashlib.sha256(model.encode()).hexdigest()
    )
    assert candidate["task_sha256"] == finite_task_sha256(candidate["task"])
    assert evaluate_finite_task(candidate)["attainment"] == "attained"
