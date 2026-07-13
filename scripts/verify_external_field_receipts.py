#!/usr/bin/env python3
"""Build and replay the external-comparator field provenance contract.

The public replay requires only normalized projection objects, the frozen
acquisition ledger, the external coordinate table, and this sealed receipt.  It
proves that every ``state=known`` projection field is unchanged from the
source-bound curation build and that every displayed coordinate is reproduced
from those projection fields.

Raw upstream response bodies are intentionally not redistributed.  When they
are available in the private authority checkout, ``--raw-source-bytes`` also
replays source hashes, JSON-pointer extractors, and locator-resolution evidence.
Interpretive fields are not public known facts.  The corpus builder downgrades
them to typed unknown before serialization.  Raw replay therefore accepts a
displayed ``state=known`` field only when every declared source binding resolves
through a receipted executable operator.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACQUISITION_LEDGER = Path(
    "data/source_projections/v2/EXTERNAL_SOURCE_ACQUISITION_LEDGER.json"
)
DEFAULT_COORDINATE_TABLE = Path(
    "packaging/public_v2/SOURCE_COORDINATE_TABLE.csv"
)
DEFAULT_RECEIPT = Path(
    "packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json"
)
RECEIPT_CONTRACT = "anibench.external-field-provenance-receipt.v2"
MECHANICAL = "mechanically_extracted_source_bound"
CURATED = "curated_manual_source_bound"
DOWNGRADE_REASON_CODE = "nonmechanical_source_binding_typed_unknown"
MECHANICAL_OPERATORS = frozenset(
    {
        "json_pointer_identity",
        "json_pointer_array_length",
        "json_pointer_object_count",
        "json_pointer_casefold_equals_randomized",
    }
)
CURATED_LOCATOR_RESOLUTIONS = frozenset(
    {
        "json_pointer_resolved_for_manual_interpretation",
        "literal_source_bytes_resolved",
        "curator_declared_locator_not_machine_resolved",
    }
)

COORDINATE_COLUMNS = (
    "study_id,projection_lane,population_value,population_semantics,population_state,"
    "duration_days,duration_semantics,duration_state,policy_arms,randomized_policy,"
    "concurrent_control,deployed_operator_families,identifiable_policy_contrasts,"
    "adaptive_reassignment,within_policy_randomized,known_projected_measurement_modules,"
    "conditional_measurement_modules,unknown_measurement_modules,open_gate_count,"
    "source_projection_sha256"
).split(",")


class FieldProvenanceError(ValueError):
    """Raised when a sealed field or raw-source binding cannot be replayed."""


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _value_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _walk_known_facts(
    value: Any,
    pointer: str = "",
) -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if value.get("state") == "known" and value.get("source_ids"):
            yield pointer, value
        for key, child in value.items():
            yield from _walk_known_facts(
                child,
                f"{pointer}/{_escape_pointer_token(str(key))}",
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_known_facts(child, f"{pointer}/{index}")


def _walk_downgraded_unknowns(
    value: Any,
    pointer: str = "",
) -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if (
            value.get("state") == "unknown"
            and value.get("reason_code") == DOWNGRADE_REASON_CODE
        ):
            yield pointer, value
        for key, child in value.items():
            yield from _walk_downgraded_unknowns(
                child,
                f"{pointer}/{_escape_pointer_token(str(key))}",
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_downgraded_unknowns(child, f"{pointer}/{index}")


def _json_pointer_get(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise FieldProvenanceError(f"not a JSON pointer: {pointer}")
    current = value
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise FieldProvenanceError(f"pointer traverses a scalar: {pointer}")
    return current


def _mechanical_extraction(source_value: Any, fact_value: Any) -> tuple[str, Any] | None:
    if type(source_value) is type(fact_value) and source_value == fact_value:
        return "json_pointer_identity", source_value
    if isinstance(source_value, list) and not isinstance(fact_value, bool):
        if len(source_value) == fact_value:
            return "json_pointer_array_length", len(source_value)
    if isinstance(source_value, dict) and "count" in source_value:
        count = source_value["count"]
        if type(count) is type(fact_value) and count == fact_value:
            return "json_pointer_object_count", count
    if isinstance(source_value, str) and isinstance(fact_value, bool):
        derived = source_value.casefold() == "randomized"
        if derived is fact_value:
            return "json_pointer_casefold_equals_randomized", derived
    return None


def _resolve_source_binding(
    *,
    source_body: bytes,
    source_id: str,
    source_sha256: str,
    source_bytes: int,
    locator: str,
    fact_value: Any,
) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "source_id": source_id,
        "source_object_sha256": source_sha256,
        "source_object_bytes": source_bytes,
        "locator": locator,
        "locator_sha256": _sha256_bytes(locator.encode("utf-8")),
    }
    source_json: Any | None = None
    try:
        source_json = json.loads(source_body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass

    if locator.startswith("/") and source_json is not None:
        try:
            source_value = _json_pointer_get(source_json, locator)
        except (FieldProvenanceError, KeyError, IndexError, TypeError, ValueError):
            source_value = None
        else:
            extraction = _mechanical_extraction(source_value, fact_value)
            source_value_sha256 = _value_sha256(source_value)
            if extraction is not None:
                operator, derived = extraction
                binding.update(
                    {
                        "binding_mode": MECHANICAL,
                        "operator": operator,
                        "locator_resolution": "json_pointer_resolved",
                        "source_value_sha256": source_value_sha256,
                        "derived_value_sha256": _value_sha256(derived),
                    }
                )
                return binding
            binding.update(
                {
                    "binding_mode": CURATED,
                    "operator": "manual_curatorial_interpretation",
                    "locator_resolution": "json_pointer_resolved_for_manual_interpretation",
                    "source_value_sha256": source_value_sha256,
                }
            )
            return binding

    encoded = locator.encode("utf-8")
    offset = source_body.find(encoded)
    match_mode = "exact_bytes"
    if offset < 0:
        offset = source_body.lower().find(encoded.lower())
        match_mode = "ascii_casefold_bytes"
    if offset >= 0:
        matched = source_body[offset : offset + len(encoded)]
        binding.update(
            {
                "binding_mode": CURATED,
                "operator": "manual_curatorial_interpretation",
                "locator_resolution": "literal_source_bytes_resolved",
                "locator_match_mode": match_mode,
                "locator_byte_start": offset,
                "locator_byte_end_exclusive": offset + len(encoded),
                "matched_source_bytes_sha256": _sha256_bytes(matched),
            }
        )
        return binding

    binding.update(
        {
            "binding_mode": CURATED,
            "operator": "manual_curatorial_interpretation",
            "locator_resolution": "curator_declared_locator_not_machine_resolved",
        }
    )
    return binding


def enforce_machine_resolved_known_facts(
    *,
    projection: Mapping[str, Any],
    source_index: Mapping[str, Mapping[str, Any]],
    raw_source_cache: Mapping[str, bytes],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return a public projection in which every known fact is mechanical.

    The source-authored candidate value is used only in memory to test the
    declared bindings.  A value that cannot be reproduced by an executable
    operator is removed from the public object and replaced by typed unknown.
    Its source identifiers and exact locators remain available for future
    promotion work, but neither its value nor a curator-authored derivation is
    serialized.
    """

    public_projection = copy.deepcopy(dict(projection))
    retained = 0
    downgraded = 0
    for pointer, node in list(_walk_known_facts(public_projection)):
        source_ids = list(node.get("source_ids", []))
        source_locators = node.get("source_locators", {})
        if not source_ids or set(source_ids) != set(source_locators):
            raise FieldProvenanceError(
                f"source ids and locators differ for {projection.get('study_id')}{pointer}"
            )
        binding_summaries: list[dict[str, str]] = []
        all_mechanical = True
        for source_id in source_ids:
            source = source_index.get(source_id)
            source_body = raw_source_cache.get(source_id)
            if source is None or source_body is None:
                raise FieldProvenanceError(
                    f"source object unavailable for {projection.get('study_id')}{pointer}: "
                    f"{source_id}"
                )
            binding = _resolve_source_binding(
                source_body=source_body,
                source_id=source_id,
                source_sha256=str(source["sha256"]),
                source_bytes=int(source["bytes"]),
                locator=str(source_locators[source_id]),
                fact_value=node["value"],
            )
            all_mechanical = all_mechanical and binding["binding_mode"] == MECHANICAL
            binding_summaries.append(
                {
                    "source_id": source_id,
                    "binding_mode": str(binding["binding_mode"]),
                    "locator_resolution": str(binding["locator_resolution"]),
                    "operator": str(binding["operator"]),
                }
            )
        if all_mechanical:
            retained += 1
            continue

        preserved = {
            key: value
            for key, value in node.items()
            if key not in {"state", "value", "is_placeholder", "derivation"}
        }
        preserved.update(
            {
                "state": "unknown",
                "reason_code": DOWNGRADE_REASON_CODE,
                "reason": (
                    "The candidate value is not exposed because at least one declared "
                    "source binding lacks a machine-resolved executable derivation."
                ),
                "source_binding_resolution": binding_summaries,
            }
        )
        node.clear()
        node.update(preserved)
        downgraded += 1

    return public_projection, {
        "mechanically_retained_known_fact_count": retained,
        "nonmechanical_downgraded_unknown_fact_count": downgraded,
    }


