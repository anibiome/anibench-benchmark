"""Recompile public native summaries with the installed canonical evaluator."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import anibench
from anibench.benchmark_v1 import evaluate_benchmark
from anibench.finite_suites_v1 import suite_sha256
from anibench.summary_geometry_v1 import compile_summary_task

HERE = Path(__file__).resolve().parent


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def replay() -> tuple[bytes, dict]:
    """Return exact chart data only after every input and receipt check passes."""
    manifest = read(HERE / "manifest.json")
    for name, expected in manifest["files"].items():
        require(digest(HERE / name) == expected, f"Example file differs: {name}")
    frozen = read(HERE / "inputs.json")
    objects = frozen["objects"]
    for identity, obj in objects.items():
        require(suite_sha256(obj) == identity, "Input object identity differs")
    display = read(HERE / "pilot.json")
    generated = copy.deepcopy(display)
    generated["results"] = []
    derivation_count = 0
    for run in frozen["evaluations"]:
        profile = objects[run["profile"]]
        score = objects[run["score_profile"]]
        tasks = {t["canonical_id"]: t["task"] for t in profile["targets"]}
        binding = run["design_binding"]
        scenarios = []
        for scenario in run["scenarios"]:
            targets = []
            for row in scenario["targets"]:
                derived = compile_summary_task(
                    tasks[row["canonical_id"]],
                    objects[row["summary"]],
                    objects[row["evidence"]],
                )
                require(
                    derived["derivation_sha256"] == row["expected_derivation_sha256"],
                    "Compiled derivation differs; use the reviewed evaluator version",
                )
                request = derived["finite_task_request"]
                require(suite_sha256(request) == row["expected_request_sha256"],
                        "Compiled task request differs")
                targets.append({**binding, "canonical_id": row["canonical_id"],
                                "known_absent": False, "request": request})
                derivation_count += 1
            scenarios.append({**binding, "scenario_id": scenario["scenario_id"],
                              "targets": targets})
        request = {
            "contract": "anibench.benchmark-request.v1",
            "score_profile_sha256": run["score_profile"],
            "suite_request": {
                **binding, "contract": "anibench.finite-suite-request.v1",
                "profile_sha256": run["profile"], "scenarios": scenarios,
            },
        }
        require(suite_sha256(request) == run["expected_request_sha256"],
                "Rebuilt suite request differs")
        result = evaluate_benchmark(
            request,
            trusted_profiles={run["profile"]: profile},
            trusted_score_profiles={run["score_profile"]: score},
        )
        require(
            result["receipt_sha256"] == run["expected_result_sha256"],
            "Result receipt differs. Scientific code and Python/numpy/jsonschema "
            "versions are bound into receipts; inspect the environment in manifest.json.",
        )
        generated["results"].append({
            "family_id": run["family_id"], "se_factor": run["se_factor"],
            "result_sha256": result["receipt_sha256"],
            "suite_profile_sha256": result["suite_profile_sha256"],
            "score_profile_sha256": result["score_profile_sha256"],
            "scenarios": [{"scenario_id": s["scenario_id"],
                           "categories": s["views"][0]["categories"]}
                          for s in result["scenarios"]],
            "envelope": result["envelope"],
        })
    require(generated == display, "Canonical results differ from packaged chart semantics")
    encoded = (json.dumps(generated, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    require(encoded == (HERE / "pilot.json").read_bytes(),
            "Canonical chart bytes differ from packaged pilot.json")
    assets = Path(anibench.__file__).resolve().parent / "workbench_assets"
    require((assets / "pilot.json").read_bytes() == encoded,
            "Installed workbench chart data differs from this example")
    return encoded, {
        "schema": "anibench.native-pilot-reproduction.v1",
        "canonical_suites": len(frozen["evaluations"]),
        "summary_derivations": derivation_count,
        "all_input_and_result_identities_match": True,
        "packaged_and_installed_chart_data_bytes_match": True,
        "pilot_sha256": hashlib.sha256(encoded).hexdigest(),
        "whole_benchmark_validation": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument("--node", default="node", help="Node.js executable for shared SVG renderer")
    args = parser.parse_args()
    require(not args.out.exists(), "Output exists; choose a new directory")
    node = shutil.which(args.node)
    require(node is not None, "Node.js is needed to reproduce the workbench SVG")
    encoded, receipt = replay()
    assets = Path(anibench.__file__).resolve().parent / "workbench_assets"
    # Render in memory before creating output; the shared JS only projects receipts.
    chart = subprocess.run(
        [node, str(HERE / "render.mjs"), str(assets)], input=encoded,
        capture_output=True, check=True,
    ).stdout
    require(chart == (HERE / "expected-chart.svg").read_bytes(),
            "Shared renderer SVG differs from the reviewed chart")
    receipt["shared_renderer_svg_bytes_match"] = True
    receipt["svg_sha256"] = hashlib.sha256(chart).hexdigest()
    args.out.mkdir(parents=True, exist_ok=False)
    for name, data in (("pilot.json", encoded), ("chart.svg", chart),
                       ("receipt.json", (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())):
        with (args.out / name).open("xb") as stream:
            stream.write(data)
    print("Verified 6 canonical suites, 360 summary derivations, chart data and shared SVG.")


if __name__ == "__main__":
    main()
