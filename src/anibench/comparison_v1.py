"""Strict same-basis Pareto comparison for canonical AniBench eval receipts.

This module deliberately does not create a scalar score or ordinal leaderboard.
It compares only native metrics that share the same executable implementation,
Level-1 authority, geometry authority state, and parameter-space source object.
Caller-declared geometry remains a sandbox even when its hashes match.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


class EvalComparisonError(ValueError):
    """Raised when eval receipts do not share a defensible comparison basis."""


_ORDERED_BOOLEAN_METRICS = {"structural_personalization_eligible"}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _shared_basis(receipt: Mapping[str, Any]) -> dict[str, Any]:
    implementation = receipt["implementation_receipt"]
    authority = receipt["level1_authority"]
    uncertainty = receipt["protocol_capacity_result"]["uncertainty_reuse"]
    return {
        "assessment_schema_version": receipt["schema_version"],
        "implementation_source_bundle_sha256": implementation["source_bundle_sha256"],
        "level1_authority_raw_sha256": authority["authority_raw_sha256"],
        "level1_target_id": authority["target_id"],
        "geometry_authority_state": receipt["geometry_authority_state"],
        "parameter_space_id": uncertainty["parameter_space_id"],
        "parameter_space_source_object_sha256": uncertainty[
            "parameter_space_source_object_sha256"
        ],
    }


def _verify_assessment_receipt(receipt: Mapping[str, Any], *, index: int) -> None:
    submitted = dict(receipt)
    claimed = submitted.pop("assessment_receipt_sha256", None)
    if not isinstance(claimed, str) or _canonical_sha256(submitted) != claimed:
        raise EvalComparisonError(f"receipt {index} assessment hash does not verify")


def _family_objectives(family: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    blockers = list(family.get("blocker_codes", []))
    objectives: list[dict[str, Any]] = []
    metrics = family["native_metrics"]
    if family.get("metric_groups"):
        metrics = [
            {
                **metric,
                "objective_id": (
                    f"group:{group['group_type']}:{group['group_id']}:"
                    f"{metric['metric_id']}"
                ),
            }
            for group in family["metric_groups"]
            for metric in group["native_metrics"]
        ]
    for metric in metrics:
        value = metric["value"]
        if isinstance(value, bool):
            if metric["metric_id"] in _ORDERED_BOOLEAN_METRICS:
                objectives.append(
                    {
                        "objective_id": metric.get(
                            "objective_id", f"metric:{metric['metric_id']}"
                        ),
                        "metric_id": metric["metric_id"],
                        "unit": metric["unit"],
                        "ordering": "true_dominates_false",
                        "value": value,
                    }
                )
            continue
        objective_id = metric.get("objective_id", f"metric:{metric['metric_id']}")
        if value is None:
            blockers.append(f"UNRESOLVED_OBJECTIVE:{objective_id}")
            continue
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            blockers.append(f"NONFINITE_OBJECTIVE:{objective_id}")
            continue
        objectives.append(
            {
                "objective_id": objective_id,
                "metric_id": metric["metric_id"],
                "unit": metric["unit"],
                "ordering": "maximize",
                "value": float(value),
            }
        )
    if not objectives:
        blockers.append("NO_NUMERIC_OBJECTIVES")
    return objectives, sorted(set(blockers))


def _dominates(
    left: Mapping[str, float | bool], right: Mapping[str, float | bool]
) -> bool:
    keys = tuple(sorted(left))
    return all(left[key] >= right[key] for key in keys) and any(
        left[key] > right[key] for key in keys
    )


def compare_trial_evals(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare two or more canonical eval receipts on a strict shared basis."""

    if len(receipts) < 2:
        raise EvalComparisonError("at least two eval receipts are required")
    copied = [dict(receipt) for receipt in receipts]
    for index, receipt in enumerate(copied):
        if receipt.get("schema_version") != (
            "anibench.level1-role-aware-assessment.v3-candidate2"
        ):
            raise EvalComparisonError(f"receipt {index} is not a canonical AniBench eval")
        if len(receipt.get("scenarios", [])) != 1:
            raise EvalComparisonError(
                f"receipt {index} must contain exactly one scenario for comparison"
            )
        _verify_assessment_receipt(receipt, index=index)

    protocol_ids = [receipt["protocol_id"] for receipt in copied]
    if len(protocol_ids) != len(set(protocol_ids)):
        raise EvalComparisonError("protocol_id values must be unique")
    bases = [_shared_basis(receipt) for receipt in copied]
    if any(basis != bases[0] for basis in bases[1:]):
        raise EvalComparisonError(
            "eval receipts do not share the same implementation, Level-1 authority, "
            "geometry authority, and parameter-space source object"
        )

    family_ids = [
        family["family_id"] for family in copied[0]["scenarios"][0]["families"]
    ]
    family_results: list[dict[str, Any]] = []
    for family_index, family_id in enumerate(family_ids):
        protocol_vectors: list[dict[str, Any]] = []
        objective_contract: list[dict[str, str]] | None = None
        family_blockers: list[str] = []
        for receipt in copied:
            family = receipt["scenarios"][0]["families"][family_index]
            if family["family_id"] != family_id:
                raise EvalComparisonError("family order or identity differs across receipts")
            objectives, blockers = _family_objectives(family)
            contract = [
                {
                    "objective_id": row["objective_id"],
                    "metric_id": row["metric_id"],
                    "unit": row["unit"],
                    "ordering": row["ordering"],
                }
                for row in objectives
            ]
            if objective_contract is None:
                objective_contract = contract
            elif contract != objective_contract:
                family_blockers.append("OBJECTIVE_CONTRACT_MISMATCH")
            family_blockers.extend(
                f"{receipt['protocol_id']}:{blocker}" for blocker in blockers
            )
            protocol_vectors.append(
                {
                    "protocol_id": receipt["protocol_id"],
                    "claim_class": receipt["claim_class"],
                    "scenario_id": receipt["scenarios"][0]["scenario_id"],
                    "assessment_receipt_sha256": receipt["assessment_receipt_sha256"],
                    "objectives": objectives,
                    "non_ordering_boolean_metrics": [
                        {
                            "metric_id": metric["metric_id"],
                            "value": metric["value"],
                        }
                        for metric in family["native_metrics"]
                        if isinstance(metric["value"], bool)
                        and metric["metric_id"] not in _ORDERED_BOOLEAN_METRICS
                    ],
                }
            )

        eligible = not family_blockers
        dominance: list[dict[str, str]] = []
        front = list(protocol_ids)
        if eligible:
            vectors = {
                row["protocol_id"]: {
                    objective["objective_id"]: objective["value"]
                    for objective in row["objectives"]
                }
                for row in protocol_vectors
            }
            for left_id in protocol_ids:
                for right_id in protocol_ids:
                    if left_id != right_id and _dominates(vectors[left_id], vectors[right_id]):
                        dominance.append(
                            {"dominant_protocol_id": left_id, "dominated_protocol_id": right_id}
                        )
            dominated_ids = {row["dominated_protocol_id"] for row in dominance}
            front = [protocol_id for protocol_id in protocol_ids if protocol_id not in dominated_ids]

        family_results.append(
            {
                "family_id": family_id,
                "comparison_eligible": eligible,
                "blocker_codes": sorted(set(family_blockers)),
                "objective_contract": objective_contract or [],
                "protocol_vectors": protocol_vectors,
                "pairwise_dominance": dominance,
                "pareto_front_protocol_ids": front if eligible else [],
                "ordinal_rank": None,
            }
        )

    comparison_class = (
        "caller_declared_geometry_pareto_sandbox"
        if bases[0]["geometry_authority_state"] == "custom_unverified"
        else "content_verified_geometry_pareto"
    )
    result: dict[str, Any] = {
        "schema_version": "anibench.eval-comparison.v1",
        "comparison_implementation_sha256": (
            "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ),
        "comparison_class": comparison_class,
        "interpretation": (
            "Pareto relations compare only shared native metrics within each "
            "noncompensatory family. They are not an overall score or ordinal rank. "
            "Prospective and realized geometry may be compared without a maturity "
            "penalty, but their claim classes remain visible. Caller-declared geometry "
            "remains a sandbox until content verification."
        ),
        "shared_basis": bases[0],
        "protocol_ids": protocol_ids,
        "source_assessment_receipt_sha256s": [
            receipt["assessment_receipt_sha256"] for receipt in copied
        ],
        "families": family_results,
        "comparison_eligible": all(row["comparison_eligible"] for row in family_results),
        "overall_scalar": None,
        "overall_rank": None,
        "public_rank_emission_permitted": False,
        "promotion_allowed": False,
    }
    result["comparison_receipt_sha256"] = _canonical_sha256(result)
    return result
