# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Compile physical observations into an existing frozen finite question.

This adapter owns measurement semantics and lineage, not a new scoring rule.
Alternative instruments must observe the same registered parameter frame.
Their full joint error covariance is supplied explicitly. A count of assays,
people, reads or bytes never supplies an observation operator or covariance.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping

import numpy as np

from anibench.finite_suites_v1 import (
    evaluate_finite_suite,
    scientific_frame_sha256,
    suite_sha256,
)
from anibench.finite_tasks_v1 import evaluate_finite_task, finite_task_sha256
from anibench.information_v2 import EventContribution, event_information


class QuestionRouteError(ValueError):
    """Invalid frame, physical identity or declared observation model."""


def digest(value):
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (ValueError, TypeError) as exc:
        raise QuestionRouteError("Expected finite JSON values") from exc
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise QuestionRouteError("Object has missing or unexpected fields")


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise QuestionRouteError("Expected nonempty text")


def _tri(value):
    if value is not None and type(value) is not bool:
        raise QuestionRouteError("Expected true, false or null")


def _matrix(value, shape):
    raw = np.asarray(value, dtype=object)
    if raw.shape != shape or any(type(x) not in (int, float) for x in raw.flat):
        raise QuestionRouteError("Expected a dimension-aligned real matrix")
    result = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(result)):
        raise QuestionRouteError("Nonfinite matrix")
    return result


SIGNATURE_FIELDS = ("quantity", "unit", "compartment", "context")


def _signature(value):
    _keys(value, SIGNATURE_FIELDS)
    for item in value.values():
        _text(item)


def route_model_sha256(definition):
    """Bind the allowed physical model independently of selected acquisitions."""
    return digest(
        {key: definition[key] for key in ("parameters", "routes", "model_rationale")}
    )


def _definition(definition):
    _keys(
        definition,
        ("contract", "question", "task", "parameters", "routes", "model_rationale"),
    )
    if definition["contract"] != "anibench.question-routes.v1":
        raise QuestionRouteError("Unknown question definition")
    _text(definition["question"])
    _text(definition["model_rationale"])
    task = definition["task"]
    if task["model_sha256"] != route_model_sha256(definition):
        raise QuestionRouteError("Stale observation-model binding")
    unknown = {
        "contract": "anibench.finite-task-request.v1",
        "task": task,
        "task_sha256": finite_task_sha256(task),
        "geometry": None,
        "evidence": {
            "identifiability": None,
            "collection_verified": None,
            "support": [],
        },
    }
    evaluate_finite_task(unknown)
    parameters = definition["parameters"]
    if not isinstance(parameters, list) or len(parameters) != len(
        task["parameter_units"]
    ):
        raise QuestionRouteError("Parameter signatures must match the frozen task")
    for parameter, unit in zip(parameters, task["parameter_units"], strict=True):
        _signature(parameter)
        if parameter["unit"] != unit:
            raise QuestionRouteError("Parameter unit differs from the frozen task")
    if len({digest(p) for p in parameters}) != len(parameters):
        raise QuestionRouteError("Duplicate parameter semantics")
    routes = definition["routes"]
    if not isinstance(routes, list) or not routes:
        raise QuestionRouteError("At least one registered route required")
    indexed = {}
    for route in routes:
        _keys(route, ("route_id", "outputs", "design_operator", "assumptions"))
        _text(route["route_id"])
        if route["route_id"] in indexed:
            raise QuestionRouteError("Duplicate route identifier")
        if not isinstance(route["assumptions"], list) or not route["assumptions"]:
            raise QuestionRouteError("Every route needs explicit model assumptions")
        for assumption in route["assumptions"]:
            _text(assumption)
        outputs = route["outputs"]
        if not isinstance(outputs, list) or not outputs:
            raise QuestionRouteError("Route outputs required")
        operator = _matrix(route["design_operator"], (len(outputs), len(parameters)))
        if np.any(np.all(operator == 0, axis=1)):
            raise QuestionRouteError("A route output cannot be a zero operator")
        output_map = {}
        for i, output in enumerate(outputs):
            _keys(output, ("output_id", "signature"))
            _text(output["output_id"])
            _signature(output["signature"])
            if output["output_id"] in output_map:
                raise QuestionRouteError("Duplicate output identifier")
            output_map[output["output_id"]] = (output["signature"], operator[i])
        indexed[route["route_id"]] = output_map
    return indexed


