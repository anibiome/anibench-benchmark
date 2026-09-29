"""Independent finite distributions and adversaries for estimator MSE semantics."""
from copy import deepcopy
from fractions import Fraction
from itertools import product

import pytest

from anibench.estimator_moments_v1 import EstimatorMomentError, evaluate_estimator_moments
from anibench.question_routes_v1 import digest


def example(n=1):
    source = digest({"synthetic": "finite distributions for software verification"})
    signature = lambda i: {"quantity": f"registered_probability_{i}", "unit": "probability",
                           "compartment": "synthetic", "context": "fixed iid trial process"}
    definition = {
        "contract": "anibench.estimator-moment-definition.v1", "definition_id": "synthetic",
        "question": "Can this registered estimator resolve a probability?",
        "population_scope": "Hypothetical one-person occasion", "context": "fixed process",
        "estimators": [{"estimator_id": str(i), "target": signature(i),
                        "estimator": "Sample proportion of specified iid Bernoulli trials",
                        "method_sha256": source, "independent_unit": "trial conditional on occasion"}
                       for i in range(n)],
        "functionals": [{"functional_id": "first", "estimand": "First probability",
                         "coefficients": [1] + [0] * (n - 1), "unit": "probability", "mse_limit": 0.0025}],
        "support_requirements": ["fixed_denominator", "unbiased_moment_derivation"],
        "sources": [{"source_id": "fictional", "sha256": source, "locator": "test fixture",
                     "role": "Explicit synthetic mathematical construction"}],
        "assumptions": ["Synthetic conditional Bernoulli process; no study facts"],
    }
    request = {
        "contract": "anibench.estimator-moments-request.v1", "definition_sha256": digest(definition),
        "lifecycle": "hypothetical", "design": {
            "context": "fixed process", "collection_verified": None,
            "support": {"fixed_denominator": True, "unbiased_moment_derivation": True},
            "acquisitions": [{"physical_acquisition_id": "trial-sequence", "physical_output_id": str(i),
                              "signature": signature(i)} for i in range(n)],
            "estimator_inputs": [{"estimator_id": str(i), "physical_outputs": [["trial-sequence", str(i)]],
                                  "estimable": True} for i in range(n)]},
        "moments": {"covariance_lower": [[0.0025 * (i == j) for i in range(n)] for j in range(n)],
                    "covariance_upper": [[0.0025 * (i == j) for i in range(n)] for j in range(n)],
                    "bias_lower": [0] * n, "bias_upper": [0] * n,
                    "justification": "Exact variance 1/(4n) at p=1/2, n=100, under iid trials",
                    "source_sha256": source, "assumptions": ["Exact stated conditional model"]},
    }
    return definition, request


def evaluate(d, r):
    r = deepcopy(r)
    r["definition_sha256"] = digest(d)
    return evaluate_estimator_moments(r, trusted_definitions={digest(d): d})


def test_exact_discrete_distribution_without_gaussian_approximation():
    # Enumerate the complete distribution, independently of evaluator algebra.
    values = [Fraction(sum(bits), 4) for bits in product((0, 1), repeat=4)]
    mean = sum(values) / len(values)
    mse = sum((x - mean) ** 2 for x in values) / len(values)
    assert mse == Fraction(1, 16)
    d, r = example()
    r["moments"]["covariance_lower"] = r["moments"]["covariance_upper"] = [[float(mse)]]
    result = evaluate(d, r)
    assert result["functionals"][0]["mse"]["lower"]["exact"] == "1/16"
    assert result["attainment"] == "not_attained"
    assert result["precision_toward_target"]["upper_percent"] == 4
    assert "posterior" not in result and "information_matrix" not in result


def test_exact_boundary_and_preserved_inputs():
    d, r = example()
    before = deepcopy((d, r))
    result = evaluate(d, r)
    assert result["attainment"] == "attained" and (d, r) == before
    d["functionals"][0].update(coefficients=[0.1], mse_limit=0.01)
    r["moments"]["covariance_lower"] = r["moments"]["covariance_upper"] = [[1]]
    assert evaluate(d, r)["attainment"] == "attained"
    d["functionals"][0]["mse_limit"] = 0.009999999999999998
    assert evaluate(d, r)["attainment"] == "not_attained"


def test_loose_upper_bound_is_unknown_not_failure():
    d, r = example()
    r["moments"].update(covariance_lower=None, covariance_upper=[[0.25]])
    result = evaluate(d, r)
    assert result["attainment"] == "unknown"
    assert result["precision_toward_target"] == {"lower_percent": 1, "upper_percent": 100}
    r["moments"]["covariance_upper"] = [[0.0025]]
    assert evaluate(d, r)["attainment"] == "attained"


def test_certified_lower_bound_can_fail_even_with_unbounded_upper():
    d, r = example()
    r["moments"].update(covariance_lower=[[0.01]], covariance_upper=None)
    result = evaluate(d, r)
    assert result["attainment"] == "not_attained"
    assert result["precision_toward_target"] == {"lower_percent": 0, "upper_percent": 25}


def test_bias_is_not_silently_zero_and_can_dominate_variance():
    d, r = example()
    r["moments"].update(covariance_lower=[[0]], covariance_upper=[[0]], bias_lower=None, bias_upper=None)
    assert evaluate(d, r)["attainment"] == "unknown"
    r["moments"].update(bias_lower=[0.1], bias_upper=[0.2])
    result = evaluate(d, r)
    assert result["attainment"] == "not_attained"
    assert result["functionals"][0]["mse"]["lower"]["exact"] == "1/100"
    assert result["functionals"][0]["mse"]["upper"]["exact"] == "1/25"


