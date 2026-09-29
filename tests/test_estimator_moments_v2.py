"""Finite-law and integration tests for separable native estimator loss."""
import json
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from anibench.cli import main
from anibench.estimator_moments_v1 import EstimatorMomentError
from anibench.estimator_moments_v1 import evaluate_estimator_moments as evaluate_v1
from anibench.estimator_moments_v2 import evaluate_estimator_moments, validate_definition
from anibench.question_routes_v1 import digest
from anibench.study_questions_v2 import StudyQuestionError, evaluate_study_questions

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/estimator_moments/quadratic"


def read(name):
    return json.loads((EXAMPLES / f"{name}.json").read_text())


def evaluate(d, r):
    r = deepcopy(r)
    r["definition_sha256"] = digest(d)
    return evaluate_estimator_moments(r, trusted_definitions={digest(d): d})


@pytest.mark.parametrize("name,state", [("joint-pass", "attained"), ("joint-failure", "not_attained"),
                                       ("constant-wrong", "not_attained"), ("unknown-moments", "unknown"),
                                       ("unverified-collection", "unknown")])
def test_schema_cli_api_and_create_only_outputs(name, state, tmp_path, capsys):
    d, r = read("definition"), read(name)
    for kind, data in (("definition", d), ("request", r)):
        schema = json.loads((ROOT / f"schemas/estimator_moments/v2/{kind}.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
    out = tmp_path / "result.json"
    args = ["estimator-moments", str(EXAMPLES / "definition.json"), str(EXAMPLES / f"{name}.json"), "--out", str(out)]
    assert main(args) == 0
    result = evaluate(d, r)
    assert json.loads(out.read_text()) == result
    assert result["attainment"] == state
    assert out.stat().st_mode & 0o777 == 0o600
    first = out.read_bytes()
    assert main(args) == 2
    assert out.read_bytes() == first
    assert str(tmp_path) not in capsys.readouterr().err


@pytest.mark.parametrize("p", [F(0), F(1, 10000), F(8, 1000), F(1, 100), F(3, 100), F(1, 2), F(1)])
def test_exact_enumerated_hard_call_loss_not_coordinate_allocation(p):
    d, r = read("definition"), read("joint-pass")
    # Enumerate the two outcomes directly, independently of moment algebra.
    truth, outcomes = [1, 0, 0, 0], [(1-p, [1, 0, 0, 0]), (p, [0, 1, 0, 0])]
    mean = [sum(prob * t[j] for prob, t in outcomes) for j in range(4)]
    covariance = [[sum(prob * (t[i]-mean[i]) * (t[j]-mean[j]) for prob, t in outcomes)
                   for j in range(4)] for i in range(4)]
    direct_loss = sum(prob * sum((F(t[j])-truth[j])**2 for j in range(4))/2 for prob, t in outcomes)
    r["moments"].update(covariance_lower=[[float(x) for x in row] for row in covariance],
                        covariance_upper=[[float(x) for x in row] for row in covariance],
                        bias_lower=[float(m-t) for m, t in zip(mean, truth, strict=True)],
                        bias_upper=[float(m-t) for m, t in zip(mean, truth, strict=True)])
    result = evaluate(d, r)
    assert F(result["functionals"][0]["mse"]["lower"]["exact"]) == direct_loss == p
    assert result["attainment"] == ("attained" if p <= F(1, 100) else "not_attained")
    if p == F(8, 1000):
        assert p > F(1, 100)/4  # allocated coordinate criteria fail although joint loss passes


def test_bias_box_extrema_and_unqualified_bounds():
    d, r = read("definition"), read("joint-pass")
    r["moments"].update(covariance_lower=[[0]*4 for _ in range(4)], covariance_upper=[[0]*4 for _ in range(4)],
                        bias_lower=[-1, 2, -4, 0], bias_upper=[1, 3, -2, 0])
    z = evaluate(d, r)["functionals"][0]["mse"]
    assert F(z["lower"]["exact"]) == 4
    assert F(z["upper"]["exact"]) == 13
    r["design"]["support"]["qualified_moment_derivation"] = None
    assert evaluate(d, r)["attainment"] == "unknown"


@pytest.mark.parametrize("weights", [[0]*4, [-1, 1, 1, 1], [1], [True, 0, 0, 0], [float("nan"), 0, 0, 0]])
def test_invalid_quadratic_loss_rejected(weights):
    d = read("definition"); d["functionals"][0]["loss_weights"] = weights
    with pytest.raises(EstimatorMomentError): validate_definition(d)


def test_full_covariance_psd_remains_required_even_for_diagonal_loss():
    d, r = read("definition"), read("joint-pass")
    r["moments"]["covariance_upper"][0][1] = 5
    r["moments"]["covariance_upper"][1][0] = 5
    with pytest.raises(EstimatorMomentError): evaluate(d, r)


def test_legacy_v1_receipts_are_exactly_preserved():
    base = EXAMPLES.parent
    d = json.loads((base / "definition.json").read_text())
    for name in ("exact-pass", "exact-failure", "biased-failure", "loose-bound-unknown", "missing-support"):
        r = json.loads((base / f"{name}.json").read_text())
        registry = {digest(d): d}
        assert evaluate_estimator_moments(r, trusted_definitions=registry) == evaluate_v1(r, trusted_definitions=registry)


def test_request_and_definition_version_must_match():
    d, r = read("definition"), read("joint-pass")
    r["contract"] = "anibench.estimator-moments-request.v1"
    with pytest.raises(EstimatorMomentError): evaluate(d, r)


def test_study_wrapper_preserves_joint_receipt_and_denominator(tmp_path):
    p, r = read("profile"), read("study")
    z = evaluate_study_questions(r, trusted_profiles={digest(p): p})
    assert z["scenarios"][0]["questions"]["joint-call"]["receipt"] == evaluate(read("definition"), read("joint-pass"))
    assert z["robust_categories"][0]["passed_percent"] == 100
    out = tmp_path / "study.json"
    assert main(["study-questions", str(EXAMPLES / "profile.json"), str(EXAMPLES / "study.json"), "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == z
    r["scenarios"][0]["inputs"] = {}
    z = evaluate_study_questions(r, trusted_profiles={digest(p): p})
    assert z["robust_categories"][0]["unknown_weight"] == 1


def test_same_loss_in_two_representations_cannot_gain_another_budget():
    # Rank-one c c' equals diagonal w for a one-coordinate functional.
    from test_study_questions_moments import example

    p, r = example()
    q = deepcopy(p["questions"][0]); q["question_id"] = "renamed"; q["biological_identity"] = "renamed"
    d = q["definition"]; d["contract"] = "anibench.estimator-moment-definition.v2"
    f = d["functionals"][0]; f.pop("coefficients"); f["loss_weights"] = [1]
    p["questions"].append(q)
    r["profile_sha256"] = digest(p)
    with pytest.raises(StudyQuestionError, match="[Ff]rame"):
        evaluate_study_questions(r, trusted_profiles={digest(p): p})
