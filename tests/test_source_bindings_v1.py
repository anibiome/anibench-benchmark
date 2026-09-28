# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from anibench.source_bindings_v1 import BindingError, bind_design, derive, digest, pointer


class SourceBindingsTests(unittest.TestCase):
    def setUp(self):
        self.source = {"participants": 204, "schedule": [0, 3, 12], "unknown": None}
        self.sources = {digest(self.source): self.source}
        self.design = {"cohort_n": 204, "assignment": None, "horizon_days": 365}
        self.bindings = [
            {"target": "/cohort_n", "mode": "literal", "value_sha256": digest(204),
             "source_refs": [{"source_sha256": digest(self.source), "pointer": "/participants"}],
             "rationale": "Published parent count, not a claim of modality-complete records."},
            {"target": "/assignment", "mode": "unknown", "value_sha256": digest(None),
             "rationale": "Assignment record has not been qualified."},
            {"target": "/horizon_days", "mode": "normative_assumption", "value_sha256": digest(365),
             "rationale": "Fixed challenge horizon; not an inferred actual collection time."},
        ]

    def test_preserves_unknown_and_exposes_conditional_assumption(self):
        design, receipt, evidence = bind_design(self.design, self.bindings, self.sources)
        self.assertIsNone(design["assignment"])
        self.assertEqual(receipt["conditional_assumption_fields"], ["/horizon_days"])
        self.assertEqual(receipt["unresolved_fields"], ["/assignment"])
        self.assertEqual(self.design, {"cohort_n": 204, "assignment": None, "horizon_days": 365})
        self.assertEqual(digest(evidence), receipt["evidence_sha256"])
        self.assertNotIn("source_sha256", evidence["design"])
        design["cohort_n"] = 999
        self.assertEqual(digest(evidence), receipt["evidence_sha256"])

    def test_rejects_unbound_missingness_changed_counts_and_boolean_count(self):
        with self.assertRaises(BindingError):
            bind_design(self.design, self.bindings[:-1], self.sources)
        for replacement in [0, False, 999]:
            design = copy.deepcopy(self.design)
            design["assignment"] = replacement
            bindings = copy.deepcopy(self.bindings)
            bindings[1]["value_sha256"] = digest(replacement)
            with self.assertRaises(BindingError):
                bind_design(design, bindings, self.sources)
        changed = copy.deepcopy(self.design)
        changed["cohort_n"] = 203
        with self.assertRaises(BindingError):
            bind_design(changed, self.bindings, self.sources)

    def test_true_is_not_one_and_stale_sources_fail(self):
        source = {"count": True}
        binding = {"target": "/n", "mode": "literal", "value_sha256": digest(1),
                   "source_refs": [{"source_sha256": digest(source), "pointer": "/count"}],
                   "rationale": "Do not coerce a boolean to a participant count."}
        with self.assertRaises(BindingError):
            bind_design({"n": 1}, [binding], {digest(source): source})
        with self.assertRaises(BindingError):
            bind_design(self.design, self.bindings, {digest(self.source): {"participants": 1}})

    def test_nominal_unit_conversion_and_overlap_do_not_invent_exact_intersection(self):
        self.assertEqual(derive("affine_unit_conversion", [12], {"scale": 365/12,
                         "offset": 0, "source_unit": "nominal_month", "target_unit": "nominal_day"}), 365)
        self.assertEqual(derive("two_set_intersection", [294, 224, 120], {}), [50, 120])
        for values in [[294, 295, 120], [True, 1, 1], [10, -1, 2]]:
            with self.assertRaises(BindingError):
                derive("two_set_intersection", values, {})

    def test_pointer_escape_and_array_indices(self):
        self.assertEqual(pointer({"a/b": {"~x": [7]}}, "/a~1b/~0x/0"), 7)
        for path in ["/01", "/-1", "/1", "/~2"]:
            with self.assertRaises(BindingError):
                pointer([7], path)

    def test_receipt_changes_with_assumptions_not_binding_order(self):
        a = bind_design(self.design, self.bindings, self.sources)[0]
        b = bind_design(self.design, list(reversed(self.bindings)), self.sources)[0]
        self.assertEqual(a, b)
        modified = copy.deepcopy(self.bindings)
        modified[-1]["rationale"] = "Different scientific interpretation requires a new receipt."
        c = bind_design(self.design, modified, self.sources)[0]
        self.assertNotEqual(a["source_sha256"], c["source_sha256"])

    def test_review_must_exist_and_bind_exact_extraction(self):
        source = {"text": "The report describes one hundred enrolled participants."}
        refs = [{"source_sha256": digest(source), "pointer": "/text"}]
        binding = {"target": "/n", "mode": "qualified_extraction", "value_sha256": digest(100),
                   "source_refs": refs, "rationale": "Reviewed textual count extraction.",
                   "reviewer_receipt_sha256": "not-a-hash"}
        for key in ["not-a-hash", "sha256:" + "0" * 64]:
            binding["reviewer_receipt_sha256"] = key
            with self.assertRaises(BindingError):
                bind_design({"n": 100}, [binding], {digest(source): source})
        review = {"schema": "anibench.source-extraction-review.v1", "claims": [
            {"target": "/n", "value_sha256": digest(100), "source_refs": refs,
             "disposition": "qualified"}]}
        binding["reviewer_receipt_sha256"] = digest(review)
        _, receipt, _ = bind_design({"n": 100}, [binding], {digest(source): source},
                                  trusted_review_receipts={digest(review): review})
        self.assertEqual(receipt["reviewed_extraction_fields"], ["/n"])
        wrong = copy.deepcopy(review)
        wrong["claims"][0]["disposition"] = "unresolved"
        binding["reviewer_receipt_sha256"] = digest(wrong)
        with self.assertRaises(BindingError):
            bind_design({"n": 100}, [binding], {digest(source): source},
                        trusted_review_receipts={digest(wrong): wrong})

    def test_malformed_bindings_fail_with_an_input_error(self):
        for binding in [None, {}, {"target": []}, {"target": "/x", "mode": "literal"}]:
            with self.assertRaises(BindingError):
                bind_design(self.design, [binding], self.sources)
        with self.assertRaises(BindingError):
            bind_design({1: "bad JSON key"}, [], {})
        with self.assertRaises(BindingError):
            derive("sum", [], {})
        bad_review = {"schema": "anibench.source-extraction-review.v1", "claims": None}
        with self.assertRaises(BindingError):
            bind_design(self.design, self.bindings, self.sources,
                        trusted_review_receipts={digest(bad_review): bad_review})
        with self.assertRaises(BindingError):
            derive("affine_unit_conversion", [1], {"scale": 1, "offset": 0,
                   "source_unit": 123, "target_unit": "kg"})

    def test_large_counts_preserve_exact_integer_arithmetic(self):
        source = {"n": 9007199254740993}
        design = {"n": source["n"]}
        binding = {"target": "/n", "mode": "derived", "derivation": "sum",
                   "value_sha256": digest(design["n"]), "rationale": "Exact integer sum",
                   "source_refs": [{"source_sha256": digest(source), "pointer": "/n"}]}
        bound, _, _ = bind_design(design, [binding], {digest(source): source})
        self.assertEqual(bound["n"], 9007199254740993)
        altered = {"n": 9007199254740992}
        binding["value_sha256"] = digest(altered["n"])
        with self.assertRaises(BindingError):
            bind_design(altered, [binding], {digest(source): source})

    def test_overlap_endpoints_bind_as_leaves(self):
        source = {"parent": 10, "a": 8, "b": 7}
        refs = [{"source_sha256": digest(source), "pointer": "/" + key}
                for key in ["parent", "a", "b"]]
        bindings = [{"target": "/bounds/" + str(i), "mode": "derived",
                     "derivation": "two_set_intersection_" + end,
                     "value_sha256": digest(value), "rationale": "Same declared parent",
                     "source_refs": refs}
                    for i, (end, value) in enumerate([("lower", 5), ("upper", 7)])]
        design, _, _ = bind_design({"bounds": [5, 7]}, bindings, {digest(source): source})
        self.assertEqual(design["bounds"], [5, 7])

    def test_cli_runs_offline_and_preserves_existing_output(self):
        from anibench.cli import main

        with tempfile.TemporaryDirectory() as folder:
            request, output = Path(folder) / "request.json", Path(folder) / "private.json"
            payload = {"design": self.design, "bindings": self.bindings, "sources": self.sources}
            request.write_text(json.dumps(payload))
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["bind-design", str(request), "--out", str(output)])
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(set(json.loads(stdout.getvalue())), {"evidence_sha256", "design_sha256"})
            result = json.loads(output.read_text())
            self.assertEqual(result["receipt"]["schema"], "anibench.capability-intake-receipt.v1")
            self.assertFalse(result["receipt"]["raw_source_objects_embedded"])
            original = output.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(main(["bind-design", str(request), "--out", str(output)]), 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(json.loads(request.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