def _validate_sealed_binding_structure(
    binding: Mapping[str, Any],
    *,
    fact_value_sha256: str,
) -> None:
    mode = binding.get("binding_mode")
    operator = binding.get("operator")
    resolution = binding.get("locator_resolution")
    if mode == MECHANICAL:
        if operator not in MECHANICAL_OPERATORS:
            raise FieldProvenanceError(f"unknown mechanical operator: {operator}")
        if resolution != "json_pointer_resolved":
            raise FieldProvenanceError("mechanical binding lacks a resolved JSON pointer")
        if not str(binding.get("locator", "")).startswith("/"):
            raise FieldProvenanceError("mechanical binding locator is not a JSON pointer")
        if binding.get("derived_value_sha256") != fact_value_sha256:
            raise FieldProvenanceError("mechanical derived value digest differs from fact")
        if len(str(binding.get("source_value_sha256", ""))) != 64:
            raise FieldProvenanceError("mechanical source value digest is missing")
        return
    if mode != CURATED:
        raise FieldProvenanceError(f"unknown field provenance mode: {mode}")
    if operator != "manual_curatorial_interpretation":
        raise FieldProvenanceError("curated binding uses a non-manual operator")
    if resolution not in CURATED_LOCATOR_RESOLUTIONS:
        raise FieldProvenanceError(f"unknown curated locator resolution: {resolution}")
    if "derived_value_sha256" in binding:
        raise FieldProvenanceError("curated binding cannot carry a derived-value claim")


