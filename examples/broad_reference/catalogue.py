# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Generate explicit synthetic coordinate registry; no biological assay mapping."""

import json
from pathlib import Path

from prototype import DOMAINS

roles = {
    "genomic": "Immutable inherited-context reference covariate, not an expression or treatment response",
    "transcriptomic": "Synthetic transcript-abundance layer mode; no actual gene or tissue nominated",
    "proteomic": "Synthetic protein-abundance layer mode; no actual protein nominated",
    "metabolomic": "Synthetic metabolite-abundance layer mode; no actual metabolite nominated",
    "functional": "Synthetic physiological function mode; no actual organ assay nominated",
    "cognitive": "Synthetic task-performance mode; no actual cognitive construct nominated",
    "neural": "Synthetic neural observation mode, electrical base / spatial-hemodynamic extension; no physiological equivalence asserted",
    "digital": "Coefficient of a synthetic continuously varying channel in the frozen 24-hour Fourier basis",
}
rows = []
for band in ["base", "extension"]:
    for domain, dimension in DOMAINS.items():
        for index in range(dimension):
            basis = (
                [
                    "1",
                    "sqrt(2)*cos(2*pi*t/24)",
                    "sqrt(2)*sin(2*pi*t/24)",
                    "cos(4*pi*t/24)",
                ][index]
                if domain == "digital"
                else None
            )
            rows.append(
                {
                    "coordinate_id": f"{domain}.{band}.coordinate-{index}",
                    "authority": "explicitly synthetic reference role, not empirically validated biology",
                    "role": roles[domain],
                    "band": band,
                    "domain": domain,
                    "estimand": f"x[{index}] of {domain}.{band} latent reference vector",
                    "units": "frozen standardized synthetic reference unit",
                    "immutable": domain == "genomic",
                    "temporal_contrast_admitted": domain != "genomic",
                    "reference_operator": basis
                    or f"row e_{index}: direct synthetic coordinate observation",
                    "extension_identity": "distinct declared reference block; copied measurements cannot instantiate this block",
                    "biological_source_mapping": None,
                    "actual_study_admission": "not admitted without separately reviewed source-bound observable, normalization, operator and noise mapping",
                }
            )
if __name__ == "__main__":
    path = Path(__file__).with_name("coordinate_catalogue.json")
    with path.open("x") as stream:
        json.dump(
            {
                "contract": "anibench.synthetic-coordinate-catalogue.v1",
                "coordinates": rows,
            },
            stream,
            indent=2,
        )
        stream.write("\n")
