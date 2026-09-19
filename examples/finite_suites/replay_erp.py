# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Replay aggregate-only, hypothetical ERP finite-suite precision boundaries."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import anibench
from anibench.finite_suites_v1 import (
    evaluate_finite_suite,
    scientific_frame_sha256,
    suite_sha256,
)
from anibench.finite_tasks_v1 import finite_task_sha256

PINS = {
    "aggregate": "29ed1afb9a2554f41e26559bc85e04b5f66e06358f58d1ea141f6703d8f6bf83",
    "profile": "c2474cc4b5ae2ba5ebbd4b0f101a6080c547f8b2094f0234e0d42afa3132efcb",
}
ATTRIBUTION = (
    "Source-derived outputs: CC-BY-SA-4.0. ERP CORE by Emily S. Kappenman and "
    "Steven J. Luck; Kappenman et al. (2021), doi:10.1016/j.neuroimage.2020.117465; "
    "Zhang and Luck (2023), doi:10.1111/psyp.14264. Analysis modifications by ANI. "
    "No endorsement implied. Original analysis code Apache-2.0. Source license "
    "CC BY versus CC BY-SA discrepancy retained; see ERP source manifest."
)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def asset(relative):
    roots = [*Path(__file__).resolve().parents, Path(anibench.__file__).resolve().parent]
    for root in roots:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Asset not installed; supply explicit path: {relative}")


