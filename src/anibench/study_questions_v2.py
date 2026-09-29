# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Bind biological questions to existing evaluators and fixed category budgets.

Conditional integration adapter. No new observation, covariance or causal solver.
The trusted profile is a reviewed convention, not inferred biological truth.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from fractions import Fraction

from jsonschema import Draft202012Validator

from anibench.benchmark_v1 import _adequacy, summarize_attainment, summarize_precision
from anibench.cross_domain_collection_v1 import (
    QUESTION_SCHEMA as CROSS_DOMAIN_QUESTION_SCHEMA,
)
from anibench.cross_domain_collection_v1 import (
    evaluate_cross_domain_collection,
    native_key,
)
from anibench.estimator_moments_v1 import (
    _design as moment_design,
)
from anibench.estimator_moments_v1 import (
    _matrix as moment_matrix,
)
from anibench.estimator_moments_v2 import (
    evaluate_estimator_moments,
)
from anibench.estimator_moments_v2 import (
    validate_definition as validate_moment_definition,
)
from anibench.finite_suites_v1 import scientific_frame_sha256
from anibench.paired_collection_v1 import evaluate_paired_collection
from anibench.paired_question_v1 import INPUT_SCHEMA as PAIRED_SCHEMA
from anibench.question_routes_v1 import (
    _noise,
    compile_question_routes,
    digest,
    evaluate_question_routes,
)

PAIRED_OUTCOMES = frozenset({
    "molecular_state", "function_state",
    "molecular_individual_change", "function_individual_change",
    "molecular_mean_change", "function_mean_change",
    "molecular_function_change_relation", "exposure_aligned_function_change",
    "controlled_function_effect",
})

COLLECTION_ENGINES = {
    "paired_collection": (evaluate_paired_collection, PAIRED_OUTCOMES,
                          PAIRED_SCHEMA["properties"]["question"],
                          "anibench.paired-collection-input.v1"),
    "cross_domain_collection": (evaluate_cross_domain_collection,
                                frozenset(native_key(k) for k in PAIRED_OUTCOMES),
                                CROSS_DOMAIN_QUESTION_SCHEMA,
                                "anibench.cross-domain-collection-input.v1"),
}


def _outcome_names(engine):
    return {"target"} if engine in {"question_routes", "estimator_moments"} else COLLECTION_ENGINES[engine][1]


class StudyQuestionError(ValueError):
    """A study does not match the frozen question/reference contract."""


