"""Command-line front door for the public AniBench v2 candidate package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _parser() -> argparse.ArgumentParser:
    from . import __version__

    parser = argparse.ArgumentParser(prog="anibench")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    studio = sub.add_parser("studio", help="Run the local v2 trial-design Studio")
    studio.add_argument("--host", default="127.0.0.1")
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--unsafe-nonloopback", action="store_true")

    evaluation = sub.add_parser(
        "eval", help="Run the canonical six-task AniBench trial evaluation"
    )
    evaluation.add_argument("input", metavar="PROTOCOL_JSON", type=Path)
    evaluation.add_argument("--out", type=Path)
    evaluation.add_argument("--pretty", action="store_true")

    comparison = sub.add_parser(
        "compare", help="Compare canonical eval receipts on a strict shared Pareto basis"
    )
    comparison.add_argument("inputs", metavar="EVAL_JSON", nargs="+", type=Path)
    comparison.add_argument("--out", type=Path)
    comparison.add_argument("--pretty", action="store_true")

    for name, help_text in (
        ("v2-information", "Replay fail-closed v2 absolute information mechanics"),
        ("v2-design", "Compile a typed trial-design receipt"),
        ("v2-protocol-capacity", "Compile separate protocol-capacity families"),
        ("v2-level1-assessment", "Compile a role-aware six-family Level-1 receipt"),
        ("v2-optimize-protocol", "Explore protocol-native Pareto mutations"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("input", type=Path)
        command.add_argument("--out", type=Path)
        command.add_argument("--pretty", action="store_true")

    authority = sub.add_parser(
        "v2-level1-authority",
        help="Emit the role-aware Level-1 authority and hash-bound readback",
    )
    authority.add_argument("--out", type=Path)
    authority.add_argument("--pretty", action="store_true")

    atlas = sub.add_parser(
        "build-v2-source-atlas",
        help="Build the score-free external source atlas from its coordinate table",
    )
    atlas.add_argument("--coordinate-table", required=True, type=Path)
    atlas.add_argument("--out", required=True, type=Path)

    contracts = sub.add_parser(
        "v2-validate-contracts",
        help="Validate a bound v2 event/intervention/uncertainty contract bundle",
    )
    contracts.add_argument("--event-manifest", required=True, type=Path)
    contracts.add_argument("--intervention-design", required=True, type=Path)
    contracts.add_argument("--uncertainty", required=True, type=Path)
    contracts.add_argument("--out", type=Path)
    contracts.add_argument("--pretty", action="store_true")

    intake = sub.add_parser(
        "intake-ctgov",
        help="Capture an immutable, human-review-required ClinicalTrials.gov snapshot",
    )
    intake.add_argument("nct_id")
    intake.add_argument("--out", type=Path, required=True)

    search = sub.add_parser("search-ctgov", help="Capture a ClinicalTrials.gov search page")
    search.add_argument("query")
    search.add_argument("--page-size", type=int, default=10)
    search.add_argument("--page-token")
    search.add_argument("--out", type=Path, required=True)

    protocol = sub.add_parser(
        "intake-protocol",
        help="Capture and extract a bounded trial protocol PDF for human review",
    )
    protocol.add_argument("url")
    protocol.add_argument("--nct-id")
    protocol.add_argument("--out", type=Path, required=True)
    return parser


def _load_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be one JSON object")
    return payload


def _emit(
    result: dict[str, Any],
    *,
    out: Path | None,
    pretty: bool,
    receipt: dict[str, Any] | None = None,
) -> None:
    rendered = json.dumps(result, indent=2 if pretty else None, sort_keys=True)
    if out is None:
        print(rendered)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out), **(receipt or {})}, sort_keys=True))


def _write_snapshot(snapshot: Any, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(snapshot.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"written": str(out), "intake_id": snapshot.intake_id, "score_eligible": False},
            sort_keys=True,
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "studio":
            from .studio import serve_studio

            serve_studio(args.host, args.port, unsafe_nonloopback=args.unsafe_nonloopback)
            return 0
        if args.command == "v2-information":
            from .v2 import load_information_run, score_information_run

            result = score_information_run(load_information_run(args.input))
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={"promotion_allowed": False},
            )
            return 0
        if args.command == "v2-design":
            from .design_v2 import compile_design, load_design_input

            result = compile_design(load_design_input(args.input))
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={"input_sha256": result["input_sha256"]},
            )
            return 0
        if args.command == "v2-protocol-capacity":
            from .protocol_capacity_v2 import compile_protocol_capacity

            result = compile_protocol_capacity(
                _load_object(args.input, label="protocol-capacity input")
            )
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={
                    "protocol_sha256": result["protocol_sha256"],
                    "comparison_eligible": result["comparison_eligible"],
                },
            )
            return 0
        if args.command == "compare":
            from .comparison_v1 import compare_trial_evals

            result = compare_trial_evals(
                [
                    _load_object(path, label=f"eval receipt {index}")
                    for index, path in enumerate(args.inputs)
                ]
            )
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={
                    "comparison_receipt_sha256": result["comparison_receipt_sha256"],
                    "comparison_class": result["comparison_class"],
                    "comparison_eligible": result["comparison_eligible"],
                    "protocol_count": len(result["protocol_ids"]),
                },
            )
            return 0
        if args.command in {"eval", "v2-level1-assessment"}:
            from .level1_assessment_v3 import assess_protocol_capacity_role_aware

            result = assess_protocol_capacity_role_aware(
                _load_object(args.input, label="Level-1 protocol-capacity input")
            )
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={
                    "eval_command": "eval",
                    "assessment_receipt_sha256": result["assessment_receipt_sha256"],
                    "comparison_eligible": result["comparison_eligible"],
                    "task_count": len(result["scenarios"][0]["families"]),
                },
            )
            return 0
        if args.command == "v2-level1-authority":
            from .level1_assessment_v3 import level1_role_aware_authority_summary

            _emit(
                level1_role_aware_authority_summary(),
                out=args.out,
                pretty=args.pretty,
            )
            return 0
        if args.command == "v2-optimize-protocol":
            from .optimizer_protocol_v2 import optimize_protocol

            result = optimize_protocol(_load_object(args.input, label="optimizer input"))
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={
                    "optimizer_request_sha256": result["optimizer_request_sha256"],
                    "candidate_count": result["candidate_count"],
                },
            )
            return 0
        if args.command == "build-v2-source-atlas":
            from .source_atlas_v2 import build_source_atlas

            print(json.dumps({"written": str(build_source_atlas(args.coordinate_table, args.out))}))
            return 0
        if args.command == "v2-validate-contracts":
            from .contracts_v2 import load_contract_json, validate_contract_bundle

            result = validate_contract_bundle(
                load_contract_json(args.event_manifest),
                load_contract_json(args.intervention_design),
                load_contract_json(args.uncertainty),
            )
            _emit(
                result,
                out=args.out,
                pretty=args.pretty,
                receipt={"validation_state": result["validation_state"]},
            )
            return 0 if result["semantic_valid"] else 2
        if args.command in {"intake-ctgov", "search-ctgov", "intake-protocol"}:
            from .intake import (
                snapshot_clinicaltrials_search,
                snapshot_clinicaltrials_study,
                snapshot_protocol_pdf,
            )

            if args.command == "intake-ctgov":
                snapshot = snapshot_clinicaltrials_study(args.nct_id)
            elif args.command == "search-ctgov":
                snapshot = snapshot_clinicaltrials_search(
                    args.query, page_size=args.page_size, page_token=args.page_token
                )
            else:
                snapshot = snapshot_protocol_pdf(args.url, nct_id=args.nct_id)
            _write_snapshot(snapshot, args.out)
            return 0
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
