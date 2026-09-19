# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Actual finite-task API replay of synthetic depth/population tradeoffs.

Run with AniBench on PYTHONPATH or installed; outputs contain no private paths.
Separate scalar estimands deliberately make no claim about their joint covariance.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

from anibench.finite_tasks_v1 import evaluate_finite_task, finite_task_sha256


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    designs = [
        {"id": "two_people_extreme_depth", "N": 2, "m": 1000000, "cost_usd": 100000000},
        {"id": "large_complete_shallow", "N": 2000, "m": 1, "cost_usd": None},
        {"id": "large_missing_neural", "N": 200000, "m": 1, "cost_usd": None},
        {"id": "two_people_much_higher_cost", "N": 2, "m": 1000000, "cost_usd": 10000000000},
        {"id": "balanced_complete", "N": 2000, "m": 2000, "cost_usd": None},
    ]
    models = {
        "person_state": {
            "estimand": "one sampled person's scalar state, separate inference problem",
            "observation": "m independent readings given that scalar state",
            "likelihood_information_formula": "m / R",
            "R": 4.0,
            "prior_precision": 1e-6,
        },
        "population_mean": {
            "estimand": "mean of a synthetic population, separate inference problem",
            "observation": "N independent donor means with known variance B + R/m",
            "likelihood_information_formula": "N / (B + R/m)",
            "B": 1.0,
            "R": 4.0,
            "prior_precision": 1e-6,
        },
    }
    provenance = {
        "contract": "anibench.synthetic-depth-population-provenance.v1",
        "license": "CC-BY-4.0",
        "copyright": "2026 ANI",
        "source_kind": "invented_models_no_real_study_or_calibration",
        "models": models,
        "designs": designs,
        "toy_halfwidth": 0.1,
        "nominal_normal_coverage": 0.95,
        "warning": "Known variances and normal likelihoods; no AB1/AB2 biological thresholds.",
        "joint_inference": "None. Scalar task results are not pooled as independent blocks.",
        "role_gate_test": "Synthetic neural required-support declarations test interface logic, not calibrated neural operators.",
    }
    source = out / "synthetic-provenance.json"
    source.write_text(json.dumps(provenance, indent=2) + "\n")
    source_hash = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    z = NormalDist().inv_cdf(0.975)
    variance_limit = (provenance["toy_halfwidth"] / z) ** 2
    runs = []
    assertions = 0
    for design in designs:
        for task_name, model in models.items():
            information = (
                design["m"] / model["R"]
                if task_name == "person_state"
                else design["N"] / (model["B"] + model["R"] / design["m"])
            )
            task = {
                "contract": "anibench.finite-task-definition.v1",
                "task_id": "synthetic-depth-" + task_name,
                "task_version": "1",
                "source_sha256": source_hash,
                "model_sha256": digest(model),
                "target_population": "Invented normal population; no real participant records",
                "estimand": model["estimand"],
                "horizon": "one frozen synthetic state block",
                "claim_lane": "conditional_design",
                "comparison_scope": "finite_functionals_only",
                "parameter_units": ["toy unit"],
                "prior_precision": [[model["prior_precision"]]],
                "required_support": [{"domain_id": "synthetic_measurement", "role": "observation"}],
                "functionals": [
                    {
                        "functional_id": task_name,
                        "coefficients": [1.0],
                        "unit": "toy unit",
                        "variance_limit": variance_limit,
                    }
                ],
            }
            request = {
                "contract": "anibench.finite-task-request.v1",
                "task": task,
                "task_sha256": finite_task_sha256(task),
                "evidence": {
                    "identifiability": True,
                    "collection_verified": None,
                    "support": [
                        {
                            "domain_id": "synthetic_measurement",
                            "role": "observation",
                            "supported": True,
                        }
                    ],
                },
                "geometry": {"model_sha256": digest(model), "information_matrix": [[information]]},
            }
            receipt = evaluate_finite_task(request)
            expected = 1.0 / (model["prior_precision"] + information)
            actual = receipt["functionals"][0]["posterior_variance"]
            assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-15)
            assert receipt["functionals"][0]["prior_only_precision_attainment"] is False
            assertions += 2
            runs.append(
                {
                    "design": design,
                    "task_name": task_name,
                    "request": request,
                    "receipt": receipt,
                    "analytic_posterior_variance": expected,
                    "analytic_likelihood_variance": 1 / information,
                }
            )
    indexed = {(r["design"]["id"], r["task_name"]): r for r in runs}
    for task_name in models:
        cheap = indexed[("two_people_extreme_depth", task_name)]
        dear = indexed[("two_people_much_higher_cost", task_name)]
        assert cheap["receipt"] == dear["receipt"]
        assertions += 1

    def variance(design, task):
        return indexed[(design, task)]["receipt"]["functionals"][0]["posterior_variance"]

    assert variance("two_people_extreme_depth", "person_state") < variance(
        "large_complete_shallow", "person_state"
    )
    assert variance("two_people_extreme_depth", "population_mean") > variance(
        "large_complete_shallow", "population_mean"
    )
    assertions += 2
    assert (
        indexed[("two_people_extreme_depth", "person_state")]["receipt"]["attainment"] == "attained"
    )
    assert (
        indexed[("two_people_extreme_depth", "population_mean")]["receipt"]["attainment"]
        == "not_attained"
    )
    assert (
        indexed[("large_complete_shallow", "person_state")]["receipt"]["attainment"]
        == "not_attained"
    )
    assert (
        indexed[("large_complete_shallow", "population_mean")]["receipt"]["attainment"]
        == "attained"
    )
    assertions += 4
    # A separately named support-gate task: no invented joint covariance.
    gate_request = copy.deepcopy(indexed[("large_missing_neural", "population_mean")]["request"])
    gate_request["task"]["task_id"] = "synthetic-population-with-required-neural-support"
    gate_request["task"]["required_support"].append(
        {"domain_id": "synthetic_neural", "role": "observation"}
    )
    gate_request["task_sha256"] = finite_task_sha256(gate_request["task"])
    gates = []
    for declared, expected in [(False, "not_attained"), (None, "unknown"), (True, "attained")]:
        request = copy.deepcopy(gate_request)
        request["evidence"]["support"].append(
            {"domain_id": "synthetic_neural", "role": "observation", "supported": declared}
        )
        receipt = evaluate_finite_task(request)
        assert receipt["attainment"] == expected
        assert receipt["functionals"][0]["state"] == "attained"
        assertions += 2
        gates.append({"declared_neural_support": declared, "request": request, "receipt": receipt})
    output = {
        "contract": "anibench.synthetic-depth-population-actual-api.v1",
        "status": "executed_actual_api_not_biological_calibration",
        "source_sha256": source_hash,
        "script_sha256": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_hashes": {name: digest(model) for name, model in models.items()},
        "scalar_task_runs": runs,
        "neural_role_gate_runs": gates,
        "assertions_passed": assertions,
        "no_joint_block_assumption": True,
        "cost_treatment": "metadata only; equal acquisitions produce byte-identical API receipts",
        "comparison_scope": "Separate scalar-task precision orderings; no overall ranking",
    }
    (out / "actual-api-receipts.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "scalar_task_runs": len(runs),
                "role_gate_runs": len(gates),
                "assertions_passed": assertions,
                "all_analytic_variances_match": True,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/depth-population-audit"))
    run(parser.parse_args().out)
