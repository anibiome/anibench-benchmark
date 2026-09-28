"""Public integration and small independent scientific regressions."""

import copy
import hashlib
import json
from importlib.resources import files
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from anibench import cli
from anibench.study_capability_candidate import charts, entrypoint, linked_workload, study_profile
from anibench.study_capability_candidate import compiler as c
from anibench.study_capability_candidate.sufficient_statistics import reduce_events

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/study_capability_candidate/minimal.json"


def example():
    return json.loads(EXAMPLE.read_text())


def test_example_source_binding_schema_and_semantics():
    design = example()
    assert (
        design["source_sha256"]
        == "sha256:" + hashlib.sha256(EXAMPLE.with_name("README.md").read_bytes()).hexdigest()
    )
    schema = json.loads(files(c.__package__).joinpath("design.schema.json").read_text())
    Draft202012Validator(schema).validate(design)
    assert entrypoint.load_input(design) == (design, None)
    assert design["lifecycle"] == "hypothetical"


def test_validation_cli_has_no_files_or_evaluation(tmp_path, monkeypatch, capsys):
    def unexpected(*args, **kwargs):
        raise AssertionError("Validation must not execute the numerical experiment")

    monkeypatch.setattr(study_profile, "evaluate", unexpected)
    monkeypatch.setattr(entrypoint, "evaluate", unexpected)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["study-capability", str(EXAMPLE), "--validate-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["valid"] is True
    assert report["study_profile"] == "native36-capability-v3"
    assert list(tmp_path.iterdir()) == []


def test_export_requires_new_directory(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        entrypoint.main([str(EXAMPLE), "--out", str(tmp_path)])
    assert error.value.code == 2
    assert "already exists" in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        entrypoint.main([str(EXAMPLE)])
    assert error.value.code == 2
    assert "--out is required" in capsys.readouterr().err


def test_cli_chart_forwards_scenario_and_independent_filters(monkeypatch):
    seen = []
    monkeypatch.setattr(charts, "main", lambda args: seen.append(args))
    assert (
        cli.main(
            [
                "study-chart",
                "comparison.json",
                "--out",
                "new",
                "--scenario",
                "q1",
                "--published-only",
                "--irb-only",
            ]
        )
        == 0
    )
    assert seen == [
        [
            "comparison.json",
            "--out",
            "new",
            "--scenario",
            "q1",
            "--published-only",
            "--irb-only",
        ]
    ]


def test_correlated_repeats_and_duplicate_identity():
    panel = next(p for p in c.registry()["panels"] if p["id"] == "physical_function")
    events = [
        {"coordinate": "systolic", "physical_id": str(i), "session_id": "one", "time": 0}
        for i in range(2)
    ]
    group = {"events": events}
    H, R, *_ = c.event_model(panel, group, q=2)
    info = c.fisher(H, R)
    # Mean variance is 2*(.25 + .75/2)=1.25, not 2/2=1.
    expected = np.zeros_like(info)
    expected[6, 6] = 1 / 1.25
    np.testing.assert_allclose(info, expected, atol=1e-12)
    duplicated = {"events": events + copy.deepcopy(events)}
    h, r, *_ = c.event_model(panel, duplicated, q=2)
    np.testing.assert_allclose(c.fisher(h, r), expected, atol=1e-12)
    independent = copy.deepcopy(events)
    independent[1]["session_id"] = "two"
    h, r, *_ = c.event_model(panel, {"events": independent}, q=2)
    expected[6, 6] = 1
    np.testing.assert_allclose(c.fisher(h, r), expected, atol=1e-12)


def test_reducer_does_not_erase_unknown_or_cross_time_errors():
    e = [
        {"coordinate": "x", "physical_id": "a", "session_id": "one", "time": 0},
        {"coordinate": "x", "physical_id": "b", "session_id": "one", "time": 1},
    ]
    assert reduce_events(e) is None
    e[1]["time"] = 0
    e[1]["session_id"] = None
    assert reduce_events(e) is None


def test_old_neural_observable_is_not_an_alias():
    design = example()
    design["panels"]["evoked_neural"] = {
        "status": "present",
        "operator_qualified": True,
        "time_frame": {"unit": "days", "origin": "registered_baseline", "source_qualified": True},
        "coordinate_status": {"p3b": "unknown", "n170": "present"},
        "groups": [],
    }
    with pytest.raises(ValueError, match="Explicit status"):
        linked_workload.validate_raw(design)
    panel = next(p for p in c.registry()["panels"] if p["id"] == "evoked_neural")
    n170 = panel["coordinates"][1]
    assert n170["id"] == "n170_face_car_po8_mean110_150"
    assert n170["native_observable"]["electrode"] == "PO8"
    assert n170["native_observable"]["window_ms"] == [110, 150]
    assert n170["native_observable"]["baseline_ms"] == [-200, 0]


def test_omitted_geometry_and_known_absence_are_distinct():
    design = example()
    design["panels"]["physical_function"]["groups"][0]["events"][0]["time"] = None
    assert (
        entrypoint.load_input(design)[0]["panels"]["physical_function"]["groups"][0]["events"][0][
            "time"
        ]
        is None
    )
    design["panels"]["physical_function"]["coordinate_status"]["grip"] = "absent"
    with pytest.raises(ValueError, match="Events require"):
        linked_workload.validate_raw(design)


@pytest.mark.parametrize("resolution", ["standard", "fine"])
@pytest.mark.parametrize("noise", ["normative", "common-noise-grid-v1"])
def test_corrected_frozen_profiles_and_old_certificate_rejection(resolution, noise):
    profile = study_profile.profile(resolution, noise)
    path = files(c.__package__).joinpath(f"CAPABILITY_V3.{resolution}.{noise}.profile.json")
    assert json.loads(path.read_text()) == profile
    assert len(profile["targets"]) == 1065
    old = copy.deepcopy(profile)
    old["profile_id"] = old["profile_id"].replace("capability-v3", "capability-v2")
    with pytest.raises(ValueError, match="Unregistered hybrid reference"):
        study_profile.decide({}, [], old)
    with pytest.raises(ValueError, match="Hybrid result/reference mismatch"):
        study_profile.decide({}, [], profile)
    with pytest.raises(ValueError, match="Unsupported explicit study profile"):
        charts.registered_basis({"study_profile": "native36-capability-v2"})


def test_fine_keeps_targets_and_tightens_resolution():
    standard = study_profile.profile("standard")
    fine = study_profile.profile("fine")
    assert [t["canonical_id"] for t in standard["targets"]] == [
        t["canonical_id"] for t in fine["targets"]
    ]
    assert standard["budget"] == fine["budget"]
    for left, right in zip(standard["temporal_rules"], fine["temporal_rules"]):
        assert left["alpha"] == right["alpha"] == 0.5
        np.testing.assert_allclose(np.array(left["variance_limits"]) / 4, right["variance_limits"])
    for left, right in zip(standard["randomized_window_rules"], fine["randomized_window_rules"]):
        assert right["criterion_se_reference_scale"] == left["criterion_se_reference_scale"] / 2


def scalar_roster():
    panel = copy.deepcopy(next(p for p in c.registry()["panels"] if p["id"] == "blood_proteins"))
    panel["coordinates"] = [a for a in panel["coordinates"] if a["id"] == "albumin"]
    design = example()
    design["cohort_n"] = 200
    design["gates"].update(sampling_frame=True, measurement_semantics=True)
    supplied = {
        "status": "present",
        "operator_qualified": True,
        "time_frame": {"unit": "days", "origin": "registered_baseline", "source_qualified": True},
        "coordinate_status": {"albumin": "present"},
        "groups": [],
    }
    group = {
        "group_id": "observed",
        "n": 2,
        "site": None,
        "arm": None,
        "modifier": None,
        "timing_qualified": True,
        "events": [
            {"physical_id": "reading", "coordinate": "albumin", "time": 0, "session_id": "occasion"}
        ],
    }
    supplied["groups"] = [group]
    design["panels"] = {panel["id"]: supplied}
    return panel, design, supplied, group


def test_omitted_native_state_is_unknown_but_documented_empty_is_not():
    panel, design, supplied, group = scalar_roster()
    omitted = linked_workload.native_state_component(
        panel, supplied, None, [True], design, "reference", 0.25, 1
    )
    assert (omitted["lower"], omitted["upper"]) == (0, 1)
    empty = {**group, "events": []}
    confirmed = linked_workload.native_state_component(
        panel, supplied, empty, [True], design, "reference", 0.25, 1
    )
    assert (confirmed["lower"], confirmed["upper"]) == (0, 0)
    known = linked_workload.native_state_component(
        panel, supplied, group, [True], design, "reference", 0.25, 1
    )
    assert (known["lower"], known["upper"]) == (1, 1)
    assert known["joint_worst_variance_ratio"] == pytest.approx(0.25 / 0.75**2)


@pytest.mark.parametrize("failure", ["common", "coordinate", "clock"])
def test_omitted_state_preserves_known_failures(failure):
    panel, design, supplied, _ = scalar_roster()
    common = [False] if failure == "common" else [True]
    if failure == "coordinate":
        supplied["coordinate_status"]["albumin"] = "absent"
    if failure == "clock":
        supplied["time_frame"]["source_qualified"] = False
    result = linked_workload.native_state_component(
        panel, supplied, None, common, design, "reference", 0.25, 1
    )
    assert (result["lower"], result["upper"]) == (0, 0)


def test_population_omitted_roster_has_finite_noiseless_outer_bound():
    panel, design, supplied, group = scalar_roster()
    observed = c.population_information(panel, [group], 0.25)
    # For two independent people: Var(sample variance) = 2*(4+q)^2/(n-1).
    assert 1 / observed[0, 0] == pytest.approx(36.125)
    bound = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert bound["upper_percent"] == 100
    comp = bound["bound_components"][0]
    assert comp["joint_worst_variance_ratio"] == pytest.approx((32 / 199) / 0.25)
    # Filling the roster with a documented empty pattern does not add acquisitions.
    supplied["groups"].append({**group, "group_id": "empty", "n": 198, "events": []})
    explicit = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert explicit["upper_percent"] == 0
    assert explicit["bound_components"][0]["joint_worst_variance_ratio"] == pytest.approx(128)


@pytest.mark.parametrize("n", [1, 2, 129, 130])
def test_population_unknown_support_cannot_escape_independent_person_floor(n):
    panel, design, supplied, _ = scalar_roster()
    design["cohort_n"] = n
    supplied["groups"] = []
    result = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert result["upper_percent"] == (100 if n >= 129 else 0)
    if n > 1:
        assert result["bound_components"][0]["joint_worst_variance_ratio"] == pytest.approx(
            (32 / (n - 1)) / 0.25
        )


@pytest.mark.parametrize("failure", ["operator", "sampling", "collection", "clock", "coordinate"])
def test_population_unknown_support_retains_false_gates(failure):
    panel, design, supplied, _ = scalar_roster()
    supplied["groups"] = []
    if failure == "operator":
        supplied["operator_qualified"] = False
    elif failure == "sampling":
        design["gates"]["sampling_frame"] = False
    elif failure == "collection":
        design["lifecycle"] = "collected"
        design["gates"]["collection_verified"] = False
    elif failure == "clock":
        supplied["time_frame"]["source_qualified"] = False
    else:
        supplied["coordinate_status"]["albumin"] = "absent"
    result = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert result["upper_percent"] == result["continuous_upper_percent"] == 0


def test_population_off_baseline_readings_remain_possible_information():
    panel, design, supplied, group = scalar_roster()
    group["n"] = design["cohort_n"]
    group["events"][0]["time"] = panel["horizon_days"]
    # Reading = baseline + independent change + noise; its covariance still
    # informs baseline variance in the declared model. An upper bound cannot
    # discard it merely because it was acquired after baseline.
    observed = c.population_information(panel, [group], 0.25)
    assert 1 / observed[0, 0] == pytest.approx(2 * (4 + 1 + 0.25) ** 2 / 199)
    ideal = linked_workload.optimistic_population_groups(panel, supplied, design["cohort_n"])
    assert 1 / c.population_information(panel, ideal, 0)[0, 0] == pytest.approx(32 / 199)
    group["timing_qualified"] = False
    excluded = linked_workload.optimistic_population_groups(panel, supplied, design["cohort_n"])
    assert c.population_information(panel, excluded, 0)[0, 0] == 0


def test_global_failed_clock_is_not_overridden_but_opaque_occasion_is_separate():
    panel, design, supplied, group = scalar_roster()
    supplied["time_frame"]["source_qualified"] = False
    assert group["timing_qualified"] is True
    state = linked_workload.native_state_component(
        panel, supplied, group, [True], design, "reference", 0.25, 1
    )
    assert (state["lower"], state["upper"]) == (0, 0)
    population = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert population["upper_percent"] == 0
    # A qualified source-selected occasion establishes native state without
    # asserting a valid calendar anchor for population/longitudinal tasks.
    group["state_occasion"] = {"occasion_id": "recorded", "source_qualified": True}
    group["events"][0]["occasion_id"] = "recorded"
    group["events"][0]["time"] = None
    opaque = linked_workload.native_state_component(
        panel, supplied, group, [True], design, "reference", 0.25, 1
    )
    assert (opaque["lower"], opaque["upper"]) == (1, 1)


def test_unknown_clock_does_not_invent_acquisitions_in_a_documented_pattern():
    panel, design, supplied, group = scalar_roster()
    group.update(n=200, timing_qualified=None, events=[])
    empty = linked_workload.native_state_component(
        panel, supplied, group, [True], design, "reference", 0.25, 1
    )
    assert (empty["lower"], empty["upper"]) == (0, 0)
    bound = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert bound["upper_percent"] == 0
    group["events"] = [
        {"coordinate": "albumin", "time": None, "physical_id": "known-reading", "session_id": "one"}
    ]
    acquired = linked_workload.native_state_component(
        panel, supplied, group, [True], design, "reference", 0.25, 1
    )
    assert (acquired["lower"], acquired["upper"]) == (0, 1)
    bound = linked_workload.aggregate_upper_bound(
        panel, "population_variation", supplied, design, 1, "reference"
    )
    assert bound["upper_percent"] == 100
    group["events"] = []
    supplied["coordinate_status"]["albumin"] = "unknown"
    unresolved = linked_workload.native_state_component(
        panel, supplied, group, [True], design, "reference", 0.25, 1
    )
    assert (unresolved["lower"], unresolved["upper"]) == (0, 1)


def test_population_optimism_retains_partial_coordinate_support():
    panel, design, supplied, group = scalar_roster()
    second = {**panel["coordinates"][0], "id": "unacquired"}
    panel["coordinates"].append(second)
    supplied["coordinate_status"][second["id"]] = "present"
    group.update(n=200, timing_qualified=None)
    ideal = linked_workload.optimistic_population_groups(panel, supplied, design["cohort_n"])
    assert [{e["coordinate"] for e in g["events"]} for g in ideal] == [{"albumin"}]
    assert sum(g["n"] for g in ideal) == 200
    # The unacquired second coordinate and its covariance cannot become identified.
    information = c.population_information(panel, ideal, 0)
    np.testing.assert_allclose(information, np.diag([199 / 32, 0, 0]), atol=1e-12)


def test_omitted_roster_reaches_native_population_bound_in_linked_evaluation(monkeypatch):
    manifest = copy.deepcopy(c.registry())
    panel, design, supplied, group = scalar_roster()
    second = copy.deepcopy(panel["coordinates"][0])
    second["id"] = "second_synthetic_quantity"
    panel["coordinates"].append(second)
    supplied["coordinate_status"][second["id"]] = "present"
    group["events"].append(
        {**group["events"][0], "physical_id": "second", "coordinate": second["id"]}
    )
    manifest["panels"] = [panel]
    monkeypatch.setattr(c, "registry", lambda: copy.deepcopy(manifest))
    monkeypatch.setattr(c, "SCENARIOS", {"reference": 0.25})
    relations = [
        [
            "synthetic_pair",
            [panel["id"], "albumin"],
            [panel["id"], second["id"]],
            "Synthetic paired quantities",
        ]
    ]
    result, _ = linked_workload.evaluate(design, relations=relations)
    rows = {r["family"]: r for r in result["scenarios"][0]["rows"]}
    state = rows["individual_state"]
    assert state["lower_percent"] == 1  # Two acquired of the full 200-person cohort.
    assert state["upper_percent"] == 100
    assert sum(p["n"] for p in state["parts"]) == design["cohort_n"]
    population = rows["population_variation"]
    assert population["lower_percent"] == 0
    assert population["upper_percent"] == 100
    assert "upper_canonical_receipt_sha256" in population["parts"][0]