def _noise(noise, count):
    if noise is None:
        return None
    if count == 0 and noise == []:
        return np.empty((0, 0))
    matrix = _matrix(noise, (count, count))
    if count == 0:
        return matrix
    diagonal = np.diag(matrix)
    if np.any(diagonal <= 0):
        raise QuestionRouteError("Observation variances must be positive")
    scales = np.sqrt(diagonal)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        correlation = (matrix / scales[:, None]) / scales[None, :]
    if not np.all(np.isfinite(correlation)) or not np.allclose(
        correlation, correlation.T, rtol=1e-12, atol=1e-12
    ):
        raise QuestionRouteError("Noise must be symmetric in standardized units")
    # Do not add a ridge to rescue duplicate or nearly dependent signals.
    eigenvalues = np.linalg.eigvalsh((correlation + correlation.T) / 2)
    if eigenvalues[0] <= 1e-10 * eigenvalues[-1]:
        raise QuestionRouteError("Noise is singular or numerically unresolved")
    return matrix


def compile_question_routes(request: Mapping, *, trusted_definitions: Mapping):
    """Return confirmed/possible finite-task inputs, never caller-supplied scores.

    Noise rows are indexed by unique physical acquisition/output pairs. Repeated
    aliases coalesce only when operator, native signature and qualification agree.
    Noise includes dependence between instruments and acquisitions. It is not
    inferred from their different names. Unknown inventory leaves the possible
    geometry unknown; a known subset still remains available for the lower result.
    The caller's evidence declarations are not independently verified here.
    """
    request = json.loads(json.dumps(request, allow_nan=False))
    registry = json.loads(json.dumps(trusted_definitions, allow_nan=False))
    _keys(
        request,
        (
            "contract",
            "definition_sha256",
            "observations",
            "noise_order",
            "noise_covariance",
            "closed_inventory",
            "evidence",
        ),
    )
    if request["contract"] != "anibench.question-routes-request.v1":
        raise QuestionRouteError("Unknown request contract")
    key = request["definition_sha256"]
    if key not in registry or digest(registry[key]) != key:
        raise QuestionRouteError("Untrusted or changed definition")
    definition = registry[key]
    routes = _definition(definition)
    _tri(request["closed_inventory"])
    if not isinstance(request["observations"], list) or not isinstance(
        request["noise_order"], list
    ):
        raise QuestionRouteError("Observation and noise-order lists required")
    observations = {}
    for row in request["observations"]:
        _keys(
            row,
            (
                "physical_acquisition_id",
                "physical_output_id",
                "route_id",
                "output_id",
                "signature",
                "qualified",
            ),
        )
        for name in (
            "physical_acquisition_id",
            "physical_output_id",
            "route_id",
            "output_id",
        ):
            _text(row[name])
        _tri(row["qualified"])
        try:
            signature, operator = routes[row["route_id"]][row["output_id"]]
        except KeyError as exc:
            raise QuestionRouteError("Unregistered route/output") from exc
        if row["signature"] != signature:
            raise QuestionRouteError(
                "Observation quantity/unit/compartment/context differs from route"
            )
        physical = (row["physical_acquisition_id"], row["physical_output_id"])
        semantics = {
            "signature": signature,
            "operator": operator.tolist(),
            "qualified": row["qualified"],
        }
        if physical in observations and observations[physical] != semantics:
            raise QuestionRouteError("Conflicting descriptions of one physical output")
        observations[physical] = semantics
    order = []
    for pair in request["noise_order"]:
        if not isinstance(pair, list) or len(pair) != 2:
            raise QuestionRouteError("Noise order requires acquisition/output pairs")
        for item in pair:
            _text(item)
        order.append(tuple(pair))
    if len(set(order)) != len(order) or set(order) != set(observations):
        raise QuestionRouteError(
            "Noise order must cover unique physical outputs exactly"
        )
    covariance = _noise(request["noise_covariance"], len(order))
    task = definition["task"]
    dimension = len(task["parameter_units"])
    compiled = {}
    for mode in ("confirmed", "possible"):
        selection = [
            i
            for i, physical in enumerate(order)
            if (
                observations[physical]["qualified"] is True
                if mode == "confirmed"
                else observations[physical]["qualified"] is not False
            )
        ]
        geometry = None
        if (not selection or covariance is not None) and (
            mode == "confirmed" or request["closed_inventory"] is True
        ):
            information = np.zeros((dimension, dimension))
            if selection:
                h = np.asarray([observations[order[i]]["operator"] for i in selection])
                r = covariance[np.ix_(selection, selection)]
                scale = np.sqrt(np.diag(r))
                # Equivalent units, with well-scaled noise; no new statistical solver.
                hs = h / scale[:, None]
                rs = (r / scale[:, None]) / scale[None, :]
                if not np.all(np.isfinite(hs)) or np.any((h != 0) & (hs == 0)):
                    raise QuestionRouteError(
                        "Operator scaling is numerically unresolved"
                    )
                information = event_information(
                    EventContribution(
                        event_type_id="registered-question-routes",
                        design_operator=tuple(map(tuple, hs)),
                        noise_covariance=tuple(map(tuple, rs)),
                        effective_count=1.0,
                        source_object_id=digest(request),
                    )
                )
                if np.any(np.any(h != 0, axis=0) & (np.diag(information) <= 0)):
                    raise QuestionRouteError("Nonzero information was lost numerically")
                if np.any(
                    (information != 0) & (np.abs(information) < np.finfo(float).tiny)
                ):
                    raise QuestionRouteError(
                        "Subnormal information cannot certify target precision"
                    )
            geometry = {
                "model_sha256": task["model_sha256"],
                "information_matrix": information.tolist(),
            }
        compiled[mode] = {
            "contract": "anibench.finite-task-request.v1",
            "task": copy.deepcopy(task),
            "task_sha256": finite_task_sha256(task),
            "geometry": geometry,
            "evidence": copy.deepcopy(request["evidence"]),
        }
        evaluate_finite_task(compiled[mode])
    return {
        "contract": "anibench.question-routes-compilation.v1",
        "input_sha256": digest(request),
        "definition_sha256": key,
        "question": definition["question"],
        "unique_physical_outputs": len(order),
        "compiled": compiled,
        "semantics": "Known-subset and possible-subset conditional Gaussian experiments; use likelihood-only finite suite. Bounds are not confidence intervals or actual prediction accuracy.",
        "scope": "Finite registered question only; no whole-study or biological-reference ratification.",
    }


