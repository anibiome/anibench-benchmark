# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Independent arithmetic and semantic traps for source-summary compilation."""

import copy

import pytest

from anibench.finite_suites_v1 import evaluate_finite_suite, scientific_frame_sha256, suite_sha256
from anibench.summary_geometry_v1 import (
    SummaryGeometryError,
    compile_summary_task,
    summary_model_sha256,
)


def fixture(kind="population_mean"):
    task = {
        "contract": "anibench.finite-task-definition.v1",
        "task_id": "fictional-native-mean",
        "task_version": "illustrative1",
        "source_sha256": "sha256:" + "1" * 64,
        "model_sha256": summary_model_sha256(kind),
        "target_population": "Fictional source sampling population",
        "estimand": "Native-unit population mean or declared contrast",
        "horizon": "one defined occasion",
        "claim_lane": "conditional_design",
        "comparison_scope": "finite_functionals_only",
        "parameter_units": ["g/L"],
        "prior_precision": [[1]],
        "required_support": [{"domain_id": "molecular", "role": "observation"}],
        "functionals": [
            {"functional_id": "mean", "coefficients": [1], "unit": "g/L", "variance_limit": 1}
        ],
    }
    summary = {
        "contract": "anibench.scalar-summary.v1",
        "estimand_kind": kind,
        "unit": "g/L",
        "population_scope": "Fictional source sampling population",
        "occasion_or_change_window": "one defined occasion",
        "measurement_definition": "Native-unit population mean or declared contrast",
        "variance_multiplier": 1,
        "variance_multiplier_rationale": "Plug-in illustration; no empirical calibration",
        "assumptions": {
            "independent_sampling_units": "assumed",
            "groups_disjoint_and_independent": "assumed",
            "sampling_supports_declared_population": "assumed",
            "gaussian_sampling_approximation": "assumed",
            "rationale": "Explicit fictional sampling model",
        },
        "groups": [
            {
                "group_id": "g0",
                "n_independent": 100,
                "sample_sd": 10,
                "individual_quantity": "individual_paired_change"
                if "change" in kind
                else "individual_level",
                "source_sha256": "sha256:" + "2" * 64,
                "source_locator": "Fictional table",
                "n_locator": "N column",
                "spread_locator": "SD column",
                "extraction_status": "declared",
            }
        ],
    }
    if "contrast" in kind:
        other = copy.deepcopy(summary["groups"][0])
        other.update(group_id="g1", n_independent=25, sample_sd=5)
        summary["groups"].append(other)
    evidence = {
        "identifiability": True,
        "collection_verified": None,
        "support": [{"domain_id": "molecular", "role": "observation", "supported": True}],
    }
    return task, summary, evidence


def likelihood_result(task, request):
    profile = {
        "contract": "anibench.finite-suite-profile.v1",
        "profile_id": "test",
        "profile_type": "illustrative",
        "scope": "one fictional native mean",
        "tolerance_authority": "illustration",
        "calibration_authority": "none",
        "precision_basis": "likelihood_only",
        "scenario_quantifier": "single_conditional",
        "scenario_ids": ["plug-in"],
        "parent_sha256": None,
        "targets": [
            {
                "canonical_id": task["task_id"],
                "frame_sha256": scientific_frame_sha256(task),
                "task": task,
            }
        ],
    }
    key = suite_sha256(profile)
    binding = {"design_id": "fixture", "design_source_sha256": "sha256:" + "3" * 64}
    suite = {
        **binding,
        "contract": "anibench.finite-suite-request.v1",
        "profile_sha256": key,
        "scenarios": [
            {
                **binding,
                "scenario_id": "plug-in",
                "targets": [
                    {
                        **binding,
                        "canonical_id": task["task_id"],
                        "known_absent": False,
                        "request": request,
                    }
                ],
            }
        ],
    }
    return evaluate_finite_suite(suite, trusted_profiles={key: profile})["scenarios"][0]["targets"][
        0
    ]


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("population_mean", 1),
        ("population_mean_change", 1),
        ("population_contrast", 2),
        ("population_change_contrast", 2),
    ],
)
def test_native_mean_and_unbalanced_contrast_reach_actual_likelihood_solver(kind, expected):
    task, summary, evidence = fixture(kind)
    result = compile_summary_task(task, summary, evidence)
    assert result["sampling_variance"] == expected  # 10^2/100 + optionally 5^2/25
    target = likelihood_result(task, result["finite_task_request"])
    assert target["likelihood_diagnostics"][0]["variance"] == pytest.approx(expected)
    assert target["attainment"] == ("attained" if expected == 1 else "not_attained")


def test_reported_marginal_sd_cannot_be_used_as_paired_change_sd():
    task, summary, evidence = fixture("population_mean_change")
    summary["groups"][0]["individual_quantity"] = "individual_level"
    with pytest.raises(SummaryGeometryError, match="registered individual quantity"):
        compile_summary_task(task, summary, evidence)


