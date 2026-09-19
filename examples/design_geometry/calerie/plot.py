# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Replay CALERIE's conditional design example and render its bound figure."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import replay


def render(output, source=None):
    replay.replay(output, source)
    requests = json.loads((output / "requests.json").read_text())
    receipts = json.loads((output / "receipts.json").read_text())
    rows = replay.comparison_rows(requests, receipts)
    model = {"residual_variance": 1.0, "yearly_correlation": 0.0}
    selected = [row for row in rows if row["model"] == model]
    metadata = {
        "version": "anibench.calerie-figure.v1",
        "evidence_kind": "published_collection_counts_with_hypothetical_noise_model",
        "source_manifest_sha256": replay.MANIFEST_SHA256,
        "source_sha256": replay.load_manifest()["source"]["sha256"],
        "chart_results_sha256": hashlib.sha256(
            (output / "chart-results.json").read_bytes()
        ).hexdigest(),
        "plot_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "implementation": replay.implementation(),
        "display_unit": "standardized_scalar_unit",
        "display_transform": "square_root_of_variance",
        "interval_semantics": "feasible_support_envelope_not_confidence_interval",
        "model": model,
        "rows": selected,
    }
    with plt.rc_context(
        {
            "font.family": ["DejaVu Sans", "sans-serif"],
            "font.size": 11,
            "svg.fonttype": "none",
            "svg.hashsalt": "anibench-calerie-v1",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": "#CBD3DD",
            "text.color": "#14263D",
            "axes.labelcolor": "#475569",
            "xtick.color": "#475569",
        }
    ):
        fig, axes = plt.subplots(1, 2, figsize=(12, 7), sharex=True)
        fig.patch.set_facecolor("#FFFFFF")
        fig.subplots_adjust(left=0.21, right=0.97, top=0.65, bottom=0.30, wspace=0.38)
        fig.text(
            0.045,
            0.94,
            "ANIBENCH / REAL-STUDY DESIGN EXAMPLE",
            fontsize=10,
            weight="bold",
            color="#39716B",
        )
        fig.text(
            0.045, 0.875, "More visits answer a different question", fontsize=24, weight="bold"
        )
        fig.text(
            0.045,
            0.825,
            "CALERIE collection counts · Two analysis designs · One explicit noise scenario",
            fontsize=12,
            color="#475569",
        )
        fig.text(0.045, 0.737, "MODEL-PREDICTED STANDARD ERROR", fontsize=10, weight="bold")
        titles = ["24-month change", "Midpoint curvature"]
        designs = ["endpoint_pair", "three_timepoints"]
        labels = ["Baseline + 24 months\n185 people", "All three visits\n179–183 people"]
        for index, ax in enumerate(axes):
            ax.set_title(titles[index], loc="left", pad=18, weight="bold", fontsize=14)
            for y, design in zip([1, 0], designs, strict=True):
                row = next(
                    r
                    for r in selected
                    if r["design_id"] == design
                    and r["estimand_id"] == replay.FRAME["estimand_ids"][index]
                )
                if row["variance_interval"] is None:
                    ax.text(0.012, y, "Not identifiable", va="center", fontsize=12, color="#8C5A30")
                    continue
                low, high = np.sqrt(row["variance_interval"])
                ax.barh(y, low, height=0.28, color="#DDEBE9" if y == 0 else "#E6EDF6")
                ax.plot(
                    [low, high],
                    [y, y],
                    color="#227C70" if y == 0 else "#41658C",
                    lw=7,
                    solid_capstyle="butt",
                )
                if low == high:
                    ax.plot([low], [y], "o", color="#41658C", ms=6)
                label = f"{low:.3f}" if low == high else f"{low:.3f}–{high:.3f}"
                ax.text(low / 2, y, label, ha="center", va="center", fontsize=12, weight="bold")
            ax.set_xlim(0, 0.26)
            ax.set_ylim(-0.65, 1.55)
            ax.set_xticks([0, 0.1, 0.2], ["0", "0.10", "0.20"])
            ax.set_yticks([1, 0], labels if index == 0 else ["", ""])
            ax.tick_params(axis="y", length=0, pad=12)
            ax.grid(axis="x", color="#EEF1F5", zorder=0)
            ax.set_axisbelow(True)
            ax.set_xlabel("Standardized units · lower is more precise", labelpad=12, fontsize=10)
        fig.text(
            0.045,
            0.208,
            "A midpoint identifies curvature. Requiring complete visits loses some participants;\n"
            "under this symmetric model it does not improve endpoint-change precision.",
            fontsize=12,
            linespacing=1.5,
            va="top",
        )
        fig.text(
            0.045,
            0.110,
            "Assumed scalar variance = 1; yearly correlation = 0. Bands reflect feasible participant overlap, not confidence intervals.\n"
            "Same population and scalar assumed. No treatment effects, calibrated DNAm-clock noise, or overall study score.\n"
            "Source: Waziry et al., Nature Aging (2023), doi:10.1038/s43587-022-00357-y. Figure: AniBench, CC BY 4.0.",
            fontsize=8.5,
            color="#526276",
            linespacing=1.4,
            va="top",
        )
        fig.savefig(
            output / "comparison.svg",
            metadata={"Date": None, "Description": json.dumps(metadata, sort_keys=True)},
        )
        fig.savefig(
            output / "comparison.png",
            dpi=170,
        )
        plt.close(fig)
    (output / "figure-metadata.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n"
    )
    return {"figure": "comparison.svg", "scenario": model, "source_replayed": source is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.out, args.source), sort_keys=True))
