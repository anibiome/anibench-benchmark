# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from examples.calibration.erp_core.plan_design import evaluate_design, load_json, plan

PACKAGE = Path(__file__).resolve().parents[1] / "examples/calibration/erp_core"


def request(limits=None):
    return {
        "schema_version": "anibench.erp-design-request.v1",
        "target_status": "illustrative",
        "target_rationale": "Invented arithmetic test; no biological cutoff",
        "variance_limits_uV2": limits
        or {
            "current_session": 1,
            "persistent_person": 1,
            "population_mean": 1.25,
        },
        "grid": {"N": [2, 10, 40], "k": [1, 4, 12], "d": [1, 4, 16]},
    }


class PlannerTests(unittest.TestCase):
    def test_separately_possible_is_not_jointly_possible(self):
        r = evaluate_design(8, 1, 2, 4, 1, request()["variance_limits_uV2"])
        self.assertEqual(r["status"], "infeasible")
        self.assertIsNone(r["admissible_S_uV2"])
        self.assertTrue(r["all_tasks_individually_possible_but_jointly_infeasible"])
        self.assertEqual(
            r["individual_checks"]["persistent_person"]["admissible_S_uV2"]["upper_exact"], "3"
        )
        self.assertEqual(
            r["individual_checks"]["population_mean"]["admissible_S_uV2"]["lower_exact"], "23/3"
        )

    def test_closed_boundary_and_nearby_empty_interval_not_merged(self):
        limits = {"current_session": 1, "persistent_person": 1, "population_mean": 3}
        r = evaluate_design(8, 1, 2, 4, 1, limits)
        self.assertEqual(r["status"], "assumption_sensitive")
        self.assertEqual(r["admissible_S_uV2"], {"lower_exact": "3", "upper_exact": "3"})
        limits["population_mean"] = 3 - 1e-14
        self.assertEqual(evaluate_design(8, 1, 2, 4, 1, limits)["status"], "infeasible")

    def test_robust_and_degenerate_ranges(self):
        limits = {"current_session": 1, "persistent_person": 2.25, "population_mean": 0.20625}
        self.assertEqual(evaluate_design(8, 1, 40, 4, 1, limits)["status"], "robust")
        zero = dict.fromkeys(limits, 0)
        self.assertEqual(evaluate_design(0, 0, 2, 1, 1, zero)["status"], "robust")
        self.assertEqual(evaluate_design(0, 1, 2, 1, 1, zero)["status"], "infeasible")

    def test_unknown_is_not_zero_but_cannot_hide_contradiction(self):
        limits = {"current_session": None, "persistent_person": None, "population_mean": None}
        self.assertEqual(evaluate_design(8, 1, 2, 4, 1, limits)["status"], "unresolved")
        limits["persistent_person"], limits["population_mean"] = 1, 1.25
        self.assertEqual(evaluate_design(8, 1, 2, 4, 1, limits)["status"], "infeasible")
        result = plan(8, 1, request(dict.fromkeys(limits, None)))
        self.assertEqual(result["robust_resource_frontier"], [])
        self.assertEqual(result["possible_resource_frontier"], [])
        self.assertFalse(result["no_feasible_design_within_grid"])

    def test_positive_noise_does_not_attain_infinite_depth_floor(self):
        limits = {"current_session": 1, "persistent_person": 8, "population_mean": 4}
        for d in (1, 1e15, 1e100):
            self.assertEqual(evaluate_design(8, 1, 2, 1, d, limits)["status"], "infeasible")

    def test_same_split_witness_satisfies_all_constraints(self):
        for A in (0, 2, 8):
            for N in (2, 40):
                for k in (1, 4, 12):
                    for d in (1, 4):
                        for persistent in (0.1, 1, 10):
                            for population in (0.05, 1.25, 20):
                                limits = {
                                    "current_session": 1,
                                    "persistent_person": persistent,
                                    "population_mean": population,
                                }
                                r = evaluate_design(A, 1, N, k, d, limits)
                                interval = r["admissible_S_uV2"]
                                candidates = [Fraction(A) * t / 20 for t in range(21)]
                                if interval is not None:
                                    left, right = (
                                        Fraction(interval[key])
                                        for key in ("lower_exact", "upper_exact")
                                    )
                                    candidates += [left, right, (left + right) / 2]
                                    self.assertGreaterEqual(left, 0)
                                    self.assertLessEqual(right, A)
                                for S in candidates:
                                    actual = {
                                        "current_session": Fraction(1, d),
                                        "persistent_person": S / k + Fraction(1, k * d),
                                        "population_mean": (A - S + S / k + Fraction(1, k * d)) / N,
                                    }
                                    meets = all(
                                        actual[key] <= Fraction(str(limits[key])) for key in limits
                                    )
                                    inside = interval is not None and left <= S <= right
                                    self.assertEqual(inside, meets)

    def test_frontiers_have_no_dominated_designs_and_preserve_all_candidates(self):
        result = plan(8, 1, request())
        for state, key in (
            ({"robust"}, "robust_resource_frontier"),
            ({"robust", "assumption_sensitive"}, "possible_resource_frontier"),
        ):
            frontier = result[key]
            accepted = [r for r in result["rows"] if r["status"] in state]
            for row in accepted:
                self.assertTrue(any(all(a[k] <= row[k] for k in ("N", "k", "d")) for a in frontier))
            for row in frontier:
                self.assertFalse(
                    any(a != row and all(a[k] <= row[k] for k in row) for a in frontier)
                )
        self.assertFalse(result["biological_threshold_validated"])

    def test_strict_input_contract(self):
        invalid = []
        for value in (True, -1, float("nan"), float("inf"), "1"):
            item = request()
            item["variance_limits_uV2"]["current_session"] = value
            invalid.append(item)
        for key, value in (("N", [1.5]), ("k", [0]), ("d", [1, 1.0]), ("d", [])):
            item = request()
            item["grid"][key] = value
            invalid.append(item)
        item = request()
        item["budget"] = 100000000
        invalid.append(item)
        item = request()
        item["target_status"] = "calibrated"
        invalid.append(item)
        item = request()
        del item["variance_limits_uV2"]["current_session"]
        invalid.append(item)
        item = request()
        item["grid"]["N"] = list(range(1, 1200))
        invalid.append(item)
        for item in invalid:
            with self.assertRaises(ValueError):
                plan(8, 1, item)
        with self.assertRaises(ValueError):
            load_json('{"grid": 1, "grid": 2}')

    def test_cli_replay_hash_bindings_and_create_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            cmd = [
                sys.executable,
                str(PACKAGE / "plan_design.py"),
                "--aggregates",
                str(PACKAGE / "aggregate_results.json"),
                "--request",
                str(PACKAGE / "illustrative-plan.json"),
                "--out",
                str(out),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            r = json.loads(out.read_text())
            for key, name in (
                ("aggregate_sha256", "aggregate_results.json"),
                ("request_sha256", "illustrative-plan.json"),
                ("script_sha256", "plan_design.py"),
            ):
                self.assertEqual(
                    r["bindings"][key], hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest()
                )
            saved = json.loads((PACKAGE / "illustrative-plan-results.json").read_text())
            # Runtime version is disclosed; it does not change exact arithmetic.
            r["bindings"].pop("python")
            saved["bindings"].pop("python")
            self.assertEqual(r, saved)
            original = out.read_bytes()
            self.assertNotEqual(subprocess.run(cmd, capture_output=True, check=False).returncode, 0)
            self.assertEqual(out.read_bytes(), original)
            no_grid = copy.deepcopy(request())
            no_grid["variance_limits_uV2"] = dict.fromkeys(no_grid["variance_limits_uV2"], 0)
            self.assertTrue(plan(8, 1, no_grid)["no_feasible_design_within_grid"])
