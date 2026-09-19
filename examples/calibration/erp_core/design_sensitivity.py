# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Aggregate-only conditional ERP design sensitivity; no raw observations read."""

import argparse
import hashlib
import json
import math
import platform
from importlib.metadata import version
from pathlib import Path

ATTRIBUTION = (
    "Derived from ERP CORE P3 aggregate calibration; primary SME paper "
    "https://doi.org/10.1111/psyp.14264. Source-derived outputs: CC BY-SA 4.0 "
    "(https://creativecommons.org/licenses/by-sa/4.0/). Source OSF metadata "
    "CC BY versus project/bundled CC BY-SA discrepancy retained."
)


def bounds(A, v, N, d, k):
    """Variances in uV^2, conditional on plug-in A=B+S and source-schedule v."""
    if any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0
        for x in (A, v)
    ):
        raise ValueError("A and v must be finite nonnegative variances; no silent truncation")
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in (N, k)):
        raise ValueError("N and k must be positive integer independent units")
    if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d) or d <= 0:
        raise ValueError("d must be a positive finite hypothetical depth multiplier")
    residual = v / (k * d)
    return {
        "N": N,
        "d": d,
        "k": k,
        "current_session_variance": v / d,
        "persistent_variance_lower": residual,
        "persistent_variance_upper": A / k + residual,
        "population_variance_lower": (A / k + residual) / N,
        "population_variance_upper": (A + residual) / N,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aggregates", "--aggregate", dest="aggregate", required=True, type=Path)
    p.add_argument("--out-dir", "--out", dest="out", required=True, type=Path)
    args = p.parse_args()
    raw = args.aggregate.read_bytes()
    src = json.loads(raw)
    # Only precomputed, non-identifying aggregate quantities are accessed.
    v = src["analytic_contrast_variance_mean_uV2"]
    A = src["measurement_adjusted_person_plus_session_variance_untruncated_uV2"]
    observed_se = src["cohort_mean_observed_SE_uV"]
    if (
        src.get("schema_version") != "anibench.erp-aggregate-calibration.v1"
        or src.get("n_people") != 40
    ):
        raise ValueError("Expected the ERP CORE aggregate calibration contract and cohort")
    rows = [
        bounds(A, v, N, d, k) for N in (2, 40, 2000) for d in (1, 4, 1000000) for k in (1, 4, 12)
    ]
    for row in rows:
        for key, value in list(row.items()):
            if "variance" in key:
                row[key.replace("variance", "root_variance")] = math.sqrt(value)
    baseline = bounds(A, v, 40, 1, 1)
    if not math.isclose(
        math.sqrt(baseline["population_variance_lower"]), observed_se, rel_tol=1e-12, abs_tol=1e-12
    ):
        raise ValueError(
            "Aggregate variance decomposition does not reproduce the observed baseline"
        )
    runtime = {
        "python": platform.python_version(),
        "numpy": version("numpy"),
        "matplotlib": version("matplotlib"),
    }
    args.out.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": "anibench.erp-design-sensitivity.v1",
        "attribution": ATTRIBUTION,
        "source_filename": "aggregate_results.json",
        "aggregate_sha256": hashlib.sha256(raw).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_hashes": src["source_hashes"],
        "runtime": runtime,
        "A_uV2": A,
        "v_uV2": v,
        "variance_units": "microvolt^2",
        "root_variance_units": "microvolt",
        "interpretation": "Conditional plug-in identification ranges, not confidence intervals",
        "depth_assumption": "All retained condition trial counts scaled proportionally; unchanged independent-trial noise and fixed contrast operator; v/d is variance at scaled schedule, not R/d for a single raw reading",
        "baseline_observed_SE_uV": observed_se,
        "baseline_reproduced_SE_uV": math.sqrt(baseline["population_variance_lower"]),
        "source_mean_retained_trials": src["mean_retained_trials"],
        "rows": rows,
    }
    (args.out / "design-sensitivity.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Conditional ERP design table",
        "",
        "Variances are in µV²; roots are in µV. Brackets are identification ranges conditional on estimated A and v, not confidence intervals.",
        "",
        "| N | d | k | Current-session variance | Persistent variance range | Population variance range | Population SE range |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['N']} | {r['d']} | {r['k']} | {r['current_session_variance']:.8g} | [{r['persistent_variance_lower']:.8g}, {r['persistent_variance_upper']:.8g}] | [{r['population_variance_lower']:.8g}, {r['population_variance_upper']:.8g}] | [{r['population_root_variance_lower']:.8g}, {r['population_root_variance_upper']:.8g}] |"
        )
    lines += ["", ATTRIBUTION]
    (args.out / "DESIGN_TABLE.md").write_text("\n".join(lines) + "\n")
    plot(A, v, args.out)
    print(
        json.dumps(
            {
                "rows": len(rows),
                "baseline_SE_uV": result["baseline_reproduced_SE_uV"],
                "aggregate_sha256": result["aggregate_sha256"],
            }
        )
    )


def plot(A, v, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    d = np.geomspace(1, 1e6, 401)
    colors = ["#2166ac", "#d95f02", "#6a3d9a"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.7), layout="constrained")
    ax = axes.flat[0]
    ax.plot(
        d,
        np.sqrt(v / d),
        color="black",
        ls="--",
        lw=2,
        label="Current-session measurement RMS error",
    )
    for k, c in zip((1, 4, 12), colors):
        lower = np.sqrt(v / (k * d))
        upper = np.sqrt(A / k + v / (k * d))
        ax.fill_between(d, lower, upper, color=c, alpha=0.10)
        ax.plot(d, upper, color=c, label=f"Persistent-person upper, k={k}")
        ax.plot(d, lower, color=c, ls=":", lw=1)
    ax.set_title("Individual estimands (independent of N)")
    ax.set_ylabel("Root mean-square estimation error (µV)")
    ax.legend(fontsize=8, loc="upper right")
    for ax, N in zip(list(axes.flat)[1:], (2, 40, 2000)):
        for k, c in zip((1, 4, 12), colors):
            lower = np.sqrt((A / k + v / (k * d)) / N)
            upper = np.sqrt((A + v / (k * d)) / N)
            ax.fill_between(d, lower, upper, color=c, alpha=0.11)
            ax.plot(d, upper, color=c, label=f"k={k} hypothetical visits")
            ax.plot(d, lower, color=c, ls=":", lw=1)
        ax.axhline(math.sqrt(A / N), color="gray", ls="--", lw=0.8)
        ax.set_title(f"Population mean: N={N:,} independent people")
        ax.set_ylabel("Population-mean SE (µV)")
        ax.legend(fontsize=8)
    for ax in axes.flat:
        ax.set_xscale("log")
        ax.set_xlim(1, 1e6)
        ax.set_ylim(bottom=0)
        ax.set_xlabel("Hypothetical retained-trial depth multiplier d")
        ax.grid(alpha=0.15)
    fig.suptitle(
        "ERP P3 contrast: conditional depth and visit sensitivity\nShading spans unknown B/S split at fixed plug-in A and v; NOT confidence intervals",
        fontsize=14,
    )
    fig.supxlabel(
        "Source-derived aggregates: ERP CORE / SME paper doi:10.1111/psyp.14264 · Adapted analysis CC BY-SA 4.0",
        fontsize=9,
    )
    fig.savefig(out / "sensitivity.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
