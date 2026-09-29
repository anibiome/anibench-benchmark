# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""A wholly synthetic collection with different molecular/function subsets."""
from __future__ import annotations

import json
from pathlib import Path


def example():
    base = json.loads(Path(__file__).parents[1].joinpath("paired_question/input.json").read_text())
    old = base["design"]
    patterns = []
    for identity, n, molecular_times in (("fully-linked", 16, (0, 1)),
                                         ("baseline-molecular-only", 240, (0,))):
        acquisitions = []
        for t in (0, 1):
            if t in molecular_times:
                acquisitions.append({
                    "physical_id": f"molecular-assay-{t}", "occasion_index": t,
                    "outputs": [{"coordinate_id": name, "qualified": True}
                                for name in ("molecule_a", "molecule_b")],
                })
            acquisitions.append({
                "physical_id": f"force-reading-{t}", "occasion_index": t,
                "outputs": [{"coordinate_id": "grip_force", "qualified": True}],
            })
        patterns.append({"pattern_id": identity, "n_people": n,
                         "closed_acquisition_inventory": True,
                         "controlled_arm_counts": [n // 2, n // 2],
                         "acquisitions": acquisitions})
    base["contract"] = "anibench.paired-collection-input.v1"
    base["design"] = {
        "question_sha256": old["question_sha256"], "lifecycle": "hypothetical",
        "n_people": 256, "closed_pattern_roster": True, "patterns_are_disjoint": True,
        "homogeneous_reference_across_patterns": True, "acquisition_independent_of_state": True,
        "patterns": patterns, "support": old["support"],
        "metadata": {"name": "Wholly synthetic partial collection",
                     "ethics": "unknown", "publication": "unpublished"},
    }
    return base


if __name__ == "__main__":
    with Path(__file__).with_name("input.json").open("x", encoding="utf-8") as handle:
        json.dump(example(), handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
