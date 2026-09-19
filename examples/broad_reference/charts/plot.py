# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Plot frozen synthetic workload results without inferring biological sufficiency."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

EXPECTED_MANIFEST = "7bdb4dc26c0e4f168e340cc476de3c7ab050ce46c42b58305b04979d6c04e0ab"
CATEGORIES = [
    "State\ndepth",
    "Population\nprecision",
    "Within-person\nchange",
    "Digital\ntargets",
    "Neural\nobservation",
    "Randomized\ncontrasts",
    "Linked\npopulation",
    "Complementary\noperators",
    "Cortical\ncausal*",
]
COLORS = {"P": "#166D89", "F": "#BC4B25", "?": "#B88112", "–": "#E8EDF0"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def category(identity):
    if identity == "controlled-cortical-response":
        return 8
    if identity == "molecular-functional-complementarity":
        return 7
    if identity == "population-crossmodal-link":
        return 6
    if identity.startswith("randomized-input-"):
        return 5
    if identity.startswith("neural."):
        return 4
    if identity.startswith("digital."):
        return 3
    if identity.endswith((".time", ".annual")):
        return 2
    if identity.endswith(".population"):
        return 1
    if identity.endswith(".state"):
        return 0
    raise ValueError("Unmapped target: " + identity)


def matrix(rows, profiles):
    result = []
    for row in rows:
        targets = profiles[row["level"]]
        assert len(targets) == row["target_count"]
        assert set(row["failed"] + row["unknown"]) <= set(targets)
        states = []
        for index in range(len(CATEGORIES)):
            relevant = {name for name in targets if category(name) == index}
            states.append(
                "–"
                if not relevant
                else "F"
                if relevant.intersection(row["failed"])
                else "?"
                if relevant.intersection(row["unknown"])
                else "P"
            )
        result.append(states)
    return result


def panel(ax, values, labels, title):
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(len(values) - 0.5, -0.5)
    for y, row in enumerate(values):
        for x, status in enumerate(row):
            ax.add_patch(
                Rectangle(
                    (x - 0.45, y - 0.42),
                    0.9,
                    0.84,
                    facecolor=COLORS[status],
                    edgecolor="none",
                )
            )
            ax.text(
                x,
                y,
                status,
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color="white" if status != "–" else "#667782",
            )
    ax.set_xticks(range(9), CATEGORIES, fontsize=8.8)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=8)
    ax.set_yticks(range(len(labels)), labels, fontsize=9.5)
    ax.tick_params(axis="y", length=0, pad=12)
    ax.set_title(
        title,
        loc="left",
        x=-0.50,
        y=1.16,
        fontsize=13,
        fontweight="bold",
        color="#173246",
    )
    for spine in ax.spines.values():
        spine.set_visible(False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-packet", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.source_packet / "PACKAGE_MANIFEST.json"
    if sha(manifest_path) != EXPECTED_MANIFEST:
        raise ValueError("Frozen source manifest mismatch")
    manifest = json.loads(manifest_path.read_text())
    for record in manifest["files"]:
        name = record["path"]
        if Path(name).name != name:
            raise ValueError("Unsafe manifest path")
        file = args.source_packet / name
        if file.stat().st_size != record["bytes"] or sha(file) != record["sha256"]:
            raise ValueError("Source mismatch: " + name)
    data = json.loads((args.source_packet / "figure-data.json").read_text())
    declarations = json.loads(
        (args.source_packet / "profile-declarations.json").read_text()
    )
    profiles = {
        p["profile_id"].split(".")[0][2:]: [t["canonical_id"] for t in p["targets"]]
        for p in declarations
    }
    a = matrix(data["examples"], profiles)
    b = matrix(data["sensitivity"], profiles)
    assert len(a) == 14 and len(b) == 10
    labels = [
        "160 people · depth 16 → AB1",
        "160 people · depth 16 → AB2",
        "2112 people · depth 64 → AB1",
        "2112 people · depth 64 → AB2",
        "2 people · depth 1,000,000 → AB1",
        "100,000 people · depth 1 → AB1",
        "Depth 1,000,000 · ρ = .99 → AB1",
        "Redundant assignment arms → AB1",
        "No linked people → AB1",
        "Same daily phase only → AB1",
        "Neural observation absent → AB1",
        "Neural observation unknown → AB1",
        "No cortical assignment → neural child",
        "Controlled cortical assignment → child",
    ]
    sensitivity_labels = []
    for i, row in enumerate(data["sensitivity"]):
        condition = [
            "Baseline",
            "Measurement R: 4 → 8",
            "Between-person B: 1 → 2",
            "Occasion S: .25 → 1",
            "Repeat correlation ρ: 0 → .1",
        ][i // 2]
        sensitivity_labels.append(condition + " · AB" + row["level"])
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "svg.fonttype": "none",
            "svg.hashsalt": "anibench-broad-reference-figure-v1",
        }
    )
    fig, axes = plt.subplots(
        2, 1, figsize=(12.4, 12.6), gridspec_kw={"height_ratios": [14, 10]}
    )
    fig.subplots_adjust(left=0.36, right=0.975, top=0.80, bottom=0.13, hspace=0.48)
    panel(
        axes[0],
        a,
        labels,
        "A   Depth, population, timing and assignment impose different constraints",
    )
    panel(
        axes[1],
        b,
        sensitivity_labels,
        "B   The same witness designs fail when reference assumptions change",
    )
    fig.text(
        0.04,
        0.969,
        "Broad-reference candidate: conditional requirements",
        fontsize=19,
        weight="bold",
        color="#173246",
    )
    fig.text(
        0.04,
        0.941,
        "SYNTHETIC WORKLOAD  •  Not biological sufficiency or a rating of any real study",
        fontsize=11.2,
        weight="bold",
        color="#A34525",
    )
    fig.text(
        0.04,
        0.914,
        "Baseline: R = 4, B = 1, S = 0.25, independent repeats. All precision targets use likelihood information.",
        fontsize=10.2,
        color="#354C5C",
    )
    fig.text(
        0.04,
        0.89,
        "P = all required targets in the category pass     F = at least one fails     ? = unresolved     – = not required",
        fontsize=9.8,
        color="#354C5C",
    )
    fig.text(
        0.04,
        0.091,
        "Witness schedules: AB1, days 0/30 and two balanced groups; AB2, days 0/30/365 and four factorial groups.",
        fontsize=10,
        color="#354C5C",
    )
    fig.text(
        0.04,
        0.069,
        "Depth = effective independent reference repeats per coordinate per occasion when ρ = 0; correlated repeats provide less information.",
        fontsize=9.5,
        color="#354C5C",
    )
    fig.text(
        0.04,
        0.047,
        "*Cortical causality is an optional named child. Core neural columns concern observation. Missing neural evidence stays unknown.",
        fontsize=9.5,
        color="#354C5C",
    )
    fig.text(
        0.04,
        0.025,
        "Categories partition the frozen targets; digital/neural columns include their state, population and temporal targets. No scalar score.",
        fontsize=9.5,
        color="#354C5C",
    )
    args.out.mkdir(parents=True, exist_ok=False)
    metadata = {
        "Title": "AniBench broad-reference candidate: conditional workload outcomes",
        "Description": "Synthetic reference assumptions; not biologically calibrated sufficiency. SPDX-License-Identifier: Apache-2.0",
        "Creator": "ANI; plot.py",
        "Date": None,
    }
    fig.savefig(args.out / "broad-reference.svg", metadata=metadata)
    fig.savefig(
        args.out / "broad-reference.png",
        dpi=200,
        metadata={"Software": "AniBench synthetic reference figure"},
    )
    plt.close(fig)
    audit = {
        "contract": "anibench.broad-reference-figure.v1",
        "source_manifest_sha256": EXPECTED_MANIFEST,
        "source_figure_data_sha256": sha(args.source_packet / "figure-data.json"),
        "plot_script_sha256": sha(Path(__file__)),
        "matplotlib_version": matplotlib.__version__,
        "example_rows": 14,
        "sensitivity_rows": 10,
        "category_labels": CATEGORIES,
        "example_cells": a,
        "sensitivity_cells": b,
        "files": {
            name: sha(args.out / name)
            for name in ["broad-reference.svg", "broad-reference.png"]
        },
    }
    (args.out / "figure-metadata.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(
        json.dumps(
            {"example_rows": 14, "sensitivity_rows": 10, "files": list(audit["files"])}
        )
    )


if __name__ == "__main__":
    main()
