"""Portable adapter to the byte-pinned conditional reference experiment.

The experiment is a declared research model, not calibrated whole-biology
sufficiency. The public benchmark evaluator remains the only scoring engine.
"""

from __future__ import annotations

import copy
import hashlib
import runpy
from functools import lru_cache
from pathlib import Path
from typing import Any

from .benchmark_v1 import evaluate_benchmark
from .finite_suites_v1 import suite_sha256

ASSETS = Path(__file__).parent / "workbench_assets"
REFERENCE = ASSETS / "reference" / "v0.4" / "replay.py"
POOL = ASSETS / "reference" / "WORKLOAD_CANDIDATE.json"
REFERENCE_SHA = "0cec8d966af3ab41edef2b900d3f547e812bd86247f1092bd45a9a3441db313f"
POOL_SHA = "b539ed166d6171832cfdf6c1becb7201885eb67726715ae927ab49dd978dbd8d"


def verify_reference() -> None:
    """Reject changed scientific resources before either loading or evaluating."""
    for path, expected in ((REFERENCE, REFERENCE_SHA), (POOL, POOL_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("The installed reference differs from its reviewed version")


@lru_cache(maxsize=1)
def _engine() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    verify_reference()
    engine = runpy.run_path(str(REFERENCE))
    profiles, metadata = engine["make_profiles"]()
    return engine, profiles, metadata


def default_request() -> dict[str, Any]:
    verify_reference()
    engine, _, _ = _engine()
    baseline = copy.deepcopy(engine["DESIGNS"][0])
    baseline.setdefault("paired_endpoints", True)
    return {
        "level": "AB1",
        "baseline": baseline,
        "changed": {**baseline, "id": "changed-design", "N": 1290, "depth": 256},
    }


def evaluate_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate two declared designs against the identical finite reference."""
    verify_reference()
    if not isinstance(payload, dict) or set(payload) != {"level", "baseline", "changed"}:
        raise ValueError("Provide level, baseline, and changed designs")
    if payload["level"] not in ("AB1", "AB2"):
        raise ValueError("Choose AB1 or AB2")
    engine, profiles, metadata = _engine()
    profile = list(profiles.values())[("AB1", "AB2").index(payload["level"])]
    score = engine["score_profile"](profile, "domain_budget", metadata)
    results = {}
    for lane in ("baseline", "changed"):
        design = copy.deepcopy(payload[lane])
        engine["validate_design"](design)
        request = engine["request"](profile, score, metadata, design)
        result = evaluate_benchmark(
            request,
            trusted_profiles=profiles,
            trusted_score_profiles={suite_sha256(score): score},
        )
        results[lane] = {"design": design, "request": request, "result": result}
    return {
        "contract": "anibench.local-planner.v1",
        "version": "conditional-reference-0.4",
        "evidence_mode": "conditional_design",
        "level": payload["level"],
        "reference_script_sha256": REFERENCE_SHA,
        "profile": profile,
        "metadata": metadata,
        "results": results,
    }
