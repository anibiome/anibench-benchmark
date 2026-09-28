# ruff: noqa: TRY004 -- malformed JSON consistently raises ValueError at the public boundary
# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Draw comparable capability percentages from hash-verified local result files.

This consumer never recomputes a scientific score. The comparison manifest is a
local disclosure choice; it must not contain private participant information.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import unicodedata
from pathlib import Path

from .compiler import digest, reference_filename

FAMILIES = {
    "individual_state": "Individual measurements",
    "population_variation": "Differences between people",
    "trajectories": "Change over time",
    "controlled_effects": "Controlled effects",
    "personalized_response": "Response differences",
    "external_replication": "Replication across sites",
}
COLORS = ["#087F8C", "#7962A8", "#D47832", "#326AB3", "#B14C68", "#50624C"]


def percent_pair(row):
    """Validate saved bounds without rounding or reinterpreting unknown mass."""
    values = [row.get("lower_percent"), row.get("upper_percent")]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("Every saved bound must be finite and numeric")
    lo, hi = values
    if not 0 <= lo <= hi <= 100:
        raise ValueError("Invalid percentage interval")
    return lo, hi


def plain_label(value):
    """Plain, bounded labels cannot change Markdown structure or invoke mathtext."""
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise ValueError("Use a nonempty display label of at most 64 characters")
    if any(unicodedata.category(ch).startswith("C") or ch in "\r\n\u2028\u2029" for ch in value):
        raise ValueError("Display labels must be a single line without control characters")
    return value.strip()


def markdown_cell(value):
    value = html.escape(value, quote=True)
    for char in "\\`*_{}[]|":
        value = value.replace(char, "\\" + char)
    return value


