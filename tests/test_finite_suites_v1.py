# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

from anibench.finite_suites_v1 import (
    FiniteSuiteError,
    evaluate_finite_suite,
    scientific_frame_sha256,
    suite_sha256,
)
from anibench.finite_tasks_v1 import finite_task_sha256
from anibench.information_v2 import InformationV2Error, functional_likelihood_precision


def task(identity="neural", prior=1):
    return {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": identity,
        "task_version": "1",
        "source_sha256": "sha256:" + "a" * 64,
        "model_sha256": "sha256:" + "b" * 64,
        "target_population": "synthetic",
        "estimand": identity,
        "horizon": "one occasion",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["u"],
        "prior_precision": [[prior]],
        "required_support": [{"domain_id": identity, "role": "observation"}],
        "functionals": [
            {"functional_id": "value", "coefficients": [1], "unit": "u", "variance_limit": 0.5}
        ],
    }


def profile(*tasks, quantifier="single_conditional"):
    return {
        "contract": "anibench.finite-suite-profile.v1",
        "profile_id": "test",
        "profile_type": "custom",
        "scope": "synthetic finite observables",
        "tolerance_authority": "test convention",
        "calibration_authority": "synthetic",
        "precision_basis": "likelihood_only",
        "scenario_quantifier": quantifier,
        "scenario_ids": ["a"] if quantifier == "single_conditional" else ["a", "b"],
        "parent_sha256": None,
        "targets": [
            {"canonical_id": t["task_id"], "frame_sha256": scientific_frame_sha256(t), "task": t}
            for t in tasks
        ],
    }


def evaluation(t, information=4, supported=True):
    return {
        "contract": "anibench.finite-task-request.v1",
        "task": t,
        "task_sha256": finite_task_sha256(t),
        "evidence": {
            "identifiability": True,
            "collection_verified": None,
            "support": [dict(r, supported=supported) for r in t["required_support"]],
        },
        "geometry": {"model_sha256": t["model_sha256"], "information_matrix": [[information]]},
    }


BINDING = {"design_id": "synthetic-design", "design_source_sha256": "sha256:" + "d" * 64}


def request(p, amounts=None):
    return {
        **BINDING,
        "contract": "anibench.finite-suite-request.v1",
        "profile_sha256": suite_sha256(p),
        "scenarios": [
            {
                **BINDING,
                "scenario_id": s,
                "targets": [
                    {
                        "canonical_id": t["canonical_id"],
                        **BINDING,
                        "known_absent": False,
                        "request": evaluation(
                            t["task"], (amounts or {}).get((s, t["canonical_id"]), 4)
                        ),
                    }
                    for t in p["targets"]
                ],
            }
            for s in p["scenario_ids"]
        ],
    }


def run(p, r=None, registry=None):
    return evaluate_finite_suite(r or request(p), trusted_profiles=registry or {suite_sha256(p): p})


