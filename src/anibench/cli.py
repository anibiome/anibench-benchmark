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

    workbench = sub.add_parser("workbench", help="Open local comparisons and the reference design planner")
    workbench.add_argument("--port", type=int, default=8795)
    workbench.add_argument("--ttl", type=int, default=1800,
                           help="Automatic stop after 1–3600 seconds")

    plan = sub.add_parser("plan", help="Evaluate before/after designs against the conditional reference")
    plan.add_argument("input", type=Path)
    plan.add_argument("--out", type=Path, required=True)

    study = sub.add_parser(
        "study-capability", help="Evaluate a study against the finite native-measurement workload"
    )
    from .study_capability_candidate.entrypoint import add_arguments

    add_arguments(study)

    paired = sub.add_parser(
        "paired-question", help="Evaluate linked molecular/function questions under a declared reference"
    )
    paired.add_argument("input", type=Path)
    paired.add_argument("--out", type=Path, required=True)

    collection = sub.add_parser(
        "paired-collection", help="Evaluate a linked question with different measurement subsets"
    )
    collection.add_argument("input", type=Path)
    collection.add_argument("--out", type=Path, required=True)

    cross_domain = sub.add_parser(
        "cross-domain-collection", help="Evaluate linked native observers and a functional target"
    )
    cross_domain.add_argument("input", type=Path)
    cross_domain.add_argument("--out", type=Path, required=True)

    questions = sub.add_parser(
        "study-questions", help="Evaluate biological questions against an explicit fixed reference"
    )
    questions.add_argument("profile", type=Path, help="Reference profile to trust for this run")
    questions.add_argument("input", type=Path, help="Original study inputs, not precomputed scores")
    questions.add_argument("--out", type=Path, required=True)

    moments = sub.add_parser(
        "estimator-moments", help="Check a registered estimator against native error targets"
    )
    moments.add_argument("definition", type=Path, help="Estimator definition to trust for this run")
    moments.add_argument("input", type=Path, help="Qualified moments, support and physical inputs")
    moments.add_argument("--out", type=Path, required=True)

    study_chart = sub.add_parser(
        "study-chart", help="Draw comparable category percentages from verified study results"
    )
    study_chart.add_argument("input", type=Path)
    study_chart.add_argument("--scenario", required=True)
    study_chart.add_argument("--published-only", action="store_true")
    study_chart.add_argument("--irb-only", action="store_true")
    study_chart.add_argument("--out", type=Path, required=True)

    evaluation = sub.add_parser(
        "eval", help="Run the canonical six-task AniBench trial evaluation"
    )
    evaluation.add_argument("input", metavar="PROTOCOL_JSON", type=Path)
    evaluation.add_argument("--out", type=Path)
    evaluation.add_argument("--pretty", action="store_true")

    profile = sub.add_parser(
        "profile", help="Summarize private study collection, linkage, QC, and follow-up"
    )
    profile.add_argument("input", metavar="COLLECTION_JSON", type=Path)
    profile.add_argument("--out", type=Path, required=True)
    profile.add_argument("--pretty", action="store_true")

    tables = sub.add_parser(
        "profile-tables", help="Profile explicitly mapped local CSV or CSV.gz study tables"
    )
    tables.add_argument("input", metavar="TABLE_MAP_JSON", type=Path)
    tables.add_argument("--out", type=Path, required=True)
    tables.add_argument("--manifest-out", type=Path, help="Optional private participant-linked intermediate")
    tables.add_argument("--pretty", action="store_true")

    context = sub.add_parser(
        "study-context", help="Bind evidence metadata or a hypothetical approval copy to local bytes"
    )
    actions = context.add_subparsers(dest="context_action", required=True)
    for action in ("create", "assume-approval", "verify"):
        command = actions.add_parser(action)
        command.add_argument("input", metavar="DESIGN_INPUT", type=Path)
        command.add_argument("--result", type=Path, help="Optional exact result bytes to bind")
        if action == "verify":
            command.add_argument("--context", type=Path, required=True)
            command.add_argument("--parent", type=Path)
        else:
            command.add_argument("--id", dest="record_id", required=True)
            command.add_argument("--name", required=True)
            command.add_argument("--out", type=Path, required=True)
            command.add_argument("--pretty", action="store_true")
            if action == "create":
                command.add_argument("--evidence", type=Path,
                                     help="Optional publication/ethics evidence JSON; default unknown")
            else:
                command.add_argument("--parent", type=Path, required=True)
                command.add_argument("--reason", required=True)

    records = sub.add_parser(
        "compare-records", help="Compare one native collection metric with explicit evidence bounds"
    )
    records.add_argument("inputs", metavar="PROFILE_JSON", nargs="+", type=Path)
    records.add_argument("--basis", type=Path, required=True)
    records.add_argument("--out", type=Path, required=True)
    records.add_argument("--pretty", action="store_true")

    architecture = sub.add_parser(
        "compare-architecture", help="Compare source-reported study quantities on an explicit basis"
    )
    architecture.add_argument("input", metavar="ARCHITECTURE_JSON", type=Path)
    architecture.add_argument("--out", type=Path, required=True)
    architecture.add_argument("--pretty", action="store_true")

    comparison = sub.add_parser(
        "compare", help="Compare canonical eval receipts on a strict shared Pareto basis"
    )
    comparison.add_argument("inputs", metavar="EVAL_JSON", nargs="+", type=Path)
    comparison.add_argument("--out", type=Path)
    comparison.add_argument("--pretty", action="store_true")

    suite = sub.add_parser("finite-suite", help="Evaluate one frozen finite-target profile")
    suite.add_argument("input", type=Path)
    suite.add_argument("--registry", type=Path, required=True,
                       help="Explicit trusted local profile map keyed by SHA-256")
    suite.add_argument("--out", type=Path)
    suite.add_argument("--pretty", action="store_true")

    benchmark = sub.add_parser("benchmark", help="Evaluate frozen workload category percentages")
    benchmark.add_argument("input", type=Path)
    benchmark.add_argument("--registry", type=Path, required=True,
                           help="Trusted local finite-suite profiles keyed by SHA-256")
    benchmark.add_argument("--scores", type=Path, required=True,
                           help="Trusted local category/weight profiles keyed by SHA-256")
    benchmark.add_argument("--out", type=Path, required=True,
                           help="New result path; existing files are preserved")

    summary = sub.add_parser("summary-task", help="Compile native summary sampling precision")
    summary.add_argument("input", type=Path, help="JSON object with task, summary and evidence")
    summary.add_argument("--out", type=Path, required=True,
                         help="New derivation path; existing files are preserved")

    binding = sub.add_parser("bind-design", help="Bind local design fields to sources and assumptions")
    binding.add_argument("input", type=Path, help="JSON object with design, bindings and sources")
    binding.add_argument("--reviews", type=Path,
                         help="Explicit trusted review map; omitted means no extraction reviews trusted")
    binding.add_argument("--out", type=Path, required=True,
                         help="New private evidence bundle; existing files are preserved")

    for name, help_text in (
        ("finite-task", "Evaluate a frozen finite precision task under declared geometry"),
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


def _load_object(path: Path, *, label: str, strict_decimals: bool = False) -> dict[str, Any]:
    options = {}
    if strict_decimals:
        from decimal import Decimal

        def parse_number(text):
            value = float(text)
            if not Decimal(text).is_finite() or Decimal(str(value)) != Decimal(text):
                raise ValueError("JSON number loses decimal precision")
            return value

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON member")
                result[key] = value
            return result

        options = {"parse_float": parse_number, "object_pairs_hook": unique_object}
    payload = json.loads(path.read_text(encoding="utf-8"), **options)
    if not isinstance(payload, dict):
        # Malformed file content is a value error in the public CLI contract.
        raise ValueError(f"{label} must be one JSON object")  # noqa: TRY004
    return payload


def _emit(
    result: dict[str, Any],
    *,
    out: Path | None,
    pretty: bool,
    receipt: dict[str, Any] | None = None,
    report_path: bool = True,
) -> None:
    rendered = json.dumps(result, indent=2 if pretty else None, sort_keys=True)
    if out is None:
        print(rendered)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps({**({"written": str(out)} if report_path else {}),
                      **(receipt or {})}, sort_keys=True))


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


