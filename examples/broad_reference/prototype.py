# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Synthetic broad reference candidate workload using actual AniBench evaluators."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from anibench.causal_v2 import contrast_information
from anibench.finite_suites_v1 import (
    evaluate_finite_suite,
    scientific_frame_sha256,
    suite_sha256,
)
from anibench.finite_tasks_v1 import finite_task_sha256

DOMAINS = {
    "genomic": 16,
    "transcriptomic": 16,
    "proteomic": 16,
    "metabolomic": 16,
    "functional": 4,
    "digital": 4,
    "cognitive": 4,
    "neural": 4,
}
STANDARD = {
    "contract": "anibench.broad-reference-candidate.v1",
    "status": "concrete_candidate_normative_synthetic_not_empirically_calibrated",
    "scope": "Broad collection-layer coverage and finite reference learnability; not saturation of all human biology",
    "domain_dimensions_per_band": DOMAINS,
    "coordinate_authority": "Normative synthetic orthogonal reference coordinates in each named layer. They are NOT independent dimensions inferred from assay counts, actual genes, ANI axes, or validated biological modes.",
    "coordinate_admission": "Actual study adapters must bind a frozen observable catalogue and validated or explicitly assumed operator; platform labels/counts alone do not establish coverage.",
    "model": {
        "measurement_variance_R": 4.0,
        "between_person_variance_B": 1.0,
        "occasion_variance_S": 0.25,
        "prior_precision": 1e-6,
        "units": "squared frozen standardized reference units",
        "repeat_information": "effective_depth=m/(1+(m-1)*rho); copies add zero",
        "population_variance": "(B+S+R/effective_depth)/N",
        "temporal_contrast_variance": "2R/effective_depth for observed occasion changes; no persistent-person claim",
        "cross_domain_covariance": "Only explicit complementary operator task is joint; other target receipts are marginal constraints, never summed into joint information",
    },
    "AB1": {
        "bands": ["base"],
        "required_days": [0, 30],
        "limits": {
            "state": 0.25,
            "population": 0.01,
            "time": 0.5,
            "causal": 0.04,
            "linkage": 0.01,
            "complementarity": 0.25,
        },
        "causal": "One randomized binary input contrast on a standardized response; no treatment benefit required",
    },
    "AB2": {
        "parent": "AB1",
        "retain_all_parent_targets": True,
        "variance_limit_multiplier": 0.25,
        "bands": ["base", "extension"],
        "required_days": [0, 30, 365],
        "interaction_variance_limit": 0.01,
        "causal": "Two crossed randomized inputs with estimable difference-of-differences",
        "neural_extension": "Additional spatial/hemodynamic reference targets require an observation operator; not direct cortical perturbation",
    },
    "optional_extension": "Named neural-causal workload additionally requires cortical assignment, response measurement and matched peripheral control; not a core AB1/AB2 gate",
    "coverage_rule": "All registered marginal variance ceilings and required roles; no simultaneous confidence coverage is claimed",
    "prior_rule": "likelihood_only; prior-only attainment never supplies acquired precision",
    "no_overall_scalar": True,
    "empirical_calibration": None,
    "real_study_scoring_allowed": False,
    "cardinality_authority": "16 and 4 are computational test-coverage conventions: multiple molecular directions and small nonmolecular operator blocks. They do not estimate biological rank or sufficient coverage.",
    "normative_choices": [
        "layers and finite coordinate cardinalities",
        "days/horizons",
        "variance ceilings",
        "noise/heterogeneity workload",
        "causal contrast set",
    ],
    "not_normative_facts": [
        "actual study covariance",
        "actual signal-to-noise",
        "participant overlap",
        "assay independence",
        "physiological equivalence",
    ],
}


def digest(value):
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest()
    )


