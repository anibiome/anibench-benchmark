"""Stable programmatic front door for the AniBench v2 candidate mechanics."""

from __future__ import annotations

from typing import Any

from .comparison_v1 import compare_trial_evals
from .design_v2 import compile_design
from .level1_assessment_v3 import assess_protocol_capacity_role_aware
from .optimizer_protocol_v2 import optimize_protocol
from .protocol_capacity_v2 import compile_protocol_capacity
from .v2 import score_information_run


def score_joint_information_v2(run: dict[str, Any]) -> dict[str, Any]:
    """Replay absolute information mechanics under the fail-closed registry."""

    return score_information_run(run)


def compile_trial_design_v2(design: dict[str, Any]) -> dict[str, Any]:
    """Compile a prospective, protocol, or realized design into typed coordinates."""

    return compile_design(design)


def compile_protocol_capacity_v2(protocol: dict[str, Any]) -> dict[str, Any]:
    """Compile separate prospective capacity families from protocol geometry."""

    return compile_protocol_capacity(protocol)


def assess_protocol_level1_v2(protocol: dict[str, Any]) -> dict[str, Any]:
    """Compile a protocol into the role-aware six-family Level-1 receipt."""

    return assess_protocol_capacity_role_aware(protocol)


def run_trial_eval(protocol: dict[str, Any]) -> dict[str, Any]:
    """Run the canonical six-task AniBench evaluation.

    This public name is the stable benchmark entry point.  It deliberately
    returns the same hash-bound receipt as ``assess_protocol_level1_v2`` so the
    human-facing command cannot drift from the mathematical authority.
    """

    return assess_protocol_capacity_role_aware(protocol)


def compare_trial_eval_receipts(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    """Return strict within-family Pareto relations for same-basis eval receipts."""

    return compare_trial_evals(receipts)


def optimize_protocol_design_v2(request: dict[str, Any]) -> dict[str, Any]:
    """Recompile protocol mutations and return their multi-objective Pareto frontier."""

    return optimize_protocol(request)
