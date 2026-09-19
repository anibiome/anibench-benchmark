# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Public aggregate/synthetic tests; no article body or participant inputs."""

import copy
import hashlib
import itertools
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from anibench.causal_v2 import contrast_information
from examples.design_geometry.calerie import replay as example


class CalerieDesignTests(unittest.TestCase):
    def setUp(self):
        self.manifest = example.load_manifest()
        self.support, self.requests = example.build_requests(self.manifest)

    def test_exact_feasible_support_matches_exhaustive_small_population(self):
        # Enumerate all arm memberships and all visit subsets for a small universe.
        for n in [1, 2, 3]:
            actual = {}
            people = set(range(n))
            subsets = [set(c) for k in range(n + 1) for c in itertools.combinations(people, k)]
            for cr, first, second in itertools.product(subsets, repeat=3):
                al = people - cr
                key = (len(first & cr), len(first & al), len(second & cr), len(second & al))
                actual.setdefault(key, set()).add(
                    (len(first & second & cr), len(first & second & al))
                )
            for (a, b, c, d), expected in actual.items():
                result = example.feasible_supports(n, {"CR": a, "AL": b}, {"CR": c, "AL": d})
                observed = {(r["CR"], r["AL"]) for r in result["feasible_arm_counts"]}
                self.assertEqual(observed, expected)

    def test_exact_union_sensitivity_is_not_claimed_as_source_fact(self):
        facts = self.manifest["reported_facts"]
        result = example.feasible_supports(
            facts["baseline_and_at_least_one_followup_people"],
            facts["12mo_change_people"],
            facts["24mo_change_people"],
            union_complete=True,
        )
        self.assertEqual(result["arm_conditioned_intersection_bound"], [179, 179])
        self.assertEqual(len(result["feasible_arm_counts"]), 5)
        self.assertTrue(all(sum(row.values()) == 179 for row in result["feasible_arm_counts"]))
        with self.assertRaises(ValueError):
            example.feasible_supports(4, {"CR": 1, "AL": 1}, {"CR": 1, "AL": 1}, union_complete=1)

    def test_published_support_and_144_requests(self):
        self.assertEqual(self.support["pooled_intersection_bound"], [179, 185])
        self.assertEqual(self.support["arm_conditioned_intersection_bound"], [179, 183])
        self.assertEqual(len(self.support["feasible_arm_counts"]), 15)
        self.assertEqual(len(self.requests), 144)
        self.assertEqual(len({r["payload_sha256"] for r in self.requests}), 144)

    def test_existing_apis_analytic_checks_and_count_selection_tradeoff(self):
        receipts = [example.evaluate(r) for r in self.requests]
        rows = example.comparison_rows(self.requests, receipts)
        self.assertEqual(len(rows), 36)
        for model in {r["model_id"] for r in rows}:
            selected = [r for r in rows if r["model_id"] == model]
            linear = [r for r in selected if r["estimand_id"] == example.FRAME["estimand_ids"][0]]
            endpoint = next(r for r in linear if r["design_id"] == "endpoint_pair")
            triple = next(r for r in linear if r["design_id"] == "three_timepoints")
            self.assertGreater(triple["variance_interval"][0], endpoint["variance_interval"][1])
            curvature = [
                r for r in selected if r["estimand_id"] == example.FRAME["estimand_ids"][1]
            ]
            missing = next(r for r in curvature if r["design_id"] == "endpoint_pair")
            self.assertIsNone(missing["variance_interval"])
            self.assertEqual(missing["state"], "unidentifiable")

    def test_time_basis_units_and_observation_scale(self):
        years = np.array([0.0, 1.0, 2.0])
        months = 12 * years
        a = contrast_information(np.column_stack([years / 2, (years - 1) ** 2]))
        b = contrast_information(np.column_stack([months / 24, ((months - 12) / 12) ** 2]))
        np.testing.assert_allclose(a.information_matrix, b.information_matrix)
        request = self.requests[0]
        changed = copy.deepcopy(request)
        changed.pop("payload_sha256")
        changed["model"]["residual_variance"] *= 1000**2
        scaled = example.evaluate(example.seal(changed))
        base = example.evaluate(request)
        self.assertAlmostEqual(
            scaled["estimands"][0]["variance"] / base["estimands"][0]["variance"], 1000**2
        )

    def test_shared_frame_and_source_required(self):
        receipt = example.evaluate(self.requests[0])
        for field in ["population_id", "observable_id", "outcome_unit_id", "time_unit_id"]:
            changed = copy.deepcopy(self.requests[0])
            changed.pop("payload_sha256")
            changed["frame"][field] = "different"
            with self.assertRaises(ValueError):
                example.comparison_rows(
                    [self.requests[0], example.seal(changed)], [receipt, receipt]
                )
        changed = copy.deepcopy(self.requests[0])
        changed.pop("payload_sha256")
        changed["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            example.evaluate(example.seal(changed))

    def test_stale_receipts_source_and_manifest_rejected(self):
        request = self.requests[0]
        receipt = example.evaluate(request)
        example.verify_receipt(request, json.loads(json.dumps(receipt)))
        bad = copy.deepcopy(receipt)
        bad.pop("payload_sha256")
        bad["implementation"]["numpy"] = "old"
        with self.assertRaises(ValueError):
            example.verify_receipt(request, example.seal(bad))
        bad = copy.deepcopy(receipt)
        bad["estimands"][0]["variance"] = 0
        with self.assertRaises(ValueError):
            example.verify_receipt(request, bad)
        with self.assertRaises(ValueError):
            example.verify_source(b"stale or fabricated document", self.manifest)
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "manifest.json"
            manifest.write_text(json.dumps(self.manifest))  # Exact frozen bytes differ.
            with self.assertRaises(ValueError):
                example.load_manifest(manifest)

    def test_strict_invalid_models_counts_and_requests(self):
        for value in [True, "1", None, 0, -1, float("nan"), float("inf")]:
            with self.subTest(variance=value), self.assertRaises(ValueError):
                example.validate_model(value, 0.5)
        for value in [True, "0", None, -0.1, 1, float("nan"), float("inf")]:
            with self.subTest(rho=value), self.assertRaises(ValueError):
                example.validate_model(1, value)
        with self.assertRaises(ValueError):
            example.feasible_supports(4, {"CR": 3, "AL": 2}, {"CR": 1, "AL": 1})
        bad = copy.deepcopy(self.requests[0])
        bad.pop("payload_sha256")
        bad["arm_counts"]["CR"] = True
        with self.assertRaises(ValueError):
            example.evaluate(example.seal(bad))

    def test_assumptions_and_complete_support_cannot_be_removed(self):
        for mutation in [
            lambda r: r.update(assumptions=[]),
            lambda r: r.update(unreviewed_assumption=True),
            lambda r: r["model"].update(unknown_effect=1),
        ]:
            bad = copy.deepcopy(self.requests[0])
            bad.pop("payload_sha256")
            mutation(bad)
            with self.assertRaises(ValueError):
                example.evaluate(example.seal(bad))
        one_model = self.requests[:16]
        receipts = [example.evaluate(r) for r in one_model]
        self.assertEqual(len(example.comparison_rows(one_model, receipts)), 4)
        with self.assertRaises(ValueError):
            example.comparison_rows(one_model[:-1], receipts[:-1])
        with self.assertRaises(ValueError):
            example.comparison_rows(one_model + one_model[:1], receipts + receipts[:1])

    def test_create_only_and_deterministic_replay_without_private_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "first", Path(folder) / "second"
            self.assertFalse(example.replay(first)["source_replayed"])
            example.replay(second)
            for p in first.iterdir():
                self.assertEqual(p.read_bytes(), (second / p.name).read_bytes())
                self.assertNotIn(folder.encode(), p.read_bytes())
            before = {p.name: p.read_bytes() for p in first.iterdir()}
            with self.assertRaises(FileExistsError):
                example.replay(first)
            self.assertEqual(before, {p.name: p.read_bytes() for p in first.iterdir()})

    def test_published_chart_is_bound_to_replay_and_exact_example_code(self):
        directory = Path(example.__file__).parent
        metadata = json.loads((directory / "figure-metadata.json").read_text())
        self.assertEqual(metadata["implementation"]["sha256"], example.implementation()["sha256"])
        self.assertEqual(metadata["source_manifest_sha256"], example.MANIFEST_SHA256)
        self.assertEqual(metadata["source_sha256"], self.manifest["source"]["sha256"])
        self.assertEqual(
            metadata["plot_script_sha256"],
            hashlib.sha256((directory / "plot.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            metadata["chart_results_sha256"],
            hashlib.sha256((directory / "chart-results.json").read_bytes()).hexdigest(),
        )
        rows = example.comparison_rows(self.requests, [example.evaluate(r) for r in self.requests])
        self.assertEqual(json.loads((directory / "chart-results.json").read_text()), rows)
        self.assertEqual(
            metadata["rows"], [row for row in rows if row["model"] == metadata["model"]]
        )
        root = directory.parents[2]
        self.assertEqual(
            (root / "web/calerie-design.svg").read_bytes(),
            (directory / "comparison.svg").read_bytes(),
        )
        self.assertEqual(
            (root / "web/calerie-design.json").read_bytes(),
            (directory / "figure-metadata.json").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
