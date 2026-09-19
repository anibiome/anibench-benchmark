"""Local, outcome-independent summaries of a study's collected record.

Feature availability is measured here; independent biological information is not.
Participant identities and measurement values never enter the aggregate output.
The input manifest remains private and its hash is not an anonymization claim.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from importlib.metadata import version
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator

from .paths import schema_path


class CollectionError(ValueError):
    """The collection manifest cannot support an unambiguous record profile."""


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _distribution(values: list[float | int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "p10": None, "median": None, "p90": None, "max": None}
    array = np.asarray(values, dtype=float)
    quantiles = np.quantile(array, [0.1, 0.5, 0.9], method="linear")
    return {
        "n": len(values),
        "min": float(array.min()),
        "p10": float(quantiles[0]),
        "median": float(quantiles[1]),
        "p90": float(quantiles[2]),
        "max": float(array.max()),
    }


def _validate(manifest: dict[str, Any]) -> None:
    schema = json.loads(schema_path("collection/record.schema.json").read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda e: str(e.path))
    if errors:
        # Schema messages can echo participant IDs or raw input. Emit location only.
        location = "/".join(str(part) for part in errors[0].absolute_path) or "root"
        raise CollectionError(f"Invalid collection manifest at {location}; see the input schema")
    for event in manifest["events"]:
        if event["time_days"] is not None and not math.isfinite(event["time_days"]):
            raise CollectionError("Event times must be finite")
    if not math.isfinite(manifest["time_resolution_days"]):
        raise CollectionError("Time resolution must be finite")


def profile_collection(manifest: dict[str, Any]) -> dict[str, Any]:
    """Count canonical target/event coverage; never score clinical benefit.

    Dated event aliases at the same declared time coordinate cannot inflate
    follow-up. Undated events retain their source event identity. Distinct time
    coordinates are never joined by an inferred window. Co-observation at a
    stated time resolution does not establish molecular independence.
    """
    _validate(manifest)
    participants = set(manifest["participant_ids"])
    modules = {row["module_id"]: row for row in manifest["modules"]}
    if len(modules) != len(manifest["modules"]):
        raise CollectionError("Module identifiers must be unique")
    targets = {key: set(module["target_ids"]) for key, module in modules.items()}
    target_sets = {}
    for index, target_set in enumerate(manifest.get("target_sets", [])):
        set_id = target_set["target_set_id"]
        module_id = target_set["module_id"]
        if set_id in target_sets or module_id not in modules:
            raise CollectionError(f"Target set {index} has a duplicate identifier or unknown module")
        if not set(target_set["target_ids"]) <= targets[module_id]:
            raise CollectionError(f"Target set {index} has an unregistered target")
        target_sets[set_id] = target_set
    events: dict[tuple[str, str], tuple[str, float | str]] = {}
    for index, row in enumerate(manifest["events"]):
        if row["participant_id"] not in participants:
            raise CollectionError(f"Event {index} references a person outside the roster")
        key = row["participant_id"], row["event_id"]
        if key in events:
            raise CollectionError(f"Event {index} repeats a participant/event identifier")
        coordinate = float(row["time_days"]) if row["time_days"] is not None else "undated:" + row["event_id"]
        events[key] = row["participant_id"], coordinate

    seen: dict[str, dict[str, Any]] = {}
    duplicate_rows = 0
    statuses: Counter[str] = Counter()
    by_module: dict[str, dict[tuple[str, float | str], set[str]]] = {
        key: defaultdict(set) for key in modules
    }
    source_hashes: set[str] = set()
    unique_records = 0
    for index, row in enumerate(manifest["acquisitions"]):
        event_key = row["participant_id"], row["event_id"]
        module_id = row["module_id"]
        if event_key not in events or module_id not in modules:
            raise CollectionError(f"Acquisition {index} has an unknown event or module")
        if "target_set_id" in row:
            target_set = target_sets.get(row["target_set_id"])
            if target_set is None or target_set["module_id"] != module_id:
                raise CollectionError(f"Acquisition {index} has an unknown or cross-module target set")
            row_targets = target_set["target_ids"]
        else:
            row_targets = row["target_ids"]
        if not set(row_targets).issubset(targets[module_id]):
            raise CollectionError(f"Acquisition {index} has an unregistered target")
        status = row["quality_status"]
        if (manifest["record_basis"] == "planned") != (status == "planned"):
            raise CollectionError("Planned and collected acquisitions cannot share one profile")
        canonical_row = {key: value for key, value in row.items() if key != "target_set_id"}
        canonical_row["target_ids"] = sorted(row_targets)
        acquisition_id = row["acquisition_id"]
        if acquisition_id in seen:
            if seen[acquisition_id] != canonical_row:
                raise CollectionError(f"Acquisition {index} conflicts with an earlier lineage")
            duplicate_rows += 1
            continue
        seen[acquisition_id] = canonical_row
        unique_records += 1
        statuses[status] += 1
        source_hashes.add(row["source_sha256"])
        if status in {"pass", "planned"}:
            by_module[module_id][events[event_key]].update(row_targets)

    accepted_events: dict[str, set[float | str]] = {person: set() for person in participants}
    event_modules: dict[tuple[str, float | str], set[str]] = defaultdict(set)
    person_domains: dict[str, set[str]] = {person: set() for person in participants}
    module_profiles = []
    for module_id, module in sorted(modules.items()):
        by_person: dict[str, set[str]] = {person: set() for person in participants}
        event_target_counts = []
        populated = {key: value for key, value in by_module[module_id].items() if value}
        for (person, time), observed in populated.items():
            by_person[person].update(observed)
            event_target_counts.append(len(observed))
            accepted_events[person].add(time)
            event_modules[(person, time)].add(module_id)
            person_domains[person].add(module["domain"])
        measured_people = sum(bool(value) for value in by_person.values())
        module_profiles.append({
            "module_id": module_id,
            "domain": module["domain"],
            "target_unit": module["target_unit"],
            "target_definition_id": module["target_definition_id"],
            "registered_target_count": len(targets[module_id]),
            "observed_target_count": len(set().union(*populated.values())) if populated else 0,
            "people_with_accepted_targets": measured_people,
            "roster_denominator": len(participants),
            "participant_events_with_accepted_targets": len(populated),
            "target_observations": sum(event_target_counts),
            "targets_per_participant": _distribution([len(row) for row in by_person.values()]),
            "targets_per_observed_event": _distribution(event_target_counts),
            "count_semantics": "distinct_registered_targets_not_independent_biological_dimensions",
        })

    joint_profiles = []
    for left, right in combinations(sorted(modules), 2):
        same_person_left = {p for (p, _), v in by_module[left].items() if v}
        same_person_right = {p for (p, _), v in by_module[right].items() if v}
        shared_events = [key for key, values in event_modules.items() if {left, right} <= values]
        joint_profiles.append({
            "module_ids": [left, right],
            "people_with_both_modules_at_any_time": len(same_person_left & same_person_right),
            "people_with_both_modules_at_same_event": len({p for p, _ in shared_events}),
            "participant_events_with_both_modules": len(shared_events),
            "roster_denominator": len(participants),
        })
    known_times = {p: {t for t in times if isinstance(t, float)} for p, times in accepted_events.items()}
    span_values = [max(times) - min(times) for times in known_times.values() if len(times) >= 2]
    intervals = [
        end - start
        for times in known_times.values()
        for start, end in zip(sorted(times), sorted(times)[1:])
    ]
    known_complete = manifest["inventory_status"] == "complete" and not statuses["unknown"]
    result = {
        "schema_version": "anibench.collection-profile.v1",
        "implementation": {
            "engine": "anibench.collection-record.v1",
            "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "schema_sha256": hashlib.sha256(schema_path("collection/record.schema.json").read_bytes()).hexdigest(),
            "numpy_version": np.__version__,
            "jsonschema_version": version("jsonschema"),
        },
        "study_id": manifest["study_id"],
        "record_basis": manifest["record_basis"],
        "inventory_status": manifest["inventory_status"],
        "time_resolution_days": manifest["time_resolution_days"],
        "coverage_interpretation": "exact_supplied_inventory" if known_complete else "lower_bound",
        "manifest_sha256": _digest(manifest),
        "source_sha256": sorted(source_hashes),
        "population": {
            "roster_participants": len(participants),
            "participants_with_accepted_targets": sum(bool(times) for times in accepted_events.values()),
            "participants_with_two_or_more_times": len(span_values),
        },
        "acquisition_audit": {
            "submitted_rows": len(manifest["acquisitions"]),
            "unique_lineages": unique_records,
            "identical_repeated_rows_removed": duplicate_rows,
            "quality_status_counts": {key: statuses[key] for key in ("pass", "fail", "unknown", "planned")},
        },
        "modules": module_profiles,
        "domain_coverage": [
            {"domain": domain, "participants": sum(domain in v for v in person_domains.values()),
             "roster_denominator": len(participants)}
            for domain in sorted({row["domain"] for row in modules.values()})
        ],
        "longitudinal": {
            "observed_events_per_participant": _distribution([len(t) for t in accepted_events.values()]),
            "distinct_known_times_per_participant": _distribution([len(t) for t in known_times.values()]),
            "events_with_unknown_time": sum(isinstance(t, str) for times in accepted_events.values() for t in times),
            "span_days_among_repeated_participants": _distribution(span_values),
            "adjacent_intervals_days": _distribution(intervals),
            "interval_weighting": "one_weight_per_interval_not_per_person",
            "time_semantics": "elapsed_days_from_each_participant_origin",
            "summary_scope": "conditional_on_observed_dated_events_not_a_bound_on_unobserved_followup",
        },
        "joint_coverage": joint_profiles,
        "assumptions": [
            "The submitted roster defines the denominator, including people with no accepted measurements.",
            "Elapsed times and linkage are source declarations, not independently verified identities.",
            "Targets are counted within registered modules; counts are not summed across different units.",
            "An accepted target is recorded availability; biological information and treatment benefit are not estimated.",
            "Dated event aliases at identical participant/time coordinates do not add coverage.",
            "Temporal linkage retains the declared time resolution; a shared day is not exact simultaneity.",
            "No time-window matching, imputation, or independence assumption is introduced.",
            "Quantiles use linear interpolation; they summarize this roster, not sampling uncertainty.",
            "Aggregate output is not automatically safe to publish, especially for small cohorts.",
        ],
        "biological_information": {"state": "not_estimated", "reason": "requires_target_observation_and_noise_model"},
        "overall_score": None,
    }
    result["profile_sha256"] = _digest(result)
    return result
