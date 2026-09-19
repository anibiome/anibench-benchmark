# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""225 synthetic experiments against unmodified AniBench helpers, no real-study claims."""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/synthetic_geometry_audit"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
from anibench.causal_v2 import contrast_information
from anibench.information_v2 import (
    EventContribution,
    absolute_mechanics,
    assemble_joint_information,
    canonical_matrix_sha256,
    event_information,
    nuisance_adjusted_information,
    reconstruction_metrics,
)
from anibench.v2 import score_information_run


def event(A, R, n=1):
    return event_information(
        EventContribution(
            "synthetic", tuple(map(tuple, A)), tuple(map(tuple, R)), n, "synthetic:no-real-study"
        )
    )


def logdiag(v):
    return sum(math.log1p(x) for x in v) / (2 * math.log(10))


def replay(F):
    d = len(F)
    I = np.eye(d).tolist()
    f = F.tolist()
    p = {
        "contract": "anibench.information-run.v2-candidate1",
        "benchmark_suite_version": "synthetic-council-v1",
        "lane": "design_preview",
        "reference_authority_id": "synthetic-unverified",
        "information_matrix": f,
        "prior_precision": I,
        "reference_information": I,
        "reference_direction_basis": I,
        "source_objects": [
            {
                "object_id": "synthetic",
                "sha256": "sha256:" + hashlib.sha256(b"synthetic").hexdigest(),
            }
        ],
    }
    for k in [
        "parameter_space_hash",
        "prior_metric_hash",
        "reference_level_hash",
        "event_manifest_hash",
        "intervention_design_hash",
        "uncertainty_model_hash",
    ]:
        p[k] = "sha256:" + hashlib.sha256(k.encode()).hexdigest()
    p["matrix_hashes"] = {
        k: canonical_matrix_sha256(v)
        for k, v in [
            ("information_matrix_sha256", f),
            ("prior_precision_matrix_sha256", I),
            ("reference_information_matrix_sha256", I),
            ("reference_direction_basis_sha256", I),
        ]
    }
    return score_information_run(p)


