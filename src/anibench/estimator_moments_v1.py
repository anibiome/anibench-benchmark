# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Finite estimator error from declared second moments and explicit bias bounds.

This evaluates a frozen estimator, not Fisher information, a posterior, or the
best possible estimator. Received numbers' shortest decimal representations are
treated as exact rationals; no ridge or threshold tolerance creates a pass.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path

from anibench.question_routes_v1 import digest


class EstimatorMomentError(ValueError):
    """Malformed or incompatible estimator, moment, support, or identity input."""


def _snapshot(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise EstimatorMomentError("Expected finite JSON values") from exc


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise EstimatorMomentError("Missing or unexpected contract fields")


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise EstimatorMomentError("Expected nonempty text")


def _texts(value):
    if not isinstance(value, list) or not value:
        raise EstimatorMomentError("Expected a nonempty text list")
    for item in value:
        _text(item)


def _number(value):
    if type(value) not in (int, float):
        raise EstimatorMomentError("Expected a finite JSON number")
    return Fraction(str(value))


def _vector(value, n):
    if not isinstance(value, list) or len(value) != n:
        raise EstimatorMomentError("Vector does not match estimator dimension")
    return [_number(x) for x in value]


def _hash(value):
    if (not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:")
            or any(c not in "0123456789abcdef" for c in value[7:])):
        raise EstimatorMomentError("Expected a SHA256 content binding")


def _tri(value):
    if value is not None and type(value) is not bool:
        raise EstimatorMomentError("Expected true, false or null")


def _signature(value):
    _keys(value, {"quantity", "unit", "compartment", "context"})
    for x in value.values():
        _text(x)


def _indexed(rows, key):
    if not isinstance(rows, list) or not rows:
        raise EstimatorMomentError("Expected a nonempty registered list")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or key not in row:
            raise EstimatorMomentError("Missing registered identity")
        _text(row[key])
        if row[key] in result:
            raise EstimatorMomentError("Duplicate registered identity")
        result[row[key]] = row
    return result


def validate_definition(definition):
    """Validate a trusted finite target/estimator contract, even without input."""
    d = _snapshot(definition)
    _keys(d, {"contract", "definition_id", "question", "population_scope", "context",
              "estimators", "functionals", "support_requirements", "sources", "assumptions"})
    if d["contract"] != "anibench.estimator-moment-definition.v1":
        raise EstimatorMomentError("Unknown estimator definition")
    for field in ("definition_id", "question", "population_scope", "context"):
        _text(d[field])
    _texts(d["assumptions"])
    _texts(d["support_requirements"])
    if len(set(d["support_requirements"])) != len(d["support_requirements"]):
        raise EstimatorMomentError("Duplicate support requirement")
    estimators = _indexed(d["estimators"], "estimator_id")
    if len(estimators) > 128:
        raise EstimatorMomentError("This finite adapter supports at most 128 estimators")
    signatures = set()
    for e in estimators.values():
        _keys(e, {"estimator_id", "target", "estimator", "method_sha256", "independent_unit"})
        _signature(e["target"])
        _text(e["estimator"])
        _text(e["independent_unit"])
        _hash(e["method_sha256"])
        key = digest(e["target"])
        if key in signatures:
            raise EstimatorMomentError("Duplicate target semantics")
        signatures.add(key)
    functionals = _indexed(d["functionals"], "functional_id")
    for f in functionals.values():
        _keys(f, {"functional_id", "estimand", "coefficients", "unit", "mse_limit"})
        _text(f["estimand"])
        _text(f["unit"])
        if not any(_vector(f["coefficients"], len(estimators))):
            raise EstimatorMomentError("A target functional must be nonzero")
        if _number(f["mse_limit"]) <= 0:
            raise EstimatorMomentError("MSE limit must be positive")
    sources = _indexed(d["sources"], "source_id")
    for source in sources.values():
        _keys(source, {"source_id", "sha256", "locator", "role"})
        _hash(source["sha256"])
        _text(source["locator"])
        _text(source["role"])
    return d


def _psd(matrix):
    """Exact rational Schur complements; includes singular PSD matrices."""
    n = len(matrix)
    if any(matrix[i][j] != matrix[j][i] for i in range(n) for j in range(n)):
        raise EstimatorMomentError("Covariance must be exactly symmetric")
    a = [row[:] for row in matrix]
    for k in range(n):
        pivot = a[k][k]
        if pivot < 0 or (pivot == 0 and any(a[k][j] != 0 for j in range(k + 1, n))):
            raise EstimatorMomentError("Covariance bounds must be positive semidefinite")
        if pivot:
            for i in range(k + 1, n):
                for j in range(i, n):
                    a[i][j] -= a[i][k] * a[k][j] / pivot
                    a[j][i] = a[i][j]


def _matrix(value, n):
    if not isinstance(value, list) or len(value) != n:
        raise EstimatorMomentError("Covariance does not match estimator dimension")
    result = [_vector(row, n) for row in value]
    _psd(result)
    return result


def _moments(value, n):
    _keys(value, {"covariance_lower", "covariance_upper", "bias_lower", "bias_upper",
                  "justification", "source_sha256", "assumptions"})
    _text(value["justification"])
    _hash(value["source_sha256"])
    _texts(value["assumptions"])
    lower = ([[Fraction(0)] * n for _ in range(n)] if value["covariance_lower"] is None
             else _matrix(value["covariance_lower"], n))
    upper = None if value["covariance_upper"] is None else _matrix(value["covariance_upper"], n)
    if upper is not None:
        _psd([[upper[i][j] - lower[i][j] for j in range(n)] for i in range(n)])
    b0, b1 = value["bias_lower"], value["bias_upper"]
    if (b0 is None) != (b1 is None):
        raise EstimatorMomentError("Supply both bias bounds or neither")
    if b0 is not None:
        b0, b1 = _vector(b0, n), _vector(b1, n)
        if any(a > b for a, b in zip(b0, b1, strict=True)):
            raise EstimatorMomentError("Reversed bias bounds")
    return lower, upper, b0, b1


def _design(value, definition):
    _keys(value, {"context", "acquisitions", "estimator_inputs", "support", "collection_verified"})
    if value["context"] != definition["context"]:
        raise EstimatorMomentError("Study changed the frozen estimator context")
    _tri(value["collection_verified"])
    _keys(value["support"], definition["support_requirements"])
    for flag in value["support"].values():
        _tri(flag)
    if not isinstance(value["acquisitions"], list):
        raise EstimatorMomentError("Acquisitions must be a list")
    physical = {}
    for row in value["acquisitions"]:
        _keys(row, {"physical_acquisition_id", "physical_output_id", "signature"})
        _text(row["physical_acquisition_id"])
        _text(row["physical_output_id"])
        _signature(row["signature"])
        key = (row["physical_acquisition_id"], row["physical_output_id"])
        if key in physical and physical[key] != row:
            raise EstimatorMomentError("Conflicting physical output identity")
        physical[key] = row
    indexed = _indexed(value["estimator_inputs"], "estimator_id")
    if set(indexed) != {e["estimator_id"] for e in definition["estimators"]}:
        raise EstimatorMomentError("Every estimator needs an explicit input mapping")
    normalized = []
    for key, row in indexed.items():
        _keys(row, {"estimator_id", "physical_outputs", "estimable"})
        _tri(row["estimable"])
        if not isinstance(row["physical_outputs"], list):
            raise EstimatorMomentError("Physical outputs must be a list")
        outputs = set()
        for pair in row["physical_outputs"]:
            if not isinstance(pair, list) or len(pair) != 2:
                raise EstimatorMomentError("Expected physical acquisition/output pairs")
            for x in pair:
                _text(x)
            if tuple(pair) not in physical:
                raise EstimatorMomentError("Estimator references an unregistered physical output")
            outputs.add(tuple(pair))
        if row["estimable"] is True and not outputs:
            raise EstimatorMomentError("An acquired estimator needs physical input support")
        normalized.append({"estimator_id": key, "physical_outputs": [list(pair) for pair in sorted(outputs)]})
    return {"context": value["context"], "acquisitions": [physical[k] for k in sorted(physical)],
            "estimator_inputs": sorted(normalized, key=lambda r: r["estimator_id"])}, indexed


def _quadratic(c, matrix):
    return sum(c[i] * matrix[i][j] * c[j] for i in range(len(c)) for j in range(len(c)))


def _bound(value):
    """Exact rational plus display approximation; null upper means unbounded."""
    if value is None:
        return {"exact": None, "approximate": None, "unbounded": True}
    try:
        approximate = float(value)
    except OverflowError:
        approximate = None
    return {"exact": str(value), "approximate": approximate, "unbounded": False}


def _adequacy(limit, risk):
    return Fraction(0) if risk is None else Fraction(1) if risk == 0 else min(Fraction(1), limit / risk)


def evaluate_estimator_moments(request: Mapping, *, trusted_definitions: Mapping):
    """Assess supplied qualified estimator moments without distributional invention.

    Covariance bounds are Loewner bounds. Bias is a Cartesian box. The product
    of both sets is an outer uncertainty set; its endpoints need not describe
    jointly attainable biology. A supplied bound is not verified by this code.
    """
    r, registry = _snapshot(request), _snapshot(trusted_definitions)
    _keys(r, {"contract", "definition_sha256", "lifecycle", "design", "moments"})
    if r["contract"] != "anibench.estimator-moments-request.v1":
        raise EstimatorMomentError("Unknown estimator request")
    key = r["definition_sha256"]
    if not isinstance(key, str) or key not in registry or digest(registry[key]) != key:
        raise EstimatorMomentError("Untrusted or stale estimator definition")
    d = validate_definition(registry[key])
    if r["lifecycle"] not in ("planned", "hypothetical", "realized"):
        raise EstimatorMomentError("Unknown study lifecycle")
    geometry, inputs = _design(r["design"], d)
    n = len(d["estimators"])
    lower, upper, b0, b1 = _moments(r["moments"], n)
    support = list(r["design"]["support"].values())
    if r["lifecycle"] == "realized":
        support.append(r["design"]["collection_verified"])
    rows = []
    for functional in d["functionals"]:
        c, limit = _vector(functional["coefficients"], n), _number(functional["mse_limit"])
        v0, v1 = _quadratic(c, lower), None if upper is None else _quadratic(c, upper)
        if b0 is None:
            bias0, bias1 = Fraction(0), None
        else:
            left = sum(min(x * a, x * b) for x, a, b in zip(c, b0, b1, strict=True))
            right = sum(max(x * a, x * b) for x, a, b in zip(c, b0, b1, strict=True))
            bias0 = Fraction(0) if left <= 0 <= right else min(left**2, right**2)
            bias1 = max(left**2, right**2)
        risk0 = v0 + bias0
        risk1 = None if v1 is None or bias1 is None else v1 + bias1
        flags = support + [inputs[e["estimator_id"]]["estimable"]
                           for x, e in zip(c, d["estimators"], strict=True) if x]
        lo, hi = _adequacy(limit, risk1), _adequacy(limit, risk0)
        state, reason = "unknown", "Error bounds straddle the target or are unbounded"
        if False in flags:
            state, reason, lo, hi = "not_attained", "Required acquisition, support or estimability fails", Fraction(0), Fraction(0)
        elif None in flags:
            reason, lo, hi = "Required acquisition, support or estimability is unresolved", Fraction(0), Fraction(1)
        elif risk1 is not None and risk1 <= limit:
            state, reason = "attained", "Certified upper error bound meets the frozen target"
        elif risk0 > limit:
            state, reason = "not_attained", "Certified lower error bound exceeds the frozen target"
        rows.append({"functional_id": functional["functional_id"], "unit": functional["unit"],
                     "mse_limit": functional["mse_limit"], "attainment": state, "reason": reason,
                     "variance": {"lower": _bound(v0), "upper": _bound(v1)},
                     "squared_bias": {"lower": _bound(bias0), "upper": _bound(bias1)},
                     "mse": {"lower": _bound(risk0), "upper": _bound(risk1)},
                     "exact_mse_established_under_declared_model": risk0 == risk1,
                     "precision_toward_target": {"lower_percent": float(100 * lo), "upper_percent": float(100 * hi)}})
    states = [row["attainment"] for row in rows]
    result = {"contract": "anibench.estimator-moments-result.v1", "definition_sha256": key,
              "request_sha256": digest(r), "lifecycle": r["lifecycle"], "definition": d,
              "claim_scope": "finite_estimator_mean_squared_error_under_declared_moment_bounds",
              "attainment": "not_attained" if "not_attained" in states else "unknown" if "unknown" in states else "attained",
              "functionals": rows, "design_frame": geometry, "design_frame_sha256": digest(geometry),
              "precision_toward_target": {k: min(row["precision_toward_target"][k] for row in rows)
                                          for k in ("lower_percent", "upper_percent")},
              "evidence_verification": "caller_declared_not_independently_certified",
              "uncertainty": "Outer moment/bias bounds; not confidence intervals",
              "joint_endpoint_attainability_established": False,
              "distributional_assumption": "None supplied by the evaluator; input moment derivations retain their own assumptions",
              "numerical_contract": "Exact rationals from str(received Python int/float); no threshold tolerance; original JSON lexemes are not available to this API",
              "implementation_sha256": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "all_direction_attainment": None, "empirical_learning_plateau": None,
              "public_rank_emission_permitted": False}
    result["receipt_sha256"] = digest(result)
    return result
