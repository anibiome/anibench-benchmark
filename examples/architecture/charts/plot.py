# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Source-bound publication figures; no cross-entity totals or implied completeness."""

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PIL import Image

TEAL = "#176b75"
AMBER = "#a56917"
INK = "#172c37"
MUTED = "#50636d"
GRID = "#dce4e7"


def main(packet, out):
    raw = packet.read_bytes()
    data = json.loads(raw)
    assert data["schema_version"] == "anibench.public-study-architecture.v1"
    digest = hashlib.sha256(raw).hexdigest()
    for source in data["sources"].values():
        if "scope" in source:
            source["scope"] = source["scope"].replace("; historical_alias_unresolved", "")
    studies = data["studies"]
    facts = [(s, f) for s in studies for f in s["numeric_facts"]]
    assert len(facts) == 21 and sum(len(s["coverage"]) for s in studies) == 30
    source_ids = list(dict.fromkeys(f["source"]["source_id"] for _, f in facts))
    refs = {id: i + 1 for i, id in enumerate(source_ids)}
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.labelcolor": MUTED,
            "text.color": INK,
            "axes.edgecolor": GRID,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "svg.fonttype": "none",
            "svg.hashsalt": digest,
            "savefig.facecolor": "white",
        }
    )
    out.mkdir(exist_ok=False)
    figures = []

    def value(f):
        prefix = {"approximate": "≈", "strict_lower_bound": ">"}.get(f["precision"], "")
        return prefix + format(f["value"], ",g")

    def ref(f):
        return f"[{refs[f['source']['source_id']]}]"

    def label(text, width):
        return "\n".join(textwrap.wrap(text, width))

    def title(fig, n, heading, sub):
        fig.text(
            0.06,
            0.97,
            "ANIBENCH  /  SOURCE-REPORTED ARCHITECTURE",
            fontsize=10,
            color=TEAL,
            weight="bold",
        )
        fig.text(0.06, 0.93, heading, fontsize=21, weight="bold")
        fig.text(0.06, 0.895, sub, fontsize=11, color=MUTED)
        fig.text(0.94, 0.97, str(n), ha="right", fontsize=10, color=MUTED)

    def save(fig, name, ids, extra):
        provenance = {
            "source_packet_sha256": digest,
            "selected_fact_ids": ids,
            "source_ids": source_ids,
            "scope": data["claim_scope"],
            **extra,
        }
        fig.savefig(
            out / (name + ".svg"),
            metadata={
                "Title": name.replace("-", " "),
                "Description": json.dumps(provenance, sort_keys=True),
                "Date": None,
            },
        )
        fig.savefig(
            out / (name + ".png"),
            dpi=180,
            metadata={"Software": "AniBench scientific source figure"},
        )
        with Image.open(out / (name + ".png")) as im:
            assert "Description" not in im.info
        figures.append(
            {
                "name": name,
                **provenance,
                "artifacts": {
                    ext: hashlib.sha256((out / (name + "." + ext)).read_bytes()).hexdigest()
                    for ext in ["svg", "png"]
                },
            }
        )
        plt.close(fig)

    # Population: source order, log scale to preserve small and large cohort readability.
    pop = [(s, f) for s, f in facts if f["panel"] == "population"]
    fig = plt.figure(figsize=(12, 11.4))
    title(
        fig,
        1,
        "Who was observed — and what was reported",
        "Source-defined populations and subsets; no single enrollment denominator covers every modality.",
    )
    ax = fig.add_axes([0.41, 0.52, 0.48, 0.315])
    ax.set_xscale("log")
    ax.set_xlim(20, 1e6)
    ax.set_ylim(-0.6, len(pop) - 0.4)
    ax.invert_yaxis()
    ax.set_yticks([])
    ax.set_xticks(
        [100, 1000, 10000, 100000, 1000000], ["100", "1,000", "10,000", "100,000", "1,000,000"]
    )
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.set_xlabel("People (logarithmic axis)", labelpad=9)
    for i, (s, f) in enumerate(pop):
        short = s["name"].replace("Human Phenotype Project", "Human Phenotype Project¹")
        ax.text(
            -0.73,
            i,
            short + "\n" + f["label"],
            transform=ax.get_yaxis_transform(),
            va="center",
            fontsize=10.2,
            linespacing=1.35,
        )
        marker = ">" if f["precision"] == "strict_lower_bound" else "o"
        point = ax.scatter(f["value"], i, s=58, color=TEAL, marker=marker, zorder=3)
        point.set_url(data["sources"][f["source"]["source_id"]]["url"])
        ax.annotate(
            value(f) + " " + ref(f),
            (f["value"], i),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=10.2,
            weight="bold",
        )
    fig.text(0.06, 0.855, "A   Population / subset support", fontsize=13, weight="bold")
    fig.text(
        0.06,
        0.457,
        "≈ Rounded source value.  > Strict source lower bound; triangle marks the bound, not an exact count.",
        fontsize=9.5,
        color=MUTED,
    )
    fig.text(
        0.06,
        0.435,
        "Enrolled, completed, assay-subset and imaging counts are distinct. ELITE has no public numeric count in this packet.",
        fontsize=9.5,
        color=MUTED,
    )
    # Categorical matrix: symbols and colors, never a sum.
    domains = ["molecular", "digital", "functional", "cognitive", "neural", "perturbation"]
    cx = fig.add_axes([0.27, 0.165, 0.65, 0.19])
    cx.set_xlim(-0.5, 5.5)
    cx.set_ylim(4.5, -0.5)
    cx.set_xticks(
        range(6), ["Molecular", "Digital", "Functional", "Cognitive", "Neural", "Perturbation"]
    )
    cx.xaxis.tick_top()
    cx.tick_params(axis="both", length=0, pad=10)
    cx.set_yticks(range(5), [s["name"] for s in studies])
    cx.spines["bottom"].set_visible(False)
    fig.text(
        0.06, 0.392, "B   Reported presence, not complete coverage", fontsize=13, weight="bold"
    )
    for i, s in enumerate(studies):
        for j, domain in enumerate(domains):
            c = next(c for c in s["coverage"] if c["domain"] == domain)
            state = c["state"]
            marker, color, size = {
                "reported_present": ("o", TEAL, 135),
                "source_described": ("D", AMBER, 100),
                "unreported": ("_", "#8e9da4", 115),
            }[state]
            cx.scatter(j, i, marker=marker, s=size, color=color, zorder=3)
        cx.axhline(i + 0.5, color=GRID, lw=0.6)
    fig.text(
        0.06,
        0.124,
        "●  Reported in publication / resource     ◆  Official description only     —  Unreported in reviewed material; not absent",
        fontsize=10,
        color=MUTED,
    )
    notes = "Digital includes self-report (iPOP); functional includes metabolic challenges. UK Biobank perturbation denotes a subset exercise challenge, not an assigned therapy. Neural means source-described brain measurement; cognitive tests do not establish neural sensing."
    fig.text(0.06, 0.103, label(notes, 147), fontsize=9, color=MUTED, va="top", linespacing=1.5)
    fig.text(
        0.06,
        0.039,
        "¹ HPP counts: July 2025 abstract. ELITE: public description, not verified collection.",
        fontsize=9,
        color=MUTED,
    )
    fig.text(
        0.06,
        0.018,
        "Source packet SHA-256 "
        + digest[:20]
        + "…  •  Full locators, source URLs and denominator notes: metadata.json",
        fontsize=8.5,
        color=MUTED,
    )
    save(
        fig,
        "01-populations-and-coverage",
        [f["fact_id"] for _, f in pop],
        {
            "coverage_cells": [
                {"study_id": s["study_id"], "domain": c["domain"], "state": c["state"]}
                for s in studies
                for c in s["coverage"]
            ]
        },
    )
    # Native molecular entities: independent panels, no shared numerical scale.
    fig = plt.figure(figsize=(12, 11.4))
    title(
        fig,
        2,
        "Measurement quantities are not interchangeable",
        "Separate entity inventories and timing statements; neither panel measures independent biological information.",
    )
    fig.text(
        0.06,
        0.854,
        "C   Molecular inventories — independent axes and units",
        fontsize=13,
        weight="bold",
    )
    entities = [
        ("proteins", "Unique / reported proteins"),
        ("transcripts", "PBMC transcripts"),
        ("metabolites", "Plasma metabolites"),
        ("cytokines_growth_factors", "Cytokines / growth factors"),
        ("glycan_peaks", "Measured glycan peaks"),
        ("derived_glycan_traits", "Derived glycan traits"),
    ]
    mol = [(s, f) for s, f in facts if f["panel"] == "molecular"]
    for i, (entity, heading) in enumerate(entities):
        rows = [(s, f) for s, f in mol if f["entity"] == entity]
        col = i % 2
        row = i // 2
        a = fig.add_axes([0.08 + col * 0.47, 0.702 - row * 0.132, 0.35, 0.075])
        a.set_title(heading, loc="left", fontsize=11.5, weight="bold", pad=16)
        maximum = max(f["value"] for _, f in rows)
        a.set_xlim(0, maximum * 1.4)
        a.set_ylim(-0.5, len(rows) + 0.02)
        a.invert_yaxis()
        a.set_yticks([])
        a.xaxis.set_major_locator(MaxNLocator(3, integer=True))
        a.xaxis.set_major_formatter(FuncFormatter(lambda v, p: format(v, ",g")))
        a.tick_params(labelsize=9)
        a.grid(axis="x", color=GRID)
        a.set_axisbelow(True)
        for j, (s, f) in enumerate(rows):
            p = a.scatter(f["value"], j, color=TEAL, s=50, zorder=3)
            p.set_url(data["sources"][f["source"]["source_id"]]["url"])
            a.annotate(
                value(f) + " " + ref(f),
                (f["value"], j),
                xytext=(7, 0),
                textcoords="offset points",
                va="center",
                fontsize=10.3,
                weight="bold",
            )
            a.text(
                0.01,
                j + 0.43,
                s["name"],
                transform=a.get_yaxis_transform(),
                fontsize=9.2,
                color=MUTED,
            )
    fig.text(
        0.06,
        0.394,
        "Protein panels use different assay technologies. Source-wide inventories do not imply complete measurements in each person.",
        fontsize=9.5,
        color=MUTED,
    )
    fig.text(
        0.06,
        0.374,
        "Glycan peaks may contain multiple structures; derived traits are calculated features, not additional independent acquisitions.",
        fontsize=9.5,
        color=MUTED,
    )
    fig.text(
        0.06,
        0.33,
        "D   Timing and repetition — distinct source meanings",
        fontsize=13,
        weight="bold",
    )
    time = [(s, f) for s, f in facts if f["panel"] == "timing"]
    ta = fig.add_axes([0.06, 0.12, 0.88, 0.18])
    ta.axis("off")
    unit = {"visits_per_participant": "visits / person", "treatment_sessions": "treatment sessions"}
    cell = [
        [s["name"], f["label"], value(f) + " " + unit.get(f["unit"], f["unit"]) + " " + ref(f)]
        for s, f in time
    ]
    table = ta.table(
        cellText=cell,
        colLabels=["Study", "Source quantity", "Reported value"],
        colWidths=[0.23, 0.47, 0.30],
        loc="upper left",
        cellLoc="left",
        colLoc="left",
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, col), c in table.get_celld().items():
        c.set_edgecolor(GRID)
        c.set_linewidth(0.6)
        c.PAD = 0.06
        c.set_facecolor("#eef4f5" if row == 0 else "white")
        c.set_text_props(color=INK, weight="bold" if row == 0 else "normal")
    fig.text(
        0.06,
        0.087,
        "Visit medians, sampling intervals, regimen spans, treatment sessions and wear windows are not a common “duration” axis.",
        fontsize=9.4,
        color=MUTED,
    )
    fig.text(
        0.06,
        0.066,
        "UK Biobank wear window is for a subset. CIRCULATE treatment sessions are not sampling occasions. No values were imputed.",
        fontsize=9.4,
        color=MUTED,
    )
    source_names = {
        "PMC6666404": "iPOP/iHMP",
        "PMC12341816": "CIRCULATE TPE",
        "UKB_TYPES": "UK Biobank resource",
        "PMC10567551": "UKB-PPP",
        "hpp-nature-medicine-2025-abstract": "Human Phenotype Project",
    }
    used = "  ·  ".join("[" + str(refs[k]) + "] " + source_names[k] for k in source_ids)
    fig.text(
        0.06,
        0.042,
        label("Sources: " + used, 160),
        fontsize=8,
        color=MUTED,
        va="top",
        linespacing=1.4,
    )
    save(fig, "02-entities-and-timing", [f["fact_id"] for _, f in mol + time], {})
    metadata = {
        "source_packet_filename": packet.name,
        "source_packet_sha256": digest,
        "plot_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "claim_scope": data["claim_scope"],
        "figures": figures,
        "numeric_facts": [
            {"study_id": s["study_id"], "study_name": s["name"], **f} for s, f in facts
        ],
        "coverage": [{"study_id": s["study_id"], **c} for s in studies for c in s["coverage"]],
        "sources": data["sources"],
        "rendering": {
            "matplotlib": matplotlib.__version__,
            "PNG_dpi": 180,
            "PNG_Description_metadata": False,
            "ordering": "source packet order; not numerical rank",
            "transformations": "Population axis logarithmic; molecular entity axes separate and linear; numeric values unchanged; no cross-unit totals.",
        },
        "limitations": [
            "Source-specific denominators, assay technologies, completeness and source versions differ.",
            "Presence is not participant completeness, quality or functional/neural equivalence.",
            "HPP abstract-only July2025 counts.",
            "ELITE presence only public description; no proprietary values used.",
            "Figure uses packet bytes, not an independent fresh source acquisition.",
        ],
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(
        json.dumps(
            {
                "figures": len(figures),
                "numeric_facts": len(facts),
                "coverage_cells": 30,
                "packet_sha256": digest,
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    main(a.packet, a.out)
