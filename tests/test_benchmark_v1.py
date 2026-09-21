# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Scientific aggregation regressions, with analytic expected results."""

import copy
import json

import pytest
from test_finite_suites_v1 import profile, request, task

from anibench.benchmark_v1 import BenchmarkError, evaluate_benchmark
from anibench.cli import main
from anibench.finite_suites_v1 import suite_sha256


def score_profile(p, weights=None, gates=()):
    return {
        "contract": "anibench.score-profile.v1",
        "score_profile_id": "synthetic-checks",
        "suite_profile_sha256": suite_sha256(p),
        "weighting_rationale": "Test convention",
        "gate_only_targets": list(gates),
        "views": [
            {
                "view_id": "capability",
                "label": "Capability",
                "categories": [
                    {
                        "category_id": "state",
                        "label": "State",
                        "question": "Which targets pass?",
                        "targets": [
                            {
                                "canonical_id": t["canonical_id"],
                                "weight": (weights or {}).get(t["canonical_id"], 1),
                            }
                            for t in p["targets"]
                            if t["canonical_id"] not in gates
                        ],
                    }
                ],
            }
        ],
    }


def execute(p, r=None, score=None):
    score = score or score_profile(p)
    return evaluate_benchmark(
        {
            "contract": "anibench.benchmark-request.v1",
            "score_profile_sha256": suite_sha256(score),
            "suite_request": r or request(p),
        },
        trusted_profiles={suite_sha256(p): p},
        trusted_score_profiles={suite_sha256(score): score},
    )


def category(result):
    return result["scenarios"][0]["views"][0]["categories"][0]


def test_fixed_denominator_twenty_tasks_known_unknown_and_failed():
    p = profile(*(task(f"observable-{i}") for i in range(20)))
    r = request(p)
    for row in r["scenarios"][0]["targets"][12:17]:
        row.update(known_absent=True, request=None)
    r["scenarios"][0]["targets"] = r["scenarios"][0]["targets"][:17]
    result = execute(p, r)
    c = category(result)
    assert (c["passed_percent"], c["upper_percent"], c["unknown_percent"]) == (60, 75, 15)
    assert (c["weight_total"], c["passed_weight"], c["failed_weight"], c["unknown_weight"]) == (
        20,
        12,
        5,
        3,
    )
    assert result["level_attainment"] == "not_attained"


def test_threshold_cliff_is_distinct_from_continuous_adequacy():
    p = profile(task())
    r = request(p, {("a", "neural"): 1 / (0.5 * 1.01)})
    c = category(execute(p, r))
    assert c["passed_percent"] == 0
    assert c["precision_toward_targets"]["lower_percent"] == pytest.approx(100 / 1.01)


def test_prior_cannot_supply_acquired_information():
    p = profile(task(prior=1e6))
    c = category(execute(p, request(p, {("a", "neural"): 0})))
    assert c["passed_percent"] == c["precision_toward_targets"]["upper_percent"] == 0
    p["precision_basis"] = "posterior_total"
    with pytest.raises(BenchmarkError, match="likelihood_only"):
        execute(p)


def test_gate_only_target_can_prevent_level_at_one_hundred_percent():
    p = profile(task("observed"), task("required-control"))
    r = request(p)
    r["scenarios"][0]["targets"].pop()
    result = execute(p, r, score_profile(p, gates=["required-control"]))
    assert category(result)["passed_percent"] == 100
    assert result["level_attainment"] == "unknown"
    assert result["scenarios"][0]["gates"][0]["attainment"] == "unknown"


def test_rounded_hundred_does_not_pass_level():
    p = profile(task("common"), task("tiny"))
    r = request(p)
    r["scenarios"][0]["targets"][1].update(known_absent=True, request=None)
    result = execute(p, r, score_profile(p, {"common": 999999999, "tiny": 1}))
    assert round(category(result)["passed_percent"], 2) == 100
    assert category(result)["failed_weight"] == 1
    assert result["level_attainment"] == "not_attained"


def test_two_incompatible_favorable_scenarios_do_not_make_a_level_pass():
    p = profile(task("x"), task("y"), quantifier="exists_declared_scenario")
    r = request(p, {("a", "x"): 4, ("a", "y"): 1, ("b", "x"): 1, ("b", "y"): 4})
    result = execute(p, r)
    assert all(s["views"][0]["categories"][0]["passed_percent"] == 50 for s in result["scenarios"])
    assert result["envelope"][0]["categories"][0]["upper_percent"] == 50
    assert result["envelope_joint_attainability_established"] is False
    assert result["level_attainment"] == "not_attained"


@pytest.mark.parametrize("bad_weight", [0, -1, True, 1.0])
def test_no_free_weight_or_float_ambiguity(bad_weight):
    p = profile(task())
    with pytest.raises(BenchmarkError):
        execute(p, score=score_profile(p, {"neural": bad_weight}))


def test_duplicate_omitted_and_unregistered_target_mass_rejected():
    p = profile(task("x"), task("y"))
    score = score_profile(p)
    targets = score["views"][0]["categories"][0]["targets"]
    for replacement in (
        [targets[0]],
        [targets[0], targets[0]],
        targets + [{"canonical_id": "invented", "weight": 1}],
    ):
        mutated = copy.deepcopy(score)
        mutated["views"][0]["categories"][0]["targets"] = replacement
        with pytest.raises(BenchmarkError):
            execute(p, score=mutated)


def test_unknown_support_limits_precision_and_known_absence_is_zero():
    p = profile(task())
    r = request(p)
    support = r["scenarios"][0]["targets"][0]["request"]["evidence"]["support"][0]
    support["supported"] = None
    c = category(execute(p, r))
    assert (c["passed_percent"], c["upper_percent"]) == (0, 100)
    assert c["precision_toward_targets"] == {"lower_percent": 0, "upper_percent": 100}
    support["supported"] = False
    assert category(execute(p, r))["precision_toward_targets"]["upper_percent"] == 0


def test_renaming_design_does_not_change_categories():
    p = profile(task())
    r = request(p)
    original = category(execute(p, r))
    r["design_id"] = "different-institution"
    for s in r["scenarios"]:
        s["design_id"] = r["design_id"]
        for t in s["targets"]:
            t["design_id"] = r["design_id"]
    assert category(execute(p, r)) == original


def test_cli_runs_and_preserves_existing_outputs(tmp_path, capsys):
    p = profile(task())
    score = score_profile(p)
    objects = {
        "request.json": {
            "contract": "anibench.benchmark-request.v1",
            "score_profile_sha256": suite_sha256(score),
            "suite_request": request(p),
        },
        "registry.json": {suite_sha256(p): p},
        "scores.json": {suite_sha256(score): score},
    }
    for name, data in objects.items():
        (tmp_path / name).write_text(json.dumps(data))
    out = tmp_path / "result.json"
    args = [
        "benchmark",
        str(tmp_path / "request.json"),
        "--registry",
        str(tmp_path / "registry.json"),
        "--scores",
        str(tmp_path / "scores.json"),
        "--out",
        str(out),
    ]
    assert main(args) == 0
    before = out.read_bytes()
    assert json.loads(before)["level_attainment"] == "attained"
    assert main(args) == 2
    assert out.read_bytes() == before
