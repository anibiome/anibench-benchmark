"""Native-role admission and independent preservation/anti-gaming checks."""
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from anibench.cli import main
from anibench.cross_domain_collection_v1 import (
    INPUT_SCHEMA,
    compile_cross_domain_collection,
    evaluate_cross_domain_collection,
    native_key,
)
from anibench.paired_collection_v1 import evaluate_paired_collection
from anibench.paired_question_v1 import digest

ROOT = Path(__file__).resolve().parents[1]


def example():
    return json.loads((ROOT / "examples/cross_domain_collection/input.json").read_text())


def bind(payload):
    for key in ("scenario", "design"):
        payload[key]["question_sha256"] = digest(payload["question"])


def test_native_roles_preserve_exact_legacy_arithmetic():
    source, compiled = compile_cross_domain_collection(example())
    result = evaluate_cross_domain_collection(source)
    old = evaluate_paired_collection(compiled)
    assert result["compatibility_receipt"] == old
    assert [c["biological_domain"] for c in result["native_coordinates"]] == ["digital", "cognitive"]
    for key, row in old["results"].items():
        assert result["results"][native_key(key)]["adequacy_percent"] == row["adequacy_percent"]
        assert result["results"][native_key(key)]["independent_people"] == row["independent_people"]
    assert "molecular" not in json.dumps(result["results"])
    assert "molecular" not in json.dumps(result["coverage"])
    assert result["whole_benchmark_complete"] is False


def test_domain_name_changes_no_numbers_and_old_receipt_retains_binding():
    payload = example()
    before = evaluate_cross_domain_collection(payload)
    payload["question"]["coordinates"][0]["biological_domain"] = "neural"
    bind(payload)
    after = evaluate_cross_domain_collection(payload)
    assert before["results"] == after["results"]
    assert before["question_sha256"] != after["question_sha256"]
    # Same algebra, but the native contract/receipt must retain the distinction.
    assert before["calculation_sha256"] != after["calculation_sha256"]
    assert before["compatibility_receipt"] == after["compatibility_receipt"]


def test_native_units_change_covariances_but_not_attainment():
    payload = example()
    before = evaluate_cross_domain_collection(payload)
    payload["question"]["coordinates"][0]["unit"] = "gravity"
    scales = np.diag([.001, 1, .001, 1])
    for key in ("biological_covariance", "measurement_error_covariance"):
        payload["scenario"][key] = (scales @ np.array(payload["scenario"][key]) @ scales).tolist()
    for key, values in payload["question"]["tolerances"].items():
        if key.startswith("observer") or key == "change_cross_covariance":
            payload["question"]["tolerances"][key] = [v * .001 for v in values]
    bind(payload)
    after = evaluate_cross_domain_collection(payload)
    for key, row in before["results"].items():
        assert after["results"][key]["state"] == row["state"]
        assert after["results"][key]["adequacy_percent"] == pytest.approx(row["adequacy_percent"])


def test_native_scalar_mean_change_matches_direct_formula():
    payload = example()
    result = evaluate_cross_domain_collection(payload)
    b = np.array(payload["scenario"]["biological_covariance"])
    r = np.array(payload["scenario"]["measurement_error_covariance"])
    v = b + r
    expected = (v[3, 3] + v[1, 1] - 2 * v[1, 3]) / 256
    row = result["results"]["function_mean_change"]
    assert row["lower_support_result"]["covariance"][0][0] == pytest.approx(expected)


def test_unlinked_observers_do_not_create_functional_relationship():
    payload = example()
    first = payload["design"]["patterns"][0]
    second = deepcopy(first)
    first.update(pattern_id="observer-only", n_people=128, controlled_arm_counts=None)
    second.update(pattern_id="function-only", n_people=128, controlled_arm_counts=None)
    first["acquisitions"] = [a for a in first["acquisitions"] if a["outputs"][0]["coordinate_id"] == "activity"]
    second["acquisitions"] = [a for a in second["acquisitions"] if a["outputs"][0]["coordinate_id"] == "reaction_time"]
    payload["design"]["patterns"] = [first, second]
    result = evaluate_cross_domain_collection(payload)
    assert result["results"]["observer_state"]["state"] == "attained"
    assert result["results"]["function_state"]["state"] == "attained"
    assert result["results"]["observer_function_change_relation"]["state"] == "not_supported"
    assert result["conditional_functional_learning"]["baseline_function_and_observer"]["state"] == "not_supported"


def test_null_noise_is_unknown_and_observation_is_not_control():
    payload = example()
    rows = evaluate_cross_domain_collection(payload)["results"]
    assert rows["controlled_function_effect"]["state"] == "not_supported"
    assert rows["observer_function_change_relation"]["state"] != "not_supported"
    payload["scenario"]["measurement_error_covariance"] = None
    rows = evaluate_cross_domain_collection(payload)["results"]
    assert rows["observer_state"]["adequacy_percent"] == {"lower": 0, "upper": 100}
    assert rows["observer_function_change_relation"]["lower_support_result"]["reason"] == "Estimator covariance is unavailable or numerically unresolved"


@pytest.mark.parametrize("mutation", ["stale", "empty-role", "two-functions", "unknown-domain", "unknown-field"])
def test_invalid_native_contract_is_rejected_before_legacy_translation(mutation):
    payload = example()
    if mutation == "stale":
        payload["question"]["question"] += " Changed"
    elif mutation == "empty-role":
        payload["question"]["coordinates"][0].pop("role")
        bind(payload)
    elif mutation == "two-functions":
        payload["question"]["coordinates"][0]["role"] = "function"
        bind(payload)
    elif mutation == "unknown-domain":
        payload["question"]["coordinates"][0]["biological_domain"] = "superintelligence"
        bind(payload)
    else:
        payload["question"]["manual_score"] = 100
        bind(payload)
    with pytest.raises(ValueError):
        evaluate_cross_domain_collection(payload)


def test_duplicate_and_metadata_change_do_not_buy_information():
    payload = example()
    before = evaluate_cross_domain_collection(payload)
    payload["design"]["patterns"] *= 2
    payload["design"]["patterns"][0]["acquisitions"] *= 3
    payload["design"]["metadata"] = {"cost": 100000000, "ethics": "approved"}
    after = evaluate_cross_domain_collection(payload)
    assert before["calculation_sha256"] == after["calculation_sha256"]
    assert before["input_sha256"] != after["input_sha256"]


def test_schema_and_create_only_cli(tmp_path, capsys):
    assert json.loads((ROOT / "schemas/cross_domain_collection/v1/input.schema.json").read_text()) == INPUT_SCHEMA
    source, target = tmp_path / "private-input.json", tmp_path / "private-output.json"
    source.write_text(json.dumps(example()))
    assert main(["cross-domain-collection", str(source), "--out", str(source)]) == 2
    assert main(["cross-domain-collection", str(source), "--out", str(target)]) == 0
    saved = target.read_bytes()
    assert main(["cross-domain-collection", str(source), "--out", str(target)]) == 2
    assert target.read_bytes() == saved
    result = json.loads(saved)
    receipt = result.pop("receipt_sha256")
    assert digest(result) == receipt
    assert str(tmp_path) not in capsys.readouterr().err
