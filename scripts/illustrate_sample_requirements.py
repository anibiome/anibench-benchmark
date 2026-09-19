# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Reproduce illustrative precision/power arithmetic; no calibrated biological targets."""

import json
import math
from statistics import NormalDist


def requirements(arms, rho, *, repeats=4, attrition=0.2, delta=0.3, halfwidth=0.15):
    """Equal arms; independent people; known unit variance; exchangeable repeats."""
    z = NormalDist().inv_cdf(1 - 0.05 / (2 * (arms - 1)))
    zpower = NormalDist().inv_cdf(0.90)
    variance = rho + (1 - rho) / repeats
    precision = 2 * arms * variance * z**2 / halfwidth**2
    power = 2 * arms * variance * (z + zpower) ** 2 / delta**2
    enrollment = math.ceil(max(precision, power) / (1 - attrition) / arms) * arms
    return {
        "arms": arms,
        "rho": rho,
        "retained_precision_requirement": precision,
        "retained_approximate_power_requirement": power,
        "enrollment_rounded_to_equal_arms": enrollment,
        "expected_simultaneous_ci_halfwidth": z
        * math.sqrt(2 * arms * variance / (enrollment * (1 - attrition))),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "status": "illustrative_normal_model_not_calibrated_biological_target",
                "assumptions": {
                    "single_reading_variance": 1,
                    "repeats_per_person": 4,
                    "noninformative_attrition_fraction": 0.2,
                    "effect_in_single_reading_sd_units": 0.3,
                    "ci_halfwidth_in_same_units": 0.15,
                    "familywise_alpha": 0.05,
                    "approximate_marginal_power_per_contrast": 0.9,
                    "multiplicity": "Bonferroni across K-1 active-versus-control contrasts",
                    "excludes": "clustering, carryover, informative dropout, treatment-time interactions",
                },
                "rows": [requirements(k, rho) for k in (2, 3, 5) for rho in (0, 0.5, 0.9)],
            },
            indent=2,
        )
    )
