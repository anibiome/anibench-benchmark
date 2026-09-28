# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Finite absolute-time contrast workload with ONE shared nodal generative model.
No per-study time rescaling, fitted biological covariance, or arbitrary trajectory claim.
"""

import copy
import math
from pathlib import Path

import numpy as np

from . import compiler as c
from .compare_metrics import continuous

BASE = Path(__file__).parent
TIMES = [7.0, 30.0, 90.0, 365.0]
KNOTS = sorted(set([0.0] + TIMES + [t / 2 for t in TIMES]))
K = len(KNOTS)
MODEL = {
    "id": "fixed-absolute-time-nodal-v0",
    "knots_days": KNOTS,
    "timescale_days": TIMES,
    "basis": "Piecewise-linear interpolation of fixed nodal values; outside[0,365]inadmissible. Not arbitrarytrajectorytruth.",
    "random_person_covariance": "C tensor (4*11T + sum_l centeredOU_l), C=.75I+.25 11T; centeredOU_l(t,s)=exp(-abs(t-s)/l)-exp(-t/l)-exp(-s/l)+1, l=7,30,365days. Baseline traitindependent ofcentered processes.",
    "measurement_noise": "same q(.75I+.25ZZT) as linked acquisition challenge; sessiondefinition qualified",
    "precision": "Likelihood-only personcoefficients, no randompopulationprior createsacquisition",
    "weights": "Trajectory temporalbudget split equally across4named timescales; within each, halfnativecontrasts andhalfjoint. No panelweightmultiplication.",
}


def basis(t):
    if not math.isfinite(t) or not 0 <= t <= KNOTS[-1]:
        raise ValueError("absolute time outside fixed model")
    f = np.zeros(K)
    if t in KNOTS:
        f[KNOTS.index(t)] = 1
        return f
    j = np.searchsorted(KNOTS, t)
    w = (t - KNOTS[j - 1]) / (KNOTS[j] - KNOTS[j - 1])
    f[j - 1] = 1 - w
    f[j] = w
    return f


def geometry(panel, group, q):
    # Longer source followup is retained by caller; this registered task selects only its365day window.
    all_events = list({e["physical_id"]: e for e in group["events"]}.values())
    events = [e for e in all_events if 0 <= e["time"] <= 365]
    from .sufficient_statistics import reduce_events

    physical_count = len(events)
    reduced = reduce_events(events)
    if reduced is not None:
        events, variances = reduced
    m = len(panel["coordinates"])
    H = np.zeros((len(events), m * K))
    for r, e in enumerate(events):
        j = [a["id"] for a in panel["coordinates"]].index(e["coordinate"])
        H[r, j * K : (j + 1) * K] = basis(e["time"])
    if reduced is not None:
        R = np.diag(variances) * q
    else:
        R = np.eye(len(events)) * 0.75 * q
        for a, ea in enumerate(events):
            for b, eb in enumerate(events):
                if ea["coordinate"] == eb["coordinate"] and ea["session_id"] == eb["session_id"]:
                    R[a, b] += 0.25 * q
    t = np.asarray(KNOTS)
    kernel = np.full((K, K), 4.0)
    for ell in [7.0, 30.0, 365.0]:
        kernel += (
            np.exp(-abs(t[:, None] - t[None, :]) / ell)
            - np.exp(-t[:, None] / ell)
            - np.exp(-t[None, :] / ell)
            + 1
        )
    C = 0.75 * np.eye(m) + 0.25 * np.ones((m, m))
    B = np.kron(C, kernel)
    return (
        H,
        R,
        B,
        {
            "selected_events": physical_count,
            "retained_target_rows": len(events),
            "effective_rows": [{"coordinate": e["coordinate"], "time": e["time"]} for e in events],
            "reduction": "known-homogeneous-error-block-gls-v1" if reduced is not None else None,
            "outside_window_events": len(all_events) - physical_count,
        },
    )


def definition(panel, horizon, factor=1.0):
    m = len(panel["coordinates"])
    L = []
    labels = []
    for j, a in enumerate(panel["coordinates"]):
        for label, contrast in [
            ("endpoint_change", basis(horizon) - basis(0)),
            (
                "midpoint_departure",
                basis(horizon / 2) - 0.5 * (basis(0) + basis(horizon)),
            ),
        ]:
            row = np.zeros(m * K)
            row[j * K : (j + 1) * K] = contrast
            L.append(row)
            labels.append(a["id"] + "." + label)
    L = np.asarray(L)
    limits = np.full(2 * m, (0.75 * factor) ** 2)
    p = {
        **panel,
        "id": panel["id"] + ".horizon-" + str(int(horizon)),
        "horizon_days": horizon,
    }
    task = {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": p["id"] + ".trajectories",
        "task_version": "absolute-multiscale-proposal0",
        "source_sha256": c.digest({"panel": panel, "MODEL": MODEL}),
        "model_sha256": c.digest(MODEL),
        "target_population": "Declared selected cohort; per-person linked native finitecontrasts atregisteredabsolutetimes",
        "estimand": "Perperson endpoint change and midpointdeparture fromendpoint interpolation at "
        + str(horizon)
        + "days; finite nodalcontrasts, not arbitrarytrajectoryrecovery",
        "horizon": str(horizon)
        + "absolute elapsed days fromqualifiedbaseline; neverstudy-normalized",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["fixed_reference_native_scale"] * (m * K),
        "prior_precision": (np.eye(m * K) / 1000).tolist(),
        "required_support": [
            {"domain_id": panel["domain"], "role": "observation"},
            {"domain_id": "joint_native_resolution", "role": "observation"},
        ],
        "functionals": [
            {
                "functional_id": name,
                "coefficients": row.tolist(),
                "unit": "fixed_reference_native_scale",
                "variance_limit": float(v),
            }
            for name, row, v in zip(labels, L, limits)
        ],
    }
    return p, (task, L, limits)


def effect_information(panel, groups, q, horizon, external=False):
    m = len(panel["coordinates"])
    p = 8 * m
    J = np.zeros((p * (2 if external else 1),) * 2)
    if any(g["site"] is None or g["arm"] is None or g["modifier"] is None for g in groups):
        return None
    for g in groups:
        if not external and g["site"] != "internal":
            continue
        selected = copy.deepcopy(g)
        selected["events"] = [e for e in g["events"] if e["time"] in [0, horizon]]
        H, R, B, metadata = geometry(panel, selected, q)
        events = metadata["effective_rows"]
        if not events:
            continue
        X = np.zeros((len(events), p))
        z = g["modifier"]
        a = g["arm"]
        for r, e in enumerate(events):
            j = [x["id"] for x in panel["coordinates"]].index(e["coordinate"])
            u = float(e["time"] == horizon)
            X[r, 8 * j : 8 * j + 8] = [1, u, 0, z, z * u, 0, a * u, a * z * u]
        V = H @ B @ H.T + R
        JJ = c.fisher(X, V) * g["n"]
        offset = p if external and g["site"] == "external" else 0
        J[offset : offset + p, offset : offset + p] += JJ
    return J


def evaluate_panel(
    panel,
    groups,
    cohort_n,
    design,
    coordinate_status,
    q=1.0,
    factor=1.0,
    gates=None,
    family="trajectories",
    return_components=False,
):
    if gates is None:
        gates = [True]
    out = []
    components = []
    if sum(g["n"] for g in groups) > cohort_n:
        raise ValueError("groupN exceeds cohort")
    for horizon in TIMES:
        pg, task = definition(panel, horizon, factor)
        parts = []
        if family == "trajectories":
            for g in groups:
                H, R, _B, diag = geometry(panel, g, q)
                gg = list(gates) + (
                    [None]
                    if any(
                        e.get("session_id") is None for e in g["events"] if 0 <= e["time"] <= 365
                    )
                    else []
                )
                comp = c.canonical(
                    pg,
                    family,
                    c.fisher(H, R),
                    gg,
                    design,
                    c.scenario_name(design, q),
                    {},
                    factor,
                    coordinate_status,
                    task,
                )
                components.append(comp)
                cc = continuous(comp)
                parts.append(
                    {
                        "n": g["n"],
                        "group_id": g["group_id"],
                        "lower_percent": 100 * comp["lower"],
                        "upper_percent": 100 * comp["upper"],
                        "continuous_lower_percent": cc["lower_percent"],
                        "continuous_upper_percent": cc["upper_percent"],
                        "geometry": diag,
                        "canonical_receipt_sha256": comp["canonical_receipt_sha256"],
                    }
                )
            missing = cohort_n - sum(g["n"] for g in groups)
            if missing:
                comp = c.canonical(
                    pg,
                    family,
                    np.zeros((len(task[0]["parameter_units"]),) * 2),
                    gates,
                    design,
                    c.scenario_name(design, q),
                    {},
                    factor,
                    coordinate_status,
                    task,
                )
                components.append(comp)
                cc = continuous(comp)
                parts.append(
                    {
                        "n": missing,
                        "group_id": "unobserved",
                        "canonical_receipt_sha256": comp["canonical_receipt_sha256"],
                        "lower_percent": 100 * comp["lower"],
                        "upper_percent": 100 * comp["upper"],
                        "continuous_lower_percent": cc["lower_percent"],
                        "continuous_upper_percent": cc["upper_percent"],
                    }
                )
            denom = cohort_n
        elif family in [
            "controlled_effects",
            "personalized_response",
            "external_replication",
        ]:
            task0, L, limits = c.definition(pg, family, factor)
            task0["model_sha256"] = c.digest(
                {
                    "model": MODEL,
                    "family": family,
                    "mean": "Freebaseline/endpointmeanswithbaseline-no-treatment-effect;interiorobservationsnotusedforcausalcontrast",
                    "horizon": horizon,
                    "native_panel": panel,
                }
            )
            task0["task_version"] = "coherent-absolute-endpoint0"
            task0["source_sha256"] = c.digest({"panel": panel, "MODEL": MODEL})
            task = (task0, L, limits)
            J = effect_information(panel, groups, q, horizon, family == "external_replication")
            gs = list(gates)
            if J is None:
                gs.append(None)
            if any(
                e.get("session_id") is None
                for g in groups
                for e in g["events"]
                if e["time"] in [0, horizon]
            ):
                gs.append(None)
            comp = c.canonical(
                pg,
                family,
                J,
                gs,
                design,
                c.scenario_name(design, q),
                {},
                factor,
                coordinate_status,
                task,
            )
            components.append(comp)
            cc = continuous(comp)
            parts = [
                {
                    "n": 1,
                    "group_id": "study_endpoint_contrast",
                    "lower_percent": 100 * comp["lower"],
                    "upper_percent": 100 * comp["upper"],
                    "continuous_lower_percent": cc["lower_percent"],
                    "continuous_upper_percent": cc["upper_percent"],
                    "canonical_receipt_sha256": comp["canonical_receipt_sha256"],
                }
            ]
            denom = 1
        else:
            raise ValueError("unsupportedtemporal family")
        out.append(
            {
                "horizon_days": horizon,
                "temporal_weight": 0.25,
                "parts": parts,
                **{
                    k: sum(g["n"] * g[k] for g in parts) / denom
                    for k in [
                        "lower_percent",
                        "upper_percent",
                        "continuous_lower_percent",
                        "continuous_upper_percent",
                    ]
                },
            }
        )
    result = {
        "panel_id": panel["id"],
        "family": family,
        "timescale_tasks": out,
        **{
            k: sum(r[k] / 4 for r in out)
            for k in [
                "lower_percent",
                "upper_percent",
                "continuous_lower_percent",
                "continuous_upper_percent",
            ]
        },
        "model": MODEL,
    }
    return (result, components) if return_components else result