def registered_basis(result):
    """Validate one supported fixed reference; equality alone is insufficient."""
    if result.get("study_profile") == "native36-capability-v3":
        from .study_profile import validate_chart_result
        from .temporal_prediction import _scenario_registry

        noise = result.get("measurement_noise_profile")
        if noise is not None:
            if not isinstance(noise, dict):
                raise ValueError("Malformed hybrid measurement-noise metadata")
            _scenario_registry(noise.get("multipliers"))
        basis = validate_chart_result(result)
        basis["profile_label"] = (
            "Native36 v3: source-corrected ERP, prediction + randomized windows"
        )
        return basis
    if result.get("study_profile") is not None:
        raise ValueError("Unsupported explicit study profile")
    from importlib.resources import files

    from . import compiler, linked_workload, noise_sensitivity

    factor = result.get("resolution_factor")
    if type(factor) not in (int, float) or factor not in (1.0, 0.5):
        raise ValueError("Resolution must be the registered standard or fine numeric factor")
    resolution = "standard" if factor == 1 else "fine"
    level = "AB1" if factor == 1 else "AB2"
    catalogue = "native36-operator-pilot-v2"
    if result.get("catalogue_profile") != catalogue:
        raise ValueError("Unsupported or missing catalogue profile")
    if result.get("requested_resolution") != resolution:
        raise ValueError("Resolution label differs from its registered factor")
    manifest = compiler.registry()
    if result.get("manifest_sha256") != digest(manifest):
        raise ValueError("Native catalogue differs from the installed registered reference")
    if result.get("model_variant") != "coherent_absolute_v1":
        raise ValueError("Unsupported biological process model")
    if result.get("temporal_prediction_profile") is not None:
        raise ValueError(
            "Conditional temporal prediction requires its separately reviewed consumer"
        )
    noise = result.get("measurement_noise_profile")
    if noise is None:
        profile = json.loads(files(__package__).joinpath(reference_filename(level)).read_text())
        scenarios = dict(compiler.SCENARIOS)
        noise_id = "inherited-q1-q2"
    else:
        if not isinstance(noise, dict) or noise.get("id") != "common-noise-grid-v1":
            raise ValueError("Unsupported measurement-noise profile")
        scenarios = dict(noise_sensitivity.SCENARIOS)
        supplied = noise.get("multipliers")
        if (
            not isinstance(supplied, dict)
            or set(supplied) != set(scenarios)
            or any(
                type(supplied[k]) not in (int, float) or supplied[k] != v
                for k, v in scenarios.items()
            )
        ):
            raise ValueError("Noise scenario registry differs from the frozen challenge")
        if noise.get("native_increment_manifest_sha256") != digest(manifest):
            raise ValueError("Noise profile uses a different native increment reference")
        profile = noise_sensitivity.profile(level)
        noise_id = noise["id"]
    if result.get("reference_profile_sha256") != digest(profile):
        raise ValueError("Missing or unregistered complete reference profile")
    supplied_registry = result.get("scenario_registry")
    if supplied_registry is not None and (
        not isinstance(supplied_registry, dict)
        or set(supplied_registry) != set(scenarios)
        or any(
            type(supplied_registry[k]) not in (int, float) or supplied_registry[k] != v
            for k, v in scenarios.items()
        )
    ):
        raise ValueError("Conflicting explicit scenario registry")
    actual_scenarios = result.get("scenarios")
    if (
        not isinstance(actual_scenarios, list)
        or len(actual_scenarios) != len(scenarios)
        or not all(isinstance(s, dict) for s in actual_scenarios)
        or {s.get("scenario_id") for s in actual_scenarios} != set(scenarios)
    ):
        raise ValueError("Result must preserve the complete registered coherent scenarios")
    provenance = result.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError("Missing calculation provenance")
    modules = [
        "sufficient_statistics.py",
        "linked_workload.py",
        "compiler.py",
        "multiscale.py",
        "population_reml.py",
        "compare_metrics.py",
    ]
    if noise is not None:
        modules.append("noise_sensitivity.py")
    expected_code = {
        name: "sha256:" + hashlib.sha256(files(__package__).joinpath(name).read_bytes()).hexdigest()
        for name in modules
    }
    if provenance.get("calculation_files") != expected_code:
        raise ValueError(
            "Result calculation bytes differ from the installed reviewed implementation"
        )
    if provenance.get("relations_sha256") != digest(linked_workload.RELATIONS) or provenance.get(
        "budgets_sha256"
    ) != digest(linked_workload.relation_budgets(linked_workload.RELATIONS, manifest)):
        raise ValueError("Result uses a different relation or weight contract")
    domains = {p["domain"] for p in manifest["panels"]}
    expected_rows = {(p["id"], family) for p in manifest["panels"] for family in FAMILIES}
    for scenario in actual_scenarios:
        summary = scenario.get("summary")
        if (
            not isinstance(summary, list)
            or len(summary) != len(FAMILIES)
            or not all(isinstance(s, dict) for s in summary)
            or {s.get("family") for s in summary} != set(FAMILIES)
        ):
            raise ValueError("Result must preserve all six capability families")
        rows = scenario.get("rows")
        if (
            not isinstance(rows, list)
            or len(rows) != len(expected_rows)
            or not all(isinstance(r, dict) for r in rows)
            or {(r.get("panel_id"), r.get("family")) for r in rows} != expected_rows
        ):
            raise ValueError("Result is missing registered panel/family denominator rows")
        for row in rows:
            percent_pair(row)
        for summary_row in summary:
            percent_pair(summary_row)
            values = summary_row.get("domains")
            if (
                not isinstance(values, list)
                or len(values) != len(domains)
                or not all(isinstance(d, dict) for d in values)
                or {d.get("domain") for d in values} != domains
            ):
                raise ValueError("Result must preserve every fixed biological-domain denominator")
            for domain in values:
                percent_pair(domain)
    return {
        "catalogue_profile": catalogue,
        "profile_id": profile["profile_id"],
        "reference_profile_sha256": digest(profile),
        "manifest_sha256": digest(manifest),
        "model_variant": result["model_variant"],
        "resolution_factor": factor,
        "resolution": resolution,
        "scenario_registry": scenarios,
        "noise_profile": noise_id,
        "calculation_files": expected_code,
        "relations_sha256": provenance["relations_sha256"],
        "budgets_sha256": provenance["budgets_sha256"],
        "metric_id": "registered-likelihood-task-attainment-v1",
    }


