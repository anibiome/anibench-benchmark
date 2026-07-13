"""Build the AniBench v2 score-free source atlas from one coordinate table.

The atlas is deliberately descriptive.  It preserves the coordinate-table row
order, carries missing values as missing, and never produces a composite score
or a rank.  The plot-data and build receipts make every rendered coordinate
machine-replayable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "anibench-source-atlas-v2"
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ATLAS_VERSION = "ani.source_atlas.v2.candidate"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_COLUMNS = (
    "study_id,projection_lane,population_value,population_semantics,"
    "population_state,duration_days,duration_semantics,duration_state,"
    "policy_arms,randomized_policy,concurrent_control,deployed_operator_families,"
    "identifiable_policy_contrasts,adaptive_reassignment,within_policy_randomized,"
    "known_projected_measurement_modules,conditional_measurement_modules,"
    "unknown_measurement_modules,open_gate_count,source_projection_sha256"
).split(",")
FIGURES = (
    "01_evidence_module_states",
    "02_population_duration_coordinates",
    "03_causal_architecture",
    "04_open_gates",
)

NAVY = "#19324D"
TEAL = "#168C8C"
AMBER = "#E6A23C"
GRAY = "#A5ADB6"
PALE = "#F2F5F7"
INK = "#17212B"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _number(value: str) -> int | float | None:
    if value == "":
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def _boolean(value: str) -> bool | None:
    if value == "":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"Expected true, false, or blank; received {value!r}")


def _load_rows(coordinate_table: Path) -> list[dict[str, str]]:
    with coordinate_table.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(
                "Coordinate-table schema mismatch: "
                f"expected {EXPECTED_COLUMNS!r}, got {reader.fieldnames!r}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError("Coordinate table contains no studies")
    study_ids = [row["study_id"] for row in rows]
    if len(study_ids) != len(set(study_ids)):
        raise ValueError("Coordinate table contains duplicate study_id values")
    return rows


def _verify_projection_hashes(
    rows: list[dict[str, str]], coordinate_table: Path
) -> list[dict[str, str]]:
    projection_root = coordinate_table.parent
    verified: list[dict[str, str]] = []
    for row in rows:
        study_id = row["study_id"]
        path = projection_root / f"{study_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing source projection for {study_id}: {path}")
        actual = _sha256(path)
        expected = row["source_projection_sha256"]
        if actual != expected:
            raise ValueError(
                f"Source projection hash mismatch for {study_id}: expected {expected}, got {actual}"
            )
        verified.append(
            {
                "study_id": study_id,
                "path": _portable_path(path),
                "sha256": actual,
            }
        )
    return verified


def _plot_data(rows: list[dict[str, str]], coordinate_table: Path) -> dict[str, Any]:
    studies = []
    for row in rows:
        studies.append(
            {
                "study_id": row["study_id"],
                "projection_lane": row["projection_lane"],
                "evidence_module_states": {
                    "known_projected": _number(row["known_projected_measurement_modules"]),
                    "conditional": _number(row["conditional_measurement_modules"]),
                    "unknown": _number(row["unknown_measurement_modules"]),
                },
                "population": {
                    "value": _number(row["population_value"]),
                    "semantics": row["population_semantics"],
                    "state": row["population_state"],
                },
                "duration": {
                    "days": _number(row["duration_days"]),
                    "semantics": row["duration_semantics"],
                    "state": row["duration_state"],
                },
                "causal_architecture": {
                    "policy_arms": _number(row["policy_arms"]),
                    "randomized_policy": _boolean(row["randomized_policy"]),
                    "concurrent_control": _boolean(row["concurrent_control"]),
                    "deployed_operator_families": _number(row["deployed_operator_families"]),
                    "identifiable_policy_contrasts": _number(row["identifiable_policy_contrasts"]),
                    "adaptive_reassignment": _boolean(row["adaptive_reassignment"]),
                    "within_policy_randomized": _boolean(row["within_policy_randomized"]),
                },
                "open_gate_count": _number(row["open_gate_count"]),
                "source_projection_sha256": row["source_projection_sha256"],
            }
        )
    return {
        "schema": ATLAS_VERSION,
        "coordinate_table": {
            "path": _portable_path(coordinate_table),
            "sha256": _sha256(coordinate_table),
        },
        "row_order_semantics": "source_coordinate_table_order_not_a_rank",
        "studies": studies,
    }


def _style_axes(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#C7CED4")
    ax.tick_params(colors="#425466")
    ax.grid(axis="y", color="#E5E9ED", linewidth=0.8)
    ax.set_axisbelow(True)


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    paths = []
    for suffix in ("png", "svg"):
        path = output_dir / f"{stem}.{suffix}"
        metadata = {"Date": None} if suffix == "svg" else {"Software": "AniBench"}
        fig.savefig(path, dpi=220, bbox_inches="tight", metadata=metadata)
        paths.append(path)
    plt.close(fig)
    return paths


def _evidence_figure(studies: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    labels = [study["study_id"] for study in studies]
    known_projected = [
        study["evidence_module_states"]["known_projected"] for study in studies
    ]
    conditional = [study["evidence_module_states"]["conditional"] for study in studies]
    unknown = [study["evidence_module_states"]["unknown"] for study in studies]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    ax.bar(x, known_projected, label="Machine-resolved module", color=TEAL)
    ax.bar(x, conditional, bottom=known_projected, label="Conditional", color=AMBER)
    lower = np.asarray(known_projected) + np.asarray(conditional)
    ax.bar(x, unknown, bottom=lower, label="Unknown", color=GRAY)
    for index, parts in enumerate(zip(known_projected, conditional, unknown, strict=True)):
        running = 0
        for value in parts:
            if value:
                ax.text(index, running + value / 2, str(value), ha="center", va="center")
            running += value
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set_ylabel("Measurement modules (count)")
    ax.set_title("Measurement evidence states", loc="left", weight="bold", color=INK)
    ax.legend(frameon=False, ncols=3, loc="upper right")
    _style_axes(ax)
    fig.tight_layout()
    return _save_figure(fig, output_dir, FIGURES[0])


def _coordinate_panel(
    ax: plt.Axes,
    studies: list[dict[str, Any]],
    coordinate: str,
) -> None:
    labels = [study["study_id"] for study in studies]
    if coordinate == "population":
        values = [study[coordinate]["value"] for study in studies]
        semantics = [study[coordinate]["semantics"] for study in studies]
        states = [study[coordinate]["state"] for study in studies]
        title = "Population coordinate (declared semantics)"
        ylabel = "People"
    else:
        values = [study[coordinate]["days"] for study in studies]
        semantics = [study[coordinate]["semantics"] for study in studies]
        states = [study[coordinate]["state"] for study in studies]
        title = "Duration coordinate (declared semantics)"
        ylabel = "Days"
    x = np.arange(len(labels))
    numeric = [0 if value is None else value for value in values]
    colors = [AMBER if state == "conditional" else NAVY for state in states]
    bars = ax.bar(x, numeric, color=colors)
    for index, (bar, value, semantic, state) in enumerate(
        zip(bars, values, semantics, states, strict=True)
    ):
        if value is None:
            ax.text(index, 0, "unknown", ha="center", va="bottom", color="#65727E")
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value}\n{semantic}\n[{state}]",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", weight="bold", color=INK)
    ax.margins(y=0.30)
    _style_axes(ax)


def _population_duration_figure(studies: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    fig, axes = plt.subplots(2, 1, figsize=(13.2, 11.4))
    _coordinate_panel(axes[0], studies, "population")
    _coordinate_panel(axes[1], studies, "duration")
    fig.suptitle(
        "Population and time are typed coordinates, not a composite",
        x=0.075,
        ha="left",
        fontsize=15,
        weight="bold",
        color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _save_figure(fig, output_dir, FIGURES[1])


def _display(value: Any) -> str:
    if value is None:
        return "?"
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return str(value)


def _causal_figure(studies: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    columns = [
        ("policy_arms", "Policy\narms"),
        ("randomized_policy", "Randomized\npolicy"),
        ("concurrent_control", "Concurrent\ncontrol"),
        ("deployed_operator_families", "Deployed operator\nfamilies"),
        ("identifiable_policy_contrasts", "Identifiable policy\ncontrasts"),
        ("adaptive_reassignment", "Adaptive\nreassignment"),
        ("within_policy_randomized", "Within-policy\nrandomized"),
    ]
    cell_text = [
        [_display(study["causal_architecture"][key]) for key, _ in columns] for study in studies
    ]
    cell_colors = []
    for study in studies:
        colors = []
        for key, _ in columns:
            value = study["causal_architecture"][key]
            if value is None:
                colors.append("#E1E5E9")
            elif value is True:
                colors.append("#D4EFE8")
            elif value is False:
                colors.append("#EAF0F5")
            else:
                colors.append(PALE)
        cell_colors.append(colors)
    fig, ax = plt.subplots(figsize=(15.2, 6.5))
    ax.axis("off")
    table = ax.table(
        cellText=cell_text,
        rowLabels=[study["study_id"] for study in studies],
        colLabels=[label for _, label in columns],
        cellColours=cell_colors,
        cellLoc="center",
        rowLoc="right",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.2)
    for (row, _column), cell in table.get_celld().items():
        cell.set_edgecolor("#CBD2D9")
        if row == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color="white", weight="bold")
    ax.set_title(
        "Causal architecture coordinates (? = not source-established)",
        loc="left",
        fontsize=15,
        weight="bold",
        color=INK,
        pad=18,
    )
    fig.tight_layout()
    return _save_figure(fig, output_dir, FIGURES[2])


def _gates_figure(studies: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    labels = [study["study_id"] for study in studies]
    values = [study["open_gate_count"] for study in studies]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    bars = ax.bar(x, values, color=NAVY)
    ax.bar_label(bars, labels=[str(value) for value in values], padding=3)
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set_ylabel("Source-projection open gates (count)")
    ax.set_title("Open source-truth gates", loc="left", weight="bold", color=INK)
    ax.margins(y=0.15)
    _style_axes(ax)
    fig.tight_layout()
    return _save_figure(fig, output_dir, FIGURES[3])


def build_source_atlas(coordinate_table: Path, output_dir: Path) -> Path:
    """Build and receipt a source atlas; return the build-receipt path."""
    coordinate_table = coordinate_table.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _load_rows(coordinate_table)
    verified_projections = _verify_projection_hashes(rows, coordinate_table)
    plot_data = _plot_data(rows, coordinate_table)

    plot_data_path = output_dir / "SOURCE_ATLAS_PLOT_DATA.json"
    plot_data_path.write_text(
        json.dumps(plot_data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    coordinate_copy = output_dir / "SOURCE_ATLAS_COORDINATES.csv"
    shutil.copyfile(coordinate_table, coordinate_copy)

    studies = plot_data["studies"]
    generated: list[Path] = [plot_data_path, coordinate_copy]
    generated.extend(_evidence_figure(studies, output_dir))
    generated.extend(_population_duration_figure(studies, output_dir))
    generated.extend(_causal_figure(studies, output_dir))
    generated.extend(_gates_figure(studies, output_dir))

    readme = output_dir / "README.md"
    readme.write_text(
        (
            "# AniBench v2 source-atlas candidate\n\n"
            "This package renders typed trial-design coordinates from "
            "`SOURCE_ATLAS_COORDINATES.csv`. It preserves source order and missing "
            "values. The figures are descriptive views of evidence modules, declared "
            "population and duration semantics, causal architecture, and open gates.\n\n"
            "Rebuild with:\n\n"
            "```bash\n"
            "python -m anibench.source_atlas_v2 \\\n+  --coordinate-table data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv \\\n+  --output-dir release/v2-source-atlas-candidate\n"
            "```\n"
        ).replace("\n+", "\n"),
        encoding="utf-8",
    )
    generated.append(readme)

    receipt = {
        "schema": ATLAS_VERSION,
        "evidence_class": "source_linked_derived_candidate",
        "coordinate_table": plot_data["coordinate_table"],
        "source_projection_hashes_verified": verified_projections,
        "study_order": [study["study_id"] for study in studies],
        "order_semantics": "source_coordinate_table_order_not_a_rank",
        "coordinate_policy": {
            "composite_coordinates_emitted": False,
            "ordinal_positions_emitted": False,
            "missing_values_imputed": False,
            "release_readiness_asserted": False,
        },
        "artifacts": [
            {
                "path": path.name,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in generated
        ],
        "builder": {
            "module": "anibench.source_atlas_v2",
            "path": _portable_path(Path(__file__)),
            "sha256": _sha256(Path(__file__).resolve()),
        },
    }
    receipt_path = output_dir / "SOURCE_ATLAS_BUILD_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the AniBench v2 score-free source atlas")
    parser.add_argument("--coordinate-table", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt = build_source_atlas(args.coordinate_table, args.output_dir)
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
