"""Metric-specific comparisons of hashed collection profiles in native units.

A declared comparison basis is not an independent scientific endorsement. The
receipt preserves it so reviewers can challenge population, QC and scope choices.
"""

from __future__ import annotations

import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .collection_v1 import _digest
from .paths import schema_path

METRICS = {
    "roster_participants": ("people", "Complete declared study roster"),
    "measured_participants": ("people", "Roster members with accepted targets"),
    "repeated_participants": ("people", "Roster members with at least two distinct dated observations"),
    "median_observation_times": ("distinct times per roster member", "Median distinct dated observations, including zeros"),
    "median_observed_span_days": ("days", "Median span among people with at least two dated observations"),
    "module_participants": ("people", "Roster members with accepted targets in the selected module"),
    "module_targets": ("module targets", "Distinct accepted targets across the selected module"),
    "module_median_targets": ("module targets per roster member", "Median distinct module targets per person, including zeros"),
    "module_participant_events": ("participant-events", "Accepted participant-events in the selected module"),
    "module_target_observations": ("target observations", "Distinct target/participant/event tuples in the selected module"),
}


class CollectionComparisonError(ValueError):
    """Invalid comparison data or an incompatible declared basis."""


def _number(value: Any, *, integer: bool = False) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CollectionComparisonError("Metric values must be numeric")
    if not math.isfinite(value) or value < 0 or (integer and int(value) != value):
        raise CollectionComparisonError("Metric values must be finite, nonnegative and in the declared units")
    return value


