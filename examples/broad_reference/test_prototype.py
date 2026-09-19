# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

import numpy as np
import pytest
from prototype import evaluate, profiles, state_information, summary, witness


class BroadStandardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry, cls.metadata = profiles()

    def run_design(self, d, level=1):
        return evaluate(d, level, self.registry, self.metadata)

    def test_level_witnesses_and_parent(self):
        self.assertEqual(summary(self.run_design(witness(1)))["attainment"], "attained")
        self.assertEqual(
            summary(self.run_design(witness(1), 2))["attainment"], "not_attained"
        )
        self.assertEqual(
            summary(self.run_design(witness(2), 2))["attainment"], "attained"
        )
        self.assertEqual(
            summary(self.run_design(witness(2), 1))["attainment"], "attained"
        )

    def test_independent_scalar_oracles_and_boundary(self):
        d = witness(1)
        run = self.run_design(d)
        targets = {
            t["canonical_id"]: t for t in run["receipt"]["scenarios"][0]["targets"]
        }
        expected = {
            "genomic.base.state": 4 / 16,
            "genomic.base.population": 1.5 / 160,
            "transcriptomic.base.time": 8 / 16,
            "randomized-input-contrast": 6 / 160,
            "population-crossmodal-link": 1.5 / 160,
            "molecular-functional-complementarity": 2 / 16,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(
                targets[key]["likelihood_diagnostics"][0]["variance"], value, places=10
            )
        for n in [148, 150]:
            x = witness(1)
            x["people"] = x["linked_people"] = n
            self.assertEqual(
                summary(self.run_design(x))["attainment"],
                "attained" if n == 150 else "not_attained",
            )
        for n in [2096, 2100]:
            x = witness(2)
            x["people"] = x["linked_people"] = n
            self.assertEqual(
                summary(self.run_design(x, 2))["attainment"],
                "attained" if n == 2100 else "not_attained",
            )

    def test_tiny_deep_and_huge_shallow(self):
        tiny = witness(1)
        tiny.update(people=2, linked_people=2, raw_depth=1000000, expense=100000000)
        small = summary(self.run_design(tiny))
        self.assertIn("genomic.base.population", small["failed"])
        self.assertIn("randomized-input-contrast", small["failed"])
        self.assertNotIn("genomic.base.state", small["failed"])
        huge = witness(1)
        huge.update(people=100000, linked_people=100000, raw_depth=1)
        large = summary(self.run_design(huge))
        self.assertIn("genomic.base.state", large["failed"])
        self.assertNotIn("genomic.base.population", large["failed"])

    def test_copy_expense_and_name_invariance(self):
        a = witness(1)
        b = copy.deepcopy(a)
        b.update(copied_rows=1000000, expense=100000000, design_id="renamed")
        x = self.run_design(a)
        y = self.run_design(b)

        def metrics(r):
            return [
                (t["canonical_id"], t["attainment"], t["likelihood_diagnostics"])
                for t in r["receipt"]["scenarios"][0]["targets"]
            ]

        self.assertEqual(metrics(x), metrics(y))
        b["raw_depth"] = 32
        self.assertLess(
            self.run_design(b)["receipt"]["scenarios"][0]["targets"][0][
                "likelihood_diagnostics"
            ][0]["variance"],
            0.25,
        )

    def test_missing_domains_and_rank(self):
        for support, state in [(False, "not_attained"), (None, "unknown")]:
            d = witness(1)
            d["domains"]["neural"] = support
            self.assertEqual(summary(self.run_design(d))["attainment"], state)
        d = witness(1)
        d["mode_fraction"] = 0.25
        d["copied_rows"] = 1000000
        self.assertEqual(summary(self.run_design(d))["attainment"], "not_attained")
        self.assertEqual(np.linalg.matrix_rank(state_information(d, "genomic", 16)), 4)

    def test_linkage_time_arms_and_temporal_alias(self):
        for update, failed in [
            ({"linked_people": 0}, "population-crossmodal-link"),
            ({"days": [0]}, "transcriptomic.base.time"),
            ({"assignment": "redundant"}, "randomized-input-contrast"),
            ({"digital_hours": [0, 24, 48, 72]}, "digital.base.state"),
        ]:
            d = witness(1)
            d.update(update)
            self.assertIn(failed, summary(self.run_design(d))["failed"])
        d = witness(1)
        d["linked_people"] = None
        self.assertEqual(summary(self.run_design(d))["attainment"], "unknown")

    def test_neural_observation_is_not_cortical_intervention(self):
        d = witness(1)
        self.assertEqual(summary(self.run_design(d))["attainment"], "attained")
        self.assertIn(
            "controlled-cortical-response",
            summary(self.run_design(d, "1-neural"))["failed"],
        )
        d["cortical_assignment"] = True
        self.assertIn(
            "controlled-cortical-response",
            summary(self.run_design(d, "1-neural"))["failed"],
        )
        d["matched_peripheral_control"] = True
        self.assertEqual(
            summary(self.run_design(d, "1-neural"))["attainment"], "attained"
        )

    def test_complementary_operators_and_correlated_oversampling(self):
        h = np.array([[1.0, 1.0], [1.0, -1.0]])
        self.assertEqual(np.linalg.matrix_rank(h[:1].T @ h[:1]), 1)
        self.assertEqual(np.linalg.matrix_rank(h.T @ h), 2)
        d = witness(1)
        d.update(raw_depth=1000000, repeat_correlation=0.99)
        self.assertEqual(summary(self.run_design(d))["attainment"], "not_attained")

    def test_strict_invalid_design_values(self):
        for updates in [
            {"people": True},
            {"raw_depth": 0},
            {"repeat_correlation": 1},
            {"mode_fraction": float("nan")},
            {"linked_people": 161},
            {"digital_hours": [True]},
            {"cortical_assignment": "yes"},
        ]:
            d = witness(1)
            d.update(updates)
            with self.assertRaises(ValueError):
                self.run_design(d)


if __name__ == "__main__":
    unittest.main()


def test_actual_study_admission_rejected():
    design = witness(1)
    design["evidence_type"] = "source_backed_real_study"
    with pytest.raises(ValueError, match="Synthetic reference"):
        evaluate(design, 1)


def test_stale_model_registry_cannot_change_geometry_under_old_identity():
    import prototype as p

    registry, metadata = p.profiles()
    design = p.witness(1)
    design["raw_depth"] = 1
    before = p.evaluate(design, 1, registry, metadata)
    assert p.summary(before)["attainment"] == "not_attained"
    original = copy.deepcopy(p.STANDARD["model"])
    try:
        p.STANDARD["model"]["measurement_variance_R"] = 0.01
        with pytest.raises(ValueError, match="stale or altered"):
            p.evaluate(design, 1, registry, metadata)
        revised_registry, revised_metadata = p.profiles()
        after = p.evaluate(design, 1, revised_registry, revised_metadata)
        assert p.summary(after)["attainment"] == "attained"
        assert before["request"]["profile_sha256"] != after["request"]["profile_sha256"]
        a = before["request"]["scenarios"][0]["targets"][0]["request"]["task"]
        b = after["request"]["scenarios"][0]["targets"][0]["request"]["task"]
        assert a["model_sha256"] != b["model_sha256"]
    finally:
        p.STANDARD["model"].clear()
        p.STANDARD["model"].update(original)


def test_altered_metadata_and_registry_rejected():
    registry, metadata = profiles()
    stale = copy.deepcopy(metadata)
    stale["genomic.base.state"]["dimension"] = 1
    with pytest.raises(ValueError, match="stale or altered"):
        evaluate(witness(1), 1, registry, stale)
    modified = copy.deepcopy(registry)
    next(iter(modified.values()))["scope"] = "altered"
    with pytest.raises(ValueError, match="stale or altered"):
        evaluate(witness(1), 1, modified, metadata)


@pytest.mark.parametrize("value", [True, 0, -1, float("nan"), float("inf")])
def test_invalid_reference_noise_rejected(value):
    import prototype as p

    original = p.STANDARD["model"]["between_person_variance_B"]
    try:
        p.STANDARD["model"]["between_person_variance_B"] = value
        with pytest.raises(ValueError, match="finite positive"):
            p.profiles()
    finally:
        p.STANDARD["model"]["between_person_variance_B"] = original


def test_distributed_declarations_and_catalogue_match_generator():
    import json
    from pathlib import Path

    from catalogue import rows
    from replay import compact_profiles

    root = Path(__file__).parent
    assert json.loads(
        (root / "profile-declarations.json").read_text()
    ) == compact_profiles(profiles()[0])
    assert (
        json.loads((root / "coordinate_catalogue.json").read_text())["coordinates"]
        == rows
    )
    assert len({r["coordinate_id"] for r in rows}) == 160
    assert all(
        not r["temporal_contrast_admitted"] for r in rows if r["domain"] == "genomic"
    )


def test_distributed_script_hashes_and_chart_boundaries():
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).parent
    bindings = json.loads((root / "replay-bindings.json").read_text())
    for name, expected in bindings["script_sha256"].items():
        assert (
            "sha256:" + hashlib.sha256((root / name).read_bytes()).hexdigest()
            == expected
        )
    data = json.loads((root / "figure-data.json").read_text())
    assert len(data["examples"]) == 14
    assert len(data["sensitivity"]) == 10
    assert [x["attainment"] for x in data["examples"][:4]] == [
        "attained",
        "not_attained",
        "attained",
        "attained",
    ]
    assert all(x["attainment"] == "not_attained" for x in data["sensitivity"][2:])
