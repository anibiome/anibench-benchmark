# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Keep the published reference declarations and executable cases in agreement."""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/broad_reference"


def assert_equivalent(actual, expected):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_equivalent(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected, strict=True):
            assert_equivalent(a, e)
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-13)
    else:
        assert actual == expected


def test_frozen_payload_and_full_replay(tmp_path):
    manifest = json.loads((EXAMPLE / "PACKAGE_MANIFEST.json").read_text())
    for row in manifest["files"]:
        data = (EXAMPLE / row["path"]).read_bytes()
        assert len(data) == row["bytes"]
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
    out = tmp_path / "replay"
    run = subprocess.run(
        [sys.executable, str(EXAMPLE / "replay.py"), "--out", str(out)],
        check=True, capture_output=True, text=True, cwd=tmp_path,
    )
    assert json.loads(run.stdout) == {"examples": 14, "sensitivity_cases": 10}
    for name in ("standard.json", "coordinate_catalogue.json",
                 "profile-declarations.json", "figure-data.json"):
        assert_equivalent(json.loads((out / name).read_text()),
                          json.loads((EXAMPLE / name).read_text()))
    preserved = (out / "figure-data.json").read_bytes()
    repeated = subprocess.run(
        [sys.executable, str(EXAMPLE / "replay.py"), "--out", str(out)],
        check=False, capture_output=True, cwd=tmp_path,
    )
    assert repeated.returncode != 0
    assert (out / "figure-data.json").read_bytes() == preserved


def test_reference_boundary_and_adversarial_oracles():
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(EXAMPLE / "test_prototype.py")],
        check=True, capture_output=True, text=True,
    )
