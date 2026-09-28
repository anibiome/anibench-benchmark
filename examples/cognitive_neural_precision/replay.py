"""Reproduce reviewed cognitive/neural aggregates with installed AniBench APIs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from anibench.benchmark_v1 import evaluate_benchmark
from anibench.finite_suites_v1 import suite_sha256
from anibench.information_v2 import functional_likelihood_precision
from anibench.summary_geometry_v1 import compile_summary_task

HERE = Path(__file__).resolve().parent


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def encode(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def replay() -> tuple[bytes, dict]:
    manifest = read("manifest.json")
    for name, expected in manifest["files"].items():
        require(hashlib.sha256((HERE/name).read_bytes()).hexdigest() == expected,
                f"Example file differs: {name}")
    frozen, sources, expected = read("inputs.json"), read("sources.json"), read("expected-results.json")
    objects = frozen["objects"]
    for identity, value in objects.items():
        require(suite_sha256(value) == identity, "Content-addressed input object differs")
    generated = copy.deepcopy(expected)
    records = {r["record_id"]: r for r in generated["records"]}
    require(len(records) == 12, "Expected twelve distinct measurement records")
    source_rows = {r["id"]: r for r in sources["records"]}
    require(set(records) == set(source_rows), "Source and result record identities differ")
    for identity, record in records.items():
        source_row = source_rows[identity]
        for key in ["family_id", "question_id", "unit", "n", "sample_sd", "operator", "population", "denominator_status"]:
            require(record[key] == source_row[key], f"Source metadata differs: {identity}/{key}")
        require(record["source"] == sources["sources"][source_row["source_id"]],
                f"Source declaration differs: {identity}")
        record["native_scenarios"], record["task_results"] = [], []
    derivations = 0

    def compile_row(row: dict) -> dict:
        nonlocal derivations
        derived = compile_summary_task(objects[row["task"]], objects[row["summary"]], objects[row["evidence"]])
        require(derived["derivation_sha256"] == row["expected_derivation_sha256"], "Derivation identity differs")
        require(suite_sha256(derived) == row["expected_full_derivation_sha256"], "Full compiled derivation differs")
        require(suite_sha256(derived["finite_task_request"]) == row["expected_request_sha256"], "Compiled task request differs")
        derivations += 1
        return derived

    for row in frozen["native_diagnostics"]:
        derived = compile_row(row)
        request = derived["finite_task_request"]
        # The unit variance limit is an inert API placeholder for this diagnostic.
        # No percentage or pass decision is emitted by this path.
        diagnostic = functional_likelihood_precision(request["geometry"]["information_matrix"], [[1]], [1])
        require(diagnostic == objects[row["expected_diagnostic"]], "Native likelihood diagnostic differs")
        summary = derived["summary"]
        records[row["record_id"]]["native_scenarios"].append({
            "scenario_id": row["scenario_id"], "variance": diagnostic["variance"],
            "standard_error": math.sqrt(diagnostic["variance"]),
            "sampling_sd": summary["groups"][0]["sample_sd"],
            "q": summary["variance_multiplier"], "percentage": None,
            "derivation_sha256": suite_sha256(derived),
        })

    for run in frozen["evaluations"]:
        profile, score = objects[run["profile"]], objects[run["score_profile"]]
        task_ids = {t["canonical_id"]: suite_sha256(t["task"]) for t in profile["targets"]}
        binding, scenarios = run["design_binding"], []
        for scenario in run["scenarios"]:
            targets = []
            for row in scenario["targets"]:
                require(task_ids[row["canonical_id"]] == row["task"], "Profile and task identity differ")
                derived = compile_row(row)
                targets.append({**binding, "canonical_id": row["canonical_id"],
                                "known_absent": False, "request": derived["finite_task_request"]})
            scenarios.append({**binding, "scenario_id": scenario["scenario_id"], "targets": targets})
        request = {"contract": "anibench.benchmark-request.v1", "score_profile_sha256": run["score_profile"],
                   "suite_request": {**binding, "contract": "anibench.finite-suite-request.v1",
                                     "profile_sha256": run["profile"], "scenarios": scenarios}}
        require(suite_sha256(request) == run["expected_request_sha256"], "Suite request differs")
        result = evaluate_benchmark(request, trusted_profiles={run["profile"]: profile},
                                    trusted_score_profiles={run["score_profile"]: score})
        require(result["receipt_sha256"] == run["expected_result_sha256"],
                "Result receipt differs; use the reference implementation and runtime in manifest.json")
        require(suite_sha256(result) == run["expected_full_result_sha256"], "Full canonical result differs")
        records[run["record_id"]]["task_results"].append({
            "se_factor": run["se_factor"], "result_sha256": result["receipt_sha256"],
            "suite_profile_sha256": result["suite_profile_sha256"],
            "score_profile_sha256": result["score_profile_sha256"],
            "scenarios": result["scenarios"], "envelope": result["envelope"],
        })
    require(derivations == 216 and len(frozen["evaluations"]) == 24, "Incomplete workload")
    require(generated == expected, "Regenerated native results differ from the reviewed packet")
    data = encode(generated)
    require(data == (HERE/"expected-results.json").read_bytes(), "Regenerated result bytes differ")
    return data, {
        "schema": "anibench.cognitive-neural-reproduction.v1",
        "records": 12, "source_families": 7, "summary_derivations": derivations,
        "native_diagnostics": 72, "canonical_suites": 24, "canonical_task_scenarios": 144,
        "all_input_and_result_identities_match": True,
        "results_sha256": hashlib.sha256(data).hexdigest(),
        "native_only_cortical_records": 4, "whole_study_ranking": False,
        "biological_calibration_established": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    require(not args.out.exists(), "Output exists; choose a new directory")
    data, receipt = replay()
    args.out.mkdir(parents=True, exist_ok=False)
    for name, value in [("results.json", data), ("receipt.json", encode(receipt))]:
        with (args.out/name).open("xb") as stream:
            stream.write(value)
    print("Verified 12 records, 72 native diagnostics, 216 derivations and 24 suites; result bytes match.")


if __name__ == "__main__":
    main()
