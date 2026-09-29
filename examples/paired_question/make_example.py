# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Generate a wholly synthetic reference; no human data or adopted AB targets."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from anibench.paired_question_v1 import digest


def example():
    coordinates = [
        {"id": "molecule_a", "unit": "mmol/L", "domain": "molecular",
         "definition": "Fictional circulating molecular concentration A"},
        {"id": "molecule_b", "unit": "mmol/L", "domain": "molecular",
         "definition": "Fictional circulating molecular concentration B"},
        {"id": "grip_force", "unit": "kg-force", "domain": "functional",
         "definition": "Independently measured scalar grip force in this fictional experiment"},
    ]
    question = {
        "contract": "anibench.paired-biological-question.v1",
        "question_id": "synthetic_molecular_context_and_grip.v1",
        "question": "What do linked molecular observations add to measurement of grip and its change?",
        "population_scope": "Independent people from an invented homogeneous Gaussian population",
        "coordinates": coordinates, "occasions_days": [0, 365],
        "tolerances": {
            "molecular_state": [0.02, 0.02], "function_state": [2.0],
            "molecular_change": [0.025, 0.025], "function_change": [3.0],
            "molecular_mean_change": [0.005, 0.005], "function_mean_change": [0.5],
            "change_cross_covariance": [0.075, 0.075], "controlled_function_effect": [1.0],
        },
        "tolerance_authority": "Invented software example; no clinical threshold or adopted AB reference",
        "functional_operator": "Direct scalar force reading with stipulated additive unbiased error",
    }
    a = np.eye(6)
    for i in (0, 1):
        a[i + 3, i], a[i + 3, i + 3] = 0.7, np.sqrt(0.51)
    a[5, :] = [0.5, 0.3, 0.6, 0, 0, np.sqrt(0.30)]
    scales = np.asarray([0.05, 0.05, 10.0] * 2)
    b = (a @ a.T) * scales[:, None] * scales[None, :]
    r = np.diag((0.2 * scales) ** 2)
    scenario = {
        "question_sha256": digest(question), "biological_covariance": b.tolist(),
        "measurement_error_covariance": r.tolist(), "error_covariance_treated_as_known": True,
        "assumptions": ["Wholly invented Gaussian reference, not a named human study",
                        "Independent people; additive error independent of biological state",
                        "Known error covariance; homogeneous paired measurements and common arm covariance"],
    }
    design = {
        "question_sha256": digest(question), "lifecycle": "hypothetical",
        "n_independent_complete": 256, "closed_acquisition_inventory": True,
        "observations": [{"physical_id": f"synthetic-{c['id']}-{t}", "coordinate_id": c["id"],
                          "occasion_index": t, "qualified": True}
                         for t in (0, 1) for c in coordinates],
        "controlled_arm_counts": [128, 128],
        "support": {key: True for key in (
            "operator_valid", "zero_mean_measurement_error", "independent_measurement_error",
            "reference_model_applicable", "independent_people", "declared_population",
            "paired_occasions", "cross_domain_linkage", "independently_measured_function",
            "gaussian_reference", "prediction_time_order", "documented_exposure",
            "exposure_aligned_window", "controlled_assignment_identified", "collection_verified",
        )},
        "metadata": {"name": "Synthetic example", "ethics": "unknown", "publication": "unpublished"},
    }
    return {"contract": "anibench.paired-question-input.v1", "question": question,
            "scenario": scenario, "design": design}


if __name__ == "__main__":
    destination = Path(__file__).with_name("input.json")
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(example(), handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
