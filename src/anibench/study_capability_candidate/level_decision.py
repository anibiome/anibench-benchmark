# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Exact finite-reference conjunction from final used canonical target receipts."""

import hashlib
from pathlib import Path

from anibench.finite_suites_v1 import scientific_frame_sha256, suite_sha256

from .compiler import digest


def decide_level(result, components, profile):
    expected = {t["canonical_id"]: t for t in profile["targets"]}
    if len(expected) != len(profile["targets"]):
        raise ValueError("Duplicate required reference target")
    by_receipt = {}
    for component in components:
        receipt = component.get("receipt", component.get("canonical_result"))
        if receipt is not None:
            payload = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
            if suite_sha256(payload) != receipt["receipt_sha256"]:
                raise ValueError("Stale canonical result receipt")
            if (
                suite_sha256(component["profile"]) != receipt["suite_profile_sha256"]
                or suite_sha256(component["request"]) != receipt["request_sha256"]
            ):
                raise ValueError("Stale canonical profile/request binding")
            by_receipt[receipt["receipt_sha256"]] = (component, receipt)

    def states(receipt_id, scenario):
        if receipt_id not in by_receipt:
            raise ValueError("Final component receipt is missing")
        component, receipt = by_receipt[receipt_id]
        entries = {t["canonical_id"]: t for t in component["profile"]["targets"]}
        scenarios = receipt["suite_result"]["scenarios"]
        if len(scenarios) != 1 or scenarios[0]["scenario_id"] != scenario:
            raise ValueError("Final component scenario differs from reference")
        out = {}
        for row in scenarios[0]["targets"]:
            key = row["canonical_id"]
            if key not in expected:
                raise ValueError("Compiled target is outside exact reference")
            actual = entries[key]
            required = expected[key]
            if (
                actual["frame_sha256"] != required["frame_sha256"]
                or scientific_frame_sha256(actual["task"]) != required["frame_sha256"]
            ):
                raise ValueError("Compiled target scientific frame differs from reference: " + key)
            if (
                actual["task"]["functionals"] != required["task"]["functionals"]
                or actual["task"]["required_support"] != required["task"]["required_support"]
            ):
                raise ValueError("Compiled target limits or support differ from reference: " + key)
            out[key] = row["attainment"]
        return out

    def leaves(parts):
        for part in parts:
            if "parts" in part:
                yield from leaves(part["parts"])
            else:
                yield part

    records = []
    seen = {}

    def add(part, scenario, context):
        low = states(part["canonical_receipt_sha256"], scenario)
        upper = states(
            part.get("upper_canonical_receipt_sha256", part["canonical_receipt_sha256"]),
            scenario,
        )
        if set(low) != set(upper):
            raise ValueError("Lower/upper components have different targets")
        for key in low:
            state = (
                "pass"
                if low[key] == "attained"
                else "fail"
                if upper[key] == "not_attained"
                else "unresolved"
            )
            records.append(
                {
                    "scenario_id": scenario,
                    "canonical_id": key,
                    "status": state,
                    "scope": context,
                    "lower_receipt_sha256": part["canonical_receipt_sha256"],
                    "upper_receipt_sha256": part.get(
                        "upper_canonical_receipt_sha256",
                        part["canonical_receipt_sha256"],
                    ),
                }
            )
            seen.setdefault(scenario, set()).add(key)

    for scenario in result["scenarios"]:
        sid = scenario["scenario_id"]
        for row in scenario["rows"]:
            terminal = list(leaves(row["parts"]))
            if row["family"] in ["individual_state", "trajectories"]:
                # Each horizon independently retains the complete participant roster.
                groups = [row] if row["family"] == "individual_state" else row["parts"]
                for group in groups:
                    if sum(p["n"] for p in group["parts"]) != row["cohort_n"]:
                        raise ValueError("Reference decision lost required roster mass")
            for part in terminal:
                add(part, sid, "native roster or aggregate task")
        for relation in scenario["cross_panel_relations"]:
            if sum(p["n"] for p in relation["individual_state"]["parts"]) != result["cohort_n"]:
                raise ValueError("Relation roster mismatch")
            for part in relation["individual_state"]["parts"]:
                add(part, sid, "linked per-person target")
            add(relation["population_variation"], sid, "linked population target")
    if set(seen) != set(profile["scenario_ids"]) or any(
        keys != set(expected) for keys in seen.values()
    ):
        raise ValueError("Final receipts do not cover every required reference target and scenario")
    status = (
        "fail"
        if any(r["status"] == "fail" for r in records)
        else "unresolved"
        if any(r["status"] == "unresolved" for r in records)
        else "pass"
    )
    decision = {
        "schema": "anibench.native-panel-level-decision.v1",
        "implementation_sha256": "sha256:"
        + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "level_profile_id": profile["profile_id"],
        "reference_profile_sha256": suite_sha256(profile),
        "status": status,
        "required_targets_per_scenario": len(expected),
        "scenario_ids": profile["scenario_ids"],
        "task_instances": len(records),
        "status_counts": {
            s: sum(r["status"] == s for r in records) for s in ["pass", "fail", "unresolved"]
        },
        "limiting_targets": list(
            dict.fromkeys(r["canonical_id"] for r in records if r["status"] != "pass")
        )[:20],
        "decision_basis": "Exact conjunction of final native/relation target and support receipts for every roster pattern and declared scenario; no percentage or rounding decision.",
        "task_instances_sha256": digest(records),
        "task_instances_records": records,
    }
    decision["receipt_sha256"] = digest(decision)
    return decision
