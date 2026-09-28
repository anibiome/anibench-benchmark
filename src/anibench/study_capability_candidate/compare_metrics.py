# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Alternative score adjudication over the same frozen finite workload.
This is a research comparator, not an adopted public score implementation.
"""

from pathlib import Path

import numpy as np

from . import compiler as c

BASE = Path(__file__).parent


def continuous(component):
    """Separate support/identifiability from precision, including joint weak direction."""
    reqs = component["request"]["suite_request"]["scenarios"][0]["targets"]
    weights = component["score_profile"]["views"][0]["categories"][0]["targets"]
    Jnext = next(
        (
            np.asarray(x["request"]["geometry"]["information_matrix"])
            for x in reqs
            if x["request"]["geometry"] is not None
        ),
        None,
    )
    results = []
    for item, w in zip(reqs, weights):
        req = item["request"]
        task = req["task"]
        isjoint = item["canonical_id"].endswith(".joint")
        # joint_native_resolution=False means insufficient precision, not missing support.
        gates = [
            s["supported"]
            for s in req["evidence"]["support"]
            if s["domain_id"] != "joint_native_resolution"
        ]
        gate = c.tri(gates)
        if gate is False:
            lo = hi = 0.0
        elif gate is None:
            lo, hi = 0.0, 1.0
            if isjoint:
                # Missing tasks do not hide a known weak direction in already qualified targets.
                known = []
                lim = []
                for other in reqs:
                    if other is item:
                        continue
                    rr = other["request"]
                    if c.tri([s["supported"] for s in rr["evidence"]["support"]]) is True:
                        known.append(rr["task"]["functionals"][0]["coefficients"])
                        lim.append(rr["task"]["functionals"][0]["variance_limit"])
                if known and Jnext is not None:
                    flag, V = c.projected(Jnext, np.asarray(known))
                    if flag is False:
                        hi = 0.0
                    elif flag is True:
                        D = np.diag(1 / np.sqrt(lim))
                        hi = min(1.0, 1.0 / float(np.linalg.eigvalsh(D @ V @ D)[-1]))
        else:
            geom = req["geometry"]
            if geom is None:
                lo, hi = 0.0, 1.0
            else:
                J = np.asarray(geom["information_matrix"])
                L = np.asarray([f["coefficients"] for f in task["functionals"]])
                limits = np.asarray([f["variance_limit"] for f in task["functionals"]])
                flag, V = c.projected(J, L)
                if flag is False:
                    lo = hi = 0.0
                elif flag is None:
                    lo, hi = 0.0, 1.0
                else:
                    D = np.diag(1 / np.sqrt(limits))
                    ratio = float(np.linalg.eigvalsh(D @ V @ D)[-1])
                    lo = hi = min(1.0, 1.0 / ratio)
        results.append(
            {
                "canonical_id": item["canonical_id"],
                "weight": w["weight"],
                "lower": lo,
                "upper": hi,
            }
        )
    total = sum(x["weight"] for x in results)
    return {
        "lower_percent": 100 * sum(x["weight"] * x["lower"] for x in results) / total,
        "upper_percent": 100 * sum(x["weight"] * x["upper"] for x in results) / total,
        "targets": results,
    }
