# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Explicit hybrid study profile; historical native36 contracts remain separate."""

from __future__ import annotations

import copy
import hashlib
import json
from importlib.resources import files

import numpy as np

from anibench.finite_suites_v1 import scientific_frame_sha256, suite_sha256

from . import compiler as c
from . import linked_workload as linked
from . import multiscale, noise_sensitivity, plain_rct, temporal_prediction
from .level_decision import decide_level

PROFILE_ID = "native36-capability-v3"
REPLACED = ("trajectories", "controlled_effects")
SCORES = ("lower_percent", "upper_percent")
MODULES = [
    "sufficient_statistics.py",
    "linked_workload.py",
    "compiler.py",
    "multiscale.py",
    "population_reml.py",
    "compare_metrics.py",
    "plain_rct.py",
    "temporal_prediction.py",
    "study_profile.py",
    "level_decision.py",
    "noise_sensitivity.py",
]


def _settings(resolution, noise_profile):
    if resolution not in ("standard", "fine"):
        raise ValueError("Unregistered resolution")
    if noise_profile not in ("normative", "common-noise-grid-v1"):
        raise ValueError("Unregistered noise profile")
    return (
        1.0 if resolution == "standard" else 0.5,
        dict(c.SCENARIOS if noise_profile == "normative" else noise_sensitivity.SCENARIOS),
    )


def inherited_profile(resolution, noise_profile):
    level = "AB1" if resolution == "standard" else "AB2"
    p = (
        json.loads(files(__package__).joinpath(c.reference_filename(level)).read_text())
        if noise_profile == "normative"
        else noise_sensitivity.profile(level)
    )
    p["targets"] = [
        t for t in p["targets"] if not any("." + f + "." in t["canonical_id"] for f in REPLACED)
    ]
    p["profile_id"] = (
        PROFILE_ID + "." + resolution + "." + noise_profile + ".inherited-four-families"
    )
    p["parent_sha256"] = None
    return p


def profile(resolution="standard", noise_profile="normative"):
    """Machine-readable finite rules, including endpoint existential quantifiers."""
    factor, scenarios = _settings(resolution, noise_profile)
    native = c.registry()
    inherited = inherited_profile(resolution, noise_profile)
    targets = [
        {
            "canonical_id": t["canonical_id"],
            "kind": "inherited",
            "scientific_frame_sha256": t["frame_sha256"],
        }
        for t in inherited["targets"]
    ]
    temporal_rules = []
    rct_rules = []
    for panel in native["panels"]:
        for horizon in multiscale.TIMES:
            _, (_, L, limits) = multiscale.definition(panel, horizon, factor)
            prefix = (
                panel["id"] + ".horizon-" + str(int(horizon)) + "." + temporal_prediction.VERSION
            )
            for suffix in ["native-" + str(i) for i in range(len(L))] + ["joint"]:
                targets.append(
                    {"canonical_id": prefix + "." + suffix, "kind": "temporal_prediction"}
                )
            temporal_rules.append(
                {
                    "panel_id": panel["id"],
                    "horizon_days": horizon,
                    "operator": L.tolist(),
                    "variance_limits": limits.tolist(),
                    "model_sha256": c.digest(
                        temporal_prediction._fixed_model(panel, 0.5, scenarios)
                    ),
                    "required_full_roster": True,
                    "alpha": 0.5,
                }
            )
        for window in plain_rct.WINDOWS:
            suffixes = ["native-" + str(i) for i in range(len(panel["coordinates"]))]
            if len(panel["coordinates"]) > 1:
                suffixes.append("joint")
            prefix = panel["id"] + ".plain-rct-" + window[0] + ".controlled_effects"
            for suffix in suffixes:
                targets.append({"canonical_id": prefix + "." + suffix, "kind": "randomized_window"})
            rct_rules.append(
                {
                    "panel_id": panel["id"],
                    "window": window,
                    "criterion_se_reference_scale": 0.5 * factor,
                    "quantifier": "One actual common endpoint and coherent admissible subset must pass all native and joint criteria in this window. Upper remains an outer bound.",
                }
            )
    descriptor = {
        "schema": "anibench.hybrid-study-profile.v1",
        "profile_id": PROFILE_ID + "." + resolution + "." + noise_profile,
        "catalogue_profile": native["profile_id"],
        "manifest_sha256": c.digest(native),
        "resolution": resolution,
        "resolution_factor": factor,
        "scenario_registry": scenarios,
        "inherited_four_family_profile_sha256": c.digest(inherited),
        "replacements": {
            "trajectories": temporal_prediction.VERSION,
            "controlled_effects": plain_rct.MODEL["id"],
        },
        "temporal_rules": temporal_rules,
        "randomized_window_rules": rct_rules,
        "rct_model": plain_rct.MODEL,
        "targets": targets,
        "budget": {
            "domain": "Five equal domains, equal panel shares within each domain",
            "trajectory": "Four equal horizons; half native functionals and half joint within each panel/horizon; full selected cohort denominator",
            "controlled": "Four equal windows; existing native/joint panel budget retained",
            "other_families": "Inherited unchanged, including75/25native/cross-panel state and population budgets",
        },
        "relations_sha256": c.digest(linked.RELATIONS),
        "relation_budgets_sha256": c.digest(linked.relation_budgets(linked.RELATIONS, native)),
        "certificate_rule": "Exact conjunction of every required target, support and roster instance across every declared scenario. Window pass requires a coherent common endpoint/subset witness; no rounded percentage or historical certificate.",
    }

    # Persisted profiles have exactly the same JSON-native container types.
    return json.loads(json.dumps(descriptor, allow_nan=False))