def _fact_value(fact: Mapping[str, Any] | None) -> str:
    if fact is None or fact.get("state") == "unknown":
        return ""
    value = fact["value"]
    return str(value).lower() if isinstance(value, bool) else str(value)


def _first_fact(
    section: Mapping[str, dict[str, Any]],
    preferred: Sequence[str],
) -> tuple[str, dict[str, Any]]:
    for key in preferred:
        if key in section:
            return key, section[key]
    key = next(iter(section))
    return key, section[key]


def external_coordinate_row(
    projection: dict[str, Any],
    projection_sha256: str,
) -> dict[str, str]:
    population_name, population = _first_fact(
        projection["population"],
        (
            "randomized",
            "cohort_enrollment",
            "combined_profiled",
            "profiled_participants",
            "planned_enrollment",
            "released_participants_lower_bound",
            "registry_enrollment",
            "registry_full_program",
            "enrolled",
        ),
    )
    duration_candidates = [
        key
        for key in (
            "intervention_duration_days",
            "protocol_duration_days",
            "training_duration_days",
            "planned_primary_endpoint_days",
            "median_observation_span_days",
        )
        if key in projection["timeline"]
    ]
    if duration_candidates:
        duration_name = duration_candidates[0]
        duration = projection["timeline"][duration_name]
    else:
        duration_name = next(iter(projection["timeline"]))
        duration = projection["timeline"][duration_name]
        if not duration_name.endswith("_days"):
            duration = {"state": "unknown"}
    design = projection["intervention_design"]
    classes = projection["measurement_module_classes"]
    return {
        "study_id": projection["study_id"],
        "projection_lane": projection["evaluation_mode"],
        "population_value": _fact_value(population),
        "population_semantics": population_name,
        "population_state": population["state"],
        "duration_days": _fact_value(duration),
        "duration_semantics": duration_name,
        "duration_state": duration.get("state", "unknown"),
        "policy_arms": _fact_value(design["policy_arms"]),
        "randomized_policy": _fact_value(design["randomized_policy_assignment"]),
        "concurrent_control": _fact_value(design["active_concurrent_comparator"]),
        "deployed_operator_families": _fact_value(
            design["deployed_operator_families"]
        ),
        "identifiable_policy_contrasts": _fact_value(
            design["causally_identifiable_policy_contrasts"]
        ),
        "adaptive_reassignment": _fact_value(design["adaptive_reassignment"]),
        "within_policy_randomized": _fact_value(
            design["within_policy_adaptation_randomized"]
        ),
        "known_projected_measurement_modules": str(len(classes["exact"])),
        "conditional_measurement_modules": str(len(classes["conditional"])),
        "unknown_measurement_modules": str(len(classes["unknown"])),
        "open_gate_count": str(len(projection["open_gates"])),
        "source_projection_sha256": projection_sha256,
    }


