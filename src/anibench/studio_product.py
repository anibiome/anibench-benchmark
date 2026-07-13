"""Source-bound product views used by the local AniBench Studio.

This module deliberately builds a descriptive comparator atlas rather than a
leaderboard.  A public source projection is visible only after the coordinate
table's projection hash has been replayed against the exact packaged JSON
object.  Missing protocol-capacity geometry remains ``not_scoreable``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ATLAS_CONTRACT = "anibench.studio-comparator-atlas.v1"
FIELD_RECEIPT_CONTRACT = "anibench.external-field-provenance-receipt.v2"
SOURCE_COORDINATE_CONTRACT = "anibench.source-projection-six-family-coordinates.v1"
FAMILY_IDS = (
    "intensive",
    "extensive",
    "longitudinal",
    "causal",
    "personalized_sequential",
    "transport",
)
REQUIRED_COLUMNS = {
    "study_id",
    "projection_lane",
    "population_value",
    "population_semantics",
    "population_state",
    "duration_days",
    "duration_semantics",
    "duration_state",
    "policy_arms",
    "randomized_policy",
    "concurrent_control",
    "deployed_operator_families",
    "identifiable_policy_contrasts",
    "adaptive_reassignment",
    "within_policy_randomized",
    "known_projected_measurement_modules",
    "conditional_measurement_modules",
    "unknown_measurement_modules",
    "open_gate_count",
    "source_projection_sha256",
}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
STUDY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")


class StudioAtlasError(ValueError):
    """Raised when the packaged comparator corpus cannot be verified."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table_path(root: Path) -> Path:
    # The source repository contains ANI-internal projections as well as the
    # explicitly public table.  The installed public wheel contains only the
    # latter at the data path.  Prefer the public export in a source checkout.
    candidates = (
        root / "packaging" / "public_v2" / "SOURCE_COORDINATE_TABLE.csv",
        root / "data" / "source_projections" / "v2" / "SOURCE_COORDINATE_TABLE.csv",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise StudioAtlasError("public comparator coordinate table is not installed")


def _projection_root(root: Path) -> Path:
    candidate = root / "data" / "source_projections" / "v2"
    if candidate.is_dir():
        return candidate
    raise StudioAtlasError("public comparator projection objects are not installed")


def _field_receipt_path(root: Path) -> Path:
    candidates = (
        root / "packaging" / "public_v2" / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
        root
        / "data"
        / "source_projections"
        / "v2"
        / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise StudioAtlasError("external field provenance receipt is not installed")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _number(value: str) -> int | float | None:
    if value == "":
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise StudioAtlasError(f"invalid numeric coordinate {value!r}") from exc
    return int(number) if number.is_integer() else number


def _boolean(value: str) -> bool | None:
    if value == "":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    raise StudioAtlasError(f"invalid typed boolean {value!r}")


def _coordinate(value: str, state: str, semantics: str, *, unit: str) -> dict[str, Any]:
    return {
        "value": _number(value),
        "state": state or "unknown",
        "semantics": semantics or "unknown",
        "unit": unit,
    }


def build_studio_comparator_atlas(root: str | Path) -> dict[str, Any]:
    """Build the hash-verified, score-free external comparator view.

    The returned object is safe to display in Studio because it contains only
    the explicitly public comparator table and the corresponding public source
    projections.  It never reads the ANI-internal rows present in the broader
    development coordinate table.
    """

    root_path = Path(root)
    table_path = _table_path(root_path)
    projection_root = _projection_root(root_path)
    field_receipt_path = _field_receipt_path(root_path)
    try:
        field_receipt = json.loads(field_receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StudioAtlasError(f"invalid external field provenance receipt: {exc}") from exc
    if field_receipt.get("contract") != FIELD_RECEIPT_CONTRACT:
        raise StudioAtlasError("external field provenance receipt contract mismatch")
    if field_receipt.get("public_rank_allowed") is not False:
        raise StudioAtlasError("external field provenance receipt cannot authorize rank")
    if field_receipt.get("all_known_fields_bound") is not True:
        raise StudioAtlasError("external field provenance receipt is incomplete")
    if field_receipt.get("all_known_fields_machine_resolved") is not True:
        raise StudioAtlasError(
            "external field provenance receipt permits nonmechanical known fields"
        )
    if field_receipt.get("curated_manual_fact_count") != 0:
        raise StudioAtlasError(
            "external field provenance receipt contains manual known facts"
        )
    coordinate_receipt = field_receipt.get("coordinate_table") or {}
    if coordinate_receipt.get("sha256") != _sha256(table_path):
        raise StudioAtlasError("field receipt does not bind the installed coordinate table")
    projection_receipts = {
        row.get("study_id"): row for row in field_receipt.get("projections", [])
    }
    if len(projection_receipts) != field_receipt.get("projection_count"):
        raise StudioAtlasError("field receipt projection set is incomplete or duplicated")
    with table_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
        if missing_columns:
            raise StudioAtlasError(
                "public comparator coordinate table is missing columns: "
                + ", ".join(missing_columns)
            )
        rows = list(reader)
    if not rows:
        raise StudioAtlasError("public comparator coordinate table is empty")

    studies: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row_index, row in enumerate(rows, start=2):
        study_id = row["study_id"]
        if not STUDY_ID_RE.fullmatch(study_id) or study_id in seen_ids:
            raise StudioAtlasError(
                f"invalid or duplicate study_id {study_id!r} at coordinate-table row {row_index}"
            )
        seen_ids.add(study_id)
        expected_hash = row["source_projection_sha256"]
        if not SHA256_RE.fullmatch(expected_hash):
            raise StudioAtlasError(
                f"invalid source projection hash for {study_id}: {expected_hash!r}"
            )
        projection_path = (projection_root / f"{study_id}.json").resolve()
        if projection_root.resolve() not in projection_path.parents:
            raise StudioAtlasError(f"source projection path escapes the public corpus: {study_id}")
        if not projection_path.is_file():
            raise StudioAtlasError(f"missing public source projection for {study_id}")
        actual_hash = _sha256(projection_path)
        if actual_hash != expected_hash:
            raise StudioAtlasError(
                f"source projection hash mismatch for {study_id}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        projection_receipt = projection_receipts.get(study_id)
        if (
            not isinstance(projection_receipt, dict)
            or projection_receipt.get("projection_sha256") != actual_hash
        ):
            raise StudioAtlasError(
                f"field provenance receipt does not bind projection {study_id}"
            )
        fact_rows = projection_receipt.get("facts")
        if (
            not isinstance(fact_rows, list)
            or len(fact_rows) != projection_receipt.get("known_fact_count")
        ):
            raise StudioAtlasError(f"field provenance fact set is incomplete for {study_id}")
        provenance_counts = {
            "mechanically_extracted_source_bound": sum(
                row.get("provenance_mode") == "mechanically_extracted_source_bound"
                for row in fact_rows
                if isinstance(row, dict)
            ),
            "curated_manual_source_bound": sum(
                row.get("provenance_mode") == "curated_manual_source_bound"
                for row in fact_rows
                if isinstance(row, dict)
            ),
        }
        if sum(provenance_counts.values()) != len(fact_rows):
            raise StudioAtlasError(f"unknown field provenance mode for {study_id}")
        if provenance_counts["curated_manual_source_bound"] != 0:
            raise StudioAtlasError(
                f"public known-fact scope contains manual curation for {study_id}"
            )
        downgraded_unknown_count = projection_receipt.get(
            "downgraded_unknown_fact_count"
        )
        if not isinstance(downgraded_unknown_count, int) or downgraded_unknown_count < 0:
            raise StudioAtlasError(
                f"invalid downgraded-unknown count for {study_id}"
            )
        try:
            projection = json.loads(projection_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StudioAtlasError(
                f"invalid public source projection for {study_id}: {exc}"
            ) from exc
        if not isinstance(projection, dict) or projection.get("study_id") != study_id:
            raise StudioAtlasError(f"source projection identity mismatch for {study_id}")
        if "suite_compiler" in projection or "suite_input_path" in projection:
            raise StudioAtlasError(
                f"source projection for {study_id} carries a retired suite contract"
            )
        open_gates = projection.get("open_gates")
        if not isinstance(open_gates, list) or not all(
            isinstance(gate, str) and gate for gate in open_gates
        ) or len(set(open_gates)) != len(open_gates):
            raise StudioAtlasError(f"source projection for {study_id} has invalid open gates")
        source_coordinates = projection.get("source_coordinate_contract")
        if not isinstance(source_coordinates, dict):
            raise StudioAtlasError(
                f"source projection for {study_id} lacks the six-family coordinate contract"
            )
        if set(source_coordinates) != {
            "contract",
            "coordinate_basis",
            "overall_scalar",
            "public_rank_allowed",
            "families",
        }:
            raise StudioAtlasError(
                f"source projection for {study_id} has undeclared coordinate fields"
            )
        if source_coordinates.get("contract") != SOURCE_COORDINATE_CONTRACT:
            raise StudioAtlasError(
                f"source projection for {study_id} has a retired family contract"
            )
        if (
            source_coordinates.get("coordinate_basis") != "source_bound_projection_only"
            or source_coordinates.get("overall_scalar") is not None
            or source_coordinates.get("public_rank_allowed") is not False
        ):
            raise StudioAtlasError(
                f"source projection for {study_id} violates the score-free coordinate boundary"
            )
        coordinate_families = source_coordinates.get("families")
        if not isinstance(coordinate_families, dict) or set(coordinate_families) != set(
            FAMILY_IDS
        ):
            raise StudioAtlasError(
                f"source projection for {study_id} does not declare exactly six families"
            )
        family_eligibility: dict[str, dict[str, Any]] = {}
        for family_id in FAMILY_IDS:
            family = coordinate_families[family_id]
            if not isinstance(family, dict):
                raise StudioAtlasError(
                    f"source projection for {study_id} has an invalid {family_id} coordinate"
                )
            if set(family) != {
                "evidence_state",
                "coordinate_state",
                "coordinates",
                "reason",
                "open_gate_ids",
            }:
                raise StudioAtlasError(
                    f"source projection for {study_id} has undeclared {family_id} fields"
                )
            if (
                family.get("evidence_state") != "unknown"
                or family.get("coordinate_state") != "not_scoreable"
                or family.get("coordinates") is not None
                or family.get("reason")
                != "source_complete_protocol_capacity_geometry_not_available"
                or family.get("open_gate_ids") != open_gates
            ):
                raise StudioAtlasError(
                    f"source projection for {study_id} overstates the {family_id} coordinate"
                )
            family_eligibility[family_id] = {
                "state": family["coordinate_state"],
                "evidence_state": family["evidence_state"],
                "coordinates": family["coordinates"],
                "reason": family["reason"],
                "open_gate_ids": list(family["open_gate_ids"]),
                "source_projection_sha256": f"sha256:{actual_hash}",
            }
        if _number(row["open_gate_count"]) != len(open_gates):
            raise StudioAtlasError(
                f"open-gate count mismatch for {study_id}: table={row['open_gate_count']}, "
                f"projection={len(open_gates)}"
            )
        authorities = projection.get("authorities")
        if not isinstance(authorities, list) or not authorities:
            raise StudioAtlasError(f"source projection for {study_id} has no authority objects")
        authority_bindings = []
        for authority in authorities:
            if not isinstance(authority, dict):
                raise StudioAtlasError(f"source projection for {study_id} has invalid authority")
            source_id = authority.get("source_id")
            source_sha256 = authority.get("sha256")
            if not isinstance(source_id, str) or not source_id:
                raise StudioAtlasError(f"source projection for {study_id} has an unnamed authority")
            if not isinstance(source_sha256, str) or not SHA256_RE.fullmatch(source_sha256):
                raise StudioAtlasError(
                    f"source projection for {study_id} has an invalid authority hash"
                )
            authority_bindings.append(
                {
                    "source_id": source_id,
                    "sha256": source_sha256,
                    "evidence_class": authority.get("evidence_class", "not_declared"),
                }
            )

        source_binding = {
            "source_projection_sha256": f"sha256:{actual_hash}",
            "source_projection_path": _relative(projection_path, root_path),
            "coordinate_table_row": row_index,
            "authority_objects": authority_bindings,
                "field_provenance": {
                "receipt_sha256": f"sha256:{_sha256(field_receipt_path)}",
                    "known_fact_count": len(fact_rows),
                    "downgraded_unknown_fact_count": downgraded_unknown_count,
                    **provenance_counts,
            },
        }
        studies.append(
            {
                "study_id": study_id,
                "name": projection.get("name", study_id),
                "projection_lane": row["projection_lane"],
                "projection_status": projection.get("projection_status", "unknown"),
                "population": _coordinate(
                    row["population_value"],
                    row["population_state"],
                    row["population_semantics"],
                    unit="participants",
                ),
                "duration": _coordinate(
                    row["duration_days"],
                    row["duration_state"],
                    row["duration_semantics"],
                    unit="days",
                ),
                "causal_architecture": {
                    "policy_arms": _number(row["policy_arms"]),
                    "randomized_policy": _boolean(row["randomized_policy"]),
                    "concurrent_control": _boolean(row["concurrent_control"]),
                    "deployed_operator_families": _number(row["deployed_operator_families"]),
                    "identifiable_policy_contrasts": _number(row["identifiable_policy_contrasts"]),
                    "adaptive_reassignment": _boolean(row["adaptive_reassignment"]),
                    "within_policy_randomized": _boolean(row["within_policy_randomized"]),
                },
                "measurement_module_states": {
                    "known_projected": _number(row["known_projected_measurement_modules"]),
                    "conditional": _number(row["conditional_measurement_modules"]),
                    "unknown": _number(row["unknown_measurement_modules"]),
                },
                "open_gates": list(open_gates),
                "family_eligibility": family_eligibility,
                "comparison_eligible": False,
                "source_binding": source_binding,
            }
        )

    mechanical_total = sum(
        study["source_binding"]["field_provenance"][
            "mechanically_extracted_source_bound"
        ]
        for study in studies
    )
    curated_total = sum(
        study["source_binding"]["field_provenance"]["curated_manual_source_bound"]
        for study in studies
    )
    downgraded_total = sum(
        study["source_binding"]["field_provenance"][
            "downgraded_unknown_fact_count"
        ]
        for study in studies
    )
    if (
        mechanical_total != field_receipt.get("mechanically_extracted_fact_count")
        or curated_total != field_receipt.get("curated_manual_fact_count")
        or mechanical_total + curated_total != field_receipt.get("known_fact_count")
        or downgraded_total != field_receipt.get("downgraded_unknown_fact_count")
        or field_receipt.get("all_known_fields_machine_resolved") is not True
    ):
        raise StudioAtlasError("field provenance aggregate counts drifted")

    return {
        "schema_version": ATLAS_CONTRACT,
        "claim_class": "source_bound_descriptive_comparator_atlas",
        "overall_scalar": None,
        "public_rank_emission_permitted": False,
        "row_order_semantics": "coordinate_table_source_order_not_rank",
        "source_coordinate_contract": SOURCE_COORDINATE_CONTRACT,
        "coordinate_table": {
            "path": _relative(table_path, root_path),
            "sha256": f"sha256:{_sha256(table_path)}",
        },
        "field_provenance_receipt": {
            "contract": FIELD_RECEIPT_CONTRACT,
            "path": _relative(field_receipt_path, root_path),
            "sha256": f"sha256:{_sha256(field_receipt_path)}",
            "known_fact_count": field_receipt["known_fact_count"],
            "mechanically_extracted_fact_count": field_receipt[
                "mechanically_extracted_fact_count"
            ],
            "curated_manual_fact_count": field_receipt["curated_manual_fact_count"],
            "downgraded_unknown_fact_count": field_receipt[
                "downgraded_unknown_fact_count"
            ],
            "all_known_fields_machine_resolved": True,
            "manual_interpretations_mechanically_validated": False,
        },
        "study_count": len(studies),
        "comparison_eligible_study_count": sum(
            study["comparison_eligible"] is True for study in studies
        ),
        "placement_state": "typed_unknown_no_source_complete_comparator_geometry",
        "studies": studies,
    }
