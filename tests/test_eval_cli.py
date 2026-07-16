from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from anibench import assess_protocol_level1_v2, run_trial_eval
from anibench.cli import main


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "web" / "protocol-capacity-example.json"
EVAL_CARD = ROOT / "evals" / "level1" / "eval-card.json"
FAMILY_IDS = (
    "intensive",
    "extensive",
    "longitudinal",
    "causal",
    "personalized_sequential",
    "transport",
)


def _payload() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def _native_values(result: dict) -> list[list[object]]:
    return [
        [metric["value"] for metric in family["native_metrics"]]
        for family in result["scenarios"][0]["families"]
    ]


def test_eval_cli_is_the_canonical_six_task_entry_point(tmp_path: Path) -> None:
    output = tmp_path / "eval.json"
    assert main(["eval", str(PROTOCOL), "--out", str(output), "--pretty"]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))

    assert result == run_trial_eval(_payload())
    assert result == assess_protocol_level1_v2(_payload())
    assert tuple(row["family_id"] for row in result["scenarios"][0]["families"]) == FAMILY_IDS
    assert result["overall_scalar"] is None
    assert result["scenarios"][0]["public_rank"] is None
    assert result["public_rank_emission_permitted"] is False
    assert result["assessment_receipt_sha256"].startswith("sha256:")

    schema = json.loads(
        (ROOT / "schemas/v3/level1-role-aware-assessment.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(result)


def test_legacy_descriptive_command_is_byte_identical_alias(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.json"
    legacy = tmp_path / "legacy.json"
    assert main(["eval", str(PROTOCOL), "--out", str(canonical)]) == 0
    assert main(["v2-level1-assessment", str(PROTOCOL), "--out", str(legacy)]) == 0
    assert canonical.read_bytes() == legacy.read_bytes()


def test_eval_card_matches_executable_tasks_and_metrics() -> None:
    card = json.loads(EVAL_CARD.read_text(encoding="utf-8"))
    result = run_trial_eval(_payload())
    emitted = result["scenarios"][0]["families"]
    assert tuple(row["task_id"] for row in card["tasks"]) == FAMILY_IDS
    assert card["overall_scalar"] is None
    assert card["task_aggregation"] == "none_noncompensatory_vector"
    for declared, actual in zip(card["tasks"], emitted, strict=True):
        assert declared["task_id"] == actual["family_id"]
        assert declared["native_metric_ids"] == [row["metric_id"] for row in actual["native_metrics"]]
    transport = emitted[-1]
    assert transport["metric_groups"][0]["group_type"] == "transport_axis_family"
    assert card["tasks"][-1]["metric_group_contract"]["rule"] == (
        "emit_every_registered_axis_family_without_selection_or_collapse"
    )


def test_study_name_and_identifier_cannot_change_native_eval_metrics() -> None:
    original = _payload()
    blinded = deepcopy(original)
    blinded["protocol_id"] = "blinded-protocol-identity"
    assert _native_values(run_trial_eval(original)) == _native_values(run_trial_eval(blinded))


def test_proposed_and_realized_geometry_use_identical_native_math() -> None:
    proposed = _payload()
    realized = deepcopy(proposed)
    realized["protocol_id"] = "realized-geometry-example"
    realized["claim_class"] = "realized_dataset_geometry_capacity"
    proposed_result = run_trial_eval(proposed)
    realized_result = run_trial_eval(realized)
    assert realized_result["claim_class"] == "realized_dataset_geometry_capacity"
    assert realized_result["empirical_attainment"] is False
    assert _native_values(proposed_result) == _native_values(realized_result)


def test_eval_documentation_names_the_command_and_claim_boundary() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/EVALUATION.md").read_text(encoding="utf-8")
    assert "anibench eval" in readme
    assert "anibench eval" in guide
    assert "overall_scalar: null" in guide
    assert "public_rank: null" in guide
    assert "completed study" in guide
