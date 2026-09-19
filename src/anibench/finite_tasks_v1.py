# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Frozen finite-functional Gaussian precision tasks, conditional and uncalibrated."""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Mapping
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator

from .information_v2 import prior_whitened_information

CONTRACT = "anibench.finite-task-precision.v1"
NUMERICAL_RELATIVE_TOLERANCE = 1e-10


class FiniteTaskError(ValueError):
    """Invalid task, identity, or declared geometry; not an unknown measurement."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise FiniteTaskError("Inputs must be finite JSON values") from exc


def finite_task_sha256(task: Mapping[str, Any]) -> str:
    """Bind exact task content; a digest neither validates nor endorses its science."""
    return "sha256:" + hashlib.sha256(_canonical(task)).hexdigest()


def _asset_path(filename: str) -> Path:
    relative = Path("schemas/finite_precision/v1") / filename
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parent):
        path = root / relative
        if path.is_file():
            return path
    raise FiniteTaskError("Finite-task schema is not installed")


def _schema() -> dict[str, Any]:
    return json.loads(_asset_path("evaluation-input.schema.json").read_text())


def _implementation_receipt() -> dict[str, Any]:
    directory = Path(__file__).resolve().parent
    files = {
        "finite_tasks_v1.py": directory / "finite_tasks_v1.py",
        "information_v2.py": directory / "information_v2.py",
        "evaluation-input.schema.json": _asset_path("evaluation-input.schema.json"),
        "evaluation-result.schema.json": _asset_path("evaluation-result.schema.json"),
    }
    return {
        "contract": "anibench.finite-task-implementation.v1",
        "sha256": {
            name: "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in files.items()
        },
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "jsonschema_version": version("jsonschema"),
    }


def _conjunction(states: list[str]) -> str:
    if "not_attained" in states:
        return "not_attained"
    if "unknown" in states:
        return "unknown"
    return "attained"


def _state(value: bool | None) -> str:
    return "unknown" if value is None else ("attained" if value else "not_attained")


def evaluate_finite_task(request: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate only frozen finite linear functionals, never all-direction saturation.

    Planned observations can meet conditional precision without outcomes or
    held-out model utility. Realized records additionally require collection
    verification. Declared evidence is bound and checked, not independently audited.
    """
    encoded = _canonical(request)
    # Work on a detached JSON snapshot, so caller mutation cannot change the receipt.
    payload = json.loads(encoded)
    errors = list(Draft202012Validator(_schema()).iter_errors(payload))
    if errors:
        raise FiniteTaskError("Input violates the finite-task schema")
    task = payload["task"]
    task_hash = finite_task_sha256(task)
    if payload["task_sha256"] != task_hash:
        raise FiniteTaskError("Task hash does not match the frozen task")
    dimension = len(task["parameter_units"])
    try:
        prior = np.asarray(task["prior_precision"], dtype=float)
    except (TypeError, ValueError) as exc:
        raise FiniteTaskError("Prior must be a rectangular numeric matrix") from exc
    functionals = task["functionals"]
    if len({f["functional_id"] for f in functionals}) != len(functionals):
        raise FiniteTaskError("Functional identifiers must be unique")
    for functional in functionals:
        c = functional["coefficients"]
        if len(c) != dimension or not any(value != 0 for value in c):
            raise FiniteTaskError("Each functional needs a nonzero dimension-aligned vector")
    if prior.shape != (dimension, dimension):
        raise FiniteTaskError("Prior must match the declared parameter dimension")
    # Validate the prior even if observation geometry is unavailable.
    try:
        prior_whitened_information(np.zeros_like(prior), prior)
    except (ValueError, TypeError, np.linalg.LinAlgError) as exc:
        raise FiniteTaskError(str(exc)) from exc
    prior = 0.5 * (prior + prior.T)
    required = [(r["domain_id"], r["role"]) for r in task["required_support"]]
    if len(set(required)) != len(required):
        raise FiniteTaskError("Required domain-role pairs must be unique")
    supports = payload["evidence"]["support"]
    keys = [(r["domain_id"], r["role"]) for r in supports]
    if len(set(keys)) != len(keys):
        raise FiniteTaskError("Evidence domain-role pairs must be unique")
    observed = {key: row["supported"] for key, row in zip(keys, supports, strict=True)}
    support_results = [
        {"domain_id": domain, "role": role, "state": _state(observed.get((domain, role)))}
        for domain, role in required
    ]
    checks = {"identifiability": _state(payload["evidence"]["identifiability"])}
    if task["claim_lane"] == "realized_record":
        checks["collection_verified"] = _state(payload["evidence"]["collection_verified"])
    geometry = payload["geometry"]
    whitened = None
    if geometry is not None:
        if geometry["model_sha256"] != task["model_sha256"]:
            raise FiniteTaskError("Geometry model identity differs from the frozen task")
        try:
            whitened = prior_whitened_information(geometry["information_matrix"], prior)
        except (ValueError, TypeError, np.linalg.LinAlgError) as exc:
            raise FiniteTaskError(str(exc)) from exc
    precision_results = []
    values, vectors = np.linalg.eigh(prior)
    inverse_sqrt = (vectors * (1 / np.sqrt(values))) @ vectors.T
    for functional in functionals:
        variance = None
        state = "unknown"
        c = inverse_sqrt @ np.asarray(functional["coefficients"], dtype=float)
        prior_variance = float(c @ c)
        if not np.isfinite(prior_variance) or prior_variance <= 0:
            raise FiniteTaskError("Prior functional variance must be finite and positive")
        prior_attained = prior_variance <= functional["variance_limit"] * (
            1 + NUMERICAL_RELATIVE_TOLERANCE
        )
        if whitened is not None:
            variance = float(c @ np.linalg.solve(np.eye(dimension) + whitened, c))
            if not np.isfinite(variance) or variance <= 0:
                raise FiniteTaskError("Posterior functional variance must be finite and positive")
            state = _state(
                variance <= functional["variance_limit"] * (1 + NUMERICAL_RELATIVE_TOLERANCE)
            )
        precision_results.append(
            {
                "functional_id": functional["functional_id"],
                "unit": functional["unit"],
                "posterior_variance": variance,
                "prior_variance": prior_variance,
                "prior_only_precision_attainment": prior_attained,
                "variance_reduction": (
                    None if variance is None else max(0.0, prior_variance - variance)
                ),
                "variance_limit": functional["variance_limit"],
                "state": state,
            }
        )
    states = [r["state"] for r in support_results + precision_results] + list(checks.values())
    return {
        "contract": CONTRACT,
        "implementation": _implementation_receipt(),
        "task_id": task["task_id"],
        "task_version": task["task_version"],
        "task_sha256": task_hash,
        "request_sha256": "sha256:" + hashlib.sha256(encoded).hexdigest(),
        "claim_lane": task["claim_lane"],
        "claim_scope": "conditional_gaussian_finite_functionals_not_biological_calibration",
        "comparison_scope": "finite_functionals_only",
        "attainment": _conjunction(states),
        "support": support_results,
        "checks": checks,
        "functionals": precision_results,
        "numerical_relative_tolerance": NUMERICAL_RELATIVE_TOLERANCE,
        "evidence_verification": "caller_declared_not_independently_certified",
        "all_direction_attainment": None,
        "empirical_learning_plateau": None,
        "public_saturation_claim_allowed": False,
        "promotion_allowed": False,
    }
