# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Versioned reference-process prediction, distinct from exact nodal identification.

No outcomes are required. Dates are never rounded. The fixed population reference
is explicit: both posterior precision and data-induced uncertainty reduction must
pass. This module does not replace or modify the exact-nodal compiler.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

from anibench.finite_suites_v1 import evaluate_finite_suite, scientific_frame_sha256, suite_sha256
from anibench.finite_tasks_v1 import finite_task_sha256

from . import compiler as c
from . import linked_workload as linked
from . import multiscale as temporal

VERSION = "reference-process-temporal-prediction-v5"
COMMON_NOISE_GRID = {"q0.0625": 0.0625, "q0.25": 0.25, "q1": 1.0, "q2": 2.0}
REGISTERED_ALPHA = (0.25, 0.5, 0.75)
TOLERANCE = 1e-10


def _strict_number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(label + " must be a finite number")
    return float(value)


def _worst_ratio(covariance, reference):
    """Generalized covariance order, with no ridge or eigenvalue clipping."""
    root = np.linalg.cholesky(reference)
    left = np.linalg.solve(root, covariance)
    whitened = np.linalg.solve(root, left.T).T
    return float(np.linalg.eigvalsh((whitened + whitened.T) / 2)[-1])


def _scenario_registry(value):
    """Admit only exact registered names and numeric values, never bool aliases."""
    if value is None:
        return copy.deepcopy(c.SCENARIOS)
    if not isinstance(value, dict) or any(
        not isinstance(name, str) or type(q) not in (int, float) or not math.isfinite(q)
        for name, q in value.items()
    ):
        raise ValueError("Scenario registry must be an exact registered numeric mapping")
    if value != c.SCENARIOS and value != COMMON_NOISE_GRID:
        raise ValueError("Only the normative q1/q2 or frozen common-noise grid is admitted")
    return copy.deepcopy(value)


def _fixed_model(panel, alpha, scenarios):
    return {
        "id": VERSION,
        "panel_sha256": c.digest(panel),
        "nodes_days": temporal.KNOTS,
        "timescales_days": [7.0, 30.0, 365.0],
        "covariance": "B=C tensor K; C=.75I+.25ones; K=4ones+sum baseline-centered OU kernels",
        "observation": "Actual elapsed days, piecewise-linear interpolation of the fixed nodal process; no date rounding",
        "noise": "q(.75I+.25ZZT); exact registered scenario multiplier scales measurement error only, within-coordinate session error blocks",
        "measurement_noise_scenarios": copy.deepcopy(scenarios),
        "precision_basis": "posterior_total with explicit fixed reference baseline",
        "data_requirement": "Vposterior <= alpha Vbaseline in PSD order for joint target; native variance ratio for scalar target",
        "alpha": alpha,
        "selection": "Best supported conditional precision among source-admissible subsets; each coordinate uses all known error blocks or one unknown-block reading. No physical-name-based selection. Unknown covariance remains an outer bound.",
        "alpha_authority": "Registered uncertainty-reduction convention; default .5, sensitivity .25/.75; not empirical calibration",
    }