def render_external_coordinate_table(rows: Iterable[dict[str, str]]) -> bytes:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=COORDINATE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def build_field_provenance_receipt(
    *,
    root: Path,
    projection_ids: Sequence[str],
    acquisition_ledger: Path,
    coordinate_table: Path,
) -> dict[str, Any]:
    acquisition = json.loads(acquisition_ledger.read_text(encoding="utf-8"))
    source_index = {row["source_id"]: row for row in acquisition["sources"]}
    raw_source_cache: dict[str, bytes] = {}
    for source_id, source in source_index.items():
        source_body = (root / source["path"]).read_bytes()
        if (
            len(source_body) != source["bytes"]
            or _sha256_bytes(source_body) != source["sha256"]
        ):
            raise FieldProvenanceError(
                f"raw source object drifted before receipt build: {source_id}"
            )
        raw_source_cache[source_id] = source_body
    projection_rows: list[dict[str, Any]] = []
    mechanical_count = 0
    curated_count = 0
    downgraded_unknown_count = 0
    locator_resolution_counts: dict[str, int] = {}
    coordinate_rows: list[dict[str, str]] = []

    for study_id in projection_ids:
        projection_path = root / f"data/source_projections/v2/{study_id}.json"
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        projection_sha256 = _sha256_path(projection_path)
        facts: list[dict[str, Any]] = []
        downgraded_unknowns: list[dict[str, Any]] = []
        for pointer, node in _walk_known_facts(projection):
            source_ids = list(node["source_ids"])
            if set(source_ids) != set(node["source_locators"]):
                raise FieldProvenanceError(
                    f"source ids and locators differ for {study_id}{pointer}"
                )
            bindings = []
            for source_id in source_ids:
                try:
                    source = source_index[source_id]
                except KeyError as exc:
                    raise FieldProvenanceError(
                        f"unknown source id {source_id} for {study_id}{pointer}"
                    ) from exc
                binding = _resolve_source_binding(
                    source_body=raw_source_cache[source_id],
                    source_id=source_id,
                    source_sha256=source["sha256"],
                    source_bytes=source["bytes"],
                    locator=node["source_locators"][source_id],
                    fact_value=node["value"],
                )
                bindings.append(binding)
                locator_resolution_counts[binding["locator_resolution"]] = (
                    locator_resolution_counts.get(binding["locator_resolution"], 0) + 1
                )
            fact_mode = (
                MECHANICAL
                if bindings and all(row["binding_mode"] == MECHANICAL for row in bindings)
                else CURATED
            )
            if fact_mode != MECHANICAL:
                raise FieldProvenanceError(
                    "displayed known fact lacks an all-mechanical source derivation: "
                    f"{study_id}{pointer}"
                )
            mechanical_count += fact_mode == MECHANICAL
            curated_count += fact_mode == CURATED
            fact = {
                "fact_id": _sha256_bytes(f"{study_id}\0{pointer}".encode("utf-8")),
                "projection_pointer": pointer,
                "value": node["value"],
                "value_sha256": _value_sha256(node["value"]),
                "provenance_mode": fact_mode,
                "source_bindings": bindings,
            }
            if "derivation" in node:
                fact["curator_declared_derivation"] = node["derivation"]
            facts.append(fact)
        for pointer, node in _walk_downgraded_unknowns(projection):
            if "value" in node or not node.get("reason"):
                raise FieldProvenanceError(
                    f"invalid nonmechanical downgrade at {study_id}{pointer}"
                )
            source_ids = list(node.get("source_ids", []))
            source_locators = node.get("source_locators", {})
            if not source_ids or set(source_ids) != set(source_locators):
                raise FieldProvenanceError(
                    f"downgraded source ids and locators differ for {study_id}{pointer}"
                )
            resolution = node.get("source_binding_resolution")
            if not isinstance(resolution, list) or [
                row.get("source_id") for row in resolution if isinstance(row, dict)
            ] != source_ids:
                raise FieldProvenanceError(
                    f"downgraded source-resolution summary drifted for {study_id}{pointer}"
                )
            if all(row.get("binding_mode") == MECHANICAL for row in resolution):
                raise FieldProvenanceError(
                    f"all-mechanical fact was incorrectly downgraded at {study_id}{pointer}"
                )
            downgraded_unknowns.append(
                {
                    "projection_pointer": pointer,
                    "reason_code": DOWNGRADE_REASON_CODE,
                    "source_ids": source_ids,
                    "source_locators_sha256": _value_sha256(source_locators),
                }
            )
        downgraded_unknown_count += len(downgraded_unknowns)
        projection_rows.append(
            {
                "study_id": study_id,
                "projection_path": projection_path.relative_to(root).as_posix(),
                "projection_sha256": projection_sha256,
                "known_fact_count": len(facts),
                "downgraded_unknown_fact_count": len(downgraded_unknowns),
                "facts": facts,
                "downgraded_unknowns": downgraded_unknowns,
            }
        )
        coordinate_rows.append(external_coordinate_row(projection, projection_sha256))

    coordinate_bytes = render_external_coordinate_table(coordinate_rows)
    coordinate_table.parent.mkdir(parents=True, exist_ok=True)
    coordinate_table.write_bytes(coordinate_bytes)
    fact_count = mechanical_count + curated_count
    return {
        "contract": RECEIPT_CONTRACT,
        "status": "machine_only_field_bindings_candidate_not_scored",
        "projection_scope": (
            "all_state_known_fields_and_nonmechanical_downgrades_in_16_public_"
            "external_projection_objects"
        ),
        "fact_policy": {
            "mechanically_extracted_source_bound": (
                "The declared operator deterministically maps a resolved source JSON node "
                "to the projection value."
            ),
            "nonmechanical_source_binding_typed_unknown": (
                "A candidate value whose bindings are curated, unresolved, or otherwise "
                "non-executable is removed and retained only as typed unknown with source "
                "identifiers, locators, and reason."
            ),
            "unknown_fields": "Typed unknown fields never enter displayed known-value scope.",
        },
        "acquisition_ledger": {
            "path": acquisition_ledger.relative_to(root).as_posix(),
            "sha256": _sha256_path(acquisition_ledger),
            "source_count": len(source_index),
            "raw_source_bodies_redistributed": False,
        },
        "coordinate_table": {
            "path": coordinate_table.relative_to(root).as_posix(),
            "sha256": _sha256_bytes(coordinate_bytes),
            "row_count": len(coordinate_rows),
            "derivation_contract": "anibench.external-coordinate-table-from-projections.v1",
        },
        "projection_count": len(projection_rows),
        "known_fact_count": fact_count,
        "mechanically_extracted_fact_count": mechanical_count,
        "curated_manual_fact_count": curated_count,
        "downgraded_unknown_fact_count": downgraded_unknown_count,
        "locator_resolution_counts": dict(sorted(locator_resolution_counts.items())),
        "all_known_fields_bound": True,
        "all_known_fields_machine_resolved": True,
        "raw_source_build_status": (
            "passed_source_hashes_extractors_and_locator_resolution_recorded"
        ),
        "raw_source_object_count_verified": len(raw_source_cache),
        "curated_manual_interpretations_mechanically_validated": False,
        "public_rank_allowed": False,
        "projections": projection_rows,
    }


