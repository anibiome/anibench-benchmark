# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Replay the synthetic reference ladder; default output is compact aggregate data."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import prototype as p
from catalogue import rows as coordinates


def write_json(directory, name, value):
    with (directory / name).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def cases():
    designs = [
        (p.witness(1), 1),
        (p.witness(1), 2),
        (p.witness(2), 1),
        (p.witness(2), 2),
    ]
    for label, changes in [
        (
            "two-people-extreme-depth",
            {
                "people": 2,
                "linked_people": 2,
                "raw_depth": 1_000_000,
                "expense": 100_000_000,
            },
        ),
        ("huge-shallow", {"people": 100_000, "linked_people": 100_000, "raw_depth": 1}),
        (
            "correlated-oversampling",
            {"raw_depth": 1_000_000, "repeat_correlation": 0.99},
        ),
        ("redundant-arms", {"assignment": "redundant"}),
        ("unlinked", {"linked_people": 0}),
        ("daily-alias", {"digital_hours": [0, 24, 48, 72]}),
        ("neural-absent", {"domains": {**p.witness(1)["domains"], "neural": False}}),
        ("neural-unknown", {"domains": {**p.witness(1)["domains"], "neural": None}}),
    ]:
        design = p.witness(1)
        design.update(changes, design_id=label)
        designs.append((design, 1))
    for label, present in [
        ("observation-without-cortical-assignment", False),
        ("controlled-cortical-assignment", True),
    ]:
        design = p.witness(1)
        design.update(
            design_id=label,
            cortical_assignment=present,
            matched_peripheral_control=present,
        )
        designs.append((design, "1-neural"))
    return designs


def compact_profiles(registry):
    return [
        {
            "profile_sha256": key,
            "profile_id": value["profile_id"],
            "profile_type": value["profile_type"],
            "parent_sha256": value["parent_sha256"],
            "precision_basis": value["precision_basis"],
            "scope": value["scope"],
            "scenario_ids": value["scenario_ids"],
            "targets": [
                {
                    "canonical_id": t["canonical_id"],
                    "frame_sha256": t["frame_sha256"],
                    "task_sha256": p.finite_task_sha256(t["task"]),
                    "functional_count": len(t["task"]["functionals"]),
                    "variance_limits": sorted(
                        {f["variance_limit"] for f in t["task"]["functionals"]}
                    ),
                }
                for t in value["targets"]
            ],
        }
        for key, value in registry.items()
    ]


def chart_row(design, level, run):
    model = p.STANDARD["model"]
    d = design["raw_depth"] / (
        1 + (design["raw_depth"] - 1) * design["repeat_correlation"]
    )
    variance = (
        model["between_person_variance_B"]
        + model["occasion_variance_S"]
        + model["measurement_variance_R"] / d
    )
    return {
        **p.summary(run),
        "level": str(level),
        "people": design["people"],
        "depth_per_coordinate_per_occasion": design["raw_depth"],
        "effective_depth": d,
        "visits_days": design["days"],
        "assignment": design["assignment"],
        "assignment_groups": {"binary": 2, "factorial": 4, "redundant": 4, "none": 1}[
            design["assignment"]
        ],
        "linked_people": design["linked_people"],
        "repeat_correlation": design["repeat_correlation"],
        "model": {
            k: model[k]
            for k in [
                "measurement_variance_R",
                "between_person_variance_B",
                "occasion_variance_S",
            ]
        },
        "reference_identity_operator_variance": model["measurement_variance_R"] / d,
        "reference_population_variance": variance / design["people"],
        "profile_sha256": run["request"]["profile_sha256"],
        "design_source_sha256": run["request"]["design_source_sha256"],
    }


def replay(output, save_receipts=False):
    output.mkdir(parents=True, exist_ok=False)
    registry, metadata = p.profiles()
    write_json(output, "standard.json", p.STANDARD)
    write_json(output, "profile-declarations.json", compact_profiles(registry))
    write_json(
        output,
        "coordinate_catalogue.json",
        {
            "contract": "anibench.synthetic-coordinate-catalogue.v1",
            "coordinates": coordinates,
        },
    )
    baseline = copy.deepcopy(p.STANDARD["model"])
    examples = []
    sensitivity = []
    for index, (design, level) in enumerate(cases()):
        run = p.evaluate(design, level, registry, metadata)
        examples.append(chart_row(design, level, run))
        if save_receipts:
            write_json(output, f"case-{index:02d}.json", run)
    try:
        for r, b, s, rho in [
            (4.0, 1.0, 0.25, 0.0),
            (8.0, 1.0, 0.25, 0.0),
            (4.0, 2.0, 0.25, 0.0),
            (4.0, 1.0, 1.0, 0.0),
            (4.0, 1.0, 0.25, 0.1),
        ]:
            p.STANDARD["model"].update(
                measurement_variance_R=r,
                between_person_variance_B=b,
                occasion_variance_S=s,
            )
            frozen_registry, frozen_metadata = p.profiles()
            for level in [1, 2]:
                design = p.witness(level)
                design["repeat_correlation"] = rho
                run = p.evaluate(design, level, frozen_registry, frozen_metadata)
                sensitivity.append(chart_row(design, level, run))
                if save_receipts:
                    write_json(output, f"sensitivity-{len(sensitivity):02d}.json", run)
    finally:
        p.STANDARD["model"].clear()
        p.STANDARD["model"].update(baseline)
    result = {
        "contract": "anibench.broad-reference-figure-data.v1",
        "scope": "Conditional synthetic reference workload; not biological sufficiency, population transport, or any named-study rating.",
        "sensitivity_rule": "Noise changes define alternative frozen profiles, not same-frame study comparisons.",
        "operator_warning": "Variance columns are identity-operator reference values; actual digital aliasing, missing roles or assignment rank can fail despite these reference numbers.",
        "examples": examples,
        "sensitivity": sensitivity,
    }
    write_json(output, "figure-data.json", result)
    write_json(
        output,
        "replay-bindings.json",
        {
            "script_sha256": {
                name: "sha256:"
                + hashlib.sha256(
                    Path(__file__).with_name(name).read_bytes()
                ).hexdigest()
                for name in ["prototype.py", "catalogue.py", "replay.py"]
            },
            "evaluator_bindings": run["receipt"].get(
                "implementation", run["receipt"].get("implementation_sha256", None)
            ),
            "note": "Full evaluator implementation/runtime bindings are available in regenerated receipts with --receipts.",
        },
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--receipts", action="store_true")
    args = parser.parse_args()
    result = replay(args.out, args.receipts)
    print(
        json.dumps(
            {
                "examples": len(result["examples"]),
                "sensitivity_cases": len(result["sensitivity"]),
            }
        )
    )
