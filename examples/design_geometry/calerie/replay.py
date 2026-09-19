# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-supported CALERIE design scenarios through existing AniBench APIs.

Uses public aggregate counts only. Optional source verification is read-only;
there is no network access. Output directories must not already exist.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import math
import platform
import re
from pathlib import Path

import numpy as np

from anibench.causal_v2 import contrast_information
from anibench.information_v2 import EventContribution, event_information

MANIFEST_SHA256 = "592d014e034f4e440ae26c9b6d9d3fe6d71ca6265918db9b48210ebf4a8a32cb"
VERSION = "anibench.calerie-design-example.v1"
FRAME = {
    "observable_id": "illustrative_standardized_DNAm_scalar_not_calibrated_clock",
    "population_id": "CALERIE_197_baseline_plus_followup_reference",
    "estimand_ids": ["CR_minus_AL_24mo_endpoint_change", "CR_minus_AL_24mo_curvature"],
    "time_unit_id": "nominal_year_12_calendar_months",
    "outcome_unit_id": "standardized_scalar_unit",
    "horizon_years": 2.0,
}
ASSUMPTIONS = [
    "The same illustrative scalar and mean-trajectory model apply in both designs and arms.",
    "Independent participants; residual covariance is variance*rho**abs(year_difference).",
    "Nominal collection months stand in for actual timestamps, which are unavailable here.",
    "Retained subsets are exchangeable for the common population estimand; counts do not verify this.",
    "Common arm residual variance and scalar calibration are hypothetical, not source estimates.",
    "Causal interpretation additionally needs consistency, no interference and retained-sample exchangeability.",
]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def seal(value):
    return {**value, "payload_sha256": digest(value)}


def verify_seal(value):
    payload = {k: v for k, v in value.items() if k != "payload_sha256"}
    if value.get("payload_sha256") != digest(payload):
        raise ValueError("payload digest mismatch")


def load_manifest(path=None):
    raw = (path or Path(__file__).with_name("source_manifest.json")).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("frozen source manifest mismatch")
    return json.loads(raw)


def verify_source(raw, manifest):
    source = manifest["source"]
    if len(raw) != source["size_bytes"] or hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError("exact source-byte hash/size mismatch")
    text = json.loads(raw)[0]["documents"][0]["passages"][5]["text"]
    if hashlib.sha256(text.encode()).hexdigest() != source["passage_utf8_sha256"]:
        raise ValueError("source passage hash mismatch")
    normalized = " ".join(text.split())
    population = int(re.search(r"n\s*=\s*(\d+) participants", normalized).group(1))
    cr = list(map(int, re.findall(r"n\s*=\s*(\d+) CR", normalized)))
    al = list(map(int, re.findall(r"n\s*=\s*(\d+) AL", normalized)))
    if not re.search(r"baseline, 12 months and 24 months", normalized):
        raise ValueError("reviewed time mapping changed")
    extracted = {
        "baseline_and_at_least_one_followup_people": population,
        "nominal_months": [0, 12, 24],
        "12mo_change_people": dict(zip(["CR", "AL"], [cr[0], al[0]], strict=True)),
        "24mo_change_people": dict(zip(["CR", "AL"], [cr[1], al[1]], strict=True)),
    }
    if extracted != manifest["reported_facts"]:
        raise ValueError("source literals disagree with manifest")


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("count must be an integer within its declared range")
    return value


def feasible_supports(population, first, second, *, union_complete=False):
    """Exact intersection possibilities for two visits in two disjoint arms.

    Only a common parent universe is assumed; exact union size is not inferred
    from the two endpoint-analysis counts. No independent missingness assumption.
    """
    integer(population, 1)
    if type(union_complete) is not bool:
        raise ValueError("union_complete must be a boolean assumption")
    if set(first) != {"CR", "AL"} or set(second) != {"CR", "AL"}:
        raise ValueError("both visits must name exactly CR and AL")
    for count in [*first.values(), *second.values()]:
        if integer(count) > population:
            raise ValueError("count exceeds parent population")
    feasible = set()
    lower_cr = max(first["CR"], second["CR"])
    upper_cr = population - max(first["AL"], second["AL"])
    for cr_parent in range(lower_cr, upper_cr + 1):
        al_parent = population - cr_parent
        ranges = []
        for arm, parent in [("CR", cr_parent), ("AL", al_parent)]:
            lower = max(0, first[arm] + second[arm] - parent)
            upper = min(first[arm], second[arm])
            ranges.append(range(lower, upper + 1))
        feasible.update((cr, al) for cr in ranges[0] for al in ranges[1])
    if union_complete:
        intersection_total = sum(first.values()) + sum(second.values()) - population
        feasible = {pair for pair in feasible if sum(pair) == intersection_total}
    if not feasible:
        raise ValueError("inconsistent visit/arm counts and parent population")
    pooled = [
        max(0, sum(first.values()) + sum(second.values()) - population),
        min(sum(first.values()), sum(second.values())),
    ]
    pairs = [{"CR": cr, "AL": al} for cr, al in sorted(feasible)]
    return {
        "pooled_intersection_bound": pooled,
        "arm_conditioned_intersection_bound": [min(map(sum, feasible)), max(map(sum, feasible))],
        "feasible_arm_counts": pairs,
    }


