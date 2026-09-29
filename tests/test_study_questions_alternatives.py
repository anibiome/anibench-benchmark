"""Complete native witnesses, without pooling unlike biological targets."""
from copy import deepcopy

import pytest
from test_study_questions_v2 import example as legacy_example
from test_study_questions_v2 import execute

from anibench.paired_collection_v1 import evaluate_paired_collection
from anibench.question_routes_v1 import digest
from anibench.study_questions_v2 import StudyQuestionError


def example():
    profile, request = legacy_example()
    question = profile["questions"][1]
    payload = request["scenarios"][0]["inputs"]["paired"]
    profile.update(contract="anibench.study-question-profile.v3",
                   profile_id="fictional-complete-native-alternatives.v1",
                   scope="Invented two-specimen software example, not a human study or biological reference",
                   selection_rationale="Exercise a declared disjunction without treating native specimen values as interchangeable",
                   weighting_rationale="One fixed requirement budget, regardless of native alternatives")
    request.update(contract="anibench.study-questions-request.v3", study_id="fictional-native-alternatives")
    profile["questions"] = []
    profile["scenarios"][0]["paired_biological_covariance"] = {}
    request["scenarios"][0]["inputs"] = {}
    for name in ("specimen_a", "specimen_b"):
        q, value = deepcopy(question), deepcopy(payload)
        q.update(question_id=name, biological_identity="fictional-" + name)
        definition = q["definition"]
        definition["question_id"] = "fictional-" + name
        definition["question"] = "Resolve two fictional native molecules and independent grip in " + name
        for coordinate in definition["coordinates"][:2]:
            coordinate["definition"] += "; native specimen " + name
        value["question"] = deepcopy(definition)
        for part in ("scenario", "design"):
            value[part]["question_sha256"] = digest(definition)
        for pattern in value["design"]["patterns"]:
            for acquisition in pattern["acquisitions"]:
                acquisition["physical_id"] = name + ":" + acquisition["physical_id"]
        profile["questions"].append(q)
        profile["scenarios"][0]["paired_biological_covariance"][name] = value["scenario"]["biological_covariance"]
        request["scenarios"][0]["inputs"][name] = value
    profile["categories"] = [{
        "category_id": "complete_state", "label": "Complete native state",
        "question": "Can one registered specimen provide both the molecular and functional requirements?",
        "requirements": [{"requirement_id": "native_molecular_function_state", "weight": 7,
                          "rationale": "Fictional alternative-capability requirement; no specimen equivalence claimed",
                          "alternatives": [{"question_id": name,
                                            "outcomes": ["molecular_state", "function_state"]}
                                           for name in ("specimen_a", "specimen_b")]}],
    }]
    return profile, request


def scale_error(payload, coordinates, factor=1000):
    # Congruence preserves positive definiteness, including off-diagonal terms.
    matrix = payload["scenario"]["measurement_error_covariance"]
    diagonal = [factor ** 0.5 if i in coordinates else 1 for i in range(len(matrix))]
    payload["scenario"]["measurement_error_covariance"] = [
        [value * diagonal[i] * diagonal[j] for j, value in enumerate(row)]
        for i, row in enumerate(matrix)]


def first_category(result):
    return result["scenarios"][0]["categories"][0]


def test_complete_frame_keeps_original_receipts_and_one_budget():
    p, r = example()
    before = deepcopy((p, r))
    result = execute(p, r)
    assert (p, r) == before
    row = first_category(result)
    assert (row["passed_weight"], row["weight_total"], row["task_count"]) == (7, 7, 1)
    assert row["requirements"][0]["attaining_question_ids"] == ["specimen_a", "specimen_b"]
    assert result["robust_reference_attainment"] == "attained"
    for identity, value in r["scenarios"][0]["inputs"].items():
        assert result["scenarios"][0]["questions"][identity]["receipt"] == evaluate_paired_collection(value)


def test_complementary_failures_cannot_form_a_cross_frame_mosaic():
    p, r = example()
    inputs = r["scenarios"][0]["inputs"]
    scale_error(inputs["specimen_a"], [2, 5])
    scale_error(inputs["specimen_b"], [0, 1, 3, 4])
    result = execute(p, r)
    a, b = (result["scenarios"][0]["questions"][name]["outcomes"]
            for name in ("specimen_a", "specimen_b"))
    assert a["molecular_state"]["attainment"] == b["function_state"]["attainment"] == "attained"
    row = first_category(result)
    assert row["passed_percent"] == row["upper_percent"] == 0
    assert row["requirements"][0]["attaining_question_ids"] == []
    assert row["precision_toward_targets"]["upper_percent"] < 1


