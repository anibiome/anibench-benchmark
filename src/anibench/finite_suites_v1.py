# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Trusted, frozen finite-target profiles; conditional scope, no biological certification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .finite_tasks_v1 import (
    _canonical,
    _conjunction,
    _implementation_receipt,
    evaluate_finite_task,
    finite_task_sha256,
)
from .information_v2 import functional_likelihood_precision


class FiniteSuiteError(ValueError):
    """Invalid profile identity, hierarchy, or request; distinct from unknown evidence."""


def suite_sha256(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _asset(name: str) -> Path:
    relative = Path("schemas/finite_suites/v1") / name
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parent):
        if (root / relative).is_file():
            return root / relative
    raise FiniteSuiteError("Finite suite schema is not installed")


def scientific_frame_sha256(task: Mapping[str, Any]) -> str:
    """Normalize same-frame scale/sign aliases; never infer biological equivalence."""
    frame = {
        k: v
        for k, v in task.items()
        if k
        not in {
            "task_id",
            "task_version",
            "required_support",
            "functionals",
        }
    }
    directions = []
    for f in task["functionals"]:
        c = f["coefficients"]
        scale = next((x for x in c if x != 0), None)
        if scale is None:
            raise FiniteSuiteError("Zero functional")
        directions.append(
            {"unit": f["unit"], "direction": [0.0 if x == 0 else x / scale for x in c]}
        )
    directions.sort(key=lambda x: _canonical(x))
    if len({_canonical(d) for d in directions}) != len(directions):
        raise FiniteSuiteError("Duplicate scale/sign-equivalent functionals")
    frame["directions"] = directions
    return suite_sha256(frame)


def _validate(schema, value):
    if list(Draft202012Validator(schema).iter_errors(value)):
        raise FiniteSuiteError("Input violates the finite-suite schema")


def _validate_profile(profile, schema):
    _validate(schema, profile)
    if profile["scenario_quantifier"] == "single_conditional" and len(profile["scenario_ids"]) != 1:
        raise FiniteSuiteError("Single conditional profile requires exactly one scenario")
    identities, frames = set(), set()
    for target in profile["targets"]:
        task = target["task"]
        # Existing validation, including numerical geometry-independent checks.
        evaluate_finite_task(
            {
                "contract": "anibench.finite-task-request.v1",
                "task": task,
                "task_sha256": finite_task_sha256(task),
                "evidence": {"identifiability": None, "collection_verified": None, "support": []},
                "geometry": None,
            }
        )
        frame = scientific_frame_sha256(task)
        if target["frame_sha256"] != frame:
            raise FiniteSuiteError("Stale scientific frame digest")
        if target["canonical_id"] in identities or frame in frames:
            raise FiniteSuiteError("Duplicate canonical target or renamed equivalent frame")
        identities.add(target["canonical_id"])
        frames.add(frame)
    if len({t["task"]["claim_lane"] for t in profile["targets"]}) != 1:
        raise FiniteSuiteError("A profile cannot mix planned and realized claim lanes")


def _parent_check(child, parent):
    for field in ("precision_basis", "scenario_quantifier", "scenario_ids"):
        if child[field] != parent[field]:
            raise FiniteSuiteError("Hierarchy changed precision basis or scenario frame")
    targets = {t["canonical_id"]: t for t in child["targets"]}
    for p in parent["targets"]:
        c = targets.get(p["canonical_id"])
        if c is None or c["frame_sha256"] != p["frame_sha256"]:
            raise FiniteSuiteError("Child removed or changed a parent scientific target")
        pt, ct = p["task"], c["task"]
        roles = lambda task: {(x["domain_id"], x["role"]) for x in task["required_support"]}
        if not roles(pt) <= roles(ct):
            raise FiniteSuiteError("Child removed a required role")
        cf = {f["functional_id"]: f for f in ct["functionals"]}
        for f in pt["functionals"]:
            g = cf.get(f["functional_id"])
            if g is None or g["coefficients"] != f["coefficients"] or g["unit"] != f["unit"]:
                raise FiniteSuiteError("Child changed a parent functional")
            if g["variance_limit"] > f["variance_limit"]:
                raise FiniteSuiteError("Child weakened a parent variance limit")


