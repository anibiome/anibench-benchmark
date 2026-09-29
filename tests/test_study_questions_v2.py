"""Integration adversaries over existing synthetic engines; no real-study scores."""
from copy import deepcopy

import pytest

from anibench.benchmark_v1 import (
    BenchmarkError,
    summarize_attainment,
    summarize_precision,
)
from anibench.paired_collection_v1 import evaluate_paired_collection
from anibench.question_routes_v1 import digest, route_model_sha256
from anibench.study_questions_v2 import StudyQuestionError, evaluate_study_questions


def example():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "examples/study_questions"
    return (json.loads((root / "LEGACY_PROFILE.json").read_text()),
            json.loads((root / "legacy_REQUEST.json").read_text()))


def execute(profile, request):
    request = deepcopy(request)
    request["profile_sha256"] = digest(profile)
    return evaluate_study_questions(request, trusted_profiles={digest(profile): profile})


def category(result):
    return result["scenarios"][0]["categories"][0]


def test_engines_are_executed_and_originals_preserved():
    p, r = example()
    before = deepcopy((p, r))
    result = execute(p, r)
    assert (p, r) == before
    c = category(result)
    assert c["passed_percent"] == c["upper_percent"] == 100
    assert c["weight_total"] == 3 and c["task_count"] == 2
    assert result["scenarios"][0]["questions"]["paired"]["receipt"] == evaluate_paired_collection(r["scenarios"][0]["inputs"]["paired"])
    assert result["whole_benchmark_complete"] is False


def test_missing_input_keeps_full_denominator():
    p, r = example()
    del r["scenarios"][0]["inputs"]["paired"]
    c = category(execute(p, r))
    assert (c["passed_weight"], c["unknown_weight"], c["failed_weight"], c["weight_total"]) == (2, 1, 0, 3)
    assert c["passed_percent"] == pytest.approx(200 / 3)
    assert c["upper_percent"] == 100


def test_closed_absence_and_open_inventory_have_different_results():
    p, r = example()
    route = r["scenarios"][0]["inputs"]["route"]
    route.update(observations=[], noise_order=[], noise_covariance=[])
    c = category(execute(p, r))
    assert c["passed_percent"] == c["upper_percent"] == pytest.approx(100 / 3)
    route["closed_inventory"] = None
    c = category(execute(p, r))
    assert c["passed_percent"] == pytest.approx(100 / 3) and c["upper_percent"] == 100


def test_partial_qualification_is_unknown_not_suite_conjunction_failure():
    p, r = example()
    r["scenarios"][0]["inputs"]["route"]["observations"][1]["qualified"] = None
    result = execute(p, r)
    assert category(result)["unknown_weight"] == 2
    assert result["robust_reference_attainment"] == "unknown"


def test_question_outcomes_share_one_budget_and_are_conjunctive():
    p, r = example()
    r["scenarios"][0]["inputs"]["paired"]["design"]["support"]["independently_measured_function"] = False
    c = category(execute(p, r))
    assert c["failed_weight"] == 1 and c["weight_total"] == 3


def test_duplicate_physical_data_and_metadata_do_not_improve_score():
    p, r = example()
    expected = category(execute(p, r))
    r["scenarios"][0]["inputs"]["route"]["observations"] *= 20
    paired = r["scenarios"][0]["inputs"]["paired"]
    paired["design"]["patterns"][0]["acquisitions"] *= 4
    paired["design"]["metadata"] = {"name": "Favored study", "budget": 1000000000, "ethics": "approved"}
    r["study_id"] = "different-name"
    assert category(execute(p, r)) == expected


def test_extra_assay_routes_do_not_add_question_weight():
    p, r = example()
    expected = category(execute(p, r))
    d = p["questions"][0]["definition"]
    alternate = deepcopy(d["routes"][0]); alternate["route_id"] = "another-instrument"
    d["routes"].append(alternate)
    d["task"]["model_sha256"] = route_model_sha256(d)
    r["scenarios"][0]["inputs"]["route"]["definition_sha256"] = digest(d)
    assert category(execute(p, r)) == expected


@pytest.mark.parametrize("field", ["biological_identity", "equivalent_frame"])
def test_renamed_question_cannot_gain_another_budget(field):
    p, r = example()
    extra = deepcopy(p["questions"][0]); extra["question_id"] = "renamed"
    if field == "equivalent_frame":
        extra["biological_identity"] = "new-label"
        extra["definition"]["question"] = "Renamed same target"
        extra["definition"]["task"]["task_id"] = "new-task-name"
        extra["definition"]["task"]["functionals"][0]["variance_limit"] *= 10
        extra["definition"]["model_rationale"] = "Same targets, different route catalogue metadata"
        extra["definition"]["task"]["model_sha256"] = route_model_sha256(extra["definition"])
    p["questions"].append(extra)
    with pytest.raises(StudyQuestionError, match="Duplicate biological|equivalent"):
        execute(p, r)


@pytest.mark.parametrize("mutation", ["duplicate", "zero", "float", "unknown_outcome", "learning_as_attainment"])
def test_invalid_denominators_and_predictive_claims_rejected(mutation):
    p, r = example()
    entries = p["categories"][0]["questions"]
    if mutation == "duplicate": entries.append(deepcopy(entries[0]))
    elif mutation == "zero": entries[0]["weight"] = 0
    elif mutation == "float": entries[0]["weight"] = 0.5
    elif mutation == "unknown_outcome": entries[0]["outcomes"] = ["made-up"]
    else: entries[1]["outcomes"] = ["observed_held_out_prediction"]
    with pytest.raises(StudyQuestionError): execute(p, r)