def test_one_fixed_frame_must_work_across_every_scenario():
    p, r = example()
    second_reference, second_input = deepcopy(p["scenarios"][0]), deepcopy(r["scenarios"][0])
    second_reference["scenario_id"] = second_input["scenario_id"] = "other"
    p["scenarios"].append(second_reference)
    r["scenarios"].append(second_input)
    scale_error(r["scenarios"][0]["inputs"]["specimen_a"], range(6))
    scale_error(r["scenarios"][1]["inputs"]["specimen_b"], range(6))
    result = execute(p, r)
    assert all(s["reference_attainment"] == "attained" for s in result["scenarios"])
    assert result["envelope"][0]["lower_percent"] == 100
    assert result["robust_reference_attainment"] == "not_attained"
    robust = result["robust_categories"][0]
    assert robust["passed_percent"] == robust["upper_percent"] == 0
    assert robust["precision_toward_targets"]["upper_percent"] < 1


@pytest.mark.parametrize("other_state,expected", [
    ("attained", "attained"), ("unknown", "unknown"), ("not_attained", "unknown")])
def test_unknown_alternative_does_not_erase_known_complete_witness(other_state, expected):
    p, r = example()
    inputs = r["scenarios"][0]["inputs"]
    del inputs["specimen_b"]
    if other_state == "unknown":
        inputs["specimen_a"]["scenario"]["measurement_error_covariance"] = None
    elif other_state == "not_attained":
        scale_error(inputs["specimen_a"], range(6))
    result = execute(p, r)
    row = first_category(result)
    assert row["requirements"][0]["attainment"] == expected
    assert row["weight_total"] == 7 and row["upper_percent"] == 100
    assert row["passed_percent"] == (100 if expected == "attained" else 0)


def test_all_inadequate_native_frames_fail():
    p, r = example()
    for payload in r["scenarios"][0]["inputs"].values():
        scale_error(payload, range(6))
    result = execute(p, r)
    assert first_category(result)["failed_weight"] == 7
    assert result["robust_reference_attainment"] == "not_attained"


def test_incomplete_native_panel_cannot_shrink_to_available_coordinates():
    p, r = example()
    for payload in r["scenarios"][0]["inputs"].values():
        for acquisition in payload["design"]["patterns"][0]["acquisitions"]:
            acquisition["outputs"] = [o for o in acquisition["outputs"] if o["coordinate_id"] != "molecule_b"]
    row = first_category(execute(p, r))
    assert row["passed_percent"] == row["upper_percent"] == 0


@pytest.mark.parametrize("fault", ["duplicate_alternative", "repeat_budget", "missing_weight",
                                   "zero_weight", "empty_alternatives", "bad_outcome",
                                   "unregistered_frame", "wrong_version", "missing_rationale"])
def test_invalid_or_inflated_requirements_rejected(fault):
    p, r = example()
    requirements = p["categories"][0]["requirements"]
    entry = requirements[0]
    if fault == "duplicate_alternative":
        entry["alternatives"].append(deepcopy(entry["alternatives"][0]))
    elif fault == "repeat_budget":
        clone = deepcopy(entry); clone["requirement_id"] = "renamed-requirement"
        requirements.append(clone)
    elif fault == "missing_weight":
        del entry["weight"]
    elif fault == "zero_weight":
        entry["weight"] = 0
    elif fault == "empty_alternatives":
        entry["alternatives"] = []
    elif fault == "bad_outcome":
        entry["alternatives"][0]["outcomes"] = ["neural_causal_truth"]
    elif fault == "unregistered_frame":
        entry["alternatives"][0]["question_id"] = "not-registered"
    elif fault == "wrong_version":
        p["contract"] = "anibench.study-question-profile.v2"
    else:
        del entry["rationale"]
    with pytest.raises(StudyQuestionError):
        execute(p, r)


def test_duplicate_physical_measurements_and_metadata_do_not_change_result():
    p, r = example()
    expected = first_category(execute(p, r))
    for payload in r["scenarios"][0]["inputs"].values():
        payload["design"]["patterns"][0]["acquisitions"] *= 20
        payload["design"]["metadata"] = {"cost": 1e10, "ethics": "approved", "publication": "published"}
    r["study_id"] = "favored-name"
    # Original engine receipts include metadata/duplicate provenance, but question
    # outcomes and their fixed requirement budget must be invariant.
    assert first_category(execute(p, r)) == expected


def test_alternative_order_preserves_numerical_result_and_witnesses():
    p, r = example()
    scale_error(r["scenarios"][0]["inputs"]["specimen_a"], range(6))
    expected = first_category(execute(p, r))
    p["questions"].reverse()
    p["categories"][0]["requirements"][0]["alternatives"].reverse()
    actual = first_category(execute(p, r))
    for field in ("passed_weight", "weight_total", "passed_percent", "upper_percent", "precision_toward_targets"):
        assert actual[field] == expected[field]
    assert actual["requirements"][0]["attaining_question_ids"] == ["specimen_b"]


def test_uncertainty_does_not_change_acquisition_design():
    p, r = example()
    second_reference, second_input = deepcopy(p["scenarios"][0]), deepcopy(r["scenarios"][0])
    second_reference["scenario_id"] = second_input["scenario_id"] = "other"
    second_input["inputs"]["specimen_a"]["design"]["patterns"][0]["acquisitions"].pop()
    p["scenarios"].append(second_reference)
    r["scenarios"].append(second_input)
    with pytest.raises(StudyQuestionError, match="geometry"):
        execute(p, r)
