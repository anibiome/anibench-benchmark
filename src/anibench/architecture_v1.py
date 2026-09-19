# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Source-literal native quantities, scoped interval comparisons, no information score."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from .collection_compare import _number as _native_number
from .comparison_v1 import _dominates

CONTRACT = "anibench.architecture-comparison.v1"
DIRECTIONS = {"higher_quantity", "lower_quantity", "descriptor_only"}
KINDS = {
    "population_count",
    "measurement_breadth",
    "measurement_depth",
    "observation_time",
    "temporal_support",
    "perturbation_architecture",
    "linkage_support",
    "descriptor",
}
STATUSES = {"planned", "collected", "released", "reported_unspecified"}


class ArchitectureError(ValueError):
    """Invalid source-coordinate contract; distinct from unknown/incompatible evidence."""


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise ArchitectureError("Expected finite JSON") from exc


def architecture_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _keys(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ArchitectureError("Unexpected or missing contract fields")


def _text(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ArchitectureError("Expected nonempty canonical text without edge whitespace")
    return value


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ArchitectureError("Expected a SHA-256 identity")


@dataclass(frozen=True)
class CoordinateSemantics:
    """Immutable comparison meaning; cohort identity is deliberately separate."""

    quantity_kind: str
    unit: str
    entity_namespace: str
    denominator: str
    collection_status: str
    time_scope: str
    aggregation: str

    @classmethod
    def from_json(cls, value):
        _keys(value, cls.__dataclass_fields__)
        for item in value.values():
            _text(item)
        if value["quantity_kind"] not in KINDS or value["collection_status"] not in STATUSES:
            raise ArchitectureError("Unsupported quantity kind or collection status")
        return cls(**value)


def _sources(value, *, required):
    if not isinstance(value, list) or (required and not value):
        raise ArchitectureError("Known quantities require source identities and locators")
    seen = set()
    for source in value:
        _keys(source, {"source_sha256", "locator"})
        _hash(source["source_sha256"])
        _text(source["locator"])
        key = (source["source_sha256"], source["locator"])
        if key in seen:
            raise ArchitectureError("Duplicate source locator")
        seen.add(key)


def _number(value, *, integer=False):
    try:
        return _native_number(value, integer=integer)
    except (ValueError, OverflowError) as exc:
        raise ArchitectureError(str(exc)) from exc


def _bounds(value):
    if not isinstance(value, dict):
        raise ArchitectureError("Expected a typed point, bound or unknown")
    state = value.get("state")
    if state == "point":
        _keys(value, {"state", "value"})
        number = _number(value["value"])
        return number, number
    if state == "bounded":
        _keys(value, {"state", "lower", "upper"})
        lower = _number(value["lower"])
        upper = None if value["upper"] is None else _number(value["upper"])
        if upper is not None and upper <= lower:
            raise ArchitectureError("Bounds must be ordered; equal bounds use a point")
        return lower, upper
    if state == "unknown":
        _keys(value, {"state", "reason"})
        _text(value["reason"])
        return None, None
    raise ArchitectureError("Unsupported value state")


def _oriented(row, direction):
    high = math.inf if row["upper"] is None else row["upper"]
    return (row["lower"], high) if direction == "higher_quantity" else (-high, -row["lower"])


def _interval_relation(left, right, direction):
    a, b = _oriented(left, direction), _oriented(right, direction)
    if a[0] > b[1]:
        return "first_strictly_preferred_quantity"
    if b[0] > a[1]:
        return "second_strictly_preferred_quantity"
    if left["state"] == right["state"] == "point" and a[0] == b[0]:
        return "exact_tie"
    return "unresolved_overlap"


def compare_architecture(request: dict[str, Any]) -> dict[str, Any]:
    """Compare caller-declared source quantities, with explicit scope and no H/R.

    Hashes bind supplied statements, not source truth. Descriptor-only coordinates
    remain visible but do not define preferences. No per-person profile is inferred.
    """
    request = json.loads(_canonical(request))
    _keys(request, {"contract", "basis", "records"})
    if request["contract"] != "anibench.architecture-request.v1":
        raise ArchitectureError("Unsupported request contract")
    basis = request["basis"]
    _keys(basis, {"basis_id", "population_comparison", "coordinates"})
    _text(basis["basis_id"])
    population = basis["population_comparison"]
    _keys(population, {"mode", "rationale"})
    if population["mode"] != "quantity_only_preserve_each_population_scope":
        raise ArchitectureError(
            "Only explicit quantity comparisons across preserved scopes are supported"
        )
    _text(population["rationale"])
    if not isinstance(basis["coordinates"], list) or not basis["coordinates"]:
        raise ArchitectureError("Select at least one coordinate")
    selected, seen_semantics = {}, set()
    for coordinate in basis["coordinates"]:
        _keys(coordinate, {"coordinate_id", "semantics", "direction"})
        identity = _text(coordinate["coordinate_id"])
        semantics = CoordinateSemantics.from_json(coordinate["semantics"])
        if _text(coordinate["direction"]) not in DIRECTIONS:
            raise ArchitectureError("Unknown quantity preference")
        if semantics.quantity_kind == "descriptor" and coordinate["direction"] != "descriptor_only":
            raise ArchitectureError("A descriptor cannot acquire a quantity preference")
        if identity in selected or semantics in seen_semantics:
            raise ArchitectureError("Duplicate coordinate identity or semantic alias")
        selected[identity] = coordinate
        seen_semantics.add(semantics)
    records = request["records"]
    if not isinstance(records, list) or not records:
        raise ArchitectureError("At least one aggregate source record is required")
    entries, record_ids = [], set()
    for record in records:
        _keys(record, {"record_id", "study_id", "population_scope", "coordinates"})
        for field in ("record_id", "study_id", "population_scope"):
            _text(record[field])
        if record["record_id"] in record_ids:
            raise ArchitectureError("Duplicate record identity")
        record_ids.add(record["record_id"])
        if not isinstance(record["coordinates"], list):
            raise ArchitectureError("Record coordinates must be a list")
        supplied, semantic_keys = {}, set()
        for coordinate in record["coordinates"]:
            _keys(coordinate, {"coordinate_id", "semantics", "value", "sources"})
            identity = _text(coordinate["coordinate_id"])
            semantics = CoordinateSemantics.from_json(coordinate["semantics"])
            if identity not in selected or identity in supplied or semantics in semantic_keys:
                raise ArchitectureError(
                    "Unselected, duplicate or semantically redundant coordinate"
                )
            lower, upper = _bounds(coordinate["value"])
            if (
                semantics.quantity_kind == "population_count"
                and semantics.aggregation == "distinct_count"
                and coordinate["value"]["state"] != "unknown"
            ):
                _number(lower, integer=True)
                if upper is not None:
                    _number(upper, integer=True)
            _sources(coordinate["sources"], required=coordinate["value"]["state"] != "unknown")
            supplied[identity] = coordinate
            semantic_keys.add(semantics)
        rows = []
        for identity, coordinate in selected.items():
            supplied_row = supplied.get(identity)
            if supplied_row is None:
                rows.append(
                    {
                        "coordinate_id": identity,
                        "state": "unknown",
                        "lower": None,
                        "upper": None,
                        "semantics": None,
                        "compatibility": "unknown",
                        "reason": "coordinate_not_supplied_not_verified_absent",
                        "sources": [],
                    }
                )
                continue
            lower, upper = _bounds(supplied_row["value"])
            semantics = CoordinateSemantics.from_json(supplied_row["semantics"])
            compatible = semantics == CoordinateSemantics.from_json(coordinate["semantics"])
            # Unknown lifecycle is displayable, but cannot silently mix planned and collected facts.
            ordering_known = semantics.collection_status != "reported_unspecified"
            rows.append(
                {
                    "coordinate_id": identity,
                    "state": supplied_row["value"]["state"],
                    "lower": lower,
                    "upper": upper,
                    "semantics": asdict(semantics),
                    "compatibility": "compatible"
                    if compatible and ordering_known
                    else "incompatible",
                    "reason": supplied_row["value"].get("reason", "source_literal_quantity")
                    if compatible and ordering_known
                    else "semantic_mismatch_or_unspecified_collection_status",
                    "sources": supplied_row["sources"],
                }
            )
        entries.append(
            {
                "record_id": record["record_id"],
                "study_id": record["study_id"],
                "population_scope": record["population_scope"],
                "record_sha256": architecture_sha256(record),
                "coordinates": rows,
            }
        )
    entries.sort(key=lambda row: row["record_id"])
    objectives = {
        key: value["direction"]
        for key, value in selected.items()
        if value["direction"] != "descriptor_only"
    }
    pairs = []
    for first, second in combinations(entries, 2):
        left = {r["coordinate_id"]: r for r in first["coordinates"]}
        right = {r["coordinate_id"]: r for r in second["coordinates"]}
        relations = []
        lower_left, upper_left, lower_right, upper_right = {}, {}, {}, {}
        blocked = False
        for identity, direction in objectives.items():
            a, b = left[identity], right[identity]
            if a["compatibility"] != "compatible" or b["compatibility"] != "compatible":
                relation = "unresolved_incompatible_or_missing_semantics"
                blocked = True
            elif a["state"] == "unknown" or b["state"] == "unknown":
                relation = "unresolved_unknown_value"
                blocked = True
            else:
                relation = _interval_relation(a, b, direction)
                lower_left[identity], upper_left[identity] = _oriented(a, direction)
                lower_right[identity], upper_right[identity] = _oriented(b, direction)
            relations.append(
                {"coordinate_id": identity, "direction": direction, "relation": relation}
            )
        if not objectives:
            relation = "descriptor_only"
        elif blocked:
            relation = "unresolved"
        elif _dominates(lower_left, upper_right):
            relation = "first_dominates_selected_quantities"
        elif _dominates(lower_right, upper_left):
            relation = "second_dominates_selected_quantities"
        elif all(r["relation"] == "exact_tie" for r in relations):
            relation = "exact_tie"
        elif any(lower_left[k] > upper_right[k] for k in objectives) and any(
            lower_right[k] > upper_left[k] for k in objectives
        ):
            relation = "definite_tradeoff"
        else:
            relation = "unresolved"
        pairs.append(
            {
                "record_ids": [first["record_id"], second["record_id"]],
                "relation": relation,
                "coordinates": relations,
            }
        )
    dominated, unresolved = set(), set()
    for pair in pairs:
        first, second = pair["record_ids"]
        if pair["relation"] == "first_dominates_selected_quantities":
            dominated.add(second)
        elif pair["relation"] == "second_dominates_selected_quantities":
            dominated.add(first)
        elif pair["relation"] == "unresolved":
            unresolved.update((first, second))
    possible = sorted(record_ids - dominated) if objectives else []
    definite = sorted(record_ids - dominated - unresolved) if objectives else []
    # Even a one-record corpus cannot have a certified frontier if its selected
    # coordinates are unknown or incompatible with the declared ordering basis.
    for entry in entries:
        if (
            any(
                row["coordinate_id"] in objectives
                and (row["state"] == "unknown" or row["compatibility"] != "compatible")
                for row in entry["coordinates"]
            )
            and entry["record_id"] in definite
        ):
            definite.remove(entry["record_id"])
    implementation = {}
    for name in ("architecture_v1.py", "collection_compare.py", "comparison_v1.py"):
        implementation[name] = (
            "sha256:" + hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        )
    result = {
        "contract": CONTRACT,
        "basis": basis,
        "basis_sha256": architecture_sha256(basis),
        "request_sha256": architecture_sha256(request),
        "entries": entries,
        "pairwise_relations": pairs,
        "selected_ordered_coordinates": list(objectives),
        "definitely_undominated_record_ids": definite,
        "possibly_undominated_record_ids": possible,
        "implementation": {"sha256": implementation, "python": platform.python_version()},
        "interval_semantics": "closed_source_evidence_bounds_not_confidence_intervals; null_upper_is_unbounded",
        "comparison_scope": "selected_compatible_native_quantities_only_not_overall_biology",
        "population_scope": "quantity_comparison_not_population_equivalence_or_transportability",
        "evidence_status": "caller_declared_source_identity_and_semantics_not_independently_certified",
        "overall_score": None,
        "biological_saturation": None,
    }
    result["receipt_sha256"] = architecture_sha256(result)
    return result
