"""Stable programmatic front door for the AniBench v2 candidate mechanics."""

from __future__ import annotations

from typing import Any

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


def optimize_protocol_design_v2(request: dict[str, Any]) -> dict[str, Any]:
    """Recompile protocol mutations and return their multi-objective Pareto frontier."""

    return optimize_protocol(request)
