"""Protocol-native prospective optimizer for AniBench v2.

Every candidate is produced by patching declarative protocol geometry and then
calling :func:`compile_protocol_capacity`.  The optimizer has no route for
patching family outputs, no weighted aggregate, and no rank emission.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .protocol_capacity_v2 import ProtocolCapacityError, compile_protocol_capacity


OPTIMIZER_PROTOCOL_VERSION = "anibench.optimizer-protocol.v2-candidate4"
MAX_CANDIDATES = 10_000
_RESOURCE_DECIMAL_PRECISION = 1024
_GEOMETRY_ROOTS = ("/measurement_geometry", "/causal_geometry")


class ProtocolOptimizerError(ValueError):
    """Raised when an optimization request is invalid or gameable."""


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2] / "schemas" / "v2"
    if not root.is_dir():
        root = Path(__file__).resolve().parent / "schemas" / "v2"
    return json.loads((root / "optimizer-protocol-input.schema.json").read_text(encoding="utf-8"))


def _validate(request: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(dict(request)),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        detail = "; ".join(
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise ProtocolOptimizerError(detail)


def _decode_pointer(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ProtocolOptimizerError(f"JSON pointer must begin with '/': {path!r}")
    decoded: list[str] = []
    for raw_part in path[1:].split("/"):
        index = 0
        value: list[str] = []
        while index < len(raw_part):
            character = raw_part[index]
            if character != "~":
                value.append(character)
                index += 1
                continue
            if index + 1 >= len(raw_part) or raw_part[index + 1] not in {"0", "1"}:
                raise ProtocolOptimizerError(
                    f"JSON pointer contains a noncanonical escape in {path!r}"
                )
            value.append("~" if raw_part[index + 1] == "0" else "/")
            index += 2
        decoded.append("".join(value))
    return decoded


def _array_index(token: str, *, allow_append: bool = False) -> int | None:
    if token == "-" and allow_append:
        return None
    if re.fullmatch(r"0|[1-9][0-9]*", token) is None:
        raise ProtocolOptimizerError(f"noncanonical JSON pointer array index {token!r}")
    return int(token)


def _geometry_path(path: str) -> bool:
    return any(path == root or path.startswith(root + "/") for root in _GEOMETRY_ROOTS)


def _resolve_parent(document: Any, path: str) -> tuple[Any, str]:
    parts = _decode_pointer(path)
    if not parts:
        raise ProtocolOptimizerError("root replacement is prohibited")
    cursor = document
    for part in parts[:-1]:
        if isinstance(cursor, list):
            if part == "-":
                raise ProtocolOptimizerError("'-' is valid only as the final add segment")
            try:
                index = _array_index(part)
                assert index is not None
                cursor = cursor[index]
            except IndexError as exc:
                raise ProtocolOptimizerError(f"invalid list segment {part!r} in {path!r}") from exc
        elif isinstance(cursor, Mapping):
            if part not in cursor:
                raise ProtocolOptimizerError(f"missing object segment {part!r} in {path!r}")
            cursor = cursor[part]
        else:
            raise ProtocolOptimizerError(f"cannot traverse scalar in {path!r}")
    return cursor, parts[-1]


def _apply_operation(protocol: dict[str, Any], operation: Mapping[str, Any]) -> None:
    path = str(operation["path"])
    if not _geometry_path(path):
        raise ProtocolOptimizerError(
            f"mutation path {path!r} is outside measurement/causal protocol geometry"
        )
    parent, key = _resolve_parent(protocol, path)
    op = operation["op"]
    if isinstance(parent, list):
        if op == "add":
            if key == "-":
                parent.append(copy.deepcopy(operation["value"]))
                return
            index = _array_index(key, allow_append=True)
            assert index is not None
            if index < 0 or index > len(parent):
                raise ProtocolOptimizerError(f"list add index {index} is outside support")
            parent.insert(index, copy.deepcopy(operation["value"]))
            return
        try:
            index = _array_index(key)
            assert index is not None
            parent[index]
        except IndexError as exc:
            raise ProtocolOptimizerError(f"invalid list index {key!r}") from exc
        if op == "replace":
            parent[index] = copy.deepcopy(operation["value"])
        else:
            del parent[index]
        return
    if not isinstance(parent, dict):
        raise ProtocolOptimizerError(f"mutation parent at {path!r} is not mutable")
    if op == "add":
        if key in parent:
            raise ProtocolOptimizerError(f"add target already exists at {path!r}")
        parent[key] = copy.deepcopy(operation["value"])
    elif op == "replace":
        if key not in parent:
            raise ProtocolOptimizerError(f"replace target does not exist at {path!r}")
        parent[key] = copy.deepcopy(operation["value"])
    else:
        if key not in parent:
            raise ProtocolOptimizerError(f"remove target does not exist at {path!r}")
        del parent[key]


def _paths_overlap(left: str, right: str) -> bool:
    left_parts = _decode_pointer(left)
    right_parts = _decode_pointer(right)
    limit = min(len(left_parts), len(right_parts))
    return left_parts[:limit] == right_parts[:limit]


def _list_sibling_indices_can_shift(
    document: Mapping[str, Any],
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    """Reject order-sensitive edits to sibling indices of one existing list."""

    left_parts = _decode_pointer(str(left["path"]))
    right_parts = _decode_pointer(str(right["path"]))
    if left_parts[:-1] != right_parts[:-1]:
        return False
    try:
        parent, _ = _resolve_parent(document, str(left["path"]))
    except ProtocolOptimizerError:
        return False
    return isinstance(parent, list) and (
        left["op"] in {"add", "remove"} or right["op"] in {"add", "remove"}
    )


def _validate_operation_path(document: Mapping[str, Any], operation: Mapping[str, Any]) -> None:
    """Resolve once against the base so overlap checks use canonical list tokens."""

    path = str(operation["path"])
    parent, token = _resolve_parent(document, path)
    if not isinstance(parent, list):
        return
    if token == "-":
        if operation["op"] != "add":
            raise ProtocolOptimizerError("'-' is valid only as the final add segment")
        return
    index = _array_index(token)
    assert index is not None
    if operation["op"] == "add":
        if index > len(parent):
            raise ProtocolOptimizerError(f"list add index {index} is outside support")
    elif index >= len(parent):
        raise ProtocolOptimizerError(f"invalid list index {token!r}")


def _apply_mutations(
    base_protocol: Mapping[str, Any], mutations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    selected = sorted(mutations, key=lambda row: row["mutation_id"])
    operations: list[tuple[str, Mapping[str, Any]]] = []
    for mutation in selected:
        for operation in mutation["protocol_operations"]:
            _validate_operation_path(base_protocol, operation)
            for other_id, other in operations:
                if _paths_overlap(str(operation["path"]), str(other["path"])):
                    raise ProtocolOptimizerError(
                        "selected mutations have overlapping protocol operations: "
                        f"{other_id!r} and {mutation['mutation_id']!r}"
                    )
                if _list_sibling_indices_can_shift(base_protocol, operation, other):
                    raise ProtocolOptimizerError(
                        "selected mutations contain order-sensitive sibling list edits: "
                        f"{other_id!r} and {mutation['mutation_id']!r}"
                    )
            operations.append((mutation["mutation_id"], operation))
    protocol = copy.deepcopy(dict(base_protocol))
    for _, operation in operations:
        _apply_operation(protocol, operation)
    if protocol == dict(base_protocol) and selected:
        raise ProtocolOptimizerError("selected mutation set does not alter protocol geometry")
    return protocol


def _combination_count(mutation_count: int, maximum_size: int) -> int:
    return sum(math.comb(mutation_count, size) for size in range(maximum_size + 1))


def _objective_value(capacity: Mapping[str, Any], objective: Mapping[str, Any]) -> dict[str, Any]:
    path = objective["family_path"]
    envelope = capacity["family_envelopes"].get(path)
    if envelope is None:
        raise ProtocolOptimizerError(
            f"objective family_path {path!r} is not emitted by compile_protocol_capacity"
        )
    raw_value = envelope[objective["envelope_bound"]]
    # A compiler envelope may expose the extrema of the scenarios that did
    # resolve while still marking the family unresolved overall.  Those
    # partial extrema are diagnostics, not orderable objective values: using
    # one would silently drop the unresolved scenarios from Pareto selection.
    if envelope.get("resolution_state") == "unresolved" or raw_value is None:
        return {
            "value_state": "unknown",
            "value": None,
            "reason": (
                f"compiler envelope {path!r} is unresolved for one or more scenarios; "
                "the optimizer cannot substitute or order an unknown coordinate"
            ),
            "compiler_resolution_state": envelope.get("resolution_state", "unresolved"),
            "resolved_scenario_count": int(envelope.get("resolved_scenario_count", 0)),
            "total_scenario_count": int(envelope.get("total_scenario_count", 0)),
        }
    value = float(raw_value)
    if not math.isfinite(value):
        raise ProtocolOptimizerError(f"objective family_path {path!r} is non-finite")
    return {"value_state": "resolved", "value": value}


def _resource_decimal(value: Any, label: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ProtocolOptimizerError(f"{label} must be numeric") from exc
    if not amount.is_finite() or amount < 0:
        raise ProtocolOptimizerError(f"{label} must be finite and nonnegative")
    try:
        emitted = float(amount)
    except (OverflowError, ValueError) as exc:
        raise ProtocolOptimizerError(f"{label} exceeds the supported numeric range") from exc
    if not math.isfinite(emitted):
        raise ProtocolOptimizerError(f"{label} exceeds the supported numeric range")
    return amount


def _resource_totals(
    constraints: Sequence[Mapping[str, Any]], mutations: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], bool]:
    constraint_by_id = {row["resource_id"]: row for row in constraints}
    totals: dict[str, Decimal] = {}
    maxima: dict[str, Decimal] = {}
    for row in constraints:
        base_amount = _resource_decimal(row["base_amount"], "resource base amounts")
        maximum_amount = _resource_decimal(row["maximum_amount"], "resource maxima")
        try:
            date.fromisoformat(row["as_of"])
        except ValueError as exc:
            raise ProtocolOptimizerError("resource as_of must be an ISO calendar date") from exc
        totals[row["resource_id"]] = base_amount
        maxima[row["resource_id"]] = maximum_amount
    for mutation in mutations:
        seen: set[str] = set()
        for delta in mutation["resource_deltas"]:
            resource_id = delta["resource_id"]
            if resource_id in seen:
                raise ProtocolOptimizerError(
                    f"mutation {mutation['mutation_id']!r} repeats resource {resource_id!r}"
                )
            seen.add(resource_id)
            constraint = constraint_by_id.get(resource_id)
            if constraint is None:
                raise ProtocolOptimizerError(f"undeclared resource {resource_id!r}")
            if delta["unit"] != constraint["unit"]:
                raise ProtocolOptimizerError(
                    f"resource {resource_id!r} unit does not match its constraint"
                )
            amount = _resource_decimal(delta["amount"], "resource deltas")
            try:
                date.fromisoformat(delta["as_of"])
            except ValueError as exc:
                raise ProtocolOptimizerError(
                    "resource-delta as_of must be an ISO calendar date"
                ) from exc
            current = totals[resource_id]
            with localcontext() as context:
                context.prec = _RESOURCE_DECIMAL_PRECISION
                updated = current + amount
            current_emitted = float(current)
            updated_emitted = float(updated)
            if amount > 0 and updated_emitted == current_emitted:
                minimum_increment = math.nextafter(current_emitted, math.inf) - current_emitted
                raise ProtocolOptimizerError(
                    f"mutation {mutation['mutation_id']!r} resource delta for "
                    f"{resource_id!r} is below representable resolution at the current "
                    f"total {current_emitted!r}; minimum representable increment is "
                    f"{minimum_increment!r} {constraint['unit']}"
                )
            if not math.isfinite(updated_emitted):
                raise ProtocolOptimizerError(
                    f"mutation {mutation['mutation_id']!r} overflows resource {resource_id!r}"
                )
            totals[resource_id] = updated
    rows = []
    feasible = True
    for constraint in sorted(constraints, key=lambda row: row["resource_id"]):
        amount_decimal = totals[constraint["resource_id"]]
        maximum_decimal = maxima[constraint["resource_id"]]
        amount = float(amount_decimal)
        maximum = float(maximum_decimal)
        within = amount_decimal <= maximum_decimal
        feasible = feasible and within
        rows.append(
            {
                "resource_id": constraint["resource_id"],
                "unit": constraint["unit"],
                "total_amount": amount,
                "total_amount_decimal": str(amount_decimal),
                "maximum_amount": maximum,
                "maximum_amount_decimal": str(maximum_decimal),
                "within_constraint": within,
                "constraint_as_of": constraint["as_of"],
                "constraint_source_object_sha256": constraint["source_object_sha256"],
                "constraint_source_locator": constraint["source_locator"],
            }
        )
    return rows, feasible


def _incompatible(mutations: Sequence[Mapping[str, Any]]) -> bool:
    selected = {row["mutation_id"] for row in mutations}
    return any(
        incompatible_id in selected
        for mutation in mutations
        for incompatible_id in mutation.get("incompatible_mutation_ids", [])
    )


def _candidate(
    request_sha256: str,
    base_protocol: Mapping[str, Any],
    objectives: Sequence[Mapping[str, Any]],
    constraints: Sequence[Mapping[str, Any]],
    mutations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    protocol = _apply_mutations(base_protocol, mutations)
    try:
        capacity = compile_protocol_capacity(protocol)
    except ProtocolCapacityError as exc:
        raise ProtocolOptimizerError(f"candidate protocol does not compile: {exc}") from exc
    objective_values = [
        {
            "objective_id": objective["objective_id"],
            "family_path": objective["family_path"],
            "envelope_bound": objective["envelope_bound"],
            "direction": objective["direction"],
            **_objective_value(capacity, objective),
        }
        for objective in objectives
    ]
    resource_totals, feasible = _resource_totals(constraints, mutations)
    mutation_ids = sorted(row["mutation_id"] for row in mutations)
    capacity_sha256 = _canonical_sha256(capacity)
    replay_material = {
        "optimizer_request_sha256": request_sha256,
        "mutation_ids": mutation_ids,
        "candidate_protocol_sha256": capacity["protocol_sha256"],
        "capacity_result_sha256": capacity_sha256,
        "resource_totals": resource_totals,
    }
    return {
        "candidate_id": "base" if not mutation_ids else "+".join(mutation_ids),
        "mutation_ids": mutation_ids,
        "candidate_protocol_sha256": capacity["protocol_sha256"],
        "capacity_result_sha256": capacity_sha256,
        "replay_sha256": _canonical_sha256(replay_material),
        "comparison_eligible": capacity["comparison_eligible"],
        "ontology_binding_state": capacity["ontology_binding_state"],
        "constraint_eligible": feasible,
        "objective_values": objective_values,
        "resource_totals": resource_totals,
        "scenario_count": capacity["scenario_count"],
        "family_envelopes": capacity["family_envelopes"],
        "capacity_result": capacity,
    }


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_values = {row["objective_id"]: row for row in left["objective_values"]}
    right_values = {row["objective_id"]: row for row in right["objective_values"]}
    no_worse = True
    strictly_better = False
    for objective_id, left_row in left_values.items():
        right_row = right_values[objective_id]
        if left_row["value_state"] != "resolved" or right_row["value_state"] != "resolved":
            return False
        if left_row["direction"] == "maximize":
            no_worse = no_worse and left_row["value"] >= right_row["value"]
            strictly_better = strictly_better or left_row["value"] > right_row["value"]
        else:
            no_worse = no_worse and left_row["value"] <= right_row["value"]
            strictly_better = strictly_better or left_row["value"] < right_row["value"]
    left_resources = {
        row["resource_id"]: Decimal(row["total_amount_decimal"]) for row in left["resource_totals"]
    }
    right_resources = {
        row["resource_id"]: Decimal(row["total_amount_decimal"]) for row in right["resource_totals"]
    }
    if set(left_resources) != set(right_resources):
        raise ProtocolOptimizerError("candidate resource ledgers are not comparable")
    for resource_id, left_amount in left_resources.items():
        right_amount = right_resources[resource_id]
        no_worse = no_worse and left_amount <= right_amount
        strictly_better = strictly_better or left_amount < right_amount
    return no_worse and strictly_better


def optimize_protocol(request: Mapping[str, Any]) -> dict[str, Any]:
    """Enumerate and Pareto-filter protocol mutations through one compiler path."""

    _validate(request)
    request_copy = copy.deepcopy(dict(request))
    request_sha256 = _canonical_sha256(request_copy)
    mutations = sorted(request_copy["mutations"], key=lambda row: row["mutation_id"])
    mutation_ids = [row["mutation_id"] for row in mutations]
    if len(mutation_ids) != len(set(mutation_ids)):
        raise ProtocolOptimizerError("mutation identifiers must be unique")
    if "base" in mutation_ids:
        raise ProtocolOptimizerError("mutation identifier 'base' is reserved")
    objective_ids = [row["objective_id"] for row in request_copy["objectives"]]
    if len(objective_ids) != len(set(objective_ids)):
        raise ProtocolOptimizerError("objective identifiers must be unique")
    objective_paths = [
        (row["family_path"], row["envelope_bound"]) for row in request_copy["objectives"]
    ]
    if len(objective_paths) != len(set(objective_paths)):
        raise ProtocolOptimizerError(
            "a family envelope path may appear only once; opposing duplicate objectives are forbidden"
        )
    resource_ids = [row["resource_id"] for row in request_copy["resource_constraints"]]
    if len(resource_ids) != len(set(resource_ids)):
        raise ProtocolOptimizerError("resource identifiers must be unique")
    known_mutations = set(mutation_ids)
    for mutation in mutations:
        incompatible = mutation.get("incompatible_mutation_ids", [])
        if mutation["mutation_id"] in incompatible:
            raise ProtocolOptimizerError("a mutation cannot be incompatible with itself")
        if not set(incompatible) <= known_mutations:
            raise ProtocolOptimizerError("incompatible mutation identifier is unknown")
        if not any(float(row["amount"]) > 0 for row in mutation["resource_deltas"]):
            raise ProtocolOptimizerError(
                f"mutation {mutation['mutation_id']!r} requires at least one positive, sourced resource delta"
            )
        # Validate each mutation against the base ledger even if the requested
        # search depth is zero. Combination-specific loss of representability
        # is checked again while each candidate ledger is accumulated.
        _resource_totals(request_copy["resource_constraints"], [mutation])

    maximum_size = min(int(request_copy["maximum_mutations_per_candidate"]), len(mutations))
    proposed_count = _combination_count(len(mutations), maximum_size)
    candidate_limit = int(request_copy["candidate_limit"])
    if candidate_limit > MAX_CANDIDATES:
        raise ProtocolOptimizerError(f"candidate_limit cannot exceed {MAX_CANDIDATES}")
    if proposed_count > candidate_limit:
        raise ProtocolOptimizerError(
            f"protocol search expands to {proposed_count} candidates; limit is {candidate_limit}"
        )

    base_capacity = compile_protocol_capacity(request_copy["base_protocol"])
    available_paths = set(base_capacity["family_envelopes"])
    requested_paths = {row["family_path"] for row in request_copy["objectives"]}
    unknown_paths = requested_paths - available_paths
    if unknown_paths:
        raise ProtocolOptimizerError(
            f"objective paths are not compiler-emitted: {sorted(unknown_paths)}"
        )

    candidates = []
    for size in range(maximum_size + 1):
        for selected in itertools.combinations(mutations, size):
            if _incompatible(selected):
                continue
            candidates.append(
                _candidate(
                    request_sha256,
                    request_copy["base_protocol"],
                    request_copy["objectives"],
                    request_copy["resource_constraints"],
                    selected,
                )
            )

    feasible = [
        row
        for row in candidates
        if row["constraint_eligible"]
        and all(value["value_state"] == "resolved" for value in row["objective_values"])
    ]
    frontier = [
        row["candidate_id"]
        for row in feasible
        if not any(
            other["candidate_id"] != row["candidate_id"] and _dominates(other, row)
            for other in feasible
        )
    ]
    base = next(row for row in candidates if row["candidate_id"] == "base")
    base_values = {row["objective_id"]: row for row in base["objective_values"]}
    mutation_effects = []
    for mutation in mutations:
        if maximum_size == 0:
            mutation_effects.append(
                {
                    "mutation_id": mutation["mutation_id"],
                    "source_object_sha256": mutation["source_object_sha256"],
                    "source_locator": mutation["source_locator"],
                    "effect_state": "not_evaluated_search_depth_zero",
                    "candidate_generated": False,
                    "reason": (
                        "maximum_mutations_per_candidate is zero; only the base protocol "
                        "is inside the declared search space"
                    ),
                    "resource_deltas": copy.deepcopy(mutation["resource_deltas"]),
                }
            )
            continue
        row = next(
            candidate
            for candidate in candidates
            if candidate["mutation_ids"] == [mutation["mutation_id"]]
        )
        mutation_effects.append(
            {
                "mutation_id": mutation["mutation_id"],
                "source_object_sha256": mutation["source_object_sha256"],
                "source_locator": mutation["source_locator"],
                "effect_state": "evaluated_singleton_candidate",
                "candidate_generated": True,
                "constraint_eligible": row["constraint_eligible"],
                "candidate_protocol_sha256": row["candidate_protocol_sha256"],
                "capacity_result_sha256": row["capacity_result_sha256"],
                "objective_deltas_from_base": [
                    (
                        {
                            "objective_id": value["objective_id"],
                            "delta_state": "resolved",
                            "delta": value["value"] - base_values[value["objective_id"]]["value"],
                        }
                        if value["value_state"] == "resolved"
                        and base_values[value["objective_id"]]["value_state"] == "resolved"
                        else {
                            "objective_id": value["objective_id"],
                            "delta_state": "unknown",
                            "delta": None,
                            "reason": (
                                "candidate or base objective envelope is unresolved; "
                                "no numeric delta is emitted"
                            ),
                        }
                    )
                    for value in row["objective_values"]
                ],
                "resource_deltas": copy.deepcopy(mutation["resource_deltas"]),
            }
        )

    all_comparison_ineligible = all(not row["comparison_eligible"] for row in candidates)
    return {
        "schema_version": "anibench.optimizer-protocol-result.v2",
        "optimizer_version": OPTIMIZER_PROTOCOL_VERSION,
        "optimizer_id": request_copy["optimizer_id"],
        "optimizer_request_sha256": request_sha256,
        "claim_class": "prospective_protocol_design_sandbox",
        "empirical_attainment": False,
        "public_rank_emission_permitted": False,
        "comparison_eligible": False,
        "ontology_binding_state": "custom_unverified",
        "source_binding_state": {
            "protocol_geometry": "compiler_bound_protocol_hash",
            "resource_constraints": "caller_declared_not_content_verified",
            "mutation_evidence": "caller_declared_not_content_verified",
        },
        "overall_scalar": None,
        "candidate_count": len(candidates),
        "feasible_candidate_count": len(feasible),
        "objectives": copy.deepcopy(request_copy["objectives"]),
        "pareto_frontier_candidate_ids": sorted(frontier),
        "mutation_effects": mutation_effects,
        "candidates": candidates,
        "anti_gaming_contract": {
            "all_candidates_recompiled_from_protocol_geometry": True,
            "direct_family_result_patch_accepted": False,
            "weighted_aggregate_emitted": False,
            "stable_rank_emitted": False,
            "exact_decimal_resource_accumulation": True,
            "nonrepresentable_positive_resource_delta_accepted": False,
            "order_sensitive_sibling_list_edits_accepted": False,
            "noncanonical_json_pointer_array_tokens_accepted": False,
            "normalized_overlapping_mutations_accepted": False,
            "reserved_base_mutation_id_accepted": False,
            "custom_unverified_comparison_eligibility_propagated": all_comparison_ineligible,
            "candidate_cap": MAX_CANDIDATES,
        },
    }
