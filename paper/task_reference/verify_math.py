# SPDX-License-Identifier: Apache-2.0
"""Replay synthetic mathematical witnesses using installed AniBench.

These checks concern conditional reference geometry and numerical behavior,
not biological calibration or whole-study rankings. Run with
``python verify_math.py --out NEW_RECEIPT.json`` after installing AniBench.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

import anibench
from anibench.benchmark_v1 import evaluate_benchmark
from anibench.finite_suites_v1 import suite_sha256
from anibench.information_v2 import functional_likelihood_precision
from anibench.reference_planner import _engine


def require(condition: bool, message: str) -> None:
    """Keep verification active even when Python assertions are disabled."""
    if not condition:
        raise ValueError(message)


def verify() -> dict:
    engine, profiles, metadata = _engine()
    matches = [
        value for value in profiles.values()
        if value["profile_id"] == "native-broad-reference-candidate-AB1-v0.4-tolerance1.0"
    ]
    require(len(matches) == 1, "Expected the reviewed AB1 v0.4 reference profile")
    profile = matches[0]
    score = engine["score_profile"](profile, "domain_budget", metadata)
    trusted_scores = {suite_sha256(score): score}
    baseline = copy.deepcopy(engine["DESIGNS"][0])
    designs = {
        "baseline": baseline,
        "depth_only": dict(baseline, depth=1024),
        "tiny_extreme": copy.deepcopy(engine["DESIGNS"][2]),
        "missing_neural": dict(baseline, absent_domain="neural_observation"),
        "unknown_neural": dict(baseline, unknown_domain="neural_observation"),
        "fully_correlated_4": dict(
            baseline, repeat_rho=1.0, technical_repeats_per_endpoint=4
        ),
        "fully_correlated_1000": dict(
            baseline, repeat_rho=1.0, technical_repeats_per_endpoint=1000
        ),
    }
    requests, results = {}, {}
    for name, design in designs.items():
        request = engine["request"](profile, score, metadata, design)
        result = evaluate_benchmark(
            request, trusted_profiles=profiles, trusted_score_profiles=trusted_scores
        )
        requests[name] = request
        results[name] = {
            "attainment": result["level_attainment"],
            "envelope": result["envelope"],
            "receipt_sha256": result["receipt_sha256"],
        }

    def category(name: str, category_id: str) -> dict:
        return next(
            row for row in results[name]["envelope"][1]["categories"]
            if row["category_id"] == category_id
        )

    require(
        results["fully_correlated_4"]["envelope"]
        == results["fully_correlated_1000"]["envelope"],
        "Fully correlated repeat counts changed the result",
    )
    missing = category("missing_neural", "neural_observation")
    unknown = category("unknown_neural", "neural_observation")
    require(missing["upper_percent"] == 0, "Known absence gained task support")
    require(
        unknown["lower_percent"] == 0 and unknown["upper_percent"] > 0,
        "Unresolved support was not retained as an interval",
    )
    require(
        results["tiny_extreme"]["attainment"] != "attained",
        "Extreme depth incorrectly conferred full level attainment",
    )

    duplicate = copy.deepcopy(requests["baseline"])
    targets = duplicate["suite_request"]["scenarios"][0]["targets"]
    targets.append(copy.deepcopy(targets[0]))
    try:
        evaluate_benchmark(
            duplicate, trusted_profiles=profiles, trusted_score_profiles=trusted_scores
        )
    except ValueError:
        duplicate_rejected = True
    else:
        duplicate_rejected = False
    require(duplicate_rejected, "Duplicate canonical target accepted")

    oracles = []
    for name in ("baseline", "depth_only"):
        design = designs[name]
        n, depth = design["N"], design["depth"]
        repeats = design["technical_repeats_per_endpoint"]
        effective_repeats = repeats / (1 + (repeats - 1) * design["repeat_rho"])
        for row in requests[name]["suite_request"]["scenarios"][0]["targets"]:
            task = metadata[row["canonical_id"]]
            question = task["question"]
            anchor = np.asarray(task["physical_scale_SE"])
            information = np.asarray(row["request"]["geometry"]["information_matrix"])
            variance = np.diag(np.linalg.inv(information))
            expected = {
                "current_state": 4 / depth,
                "population_mean": 80 / n,
                "controlled_contrast": 4 * (40 + 80 / depth) / n,
            }.get(question)
            if question == "longitudinal_change":
                half = len(variance) // 2
                expected = np.asarray(
                    [160 / (depth * effective_repeats)] * half
                    + [(40 + 160 / (depth * effective_repeats)) / (n - 1)] * half
                )
            if expected is not None:
                require(
                    np.allclose(variance, anchor**2 * expected, rtol=1e-12, atol=0),
                    f"Analytic covariance mismatch: {name}/{row['canonical_id']}",
                )
                oracles.append({
                    "case": name, "canonical_id": row["canonical_id"],
                    "question": question, "coordinate_count": len(variance),
                    "passed": True,
                })
    require(len(oracles) == 36, "Expected 36 independent covariance formula checks")

    prior_only = functional_likelihood_precision([[0]], [[1e15]], [1])
    require(prior_only["identified"] is False, "Prior-only acquisition was accepted")
    scales = [1e-6, 1, 1e6]
    for scale in scales:
        diagnostic = functional_likelihood_precision(
            [[2 / scale**2]], [[0.001 / scale**2]], [1]
        )
        require(
            abs(diagnostic["variance"] / scale**2 - 0.5) < 1e-12,
            "Native-unit scaling changed likelihood precision",
        )

    # Positive-semidefinite information addition cannot worsen exact precision.
    # This ill-conditioned case documents the conservative numerical exception:
    # the unchanged second direction has exact variance 1, but the rank cutoff
    # makes its computed identification unknown after the first direction grows.
    identity = [[1, 0], [0, 1]]
    enlarged = [[1e20, 0], [0, 1]]
    initial = functional_likelihood_precision(identity, identity, [0, 1])
    final = functional_likelihood_precision(enlarged, identity, [0, 1])
    require(initial["identified"] is True and initial["variance"] == 1, "Initial witness failed")
    require(
        final["identified"] is None and final["variance"] is None
        and final["numerically_ambiguous"] is True,
        "Expected numerical-monotonicity limitation was not reproduced",
    )

    installed_root = Path(anibench.__file__).resolve().parent
    filenames = [
        "benchmark_v1.py", "summary_geometry_v1.py", "reference_planner.py",
        "finite_tasks_v1.py", "finite_suites_v1.py", "information_v2.py",
        "workbench_assets/reference/v0.4/replay.py",
        "workbench_assets/reference/WORKLOAD_CANDIDATE.json",
        "workbench_assets/paper.md",
    ]
    return {
        "schema": "anibench.paper-math-reproduction.v1",
        "scope": "Finite synthetic witnesses and analytic covariance checks; not biological validation or full release acceptance.",
        "checks": {
            "correlated_repeats_invariant": True,
            "missing_vs_unknown_preserved": True,
            "tiny_extreme_no_level_pass": True,
            "duplicate_canonical_rejected": True,
            "strong_prior_without_data_no_acquisition": True,
            "native_unit_scaling": scales,
        },
        "analytic_oracles": oracles,
        "results": results,
        "numerical_monotonicity_witness": {
            "prior_precision": identity, "coefficients": [0, 1],
            "initial_information": identity, "enlarged_information": enlarged,
            "exact_likelihood_variance_both": 1,
            "initial_diagnostic": initial, "enlarged_diagnostic": final,
            "interpretation": "Exact precision remains unchanged; conservative numerical identification becomes unknown. Software attainment is not globally monotone at numerical rank boundaries.",
        },
        "installed_source_sha256": {
            name: hashlib.sha256((installed_root / name).read_bytes()).hexdigest()
            for name in filenames
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New JSON receipt path")
    args = parser.parse_args()
    require(not args.out.exists(), "Output exists; choose a new JSON path")
    receipt = verify()
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print("Verified seven designs, 36 covariance checks and the numerical-limit witness.")


if __name__ == "__main__":
    main()
