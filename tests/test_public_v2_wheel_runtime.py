from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_built_wheel_runs_only_current_front_doors_from_unpacked_install(tmp_path: Path) -> None:
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
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    check = r"""
import hashlib
import importlib.util
import json
from importlib import resources
from pathlib import Path

import anibench
import anibench.release as public_release
from anibench.level1_target_v3 import readback_role_aware_authority
from anibench.studio_product import build_studio_comparator_atlas

root = resources.files("anibench")
protocol = json.loads(root.joinpath("web/protocol-capacity-example.json").read_text())
evaluation = anibench.run_trial_eval(protocol)
assert len(evaluation["scenarios"][0]["families"]) == 6
assert evaluation["overall_scalar"] is None
peer_protocol = dict(protocol)
peer_protocol["protocol_id"] = "installed-wheel-comparison-peer"
peer_evaluation = anibench.run_trial_eval(peer_protocol)
comparison = anibench.compare_trial_eval_receipts([evaluation, peer_evaluation])
illustrative_source = root.joinpath("examples/v2/illustrative-protocol-source.json")
illustrative_source_sha256 = "sha256:" + hashlib.sha256(illustrative_source.read_bytes()).hexdigest()
request = json.loads(root.joinpath("web/optimizer-protocol-example.json").read_text())
request["base_protocol"] = protocol
design = json.loads(root.joinpath("examples/v2/illustrative-design.json").read_text())
authority = readback_role_aware_authority()
atlas = build_studio_comparator_atlas(Path(anibench.__file__).parent)
level1 = anibench.assess_protocol_level1_v2(protocol)
result = {
    "module": anibench.__file__,
    "exports": sorted(anibench.__all__),
    "legacy_exports": [
        name for name in ("score_study", "optimize_trial_design", "LANES", "ScoreResult")
        if hasattr(anibench, name)
    ],
    "release_exports": sorted(public_release.__all__),
    "legacy_release_modules": [
        name for name in (
            "anibench.release.receipt",
            "anibench.release.verify",
            "anibench.release.validation_run",
            "anibench.release.external_validation",
        ) if importlib.util.find_spec(name) is not None
    ],
    "protocol_scalar": anibench.compile_protocol_capacity_v2(protocol)["overall_scalar"],
    "illustrative_source_present": illustrative_source.is_file(),
    "illustrative_source_bound": protocol["parameter_space"]["source_object_sha256"] == illustrative_source_sha256,
    "optimizer_scalar": anibench.optimize_protocol_design_v2(request)["overall_scalar"],
    "design_promotion": anibench.compile_trial_design_v2(design)["promotion_allowed"],
    "authority_contract": authority["contract"],
    "authority_promotion": authority["promotion_allowed"],
    "authority_global_enrollment_state": authority["global_enrollment_state"],
    "atlas_study_count": atlas["study_count"],
    "atlas_field_fact_count": atlas["field_provenance_receipt"]["known_fact_count"],
    "atlas_downgraded_unknown_count": atlas["field_provenance_receipt"]["downgraded_unknown_fact_count"],
    "atlas_all_known_machine_resolved": atlas["field_provenance_receipt"]["all_known_fields_machine_resolved"],
    "atlas_manual_validated": atlas["field_provenance_receipt"]["manual_interpretations_mechanically_validated"],
    "level1_contract": level1["schema_version"],
    "level1_comparison_eligible": level1["comparison_eligible"],
    "level1_scalar": level1["overall_scalar"],
    "level1_family_count": len(level1["scenarios"][0]["families"]),
    "comparison_contract": comparison["schema_version"],
    "comparison_class": comparison["comparison_class"],
    "comparison_scalar": comparison["overall_scalar"],
    "comparison_rank": comparison["overall_rank"],
    "level1_target_states": [row["level1_target_attainment"]["state"] for row in level1["scenarios"][0]["families"]],
    "superseded_assets": [
        name for name in (
            "spec/v2/level1/reference-design.json",
            "spec/v2/level1/reference-protocol-mapping-receipt.json",
            "spec/v2/level1/normative-target-requirements.v2.json",
            "level1_assessment_v2.py",
            "protocol_authority_v2.py",
        ) if root.joinpath(name).is_file()
    ],
}
print(json.dumps(result, sort_keys=True))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(installed)
    environment["PYTHONNOUSERSITE"] = "1"
    runtime = subprocess.run(
        [sys.executable, "-c", check],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert runtime.returncode == 0, runtime.stderr or runtime.stdout
    result = json.loads(runtime.stdout)
    assert Path(result["module"]).is_relative_to(installed)
    assert result["legacy_exports"] == []
    assert result["release_exports"] == [
        "BundleScanReport",
        "ScanFinding",
        "redact_text_for_log",
        "scan_public_bundle",
    ]
    assert result["legacy_release_modules"] == []
    assert result["protocol_scalar"] is None
    assert result["illustrative_source_present"] is True
    assert result["illustrative_source_bound"] is True
    assert result["optimizer_scalar"] is None
    assert result["design_promotion"] is False
    assert result["authority_contract"] == "anibench.level1-role-aware-target-installed-readback.v1"
    assert result["authority_promotion"] is False
    assert result["authority_global_enrollment_state"] == "unresolved"
    assert result["atlas_study_count"] == 16
    assert result["atlas_field_fact_count"] == 27
    assert result["atlas_downgraded_unknown_count"] == 328
    assert result["atlas_all_known_machine_resolved"] is True
    assert result["atlas_manual_validated"] is False
    assert result["level1_contract"] == "anibench.level1-role-aware-assessment.v3-candidate2"
    assert result["level1_comparison_eligible"] is False
    assert result["level1_scalar"] is None
    assert result["level1_family_count"] == 6
    assert result["comparison_contract"] == "anibench.eval-comparison.v1"
    assert result["comparison_class"] == "caller_declared_geometry_pareto_sandbox"
    assert result["comparison_scalar"] is None
    assert result["comparison_rank"] is None
    assert result["level1_target_states"] == ["unresolved"] * 6
    assert result["superseded_assets"] == []
