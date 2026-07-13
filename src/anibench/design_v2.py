"""Source-honest AniBench v2 trial-design compiler."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


INPUT_CONTRACT = "anibench.design-input.v2-candidate1"
OUTPUT_CONTRACT = "anibench.design-assessment.v2-candidate1"
EVIDENCE_STATES = {"exact", "conditional", "unknown"}
TRI_STATE_FIELDS = (
    "randomized_policy",
    "concurrent_control",
    "adaptive_reassignment",
    "within_policy_randomized",
)


class DesignInputError(ValueError):
    """Raised when a design input violates its schema or semantic contract."""


def _schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    candidates = (
        root / "schemas" / "v2" / "design-input.schema.json",
        Path(__file__).resolve().parent / "schemas" / "v2" / "design-input.schema.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise DesignInputError("v2 design-input schema is not installed")


def _error_path(error: Any) -> str:
    return "/" + "/".join(str(part) for part in error.absolute_path)


def validate_design_input(payload: Mapping[str, Any]) -> None:
    """Validate both JSON shape and cross-field semantics."""
    materialized = dict(payload)
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(materialized),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    messages = [f"{_error_path(error)}: {error.message}" for error in errors]
    if not errors:
        for field in ("population", "duration"):
            coordinate = materialized[field]
            state = coordinate["state"]
            value = coordinate["value"]
            if state == "unknown" and value is not None:
                messages.append(f"/{field}/value: must be null when /{field}/state is unknown")
            if state in {"exact", "conditional"} and value is None:
                messages.append(
                    f"/{field}/value: must be a positive integer when /{field}/state is {state}"
                )

        module_ids: set[str] = set()
        for index, module in enumerate(materialized["measurement_modules"]):
            module_id = module["module_id"]
            if module_id in module_ids:
                messages.append(
                    f"/measurement_modules/{index}/module_id: duplicate module_id {module_id!r}"
                )
            module_ids.add(module_id)
            if (
                module["evidence_state"] == "unknown"
                and module["events_per_participant"] is not None
            ):
                messages.append(
                    f"/measurement_modules/{index}/events_per_participant: "
                    "must be null when evidence_state is unknown"
                )

        families = materialized["operator_families"]
        folded = [family.casefold() for family in families]
        if len(folded) != len(set(folded)):
            messages.append("/operator_families: identifiers must be unique after case folding")

        arms = materialized["policy_arms"]
        if materialized["randomized_policy"] is True and (arms is None or arms < 2):
            messages.append(
                "/randomized_policy: true requires /policy_arms to declare at least two arms"
            )
        if materialized["concurrent_control"] is True and (arms is None or arms < 2):
            messages.append(
                "/concurrent_control: true requires /policy_arms to declare at least two arms"
            )

    if messages:
        raise DesignInputError("\n".join(messages))


def load_design_input(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DesignInputError(f"could not load v2 design input: {exc}") from exc
    if not isinstance(payload, dict):
        raise DesignInputError("v2 design input must be one JSON object")
    validate_design_input(payload)
    return payload


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _declared_coordinate(
    *, value: Any, state: str, semantics: str, pointers: list[str], unit: str | None = None
) -> dict[str, Any]:
    coordinate: dict[str, Any] = {
        "value": value,
        "state": state,
        "semantics": semantics,
        "evidence_class": "self_declared",
        "source_json_pointers": pointers,
    }
    if unit is not None:
        coordinate["unit"] = unit
    return coordinate


def _gate(
    gate_id: str,
    objective: str,
    pointers: list[str],
    reason: str,
    close_when: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "objective": objective,
        "source_json_pointers": pointers,
        "reason": reason,
        "close_when": close_when,
    }


def _upgrade(
    upgrade_id: str,
    objective: str,
    pointers: list[str],
    design_change: str,
    decision_rule: str,
) -> dict[str, Any]:
    return {
        "upgrade_id": upgrade_id,
        "objective": objective,
        "source_json_pointers": pointers,
        "design_change": design_change,
        "decision_rule": decision_rule,
    }


def _open_gates(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for field in ("population", "duration"):
        coordinate = payload[field]
        if coordinate["state"] != "exact":
            gates.append(
                _gate(
                    f"resolve_{field}_{coordinate['state']}",
                    "source_resolution",
                    [f"/{field}/value", f"/{field}/state", f"/{field}/semantics"],
                    f"{field} is {coordinate['state']}, not exact",
                    f"bind an exact {field} value and preserve its declared semantics",
                )
            )

    if payload["policy_arms"] is None:
        gates.append(
            _gate(
                "declare_policy_arms",
                "causal_architecture",
                ["/policy_arms"],
                "policy-arm count is not established",
                "declare the number of policies participants can receive",
            )
        )
    for field in TRI_STATE_FIELDS:
        if payload[field] is None:
            gates.append(
                _gate(
                    f"resolve_{field}",
                    "causal_architecture",
                    [f"/{field}"],
                    f"{field} is not source-established",
                    f"bind {field} to true or false from the design source",
                )
            )

    if not payload["operator_families"]:
        gates.append(
            _gate(
                "declare_operator_families",
                "intervention_observability",
                ["/operator_families"],
                "no intervention operator family is declared",
                "name each distinct intervention operator family",
            )
        )

    for index, module in enumerate(payload["measurement_modules"]):
        base = f"/measurement_modules/{index}"
        if module["evidence_state"] != "exact":
            gates.append(
                _gate(
                    f"resolve_module_{module['module_id']}_{module['evidence_state']}",
                    "measurement_observability",
                    [f"{base}/evidence_state"],
                    f"measurement module {module['module_id']} is {module['evidence_state']}",
                    "bind module deployment to an exact protocol or realized-data source",
                )
            )
        if module["events_per_participant"] is None:
            gates.append(
                _gate(
                    f"declare_module_{module['module_id']}_events",
                    "temporal_resolution",
                    [f"{base}/events_per_participant"],
                    f"events per participant are not established for {module['module_id']}",
                    "declare the scheduled or realized participant-event count",
                )
            )

    if payload["assessment_lane"] in {
        "registered",
        "realized",
        "accessible",
        "demonstrated",
    }:
        gates.append(
            _gate(
                "bind_assessment_lane_source_receipt",
                "source_resolution",
                ["/assessment_lane"],
                "the lane is self-declared in this compact input contract",
                "bind the assessment to the content-hashed source and execution receipt required by its evidence lane",
            )
        )
    return gates


def _design_upgrades(payload: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    upgrades: dict[str, list[dict[str, Any]]] = {
        "causal_identifiability": [],
        "temporal_resolution": [],
        "measurement_observability": [],
        "personalization_learning": [],
        "population_precision": [],
        "operator_identifiability": [],
    }
    arms = payload["policy_arms"]
    if arms is None or arms < 2:
        upgrades["causal_identifiability"].append(
            _upgrade(
                "declare_comparable_policies",
                "causal_identifiability",
                ["/policy_arms"],
                "Define at least two explicit policies when a between-policy effect is an objective.",
                "Apply only when the target estimand compares policies; otherwise retain the declared design.",
            )
        )
    if payload["randomized_policy"] is not True:
        upgrades["causal_identifiability"].append(
            _upgrade(
                "randomize_policy_assignment",
                "causal_identifiability",
                ["/randomized_policy", "/policy_arms"],
                "Add randomized policy assignment with recorded allocation probabilities.",
                "Apply when exchangeable policy contrasts are required and randomization is feasible.",
            )
        )
    if payload["concurrent_control"] is not True:
        upgrades["causal_identifiability"].append(
            _upgrade(
                "add_concurrent_control_policy",
                "causal_identifiability",
                ["/concurrent_control", "/policy_arms"],
                "Add an explicit concurrent comparator policy matched to the intervention clock.",
                "Apply when temporal drift or secular change could affect the target estimand.",
            )
        )

    duration = payload["duration"]
    if duration["state"] != "exact":
        upgrades["temporal_resolution"].append(
            _upgrade(
                "freeze_duration_clock",
                "temporal_resolution",
                ["/duration/value", "/duration/state", "/duration/semantics"],
                "Freeze the exact observation clock and name whether it is intervention, follow-up, or total duration.",
                "Apply before comparing duration across designs or computing event density.",
            )
        )
    single_event_modules = [
        module["module_id"]
        for module in payload["measurement_modules"]
        if module["events_per_participant"] == 1
    ]
    if single_event_modules:
        pointers = [
            f"/measurement_modules/{index}/events_per_participant"
            for index, module in enumerate(payload["measurement_modules"])
            if module["events_per_participant"] == 1
        ]
        upgrades["temporal_resolution"].append(
            _upgrade(
                "add_repeated_measurement_events",
                "temporal_resolution",
                pointers,
                "Add repeated events for modules intended to estimate within-person movement: "
                + ", ".join(single_event_modules)
                + ".",
                "Apply only to modules intended to estimate change, velocity, recovery, or response dynamics.",
            )
        )

    unresolved_modules = [
        module["module_id"]
        for module in payload["measurement_modules"]
        if module["evidence_state"] != "exact" or module["events_per_participant"] is None
    ]
    if unresolved_modules:
        upgrades["measurement_observability"].append(
            _upgrade(
                "freeze_measurement_schedule",
                "measurement_observability",
                ["/measurement_modules"],
                "Bind exact module deployment and event schedules for: "
                + ", ".join(unresolved_modules)
                + ".",
                "Apply before using participant-event totals as design coordinates.",
            )
        )

    if payload["adaptive_reassignment"] is not True:
        upgrades["personalization_learning"].append(
            _upgrade(
                "add_response_contingent_reassignment",
                "personalization_learning",
                ["/adaptive_reassignment"],
                "Add pre-specified response-contingent reassignment stages.",
                "Apply when the trial objective includes learning which next action works for which observed state.",
            )
        )
    if payload["within_policy_randomized"] is not True:
        upgrades["personalization_learning"].append(
            _upgrade(
                "randomize_within_policy_adaptation",
                "personalization_learning",
                ["/within_policy_randomized"],
                "Randomize eligible adaptation choices and record decision-time probabilities.",
                "Apply when causal effects of personalization decisions are an objective.",
            )
        )

    population = payload["population"]
    if population["state"] != "exact":
        upgrades["population_precision"].append(
            _upgrade(
                "freeze_analysis_population",
                "population_precision",
                ["/population/value", "/population/state", "/population/semantics"],
                "Freeze the exact population denominator and whether it means planned, randomized, completed, or analyzable participants.",
                "Apply before computing precision, retention, or participant-event totals.",
            )
        )
    upgrades["population_precision"].append(
        _upgrade(
            "bind_estimand_precision_model",
            "population_precision",
            ["/population/value", "/policy_arms"],
            "Bind estimands, variance assumptions, effect scales, attrition, and multiplicity before changing population size.",
            "Do not infer adequacy from participant count alone.",
        )
    )

    if not payload["operator_families"]:
        upgrades["operator_identifiability"].append(
            _upgrade(
                "declare_operator_families",
                "operator_identifiability",
                ["/operator_families"],
                "Declare the intervention operator families and their components.",
                "Apply before asking which intervention family moved the measured state.",
            )
        )
    else:
        upgrades["operator_identifiability"].append(
            _upgrade(
                "bind_operator_policy_map",
                "operator_identifiability",
                ["/operator_families", "/policy_arms"],
                "Bind operator components to policies and explicit contrast matrices.",
                "Do not infer identifiable operator contrasts from arm count or family count.",
            )
        )
    return upgrades


def compile_design(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compile typed design coordinates, calculable event totals, gates, and upgrades."""
    validate_design_input(payload)
    materialized = dict(payload)

    population = materialized["population"]
    duration = materialized["duration"]
    arms = materialized["policy_arms"]
    coordinates: dict[str, Any] = {
        "population": _declared_coordinate(
            value=population["value"],
            state=population["state"],
            semantics=population["semantics"],
            unit="participants",
            pointers=["/population/value", "/population/state", "/population/semantics"],
        ),
        "duration": _declared_coordinate(
            value=duration["value"],
            state=duration["state"],
            semantics=duration["semantics"],
            unit="days",
            pointers=["/duration/value", "/duration/state", "/duration/semantics"],
        ),
        "policy_arms": _declared_coordinate(
            value=arms,
            state="exact" if arms is not None else "unknown",
            semantics="declared_policy_arm_count",
            unit="policies",
            pointers=["/policy_arms"],
        ),
        "operator_families": _declared_coordinate(
            value=list(materialized["operator_families"]),
            state="exact",
            semantics="declared_operator_family_identifiers",
            pointers=["/operator_families"],
        ),
        "causal_architecture": {},
        "measurement_modules": [],
    }
    for field in TRI_STATE_FIELDS:
        value = materialized[field]
        coordinates["causal_architecture"][field] = _declared_coordinate(
            value=value,
            state="exact" if value is not None else "unknown",
            semantics=field,
            pointers=[f"/{field}"],
        )

    for index, module in enumerate(materialized["measurement_modules"]):
        base = f"/measurement_modules/{index}"
        coordinates["measurement_modules"].append(
            {
                "module_id": module["module_id"],
                "label": module["label"],
                "evidence_state": module["evidence_state"],
                "events_per_participant": module["events_per_participant"],
                "evidence_class": "self_declared",
                "source_json_pointers": [
                    f"{base}/module_id",
                    f"{base}/label",
                    f"{base}/evidence_state",
                    f"{base}/events_per_participant",
                ],
            }
        )

    evidence_counts = Counter(
        module["evidence_state"] for module in materialized["measurement_modules"]
    )
    module_state_counts = {
        "exact": evidence_counts["exact"],
        "conditional": evidence_counts["conditional"],
        "unknown": evidence_counts["unknown"],
        "formula": "count(measurement_modules by evidence_state)",
        "source_json_pointers": ["/measurement_modules"],
        "evidence_class": "derived_from_self_declared_input",
    }

    participant_event_totals: list[dict[str, Any]] = []
    if population["state"] in {"exact", "conditional"}:
        for index, module in enumerate(materialized["measurement_modules"]):
            if (
                module["evidence_state"] not in {"exact", "conditional"}
                or module["events_per_participant"] is None
            ):
                continue
            value = population["value"] * module["events_per_participant"]
            state = (
                "exact"
                if population["state"] == "exact" and module["evidence_state"] == "exact"
                else "conditional"
            )
            participant_event_totals.append(
                {
                    "module_id": module["module_id"],
                    "value": value,
                    "state": state,
                    "unit": "participant_events",
                    "evidence_class": "derived_from_self_declared_input",
                    "formula": {
                        "expression": "population.value * measurement_modules[i].events_per_participant",
                        "operands": [
                            "/population/value",
                            f"/measurement_modules/{index}/events_per_participant",
                        ],
                        "state_operands": [
                            "/population/state",
                            f"/measurement_modules/{index}/evidence_state",
                        ],
                    },
                }
            )

    derived: dict[str, Any] = {
        "measurement_module_state_counts": module_state_counts,
        "participant_event_totals_by_module": participant_event_totals,
    }
    if len(participant_event_totals) == len(materialized["measurement_modules"]):
        derived["participant_module_observation_total"] = {
            "value": sum(item["value"] for item in participant_event_totals),
            "state": (
                "exact"
                if all(item["state"] == "exact" for item in participant_event_totals)
                else "conditional"
            ),
            "unit": "participant_module_observations",
            "semantics": ("workload_count_across_modules_not_unique_joint_events_or_information"),
            "evidence_class": "derived_from_self_declared_input",
            "formula": {
                "expression": "sum(participant_event_totals_by_module.value)",
                "operands": [
                    operand
                    for item in participant_event_totals
                    for operand in item["formula"]["operands"]
                ],
            },
        }

    return {
        "contract": OUTPUT_CONTRACT,
        "claim_state": "implementation_candidate_biological_promotion_gated",
        "promotion_allowed": False,
        "input_contract": INPUT_CONTRACT,
        "input_sha256": _canonical_sha256(materialized),
        "study": {
            "study_id": materialized["study_id"],
            "name": materialized["name"],
            "source_json_pointers": ["/study_id", "/name"],
        },
        "assessment_lane": {
            "value": materialized["assessment_lane"],
            "evidence_class": "self_declared",
            "source_json_pointers": ["/assessment_lane"],
        },
        "coordinates": coordinates,
        "derived_coordinates": derived,
        "open_gates": _open_gates(materialized),
        "structural_multiobjective_design_upgrades": _design_upgrades(materialized),
        "upgrade_ordering_semantics": "objective_group_then_identifier_not_preference",
        "emission_policy": {
            "composite_coordinate_emitted": False,
            "ordinal_position_emitted": False,
            "biological_information_inference_emitted": False,
            "missing_value_imputation_used": False,
        },
    }