def _selection_candidates(panel_input, group):
    """Enumerate admissible subsets without assuming unknown repeat covariance.

    For each coordinate, either use all readings whose error-block identities are
    known, or one marginally valid reading with unknown block identity. Taking
    the Cartesian product permits cross-coordinate combinations because the
    registered measurement model has independent errors across coordinates.
    """
    anchor = panel_input.get("time_frame", {}).get("source_qualified")
    linked.strict_tri(anchor)
    if group is None:
        # Omitted roster geometry is unresolved, not a verified empty record.
        # The global source gate still dominates any optimistic upper bound.
        return [[]], True, anchor
    local = group.get("timing_qualified", anchor)
    linked.strict_tri(anchor)
    linked.strict_tri(local)
    timing = c.tri([anchor, local])
    if timing is False:
        return [[]], False, False
    events = list({e["physical_id"]: e for e in group["events"]}.values())
    if timing is None:
        return [[]], bool(events), None
    unresolved = any(e["time"] is None for e in events)
    usable = [e for e in events if e["time"] is not None and 0 <= e["time"] <= 365]
    choices = []
    for coordinate in sorted({e["coordinate"] for e in usable}):
        rows = [e for e in usable if e["coordinate"] == coordinate]
        known = [e for e in rows if e["session_id"] is not None]
        unknown = [e for e in rows if e["session_id"] is None]
        if unknown and len(rows) > 1:
            unresolved = True
        options = [known] if known else []
        # Equal-time unknown-block singleton readings give the same marginal
        # geometry; their labels cannot change a candidate's numeric content.
        unique_times = {}
        for event in unknown:
            unique_times.setdefault(event["time"], event)
        options.extend([[unique_times[t]] for t in sorted(unique_times)])
        if options:
            choices.append(options)
    count = math.prod(len(options) for options in choices)
    if count > 512:
        raise ValueError(
            "More than 512 admissible repeat-block subsets; provide qualified session identities before evaluating this uncertain pattern"
        )
    candidates = [
        [event for block in combination for event in block]
        for combination in itertools.product(*choices)
    ]
    return candidates, unresolved, timing


def compile_group(
    panel, group, q=1.0, factor=1.0, alpha=0.5, *, horizon, design, scenario_registry=None
):
    """Choose a conservative attainable bound without arbitrary acquisition IDs.

    Unknown error-block relationships are never imputed. All admissible subsets
    are retained up to the declared computation limit; exceeding it raises an
    explicit missing-contract error rather than silently dropping candidates.
    """
    scenarios = _scenario_registry(scenario_registry)
    q = _strict_number(q, "q")
    c.scenario_name({"_noise_scenario_registry": scenarios}, q)
    linked.validate_raw(design)
    supplied = design["panels"].get(panel["id"], {"status": "unknown", "operator_qualified": None})
    if group is not None and not any(group == existing for existing in supplied.get("groups", [])):
        raise ValueError("Acquisition pattern is not bound to the supplied study input")
    candidates, unresolved, timing = _selection_candidates(supplied, group)
    best_lower = None
    best_upper = None
    summaries = []
    for index, events in enumerate(candidates):
        result, components = _compile_selected(
            panel,
            group,
            events,
            unresolved,
            timing,
            q,
            factor,
            alpha,
            horizon=horizon,
            design=design,
            scenario_registry=scenarios,
        )
        quality = (
            result["lower_percent"],
            -float(np.trace(result["observed_subset_posterior_target_covariance"])),
        )
        summaries.append(
            {
                "index": index,
                "lower_percent": result["lower_percent"],
                "upper_percent": result["upper_percent"],
                "information_sha256": result["observed_subset_information_sha256"],
                "selected_readings": len(events),
            }
        )
        if best_lower is None or quality > best_lower[0]:
            best_lower = (quality, index, result, components)
        if best_upper is None or result["upper_percent"] > best_upper[0]:
            best_upper = (result["upper_percent"], index, result, components)
    _, lower_index, result, lower_components = best_lower
    _, upper_index, upper_result, upper_components = best_upper
    components = {"lower": lower_components["lower"], "upper": upper_components["upper"]}
    result["upper_percent"] = upper_result["upper_percent"]
    result["target_outcomes"]["upper"] = upper_result["target_outcomes"]["upper"]
    result["upper_canonical_receipt_sha256"] = upper_result["upper_canonical_receipt_sha256"]
    result["components_sha256"] = c.digest(components)
    result["admissible_subset_selection"] = {
        "candidate_count": len(candidates),
        "lower_candidate": lower_index,
        "upper_candidate": upper_index,
        "criterion": "Maximum fixed weighted attainment, then minimum target covariance trace; deterministic semantic candidate order breaks remaining exact ties. No observed outcome or physical name is a selection variable.",
        "candidates": summaries,
    }
    result.pop("result_sha256", None)
    result["result_sha256"] = c.digest(result)
    return result, components


