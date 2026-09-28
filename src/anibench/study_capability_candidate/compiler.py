# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Conditional study-capability candidate. Gaussian challenge, not biological calibration.
Reuse AniBench's canonical likelihood evaluator; compile actual event geometry.
No participant outcomes are required or used by this calculation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pathlib
from importlib.resources import files

import numpy as np

from anibench.benchmark_v1 import evaluate_benchmark
from anibench.finite_suites_v1 import scientific_frame_sha256, suite_sha256
from anibench.finite_tasks_v1 import finite_task_sha256
from anibench.information_v2 import functional_likelihood_precision

BASE = pathlib.Path(__file__).parent
FAMILIES = [
    "individual_state",
    "population_variation",
    "trajectories",
    "controlled_effects",
    "personalized_response",
    "external_replication",
]
SCENARIOS = {"reference": 1.0, "double_measurement_noise": 2.0}


def digest(x):
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
    )


def registry():
    return json.loads(files(__package__).joinpath("TASK_MANIFEST.json").read_text(encoding="utf-8"))


def tri(values):
    return False if False in values else None if None in values else True


def validate(design, manifest):
    if design["schema"] != "anibench.study-capability-design.v0":
        raise ValueError("schema")
    if design["lifecycle"] not in ["planned", "collected", "hypothetical"]:
        raise ValueError("lifecycle")
    if type(design["cohort_n"]) is not int or design["cohort_n"] < 1:
        raise ValueError("cohort_n")
    if (
        not isinstance(design["source_sha256"], str)
        or len(design["source_sha256"]) != 71
        or not design["source_sha256"].startswith("sha256:")
    ):
        raise ValueError("source hash")
    for v in design["gates"].values():
        if v is not None and type(v) is not bool:
            raise ValueError("strict three-valued gate")
    allowed = {p["id"]: p for p in manifest["panels"]}
    if set(design["panels"]) - set(allowed):
        raise ValueError("unregistered panel")
    for key, p in design["panels"].items():
        if p["status"] not in ["present", "absent", "unknown"]:
            raise ValueError("panel status")
        if p["operator_qualified"] is not None and type(p["operator_qualified"]) is not bool:
            raise ValueError("operator gate")
        if p["status"] != "present" and p.get("groups"):
            raise ValueError("groups contradict panel status")
        if p["status"] == "present":
            frame = p.get("time_frame", {})
            if frame.get("unit") != "days":
                raise ValueError("time_frame.unit must be days; no silent unit reinterpretation")
            if (
                frame.get("source_qualified") is not None
                and type(frame["source_qualified"]) is not bool
            ):
                raise ValueError("source_qualified strict bool/null")
            if frame.get("origin") not in [
                "first_acquisition",
                "intervention_assignment",
                "registered_baseline",
                None,
            ]:
                raise ValueError("time origin")
            expected = {a["id"] for a in allowed[key]["coordinates"]}
            if set(p.get("coordinate_status", {})) != expected:
                raise ValueError("Explicit status for every registered coordinate required")
            if any(
                v not in ["present", "absent", "unknown"] for v in p["coordinate_status"].values()
            ):
                raise ValueError("coordinate status")
        gids = set()
        n = 0
        for g in p.get("groups", []):
            if g["group_id"] in gids:
                raise ValueError("duplicated group")
            gids.add(g["group_id"])
            if type(g["n"]) is not int or g["n"] < 1:
                raise ValueError("positive group n")
            n += g["n"]
            if g["site"] not in ["internal", "external", None]:
                raise ValueError("site")
            for f in ["arm", "modifier"]:
                if g[f] is not None and (type(g[f]) is not int or g[f] not in [0, 1]):
                    raise ValueError(f)
            seen = {}
            for e in g["events"]:
                if not isinstance(e.get("physical_id"), str) or not e["physical_id"]:
                    raise ValueError("physical identity")
                if e.get("session_id") is not None and (
                    not isinstance(e["session_id"], str) or not e["session_id"]
                ):
                    raise ValueError("session identity")
                if e["coordinate"] not in [a["id"] for a in allowed[key]["coordinates"]]:
                    raise ValueError("unregistered coordinate")
                if p["coordinate_status"][e["coordinate"]] != "present":
                    raise ValueError("Events require qualified present coordinate status")
                if (
                    type(e["time"]) not in [int, float]
                    or not math.isfinite(e["time"])
                    or e["time"] < 0
                ):
                    raise ValueError("nonnegative finite elapsed time required")
                # physical_id means a physical channel reading, not a source-file row.
                if e["physical_id"] in seen and seen[e["physical_id"]] != e:
                    raise ValueError("conflicting physical identity")
                seen[e["physical_id"]] = e
        if n > design["cohort_n"]:
            raise ValueError("group overlap/count exceeds selected cohort")
    return design