@pytest.mark.parametrize(
    "key,value",
    [
        ("population_scope", "Different sampling population"),
        ("occasion_or_change_window", "ten years later"),
        ("measurement_definition", "Total protein instead of albumin, in the same units"),
    ],
)
def test_same_unit_wrong_scientific_quantity_or_scope_rejected(key, value):
    task, summary, evidence = fixture()
    summary[key] = value
    with pytest.raises(SummaryGeometryError, match="scientific frame"):
        compile_summary_task(task, summary, evidence)


@pytest.mark.parametrize("status", ["unknown", "violated"])
def test_unresolved_dependence_cannot_manufacture_zero_covariance(status):
    task, summary, evidence = fixture("population_contrast")
    summary["assumptions"]["groups_disjoint_and_independent"] = status
    result = compile_summary_task(task, summary, evidence)
    assert result["sampling_variance"] is None
    assert result["finite_task_request"]["geometry"] is None
    assert likelihood_result(task, result["finite_task_request"])["attainment"] == "unknown"


def test_missing_sd_and_failed_collection_have_distinct_meanings():
    task, summary, evidence = fixture()
    summary["groups"][0]["sample_sd"] = None
    result = compile_summary_task(task, summary, evidence)
    assert likelihood_result(task, result["finite_task_request"])["attainment"] == "unknown"
    summary["groups"][0]["sample_sd"] = 10
    task["claim_lane"] = "realized_record"
    evidence["collection_verified"] = False
    result = compile_summary_task(task, summary, evidence)
    assert likelihood_result(task, result["finite_task_request"])["attainment"] == "not_attained"


def test_direct_unadjusted_sem_needs_no_invented_individual_sd_or_count():
    task, summary, evidence = fixture()
    group = summary["groups"][0]
    del group["sample_sd"]
    group["unadjusted_mean_se"] = 0.1
    group["n_independent"] = None
    result = compile_summary_task(task, summary, evidence)
    assert result["sampling_variance"] == pytest.approx(0.01)
    assert "sample_sd" not in result["summary"]["groups"][0]
    assert likelihood_result(task, result["finite_task_request"])["attainment"] == "attained"
    group["sample_sd"] = 10
    with pytest.raises(SummaryGeometryError, match="schema"):
        compile_summary_task(task, summary, evidence)
    del group["sample_sd"]
    group["adjusted_mean_se"] = group.pop("unadjusted_mean_se")
    with pytest.raises(SummaryGeometryError, match="schema"):
        compile_summary_task(task, summary, evidence)


def test_integer_counts_and_no_unit_guessing():
    task, summary, evidence = fixture()
    summary["groups"][0]["n_independent"] = 100.0
    with pytest.raises(SummaryGeometryError, match="integers"):
        compile_summary_task(task, summary, evidence)
    summary["groups"][0]["n_independent"] = 100
    summary["unit"] = "mg/dL"
    with pytest.raises(SummaryGeometryError, match="native unit"):
        compile_summary_task(task, summary, evidence)


def test_duplicate_group_never_counts_as_independent_contrast():
    task, summary, evidence = fixture("population_contrast")
    summary["groups"][1] = copy.deepcopy(summary["groups"][0])
    with pytest.raises(SummaryGeometryError, match="duplicate group"):
        compile_summary_task(task, summary, evidence)


def test_variance_multiplier_is_sensitive_but_outcome_magnitude_is_not_an_input():
    task, summary, evidence = fixture()
    summary["variance_multiplier"] = 2
    result = compile_summary_task(task, summary, evidence)
    assert result["sampling_variance"] == 2
    summary["effect_size"] = 1000
    with pytest.raises(SummaryGeometryError, match="schema"):
        compile_summary_task(task, summary, evidence)


def test_wrong_model_and_zero_or_unrepresentable_variance_rejected():
    task, summary, evidence = fixture()
    task["model_sha256"] = summary_model_sha256("population_mean_change")
    with pytest.raises(SummaryGeometryError, match="exact sampling model"):
        compile_summary_task(task, summary, evidence)
    task["model_sha256"] = summary_model_sha256("population_mean")
    for sd in [0, 1e-300, 1e300]:
        summary["groups"][0]["sample_sd"] = sd
        with pytest.raises(SummaryGeometryError):
            compile_summary_task(task, summary, evidence)


def test_cli_creates_replayable_derivation_and_preserves_existing_file(tmp_path, capsys):
    import json

    from anibench.cli import main

    task, summary, evidence = fixture()
    path, out = tmp_path / "input.json", tmp_path / "derivation.json"
    path.write_text(json.dumps({"task": task, "summary": summary, "evidence": evidence}))
    assert main(["summary-task", str(path), "--out", str(out)]) == 0
    receipt = json.loads(out.read_text())
    assert likelihood_result(task, receipt["finite_task_request"])["attainment"] == "attained"
    first = out.read_bytes()
    assert main(["summary-task", str(path), "--out", str(out)]) != 0
    assert out.read_bytes() == first
    assert str(path) not in capsys.readouterr().out
