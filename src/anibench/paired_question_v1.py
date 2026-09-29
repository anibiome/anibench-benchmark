# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Conditional paired biological questions; no whole-study or AB-level claim.

Evaluate one frozen biological question under an explicit Gaussian reference.
No observed response magnitude, study name, spending or publication flag enters
the calculation. The covariance-estimator diagnostic is not Fisher information.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator

EVALUATOR = "anibench.paired-question.v1-candidate1"
_TEXT = {"type": "string", "minLength": 1, "pattern": r"\S"}
_HASH = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
_TRI = {"type": ["boolean", "null"]}
_COUNT = {"type": ["integer", "null"], "minimum": 0, "maximum": 9007199254740991}
_MATRIX = {"type": ["array", "null"], "minItems": 1,
           "items": {"type": "array", "minItems": 1, "items": {"type": "number"}}}
_SUPPORT = (
    "operator_valid", "zero_mean_measurement_error", "independent_measurement_error",
    "reference_model_applicable", "independent_people", "declared_population",
    "paired_occasions", "cross_domain_linkage", "independently_measured_function",
    "gaussian_reference", "prediction_time_order", "documented_exposure",
    "exposure_aligned_window", "controlled_assignment_identified", "collection_verified",
)
_TOLERANCES = (
    "molecular_state", "function_state", "molecular_change", "function_change",
    "molecular_mean_change", "function_mean_change", "change_cross_covariance",
    "controlled_function_effect",
)


def _object(properties, optional=()):
    return {"type": "object", "properties": properties,
            "required": [key for key in properties if key not in optional],
            "additionalProperties": False}


INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    **_object({
        "contract": {"const": "anibench.paired-question-input.v1"},
        "question": _object({
            "contract": {"const": "anibench.paired-biological-question.v1"},
            "question_id": _TEXT, "question": _TEXT, "population_scope": _TEXT,
            "coordinates": {"type": "array", "minItems": 2, "items": _object({
                "id": _TEXT, "unit": _TEXT, "definition": _TEXT,
                "domain": {"enum": ["molecular", "functional"]},
            })},
            "occasions_days": {"type": "array", "minItems": 2, "maxItems": 2,
                               "items": {"type": "number"}},
            "tolerances": _object({key: {"type": "array", "minItems": 1,
                                        "items": {"type": "number", "exclusiveMinimum": 0}}
                                   for key in _TOLERANCES}),
            "tolerance_authority": _TEXT, "functional_operator": _TEXT,
        }),
        "scenario": _object({
            "question_sha256": _HASH, "biological_covariance": _MATRIX,
            "measurement_error_covariance": _MATRIX,
            "error_covariance_treated_as_known": _TRI,
            "assumptions": {"type": "array", "minItems": 1, "items": _TEXT},
        }),
        "design": _object({
            "question_sha256": _HASH, "lifecycle": {"enum": ["planned", "hypothetical", "realized"]},
            "n_independent_complete": _COUNT, "closed_acquisition_inventory": _TRI,
            "observations": {"type": "array", "items": _object({
                "physical_id": _TEXT, "coordinate_id": _TEXT,
                "occasion_index": {"type": "integer", "enum": [0, 1]}, "qualified": _TRI,
            })},
            "controlled_arm_counts": {"type": ["array", "null"], "minItems": 2, "maxItems": 2,
                                      "items": {"type": "integer", "minimum": 0}},
            "support": _object({key: _TRI for key in _SUPPORT}),
            "metadata": {"type": "object"},
        }, optional=("metadata",)),
    }),
}


def _snapshot(payload):
    try:
        snapshot = json.loads(json.dumps(payload, allow_nan=False))
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Paired question input must contain finite JSON values") from exc
    error = next(Draft202012Validator(INPUT_SCHEMA).iter_errors(snapshot), None)
    if error is not None:
        # Do not print offending clinical values or user-supplied metadata.
        raise ValueError(f"Paired question input violates schema ({error.validator})")
    return snapshot


def evaluate_paired_question(payload):
    """Evaluate the explicit estimator/reference contract from a JSON bundle."""
    payload = _snapshot(payload)
    return evaluate(payload["question"], payload["scenario"], payload["design"])


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def tri(values):
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def flag(value):
    if value is not None and type(value) is not bool:
        raise ValueError("Support must be true, false or null")
    return value


