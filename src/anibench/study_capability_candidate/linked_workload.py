# ruff: noqa: TRY004 -- invalid JSON inputs consistently raise ValueError
# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Finite source-qualified cross-panel workload. Private candidate, not adopted AB1."""

import copy
import hashlib
import math
import re
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
from . import compiler as c
from .compare_metrics import continuous

RELATIONS = [
    (
        "glucose_pressure",
        ("targeted_metabolism", "fasting_glucose"),
        ("physical_function", "systolic"),
        "Paired glucose regulation and vascular measurement",
    ),
    (
        "inflammation_strength",
        ("blood_proteins", "il6"),
        ("physical_function", "grip"),
        "Paired inflammatory concentration and measured strength",
    ),
    (
        "activity_strength",
        ("daily_behavior", "acceleration"),
        ("physical_function", "grip"),
        "Paired movement behavior and measured strength",
    ),
    (
        "vigilance_evoked_response",
        ("cognitive_psychological", "reaction_time"),
        ("evoked_neural", "p3b"),
        "Paired instrument-specific vigilance and evoked neural response",
    ),
    (
        "cognition_structure",
        ("cognitive_psychological", "symbol_coding"),
        ("brain_structural_mri", "mri_left_hippocampus_aseg6"),
        "Paired cognitive performance and hemisphere-specific neural structure",
    ),
    (
        "transcript_protein",
        ("pbmc_transcription", "pbmc_il1b_log2tpm1"),
        ("blood_proteins", "il6"),
        "Paired cellular transcript and circulating inflammatory protein readout",
    ),
]


def strict_tri(value):
    if value is not None and type(value) is not bool:
        raise ValueError("Qualification must be bool or null")
    return value


def validate_linkage(design):
    linkage = design.get("cross_panel_linkage")
    if linkage is None:
        return {"source_qualified": None, "exhaustive": None, "partitions": []}
    strict_tri(linkage["source_qualified"])
    strict_tri(linkage["exhaustive"])
    total = 0
    identities = set()
    allocation = {}
    for part in linkage["partitions"]:
        if (
            not isinstance(part["partition_id"], str)
            or not part["partition_id"]
            or part["partition_id"] in identities
        ):
            raise ValueError("Unique aggregate partition identity required")
        identities.add(part["partition_id"])
        if type(part["n"]) is not int or part["n"] < 1:
            raise ValueError("Positive partition N")
        total += part["n"]
        strict_tri(part["common_occasion_qualified"])
        for panel_id, member in part["members"].items():
            if panel_id not in design["panels"]:
                raise ValueError("Unknown panel reference")
            if member["status"] not in ["linked", "absent", "unknown"]:
                raise ValueError("Membership status")
            if member["status"] == "linked":
                groups = {g["group_id"]: g for g in design["panels"][panel_id].get("groups", [])}
                if member["group_id"] not in groups:
                    raise ValueError("Unknown acquisition pattern")
                key = (panel_id, member["group_id"])
                allocation[key] = allocation.get(key, 0) + part["n"]
                if allocation[key] > groups[member["group_id"]]["n"]:
                    raise ValueError("Global overlap exceeds marginal pattern N")
            elif "group_id" in member:
                raise ValueError("Unlinked member cannot carry a group reference")
    if total > design["cohort_n"]:
        raise ValueError("Disjoint global partitions exceed roster")
    if linkage["exhaustive"] is True and total != design["cohort_n"]:
        raise ValueError("Exhaustive partition must retain full roster")
    if linkage["exhaustive"] is True:
        for panel_id, panel in design["panels"].items():
            known = all(
                p["members"].get(panel_id, {"status": "unknown"})["status"] != "unknown"
                for p in linkage["partitions"]
            )
            if known:
                for g in panel.get("groups", []):
                    if allocation.get((panel_id, g["group_id"]), 0) != g["n"]:
                        raise ValueError(
                            "Exhaustive known linkage must reconcile every marginal pattern"
                        )
    return linkage