def _snapshot(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise StudyQuestionError("Expected finite JSON values") from exc


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise StudyQuestionError("Missing or unexpected contract fields")


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise StudyQuestionError("Expected nonempty text")


def _indexed(rows, key):
    if not isinstance(rows, list) or not rows:
        raise StudyQuestionError("Expected a nonempty frozen list")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or key not in row:
            raise StudyQuestionError("Missing frozen identifier")
        _text(row[key])
        if row[key] in result:
            raise StudyQuestionError("Duplicate frozen identifier")
        result[row[key]] = row
    return result


def _conjunction(states):
    states = list(states)
    if not states:
        raise StudyQuestionError("Empty requirement conjunction")
    if "not_attained" in states:
        return "not_attained"
    return "unknown" if "unknown" in states else "attained"


def _disjunction(states):
    states = list(states)
    if not states:
        raise StudyQuestionError("Empty native-frame disjunction")
    if "attained" in states:
        return "attained"
    return "unknown" if "unknown" in states else "not_attained"


def _validate_outcomes(entry, questions):
    identity = entry["question_id"]
    if identity not in questions:
        raise StudyQuestionError("Unregistered biological question")
    outcomes = entry["outcomes"]
    allowed = _outcome_names(questions[identity]["engine"])
    if (not isinstance(outcomes, list) or not outcomes
            or any(not isinstance(x, str) for x in outcomes)
            or len(set(outcomes)) != len(outcomes) or not set(outcomes) <= allowed):
        raise StudyQuestionError("Unknown or duplicate question outcome")


def _alternative_category(category, scenario_questions):
    """One frame must satisfy all outcomes in every supplied scenario.

    A single scenario computes max_frame min_outcome. Multiple scenarios compute
    max_frame min_scenario min_outcome, never scenario-dependent route switching.
    Different category requirements do not establish a common linked frame.
    """
    rows, precision, details = [], [], []
    for entry in category["requirements"]:
        alternatives = []
        for alternative in entry["alternatives"]:
            identity = alternative["question_id"]
            selected = [{name: questions[identity]["outcomes"][name]
                         for name in alternative["outcomes"]}
                        for questions in scenario_questions]
            outcomes = [row for scenario in selected for row in scenario.values()]
            alternatives.append({
                **alternative,
                "attainment": _conjunction(row["attainment"] for row in outcomes),
                "precision_toward_targets": {
                    key: min(row["precision_toward_target"][key] for row in outcomes)
                    for key in ("lower_percent", "upper_percent")},
                "scenario_outcome_results": selected,
            })
        state = _disjunction(a["attainment"] for a in alternatives)
        bounds = {key: max(a["precision_toward_targets"][key] for a in alternatives)
                  for key in ("lower_percent", "upper_percent")}
        identity, weight = entry["requirement_id"], entry["weight"]
        rows.append({"canonical_id": identity, "weight": weight, "attainment": state})
        precision.append({"canonical_id": identity, "weight": weight,
                          "lower": bounds["lower_percent"] / 100,
                          "upper": bounds["upper_percent"] / 100})
        details.append({
            **entry, "attainment": state, "precision_toward_targets": bounds,
            "alternative_results": alternatives,
            "attaining_question_ids": sorted(a["question_id"] for a in alternatives
                                             if a["attainment"] == "attained"),
            "precision_witness_question_ids": {
                key: sorted(a["question_id"] for a in alternatives
                            if a["precision_toward_targets"][key] == bounds[key])
                for key in bounds},
        })
    return {"category_id": category["category_id"], "label": category["label"],
            "question": category["question"], **summarize_attainment(rows),
            "requirements": details, "precision_toward_targets": summarize_precision(precision)}


def _moment_loss_matrix(functional, order):
    # Canonical exact quadratic loss prevents an identical one-coordinate MSE
    # from receiving another budget under the diagonal-loss representation.
    if "loss_weights" in functional:
        w = [Fraction(str(functional["loss_weights"][i])) for i in order]
        return [[str(w[i] if i == j else 0) for j in range(len(w))] for i in range(len(w))]
    c = [Fraction(str(functional["coefficients"][i])) for i in order]
    return [[str(x * y) for y in c] for x in c]


def _semantic_frame(question):
    """Reject renamed exact frames; this does not resolve biological synonyms.

    The biological_identity registry remains necessary across equivalent units,
    representations and engines. Its correctness requires scientific review.
    """
    definition = question["definition"]
    if question["engine"] == "estimator_moments":
        order = sorted(range(len(definition["estimators"])),
                       key=lambda i: digest(definition["estimators"][i]["target"]))
        return digest({"engine": "estimator_moments",
                       "targets": [definition["estimators"][i]["target"] for i in order],
                       "population_scope": definition["population_scope"], "context": definition["context"],
                       "functionals": sorted([{"loss_matrix": _moment_loss_matrix(f, order),
                                                "unit": f["unit"]}
                                               for f in definition["functionals"]], key=digest)})
    if question["engine"] == "question_routes":
        # Route catalogues, provenance, prior, task labels and precision cutoffs
        # cannot create another biological question for the same target frame.
        task = copy.deepcopy(definition["task"])
        task["model_sha256"] = digest({"model": "route-independent identity"})
        task["source_sha256"] = digest({"source": "identity only"})
        size = len(task["parameter_units"])
        order = sorted(range(size), key=lambda i: digest(definition["parameters"][i]))
        task["parameter_units"] = [task["parameter_units"][i] for i in order]
        for functional in task["functionals"]:
            functional["coefficients"] = [functional["coefficients"][i] for i in order]
        task["prior_precision"] = [[int(i == j) for j in range(size)] for i in range(size)]
        return digest({"engine": "question_routes", "parameters": [definition["parameters"][i] for i in order],
                       "frame": scientific_frame_sha256(task)})
    coordinates = []
    for coordinate in definition["coordinates"]:
        # Native domain labels classify observations; reclassifying an identical
        # quantity cannot manufacture another question budget. Preserve the
        # computational role, native quantity definition and units.
        c = {k: v for k, v in coordinate.items()
             if k not in {"id", "domain", "biological_domain", "role"}}
        c["role"] = coordinate.get("role") or (
            "observer" if coordinate["domain"] == "molecular" else "function")
        coordinates.append(c)
    return digest({"engine": "paired_collection", "coordinates": sorted(coordinates, key=digest), **{
        key: definition[key] for key in
        ("population_scope", "occasions_days", "functional_operator")
    }})


def _validate_profile(profile):
    _keys(profile, {"contract", "profile_id", "scope", "selection_rationale",
                    "weighting_rationale", "questions", "categories", "scenarios"})
    if profile["contract"] not in {"anibench.study-question-profile.v1", "anibench.study-question-profile.v2",
                                   "anibench.study-question-profile.v3", "anibench.study-question-profile.v4"}:
        raise StudyQuestionError("Unknown study-question profile")
    alternatives_version = profile["contract"] in {"anibench.study-question-profile.v3", "anibench.study-question-profile.v4"}
    for name in ("profile_id", "scope", "selection_rationale", "weighting_rationale"):
        _text(profile[name])
    questions = _indexed(profile["questions"], "question_id")
    identities, frames = set(), set()
    for question in questions.values():
        _keys(question, {"question_id", "biological_identity", "engine", "definition"})
        _text(question["biological_identity"])
        if question["biological_identity"] in identities:
            raise StudyQuestionError("Duplicate biological question identity")
        identities.add(question["biological_identity"])
        definition = question["definition"]
        if question["engine"] == "estimator_moments":
            if profile["contract"] != "anibench.study-question-profile.v4":
                raise StudyQuestionError("Estimator moments require a v4 profile")
            validate_moment_definition(definition)
        elif question["engine"] == "question_routes":
            compile_question_routes({
                "contract": "anibench.question-routes-request.v1",
                "definition_sha256": digest(definition), "observations": [],
                "noise_order": [], "noise_covariance": [], "closed_inventory": None,
                "evidence": {"identifiability": None, "collection_verified": None, "support": []},
            }, trusted_definitions={digest(definition): definition})
        elif question["engine"] in COLLECTION_ENGINES:
            if (question["engine"] == "cross_domain_collection"
                    and profile["contract"] == "anibench.study-question-profile.v1"):
                raise StudyQuestionError("Native-domain questions require a v2 or v3 profile")
            error = next(Draft202012Validator(COLLECTION_ENGINES[question["engine"]][2])
                         .iter_errors(definition), None)
            if error is not None:
                raise StudyQuestionError("Invalid paired biological question definition")
        else:
            raise StudyQuestionError("Unknown question evaluator")
        frame = _semantic_frame(question)
        if frame in frames:
            raise StudyQuestionError("Renamed equivalent question frame")
        frames.add(frame)
    categories = _indexed(profile["categories"], "category_id")
    used = set()
    for category in categories.values():
        entry_key = "requirements" if alternatives_version else "questions"
        _keys(category, {"category_id", "label", "question", entry_key})
        _text(category["label"])
        _text(category["question"])
        entries = _indexed(category[entry_key], "requirement_id" if alternatives_version else "question_id")
        category_frames = set()
        for identity, entry in entries.items():
            _keys(entry, {"requirement_id", "rationale", "alternatives", "weight"}
                  if alternatives_version else {"question_id", "outcomes", "weight"})
            if type(entry["weight"]) is not int or entry["weight"] <= 0:
                raise StudyQuestionError("Question budget must be a positive integer")
            if alternatives_version:
                _text(entry["rationale"])
                alternatives = _indexed(entry["alternatives"], "question_id")
                for alternative in alternatives.values():
                    _keys(alternative, {"question_id", "outcomes"})
                    _validate_outcomes(alternative, questions)
                    qid = alternative["question_id"]
                    if qid in category_frames:
                        raise StudyQuestionError("Native frame reused in another requirement budget")
                    category_frames.add(qid)
                    used.add(qid)
            else:
                _validate_outcomes(entry, questions)
                used.add(identity)
    if used != set(questions):
        raise StudyQuestionError("Every frozen question must appear in the workload")
    scenarios = _indexed(profile["scenarios"], "scenario_id")
    paired_ids = {qid for qid, q in questions.items() if q["engine"] in COLLECTION_ENGINES}
    for scenario in scenarios.values():
        _keys(scenario, {"scenario_id", "rationale", "paired_biological_covariance"})
        _text(scenario["rationale"])
        reference = scenario["paired_biological_covariance"]
        if not isinstance(reference, dict) or set(reference) != paired_ids:
            raise StudyQuestionError("Each scenario must freeze every paired biological reference")
        # Validate semantics and covariance even when every study omits a question.
        # This neutral input is validation only; it never supplies result evidence.
        for identity in paired_ids:
            definition = questions[identity]["definition"]
            binding = digest(definition)
            support_names = PAIRED_SCHEMA["properties"]["design"]["properties"]["support"]["properties"]
            evaluator, _, _, input_contract = COLLECTION_ENGINES[questions[identity]["engine"]]
            evaluator({
                "contract": input_contract, "question": definition,
                "scenario": {"question_sha256": binding, "biological_covariance": reference[identity],
                             "measurement_error_covariance": None,
                             "error_covariance_treated_as_known": None,
                             "assumptions": ["Profile validation only; no data or attainment supplied"]},
                "design": {"question_sha256": binding, "lifecycle": "hypothetical", "n_people": 0,
                           "closed_pattern_roster": True, "patterns_are_disjoint": True,
                           "homogeneous_reference_across_patterns": None,
                           "acquisition_independent_of_state": None, "patterns": [],
                           "support": {name: None for name in support_names}},
            })
    return questions, categories, scenarios


def _paired_outcomes(receipt, names=PAIRED_OUTCOMES):
    result = {}
    for key in names:
        row = receipt["results"][key]
        low, high = row["lower_support_result"]["state"], row["upper_support_result"]["state"]
        failed = high in {"not_attained", "not_supported"}
        if low == "attained" and failed:
            raise StudyQuestionError("Inconsistent nested paired result")
        result[key] = {
            "attainment": "attained" if low == "attained" else "not_attained" if failed else "unknown",
            "precision_toward_target": {
                "lower_percent": row["adequacy_percent"]["lower"],
                "upper_percent": row["adequacy_percent"]["upper"],
            },
            "independent_people": row["independent_people"],
        }
    return result


def _unique_json(rows):
    return sorted({digest(row): row for row in rows}.values(), key=digest)


def _design_frame(question, payload):
    """Freeze acquisition geometry across uncertainty scenarios, not quality assumptions."""
    if payload is None:
        return None
    if question["engine"] == "estimator_moments":
        return moment_design(payload["design"], question["definition"])[0]
    if question["engine"] == "question_routes":
        return {"closed_inventory": payload["closed_inventory"],
                "observations": _unique_json([
                    {k: v for k, v in row.items() if k != "qualified"}
                    for row in payload["observations"]])}
    design = payload["design"]
    patterns = []
    for pattern in design["patterns"]:
        acquisitions = [
            {**a, "outputs": _unique_json([
                {k: v for k, v in output.items() if k != "qualified"}
                for output in a["outputs"]])}
            for a in pattern["acquisitions"]]
        patterns.append({**pattern, "acquisitions": _unique_json(acquisitions)})
    return {"n_people": design["n_people"],
            "closed_pattern_roster": design["closed_pattern_roster"],
            "patterns": _unique_json(patterns)}


def _check_shared_routes(inputs, questions):
    """Global physical outputs must agree within a single assumption scenario.

    Shared route observations require consistent covariance entries and a
    valid full joint noise frame. Incomplete covariance-completion problems
    are rejected instead of inventing missing correlations.
    Paired acquisitions are per-pattern templates, not individual route IDs.
    Reusing their names across engines is ambiguous and is rejected.
    """
    physical, route_frames, route_ids, template_ids = {}, [], set(), set()
    moment_ids = set()
    for identity, question in questions.items():
        payload = inputs.get(identity)
        if payload is None:
            continue
        if question["engine"] == "estimator_moments":
            moment_ids.update(a["physical_acquisition_id"] for a in payload["design"]["acquisitions"])
            continue
        if question["engine"] in COLLECTION_ENGINES:
            template_ids.update(a["physical_id"] for p in payload["design"]["patterns"]
                                for a in p["acquisitions"])
            continue
        for row in payload["observations"]:
            pair = (row["physical_acquisition_id"], row["physical_output_id"])
            route_ids.add(pair[0])
            value = (row["signature"], row["qualified"])
            if pair in physical and physical[pair] != value:
                raise StudyQuestionError("Conflicting global physical output signature or qualification")
            physical[pair] = value
        order = [tuple(pair) for pair in payload["noise_order"]]
        covariance = payload["noise_covariance"]
        frame = None if covariance is None else {
            (a, b): covariance[i][j]
            for i, a in enumerate(order) for j, b in enumerate(order)}
        route_frames.append((set(order), frame))
    pending = list(route_frames)
    while pending:
        output_set, frame = pending.pop()
        members = [(output_set, frame)]
        output_set = set(output_set)
        while True:
            linked = [item for item in pending if item[0] & output_set]
            if not linked:
                break
            for item in linked:
                pending.remove(item)
                output_set.update(item[0])
                members.append(item)
        if len(members) == 1:
            continue  # Its original engine already checked the complete matrix.
        known = {}
        for _, block in members:
            for pair, value in (block or {}).items():
                if pair in known and known[pair] != value:
                    raise StudyQuestionError("Conflicting shared physical output covariance")
                known[pair] = value
        if not known:
            continue  # Every participating original engine remains unresolved.
        order = sorted(output_set)
        if any((a, b) not in known for a in order for b in order):
            raise StudyQuestionError("Shared outputs require a complete joint noise frame; covariance completion is unsupported")
        try:
            _noise([[known[a, b] for b in order] for a in order], len(order))
        except ValueError as exc:
            raise StudyQuestionError("Shared physical noise model is not jointly valid") from exc
    if route_ids & template_ids:
        raise StudyQuestionError("Cross-engine physical identity needs an explicit template mapping")
    if moment_ids & (route_ids | template_ids):
        raise StudyQuestionError("Shared moment/raw acquisitions need an explicit cross-engine mapping")


def _check_shared_moments(inputs, questions):
    """Keep shared native outputs and estimator moments coherent, without pooling."""
    physical, estimators, frames = {}, {}, []
    for identity, question in questions.items():
        payload = inputs.get(identity)
        if question["engine"] != "estimator_moments" or payload is None:
            continue
        definition = question["definition"]
        design, moments = payload["design"], payload["moments"]
        input_map = {row["estimator_id"]: row for row in design["estimator_inputs"]}
        for row in design["acquisitions"]:
            key = (row["physical_acquisition_id"], row["physical_output_id"])
            if key in physical and physical[key] != row["signature"]:
                raise StudyQuestionError("Conflicting shared moment physical output signature")
            physical[key] = row["signature"]
        order = []
        for i, estimator in enumerate(definition["estimators"]):
            mapped = input_map[estimator["estimator_id"]]
            key = digest({"estimator": {k: v for k, v in estimator.items() if k != "estimator_id"},
                          "population_scope": definition["population_scope"], "context": definition["context"],
                          "inputs": sorted({tuple(p) for p in mapped["physical_outputs"]})})
            bias = (None if moments["bias_lower"] is None else moments["bias_lower"][i],
                    None if moments["bias_upper"] is None else moments["bias_upper"][i])
            value = (bias, mapped["estimable"])
            if key in estimators and estimators[key] != value:
                raise StudyQuestionError("Conflicting shared estimator bias or qualification")
            estimators[key] = value
            order.append(key)
        frames.append((set(order), {name: None if moments[name] is None else {
            (a, b): moments[name][i][j] for i, a in enumerate(order) for j, b in enumerate(order)}
            for name in ("covariance_lower", "covariance_upper")}))
    pending = list(frames)
    while pending:
        keys, frame = pending.pop()
        keys, members = set(keys), [frame]
        while True:
            joined = [item for item in pending if keys & item[0]]
            if not joined:
                break
            for item in joined:
                pending.remove(item)
                keys.update(item[0])
                members.append(item[1])
        if len(members) == 1:
            continue
        complete = {}
        for name in ("covariance_lower", "covariance_upper"):
            known = {}
            for member in members:
                for pair, value in (member[name] or {}).items():
                    if pair in known and known[pair] != value:
                        raise StudyQuestionError("Conflicting shared estimator covariance bound")
                    known[pair] = value
            if not known:
                complete[name] = None
                continue
            order = sorted(keys)
            if any((a, b) not in known for a in order for b in order):
                raise StudyQuestionError("Shared estimator bounds require a complete joint covariance frame")
            complete[name] = moment_matrix([[known[a, b] for b in order] for a in order], len(order))
        if all(complete[name] is not None for name in complete):
            from anibench.estimator_moments_v1 import _psd

            low, high = complete["covariance_lower"], complete["covariance_upper"]
            _psd([[high[i][j] - low[i][j] for j in range(len(keys))] for i in range(len(keys))])


def evaluate_study_questions(request: Mapping, *, trusted_profiles: Mapping):
    """Execute original engine inputs; never accept precomputed question scores.

    Each question has one fixed budget in a category. Its declared outcomes are
    conjunctive. Physical measurement routes do not receive separate votes.
    Missing question inputs remain in the denominator as unresolved evidence.
    """
    request, registry = _snapshot(request), _snapshot(trusted_profiles)
    _keys(request, {"contract", "profile_sha256", "study_id", "lifecycle", "scenarios"})
    if request["contract"] not in {"anibench.study-questions-request.v1", "anibench.study-questions-request.v2",
                                   "anibench.study-questions-request.v3", "anibench.study-questions-request.v4"}:
        raise StudyQuestionError("Unknown study-question request")
    key = request["profile_sha256"]
    if not isinstance(key, str) or key not in registry or digest(registry[key]) != key:
        raise StudyQuestionError("Untrusted or stale biological workload")
    profile = registry[key]
    questions, categories, frozen_scenarios = _validate_profile(profile)
    version = profile["contract"].rsplit(".", 1)[1]
    if request["contract"] != "anibench.study-questions-request." + version:
        raise StudyQuestionError("Request and profile versions must match")
    _text(request["study_id"])
    lifecycle = request["lifecycle"]
    if not isinstance(lifecycle, str) or lifecycle not in {"planned", "hypothetical", "realized"}:
        raise StudyQuestionError("Unknown study lifecycle")
    scenarios = _indexed(request["scenarios"], "scenario_id")
    if set(scenarios) != set(frozen_scenarios):
        raise StudyQuestionError("Expected exactly the frozen common scenario set")
    for question in questions.values():
        if question["engine"] == "question_routes":
            expected = "realized_record" if lifecycle == "realized" else "conditional_design"
            if question["definition"]["task"]["claim_lane"] != expected:
                raise StudyQuestionError("Route claim lane differs from study lifecycle")
    results = []
    design_frames = {}
    for scenario_id, frozen in frozen_scenarios.items():
        scenario = scenarios[scenario_id]
        _keys(scenario, {"scenario_id", "inputs"})
        inputs = scenario["inputs"]
        if not isinstance(inputs, dict) or not set(inputs) <= set(questions):
            raise StudyQuestionError("Unexpected question input")
        question_results = {}
        for identity, question in questions.items():
            definition = question["definition"]
            payload = inputs.get(identity)
            if payload is None:
                names = _outcome_names(question["engine"])
                question_results[identity] = {
                    "outcomes": {name: {"attainment": "unknown", "precision_toward_target": {
                        "lower_percent": 0.0, "upper_percent": 100.0}}
                        for name in sorted(names)},
                    "receipt": None, "reason": "No input supplied; frozen question mass retained",
                }
                if identity in design_frames and design_frames[identity] is not None:
                    raise StudyQuestionError("Scenario changed acquisition geometry; use a separate design request")
                design_frames[identity] = None
                continue
            if question["engine"] == "estimator_moments":
                if not isinstance(payload, dict) or payload.get("definition_sha256") != digest(definition):
                    raise StudyQuestionError("Moment input changed the registered estimator definition")
                if payload.get("lifecycle") != lifecycle:
                    raise StudyQuestionError("Moment claim lane differs from study lifecycle")
                receipt = evaluate_estimator_moments(payload, trusted_definitions={digest(definition): definition})
                outcomes = {"target": {"attainment": receipt["attainment"],
                                      "precision_toward_target": receipt["precision_toward_target"]}}
            elif question["engine"] == "question_routes":
                if not isinstance(payload, dict) or payload.get("definition_sha256") != digest(definition):
                    raise StudyQuestionError("Route input changed the registered question")
                receipt = evaluate_question_routes(payload, trusted_definitions={digest(definition): definition})
                lower = _adequacy(receipt["endpoints"]["confirmed"], {"task": definition["task"]})[0]
                upper = _adequacy(receipt["endpoints"]["possible"], {"task": definition["task"]})[1]
                if lower > upper:
                    raise StudyQuestionError("Inconsistent route precision bounds")
                outcomes = {"target": {"attainment": receipt["attainment"],
                                      "precision_toward_target": {
                                          "lower_percent": 100 * lower, "upper_percent": 100 * upper}}}
            else:
                if not isinstance(payload, dict) or payload.get("question") != definition:
                    raise StudyQuestionError("Paired input changed the registered question")
                if payload.get("design", {}).get("lifecycle") != lifecycle:
                    raise StudyQuestionError("Paired claim lane differs from study lifecycle")
                if payload.get("scenario", {}).get("biological_covariance") != frozen["paired_biological_covariance"][identity]:
                    raise StudyQuestionError("Study changed the frozen biological reference")
                evaluator, names, _, _ = COLLECTION_ENGINES[question["engine"]]
                receipt = evaluator(payload)
                outcomes = _paired_outcomes(receipt, names)
            frame = _design_frame(question, payload)
            if identity in design_frames and frame != design_frames[identity]:
                raise StudyQuestionError("Scenario changed acquisition geometry; use a separate design request")
            design_frames[identity] = frame
            question_results[identity] = {"outcomes": outcomes, "receipt": receipt}
        _check_shared_routes(inputs, questions)
        _check_shared_moments(inputs, questions)
        category_results = []
        for category in categories.values():
            if version in {"v3", "v4"}:
                category_results.append(_alternative_category(category, [question_results]))
                continue
            rows, details, precision = [], [], []
            for entry in category["questions"]:
                identity = entry["question_id"]
                outcomes = question_results[identity]["outcomes"]
                state = _conjunction(outcomes[name]["attainment"] for name in entry["outcomes"])
                rows.append({"canonical_id": identity, "weight": entry["weight"], "attainment": state})
                bounds = {key: min(outcomes[name]["precision_toward_target"][key]
                                   for name in entry["outcomes"])
                          for key in ("lower_percent", "upper_percent")}
                precision.append({"canonical_id": identity, "weight": entry["weight"],
                                  "lower": bounds["lower_percent"] / 100,
                                  "upper": bounds["upper_percent"] / 100})
                details.append({**entry, "attainment": state,
                                "precision_toward_targets": bounds,
                                "outcome_results": {name: outcomes[name] for name in entry["outcomes"]}})
            category_results.append({
                "category_id": category["category_id"], "label": category["label"],
                "question": category["question"], **summarize_attainment(rows), "questions": details,
                "precision_toward_targets": summarize_precision(precision),
            })
        results.append({"scenario_id": scenario_id, "categories": category_results,
                        "questions": question_results,
                        "reference_attainment": _conjunction(
                            row["attainment"] for c in category_results
                            for row in c["requirements" if version in {"v3", "v4"} else "questions"]),
                        "assumption_scope": frozen["rationale"]})
    envelope = []
    for i, category in enumerate(categories.values()):
        rows = [scenario["categories"][i] for scenario in results]
        envelope.append({"category_id": category["category_id"], "label": category["label"],
                         "lower_percent": min(row["passed_percent"] for row in rows),
                         "upper_percent": max(row["upper_percent"] for row in rows),
                         "precision_toward_targets": {
                             "lower_percent": min(row["precision_toward_targets"]["lower_percent"] for row in rows),
                             "upper_percent": max(row["precision_toward_targets"]["upper_percent"] for row in rows)}})
    result = {
        "contract": "anibench.study-questions-result." + version, "study_id": request["study_id"],
        "lifecycle": lifecycle, "profile_sha256": key, "profile_id": profile["profile_id"],
        "request_sha256": digest(request), "metric_label": "Biological requirements met (%)",
        "metric_meaning": "Passed fixed biological-question weight divided by all question weight in each category",
        "scenarios": results, "envelope": envelope,
        "robust_reference_attainment": _conjunction(s["reference_attainment"] for s in results),
        "envelope_joint_attainability_established": False,
        "uncertainty": "Scenario and unresolved-question outer bounds; not confidence intervals",
        "scope": profile["scope"], "profile": profile,
        "design_frame_sha256": digest(design_frames),
        "scenario_semantics": "Quality/model uncertainty for one fixed acquisition design; design changes require separate requests",
        "joint_cross_question_inference_established": False,
        "biological_calibration_established": False, "public_rank_emission_permitted": False,
        "whole_benchmark_complete": False,
    }
    if version in {"v3", "v4"}:
        robust_categories = [_alternative_category(category, [s["questions"] for s in results])
                             for category in categories.values()]
        result.update({
            "robust_categories": robust_categories,
            "robust_scenario_order": [s["scenario_id"] for s in results],
            "robust_reference_attainment": _conjunction(
                row["attainment"] for c in robust_categories for row in c["requirements"]),
            "metric_meaning": "Passed fixed requirement weight divided by all requirement weight; each requirement needs one complete registered native frame",
            "alternative_semantics": "Per requirement: one native frame must satisfy all selected outcomes; values and information are not pooled across alternative frames",
            "robust_witness_policy": "One fixed native frame per requirement across all scenarios and outcomes; separate requirements need not share a frame",
        })
    result["receipt_sha256"] = digest(result)
    return result
