from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from anibench.cli import main
from anibench.collection_compare import METRICS, compare_collection_profiles
from anibench.collection_v1 import _digest, profile_collection

ROOT = Path(__file__).resolve().parents[1]


def record(name="a", *, complete=True):
    payload = json.loads((ROOT / "examples/collection/synthetic-record.json").read_text())
    payload["study_id"] = name
    payload["inventory_status"] = "complete" if complete else "partial"
    payload["acquisitions"] = [a for a in payload["acquisitions"] if a["quality_status"] == "pass"]
    return payload


def basis(metric="measured_participants"):
    value = json.loads((ROOT / "examples/collection/comparison-basis.json").read_text())
    value["metric"] = metric
    if metric.startswith("module_"):
        module = next(m for m in record()["modules"] if m["module_id"] == "proteomics")
        value["module_definition"] = {k: module[k] for k in ("domain", "target_unit", "target_definition_id")}
    else:
        del value["module_id"], value["module_definition"]
    return value


def profiles():
    return [profile_collection(record("a")), profile_collection(record("b"))]


def rehash(profile):
    profile["profile_sha256"] = _digest({k: v for k, v in profile.items() if k != "profile_sha256"})


def test_exact_ties_share_competition_rank_without_global_score():
    result = compare_collection_profiles(profiles(), basis())
    assert result["leaders"] == ["a", "b"]
    assert result["overall_score"] is None
    assert result["pairwise_relations"][0]["relation"] == "exact_tie"
    assert all(e["rank_min"] == e["rank_max"] == 1 for e in result["entries"])


def test_missing_people_remain_in_median_denominator():
    a = record("a")
    b = record("b")
    b["participant_ids"].extend(["synthetic-extra-a", "synthetic-extra-b"])
    result = compare_collection_profiles([profile_collection(a), profile_collection(b)], basis("module_median_targets"))
    assert result["entries"][0]["denominator"] == 4
    assert result["entries"][1]["denominator"] == 6
    assert result["entries"][0]["lower"] == result["entries"][1]["lower"] == 0


def test_partial_coverage_has_closed_bounds_and_no_manufactured_leader():
    a, b = record("a"), record("b", complete=False)
    b["acquisitions"] = b["acquisitions"][:1]
    result = compare_collection_profiles([profile_collection(a), profile_collection(b)], basis())
    assert result["leaders"] == []
    assert result["possible_leaders"] == ["a", "b"]
    assert result["pairwise_relations"][0]["relation"] == "unresolved_overlap"
    assert result["entries"][1]["upper"] == len(b["participant_ids"])


def test_definite_higher_count_and_transparent_corpus_rank():
    a, b, c = record("a"), record("b"), record("c")
    b["acquisitions"] = b["acquisitions"][:1]
    c["acquisitions"] = []
    result = compare_collection_profiles([profile_collection(v) for v in [c, a, b]], basis())
    assert result["leaders"] == ["a"]
    assert [(r["study_id"], r["rank_min"], r["rank_max"]) for r in result["entries"]] == [("a", 1, 1), ("b", 2, 2), ("c", 3, 3)]


def test_incomplete_conditional_span_is_not_a_lower_bound():
    values = [profile_collection(record("a")), profile_collection(record("b", complete=False))]
    result = compare_collection_profiles(values, basis("median_observed_span_days"))
    assert result["leaders"] == []
    b = result["entries"][1]
    assert b["lower"] == 0 and b["upper"] is None
    assert b["observed_conditional_value"] == 28


def test_unknown_times_do_not_manufacture_exact_repeat_or_event_count():
    a, b = record("a"), record("b")
    a["events"][0]["time_days"] = None
    values = [profile_collection(a), profile_collection(b)]
    for metric in ("repeated_participants", "median_observation_times", "module_participant_events", "module_target_observations"):
        r = compare_collection_profiles(values, basis(metric))
        assert r["entries"][0]["state"] == "bounded"
    assert compare_collection_profiles(values, basis("module_targets"))["entries"][0]["state"] == "exact"


def test_absent_module_is_not_a_zero_observation():
    a, b = record("a"), record("b")
    b["modules"] = [m for m in b["modules"] if m["module_id"] != "proteomics"]
    b["acquisitions"] = [r for r in b["acquisitions"] if r["module_id"] != "proteomics"]
    result = compare_collection_profiles([profile_collection(a), profile_collection(b)], basis("module_targets"))
    assert result["entries"][1]["upper"] is None
    assert result["entries"][1]["source_locator"] is None
    assert result["leaders"] == []


@pytest.mark.parametrize("change", ["hash", "implementation", "study_id", "record_basis", "time_resolution_days", "target_definition", "denominator"])
def test_incompatible_or_tampered_objects_rejected(change):
    values = profiles()
    if change == "hash":
        values[1]["population"]["roster_participants"] += 1
    else:
        if change == "implementation":
            values[1]["implementation"]["engine"] = "other"
        elif change == "study_id":
            values[1]["study_id"] = values[0]["study_id"]
        elif change == "record_basis":
            values[1]["record_basis"] = "planned"
        elif change == "time_resolution_days":
            values[1]["time_resolution_days"] = 0.1
        else:
            module = next(m for m in values[1]["modules"] if m["module_id"] == "proteomics")
            module["target_definition_id" if change == "target_definition" else "roster_denominator"] = "invalid"
        rehash(values[1])
    with pytest.raises(ValueError):
        compare_collection_profiles(values, basis("module_median_targets"))


