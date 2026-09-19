# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Execute the published corpus and its independent pairwise oracle."""

import json
import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/registry_architecture"


def test_full_frozen_corpus_replays_without_source_verification_claim(tmp_path):
    out = tmp_path / "registry-replay"
    run = subprocess.run(
        [sys.executable, str(EXAMPLE / "replay.py"), "--out", str(out)],
        check=True, capture_output=True, text=True, cwd=tmp_path,
    )
    summary = json.loads(run.stdout)
    assert summary["actual_studies"] == 240
    assert summary["primary_cohort_sizes"] == [127, 107, 6]
    assert summary["primary_pairs"] == 13687
    assert summary["calendar_pairs"] == 15433
    result = json.loads((out / "results.json").read_text())
    assert result["frozen_snapshot_hash_verification"]["state"] == "not_requested"
    assert result["snapshot_coordinate_rederivation"]["state"] == "not_requested"
    assert sum(r["independent_oracle_pairs"] for r in result["primary_cohorts"]) == 13687
    assert all(p["withheld_enrollment_blocks_all_ordering"] for p in result["behavior_probes"])
    before = (out / "results.json").read_bytes()
    repeated = subprocess.run(
        [sys.executable, str(EXAMPLE / "replay.py"), "--out", str(out)],
        capture_output=True, cwd=tmp_path, check=False,
    )
    assert repeated.returncode != 0
    assert (out / "results.json").read_bytes() == before


def test_source_rederivation_adversaries():
    subprocess.run([sys.executable, str(EXAMPLE / "test_adapter.py")], check=True)
