"""Compile a trial protocol into six role-aware AniBench families.

The assessment deliberately separates two questions:

1. What design geometry does this protocol actually contain?
2. Has a normative Level-1 operating-characteristic target been authorized?

The first is computed and source-located.  The second remains a typed unknown
until the v3 authority gates are closed.  A missing target is never converted
to zero and no scalar score or public rank is emitted.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from .level1_target_v3 import (
    FAMILY_IDS,
    load_role_aware_authority,
    readback_role_aware_authority,
)
from .protocol_capacity_v2 import compile_protocol_capacity


class Level1RoleAwareAssessmentError(ValueError):
    """Raised when a role-aware assessment cannot be constructed."""


_FAMILY_LABELS = {
    "intensive": "Depth per participant-event",
    "extensive": "Breadth and population reach",
    "longitudinal": "Repeated-state resolution",
    "causal": "Intervention identifiability",
    "personalized_sequential": "Personalization and adaptive policy",
    "transport": "Generalization across contexts",
}

_METRIC_SPECS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "intensive": (
        ("effective_rank", "Effective observed dimensions", "effective_dimensions"),
        (
            "maximum_joint_bundle_log10_contraction",
            "Within-event information contraction",
            "log10_posterior_volume_contraction",
        ),
    ),
    "extensive": (
        ("retained_participant_events", "Retained participant-events", "participant_events"),
        (
            "retained_log10_contraction",
            "Population information contraction",
            "log10_posterior_volume_contraction",
        ),
    ),
    "longitudinal": (
        (
            "maximum_within_participant_distinct_offsets",
            "Maximum linked time points",
            "distinct_time_offsets",
        ),
        ("maximum_within_participant_span", "Maximum linked follow-up span", "protocol_time_units"),
        ("retained_participant_events", "Linked retained participant-events", "participant_events"),
    ),
    "causal": (
        ("policy_rank", "Independent randomized contrasts", "effective_contrast_dimensions"),
        ("component_rank", "Independent intervention components", "effective_component_dimensions"),
        ("eligible_randomized_participants", "Outcome-linked randomized participants", "participants"),
        (
            "eligible_randomized_participant_decisions",
            "Outcome-linked randomized decisions",
            "participant_decisions",
        ),
    ),
    "personalized_sequential": (
        (
            "sequential_moderator_rank",
            "Independent treatment-by-state directions",
            "effective_moderator_dimensions",
        ),
        ("eligible_randomized_participants", "Personalization-eligible participants", "participants"),
        (
            "eligible_randomized_participant_decisions",
            "Personalization-eligible decisions",
            "participant_decisions",
        ),
        (
            "structural_personalization_eligible",
            "Adaptive personalization structure present",
            "boolean",
        ),
    ),
    "transport": (
        ("transport_rank", "Independent transport directions", "effective_transport_dimensions"),
        (
            "transport_allocation_support_factor",
            "Randomized transport support",
            "allocation_support_proxy",
        ),
    ),
}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _native_metric(
    *,
    scenario_index: int,
    family_id: str,
    family: Mapping[str, Any],
    metric_id: str,
    label: str,
    unit: str,
    capacity_sha256: str,
) -> dict[str, Any]:
    value = family.get(metric_id)
    state = "resolved" if value is not None else "unresolved"
    return {
        "metric_id": metric_id,
        "label": label,
        "value": value,
        "unit": unit,
        "state": state,
        "source_object_sha256": capacity_sha256,
        "source_locator": (
            f"/scenarios/{scenario_index}/families/{family_id}/{metric_id}"
        ),
        "derivation": "anibench.protocol-capacity.v2 executable compiler output",
    }


def assess_protocol_capacity_role_aware(protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic six-family design receipt against Level-1 v3."""

    submitted = copy.deepcopy(dict(protocol))
    compiled = compile_protocol_capacity(submitted)
    authority = load_role_aware_authority()
    readback = readback_role_aware_authority()
    authority_families = {
        row["family_id"]: row
        for row in authority["family_operating_characteristic_authority"]["families"]
    }
    scenarios: list[dict[str, Any]] = []
    capacity_sha256 = _canonical_sha256(compiled)
    for scenario_index, scenario in enumerate(compiled["scenarios"]):
        family_rows: list[dict[str, Any]] = []
        for family_id in FAMILY_IDS:
            family = scenario["families"][family_id]
            target = authority_families[family_id]
            family_rows.append(
                {
                    "family_id": family_id,
                    "label": _FAMILY_LABELS[family_id],
                    "design_resolution_state": family.get("resolution_state", "unresolved"),
                    "native_metrics": [
                        _native_metric(
                            scenario_index=scenario_index,
                            family_id=family_id,
                            family=family,
                            metric_id=metric_id,
                            label=label,
                            unit=unit,
                            capacity_sha256=capacity_sha256,
                        )
                        for metric_id, label, unit in _METRIC_SPECS[family_id]
                    ],
                    "level1_target_attainment": {
                        "fact_type": "unknown",
                        "state": "unresolved",
                        "value": None,
                        "unit": None,
                        "reason_code": "LEVEL1_FAMILY_OPERATING_CHARACTERISTIC_UNRESOLVED",
                        "required_gate_ids": target["required_gate_ids"],
                    },
                    "level1_enrollment_requirement": copy.deepcopy(
                        target["family_enrollment_requirement"]
                    ),
                }
            )
        scenarios.append(
            {
                "scenario_id": scenario["scenario_id"],
                "families": family_rows,
                "overall_scalar": None,
                "public_rank": None,
            }
        )

    receipt: dict[str, Any] = {
        "schema_version": "anibench.level1-role-aware-assessment.v3-candidate1",
        "protocol_id": compiled["protocol_id"],
        "claim_class": compiled["claim_class"],
        "empirical_attainment": compiled["empirical_attainment"],
        "protocol_sha256": compiled["protocol_sha256"],
        "protocol_capacity_result_sha256": capacity_sha256,
        "level1_authority": readback,
        "interpretation": (
            "Native design geometry is computed for six noncompensatory families. "
            "Normative Level-1 attainment remains unresolved until each family's "
            "operating-characteristic authority is source-bound. Unknown is not zero."
        ),
        "scenarios": scenarios,
        "protocol_capacity_result": compiled,
        "comparison_eligible": False,
        "promotion_allowed": False,
        "public_rank_emission_permitted": False,
        "overall_scalar": None,
    }
    receipt["assessment_receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def level1_role_aware_authority_summary() -> dict[str, Any]:
    """Return the installed role map and its hash-bound readback proof."""

    authority = load_role_aware_authority()
    return {
        "schema_version": "anibench.level1-role-aware-authority-summary.v1",
        "readback": readback_role_aware_authority(),
        "authority": authority,
        "promotion_allowed": False,
    }
