from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from anibench.cli import main
from anibench.collection_v1 import CollectionError, profile_collection

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/collection/synthetic-record.json"


def record() -> dict:
    return json.loads(EXAMPLE.read_text())


def without_hashes(profile: dict) -> dict:
    return {key: value for key, value in profile.items() if not key.endswith("sha256")}


def test_roster_denominators_and_linkage_do_not_imply_uniform_assay_coverage():
    result = profile_collection(record())
    assert result["population"] == {
        "roster_participants": 4,
        "participants_with_accepted_targets": 3,
        "participants_with_two_or_more_times": 1,
    }
    proteins = next(row for row in result["modules"] if row["module_id"] == "proteomics")
    assert proteins["people_with_accepted_targets"] == 1
    assert proteins["targets_per_participant"]["median"] == 0
    assert proteins["target_observations"] == 6
    assert proteins["observed_target_count"] == 3
    pair = next(row for row in result["joint_coverage"] if row["module_ids"] == ["function", "proteomics"])
    assert pair["people_with_both_modules_at_any_time"] == 1
    assert pair["people_with_both_modules_at_same_event"] == 1
    assert pair["participant_events_with_both_modules"] == 1
    assert result["longitudinal"]["span_days_among_repeated_participants"]["median"] == 28


def test_output_contains_no_participant_identity_or_measurement_values(tmp_path, capsys):
    path = tmp_path / "profile.json"
    assert main(["profile", str(EXAMPLE), "--out", str(path)]) == 0
    rendered = path.read_text() + capsys.readouterr().out
    assert all(person not in rendered for person in record()["participant_ids"])
    result = json.loads(path.read_text())
    assert result["biological_information"]["state"] == "not_estimated"
    assert result["overall_score"] is None


def test_qc_unknown_and_partial_inventory_are_not_proof_of_absence():
    incomplete = record()
    assert profile_collection(incomplete)["coverage_interpretation"] == "lower_bound"
    incomplete["inventory_status"] = "complete"
    assert profile_collection(incomplete)["coverage_interpretation"] == "lower_bound"
    for row in incomplete["acquisitions"]:
        if row["quality_status"] == "unknown":
            row["quality_status"] = "fail"
    assert profile_collection(incomplete)["coverage_interpretation"] == "exact_supplied_inventory"


def test_reordering_does_not_change_profile_numbers():
    original = record()
    shuffled = deepcopy(original)
    for field in ("participant_ids", "modules", "events", "acquisitions"):
        shuffled[field].reverse()
    assert without_hashes(profile_collection(original)) == without_hashes(profile_collection(shuffled))


def test_duplicate_acquisition_lineage_does_not_add_coverage():
    original = record()
    repeated = deepcopy(original)
    repeated["acquisitions"].append(deepcopy(repeated["acquisitions"][0]))
    baseline = profile_collection(original)
    result = profile_collection(repeated)
    for field in ("modules", "joint_coverage", "longitudinal", "population"):
        assert result[field] == baseline[field]
    assert result["acquisition_audit"]["identical_repeated_rows_removed"] == 1
    repeated["acquisitions"][-1]["quality_status"] = "fail"
    with pytest.raises(CollectionError, match="conflicts"):
        profile_collection(repeated)


def test_event_aliases_and_technical_repeats_cannot_inflate_time_or_targets():
    original = record()
    aliased = deepcopy(original)
    first_event = aliased["events"][0]
    aliased["events"].append({**first_event, "event_id": "alias"})
    aliased["acquisitions"].append({
        **aliased["acquisitions"][0], "acquisition_id": "technical-repeat", "event_id": "alias",
    })
    baseline = profile_collection(original)
    result = profile_collection(aliased)
    for field in ("modules", "joint_coverage", "longitudinal", "population"):
        assert result[field] == baseline[field]


