#!/usr/bin/env python3
"""Build deterministic method figures for the AniBench v2 manuscript.

The figures explain the benchmark contract.  They intentionally contain no trial
scores, trial ranks, or biological-validation results.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "anibench-v2-method-figures"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import (  # noqa: E402
    FancyArrowPatch,
    FancyBboxPatch,
    RegularPolygon,
)


INK = "#17232C"
MUTED = "#5E6A72"
ORANGE = "#FF9500"
BLUE = "#3E748D"
PALE_ORANGE = "#FFF2DE"
PALE_BLUE = "#EAF3F6"
PALE_GRAY = "#F3F5F6"
FIGURE_CREATOR = "AniBench v2 deterministic method-figure builder"


def _source_date_epoch(value: int | None) -> int:
    raw = str(value) if value is not None else os.environ.get("SOURCE_DATE_EPOCH")
    if raw is None:
        raise SystemExit("Provide --source-date-epoch or set SOURCE_DATE_EPOCH")
    try:
        epoch = int(raw)
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer Unix timestamp") from exc
    if epoch < 315532800:
        raise SystemExit("SOURCE_DATE_EPOCH must be on or after 1980-01-01")
    return epoch


def _timestamp(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _setup(width: float = 11.0, height: float = 6.4):
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _box(ax, xy, width, height, text, *, fill=PALE_GRAY, edge=INK, size=10, weight="normal"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        facecolor=fill,
        edgecolor=edge,
        linewidth=1.25,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=size,
        color=INK,
        weight=weight,
        linespacing=1.15,
    )
    return patch


def _arrow(ax, start, end, *, color=INK, width=1.4, style="-|>"):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=12,
            linewidth=width,
            color=color,
            connectionstyle="arc3,rad=0",
        )
    )


def _title(ax, title, subtitle):
    ax.text(0.02, 0.96, title, ha="left", va="top", fontsize=18, weight="bold", color=INK)
    ax.text(0.02, 0.905, subtitle, ha="left", va="top", fontsize=10.5, color=MUTED)


def _save(fig, output: Path, stem: str, *, source_date_epoch: int):
    output.mkdir(parents=True, exist_ok=True)
    timestamp = _timestamp(source_date_epoch)
    png = output / f"{stem}.png"
    svg = output / f"{stem}.svg"
    fig.savefig(
        png,
        dpi=240,
        bbox_inches="tight",
        pad_inches=0.08,
        # Public-boundary scans reject embedded raster metadata.  Explicitly
        # suppress Matplotlib's default Software tEXt chunk; provenance lives
        # in the hash-bound paper build receipt instead.
        metadata={"Software": None},
    )
    fig.savefig(
        svg,
        bbox_inches="tight",
        pad_inches=0.08,
        metadata={"Date": timestamp, "Creator": FIGURE_CREATOR},
    )
    os.utime(png, (source_date_epoch, source_date_epoch))
    os.utime(svg, (source_date_epoch, source_date_epoch))
    plt.close(fig)


def pipeline(output: Path, *, source_date_epoch: int):
    fig, ax = _setup()
    _title(
        ax,
        "Source-bound compilation, not a modality checklist",
        "Every numeric family output is downstream of declared geometry and an auditable authority chain.",
    )
    labels = [
        ("Source objects\nhashes + locators", PALE_GRAY),
        ("Participant-event\nhyperedges", PALE_BLUE),
        ("Observation +\ncovariance\noperators", PALE_BLUE),
        ("Target / nuisance\ninformation", PALE_ORANGE),
        ("Six family\nrecords", PALE_ORANGE),
        ("Pareto changes\n+ receipt", PALE_GRAY),
    ]
    xs = [0.015, 0.18, 0.345, 0.51, 0.675, 0.84]
    width = 0.135
    for index, ((label, fill), x) in enumerate(zip(labels, xs, strict=True)):
        _box(ax, (x, 0.48), width, 0.20, label, fill=fill, size=7.8, weight="bold")
        if index < len(labels) - 1:
            _arrow(ax, (x + width, 0.58), (xs[index + 1] - 0.008, 0.58), color=BLUE)
    ax.text(0.02, 0.37, "Fail-closed gates", fontsize=11, weight="bold", color=INK)
    gates = [
        "same event",
        "lineage unique",
        "typed missingness",
        "linked outcomes",
        "coherent stages",
        "canonical hashes",
    ]
    for idx, gate in enumerate(gates):
        x = 0.02 + idx * 0.163
        ax.text(x, 0.30, f"{idx + 1:02d}", fontsize=9, color=ORANGE, weight="bold")
        ax.text(x + 0.055, 0.255, gate, fontsize=7.8, color=MUTED, ha="center", va="top", wrap=True)
    ax.text(
        0.5,
        0.10,
        "No overall scalar  •  no caller-provided matrices  •  no rank from missing geometry",
        ha="center",
        va="center",
        fontsize=11,
        weight="bold",
        color=INK,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor=ORANGE, linewidth=1.4),
    )
    _save(
        fig,
        output,
        "figure_01_source_bound_pipeline",
        source_date_epoch=source_date_epoch,
    )


def family_map(output: Path, *, source_date_epoch: int):
    fig, ax = _setup(width=9.5, height=7.0)
    _title(
        ax,
        "Six non-interchangeable views of a human experiment",
        "A design is a vector of biological and experimental capabilities; comparison is family-specific or Pareto-based.",
    )
    center = (0.50, 0.49)
    radius = 0.245
    families = [
        ("Intensive", "one joint state event"),
        ("Extensive", "people × retained events"),
        ("Longitudinal", "within-person offsets\n+ span"),
        ("Causal", "policy + component\ncontrasts"),
        ("Personalized", "state-dependent decisions"),
        ("Transport", "measured context support"),
    ]
    angles = [90, 30, -30, -90, -150, 150]
    for idx, ((name, detail), degrees) in enumerate(zip(families, angles, strict=True)):
        angle = degrees * 3.141592653589793 / 180
        x = center[0] + radius * __import__("math").cos(angle)
        y = center[1] + radius * __import__("math").sin(angle)
        patch = RegularPolygon(
            (x, y),
            numVertices=6,
            radius=0.105,
            orientation=0,
            facecolor=PALE_ORANGE if idx % 2 == 0 else PALE_BLUE,
            edgecolor=INK,
            linewidth=1.25,
        )
        ax.add_patch(patch)
        ax.text(x, y + 0.017, name, ha="center", va="center", fontsize=9.8, weight="bold", color=INK)
        ax.text(x, y - 0.032, detail, ha="center", va="center", fontsize=7.0, color=MUTED, linespacing=1.05)
    _box(ax, (0.39, 0.405), 0.22, 0.17, "TRIAL\nINFORMATION\nGEOMETRY", fill="white", edge=ORANGE, size=10.4, weight="bold")
    ax.text(
        0.50,
        0.035,
        "Uncertainty, source binding, evidence lane, and reproducibility cut across every family.",
        ha="center",
        fontsize=10.2,
        color=MUTED,
    )
    _save(
        fig,
        output,
        "figure_02_six_family_map",
        source_date_epoch=source_date_epoch,
    )


def same_event(output: Path, *, source_date_epoch: int):
    fig, ax = _setup()
    _title(
        ax,
        "Same-event identity and redundancy control",
        "Independent biological directions can combine only inside one declared participant-event bundle with joint covariance.",
    )
    _box(ax, (0.03, 0.60), 0.18, 0.16, "Layer A\nparticipant set P\noffset t\nlineage L1", fill=PALE_BLUE, weight="bold")
    _box(ax, (0.03, 0.30), 0.18, 0.16, "Layer B\nparticipant set P\noffset t\nlineage L2", fill=PALE_BLUE, weight="bold")
    _arrow(ax, (0.21, 0.68), (0.31, 0.58), color=BLUE)
    _arrow(ax, (0.21, 0.38), (0.31, 0.52), color=BLUE)
    _box(
        ax,
        (0.31, 0.43),
        0.24,
        0.24,
        "Canonical event ID\n(P, t, event unit)\n+ one joint covariance\n+ lineage partition",
        fill=PALE_ORANGE,
        weight="bold",
    )
    _arrow(ax, (0.55, 0.55), (0.67, 0.55), color=ORANGE)
    _box(ax, (0.67, 0.57), 0.28, 0.17, "Accepted\none participant-event\ncombined conditional information", fill="#EAF7ED", weight="bold")
    _box(ax, (0.67, 0.28), 0.28, 0.17, "Rejected\nsplit bundle, conflicting lineage,\nor duplicate physical ancestry", fill="#FBEDEE", weight="bold")
    _arrow(ax, (0.55, 0.48), (0.67, 0.37), color="#9A3D45")
    ax.text(
        0.49,
        0.14,
        "A source-bound observer that opens a new biological direction multiplies remaining-volume reduction; renaming, splitting, or repeating a direction cannot.",
        ha="center",
        fontsize=10.5,
        color=INK,
        weight="bold",
    )
    _save(
        fig,
        output,
        "figure_03_same_event_antigaming",
        source_date_epoch=source_date_epoch,
    )


def evidence_lanes(output: Path, *, source_date_epoch: int):
    fig, ax = _setup()
    _title(
        ax,
        "Evidence lane changes the claim, not identical design geometry",
        "Capacity, realized acquisition, lawful access, and demonstrated model utility are different objects.",
    )
    lanes = [
        ("Design\nPreview", "declared geometry", PALE_BLUE),
        ("Registered\nProtocol", "frozen promise", PALE_BLUE),
        ("Realized", "retained events + QC", PALE_ORANGE),
        ("Accessible", "verified execution", PALE_ORANGE),
        ("Demonstrated", "held-out utility + nulls", PALE_GRAY),
    ]
    y = 0.68
    xs = [0.025, 0.22, 0.415, 0.61, 0.805]
    for idx, ((name, detail, fill), x) in enumerate(zip(lanes, xs, strict=True)):
        _box(ax, (x, y), 0.17, 0.15, f"{name}\n{detail}", fill=fill, size=7.4, weight="bold")
        if idx < len(lanes) - 1:
            _arrow(ax, (x + 0.17, y + 0.075), (xs[idx + 1] - 0.006, y + 0.075), color=MUTED)
    ax.text(0.5, 0.59, "Each transition requires its own source-bound receipt", ha="center", fontsize=9.5, color=MUTED)
    _box(ax, (0.08, 0.28), 0.34, 0.18, "Same protocol geometry\n= same design-capacity computation", fill="white", edge=BLUE, weight="bold")
    _box(ax, (0.58, 0.28), 0.34, 0.18, "Different lane\n= different authorized claim", fill="white", edge=ORANGE, weight="bold")
    _arrow(ax, (0.42, 0.37), (0.58, 0.37), color=INK, style="<->")
    ax.text(
        0.5,
        0.12,
        "Planned trials are not penalized for being planned; they also do not borrow realized, accessible, or demonstrated status.",
        ha="center",
        fontsize=10.3,
        color=INK,
        weight="bold",
    )
    _save(
        fig,
        output,
        "figure_04_evidence_lanes",
        source_date_epoch=source_date_epoch,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "figures")
    parser.add_argument("--source-date-epoch", type=int)
    args = parser.parse_args()
    epoch = _source_date_epoch(args.source_date_epoch)
    pipeline(args.out_dir, source_date_epoch=epoch)
    family_map(args.out_dir, source_date_epoch=epoch)
    same_event(args.out_dir, source_date_epoch=epoch)
    evidence_lanes(args.out_dir, source_date_epoch=epoch)


if __name__ == "__main__":
    main()
