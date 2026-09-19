# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Full lifecycle-cohort comparisons of frozen public registry aggregate coordinates."""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
from pathlib import Path

from adapter import verify_derived

from anibench.architecture_v1 import ArchitectureError, compare_architecture


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def make_request(studies, ids, directions, label):
    records = []
    semantics = {}
    for study in studies:
        original = study["record"]
        selected = [c for c in original["coordinates"] if c["coordinate_id"] in ids]
        for c in selected:
            key = c["coordinate_id"]
            if key in semantics and semantics[key] != c["semantics"]:
                raise ValueError("cohort_semantics_mismatch")
            semantics[key] = c["semantics"]
        records.append({**original, "coordinates": selected})
    return {
        "contract": "anibench.architecture-request.v1",
        "basis": {
            "basis_id": label,
            "population_comparison": {
                "mode": "quantity_only_preserve_each_population_scope",
                "rationale": "Compare registry-reported quantities; preserve every cohort scope. No population equivalence, source truth, treatment benefit or overall quality is inferred.",
            },
            "coordinates": [
                {"coordinate_id": key, "semantics": semantics[key], "direction": directions[key]}
                for key in ids
            ],
        },
        "records": records,
    }


def summarize(result):
    counts = collections.Counter(p["relation"] for p in result["pairwise_relations"])
    examples = []
    for kind in sorted(counts):
        examples.extend([p for p in result["pairwise_relations"] if p["relation"] == kind][:2])
    return {
        "record_ids": [r["record_id"] for r in result["entries"]],
        "record_count": len(result["entries"]),
        "pair_count": len(result["pairwise_relations"]),
        "basis_sha256": result["basis_sha256"],
        "request_sha256": result["request_sha256"],
        "result_sha256": result["receipt_sha256"],
        "implementation": result["implementation"],
        "pairwise_relation_counts": dict(counts),
        "illustrative_pairs": examples,
        "definitely_undominated_record_ids": result["definitely_undominated_record_ids"],
        "possibly_undominated_record_ids": result["possibly_undominated_record_ids"],
    }


def oracle(request, result):
    """Independent sign test on actual point coordinates, no imported Pareto helper."""
    records = {
        r["record_id"]: {c["coordinate_id"]: c for c in r["coordinates"]}
        for r in request["records"]
    }
    for pair in result["pairwise_relations"]:
        a, b = [records[k] for k in pair["record_ids"]]
        ids = ("enrollment", "arm_groups")
        blocked = any(
            r[k]["value"]["state"] == "unknown"
            or r[k]["semantics"]["collection_status"] == "reported_unspecified"
            for r in (a, b)
            for k in ids
        )
        if blocked:
            expected = "unresolved"
        else:
            delta = [a[k]["value"]["value"] - b[k]["value"]["value"] for k in ids]
            expected = (
                "first_dominates_selected_quantities"
                if min(delta) >= 0 and max(delta) > 0
                else "second_dominates_selected_quantities"
                if max(delta) <= 0 and min(delta) < 0
                else "exact_tie"
                if min(delta) == max(delta) == 0
                else "definite_tradeoff"
            )
        if expected != pair["relation"]:
            raise ValueError("independent_pair_oracle_mismatch")
    return len(result["pairwise_relations"])