def test_planned_and_collected_support_are_distinct_but_same_counting_rule():
    collected = record()
    collected["acquisitions"] = [r for r in collected["acquisitions"] if r["quality_status"] == "pass"]
    planned = deepcopy(collected)
    planned["record_basis"] = "planned"
    for row in planned["acquisitions"]:
        row["quality_status"] = "planned"
    for key in ("population", "modules", "joint_coverage", "longitudinal"):
        assert profile_collection(collected)[key] == profile_collection(planned)[key]
    planned["acquisitions"][0]["quality_status"] = "pass"
    with pytest.raises(CollectionError, match="cannot share"):
        profile_collection(planned)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_nonfinite_or_boolean_event_times_are_rejected(value):
    payload = record()
    payload["events"][0]["time_days"] = value
    with pytest.raises(CollectionError):
        profile_collection(payload)


def test_outcome_results_are_not_capacity_inputs():
    payload = record()
    payload["rejuvenation_years"] = 5
    with pytest.raises(CollectionError, match="Invalid collection"):
        profile_collection(payload)


def test_missing_dates_preserve_measurement_coverage_without_inventing_followup():
    payload = record()
    for event in payload["events"]:
        event["time_days"] = None
    result = profile_collection(payload)
    assert result["population"]["participants_with_accepted_targets"] == 3
    assert result["population"]["participants_with_two_or_more_times"] == 0
    assert result["longitudinal"]["span_days_among_repeated_participants"]["median"] is None
    assert result["longitudinal"]["events_with_unknown_time"] == 4


def test_invalid_linkage_errors_do_not_echo_private_identifiers():
    payload = record()
    private_label = "private-participant-name-that-must-not-be-logged"
    payload["acquisitions"][0]["participant_id"] = private_label
    with pytest.raises(CollectionError) as error:
        profile_collection(payload)
    assert private_label not in str(error.value)

def test_public_fixture_exception_is_bound_to_exact_reviewed_bytes():
    from pathlib import Path

    from anibench.release.redact import _structured_findings

    path = "examples/collection/synthetic-record.json"
    body = (Path(__file__).resolve().parents[1] / path).read_text()
    assert not _structured_findings(path, body, ".json")
    edited = body.replace("synthetic-person-1", "undisclosed-participant")
    assert any(f.rule_id == "participant_id_field" for f in _structured_findings(path, edited, ".json"))
    assert any(f.rule_id == "participant_id_field" for f in _structured_findings("record.json", body, ".json"))


def test_reusable_target_sets_are_lossless_and_lineage_dedup_ignores_encoding():
    plain = record()
    compact = deepcopy(plain)
    compact["target_sets"] = []
    for index, row in enumerate(compact["acquisitions"]):
        set_id = f"set-{index}"
        compact["target_sets"].append({
            "target_set_id": set_id, "module_id": row["module_id"],
            "target_ids": row.pop("target_ids"),
        })
        row["target_set_id"] = set_id
    assert without_hashes(profile_collection(compact)) == without_hashes(profile_collection(plain))
    compact["acquisitions"].append(deepcopy(plain["acquisitions"][0]))
    result = profile_collection(compact)
    assert result["acquisition_audit"]["identical_repeated_rows_removed"] == 1
    assert result["modules"] == profile_collection(plain)["modules"]


@pytest.mark.parametrize("failure", ["unknown", "cross_module", "both_encodings", "duplicate_set"])
def test_reusable_target_sets_fail_closed(failure):
    manifest = record()
    row = manifest["acquisitions"][0]
    manifest["target_sets"] = [{"target_set_id": "set-a", "module_id": row["module_id"],
                                "target_ids": row.pop("target_ids")}]
    row["target_set_id"] = "set-a"
    if failure == "unknown":
        row["target_set_id"] = "missing"
    elif failure == "cross_module":
        row["module_id"] = "function"
    elif failure == "both_encodings":
        row["target_ids"] = []
    else:
        manifest["target_sets"].append(deepcopy(manifest["target_sets"][0]))
    with pytest.raises(CollectionError):
        profile_collection(manifest)
