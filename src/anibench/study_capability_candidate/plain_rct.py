# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Source-qualified plain randomized two-arm mean-change precision.

A separately named window question, not the old equal-modifier-stratum target.
Actual endpoint time is retained in every canonical task frame.
"""

import copy
import hashlib
import itertools
import math
from pathlib import Path

import numpy as np

from . import compiler as c
from . import multiscale as temporal
from .linked_workload import strict_tri, validate_raw

WINDOWS = [
    ("acute", 7.0, 3.5, 14.0, True),
    ("recovery", 30.0, 14.0, 60.0, False),
    ("medium", 90.0, 60.0, 180.0, False),
    ("annual", 365.0, 180.0, 365.0, False),
]
MODEL = {
    "id": "plain-randomized-change-v4",
    "windows": WINDOWS,
    "covariance": temporal.MODEL,
    "mean": "Four free arm-by-time means per coordinate, no modifier or site imputation",
    "criterion_se": 0.5,
    "endpoint_rule": "Existential precision across qualified common endpoints and admissible repeat subsets, no observed outcomes used; ties closest to center then earlier",
    "subset_rule": "One uniform subset strategy per semantically identical acquisition pattern. Per coordinate use all known error blocks or one unknown-block singleton. Coalesce equivalent patterns before finite Cartesian selection, maximum 512 candidates. Unknown alternatives can enlarge upper bounds but never erase known lower information.",
    "estimand": "Difference between randomized-arm baseline-to-selected-endpoint mean changes",
}


def definition(panel, window, endpoint, factor=1.0):
    m = len(panel["coordinates"])
    L = np.zeros((m, 4 * m))
    for j in range(m):
        L[j, 4 * j : 4 * j + 4] = [1.0, -1.0, -1.0, 1.0]
    limits = np.full(m, (0.5 * factor) ** 2)
    p = copy.deepcopy(panel)
    p["id"] += ".plain-rct-" + window[0]
    task = {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": p["id"] + ".controlled_effects",
        "task_version": MODEL["id"],
        "source_sha256": c.digest(panel),
        "model_sha256": c.digest(
            {
                "model": MODEL,
                "native_panel": panel,
                "window": window,
                "actual_common_endpoint_days": endpoint,
            }
        ),
        "target_population": "Declared selected randomized trial population; pooled arm mean changes, not external transport",
        "estimand": MODEL["estimand"]
        + "; actual shared endpoint "
        + str(endpoint)
        + " days; no personalized interaction claim",
        "horizon": window[0] + " window with actual endpoint " + str(endpoint) + " days",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["reference_normalized_native_mean"] * (4 * m),
        "prior_precision": (np.eye(4 * m) / 1000).tolist(),
        "required_support": [
            {"domain_id": panel["domain"], "role": "perturbation"},
            {"domain_id": "joint_native_resolution", "role": "observation"},
        ],
        "functionals": [
            {
                "functional_id": a["id"] + ".randomized_mean_change",
                "coefficients": L[j].tolist(),
                "unit": "fixed_reference_scale",
                "variance_limit": float(limits[j]),
            }
            for j, a in enumerate(panel["coordinates"])
        ],
    }
    return p, (task, L, limits)


def information(panel, groups, q, endpoint):
    """Exact marginal Gaussian GLS information; subjects remain independent units."""
    m = len(panel["coordinates"])
    J = np.zeros((4 * m, 4 * m))
    unresolved = set()
    used = 0
    if endpoint is None:
        return J, unresolved, used
    ids = [x["id"] for x in panel["coordinates"]]
    for group in groups:
        if group["arm"] not in [0, 1]:
            unresolved.update(e["coordinate"] for e in group["events"])
            continue
        events = list(
            {e["physical_id"]: e for e in group["events"] if e["time"] in [0, endpoint]}.values()
        )
        group_unknown = set()
        selected_events = []
        for coordinate in ids:
            readings = [e for e in events if e["coordinate"] == coordinate]
            known = [e for e in readings if e["session_id"] is not None]
            if len(readings) > 1 and any(e["session_id"] is None for e in readings):
                group_unknown.add(coordinate)
            selected_events.extend(known if known else readings if len(readings) == 1 else [])
        unresolved.update(group_unknown)
        events = selected_events
        if not events:
            continue
        selected = {**group, "events": events}
        H, R, B, metadata = temporal.geometry(panel, selected, q)
        events = metadata["effective_rows"]
        X = np.zeros((len(events), 4 * m))
        for i, event in enumerate(events):
            X[
                i,
                4 * ids.index(event["coordinate"])
                + 2 * group["arm"]
                + int(event["time"] == endpoint),
            ] = 1
        J += group["n"] * c.fisher(X, H @ B @ H.T + R)
        used += group["n"]
    return J, unresolved, used


def information_candidates(panel, groups, q, endpoint):
    """Coherent safe-subset information, invariant to names and pattern splitting.

    This supplies attainable conservative lower witnesses, not an optimal
    allocation of different estimators to otherwise identical people. The
    uniform strategy is fixed before looking at measurements or study names.
    """
    m = len(panel["coordinates"])
    if endpoint is None:
        return [(np.zeros((4 * m, 4 * m)), 0)], set(), 0
    merged = {}
    unresolved = set()
    for group in groups:
        events = list(
            {e["physical_id"]: e for e in group["events"] if e["time"] in [0, endpoint]}.values()
        )
        if group["arm"] not in (0, 1):
            unresolved.update(e["coordinate"] for e in events)
            continue
        signature = []
        for coordinate in sorted(a["id"] for a in panel["coordinates"]):
            rows = [e for e in events if e["coordinate"] == coordinate]
            blocks = {}
            for e in rows:
                if e["session_id"] is not None:
                    blocks.setdefault(e["session_id"], []).append(e["time"])
            known = tuple(sorted(tuple(sorted(times)) for times in blocks.values()))
            unknown = tuple(sorted({e["time"] for e in rows if e["session_id"] is None}))
            if unknown and len(rows) > 1:
                unresolved.add(coordinate)
            if known or unknown:
                signature.append((coordinate, known, unknown))
        if not signature:
            continue
        key = (group["arm"], tuple(signature))
        merged[key] = merged.get(key, 0) + group["n"]
    group_options = []
    for (arm, signature), n in sorted(merged.items()):
        coordinate_options = []
        for coordinate, blocks, unknown in signature:
            options = []
            if blocks:
                options.append(
                    [
                        {
                            "coordinate": coordinate,
                            "time": time,
                            "session_id": f"known-{bi}",
                            "physical_id": f"{coordinate}-{bi}-{ri}",
                        }
                        for bi, times in enumerate(blocks)
                        for ri, time in enumerate(times)
                    ]
                )
            options.extend(
                [
                    {
                        "coordinate": coordinate,
                        "time": time,
                        "session_id": None,
                        "physical_id": coordinate + "-unknown",
                    }
                ]
                for time in unknown
            )
            coordinate_options.append(options)
        count = math.prod(len(options) for options in coordinate_options)
        if count > 512:
            raise ValueError(
                "More than 512 admissible repeat-block subsets; qualify session identities"
            )
        opts = []
        for combination in itertools.product(*coordinate_options):
            selected = {"arm": arm, "n": n, "events": [e for block in combination for e in block]}
            J, _, used = information(panel, [selected], q, endpoint)
            opts.append((J, used))
        group_options.append(opts)
    if math.prod(len(options) for options in group_options) > 512:
        raise ValueError(
            "More than 512 joint admissible repeat-block subsets after coalescing; qualify session identities"
        )
    candidates = []
    for combination in itertools.product(*group_options):
        J = sum((item[0] for item in combination), start=np.zeros((4 * m, 4 * m)))
        candidates.append((J, sum(item[1] for item in combination)))
    return candidates, unresolved, len(merged)


def evaluate_panel(panel, supplied, design, q=1.0, factor=1.0):
    if (
        type(q) not in (int, float)
        or type(factor) not in (int, float)
        or not np.isfinite(q)
        or q <= 0
        or not np.isfinite(factor)
        or factor <= 0
    ):
        raise ValueError(
            "Positive finite numeric q and resolution required; booleans are not numbers"
        )
    frame = supplied.get("time_frame", {})
    gates = [
        {"present": True, "absent": False, "unknown": None}[supplied.get("status", "unknown")],
        supplied.get("operator_qualified"),
        design["gates"].get("measurement_semantics"),
        design["gates"].get("group_linkage_and_disjointness"),
        design["gates"].get("sampling_frame"),
        design["gates"].get("assignment_randomized"),
        design["gates"].get("assignment_consistency_and_followup"),
        True
        if frame.get("origin") == "intervention_assignment"
        else design["gates"].get("baseline_aligned_to_assignment"),
        frame.get("source_qualified"),
    ]
    if design["lifecycle"] == "collected":
        gates.append(design["gates"].get("collection_verified"))
    groups = []
    unresolved = set()
    for group in supplied.get("groups", []):
        timing = strict_tri(group.get("timing_qualified", frame.get("source_qualified")))
        if timing is False:
            continue
        if timing is None:
            unresolved.update(e["coordinate"] for e in group["events"])
            continue
        unresolved.update(e["coordinate"] for e in group["events"] if e["time"] is None)
        groups.append({**group, "events": [e for e in group["events"] if e["time"] is not None]})
    coordinates = supplied.get(
        "coordinate_status", {a["id"]: "unknown" for a in panel["coordinates"]}
    )
    rows = []
    components = []
    for window in WINDOWS:
        name, center, lo, hi, inclusive = window
        times = []
        for arm in [0, 1]:
            times.append(
                {
                    e["time"]
                    for g in groups
                    if g["arm"] == arm
                    for e in g["events"]
                    if (e["time"] >= lo if inclusive else e["time"] > lo) and e["time"] <= hi
                }
            )
        common = times[0] & times[1]
        candidates = []
        for endpoint in sorted(common) if common else [None]:
            alternatives, unknown, pattern_count = information_candidates(
                panel, groups, q, endpoint
            )
            unknown |= unresolved
            unknown |= {e["coordinate"] for g in groups if g["arm"] is None for e in g["events"]}
            upper_status = {
                k: ("unknown" if k in unknown and v != "absent" else v)
                for k, v in coordinates.items()
            }
            p, task = definition(panel, window, endpoint, factor)
            for subset_index, (J, used) in enumerate(alternatives):
                comp = c.canonical(
                    p,
                    "controlled_effects",
                    J,
                    gates,
                    design,
                    c.scenario_name(design, q),
                    {},
                    factor,
                    coordinates,
                    task,
                )
                upper = (
                    c.canonical(
                        p,
                        "controlled_effects",
                        J,
                        gates,
                        design,
                        c.scenario_name(design, q),
                        {},
                        factor,
                        upper_status,
                        task,
                    )
                    if unknown
                    else comp
                )
                if (
                    upper["upper"] + 1e-10 < comp["lower"]
                    or upper["continuous_upper"] + 1e-10 < comp["continuous_lower"]
                ):
                    raise ValueError("Conservative subset bounds are inconsistent")
                components.extend([comp, upper] if unknown else [comp])
                candidates.append(
                    {
                        "actual_endpoint_days": endpoint,
                        "lower_percent": 100 * comp["lower"],
                        "upper_percent": 100 * upper["upper"],
                        "continuous_lower_percent": 100 * comp["continuous_lower"],
                        "continuous_upper_percent": 100 * upper["continuous_upper"],
                        "canonical_receipt_sha256": comp["canonical_receipt_sha256"],
                        "upper_canonical_receipt_sha256": upper["canonical_receipt_sha256"],
                        "contributing_people": used,
                        "subset_index": subset_index,
                        "subset_count": len(alternatives),
                        "coalesced_pattern_count": pattern_count,
                        "information_sha256": c.digest(J.tolist()),
                    }
                )

        def choice(key, candidates=candidates, center=center):
            return max(
                candidates,
                key=lambda row: (
                    row[key],
                    row["continuous_" + key] if not key.startswith("continuous_") else 0,
                    -abs((row["actual_endpoint_days"] or center) - center),
                    -(row["actual_endpoint_days"] or center),
                ),
            )

        low = choice("lower_percent")
        high = choice("upper_percent")
        rows.append(
            {
                "window_id": name,
                "window_center_days": center,
                "window_weight": 0.25,
                "actual_endpoint_days": low["actual_endpoint_days"],
                "upper_bound_endpoint_days": high["actual_endpoint_days"],
                "lower_percent": low["lower_percent"],
                "upper_percent": high["upper_percent"],
                "continuous_lower_percent": choice("continuous_lower_percent")[
                    "continuous_lower_percent"
                ],
                "continuous_upper_percent": choice("continuous_upper_percent")[
                    "continuous_upper_percent"
                ],
                "canonical_receipt_sha256": low["canonical_receipt_sha256"],
                "upper_canonical_receipt_sha256": high["upper_canonical_receipt_sha256"],
                "contributing_people": low["contributing_people"],
                "candidates": candidates,
                "selection": "Existence of a source-qualified shared endpoint and coherent safe subset in this fixed window; native/joint success uses one endpoint and one subset per candidate. Lower and upper may select different candidates; upper is an outer bound, not joint attainability.",
            }
        )
    return {
        "panel_id": panel["id"],
        "domain": panel["domain"],
        "family": "controlled_effects",
        "profile_id": MODEL["id"],
        "parts": rows,
        **{
            key: sum(r[key] / 4 for r in rows)
            for key in [
                "lower_percent",
                "upper_percent",
                "continuous_lower_percent",
                "continuous_upper_percent",
            ]
        },
    }, components


def evaluate(design, scenario_registry=None, factor=1.0):
    validate_raw(design)
    scenarios = c.SCENARIOS if scenario_registry is None else scenario_registry
    if scenarios not in [c.SCENARIOS, {"q0.0625": 0.0625, "q0.25": 0.25, "q1": 1.0, "q2": 2.0}]:
        raise ValueError("Only frozen noise scenarios are admitted")
    calculation = copy.deepcopy(design)
    if scenario_registry is not None:
        calculation["_noise_scenario_registry"] = copy.deepcopy(scenarios)
    output = []
    components = []
    for scenario, q in scenarios.items():
        rows = []
        for panel in c.registry()["panels"]:
            row, parts = evaluate_panel(
                panel,
                calculation["panels"].get(
                    panel["id"], {"status": "unknown", "operator_qualified": None, "groups": []}
                ),
                calculation,
                q,
                factor,
            )
            rows.append(row)
            components.extend(parts)
        domains = []
        for domain in sorted({p["domain"] for p in c.registry()["panels"]}):
            selected = [r for r in rows if r["domain"] == domain]
            domains.append(
                {
                    "domain": domain,
                    **{
                        key: sum(r[key] for r in selected) / len(selected)
                        for key in [
                            "lower_percent",
                            "upper_percent",
                            "continuous_lower_percent",
                            "continuous_upper_percent",
                        ]
                    },
                }
            )
        output.append(
            {
                "scenario_id": scenario,
                "rows": rows,
                "domains": domains,
                **{
                    key: sum(d[key] for d in domains) / len(domains)
                    for key in [
                        "lower_percent",
                        "upper_percent",
                        "continuous_lower_percent",
                        "continuous_upper_percent",
                    ]
                },
            }
        )
    result = {
        "schema": "anibench.plain-randomized-change-result.v1",
        "profile_id": MODEL["id"],
        "scenarios": output,
        "model": MODEL,
        "input_sha256": c.digest(design),
        "manifest_sha256": c.digest(c.registry()),
        "canonical_components_sha256": c.digest(components),
        "implementation_sha256": "sha256:"
        + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Finite conditional selected-trial arm change contrasts at measured common times; no treatment efficacy or whole-study level certificate",
    }
    result["calculation_files"] = {
        name: "sha256:" + hashlib.sha256((Path(c.__file__).parent / name).read_bytes()).hexdigest()
        for name in ["compiler.py", "multiscale.py", "linked_workload.py", "compare_metrics.py"]
    }
    result["result_sha256"] = c.digest(result)
    return result, components