def _status(low, high):
    return "pass" if low == "attained" else "fail" if high == "not_attained" else "unresolved"


def _suite(component, scenario):
    """Check direct finite-suite receipt bindings and return exact target states."""
    p, req, rec = component["profile"], component["request"], component["receipt"]
    if rec["profile_sha256"] != suite_sha256(p) or rec["request_sha256"] != suite_sha256(req):
        raise ValueError("Stale direct suite binding")
    if len(rec["scenarios"]) != 1 or rec["scenarios"][0]["scenario_id"] != scenario:
        raise ValueError("Mismatched direct suite scenario")
    entries = {t["canonical_id"]: t for t in p["targets"]}
    if len(entries) != len(p["targets"]):
        raise ValueError("Duplicate direct target")
    for entry in entries.values():
        if scientific_frame_sha256(entry["task"]) != entry["frame_sha256"]:
            raise ValueError("Stale target frame")
    return entries, {x["canonical_id"]: x["attainment"] for x in rec["scenarios"][0]["targets"]}


def _benchmark(component, scenario):
    rec = component["receipt"]
    if (
        suite_sha256({k: v for k, v in rec.items() if k != "receipt_sha256"})
        != rec["receipt_sha256"]
    ):
        raise ValueError("Stale benchmark receipt")
    if rec["suite_profile_sha256"] != suite_sha256(component["profile"]) or rec[
        "request_sha256"
    ] != suite_sha256(component["request"]):
        raise ValueError("Stale benchmark input binding")
    rows = rec["suite_result"]["scenarios"]
    if len(rows) != 1 or rows[0]["scenario_id"] != scenario:
        raise ValueError("Mismatched benchmark scenario")
    entries = {t["canonical_id"]: t for t in component["profile"]["targets"]}
    for entry in entries.values():
        if scientific_frame_sha256(entry["task"]) != entry["frame_sha256"]:
            raise ValueError("Stale target frame")
    return entries, {x["canonical_id"]: x["attainment"] for x in rows[0]["targets"]}


