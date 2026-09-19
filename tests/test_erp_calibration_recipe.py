# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 AniBench contributors
"""Synthetic tests; no ERP participant files or rows are included."""

import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from examples.calibration.erp_core.analyze_erp import (
    EXPECTED_FILES,
    conditional_variances,
    validate_identifiers,
    verify_sources,
)


class ConditionalPrecisionTests(unittest.TestCase):
    def test_known_variance_and_exact_empirical_bootstrap(self):
        # Enumerate all size-two resamples of [0, 2]: mean variance is 0.5.
        trials = np.array([0.0, 2.0])
        means = np.array([(a + b) / 2 for a in trials for b in trials])
        sd = np.full((1, 2), trials.std(ddof=1))
        analytic, empirical = conditional_variances(sd, np.full((1, 2), 2))
        np.testing.assert_allclose(analytic, 1.0)
        np.testing.assert_allclose(empirical, means.var(ddof=0))

    def test_units_scaling(self):
        sd = np.array([[2.0, 4.0], [3.0, 5.0]])
        n = np.array([[10.0, 20.0], [30.0, 40.0]])
        for x, y in zip(
            conditional_variances(sd, n), conditional_variances(sd * 1000, n)
        ):
            np.testing.assert_allclose(y, x * 1e6)

    def test_more_trials_reduce_mean_variance(self):
        sd = np.ones((2, 2))
        a, _ = conditional_variances(sd, np.full((2, 2), 10))
        b, _ = conditional_variances(sd, np.full((2, 2), 20))
        np.testing.assert_allclose(b, a / 2)

    def test_invalid_counts_and_variances_rejected(self):
        for value in [0.0, 1.0, -1.0, 2.5, np.nan, np.inf]:
            with self.subTest(count=value), self.assertRaises(ValueError):
                conditional_variances(np.ones((1, 2)), np.full((1, 2), value))
        for value in [0.0, -1.0, np.nan, np.inf]:
            with self.subTest(sd=value), self.assertRaises(ValueError):
                conditional_variances(np.full((1, 2), value), np.full((1, 2), 10))

    def test_reordered_or_duplicate_keys_rejected(self):
        ids = np.arange(1, 41)
        validate_identifiers(ids, ids.copy())
        for other in [ids[::-1], np.ones(40), ids[:-1]]:
            with self.assertRaises(ValueError):
                validate_identifiers(ids, other)

    def test_duplicate_traversal_and_unexpected_filenames_rejected(self):
        valid = sorted(EXPECTED_FILES)
        cases = [
            [valid[0]] * 5,
            ["../escape"] + valid[1:],
            ["dir\\escape"] + valid[1:],
            ["unexpected"] + valid[1:],
        ]
        for names in cases:
            with self.subTest(names=names), self.assertRaises(ValueError):
                verify_sources(Path("unused"), {"files": [{"name": n} for n in names]})

    def test_hash_guard_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            files = []
            for name in sorted(EXPECTED_FILES):
                data = b"fixture"
                (base / name).write_bytes(data)
                files.append(
                    {
                        "name": name,
                        "size_bytes": len(data),
                        "hashes": {"sha256": hashlib.sha256(data).hexdigest()},
                    }
                )
            manifest = {"files": files}
            verify_sources(base, manifest)
            (base / files[0]["name"]).write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_sources(base, manifest)


if __name__ == "__main__":
    unittest.main()