def event_model(panel, group, q):
    """Reference-normalized native readings; no sample-specific z-scoring."""
    events = list({e["physical_id"]: e for e in group["events"]}.values())
    from .sufficient_statistics import reduce_events

    reduced = reduce_events(events)
    if reduced is not None:
        events, variances = reduced
    m = len(panel["coordinates"])
    k = 3 * m
    H = np.zeros((len(events), k))
    for r, e in enumerate(events):
        j = [a["id"] for a in panel["coordinates"]].index(e["coordinate"])
        u = e["time"] / panel["horizon_days"]
        H[r, 3 * j : 3 * j + 3] = [1, u, 4 * u * (1 - u)]
    # A shared occasion error within a coordinate/session plus independent reading error.
    # Distinct coordinates independent measurement error; biological covariance is explicit below.
    if reduced is not None:
        R = np.diag(variances) * q
    else:
        R = np.eye(len(events)) * 0.75 * q
        for a, ea in enumerate(events):
            for b, eb in enumerate(events):
                if ea["session_id"] == eb["session_id"] and ea["coordinate"] == eb["coordinate"]:
                    R[a, b] += 0.25 * q
    C = 0.75 * np.eye(m) + 0.25 * np.ones((m, m))
    B = np.kron(C, np.diag([4.0, 1.0, 1.0]))
    return H, R, B, events


def fisher(H, R):
    return H.T @ np.linalg.solve(R, H) if len(H) else np.zeros((H.shape[1], H.shape[1]))


def projected(J, L):
    """Use canonical estimability and polarization, without a second rank solver."""
    prior = np.eye(len(J)) / 1000
    rs = [functional_likelihood_precision(J, prior, l) for l in L]
    flags = [r["identified"] for r in rs]
    if False in flags:
        return False, None
    if None in flags:
        return None, None
    V = np.diag([r["variance"] for r in rs])
    for i in range(len(L)):
        for j in range(i):
            r = functional_likelihood_precision(J, prior, L[i] + L[j])
            if r["identified"] is not True:
                return r["identified"], None
            V[i, j] = V[j, i] = (r["variance"] - V[i, i] - V[j, j]) / 2
    return True, V