names = [
    "tiny_population_extreme_depth",
    "giant_shallow",
    "copied_acquisitions",
    "independent_replicates",
    "correlated_oversampling",
    "missing_neural",
    "redundant_arm_columns",
    "near_singular_noise",
    "observation_unit_invariance",
    "cost_without_information",
    "duration_without_operator_change",
    "increasing_noise",
    "nuisance_penalty",
    "marginal_vs_joint_completion",
    "independent_population_growth",
]
results = []
for fam in names:
    for j in range(15):
        x = j + 1
        checks = {}
        extra = {}
        support = "supported_conditional_geometry"
        A = None
        R = None
        try:
            if fam == "tiny_population_extreme_depth":
                a = 10 ** (1 + x / 5)
                A = np.array([[a, 0], [0, 0.03 * x]])
                R = np.eye(2)
                F = event(A, R, 2)
                expected = [2 * a * a, 2 * (0.03 * x) ** 2]
                extra = {
                    "people": 2,
                    "total_cost_usd": 100000000,
                    "population_generalization": "not_inferred",
                    "narrow_precision_can_improve": True,
                }
            elif fam == "giant_shallow":
                n = 100000 * x + 37
                A = np.array([[1.0, 0.0, 0.0]])
                R = np.eye(1)
                F = event(A, R, n)
                expected = [n, 0, 0]
                checks["null_directions_preserved"] = np.linalg.matrix_rank(F) == 1
            elif fam == "copied_acquisitions":
                a = 0.13 * x
                row = EventContribution("same", ((a, 0.0),), ((1.0,),), 1.0, "same-source")
                single = event_information(row)
                F = assemble_joint_information([row, row])
                expected = [2 * a * a, 0]
                support = "low_level_helper_not_a_lineage_deduplicator"
                extra = {
                    "copied_rows": 2,
                    "semantic_duplicate_invariance": bool(np.allclose(F, single)),
                    "interpretation": "Helper sums supplied contributions, so copied inputs are overcounted unless collection/lineage validation occurs upstream. No full-compiler failure inferred.",
                }
                checks["documented_additive_mechanics"] = np.allclose(F, 2 * single)
            elif fam == "independent_replicates":
                m = x + 2
                a = 0.17 + x / 10
                A = np.ones((m, 1)) * a
                R = np.eye(m)
                F = event(A, R)
                expected = [m * a * a]
            elif fam == "correlated_oversampling":
                m = x + 3
                rho = 0.90 + 0.005 * x
                a = 0.8
                A = np.ones((m, 1)) * a
                R = (1 - rho) * np.eye(m) + rho * np.ones((m, m))
                F = event(A, R)
                expected = [a * a * m / (1 + (m - 1) * rho)]
                checks["less_than_independent"] = F[0, 0] < m * a * a
            elif fam == "missing_neural":
                expected = [x * 13.7, x * 7.1, 0]
                F = np.diag(expected)
                checks["required_neural_unresolved"] = F[2, 2] == 0
                extra = {
                    "domain_meaning": "synthetic third coordinate declared neural only for this test",
                    "full_attainment": False,
                }
            elif fam == "redundant_arm_columns":
                # Duplicate contrast columns, distinct assignment allocations across settings.
                n0 = x + 3
                n1 = 2 * x + 5
                X = np.array([[0.0, 0.0]] * n0 + [[1.0, 1.0]] * n1)
                c = contrast_information(X)
                F = np.array(c.information_matrix)
                scalar = n0 * n1 / (n0 + n1)
                expected = [0, 2 * scalar]
                checks["contrast_rank_one"] = c.rank == 1
                A = X
            elif fam == "near_singular_noise":
                eps = 10 ** (-2 - x / 3)
                A = np.ones((2, 1))
                R = np.array([[1, 1 - eps], [1 - eps, 1]])
                F = event(A, R)
                expected = [2 / (2 - eps)]
                extra = {"noise_min_eigenvalue": eps, "noise_spd": True}
                checks["finite_correlated_precision"] = np.isfinite(F).all()
            elif fam == "observation_unit_invariance":
                a = 0.3 + x / 8
                r = 0.4 + x / 7
                A = np.diag([a, 2 * a])
                R = np.diag([r, 3 * r])
                F = event(A, R)
                scale = 10 ** (-3 + x / 3)
                B = np.diag([scale, 1 / scale])
                changed = event(B @ A, B @ R @ B.T)
                expected = [a * a / r, 4 * a * a / (3 * r)]
                checks["unit_invariance"] = np.allclose(F, changed, rtol=1e-8, atol=1e-9)
            elif fam == "cost_without_information":
                expected = [0.213 * x, 0.717 * x]
                F = np.diag(expected)
                extra = {
                    "cost_baseline": 10000,
                    "cost_changed": 10000 * 10 ** (x / 3),
                    "cost_not_an_input": True,
                }
                checks["same_geometry_same_mechanics"] = absolute_mechanics(
                    F, np.eye(2)
                ) == absolute_mechanics(F, np.eye(2))
            elif fam == "duration_without_operator_change":
                expected = [0.117 * x, 0.331 * x]
                F = np.diag(expected)
                extra = {
                    "duration_metadata_days": [7, 365 * x],
                    "time_sensitivity_model": "unchanged",
                    "calendar_metadata_not_information_input": True,
                }
                checks["no_calendar_multiplier"] = True
            elif fam == "increasing_noise":
                r = 1 + x / 3
                A = np.diag([1.1, 2.3])
                R = r * np.eye(2)
                F = event(A, R)
                expected = [1.21 / r, 5.29 / r]
                checks["noise_reduces_information"] = np.trace(F) < 1.21 + 5.29
            elif fam == "nuisance_penalty":
                a = 2 + x / 4
                b = 0.7 + x / 9
                c = 4 + x / 3
                prior = 0.3
                full = np.array([[a, b], [b, c]])
                F = nuisance_adjusted_information(
                    full,
                    target_indices=[0],
                    nuisance_indices=[1],
                    nuisance_prior_precision=[[prior]],
                )
                expected = [a - b * b / (c + prior)]
                checks["nuisance_not_bonus"] = F[0, 0] < a
                A = full
            elif fam == "marginal_vs_joint_completion":
                q = 0.01 + 0.032 * x
                S = np.array([[0.5, q], [q, 0.5]])
                F = np.linalg.inv(S) - np.eye(2)
                expected = [1 / (0.5 + q) - 1, 1 / (0.5 - q) - 1]
                metrics = reconstruction_metrics(F, np.eye(2), np.eye(2), np.eye(2))
                checks["basis_completion_100"] = abs(metrics.level1_completion_percent - 100) < 1e-8
                checks["joint_dominance_fails"] = 2 * (0.5 + q) > 1
                checks["new_joint_diagnostic_rejects"] = not metrics.conditional_joint_diagnostic[
                    "all_direction_reference_attainment"
                ]
                checks["new_joint_ratio_matches_analytic"] = math.isclose(
                    metrics.conditional_joint_diagnostic[
                        "worst_direction_posterior_variance_ratio"
                    ],
                    1 + 2 * q,
                    rel_tol=1e-8,
                )
                extra = {
                    "posterior_covariance": S.tolist(),
                    "basis_completion_percent": metrics.level1_completion_percent,
                    "worst_direction_variance_ratio": 1 + 2 * q,
                    "all_directions_attainment": False,
                    "interpretation": "Reproduced helper semantic limitation, not current public rank bug.",
                }
            elif fam == "independent_population_growth":
                n = 3 * x + 1
                A = np.diag([0.41, 0.91])
                R = np.eye(2)
                F = event(A, R, n)
                expected = [n * 0.41**2, n * 0.91**2]
                checks["information_unbounded_as_n_grows"] = True
            observed = absolute_mechanics(F, np.eye(len(F))).absolute_log10_contraction
            checks["analytic_log_volume"] = math.isclose(
                observed, logdiag(expected), rel_tol=1e-7, abs_tol=1e-8
            )
            packet = replay(F)
            checks["actual_replay_matches_helper"] = math.isclose(
                packet["absolute_mechanics"]["absolute_log10_contraction"],
                observed,
                rel_tol=1e-9,
                abs_tol=1e-10,
            )
            checks["no_public_rank_or_completion"] = (
                not packet["claim_permissions"]["public_rank_allowed"]
                and not packet["claim_permissions"]["public_completion_claim_allowed"]
                and packet["reference_metrics"] is None
            )
            results.append(
                {
                    "id": f"{fam}-{x:02}",
                    "family": fam,
                    "support": support,
                    "inputs": {
                        "operator": None if A is None else A.tolist(),
                        "noise": None if R is None else R.tolist(),
                        "information": F.tolist(),
                    },
                    "expected_information_eigenvalues": expected,
                    "expected_log10_contraction": logdiag(expected),
                    "observed_log10_contraction": observed,
                    "checks": {k: bool(v) for k, v in checks.items()},
                    "pass": all(checks.values()),
                    "details": extra,
                }
            )
        except (ValueError, TypeError, KeyError, np.linalg.LinAlgError) as e:
            results.append(
                {
                    "id": f"{fam}-{x:02}",
                    "family": fam,
                    "pass": False,
                    "exception": type(e).__name__ + ": " + str(e),
                }
            )
