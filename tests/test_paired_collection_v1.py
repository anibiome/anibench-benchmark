"""Partial-acquisition scientific counterexamples and compatibility oracles."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from anibench.cli import main
from anibench.paired_collection_v1 import INPUT_SCHEMA, evaluate_paired_collection
from anibench.paired_question_v1 import evaluate_paired_question

ROOT = Path(__file__).resolve().parents[1]


def example():
    base = json.loads((ROOT / "examples/paired_question/input.json").read_text())
    old = base["design"]
    pattern = {"pattern_id": "complete", "n_people": 256,
               "closed_acquisition_inventory": True, "controlled_arm_counts": [128, 128],
               "acquisitions": []}
    # A single molecular assay has multiple correlated outputs at each occasion.
    for t in (0, 1):
        pattern["acquisitions"].extend([
            {"physical_id": f"assay-{t}", "occasion_index": t,
             "outputs": [{"coordinate_id": name, "qualified": True}
                         for name in ("molecule_a", "molecule_b")]},
            {"physical_id": f"force-{t}", "occasion_index": t,
             "outputs": [{"coordinate_id": "grip_force", "qualified": True}]},
        ])
    base["contract"] = "anibench.paired-collection-input.v1"
    base["design"] = {
        "question_sha256": old["question_sha256"], "lifecycle": old["lifecycle"],
        "n_people": 256, "closed_pattern_roster": True, "patterns_are_disjoint": True,
        "homogeneous_reference_across_patterns": True, "acquisition_independent_of_state": True,
        "support": old["support"], "metadata": old["metadata"], "patterns": [pattern],
    }
    return base


def keep(pattern, names, times=(0, 1)):
    pattern["acquisitions"] = [a for a in pattern["acquisitions"] if a["occasion_index"] in times]
    for acquisition in pattern["acquisitions"]:
        acquisition["outputs"] = [o for o in acquisition["outputs"] if o["coordinate_id"] in names]
    pattern["acquisitions"] = [a for a in pattern["acquisitions"] if a["outputs"]]


def test_complete_pattern_matches_existing_estimator():
    old = evaluate_paired_question(json.loads((ROOT / "examples/paired_question/input.json").read_text()))
    result = evaluate_paired_collection(example())
    assert result["canonical_physical_slots"] == 4
    for key, row in old["results"].items():
        assert result["results"][key]["lower_support_result"] == row
        assert result["results"][key]["upper_support_result"] == row
    for key in ("mean_only", "baseline_function", "baseline_function_and_molecular"):
        assert result["conditional_functional_learning"][key]["lower_support_result"] == old["conditional_functional_learning"][key]


def test_published_schema_and_example_match_runtime():
    assert json.loads((ROOT / "schemas/paired_collection/v1/input.schema.json").read_text()) == INPUT_SCHEMA
    payload = json.loads((ROOT / "examples/paired_collection/input.json").read_text())
    result = evaluate_paired_collection(payload)
    assert result["results"]["molecular_function_change_relation"]["independent_people"] == {"lower": 16, "upper": 16}
    assert result["results"]["function_mean_change"]["independent_people"] == {"lower": 256, "upper": 256}


def test_cli_create_only_and_private_errors(tmp_path, capsys):
    payload = example()
    source = tmp_path / "private-source.json"
    source.write_text(json.dumps(payload))
    before = source.read_bytes()
    assert main(["paired-collection", str(source), "--out", str(source)]) == 2
    assert source.read_bytes() == before
    output = tmp_path / "private-result.json"
    assert main(["paired-collection", str(source), "--out", str(output)]) == 0
    saved = output.read_bytes()
    assert main(["paired-collection", str(source), "--out", str(output)]) == 2
    assert output.read_bytes() == saved
    assert json.loads(saved) == evaluate_paired_collection(payload)
    errors = capsys.readouterr().err
    assert str(source) not in errors
    assert str(output) not in errors


def test_unlinked_marginals_keep_depth_but_not_relationship():
    payload = example()
    molecular = payload["design"]["patterns"][0]
    functional = deepcopy(molecular)
    molecular.update(pattern_id="molecular", n_people=128, controlled_arm_counts=[64, 64])
    functional.update(pattern_id="functional", n_people=128, controlled_arm_counts=[64, 64])
    keep(molecular, {"molecule_a", "molecule_b"})
    keep(functional, {"grip_force"})
    payload["design"]["patterns"] = [molecular, functional]
    result = evaluate_paired_collection(payload)
    rows = result["results"]
    assert rows["molecular_state"]["state"] == "attained"
    assert rows["function_state"]["state"] == "attained"
    assert rows["molecular_function_change_relation"]["independent_people"] == {"lower": 0, "upper": 0}
    assert rows["molecular_function_change_relation"]["state"] == "not_supported"
    assert result["conditional_functional_learning"]["baseline_function_and_molecular"]["state"] == "not_supported"
    # Independent oracle: only 128 functional pairs support mean change.
    old = json.loads((ROOT / "examples/paired_question/input.json").read_text())
    full = evaluate_paired_question(old)["results"]["function_mean_change"]["covariance"][0][0]
    assert rows["function_mean_change"]["lower_support_result"]["covariance"][0][0] == pytest.approx(2 * full)


def test_joint_subset_is_not_total_enrollment_and_missing_future_molecules_do_not_block_prediction():
    payload = example()
    complete = payload["design"]["patterns"][0]
    partial = deepcopy(complete)
    complete.update(n_people=16, controlled_arm_counts=[8, 8])
    partial.update(pattern_id="baseline-molecules", n_people=240, controlled_arm_counts=[120, 120])
    partial["acquisitions"] = [a for a in partial["acquisitions"] if a["physical_id"] != "assay-1"]
    payload["design"]["patterns"].append(partial)
    result = evaluate_paired_collection(payload)
    assert result["results"]["molecular_function_change_relation"]["independent_people"] == {"lower": 16, "upper": 16}
    assert result["conditional_functional_learning"]["baseline_function_and_molecular"]["independent_people"] == {"lower": 256, "upper": 256}
    assert result["results"]["function_mean_change"]["independent_people"] == {"lower": 256, "upper": 256}


def test_duplicate_patterns_acquisitions_and_metadata_do_not_inflate():
    payload = example()
    original = evaluate_paired_collection(payload)
    payload["design"]["patterns"] *= 3
    payload["design"]["patterns"][0]["acquisitions"] *= 2
    payload["design"]["metadata"] = {"cost": 5e10, "ethics": "approved", "name": "Different study"}
    result = evaluate_paired_collection(payload)
    assert result["calculation_sha256"] == original["calculation_sha256"]
    assert result["input_sha256"] != original["input_sha256"]
    assert result["canonical_patterns"] == 1
    assert result["canonical_physical_slots"] == 4


def test_disjoint_pattern_splitting_preserves_calculation():
    payload = example()
    original = evaluate_paired_collection(payload)
    first = payload["design"]["patterns"][0]
    first.update(n_people=128, controlled_arm_counts=[64, 64])
    second = deepcopy(first)
    second["pattern_id"] = "other-disjoint-people"
    payload["design"]["patterns"].append(second)
    assert evaluate_paired_collection(payload)["calculation_sha256"] == original["calculation_sha256"]


def test_unknown_roster_retained_as_finite_outer_bounds():
    payload = example()
    payload["design"]["closed_pattern_roster"] = None
    payload["design"]["patterns"][0].update(n_people=16, controlled_arm_counts=[8, 8])
    result = evaluate_paired_collection(payload)
    assert result["omitted_people"] == 240
    row = result["results"]["function_mean_change"]
    assert row["independent_people"] == {"lower": 16, "upper": 256}
    assert row["lower_support_result"]["covariance"][0][0] == pytest.approx(16 * row["upper_support_result"]["covariance"][0][0])
    assert row["adequacy_percent"]["lower"] < row["adequacy_percent"]["upper"]


def test_known_absence_dominates_unknown_and_no_people_is_failure():
    payload = example()
    payload["design"]["patterns"][0]["closed_acquisition_inventory"] = None
    payload["design"]["patterns"][0]["acquisitions"][0]["outputs"][0]["qualified"] = False
    result = evaluate_paired_collection(payload)
    assert result["results"]["molecular_state"]["adequacy_percent"] == {"lower": 0, "upper": 0}
    payload["design"]["n_people"] = 0
    payload["design"]["patterns"] = []
    assert all(r["state"] == "not_supported" for r in evaluate_paired_collection(payload)["results"].values())


def test_selection_unknown_does_not_erase_individual_resolution():
    payload = example()
    payload["design"]["acquisition_independent_of_state"] = None
    rows = evaluate_paired_collection(payload)["results"]
    assert rows["function_state"]["state"] == "attained"
    assert rows["function_mean_change"]["state"] == "unknown"


def test_arm_upper_bound_respects_definite_imbalance():
    payload = example()
    payload["design"]["closed_pattern_roster"] = None
    payload["design"]["patterns"][0].update(n_people=200, controlled_arm_counts=[199, 1])
    row = evaluate_paired_collection(payload)["results"]["controlled_function_effect"]
    assert row["arm_count_bounds"]["optimistic_feasible_allocation"] == [199, 57]
    low = row["lower_support_result"]["covariance"][0][0]
    high = row["upper_support_result"]["covariance"][0][0]
    assert high / low == pytest.approx((1 / 199 + 1 / 57) / (1 / 199 + 1))


def test_unresolved_acquisition_cannot_reassign_known_arms():
    payload = example()
    pattern = payload["design"]["patterns"][0]
    pattern["controlled_arm_counts"] = [255, 1]
    for acquisition in pattern["acquisitions"]:
        for output in acquisition["outputs"]:
            output["qualified"] = None
    row = evaluate_paired_collection(payload)["results"]["controlled_function_effect"]
    assert row["independent_people"] == {"lower": 0, "upper": 256}
    assert row["arm_count_bounds"]["optimistic_feasible_allocation"] == [255, 1]
    # Biological change variance = 100 + 100 - 2*60; error adds 4+4.
    assert row["upper_support_result"]["covariance"][0][0] == pytest.approx(
        88 * (1 / 255 + 1)
    )


@pytest.mark.parametrize("mutation", ["overlap", "roster", "arms", "duplicate-pattern", "physical", "repeat", "unknown-field", "boolean-count", "stale-question"])
def test_invalid_inputs_rejected(mutation):
    payload = example()
    design = payload["design"]
    pattern = design["patterns"][0]
    if mutation == "overlap":
        design["patterns_are_disjoint"] = False
    elif mutation == "roster":
        design["n_people"] = 255
    elif mutation == "arms":
        pattern["controlled_arm_counts"] = [128, 127]
    elif mutation == "duplicate-pattern":
        other = deepcopy(pattern)
        other["n_people"] = 0
        other["controlled_arm_counts"] = [0, 0]
        design["patterns"].append(other)
    elif mutation == "physical":
        pattern["acquisitions"][2]["physical_id"] = pattern["acquisitions"][0]["physical_id"]
    elif mutation == "repeat":
        other = deepcopy(pattern["acquisitions"][0])
        other["physical_id"] = "another-assay"
        pattern["acquisitions"].append(other)
    elif mutation == "unknown-field":
        design["bonus"] = 20
    elif mutation == "boolean-count":
        pattern["n_people"] = True
    else:
        payload["question"]["question_id"] = "Changed without rebinding"
    with pytest.raises(ValueError):
        evaluate_paired_collection(payload)
