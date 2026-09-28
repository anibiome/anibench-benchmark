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