def _protect_collection_inputs(inputs: list[Path], outputs: list[Path]) -> None:
    """Do not let a result path overwrite its private source or other output."""
    def resolve(path: Path) -> Path:
        try:
            return path.resolve()
        except (OSError, RuntimeError) as exc:
            raise ValueError("Unable to resolve input or output paths") from exc

    protected = list(inputs)
    for output in outputs:
        for source in protected:
            if resolve(output) == resolve(source) or (
                output.exists() and source.exists() and output.samefile(source)
            ):
                raise ValueError("Outputs must be distinct from inputs and each other")
        protected.append(output)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command in ("study-questions", "estimator-moments"):
            import os

            from .question_routes_v1 import digest

            try:
                reference_path = args.profile if args.command == "study-questions" else args.definition
                _protect_collection_inputs([reference_path, args.input], [args.out])
                if args.out.exists():
                    raise ValueError("Destination already exists")
                strict = args.command == "estimator-moments"
                profile = _load_object(reference_path, label="biological reference", strict_decimals=strict)
                if (args.command == "study-questions"
                        and profile.get("contract") == "anibench.study-question-profile.v4"):
                    strict = True
                    profile = _load_object(reference_path, label="biological reference", strict_decimals=True)
                request = _load_object(args.input, label="study question inputs", strict_decimals=strict)
                if args.command == "study-questions":
                    from .study_questions_v2 import evaluate_study_questions

                    result = evaluate_study_questions(request, trusted_profiles={digest(profile): profile})
                else:
                    from .estimator_moments_v1 import evaluate_estimator_moments

                    result = evaluate_estimator_moments(request, trusted_definitions={digest(profile): profile})
                content = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
                args.out.parent.mkdir(parents=True, exist_ok=True)
                descriptor = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(content)
            except (OSError, ValueError, TypeError, KeyError, RuntimeError):
                print("Evaluation failed; check the input contracts and choose a new output path.",
                      file=sys.stderr)
                return 2
            print(json.dumps({"contract": result["contract"], "receipt_sha256": result["receipt_sha256"]}))
            return 0
        if args.command in ("paired-question", "paired-collection", "cross-domain-collection"):
            if args.command == "paired-question":
                from .paired_question_v1 import evaluate_paired_question as evaluate_paired
            elif args.command == "cross-domain-collection":
                from .cross_domain_collection_v1 import (
                    evaluate_cross_domain_collection as evaluate_paired,
                )
            else:
                from .paired_collection_v1 import evaluate_paired_collection as evaluate_paired

            _protect_collection_inputs([args.input], [args.out])
            result = evaluate_paired(_load_object(args.input, label="paired biological input"))
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
            print(json.dumps({"contract": result["contract"], "receipt_sha256": result["receipt_sha256"]}))
            return 0
        if args.command == "study-capability":
            from .study_capability_candidate.entrypoint import main as capability_main

            capability_main([
                str(args.input),
                "--resolution", args.resolution, "--noise-profile", args.noise_profile,
                "--study-profile", args.study_profile,
            ] + (["--out", str(args.out)] if args.out is not None else [])
              + (["--validate-only"] if args.validate_only else []))
            return 0
        if args.command == "study-chart":
            from .study_capability_candidate.charts import main as chart_main

            chart_main([
                str(args.input), "--out", str(args.out), "--scenario", args.scenario,
            ] + (["--published-only"] if args.published_only else [])
              + (["--irb-only"] if args.irb_only else []))
            return 0
        if args.command == "workbench":
            from .workbench import serve_workbench

            serve_workbench(args.port, args.ttl)
            return 0
        if args.command == "plan":
            from .reference_planner import evaluate_plan

            _protect_collection_inputs([args.input], [args.out])
            result = evaluate_plan(_load_object(args.input, label="reference design"))
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
            print(json.dumps({"written": str(args.out), "contract": result["contract"]}))
            return 0
        if args.command == "studio":
            from .studio import serve_studio

            serve_studio(args.host, args.port, unsafe_nonloopback=args.unsafe_nonloopback)
            return 0
        if args.command == "study-context":
            from .study_context import create_context, hypothetical_approval_copy, validate_context

            inputs = [args.input] + ([args.result] if args.result is not None else [])
            for name in ("parent", "context", "evidence"):
                value = getattr(args, name, None)
                if value is not None:
                    inputs.append(value)
            out = getattr(args, "out", None)
            _protect_collection_inputs(inputs, [out] if out is not None else [])
            input_bytes = args.input.read_bytes()
            result_bytes = args.result.read_bytes() if args.result is not None else None
            parent_path = getattr(args, "parent", None)
            parent = _load_object(parent_path, label="parent context") if parent_path else None
            if args.context_action == "verify":
                result = _load_object(args.context, label="study context")
                validate_context(result, input_bytes=input_bytes,
                                 result_bytes=result_bytes, parent=parent)
                print(json.dumps({"valid": True, "context_sha256": result["context_sha256"],
                                  "scientific_result_verified": False}))
                return 0
            if args.context_action == "create":
                evidence = _load_object(args.evidence, label="study evidence") if args.evidence else None
                result = create_context(args.record_id, args.name, input_bytes=input_bytes,
                                        result_bytes=result_bytes, evidence=evidence)
            else:
                result = hypothetical_approval_copy(
                    parent, args.record_id, args.name, reason=args.reason,
                    input_bytes=input_bytes, result_bytes=result_bytes,
                )
            _emit(result, out=out, pretty=args.pretty,
                  receipt={"context_sha256": result["context_sha256"]}, report_path=False)
            return 0
        if args.command == "compare-architecture":
            from .architecture_v1 import compare_architecture

            _protect_collection_inputs([args.input], [args.out])
            result = compare_architecture(_load_object(args.input, label="architecture request"))
            _emit(result, out=args.out, pretty=args.pretty,
                  receipt={"receipt_sha256": result["receipt_sha256"],
                           "basis_sha256": result["basis_sha256"]}, report_path=False)
            return 0
        if args.command == "finite-suite":
            from .finite_suites_v1 import evaluate_finite_suite

            _protect_collection_inputs([args.input, args.registry],
                                       [args.out] if args.out is not None else [])
            result = evaluate_finite_suite(
                _load_object(args.input, label="finite-suite request"),
                trusted_profiles=_load_object(args.registry, label="trusted profile registry"),
            )
            _emit(result, out=args.out, pretty=args.pretty,
                  receipt={"profile_sha256": result["profile_sha256"],
                           "request_sha256": result["request_sha256"],
                           "attainment": result["attainment"]}, report_path=False)
            return 0
        if args.command == "bind-design":
            from .source_bindings_v1 import bind_design

            inputs = [args.input] + ([args.reviews] if args.reviews else [])
            _protect_collection_inputs(inputs, [args.out])
            payload = _load_object(args.input, label="design source bindings")
            if set(payload) != {"design", "bindings", "sources"}:
                raise ValueError("Expected exactly design, bindings and sources")
            reviews = _load_object(args.reviews, label="trusted extraction reviews") if args.reviews else {}
            design, receipt, evidence = bind_design(**payload, trusted_review_receipts=reviews)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump({"design": design, "receipt": receipt, "evidence": evidence},
                          stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
            print(json.dumps({"evidence_sha256": receipt["evidence_sha256"],
                              "design_sha256": receipt["design_sha256"]}))
            return 0
        if args.command == "summary-task":
            from .summary_geometry_v1 import compile_summary_task

            _protect_collection_inputs([args.input], [args.out])
            payload = _load_object(args.input, label="summary task")
            if set(payload) != {"task", "summary", "evidence"}:
                raise ValueError("Expected exactly task, summary and evidence")
            result = compile_summary_task(**payload)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
            print(json.dumps({"derivation_sha256": result["derivation_sha256"],
                              "status": result["status"]}))
            return 0
        if args.command == "benchmark":
            from .benchmark_v1 import evaluate_benchmark

            _protect_collection_inputs([args.input, args.registry, args.scores], [args.out])
            result = evaluate_benchmark(
                _load_object(args.input, label="benchmark request"),
                trusted_profiles=_load_object(args.registry, label="trusted suite registry"),
                trusted_score_profiles=_load_object(args.scores, label="trusted score registry"),
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
            print(json.dumps({"receipt_sha256": result["receipt_sha256"],
                              "level_attainment": result["level_attainment"]}))
            return 0
        if args.command == "finite-task":
            from .finite_tasks_v1 import evaluate_finite_task

            _protect_collection_inputs([args.input], [args.out] if args.out is not None else [])
            result = evaluate_finite_task(_load_object(args.input, label="finite-task request"))
            _emit(result, out=args.out, pretty=args.pretty,
                  receipt={"task_sha256": result["task_sha256"],
                           "attainment": result["attainment"]})
            return 0
        if args.command == "profile":
            from .collection_v1 import profile_collection

            _protect_collection_inputs([args.input], [args.out])
            result = profile_collection(_load_object(args.input, label="collection record"))
            _emit(
                result, out=args.out, pretty=args.pretty,
                receipt={"profile_sha256": result["profile_sha256"]},
            )
            return 0
        if args.command == "compare-records":
            from .collection_compare import compare_collection_profiles

            _protect_collection_inputs([*args.inputs, args.basis], [args.out])
            result = compare_collection_profiles(
                [_load_object(path, label="collection profile") for path in args.inputs],
                _load_object(args.basis, label="comparison basis"),
            )
            _emit(result, out=args.out, pretty=args.pretty,
                  receipt={"comparison_sha256": result["comparison_sha256"]})
            return 0
        if args.command == "profile-tables":
            from .collection_ingest import import_collection_tables
            from .collection_v1 import profile_collection

            mapping = _load_object(args.input, label="table mapping")
            base = args.input.resolve().parent
            manifest, audit = import_collection_tables(mapping, base=base)
            _protect_collection_inputs(
                [args.input] + [base / source["path"] for source in mapping["sources"]],
                [args.out] + ([args.manifest_out] if args.manifest_out is not None else []),
            )
            profile = profile_collection(manifest)
            if args.manifest_out is not None:
                _emit(manifest, out=args.manifest_out, pretty=args.pretty)
            _emit(
                {"schema_version": "anibench.collection-table-evaluation.v1",
                 "profile": profile, "import_audit": audit},
                out=args.out, pretty=args.pretty,
                receipt={"profile_sha256": profile["profile_sha256"]},
            )
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
        if args.command in ("paired-question", "paired-collection", "cross-domain-collection") and isinstance(exc, OSError):
            print("Unable to read input or create a new result file", file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
