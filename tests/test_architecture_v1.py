# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from dataclasses import FrozenInstanceError
from itertools import product

from anibench.architecture_v1 import (
    ArchitectureError,
    CoordinateSemantics,
    architecture_sha256,
    compare_architecture,
)


def semantics(kind="population_count"):
    return {
        "quantity_kind": kind,
        "unit": "people",
        "entity_namespace": "distinct_humans",
        "denominator": "whole_declared_cohort",
        "collection_status": "collected",
        "time_scope": "declared_collection_window",
        "aggregation": "distinct_count",
    }


def request(first=10, second=20):
    sem = semantics()
    return {
        "contract": "anibench.architecture-request.v1",
        "basis": {
            "basis_id": "population-quantity.v1",
            "population_comparison": {
                "mode": "quantity_only_preserve_each_population_scope",
                "rationale": "Compare collected reach, not equivalent populations.",
            },
            "coordinates": [
                {"coordinate_id": "people", "semantics": sem, "direction": "higher_quantity"}
            ],
        },
        "records": [
            {
                "record_id": identity,
                "study_id": identity + "-study",
                "population_scope": population,
                "coordinates": [
                    {
                        "coordinate_id": "people",
                        "semantics": copy.deepcopy(sem),
                        "value": {"state": "point", "value": value},
                        "sources": [
                            {
                                "source_sha256": "sha256:" + "a" * 64,
                                "locator": "/public/synthetic/aggregate",
                            }
                        ],
                    }
                ],
            }
            for identity, population, value in [
                ("a", "adults in catchment A", first),
                ("b", "adults in catchment B", second),
            ]
        ],
    }


def add_depth(req, first, second, direction="higher_quantity"):
    sem = dict(
        semantics("measurement_depth"),
        unit="distinct occasions per person",
        entity_namespace="dated_person_measurement_occasions",
        aggregation="median_including_zero",
    )
    req["basis"]["coordinates"].append(
        {"coordinate_id": "depth", "semantics": sem, "direction": direction}
    )
    for row, value in zip(req["records"], [first, second], strict=True):
        row["coordinates"].append(
            {
                "coordinate_id": "depth",
                "semantics": sem,
                "value": {"state": "point", "value": value},
                "sources": [
                    {"source_sha256": "sha256:" + "b" * 64, "locator": "/synthetic/declared_median"}
                ],
            }
        )


def relation(req):
    return compare_architecture(req)["pairwise_relations"][0]["relation"]