def definition(panel, family, resolution_factor=1.0):
    m = len(panel["coordinates"])
    k = 3 * m
    if family in ["individual_state", "trajectories"]:
        p = k
        ids = [(j, b) for j in range(m) for b in ([0] if family == "individual_state" else [1, 2])]
        L = np.eye(p)[[3 * j + b for j, b in ids]]
        limits = np.full(len(ids), 0.75**2)
        labels = [
            panel["coordinates"][j]["id"]
            + [".baseline", ".endpoint_change", ".midpoint_departure"][b]
            for j, b in ids
        ]
    elif family == "population_variation":
        pairs = [(i, j) for i in range(m) for j in range(i, m)]
        p = len(pairs)
        L = np.eye(p)
        limits = np.full(p, 0.5**2)
        labels = [
            f"baseline_covariance.{panel['coordinates'][i]['id']}.{panel['coordinates'][j]['id']}"
            for i, j in pairs
        ]
    else:
        # Per coordinate: nuisance 1,u,curve,z,z*u,z*curve; treatment u, treatment*modifier u.
        p = 8 * m * (2 if family == "external_replication" else 1)
        L = np.zeros((m, p))
        for j in range(m):
            if family == "personalized_response":
                L[j, 8 * j + 7] = 1
            else:
                L[j, 8 * j + 6] = 1
                L[j, 8 * j + 7] = 0.5  # prespecified equal-stratum standardization
                if family == "external_replication":
                    L[j, 8 * m + 8 * j + 6] = -1
                    L[j, 8 * m + 8 * j + 7] = -0.5
        limits = np.full(m, 0.5**2)
        labels = [a["id"] + "." + family for a in panel["coordinates"]]
    limits = limits * resolution_factor**2
    model = {
        "id": "baseline-common-native-challenge-v1"
        if family in ["individual_state", "population_variation"]
        else "historical-quadratic-native-challenge-v0",
        "panel": panel,
        "family": family,
        "active_model": "Day0 native state or residual covariance4C"
        if family in ["individual_state", "population_variation"]
        else "Historical coefficients[1,u,4u(1-u)], B=C tensor diag(4,1,1); coherent temporal caller overrides this definition",
        "noise": "q(.75I+.25ZZT)",
        "scenario_ids": list(SCENARIOS),
    }
    roles = [
        {
            "domain_id": panel["domain"],
            "role": "perturbation" if family in FAMILIES[3:] else "observation",
        },
        {"domain_id": "joint_native_resolution", "role": "observation"},
    ]
    task = {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": panel["id"] + "." + family,
        "task_version": "capability-prototype0",
        "source_sha256": digest(panel),
        "model_sha256": digest(model),
        "target_population": "Declared selected cohort and exact input sampling frame; conditional common-noise challenge",
        "estimand": registry()["families"][family]["estimand"]
        + "; coordinates "
        + ",".join(a["id"] for a in panel["coordinates"]),
        "horizon": "Day0 qualified baseline"
        if family in ["individual_state", "population_variation"]
        else str(panel["horizon_days"]) + " days fixed by task, not by study duration",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": [
            "reference_normalized_native_coordinate"
            if family != "population_variation"
            else "reference_normalized_native_covariance"
        ]
        * p,
        "prior_precision": (np.eye(p) / 1000).tolist(),
        "required_support": roles,
        "functionals": [
            {
                "functional_id": label,
                "coefficients": l.tolist(),
                "unit": "fixed_reference_scale",
                "variance_limit": float(v),
            }
            for label, l, v in zip(labels, L, limits)
        ],
    }
    return task, L, limits


