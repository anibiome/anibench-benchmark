# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

from anibench.finite_tasks_v1 import evaluate_finite_task

STAGING = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("ANIBENCH_REVIEW_ROOT", STAGING))
spec = importlib.util.spec_from_file_location(
    "chart_builder", STAGING / "scripts/build_release_charts.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_actual_replay_points_gates_and_receipt_hashes(tmp_path):
    out = tmp_path / "charts"
    receipt = builder.build_release_charts(out, ROOT)
    packet = json.loads((out / "release-results.json").read_bytes())
    runs = json.loads((out / "release-chart-receipts.json").read_bytes())
    assert receipt["scalar_points"] == len(packet["points"]) == 10
    assert len({p["point_id"] for p in packet["points"]}) == 10
    assert packet["assertions_passed"] == 34
    for point, run in zip(packet["points"], runs["scalar_task_runs"], strict=True):
        replay = evaluate_finite_task(run["request"])
        assert replay == run["receipt"]
        assert point["posterior_variance"] == replay["functionals"][0]["posterior_variance"]
        assert point["receipt_sha256"] == builder.sha(builder.encode(replay))
        value = runs
        for component in point["value_pointer"].strip("/").split("/"):
            value = value[int(component)] if isinstance(value, list) else value[component]
        assert value == point["posterior_variance"]
    assert [g["attainment"] for g in packet["neural_role_gates"]] == [
        "not_attained",
        "unknown",
        "attained",
    ]
    for gate, run in zip(packet["neural_role_gates"], runs["neural_role_gate_runs"], strict=True):
        assert evaluate_finite_task(run["request"]) == run["receipt"]
        assert gate["receipt_sha256"] == builder.sha(builder.encode(run["receipt"]))
    assert packet["overall_rank"] is None and packet["biological_threshold_validated"] is False
    for name, digest in receipt["files"].items():
        assert builder.sha((out / name).read_bytes()) == digest


def test_erp_bytes_licenses_and_public_boundary(tmp_path):
    out = tmp_path / "charts"
    builder.build_release_charts(out, ROOT)
    packet = json.loads((out / "release-results.json").read_bytes())
    assert packet["license"] == "CC-BY-4.0"
    for external in packet["external_chart_packets"]:
        assert external["license"] == "CC-BY-SA-4.0"
        assert (out / external["file"]).read_bytes() == (
            ROOT / external["source_path"]
        ).read_bytes()
    assert len(json.loads((out / "erp-design-sensitivity.json").read_bytes())["rows"]) == 27
    assert len(json.loads((out / "erp-design-plan.json").read_bytes())["rows"]) == 105
    for file in out.iterdir():
        assert file.stat().st_size < 200000
        assert all(
            s not in file.read_bytes() for s in (b"/Users/", b"/tmp/", b"/private/", b"file://")
        )


def test_reproducible_output_and_no_overwrite(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert builder.build_release_charts(a, ROOT) == builder.build_release_charts(b, ROOT)
    before = {f.name: f.read_bytes() for f in a.iterdir()}
    with pytest.raises(FileExistsError):
        builder.build_release_charts(a, ROOT)
    assert before == {f.name: f.read_bytes() for f in a.iterdir()}


def test_stale_erp_code_binding_rejected_before_output(tmp_path):
    miniature = tmp_path / "root"
    (miniature / "scripts").mkdir(parents=True)
    (miniature / "src").symlink_to(ROOT / "src", target_is_directory=True)
    shutil.copyfile(
        ROOT / "scripts/audit_depth_population_tradeoff.py",
        miniature / "scripts/audit_depth_population_tradeoff.py",
    )
    directory = miniature / "examples/calibration/erp_core"
    directory.mkdir(parents=True)
    for name in (
        "aggregate_results.json",
        "design-sensitivity.json",
        "illustrative-plan-results.json",
        "design_sensitivity.py",
        "plan_design.py",
        "illustrative-plan.json",
    ):
        shutil.copyfile(ROOT / "examples/calibration/erp_core" / name, directory / name)
    packet = json.loads((directory / "design-sensitivity.json").read_text())
    packet["script_sha256"] = "0" * 64
    (directory / "design-sensitivity.json").write_text(json.dumps(packet))
    out = tmp_path / "charts"
    with pytest.raises(ValueError, match="code binding is stale"):
        builder.build_release_charts(out, miniature)
    assert not out.exists()