def bind_lifecycle(record, comparison_path, result):
    """Bind the evaluated lifecycle to the original local input, not a display flag."""
    from .entrypoint import load_input

    if not isinstance(record.get("input"), str) or not record["input"]:
        raise ValueError("A local original input sidecar is required to bind evidence lifecycle")
    raw = (comparison_path.parent / record["input"]).resolve().read_bytes()
    if record.get("input_file_sha256") != "sha256:" + hashlib.sha256(raw).hexdigest():
        raise ValueError("Original input bytes differ from the comparison manifest")
    design, _ = load_input(json.loads(raw))
    if not isinstance(result.get("provenance"), dict):
        raise ValueError("Missing source provenance")
    if digest(design) != result.get("source_input_sha256") or digest(design) != result[
        "provenance"
    ].get("original_input_sha256"):
        raise ValueError("Input sidecar is not the source of this evaluated result")
    if design["design_id"] != result.get("design_id"):
        raise ValueError("Result and source design identity differ")
    if record["lifecycle"] != design["lifecycle"]:
        raise ValueError("Display lifecycle differs from the evaluated source input")
    return design["lifecycle"]


def read_comparison(path, scenario, *, published_only=False, irb_only=False):
    from importlib.resources import files

    from jsonschema import Draft202012Validator

    manifest = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(files(__package__).joinpath("chart.schema.json").read_text())
    if not Draft202012Validator(schema).is_valid(manifest):
        raise ValueError("Invalid local chart manifest structure")
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != "anibench.study-chart-comparison.v1"
    ):
        raise ValueError("Unsupported chart manifest")
    if not isinstance(manifest.get("studies"), list):
        raise ValueError("Comparison requires study records")
    selected = []
    basis = None
    identities = set()
    for record in manifest["studies"]:
        if not isinstance(record, dict):
            raise ValueError("Each study record must be an object")
        if not isinstance(record.get("result"), str) or not record["result"]:
            raise ValueError("Each study requires a local result path")
        if record.get("study_publication") not in {
            "peer_reviewed_results",
            "preprint_results",
            "protocol_only",
            "unpublished",
            "unknown",
        }:
            raise ValueError("Use an explicit study-publication status")
        if record.get("ethics") not in {
            "approved",
            "exempt",
            "not_required",
            "not_approved",
            "unknown",
        }:
            raise ValueError("Use an explicit ethics status")
        if record.get("lifecycle") not in {"planned", "collected", "hypothetical"}:
            raise ValueError("Use an explicit lifecycle")
        label = plain_label(record.get("label"))
        if published_only and record["study_publication"] != "peer_reviewed_results":
            continue
        if irb_only and record["ethics"] != "approved":
            continue
        result_path = (path.parent / record["result"]).resolve()
        raw = result_path.read_bytes()
        expected_bytes = "sha256:" + hashlib.sha256(raw).hexdigest()
        if expected_bytes != record.get("result_file_sha256"):
            raise ValueError("Result file differs from the comparison manifest")
        result = json.loads(raw)
        if (
            not isinstance(result, dict)
            or result.get("schema") != "anibench.linked-study-capability-candidate.v1"
        ):
            raise ValueError("Unsupported result schema")
        payload = {k: v for k, v in result.items() if k != "result_sha256"}
        if digest(payload) != result.get("result_sha256"):
            raise ValueError("Stale result content hash")
        study_id = result.get("design_id")
        if not isinstance(study_id, str) or not study_id:
            raise ValueError("A nonempty evaluated design identity is required")
        if study_id in identities:
            raise ValueError("A study instance cannot appear twice in one comparison")
        identities.add(study_id)
        lifecycle = bind_lifecycle(record, path, result)
        current_basis = registered_basis(result)
        if basis is not None and current_basis != basis:
            raise ValueError("Results use different scientific comparison bases")
        basis = current_basis
        matches = [s for s in result["scenarios"] if s["scenario_id"] == scenario]
        if len(matches) != 1:
            raise ValueError("Requested scenario must occur exactly once in every result")
        summary = matches[0]["summary"]
        if len(summary) != len(FAMILIES) or {s["family"] for s in summary} != set(FAMILIES):
            raise ValueError("Result must preserve all six capability families")
        scores = {s["family"]: percent_pair(s) for s in summary}
        selected.append(
            {
                "label": label,
                "design_id": study_id,
                "lifecycle": lifecycle,
                "ethics": record["ethics"],
                "study_publication": record["study_publication"],
                "result_sha256": result["result_sha256"],
                "result_file_sha256": expected_bytes,
                "scores": scores,
            }
        )
    if not 1 <= len(selected) <= 6:
        raise ValueError(
            "Select one to six study instances; the filters may have removed all records"
        )
    return {
        "schema": "anibench.study-chart-data.v1",
        "scenario": scenario,
        "basis": basis,
        "filters": {
            "peer_reviewed_results_only": published_only,
            "approved_only": irb_only,
        },
        "metric": "Benchmark tasks met (%)",
        "studies": selected,
        "uncertainty": "Unresolved evidence outer bounds; not confidence intervals or joint attainability certificates",
        "evidence_mode": "Conditional common-reference challenge; source qualification is not authenticated by hashes",
        "metadata_status": "Study publication and ethics are supplied metadata; filters do not certify their truth",
    }