def make_target(identity, dimension, limit, supports, kind, domain=None, band="base"):
    description = {
        "standard": digest(STANDARD),
        "kind": kind,
        "domain": domain,
        "band": band,
        "dimension": dimension,
    }
    task = {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": identity,
        "task_version": "candidate-1",
        "source_sha256": digest(STANDARD),
        "model_sha256": digest(description),
        "target_population": "Normative homogeneous synthetic reference population; no transport claim",
        "estimand": identity,
        "horizon": "Frozen standard time scope for " + kind,
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["standardized_reference_unit"] * dimension,
        "prior_precision": (np.eye(dimension) * 1e-6).tolist(),
        "required_support": [
            {"domain_id": name, "role": role} for name, role in supports
        ],
        "functionals": [
            {
                "functional_id": f"coordinate-{i}",
                "coefficients": np.eye(dimension)[i].tolist(),
                "unit": "standardized_reference_unit",
                "variance_limit": limit,
            }
            for i in range(dimension)
        ],
    }
    if kind == "interaction":
        task["functionals"] = [
            {
                "functional_id": "difference-of-differences",
                "coefficients": [0.0, 0.0, 2.0],
                "unit": "standardized_reference_unit",
                "variance_limit": limit,
            }
        ]
    return {
        "canonical_id": identity,
        "frame_sha256": scientific_frame_sha256(task),
        "task": task,
    }, description


