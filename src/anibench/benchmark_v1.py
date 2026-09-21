# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Frozen workload percentages over the existing likelihood-only suite evaluator.

This module aggregates task decisions; it does not infer biology from assay counts.
The trusted local registries are an explicit scientific choice, not certification.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .finite_suites_v1 import evaluate_finite_suite, suite_sha256

CONTRACT = "anibench.benchmark-result.v1"
_TEXT = {"type": "string", "minLength": 1, "pattern": r".*\S.*"}
_HASH = {"type": "string", "pattern": r"^sha256:[0-9a-f]{64}$"}


def _object(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _array(items: dict) -> dict:
    return {"type": "array", "items": items, "minItems": 1}


SCORE_PROFILE_SCHEMA = _object(
    {
        "contract": {"const": "anibench.score-profile.v1"},
        "score_profile_id": _TEXT,
        "suite_profile_sha256": _HASH,
        "weighting_rationale": _TEXT,
        "gate_only_targets": {"type": "array", "items": _TEXT, "uniqueItems": True},
        "views": _array(
            _object(
                {
                    "view_id": _TEXT,
                    "label": _TEXT,
                    "categories": _array(
                        _object(
                            {
                                "category_id": _TEXT,
                                "label": _TEXT,
                                "question": _TEXT,
                                "targets": _array(
                                    _object(
                                        {
                                            "canonical_id": _TEXT,
                                            "weight": {"type": "integer", "minimum": 1},
                                        }
                                    )
                                ),
                            }
                        )
                    ),
                }
            )
        ),
    }
)


class BenchmarkError(ValueError):
    """Invalid or incompatible frozen scoring declarations."""


def _snapshot(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise BenchmarkError("Expected finite JSON values") from exc


def _unique(rows: list[dict], key: str) -> None:
    if len({row[key] for row in rows}) != len(rows):
        raise BenchmarkError(f"Duplicate {key}")


def _validate_profile(score: dict, suite: dict) -> None:
    errors = list(Draft202012Validator(SCORE_PROFILE_SCHEMA).iter_errors(score))
    if errors:
        raise BenchmarkError("Score profile violates schema: " + errors[0].message)
    if suite["precision_basis"] != "likelihood_only":
        raise BenchmarkError("Acquired-information percentages require likelihood_only")
    modes = {t["task"]["claim_lane"] for t in suite["targets"]}
    if len(modes) != 1:
        raise BenchmarkError("A comparison profile must use one evidence mode")
    required = {t["canonical_id"] for t in suite["targets"]}
    gates = set(score["gate_only_targets"])
    if not gates <= required:
        raise BenchmarkError("Unregistered gate target")
    _unique(score["views"], "view_id")
    for view in score["views"]:
        _unique(view["categories"], "category_id")
        targets = [t for c in view["categories"] for t in c["targets"]]
        if any(type(t["weight"]) is not int for t in targets):
            raise BenchmarkError("Weights must be positive integer units of workload mass")
        _unique(targets, "canonical_id")
        if {t["canonical_id"] for t in targets} != required - gates:
            raise BenchmarkError("Each view must cover every scored target exactly once")


def _adequacy(row: dict, target: dict) -> tuple[float, float]:
    """Conjunctive precision progress, with support/identification uncertainty."""
    receipt = row["task_receipt"]
    if receipt is None:
        return (0.0, 0.0) if row["attainment"] == "not_attained" else (0.0, 1.0)
    gates = list(receipt["checks"].values()) + [s["state"] for s in receipt["support"]]
    if "not_attained" in gates:
        return 0.0, 0.0
    limits = {f["functional_id"]: f["variance_limit"] for f in target["task"]["functionals"]}
    lower, upper = [], []
    for diagnostic in row["likelihood_diagnostics"]:
        if diagnostic.get("identified") is False:
            lower.append(0.0)
            upper.append(0.0)
        elif diagnostic.get("identified") is True:
            value = min(1.0, limits[diagnostic["functional_id"]] / diagnostic["variance"])
            lower.append(value)
            upper.append(value)
        else:
            lower.append(0.0)
            upper.append(1.0)
    # Every registered functional must be represented by the underlying evaluator.
    if len(lower) != len(limits):
        raise BenchmarkError("Incomplete likelihood diagnostics")
    return (0.0 if "unknown" in gates else min(lower), min(upper))


def _category(category: dict, outcomes: dict, targets: dict) -> dict:
    total = sum(t["weight"] for t in category["targets"])
    passed = unknown = 0
    precision_lower = precision_upper = 0.0
    rows = []
    for declaration in category["targets"]:
        identity, weight = declaration["canonical_id"], declaration["weight"]
        row = outcomes[identity]
        state = row["attainment"]
        passed += weight if state == "attained" else 0
        unknown += weight if state == "unknown" else 0
        lower, upper = _adequacy(row, targets[identity])
        precision_lower += float(Fraction(weight, total)) * lower
        precision_upper += float(Fraction(weight, total)) * upper
        rows.append(
            {
                **declaration,
                "attainment": state,
                "precision_toward_target": {
                    "lower_percent": 100 * lower,
                    "upper_percent": 100 * upper,
                },
            }
        )
    return {
        "category_id": category["category_id"],
        "label": category["label"],
        "question": category["question"],
        "task_count": len(rows),
        "weight_total": total,
        "passed_weight": passed,
        "unknown_weight": unknown,
        "failed_weight": total - passed - unknown,
        "passed_percent": float(100 * Fraction(passed, total)),
        "unknown_percent": float(100 * Fraction(unknown, total)),
        "upper_percent": float(100 * Fraction(passed + unknown, total)),
        "precision_toward_targets": {
            "lower_percent": min(100.0, 100 * precision_lower),
            "upper_percent": min(100.0, 100 * precision_upper),
        },
        "uncertainty_kind": "unresolved_task_mass_outer_bound",
        "targets": rows,
    }


def evaluate_benchmark(
    request: Mapping[str, Any],
    *,
    trusted_profiles: Mapping[str, Any],
    trusted_score_profiles: Mapping[str, Any],
) -> dict:
    """Execute a suite and aggregate its decisions against one immutable workload.

    Supplied result receipts are never accepted in place of an actual evaluation.
    Each scenario is evaluated as a whole. Envelope bounds are conservative and
    need not be simultaneously attainable across categories or unresolved tasks.
    """
    request = _snapshot(request)
    registry, scores = _snapshot(trusted_profiles), _snapshot(trusted_score_profiles)
    if not isinstance(request, dict) or set(request) != {
        "contract",
        "score_profile_sha256",
        "suite_request",
    }:
        raise BenchmarkError("Expected contract, score_profile_sha256 and suite_request")
    if request["contract"] != "anibench.benchmark-request.v1":
        raise BenchmarkError("Unknown benchmark request contract")
    key = request["score_profile_sha256"]
    if not isinstance(key, str) or key not in scores or suite_sha256(scores[key]) != key:
        raise BenchmarkError("Untrusted or stale score profile")
    score = scores[key]
    if not isinstance(score, dict):
        raise BenchmarkError("Score profile must be a JSON object")
    # Run first: the suite validates all profiles, task frames and request geometry.
    suite_result = evaluate_finite_suite(request["suite_request"], trusted_profiles=registry)
    if score.get("suite_profile_sha256") != suite_result["profile_sha256"]:
        raise BenchmarkError("Scoring profile and evaluated suite differ")
    suite = registry[suite_result["profile_sha256"]]
    _validate_profile(score, suite)
    targets = {t["canonical_id"]: t for t in suite["targets"]}
    scenarios = []
    for scenario in suite_result["scenarios"]:
        outcomes = {t["canonical_id"]: t for t in scenario["targets"]}
        scenarios.append(
            {
                "scenario_id": scenario["scenario_id"],
                "attainment": scenario["attainment"],
                "gates": [
                    {"canonical_id": t, "attainment": outcomes[t]["attainment"]}
                    for t in score["gate_only_targets"]
                ],
                "views": [
                    {
                        "view_id": v["view_id"],
                        "label": v["label"],
                        "categories": [_category(c, outcomes, targets) for c in v["categories"]],
                    }
                    for v in score["views"]
                ],
            }
        )
    envelope = []
    for vi, view in enumerate(score["views"]):
        categories = []
        for ci, category in enumerate(view["categories"]):
            rows = [s["views"][vi]["categories"][ci] for s in scenarios]
            categories.append(
                {
                    "category_id": category["category_id"],
                    "label": category["label"],
                    "question": category["question"],
                    "lower_percent": min(r["passed_percent"] for r in rows),
                    "upper_percent": max(r["upper_percent"] for r in rows),
                    "uncertainty_kind": "scenario_and_unresolved_task_outer_bound",
                    "precision_toward_targets": {
                        "lower_percent": min(
                            r["precision_toward_targets"]["lower_percent"] for r in rows
                        ),
                        "upper_percent": max(
                            r["precision_toward_targets"]["upper_percent"] for r in rows
                        ),
                    },
                }
            )
        envelope.append(
            {"view_id": view["view_id"], "label": view["label"], "categories": categories}
        )
    result = {
        "contract": CONTRACT,
        "score_profile_id": score["score_profile_id"],
        "score_profile_sha256": key,
        "suite_profile_sha256": suite_result["profile_sha256"],
        "request_sha256": suite_sha256(request),
        "design_id": suite_result["design_id"],
        "design_source_sha256": suite_result["design_source_sha256"],
        "evidence_mode": next(iter(targets.values()))["task"]["claim_lane"],
        "metric_label": "Benchmark targets met (%)",
        "metric_meaning": "Passed weight divided by all frozen scored weight in this category",
        "level_attainment": suite_result["attainment"],
        "scenario_quantifier": suite_result["scenario_quantifier"],
        "scenarios": scenarios,
        "envelope": envelope,
        "envelope_joint_attainability_established": False,
        "envelope_interpretation": "Outer bounds; joint attainability is not asserted. Not confidence intervals.",
        "suite_result": suite_result,
        "score_profile": score,
        "implementation_sha256": "sha256:"
        + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "biological_calibration_established": False,
        "public_saturation_claim_allowed": False,
    }
    result["receipt_sha256"] = suite_sha256(result)
    return result