class LikelihoodTests(unittest.TestCase):
    def test_range_not_pseudoinverse_zero(self):
        self.assertEqual(
            functional_likelihood_precision([[100, 0], [0, 0]], np.eye(2), [1, 0])["variance"], 0.01
        )
        for c in ([0, 1], [1, 1]):
            d = functional_likelihood_precision([[100, 0], [0, 0]], np.eye(2), c)
            self.assertFalse(d["identified"])
            self.assertIsNone(d["variance"])

    def test_tiny_null_component_and_rotated_adversary(self):
        j = np.diag([100.0, 0.0])
        for epsilon in [1e-11, 1e-100, 1e-300]:
            self.assertIs(
                functional_likelihood_precision(j, np.eye(2), [1, epsilon])["identified"], False
            )
        transform = np.array([[1.0, 2.0], [0.5, 3.0]])
        inverse = np.linalg.inv(transform)
        transformed_j = inverse.T @ j @ inverse
        transformed_p = inverse.T @ inverse
        for c in [np.array([1.0, 1e-11]), np.array([1.0, 1.0]), np.array([1.0, 0.0])]:
            result = functional_likelihood_precision(transformed_j, transformed_p, inverse.T @ c)
            self.assertIsNot(result["identified"], True)
            self.assertIsNone(result["variance"])

    def test_ill_conditioned_prior_cannot_invent_rank(self):
        j = np.ones((2, 2))
        p = j + 1e-14 * np.eye(2)
        result = functional_likelihood_precision(j, p, [1, -1])
        self.assertIsNone(result["identified"])
        self.assertIsNone(result["variance"])
        self.assertEqual(result["raw_information_rank"], 1)
        for a in range(1, 5):
            for b in range(1, 5):
                u = np.array([float(a), float(b)])
                j = np.outer(u, u)  # Exact integer rank-one matrix.
                for exponent in [2, 4, 6, 8, 10, 12]:
                    try:
                        result = functional_likelihood_precision(
                            j, j + 10.0 ** (-exponent) * np.eye(2), [float(b), -float(a)]
                        )
                    except InformationV2Error:
                        # Existing whitening validation may reject amplified
                        # roundoff as materially non-PSD; never turn it into a pass.
                        continue
                    self.assertIsNot(result["identified"], True)
                    self.assertIsNone(result["variance"])
        for epsilon in [-1e-12, 1e-12]:
            result = functional_likelihood_precision(np.diag([100.0, epsilon]), np.eye(2), [0, 1])
            self.assertIsNone(result["identified"])
            self.assertIsNone(result["variance"])

    def test_full_rank_independent_solve_oracle(self):
        rng = np.random.default_rng(931)
        for _ in range(20):
            a = rng.normal(size=(4, 4))
            b = rng.normal(size=(4, 4))
            j = a.T @ a + np.eye(4)
            p = b.T @ b + 0.5 * np.eye(4)
            c = rng.normal(size=4)
            expected = float(c @ np.linalg.solve(j, c))
            actual = functional_likelihood_precision(j, p, c)
            self.assertIs(actual["identified"], True)
            self.assertAlmostEqual(actual["variance"], expected, places=11)
        for c in [[1e-200], [1e200]]:
            with self.assertRaises(InformationV2Error):
                functional_likelihood_precision([[1]], [[1]], c)

    def test_coordinate_and_unit_invariance_nonidentity_prior(self):
        p = np.array([[3.0, 0.4], [0.4, 2.0]])
        j = np.array([[8.0, 1.0], [1.0, 4.0]])
        c = np.array([1.0, -2.0])
        a = np.array([[1000.0, 200.0], [0.0, 0.1]])
        inverse = np.linalg.inv(a)
        original = functional_likelihood_precision(j, p, c)["variance"]
        changed = functional_likelihood_precision(
            inverse.T @ j @ inverse, inverse.T @ p @ inverse, inverse.T @ c
        )["variance"]
        self.assertAlmostEqual(original, changed, places=9)
        self.assertLess(functional_likelihood_precision(j + np.eye(2), p, c)["variance"], original)

    def test_invalid_and_ambiguous(self):
        for j, p, c in [
            ([[True]], [[1]], [1]),
            ([[-1]], [[1]], [1]),
            ([[1]], [[0]], [1]),
            ([[1]], [[1]], [0]),
            ([[float("nan")]], [[1]], [1]),
        ]:
            with self.assertRaises((ValueError, InformationV2Error)):
                functional_likelihood_precision(j, p, c)
        self.assertIsNone(
            functional_likelihood_precision(np.diag([1.0, 1e-12]), np.eye(2), [0, 1])["identified"]
        )