def profiles():
    for key in (
        "measurement_variance_R",
        "between_person_variance_B",
        "occasion_variance_S",
        "prior_precision",
    ):
        value = STANDARD["model"][key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError("reference model requires finite positive " + key)
    metadata = {}

    def add(profile, identity, dim, limit, supports, kind, domain=None, band="base"):
        target, description = make_target(
            identity, dim, limit, supports, kind, domain, band
        )
        profile["targets"].append(target)
        metadata[identity] = description

    base = {
        "contract": "anibench.finite-suite-profile.v1",
        "profile_id": "AB1.broad-reference.candidate.v1",
        "profile_type": "custom",
        "scope": STANDARD["scope"],
        "tolerance_authority": "Normative variance ceilings, not empirical biological thresholds",
        "calibration_authority": "Synthetic frozen standardized units; model="
        + digest(STANDARD["model"])
        + ". No actual-study calibration.",
        "precision_basis": "likelihood_only",
        "scenario_quantifier": "single_conditional",
        "scenario_ids": ["declared-reference-model"],
        "parent_sha256": None,
        "targets": [],
    }
    for domain, dimension in DOMAINS.items():
        for kind in ["state", "population"] + ([] if domain == "genomic" else ["time"]):
            supports = [(domain, "observation")]
            if kind == "population":
                supports.append(("population_sampling", "observation"))
            if kind == "time":
                supports.append(("day-30-person-linkage", "observation"))
            add(
                base,
                f"{domain}.base.{kind}",
                dimension,
                STANDARD["AB1"]["limits"][kind],
                supports,
                kind,
                domain,
            )
    add(
        base,
        "randomized-input-contrast",
        1,
        0.04,
        [("input-A", "perturbation"), ("response", "observation")],
        "causal",
    )
    add(
        base,
        "population-crossmodal-link",
        1,
        0.01,
        [("linked-people", "observation")],
        "linkage",
    )
    add(
        base,
        "molecular-functional-complementarity",
        2,
        0.25,
        [
            ("metabolomic", "observation"),
            ("functional", "observation"),
            ("linked-people", "observation"),
        ],
        "complementarity",
    )
    harder = copy.deepcopy(base)
    harder["profile_id"] = "AB2.broad-reference.candidate.v1"
    harder["parent_sha256"] = suite_sha256(base)
    for target in harder["targets"]:
        for functional in target["task"]["functionals"]:
            functional["variance_limit"] *= 0.25
    for domain, dimension in DOMAINS.items():
        for kind in ["state", "population"] + ([] if domain == "genomic" else ["time"]):
            supports = [(domain, "observation"), (domain + "-extension", "observation")]
            if domain == "neural":
                supports.append(("spatial-neural-observation", "observation"))
            if kind == "population":
                supports.append(("population_sampling", "observation"))
            if kind == "time":
                supports.append(("day-30-person-linkage", "observation"))
            add(
                harder,
                f"{domain}.extension.{kind}",
                dimension,
                STANDARD["AB1"]["limits"][kind] * 0.25,
                supports,
                kind,
                domain,
                "extension",
            )
        if domain != "genomic":
            for band in ["base", "extension"]:
                supports = [
                    (domain, "observation"),
                    ("day-365-person-linkage", "observation"),
                ]
                if band == "extension":
                    supports.append((domain + "-extension", "observation"))
                if domain == "neural" and band == "extension":
                    supports.append(("spatial-neural-observation", "observation"))
                add(
                    harder,
                    f"{domain}.{band}.annual",
                    dimension,
                    0.125,
                    supports,
                    "annual",
                    domain,
                    band,
                )
    add(
        harder,
        "randomized-input-interaction",
        3,
        0.01,
        [
            ("input-A", "perturbation"),
            ("input-B", "perturbation"),
            ("response", "observation"),
        ],
        "interaction",
    )
    neural = copy.deepcopy(base)
    neural["profile_id"] = "AB1-neural.broad-reference.candidate.v1"
    neural["parent_sha256"] = suite_sha256(base)
    add(
        neural,
        "controlled-cortical-response",
        1,
        0.04,
        [
            ("neural", "observation"),
            ("cortical-assignment", "perturbation"),
            ("matched-peripheral-control", "perturbation"),
        ],
        "neural_causal",
    )
    return {suite_sha256(p): p for p in [base, harder, neural]}, metadata


def witness(level=1):
    return {
        "evidence_type": "hypothetical_reference_design",
        "design_id": f"AB{level}-witness",
        "people": 160 if level == 1 else 2112,
        "linked_people": 160 if level == 1 else 2112,
        "raw_depth": 16 if level == 1 else 64,
        "repeat_correlation": 0.0,
        "days": [0, 30] if level == 1 else [0, 30, 365],
        "assignment": "binary" if level == 1 else "factorial",
        "domains": {d: True for d in DOMAINS},
        "extension_domains": {d: level == 2 for d in DOMAINS},
        "spatial_neural_observation": level == 2,
        "digital_hours": [0, 6, 12, 18],
        "mode_fraction": 1.0,
        "copied_rows": 1,
        "expense": 0.0,
        "cortical_assignment": False,
        "matched_peripheral_control": False,
    }


def state_information(design, domain, dimension):
    m = design["raw_depth"]
    rho = design["repeat_correlation"]
    depth = m / (1 + (m - 1) * rho)
    if domain == "digital":
        hours = np.asarray(sorted(set(design["digital_hours"])), dtype=float)
        if not len(hours):
            return np.zeros((dimension, dimension))
        phi = 2 * np.pi * hours / 24
        h = np.column_stack(
            [
                np.ones(len(phi)),
                np.sqrt(2) * np.cos(phi),
                np.sqrt(2) * np.sin(phi),
                np.cos(2 * phi),
            ]
        )
        gram = h.T @ h / len(hours)
    else:
        gram = np.eye(dimension)
    observed = int(dimension * design["mode_fraction"])
    mask = np.diag([1.0] * observed + [0.0] * (dimension - observed))
    # Copies intentionally do not enter the information calculation. Independent
    # repeats are raw_depth, with their own declared dependence rho.
    return depth / STANDARD["model"]["measurement_variance_R"] * (mask @ gram @ mask)


def evaluate(design, level, registry=None, metadata=None):
    if design.get("evidence_type") != "hypothetical_reference_design":
        raise ValueError(
            "Synthetic reference designs only; actual source adapters are not implemented"
        )
    expected_registry, expected_metadata = profiles()
    if registry is None:
        if metadata is not None:
            raise ValueError("metadata requires a matching frozen registry")
        registry, metadata = expected_registry, expected_metadata
    elif registry != expected_registry or metadata != expected_metadata:
        raise ValueError(
            "stale or altered registry/metadata for the current frozen reference model"
        )
    for key in ["people", "raw_depth", "copied_rows"]:
        if (
            isinstance(design[key], bool)
            or not isinstance(design[key], int)
            or design[key] < 1
        ):
            raise ValueError(key)
    if design["linked_people"] is not None and (
        isinstance(design["linked_people"], bool)
        or not isinstance(design["linked_people"], int)
        or not 0 <= design["linked_people"] <= design["people"]
    ):
        raise ValueError("linked_people")
    for key in ["repeat_correlation", "mode_fraction", "expense"]:
        if isinstance(design[key], bool) or not math.isfinite(design[key]):
            raise ValueError(key)
    if (
        not 0 <= design["repeat_correlation"] < 1
        or not 0 <= design["mode_fraction"] <= 1
        or design["expense"] < 0
    ):
        raise ValueError("range")
    for values in [design["domains"], design["extension_domains"]]:
        if set(values) != set(DOMAINS) or any(
            x is not None and type(x) is not bool for x in values.values()
        ):
            raise ValueError("domain support")
    if not isinstance(design["digital_hours"], list) or any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
        for x in design["digital_hours"]
    ):
        raise ValueError("digital_hours")
    for key in ["cortical_assignment", "matched_peripheral_control"]:
        if design[key] is not None and type(design[key]) is not bool:
            raise ValueError(key)
    if design["assignment"] not in ["binary", "factorial", "redundant", "none"]:
        raise ValueError("assignment")
    if (
        design["spatial_neural_observation"] is not None
        and type(design["spatial_neural_observation"]) is not bool
    ):
        raise ValueError("spatial support")
    days = None if design["days"] is None else set(design["days"])
    if days is not None and any(
        isinstance(x, bool)
        or not isinstance(x, (float, int))
        or not math.isfinite(x)
        or x < 0
        for x in days
    ):
        raise ValueError("days")
    m = design["raw_depth"]
    d = m / (1 + (m - 1) * design["repeat_correlation"])
    v = (
        STANDARD["model"]["between_person_variance_B"]
        + STANDARD["model"]["occasion_variance_S"]
        + STANDARD["model"]["measurement_variance_R"] / d
    )
    arms = {
        "binary": [[-1, 0, 0], [1, 0, 0]],
        "factorial": [[-1, -1, 1], [-1, 1, -1], [1, -1, -1], [1, 1, 1]],
        "redundant": [[1, 1, 1]] * 4,
        "none": [[0, 0, 0]],
    }[design["assignment"]]
    if design["people"] % len(arms):
        raise ValueError("Balanced reference arms need integer counts")
    causal = np.asarray(
        contrast_information(
            arms, observation_precision=[design["people"] / len(arms) / v] * len(arms)
        ).information_matrix
    )
    profile = next(
        p for p in registry.values() if p["profile_id"].startswith(f"AB{level}.")
    )
    provenance = {
        "contract": "anibench.synthetic-design-provenance.v1",
        "standard_sha256": digest(STANDARD),
        "design": design,
        "script_sha256": "sha256:"
        + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    binding = {
        "design_id": design["design_id"],
        "design_source_sha256": digest(provenance),
    }
    rows = []
    for target in profile["targets"]:
        identity = target["canonical_id"]
        task = target["task"]
        description = metadata[identity]
        kind = description["kind"]
        domain = description["domain"]
        band = description["band"]
        dimension = description["dimension"]
        support = {name: val for name, val in design["domains"].items()}
        support.update(
            {
                name + "-extension": val
                for name, val in design["extension_domains"].items()
            }
        )
        support.update(
            {
                "population_sampling": True,
                "day-30-person-linkage": None if days is None else {0, 30} <= days,
                "day-365-person-linkage": None if days is None else {0, 365} <= days,
                "input-A": design["assignment"] in ["binary", "factorial"],
                "input-B": design["assignment"] == "factorial",
                "response": True,
                "linked-people": None
                if design["linked_people"] is None
                else design["linked_people"] > 0,
                "spatial-neural-observation": design["spatial_neural_observation"],
                "cortical-assignment": design["cortical_assignment"],
                "matched-peripheral-control": design["matched_peripheral_control"],
            }
        )
        required = [
            dict(r, supported=support[r["domain_id"]]) for r in task["required_support"]
        ]
        if any(r["supported"] is None for r in required):
            geometry = None
        else:
            if kind in ["state", "population", "time", "annual"]:
                info = state_information(design, domain, dimension)
                if kind == "population":
                    # Identified marginal reference states have B+S as genuine between-person
                    # variability; deep repeats do not manufacture independent people.
                    eig, u = np.linalg.eigh(info)
                    covnoise = np.divide(
                        1, eig, out=np.full_like(eig, np.inf), where=eig > 1e-10
                    )
                    precision = np.divide(
                        design["people"],
                        STANDARD["model"]["between_person_variance_B"]
                        + STANDARD["model"]["occasion_variance_S"]
                        + covnoise,
                    )
                    info = (u * precision) @ u.T
                elif kind in ["time", "annual"]:
                    info /= 2
                if support[domain] is False or (
                    band == "extension" and support[domain + "-extension"] is False
                ):
                    info = np.zeros_like(info)
            elif kind in ["causal", "neural_causal"]:
                info = causal[:1, :1]
            elif kind == "interaction":
                info = causal
            elif kind == "linkage":
                info = np.array([[design["linked_people"] / v]])
            else:
                h = []
                if support["metabolomic"]:
                    h.append([1.0, 1.0])
                if support["functional"]:
                    h.append([1.0, -1.0])
                matrix = np.asarray(h).reshape(-1, 2)
                info = (
                    d
                    / STANDARD["model"]["measurement_variance_R"]
                    * (matrix.T @ matrix)
                )
            geometry = {
                "model_sha256": task["model_sha256"],
                "information_matrix": info.tolist(),
            }
        req = {
            "contract": "anibench.finite-task-request.v1",
            "task": task,
            "task_sha256": finite_task_sha256(task),
            "evidence": {
                "identifiability": True,
                "collection_verified": None,
                "support": required,
            },
            "geometry": geometry,
        }
        rows.append(
            {**binding, "canonical_id": identity, "known_absent": False, "request": req}
        )
    request = {
        **binding,
        "contract": "anibench.finite-suite-request.v1",
        "profile_sha256": suite_sha256(profile),
        "scenarios": [
            {**binding, "scenario_id": "declared-reference-model", "targets": rows}
        ],
    }
    receipt = evaluate_finite_suite(request, trusted_profiles=registry)
    return {"provenance": provenance, "request": request, "receipt": receipt}


def summary(run):
    targets = run["receipt"]["scenarios"][0]["targets"]
    return {
        "design_id": run["receipt"]["design_id"],
        "attainment": run["receipt"]["attainment"],
        "failed": [
            t["canonical_id"] for t in targets if t["attainment"] == "not_attained"
        ],
        "unknown": [t["canonical_id"] for t in targets if t["attainment"] == "unknown"],
        "target_count": len(targets),
        "functional_count": sum(len(t["task_receipt"]["functionals"]) for t in targets),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    for name, default in [("R", 4.0), ("B", 1.0), ("S", 0.25)]:
        parser.add_argument("--" + name, type=float, default=default)
    args = parser.parse_args()
    for name, key in [
        ("R", "measurement_variance_R"),
        ("B", "between_person_variance_B"),
        ("S", "occasion_variance_S"),
    ]:
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(name)
        STANDARD["model"][key] = value
    args.out.mkdir(parents=True, exist_ok=False)
    registry, metadata = profiles()
    (args.out / "standard.json").write_text(json.dumps(STANDARD, indent=2) + "\n")
    (args.out / "trusted-profiles.json").write_text(
        json.dumps(registry, indent=2) + "\n"
    )
    designs = [(witness(1), 1), (witness(1), 2), (witness(2), 1), (witness(2), 2)]
    for label, updates in [
        (
            "two-people-extreme-depth",
            {
                "people": 2,
                "linked_people": 2,
                "raw_depth": 1000000,
                "expense": 100000000,
            },
        ),
        ("huge-shallow", {"people": 100000, "linked_people": 100000, "raw_depth": 1}),
        ("correlated-oversampling", {"raw_depth": 1000000, "repeat_correlation": 0.99}),
        ("redundant-arms", {"assignment": "redundant"}),
        ("unlinked", {"linked_people": 0}),
        ("daily-alias", {"digital_hours": [0, 24, 48, 72]}),
    ]:
        d = witness(1)
        d.update(updates)
        d["design_id"] = label
        designs.append((d, 1))
    for level, updates in [
        (1, {"domains": dict(witness(1)["domains"], neural=False)}),
        (1, {"domains": dict(witness(1)["domains"], neural=None)}),
        ("1-neural", {}),
        ("1-neural", {"cortical_assignment": True, "matched_peripheral_control": True}),
    ]:
        d = witness(1)
        d.update(updates)
        d["design_id"] = "role-case-" + str(len(designs))
        designs.append((d, level))
    result = []
    for index, (design, level) in enumerate(designs):
        run = evaluate(design, level, registry, metadata)
        row = summary(run)
        row["level"] = level
        result.append(row)
        (args.out / f"case-{index:02d}.json").write_text(
            json.dumps(run, indent=2) + "\n"
        )
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
