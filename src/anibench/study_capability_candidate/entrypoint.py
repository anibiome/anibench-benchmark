# ruff: noqa: TRY004 -- invalid JSON inputs consistently raise ValueError
# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Private local intake and create-only linked-capability result export."""

import argparse
import gzip
import hashlib
import json
from importlib.resources import files
from pathlib import Path

from . import compiler
from .level_decision import decide_level
from .linked_workload import evaluate, validate_raw


def load_input(payload):
    if not isinstance(payload, dict):
        raise ValueError("Input must be a design object or a bind-design evidence bundle")
    if set(payload) == {"design", "receipt", "evidence"}:
        design = payload["design"]
        receipt = payload["receipt"]
        evidence = payload["evidence"]
        if not all(isinstance(v, dict) for v in [design, receipt, evidence]):
            raise ValueError("Malformed bound-design bundle")
        if (
            receipt.get("schema") != "anibench.capability-intake-receipt.v1"
            or evidence.get("schema") != "anibench.capability-source-bindings.v1"
        ):
            raise ValueError("Unsupported bound-design receipt")
        source = compiler.digest(evidence)
        if (
            receipt.get("evidence_sha256") != source
            or design.get("source_sha256") != source
            or receipt.get("design_sha256") != compiler.digest(design)
        ):
            raise ValueError("Stale bound-design/evidence identity")
        bare = {k: v for k, v in design.items() if k != "source_sha256"}
        if bare != evidence.get("design"):
            raise ValueError("Bound design differs from evidence snapshot")
        # This checks immutable intake identity. It cannot independently authenticate
        # historical source truth; keep the original source/review qualification.
        return validate_raw(design), receipt
    return validate_raw(payload), None


def add_arguments(parser):
    """Share the exact input contract between module and top-level entry points."""
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Check input structure and immutable bindings without evaluating or writing files",
    )
    parser.add_argument("input", type=Path, help="Design JSON or output of anibench bind-design")
    parser.add_argument(
        "--out",
        type=Path,
        help="New result directory, required unless --validate-only; never overwrite an existing path",
    )
    parser.add_argument(
        "--noise-profile",
        choices=["normative", "common-noise-grid-v1"],
        default="normative",
        help="Normative q1/q2 or separately labelled frozen common-noise sensitivity",
    )
    parser.add_argument(
        "--resolution",
        choices=["standard", "fine"],
        default="standard",
        help="Expanded native36 pilot resolution; fine halves standard SE limits, not a native31 AB certificate",
    )
    parser.add_argument(
        "--study-profile",
        choices=["native36-operator-pilot-v2", "native36-capability-v3"],
        default="native36-capability-v3",
        help="Source-corrected native36 likelihood profile or separately named temporal-prediction/plain-RCT profile; old catalogues require their preserved package version",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate finite native-panel study capability locally. Primary metric: benchmark tasks met; continuous precision is secondary."
    )
    add_arguments(parser)
    args = parser.parse_args(argv)
    args.level = "AB1" if args.resolution == "standard" else "AB2"
    try:
        design, intake = load_input(json.loads(args.input.read_text(encoding="utf-8")))
        if args.validate_only:
            print(
                json.dumps(
                    {
                        "valid": True,
                        "input_sha256": compiler.digest(design),
                        "study_profile": args.study_profile,
                        "scope": "Input semantics and supplied bindings only; source truth and numerical results not verified",
                    }
                )
            )
            return
        if args.out is None:
            raise ValueError("--out is required unless --validate-only")
        if args.out.exists():
            raise ValueError("Output directory already exists")
        if args.study_profile == "native36-capability-v3":
            from .study_profile import evaluate as evaluate_profile

            result, components, profile = evaluate_profile(
                design, args.resolution, args.noise_profile
            )
        elif args.noise_profile == "common-noise-grid-v1":
            from .noise_sensitivity import evaluate_sensitivity

            result, components, profile = evaluate_sensitivity(design, args.level)
        else:
            result, components = evaluate(design, 1.0 if args.level == "AB1" else 0.5)
            profile = json.loads(
                files(__package__).joinpath(compiler.reference_filename(args.level)).read_text()
            )
        result["intake_receipt_sha256"] = None if intake is None else compiler.digest(intake)
        result["requested_resolution"] = "standard" if args.level == "AB1" else "fine"
        result["catalogue_profile"] = "native36-operator-pilot-v2"
        result["reference_profile_sha256"] = compiler.digest(profile)
        if args.noise_profile == "normative" and args.study_profile == "native36-operator-pilot-v2":
            result["expanded_profile_decision"] = decide_level(result, components, profile)
        result.pop("result_sha256", None)
        result["result_sha256"] = compiler.digest(result)
        args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
        (args.out / "RESULT.json").write_text(
            json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        )
        with (
            (args.out / "CANONICAL_COMPONENTS.json.gz").open("xb") as raw,
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
        ):
            for chunk in json.JSONEncoder(
                sort_keys=True, separators=(",", ":"), allow_nan=False
            ).iterencode(components):
                compressed.write(chunk.encode())
        if args.study_profile == "native36-capability-v3":
            (args.out / "REFERENCE_PROFILE.json").write_text(
                json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            )
        artifact_receipt = {
            "schema": "anibench.linked-export-receipt.v1",
            "original_input_sha256": compiler.digest(design),
            "reference_profile_sha256": compiler.digest(profile),
            "final_result_sha256": result["result_sha256"],
            "canonical_components_sha256": compiler.digest(components),
            "entrypoint_sha256": "sha256:"
            + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "files": {
                name: "sha256:" + hashlib.sha256((args.out / name).read_bytes()).hexdigest()
                for name in (
                    ["RESULT.json", "CANONICAL_COMPONENTS.json.gz"]
                    + (
                        ["REFERENCE_PROFILE.json"]
                        if args.study_profile == "native36-capability-v3"
                        else []
                    )
                )
            },
        }
        (args.out / "RECEIPT.json").write_text(json.dumps(artifact_receipt, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "result_sha256": result["result_sha256"],
                    "scenario_count": len(result["scenarios"]),
                    "canonical_component_count": len(components),
                    "scope": "Conditional finite native-panel capability; not empirical all-biology calibration",
                }
            )
        )
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, "AniBench input/output error: " + str(error) + "\n")
