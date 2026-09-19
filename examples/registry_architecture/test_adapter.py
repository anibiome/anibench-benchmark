# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Synthetic source fixtures; no registry narratives or participant data."""

import copy
import hashlib
import json
import unittest

from adapter import derive_snapshot, verify_derived


def fixture():
    source = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "designModule": {
                "enrollmentInfo": {"count": 10, "type": "ESTIMATED"},
                "designInfo": {"allocation": "RANDOMIZED"},
                "phases": ["PHASE2"],
            },
            "armsInterventionsModule": {"armGroups": [{}, {}]},
            "statusModule": {
                "startDateStruct": {"date": "2024-01", "type": "ESTIMATED"},
                "primaryCompletionDateStruct": {"date": "2024-03", "type": "ESTIMATED"},
            },
        }
    }
    raw = json.dumps(source).encode()
    sha = hashlib.sha256(raw).hexdigest()
    row = derive_snapshot(raw, {"nct_id": "NCT00000001", "raw_sha256": sha})
    row["source_sha256"] = sha
    return raw, row


class AdapterTests(unittest.TestCase):
    def test_correct_source_and_month_precision(self):
        raw, row = fixture()
        verify_derived(row, raw)
        coordinates = {c["coordinate_id"]: c for c in row["record"]["coordinates"]}
        self.assertEqual(
            coordinates["calendar_span"]["value"], {"state": "bounded", "lower": 30, "upper": 90}
        )
        self.assertEqual(row["enrollment_lifecycle"], "planned")

    def test_changed_count_with_original_source_hash_rejected(self):
        raw, row = fixture()
        row["record"]["coordinates"][0]["value"]["value"] = 11
        with self.assertRaisesRegex(ValueError, "snapshot_derived_coordinate_mismatch"):
            verify_derived(row, raw)

    def test_semantics_and_descriptors_rederived_not_trusted(self):
        raw, original = fixture()
        for field, value in [
            ("phase_tokens", ["PHASE3"]),
            ("allocation_token", "NON_RANDOMIZED"),
            ("enrollment_lifecycle", "collected"),
        ]:
            with self.subTest(field=field):
                row = copy.deepcopy(original)
                row[field] = value
                with self.assertRaisesRegex(ValueError, "snapshot_derived_coordinate_mismatch"):
                    verify_derived(row, raw)

    def test_raw_change_cannot_retain_prior_hash(self):
        raw, row = fixture()
        with self.assertRaisesRegex(ValueError, "frozen_snapshot_hash_mismatch"):
            verify_derived(row, raw + b" ")


if __name__ == "__main__":
    unittest.main()