def test_study_cannot_change_common_reference_or_supply_a_result():
    p, r = example()
    r["scenarios"][0]["inputs"]["paired"]["scenario"]["biological_covariance"][0][0] += 1
    with pytest.raises(StudyQuestionError, match="frozen biological"):
        execute(p, r)
    p, r = example()
    r["scenarios"][0]["inputs"]["route"] = {"attainment": "attained"}
    with pytest.raises(StudyQuestionError): execute(p, r)


def test_invalid_frozen_definition_rejected_even_when_input_is_missing():
    p, r = example()
    r["scenarios"][0]["inputs"] = {}
    p["questions"][1]["definition"]["occasions_days"] = [1, 0]
    with pytest.raises(ValueError, match="ordered"):
        execute(p, r)


def test_lifecycle_is_shared_and_planned_does_not_require_collection():
    p, r = example()
    expected = category(execute(p, r))
    r["lifecycle"] = "planned"
    paired = r["scenarios"][0]["inputs"]["paired"]
    paired["design"]["lifecycle"] = "planned"
    paired["design"]["support"]["collection_verified"] = None
    assert category(execute(p, r)) == expected
    paired["design"]["lifecycle"] = "realized"
    with pytest.raises(StudyQuestionError, match="claim lane"):
        execute(p, r)


def test_scenarios_are_not_cherry_picked_per_question():
    p, r = example()
    s = deepcopy(p["scenarios"][0]); s["scenario_id"] = "other"
    p["scenarios"].append(s)
    s = deepcopy(r["scenarios"][0]); s["scenario_id"] = "other"
    r["scenarios"].append(s)
    for observation in r["scenarios"][0]["inputs"]["route"]["observations"]:
        observation["qualified"] = False
    r["scenarios"][1]["inputs"]["paired"]["design"]["support"]["operator_valid"] = False
    result = execute(p, r)
    assert result["robust_reference_attainment"] == "not_attained"
    assert result["envelope"][0]["upper_percent"] == pytest.approx(200 / 3)
    assert result["envelope_joint_attainability_established"] is False
    r["scenarios"].pop()
    with pytest.raises(StudyQuestionError, match="scenario set"):
        execute(p, r)


def test_canonical_summary_exact_mass_unknown_and_nonrounding():
    rows = [{"canonical_id": "easy", "weight": 999999, "attainment": "attained"},
            {"canonical_id": "hard", "weight": 1, "attainment": "unknown"}]
    c = summarize_attainment(rows)
    assert c["passed_percent"] == 99.9999 and c["unknown_weight"] == 1
    assert c["weight_total"] == 1000000 and c["upper_percent"] == 100
    rows[1]["attainment"] = "not_attained"
    assert summarize_attainment(rows)["upper_percent"] < 100
    rows[1]["attainment"] = []
    with pytest.raises(BenchmarkError): summarize_attainment(rows)


def test_precision_progress_does_not_change_exact_attainment():
    p, r = example()
    route = r["scenarios"][0]["inputs"]["route"]
    route["noise_covariance"] = [[x * 100 for x in row] for row in route["noise_covariance"]]
    result = execute(p, r)
    c = category(result)
    assert c["passed_percent"] == pytest.approx(100 / 3)
    assert c["passed_percent"] < c["precision_toward_targets"]["lower_percent"] < 100
    assert result["robust_reference_attainment"] == "not_attained"


def test_precision_unknown_uses_full_budget():
    p, r = example()
    del r["scenarios"][0]["inputs"]["paired"]
    c = category(execute(p, r))
    assert c["precision_toward_targets"] == {"lower_percent": 100 * (2 / 3), "upper_percent": 100}
    for bad in [float("nan"), -1, 2, True]:
        with pytest.raises(BenchmarkError):
            summarize_precision([{"canonical_id": "a", "weight": 1, "lower": bad, "upper": 1}])


@pytest.mark.parametrize("lifecycle", ["planned", "hypothetical", "realized"])
def test_acquisition_changes_require_a_separate_design(lifecycle):
    p, r = example()
    # Paired-only fixture supports every evidence lane without changing route profile.
    p["questions"] = p["questions"][1:]
    p["categories"][0]["questions"] = p["categories"][0]["questions"][1:]
    del r["scenarios"][0]["inputs"]["route"]
    r["lifecycle"] = lifecycle
    r["scenarios"][0]["inputs"]["paired"]["design"]["lifecycle"] = lifecycle
    p["scenarios"].append({**deepcopy(p["scenarios"][0]), "scenario_id": "other"})
    r["scenarios"].append({**deepcopy(r["scenarios"][0]), "scenario_id": "other"})
    design = r["scenarios"][1]["inputs"]["paired"]["design"]
    design["n_people"] = 32
    design["patterns"][0].update(n_people=32, controlled_arm_counts=[16, 16])
    with pytest.raises(StudyQuestionError, match="separate design"):
        execute(p, r)


def test_scenario_binding_ignores_duplicates_order_and_metadata():
    p, r = example()
    p["scenarios"].append({**deepcopy(p["scenarios"][0]), "scenario_id": "other"})
    r["scenarios"].append({**deepcopy(r["scenarios"][0]), "scenario_id": "other"})
    payload = r["scenarios"][1]["inputs"]
    payload["route"]["observations"] = list(reversed(payload["route"]["observations"])) * 2
    route = payload["route"]
    route["noise_order"].reverse()
    route["noise_covariance"] = [list(reversed(row)) for row in reversed(route["noise_covariance"])]
    design = payload["paired"]["design"]
    design["metadata"] = {"cost": 5e10}
    design["patterns"] *= 2
    for pattern in design["patterns"]:
        pattern["acquisitions"].reverse()
        for acquisition in pattern["acquisitions"]:
            acquisition["outputs"].reverse()
    assert execute(p, r)["robust_reference_attainment"] == "attained"
