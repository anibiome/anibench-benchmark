#!/usr/bin/env python3
"""Stress-test AniBench intake and sparse design compilation on 50 live trials.

This is deliberately not a registry-to-score shortcut. ClinicalTrials.gov is
used to prove that heterogeneous public records can be locked, source-located,
and passed through the typed design front door without inventing measurement
operators, longitudinal geometry, causal contrasts, or biological information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from anibench.design_v2 import compile_design
from anibench.intake import (
    IntakeSnapshot,
    snapshot_clinicaltrials_search,
    snapshot_clinicaltrials_study,
)


CONTRACT = "anibench.ctgov-heterogeneous-trial-stress-test.v1"
CTGOV_VERSION_URL = "https://clinicaltrials.gov/api/v2/version"
DEFAULT_OUTPUT = Path("docs/audits/CTGOV_50_TRIAL_STRESS_TEST_2026-07-14.json")
PER_STRATUM = 5
QUERY_PAGE_SIZE = 50

QUERY_STRATA: tuple[tuple[str, str], ...] = (
    (
        "healthy-aging-multiomics",
        'AREA[StudyType]INTERVENTIONAL AND (multiomics OR "multi-omics" OR proteomics OR metabolomics) AND aging',
    ),
    (
        "precision-oncology-genomic",
        'AREA[StudyType]INTERVENTIONAL AND ("precision oncology" OR genomic) AND cancer',
    ),
    ("vaccine", "AREA[StudyType]INTERVENTIONAL AND vaccine"),
    ("exercise", "AREA[StudyType]INTERVENTIONAL AND exercise"),
    (
        "nutrition-microbiome",
        "AREA[StudyType]INTERVENTIONAL AND (nutrition OR diet) AND microbiome",
    ),
    (
        "digital-wearable",
        'AREA[StudyType]INTERVENTIONAL AND (wearable OR "digital health")',
    ),
    ("gene-therapy", 'AREA[StudyType]INTERVENTIONAL AND "gene therapy"'),
    (
        "cell-therapy",
        'AREA[StudyType]INTERVENTIONAL AND ("cell therapy" OR "CAR-T")',
    ),
    (
        "micro-randomized",
        'AREA[StudyType]INTERVENTIONAL AND ("micro-randomized" OR microrandomized)',
    ),
    (
        "smart-adaptive",
        'AREA[StudyType]INTERVENTIONAL AND ("sequential multiple assignment" OR "SMART trial")',
    ),
)

FIELD_POINTERS = {
    "nct_id": "/protocolSection/identificationModule/nctId",
    "brief_title": "/protocolSection/identificationModule/briefTitle",
    "study_type": "/protocolSection/designModule/studyType",
    "overall_status": "/protocolSection/statusModule/overallStatus",
    "phases": "/protocolSection/designModule/phases",
    "enrollment_count": "/protocolSection/designModule/enrollmentInfo/count",
    "enrollment_type": "/protocolSection/designModule/enrollmentInfo/type",
    "allocation": "/protocolSection/designModule/designInfo/allocation",
    "intervention_model": "/protocolSection/designModule/designInfo/interventionModel",
    "masking": "/protocolSection/designModule/designInfo/maskingInfo/masking",
}

COUNT_POINTERS = {
    "arm_count": "/protocolSection/armsInterventionsModule/armGroups",
    "intervention_count": "/protocolSection/armsInterventionsModule/interventions",
    "outcome_count": "/protocolSection/outcomesModule/outcomes",
    "location_count": "/protocolSection/contactsLocationsModule/locations",
}


class StressTestError(RuntimeError):
    """Raised when the live corpus violates the fail-closed audit contract."""


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_sha256(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise StressTestError(f"JSON pointer must be absolute: {pointer!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def pointer_value(document: Any, pointer: str) -> tuple[bool, Any]:
    current = document
    for part in _pointer_parts(pointer):
        if isinstance(current, Mapping):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                index = int(part)
            except ValueError:
                return False, None
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current


def _source_binding(snapshot: IntakeSnapshot, pointer: str, *, derivation: str) -> dict[str, Any]:
    return {
        "source_uri": snapshot.source_uri,
        "source_sha256": snapshot.raw_content_sha256,
        "json_pointer": pointer,
        "derivation": derivation,
    }


def _field(snapshot: IntakeSnapshot, pointer: str) -> dict[str, Any]:
    exists, value = pointer_value(snapshot.parsed_content, pointer)
    return {
        "value": value if exists else None,
        "state": "exact" if exists and value is not None else "unknown",
        "binding": _source_binding(snapshot, pointer, derivation="json_pointer_identity"),
    }


def _array_count(snapshot: IntakeSnapshot, pointer: str) -> dict[str, Any]:
    exists, value = pointer_value(snapshot.parsed_content, pointer)
    valid = exists and isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )
    return {
        "value": len(value) if valid else None,
        "state": "exact" if valid else "unknown",
        "binding": _source_binding(snapshot, pointer, derivation="len(json_pointer_array)"),
    }


def extract_registry_record(snapshot: IntakeSnapshot) -> dict[str, Any]:
    if snapshot.source_kind != "clinicaltrials_gov_v2_study":
        raise StressTestError("Expected one ClinicalTrials.gov v2 study snapshot")
    fields = {name: _field(snapshot, pointer) for name, pointer in FIELD_POINTERS.items()}
    fields.update({name: _array_count(snapshot, pointer) for name, pointer in COUNT_POINTERS.items()})
    return {
        "source_object": {
            "source_uri": snapshot.source_uri,
            "retrieved_at": snapshot.retrieved_at,
            "raw_content_sha256": snapshot.raw_content_sha256,
            "raw_content_bytes": snapshot.raw_content_bytes,
            "source_locator_count": len(snapshot.source_locators),
            "source_locator_count_derivation": "len(intake_snapshot.source_locators)",
        },
        "fields": fields,
    }


def sparse_design_input(record: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = record["fields"]
    nct_id = fields["nct_id"]["value"]
    title = fields["brief_title"]["value"]
    if not isinstance(nct_id, str) or not isinstance(title, str) or not title.strip():
        raise StressTestError("Registry record is missing its NCT identifier or brief title")

    enrollment_count = fields["enrollment_count"]["value"]
    enrollment_type = fields["enrollment_type"]["value"]
    if (
        isinstance(enrollment_count, bool)
        or not isinstance(enrollment_count, int)
        or enrollment_count < 1
    ):
        population = {"value": None, "state": "unknown", "semantics": "registry_enrollment"}
    elif enrollment_type == "ACTUAL":
        population = {
            "value": enrollment_count,
            "state": "exact",
            "semantics": "registry_actual_enrollment",
        }
    elif enrollment_type == "ESTIMATED":
        population = {
            "value": enrollment_count,
            "state": "conditional",
            "semantics": "registry_estimated_enrollment",
        }
    else:
        population = {"value": None, "state": "unknown", "semantics": "registry_enrollment"}

    arms = fields["arm_count"]["value"]
    policy_arms = (
        arms
        if isinstance(arms, int) and not isinstance(arms, bool) and arms >= 1
        else None
    )
    allocation = fields["allocation"]["value"]
    randomization_note = "allocation_not_promoted_to_randomization"
    if allocation == "RANDOMIZED" and policy_arms is not None and policy_arms >= 2:
        randomized_policy: bool | None = True
        randomization_note = "RANDOMIZED plus at least two source-counted arm groups"
    elif allocation == "NON_RANDOMIZED":
        randomized_policy = False
        randomization_note = "NON_RANDOMIZED registry allocation"
    else:
        randomized_policy = None

    payload = {
        "contract": "anibench.design-input.v2-candidate1",
        "study_id": nct_id,
        "name": title,
        "assessment_lane": "registered",
        "population": population,
        "duration": {"value": None, "state": "unknown", "semantics": "registry_duration"},
        "policy_arms": policy_arms,
        "randomized_policy": randomized_policy,
        "concurrent_control": None,
        "adaptive_reassignment": None,
        "within_policy_randomized": None,
        "operator_families": [],
        "measurement_modules": [
            {
                "module_id": "registry-measurement-geometry-unresolved",
                "label": "Registry outcomes require source review before biological encoding",
                "evidence_state": "unknown",
                "events_per_participant": None,
            }
        ],
    }
    mapping = {
        "population": {
            "source_fields": ["enrollment_count", "enrollment_type"],
            "derivation": "actual->exact; estimated->conditional; otherwise unknown",
        },
        "policy_arms": {
            "source_fields": ["arm_count"],
            "derivation": "len(armGroups) when the array exists; otherwise unknown",
        },
        "randomized_policy": {
            "source_fields": ["allocation", "arm_count"],
            "derivation": randomization_note,
        },
        "duration": "not_inferred_from_registry_calendar_dates",
        "concurrent_control": "not_inferred_from_arm_labels",
        "adaptive_reassignment": "not_inferred_from_intervention_model",
        "within_policy_randomized": "not_inferred_from_intervention_model",
        "operator_families": "not_inferred_from_intervention_menu",
        "measurement_modules": "not_inferred_from outcome names or counts",
    }
    return payload, mapping


def _compiler_probe(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = compile_design(payload)
    required_false = {
        "composite_coordinate_emitted",
        "ordinal_position_emitted",
        "biological_information_inference_emitted",
        "missing_value_imputation_used",
    }
    for field in required_false:
        if result["emission_policy"].get(field) is not False:
            raise StressTestError(f"Sparse compiler emitted forbidden state: {field}")
    if result["promotion_allowed"] is not False or not result["open_gates"]:
        raise StressTestError("Sparse registry input did not remain promotion-gated")
    return {
        "passed": True,
        "input_sha256": result["input_sha256"],
        "output_contract": result["contract"],
        "promotion_allowed": result["promotion_allowed"],
        "open_gate_ids": [gate["gate_id"] for gate in result["open_gates"]],
        "emission_policy": result["emission_policy"],
    }


def audit_study_snapshot(
    snapshot: IntakeSnapshot,
    *,
    expected_nct_id: str,
    stratum_id: str,
    search_source: Mapping[str, Any],
) -> dict[str, Any]:
    record = extract_registry_record(snapshot)
    fields = record["fields"]
    actual_nct_id = fields["nct_id"]["value"]
    identity_match = actual_nct_id == expected_nct_id
    interventional = fields["study_type"]["value"] == "INTERVENTIONAL"
    if not identity_match:
        raise StressTestError(f"Exact-study identity mismatch: {expected_nct_id} != {actual_nct_id}")
    if not interventional:
        raise StressTestError(f"Search stratum returned a non-interventional study: {actual_nct_id}")
    payload, mapping = sparse_design_input(record)
    compiler_probe = _compiler_probe(payload)
    return {
        "nct_id": actual_nct_id,
        "stratum_id": stratum_id,
        "identity_match": identity_match,
        "study_type_interventional": interventional,
        "intake_score_eligible": snapshot.score_eligible,
        "intake_requires_human_review": snapshot.requires_human_review,
        "source_object": record["source_object"],
        "search_source": dict(search_source),
        "fields": fields,
        "registry_to_sparse_design_mapping": mapping,
        "compiler_probe": compiler_probe,
        "passed": identity_match
        and interventional
        and snapshot.score_eligible is False
        and snapshot.requires_human_review is True
        and compiler_probe["passed"],
    }


def _fetch_ctgov_version() -> dict[str, Any]:
    request = Request(
        CTGOV_VERSION_URL,
        headers={"Accept": "application/json", "User-Agent": "AniBench-50-trial-audit/1"},
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read(100_001)
    if len(raw) > 100_000:
        raise StressTestError("ClinicalTrials.gov version object exceeded the audit cap")
    payload = json.loads(raw)
    if (
        not isinstance(payload, dict)
        or not payload.get("apiVersion")
        or not payload.get("dataTimestamp")
    ):
        raise StressTestError("ClinicalTrials.gov version object is incomplete")
    return {
        "source_uri": CTGOV_VERSION_URL,
        "raw_content_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_content_bytes": len(raw),
        "api_version": payload["apiVersion"],
        "data_timestamp": payload["dataTimestamp"],
    }


def _study_ids(search_snapshot: IntakeSnapshot) -> list[str]:
    exists, studies = pointer_value(search_snapshot.parsed_content, "/studies")
    if not exists or not isinstance(studies, Sequence):
        raise StressTestError("ClinicalTrials.gov search response has no studies array")
    identifiers: list[str] = []
    for study in studies:
        exists, nct_id = pointer_value(study, "/protocolSection/identificationModule/nctId")
        if exists and isinstance(nct_id, str):
            identifiers.append(nct_id)
    return identifiers


def _counter(records: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    values = [record["fields"][field]["value"] for record in records]
    normalized = ["UNKNOWN" if value is None else str(value) for value in values]
    return dict(sorted(Counter(normalized).items()))


def run_live_stress_test(*, per_stratum: int = PER_STRATUM) -> dict[str, Any]:
    if per_stratum < 1:
        raise StressTestError("per_stratum must be positive")
    expected_total = per_stratum * len(QUERY_STRATA)
    selected: set[str] = set()
    audited: list[dict[str, Any]] = []
    search_receipts: list[dict[str, Any]] = []
    for stratum_id, query in QUERY_STRATA:
        search = snapshot_clinicaltrials_search(query, page_size=QUERY_PAGE_SIZE)
        candidates = [nct_id for nct_id in _study_ids(search) if nct_id not in selected]
        chosen = candidates[:per_stratum]
        if len(chosen) != per_stratum:
            raise StressTestError(
                f"Stratum {stratum_id!r} yielded only {len(chosen)} unique studies; "
                f"need {per_stratum}"
            )
        search_source = {
            "source_uri": search.source_uri,
            "retrieved_at": search.retrieved_at,
            "raw_content_sha256": search.raw_content_sha256,
            "raw_content_bytes": search.raw_content_bytes,
            "selection_derivation": (
                "first globally unique NCT identifiers in exact API response order"
            ),
            "selected_nct_ids": chosen,
        }
        search_receipts.append({"stratum_id": stratum_id, "query": query, **search_source})
        for nct_id in chosen:
            selected.add(nct_id)
            audited.append(
                audit_study_snapshot(
                    snapshot_clinicaltrials_study(nct_id),
                    expected_nct_id=nct_id,
                    stratum_id=stratum_id,
                    search_source={
                        "source_uri": search.source_uri,
                        "raw_content_sha256": search.raw_content_sha256,
                    },
                )
            )

    passed = (
        len(audited) == expected_total
        and len(selected) == expected_total
        and all(record["passed"] for record in audited)
    )
    report: dict[str, Any] = {
        "contract": CONTRACT,
        "generated_at": _now_utc(),
        "evidence_class": "live_source_bound_structural_stress_test",
        "purpose": (
            "Validate heterogeneous registry intake and typed sparse compilation; "
            "never infer biological geometry or trial rank from registry prose."
        ),
        "ctgov_version_source": _fetch_ctgov_version(),
        "selection": {
            "stratum_count": len(QUERY_STRATA),
            "per_stratum": per_stratum,
            "expected_unique_trials": expected_total,
            "query_page_size": QUERY_PAGE_SIZE,
            "search_receipts": search_receipts,
        },
        "aggregate": {
            "unique_trial_count": len(selected),
            "passed_trial_count": sum(record["passed"] for record in audited),
            "failed_trial_count": sum(not record["passed"] for record in audited),
            "status_counts": _counter(audited, "overall_status"),
            "allocation_counts": _counter(audited, "allocation"),
            "intervention_model_counts": _counter(audited, "intervention_model"),
            "enrollment_type_counts": _counter(audited, "enrollment_type"),
            "derivations": {
                "unique_trial_count": "len(set(trials[*].nct_id))",
                "passed_trial_count": "sum(trials[*].passed == true)",
                "failed_trial_count": "sum(trials[*].passed == false)",
                "categorical_counts": (
                    "Counter(trials[*].fields[field].value; null -> UNKNOWN)"
                ),
            },
        },
        "invariants": {
            "registry_records_auto_scored": False,
            "overall_scalar_emitted": False,
            "ordinal_rank_emitted": False,
            "measurement_geometry_inferred_from_outcome_names": False,
            "operator_geometry_inferred_from_intervention_names": False,
            "calendar_span_used_as_intervention_duration": False,
            "unknown_converted_to_zero": False,
            "all_exact_study_identities_matched": all(
                record["identity_match"] for record in audited
            ),
            "all_sparse_compiler_probes_passed": all(
                record["compiler_probe"]["passed"] for record in audited
            ),
        },
        "trials": audited,
        "passed": passed,
    }
    report["report_payload_sha256"] = _json_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--per-stratum", type=int, default=PER_STRATUM)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = run_live_stress_test(per_stratum=args.per_stratum)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "output": str(args.out),
                "report_payload_sha256": report["report_payload_sha256"],
                "unique_trial_count": report["aggregate"]["unique_trial_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
