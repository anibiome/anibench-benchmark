# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Native aggregate sampling precision, compiled into the finite-task evaluator.

This adapter does not infer assay noise or causal identification from an SD. It
models uncertainty in a population mean (or a contrast of population means),
conditional on declared sampling assumptions and plug-in variance estimates.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .finite_tasks_v1 import evaluate_finite_task, finite_task_sha256

_TEXT = {"type": "string", "minLength": 1, "pattern": r".*\S.*"}
_HASH = {"type": "string", "pattern": r"^sha256:[0-9a-f]{64}$"}
_KINDS = {
    "population_mean": (1, "individual_level"),
    "population_mean_change": (1, "individual_paired_change"),
    "population_contrast": (2, "individual_level"),
    "population_change_contrast": (2, "individual_paired_change"),
}


def _object(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_STATUS = {"enum": ["assumed", "source_supported", "unknown", "violated"]}
_GROUP = {
    "group_id": _TEXT,
    "n_independent": {"type": ["integer", "null"], "minimum": 2},
    "individual_quantity": {"enum": ["individual_level", "individual_paired_change"]},
    "source_sha256": _HASH,
    "source_locator": _TEXT,
    "n_locator": _TEXT,
    "spread_locator": _TEXT,
    "extraction_status": {"enum": ["source_supported", "declared", "unknown"]},
}
_POSITIVE_OR_UNKNOWN = {"type": ["number", "null"], "exclusiveMinimum": 0}
_GROUP_SCHEMA = {
    "oneOf": [
        _object({**_GROUP, "sample_sd": _POSITIVE_OR_UNKNOWN}),
        _object({**_GROUP, "unadjusted_mean_se": _POSITIVE_OR_UNKNOWN}),
    ]
}
SUMMARY_SCHEMA = _object(
    {
        "contract": {"const": "anibench.scalar-summary.v1"},
        "estimand_kind": {"enum": list(_KINDS)},
        "unit": _TEXT,
        "population_scope": _TEXT,
        "occasion_or_change_window": _TEXT,
        "measurement_definition": _TEXT,
        "variance_multiplier": {"type": "number", "exclusiveMinimum": 0},
        "variance_multiplier_rationale": _TEXT,
        "assumptions": _object(
            {
                "independent_sampling_units": _STATUS,
                "groups_disjoint_and_independent": _STATUS,
                "sampling_supports_declared_population": _STATUS,
                "gaussian_sampling_approximation": _STATUS,
                "rationale": _TEXT,
            }
        ),
        "groups": {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": _GROUP_SCHEMA,
        },
    }
)


class SummaryGeometryError(ValueError):
    """Invalid summary, incompatible target or unsupported numerical variance."""


def summary_model(estimand_kind: str) -> dict:
    """Common scientific model identity, independent of study name or outcome."""
    if estimand_kind not in _KINDS:
        raise SummaryGeometryError("Unknown estimand kind")
    return {
        "contract": "anibench.scalar-summary-model.v1",
        "estimand_kind": estimand_kind,
        "formula": "variance = variance_multiplier * sum(group_mean_variance_g)",
        "group_mean_variance": "sample_sd_g ** 2 / n_g OR source-reported unadjusted_mean_se_g ** 2",
        "observation_model": "scalar Gaussian sampling distribution of the declared mean or contrast",
        "source_individual_quantity": _KINDS[estimand_kind][1],
        "contrast_order": "group 1 minus group 0" if _KINDS[estimand_kind][0] == 2 else None,
        "variance_estimation": "plug-in sample variance; estimation uncertainty not integrated",
        "limitations": [
            "Not measurement error variance of an individual or a fixed observed-record mean",
            "Paired changes require individual-change SD and paired-person N, or unadjusted paired-change mean SE",
            "No pooled marginal-visit SD, unreported cross-group covariance or effective N substitution",
            "No causal identification, unbiased sampling or transportability inferred from a variance",
            "No treatment benefit or effect estimate enters capacity",
            "Sensitivity multipliers are assumptions, not confidence intervals",
        ],
    }


def summary_model_sha256(estimand_kind: str) -> str:
    return finite_task_sha256(summary_model(estimand_kind))


def compile_summary_task(
    task: Mapping[str, Any], summary: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict:
    """Return a validated finite-task request plus its inspectable derivation.

    ``evidence`` retains the existing finite-task semantics. In particular,
    collection verification and acquisition/assignment support are supplied by
    a qualified adapter or reviewer; this function never upgrades those facts.
    Hashes bind declarations and do not independently verify source documents.
    """
    try:
        payload = json.loads(json.dumps(dict(summary), allow_nan=False))
        target = json.loads(json.dumps(dict(task), allow_nan=False))
        facts = json.loads(json.dumps(dict(evidence), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise SummaryGeometryError("Expected finite JSON objects") from exc
    errors = list(Draft202012Validator(SUMMARY_SCHEMA).iter_errors(payload))
    if errors:
        raise SummaryGeometryError("Summary violates schema: " + errors[0].message)
    kind = payload["estimand_kind"]
    count, quantity = _KINDS[kind]
    groups = payload["groups"]
    if len(groups) != count or len({g["group_id"] for g in groups}) != count:
        raise SummaryGeometryError("Wrong group count or duplicate group identity")
    if any(g["individual_quantity"] != quantity for g in groups):
        raise SummaryGeometryError("Spread does not describe the registered individual quantity")
    if any(g["n_independent"] is not None and type(g["n_independent"]) is not int for g in groups):
        raise SummaryGeometryError("Independent-person counts must be integers, not weights")
    if target.get("model_sha256") != summary_model_sha256(kind):
        raise SummaryGeometryError("Task does not bind this exact sampling model")
    for summary_key, task_key in (
        ("population_scope", "target_population"),
        ("occasion_or_change_window", "horizon"),
        ("measurement_definition", "estimand"),
    ):
        if payload[summary_key] != target.get(task_key):
            raise SummaryGeometryError(
                "Summary scientific frame differs from frozen task: " + task_key
            )
    functionals = target.get("functionals", [])
    if (
        target.get("parameter_units") != [payload["unit"]]
        or len(functionals) != 1
        or functionals[0].get("coefficients") != [1]
        or functionals[0].get("unit") != payload["unit"]
    ):
        raise SummaryGeometryError("Task must assess this scalar in its exact native unit")

    statuses = [v for k, v in payload["assumptions"].items() if k != "rationale"]
    reasons = []
    if "violated" in statuses:
        reasons.append("Declared sampling assumption violated; formula is inapplicable")
    if "unknown" in statuses:
        reasons.append("Sampling assumptions unresolved")
    if any(g["extraction_status"] == "unknown" for g in groups):
        reasons.append("Source extraction unresolved")
    if any(
        (g["sample_sd"] is None or g["n_independent"] is None)
        if "sample_sd" in g
        else g["unadjusted_mean_se"] is None
        for g in groups
    ):
        reasons.append("Required count/individual SD or reported mean SE unavailable")

    terms, variance, geometry = [], None, None
    if not reasons:
        try:
            terms = [
                g["sample_sd"] ** 2 / g["n_independent"]
                if "sample_sd" in g
                else g["unadjusted_mean_se"] ** 2
                for g in groups
            ]
            variance = payload["variance_multiplier"] * math.fsum(terms)
            information = 1.0 / variance
        except (OverflowError, ZeroDivisionError) as exc:
            raise SummaryGeometryError("Sampling variance outside supported numeric range") from exc
        if not all(math.isfinite(v) and v > 0 for v in [*terms, variance, information]):
            raise SummaryGeometryError("Sampling variance outside supported numeric range")
        geometry = {
            "model_sha256": target["model_sha256"],
            "information_matrix": [[information]],
        }
    request = {
        "contract": "anibench.finite-task-request.v1",
        "task": target,
        "task_sha256": finite_task_sha256(target),
        "evidence": facts,
        "geometry": geometry,
    }
    # Use the canonical validator/evaluator, rather than a competing task schema.
    evaluate_finite_task(request)
    result = {
        "contract": "anibench.scalar-summary-derivation.v1",
        "summary_sha256": finite_task_sha256(payload),
        "summary": payload,
        "model": summary_model(kind),
        "compiler_sha256": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": "conditional_geometry" if geometry else "geometry_unavailable",
        "reasons": reasons,
        "unscaled_group_variances": terms,
        "sampling_variance": variance,
        "sampling_variance_unit": f"({payload['unit']})^2",
        "source_documents_independently_verified": False,
        "biological_calibration_established": False,
        "finite_task_request": copy.deepcopy(request),
    }
    result["derivation_sha256"] = finite_task_sha256(result)
    return result
