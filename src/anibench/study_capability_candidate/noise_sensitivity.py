# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Frozen common-noise sensitivity; distinct from normative AB1/AB2 scenarios."""

import hashlib
import json
from importlib.resources import files
from pathlib import Path

from anibench.finite_suites_v1 import scientific_frame_sha256

from .compiler import digest, reference_filename, registry
from .level_decision import decide_level
from .linked_workload import evaluate

SCENARIOS = {"q0.0625": 0.0625, "q0.25": 0.25, "q1": 1.0, "q2": 2.0}


def profile(level="AB1"):
    if level not in ["AB1", "AB2"]:
        raise ValueError("Unknown native resolution level")
    out = json.loads(files(__package__).joinpath(reference_filename(level)).read_text())
    out["profile_id"] = out["profile_id"] + ".common-noise-grid-v1"
    out["profile_type"] = "custom"
    out["scope"] = (
        "Frozen common measurement-noise sensitivity profile; same native quantities and resolution as "
        + level
        + " but not the normative level scenario frame."
    )
    out["scenario_ids"] = list(SCENARIOS)
    out["parent_sha256"] = None if level == "AB1" else digest(profile("AB1"))
    for entry in out["targets"]:
        t = entry["task"]
        t["model_sha256"] = digest(
            {
                "base_model_sha256": t["model_sha256"],
                "measurement_noise_scenarios": SCENARIOS,
                "profile": "common-noise-grid-v1",
            }
        )
        t["task_version"] += ".common-noise-grid-v1"
        entry["frame_sha256"] = scientific_frame_sha256(t)
    return out


def evaluate_sensitivity(design, level="AB1"):
    reference = profile(level)
    result, components = evaluate(
        design, 1.0 if level == "AB1" else 0.5, scenario_registry=SCENARIOS
    )
    result["measurement_noise_profile"] = {
        "id": "common-noise-grid-v1",
        "multipliers": SCENARIOS,
        "meaning": "q multiplies the complete fixed within-coordinate measurement-error covariance; population biological covariance and all source design geometry remain unchanged.",
        "native_increment_manifest_sha256": digest(registry()),
        "calibration": "Declared common-noise sensitivity only; no empirical cross-assay equivalence.",
    }
    result["sensitivity_decision"] = decide_level(result, components, reference)
    result["provenance"]["calculation_files"]["noise_sensitivity.py"] = (
        "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    result["reference_profile_sha256"] = digest(reference)
    result.pop("result_sha256", None)
    result["result_sha256"] = digest(result)
    return result, components, reference