def test_shared_dependence_and_bias_cancellation():
    d, r = example(2)
    d["functionals"][0].update(coefficients=[1, -1])
    r["moments"].update(covariance_lower=[[1, 1], [1, 1]], covariance_upper=[[1, 1], [1, 1]],
                        bias_lower=[2, 2], bias_upper=[2, 2])
    assert evaluate(d, r)["attainment"] == "attained"
    # Unknown signs cannot inherit the exact common-bias cancellation.
    r["moments"].update(bias_lower=[-2, -2], bias_upper=[2, 2])
    assert evaluate(d, r)["attainment"] == "unknown"
    assert evaluate(d, r)["functionals"][0]["mse"]["upper"]["exact"] == "16"
    # Perfectly correlated trials do not gain independent-repeat precision.
    d["functionals"][0].update(coefficients=[0.5, 0.5], mse_limit=0.125)
    r["moments"].update(covariance_lower=[[0.25, 0.25], [0.25, 0.25]],
                        covariance_upper=[[0.25, 0.25], [0.25, 0.25]], bias_lower=[0, 0], bias_upper=[0, 0])
    assert evaluate(d, r)["attainment"] == "not_attained"
    r["moments"].update(covariance_lower=[[0.25, 0], [0, 0.25]], covariance_upper=[[0.25, 0], [0, 0.25]])
    assert evaluate(d, r)["attainment"] == "attained"


def test_duplicate_exports_preserve_design_and_numerics():
    d, r = example()
    first = evaluate(d, r)
    r["design"]["acquisitions"] *= 20
    r["design"]["estimator_inputs"][0]["physical_outputs"] *= 20
    second = evaluate(d, r)
    for key in ("design_frame_sha256", "attainment", "functionals", "precision_toward_target"):
        assert first[key] == second[key]
    assert first["request_sha256"] != second["request_sha256"]


def test_units_change_covariance_bias_functional_and_threshold_together():
    d, r = example(2)
    d["functionals"][0].update(coefficients=[1, -1], mse_limit=0.02)
    r["moments"].update(bias_lower=[0.02, -0.03], bias_upper=[0.02, -0.03])
    expected = evaluate(d, r)
    # First estimator changes to percent units; native functional is unchanged.
    d["estimators"][0]["target"]["unit"] = "percent"
    d["functionals"][0]["coefficients"] = [0.01, -1]
    r["moments"]["covariance_lower"][0][0] = 25
    r["moments"]["covariance_upper"][0][0] = 25
    r["moments"]["bias_lower"][0] = r["moments"]["bias_upper"][0] = 2
    result = evaluate(d, r)
    assert result["functionals"] == expected["functionals"]


@pytest.mark.parametrize("flag,expected", [(None, "unknown"), (False, "not_attained"), (True, "attained")])
def test_qualification_and_realized_collection(flag, expected):
    d, r = example()
    r["design"]["support"]["fixed_denominator"] = flag
    assert evaluate(d, r)["attainment"] == expected
    r["design"]["support"]["fixed_denominator"] = True
    r["lifecycle"] = "realized"
    r["design"]["collection_verified"] = flag
    assert evaluate(d, r)["attainment"] == expected
    r["lifecycle"] = "planned"
    assert evaluate(d, r)["attainment"] == "attained"


@pytest.mark.parametrize("matrix", [[[0, 1], [1, 1]], [[1, 2], [2, 1]],
                                     [[1, 0], [1e-30, 1]], [[True, 0], [0, 1]],
                                     [[1, 1.0000000000000002], [1.0000000000000002, 1]]])
def test_invalid_covariance_not_repaired_by_ridge_or_tolerance(matrix):
    d, r = example(2)
    r["moments"]["covariance_upper"] = matrix
    with pytest.raises(EstimatorMomentError): evaluate(d, r)


def test_individually_psd_bounds_need_loewner_order():
    d, r = example(2)
    r["moments"].update(covariance_lower=[[1, 0.9], [0.9, 1]], covariance_upper=[[1.1, 0], [0, 1.1]])
    with pytest.raises(EstimatorMomentError): evaluate(d, r)


def test_unknown_support_does_not_convert_conditional_risk_into_proven_failure():
    d, r = example()
    r["moments"].update(covariance_lower=[[1]], covariance_upper=[[1]])
    r["design"]["estimator_inputs"][0]["estimable"] = None
    result = evaluate(d, r)
    assert result["attainment"] == "unknown"
    assert result["precision_toward_target"] == {"lower_percent": 0, "upper_percent": 100}


@pytest.mark.parametrize("mutation", ["stale", "extra_score", "missing_moment", "empty_input", "identity", "bias"])
def test_invalid_contracts_are_rejected(mutation):
    d, r = example()
    if mutation == "stale": r["definition_sha256"] = digest({"other": 1})
    elif mutation == "extra_score": r["score"] = 100
    elif mutation == "missing_moment": del r["moments"]["bias_lower"]
    elif mutation == "empty_input": r["design"]["estimator_inputs"][0]["physical_outputs"] = []
    elif mutation == "identity":
        row = deepcopy(r["design"]["acquisitions"][0]); row["signature"]["unit"] = "wrong"
        r["design"]["acquisitions"].append(row)
    else: r["moments"].update(bias_lower=[1], bias_upper=[0])
    with pytest.raises(EstimatorMomentError):
        evaluate_estimator_moments(r, trusted_definitions={digest(d): d})