class SuiteTests(unittest.TestCase):
    def test_prior_only_does_not_pass_data(self):
        p = profile(task(prior=100))
        r = request(p, {("a", "neural"): 0})
        result = run(p, r)
        self.assertEqual(result["attainment"], "not_attained")
        self.assertEqual(
            result["scenarios"][0]["targets"][0]["task_receipt"]["attainment"], "attained"
        )
        r["scenarios"][0]["targets"][0]["request"]["geometry"] = None
        self.assertEqual(run(p, r)["attainment"], "unknown")

    def test_absent_unknown_and_lane(self):
        p = profile(task())
        r = request(p)
        r["scenarios"][0]["targets"] = []
        self.assertEqual(run(p, r)["attainment"], "unknown")
        r["scenarios"][0]["targets"] = [
            {**BINDING, "canonical_id": "neural", "known_absent": True, "request": None}
        ]
        self.assertEqual(run(p, r)["attainment"], "not_attained")
        self.assertEqual(run(p)["attainment"], "attained")
        t = task()
        t["claim_lane"] = "realized_record"
        self.assertEqual(run(profile(t))["attainment"], "unknown")

    def test_neural_and_perturbation_roles(self):
        p = profile(task("molecular"), task("neural"))
        r = request(p, {("a", "molecular"): 1e9})
        neural = r["scenarios"][0]["targets"][1]["request"]
        neural["evidence"]["support"][0]["supported"] = False
        self.assertEqual(run(p, r)["attainment"], "not_attained")
        neural["evidence"]["support"][0]["supported"] = None
        self.assertEqual(run(p, r)["attainment"], "unknown")
        t = task()
        t["required_support"].append({"domain_id": "cortical_assignment", "role": "perturbation"})
        p = profile(t)
        r = request(p)
        r["scenarios"][0]["targets"][0]["request"]["evidence"]["support"].pop()
        self.assertEqual(run(p, r)["attainment"], "unknown")

    def test_same_scenario_quantifiers(self):
        p = profile(task("molecular"), task("neural"), quantifier="exists_declared_scenario")
        r = request(
            p,
            {
                ("a", "molecular"): 100,
                ("a", "neural"): 0.1,
                ("b", "molecular"): 0.1,
                ("b", "neural"): 100,
            },
        )
        self.assertEqual(run(p, r)["attainment"], "not_attained")
        r["scenarios"][0]["targets"][1]["request"]["geometry"]["information_matrix"] = [[100]]
        self.assertEqual(run(p, r)["attainment"], "attained")
        p["scenario_quantifier"] = "all_declared_scenarios"
        r["profile_sha256"] = suite_sha256(p)
        self.assertEqual(run(p, r)["attainment"], "not_attained")

    def test_duplicates_renaming_and_stale(self):
        p = profile(task())
        r = request(p)
        r["scenarios"][0]["targets"].append(copy.deepcopy(r["scenarios"][0]["targets"][0]))
        with self.assertRaises(FiniteSuiteError):
            run(p, r)
        duplicate = copy.deepcopy(p["targets"][0])
        duplicate["canonical_id"] = "renamed"
        duplicate["task"]["task_id"] = "renamed"
        p["targets"].append(duplicate)
        with self.assertRaises(FiniteSuiteError):
            run(p)
        t = task()
        t["functionals"].append(
            dict(t["functionals"][0], functional_id="renamed", coefficients=[-2])
        )
        with self.assertRaises(FiniteSuiteError):
            scientific_frame_sha256(t)
        p = profile(task())
        r = request(p)
        r["scenarios"][0]["targets"][0]["request"]["task"]["horizon"] = "changed"
        with self.assertRaises(ValueError):
            run(p, r)

    def test_schema_embedding_has_not_drifted(self):
        root = Path(__file__).resolve().parents[1]
        original = json.loads(
            (root / "schemas/finite_precision/v1/evaluation-input.schema.json").read_text()
        )
        suite = json.loads((root / "schemas/finite_suites/v1/input.schema.json").read_text())
        embedded = suite["properties"]["scenarios"]["items"]["properties"]["targets"]["items"][
            "properties"
        ]["request"]["anyOf"][0]
        self.assertEqual(embedded, original)
        self.assertEqual(
            suite["$defs"]["profile"]["properties"]["targets"]["items"]["properties"]["task"],
            original["properties"]["task"],
        )

    def test_design_binding_mismatch(self):
        p = profile(task())
        for location in ["scenario", "target"]:
            r = request(p)
            row = r["scenarios"][0]
            if location == "target":
                row = row["targets"][0]
            row["design_source_sha256"] = "sha256:" + "e" * 64
            with self.assertRaises(FiniteSuiteError):
                run(p, r)
        result = run(p)
        self.assertEqual(result["design_id"], BINDING["design_id"])
        self.assertEqual(
            result["scenarios"][0]["targets"][0]["design_source_sha256"],
            BINDING["design_source_sha256"],
        )

    def test_shipped_illustrative_profile(self):
        root = Path(__file__).resolve().parents[1]
        p = json.loads((root / "spec/finite_suites/v1/erp-p3b-resolution.json").read_text())
        self.assertEqual(p["profile_type"], "illustrative")
        self.assertEqual(
            p["targets"][0]["task"]["model_sha256"],
            "sha256:" + hashlib.sha256(p["calibration_authority"].encode()).hexdigest(),
        )
        source = root / "examples/calibration/erp_core/source_manifest.json"
        self.assertEqual(
            p["targets"][0]["task"]["source_sha256"],
            "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        result = run(p)
        self.assertEqual(result["attainment"], "attained")
        self.assertFalse(result["public_saturation_claim_allowed"])

    def test_parent_roles_cannot_be_removed(self):
        t = task()
        t["required_support"].append({"domain_id": "control", "role": "perturbation"})
        parent = profile(t)
        child = copy.deepcopy(parent)
        child["profile_id"] = "weakened"
        child["parent_sha256"] = suite_sha256(parent)
        child["targets"][0]["task"]["required_support"].pop()
        with self.assertRaises(FiniteSuiteError):
            run(child, registry={suite_sha256(p): p for p in [parent, child]})

    def test_monotone_parent_and_hashes(self):
        parent = profile(task())
        child = copy.deepcopy(parent)
        child["profile_id"] = "finer"
        child["parent_sha256"] = suite_sha256(parent)
        child["targets"][0]["task"]["functionals"][0]["variance_limit"] = 0.25
        registry = {suite_sha256(p): p for p in [parent, child]}
        result = run(child, registry=registry)
        self.assertEqual(result["attainment"], "attained")
        self.assertEqual(run(parent)["attainment"], "attained")
        self.assertIn("finite_suites/finite_suites_v1.py", result["implementation"]["sha256"])
        child["targets"][0]["task"]["functionals"][0]["variance_limit"] = 1
        with self.assertRaises(FiniteSuiteError):
            run(child, registry={suite_sha256(p): p for p in [parent, child]})
        p = profile(task())
        r = request(p)
        r["extra"] = 1
        with self.assertRaises(FiniteSuiteError):
            run(p, r)


if __name__ == "__main__":
    unittest.main()
