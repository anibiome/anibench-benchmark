"""Exercise the actual evaluator on the depth-versus-population falsifier."""
import json

from scripts.audit_depth_population_tradeoff import run


def test_actual_api_keeps_narrow_depth_population_and_support_distinct(tmp_path):
    run(tmp_path)
    result = json.loads((tmp_path / "actual-api-receipts.json").read_text())
    assert result["assertions_passed"] == 34
    assert len(result["scalar_task_runs"]) == 10
    assert len(result["neural_role_gate_runs"]) == 3
    assert result["no_joint_block_assumption"] is True
    assert {row["receipt"]["attainment"] for row in result["neural_role_gate_runs"]} == {
        "attained", "not_attained", "unknown"}
