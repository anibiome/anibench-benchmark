"""Local CSV/CSV.gz adapters for availability, dates, and declared quality.

Numeric measurements are inspected for availability and then discarded. No
model fitting, clinical effect calculation, network call, or participant export
is performed. The optional intermediate collection manifest remains private.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .collection_v1 import CollectionError, profile_collection
from .paths import schema_path

MISSING = frozenset({"", "na", "n/a", "nan", "null", "none"})


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _available(value: str, kind: str) -> bool:
    if value.strip().lower() in MISSING:
        return False
    if kind == "nonempty":
        return True
    try:
        numeric = float(value)
    except ValueError as error:
        raise CollectionError("A target value is neither numeric nor a declared missing token") from error
    if not math.isfinite(numeric):
        raise CollectionError("A numeric target value is nonfinite")
    return True


def _time(value: str, kind: str) -> float | None:
    if value.strip().lower() in MISSING:
        return None
    try:
        if kind == "elapsed_days":
            result = float(value)
        elif kind == "iso_date":
            result = float(date.fromisoformat(value).toordinal())
        else:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                raise CollectionError("ISO timestamps require an explicit timezone")
            # Align with date ordinals while retaining sub-day information.
            result = instant.astimezone(timezone.utc).timestamp() / 86400 + date(1970, 1, 1).toordinal()
    except (ValueError, OverflowError) as error:
        raise CollectionError("A time field does not match its declared format") from error
    if not math.isfinite(result):
        raise CollectionError("Time fields must be finite")
    return result


def import_collection_tables(mapping: dict[str, Any], *, base: Path) -> tuple[dict, dict]:
    """Import only explicitly mapped local columns; return manifest and audit.

    Long rows are grouped into module/event/quality records within each source.
    Repeated cells never increase distinct target or participant-event counts.
    The roster is always provided explicitly; it is never inferred from the
    subset of people with successful assays.
    """
    schema = json.loads(schema_path("collection/table-map.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(mapping))
    if errors:
        raise CollectionError("Invalid table mapping; see schemas/collection/table-map.schema.json")
    roster = set(mapping["participant_ids"])
    modules = {row["module_id"]: row for row in mapping["modules"]}
    if len(modules) != len(mapping["modules"]):
        raise CollectionError("The table mapping repeats a module identifier")
    bases = {"relative" if s["time_format"] == "elapsed_days" else "absolute" for s in mapping["sources"]}
    if len(bases) != 1:
        raise CollectionError("Absolute and relative clocks require an explicit upstream alignment")
    absolute_time = "absolute" in bases
    all_targets: dict[str, set[str]] = {key: set() for key in modules}
    event_times: dict[tuple[str, str], float | None] = {}
    acquired: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)
    audits = []
    for source_index, source in enumerate(mapping["sources"]):
        path = (base / source["path"]).resolve()
        if not path.is_file():
            raise CollectionError(f"Mapped source {source_index} is not a regular local file")
        before = _file_hash(path)
        if source.get("sha256") is not None and before != source["sha256"]:
            raise CollectionError(f"Mapped source {source_index} does not match its pinned hash")
        counts: Counter[str] = Counter()
        opener = gzip.open if path.suffix.lower() == ".gz" else Path.open
        with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            if not headers or len(headers) != len(set(headers)):
                raise CollectionError(f"Mapped source {source_index} has missing or duplicate headers")
            required = {source["participant_column"], source["event_column"], source["time_column"]}
            required.update(rule["column"] for rule in source.get("filters", []))
            required.update(source[key] for key in ("module_column", "quality_column") if key in source)
            if source["format"] == "long":
                required.update([source["feature_column"], source["value_column"]])
            else:
                required.update(source["feature_columns"])
            if not required <= set(headers):
                raise CollectionError(f"Mapped source {source_index} lacks required columns")
            for row_number, row in enumerate(reader, start=2):
                counts["rows_read"] += 1
                if None in row or any(value is None for value in row.values()):
                    raise CollectionError(f"Mapped source {source_index}, row {row_number} has malformed columns")
                if any(row[rule["column"]] not in rule["values"] for rule in source.get("filters", [])):
                    counts["filtered_rows"] += 1
                    continue
                person = row[source["participant_column"]]
                if person not in roster:
                    if mapping["outside_roster"] == "exclude":
                        counts["outside_roster_rows"] += 1
                        continue
                    raise CollectionError(f"Mapped source {source_index}, row {row_number} is outside the declared roster")
                event = row[source["event_column"]]
                module = row[source["module_column"]] if "module_column" in source else source["module_id"]
                if not event or module not in modules:
                    raise CollectionError(f"Mapped source {source_index}, row {row_number} has an invalid event or module")
                try:
                    time = _time(row[source["time_column"]], source["time_format"])
                    if "quality_column" in source:
                        status = source["quality_map"][row[source["quality_column"]]]
                    else:
                        status = source["quality_status"]
                    pairs = (
                        [(row[source["feature_column"]], row[source["value_column"]])]
                        if source["format"] == "long"
                        else [(feature, row[feature]) for feature in source["feature_columns"]]
                    )
                    observed = set()
                    for target, value in pairs:
                        if not target:
                            raise CollectionError("Target identifiers must not be empty")
                        all_targets[module].add(target)
                        if _available(value, source["value_kind"]):
                            observed.add(target)
                        else:
                            counts["missing_target_cells"] += 1
                except (CollectionError, KeyError):
                    # Source exception context can contain the original cell. Never
                    # chain it into a traceback or include it in the user-facing error.
                    raise CollectionError(f"Mapped source {source_index}, row {row_number} has an invalid time, quality, or target field") from None
                key = person, event
                if key in event_times and event_times[key] != time:
                    raise CollectionError(f"Mapped source {source_index}, row {row_number} conflicts with the event clock")
                event_times[key] = time
                acquired[(person, event, module, status, before)].update(observed)
                counts["included_rows"] += 1
        if _file_hash(path) != before:
            raise CollectionError(f"Mapped source {source_index} changed during import")
        audits.append({"source_index": source_index, "source_sha256": before, **dict(sorted(counts.items()))})

    origins: dict[str, float] = {}
    if absolute_time:
        for (person, _), time in event_times.items():
            if time is not None:
                origins[person] = min(time, origins.get(person, time))
    manifest = {
        "schema_version": "anibench.collection-record.v1",
        "study_id": mapping["study_id"],
        "record_basis": mapping["record_basis"],
        "inventory_status": mapping["inventory_status"],
        "time_resolution_days": mapping["time_resolution_days"],
        "participant_ids": sorted(roster),
        "modules": [{**module, "target_ids": sorted(all_targets[key])} for key, module in sorted(modules.items())],
        "events": [
            {"participant_id": person, "event_id": event,
             "time_days": None if time is None else time - origins.get(person, 0)}
            for (person, event), time in sorted(event_times.items())
        ],
        "acquisitions": [
            {"acquisition_id": "import-" + hashlib.sha256(json.dumps(key).encode()).hexdigest(),
             "participant_id": key[0], "event_id": key[1], "module_id": key[2],
             "quality_status": key[3], "source_sha256": key[4], "target_ids": sorted(targets)}
            for key, targets in sorted(acquired.items())
        ],
    }
    # Validate the complete semantic contract before returning or writing it.
    profile = profile_collection(manifest)
    audit = {
        "schema_version": "anibench.collection-import.v1",
        "mapping_sha256": "sha256:" + hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest(),
        "sources": audits,
        "time_origin": "first_included_source_event_per_participant" if absolute_time else "caller_declared_elapsed_days",
        "record_unit": "source_module_event_quality_group_not_technical_replicate_count",
        "manifest_sha256": profile["manifest_sha256"],
        "participant_data_in_audit": False,
    }
    return manifest, audit