def validate_model(variance, correlation):
    for value in (variance, correlation):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("model parameters must be finite real numbers, not booleans")
    if variance <= 0 or not 0 <= correlation < 1:
        raise ValueError("variance must be positive and yearly correlation in [0,1)")


def build_requests(manifest):
    facts = manifest["reported_facts"]
    support = feasible_supports(
        facts["baseline_and_at_least_one_followup_people"],
        facts["12mo_change_people"],
        facts["24mo_change_people"],
    )
    requests = []
    for variance in manifest["model_scenarios"]["residual_variances"]:
        for rho in manifest["model_scenarios"]["yearly_correlations"]:
            validate_model(variance, rho)
            for design, times, counts in [
                ("endpoint_pair", [0.0, 2.0], [facts["24mo_change_people"]]),
                ("three_timepoints", [0.0, 1.0, 2.0], support["feasible_arm_counts"]),
            ]:
                for arm_counts in counts:
                    requests.append(
                        seal(
                            {
                                "version": VERSION,
                                "frame": copy.deepcopy(FRAME),
                                "source_sha256": manifest["source"]["sha256"],
                                "source_manifest_sha256": MANIFEST_SHA256,
                                "model": {"residual_variance": variance, "yearly_correlation": rho},
                                "design_id": design,
                                "time_years": times,
                                "arm_counts": arm_counts,
                                "assumptions": list(ASSUMPTIONS),
                            }
                        )
                    )
    return support, requests


def implementation():
    paths = [__file__, inspect.getfile(contrast_information), inspect.getfile(event_information)]
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "sha256": {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
    }


def evaluate(request):
    verify_seal(request)
    if set(request) != {
        "version",
        "frame",
        "source_sha256",
        "source_manifest_sha256",
        "model",
        "design_id",
        "time_years",
        "arm_counts",
        "assumptions",
        "payload_sha256",
    }:
        raise ValueError("request must preserve the complete declared comparison contract")
    manifest = load_manifest()
    if (
        request["version"] != VERSION
        or request["frame"] != FRAME
        or request["source_manifest_sha256"] != MANIFEST_SHA256
        or request["source_sha256"] != manifest["source"]["sha256"]
        or request["assumptions"] != ASSUMPTIONS
    ):
        raise ValueError("request source or estimand frame mismatch")
    model = request["model"]
    if set(model) != {"residual_variance", "yearly_correlation"}:
        raise ValueError("exact covariance model required")
    variance, rho = model["residual_variance"], model["yearly_correlation"]
    validate_model(variance, rho)
    expected_times = {"endpoint_pair": [0.0, 2.0], "three_timepoints": [0.0, 1.0, 2.0]}
    if request["design_id"] not in expected_times:
        raise ValueError("unknown design")
    if not isinstance(request["time_years"], list) or any(
        type(t) not in (int, float) or not math.isfinite(t) for t in request["time_years"]
    ):
        raise ValueError("finite real nominal times required")
    if request["time_years"] != expected_times[request["design_id"]]:
        raise ValueError("times differ from frozen design")
    if set(request["arm_counts"]) != {"CR", "AL"}:
        raise ValueError("exact arm set required")
    for count in request["arm_counts"].values():
        integer(count, 1)
    facts = manifest["reported_facts"]
    feasible = feasible_supports(
        facts["baseline_and_at_least_one_followup_people"],
        facts["12mo_change_people"],
        facts["24mo_change_people"],
    )["feasible_arm_counts"]
    permitted = (
        [facts["24mo_change_people"]] if request["design_id"] == "endpoint_pair" else feasible
    )
    if request["arm_counts"] not in permitted:
        raise ValueError("counts violate source support")
    times = np.asarray(request["time_years"])
    covariance = variance * rho ** np.abs(times[:, None] - times[None, :])
    basis = np.column_stack([times / 2, (times - 1) ** 2])
    arms = {}
    for arm, count in request["arm_counts"].items():
        precision = count * np.linalg.solve(covariance, np.eye(len(times)))
        result = contrast_information(basis, observation_precision=precision).as_dict()
        gram = np.asarray(result["information_matrix"])
        # Time reversal makes the centered linear column odd and curvature even.
        # Check that numerical precision preserves this proven orthogonality;
        # scalar reciprocals are valid ONLY after this check.
        scale = max(float(np.max(np.abs(gram))), np.finfo(float).tiny)
        if abs(gram[0, 1]) > 1e-10 * scale:
            raise ValueError("declared temporal estimands are not information-orthogonal")
        centered = ((times - 1) / 2)[:, None]
        check = event_information(
            EventContribution(
                "endpoint_change",
                tuple(map(tuple, centered)),
                tuple(map(tuple, covariance)),
                count,
                manifest["source"]["sha256"],
            )
        )
        if not np.isclose(check[0, 0], gram[0, 0], rtol=1e-10, atol=0):
            raise ValueError("existing API cross-check failed")
        arms[arm] = result
    estimands = []
    for index, estimand_id in enumerate(FRAME["estimand_ids"]):
        identifiable = request["design_id"] == "three_timepoints" or index == 0
        value = None
        if identifiable:
            value = sum(1 / a["information_matrix"][index][index] for a in arms.values())
            factor = sum(1 / n for n in request["arm_counts"].values())
            analytic = (
                variance
                * factor
                * (2 * (1 - rho**2) if index == 0 else 1.5 - 2 * rho + 0.5 * rho**2)
            )
            if not math.isclose(value, analytic, rel_tol=1e-9):
                raise ValueError("independent analytic variance identity failed")
        estimands.append(
            {
                "estimand_id": estimand_id,
                "identifiable": identifiable,
                "variance": value,
                "standard_error": None if value is None else math.sqrt(value),
                "variance_unit": "standardized_scalar_unit_squared",
            }
        )
    return seal(
        {
            "version": VERSION,
            "request_sha256": request["payload_sha256"],
            "implementation": implementation(),
            "arm_api_results": arms,
            "estimands": estimands,
        }
    )


