"""Reproduce aggregate empirical figure from a frozen result; no participant data."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def render(result_path, out):
    result = json.loads(result_path.read_text())
    if result["schema"] != "anibench.native-repeat-results.v1":
        raise ValueError("Expected frozen native-repeat result")
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    models = ["population_mean", "one_reading", "last_reading", "two_readings", "linear"]
    labels = [
        "Population average",
        "First reading",
        "Second reading",
        "Average of two",
        "Fitted linear model",
    ]
    colors = ["#cbd5e1", "#64748b", "#64748b", "#087f74", "#24374b"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "svg.fonttype": "none",
            "svg.hashsalt": "anibench-native-repeat-v1",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    fig.subplots_adjust(left=0.18, right=0.96, bottom=0.24, top=0.71, wspace=0.42)
    fig.text(
        0.045, 0.94, "ANIBENCH  /  EMPIRICAL VALIDATION", color="#087f74", size=11, weight="bold"
    )
    fig.text(
        0.045,
        0.87,
        "Do extra readings improve prediction?",
        size=25,
        weight="bold",
        color="#152536",
    )
    fig.text(
        0.045,
        0.805,
        "Predict a withheld third blood-pressure reading · NHANES 2015–2016",
        size=13,
        color="#536273",
    )
    table = []
    for ax, target in zip(axes, result["results"]):
        rows = [target["models"][name] for name in models]
        values = [row["RMSE"] for row in rows]
        lower = [v - np.sqrt(row["MSE_cluster_interval"][0]) for row, v in zip(rows, values)]
        upper = [np.sqrt(row["MSE_cluster_interval"][1]) - v for row, v in zip(rows, values)]
        y = np.arange(len(models))
        ax.barh(y, values, color=colors, height=0.56)
        ax.errorbar(
            values, y, xerr=[lower, upper], fmt="none", ecolor="#233647", capsize=3, linewidth=1
        )
        for yy, value, error in zip(y, values, upper):
            ax.text(value + error + 0.3, yy, f"{value:.2f}", va="center", fontsize=10)
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlim(0, 21)
        ax.set_xticks([0, 5, 10, 15, 20])
        ax.set_xlabel("Prediction error (RMSE, mmHg) · lower is better", size=10)
        ax.set_title(target["target"].capitalize(), loc="left", weight="bold", pad=16)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#edf0f3")
        table.extend(
            {
                "target": target["target"],
                "model": name,
                "RMSE": row["RMSE"],
                "MSE_cluster_interval": row["MSE_cluster_interval"],
            }
            for name, row in zip(models, rows)
        )
    fig.text(
        0.045,
        0.12,
        "Combining readings helped. The simple noise model did not fully explain the gains.",
        color="#152536",
        weight="bold",
        size=12,
    )
    test_people = result["counts"]["split_people"][1]
    test_groups = result["counts"]["split_groups"][1]
    fig.text(
        0.045,
        0.068,
        f"{test_people:,} held-out adults · {test_groups} masked groups · Nominal 95% cluster-bootstrap intervals\n"
        "Same-session prediction; these are not biological-state accuracy or AniBench study scores.",
        color="#536273",
        size=10,
        linespacing=1.5,
    )
    fig.savefig(out / "native-repeat-validation.png", dpi=180, facecolor="white")
    fig.savefig(out / "native-repeat-validation.svg", facecolor="white", metadata={"Date": None})
    plt.close(fig)
    packet = {
        "schema": "anibench.native-repeat-figure.v1",
        "result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rows": table,
        "counts": result["counts"],
        "scope": result["scope"],
    }
    (out / "figure-data.json").write_text(json.dumps(packet, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    render(args.results, args.out)
