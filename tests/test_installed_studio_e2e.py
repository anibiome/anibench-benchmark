from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.verify_installed_studio import verify_installed_studio


ROOT = Path(__file__).resolve().parents[1]


def test_exact_unpacked_wheel_serves_complete_studio_http_contract(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr or build.stdout
    wheel = next(dist.glob("anibench-*.whl"))

    receipt = verify_installed_studio(wheel, require_browser=False)

    assert receipt["contract"] == "anibench.installed-studio-e2e-gate.v1"
    assert receipt["passed"] is True
    assert receipt["runtime"] == {
        "installation_mode": "wheel_archive_unpacked_outside_source_checkout",
        "module_path_relative": "anibench/__init__.py",
        "loopback_binding": True,
    }
    assert receipt["browser"] is None
    assert receipt["http"]["passed"] is True
    assert receipt["http"]["checks"] == [
        "root_html_and_security_headers",
        "packaged_html_js_css_svg",
        "health_get",
        "primary_design_post_10m_and_lane_invariance",
        "comparator_atlas_get",
        "packaged_example_gets",
        "protocol_capacity_post",
        "level1_role_aware_authority_get",
        "recursive_level1_template_retired",
        "level1_assessment_post_and_deterministic_receipt",
        "clinicaltrials_registry_intake_routes_fail_closed_without_network",
        "protocol_optimizer_post",
        "all_retired_post_routes",
        "static_404_and_path_traversal",
    ]
    assert receipt["http"]["planned_design_population"] == 10_000_000
    assert (
        receipt["http"]["planned_design_participant_module_observations"]
        == 3_723_000_000_000
    )
    assert receipt["http"]["planned_realized_geometry_equal"] is True
    assert (
        receipt["http"]["planned_design_input_sha256"]
        != receipt["http"]["realized_design_input_sha256"]
    )
    assert receipt["http"]["comparator_study_count"] == 16
    assert receipt["http"]["level1_family_count"] == 6
    assert receipt["http"]["level1_target_state"] == "unresolved"
    assert receipt["http"]["level1_overall_scalar"] is None
    assert len(receipt["http"]["level1_authority_sha256"]) == 64
    assert receipt["http"]["level1_receipt_replay_equal"] is True
    assert receipt["http"]["optimizer_candidate_count"] >= 1
