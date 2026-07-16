from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from anibench import compare_trial_eval_receipts, run_trial_eval
from anibench.cli import main
from anibench.comparison_v1 import EvalComparisonError


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "web" / "protocol-capacity-example.json"


def _protocol(protocol_id: str) -> dict:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["protocol_id"] = protocol_id
    return payload


def test_same_basis_comparison_is_hash_bound_pareto_not_ordinal() -> None:
    left = run_trial_eval(_protocol("preview-left"))
    right = run_trial_eval(_protocol("preview-right"))
    result = compare_trial_eval_receipts([left, right])

    assert result["comparison_class"] == "caller_declared_geometry_pareto_sandbox"
    assert result["comparison_implementation_sha256"].startswith("sha256:")
    assert result["comparison_eligible"] is True
    assert result["overall_scalar"] is None
    assert result["overall_rank"] is None
    assert result["public_rank_emission_permitted"] is False
    assert all(row["ordinal_rank"] is None for row in result["families"])
    assert {
        row["claim_class"]
        for row in result["families"][0]["protocol_vectors"]
    } == {"prospective_protocol_capacity"}
    personalized = next(
        row for row in result["families"] if row["family_id"] == "personalized_sequential"
    )
    structural = next(
        row
        for row in personalized["protocol_vectors"][0]["objectives"]
        if row["metric_id"] == "structural_personalization_eligible"
    )
    assert structural["ordering"] == "true_dominates_false"
    assert structural["value"] is False
    assert all(
        row["pareto_front_protocol_ids"] == ["preview-left", "preview-right"]
        for row in result["families"]
    )

    schema = json.loads(
        (ROOT / "schemas/v3/eval-comparison.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)


def test_compare_cli_reads_only_canonical_eval_receipts(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    compared = tmp_path / "comparison.json"
    left.write_text(json.dumps(run_trial_eval(_protocol("left"))) + "\n")
    right.write_text(json.dumps(run_trial_eval(_protocol("right"))) + "\n")

    assert main(["compare", str(left), str(right), "--out", str(compared)]) == 0
    result = json.loads(compared.read_text(encoding="utf-8"))
    assert result["protocol_ids"] == ["left", "right"]
    assert result["comparison_receipt_sha256"].startswith("sha256:")


def test_comparison_rejects_tampered_receipt() -> None:
    left = run_trial_eval(_protocol("left"))
    right = run_trial_eval(_protocol("right"))
    tampered = copy.deepcopy(right)
    tampered["scenarios"][0]["families"][0]["native_metrics"][0]["value"] = 1e30
    with pytest.raises(EvalComparisonError, match="assessment hash does not verify"):
        compare_trial_eval_receipts([left, tampered])


def test_comparison_rejects_mismatched_parameter_space_authority() -> None:
    left = run_trial_eval(_protocol("left"))
    right = run_trial_eval(_protocol("right"))
    right["protocol_capacity_result"]["uncertainty_reuse"][
        "parameter_space_source_object_sha256"
    ] = "sha256:" + "0" * 64
    payload = dict(right)
    payload.pop("assessment_receipt_sha256")
    from anibench.comparison_v1 import _canonical_sha256

    right["assessment_receipt_sha256"] = _canonical_sha256(payload)
    with pytest.raises(EvalComparisonError, match="do not share the same"):
        compare_trial_eval_receipts([left, right])


def test_comparison_preserves_family_specific_typed_unknowns() -> None:
    left_protocol = _protocol("cluster-left")
    right_protocol = _protocol("cluster-right")
    for protocol in (left_protocol, right_protocol):
        protocol["causal_geometry"]["assignment_stages"][0][
            "assignment_mechanism"
        ] = "cluster_randomized"
        for context in protocol["causal_geometry"]["transport_geometry"]["contexts"]:
            context["assignment_mechanism"] = "cluster_randomized"
    result = compare_trial_eval_receipts(
        [run_trial_eval(left_protocol), run_trial_eval(right_protocol)]
    )
    by_family = {row["family_id"]: row for row in result["families"]}
    assert by_family["intensive"]["comparison_eligible"] is True
    for family_id in ("causal", "personalized_sequential", "transport"):
        assert by_family[family_id]["comparison_eligible"] is False
        assert any(
            "DEPENDENT_RANDOMIZATION_GEOMETRY_UNSUPPORTED" in blocker
            for blocker in by_family[family_id]["blocker_codes"]
        )
        assert by_family[family_id]["ordinal_rank"] is None
