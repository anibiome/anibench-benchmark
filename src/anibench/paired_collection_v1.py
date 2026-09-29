# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Question-specific support from disjoint, partly observed acquisition patterns.

This adapter reuses the paired-question estimator. It never reconstructs a joint
roster from marginal assay counts. Shared reference covariance and ignorable
acquisition are explicit assumptions, not consequences of an assay inventory.
"""
from __future__ import annotations

import copy
import json

from jsonschema import Draft202012Validator

from .paired_question_v1 import (
    INPUT_SCHEMA as QUESTION_SCHEMA,
)
from .paired_question_v1 import digest, evaluate_paired_question, tri

EVALUATOR = "anibench.paired-collection.v1-candidate1"
_TEXT = {"type": "string", "minLength": 1, "pattern": r"\S"}
_TRI = {"type": ["boolean", "null"]}
_COUNT = {"type": "integer", "minimum": 0, "maximum": 9007199254740991}


def _object(properties, optional=()):
    return {"type": "object", "properties": properties,
            "required": [key for key in properties if key not in optional],
            "additionalProperties": False}


_OLD_DESIGN = QUESTION_SCHEMA["properties"]["design"]["properties"]
_PATTERN = _object({
    "pattern_id": _TEXT, "n_people": _COUNT,
    "closed_acquisition_inventory": _TRI,
    "controlled_arm_counts": copy.deepcopy(_OLD_DESIGN["controlled_arm_counts"]),
    "acquisitions": {"type": "array", "items": _object({
        "physical_id": _TEXT, "occasion_index": {"type": "integer", "enum": [0, 1]},
        "outputs": {"type": "array", "minItems": 1, "items": _object({
            "coordinate_id": _TEXT, "qualified": _TRI,
        })},
    })},
})
INPUT_SCHEMA = copy.deepcopy(QUESTION_SCHEMA)
INPUT_SCHEMA["properties"]["contract"] = {"const": "anibench.paired-collection-input.v1"}
INPUT_SCHEMA["properties"]["design"] = _object({
    "question_sha256": copy.deepcopy(_OLD_DESIGN["question_sha256"]),
    "lifecycle": copy.deepcopy(_OLD_DESIGN["lifecycle"]),
    "n_people": _COUNT, "closed_pattern_roster": _TRI,
    "patterns_are_disjoint": {"const": True},
    "homogeneous_reference_across_patterns": _TRI,
    "acquisition_independent_of_state": _TRI,
    "patterns": {"type": "array", "items": _PATTERN},
    "support": copy.deepcopy(_OLD_DESIGN["support"]),
    "metadata": {"type": "object"},
}, optional=("metadata",))


def _snapshot(payload):
    try:
        snapshot = json.loads(json.dumps(payload, allow_nan=False))
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Paired collection requires finite JSON values") from exc
    error = next(Draft202012Validator(INPUT_SCHEMA).iter_errors(snapshot), None)
    if error is not None:
        raise ValueError(f"Paired collection input violates schema ({error.validator})")
    return snapshot


def _patterns(design, names):
    """Canonicalize template slots; one physical assay can emit many quantities."""
    if type(design["n_people"]) is not int:
        raise ValueError("Population count must be an integer")
    patterns = {}
    for pattern in design["patterns"]:
        if type(pattern["n_people"]) is not int:
            raise ValueError("Pattern count must be an integer")
        physical, slots = {}, {}
        for acquisition in pattern["acquisitions"]:
            if type(acquisition["occasion_index"]) is not int:
                raise ValueError("Acquisition occasion index must be an integer")
            outputs = {}
            for output in acquisition["outputs"]:
                name, qualified = output["coordinate_id"], output["qualified"]
                if name not in names:
                    raise ValueError("Acquisition is outside the frozen question")
                if name in outputs and outputs[name] is not qualified:
                    raise ValueError("Conflicting repeated output qualification")
                outputs[name] = qualified
            canonical = {"occasion_index": acquisition["occasion_index"],
                         "outputs": dict(sorted(outputs.items()))}
            identity = acquisition["physical_id"]
            if identity in physical:
                if physical[identity] != canonical:
                    raise ValueError("Conflicting physical acquisition reuse")
                continue
            physical[identity] = canonical
            for name, qualified in outputs.items():
                slot = (name, acquisition["occasion_index"])
                if slot in slots:
                    raise ValueError("Repeated slot requires a qualified repeat-error adapter")
                slots[slot] = qualified
        arms = pattern["controlled_arm_counts"]
        if arms is not None and (any(type(n) is not int for n in arms) or sum(arms) != pattern["n_people"]):
            raise ValueError("Arm counts must partition each pattern")
        canonical = {key: value for key, value in pattern.items() if key != "acquisitions"}
        canonical["physical"] = dict(sorted(physical.items()))
        identity = pattern["pattern_id"]
        if identity in patterns:
            if patterns[identity][0] != canonical:
                raise ValueError("Conflicting pattern identity reuse")
            continue
        patterns[identity] = (canonical, slots)
    represented = sum(p[0]["n_people"] for p in patterns.values())
    if represented > design["n_people"]:
        raise ValueError("Disjoint patterns exceed the declared population")
    if design["closed_pattern_roster"] is True and represented != design["n_people"]:
        raise ValueError("Closed patterns must partition the declared population")
    return patterns, design["n_people"] - represented


def _requirements(question):
    molecules = [c["id"] for c in question["coordinates"] if c["domain"] == "molecular"]
    function = [c["id"] for c in question["coordinates"] if c["domain"] == "functional"]
    all_names = molecules + function

    def slots(names, times):
        return frozenset((name, t) for name in names for t in times)

    requirements = {}
    for domain, names in (("molecular", molecules), ("function", function)):
        requirements[domain + "_state"] = slots(names, [0])
        for suffix in ("individual_change", "mean_change"):
            requirements[domain + "_" + suffix] = slots(names, [0, 1])
    requirements["molecular_function_change_relation"] = slots(all_names, [0, 1])
    for key in ("exposure_aligned_function_change", "controlled_function_effect"):
        requirements[key] = slots(function, [0, 1])
    learning = {
        "mean_only": slots(function, [1]),
        "baseline_function": slots(function, [0, 1]),
        "baseline_function_and_molecular": slots(function, [0, 1]) | slots(molecules, [0]),
    }
    return requirements, learning


def _support_counts(required, patterns, omitted):
    lower, upper = 0, omitted
    arm_lower = [0, 0]
    possible_known_arms = [0, 0]
    all_definite_arms_known = True
    for pattern, slots in patterns.values():
        absent = False if pattern["closed_acquisition_inventory"] is True else None
        supported = tri([slots.get(slot, absent) for slot in required])
        n = pattern["n_people"]
        arms = pattern["controlled_arm_counts"]
        if supported is not False:
            upper += n
            if arms is not None:
                possible_known_arms = [a + b for a, b in zip(possible_known_arms, arms)]
        if supported is True:
            lower += n
            if arms is None and n:
                all_definite_arms_known = False
            elif arms is not None:
                arm_lower = [a + b for a, b in zip(arm_lower, arms)]
    return lower, upper, arm_lower, possible_known_arms, all_definite_arms_known


def _arm_endpoints(upper, arm_lower, possible_known_arms, known):
    # The lower endpoint can use only definitely acquired, known-arm people.
    # The upper endpoint allows unknown eligible people in the most informative
    # feasible allocation; this is an outer bound, not an imputed allocation.
    lower_arms = arm_lower if known else None
    # At maximum eligible support, all possibly acquired known-arm patterns
    # retain their declared allocations. Only unassigned/omitted people may
    # receive an optimistic allocation; unknown acquisition cannot rebalance a
    # known arm partition.
    n0 = min(max(upper // 2, possible_known_arms[0]), upper - possible_known_arms[1])
    upper_arms = [n0, upper - n0]
    return lower_arms, upper_arms


def evaluate_paired_collection(payload):
    """Evaluate each estimand on its own complete support, with outer bounds.

    Partly observed people can support marginal tasks. They do not acquire joint
    information merely because different people supply the other measurements.
    """
    payload = _snapshot(payload)
    question, scenario, design = (payload[k] for k in ("question", "scenario", "design"))
    names = [c["id"] for c in question["coordinates"]]
    patterns, omitted = _patterns(design, names)
    requirements, routes = _requirements(question)
    support = copy.deepcopy(design["support"])
    support["reference_model_applicable"] = tri([
        support["reference_model_applicable"], design["homogeneous_reference_across_patterns"],
    ])
    # Selection affects population estimands and learning, not measurement error
    # of an observed individual's reading. Each endpoint uses the same model.
    support["declared_population"] = tri([
        support["declared_population"], design["acquisition_independent_of_state"],
    ])
    cache = {}

    def endpoint(required, n, arms):
        key = (tuple(sorted(required)), n, None if arms is None else tuple(arms))
        if key not in cache:
            candidate = {"question_sha256": design["question_sha256"],
                         "lifecycle": design["lifecycle"], "n_independent_complete": n,
                         "closed_acquisition_inventory": True, "controlled_arm_counts": arms,
                         "support": support,
                         "observations": [{"physical_id": digest([name, t]), "coordinate_id": name,
                                           "occasion_index": t, "qualified": True}
                                          for name, t in sorted(required)]}
            cache[key] = evaluate_paired_question({"contract": "anibench.paired-question-input.v1",
                                                  "question": question, "scenario": scenario,
                                                  "design": candidate})
        return cache[key]

    # Validate the full question/scenario even when there are no usable people.
    endpoint(frozenset(), 0, None)
    results, learning, coverage = {}, {}, {}
    for key, required in {**requirements, **routes}.items():
        lower, upper, arm_lower, possible_known_arms, known = _support_counts(required, patterns, omitted)
        lo_arms, hi_arms = _arm_endpoints(upper, arm_lower, possible_known_arms, known)
        controlled = key == "controlled_function_effect"
        lo = endpoint(required, lower, lo_arms if controlled else None)
        hi = endpoint(required, upper, hi_arms if controlled else None)
        count = {"lower": lower, "upper": upper}
        coverage[key] = {"independent_people": count,
                         "required_slots": [[name, t] for name, t in sorted(required)]}
        if key in requirements:
            low, high = lo["results"][key], hi["results"][key]
            interval = {"lower": low["adequacy_percent"]["lower"],
                        "upper": high["adequacy_percent"]["upper"]}
            if interval["lower"] > interval["upper"] + 1e-10:
                raise ValueError("Inconsistent acquisition precision bounds")
            results[key] = {"state": low["state"] if low == high else "bounded",
                            "independent_people": count, "adequacy_percent": interval,
                            "lower_support_result": low, "upper_support_result": high}
            if controlled:
                results[key]["arm_count_bounds"] = {
                    "definite_known_arms": arm_lower,
                    "possible_known_arms": possible_known_arms,
                    "optimistic_feasible_allocation": hi_arms,
                    "meaning": "Per-task bounding allocation; not an inferred actual arm roster",
                }
        else:
            low = lo["conditional_functional_learning"][key]
            high = hi["conditional_functional_learning"][key]
            learning[key] = {"independent_people": count,
                             "lower_support_result": low, "upper_support_result": high,
                             "state": low["state"] if low == high else "bounded"}
    learning["observed_held_out_prediction"] = {"state": "not_evaluated"}
    learning["selection_scope"] = "Route-specific analytic reference risks; no empirical selection or pooled route winner"
    answer = {
        "contract": "anibench.paired-collection-result.v1", "evaluator": EVALUATOR,
        "question_sha256": digest(question), "scenario_sha256": digest(scenario),
        "input_sha256": digest(payload), "question": question["question"],
        "lifecycle": design["lifecycle"], "scope": "Conditional one-question partial-collection analysis",
        "n_people": design["n_people"], "omitted_people": omitted,
        "canonical_patterns": len(patterns),
        "canonical_physical_slots": sum(len(p[0]["physical"]) for p in patterns.values()),
        "coverage": coverage, "results": results, "conditional_functional_learning": learning,
        "uncertainty": "Outer bounds from unresolved acquisition support under one shared covariance scenario; not confidence intervals or jointly attained study designs",
        "model_assumptions": scenario["assumptions"], "public_rank_emission_permitted": False,
    }
    answer["calculation_sha256"] = digest({"evaluator": EVALUATOR, "question": question,
                                           "scenario": scenario, "results": results, "learning": learning})
    answer["receipt_sha256"] = digest(answer)
    return answer