def _read_coordinate_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COORDINATE_COLUMNS:
            raise FieldProvenanceError("coordinate table columns drifted")
        return list(reader)


def _resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def verify_field_provenance_receipt(
    *,
    root: Path,
    receipt_path: Path,
    raw_source_bytes: bool = False,
) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("contract") != RECEIPT_CONTRACT:
        raise FieldProvenanceError("unexpected field provenance receipt contract")
    if receipt.get("all_known_fields_bound") is not True:
        raise FieldProvenanceError("receipt does not bind all known fields")
    if receipt.get("all_known_fields_machine_resolved") is not True:
        raise FieldProvenanceError("receipt does not require machine-resolved known fields")
    if receipt.get("public_rank_allowed") is not False:
        raise FieldProvenanceError("field receipt cannot authorize a public rank")
    if receipt.get("curated_manual_interpretations_mechanically_validated") is not False:
        raise FieldProvenanceError("manual interpretations are mislabeled as validated")
    if receipt.get("curated_manual_fact_count") != 0:
        raise FieldProvenanceError("public known-fact scope contains manual curation")
    acquisition_meta = receipt["acquisition_ledger"]
    acquisition_path = _resolve_path(root, acquisition_meta["path"])
    if _sha256_path(acquisition_path) != acquisition_meta["sha256"]:
        raise FieldProvenanceError("acquisition ledger hash drifted")
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    source_index = {row["source_id"]: row for row in acquisition["sources"]}
    if len(source_index) != acquisition_meta["source_count"]:
        raise FieldProvenanceError("acquisition source count drifted")
    if receipt.get("raw_source_object_count_verified") != len(source_index):
        raise FieldProvenanceError("receipt did not verify every acquisition source object")
    raw_source_cache: dict[str, bytes] = {}
    if raw_source_bytes:
        for source_id, source in source_index.items():
            source_path = _resolve_path(root, source["path"])
            if not source_path.is_file():
                raise FieldProvenanceError(f"raw source object missing: {source['path']}")
            source_body = source_path.read_bytes()
            if (
                len(source_body) != source["bytes"]
                or _sha256_bytes(source_body) != source["sha256"]
            ):
                raise FieldProvenanceError(f"raw source object drifted: {source_id}")
            raw_source_cache[source_id] = source_body

    observed_projection_ids: list[str] = []
    coordinate_rows: list[dict[str, str]] = []
    fact_count = 0
    mechanical_count = 0
    curated_count = 0
    downgraded_unknown_count = 0
    locator_resolution_counts: dict[str, int] = {}
    for projection_receipt in receipt["projections"]:
        study_id = projection_receipt["study_id"]
        observed_projection_ids.append(study_id)
        projection_path = _resolve_path(root, projection_receipt["projection_path"])
        if _sha256_path(projection_path) != projection_receipt["projection_sha256"]:
            raise FieldProvenanceError(f"projection hash drifted: {study_id}")
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        observed = list(_walk_known_facts(projection))
        expected = projection_receipt["facts"]
        if len(observed) != projection_receipt["known_fact_count"] or len(observed) != len(expected):
            raise FieldProvenanceError(f"known fact count drifted: {study_id}")
        for (pointer, node), fact in zip(observed, expected, strict=True):
            if pointer != fact["projection_pointer"]:
                raise FieldProvenanceError(f"fact pointer drifted: {study_id}{pointer}")
            if node["value"] != fact["value"] or type(node["value"]) is not type(fact["value"]):
                raise FieldProvenanceError(f"fact value drifted: {study_id}{pointer}")
            if _value_sha256(node["value"]) != fact["value_sha256"]:
                raise FieldProvenanceError(f"fact value digest drifted: {study_id}{pointer}")
            expected_id = _sha256_bytes(f"{study_id}\0{pointer}".encode("utf-8"))
            if fact["fact_id"] != expected_id:
                raise FieldProvenanceError(f"fact identity drifted: {study_id}{pointer}")
            bindings = fact["source_bindings"]
            if [row["source_id"] for row in bindings] != list(node["source_ids"]):
                raise FieldProvenanceError(f"source order drifted: {study_id}{pointer}")
            observed_modes: list[str] = []
            for binding in bindings:
                source_id = binding["source_id"]
                source = source_index.get(source_id)
                if source is None:
                    raise FieldProvenanceError(f"unknown receipt source: {source_id}")
                locator = node["source_locators"].get(source_id)
                if locator != binding["locator"]:
                    raise FieldProvenanceError(f"locator drifted: {study_id}{pointer}")
                if binding["locator_sha256"] != _sha256_bytes(locator.encode("utf-8")):
                    raise FieldProvenanceError(f"locator digest drifted: {study_id}{pointer}")
                if (
                    binding["source_object_sha256"] != source["sha256"]
                    or binding["source_object_bytes"] != source["bytes"]
                ):
                    raise FieldProvenanceError(f"source binding drifted: {study_id}{pointer}")
                _validate_sealed_binding_structure(
                    binding,
                    fact_value_sha256=fact["value_sha256"],
                )
                observed_modes.append(binding["binding_mode"])
                locator_resolution_counts[binding["locator_resolution"]] = (
                    locator_resolution_counts.get(binding["locator_resolution"], 0) + 1
                )
                if raw_source_bytes:
                    replayed = _resolve_source_binding(
                        source_body=raw_source_cache[source_id],
                        source_id=source_id,
                        source_sha256=source["sha256"],
                        source_bytes=source["bytes"],
                        locator=locator,
                        fact_value=node["value"],
                    )
                    if replayed != binding:
                        raise FieldProvenanceError(
                            f"raw source locator replay drifted: {study_id}{pointer}"
                        )
            expected_mode = (
                MECHANICAL
                if observed_modes and all(mode == MECHANICAL for mode in observed_modes)
                else CURATED
            )
            if expected_mode != MECHANICAL:
                raise FieldProvenanceError(
                    "displayed known fact lacks an all-mechanical source derivation: "
                    f"{study_id}{pointer}"
                )
            if fact["provenance_mode"] != expected_mode:
                raise FieldProvenanceError(f"fact provenance mode drifted: {study_id}{pointer}")
            mechanical_count += expected_mode == MECHANICAL
            curated_count += expected_mode == CURATED
            fact_count += 1
        observed_downgrades = list(_walk_downgraded_unknowns(projection))
        expected_downgrades = projection_receipt.get("downgraded_unknowns")
        if (
            not isinstance(expected_downgrades, list)
            or len(observed_downgrades)
            != projection_receipt.get("downgraded_unknown_fact_count")
            or len(observed_downgrades) != len(expected_downgrades)
        ):
            raise FieldProvenanceError(f"downgraded unknown count drifted: {study_id}")
        for (pointer, node), downgrade in zip(
            observed_downgrades,
            expected_downgrades,
            strict=True,
        ):
            if "value" in node or not node.get("reason"):
                raise FieldProvenanceError(
                    f"downgraded unknown exposes a value: {study_id}{pointer}"
                )
            source_ids = list(node.get("source_ids", []))
            source_locators = node.get("source_locators", {})
            if (
                pointer != downgrade.get("projection_pointer")
                or downgrade.get("reason_code") != DOWNGRADE_REASON_CODE
                or source_ids != downgrade.get("source_ids")
                or _value_sha256(source_locators)
                != downgrade.get("source_locators_sha256")
            ):
                raise FieldProvenanceError(
                    f"downgraded unknown receipt drifted: {study_id}{pointer}"
                )
            resolution = node.get("source_binding_resolution")
            if not isinstance(resolution, list) or [
                row.get("source_id") for row in resolution if isinstance(row, dict)
            ] != source_ids:
                raise FieldProvenanceError(
                    f"downgraded source-resolution summary drifted: {study_id}{pointer}"
                )
            if all(row.get("binding_mode") == MECHANICAL for row in resolution):
                raise FieldProvenanceError(
                    f"all-mechanical fact was incorrectly downgraded: {study_id}{pointer}"
                )
            downgraded_unknown_count += 1
        coordinate_rows.append(
            external_coordinate_row(projection, projection_receipt["projection_sha256"])
        )

    if len(set(observed_projection_ids)) != len(observed_projection_ids):
        raise FieldProvenanceError("duplicate projection id in receipt")
    if len(observed_projection_ids) != receipt["projection_count"]:
        raise FieldProvenanceError("projection count drifted")
    if fact_count != receipt["known_fact_count"]:
        raise FieldProvenanceError("known fact total drifted")
    if mechanical_count != receipt["mechanically_extracted_fact_count"]:
        raise FieldProvenanceError("mechanical fact total drifted")
    if curated_count != receipt["curated_manual_fact_count"]:
        raise FieldProvenanceError("curated fact total drifted")
    if downgraded_unknown_count != receipt.get("downgraded_unknown_fact_count"):
        raise FieldProvenanceError("downgraded unknown total drifted")
    if dict(sorted(locator_resolution_counts.items())) != receipt["locator_resolution_counts"]:
        raise FieldProvenanceError("locator resolution totals drifted")

    coordinate_meta = receipt["coordinate_table"]
    coordinate_path = _resolve_path(root, coordinate_meta["path"])
    derived_coordinate_bytes = render_external_coordinate_table(coordinate_rows)
    if _sha256_bytes(derived_coordinate_bytes) != coordinate_meta["sha256"]:
        raise FieldProvenanceError("derived coordinate table digest drifted")
    if _sha256_path(coordinate_path) != coordinate_meta["sha256"]:
        raise FieldProvenanceError("packaged coordinate table digest drifted")
    if _read_coordinate_rows(coordinate_path) != coordinate_rows:
        raise FieldProvenanceError("packaged coordinate rows drifted")

    return {
        "contract": "anibench.external-field-provenance-replay.v1",
        "receipt_contract": RECEIPT_CONTRACT,
        "receipt_path": receipt_path.relative_to(root).as_posix(),
        "receipt_sha256": _sha256_path(receipt_path),
        "public_field_binding_replay_passed": True,
        "coordinate_derivation_replay_passed": True,
        "projection_count": len(observed_projection_ids),
        "known_fact_count": fact_count,
        "mechanically_extracted_fact_count": mechanical_count,
        "curated_manual_fact_count": curated_count,
        "downgraded_unknown_fact_count": downgraded_unknown_count,
        "raw_source_revalidation_status": (
            "passed_source_hashes_extractors_and_locator_resolution_replayed"
            if raw_source_bytes
            else "not_requested_public_replay_does_not_require_source_bodies"
        ),
        "curated_manual_interpretations_mechanically_revalidated": False,
        "all_displayed_known_facts_machine_resolved": True,
        "public_rank_allowed": False,
        "passed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument(
        "--raw-source-bytes",
        action="store_true",
        help=(
            "Also replay exact upstream source hashes and locator/extractor evidence; "
            "requires the non-redistributed source objects in the authority checkout"
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    receipt = _resolve_path(root, args.receipt)
    try:
        result = verify_field_provenance_receipt(
            root=root,
            receipt_path=receipt,
            raw_source_bytes=args.raw_source_bytes,
        )
    except (FieldProvenanceError, FileNotFoundError, json.JSONDecodeError) as exc:
        result = {
            "contract": "anibench.external-field-provenance-replay.v1",
            "passed": False,
            "error": str(exc),
        }
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