def _verified_profile(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") == "anibench.collection-table-evaluation.v1":
        value = value["profile"]
    if value.get("schema_version") != "anibench.collection-profile.v1":
        raise CollectionComparisonError("Expected a collection profile, not a geometry or outcome receipt")
    bound = {k: v for k, v in value.items() if k != "profile_sha256"}
    if value.get("profile_sha256") != _digest(bound):
        raise CollectionComparisonError("Collection profile hash mismatch")
    if not isinstance(value.get("study_id"), str) or not value["study_id"]:
        raise CollectionComparisonError("Profiles require study identifiers")
    if value.get("coverage_interpretation") not in {"lower_bound", "exact_supplied_inventory"}:
        raise CollectionComparisonError("Unsupported coverage interpretation")
    if value.get("record_basis") not in {"planned", "collected"}:
        raise CollectionComparisonError("Unsupported record basis")
    # A caller can recompute a content hash. It binds submitted bytes, not their
    # truth, but internally impossible counts are rejectable without raw records.
    population = value["population"]
    roster = _number(population["roster_participants"], integer=True)
    measured = _number(population["participants_with_accepted_targets"], integer=True)
    repeated = _number(population["participants_with_two_or_more_times"], integer=True)
    if not repeated <= measured <= roster:
        raise CollectionComparisonError("Repeated, measured, and roster participant counts are inconsistent")
    for module in value["modules"]:
        registered = _number(module["registered_target_count"], integer=True)
        observed = _number(module["observed_target_count"], integer=True)
        if observed > registered:
            raise CollectionComparisonError("Observed targets exceed the registered target count")
    return value


def _extract(profile: dict, metric: str, module_id: str | None, basis: dict) -> dict:
    roster = _number(profile["population"]["roster_participants"], integer=True)
    if roster < 1:
        raise CollectionComparisonError("A comparison requires a nonempty declared roster")
    complete = profile["coverage_interpretation"] == "exact_supplied_inventory"
    unknown_times = _number(profile["longitudinal"]["events_with_unknown_time"], integer=True)
    if metric in {"repeated_participants", "median_observation_times"} and unknown_times:
        complete = False
    lower, upper, observed, denominator = None, None, None, roster
    reason = "exact_supplied_inventory" if complete else "incomplete_inventory_or_unresolved_quality"
    locator = ""
    if metric == "roster_participants":
        locator = "/population/roster_participants"
        lower = upper = roster
        reason = "exact_declared_roster"
    elif metric in {"measured_participants", "repeated_participants"}:
        field = {"measured_participants": "participants_with_accepted_targets",
                 "repeated_participants": "participants_with_two_or_more_times"}[metric]
        locator = "/population/" + field
        lower = _number(profile["population"][field], integer=True)
        upper = lower if complete else roster
    elif metric == "median_observation_times":
        locator = "/longitudinal/distinct_known_times_per_participant/median"
        distribution = profile["longitudinal"]["distinct_known_times_per_participant"]
        if distribution["n"] != roster:
            raise CollectionComparisonError("Observation-time medians must retain the whole roster")
        lower = _number(distribution["median"])
        upper = lower if complete else None
    elif metric == "median_observed_span_days":
        locator = "/longitudinal/span_days_among_repeated_participants/median"
        distribution = profile["longitudinal"]["span_days_among_repeated_participants"]
        denominator = _number(distribution["n"], integer=True)
        observed = distribution["median"]
        if observed is not None:
            _number(observed)
        if complete and profile["longitudinal"]["events_with_unknown_time"] == 0 and denominator:
            lower = upper = observed
        else:
            # Adding previously unobserved repeat people can move a conditional
            # median in either direction. It is not a monotone coverage count.
            lower, upper = 0, None
            reason = "conditional_span_not_orderable_with_incomplete_dates_or_inventory"
    else:
        modules = [(i, m) for i, m in enumerate(profile["modules"]) if m["module_id"] == module_id]
        if len(modules) > 1:
            raise CollectionComparisonError("Duplicate selected module")
        if not modules:
            lower, upper = 0, None
            reason = "module_not_reported_not_verified_absent"
        else:
            index, module = modules[0]
            for field in ("target_definition_id", "target_unit", "domain"):
                if module[field] != basis["module_definition"][field]:
                    raise CollectionComparisonError("Selected modules do not share the declared target definition and units")
            if module["roster_denominator"] != roster:
                raise CollectionComparisonError("Module denominator differs from the declared roster")
            fields = {"module_participants": "people_with_accepted_targets",
                      "module_targets": "observed_target_count",
                      "module_median_targets": "targets_per_participant",
                      "module_participant_events": "participant_events_with_accepted_targets",
                      "module_target_observations": "target_observations"}
            field = fields[metric]
            locator = f"/modules/{index}/{field}"
            value = module[field]
            if metric == "module_median_targets":
                if value["n"] != roster:
                    raise CollectionComparisonError("Target medians must retain the whole roster")
                locator += "/median"
                value = value["median"]
            lower = _number(value, integer=metric != "module_median_targets")
            upper = lower if complete else (roster if metric == "module_participants" else None)
            if metric in {"module_participant_events", "module_target_observations"} and unknown_times:
                # Undated event aliases may collapse when their dates resolve.
                observed, lower, upper = lower, 0, None
                reason = "undated_event_identity_prevents_definite_event_count_ordering"
    lower = _number(lower)
    if upper is not None and (_number(upper) < lower):
        raise CollectionComparisonError("Inconsistent metric bounds or participant denominator")
    if metric in {"measured_participants", "repeated_participants", "module_participants"} and lower > roster:
        raise CollectionComparisonError("Participant coverage exceeds its roster")
    return {"study_id": profile["study_id"], "profile_sha256": profile["profile_sha256"],
            "manifest_sha256": profile["manifest_sha256"], "source_sha256": profile["source_sha256"],
            "source_locator": locator or None, "denominator": denominator,
            "lower": lower, "upper": upper, "state": "exact" if lower == upper else "bounded",
            "reason": reason, "observed_conditional_value": observed}


def compare_collection_profiles(profiles: list[dict], basis: dict) -> dict:
    """Emit definite pairwise relations and conservative possible ordinal ranks.

    Intervals describe the supplied evidence, not confidence levels. A null upper
    bound means unbounded missing support, never zero. Ranks apply only to this
    one metric and this corpus. There is deliberately no aggregate score.
    """
    schema_file = schema_path("collection/comparison-basis.schema.json")
    schema = json.loads(schema_file.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(basis))
    if errors:
        raise CollectionComparisonError("Invalid collection comparison basis; see its schema")
    if len(profiles) < 2:
        raise CollectionComparisonError("A comparison requires at least two profiles")
    metric = basis["metric"]
    if metric not in METRICS:
        raise CollectionComparisonError("Unsupported collection metric")
    module_id = basis.get("module_id")
    is_module = metric.startswith("module_")
    if is_module != ("module_id" in basis) or is_module != ("module_definition" in basis):
        raise CollectionComparisonError("Only module metrics require a selected module and target definition")
    _number(basis["time_resolution_days"])
    verified = [_verified_profile(p) for p in profiles]
    first = verified[0]
    if len({p["study_id"] for p in verified}) != len(verified):
        raise CollectionComparisonError("Study identifiers must be unique within the comparison")
    for profile in verified:
        if profile["record_basis"] != basis["record_basis"]:
            raise CollectionComparisonError("Planned and collected evidence cannot share a comparison")
        if profile["implementation"] != first["implementation"]:
            raise CollectionComparisonError("Collection profiles require one identical implementation basis")
        if profile["time_resolution_days"] != basis["time_resolution_days"]:
            raise CollectionComparisonError("Collection profiles require the declared common time resolution")
    rows = sorted([_extract(p, metric, module_id, basis) for p in verified], key=lambda x: x["study_id"])

    def high(row):
        return math.inf if row["upper"] is None else row["upper"]

    relations = []
    for a, b in combinations(rows, 2):
        if a["lower"] > high(b):
            relation = "first_strictly_higher"
        elif b["lower"] > high(a):
            relation = "second_strictly_higher"
        elif a["state"] == b["state"] == "exact" and a["lower"] == b["lower"]:
            relation = "exact_tie"
        else:
            relation = "unresolved_overlap"
        relations.append({"study_ids": [a["study_id"], b["study_id"]], "relation": relation})
    for row in rows:
        others = [other for other in rows if other is not row]
        row["rank_min"] = 1 + sum(other["lower"] > high(row) for other in others)
        row["rank_max"] = 1 + sum(high(other) > row["lower"] for other in others)
    units, definition = METRICS[metric]
    if metric in {"module_targets", "module_median_targets"}:
        units = basis["module_definition"]["target_unit"] + (" per roster member" if metric.endswith("median_targets") else "")
    result = {
        "schema_version": "anibench.collection-metric-comparison.v1",
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "basis_schema_sha256": hashlib.sha256(schema_file.read_bytes()).hexdigest(),
        "collection_implementation": first["implementation"],
        "basis": basis, "basis_sha256": _digest(basis),
        "metric_card": {"version": "1", "metric": metric, "definition": definition,
                        "units": units, "direction": "higher_quantity", "overall_quality_direction": None,
                        "ties": "exact_equal_points_only", "uncertainty": "closed_evidence_bounds_not_confidence_intervals",
                        "ranking": "competition_rank_interval_within_this_metric_and_corpus"},
        "corpus_sha256": _digest(sorted(p["profile_sha256"] for p in verified)),
        "entries": rows, "pairwise_relations": relations,
        "leaders": [r["study_id"] for r in rows if r["rank_max"] == 1],
        "possible_leaders": [r["study_id"] for r in rows if r["rank_min"] == 1],
        "review_status": "basis_declared_by_caller_not_independently_reviewed",
        "claim_scope": "one_native_metric_in_this_bound_corpus_not_overall_study_quality_or_biological_information",
        "overall_score": None,
    }
    result["comparison_sha256"] = _digest(result)
    return result
