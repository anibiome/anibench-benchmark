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
import importlib.metadata
import json
import platform
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .level1_target_v3 import (
    FAMILY_IDS,
    load_role_aware_authority,
    readback_role_aware_authority,
)
from .causal_v2 import contrast_information
from .information_v2 import absolute_mechanics
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
        ("effective_rank", "Population effective observed dimensions", "effective_dimensions"),
        ("retained_participant_events", "Retained participant-events", "participant_events"),
        (
            "retained_log10_contraction",
            "Population information contraction",
            "log10_posterior_volume_contraction",
        ),
    ),
    "longitudinal": (
        (
            "participant_weighted_median_distinct_offsets",
            "Participant-weighted median linked time points",
            "distinct_time_offsets",
        ),
        (
            "participant_weighted_median_span",
            "Participant-weighted median linked follow-up span",
            "protocol_time_units",
        ),
        ("retained_participant_events", "Linked retained participant-events", "participant_events"),
    ),
    "causal": (
        ("policy_rank", "Independent randomized contrasts", "effective_contrast_dimensions"),
        (
            "policy_allocation_support_factor",
            "Randomized policy allocation support",
            "allocation_support_proxy",
        ),
        ("component_rank", "Independent intervention components", "effective_component_dimensions"),
        (
            "component_allocation_support_factor",
            "Randomized component allocation support",
            "allocation_support_proxy",
        ),
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
        (
            "sequential_moderator_allocation_support_factor",
            "Randomized treatment-by-state allocation support",
            "allocation_support_proxy",
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


def _implementation_receipt() -> dict[str, Any]:
    paths = {
        "causal_v2.py": Path(contrast_information.__code__.co_filename),
        "information_v2.py": Path(absolute_mechanics.__code__.co_filename),
        "level1_assessment_v3.py": Path(__file__),
        "level1_target_v3.py": Path(load_role_aware_authority.__code__.co_filename),
        "protocol_capacity_v2.py": Path(compile_protocol_capacity.__code__.co_filename),
    }
    files = [
        {
            "module": module,
            "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for module, path in sorted(paths.items())
    ]
    try:
        package_version = importlib.metadata.version("anibench")
    except importlib.metadata.PackageNotFoundError:
        package_version = "source-tree-uninstalled"
    numpy_config = np.show_config(mode="dicts")
    build_dependencies = numpy_config.get("Build Dependencies", {})
    linear_algebra = {
        name: {
            "name": dependency.get("name", "unknown"),
            "version": dependency.get("version", "unknown"),
        }
        for name, dependency in sorted(build_dependencies.items())
        if name in {"blas", "lapack"}
    }
    return {
        "package_name": "anibench",
        "package_version": package_version,
        "source_modules": files,
        "source_bundle_sha256": _canonical_sha256(files),
        "runtime_environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "numpy_version": np.__version__,
            "jsonschema_version": importlib.metadata.version("jsonschema"),
            "system": platform.system().lower(),
            "machine": platform.machine().lower(),
            "linear_algebra": linear_algebra,
            "supported_environment_contract": (
                "deterministic within the tested Python/NumPy/platform matrix; "
                "tolerance-boundary replay must inspect this receipt"
            ),
        },
    }


def _native_metric(
    *,
    scenario_index: int,
    family_id: str,
    family: Mapping[str, Any],
    metric_id: str,
    label: str,
    unit: str,
    capacity_sha256: str,
    geometry_authority_state: str,
    source_locator: str | None = None,
    force_unresolved: bool = False,
) -> dict[str, Any]:
    value = None if force_unresolved else family.get(metric_id)
    state = (
        "computed_unverified_geometry"
        if value is not None and geometry_authority_state == "custom_unverified"
        else "resolved"
        if value is not None
        else "unresolved"
    )
    return {
        "metric_id": metric_id,
        "label": label,
        "value": value,
        "unit": unit,
        "state": state,
        "geometry_authority_state": geometry_authority_state,
        "source_object_sha256": capacity_sha256,
        "source_locator": source_locator
        or f"/scenarios/{scenario_index}/families/{family_id}/{metric_id}",
        "derivation": "anibench.protocol-capacity.v2 executable compiler output",
    }


def _metric_groups(
    *,
    scenario_index: int,
    family_id: str,
    family: Mapping[str, Any],
    capacity_sha256: str,
    geometry_authority_state: str,
    force_unresolved: bool = False,
) -> list[dict[str, Any]]:
    """Expose non-collapsible native metric vectors inside a benchmark family."""

    if family_id != "transport":
        return []
    groups: list[dict[str, Any]] = []
    for group_index, axis_family in enumerate(family.get("axis_family_frontier", [])):
        prefix = (
            f"/scenarios/{scenario_index}/families/transport/"
            f"axis_family_frontier/{group_index}"
        )
        groups.append(
            {
                "group_type": "transport_axis_family",
                "group_id": axis_family["transport_axis_family_id"],
                "reference_estimand_id": axis_family["reference_estimand_id"],
                "required_dimension_ids": axis_family["required_transport_axis_ids"],
                "design_resolution_state": axis_family["resolution_state"],
                "native_metrics": [
                    _native_metric(
                        scenario_index=scenario_index,
                        family_id=family_id,
                        family=axis_family,
                        metric_id=metric_id,
                        label=label,
                        unit=unit,
                        capacity_sha256=capacity_sha256,
                        geometry_authority_state=geometry_authority_state,
                        source_locator=f"{prefix}/{metric_id}",
                        force_unresolved=force_unresolved,
                    )
                    for metric_id, label, unit in _METRIC_SPECS["transport"]
                ],
            }
        )
    return groups


def _family_blocker_codes(
    *,
    family_id: str,
    scenario: Mapping[str, Any],
) -> list[str]:
    """Map unsupported dependence mechanisms to typed unknown eval output.

    The mechanics compiler keeps cluster and crossover declarations in its audit
    ledger, but it cannot identify their causal precision without ICC, cluster,
    period, sequence, and carryover geometry.  Zero would incorrectly mean
    measured absence of capacity, so the public eval emits an unresolved vector.
    """

    if family_id in {"causal", "personalized_sequential"}:
        causal = scenario["families"]["causal"]
        selected_ids = set(causal.get("selected_stage_ids", []))
        if any(
            (not selected_ids or row.get("stage_id") in selected_ids)
            and row.get("dependence_geometry_required")
            for row in causal.get("stage_ledger", [])
        ):
            return ["DEPENDENT_RANDOMIZATION_GEOMETRY_UNSUPPORTED"]
    if family_id == "transport":
        transport = scenario["families"]["transport"]
        context_rows = transport.get("transport_ledger", {}).get(
            "context_support_ledger", []
        )
        if any(row.get("dependence_geometry_required") for row in context_rows):
            return ["DEPENDENT_RANDOMIZATION_GEOMETRY_UNSUPPORTED"]
    return []


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
            blocker_codes = _family_blocker_codes(
                family_id=family_id,
                scenario=scenario,
            )
            force_unresolved = bool(blocker_codes)
            family_rows.append(
                {
                    "family_id": family_id,
                    "label": _FAMILY_LABELS[family_id],
                    "design_resolution_state": (
                        "unresolved_unsupported_dependence_geometry"
                        if force_unresolved
                        else family.get("resolution_state", "unresolved")
                    ),
                    "blocker_codes": blocker_codes,
                    "native_metrics": [
                        _native_metric(
                            scenario_index=scenario_index,
                            family_id=family_id,
                            family=family,
                            metric_id=metric_id,
                            label=label,
                            unit=unit,
                            capacity_sha256=capacity_sha256,
                            geometry_authority_state=compiled["ontology_binding_state"],
                            force_unresolved=force_unresolved,
                        )
                        for metric_id, label, unit in _METRIC_SPECS[family_id]
                    ],
                    "metric_groups": _metric_groups(
                        scenario_index=scenario_index,
                        family_id=family_id,
                        family=family,
                        capacity_sha256=capacity_sha256,
                        geometry_authority_state=compiled["ontology_binding_state"],
                        force_unresolved=force_unresolved,
                    ),
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
        "schema_version": "anibench.level1-role-aware-assessment.v3-candidate2",
        "protocol_id": compiled["protocol_id"],
        "claim_class": compiled["claim_class"],
        "empirical_attainment": compiled["empirical_attainment"],
        "protocol_sha256": compiled["protocol_sha256"],
        "protocol_capacity_result_sha256": capacity_sha256,
        "implementation_receipt": _implementation_receipt(),
        "geometry_authority_state": compiled["ontology_binding_state"],
        "source_binding_state": compiled["source_binding_state"],
        "level1_authority": readback,
        "interpretation": (
            "Native design geometry is computed for six noncompensatory families. "
            "Caller-declared custom operators, priors, and covariance remain explicitly "
            "computed_unverified_geometry until a content-verified Level-1 binding exists. "
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
