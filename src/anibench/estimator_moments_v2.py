# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Nonnegative separable quadratic loss from the shared estimator moments.

V1 linear-functional MSE is unchanged. V2 evaluates a registered sum of squared
coordinate errors, not a conjunction of allocated coordinate thresholds.
"""
from __future__ import annotations

import hashlib
from fractions import Fraction
from pathlib import Path

from anibench import estimator_moments_v1 as core
from anibench.question_routes_v1 import digest


def validate_definition(definition):
    """Dispatch unchanged v1, or validate the separable-loss definition v2."""
    d = core._snapshot(definition)
    if isinstance(d, dict) and d.get("contract") == "anibench.estimator-moment-definition.v1":
        return core.validate_definition(d)
    if not isinstance(d, dict) or d.get("contract") != "anibench.estimator-moment-definition.v2":
        raise core.EstimatorMomentError("Unknown estimator definition")
    # Reuse common target/method/provenance validation. This shadow is never a
    # scientific input or a scoring result; it only validates the common fields.
    if not isinstance(d.get("estimators"), list) or not d["estimators"]:
        raise core.EstimatorMomentError("Expected registered estimators")
    n = len(d["estimators"])
    functionals = core._indexed(d.get("functionals"), "functional_id")
    shadows = []
    for f in functionals.values():
        core._keys(f, {"functional_id", "estimand", "loss_weights", "unit", "mse_limit"})
        weights = core._vector(f["loss_weights"], n)
        if any(w < 0 for w in weights) or not any(weights):
            raise core.EstimatorMomentError("Loss weights must be nonnegative and not all zero")
        shadows.append({k: v for k, v in f.items() if k != "loss_weights"} |
                       {"coefficients": [1] + [0] * (n - 1)})
    common = dict(d, contract="anibench.estimator-moment-definition.v1", functionals=shadows)
    core.validate_definition(common)
    return d


def evaluate_estimator_moments(request, *, trusted_definitions):
    """Evaluate E[sum_j w_j (T_j-theta_j)^2] with exact outer bounds.

    Nonnegative weights make diagonal covariance bounds valid under Loewner
    order. Cartesian bias bounds give exact extrema of the separable bias loss.
    No coordinate-threshold failure is used as evidence of joint-loss failure.
    """
    r, registry = core._snapshot(request), core._snapshot(trusted_definitions)
    if isinstance(r, dict) and r.get("contract") == "anibench.estimator-moments-request.v1":
        return core.evaluate_estimator_moments(r, trusted_definitions=registry)
    core._keys(r, {"contract", "definition_sha256", "lifecycle", "design", "moments"})
    if r["contract"] != "anibench.estimator-moments-request.v2":
        raise core.EstimatorMomentError("Unknown estimator request")
    key = r["definition_sha256"]
    if not isinstance(key, str) or key not in registry or digest(registry[key]) != key:
        raise core.EstimatorMomentError("Untrusted or stale estimator definition")
    d = validate_definition(registry[key])
    if d["contract"] != "anibench.estimator-moment-definition.v2":
        raise core.EstimatorMomentError("Request and definition versions must match")
    if r["lifecycle"] not in ("planned", "hypothetical", "realized"):
        raise core.EstimatorMomentError("Unknown study lifecycle")
    frame, inputs = core._design(r["design"], d)
    n = len(d["estimators"])
    lower, upper, b0, b1 = core._moments(r["moments"], n)
    support = list(r["design"]["support"].values())
    if r["lifecycle"] == "realized":
        support.append(r["design"]["collection_verified"])
    rows = []
    for f in d["functionals"]:
        weights, limit = core._vector(f["loss_weights"], n), core._number(f["mse_limit"])
        v0 = sum(w * lower[j][j] for j, w in enumerate(weights))
        v1 = None if upper is None else sum(w * upper[j][j] for j, w in enumerate(weights))
        if b0 is None:
            bias0, bias1 = Fraction(0), None
        else:
            bias0 = sum(w * (0 if a <= 0 <= b else min(a*a, b*b))
                        for w, a, b in zip(weights, b0, b1, strict=True))
            bias1 = sum(w * max(a*a, b*b) for w, a, b in zip(weights, b0, b1, strict=True))
        risk0 = v0 + bias0
        risk1 = None if v1 is None or bias1 is None else v1 + bias1
        flags = support + [inputs[e["estimator_id"]]["estimable"]
                           for w, e in zip(weights, d["estimators"], strict=True) if w]
        lo, hi = core._adequacy(limit, risk1), core._adequacy(limit, risk0)
        state, reason = "unknown", "Error bounds straddle the target or are unbounded"
        if False in flags:
            state, reason, lo, hi = "not_attained", "Required acquisition, support or estimability fails", Fraction(0), Fraction(0)
        elif None in flags:
            reason, lo, hi = "Required acquisition, support or estimability is unresolved", Fraction(0), Fraction(1)
        elif risk1 is not None and risk1 <= limit:
            state, reason = "attained", "Certified upper loss bound meets the frozen target"
        elif risk0 > limit:
            state, reason = "not_attained", "Certified lower loss bound exceeds the frozen target"
        rows.append({"functional_id": f["functional_id"], "unit": f["unit"],
                     "mse_limit": f["mse_limit"], "loss_weights": f["loss_weights"],
                     "attainment": state, "reason": reason,
                     "variance_loss": {"lower": core._bound(v0), "upper": core._bound(v1)},
                     "squared_bias_loss": {"lower": core._bound(bias0), "upper": core._bound(bias1)},
                     "mse": {"lower": core._bound(risk0), "upper": core._bound(risk1)},
                     "exact_mse_established_under_declared_model": risk0 == risk1,
                     "precision_toward_target": {"lower_percent": float(100 * lo), "upper_percent": float(100 * hi)}})
    states = [row["attainment"] for row in rows]
    result = {"contract": "anibench.estimator-moments-result.v2", "definition_sha256": key,
              "request_sha256": digest(r), "lifecycle": r["lifecycle"], "definition": d,
              "claim_scope": "finite_separable_quadratic_estimator_loss_under_declared_moment_bounds",
              "attainment": "not_attained" if "not_attained" in states else "unknown" if "unknown" in states else "attained",
              "functionals": rows, "design_frame": frame, "design_frame_sha256": digest(frame),
              "precision_toward_target": {k: min(row["precision_toward_target"][k] for row in rows)
                                          for k in ("lower_percent", "upper_percent")},
              "evidence_verification": "caller_declared_not_independently_certified",
              "uncertainty": "Outer moment/bias bounds; not confidence intervals",
              "joint_endpoint_attainability_established": False,
              "distributional_assumption": "None supplied by the evaluator; input moment derivations retain their own assumptions",
              "numerical_contract": "Exact rationals from str(received Python int/float); no threshold tolerance; original JSON lexemes are not available to this API",
              "implementation_sha256": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "shared_moment_core_sha256": "sha256:" + hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
              "all_direction_attainment": None, "empirical_learning_plateau": None,
              "public_rank_emission_permitted": False}
    result["receipt_sha256"] = digest(result)
    return result