def _compile_selected(
    panel,
    group,
    known,
    unresolved_acquisition,
    timing,
    q=1.0,
    factor=1.0,
    alpha=0.5,
    *,
    horizon,
    design,
    scenario_registry=None,
):
    """Compile one existing aggregate pattern into canonical prediction receipts.

    `panel` must exactly equal a frozen registry panel. `group`, when supplied,
    must exactly match a pattern in `design`; None represents an unobserved roster
    pattern. The caller retains full-roster weighting. This function does not
    certify a whole study or any AB1/AB2 reference.
    """
    q = _strict_number(q, "q")
    factor = _strict_number(factor, "factor")
    alpha = _strict_number(alpha, "alpha")
    horizon = _strict_number(horizon, "horizon")
    scenarios = _scenario_registry(scenario_registry)
    scenario = c.scenario_name({"_noise_scenario_registry": scenarios}, q)
    if alpha not in REGISTERED_ALPHA or horizon not in temporal.TIMES or factor <= 0:
        raise ValueError(
            "Unregistered noise, uncertainty-reduction or horizon setting; factor must be positive"
        )
    linked.validate_raw(design)
    registered = {p["id"]: p for p in c.registry()["panels"]}
    if (
        not isinstance(panel, dict)
        or panel.get("id") not in registered
        or panel != registered[panel["id"]]
    ):
        raise ValueError("Panel differs from frozen native registry")
    supplied = design["panels"].get(panel["id"], {"status": "unknown", "operator_qualified": None})
    if group is not None and not any(group == existing for existing in supplied.get("groups", [])):
        raise ValueError("Acquisition pattern is not bound to the supplied study input")
    skeleton = {"group_id": "unobserved" if group is None else group["group_id"], "events": known}
    H, R, B, geometry_diagnostics = temporal.geometry(panel, skeleton, q)
    _, (_, L, limits) = temporal.definition(panel, horizon, factor)
    V0 = L @ B @ L.T
    J = c.fisher(H, R)
    prior_precision = np.linalg.solve(B, np.eye(len(B)))
    posterior = np.linalg.solve(prior_precision + J, np.eye(len(B)))
    V1 = L @ posterior @ L.T
    V0 = (V0 + V0.T) / 2
    V1 = (V1 + V1.T) / 2
    # A numerical or model violation is rejected, never repaired with a ridge.
    np.linalg.cholesky(B)
    np.linalg.cholesky(V0)
    if np.linalg.eigvalsh(V0 - V1).min() < -TOLERANCE * max(1.0, float(np.linalg.norm(V0, 2))):
        raise ValueError("Posterior covariance violates reference data monotonicity")
    native_ratios = np.diag(V1) / np.diag(V0)
    joint_ratio = _worst_ratio(V1, V0)
    absolute_ratio = _worst_ratio(V1, np.diag(limits))
    common = [
        {"present": True, "absent": False, "unknown": None}[supplied["status"]],
        supplied.get("operator_qualified"),
        design["gates"].get("measurement_semantics"),
        design["gates"].get("group_linkage_and_disjointness"),
        supplied.get("time_frame", {}).get("source_qualified"),
        timing is not False,
    ]
    if design["lifecycle"] == "collected":
        common.append(design["gates"].get("collection_verified"))
    status = supplied.get("coordinate_status", {a["id"]: "unknown" for a in panel["coordinates"]})
    source_support = c.tri(common)
    model = _fixed_model(panel, alpha, scenarios)
    family_id = panel["id"] + ".horizon-" + str(int(horizon)) + "." + VERSION
    base = {
        "contract": "anibench.finite-task-definition.v1",
        "task_version": VERSION,
        "source_sha256": c.digest(panel),
        "model_sha256": c.digest(model),
        "target_population": "Declared selected cohort; fixed common Gaussian process, not empirically calibrated biology",
        "estimand": "Conditional prediction of native endpoint change and midpoint departure; actual observation dates retained",
        "horizon": str(horizon) + " absolute elapsed days from source-qualified baseline",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["fixed_reference_native_scale"] * len(B),
        "prior_precision": prior_precision.tolist(),
    }
    definitions = [(f"native-{i}", [i], False, 1) for i in range(len(L))]
    definitions.append(("joint", list(range(len(L))), True, len(L)))
    profiles = []
    requests = {"lower": [], "upper": []}
    weights = []
    for suffix, indices, joint, weight in definitions:
        identity = family_id + "." + suffix
        task = copy.deepcopy(base)
        task["task_id"] = identity
        task["estimand"] += (
            "; all-direction joint resolution and data reduction"
            if joint
            else "; " + str(indices[0])
        )
        task["functionals"] = [
            {
                "functional_id": panel["coordinates"][i // 2]["id"]
                + (".endpoint_change" if i % 2 == 0 else ".midpoint_departure"),
                "coefficients": L[i].tolist(),
                "unit": "fixed_reference_native_scale",
                "variance_limit": float(limits[i]),
            }
            for i in indices
        ]
        task["required_support"] = [
            {"domain_id": panel["domain"], "role": "observation"},
            {"domain_id": "registered_reference_uncertainty_reduction", "role": "observation"},
        ]
        if joint:
            task["required_support"].append(
                {"domain_id": "joint_native_resolution", "role": "observation"}
            )
        profiles.append(
            {"canonical_id": identity, "frame_sha256": scientific_frame_sha256(task), "task": task}
        )
        weights.append({"canonical_id": identity, "weight": weight})
        coordinate_gate = c.tri(
            [
                {"present": True, "absent": False, "unknown": None}[
                    status[panel["coordinates"][i // 2]["id"]]
                ]
                for i in indices
            ]
        )
        qualified = c.tri([source_support, coordinate_gate])
        data_pass = bool(
            (joint_ratio if joint else native_ratios[indices[0]]) <= alpha * (1 + TOLERANCE)
        )
        for bound in ("lower", "upper"):
            unknown_upper = bound == "upper" and (unresolved_acquisition or qualified is None)
            support = [{**task["required_support"][0], "supported": qualified}]
            support.append(
                {**task["required_support"][1], "supported": None if unknown_upper else data_pass}
            )
            if joint:
                support.append(
                    {
                        **task["required_support"][2],
                        "supported": None
                        if unknown_upper
                        else bool(absolute_ratio <= 1 + TOLERANCE),
                    }
                )
            request = {
                "contract": "anibench.finite-task-request.v1",
                "task": task,
                "task_sha256": finite_task_sha256(task),
                "evidence": {
                    "identifiability": True,
                    "collection_verified": None,
                    "support": support,
                },
                "geometry": None
                if unknown_upper
                else {
                    "model_sha256": task["model_sha256"],
                    "information_matrix": ((J + J.T) / 2).tolist(),
                },
            }
            requests[bound].append(
                {
                    "canonical_id": identity,
                    "known_absent": False,
                    "request": request,
                    "design_id": design["design_id"],
                    "design_source_sha256": design["source_sha256"],
                }
            )
    profile = {
        "contract": "anibench.finite-suite-profile.v1",
        "profile_id": family_id
        + ".alpha-"
        + str(alpha)
        + ".factor-"
        + str(factor)
        + "."
        + scenario,
        "profile_type": "normative",
        "scope": "Versioned finite conditional reference-process prediction; not exact nodal likelihood identification or all biology",
        "tolerance_authority": "Native precision convention plus registered fractional reference uncertainty reduction",
        "calibration_authority": "Fixed Gaussian process reference; not empirical instrument or biological calibration",
        "precision_basis": "posterior_total",
        "scenario_quantifier": "single_conditional",
        "scenario_ids": [scenario],
        "parent_sha256": None,
        "targets": profiles,
    }
    components = {}
    binding = {"design_id": design["design_id"], "design_source_sha256": design["source_sha256"]}
    for bound in ("lower", "upper"):
        request = {
            "contract": "anibench.finite-suite-request.v1",
            **binding,
            "profile_sha256": suite_sha256(profile),
            "scenarios": [{"scenario_id": scenario, **binding, "targets": requests[bound]}],
        }
        receipt = evaluate_finite_suite(request, trusted_profiles={suite_sha256(profile): profile})
        components[bound] = {"profile": profile, "request": request, "receipt": receipt}
    # Explicit conditional-prediction workload adapter. It does not call or relax
    # benchmark_v1's acquired-information/likelihood-only contract.
    outcomes = {
        bound: {
            row["canonical_id"]: row["attainment"]
            for row in component["receipt"]["scenarios"][0]["targets"]
        }
        for bound, component in components.items()
    }
    total = sum(Fraction(row["weight"]) for row in weights)
    lower = float(
        100
        * sum(
            Fraction(row["weight"])
            for row in weights
            if outcomes["lower"][row["canonical_id"]] == "attained"
        )
        / total
    )
    upper = float(
        100
        * sum(
            Fraction(row["weight"])
            for row in weights
            if outcomes["upper"][row["canonical_id"]] != "not_attained"
        )
        / total
    )
    if upper + TOLERANCE < lower:
        raise ValueError("Conditional prediction bounds are inconsistent")
    result = {
        "schema": "anibench.reference-process-prediction.v1",
        "model": model,
        "model_sha256": c.digest(model),
        "source_input_sha256": c.digest(design),
        "pattern_sha256": c.digest(group),
        "panel_sha256": c.digest(panel),
        "q": q,
        "scenario_id": scenario,
        "measurement_noise_scenarios": scenarios,
        "factor": factor,
        "alpha": alpha,
        "horizon_days": horizon,
        "lower_percent": lower,
        "upper_percent": upper,
        "percentage_semantics": "Fixed weighted fraction of registered conditional-prediction targets meeting BOTH posterior precision and data-induced uncertainty reduction; not acquired-information percentage",
        "target_weights": weights,
        "target_outcomes": outcomes,
        "reference_baseline_target_covariance": V0.tolist(),
        "observed_subset_posterior_target_covariance": V1.tolist(),
        "reference_prior_covariance_sha256": c.digest(B.tolist()),
        "observed_subset_information_sha256": c.digest(J.tolist()),
        "native_posterior_to_baseline_ratios": native_ratios.tolist(),
        "joint_posterior_to_baseline_ratio": joint_ratio,
        "joint_absolute_variance_ratio": absolute_ratio,
        "unresolved_acquisition": unresolved_acquisition,
        "known_subset_geometry": geometry_diagnostics,
        "selected_physical_readings": len(known),
        "lower_canonical_receipt_sha256": suite_sha256(components["lower"]["receipt"]),
        "upper_canonical_receipt_sha256": suite_sha256(components["upper"]["receipt"]),
        "components_sha256": c.digest(components),
        "implementation_sha256": "sha256:"
        + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dependency_implementation_sha256": {
            name: "sha256:" + hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name, module in [
                ("compiler", c),
                ("linked_workload", linked),
                ("multiscale", temporal),
            ]
        },
        "limits": [
            "Fixed-process conditional prediction, not likelihood-only trajectory identification.",
            "Unresolved acquisition upper bounds are conservative outer bounds, not attainability certificates.",
            "No outcomes, caller-selected biological prior or rounded observation dates are used.",
            "Standalone group/horizon component; caller must preserve full-roster and fixed domain/horizon weights.",
        ],
    }
    result["result_sha256"] = c.digest(result)
    return result, components