def matrix(value, dimension, name, *, definite=False):
    if value is None:
        return None
    try:
        a = np.asarray(value, dtype=float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(name + " cannot be represented as a numeric matrix") from exc
    if a.shape != (dimension, dimension) or not np.isfinite(a).all():
        raise ValueError(name + " must be a finite dimension-aligned matrix")
    # Normalize before PSD checks: units must not decide numerical admission.
    diagonal = np.diag(a)
    if (diagonal < 0).any():
        raise ValueError(name + " has negative variance")
    zero = diagonal == 0
    if np.any(a[zero, :] != 0) or np.any(a[:, zero] != 0):
        raise ValueError(name + " has nonzero covariance with a zero-variance quantity")
    positive = ~zero
    if definite and not positive.all():
        raise ValueError(name + " must be positive definite")
    scales = np.sqrt(diagonal[positive])
    try:
        with np.errstate(over="raise", under="raise", divide="raise", invalid="raise"):
            reduced = a[np.ix_(positive, positive)] / scales[:, None] / scales[None, :]
    except FloatingPointError as exc:
        raise ValueError(name + " normalization is numerically unresolved") from exc
    if not np.isfinite(reduced).all() or np.any(np.abs(reduced) > 1 + 1e-12):
        raise ValueError(name + " violates covariance correlation bounds")
    if not np.allclose(reduced, reduced.T, rtol=1e-12, atol=1e-12):
        raise ValueError(name + " must be symmetric")
    if reduced.size:
        eigen = np.linalg.eigvalsh(0.5 * reduced + 0.5 * reduced.T)
        if not np.isfinite(eigen).all() or eigen[0] < -1e-12 or (definite and eigen[0] <= 1e-10):
            raise ValueError(name + " has invalid or numerically ambiguous rank")
    # Preserve exactly symmetric values, especially subnormal diagonals: halving
    # each first can otherwise erase a nonzero variance and create false 100%.
    symmetric = 0.5 * a + 0.5 * a.T
    symmetric[a == a.T] = a[a == a.T]
    if np.any((symmetric == 0) & (a != -a.T)):
        raise ValueError(name + " symmetrization is numerically unresolved")
    return symmetric


def cross_covariance_sampling_variance(v, pairs, n):
    """Exact covariance of unbiased sample-covariance entries, Gaussian iid rows.

    Subtracting a known measurement-error covariance changes the expectation,
    not this sampling covariance. Uncertain error calibration is unsupported.
    """
    if type(n) is not int or n < 2:
        raise ValueError("Sample covariance needs at least two independent people")
    # Extreme unit choices can underflow fourth-moment products to an apparent
    # zero estimator error. Fail closed rather than reporting perfect precision.
    with np.errstate(over="raise", under="raise", invalid="raise"):
        return np.asarray([
            [(v[a, c] * v[b, d] + v[a, d] * v[b, c]) / (n - 1)
             for c, d in pairs]
            for a, b in pairs
        ])


def ols_risk(v, predictors, target, n):
    """Expected independent-test MSE of OLS with a fitted intercept.

    This is a reference-distribution calculation, not a trained model result.
    Only baseline predictors may be passed by the registered question compiler.
    """
    p = len(predictors)
    if type(n) is not int or n < 1:
        raise ValueError("OLS requires an integer independent-person count")
    if p == 0:
        residual = float(v[target, target])
    else:
        xx = v[np.ix_(predictors, predictors)]
        scales = np.sqrt(np.diag(xx))
        standardized = xx / scales[:, None] / scales[None, :]
        eigen = np.linalg.eigvalsh(standardized)
        if eigen[0] <= 1e-10:
            return {"state": "unknown", "reason": "Predictor covariance rank ambiguous"}
        xy = v[predictors, target] / scales
        residual = float(v[target, target] - xy @ np.linalg.solve(standardized, xy))
    if not np.isfinite(residual) or residual <= 0:
        return {"state": "unknown", "reason": "Residual variance is numerically unresolved"}
    if n <= p + 2 and p:
        return {
            "state": "no_finite_expected_risk",
            "reason": "OLS inverse-scatter expectation does not exist or fit is underdetermined",
            "predictors": p,
            "n": n,
            "conditional_residual_variance": residual,
        }
    multiplier = (1 + 1 / n) * (1 + p / (n - p - 2)) if p else 1 + 1 / n
    risk = residual * multiplier
    if not np.isfinite(risk):
        return {"state": "unknown", "reason": "Expected risk is numerically unresolved"}
    return {
        "state": "conditional",
        "predictors": p,
        "n": n,
        "conditional_residual_variance": residual,
        "expected_test_mse": risk,
        "sqrt_expected_test_mse": float(np.sqrt(risk)),
        "scope": "Expected error of a specified learner under the declared Gaussian reference",
    }


def precision(covariance, tolerances, support, reason):
    """Whole-vector error-covariance adequacy; one question, no feature voting.

    C <= diag(tolerance**2) is a covariance-order requirement. It does not
    mean simultaneous confidence coverage or a probability that biology is known.
    """
    if support is False:
        return {"state": "not_supported", "reason": reason,
                "adequacy_percent": {"lower": 0.0, "upper": 0.0}}
    if support is True and covariance is None:
        return {"state": "unknown", "reason": "Estimator covariance is unavailable or numerically unresolved",
                "adequacy_percent": {"lower": 0.0, "upper": 100.0}}
    if support is None:
        return {"state": "unknown", "reason": reason,
                "adequacy_percent": {"lower": 0.0, "upper": 100.0}}
    covariance = np.asarray(covariance, dtype=float)
    scales = np.asarray(tolerances, dtype=float)
    if scales.ndim != 1 or covariance.shape != (len(scales), len(scales)):
        raise ValueError("Exact covariance and tolerance dimensions required; no broadcasting")
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("Native tolerances must be finite and strictly positive")
    unknown = {"state": "unknown", "reason": "Normalized covariance is numerically unresolved",
               "adequacy_percent": {"lower": 0.0, "upper": 100.0}}
    try:
        with np.errstate(over="raise", under="raise", divide="raise", invalid="raise"):
            normalized = covariance / scales[:, None] / scales[None, :]
    except FloatingPointError:
        return unknown
    if not np.isfinite(normalized).all() or not np.allclose(normalized, normalized.T, rtol=1e-12, atol=1e-12):
        return unknown
    eigen = np.linalg.eigvalsh(0.5 * normalized + 0.5 * normalized.T)
    if not np.isfinite(eigen).all() or eigen[0] < -1e-12 or np.any(np.diag(covariance) < 0):
        return unknown
    ratio = max(0.0, float(eigen[-1]))
    adequacy = 100.0 if ratio == 0 else 100 * min(1.0, 1.0 / ratio)
    return {
        "state": "attained" if ratio <= 1 + 1e-10 else "not_attained",
        "covariance": covariance.tolist(),
        "native_standard_errors": np.sqrt(np.diag(covariance)).tolist(),
        "tolerances": scales.tolist(),
        "worst_variance_ratio": ratio,
        "adequacy_percent": {"lower": adequacy, "upper": adequacy},
        "meaning": "Precision toward this registered question's error target; not accuracy or percent of biology",
    }


def _scaled_covariance(covariance, factor):
    if covariance is None:
        return None
    try:
        with np.errstate(over="raise", under="raise", invalid="raise"):
            return covariance * factor
    except FloatingPointError:
        return None


def evaluate(question, scenario, design):
    # Snapshot before validation so later caller mutation cannot alter a receipt.
    payload = _snapshot({"contract": "anibench.paired-question-input.v1",
                         "question": question, "scenario": scenario, "design": design})
    question, scenario, design = payload["question"], payload["scenario"], payload["design"]
    if question["contract"] != "anibench.paired-biological-question.v1":
        raise ValueError("Unrecognized question contract")
    if scenario["question_sha256"] != digest(question):
        raise ValueError("Scenario does not bind this exact question")
    if design["question_sha256"] != digest(question):
        raise ValueError("Design does not bind this exact question")
    if design["lifecycle"] not in {"planned", "hypothetical", "realized"}:
        raise ValueError("Unrecognized lifecycle")
    times = question["occasions_days"]
    if len(times) != 2 or not all(type(x) in (int, float) and np.isfinite(x) for x in times) or times[1] <= times[0]:
        raise ValueError("Exactly two ordered finite occasions required")
    coords = question["coordinates"]
    names = [c["id"] for c in coords]
    if len(set(names)) != len(names) or not names:
        raise ValueError("Canonical coordinates must be unique")
    if any(not c["unit"] or c["domain"] not in {"molecular", "functional"} for c in coords):
        raise ValueError("Every coordinate needs a native unit and registered domain")
    molecular = [i for i, c in enumerate(coords) if c["domain"] == "molecular"]
    functional = [i for i, c in enumerate(coords) if c["domain"] == "functional"]
    if not molecular or len(functional) != 1:
        raise ValueError("This question requires a molecular vector and one functional quantity")
    f = functional[0]
    d = len(coords)
    expected_tolerances = {
        "molecular_state": len(molecular), "function_state": 1,
        "molecular_change": len(molecular), "function_change": 1,
        "molecular_mean_change": len(molecular), "function_mean_change": 1,
        "change_cross_covariance": len(molecular), "controlled_function_effect": 1,
    }
    if set(question["tolerances"]) != set(expected_tolerances):
        raise ValueError("Question must freeze all and only the supported precision targets")
    for key, length in expected_tolerances.items():
        values = question["tolerances"][key]
        if len(values) != length or any(type(x) not in (float, int) or not np.isfinite(x) or x <= 0 for x in values):
            raise ValueError("Invalid native tolerance vector: " + key)
    n = design["n_independent_complete"]
    if n is not None and (type(n) is not int or n < 0):
        raise ValueError("Independent-person count must be a nonnegative integer or null")
    gates = {key: flag(value) for key, value in design["support"].items()}
    base_names = ["operator_valid", "zero_mean_measurement_error", "independent_measurement_error", "reference_model_applicable"]
    common = tri([gates.get(key) for key in base_names])
    if design["lifecycle"] == "realized":
        common = tri([common, gates.get("collection_verified")])
    population = tri([common, gates.get("independent_people"), gates.get("declared_population")])
    paired = tri([common, gates.get("paired_occasions")])
    linked = gates.get("cross_domain_linkage")
    independent_function = gates.get("independently_measured_function")
    b = matrix(scenario["biological_covariance"], 2 * d, "Biological covariance")
    r = matrix(scenario["measurement_error_covariance"], 2 * d, "Error covariance")
    v = None if b is None or r is None else matrix((b + r).tolist(), 2 * d, "Observed covariance", definite=True)
    known_error = flag(scenario["error_covariance_treated_as_known"])
    common = tri([common, known_error])
    # Fixed covariance of a single registered reading at each coordinate/occasion.
    # Additional technical repeats need a qualified aggregation/noise adapter.
    by_physical = {}
    by_slot = {}
    for obs in design["observations"]:
        if set(obs) != {"physical_id", "coordinate_id", "occasion_index", "qualified"}:
            raise ValueError("Observation must use the exact acquisition schema")
        identity = obs["physical_id"]
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Physical identity required")
        if obs["coordinate_id"] not in names or type(obs["occasion_index"]) is not int or obs["occasion_index"] not in (0, 1):
            raise ValueError("Observation is outside the frozen native frame")
        flag(obs["qualified"])
        signature = {key: value for key, value in obs.items() if key != "physical_id"}
        if identity in by_physical:
            if by_physical[identity] != signature:
                raise ValueError("Conflicting physical acquisition reuse")
            continue
        slot = (obs["coordinate_id"], obs["occasion_index"])
        if slot in by_slot:
            raise ValueError("Repeated slot requires an explicit qualified repeat-error model")
        by_physical[identity] = signature
        by_slot[slot] = obs["qualified"]
    closed = flag(design["closed_acquisition_inventory"])

    def available(indices, occasions):
        return tri([by_slot.get((names[i], t), False if closed is True else None)
                    for i in indices for t in occasions])

    def sub(a, indices):
        return None if a is None else a[np.ix_(indices, indices)]

    D = np.hstack([-np.eye(d), np.eye(d)])
    change_r = None if r is None else D @ r @ D.T
    change_v = None if v is None else D @ v @ D.T
    enough = None if n is None else n > 0
    tolerances = question["tolerances"]
    results = {}
    for domain, indices in (("molecular", molecular), ("function", functional)):
        extra = independent_function if domain == "function" else True
        state_support = tri([common, extra, available(indices, [0]), enough])
        change_support = tri([paired, known_error, extra, available(indices, [0, 1]), enough])
        results[domain + "_state"] = precision(
            sub(r, indices), tolerances[domain + "_state"], state_support,
            "Requires native baseline acquisition with qualified error model"
        )
        results[domain + "_individual_change"] = precision(
            sub(change_r, indices), tolerances[domain + "_change"], change_support,
            "Requires linked native acquisitions at both registered occasions"
        )
        mean_cov = None if not n else _scaled_covariance(sub(change_v, indices), 1 / n)
        mean_support = tri([change_support, population])
        results[domain + "_mean_change"] = precision(
            mean_cov, tolerances[domain + "_mean_change"], mean_support,
            "Requires complete paired independent people in the stated population"
        )
    pairs = [(i, f) for i in molecular]
    relation_gate = tri([population, paired, known_error, linked, independent_function,
                         gates.get("gaussian_reference"), available(range(d), [0, 1]),
                         None if n is None else n > 1])
    relation_cov = None
    if change_v is not None and n is not None and n > 1:
        try:
            relation_cov = cross_covariance_sampling_variance(change_v, pairs, n)
        except FloatingPointError:
            relation_cov = None
    results["molecular_function_change_relation"] = precision(
        relation_cov, tolerances["change_cross_covariance"], relation_gate,
        "Requires paired molecular and independently measured functional change in the same people"
    )
    results["molecular_function_change_relation"]["estimand"] = "Covariance of molecular change with functional change, after subtraction of known error covariance"
    results["molecular_function_change_relation"]["interpretation"] = "Relationship estimation precision; neither mechanism, causation nor demonstrated prediction"
    exposure_gate = tri([population, paired, known_error, independent_function,
                         available(functional, [0, 1]), enough,
                         gates.get("documented_exposure"), gates.get("exposure_aligned_window")])
    results["exposure_aligned_function_change"] = precision(
        None if not n else _scaled_covariance(sub(change_v, functional), 1 / n),
        tolerances["function_mean_change"], exposure_gate,
        "Requires measured function before and after a documented, time-aligned exposure"
    )
    results["exposure_aligned_function_change"]["interpretation"] = "Descriptive change; no untreated counterfactual is identified by this contrast"
    arms = design.get("controlled_arm_counts")
    control_gate = tri([population, paired, known_error, independent_function,
                        available(functional, [0, 1]),
                        None if n is None else n >= 2,
                        gates.get("controlled_assignment_identified"),
                        gates.get("exposure_aligned_window")])
    contrast_cov = None
    if arms is None:
        control_gate = tri([control_gate, None])
    else:
        if len(arms) != 2 or any(type(a) is not int or a < 0 for a in arms) or n is None or sum(arms) != n:
            raise ValueError("Two disjoint arm counts must partition the complete roster")
        if min(arms) == 0:
            control_gate = False
        elif change_v is not None:
            contrast_cov = _scaled_covariance(sub(change_v, functional), 1 / arms[0] + 1 / arms[1])
    results["controlled_function_effect"] = precision(
        contrast_cov, tolerances["controlled_function_effect"], control_gate,
        "Requires identified assignment contrast and paired functional observations in both arms"
    )
    results["controlled_function_effect"]["interpretation"] = "Identified assignment/ITT mean-change contrast under declared causal assumptions; not actual-exposure efficacy and no treatment-benefit requirement"
    # Frozen baseline-only routes prohibit post-outcome molecular predictors.
    routes = {"mean_only": [], "baseline_function": [f], "baseline_function_and_molecular": [f, *molecular]}
    learning = {}
    for route_id, predictors in routes.items():
        route_gate = tri([population, known_error, independent_function,
                          gates.get("gaussian_reference"), gates.get("prediction_time_order"),
                          available(functional, [1]), available(predictors, [0]), enough,
                          gates.get("paired_occasions") if predictors else True,
                          linked if any(i in molecular for i in predictors) else True])
        if route_gate is not True or v is None:
            learning[route_id] = {"state": "not_supported" if route_gate is False else "unknown"}
        elif predictors and np.any(r[d + f, predictors] != 0):
            learning[route_id] = {
                "state": "unknown",
                "reason": "Target and predictor measurement errors are shared; observed-target prediction may learn measurement error instead of biological function",
            }
        else:
            learning[route_id] = ols_risk(v, predictors, d + f, n)
    known_routes = [(key, row["expected_test_mse"]) for key, row in learning.items()
                    if row["state"] == "conditional"]
    learning["best_registered_available_route"] = min(known_routes, key=lambda x: x[1])[0] if known_routes else None
    learning["selection_scope"] = "Minimum analytic reference risk among frozen routes; no fitted-model selection or empirical result"
    learning["observed_held_out_prediction"] = {"state": "not_evaluated", "reason": "Requires a separate source-qualified held-person experiment"}
    learning["target"] = "Independently measured follow-up functional value using only registered baseline inputs"
    answer = {
        "contract": "anibench.paired-biological-question-result.v1",
        "evaluator": EVALUATOR,
        "question_sha256": digest(question), "scenario_sha256": digest(scenario),
        "input_sha256": digest(design), "question": question["question"],
        "lifecycle": design["lifecycle"], "scope": "Conditional one-question evaluation; not full study quality or AB1",
        "canonical_acquisitions": len(by_physical),
        "results": results, "conditional_functional_learning": learning,
        "model_assumptions": scenario["assumptions"],
        "public_rank_emission_permitted": False,
    }
    # Numerical result identity excludes provenance/metadata and duplicate rows.
    answer["calculation_sha256"] = digest({"evaluator": EVALUATOR, "question": question, "scenario": scenario,
                                          "results": results, "learning": learning})
    answer["receipt_sha256"] = digest(answer)
    return copy.deepcopy(answer)