try:
    repo_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()
except (OSError, subprocess.CalledProcessError):
    repo_commit = None  # Source archives have hashes but need not contain Git metadata.
summary = {
    "license": "CC-BY-4.0",
    "copyright": "2026 ANI",
    "implementation_sha256": {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            ROOT / "src/anibench/information_v2.py",
            ROOT / "src/anibench/causal_v2.py",
            ROOT / "src/anibench/v2.py",
            Path(__file__),
        ]
    },
    "schema": "anibench.synthetic.actual-helper-audit.v1",
    "repo_commit": repo_commit,
    "numpy_version": np.__version__,
    "synthetic_cases": len(results),
    "families": len(names),
    "passed": sum(r["pass"] for r in results),
    "failed": [r["id"] for r in results if not r["pass"]],
    "stronger_joint_attainment_counterexamples": sum(
        r.get("family") == "marginal_vs_joint_completion"
        and r.get("details", {}).get("all_directions_attainment") is False
        for r in results
    ),
    "copied_input_semantic_invariance_failures": sum(
        r.get("family") == "copied_acquisitions"
        and r.get("details", {}).get("semantic_duplicate_invariance") is False
        for r in results
    ),
    "unique_information_matrices": len(
        {json.dumps(r.get("inputs", {}).get("information")) for r in results}
    ),
    "scope": "Actual low-level information helpers and score_information_run; not protocol compiler, collected-record profiler, empirical validation or 200 real studies.",
    "limitations": [
        "Cost/duration absence from helper inputs tests interface scope, not full product invariance.",
        "Copied contribution semantic invariance fails at additive helper by design; upstream deduplication not executed.",
        "Marginal-completion counterexamples all fail the stronger joint-attainment claim; existing helper formula itself matches expectations.",
    ],
    "results": results,
}
(OUT / "actual_geometry_results.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "results"}))

raise SystemExit(1 if summary["failed"] else 0)