@pytest.mark.parametrize("metric", METRICS)
def test_input_order_invariance_and_self_describing_metric_cards(metric):
    values = profiles()
    result = compare_collection_profiles(values, basis(metric))
    assert result == compare_collection_profiles(values[::-1], basis(metric))
    assert result["metric_card"]["metric"] == metric
    assert result["metric_card"]["overall_quality_direction"] is None


def test_boundary_touch_is_not_strict_ordering():
    values = profiles()
    values[1]["coverage_interpretation"] = "lower_bound"
    values[1]["population"]["participants_with_accepted_targets"] = 0
    values[1]["population"]["participants_with_two_or_more_times"] = 0
    values[0]["population"]["participants_with_accepted_targets"] = 4
    for value in values:
        rehash(value)
    result = compare_collection_profiles(values, basis())
    assert result["pairwise_relations"][0]["relation"] == "unresolved_overlap"
    # The exact count cannot be beaten, but the interval may tie it.
    assert result["leaders"] == ["a"]
    assert result["entries"][1]["rank_min"] == 1
    assert result["entries"][1]["rank_max"] == 2


def test_cli_accepts_aggregate_envelopes_and_protects_inputs(tmp_path, capsys):
    paths = []
    for i, profile in enumerate(profiles()):
        path = tmp_path / f"p{i}.json"
        path.write_text(json.dumps({"schema_version": "anibench.collection-table-evaluation.v1", "profile": profile}))
        paths.append(str(path))
    rules = tmp_path / "basis.json"
    rules.write_text(json.dumps(basis()))
    out = tmp_path / "comparison.json"
    assert main(["compare-records", *paths, "--basis", str(rules), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["leaders"] == ["a", "b"]
    original = rules.read_bytes()
    assert main(["compare-records", *paths, "--basis", str(rules), "--out", str(rules)]) == 2
    assert rules.read_bytes() == original
    assert "participant_id" not in out.read_text()


def test_malformed_basis_and_nonfinite_numbers_rejected():
    for invalid in ({}, {**basis(), "weight": 20}, {**basis(), "time_resolution_days": float("nan")}):
        with pytest.raises(ValueError):
            compare_collection_profiles(profiles(), invalid)
    values = deepcopy(profiles())
    values[0]["population"]["participants_with_accepted_targets"] = True
    rehash(values[0])
    with pytest.raises(ValueError):
        compare_collection_profiles(values, basis())


def test_possible_rank_bounds_cover_every_admissible_small_integer_world():
    from itertools import product

    values = profiles() + [profile_collection(record("c"))]
    for i, (lower, upper) in enumerate([(1, 2), (2, 2), (0, 4)]):
        values[i]["population"]["roster_participants"] = upper
        values[i]["population"]["participants_with_accepted_targets"] = lower
        values[i]["population"]["participants_with_two_or_more_times"] = min(
            values[i]["population"]["participants_with_two_or_more_times"], lower
        )
        values[i]["coverage_interpretation"] = "exact_supplied_inventory" if lower == upper else "lower_bound"
        rehash(values[i])
    result = compare_collection_profiles(values, basis())
    worlds = list(product(range(1, 3), [2], range(5)))
    for i, row in enumerate(result["entries"]):
        ranks = [1 + sum(x > world[i] for j, x in enumerate(world) if i != j) for world in worlds]
        assert row["rank_min"] == min(ranks)
        assert row["rank_max"] == max(ranks)


@pytest.mark.parametrize("metric", ["module_targets", "measured_participants"])
def test_rehashed_observed_targets_cannot_exceed_registry_for_any_selected_metric(metric):
    values = profiles()
    module = next(m for m in values[1]["modules"] if m["module_id"] == "proteomics")
    module["observed_target_count"] = module["registered_target_count"] + 1000
    rehash(values[1])
    with pytest.raises(ValueError, match="Observed targets exceed"):
        compare_collection_profiles(values, basis(metric))


@pytest.mark.parametrize("metric", ["repeated_participants", "module_targets"])
def test_rehashed_repeated_people_cannot_exceed_measured_people_for_any_metric(metric):
    values = profiles()
    values[1]["population"]["participants_with_accepted_targets"] = 1
    values[1]["population"]["participants_with_two_or_more_times"] = 2
    rehash(values[1])
    with pytest.raises(ValueError, match="participant counts are inconsistent"):
        compare_collection_profiles(values, basis(metric))


def test_rehashed_measured_people_cannot_exceed_roster_on_unrelated_metric():
    values = profiles()
    values[1]["population"]["participants_with_accepted_targets"] = 5
    rehash(values[1])
    with pytest.raises(ValueError, match="participant counts are inconsistent"):
        compare_collection_profiles(values, basis("module_targets"))


def test_valid_boundary_counts_remain_comparable():
    values = profiles()
    for value in values:
        population = value["population"]
        population["participants_with_two_or_more_times"] = population["participants_with_accepted_targets"]
        for module in value["modules"]:
            module["observed_target_count"] = module["registered_target_count"]
        rehash(value)
    # Equality is legitimate; these checks are not independent source validation.
    for metric in ["repeated_participants", "module_targets"]:
        result = compare_collection_profiles(values, basis(metric))
        assert result["leaders"] == ["a", "b"]
        assert result["review_status"] == "basis_declared_by_caller_not_independently_reviewed"
