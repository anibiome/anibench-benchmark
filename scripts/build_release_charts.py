# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Build public chart aggregates by replaying the existing finite-task audit.

Output is a new directory. Raw calibration source files are never read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def build_release_charts(output: Path, root: Path) -> dict:
    root = root.resolve()
    runner = root / "scripts/audit_depth_population_tradeoff.py"
    runner_before = sha(runner.read_bytes())
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="anibench-chart-replay-") as temporary:
        replay = Path(temporary) / "replay"
        subprocess.run(
            [sys.executable, "-B", str(runner), "--out", str(replay)],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        receipt_bytes = (replay / "actual-api-receipts.json").read_bytes()
        provenance_bytes = (replay / "synthetic-provenance.json").read_bytes()
    receipts = json.loads(receipt_bytes)
    provenance = json.loads(provenance_bytes)
    if sha(runner.read_bytes()) != runner_before:
        raise ValueError("Audit source changed during replay")
    if receipts["source_sha256"] != "sha256:" + sha(provenance_bytes):
        raise ValueError("Synthetic provenance hash mismatch")
    if receipts["script_sha256"] != "sha256:" + runner_before:
        raise ValueError("Audit script hash mismatch")
    runs, gates = receipts["scalar_task_runs"], receipts["neural_role_gate_runs"]
    if len(runs) != 10 or len(gates) != 3 or receipts["assertions_passed"] != 34:
        raise ValueError("Unexpected audit shape; review chart adapter against new audit contract")
    points = []
    for index, run in enumerate(runs):
        receipt = run["receipt"]
        (metric,) = receipt["functionals"]
        # This is the real evaluator's value, not a separately scored browser result.
        variance = metric["posterior_variance"]
        if not isinstance(variance, (int, float)) or not math.isfinite(variance) or variance <= 0:
            raise ValueError("Invalid evaluator variance")
        pointer = f"/scalar_task_runs/{index}"
        points.append(
            {
                "point_id": run["design"]["id"] + ":" + run["task_name"],
                "design": run["design"],
                "task": run["task_name"],
                "unit": metric["unit"],
                "posterior_variance": variance,
                "posterior_standard_deviation": math.sqrt(variance),
                "likelihood_variance": run["analytic_likelihood_variance"],
                "illustrative_variance_limit": metric["variance_limit"],
                "attainment": receipt["attainment"],
                "prior_only_precision_attainment": metric["prior_only_precision_attainment"],
                "source_sha256": run["request"]["task"]["source_sha256"],
                "model_sha256": run["request"]["task"]["model_sha256"],
                "task_sha256": receipt["task_sha256"],
                "request_sha256": receipt["request_sha256"],
                "receipt_file": "release-chart-receipts.json",
                "receipt_pointer": pointer + "/receipt",
                "value_pointer": pointer + "/receipt/functionals/0/posterior_variance",
                "receipt_sha256": sha(encode(receipt)),
            }
        )
    role_gates = [
        {
            "gate_id": "neural-"
            + (
                "unknown"
                if g["declared_neural_support"] is None
                else "present"
                if g["declared_neural_support"]
                else "absent"
            ),
            "declared_neural_support": g["declared_neural_support"],
            "attainment": g["receipt"]["attainment"],
            "scalar_precision_state": g["receipt"]["functionals"][0]["state"],
            "request_sha256": g["receipt"]["request_sha256"],
            "receipt_file": "release-chart-receipts.json",
            "receipt_pointer": f"/neural_role_gate_runs/{index}/receipt",
            "receipt_sha256": sha(encode(g["receipt"])),
        }
        for index, g in enumerate(gates)
    ]
    if len({p["point_id"] for p in points}) != 10:
        raise ValueError("Duplicate chart point identities")
    # Preserve original ERP packet bytes and share-alike licensing separately.
    erp = root / "examples/calibration/erp_core"
    sensitivity_bytes = (erp / "design-sensitivity.json").read_bytes()
    plan_bytes = (erp / "illustrative-plan-results.json").read_bytes()
    sensitivity, plan = json.loads(sensitivity_bytes), json.loads(plan_bytes)
    aggregate_hash = sha((erp / "aggregate_results.json").read_bytes())
    if (
        sensitivity["aggregate_sha256"] != aggregate_hash
        or plan["bindings"]["aggregate_sha256"] != aggregate_hash
    ):
        raise ValueError("ERP outputs do not bind current public aggregates")
    if sensitivity["script_sha256"] != sha((erp / "design_sensitivity.py").read_bytes()):
        raise ValueError("ERP sensitivity code binding is stale")
    if plan["bindings"]["script_sha256"] != sha((erp / "plan_design.py").read_bytes()):
        raise ValueError("ERP planner code binding is stale")
    if plan["bindings"]["request_sha256"] != sha((erp / "illustrative-plan.json").read_bytes()):
        raise ValueError("ERP planner request binding is stale")
    if len(sensitivity["rows"]) != 27 or len(plan["rows"]) != 105:
        raise ValueError("ERP scenario shape changed; review chart adapters")
    files = {
        "release-chart-receipts.json": receipt_bytes,
        "release-chart-provenance.json": provenance_bytes,
        "erp-design-sensitivity.json": sensitivity_bytes,
        "erp-design-plan.json": plan_bytes,
    }
    packet = {
        "schema_version": "anibench.public-release-charts.v1",
        "license": "CC-BY-4.0",
        "copyright": "2026 ANI",
        "evidence_kind": "synthetic_executed_finite_task_model",
        "scope": "Separate scalar estimands; no joint covariance, real-study ranking or biological threshold",
        "biological_threshold_validated": False,
        "overall_rank": None,
        "audit_script_sha256": runner_before,
        "adapter_script_sha256": sha(Path(__file__).read_bytes()),
        "provenance_file": "release-chart-provenance.json",
        "provenance_sha256": sha(provenance_bytes),
        "receipts_file": "release-chart-receipts.json",
        "receipts_sha256": sha(receipt_bytes),
        "receipt_digest_encoding": "SHA-256 of sort_keys=True, indent=2 JSON plus LF, UTF-8; no NaN",
        "assertions_passed": receipts["assertions_passed"],
        "models": provenance["models"],
        "points": points,
        "neural_role_gates": role_gates,
        "external_chart_packets": [
            {
                "file": name,
                "sha256": sha(files[name]),
                "license": "CC-BY-SA-4.0",
                "evidence_kind": "empirical_aggregate_conditioned_hypothetical_design",
                "attribution": "ERP CORE contributors; Zhang and Luck (2023); https://doi.org/10.1111/psyp.14264",
                "source_path": "examples/calibration/erp_core/" + source,
            }
            for name, source in [
                ("erp-design-sensitivity.json", "design-sensitivity.json"),
                ("erp-design-plan.json", "illustrative-plan-results.json"),
            ]
        ],
    }
    files["release-results.json"] = encode(packet)
    # Only approved aggregate structures are emitted. Detect unintended local paths.
    for name, raw in files.items():
        if any(marker in raw for marker in (b"/Users/", b"/private/", b"/tmp/", b"file://")):
            raise ValueError("Local path found in public chart output: " + name)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        (output / name).write_bytes(raw)
    return {
        "schema_version": "anibench.release-chart-build.v1",
        "scalar_points": len(points),
        "role_gates": len(role_gates),
        "files": {name: sha(raw) for name, raw in files.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_release_charts(args.out, args.root), indent=2))


if __name__ == "__main__":
    main()