def replay(out, *, aggregate=None, profile=None, source_manifest=None):
    """Create a new output directory; originals are read-only and pinned."""
    aggregate = aggregate or asset("examples/calibration/erp_core/aggregate_results.json")
    profile = profile or asset("spec/finite_suites/v1/erp-p3b-resolution.json")
    source_manifest = source_manifest or asset("examples/calibration/erp_core/source_manifest.json")
    inputs = {
        "aggregate": Path(aggregate).read_bytes(),
        "profile": Path(profile).read_bytes(),
        "source_manifest": Path(source_manifest).read_bytes(),
    }
    for name, pin in PINS.items():
        if hashlib.sha256(inputs[name]).hexdigest() != pin:
            raise ValueError(f"Stale or changed pinned {name}")
    aggregate_value = json.loads(inputs["aggregate"])
    r1 = json.loads(inputs["profile"])
    t1 = r1["targets"][0]["task"]
    if t1["source_sha256"] != sha(inputs["source_manifest"]):
        raise ValueError("Source manifest does not match frozen profile")
    v = aggregate_value["analytic_contrast_variance_mean_uV2"]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
        raise ValueError("Expected finite positive source contrast measurement variance")
    r2 = copy.deepcopy(r1)
    r2["profile_id"] = "erp-p3b-resolution.illustrative.R2.v1"
    r2["parent_sha256"] = suite_sha256(r1)
    r2["tolerance_authority"] = (
        "Illustrative child: half-width 0.5 microvolt; variance limit one quarter of R1. Not a biological minimum."
    )
    r2["targets"][0]["task"]["functionals"][0]["variance_limit"] /= 4
    strong = copy.deepcopy(r1)
    strong["profile_id"] = "synthetic-strong-prior.likelihood-only.v1"
    strong["profile_type"] = "custom"
    strong["scope"] = "Synthetic strong-prior adversary, separate from R1/R2 scientific frame"
    strong["tolerance_authority"] = (
        "Synthetic prior precision 100; inherited illustrative variance limit. No empirical prior authority."
    )
    strong["targets"][0]["task"]["prior_precision"] = [[100]]
    strong["targets"][0]["frame_sha256"] = scientific_frame_sha256(strong["targets"][0]["task"])
    posterior = copy.deepcopy(strong)
    posterior["profile_id"] = "synthetic-strong-prior.posterior-total.v1"
    posterior["precision_basis"] = "posterior_total"
    profiles = {suite_sha256(p): p for p in [r1, r2, strong, posterior]}
    script_hash = sha(Path(__file__).read_bytes())
    source_bindings = {name: sha(raw) for name, raw in inputs.items()}
    source_bindings["replay_script"] = script_hash
    source_bindings["trusted_profiles"] = sha(encoded(profiles))
    outputs = {"trusted-profiles.json": encoded(profiles)}
    rows = []
    for depth, label, selected in [
        *[(d, level, p) for d in [1, 22, 23, 90, 91] for level, p in [("R1", r1), ("R2", r2)]],
        (0, "strong-prior-likelihood", strong),
        (0, "strong-prior-posterior", posterior),
    ]:
        design_id = f"hypothetical-source-schedule-depth-{depth}"
        provenance = {
            "contract": "anibench.synthetic-erp-design.v1",
            "design_id": design_id,
            "source_bindings": source_bindings,
            "source_schedule_multiplier": depth,
            "mean_source_contrast_variance_microvolt2": v,
            "geometry_rule": "J=d/v; inverse-depth scaling is assumed, not empirically verified",
            "scope": "Homogeneous current-session score approximation; no each-person guarantee, repeated-session decomposition or population transport validity",
            "license": "CC-BY-SA-4.0",
            "attribution": ATTRIBUTION,
        }
        provenance_bytes = encoded(provenance)
        outputs[f"{design_id}.provenance.json"] = provenance_bytes
        binding = {"design_id": design_id, "design_source_sha256": sha(provenance_bytes)}
        target = selected["targets"][0]
        task = target["task"]
        evaluation = {
            "contract": "anibench.finite-task-request.v1",
            "task": task,
            "task_sha256": finite_task_sha256(task),
            "evidence": {
                "identifiability": True,
                "collection_verified": None,
                "support": [dict(role, supported=True) for role in task["required_support"]],
            },
            "geometry": {"model_sha256": task["model_sha256"], "information_matrix": [[depth / v]]},
        }
        request = {
            **binding,
            "contract": "anibench.finite-suite-request.v1",
            "profile_sha256": suite_sha256(selected),
            "scenarios": [
                {
                    **binding,
                    "scenario_id": "declared-model",
                    "targets": [
                        {
                            **binding,
                            "canonical_id": target["canonical_id"],
                            "known_absent": False,
                            "request": evaluation,
                        }
                    ],
                }
            ],
        }
        result = evaluate_finite_suite(request, trusted_profiles=profiles)
        prefix = f"{label}-depth-{depth}"
        outputs[f"{prefix}.request.json"] = encoded(request)
        outputs[f"{prefix}.receipt.json"] = encoded(result)
        functional = result["scenarios"][0]["targets"][0]["task_receipt"]["functionals"][0]
        expected = 1 / (task["prior_precision"][0][0] + depth / v)
        if not math.isclose(functional["posterior_variance"], expected, rel_tol=1e-12):
            raise AssertionError("Actual API differs from independent scalar posterior formula")
        rows.append(
            {
                "case": prefix,
                "design_id": design_id,
                "profile_id": selected["profile_id"],
                "source_schedule_multiplier": depth,
                "attainment": result["attainment"],
                "posterior_variance_microvolt2": functional["posterior_variance"],
                "likelihood_variance_microvolt2": v / depth if depth else None,
                "variance_limit_microvolt2": functional["variance_limit"],
                "prior_only_precision_attainment": functional["prior_only_precision_attainment"],
            }
        )
    summary = {
        "contract": "anibench.synthetic-erp-suite-replay.v1",
        "source_bindings": source_bindings,
        "cases": rows,
        "license": "CC-BY-SA-4.0",
        "attribution": ATTRIBUTION,
        "biological_calibration": False,
        "full_AB1_or_AB2": False,
        "limitations": [
            "Mean source measurement error is not each-person precision calibration.",
            "Source-schedule multiplier is not a literal trial count.",
            "Inverse-depth scaling and homogeneous Gaussian likelihood are assumed.",
            "No persistent-person, population transport, cortical causal or treatment-benefit claim.",
        ],
    }
    outputs["results.json"] = encoded(summary)
    lines = [
        "# Hypothetical ERP profile replay",
        "",
        ATTRIBUTION,
        "",
        "Illustrative resolution only; not AB1/AB2. Mean source error and inverse-depth scaling do not certify each person.",
        "",
        "| Case | Attainment | Likelihood variance (microvolt²) |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {r['case']} | {r['attainment']} | {r['likelihood_variance_microvolt2']} |" for r in rows
    )
    outputs["RESULTS.md"] = ("\n".join(lines) + "\n").encode()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for name, raw in outputs.items():
        with (out / name).open("xb") as stream:
            stream.write(raw)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    args = parser.parse_args()
    result = replay(
        args.out,
        aggregate=args.aggregate,
        profile=args.profile,
        source_manifest=args.source_manifest,
    )
    print(json.dumps({"cases": len(result["cases"]), "biological_calibration": False}))


if __name__ == "__main__":
    main()