class ArchitectureTests(unittest.TestCase):
    def test_impossible_or_fractional_population_bounds_rejected(self):
        for lower, upper in [(0.1, 0.2), (1.5, 3), (1, 2.5), (1.5, None)]:
            req = request(1, 0)
            req["records"][0]["coordinates"][0]["value"] = {
                "state": "bounded", "lower": lower, "upper": upper
            }
            with self.assertRaises(ArchitectureError):
                compare_architecture(req)

    def test_oversized_numeric_value_is_contract_error(self):
        with self.assertRaises(ArchitectureError):
            compare_architecture(request(10**400, 1))

    def test_different_populations_quantity_only(self):
        req = request()
        result = compare_architecture(req)
        self.assertEqual(
            result["pairwise_relations"][0]["relation"], "second_dominates_selected_quantities"
        )
        self.assertEqual(result["definitely_undominated_record_ids"], ["b"])
        self.assertEqual(result["entries"][0]["population_scope"], "adults in catchment A")
        self.assertIsNone(result["overall_score"])
        self.assertNotIn("information_matrix", str(result))
        self.assertEqual(
            result["receipt_sha256"],
            architecture_sha256({k: v for k, v in result.items() if k != "receipt_sha256"}),
        )

    def test_single_fact_view_without_geometry(self):
        req = request()
        req["records"].pop()
        result = compare_architecture(req)
        self.assertEqual(result["entries"][0]["coordinates"][0]["lower"], 10)
        self.assertEqual(result["pairwise_relations"], [])
        self.assertEqual(result["definitely_undominated_record_ids"], ["a"])
        req["records"][0]["coordinates"] = []
        self.assertEqual(compare_architecture(req)["definitely_undominated_record_ids"], [])

    def test_tiny_deep_large_shallow_and_no_imputed_profile(self):
        req = request(2, 10000)
        add_depth(req, 1000000, 1)
        self.assertEqual(relation(req), "definite_tradeoff")
        result = compare_architecture(req)
        self.assertEqual(result["definitely_undominated_record_ids"], ["a", "b"])
        req["records"][0]["coordinates"].pop()
        self.assertEqual(relation(req), "unresolved")
        self.assertEqual(
            compare_architecture(req)["entries"][0]["coordinates"][1]["state"], "unknown"
        )

    def test_bounds_unknown_and_exact_ties(self):
        req = request(20, 10)
        req["records"][0]["coordinates"][0]["value"] = {
            "state": "bounded",
            "lower": 11,
            "upper": None,
        }
        self.assertEqual(relation(req), "first_dominates_selected_quantities")
        req["records"][0]["coordinates"][0]["value"] = {
            "state": "bounded",
            "lower": 10,
            "upper": 20,
        }
        self.assertEqual(relation(req), "unresolved")
        self.assertEqual(relation(request(10, 10)), "exact_tie")
        req["records"][0]["coordinates"][0]["value"] = {
            "state": "unknown",
            "reason": "not reported",
        }
        self.assertEqual(relation(req), "unresolved")
        req["records"][0]["coordinates"][0]["value"] = {"state": "point", "value": 0}
        self.assertEqual(relation(req), "second_dominates_selected_quantities")

    def test_touching_bounds_with_strict_other_axis(self):
        req = request()
        add_depth(req, 5, 2)
        req["records"][0]["coordinates"][0]["value"] = {"state": "bounded", "lower": 2, "upper": 3}
        req["records"][1]["coordinates"][0]["value"] = {"state": "bounded", "lower": 1, "upper": 2}
        self.assertEqual(relation(req), "first_dominates_selected_quantities")
        # Independently enumerate every integer point of these closed rectangles.
        for a, b in product(product([2, 3], [5]), product([1, 2], [2])):
            self.assertTrue(all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b)))

    def test_direction_and_descriptors(self):
        req = request(10, 20)
        req["basis"]["coordinates"][0]["direction"] = "lower_quantity"
        self.assertEqual(relation(req), "first_dominates_selected_quantities")
        req["basis"]["coordinates"][0]["direction"] = "descriptor_only"
        result = compare_architecture(req)
        self.assertEqual(result["pairwise_relations"][0]["relation"], "descriptor_only")
        self.assertEqual(result["possibly_undominated_record_ids"], [])

    def test_mismatched_semantics_unresolved(self):
        for field, value in [
            ("unit", "cells"),
            ("entity_namespace", "assay_probes"),
            ("denominator", "assayed_subset"),
            ("collection_status", "planned"),
            ("time_scope", "first_year_only"),
            ("aggregation", "maximum"),
        ]:
            req = request()
            req["records"][0]["coordinates"][0]["semantics"][field] = value
            self.assertEqual(relation(req), "unresolved", field)
        req = request()
        req["basis"]["coordinates"][0]["semantics"]["collection_status"] = "reported_unspecified"
        for r in req["records"]:
            r["coordinates"][0]["semantics"]["collection_status"] = "reported_unspecified"
        self.assertEqual(relation(req), "unresolved")

    def test_duplicates_and_expense_fields_rejected(self):
        for mutate in [
            lambda r: r["basis"]["coordinates"].append(copy.deepcopy(r["basis"]["coordinates"][0])),
            lambda r: r["basis"]["coordinates"].append(
                dict(r["basis"]["coordinates"][0], coordinate_id="renamed")
            ),
            lambda r: r["records"][0]["coordinates"].append(
                copy.deepcopy(r["records"][0]["coordinates"][0])
            ),
            lambda r: r["records"][0].update(expense=100000000),
            lambda r: r["basis"].update(weights=[1]),
        ]:
            req = request()
            mutate(req)
            with self.assertRaises(ArchitectureError):
                compare_architecture(req)
        req = request()
        req["basis"]["coordinates"][0]["semantics"]["quantity_kind"] = "expense"
        with self.assertRaises(ArchitectureError):
            compare_architecture(req)

    def test_malformed_numbers_bounds_and_sources(self):
        for value in [
            {"state": "point", "value": True},
            {"state": "point", "value": 2.5},
            {"state": "point", "value": float("nan")},
            {"state": "point", "value": -1},
            {"state": "bounded", "lower": 2, "upper": 1},
            {"state": "bounded", "lower": 2, "upper": 2},
            {"state": "unknown", "reason": " "},
            {"state": "bounded", "lower": 0, "upper": float("inf")},
        ]:
            req = request()
            req["records"][0]["coordinates"][0]["value"] = value
            with self.assertRaises(ValueError):
                compare_architecture(req)
        req = request()
        req["records"][0]["coordinates"][0]["sources"] = []
        with self.assertRaises(ArchitectureError):
            compare_architecture(req)

    def test_names_order_do_not_influence_quantity(self):
        req = request()
        before = copy.deepcopy(req)
        result = compare_architecture(req)
        self.assertEqual(req, before)
        req["records"].reverse()
        self.assertEqual(
            compare_architecture(req)["pairwise_relations"], result["pairwise_relations"]
        )
        for r in req["records"]:
            r["study_id"] = "new-name-" + r["study_id"]
        self.assertEqual(
            compare_architecture(req)["pairwise_relations"], result["pairwise_relations"]
        )
        sem = CoordinateSemantics.from_json(semantics())
        with self.assertRaises(FrozenInstanceError):
            sem.unit = "cost"


if __name__ == "__main__":
    unittest.main()
