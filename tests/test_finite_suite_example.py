# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "erp_suite_replay", ROOT / "examples/finite_suites/replay_erp.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ERPExampleTests(unittest.TestCase):
    def test_actual_boundaries_and_create_only_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "first"
            result = MODULE.replay(out)
            cases = {row["case"]: row for row in result["cases"]}
            self.assertEqual(len(cases), 12)
            for depth in [1, 22, 23, 90, 91]:
                for level, boundary in [("R1", 23), ("R2", 91)]:
                    self.assertEqual(
                        cases[f"{level}-depth-{depth}"]["attainment"],
                        "attained" if depth >= boundary else "not_attained",
                    )
            self.assertEqual(cases["strong-prior-likelihood-depth-0"]["attainment"], "not_attained")
            self.assertEqual(cases["strong-prior-posterior-depth-0"]["attainment"], "attained")
            self.assertTrue(
                cases["strong-prior-likelihood-depth-0"]["prior_only_precision_attainment"]
            )
            with self.assertRaises(FileExistsError):
                MODULE.replay(out)
            second = Path(temporary) / "second"
            MODULE.replay(second)
            self.assertEqual(
                {p.name: p.read_bytes() for p in out.iterdir()},
                {p.name: p.read_bytes() for p in second.iterdir()},
            )
            for path in out.glob("*.request.json"):
                request = json.loads(path.read_text())
                provenance = out / (request["design_id"] + ".provenance.json")
                self.assertEqual(
                    request["design_source_sha256"],
                    "sha256:" + hashlib.sha256(provenance.read_bytes()).hexdigest(),
                )
                self.assertNotIn(str(ROOT), path.read_text())
            profiles = json.loads((out / "trusted-profiles.json").read_text())
            r2 = next(p for p in profiles.values() if p["parent_sha256"])
            r1 = profiles[r2["parent_sha256"]]
            self.assertEqual(r1["targets"][0]["frame_sha256"], r2["targets"][0]["frame_sha256"])

    def test_stale_input_rejects_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            changed = base / "changed.json"
            original = ROOT / "examples/calibration/erp_core/aggregate_results.json"
            changed.write_bytes(original.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                MODULE.replay(base / "out", aggregate=changed)
            self.assertFalse((base / "out").exists())


if __name__ == "__main__":
    unittest.main()