def replay(inputs, out, snapshot_cache=None):
    data = json.loads(inputs.read_text())
    if data.get("schema") != "anibench.registry-native-architecture-inputs.v1":
        raise ValueError("input_schema")
    studies = data["studies"]
    ids = [s["record"]["record_id"] for s in studies]
    if len(ids) != 240 or len(set(ids)) != 240:
        raise ValueError("expected_240_unique_studies")
    verified = 0
    for study in studies:
        nct = study["record"]["record_id"]
        if not re.fullmatch(r"NCT\d{8}", nct) or study["record"]["study_id"] != nct:
            raise ValueError("study_identity")
        if study["source_uri"] != f"https://clinicaltrials.gov/api/v2/studies/{nct}":
            raise ValueError("source_identity")
        if not re.fullmatch(r"[a-f0-9]{64}", study["source_sha256"]):
            raise ValueError("source_hash")
        for c in study["record"]["coordinates"]:
            if any(s["source_sha256"] != "sha256:" + study["source_sha256"] for s in c["sources"]):
                raise ValueError("coordinate_source_binding")
        if snapshot_cache is not None:
            raw = (snapshot_cache / f"{nct}.json").read_bytes()
            if digest(raw) != study["source_sha256"]:
                raise ValueError("frozen_snapshot_hash_mismatch")
            verify_derived(study, raw)
            verified += 1
    # Complete all checks before creating outputs. Existing runs are immutable.
    out.mkdir(exist_ok=False)
    primary, calendar, probes = [], [], []
    observed = set()
    for lifecycle in ("collected", "planned", "reported_unspecified"):
        cohort = sorted(
            [s for s in studies if s["enrollment_lifecycle"] == lifecycle],
            key=lambda s: s["record"]["record_id"],
        )
        if not cohort:
            continue
        req = make_request(
            cohort,
            ["enrollment", "arm_groups", "randomization_declaration"],
            {
                "enrollment": "higher_quantity",
                "arm_groups": "higher_quantity",
                "randomization_declaration": "descriptor_only",
            },
            "full-enrollment-arm-cohort-" + lifecycle,
        )
        result = compare_architecture(req)
        checked = oracle(req, result)
        expected_pairs = len(cohort) * (len(cohort) - 1) // 2
        if checked != expected_pairs:
            raise ValueError("incomplete_within_cohort_pairs")
        observed.update(r["record"]["record_id"] for r in cohort)
        primary.append(
            {"lifecycle": lifecycle, **summarize(result), "independent_oracle_pairs": checked}
        )
        write(out / ("primary-" + lifecycle + ".input.json"), req)
        reverse = copy.deepcopy(req)
        reverse["records"].reverse()
        if compare_architecture(reverse)["pairwise_relations"] != result["pairwise_relations"]:
            raise ValueError("record_order_dependence")
        hidden = copy.deepcopy(req)
        for r in hidden["records"]:
            r["coordinates"] = [c for c in r["coordinates"] if c["coordinate_id"] != "enrollment"]
        hidden_result = compare_architecture(hidden)
        if (
            any(p["relation"] != "unresolved" for p in hidden_result["pairwise_relations"])
            or hidden_result["definitely_undominated_record_ids"]
        ):
            raise ValueError("withheld_enrollment_promoted")
        preference = copy.deepcopy(req)
        preference["basis"]["coordinates"][1]["direction"] = "lower_quantity"
        alternative = compare_architecture(preference)
        changed = sum(
            a["relation"] != b["relation"]
            for a, b in zip(result["pairwise_relations"], alternative["pairwise_relations"])
        )
        alias = copy.deepcopy(req)
        alias["basis"]["coordinates"].append(
            {**alias["basis"]["coordinates"][0], "coordinate_id": "enrollment_alias"}
        )
        try:
            compare_architecture(alias)
        except ArchitectureError:
            pass
        else:
            raise ValueError("semantic_alias_accepted")
        probes.append(
            {
                "lifecycle": lifecycle,
                "record_order_invariant": True,
                "withheld_enrollment_blocks_all_ordering": True,
                "semantic_alias_rejected": True,
                "arm_preference_reversal_changed_pairs": changed,
            }
        )
    if len(observed) != 240:
        raise ValueError("enrollment_cohort_partition_incomplete")
    for lifecycle in ("collected", "planned", "reported_unspecified"):
        cohort = sorted(
            [s for s in studies if s["duration_lifecycle"] == lifecycle],
            key=lambda s: s["record"]["record_id"],
        )
        if not cohort:
            continue
        req = make_request(
            cohort,
            ["calendar_span"],
            {"calendar_span": "higher_quantity"},
            "full-calendar-scope-" + lifecycle,
        )
        result = compare_architecture(req)
        if len(result["pairwise_relations"]) != len(cohort) * (len(cohort) - 1) // 2:
            raise ValueError("incomplete_calendar_cohort_pairs")
        calendar.append({"lifecycle": lifecycle, **summarize(result)})
        write(out / ("calendar-" + lifecycle + ".input.json"), req)
    total = collections.Counter()
    for row in primary:
        total.update(row["pairwise_relation_counts"])
    report = {
        "schema": "anibench.registry-native-architecture-replay.v1",
        "inputs_sha256": digest(inputs.read_bytes()),
        "replay_script_sha256": digest(Path(__file__).read_bytes()),
        "source_manifest_sha256": data["snapshot_manifest_sha256"],
        "frozen_snapshot_hash_verification": {
            "state": "verified" if verified == 240 else "not_requested",
            "count": verified,
        },
        "snapshot_coordinate_rederivation": {
            "state": "verified" if verified == 240 else "not_requested",
            "count": verified,
            "adapter_sha256": digest(Path(__file__).with_name("adapter.py").read_bytes()),
        },
        "actual_registry_studies": 240,
        "snapshot_retrieval_range": [
            min(s["retrieved_at"] for s in studies),
            max(s["retrieved_at"] for s in studies),
        ],
        "primary_cohorts": primary,
        "calendar_cohorts": calendar,
        "primary_pairwise_relation_counts": dict(total),
        "primary_pairs": sum(total.values()),
        "behavior_probes": probes,
        "scope": "Complete within-lifecycle quantity comparisons across this frozen 240-study corpus. Lifecycle cohorts are not mutually exchangeable; there is no cross-lifecycle or overall-biology ranking.",
        "limitations": [
            "Registry-reported source quantities, not verified study execution, participant linkage or information matrices.",
            "No phase ordinal score; randomization is a descriptor-only registry token.",
            "Calendar span is study-level, not individual follow-up.",
            "Direction choices are explicit preferences, not biological quality judgments.",
            "Optional snapshot checks verify bytes, identity and exact source-derived coordinates, not clinical truth or manifest-supplied retrieval metadata.",
            "Query-selected corpus is not a representative sample of all studies. No network refresh occurs.",
        ],
    }
    write(out / "results.json", report)
    return {
        "actual_studies": 240,
        "primary_pairs": report["primary_pairs"],
        "primary_cohort_sizes": [r["record_count"] for r in primary],
        "calendar_pairs": sum(r["pair_count"] for r in calendar),
        "source_snapshots_verified": verified,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=Path(__file__).with_name("inputs.json"))
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument(
        "--snapshot-cache",
        type=Path,
        help="Optional exact frozen NCTxxxxxxxx.json files; no downloads",
    )
    args = parser.parse_args()
    print(json.dumps(replay(args.inputs, args.out, args.snapshot_cache), sort_keys=True))
