# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Extract only source-literal public registry aggregates; never copy narratives."""

from __future__ import annotations

import argparse
import calendar
import datetime
import hashlib
import json
import re
from pathlib import Path


def semantics(kind, unit, namespace, aggregation, status):
    return {
        "quantity_kind": kind,
        "unit": unit,
        "entity_namespace": namespace,
        "denominator": "whole_registry_protocol_record",
        "collection_status": status,
        "time_scope": "source_snapshot_protocol_scope",
        "aggregation": aggregation,
    }


def date_bounds(value):
    try:
        if len(value) == 10:
            date = datetime.date.fromisoformat(value)
            return date, date
        if len(value) == 7:
            year, month = map(int, value.split("-"))
            return datetime.date(year, month, 1), datetime.date(
                year, month, calendar.monthrange(year, month)[1]
            )
    except (ValueError, TypeError):
        return None
    return None


def derive_snapshot(raw, provenance):
    """Reproduce facts from matching bytes; provenance supplies retrieval metadata only."""
    nct = provenance["nct_id"]
    if not re.fullmatch(r"NCT\d{8}", nct):
        raise ValueError("snapshot_identity_format")
    if hashlib.sha256(raw).hexdigest() != provenance["raw_sha256"]:
        raise ValueError("frozen_snapshot_hash_mismatch")
    source = json.loads(raw)["protocolSection"]
    if source["identificationModule"]["nctId"] != nct:
        raise ValueError("snapshot_identity_mismatch")
    design = source.get("designModule", {})
    status = source.get("statusModule", {})
    enroll = design.get("enrollmentInfo", {})
    lifecycle = {"ACTUAL": "collected", "ESTIMATED": "planned"}.get(
        enroll.get("type"), "reported_unspecified"
    )

    def point(value):
        return {"state": "point", "value": value}

    def unknown(reason):
        return {"state": "unknown", "reason": reason}

    def coordinate(identity, sem, value, pointers):
        return {
            "coordinate_id": identity,
            "semantics": sem,
            "value": value,
            "sources": [
                {"source_sha256": "sha256:" + provenance["raw_sha256"], "locator": p}
                for p in pointers
            ],
        }

    count = enroll.get("count")
    nv = (
        point(count)
        if enroll.get("type") in {"ACTUAL", "ESTIMATED"}
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count >= 0
        else unknown("Registry enrollment count or actual/estimated type not supplied")
    )
    arms = source.get("armsInterventionsModule", {}).get("armGroups")
    av = (
        point(len(arms))
        if isinstance(arms, list) and arms
        else unknown("No nonempty arm-group list; absence does not establish zero arms")
    )
    start = status.get("startDateStruct", {})
    end = status.get("primaryCompletionDateStruct", {})
    ds = {"ACTUAL": "collected", "ESTIMATED": "planned"}.get(
        start.get("type"), "reported_unspecified"
    )
    sd, ed = date_bounds(start.get("date", "")), date_bounds(end.get("date", ""))
    dv = unknown(
        "Date statuses missing/mixed, dates incomplete, or calendar chronology unsupported"
    )
    if sd and ed and start.get("type") == end.get("type") and ds != "reported_unspecified":
        low, high = (ed[0] - sd[1]).days, (ed[1] - sd[0]).days
        if low >= 0:
            dv = point(low) if low == high else {"state": "bounded", "lower": low, "upper": high}
    allocation = design.get("designInfo", {}).get("allocation")
    rv = (
        point(1 if allocation == "RANDOMIZED" else 0)
        if allocation in {"RANDOMIZED", "NON_RANDOMIZED"}
        else unknown("Registry allocation token missing or not applicable")
    )
    coords = [
        coordinate(
            "enrollment",
            semantics(
                "population_count",
                "people",
                "registry_enrollment_not_assay_complete",
                "distinct_count",
                lifecycle,
            ),
            nv,
            ["/protocolSection/designModule/enrollmentInfo"],
        ),
        coordinate(
            "arm_groups",
            semantics(
                "perturbation_architecture",
                "listed_arm_groups",
                "registry_protocol_arm_group_entries_not_verified_executed_arms",
                "listed_entry_count",
                "planned",
            ),
            av,
            ["/protocolSection/armsInterventionsModule/armGroups"],
        ),
        coordinate(
            "calendar_span",
            semantics(
                "observation_time",
                "days",
                "study_calendar_start_to_primary_completion_not_participant_followup",
                "source_date_interval_difference",
                ds,
            ),
            dv,
            [
                "/protocolSection/statusModule/startDateStruct",
                "/protocolSection/statusModule/primaryCompletionDateStruct",
            ],
        ),
        coordinate(
            "randomization_declaration",
            semantics(
                "descriptor",
                "registry_declaration_indicator",
                "registry_randomized_assignment_declaration_not_verified_mechanism",
                "binary_registry_token",
                "planned",
            ),
            rv,
            ["/protocolSection/designModule/designInfo/allocation"],
        ),
    ]
    return {
        "record": {
            "record_id": nct,
            "study_id": nct,
            "population_scope": "registered cohort of "
            + nct
            + "; no population equivalence inferred",
            "coordinates": coords,
        },
        "enrollment_lifecycle": lifecycle,
        "duration_lifecycle": ds,
        "registry_last_update_date": status.get("lastUpdatePostDateStruct", {}).get("date"),
        "phase_tokens": design.get("phases", []),
        "phase_locator": "/protocolSection/designModule/phases",
        "phase_ordering": "categorical_descriptor_not_ordinal_capacity",
        "allocation_token": allocation,
    }


def verify_derived(study, raw):
    derived = derive_snapshot(
        raw, {"nct_id": study["record"]["record_id"], "raw_sha256": study["source_sha256"]}
    )
    # The complete record includes numeric/unknown/descriptor values, semantics,
    # cohort identity and exact locators, not merely its source hash.
    if any(study.get(key) != value for key, value in derived.items()):
        raise ValueError("snapshot_derived_coordinate_mismatch")
    return derived


def adapt_directory(manifest_path, cache, output):
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    entries = manifest["studies"]
    ids = [entry["nct_id"] for entry in entries]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("manifest_identity_count")
    studies = []
    for entry in entries:
        nct = entry["nct_id"]
        # Check before using the identity in a filesystem path.
        if not re.fullmatch(r"NCT\d{8}", nct):
            raise ValueError("snapshot_identity_format")
        uri = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
        if entry["source_uri"] != uri:
            raise ValueError("manifest_source_uri")
        derived = derive_snapshot((cache / (nct + ".json")).read_bytes(), entry)
        studies.append(
            {
                **derived,
                "stratum_id": entry.get("stratum_id"),
                "source_uri": uri,
                "source_sha256": entry["raw_sha256"],
                "retrieved_at": entry["retrieved_at"],
            }
        )
    packet = {
        "schema": "anibench.registry-native-architecture-inputs.v1",
        "snapshot_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "selection_frozen_at": manifest.get("selection_frozen_at"),
        "selection_rule": manifest.get("selection_rule"),
        "preregistration_sha256": manifest.get("preregistration_sha256"),
        "snapshot_freshness": "Frozen retrievals; no network query. Retrieval metadata supplied by manifest, not inferred from study bytes.",
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "studies": studies,
    }
    # Create only after all source checks succeed; never overwrite prior packets.
    with output.open("x") as handle:
        json.dump(packet, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return {"studies": len(studies), "source_hashes_verified": len(studies)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--snapshot-cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New aggregate input JSON file")
    args = parser.parse_args()
    print(json.dumps(adapt_directory(args.manifest, args.snapshot_cache, args.out), sort_keys=True))
