# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Native 6.5-inch paper plates from public frozen JSON; no biological rescoring."""

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator

EXPECTED_INPUT_SHA256 = {
    "architecture": "881916b01f134c061ffab62580f858fc45e0ea7c14da8a6c2f0b1f73f5ef1108",
    "reference": "07c504463cc95d40738eed16547c523f3dfe7940fe7c2b9a8b1b9147018b4653",
    "profiles": "0ecb5abf8fb886b480ba5b0eb6149560b1ff90087e329cf1e5934185497744ea",
}

TEAL = "#176b75"
INK = "#172c37"
MUTED = "#50636d"
GRID = "#dce4e7"
COLORS = {"P": "#166D89", "F": "#BC4B25", "?": "#B88112", "–": "#E8EDF0"}
DOMAINS = ["molecular", "digital", "functional", "cognitive", "neural", "perturbation"]
CATS = [
    "State",
    "Pop.",
    "Time",
    "Digital",
    "Neural",
    "Causal",
    "Linked",
    "Joint",
    "Cortical*",
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wrap(s, n=88):
    return "\n".join(textwrap.wrap(s, n, break_long_words=False))


def val(f):
    return {"approximate": "≈ ", "strict_lower_bound": "> "}.get(
        f["precision"], ""
    ) + format(f["value"], ",g")


def category(s):
    if s == "controlled-cortical-response":
        return 8
    if s == "molecular-functional-complementarity":
        return 7
    if s == "population-crossmodal-link":
        return 6
    if s.startswith("randomized-input-"):
        return 5
    if s.startswith("neural."):
        return 4
    if s.startswith("digital."):
        return 3
    if s.endswith((".time", ".annual")):
        return 2
    if s.endswith(".population"):
        return 1
    if s.endswith(".state"):
        return 0
    raise ValueError(s)


def main(architecture, reference, profiles, out):
    a = json.loads(architecture.read_bytes())
    b = json.loads(reference.read_bytes())
    p = json.loads(profiles.read_bytes())
    assert a["schema_version"] == "anibench.public-study-architecture.v1"
    assert b["contract"] == "anibench.broad-reference-figure-data.v1"
    inputs = {
        "architecture": sha(architecture),
        "reference": sha(reference),
        "profiles": sha(profiles),
    }
    if inputs != EXPECTED_INPUT_SHA256:
        raise ValueError(
            "Input bytes differ from the reviewed frozen plate sources; review new labels and regenerate the contract first"
        )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": hashlib.sha256(
                json.dumps(inputs, sort_keys=True).encode()
            ).hexdigest(),
            "savefig.facecolor": "white",
        }
    )
    out.mkdir(parents=True, exist_ok=False)
    receipts = []

    def start(title, subtitle, height=6.5):
        fig = plt.figure(figsize=(6.5, height))
        fig.text(0.04, 0.965, title, fontsize=14, weight="bold", va="top")
        fig.text(0.04, 0.905, wrap(subtitle, 87), fontsize=9, va="top", linespacing=1.4)
        return fig

    def note(fig, text, y=0.08):
        fig.text(0.04, y, wrap(text, 97), fontsize=8, va="top", linespacing=1.4)

    def save(fig, name, evidence):
        assert abs(fig.get_figwidth() - 6.5) < 1e-10
        for artist in fig.findobj(match=matplotlib.text.Text):
            if artist.get_text():
                assert artist.get_fontsize() >= 8, (name, artist.get_text())
        receipt = {
            "id": name,
            "width_inches": 6.5,
            "height_inches": fig.get_figheight(),
            "minimum_body_label_pt": 9,
            "minimum_notes_pt": 8,
            "input_sha256": inputs,
            "evidence": evidence,
        }
        fig.savefig(
            out / (name + ".svg"),
            metadata={
                "Title": name,
                "Description": json.dumps(receipt, sort_keys=True),
                "Date": None,
            },
        )
        fig.savefig(
            out / (name + ".png"),
            dpi=180,
            metadata={"Software": "AniBench paper plates"},
        )
        receipt["artifacts"] = {
            ext: sha(out / (name + "." + ext)) for ext in ["svg", "png"]
        }
        receipts.append(receipt)
        plt.close(fig)

    studies = a["studies"]
    facts = [(s, f) for s in studies for f in s["numeric_facts"]]
    # Plate 1: two-line row labels use margin width; bounds are explicit text/marks.
    pop = [(s, f) for s, f in facts if f["panel"] == "population"]
    fig = start(
        "Population and subset support",
        "Source-reported people; enrollment, completion and assay subsets are distinct.",
        6.5,
    )
    ax = fig.add_axes([0.43, 0.22, 0.51, 0.55])
    ax.set_xscale("log")
    ax.set_xlim(20, 2e6)
    ax.set_ylim(7.6, -0.6)
    ax.set_yticks([])
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.set_xticks([100, 10000, 1000000], ["100", "10,000", "1,000,000"])
    ax.set_xlabel("People · logarithmic axis")
    for i, (s, f) in enumerate(pop):
        name = s["name"].replace("Human Phenotype Project", "HPP")
        label = f["label"].replace(" by July 2025", " (Jul 2025)")
        fig.text(
            0.04,
            0.77 - (i + 0.6) / 8.2 * 0.55,
            name + "\n" + label,
            fontsize=9,
            va="center",
            linespacing=1.3,
        )
        marker = ">" if f["precision"] == "strict_lower_bound" else "o"
        ax.scatter(
            f["value"],
            i,
            marker=marker,
            s=30,
            facecolors="white" if f["precision"] == "approximate" else TEAL,
            edgecolors=TEAL,
            zorder=3,
        )
        ax.annotate(
            val(f),
            (f["value"], i),
            xytext=(-6 if f["value"] >= 500000 else 5, 0),
            ha="right" if f["value"] >= 500000 else "left",
            textcoords="offset points",
            fontsize=9,
            va="center",
        )
    note(
        fig,
        "≈ Rounded value; > strict lower bound, not an exact count. Groups may overlap; do not add them. HPP = Human Phenotype Project (July 2025 abstract). ELITE has no numeric population in this packet.",
        0.14,
    )
    save(
        fig,
        "01-population",
        {"numeric_facts": [{"study_id": s["study_id"], **f} for s, f in pop]},
    )
    # Plate 2: presence only, transposed to give every domain a full readable word.
    fig = start(
        "Which observations are documented?",
        "Source-reported coverage; no cell establishes complete participant coverage.",
        6.3,
    )
    ax = fig.add_axes([0.22, 0.30, 0.73, 0.45])
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(5.5, -0.5)
    ax.set_xticks(
        range(5), ["iPOP /\niHMP", "CIRCULATE\nTPE", "UK\nBiobank", "HPP", "ELITE"]
    )
    ax.xaxis.tick_top()
    ax.set_yticks(
        range(6),
        ["Molecular", "Digital", "Functional", "Cognitive", "Neural", "Perturbation"],
    )
    ax.tick_params(length=0, pad=9)
    for i, s in enumerate(studies):
        for j, dom in enumerate(DOMAINS):
            c = next(c for c in s["coverage"] if c["domain"] == dom)
            m, color = {
                "reported_present": ("o", TEAL),
                "source_described": ("D", "#a56917"),
                "unreported": ("_", "#87939b"),
            }[c["state"]]
            ax.scatter(i, j, marker=m, s=72, color=color)
    for j in range(7):
        ax.axhline(j - 0.5, color=GRID, lw=0.6)
    note(
        fig,
        "● Reported in publication/resource   ◆ Official description only\n— Unreported in reviewed material, not absent.",
        0.23,
    )
    note(
        fig,
        "Digital includes iPOP self-report. Functional includes metabolic challenges. UK Biobank perturbation is subset exercise testing, not assigned therapy. Neural means brain measurement; cognitive tests alone do not establish neural sensing. HPP is abstract-only; ELITE is public description.",
        0.15,
    )
    save(
        fig,
        "02-coverage",
        {
            "coverage": [
                {"study_id": s["study_id"], **c} for s in studies for c in s["coverage"]
            ]
        },
    )
    # Plate 3: one entity per facet, fixed independent axes, all figures use exactly source values.
    mol = [(s, f) for s, f in facts if f["panel"] == "molecular"]
    fig = start(
        "Molecular entities stay separate",
        "Each panel has its own axis. Inventories do not measure independent information.",
        7.1,
    )
    entities = [
        ("proteins", "Proteins"),
        ("transcripts", "PBMC transcripts"),
        ("metabolites", "Plasma metabolites"),
        ("cytokines_growth_factors", "Cytokines / growth factors"),
        ("glycan_peaks", "Glycan peaks"),
        ("derived_glycan_traits", "Derived glycan traits"),
    ]
    for i, (ent, title) in enumerate(entities):
        group = [(s, f) for s, f in mol if f["entity"] == ent]
        ax = fig.add_axes([0.09 + (i % 2) * 0.48, 0.655 - (i // 2) * 0.21, 0.37, 0.105])
        ax.set_title(title, fontsize=10, loc="left", pad=21)
        maximum = max(f["value"] for s, f in group)
        ax.set_xlim(0, maximum * 1.40)
        ax.set_ylim(-0.6, len(group) + 0.45)
        ax.invert_yaxis()
        ax.set_yticks([])
        ax.xaxis.set_major_locator(MaxNLocator(2, integer=True))
        ax.grid(axis="x", color=GRID)
        ax.set_axisbelow(True)
        for j, (s, f) in enumerate(group):
            ax.scatter(f["value"], j, s=25, color=TEAL)
            ax.annotate(
                val(f),
                (f["value"], j),
                xytext=(5, 0),
                textcoords="offset points",
                fontsize=9,
                va="center",
            )
            ax.text(
                0.01,
                j + 0.65,
                s["name"],
                transform=ax.get_yaxis_transform(),
                fontsize=9,
                va="center",
            )
    note(
        fig,
        "Assay technologies and source-wide completeness differ. Glycan peaks can contain multiple structures; calculated traits are not extra independent acquisitions. Values do not establish every target in every person.",
        0.12,
    )
    save(
        fig,
        "03-molecular",
        {"numeric_facts": [{"study_id": s["study_id"], **f} for s, f in mol]},
    )
    # Plate 4: timeline statements are incompatible units; table makes no common score.
    timing = [(s, f) for s, f in facts if f["panel"] == "timing"]
    fig = start(
        "Timing and repetition retain their meaning",
        "A median span, a sampling interval, treatments and sensor wear are different quantities.",
        5.7,
    )
    ys = [0.75 - i * 0.085 for i in range(len(timing))]
    for y, (s, f) in zip(ys, timing):
        label = f["label"].replace(
            "Typical healthy-sampling interval", "Typical healthy interval"
        )
        unit = {
            "visits_per_participant": "visits / person",
            "treatment_sessions": "treatments",
        }.get(f["unit"], f["unit"])
        fig.text(0.04, y, s["name"], fontsize=9, weight="bold")
        fig.text(0.04, y - 0.030, label, fontsize=9)
        fig.text(0.74, y, val(f) + " " + unit, fontsize=9, ha="left")
        fig.lines.append(
            plt.Line2D(
                [0.04, 0.96],
                [y - 0.048, y - 0.048],
                transform=fig.transFigure,
                color=GRID,
                lw=0.7,
            )
        )
    note(
        fig,
        "Span and visit counts are medians; the healthy interval is a typical schedule. TPE rows describe distinct regimens. UK Biobank wear is a subset schedule. No individual follow-up duration or treatment exposure is imputed.",
        0.17,
    )
    save(
        fig,
        "04-timing",
        {"numeric_facts": [{"study_id": s["study_id"], **f} for s, f in timing]},
    )
    # Broad matrices: exact task-category conjunction, with unknown retained.
    bylevel = {
        x["profile_id"].split(".")[0].removeprefix("AB"): [
            t["canonical_id"] for t in x["targets"]
        ]
        for x in p
    }
    labels = [
        "160 × 16 → AB1",
        "160 × 16 → AB2",
        "2,112 × 64 → AB1",
        "2,112 × 64 → AB2",
        "2 people × 1,000,000",
        "100,000 people × 1",
        "1,000,000 repeats; ρ=.99",
        "Redundant arms",
        "No linked people",
        "Same daily phase",
        "Neural absent",
        "Neural unknown",
        "No cortical assignment*",
        "Cortical assignment*",
    ]
    for name, rows, rowlabels, title in [
        ("05-reference-examples", b["examples"], labels, "Which requirements fail?"),
        (
            "06-reference-sensitivity",
            b["sensitivity"],
            [
                "Baseline · AB1",
                "Baseline · AB2",
                "R: 4 → 8 · AB1",
                "R: 4 → 8 · AB2",
                "B: 1 → 2 · AB1",
                "B: 1 → 2 · AB2",
                "S: .25 → 1 · AB1",
                "S: .25 → 1 · AB2",
                "ρ: 0 → .1 · AB1",
                "ρ: 0 → .1 · AB2",
            ],
            "Model assumptions change attainment",
        ),
    ]:
        fig = start(
            title,
            "SYNTHETIC REFERENCE CANDIDATE · not calibrated biological sufficiency.",
            7.0,
        )
        fig.text(
            0.04,
            0.85,
            "Reference: R = 4, B = 1, S = 0.25; independent repeats (ρ = 0).",
            fontsize=9,
        )
        ax = fig.add_axes([0.355, 0.29, 0.615, 0.47])
        ax.set_xlim(-0.5, 8.5)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        ax.set_xticks(range(9), CATS, rotation=60, ha="left")
        ax.xaxis.tick_top()
        ax.set_yticks(range(len(rows)), rowlabels)
        ax.tick_params(length=0, pad=5)
        ax.set_frame_on(False)
        matrix = []
        for y, r in enumerate(rows):
            targets = bylevel[r["level"]]
            assert len(targets) == r["target_count"]
            assert set(r["failed"] + r["unknown"]) <= set(targets)
            cells = []
            for x in range(9):
                relevant = {t for t in targets if category(t) == x}
                state = (
                    "–"
                    if not relevant
                    else "F"
                    if relevant.intersection(r["failed"])
                    else "?"
                    if relevant.intersection(r["unknown"])
                    else "P"
                )
                cells.append(state)
                ax.add_patch(
                    Rectangle(
                        (x - 0.46, y - 0.43), 0.92, 0.86, color=COLORS[state], lw=0
                    )
                )
                ax.text(
                    x,
                    y,
                    state,
                    ha="center",
                    va="center",
                    fontsize=9,
                    weight="bold",
                    color=INK if state == "–" else "white",
                )
            matrix.append(cells)
        note(
            fig,
            "P All required targets in category pass   F At least one fails\n? Unresolved   – Not required. No scores are summed across columns.",
            0.24,
        )
        note(
            fig,
            "State: coordinate depth; Pop.: population precision; Time: within-person change. Digital/neural include their state, population and temporal targets. Causal: randomized contrasts; Linked: joint people; Joint: complementary operators.",
            0.17,
        )
        note(
            fig,
            "* Optional neural child; other adversaries use AB1. Witnesses: AB1 days 0/30, two groups; AB2 days 0/30/365, four groups. R/B/S are measurement/person/occasion variances; ρ is repeat correlation. “×” means people × repeats per coordinate per occasion.",
            0.09,
        )
        save(
            fig,
            name,
            {"rows": rows, "category_matrix": matrix, "category_labels": CATS},
        )
    metadata = {
        "contract": "anibench.paper-plates.v1",
        "source_files": {
            k: {"filename": str(v.name), "sha256": inputs[k]}
            for k, v in [
                ("architecture", architecture),
                ("reference", reference),
                ("profiles", profiles),
            ]
        },
        "plot_script_sha256": sha(Path(__file__)),
        "plates": receipts,
        "source_architecture_sources": a["sources"],
        "rendering": {
            "matplotlib": matplotlib.__version__,
            "native_width_inches": 6.5,
            "minimum_body_label_pt": 9,
            "minimum_note_pt": 8,
            "png_dpi": 180,
        },
        "claim_scope": "Formatting and exact record/category projection only; no new scientific quantities or source acquisitions",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"plates": len(receipts), "out": str(out)}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--architecture", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    main(args.architecture, args.reference, args.profiles, args.out)