def validate_raw(design):
    """Validate source rows before time selection; null is never silently numeric."""
    try:
        if not isinstance(design, dict):
            raise ValueError("Design must be an object")
        if "_noise_scenario_registry" in design:
            raise ValueError(
                "Noise registry is evaluator configuration, never a source design field"
            )
        if not isinstance(design.get("design_id"), str) or not design["design_id"].strip():
            raise ValueError("Nonempty design_id string required")
        if (
            not isinstance(design.get("source_sha256"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", design["source_sha256"]) is None
        ):
            raise ValueError("source_sha256 must be a lowercase SHA256 identity")
        if not isinstance(design.get("panels"), dict) or not isinstance(design.get("gates"), dict):
            raise ValueError("panels and gates must be objects")
        projection = copy.deepcopy(design)
        for panel_id, panel in design["panels"].items():
            if not isinstance(panel, dict):
                raise ValueError("Panel must be an object")
            if not isinstance(panel.get("groups", []), list):
                raise ValueError("Panel groups must be an array")
            for index, group in enumerate(panel.get("groups", [])):
                if not isinstance(group, dict) or not isinstance(group.get("events"), list):
                    raise ValueError("Group requires an event array")
                if not isinstance(group.get("group_id"), str) or not group["group_id"]:
                    raise ValueError("Nonempty group identity required")
                if "timing_qualified" in group:
                    strict_tri(group["timing_qualified"])
                occasion = group.get("state_occasion")
                if occasion is not None:
                    if (
                        not isinstance(occasion, dict)
                        or not isinstance(occasion.get("occasion_id"), str)
                        or not occasion["occasion_id"]
                    ):
                        raise ValueError("Qualified selected occasion requires nonempty identity")
                    strict_tri(occasion["source_qualified"])
                seen = {}
                for j, event in enumerate(group["events"]):
                    if not isinstance(event, dict):
                        raise ValueError("Event must be an object")
                    if "time" not in event:
                        raise ValueError("Event time must be numeric or explicit null")
                    if "session_id" not in event:
                        raise ValueError(
                            "Event session_id must be a nonempty identity or explicit null"
                        )
                    t = event["time"]
                    if t is not None and (
                        type(t) not in [int, float] or not math.isfinite(t) or t < 0
                    ):
                        raise ValueError(
                            "Event time must be finite nonnegative days or explicit null"
                        )
                    key = event.get("physical_id")
                    if not isinstance(key, str) or not key:
                        raise ValueError("Nonempty physical acquisition identity required")
                    if key in seen and seen[key] != event:
                        raise ValueError("Conflicting physical acquisition identity")
                    seen[key] = event
                    if "occasion_id" in event and (
                        not isinstance(event["occasion_id"], str) or not event["occasion_id"]
                    ):
                        raise ValueError("Event occasion identity must be nonempty")
                    # Validation-only placeholder: no result or geometry uses this copy.
                    if t is None:
                        projection["panels"][panel_id]["groups"][index]["events"][j]["time"] = 0
        c.validate(projection, c.registry())
        linkage = design.get("cross_panel_linkage")
        if linkage is not None:
            if not isinstance(linkage, dict) or not isinstance(linkage.get("partitions"), list):
                raise ValueError("Linkage requires partition array")
            for part in linkage["partitions"]:
                if not isinstance(part, dict) or not isinstance(part.get("members"), dict):
                    raise ValueError("Partition requires member mapping")
                if any(not isinstance(member, dict) for member in part["members"].values()):
                    raise ValueError("Linkage member must be an object")
        validate_linkage(design)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(
            "Malformed design structure: required typed fields are missing or invalid"
        ) from error
    return design


def pair_panel(relation, manifest):
    rid, left, right, label = relation
    panels = {p["id"]: p for p in manifest["panels"]}
    coordinates = []
    for panel_id, target in [left, right]:
        coordinate = copy.deepcopy(
            next(x for x in panels[panel_id]["coordinates"] if x["id"] == target)
        )
        coordinate["id"] = panel_id + "__" + target
        coordinate["source_panel"] = panel_id
        coordinate["source_coordinate"] = target
        coordinates.append(coordinate)
    return {
        "id": "relation." + rid,
        "domain": "cross_panel",
        "coordinates": coordinates,
        "horizon_days": 365,
        "question": label,
        "endpoint_domains": sorted({panels[p]["domain"] for p, t in [left, right]}),
    }


def selected_occasion(panel, group, target):
    """Return qualified selected-occasion readings; never impute an unknown calendar time."""
    occasion = group.get("state_occasion")
    if occasion is not None:
        qualified = strict_tri(occasion["source_qualified"])
        if not isinstance(occasion.get("occasion_id"), str) or not occasion["occasion_id"]:
            raise ValueError("Opaque acquired-occasion identity required")
        events = [
            e
            for e in group["events"]
            if e["coordinate"] == target and e.get("occasion_id") == occasion["occasion_id"]
        ]
        mode = "source_selected_occasion_without_calendar_imputation"
    else:
        frame = panel.get("time_frame", {})
        qualified = c.tri(
            [
                strict_tri(frame.get("source_qualified")),
                strict_tri(group.get("timing_qualified", frame.get("source_qualified"))),
            ]
        )
        events = [e for e in group["events"] if e["coordinate"] == target and e.get("time") == 0]
        mode = "qualified_registered_baseline"
        if any(e["coordinate"] == target and e.get("time") is None for e in group["events"]):
            qualified = c.tri([qualified, None])
    distinct = {}
    for event in events:
        key = event["physical_id"]
        if key in distinct and distinct[key] != event:
            raise ValueError("Conflicting selected physical acquisition identity")
        distinct[key] = event
    events = list(distinct.values())
    # R shares errors only within a coordinate/session. One physical reading has
    # marginal variance q without knowing which other session it belongs to.
    if len(events) > 1 and any(e.get("session_id") is None for e in events):
        qualified = c.tri([qualified, None])
    return events, qualified, mode


def compile_partition(design, part, pair, linkage):
    events = []
    status = {}
    qualifications = []
    role_values = {x: set() for x in ["site", "arm", "modifier"]}
    modes = []
    for coordinate in pair["coordinates"]:
        panel_id = coordinate["source_panel"]
        native = coordinate["source_coordinate"]
        target = coordinate["id"]
        panel = design["panels"].get(panel_id, {"status": "unknown", "coordinate_status": {}})
        native_status = panel.get("coordinate_status", {}).get(native, "unknown")
        member = part["members"].get(panel_id, {"status": "unknown"})
        if (
            panel.get("status") == "absent"
            or native_status == "absent"
            or member["status"] == "absent"
        ):
            status[target] = "absent"
            continue
        if member["status"] != "linked" or native_status != "present":
            status[target] = "unknown"
            continue
        group = next(g for g in panel["groups"] if g["group_id"] == member["group_id"])
        for role, values in role_values.items():
            if group.get(role) is not None:
                values.add(group[role])
        selected, qualified, mode = selected_occasion(panel, group, native)
        modes.append(mode)
        qualified = c.tri(
            [
                qualified,
                panel.get("operator_qualified"),
                design["gates"].get("measurement_semantics"),
                design["gates"].get("group_linkage_and_disjointness"),
            ]
        )
        if design["lifecycle"] == "collected":
            qualified = c.tri([qualified, design["gates"].get("collection_verified")])
        qualifications.append(qualified)
        status[target] = (
            "present" if qualified is True else "absent" if qualified is False else "unknown"
        )
        if qualified is True:
            for e in selected:
                events.append(
                    {
                        "physical_id": panel_id + "::" + e["physical_id"],
                        "coordinate": target,
                        "time": 0,
                        "session_id": None
                        if e["session_id"] is None
                        else panel_id + "::" + e["session_id"],
                    }
                )
    if any(len(v) > 1 for v in role_values.values()):
        raise ValueError("Linked participant has contradictory biological strata")
    group = {
        "group_id": part["partition_id"],
        "n": part["n"],
        "events": events,
        **{k: next(iter(v)) if v else None for k, v in role_values.items()},
    }
    shared = c.tri([linkage["source_qualified"], part["common_occasion_qualified"]])
    return group, status, shared, modes


def relation_definition(pair, family, factor):
    task, L, limits = c.definition(pair, family, factor)
    task["task_version"] = "cross-panel-selected-occasion-v1"
    task["estimand"] = (
        "Joint within-person native state"
        if family == "individual_state"
        else "Cross-person covariance of the two native quantities"
    ) + " at a source-qualified common acquired occasion; not mechanism or causal relationship."
    task["horizon"] = (
        "Declared source-native common acquisition occasion; no missing calendar date is assigned to day0."
        if family == "individual_state"
        else "Qualified actual registered day0 common baseline; undated or later selected state occasions do not become baseline covariance observations."
    )
    if family == "population_variation":
        task["estimand"] = (
            "Cross-person covariance of the two registered native quantities at qualified actual day0 common baseline, with reference population covariance4C; not arbitrary-occasion or causal relationship."
        )
    task["model_sha256"] = c.digest(
        {
            "global_native_covariance": "4*(.75I+.25ones), pair principal submatrix",
            "pair": pair,
            "measurement_noise": "q(.75I+.25ZZT)",
            "family": family,
        }
    )
    return task, L, limits


def select_canonical(component, suffix):
    """A new canonical one-target score selects joint state or cross covariance only."""
    source = copy.deepcopy(component)
    selected = [x for x in source["profile"]["targets"] if x["canonical_id"].endswith("." + suffix)]
    if len(selected) != 1:
        raise ValueError("Unique selected target required")
    ident = selected[0]["canonical_id"]
    source["profile"]["targets"] = selected
    score = source["score_profile"]
    score["weighting_rationale"] = (
        "Only the registered joint-state or cross-covariance relation target receives relation budget; native marginals are not duplicated."
    )
    score["suite_profile_sha256"] = c.suite_sha256(source["profile"])
    score["views"][0]["categories"][0]["targets"] = [{"canonical_id": ident, "weight": 1}]
    request = source["request"]
    request["score_profile_sha256"] = c.suite_sha256(score)
    request["suite_request"]["profile_sha256"] = c.suite_sha256(source["profile"])
    request["suite_request"]["scenarios"][0]["targets"] = [
        x for x in request["suite_request"]["scenarios"][0]["targets"] if x["canonical_id"] == ident
    ]
    result = c.evaluate_benchmark(
        request,
        trusted_profiles={c.suite_sha256(source["profile"]): source["profile"]},
        trusted_score_profiles={c.suite_sha256(score): score},
    )
    target = next(x for x in continuous(component)["targets"] if x["canonical_id"] == ident)
    # Native/known-direction bounds are inherited from the full canonical component;
    # no marginal task receives additional relation budget.
    cat = result["envelope"][0]["categories"][0]
    return {
        "lower_percent": cat["lower_percent"],
        "upper_percent": cat["upper_percent"],
        "continuous_lower_percent": 100 * target["lower"],
        "continuous_upper_percent": 100 * target["upper"],
        "canonical_receipt_sha256": result["receipt_sha256"],
        "selected_target": ident,
        "canonical_result": result,
        "profile": source["profile"],
        "request": request,
        "score_profile": score,
        "source_component": component,
    }


def evaluate_relation(design, relation, q=1.0, factor=1.0):
    linkage = validate_linkage(design)
    pair = pair_panel(relation, c.registry())
    parts = []
    population_groups = []
    uncertain = False
    canonical_components = []
    possible_pair_n = 0
    baseline_design = copy.deepcopy(design)
    for panel in baseline_design["panels"].values():
        for group in panel.get("groups", []):
            group.pop("state_occasion", None)
    partitions = list(linkage["partitions"])
    used = sum(p["n"] for p in partitions)
    if used < design["cohort_n"]:
        partitions.append(
            {
                "partition_id": "unresolved_roster",
                "n": design["cohort_n"] - used,
                "common_occasion_qualified": None,
                "members": {},
            }
        )
    for part in partitions:
        group, status, shared, modes = compile_partition(design, part, pair, linkage)
        H, R, _B, _ = c.event_model(pair, group, q)
        comp = c.canonical(
            pair,
            "individual_state",
            c.fisher(H, R),
            [shared],
            design,
            c.scenario_name(design, q),
            {},
            factor,
            status,
            relation_definition(pair, "individual_state", factor),
        )
        selected = select_canonical(comp, "joint")
        canonical_components.append(selected)
        parts.append(
            {
                "partition_id": part["partition_id"],
                "n": part["n"],
                "occasion_modes": modes,
                **{
                    k: v
                    for k, v in selected.items()
                    if k
                    not in [
                        "canonical_result",
                        "source_component",
                        "profile",
                        "request",
                        "score_profile",
                    ]
                },
            }
        )
        # Covariance uses the coherent process baseline4C, never imputed opaque times.
        baseline_group, baseline_status, baseline_shared, _ = compile_partition(
            baseline_design, part, pair, linkage
        )
        observed = {e["coordinate"] for e in baseline_group["events"]}
        if baseline_shared is not False and all(
            baseline_status[a["id"]] == "unknown"
            or (baseline_status[a["id"]] == "present" and a["id"] in observed)
            for a in pair["coordinates"]
        ):
            possible_pair_n += part["n"]
        if baseline_shared is True:
            population_groups.append(baseline_group)
        if baseline_shared is None or "unknown" in baseline_status.values():
            uncertain = True
    J = c.population_information(pair, population_groups, q)
    common = [
        design["gates"].get("sampling_frame"),
        design["gates"].get("measurement_semantics"),
        design["gates"].get("group_linkage_and_disjointness"),
        linkage["source_qualified"],
    ] + [
        design["panels"].get(a["source_panel"], {}).get("operator_qualified")
        for a in pair["coordinates"]
    ]
    for coordinate in pair["coordinates"]:
        source_panel = design["panels"].get(coordinate["source_panel"], {})
        common.extend(
            [
                {"present": True, "absent": False, "unknown": None}.get(source_panel.get("status")),
                {"present": True, "absent": False, "unknown": None}.get(
                    source_panel.get("coordinate_status", {}).get(coordinate["source_coordinate"])
                ),
            ]
        )
    if design["lifecycle"] == "collected":
        common.append(design["gates"].get("collection_verified"))
    comp = c.canonical(
        pair,
        "population_variation",
        J,
        common,
        design,
        c.scenario_name(design, q),
        {},
        factor,
        {a["id"]: "present" for a in pair["coordinates"]},
        relation_definition(pair, "population_variation", factor),
    )
    pop = select_canonical(comp, "native-1")
    canonical_components.append(copy.deepcopy(pop))
    possible = all(
        design["panels"].get(a["source_panel"], {}).get("status") != "absent"
        and design["panels"]
        .get(a["source_panel"], {})
        .get("coordinate_status", {})
        .get(a["source_coordinate"])
        != "absent"
        for a in pair["coordinates"]
    )
    if uncertain and possible and c.tri(common) is not False:
        # Optimistic exact quadratic-score experiment: only possibly paired people,
        # noiseless observations, all nuisance means/variances known. Unpaired
        # people may estimate nuisances but never become paired cross-covariance N.
        # At B=[[4,1],[1,4]], I_cross=17/225 per person; Var=225/(17*N).
        JJ = np.zeros((3, 3))
        JJ[1, 1] = possible_pair_n * 17.0 / 225.0
        optimistic = c.canonical(
            pair,
            "population_variation",
            JJ,
            [True],
            design,
            c.scenario_name(design, q),
            {},
            factor,
            {a["id"]: "present" for a in pair["coordinates"]},
            relation_definition(pair, "population_variation", factor),
        )
        bound = select_canonical(optimistic, "native-1")
        canonical_components.append(bound)
        pop["upper_canonical_receipt_sha256"] = bound["canonical_receipt_sha256"]
        pop["upper_percent"] = max(pop["lower_percent"], bound["upper_percent"])
        pop["continuous_upper_percent"] = max(
            pop["continuous_lower_percent"], bound["continuous_upper_percent"]
        )
        pop["possibly_paired_baseline_n"] = possible_pair_n
        pop["bound_semantics"] = (
            "Unknown overlap/timing retains epistemic mass only for possibly paired baseline participants; upper precision uses a noiseless known-nuisance quadratic-score experiment, never acquired precision or extra paired people."
        )
    keys = [
        "lower_percent",
        "upper_percent",
        "continuous_lower_percent",
        "continuous_upper_percent",
    ]
    return {
        "canonical_components": canonical_components,
        "relation_id": relation[0],
        "endpoint_domains": pair["endpoint_domains"],
        "individual_state": {
            **{k: sum(p["n"] * p[k] for p in parts) / design["cohort_n"] for k in keys},
            "parts": parts,
        },
        "population_variation": pop,
        "input_sha256": c.digest(design),
        "claim": "Qualified joint native state and between-person relationship precision; not latent recovery, causal mechanism or universal transfer.",
    }


def relation_budgets(relations, manifest):
    domains = sorted({p["domain"] for p in manifest["panels"]})
    endpoints = {r[0]: pair_panel(r, manifest)["endpoint_domains"] for r in relations}
    incident = {d: [key for key, ds in endpoints.items() if d in ds] for d in domains}
    if any(not values for values in incident.values()):
        raise ValueError("Every retained domain must have a registered relation allocation")
    weights = {
        key: sum(1 / len(domains) / len(incident[d]) for d in ds) for key, ds in endpoints.items()
    }
    return {
        "within_capability_native_fraction": 0.75,
        "within_capability_relation_fraction": 0.25,
        "domain_incidence": incident,
        "relation_global_weights": weights,
        "rationale": "Every domain retains75% native-panel budget and allocates25% to fixed registered incident relationships. A relation appearing in two domain views has the summed fractional mass, not two extra votes. Changes require a versioned registry.",
    }


def optimistic_population_groups(panel, supplied, cohort_n):
    """Relax precision, never turn a known empty baseline into an acquisition.

    Only possibly acquired coordinates receive noiseless baseline measurements.
    Documented people retain their count; an omitted roster has unknown support.
    A shared nuisance mean is an optimistic relaxation, not acquired information.
    In this model, off-baseline readings add independent trajectory variation to
    the baseline state. Observing that state directly is an optimistic channel.
    """
    groups = []
    source_groups = [(g, False) for g in supplied.get("groups", [])]
    missing = cohort_n - sum(g["n"] for g, _ in source_groups)
    if missing < 0:
        raise ValueError("Documented groups exceed the full cohort")
    if missing:
        source_groups.append(
            (
                {
                    "group_id": "upper-omitted",
                    "n": missing,
                    "events": [],
                    "timing_qualified": c.tri(
                        [strict_tri(supplied.get("time_frame", {}).get("source_qualified")), None]
                    ),
                },
                True,
            )
        )
    for source, omitted in source_groups:
        frame_qualified = supplied.get("time_frame", {}).get("source_qualified")
        timing = c.tri(
            [
                strict_tri(frame_qualified),
                strict_tri(source.get("timing_qualified", frame_qualified)),
            ]
        )
        possible = []
        for coordinate in panel["coordinates"]:
            native = coordinate["id"]
            status = supplied.get("coordinate_status", {}).get(native, "unknown")
            if status == "absent" or timing is False:
                continue
            events = [e for e in source["events"] if e["coordinate"] == native]
            if status == "unknown" or omitted or events:
                possible.append(native)
        groups.append(
            {
                "group_id": source["group_id"],
                "n": source["n"],
                "site": None,
                "arm": None,
                "modifier": None,
                "events": [
                    {"physical_id": native, "coordinate": native, "time": 0, "session_id": native}
                    for native in possible
                ],
            }
        )
    return groups


def aggregate_upper_bound(panel, family, supplied, design, factor, scenario_id):
    from .multiscale import MODEL, TIMES, effect_information

    gates = [
        {"present": True, "absent": False, "unknown": None}.get(supplied.get("status")),
        supplied.get("operator_qualified"),
        design["gates"].get("group_linkage_and_disjointness"),
        design["gates"].get("measurement_semantics"),
        design["gates"].get("sampling_frame"),
    ]
    if design["lifecycle"] == "collected":
        gates.append(design["gates"].get("collection_verified"))
    if family != "population_variation":
        gates += [
            design["gates"].get(k)
            for k in [
                "assignment_randomized",
                "baseline_modifier_prespecified",
                "assignment_consistency_and_followup",
            ]
        ]
        frame = supplied.get("time_frame", {})
        gates += [
            True
            if frame.get("origin") == "intervention_assignment"
            else design["gates"].get("baseline_aligned_to_assignment")
        ]
        if family == "external_replication":
            gates += [
                design["gates"].get(k)
                for k in [
                    "external_site_independent",
                    "same_intervention_operator_external",
                ]
            ]
    if c.tri(gates) is False:
        return {"upper_percent": 0.0, "continuous_upper_percent": 0.0}
    optimistic_status = {
        a["id"]: (
            "absent"
            if supplied.get("coordinate_status", {}).get(a["id"]) == "absent"
            else "present"
        )
        for a in panel["coordinates"]
    }
    if family == "population_variation":
        groups = optimistic_population_groups(panel, supplied, design["cohort_n"])
        J = c.population_information(panel, groups, 0.0)
        comp = c.canonical(
            panel, family, J, [True], design, scenario_id, {}, factor, optimistic_status
        )
        return {
            "upper_percent": 100 * comp["upper"],
            "continuous_upper_percent": 100 * comp["continuous_upper"],
            "bound_components": [comp],
        }
    minimum = 8 if family == "external_replication" else 4
    if design["cohort_n"] < minimum:
        return {"upper_percent": 0.0, "continuous_upper_percent": 0.0}
    bounds = []
    for horizon in TIMES:
        groups = []
        for source in supplied.get("groups", []):
            if (
                strict_tri(
                    source.get(
                        "timing_qualified",
                        supplied.get("time_frame", {}).get("source_qualified"),
                    )
                )
                is False
            ):
                groups.append({**source, "events": []})
                continue
            group = {
                **source,
                "events": [
                    {
                        "physical_id": a["id"] + str(t),
                        "coordinate": a["id"],
                        "time": t,
                        "session_id": a["id"] + str(t),
                    }
                    for a in panel["coordinates"]
                    for t in [0, horizon]
                ],
            }
            groups.append(group)
        if sum(g["n"] for g in groups) < design["cohort_n"]:
            J = None
        else:
            J = effect_information(panel, groups, 0.0, horizon, family == "external_replication")
        pg = {
            **panel,
            "id": panel["id"] + ".horizon-" + str(int(horizon)),
            "horizon_days": horizon,
        }
        task, L, limits = c.definition(pg, family, factor)
        task["model_sha256"] = c.digest(
            {
                "model": MODEL,
                "family": family,
                "mean": "Freebaseline/endpointmeanswithbaseline-no-treatment-effect;interiorobservationsnotusedforcausalcontrast",
                "horizon": horizon,
                "native_panel": panel,
            }
        )
        task["task_version"] = "coherent-absolute-endpoint0"
        task["source_sha256"] = c.digest({"panel": panel, "MODEL": MODEL})
        comp = c.canonical(
            pg,
            family,
            J,
            [True],
            design,
            scenario_id,
            {},
            factor,
            optimistic_status,
            (task, L, limits),
        )
        bounds.append(comp)
    return {
        "upper_percent": 100 * sum(x["upper"] for x in bounds) / len(bounds),
        "continuous_upper_percent": 100 * sum(x["continuous_upper"] for x in bounds) / len(bounds),
        "bound_components": bounds,
    }


def native_state_component(panel, supplied, group, common, design, scenario, q, factor):
    """Evaluate a documented occasion or an explicitly unresolved roster remainder."""
    omitted = group is None
    if group is None:
        group = {
            "events": [],
            "timing_qualified": c.tri(
                [strict_tri(supplied.get("time_frame", {}).get("source_qualified")), None]
            ),
        }
    local_status = dict(
        supplied.get("coordinate_status", {a["id"]: "unknown" for a in panel["coordinates"]})
    )
    events = []
    for coordinate in panel["coordinates"]:
        native = coordinate["id"]
        if local_status[native] != "present":
            continue
        if not omitted and not any(e["coordinate"] == native for e in group["events"]):
            local_status[native] = "absent"
            continue
        selected, valid, _mode = selected_occasion(supplied, group, native)
        if valid is not True:
            local_status[native] = "absent" if valid is False else "unknown"
        else:
            events += [{**e, "time": 0} for e in selected]
    H, R, _, _ = c.event_model(panel, {**group, "events": events}, q)
    task, L, limits = c.definition(panel, "individual_state", factor)
    task["task_version"] = "source-selected-occasion-v1"
    task["horizon"] = "Qualified acquired occasion, not an imputed calendar date"
    task["estimand"] = (
        "Per-person registered native quantities at their explicitly selected acquisition occasion; linked cross-panel simultaneous state is a separate source-qualified relation task."
    )
    return c.canonical(
        panel,
        "individual_state",
        c.fisher(H, R),
        common,
        design,
        scenario,
        {},
        factor,
        local_status,
        (task, L, limits),
    )


def evaluate(design, factor=1.0, relations=None, scenario_registry=None):
    """Integrate fixed cross-panel tasks with six canonical foundation capabilities.

    Unknown time is preserved in the source binding and never assigned to baseline.
    Affected subgroup upper bounds are retained rather than reducing the roster.
    """
    from .multiscale import definition as temporal_definition
    from .multiscale import geometry as temporal_geometry

    relations = RELATIONS if relations is None else relations
    validate_raw(design)
    original_design = copy.deepcopy(design)
    if scenario_registry is not None:
        expected = {"q0.0625": 0.0625, "q0.25": 0.25, "q1": 1.0, "q2": 2.0}
        if scenario_registry != expected:
            raise ValueError("Only the frozen common-noise-grid-v1 registry is supported")
        design = copy.deepcopy(design)
        design["_noise_scenario_registry"] = copy.deepcopy(scenario_registry)
    prepared = copy.deepcopy(design)
    uncertain = {}
    qualified = {}
    for panel_id, panel in prepared["panels"].items():
        for group in panel.get("groups", []):
            key = (panel_id, group["group_id"])
            source_group = next(
                g
                for g in design["panels"][panel_id]["groups"]
                if g["group_id"] == group["group_id"]
            )
            timing = strict_tri(
                source_group.get(
                    "timing_qualified",
                    panel.get("time_frame", {}).get("source_qualified"),
                )
            )
            unknown_coordinates = {
                e["coordinate"]
                for e in source_group["events"]
                if e.get("time") is None and timing is not False
            }
            if timing is None:
                unknown_coordinates |= {e["coordinate"] for e in source_group["events"]}
            uncertain[key] = unknown_coordinates
            qualified[key] = timing
            group["events"] = [
                e for e in group["events"] if e.get("time") is not None and timing is True
            ]
    foundation, components = c.evaluate(prepared, factor)
    intermediate = {
        "input_sha256": c.digest(prepared),
        "result_sha256": c.digest(foundation),
        "summaries": copy.deepcopy([s["summary"] for s in foundation["scenarios"]]),
    }
    registry = c.registry()
    budget = relation_budgets(relations, registry)
    panels = {p["id"]: p for p in registry["panels"]}
    extra = []
    scores = [
        "lower_percent",
        "upper_percent",
        "continuous_lower_percent",
        "continuous_upper_percent",
    ]
    for scenario in foundation["scenarios"]:
        q = design.get("_noise_scenario_registry", c.SCENARIOS)[scenario["scenario_id"]]
        for row in scenario["rows"]:
            panel = panels[row["panel_id"]]
            supplied = design["panels"].get(panel["id"], {})
            groups = {g["group_id"]: g for g in supplied.get("groups", [])}
            common = [
                {"present": True, "absent": False, "unknown": None}.get(supplied.get("status")),
                supplied.get("operator_qualified"),
                design["gates"].get("measurement_semantics"),
                design["gates"].get("group_linkage_and_disjointness"),
            ]
            if design["lifecycle"] == "collected":
                common.append(design["gates"].get("collection_verified"))
            status = supplied.get(
                "coordinate_status", {a["id"]: "unknown" for a in panel["coordinates"]}
            )
            if row["family"] == "individual_state":
                # Per-group bounds retain the full roster; qualified opaque occasion
                # can support native state without pretending its calendar date is0.
                for part in row["parts"]:
                    group = groups.get(part.get("group_id"))
                    comp = native_state_component(
                        panel, supplied, group, common, design, scenario["scenario_id"], q, factor
                    )
                    extra.append(comp)
                    part.update(
                        {
                            k: comp[k]
                            for k in [
                                "lower",
                                "upper",
                                "continuous_lower",
                                "continuous_upper",
                                "canonical_receipt_sha256",
                            ]
                        }
                    )
                for key, small in zip(
                    scores, ["lower", "upper", "continuous_lower", "continuous_upper"]
                ):
                    row[key] = (
                        100 * sum(p["n"] * p[small] for p in row["parts"]) / design["cohort_n"]
                    )
            elif row["family"] == "trajectories":
                for horizon in row["parts"]:
                    for part in horizon["parts"]:
                        group = groups.get(part.get("group_id"))
                        if group is None or not uncertain.get((panel["id"], group["group_id"])):
                            continue
                        affected = uncertain[(panel["id"], group["group_id"])]
                        st = {
                            k: ("unknown" if k in affected and v == "present" else v)
                            for k, v in status.items()
                        }
                        pg, task = temporal_definition(panel, horizon["horizon_days"], factor)
                        known_group = next(
                            g
                            for g in prepared["panels"][panel["id"]]["groups"]
                            if g["group_id"] == group["group_id"]
                        )
                        H, R, _, _ = temporal_geometry(panel, known_group, q)
                        bound = c.canonical(
                            pg,
                            "trajectories",
                            c.fisher(H, R),
                            common,
                            design,
                            scenario["scenario_id"],
                            {},
                            factor,
                            st,
                            task,
                        )
                        extra.append(bound)
                        part["upper_canonical_receipt_sha256"] = bound["canonical_receipt_sha256"]
                        part["upper_percent"] = max(part["upper_percent"], 100 * bound["upper"])
                        part["continuous_upper_percent"] = max(
                            part["continuous_upper_percent"],
                            100 * bound["continuous_upper"],
                        )
                        part["uncertainty"] = (
                            "Unresolved timing in this participant pattern; full roster retained"
                        )
                    for key in scores:
                        horizon[key] = (
                            sum(p["n"] * p[key] for p in horizon["parts"]) / design["cohort_n"]
                        )
                for key in scores:
                    row[key] = sum(h[key] * h["temporal_weight"] for h in row["parts"])
            elif any(uncertain.get((panel["id"], g)) for g in groups) or (
                row["family"] == "population_variation"
                and sum(g["n"] for g in groups.values()) < design["cohort_n"]
            ):
                bound = aggregate_upper_bound(
                    panel,
                    row["family"],
                    supplied,
                    design,
                    factor,
                    scenario["scenario_id"],
                )
                bound_components = bound.get("bound_components", [])
                extra.extend(bound_components)
                if row["family"] == "population_variation" and bound_components:
                    row["parts"][0]["upper_canonical_receipt_sha256"] = bound_components[0][
                        "canonical_receipt_sha256"
                    ]
                elif bound_components:
                    for horizon, component in zip(row["parts"], bound_components):
                        horizon["parts"][0]["upper_canonical_receipt_sha256"] = component[
                            "canonical_receipt_sha256"
                        ]
                row["upper_percent"] = max(row["lower_percent"], bound["upper_percent"])
                row["continuous_upper_percent"] = max(
                    row["continuous_lower_percent"], bound["continuous_upper_percent"]
                )
                row["uncertainty"] = (
                    "Unresolved acquisitions or timing retain a conservative noiseless-acquisition outer bound with known failed family gates and finite roster retained; not an acquired precision or attainability certificate."
                )
        relational = [evaluate_relation(design, r, q, factor) for r in relations]
        for relation in relational:
            extra.extend(relation.pop("canonical_components"))
        scenario["cross_panel_relations"] = relational
        for summary in scenario["summary"]:
            family = summary["family"]
            for domain in summary["domains"]:
                rows = [
                    r
                    for r in scenario["rows"]
                    if r["family"] == family and r["domain"] == domain["domain"]
                ]
                native = {key: sum(r[key] for r in rows) / len(rows) for key in scores}
                if family in ["individual_state", "population_variation"]:
                    relevant = [
                        r
                        for r in relational
                        if r["relation_id"] in budget["domain_incidence"][domain["domain"]]
                    ]
                    for key in scores:
                        domain[key] = 0.75 * native[key] + 0.25 * sum(
                            r[family][key] for r in relevant
                        ) / len(relevant)
                    domain["native_component"] = native
                    domain["relation_fraction"] = 0.25
                else:
                    domain.update(native)
            for key in scores:
                summary[key] = sum(d[key] for d in summary["domains"]) / len(summary["domains"])
    foundation.update(
        {
            "schema": "anibench.linked-study-capability-candidate.v1",
            "cohort_n": design["cohort_n"],
            "source_input_sha256": c.digest(original_design),
            "qualified_numeric_time_subset_sha256": c.digest(prepared),
            "linkage_budget": budget,
            "selected_occasion_state_frame": "Native state can use qualified opaque acquisition occasion. Calendar time remains required for temporal/assignment tasks.",
            "limits": [
                "Cross-panel relationships currently extend individual state and population variation only.",
                "Unknown aggregate timing bounds in other families are conservative and not exact attainability certificates.",
                "Finite native-panel catalogue is not all biological information.",
            ],
        }
    )
    all_components = components + extra
    module_names = [
        "sufficient_statistics.py",
        "linked_workload.py",
        "compiler.py",
        "multiscale.py",
        "population_reml.py",
        "compare_metrics.py",
    ]
    module_paths = {
        name: (Path(__file__) if name == "linked_workload.py" else Path(c.__file__).parent / name)
        for name in module_names
    }
    foundation["foundation_intermediate"] = intermediate
    foundation["provenance"] = {
        "calculation_files": {
            name: "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in module_paths.items()
        },
        "relations_sha256": c.digest(relations),
        "budgets_sha256": c.digest(budget),
        "canonical_components_sha256": c.digest(all_components),
        "original_input_sha256": c.digest(original_design),
        "result_hash_rule": "SHA256 canonical sorted compact JSON excluding result_sha256 only",
    }
    foundation["result_sha256"] = c.digest(foundation)
    return foundation, all_components