def _temporal_frame(entries, panel, horizon, factor, scenarios):
    _, (_, L, limits) = multiscale.definition(panel, horizon, factor)
    _, _, prior_covariance, _ = multiscale.geometry(panel, {"events": []}, 1.0)
    expected_prior = np.linalg.solve(prior_covariance, np.eye(len(prior_covariance))).tolist()
    prefix = panel["id"] + ".horizon-" + str(int(horizon)) + "." + temporal_prediction.VERSION
    expected = {prefix + ".native-" + str(i) for i in range(len(L))} | {prefix + ".joint"}
    if set(entries) != expected:
        raise ValueError("Temporal target denominator changed")
    for key, entry in entries.items():
        t = entry["task"]
        indices = list(range(len(L))) if key.endswith(".joint") else [int(key.rsplit("-", 1)[1])]
        if (
            t["model_sha256"] != c.digest(temporal_prediction._fixed_model(panel, 0.5, scenarios))
            or t["task_version"] != temporal_prediction.VERSION
        ):
            raise ValueError("Temporal scientific model changed")
        if t["source_sha256"] != c.digest(panel) or t["parameter_units"] != [
            "fixed_reference_native_scale"
        ] * len(L[0]):
            raise ValueError("Temporal native frame changed")
        funcs = [
            {
                "functional_id": panel["coordinates"][i // 2]["id"]
                + (".endpoint_change" if i % 2 == 0 else ".midpoint_departure"),
                "coefficients": L[i].tolist(),
                "unit": "fixed_reference_native_scale",
                "variance_limit": float(limits[i]),
            }
            for i in indices
        ]
        if t["functionals"] != funcs or t["prior_precision"] != expected_prior:
            raise ValueError("Temporal target, prior or resolution changed")
        required = [
            {"domain_id": panel["domain"], "role": "observation"},
            {"domain_id": "registered_reference_uncertainty_reduction", "role": "observation"},
        ]
        if key.endswith(".joint"):
            required.append({"domain_id": "joint_native_resolution", "role": "observation"})
        if t["required_support"] != required:
            raise ValueError("Temporal support changed")


def _rct_frame(entries, panel, window, endpoint, factor, scenarios, grid):
    if endpoint is not None:
        if type(endpoint) not in (int, float) or not np.isfinite(endpoint):
            raise ValueError("Invalid actual endpoint")
        _, _, lo, hi, inclusive = window
        if not (lo <= endpoint <= hi if inclusive else lo < endpoint <= hi):
            raise ValueError("Actual endpoint outside registered window")
    p, (t, L, _) = plain_rct.definition(panel, window, endpoint, factor)
    if grid:
        t["model_sha256"] = c.digest(
            {
                "base_model_sha256": t["model_sha256"],
                "measurement_noise_scenarios": scenarios,
                "profile": "common-noise-grid-v1",
            }
        )
        t["task_version"] += ".common-noise-grid-v1"
    expected = {}
    suffixes = [("native-" + str(i), [f], False) for i, f in enumerate(t["functionals"])]
    if len(L) > 1:
        suffixes.append(("joint", t["functionals"], True))
    for suffix, funcs, joint in suffixes:
        task = copy.deepcopy(t)
        key = p["id"] + ".controlled_effects." + suffix
        task["task_id"] = key
        task["functionals"] = funcs
        if not joint:
            task["required_support"] = task["required_support"][:1]
        task["estimand"] += "; " + (
            "all-direction joint resolution" if joint else funcs[0]["functional_id"]
        )
        expected[key] = task
    if set(entries) != set(expected):
        raise ValueError("RCT target denominator changed")
    if any(entries[k]["task"] != task for k, task in expected.items()):
        raise ValueError("RCT target scientific frame changed")


def decide(result, components, descriptor):
    resolution = descriptor["resolution"]
    noise = (
        "normative" if descriptor["scenario_registry"] == c.SCENARIOS else "common-noise-grid-v1"
    )
    if descriptor != profile(resolution, noise):
        raise ValueError("Unregistered hybrid reference")
    if result.get("reference_profile_sha256") != c.digest(descriptor):
        raise ValueError("Hybrid result/reference mismatch")
    factor, scenarios = _settings(resolution, noise)
    inherited_components = [
        x for x in components if x.get("component_kind") != "temporal_prediction"
    ]
    inherited_result = copy.deepcopy(result)
    for scenario in inherited_result["scenarios"]:
        scenario["rows"] = [r for r in scenario["rows"] if r["family"] not in REPLACED]
    inherited = decide_level(
        inherited_result, inherited_components, inherited_profile(resolution, noise)
    )
    records = list(inherited["task_instances_records"])
    direct = {
        suite_sha256(x["receipt"]): x
        for x in components
        if x.get("component_kind") == "temporal_prediction"
    }
    bench = {x["receipt"]["receipt_sha256"]: x for x in inherited_components if "receipt" in x}
    panels = {p["id"]: p for p in c.registry()["panels"]}
    seen = {
        sid: {r["canonical_id"] for r in records if r["scenario_id"] == sid} for sid in scenarios
    }
    for scenario in result["scenarios"]:
        sid = scenario["scenario_id"]
        for row in scenario["rows"]:
            panel = panels[row["panel_id"]]
            if row["family"] == "trajectories":
                if [h["horizon_days"] for h in row["parts"]] != multiscale.TIMES:
                    raise ValueError("Temporal horizons changed")
                for horizon in row["parts"]:
                    if sum(p["n"] for p in horizon["parts"]) != result["cohort_n"]:
                        raise ValueError("Temporal roster loss")
                    for part in horizon["parts"]:
                        le, ls = _suite(direct[part["canonical_receipt_sha256"]], sid)
                        ue, us = _suite(direct[part["upper_canonical_receipt_sha256"]], sid)
                        _temporal_frame(le, panel, horizon["horizon_days"], factor, scenarios)
                        _temporal_frame(ue, panel, horizon["horizon_days"], factor, scenarios)
                        for key in ls:
                            records.append(
                                {
                                    "scenario_id": sid,
                                    "canonical_id": key,
                                    "status": _status(ls[key], us[key]),
                                    "scope": "full-roster conditional temporal prediction",
                                    "n": part["n"],
                                    "lower_receipt_sha256": part["canonical_receipt_sha256"],
                                    "upper_receipt_sha256": part["upper_canonical_receipt_sha256"],
                                }
                            )
                            seen[sid].add(key)
            elif row["family"] == "controlled_effects":
                if [w["window_id"] for w in row["parts"]] != [w[0] for w in plain_rct.WINDOWS]:
                    raise ValueError("RCT windows changed")
                for part, window in zip(row["parts"], plain_rct.WINDOWS):
                    le, ls = _benchmark(bench[part["canonical_receipt_sha256"]], sid)
                    ue, us = _benchmark(bench[part["upper_canonical_receipt_sha256"]], sid)
                    _rct_frame(
                        le,
                        panel,
                        window,
                        part["actual_endpoint_days"],
                        factor,
                        scenarios,
                        noise != "normative",
                    )
                    _rct_frame(
                        ue,
                        panel,
                        window,
                        part["upper_bound_endpoint_days"],
                        factor,
                        scenarios,
                        noise != "normative",
                    )
                    for key in ls:
                        records.append(
                            {
                                "scenario_id": sid,
                                "canonical_id": key,
                                "status": _status(ls[key], us[key]),
                                "scope": "one coherent actual endpoint/subset per window",
                                "lower_receipt_sha256": part["canonical_receipt_sha256"],
                                "upper_receipt_sha256": part["upper_canonical_receipt_sha256"],
                            }
                        )
                        seen[sid].add(key)
    expected = {t["canonical_id"] for t in descriptor["targets"]}
    if set(seen) != set(scenarios) or any(x != expected for x in seen.values()):
        raise ValueError("Missing hybrid target/scenario")
    status = (
        "fail"
        if any(r["status"] == "fail" for r in records)
        else "unresolved"
        if any(r["status"] == "unresolved" for r in records)
        else "pass"
    )
    out = {
        "schema": "anibench.hybrid-study-certificate.v1",
        "profile_id": descriptor["profile_id"],
        "reference_profile_sha256": c.digest(descriptor),
        "status": status,
        "required_targets_per_scenario": len(expected),
        "scenario_ids": list(scenarios),
        "task_instances": len(records),
        "status_counts": {
            s: sum(r["status"] == s for r in records) for s in ["pass", "fail", "unresolved"]
        },
        "limiting_targets": list(
            dict.fromkeys(r["canonical_id"] for r in records if r["status"] != "pass")
        )[:20],
        "task_instances_records": records,
        "task_instances_sha256": c.digest(records),
        "decision_basis": descriptor["certificate_rule"],
    }
    out["receipt_sha256"] = c.digest(out)
    return out


def evaluate(design, resolution="standard", noise_profile="normative"):
    linked.validate_raw(design)
    factor, scenarios = _settings(resolution, noise_profile)
    grid = noise_profile != "normative"
    result, components = linked.evaluate(
        design, factor, scenario_registry=scenarios if grid else None
    )
    descriptor = profile(resolution, noise_profile)
    source_calculation = copy.deepcopy(design)
    if grid:
        source_calculation["_noise_scenario_registry"] = scenarios
    panels = {p["id"]: p for p in c.registry()["panels"]}
    intermediate = {
        "result_sha256": result["result_sha256"],
        "summaries": copy.deepcopy([s["summary"] for s in result["scenarios"]]),
    }
    for scenario in result["scenarios"]:
        sid = scenario["scenario_id"]
        q = scenarios[sid]
        rows = []
        for row in scenario["rows"]:
            panel = panels[row["panel_id"]]
            supplied = design["panels"].get(
                panel["id"], {"status": "unknown", "operator_qualified": None, "groups": []}
            )
            if row["family"] == "controlled_effects":
                replacement, parts = plain_rct.evaluate_panel(
                    panel, supplied, source_calculation, q, factor
                )
                components.extend(parts)
                rows.append(replacement)
            elif row["family"] == "trajectories":
                horizons = []
                groups = supplied.get("groups", [])
                missing = design["cohort_n"] - sum(g["n"] for g in groups)
                if missing < 0:
                    raise ValueError("Roster exceeds cohort")
                for horizon in multiscale.TIMES:
                    parts = []
                    for g, n in [(g, g["n"]) for g in groups] + (
                        [(None, missing)] if missing else []
                    ):
                        value, pair = temporal_prediction.compile_group(
                            panel,
                            g,
                            q,
                            factor,
                            horizon=horizon,
                            design=design,
                            scenario_registry=scenarios,
                        )
                        for comp in pair.values():
                            components.append({**comp, "component_kind": "temporal_prediction"})
                        parts.append(
                            {
                                "n": n,
                                "group_id": g["group_id"] if g else "unobserved",
                                "lower_percent": value["lower_percent"],
                                "upper_percent": value["upper_percent"],
                                "canonical_receipt_sha256": value["lower_canonical_receipt_sha256"],
                                "upper_canonical_receipt_sha256": value[
                                    "upper_canonical_receipt_sha256"
                                ],
                                "prediction_result_sha256": value["result_sha256"],
                                "joint_data_variance_ratio": value[
                                    "joint_posterior_to_baseline_ratio"
                                ],
                            }
                        )
                    horizons.append(
                        {
                            "horizon_days": horizon,
                            "temporal_weight": 0.25,
                            "parts": parts,
                            **{
                                key: sum(p["n"] * p[key] for p in parts) / design["cohort_n"]
                                for key in SCORES
                            },
                        }
                    )
                rows.append(
                    {
                        "panel_id": panel["id"],
                        "domain": panel["domain"],
                        "family": "trajectories",
                        "cohort_n": design["cohort_n"],
                        "parts": horizons,
                        **{key: sum(h[key] / 4 for h in horizons) for key in SCORES},
                        "precision_basis": "conditional_posterior_with_data_gain",
                        "continuous_metric": "Not defined for this replacement profile; primary exact task attainment only",
                    }
                )
            else:
                rows.append(row)
        scenario["rows"] = rows
        for summary in scenario["summary"]:
            if summary["family"] not in REPLACED:
                continue
            for domain in summary["domains"]:
                selected = [
                    r
                    for r in rows
                    if r["family"] == summary["family"] and r["domain"] == domain["domain"]
                ]
                for key in SCORES:
                    domain[key] = sum(r[key] for r in selected) / len(selected)
                for key in list(domain):
                    if key.startswith("continuous_"):
                        domain.pop(key)
            for key in SCORES:
                summary[key] = sum(d[key] for d in summary["domains"]) / len(summary["domains"])
            for key in list(summary):
                if key.startswith("continuous_"):
                    summary.pop(key)
    result.update(
        {
            "study_profile": PROFILE_ID,
            "catalogue_profile": "native36-operator-pilot-v2",
            "requested_resolution": resolution,
            "scenario_registry": scenarios,
            "reference_profile_sha256": c.digest(descriptor),
            "temporal_prediction_profile": temporal_prediction.VERSION,
            "controlled_effects_profile": plain_rct.MODEL["id"],
            "replacement_semantics": descriptor["replacements"],
            "hybrid_intermediate": intermediate,
            "metric_id": "registered-hybrid-task-attainment-v1",
        }
    )
    if grid:
        result["measurement_noise_profile"] = {
            "id": noise_profile,
            "multipliers": scenarios,
            "native_increment_manifest_sha256": c.digest(c.registry()),
            "calibration": "Conditional common-noise sensitivity, not empirical calibration",
        }
    result["provenance"]["calculation_files"] = {
        name: "sha256:" + hashlib.sha256(files(__package__).joinpath(name).read_bytes()).hexdigest()
        for name in MODULES
    }
    result["provenance"]["canonical_components_sha256"] = c.digest(components)
    result["hybrid_profile_decision"] = decide(result, components, descriptor)
    result.pop("result_sha256", None)
    result["result_sha256"] = c.digest(result)
    return result, components, descriptor


def validate_chart_result(result):
    """Admit this exact mixed-question contract, without browser-side rescoring."""
    from .charts import FAMILIES, percent_pair

    factor = result.get("resolution_factor")
    if type(factor) not in (int, float) or factor not in (1.0, 0.5):
        raise ValueError("Unregistered hybrid resolution")
    resolution = "standard" if factor == 1 else "fine"
    noise = result.get("measurement_noise_profile")
    noise_id = (
        "normative" if noise is None else noise.get("id") if isinstance(noise, dict) else None
    )
    expected = profile(resolution, noise_id)
    scenarios = expected["scenario_registry"]
    if (
        result.get("reference_profile_sha256") != c.digest(expected)
        or result.get("catalogue_profile") != expected["catalogue_profile"]
        or result.get("manifest_sha256") != expected["manifest_sha256"]
    ):
        raise ValueError("Unregistered hybrid catalogue/reference")
    if (
        result.get("requested_resolution") != resolution
        or result.get("model_variant") != "coherent_absolute_v1"
    ):
        raise ValueError("Hybrid resolution/model label mismatch")
    if (
        result.get("replacement_semantics") != expected["replacements"]
        or result.get("temporal_prediction_profile") != temporal_prediction.VERSION
        or result.get("controlled_effects_profile") != plain_rct.MODEL["id"]
    ):
        raise ValueError("Hybrid family replacement mismatch")
    if result.get("metric_id") != "registered-hybrid-task-attainment-v1":
        raise ValueError("Hybrid metric mislabeled")
    temporal_prediction._scenario_registry(result.get("scenario_registry"))
    if result.get("scenario_registry") != scenarios:
        raise ValueError("Hybrid noise registry mismatch")
    if noise is not None and (
        noise.get("multipliers") != scenarios
        or noise.get("native_increment_manifest_sha256") != expected["manifest_sha256"]
    ):
        raise ValueError("Hybrid measurement scenario mismatch")
    provenance = result.get("provenance", {})
    code = {
        name: "sha256:" + hashlib.sha256(files(__package__).joinpath(name).read_bytes()).hexdigest()
        for name in MODULES
    }
    if provenance.get("calculation_files") != code:
        raise ValueError("Hybrid calculation bytes differ")
    if (
        provenance.get("relations_sha256") != expected["relations_sha256"]
        or provenance.get("budgets_sha256") != expected["relation_budgets_sha256"]
    ):
        raise ValueError("Hybrid relation budgets differ")
    decision = result.get("hybrid_profile_decision", {})
    if (
        decision.get("reference_profile_sha256") != c.digest(expected)
        or decision.get("profile_id") != expected["profile_id"]
        or decision.get("receipt_sha256")
        != c.digest({k: v for k, v in decision.items() if k != "receipt_sha256"})
    ):
        raise ValueError("Stale hybrid certificate")
    if any(key in result for key in ("expanded_profile_decision", "sensitivity_decision")):
        raise ValueError("Historical certificate cannot be reused after question replacement")
    actual = result.get("scenarios")
    if (
        not isinstance(actual, list)
        or len(actual) != len(scenarios)
        or {s.get("scenario_id") for s in actual} != set(scenarios)
    ):
        raise ValueError("Missing coherent scenarios")
    panels = c.registry()["panels"]
    domains = {p["domain"] for p in panels}
    row_ids = {(p["id"], f) for p in panels for f in FAMILIES}
    for scenario in actual:
        rows = scenario.get("rows", [])
        summaries = scenario.get("summary", [])
        if (
            len(rows) != len(row_ids)
            or {(r.get("panel_id"), r.get("family")) for r in rows} != row_ids
        ):
            raise ValueError("Hybrid panel/family denominator changed")
        if len(summaries) != len(FAMILIES) or {r.get("family") for r in summaries} != set(FAMILIES):
            raise ValueError("Hybrid capability denominator changed")
        for row in rows:
            percent_pair(row)
            if row["family"] == "trajectories":
                if row.get("precision_basis") != "conditional_posterior_with_data_gain":
                    raise ValueError("Posterior question mislabeled")
                if [h["horizon_days"] for h in row["parts"]] != multiscale.TIMES or any(
                    sum(p["n"] for p in h["parts"]) != result["cohort_n"] for h in row["parts"]
                ):
                    raise ValueError("Hybrid temporal roster/horizon mismatch")
            if (
                row["family"] == "controlled_effects"
                and row.get("profile_id") != plain_rct.MODEL["id"]
            ):
                raise ValueError("RCT question mislabeled")
        for summary in summaries:
            percent_pair(summary)
            values = summary.get("domains", [])
            if len(values) != len(domains) or {d.get("domain") for d in values} != domains:
                raise ValueError("Hybrid domain denominator changed")
            for value in values:
                percent_pair(value)
    return {
        "catalogue_profile": expected["catalogue_profile"],
        "profile_id": expected["profile_id"],
        "reference_profile_sha256": c.digest(expected),
        "manifest_sha256": expected["manifest_sha256"],
        "model_variant": result["model_variant"],
        "resolution_factor": factor,
        "resolution": resolution,
        "scenario_registry": scenarios,
        "noise_profile": noise_id,
        "calculation_files": code,
        "relations_sha256": expected["relations_sha256"],
        "budgets_sha256": expected["relation_budgets_sha256"],
        "metric_id": "registered-hybrid-task-attainment-v1",
        "replacement_semantics": expected["replacements"],
    }