def evaluate_question_routes(request: Mapping, *, trusted_definitions: Mapping):
    """Evaluate one question from acquired information and preserve uncertainty.

    Confirmed and possible observations bound one experiment. They are not two
    studies and are not alternative favorable model assumptions. The fixed
    covariance/model and the nested physical observations justify this order.
    A confirmed failure with a possible pass is unresolved, not a failed study.
    """
    compiled = compile_question_routes(request, trusted_definitions=trusted_definitions)
    task = compiled["compiled"]["confirmed"]["task"]
    identity = "registered-question"
    profile = {
        "contract": "anibench.finite-suite-profile.v1",
        "profile_id": "registered-question-route-endpoints-v1",
        "profile_type": "custom",
        "scope": "One frozen question under nested observation qualification endpoints",
        "tolerance_authority": "Frozen question definition; no automatic clinical meaning",
        "calibration_authority": "Supplied trusted observation model; not independently verified here",
        "precision_basis": "likelihood_only",
        "scenario_quantifier": "all_declared_scenarios",
        "scenario_ids": ["confirmed", "possible"],
        "parent_sha256": None,
        "targets": [
            {
                "canonical_id": identity,
                "frame_sha256": scientific_frame_sha256(task),
                "task": task,
            }
        ],
    }
    binding = {
        "design_id": "question-observations",
        "design_source_sha256": compiled["input_sha256"],
    }
    suite_request = {
        "contract": "anibench.finite-suite-request.v1",
        "profile_sha256": suite_sha256(profile),
        **binding,
        "scenarios": [
            {
                "scenario_id": mode,
                **binding,
                "targets": [
                    {
                        "canonical_id": identity,
                        **binding,
                        "known_absent": False,
                        "request": compiled["compiled"][mode],
                    }
                ],
            }
            for mode in ("confirmed", "possible")
        ],
    }
    suite = evaluate_finite_suite(
        suite_request, trusted_profiles={suite_sha256(profile): profile}
    )
    endpoints = {s["scenario_id"]: s["targets"][0] for s in suite["scenarios"]}
    lower = endpoints["confirmed"]["attainment"]
    upper = endpoints["possible"]["attainment"]
    if lower == "attained" and upper == "not_attained":
        raise QuestionRouteError("Numerically inconsistent nested experiment results")
    # Never reuse the suite's all-scenarios conjunction as this epistemic result.
    state = (
        "attained"
        if lower == "attained"
        else "not_attained"
        if upper == "not_attained"
        else "unknown"
    )
    return {
        "contract": "anibench.question-routes-result.v1",
        "input_sha256": compiled["input_sha256"],
        "definition_sha256": compiled["definition_sha256"],
        "question": compiled["question"],
        "precision_basis": "likelihood_only",
        "attainment": state,
        "attainment_bounds": {
            "lower": int(lower == "attained"),
            "upper": int(upper != "not_attained"),
            "interpretation": "Epistemic bounds on a single binary requirement; not a probability",
        },
        "endpoints": endpoints,
        "compilation_sha256": digest(compiled),
        "suite_sha256": suite_sha256(suite),
        "suite": suite,
        "promotion_allowed": False,
        "scope": "One registered question. No whole-study score, biological calibration or level claim.",
    }