def dependencies(panel, family, functional_index):
    m = len(panel["coordinates"])
    if family == "population_variation":
        return list(set([(i, j) for i in range(m) for j in range(i, m)][functional_index]))
    if family == "trajectories":
        return [functional_index // 2]
    return [functional_index]


def canonical(
    panel,
    family,
    J,
    gates,
    design,
    scenario,
    cache,
    resolution_factor=1.0,
    coordinate_status=None,
    definition_override=None,
):
    t, L, limits = (
        definition(panel, family, resolution_factor)
        if definition_override is None
        else definition_override
    )
    if "_noise_scenario_registry" in design:
        t = copy.deepcopy(t)
        t["model_sha256"] = digest(
            {
                "base_model_sha256": t["model_sha256"],
                "measurement_noise_scenarios": design["_noise_scenario_registry"],
                "profile": "common-noise-grid-v1",
            }
        )
        t["task_version"] += ".common-noise-grid-v1"
    pkey = panel["id"] + "." + family
    base = tri(gates)
    joint = None
    ratio = None
    if base is None:
        J = None
    if J is not None:
        joint, V = projected(J, L)
        if joint is True:
            D = np.diag(1 / np.sqrt(limits))
            ratio = float(np.linalg.eigvalsh(D @ V @ D)[-1])
            joint = ratio <= 1.0 + 1e-10
    entries = []
    requests = []
    weights = []
    bind = {
        "design_id": design["design_id"],
        "design_source_sha256": design["source_sha256"],
    }
    definitions = [("native-" + str(i), [f], False, 1) for i, f in enumerate(t["functionals"])]
    if len(L) > 1:
        definitions.append(("joint", t["functionals"], True, len(L)))
    for suffix, funcs, isjoint, w in definitions:
        coord_status = coordinate_status or {a["id"]: "present" for a in panel["coordinates"]}
        idx = (
            list(range(len(panel["coordinates"])))
            if isjoint
            else dependencies(panel, family, int(suffix.split("-")[-1]))
        )
        native_gate = tri(
            [
                {"present": True, "absent": False, "unknown": None}[
                    coord_status[panel["coordinates"][i]["id"]]
                ]
                for i in idx
            ]
        )
        local_base = tri([base, native_gate])
        local_J = J if local_base is not None else None
        local_joint = joint if native_gate is True else native_gate
        if isjoint and native_gate is None and base is True and J is not None:
            known = [
                i
                for i in range(len(L))
                if all(
                    coord_status[panel["coordinates"][j]["id"]] == "present"
                    for j in dependencies(panel, family, i)
                )
            ]
            if known:
                kid, kcov = projected(J, L[known])
                if kid is False:
                    local_joint = False
                elif kid is True:
                    kd = np.diag(1 / np.sqrt(limits[known]))
                    if np.linalg.eigvalsh(kd @ kcov @ kd)[-1] > 1.0 + 1e-10:
                        local_joint = False
        task = copy.deepcopy(t)
        task["task_id"] = pkey + "." + suffix
        task["functionals"] = funcs
        if not isjoint:
            task["required_support"] = task["required_support"][:1]
        task["estimand"] += "; " + (
            "all-direction joint resolution" if isjoint else funcs[0]["functional_id"]
        )
        ident = pkey + "." + suffix
        entries.append(
            {
                "canonical_id": ident,
                "frame_sha256": scientific_frame_sha256(task),
                "task": task,
            }
        )
        support = [{**task["required_support"][0], "supported": local_base}]
        if isjoint:
            support.append({**task["required_support"][1], "supported": local_joint})
        req = {
            "contract": "anibench.finite-task-request.v1",
            "task": task,
            "task_sha256": finite_task_sha256(task),
            "evidence": {
                "identifiability": True,
                "collection_verified": None,
                "support": support,
            },
            "geometry": None
            if local_J is None
            else {
                "model_sha256": task["model_sha256"],
                "information_matrix": ((local_J + local_J.T) / 2).tolist(),
            },
        }
        requests.append({"canonical_id": ident, "known_absent": False, "request": req, **bind})
        weights.append({"canonical_id": ident, "weight": w})
    profile = {
        "contract": "anibench.finite-suite-profile.v1",
        "profile_id": pkey + "." + scenario,
        "profile_type": "illustrative",
        "scope": "Conditional biological study-capability component; not certified AB1",
        "tolerance_authority": "Explicit native resolution convention, not MCID or discovered sufficiency",
        "calibration_authority": "Shared Gaussian challenge distribution; no empirical calibration",
        "precision_basis": "likelihood_only",
        "scenario_quantifier": "single_conditional",
        "scenario_ids": [scenario],
        "parent_sha256": None,
        "targets": entries,
    }
    sp = {
        "contract": "anibench.score-profile.v1",
        "score_profile_id": pkey + "." + scenario,
        "suite_profile_sha256": suite_sha256(profile),
        "weighting_rationale": "Fixed half marginal native targets, half joint bundle when multivariate; singleton receives full mass. Splitting native targets requires new registry.",
        "gate_only_targets": [],
        "views": [
            {
                "view_id": "task",
                "label": "task",
                "categories": [
                    {
                        "category_id": pkey,
                        "label": pkey,
                        "question": "What fraction of the fixed native-and-joint panel capability budget meets its registered resolution?",
                        "targets": weights,
                    }
                ],
            }
        ],
    }
    request = {
        "contract": "anibench.benchmark-request.v1",
        "score_profile_sha256": suite_sha256(sp),
        "suite_request": {
            "contract": "anibench.finite-suite-request.v1",
            **bind,
            "profile_sha256": suite_sha256(profile),
            "scenarios": [{"scenario_id": scenario, **bind, "targets": requests}],
        },
    }
    result = evaluate_benchmark(
        request,
        trusted_profiles={suite_sha256(profile): profile},
        trusted_score_profiles={suite_sha256(sp): sp},
    )
    c = result["envelope"][0]["categories"][0]
    component = {
        "lower": c["lower_percent"] / 100,
        "upper": c["upper_percent"] / 100,
        "joint_worst_variance_ratio": ratio,
        "canonical_receipt_sha256": result["receipt_sha256"],
        "request": request,
        "profile": profile,
        "score_profile": sp,
        "receipt": result,
    }
    from .compare_metrics import continuous

    progress = continuous(component)
    component["continuous_lower"] = progress["lower_percent"] / 100
    component["continuous_upper"] = progress["upper_percent"] / 100
    return component


def scenario_name(design, q):
    registry = design.get("_noise_scenario_registry", SCENARIOS)
    matches = [name for name, value in registry.items() if value == q]
    if len(matches) != 1:
        raise ValueError("Noise multiplier must match one declared coherent scenario")
    return matches[0]


def coalesce(panel, groups):
    """Canonical acquisition patterns, so splitting a row cannot spend degrees of freedom."""
    merged = {}
    for g in groups:
        g = copy.deepcopy(g)
        g["events"] = sorted(
            {e["physical_id"]: e for e in g["events"]}.values(),
            key=lambda e: (
                e["coordinate"],
                e["time"],
                str(e["session_id"]),
                e["physical_id"],
            ),
        )
        H, R, _, _ = event_model(panel, g, 1.0)
        key = digest(
            {
                "H": H.tolist(),
                "R": R.tolist(),
                "site": g["site"],
                "arm": g["arm"],
                "modifier": g["modifier"],
            }
        )
        if key in merged:
            merged[key]["n"] += g["n"]
        else:
            merged[key] = g
    return list(merged.values())


def population_information(panel, groups, q):
    # Mean nuisance strata are biological (site/arm/modifier), not acquisition patterns.
    from .population_reml import information

    J, _ = information(panel, groups, q)
    return J


def effect_information(panel, groups, q, external=False):
    m = len(panel["coordinates"])
    p = 8 * m
    J = np.zeros((p * (2 if external else 1),) * 2)
    for g in groups:
        if g["site"] is None or g["arm"] is None or g["modifier"] is None:
            continue
        if not external and g["site"] != "internal":
            continue
        H, R, B, events = event_model(panel, g, q)
        if not events:
            continue
        X = np.zeros((len(events), p))
        z = g["modifier"]
        a = g["arm"]
        for r, e in enumerate(events):
            j = [c["id"] for c in panel["coordinates"]].index(e["coordinate"])
            u = e["time"] / panel["horizon_days"]
            v = 4 * u * (1 - u)
            X[r, 8 * j : 8 * j + 8] = [1, u, v, z, z * u, z * v, a * u, a * z * u]
        V = H @ B @ H.T + R
        JJ = fisher(X, V) * g["n"]
        offset = p if external and g["site"] == "external" else 0
        J[offset : offset + p, offset : offset + p] += JJ
    return J


def evaluate(design, resolution_factor=1.0, model_variant="coherent_absolute_v1"):
    if model_variant not in ["coherent_absolute_v1", "quadratic_v0"]:
        raise ValueError("model variant")
    if not math.isfinite(resolution_factor) or resolution_factor <= 0:
        raise ValueError("positive finite resolution factor")
    manifest = registry()
    validate(design, manifest)
    if model_variant == "quadratic_v0":
        for panel in manifest["panels"]:
            for g in design["panels"].get(panel["id"], {}).get("groups", []):
                if any(e["time"] > panel["horizon_days"] for e in g["events"]):
                    raise ValueError(
                        "Historical quadratic profile cannot extrapolate outside its registered horizon"
                    )
    allrows = []
    cache = {}
    artifacts = []
    for scenario, q in design.get("_noise_scenario_registry", SCENARIOS).items():
        rows = []
        for panel in manifest["panels"]:
            supplied = design["panels"].get(
                panel["id"],
                {"status": "unknown", "operator_qualified": None, "groups": []},
            )
            present = {"present": True, "absent": False, "unknown": None}[supplied["status"]]
            groups = supplied.get("groups", [])
            coordinate_status = supplied.get(
                "coordinate_status", {a["id"]: "unknown" for a in panel["coordinates"]}
            )
            frame = supplied.get("time_frame", {})
            common = [
                present,
                supplied["operator_qualified"],
                design["gates"].get("group_linkage_and_disjointness"),
                design["gates"].get("measurement_semantics"),
                frame.get("source_qualified"),
            ]
            if frame.get("origin") not in [
                "first_acquisition",
                "intervention_assignment",
                "registered_baseline",
            ]:
                common.append(None)
            if design["lifecycle"] == "collected":
                common.append(design["gates"].get("collection_verified"))
            for family in FAMILIES:
                if model_variant == "coherent_absolute_v1" and family in [
                    "trajectories",
                    "controlled_effects",
                    "personalized_response",
                    "external_replication",
                ]:
                    from .multiscale import evaluate_panel

                    gs = list(common)
                    if family != "trajectories":
                        gs += [
                            design["gates"].get("sampling_frame"),
                            design["gates"].get("assignment_randomized"),
                            design["gates"].get("baseline_modifier_prespecified"),
                            design["gates"].get("assignment_consistency_and_followup"),
                        ]
                        gs += [
                            True
                            if frame.get("origin") == "intervention_assignment"
                            else design["gates"].get("baseline_aligned_to_assignment")
                        ]
                        if family == "external_replication":
                            gs += [
                                design["gates"].get("external_site_independent"),
                                design["gates"].get("same_intervention_operator_external"),
                            ]
                    temporal, comps = evaluate_panel(
                        panel,
                        groups,
                        design["cohort_n"],
                        design,
                        coordinate_status,
                        q,
                        resolution_factor,
                        gs,
                        family,
                        True,
                    )
                    artifacts.extend(comps)
                    rows.append(
                        {
                            "panel_id": panel["id"],
                            "domain": panel["domain"],
                            "family": family,
                            "lower_percent": temporal["lower_percent"],
                            "upper_percent": temporal["upper_percent"],
                            "continuous_lower_percent": temporal["continuous_lower_percent"],
                            "continuous_upper_percent": temporal["continuous_upper_percent"],
                            "coverage_n": sum(g["n"] for g in groups),
                            "cohort_n": design["cohort_n"],
                            "parts": temporal["timescale_tasks"],
                            "temporal_budget": "Four fixed absolute horizons, equal shares; nativepanelweight unchanged",
                        }
                    )
                    continue
                parts = []
                if family in ["individual_state", "trajectories"]:
                    for g in groups:
                        use_g = copy.deepcopy(g)
                        if model_variant == "coherent_absolute_v1":
                            use_g["events"] = [e for e in g["events"] if e["time"] == 0]
                        H, R, _B, _e = event_model(panel, use_g, q)
                        c = canonical(
                            panel,
                            family,
                            fisher(H, R),
                            common
                            + (
                                [None]
                                if any(e.get("session_id") is None for e in use_g["events"])
                                else []
                            ),
                            design,
                            scenario,
                            cache,
                            resolution_factor,
                            coordinate_status,
                        )
                        artifacts.append(c)
                        parts.append(
                            {
                                "group_id": g["group_id"],
                                "n": g["n"],
                                **{
                                    k: c[k]
                                    for k in [
                                        "lower",
                                        "upper",
                                        "continuous_lower",
                                        "continuous_upper",
                                        "joint_worst_variance_ratio",
                                        "canonical_receipt_sha256",
                                    ]
                                },
                            }
                        )
                    missing = design["cohort_n"] - sum(g["n"] for g in groups)
                    # Disjoint documented groups need not exhaust the cohort.
                    # The remainder has unknown acquisitions, not a qualified empty record.
                    if missing:
                        task, _, _ = definition(panel, family, resolution_factor)
                        zero = np.zeros((len(task["parameter_units"]),) * 2)
                        c = canonical(
                            panel,
                            family,
                            zero,
                            common + [None],
                            design,
                            scenario,
                            cache,
                            resolution_factor,
                            coordinate_status,
                        )
                        artifacts.append(c)
                        parts.append(
                            {
                                "group_id": "not_observed_or_not_documented",
                                "n": missing,
                                **{
                                    k: c[k]
                                    for k in [
                                        "lower",
                                        "upper",
                                        "continuous_lower",
                                        "continuous_upper",
                                        "joint_worst_variance_ratio",
                                        "canonical_receipt_sha256",
                                    ]
                                },
                            }
                        )
                    lo = sum(p["n"] * p["lower"] for p in parts) / design["cohort_n"]
                    hi = sum(p["n"] * p["upper"] for p in parts) / design["cohort_n"]
                    clo = sum(p["n"] * p["continuous_lower"] for p in parts) / design["cohort_n"]
                    chi = sum(p["n"] * p["continuous_upper"] for p in parts) / design["cohort_n"]
                else:
                    gs = common + [design["gates"].get("sampling_frame")]
                    if family == "population_variation":
                        popgroups = copy.deepcopy(groups)
                        if model_variant == "coherent_absolute_v1":
                            for g in popgroups:
                                g["events"] = [e for e in g["events"] if e["time"] == 0]
                        J = population_information(panel, popgroups, q)
                        if any(e.get("session_id") is None for g in popgroups for e in g["events"]):
                            gs.append(None)
                    else:
                        if any(e.get("session_id") is None for g in groups for e in g["events"]):
                            gs.append(None)
                        gs += [
                            True
                            if frame.get("origin") == "intervention_assignment"
                            else design["gates"].get("baseline_aligned_to_assignment")
                        ]
                        gs += [
                            design["gates"].get("assignment_randomized"),
                            design["gates"].get("baseline_modifier_prespecified"),
                            design["gates"].get("assignment_consistency_and_followup"),
                        ]
                        if family == "external_replication":
                            gs += [
                                design["gates"].get("external_site_independent"),
                                design["gates"].get("same_intervention_operator_external"),
                            ]
                        if any(
                            g["site"] is None or g["arm"] is None or g["modifier"] is None
                            for g in groups
                        ):
                            gs.append(None)
                        J = effect_information(
                            panel, groups, q, external=family == "external_replication"
                        )
                        if any(
                            g["site"] is None or g["arm"] is None or g["modifier"] is None
                            for g in groups
                        ):
                            J = None
                    c = canonical(
                        panel,
                        family,
                        J,
                        gs,
                        design,
                        scenario,
                        cache,
                        resolution_factor,
                        coordinate_status,
                    )
                    artifacts.append(c)
                    lo, hi = c["lower"], c["upper"]
                    clo, chi = c["continuous_lower"], c["continuous_upper"]
                    parts = [
                        {
                            k: c[k]
                            for k in [
                                "lower",
                                "upper",
                                "continuous_lower",
                                "continuous_upper",
                                "joint_worst_variance_ratio",
                                "canonical_receipt_sha256",
                            ]
                        }
                    ]
                rows.append(
                    {
                        "panel_id": panel["id"],
                        "domain": panel["domain"],
                        "family": family,
                        "lower_percent": 100 * lo,
                        "upper_percent": 100 * hi,
                        "continuous_lower_percent": 100 * clo,
                        "continuous_upper_percent": 100 * chi,
                        "coverage_n": sum(g["n"] for g in groups),
                        "cohort_n": design["cohort_n"],
                        "parts": parts,
                    }
                )
        # Fixed equal domain budgets; panels share their domain budget. No scalar across families.
        summary = []
        for family in FAMILIES:
            domains = []
            for domain in sorted({p["domain"] for p in manifest["panels"]}):
                rs = [r for r in rows if r["family"] == family and r["domain"] == domain]
                domains.append(
                    {
                        "domain": domain,
                        "lower_percent": sum(r["lower_percent"] for r in rs) / len(rs),
                        "upper_percent": sum(r["upper_percent"] for r in rs) / len(rs),
                        "continuous_lower_percent": sum(r["continuous_lower_percent"] for r in rs)
                        / len(rs),
                        "continuous_upper_percent": sum(r["continuous_upper_percent"] for r in rs)
                        / len(rs),
                    }
                )
            summary.append(
                {
                    "family": family,
                    "lower_percent": sum(x["lower_percent"] for x in domains) / len(domains),
                    "upper_percent": sum(x["upper_percent"] for x in domains) / len(domains),
                    "continuous_lower_percent": sum(x["continuous_lower_percent"] for x in domains)
                    / len(domains),
                    "continuous_upper_percent": sum(x["continuous_upper_percent"] for x in domains)
                    / len(domains),
                    "domains": domains,
                }
            )
        allrows.append({"scenario_id": scenario, "rows": rows, "summary": summary})
    return {
        "schema": "anibench.study-capability-prototype-result.v0",
        "design_id": design["design_id"],
        "input_sha256": digest(design),
        "manifest_sha256": digest(manifest),
        "resolution_factor": resolution_factor,
        "model_variant": model_variant,
        "compiler_sha256": "sha256:"
        + hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "claim": "Conditional acquisition-geometry challenge; exact Gaussian fixed-weight quadratic-moment covariance at the reference point, not empirical biological calibration",
        "population_compiler_sha256": "sha256:"
        + hashlib.sha256((BASE / "population_reml.py").read_bytes()).hexdigest(),
        "temporal_compiler_sha256": "sha256:"
        + hashlib.sha256((BASE / "multiscale.py").read_bytes()).hexdigest(),
        "alternative_metric_sha256": "sha256:"
        + hashlib.sha256((BASE / "compare_metrics.py").read_bytes()).hexdigest(),
        "coverage_n_definition": "Participants represented by declared acquisition patterns; not a claim every target or horizon was collected. Task-specific absence and unknowns remain in fixed denominator.",
        "window_usage": [
            {
                "panel_id": p["id"],
                "pattern_events_after_day365": sum(
                    len({e["physical_id"] for e in g["events"] if e["time"] > 365})
                    for g in design["panels"].get(p["id"], {}).get("groups", [])
                ),
                "handling": "Preserved in input binding; excluded from current fixed<=365day tasks, never rescaled.",
            }
            for p in manifest["panels"]
        ],
        "scenarios": allrows,
    }, artifacts


def main():
    import gzip

    parser = argparse.ArgumentParser(
        description="Evaluate the conditional study-capability candidate locally."
    )
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--resolution-factor", type=float, default=1.0)
    parser.add_argument(
        "--model-variant",
        choices=["coherent_absolute_v1", "quadratic_v0"],
        default="coherent_absolute_v1",
    )
    args = parser.parse_args()
    design = json.loads(args.input.read_text())
    args.out.mkdir(exist_ok=False)
    result, components = evaluate(design, args.resolution_factor, args.model_variant)
    (args.out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with (
        (args.out / "CANONICAL_COMPONENTS.json.gz").open("xb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
    ):
        for chunk in json.JSONEncoder(separators=(",", ":"), allow_nan=False).iterencode(
            components
        ):
            compressed.write(chunk.encode())
    print(
        json.dumps(
            {
                "scenarios": len(result["scenarios"]),
                "canonical_components": len(components),
                "model_variant": args.model_variant,
            }
        )
    )


def reference_filename(level):
    """Resolve explicit corrected-catalogue resources; AB aliases select resolution only."""
    resolutions = {"AB1": "standard", "AB2": "fine"}
    if level not in resolutions:
        raise ValueError("Unknown native resolution")
    return "NATIVE36_V2." + resolutions[level] + ".profile.json"
