# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Verify public artifacts survive actual distribution builds and source replay."""

import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from scripts.illustrate_sample_requirements import requirements

ROOT = Path(__file__).resolve().parents[1]


def test_precision_example_and_dependence_tradeoff():
    independent = requirements(2, 0)
    correlated = requirements(2, 0.9)
    assert independent["enrollment_rounded_to_equal_arms"] == 214
    assert correlated["enrollment_rounded_to_equal_arms"] == 790
    assert (
        correlated["retained_precision_requirement"] > independent["retained_precision_requirement"]
    )
    assert independent["expected_simultaneous_ci_halfwidth"] <= 0.15
    assert requirements(3, 0.9)["enrollment_rounded_to_equal_arms"] == 1551


def test_built_wheel_assets_and_sdist_audit_replay(tmp_path):
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    installed = tmp_path / "installed"
    with zipfile.ZipFile(next(dist.glob("*.whl"))) as wheel:
        for relative in [
            "schemas/v2/conditional-posterior-reference.schema.json",
            "docs/CONDITIONAL_POSTERIOR_REFERENCE.md",
            "docs/LEVELS_AND_SATURATION.md",
        ]:
            assert "anibench/" + relative in wheel.namelist()
        wheel.extractall(installed)
    check = """
import json
from importlib.resources import files
from jsonschema import Draft202012Validator
from anibench.information_v2 import posterior_reference_diagnostic
schema=json.loads(files('anibench').joinpath('schemas/v2/conditional-posterior-reference.schema.json').read_text())
result=posterior_reference_diagnostic([[1]],[[1]],[[1]])
Draft202012Validator(schema).validate(result)
assert result['all_direction_reference_attainment'] is True
assert result['promotion_allowed'] is False
"""
    subprocess.run(
        [sys.executable, "-c", check],
        cwd=tmp_path,
        check=True,
        env={**os.environ, "PYTHONPATH": str(installed)},
        capture_output=True,
        text=True,
    )
    source_dir = tmp_path / "source"
    with tarfile.open(next(dist.glob("*.tar.gz"))) as source:
        # Archive generated locally above; inspect paths before extraction.
        for name in source.getnames():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
        source.extractall(source_dir, filter="data")
    source_root = next(source_dir.iterdir())
    for relative in [
        "scripts/audit_synthetic_geometry.py",
        "scripts/illustrate_sample_requirements.py",
        "docs/LEVELS_AND_SATURATION.md",
        "tests/test_posterior_reference_diagnostic.py",
        "data/synthetic_geometry_audit/actual_geometry_results.json",
    ]:
        assert (source_root / relative).is_file()
    subprocess.run(
        [sys.executable, "scripts/audit_synthetic_geometry.py"],
        cwd=source_root,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(
        (source_root / "data/synthetic_geometry_audit/actual_geometry_results.json").read_text()
    )
    assert result["synthetic_cases"] == result["passed"] == 225
    assert result["unique_information_matrices"] == 225
    assert result["repo_commit"] is None
