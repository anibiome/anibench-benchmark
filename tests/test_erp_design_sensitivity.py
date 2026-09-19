# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
import unittest
from pathlib import Path

from examples.calibration.erp_core.design_sensitivity import bounds


class AlgebraTests(unittest.TestCase):
    def test_published_rows_bind_to_source_aggregates_and_executable(self):
        package = Path(__file__).resolve().parents[1] / "examples/calibration/erp_core"
        calibration = json.loads((package / "aggregate_results.json").read_text())
        result = json.loads((package / "design-sensitivity.json").read_text())
        for key, name in (
            ("aggregate_sha256", "aggregate_results.json"),
            ("script_sha256", "design_sensitivity.py"),
        ):
            self.assertEqual(result[key], hashlib.sha256((package / name).read_bytes()).hexdigest())
        self.assertEqual(
            calibration["script_sha256"],
            hashlib.sha256((package / "analyze_erp.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            calibration["source_manifest_sha256"],
            hashlib.sha256((package / "source_manifest.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(len(result["rows"]), 27)
        self.assertEqual(len({(r["N"], r["d"], r["k"]) for r in result["rows"]}), 27)
        for row in result["rows"]:
            expected = bounds(result["A_uV2"], result["v_uV2"], row["N"], row["d"], row["k"])
            for key, value in expected.items():
                self.assertEqual(row[key], value)
        self.assertIsNone(calibration["biological_cutoff"])
        self.assertFalse(calibration["certified_saturation"])

    def test_endpoint_and_interior_identification(self):
        for A, v in ((0.0, 0.0), (8.0, 3.0), (0.0, 3.0), (8.0, 0.0)):
            for N in (2, 40, 2000):
                for k in (1, 4, 12):
                    for d in (1, 4, 1000000):
                        r = bounds(A, v, N, d, k)
                        for S in (0.0, A / 3, A):
                            B = A - S
                            persistent = S / k + v / (k * d)
                            pop = (B + S / k + v / (k * d)) / N
                            self.assertLessEqual(r["persistent_variance_lower"] - 1e-12, persistent)
                            self.assertLessEqual(persistent, r["persistent_variance_upper"] + 1e-12)
                            self.assertLessEqual(r["population_variance_lower"] - 1e-12, pop)
                            self.assertLessEqual(pop, r["population_variance_upper"] + 1e-12)
                        self.assertAlmostEqual(
                            r["population_variance_upper"], (A + v / (k * d)) / N
                        )
                        if k == 1:
                            self.assertEqual(
                                r["population_variance_lower"], r["population_variance_upper"]
                            )

    def test_depth_limits_do_not_remove_person_variance(self):
        r = bounds(8, 3, 2, 1e15, 12)
        self.assertAlmostEqual(r["current_session_variance"], 0)
        self.assertAlmostEqual(r["persistent_variance_lower"], 0)
        self.assertAlmostEqual(r["persistent_variance_upper"], 8 / 12)
        self.assertAlmostEqual(r["population_variance_lower"], 8 / 24)
        self.assertAlmostEqual(r["population_variance_upper"], 4)

    def test_N_scaling_only_population(self):
        a = bounds(8, 3, 2, 4, 12)
        b = bounds(8, 3, 2000, 4, 12)
        for key in (
            "current_session_variance",
            "persistent_variance_lower",
            "persistent_variance_upper",
        ):
            self.assertEqual(a[key], b[key])
        for key in ("population_variance_lower", "population_variance_upper"):
            self.assertAlmostEqual(a[key] / 1000, b[key])

    def test_more_visits_not_more_current_session_precision(self):
        a = bounds(8, 3, 40, 4, 1)
        b = bounds(8, 3, 40, 4, 12)
        self.assertEqual(a["current_session_variance"], b["current_session_variance"])
        self.assertAlmostEqual(a["persistent_variance_upper"] / 12, b["persistent_variance_upper"])

    def test_reject_invalid_and_no_silent_A_truncation(self):
        for args in (
            (-1, 3, 2, 1, 1),
            (8, float("nan"), 2, 1, 1),
            (8, 3, 2, 0, 1),
            (8, 3, True, 1, 1),
            (8, 3, 2, 1, 1.5),
        ):
            with self.assertRaises(ValueError):
                bounds(*args)


if __name__ == "__main__":
    unittest.main()