def evaluate_finite_suite(
    request: Mapping[str, Any], *, trusted_profiles: Mapping[str, Any]
) -> dict:
    """Snapshot a supplied trusted registry; never fetch or promote a profile online."""
    request = json.loads(_canonical(request))
    registry = json.loads(_canonical(trusted_profiles))
    schema = json.loads(_asset("input.schema.json").read_text())
    _validate(schema, request)
    key = request["profile_sha256"]
    visited = set()

    def resolve(digest):
        if digest in visited:
            raise FiniteSuiteError("Cyclic profile hierarchy")
        visited.add(digest)
        if digest not in registry or suite_sha256(registry[digest]) != digest:
            raise FiniteSuiteError("Untrusted or stale profile digest")
        p = registry[digest]
        _validate_profile(p, schema["$defs"]["profile"])
        if p["parent_sha256"] is not None:
            _parent_check(p, resolve(p["parent_sha256"]))
        return p

    profile = resolve(key)
    scenario_ids = [s["scenario_id"] for s in request["scenarios"]]
    if len(set(scenario_ids)) != len(scenario_ids) or set(scenario_ids) != set(
        profile["scenario_ids"]
    ):
        raise FiniteSuiteError("Expected exactly the frozen shared scenario set")
    required = {t["canonical_id"]: t for t in profile["targets"]}
    binding = {field: request[field] for field in ("design_id", "design_source_sha256")}
    scenarios = []
    for scenario in request["scenarios"]:
        if any(scenario[field] != value for field, value in binding.items()):
            raise FiniteSuiteError("Scenario design declaration mismatch")
        rows = scenario["targets"]
        if any(row[field] != value for row in rows for field, value in binding.items()):
            raise FiniteSuiteError("Target design declaration mismatch")
        supplied = {r["canonical_id"]: r for r in rows}
        if len(supplied) != len(rows) or not set(supplied) <= set(required):
            raise FiniteSuiteError("Duplicate or unregistered canonical target")
        results = []
        for identity, target in required.items():
            row = supplied.get(identity)
            receipt, diagnostics = None, []
            state = "unknown"
            if row is not None:
                if row["known_absent"]:
                    if row["request"] is not None:
                        raise FiniteSuiteError("Absent target cannot include an evaluation request")
                    state = "not_attained"
                elif row["request"] is not None:
                    evaluation = row["request"]
                    if evaluation["task"] != target["task"]:
                        raise FiniteSuiteError("Task differs from immutable profile target")
                    receipt = evaluate_finite_task(evaluation)
                    state = receipt["attainment"]
                    if profile["precision_basis"] == "likelihood_only":
                        states = [state]
                        for f in target["task"]["functionals"]:
                            geometry = evaluation["geometry"]
                            diagnostic = {"functional_id": f["functional_id"], "state": "unknown"}
                            if geometry is not None:
                                diagnostic.update(
                                    functional_likelihood_precision(
                                        geometry["information_matrix"],
                                        target["task"]["prior_precision"],
                                        f["coefficients"],
                                    )
                                )
                                if diagnostic["identified"] is False:
                                    diagnostic["state"] = "not_attained"
                                elif diagnostic["identified"] is True:
                                    diagnostic["state"] = (
                                        "attained"
                                        if diagnostic["variance"]
                                        <= f["variance_limit"]
                                        * (1 + receipt["numerical_relative_tolerance"])
                                        else "not_attained"
                                    )
                            states.append(diagnostic["state"])
                            diagnostics.append(diagnostic)
                        state = _conjunction(states)
            results.append(
                {
                    **binding,
                    "canonical_id": identity,
                    "attainment": state,
                    "task_receipt": receipt,
                    "likelihood_diagnostics": diagnostics,
                }
            )
        scenarios.append(
            {
                **binding,
                "scenario_id": scenario["scenario_id"],
                "targets": results,
                "attainment": _conjunction([r["attainment"] for r in results]),
            }
        )
    states = [s["attainment"] for s in scenarios]
    attainment = _conjunction(states)
    if profile["scenario_quantifier"] == "exists_declared_scenario":
        attainment = (
            "attained"
            if "attained" in states
            else "unknown"
            if "unknown" in states
            else "not_attained"
        )
    implementation = _implementation_receipt()
    for path in [Path(__file__), _asset("input.schema.json"), _asset("result.schema.json")]:
        implementation["sha256"]["finite_suites/" + path.name] = (
            "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        )
    result = {
        **binding,
        "contract": "anibench.finite-suite-result.v1",
        "profile_sha256": key,
        "request_sha256": suite_sha256(request),
        "profile_id": profile["profile_id"],
        "profile_type": profile["profile_type"],
        "scope": profile["scope"],
        "precision_basis": profile["precision_basis"],
        "scenario_quantifier": profile["scenario_quantifier"],
        "attainment": attainment,
        "scenarios": scenarios,
        "implementation": implementation,
        "public_saturation_claim_allowed": False,
        "promotion_allowed": False,
        "empirical_learning_plateau": None,
    }
    _validate(json.loads(_asset("result.schema.json").read_text()), result)
    return result