def label_percent(lo, hi):
    """Round interval bounds outward so tiny unknown mass never becomes a point."""

    def number(value):
        return f"{value:.1f}".rstrip("0").rstrip(".")

    if lo == hi:
        return number(lo) + "%"
    lower = math.floor(lo * 10) / 10
    upper = math.ceil(hi * 10) / 10
    return number(lower) + "–" + number(upper) + "%"


def draw(data, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    if out.exists():
        raise ValueError("Chart output directory already exists")
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    studies = data["studies"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "svg.fonttype": "none",
            "svg.hashsalt": "anibench.study-chart.v1",
            "text.parse_math": False,
        }
    )
    # Reserve a separate numeric column. Wrap from actual glyph widths, including
    # long unbroken names, while retaining every character and the lifecycle.
    from matplotlib.font_manager import FontProperties

    figure, axes = plt.subplots(3, 2, figsize=(16, 10))
    figure.subplots_adjust(left=0.055, right=0.955, wspace=0.19)
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    font = FontProperties(family="DejaVu Sans", size=10)
    label_width = axes.flat[0].get_window_extent(renderer).width - 115
    wrapped = []
    for study in studies:
        text = study["label"] + " [" + study["lifecycle"] + "]"
        lines, line = [], ""
        for character in text:
            candidate = line + character
            width = renderer.get_text_width_height_descent(candidate, font, False)[0]
            if width > label_width and line:
                lines.append(line)
                line = character
            else:
                line = candidate
        lines.append(line)
        wrapped.append("\n".join(lines))
    line_inches = 0.19
    row_heights = [len(label.split("\n")) * line_inches + 0.27 for label in wrapped]
    panel_height = sum(row_heights) + 0.08
    header, footer, gap = 1.45, 1.3, 0.55
    height = header + footer + 3 * panel_height + 2 * gap
    figure.set_size_inches(16, height)
    figure.patch.set_facecolor("white")
    figure.subplots_adjust(
        left=0.055,
        right=0.955,
        top=1 - header / height,
        bottom=footer / height,
        wspace=0.19,
        hspace=gap / panel_height,
    )
    figure.text(
        0.04,
        1 - 0.32 / height,
        "ANIBENCH / STUDY COMPARISON",
        fontsize=11,
        fontweight="bold",
        color="#087F8C",
    )
    figure.text(
        0.04,
        1 - 0.76 / height,
        "What can each study resolve?",
        fontsize=26,
        fontweight="bold",
        color="#172B32",
    )
    figure.text(
        0.04,
        1 - 1.08 / height,
        "Benchmark tasks met (%)  ·  Higher means more registered requirements met",
        fontsize=12,
        color="#4C6269",
    )
    for axis, (family, title) in zip(axes.flat, FAMILIES.items(), strict=True):
        top = 0.0
        for row, study in enumerate(studies):
            lo, hi = study["scores"][family]
            bar_y = top + len(wrapped[row].split("\n")) * line_inches + 0.04
            axis.barh(bar_y, lo, color=COLORS[row], height=0.12, zorder=3)
            if hi > lo:
                axis.barh(
                    bar_y,
                    hi - lo,
                    left=lo,
                    facecolor="white",
                    edgecolor=COLORS[row],
                    hatch="////",
                    linewidth=0.8,
                    height=0.12,
                    zorder=3,
                )
            # A zero is a visible result, not a missing bar or empty cell.
            axis.text(
                0,
                top,
                wrapped[row],
                va="top",
                fontsize=10,
                linespacing=1.1,
                color="#172B32",
                gid=f"label-{family}-{row}",
            )
            axis.text(
                100,
                top,
                label_percent(lo, hi),
                va="top",
                ha="right",
                fontsize=10,
                fontweight="bold",
                color="#172B32",
                gid=f"percent-{family}-{row}",
            )
            top += row_heights[row]
        axis.set_yticks([])
        axis.set_ylim(panel_height, 0)
        axis.set_xlim(0, 100)
        axis.set_xticks([0, 50, 100], ["0", "50", "100"])
        axis.tick_params(axis="both", length=0, pad=6, labelsize=9)
        axis.set_title(title, loc="left", pad=13, fontsize=12, fontweight="bold")
        axis.grid(axis="x", color="#E1E8EC", linewidth=0.6, zorder=0)
        for side in ["left", "right", "top", "bottom"]:
            axis.spines[side].set_visible(False)
    figure.legend(
        handles=[
            Patch(facecolor="#4C6269", label="Requirements met"),
            Patch(
                facecolor="white",
                edgecolor="#4C6269",
                hatch="////",
                label="Unresolved evidence",
            ),
        ],
        loc="lower left",
        bbox_to_anchor=(0.033, 0.57 / height),
        ncol=2,
        frameon=False,
        fontsize=10,
    )
    reference_context = (
        data["basis"]["catalogue_profile"]
        + " / "
        + data["basis"]["resolution"]
        + " / "
        + data["scenario"]
        + " (q="
        + str(data["basis"]["scenario_registry"][data["scenario"]])
        + ")"
    )
    filter_context = (
        "Published results only"
        if data["filters"]["peer_reviewed_results_only"]
        else "All publication statuses"
    )
    filter_context += (
        "; approved only" if data["filters"]["approved_only"] else "; all ethics statuses"
    )
    figure.text(
        0.04,
        0.42 / height,
        "Conditional reference: " + reference_context + ".",
        fontsize=10,
        color="#4C6269",
    )
    figure.text(
        0.04,
        0.17 / height,
        filter_context
        + ". Fixed-task percentages, not all biology; ranges are unresolved outer bounds. Level checks separate.",
        fontsize=10,
        color="#4C6269",
    )
    for extension in ["svg", "png"]:
        figure.savefig(
            out / ("study-comparison." + extension),
            dpi=240,
            facecolor="white",
            metadata={"Creator": "AniBench", "Date": None} if extension == "svg" else None,
        )
    plt.close(figure)
    (out / "figure-data.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    rows = [
        "| Study | " + " | ".join(FAMILIES.values()) + " |",
        "|---|" + "---|" * len(FAMILIES),
    ]
    for study in studies:
        rows.append(
            "| "
            + markdown_cell(study["label"] + " [" + study["lifecycle"] + "]")
            + " | "
            + " | ".join(label_percent(*study["scores"][family]) for family in FAMILIES)
            + " |"
        )
    (out / "comparison.md").write_text(
        "Benchmark tasks met (%).\n\nConditional reference: "
        + reference_context
        + ".\n\n"
        + filter_context
        + ". Publication/ethics are supplied metadata; filters do not certify truth.\n\nRanges are unresolved evidence outer bounds, not sampling uncertainty or joint attainability. Fixed tasks are not all biology; full level attainment is checked separately.\n\n"
        + "\n".join(rows)
        + "\n"
    )
    receipt = {
        "schema": "anibench.study-chart-receipt.v1",
        "figure_data_sha256": digest(data),
        "renderer_sha256": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "files": {
            p.name: "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.iterdir())
            if p.is_file()
        },
    }
    (out / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--published-only", action="store_true")
    parser.add_argument("--irb-only", action="store_true")
    args = parser.parse_args(argv)
    data = read_comparison(
        args.manifest,
        args.scenario,
        published_only=args.published_only,
        irb_only=args.irb_only,
    )
    print(json.dumps(draw(data, args.out)))


if __name__ == "__main__":
    main()
