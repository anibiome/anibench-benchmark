# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Plan a bounded ERP design grid against declared, non-normative variance limits.

Uses exact decimal-rational comparisons. Source plug-in estimates are still
uncertain; arithmetic exactness does not imply biological certainty.
"""

import argparse
import hashlib
import itertools
import json
import math
import platform
from fractions import Fraction
from pathlib import Path

TASKS = ("current_session", "persistent_person", "population_mean")
MAX_DESIGNS = 10000


def number(value, name, *, positive=False, integer=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or (isinstance(value, float) and not math.isfinite(value))
        or value < 0
        or (positive and value == 0)
        or (integer and not isinstance(value, int))
    ):
        raise ValueError(f"Invalid {name}: expected a finite nonnegative number with declared type")
    return Fraction(str(value))


def interval_record(lo, hi):
    if lo > hi:
        return None
    return {"lower_exact": str(lo), "upper_exact": str(hi)}


def evaluate_design(A, v, N, k, d, limits):
    """Intersect all task constraints on the SAME unobserved session variance S.

    A = B + S, 0 <= S <= A. Persistent mean error is S/k + v/(k*d).
    Population mean error is (A - S + S/k + v/(k*d))/N.
    The current-session target is measured from that session alone: v/d.
    """
    A = number(A, "A")
    v = number(v, "v")
    n, visits, depth = (
        number(N, "N", positive=True, integer=True),
        number(k, "k", positive=True, integer=True),
        number(d, "d", positive=True),
    )
    if not isinstance(limits, dict) or set(limits) != set(TASKS):
        raise ValueError("All three variance limit keys are required; use null for unknown")
    ceilings = {
        task: None if limits[task] is None else number(limits[task], task) for task in TASKS
    }
    residual = v / (visits * depth)
    # Every inequality has the form slope*S + intercept <= ceiling.
    affine = {
        "current_session": (Fraction(0), v / depth),
        "persistent_person": (1 / visits, residual),
        "population_mean": ((1 / visits - 1) / n, (A + residual) / n),
    }
    lo, hi = Fraction(0), A
    checks = {}
    for task, (slope, intercept) in affine.items():
        ceiling = ceilings[task]
        if ceiling is None:
            checks[task] = {"status": "unresolved", "admissible_S_uV2": None}
            continue
        left, right = Fraction(0), A
        if slope > 0:
            right = min(right, (ceiling - intercept) / slope)
        elif slope < 0:
            left = max(left, (ceiling - intercept) / slope)
        elif intercept > ceiling:
            left, right = Fraction(1), Fraction(0)  # Empty interval, even if A=0.
        state = (
            "infeasible"
            if left > right
            else "robust"
            if left == 0 and right == A
            else "assumption_sensitive"
        )
        checks[task] = {"status": state, "admissible_S_uV2": interval_record(left, right)}
        lo, hi = max(lo, left), min(hi, right)
    known = "infeasible" if lo > hi else "robust" if lo == 0 and hi == A else "assumption_sensitive"
    status = "unresolved" if None in ceilings.values() and known != "infeasible" else known
    return {
        "N": N,
        "k": k,
        "d": d,
        "status": status,
        "known_constraints_status": known,
        "admissible_S_uV2": interval_record(lo, hi),
        "individual_checks": checks,
        "all_tasks_individually_possible_but_jointly_infeasible": (
            known == "infeasible"
            and all(c["status"] in ("robust", "assumption_sensitive") for c in checks.values())
        ),
    }


def nondominated(rows):
    """Componentwise resource frontier in (N,k,d); no price or weighted score."""
    ordered = sorted(rows, key=lambda r: (r["N"], r["k"], r["d"]))
    frontier = []
    for row in ordered:
        if not any(all(a[key] <= row[key] for key in ("N", "k", "d")) for a in frontier):
            frontier.append(row)
    return [{key: r[key] for key in ("N", "k", "d")} for r in frontier]


def plan(A, v, request):
    keys = {"schema_version", "target_status", "target_rationale", "variance_limits_uV2", "grid"}
    if not isinstance(request, dict) or set(request) != keys:
        raise ValueError("Unexpected or missing plan fields")
    if request["schema_version"] != "anibench.erp-design-request.v1":
        raise ValueError("Unsupported design request")
    if request["target_status"] not in ("illustrative", "user_declared_unvalidated"):
        raise ValueError("This planner cannot certify biologically calibrated targets")
    if not isinstance(request["target_rationale"], str) or not request["target_rationale"].strip():
        raise ValueError("A target rationale is required")
    grid = request["grid"]
    if not isinstance(grid, dict) or set(grid) != {"N", "k", "d"}:
        raise ValueError("Grid must declare N, k and d")
    size = 1
    for key in ("N", "k", "d"):
        values = grid[key]
        if not isinstance(values, list) or not values:
            raise ValueError("Grid axes must be nonempty lists")
        validated = [number(x, key, positive=True, integer=key != "d") for x in values]
        if len(set(validated)) != len(validated):
            raise ValueError("Duplicate grid values are not independent designs")
        size *= len(values)
    if size > MAX_DESIGNS:
        raise ValueError(f"Grid exceeds the declared computation limit of {MAX_DESIGNS} designs")
    rows = [
        evaluate_design(A, v, N, k, d, request["variance_limits_uV2"])
        for N, k, d in itertools.product(grid["N"], grid["k"], grid["d"])
    ]
    counts = {
        s: sum(r["status"] == s for r in rows)
        for s in ("robust", "assumption_sensitive", "infeasible", "unresolved")
    }
    return {
        "schema_version": "anibench.erp-design-plan.v1",
        "target_status": request["target_status"],
        "request": request,
        "A_uV2": A,
        "v_uV2": v,
        "parameter_set": "S in [0,A]; B=A-S. Plug-in A and v are fixed, not known truth.",
        "scope": "Bounded declared design grid; no global optimum or AniBench level attainment",
        "biological_threshold_validated": False,
        "precision_is_simultaneous_coverage": False,
        "variance_limit_units": "microvolt^2",
        "counts": counts,
        "no_feasible_design_within_grid": counts["infeasible"] == len(rows),
        "frontier_resource_order": ["N", "k", "d"],
        "robust_resource_frontier": nondominated([r for r in rows if r["status"] == "robust"]),
        "possible_resource_frontier": nondominated(
            [r for r in rows if r["status"] in ("robust", "assumption_sensitive")]
        ),
        "rows": rows,
    }


def load_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregates", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    raw_aggregate, raw_request = args.aggregates.read_bytes(), args.request.read_bytes()
    source, request = load_json(raw_aggregate), load_json(raw_request)
    if source.get("schema_version") != "anibench.erp-aggregate-calibration.v1":
        raise ValueError("Expected the ERP aggregate calibration contract")
    result = plan(
        source["measurement_adjusted_person_plus_session_variance_untruncated_uV2"],
        source["analytic_contrast_variance_mean_uV2"],
        request,
    )
    result["bindings"] = {
        "aggregate_sha256": hashlib.sha256(raw_aggregate).hexdigest(),
        "request_sha256": hashlib.sha256(raw_request).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
    }
    result["attribution"] = (
        "Adapted ERP CORE aggregate analysis; https://doi.org/10.1111/psyp.14264; "
        "source-derived outputs CC BY-SA 4.0. Targets are unvalidated assumptions."
    )
    # Create-only: cannot overwrite a source or a previous result, including symlinks.
    with args.out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"designs": len(result["rows"]), "counts": result["counts"]}))


if __name__ == "__main__":
    main()