def verify_receipt(request, receipt):
    verify_seal(receipt)
    # API matrices use tuples in memory; JSON stores arrays. Compare canonical
    # serialized values so a saved, unmodified receipt remains replayable.
    if digest(receipt) != digest(evaluate(request)):
        raise ValueError("receipt is stale or disagrees with current exact replay")


def comparison_rows(requests, receipts):
    if not requests or len(requests) != len(receipts):
        raise ValueError("aligned nonempty requests/receipts required")
    baseline = requests[0]
    for request, receipt in zip(requests, receipts, strict=True):
        for key in ["frame", "source_sha256", "source_manifest_sha256"]:
            if request[key] != baseline[key]:
                raise ValueError(
                    "comparison requires identical source/population/estimand/unit frame"
                )
        verify_receipt(request, receipt)
    rows = []
    models = {digest(r["model"]): r["model"] for r in requests}
    for model_id, model in sorted(models.items()):
        # An interval is the complete source-support envelope, never a selected
        # subset of favorable supports or a count of repeated identical inputs.
        model_requests = [r for r in requests if r["model"] == model]
        facts = load_manifest()["reported_facts"]
        support = feasible_supports(
            facts["baseline_and_at_least_one_followup_people"],
            facts["12mo_change_people"],
            facts["24mo_change_people"],
        )["feasible_arm_counts"]
        for design, expected in [
            ("endpoint_pair", [facts["24mo_change_people"]]),
            ("three_timepoints", support),
        ]:
            actual = [r["arm_counts"] for r in model_requests if r["design_id"] == design]
            if sorted(map(digest, actual)) != sorted(map(digest, expected)):
                raise ValueError("comparison requires each feasible support exactly once")
        for design in ["endpoint_pair", "three_timepoints"]:
            matched = [
                (r, s)
                for r, s in zip(requests, receipts, strict=True)
                if r["model"] == model and r["design_id"] == design
            ]
            if not matched:
                continue
            for index, tid in enumerate(FRAME["estimand_ids"]):
                values = [s["estimands"][index]["variance"] for _, s in matched]
                rows.append(
                    {
                        "model_id": model_id,
                        "model": model,
                        "design_id": design,
                        "estimand_id": tid,
                        "variance_unit": "standardized_scalar_unit_squared",
                        "variance_interval": None
                        if any(v is None for v in values)
                        else [min(values), max(values)],
                        "state": "unidentifiable"
                        if any(v is None for v in values)
                        else "conditional_model",
                        "interval_semantics": "support_envelope_not_confidence_interval",
                        "request_sha256": [r["payload_sha256"] for r, _ in matched],
                    }
                )
    return rows


def replay(out, source=None):
    manifest = load_manifest()
    if source is not None:
        verify_source(source.read_bytes(), manifest)
    support, requests = build_requests(manifest)
    facts = manifest["reported_facts"]
    support["union_complete_sensitivity"] = feasible_supports(
        facts["baseline_and_at_least_one_followup_people"],
        facts["12mo_change_people"],
        facts["24mo_change_people"],
        union_complete=True,
    )
    receipts = [evaluate(r) for r in requests]
    rows = comparison_rows(requests, receipts)
    # Compute and validate first; exclusive directory creation prevents overwrites.
    out.mkdir(parents=True, exist_ok=False)
    artifacts = {
        "source-facts.json": {
            "manifest_sha256": MANIFEST_SHA256,
            "source_replayed": source is not None,
            "facts": manifest["reported_facts"],
            "support": support,
        },
        "requests.json": requests,
        "receipts.json": receipts,
        "chart-results.json": rows,
    }
    for name, value in artifacts.items():
        with (out / name).open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return {
        "requests": len(requests),
        "chart_rows": len(rows),
        "source_replayed": source is not None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source", type=Path, help="Optional exact public BioC source snapshot")
    args = parser.parse_args()
    print(json.dumps(replay(args.out, args.source), sort_keys=True))


if __name__ == "__main__":
    main()
