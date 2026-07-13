"""Executable semantic validation for AniBench v2 contract bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


VALIDATION_CONTRACT = "anibench.contract-validation.v2-candidate1"
RANDOMIZED_MECHANISMS = {
    "simple_randomized",
    "stratified_randomized",
    "cluster_randomized",
    "factorial_randomized",
    "smart_rerandomized",
    "micro_randomized",
    "crossover_randomized",
}


class ContractValidationError(ValueError):
    """Raised by strict validation when a contract bundle has semantic errors."""

    def __init__(self, report: Mapping[str, Any]):
        self.report = dict(report)
        errors = self.report.get("errors", [])
        message = (
            "\n".join(f"{row['path']}: {row['message']}" for row in errors)
            or "contract validation failed"
        )
        super().__init__(message)


@dataclass
class _Audit:
    errors: list[dict[str, str]] = field(default_factory=list)
    deferred: list[dict[str, str]] = field(default_factory=list)
    passed: list[dict[str, str]] = field(default_factory=list)
    ranks: list[dict[str, Any]] = field(default_factory=list)

    def error(self, check_id: str, path: str, message: str) -> None:
        self.errors.append({"check_id": check_id, "path": path, "message": message})

    def defer(
        self,
        check_id: str,
        path: str,
        coordinate_id: str,
        state: str,
        reason: str,
    ) -> None:
        self.deferred.append(
            {
                "check_id": check_id,
                "path": path,
                "coordinate_id": coordinate_id,
                "coordinate_state": state,
                "reason": reason,
            }
        )

    def pass_check(self, check_id: str, path: str, message: str) -> None:
        self.passed.append({"check_id": check_id, "path": path, "message": message})


def _schema_root() -> Path:
    source_root = Path(__file__).resolve().parents[2] / "schemas" / "v2"
    if source_root.is_dir():
        return source_root
    installed = Path(__file__).resolve().parent / "schemas" / "v2"
    if installed.is_dir():
        return installed
    raise ContractValidationError(
        {
            "errors": [
                {
                    "check_id": "schema_installation",
                    "path": "/",
                    "message": "v2 contract schemas are not installed",
                }
            ]
        }
    )


def _schemas() -> tuple[dict[str, dict[str, Any]], Registry]:
    root = _schema_root()
    names = (
        "uncertainty.schema.json",
        "event-manifest.schema.json",
        "intervention-design.schema.json",
    )
    schemas = {name: json.loads((root / name).read_text(encoding="utf-8")) for name in names}
    registry = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
    )
    return schemas, registry


def _schema_errors(payload: Mapping[str, Any], schema_name: str, audit: _Audit) -> None:
    schemas, registry = _schemas()
    validator = Draft202012Validator(
        schemas[schema_name], registry=registry, format_checker=FormatChecker()
    )
    errors = sorted(
        validator.iter_errors(dict(payload)),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    for error in errors:
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        audit.error(f"schema_{schema_name}", path, error.message)


def _ids(rows: Iterable[Mapping[str, Any]], id_field: str, path: str, audit: _Audit) -> set[str]:
    seen: set[str] = set()
    for index, row in enumerate(rows):
        identifier = row[id_field]
        if identifier in seen:
            audit.error(
                "unique_ids",
                f"{path}/{index}/{id_field}",
                f"duplicate {id_field} {identifier!r}",
            )
        seen.add(identifier)
    return seen


def _require_refs(
    values: Iterable[str], available: set[str], path: str, label: str, audit: _Audit
) -> None:
    for index, identifier in enumerate(values):
        if identifier not in available:
            audit.error(
                "reference_resolution",
                f"{path}/{index}",
                f"{label} {identifier!r} does not resolve",
            )


def _require_ref(
    identifier: str | None, available: set[str], path: str, label: str, audit: _Audit
) -> None:
    if identifier is not None and identifier not in available:
        audit.error("reference_resolution", path, f"{label} {identifier!r} does not resolve")


def _coordinate(
    coordinate_id: str,
    uncertainty: Mapping[str, Any],
    path: str,
    audit: _Audit,
    purpose: str,
) -> Mapping[str, Any] | None:
    coordinate = uncertainty["coordinates"].get(coordinate_id)
    if coordinate is None:
        audit.error(
            "uncertainty_coordinate_resolution",
            path,
            f"uncertainty coordinate {coordinate_id!r} does not resolve",
        )
        return None
    if coordinate["state"] != "exact":
        audit.defer(
            "nonexact_coordinate_requires_resolution",
            path,
            coordinate_id,
            coordinate["state"],
            f"{purpose} cannot be treated as exact until this coordinate is resolved",
        )
    return coordinate


def _coordinate_ref(
    reference: Mapping[str, Any],
    uncertainty: Mapping[str, Any],
    path: str,
    audit: _Audit,
    purpose: str,
) -> Mapping[str, Any] | None:
    return _coordinate(reference["uncertainty_coordinate_id"], uncertainty, path, audit, purpose)


def _exact_value(coordinate: Mapping[str, Any] | None) -> float | None:
    if coordinate is None or coordinate["state"] != "exact":
        return None
    return float(coordinate["value"])


def _receipt_refs(
    rows: Iterable[Mapping[str, Any]], receipts: set[str], base: str, audit: _Audit
) -> None:
    for index, row in enumerate(rows):
        if "source_receipt_ids" in row:
            _require_refs(
                row["source_receipt_ids"],
                receipts,
                f"{base}/{index}/source_receipt_ids",
                "source receipt",
                audit,
            )


def _uncertainty_semantics(uncertainty: Mapping[str, Any], audit: _Audit) -> None:
    receipts = _ids(
        uncertainty["source_receipts"],
        "source_receipt_id",
        "/uncertainty/source_receipts",
        audit,
    )
    for coordinate_id, coordinate in uncertainty["coordinates"].items():
        path = f"/uncertainty/coordinates/{coordinate_id}"
        _require_refs(
            coordinate["source_receipt_ids"],
            receipts,
            f"{path}/source_receipt_ids",
            "source receipt",
            audit,
        )
        state = coordinate["state"]
        if state == "interval":
            lower, upper = coordinate["lower"], coordinate["upper"]
            if lower > upper:
                audit.error("interval_order", path, "interval lower exceeds upper")
            nominal = coordinate.get("nominal")
            if nominal is not None and not lower <= nominal <= upper:
                audit.error(
                    "interval_nominal_support",
                    f"{path}/nominal",
                    "interval nominal lies outside [lower, upper]",
                )
        elif state == "unknown":
            lower = coordinate.get("admissible_lower")
            upper = coordinate.get("admissible_upper")
            if lower is not None and upper is not None and lower > upper:
                audit.error(
                    "unknown_admissible_order",
                    path,
                    "admissible_lower exceeds admissible_upper",
                )
        elif state == "distribution":
            distribution = coordinate["distribution"]
            if distribution["family"] == "triangular" and not (
                distribution["lower"] <= distribution["mode"] <= distribution["upper"]
            ):
                audit.error(
                    "triangular_parameter_order",
                    f"{path}/distribution",
                    "triangular parameters must satisfy lower <= mode <= upper",
                )
            if distribution["family"] == "empirical_discrete":
                values = distribution["values"]
                probabilities = distribution["probabilities"]
                if len(values) != len(probabilities):
                    audit.error(
                        "empirical_distribution_dimensions",
                        f"{path}/distribution",
                        "values and probabilities must have equal length",
                    )
                if not np.isclose(sum(probabilities), 1.0, atol=1e-12, rtol=1e-12):
                    audit.error(
                        "empirical_distribution_probability_sum",
                        f"{path}/distribution/probabilities",
                        "probabilities must sum to one",
                    )


def _event_semantics(
    event: Mapping[str, Any],
    uncertainty: Mapping[str, Any],
    intervention: Mapping[str, Any],
    audit: _Audit,
) -> None:
    participant_sets = _ids(
        event["participant_sets"],
        "participant_set_id",
        "/event_manifest/participant_sets",
        audit,
    )
    time_bases = _ids(event["time_bases"], "time_basis_id", "/event_manifest/time_bases", audit)
    modules = _ids(
        event["measurement_modules"],
        "measurement_module_id",
        "/event_manifest/measurement_modules",
        audit,
    )
    event_types = _ids(event["event_types"], "event_type_id", "/event_manifest/event_types", audit)
    _ids(
        event["joint_event_hyperedges"],
        "hyperedge_id",
        "/event_manifest/joint_event_hyperedges",
        audit,
    )
    covariance_groups = _ids(
        event["covariance_groups"],
        "covariance_group_id",
        "/event_manifest/covariance_groups",
        audit,
    )
    receipts = _ids(
        event["source_receipts"],
        "source_receipt_id",
        "/event_manifest/source_receipts",
        audit,
    )
    for collection in (
        "participant_sets",
        "time_bases",
        "measurement_modules",
        "event_types",
        "joint_event_hyperedges",
        "covariance_groups",
    ):
        _receipt_refs(event[collection], receipts, f"/event_manifest/{collection}", audit)

    id_is_null = event.get("intervention_design_id") is None
    hash_is_null = event.get("intervention_design_sha256") is None
    if id_is_null != hash_is_null:
        audit.error(
            "intervention_binding_null_pair",
            "/event_manifest/intervention_design_id",
            "intervention_design_id and intervention_design_sha256 must both be null or both non-null",
        )

    participant_by_id = {row["participant_set_id"]: row for row in event["participant_sets"]}
    for index, row in enumerate(event["participant_sets"]):
        _require_ref(
            row.get("parent_participant_set_id"),
            participant_sets,
            f"/event_manifest/participant_sets/{index}/parent_participant_set_id",
            "parent participant set",
            audit,
        )
        _coordinate_ref(
            row["count"],
            uncertainty,
            f"/event_manifest/participant_sets/{index}/count",
            audit,
            "participant marginal comparison",
        )
        for stratum_index, stratum in enumerate(row.get("strata", [])):
            _coordinate_ref(
                stratum["count"],
                uncertainty,
                f"/event_manifest/participant_sets/{index}/strata/{stratum_index}/count",
                audit,
                "stratum count",
            )

    for index, row in enumerate(event["time_bases"]):
        for offset_index, coordinate_id in enumerate(row.get("offset_coordinate_ids", [])):
            _coordinate(
                coordinate_id,
                uncertainty,
                f"/event_manifest/time_bases/{index}/offset_coordinate_ids/{offset_index}",
                audit,
                "time offset",
            )

    module_by_id = {row["measurement_module_id"]: row for row in event["measurement_modules"]}
    event_by_id = {row["event_type_id"]: row for row in event["event_types"]}
    covariance_by_id = {row["covariance_group_id"]: row for row in event["covariance_groups"]}
    module_coordinate_fields = (
        "target_count",
        "technical_quality",
        "completeness",
        "standardization",
        "measurement_error_scale",
    )
    for index, row in enumerate(event["measurement_modules"]):
        base = f"/event_manifest/measurement_modules/{index}"
        _require_ref(
            row["covariance_group_id"],
            covariance_groups,
            f"{base}/covariance_group_id",
            "covariance group",
            audit,
        )
        _require_refs(
            row["event_type_ids"],
            event_types,
            f"{base}/event_type_ids",
            "event type",
            audit,
        )
        for field_name in module_coordinate_fields:
            _coordinate_ref(
                row[field_name],
                uncertainty,
                f"{base}/{field_name}",
                audit,
                f"measurement module {field_name}",
            )
        covariance = covariance_by_id.get(row["covariance_group_id"])
        if (
            covariance is not None
            and row["measurement_module_id"] not in covariance["member_measurement_module_ids"]
        ):
            audit.error(
                "covariance_membership_reciprocity",
                f"{base}/covariance_group_id",
                "module points to a covariance group that does not list the module",
            )
        for event_type_id in row["event_type_ids"]:
            linked_event = event_by_id.get(event_type_id)
            if (
                linked_event is not None
                and row["measurement_module_id"] not in linked_event["measurement_module_ids"]
            ):
                audit.error(
                    "event_module_reciprocity",
                    f"{base}/event_type_ids",
                    f"event type {event_type_id!r} does not list this module",
                )

    stages = {row["assignment_stage_id"] for row in intervention["assignment_stages"]}
    event_coordinate_fields = (
        "events_per_participant",
        "observation_span",
        "identity_linkage",
        "time_linkage",
    )
    for index, row in enumerate(event["event_types"]):
        base = f"/event_manifest/event_types/{index}"
        _require_ref(
            row["participant_set_id"],
            participant_sets,
            f"{base}/participant_set_id",
            "participant set",
            audit,
        )
        _require_ref(
            row["time_basis_id"],
            time_bases,
            f"{base}/time_basis_id",
            "time basis",
            audit,
        )
        _require_refs(
            row["measurement_module_ids"],
            modules,
            f"{base}/measurement_module_ids",
            "measurement module",
            audit,
        )
        _require_ref(
            row.get("assignment_stage_id"),
            stages,
            f"{base}/assignment_stage_id",
            "assignment stage",
            audit,
        )
        for field_name in event_coordinate_fields:
            _coordinate_ref(
                row[field_name],
                uncertainty,
                f"{base}/{field_name}",
                audit,
                f"event type {field_name}",
            )
        for module_id in row["measurement_module_ids"]:
            linked_module = module_by_id.get(module_id)
            if (
                linked_module is not None
                and row["event_type_id"] not in linked_module["event_type_ids"]
            ):
                audit.error(
                    "event_module_reciprocity",
                    f"{base}/measurement_module_ids",
                    f"measurement module {module_id!r} does not list this event type",
                )

    for index, row in enumerate(event["covariance_groups"]):
        _require_refs(
            row["member_measurement_module_ids"],
            modules,
            f"/event_manifest/covariance_groups/{index}/member_measurement_module_ids",
            "measurement module",
            audit,
        )

    for index, edge in enumerate(event["joint_event_hyperedges"]):
        base = f"/event_manifest/joint_event_hyperedges/{index}"
        _require_refs(
            edge["participant_set_ids"],
            participant_sets,
            f"{base}/participant_set_ids",
            "participant set",
            audit,
        )
        _require_refs(
            edge["event_type_ids"],
            event_types,
            f"{base}/event_type_ids",
            "event type",
            audit,
        )
        _require_refs(
            edge["measurement_module_ids"],
            modules,
            f"{base}/measurement_module_ids",
            "measurement module",
            audit,
        )
        for event_type_id in edge["event_type_ids"]:
            linked_event = event_by_id.get(event_type_id)
            if linked_event is None:
                continue
            if linked_event["participant_set_id"] not in edge["participant_set_ids"]:
                audit.error(
                    "hyperedge_event_participant_support",
                    f"{base}/participant_set_ids",
                    f"event type {event_type_id!r} uses a participant set absent from the hyperedge",
                )
            unsupported = set(edge["measurement_module_ids"]) - set(
                linked_event["measurement_module_ids"]
            )
            if unsupported:
                audit.error(
                    "hyperedge_event_module_support",
                    f"{base}/measurement_module_ids",
                    "hyperedge modules are not all supported by event type "
                    f"{event_type_id!r}: {sorted(unsupported)!r}",
                )

        ancestries = [
            module_by_id[module_id]["feature_ancestry_id"]
            for module_id in edge["measurement_module_ids"]
            if module_id in module_by_id
        ]
        duplicates = sorted(
            ancestry for ancestry in set(ancestries) if ancestries.count(ancestry) > 1
        )
        if duplicates:
            audit.error(
                "joint_measurement_lineage_uniqueness",
                f"{base}/measurement_module_ids",
                f"one physical feature ancestry is duplicated inside the joint event: {duplicates!r}",
            )

        joint_participant = _coordinate_ref(
            edge["joint_participant_count"],
            uncertainty,
            f"{base}/joint_participant_count",
            audit,
            "joint participant marginal comparison",
        )
        joint_participant_value = _exact_value(joint_participant)
        for participant_set_id in edge["participant_set_ids"]:
            marginal_row = participant_by_id.get(participant_set_id)
            if marginal_row is None:
                continue
            marginal = _coordinate_ref(
                marginal_row["count"],
                uncertainty,
                f"{base}/participant_set_ids/{participant_set_id}",
                audit,
                "participant marginal comparison",
            )
            marginal_value = _exact_value(marginal)
            if (
                joint_participant_value is not None
                and marginal_value is not None
                and joint_participant_value > marginal_value
            ):
                audit.error(
                    "joint_participant_marginal_bound",
                    f"{base}/joint_participant_count",
                    f"joint participant count {joint_participant_value:g} exceeds marginal {marginal_value:g}",
                )

        joint_events = _coordinate_ref(
            edge["joint_event_count"],
            uncertainty,
            f"{base}/joint_event_count",
            audit,
            "joint event marginal comparison",
        )
        joint_event_value = _exact_value(joint_events)
        for event_type_id in edge["event_type_ids"]:
            event_row = event_by_id.get(event_type_id)
            if event_row is None:
                continue
            participant_row = participant_by_id.get(event_row["participant_set_id"])
            if participant_row is None:
                continue
            participant_coordinate = _coordinate_ref(
                participant_row["count"],
                uncertainty,
                f"{base}/event_type_ids/{event_type_id}/participant_count",
                audit,
                "event marginal participant count",
            )
            event_coordinate = _coordinate_ref(
                event_row["events_per_participant"],
                uncertainty,
                f"{base}/event_type_ids/{event_type_id}/events_per_participant",
                audit,
                "event marginal event count",
            )
            participant_value = _exact_value(participant_coordinate)
            event_value = _exact_value(event_coordinate)
            if (
                joint_event_value is not None
                and participant_value is not None
                and event_value is not None
                and joint_event_value > participant_value * event_value
            ):
                audit.error(
                    "joint_event_marginal_bound",
                    f"{base}/joint_event_count",
                    f"joint event count {joint_event_value:g} exceeds event marginal "
                    f"{participant_value * event_value:g}",
                )
        for field_name in (
            "identity_linkage",
            "temporal_compatibility",
            "specimen_lineage_linkage",
            "compatible_time_window",
        ):
            if field_name in edge:
                _coordinate_ref(
                    edge[field_name],
                    uncertainty,
                    f"{base}/{field_name}",
                    audit,
                    f"joint event {field_name}",
                )


def _matrix_rank(values: list[list[float]]) -> tuple[int, float]:
    matrix = np.asarray(values, dtype=float)
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    largest = float(singular_values[0]) if singular_values.size else 0.0
    tolerance = max(matrix.shape) * np.finfo(float).eps * largest
    return int(np.linalg.matrix_rank(matrix, tol=tolerance)), tolerance


def _intervention_semantics(
    intervention: Mapping[str, Any],
    event: Mapping[str, Any],
    uncertainty: Mapping[str, Any],
    audit: _Audit,
) -> None:
    components = _ids(
        intervention["operator_components"],
        "operator_component_id",
        "/intervention_design/operator_components",
        audit,
    )
    policies = _ids(
        intervention["policies"],
        "policy_id",
        "/intervention_design/policies",
        audit,
    )
    stages = _ids(
        intervention["assignment_stages"],
        "assignment_stage_id",
        "/intervention_design/assignment_stages",
        audit,
    )
    estimands = _ids(
        intervention["estimands"],
        "estimand_id",
        "/intervention_design/estimands",
        audit,
    )
    outcomes = _ids(
        intervention["outcome_support"],
        "outcome_support_id",
        "/intervention_design/outcome_support",
        audit,
    )
    receipts = _ids(
        intervention["source_receipts"],
        "source_receipt_id",
        "/intervention_design/source_receipts",
        audit,
    )
    matrix_rows = [
        matrix
        for family in ("policy", "component", "sequential")
        for matrix in intervention["contrast_matrices"][family]
    ]
    _ids(
        matrix_rows,
        "contrast_matrix_id",
        "/intervention_design/contrast_matrices",
        audit,
    )
    for collection in (
        "operator_components",
        "policies",
        "assignment_stages",
        "estimands",
        "outcome_support",
    ):
        _receipt_refs(
            intervention[collection],
            receipts,
            f"/intervention_design/{collection}",
            audit,
        )
    _receipt_refs(matrix_rows, receipts, "/intervention_design/contrast_matrices", audit)

    event_types = {row["event_type_id"] for row in event["event_types"]}
    participant_sets = {row["participant_set_id"] for row in event["participant_sets"]}
    measurement_modules = {row["measurement_module_id"] for row in event["measurement_modules"]}

    for index, component in enumerate(intervention["operator_components"]):
        base = f"/intervention_design/operator_components/{index}"
        _coordinate_ref(
            component["dose_or_intensity"],
            uncertainty,
            f"{base}/dose_or_intensity",
            audit,
            "operator dose or intensity",
        )
        _coordinate_ref(
            component["washout_duration"],
            uncertainty,
            f"{base}/washout_duration",
            audit,
            "operator washout duration",
        )

    for index, policy in enumerate(intervention["policies"]):
        _require_refs(
            policy["operator_component_ids"],
            components,
            f"/intervention_design/policies/{index}/operator_component_ids",
            "operator component",
            audit,
        )

    alternatives = policies | components
    for index, stage in enumerate(intervention["assignment_stages"]):
        base = f"/intervention_design/assignment_stages/{index}"
        _require_ref(
            stage["decision_event_type_id"],
            event_types,
            f"{base}/decision_event_type_id",
            "decision event type",
            audit,
        )
        _require_ref(
            stage["eligibility_participant_set_id"],
            participant_sets,
            f"{base}/eligibility_participant_set_id",
            "eligibility participant set",
            audit,
        )
        _require_refs(
            stage["alternative_ids"],
            alternatives,
            f"{base}/alternative_ids",
            "assignment alternative",
            audit,
        )
        probabilities = []
        probability_exact = True
        for probability_index, coordinate_id in enumerate(
            stage["assignment_probability_coordinate_ids"]
        ):
            coordinate = _coordinate(
                coordinate_id,
                uncertainty,
                f"{base}/assignment_probability_coordinate_ids/{probability_index}",
                audit,
                "assignment probability",
            )
            value = _exact_value(coordinate)
            if value is None:
                probability_exact = False
            else:
                probabilities.append(value)
                if not 0 <= value <= 1:
                    audit.error(
                        "assignment_probability_range",
                        f"{base}/assignment_probability_coordinate_ids/{probability_index}",
                        f"exact assignment probability {value:g} lies outside [0, 1]",
                    )
        if (
            stage["assignment_mechanism"] in RANDOMIZED_MECHANISMS
            and not stage["assignment_probability_coordinate_ids"]
        ):
            audit.error(
                "randomized_assignment_probability_required",
                f"{base}/assignment_probability_coordinate_ids",
                "randomized assignment requires explicit probability coordinates",
            )
        if (
            probabilities
            and probability_exact
            and not np.isclose(sum(probabilities), 1.0, atol=1e-12, rtol=1e-12)
        ):
            audit.error(
                "assignment_probability_sum",
                f"{base}/assignment_probability_coordinate_ids",
                f"exact assignment probabilities sum to {sum(probabilities):g}, not one",
            )
        _coordinate_ref(
            stage["sequential_positivity"],
            uncertainty,
            f"{base}/sequential_positivity",
            audit,
            "sequential positivity",
        )
        if "carryover_control" in stage:
            _coordinate_ref(
                stage["carryover_control"],
                uncertainty,
                f"{base}/carryover_control",
                audit,
                "carryover control",
            )

    for index, estimand in enumerate(intervention["estimands"]):
        base = f"/intervention_design/estimands/{index}"
        _require_ref(
            estimand["population_participant_set_id"],
            participant_sets,
            f"{base}/population_participant_set_id",
            "participant set",
            audit,
        )
        _require_refs(
            estimand["treatment_condition_ids"],
            alternatives,
            f"{base}/treatment_condition_ids",
            "treatment condition",
            audit,
        )
        _require_ref(
            estimand["outcome_support_id"],
            outcomes,
            f"{base}/outcome_support_id",
            "outcome support",
            audit,
        )

    for index, outcome in enumerate(intervention["outcome_support"]):
        base = f"/intervention_design/outcome_support/{index}"
        _require_refs(
            outcome["event_type_ids"],
            event_types,
            f"{base}/event_type_ids",
            "event type",
            audit,
        )
        _require_refs(
            outcome["measurement_module_ids"],
            measurement_modules,
            f"{base}/measurement_module_ids",
            "measurement module",
            audit,
        )
        _require_ref(
            outcome["participant_set_id"],
            participant_sets,
            f"{base}/participant_set_id",
            "participant set",
            audit,
        )
        _coordinate(
            outcome["missingness_coordinate_id"],
            uncertainty,
            f"{base}/missingness_coordinate_id",
            audit,
            "outcome missingness",
        )

    for family in ("policy", "component", "sequential"):
        for index, matrix in enumerate(intervention["contrast_matrices"][family]):
            base = f"/intervention_design/contrast_matrices/{family}/{index}"
            values = matrix["values"]
            if len(values) != len(matrix["row_ids"]):
                audit.error(
                    "contrast_matrix_row_dimension",
                    f"{base}/values",
                    f"values has {len(values)} rows but row_ids has {len(matrix['row_ids'])}",
                )
            bad_rows = [
                row_index
                for row_index, row in enumerate(values)
                if len(row) != len(matrix["column_ids"])
            ]
            if bad_rows:
                audit.error(
                    "contrast_matrix_column_dimension",
                    f"{base}/values",
                    f"matrix rows do not match column_ids at row indices {bad_rows!r}",
                )
            _require_refs(
                matrix["estimand_ids"],
                estimands,
                f"{base}/estimand_ids",
                "estimand",
                audit,
            )
            if family == "policy":
                declared_columns = matrix["policy_ids"]
                _require_refs(
                    declared_columns,
                    policies,
                    f"{base}/policy_ids",
                    "policy",
                    audit,
                )
            elif family == "component":
                declared_columns = matrix["operator_component_ids"]
                _require_refs(
                    declared_columns,
                    components,
                    f"{base}/operator_component_ids",
                    "operator component",
                    audit,
                )
                _require_refs(
                    matrix["assignment_stage_ids"],
                    stages,
                    f"{base}/assignment_stage_ids",
                    "assignment stage",
                    audit,
                )
            else:
                declared_columns = matrix["path_feature_ids"]
                _require_refs(
                    matrix["assignment_stage_ids"],
                    stages,
                    f"{base}/assignment_stage_ids",
                    "assignment stage",
                    audit,
                )
            if matrix["column_ids"] != declared_columns:
                audit.error(
                    "contrast_matrix_column_binding",
                    f"{base}/column_ids",
                    "column_ids must exactly equal the matrix's declared policy, component, or path IDs",
                )
            if not bad_rows and len(values) == len(matrix["row_ids"]):
                rank, tolerance = _matrix_rank(values)
                audit.ranks.append(
                    {
                        "contrast_matrix_id": matrix["contrast_matrix_id"],
                        "matrix_family": family,
                        "rank": rank,
                        "row_count": len(matrix["row_ids"]),
                        "column_count": len(matrix["column_ids"]),
                        "tolerance": tolerance,
                        "rank_source": "server_computed_from_matrix_values",
                        "source_json_pointer": base,
                    }
                )


def _bundle_bindings(
    event: Mapping[str, Any],
    intervention: Mapping[str, Any],
    uncertainty: Mapping[str, Any],
    audit: _Audit,
) -> None:
    if event["uncertainty_model_id"] != uncertainty["uncertainty_model_id"]:
        audit.error(
            "uncertainty_model_binding",
            "/event_manifest/uncertainty_model_id",
            "event manifest uncertainty_model_id does not match supplied uncertainty model",
        )
    if intervention["uncertainty_model_id"] != uncertainty["uncertainty_model_id"]:
        audit.error(
            "uncertainty_model_binding",
            "/intervention_design/uncertainty_model_id",
            "intervention design uncertainty_model_id does not match supplied uncertainty model",
        )
    if intervention["event_manifest_id"] != event["event_manifest_id"]:
        audit.error(
            "event_manifest_binding",
            "/intervention_design/event_manifest_id",
            "intervention design event_manifest_id does not match supplied event manifest",
        )
    if event.get("intervention_design_id") not in {
        None,
        intervention["intervention_design_id"],
    }:
        audit.error(
            "intervention_design_binding",
            "/event_manifest/intervention_design_id",
            "event manifest intervention_design_id does not match supplied intervention design",
        )
    if event["study_id"] != intervention["study_id"]:
        audit.error(
            "study_binding",
            "/intervention_design/study_id",
            "event manifest and intervention design study_id values differ",
        )


def validate_contract_bundle(
    event_manifest: Mapping[str, Any],
    intervention_design: Mapping[str, Any],
    uncertainty_model: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an executable semantic-validation report for a bound v2 bundle."""
    audit = _Audit()
    _schema_errors(uncertainty_model, "uncertainty.schema.json", audit)
    _schema_errors(event_manifest, "event-manifest.schema.json", audit)
    _schema_errors(intervention_design, "intervention-design.schema.json", audit)
    if not audit.errors:
        _uncertainty_semantics(uncertainty_model, audit)
        _bundle_bindings(event_manifest, intervention_design, uncertainty_model, audit)
        _event_semantics(event_manifest, uncertainty_model, intervention_design, audit)
        _intervention_semantics(intervention_design, event_manifest, uncertainty_model, audit)

    semantic_valid = not audit.errors
    exact_semantic_complete = semantic_valid and not audit.deferred
    state = (
        "invalid"
        if not semantic_valid
        else "valid_exact"
        if exact_semantic_complete
        else "valid_with_deferred_checks"
    )
    return {
        "contract": VALIDATION_CONTRACT,
        "claim_state": "candidate_only_code_red_hold",
        "promotion_allowed": False,
        "validation_state": state,
        "semantic_valid": semantic_valid,
        "exact_semantic_complete": exact_semantic_complete,
        "errors": audit.errors,
        "deferred_semantic_checks": audit.deferred,
        "computed_contrast_ranks": audit.ranks,
        "validation_policy": {
            "schema_only_acceptance_permitted": False,
            "nonexact_coordinates_treated_as_exact": False,
            "arm_count_used_as_contrast_rank": False,
        },
    }


def validate_contract_bundle_strict(
    event_manifest: Mapping[str, Any],
    intervention_design: Mapping[str, Any],
    uncertainty_model: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the report or raise when any schema or semantic error exists."""
    report = validate_contract_bundle(event_manifest, intervention_design, uncertainty_model)
    if not report["semantic_valid"]:
        raise ContractValidationError(report)
    return report


def load_contract_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(
            {
                "errors": [
                    {
                        "check_id": "contract_load",
                        "path": str(path),
                        "message": str(exc),
                    }
                ]
            }
        ) from exc
    if not isinstance(payload, dict):
        raise ContractValidationError(
            {
                "errors": [
                    {
                        "check_id": "contract_load",
                        "path": str(path),
                        "message": "contract file must contain one JSON object",
                    }
                ]
            }
        )
    return payload
