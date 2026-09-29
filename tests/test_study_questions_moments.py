"""Fourth engine preserves complete-frame logic and existing receipt semantics."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from anibench.estimator_moments_v1 import evaluate_estimator_moments
from anibench.question_routes_v1 import digest
from anibench.study_questions_v2 import StudyQuestionError, evaluate_study_questions


def example():
    root = Path(__file__).resolve().parents[1] / "examples/estimator_moments"
    d = json.loads((root / "definition.json").read_text())
    payload = json.loads((root / "exact-pass.json").read_text())
    profile = {"contract": "anibench.study-question-profile.v4", "profile_id": "fictional-moments",
               "scope": "Software test only", "selection_rationale": "Finite hypothetical task",
               "weighting_rationale": "One indivisible requirement",
               "questions": [{"question_id": "moment", "biological_identity": "synthetic-probability",
                              "engine": "estimator_moments", "definition": d}],
               "categories": [{"category_id": "state", "label": "Native state", "question": "Is the native error target met?",
                               "requirements": [{"requirement_id": "probability", "rationale": "Complete registered target",
                                                 "weight": 40, "alternatives": [{"question_id": "moment", "outcomes": ["target"]}]}]}],
               "scenarios": [{"scenario_id": "reference", "rationale": "Declared moments",
                              "paired_biological_covariance": {}}]}
    request = {"contract": "anibench.study-questions-request.v4", "profile_sha256": digest(profile),
               "study_id": "fictional", "lifecycle": "hypothetical",
               "scenarios": [{"scenario_id": "reference", "inputs": {"moment": payload}}]}
    return profile, request


def evaluate(p, r):
    r = deepcopy(r); r["profile_sha256"] = digest(p)
    return evaluate_study_questions(r, trusted_profiles={digest(p): p})


def test_original_moment_receipt_is_retained_without_reinterpretation():
    p, r = example()
    result = evaluate(p, r)
    original = evaluate_estimator_moments(r["scenarios"][0]["inputs"]["moment"],
                                         trusted_definitions={digest(p["questions"][0]["definition"]): p["questions"][0]["definition"]})
    assert result["scenarios"][0]["questions"]["moment"]["receipt"] == original
    assert result["robust_reference_attainment"] == "attained"
    assert result["robust_categories"][0]["weight_total"] == 40
    assert result["whole_benchmark_complete"] is False


def test_missing_moment_input_retains_complete_budget():
    p, r = example(); r["scenarios"][0]["inputs"] = {}
    result = evaluate(p, r)
    assert result["robust_categories"][0]["unknown_weight"] == 40
    assert result["robust_reference_attainment"] == "unknown"


def alternative(p, r):
    q = deepcopy(p["questions"][0]); q["question_id"] = "other"; q["biological_identity"] = "other-frame"
    q["definition"]["context"] = "other fixed protocol"
    p["questions"].append(q)
    p["categories"][0]["requirements"][0]["alternatives"].append({"question_id": "other", "outcomes": ["target"]})
    x = deepcopy(r["scenarios"][0]["inputs"]["moment"])
    x["definition_sha256"] = digest(q["definition"]); x["design"]["context"] = "other fixed protocol"
    r["scenarios"][0]["inputs"]["other"] = x


def test_one_complete_frame_must_work_across_scenarios():
    p, r = example(); alternative(p, r)
    scenario = deepcopy(p["scenarios"][0]); scenario["scenario_id"] = "uncertain"
    p["scenarios"].append(scenario)
    scenario = deepcopy(r["scenarios"][0]); scenario["scenario_id"] = "uncertain"
    r["scenarios"].append(scenario)
    for s, q in zip(r["scenarios"], ("moment", "other"), strict=True):
        s["inputs"][q]["moments"].update(covariance_lower=[[1]], covariance_upper=[[1]])
    z = evaluate(p, r)
    assert all(s["reference_attainment"] == "attained" for s in z["scenarios"])
    assert z["robust_reference_attainment"] == "not_attained"


def test_uncertain_error_bound_retains_upper_mass():
    p, r = example()
    r["scenarios"][0]["inputs"]["moment"]["moments"].update(covariance_lower=None, covariance_upper=[[1]])
    c = evaluate(p, r)["robust_categories"][0]
    assert (c["passed_percent"], c["upper_percent"]) == (0, 100)
    assert c["precision_toward_targets"]["upper_percent"] == 100


def test_geometry_fixed_but_quality_uncertainty_allowed():
    p, r = example()
    s = deepcopy(p["scenarios"][0]); s["scenario_id"] = "other"; p["scenarios"].append(s)
    s = deepcopy(r["scenarios"][0]); s["scenario_id"] = "other"; r["scenarios"].append(s)
    s["inputs"]["moment"]["design"]["support"]["fixed_denominator"] = None
    assert evaluate(p, r)["robust_reference_attainment"] == "unknown"
    d = s["inputs"]["moment"]["design"]
    d["acquisitions"][0]["physical_acquisition_id"] = "another-person"
    d["estimator_inputs"][0]["physical_outputs"][0][0] = "another-person"
    with pytest.raises(StudyQuestionError, match="geometry"): evaluate(p, r)


def test_duplicate_aliases_do_not_inflate_category():
    p, r = example(); expected = evaluate(p, r)
    r["scenarios"][0]["inputs"]["moment"]["design"]["acquisitions"] *= 30
    z = evaluate(p, r)
    assert z["robust_categories"] == expected["robust_categories"]
    assert z["design_frame_sha256"] == expected["design_frame_sha256"]


@pytest.mark.parametrize("mutation", ["old_version", "lifecycle", "definition", "renamed_frame", "physical_conflict"])
def test_version_identity_and_native_guards(mutation):
    p, r = example()
    if mutation == "old_version": p["contract"] = "anibench.study-question-profile.v3"
    elif mutation == "lifecycle": r["scenarios"][0]["inputs"]["moment"]["lifecycle"] = "realized"
    elif mutation == "definition": r["scenarios"][0]["inputs"]["moment"]["definition_sha256"] = digest({"wrong": 1})
    elif mutation == "renamed_frame":
        alternative(p, r); p["questions"][1]["definition"]["context"] = p["questions"][0]["definition"]["context"]
    else:
        alternative(p, r)
        r["scenarios"][0]["inputs"]["other"]["design"]["acquisitions"][0]["signature"]["unit"] = "other unit"
    with pytest.raises(StudyQuestionError): evaluate(p, r)


def test_shared_estimator_bounds_cannot_conflict_between_functionals():
    p, r = example()
    # Same estimator may serve a distinct scaled functional without its variance changing.
    q = deepcopy(p["questions"][0]); q["question_id"] = "scaled"; q["biological_identity"] = "scaled-probability"
    q["definition"]["functionals"][0]["coefficients"] = [2]
    p["questions"].append(q)
    p["categories"][0]["requirements"][0]["alternatives"].append({"question_id": "scaled", "outcomes": ["target"]})
    x = deepcopy(r["scenarios"][0]["inputs"]["moment"]); x["definition_sha256"] = digest(q["definition"])
    r["scenarios"][0]["inputs"]["scaled"] = x
    assert evaluate(p, r)["robust_reference_attainment"] == "attained"
    x["moments"].update(covariance_lower=[[1]], covariance_upper=[[1]])
    with pytest.raises(StudyQuestionError, match="covariance bound"): evaluate(p, r)


def test_v4_cli_preserves_decimal_boundary_and_private_errors(tmp_path, capsys):
    from anibench.cli import main

    p, r = example()
    pp, rp, out = tmp_path / "profile.json", tmp_path / "private-input.json", tmp_path / "result.json"
    pp.write_text(json.dumps(p)); rp.write_text(json.dumps(r))
    assert main(["study-questions", str(pp), str(rp), "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == evaluate(p, r)
    rp.write_text(json.dumps(r).replace("0.0025", "1.0000000000000000000001"))
    assert main(["study-questions", str(pp), str(rp), "--out", str(tmp_path / "new.json")]) == 2
    assert not (tmp_path / "new.json").exists()
    assert "private-input" not in capsys.readouterr().err
