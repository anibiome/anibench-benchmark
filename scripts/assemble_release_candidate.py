#!/usr/bin/env python3
"""Assemble, scan, hash, verify, and archive an AniBench review candidate."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Mapping

from anibench.release import (
    VALIDATION_LAYER_NAMES,
    build_release_receipt,
    generate_sha256sums,
    refresh_release_receipt_id,
    scan_public_bundle,
    verify_release,
    write_release_receipt,
)

try:
    from scripts.validate_code_red_release import validate_code_red_release
    from scripts.verify_distribution_boundary import inspect_distribution
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from validate_code_red_release import validate_code_red_release
    from verify_distribution_boundary import inspect_distribution


# Public-v2 review boundary. Every executable, schema, authority, fixture, and
# test is named. Never replace these lists with broad repository-root copies.
EXTERNAL_SOURCE_ATLAS_STUDY_IDS = (
    "all-of-us-cdrv9",
    "aspree",
    "calerie-phase-2-expanded",
    "circulate-tpe-ivig",
    "do-health-bio-age",
    "dq-senolytic-bone",
    "life-study",
    "mitoimmune-urolithin-a",
    "motrpac-human-pre-suspension-expanded",
    "pearl-rapamycin",
    "predict-1",
    "sheba-sharp",
    "snyder-ipop-ihmp-106",
    "triim",
    "uk-biobank",
    "zoe-method",
)

PUBLIC_SOURCE_ATLAS_MEMBERS = (
    "data/source_projections/v2/EXTERNAL_SOURCE_ACQUISITION_LEDGER.json",
    *(
        f"data/source_projections/v2/{study_id}.json"
        for study_id in EXTERNAL_SOURCE_ATLAS_STUDY_IDS
    ),
)

PUBLIC_V2_SCHEMAS = (
    "schemas/v2/design-assessment.schema.json",
    "schemas/v2/design-input.schema.json",
    "schemas/v2/event-manifest.schema.json",
    "schemas/v2/information-run.schema.json",
    "schemas/v2/intervention-design.schema.json",
    "schemas/v2/level1-coordinate-registry.schema.json",
    "schemas/v2/optimizer-protocol-input.schema.json",
    "schemas/v2/optimizer-protocol-result.schema.json",
    "schemas/v2/protocol-capacity-input.schema.json",
    "schemas/v2/protocol-capacity-result.schema.json",
    "schemas/v2/reference-registry.schema.json",
    "schemas/v2/uncertainty.schema.json",
    "schemas/v3/level1-role-aware-assessment.schema.json",
    "schemas/v3/level1-role-aware-target-authority.schema.json",
    "schemas/v3/level1-v2-to-v3-impact-receipt.schema.json",
)

PUBLIC_V2_SPEC = (
    "spec/v2/authority/causal-encoding.json",
    "spec/v2/authority/covariance-scenario-envelopes.json",
    "spec/v2/authority/event-unit-registry.json",
    "spec/v2/authority/manifest.json",
    "spec/v2/authority/measurement-operator-profiles.json",
    "spec/v2/authority/moderator-id-registry.json",
    "spec/v2/authority/parameter-space-prior-target.json",
    "spec/v2/authority/transport-encoding.json",
    "spec/v2/level1/biological-coordinate-registry.json",
    "spec/v3/level1/role-aware-target-requirements.v3.json",
    "spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json",
    "spec/v2/mechanics-fixtures/illustrative-reference-2d.json",
    "spec/v2/parameter-space.json",
    "spec/v2/reference-registry.json",
)

# The package source remains explicit so a withdrawn module cannot re-enter a
# release because somebody added a file under src/. Legacy commands will be
# removed from the public front door separately; optimizer_v2.py is excluded now.
PUBLIC_PYTHON_MODULES = (
    "src/anibench/__init__.py",
    "src/anibench/api.py",
    "src/anibench/causal_v2.py",
    "src/anibench/cli.py",
    "src/anibench/contracts/__init__.py",
    "src/anibench/contracts/identifiers.py",
    "src/anibench/contracts_v2.py",
    "src/anibench/design_v2.py",
    "src/anibench/information_v2.py",
    "src/anibench/intake.py",
    "src/anibench/level1_assessment_v3.py",
    "src/anibench/level1_target_v3.py",
    "src/anibench/optimizer_protocol_v2.py",
    "src/anibench/paths.py",
    "src/anibench/protocol_capacity_v2.py",
    "src/anibench/release/__init__.py",
    "src/anibench/release/redact.py",
    "src/anibench/source_atlas_v2.py",
    "src/anibench/studio.py",
    "src/anibench/studio_product.py",
    "src/anibench/uncertainty_v2.py",
    "src/anibench/v2.py",
)

PUBLIC_V2_ALLOWLIST = (
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/evidence-challenge.yml",
    ".github/ISSUE_TEMPLATE/methods-rfc.yml",
    ".github/ISSUE_TEMPLATE/new-study.yml",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/workflows/codeql.yml",
    ".github/workflows/pr.yml",
    ".github/workflows/release.yml",
    ".gitignore",
    ".zenodo.json",
    "AGENTS.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CURRENT.md",
    "GOVERNANCE.md",
    "LICENSE",
    "LICENSE-DATA",
    "LICENSES/Apache-2.0.txt",
    "LICENSES/CC-BY-4.0.txt",
    "Makefile",
    "README.md",
    "ROADMAP.md",
    "REUSE.toml",
    "SECURITY.md",
    "codemeta.json",
    *PUBLIC_SOURCE_ATLAS_MEMBERS,
    "docs/ANTI_GAMING.md",
    "docs/ACCESSIBILITY.md",
    "docs/API.md",
    "docs/DESIGN_STUDIO.md",
    "docs/EVIDENCE_POLICY.md",
    "docs/DATA_GOVERNANCE.md",
    "docs/HOW_TO_READ_ANIBENCH.md",
    "docs/INTAKE_AND_ADJUDICATION.md",
    "docs/RELEASE.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/SCIENTIFIC_FOUNDATIONS.md",
    "docs/V2_METHODS_CANDIDATE.md",
    "docs/V2_OPTIMIZER.md",
    "examples/optimizer_protocol_v2_example.py",
    "examples/v2/illustrative-design.json",
    "examples/v2/illustrative-protocol-source.json",
    "openapi/anibench-v2-candidate.yaml",
    "packaging/PUBLIC_PACKAGE_ALLOWLIST.md",
    "packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
    "packaging/public_v2/EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json",
    "packaging/public_v2/REPOSITORY_ALLOWLIST.txt",
    "packaging/public_v2/SOURCE_COORDINATE_TABLE.csv",
    "paper/v2/AniBench_v2_benchmark_protocol.md",
    "paper/v2/build_method_figures.py",
    "paper/v2/REPORTING_CHECKLIST.md",
    "paper/v2/figures/figure_01_source_bound_pipeline.png",
    "paper/v2/figures/figure_01_source_bound_pipeline.svg",
    "paper/v2/figures/figure_02_six_family_map.png",
    "paper/v2/figures/figure_02_six_family_map.svg",
    "paper/v2/figures/figure_03_same_event_antigaming.png",
    "paper/v2/figures/figure_03_same_event_antigaming.svg",
    "paper/v2/figures/figure_04_evidence_lanes.png",
    "paper/v2/figures/figure_04_evidence_lanes.svg",
    "pyproject.toml",
    *PUBLIC_V2_SCHEMAS,
    "scripts/assemble_release_candidate.py",
    "scripts/build_docx_package.py",
    "scripts/build_level1_target_v3.py",
    "scripts/build_v2_external_corpus.py",
    "scripts/export_public_repository.py",
    "scripts/fetch_v2_external_sources.py",
    "scripts/__init__.py",
    "scripts/validate_code_red_release.py",
    "scripts/verify_distribution_boundary.py",
    "scripts/verify_external_field_receipts.py",
    "scripts/verify_installed_studio.py",
    "scripts/verify_release_metadata.py",
    "scripts/verify_studio_browser.mjs",
    *PUBLIC_V2_SPEC,
    *PUBLIC_PYTHON_MODULES,
    "tests/test_distribution_boundary.py",
    "tests/test_fetch_v2_external_sources.py",
    "tests/test_installed_studio_e2e.py",
    "tests/test_level1_assessment_v3.py",
    "tests/test_level1_target_v3.py",
    "tests/test_optimizer_protocol_v2.py",
    "tests/test_protocol_web_examples.py",
    "tests/test_protocol_capacity_v2.py",
    "tests/test_public_v2_distribution_boundary.py",
    "tests/test_public_repository_export.py",
    "tests/test_public_runtime_quarantine.py",
    "tests/test_public_v2_wheel_runtime.py",
    "tests/test_release_metadata_v2.py",
    "tests/test_studio_intake.py",
    "tests/test_studio_product.py",
    "tests/test_v2_design.py",
    "tests/test_v2_contract_semantics.py",
    "tests/test_v2_contracts.py",
    "tests/test_v2_information_run.py",
    "tests/test_v2_openapi_contract.py",
    "tests/test_v2_paper_protocol.py",
    "uv.lock",
    "web/favicon.svg",
    "web/optimizer-protocol-example.json",
    "web/protocol-capacity-example.json",
    "web/v2.css",
    "web/v2.html",
    "web/v2.js",
    "web/v2.test.js",
)

FORBIDDEN_PUBLIC_PREFIXES = (
    "data/source_projections/v2/ani-",
    "data/source_projections/v2/sources/",
    "data/source_projections/v2/suite_inputs/",
    "data/studies/",
    "figures/",
    "paper/build/",
    "registry/deep-scoring-lock/",
    "registry/formal-v1/studies/",
    "registry/score-input-evidence/",
    "release/",
    "reviews/",
    "tables/",
    "tasks/v1/",
    "tasks/v1.1/",
)

FORBIDDEN_PUBLIC_FRAGMENTS = (
    "/data/studies/ani-",
    "/schemas/v2/benchmark-suite-result.schema.json",
    "/schemas/v2/benchmark-suite-run.schema.json",
    "/schemas/v2/level1-reference-design.schema.json",
    "/schemas/v2/level1-reference-protocol-mapping-receipt.schema.json",
    "/src/anibench/level1_reference.py",
    "/src/anibench/level1_assessment_v2.py",
    "/src/anibench/level1_target_v2.py",
    "/src/anibench/level1_target_migration.py",
    "/src/anibench/protocol_authority_v2.py",
    "/src/anibench/simulation.py",
    "/src/anibench/suite_v2.py",
    "/src/anibench/trial_atlas_v2.py",
    "/spec/v2/level1/reference-design.json",
    "/spec/v2/level1/reference-protocol-mapping-receipt.json",
    "/spec/v2/level1/normative-target-requirements.v2.json",
    "/spec/v2/level1/reference-protocol-authority-facts.json",
    "/spec/v2/level1/reference-protocol-authority-resolution-receipt.json",
    "/scripts/derive_level1_reference.py",
    "/schemas/v2/optimizer-result.schema.json",
    "/schemas/v2/optimizer-run.schema.json",
    "/src/anibench/optimizer_v2.py",
    "/tests/test_v2_optimizer.py",
    "/web/app.js",
    "/web/app.test.js",
    "/web/index.html",
    "/web/public/data/leaderboard.json",
    "/patent/",
    "/private/",
    "/schemas/v1/",
    "/spec/v1/",
)

PUBLIC_SOURCE_ATLAS_PATHS = frozenset(
    {
        *PUBLIC_SOURCE_ATLAS_MEMBERS,
        "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv",
    }
)

EXCLUDED_NAMES = {
    ".DS_Store",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

GENERATED_PREFIXES = (
    "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv",
    "receipts/code-red-promotion-validation.json",
    "receipts/source-git.json",
)


def _excluded(path: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in path.parts) or path.suffix in EXCLUDED_SUFFIXES


def _copy_member(repo: Path, bundle: Path, relative: str) -> None:
    source = repo / relative
    if not source.exists():
        raise FileNotFoundError(f"Required release member is missing: {relative}")
    if source.is_symlink():
        raise ValueError(f"Symlinks are not valid release members: {relative}")
    destination = bundle / relative
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ValueError(
                    f"Symlinks are not valid release members: {path.relative_to(repo)}"
                )
            if _excluded(path.relative_to(repo)) or not path.is_file():
                continue
            target = bundle / path.relative_to(repo)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _write_public_source_atlas_table(repo: Path, bundle: Path) -> Path:
    """Materialize an external-only atlas table without redistributing ANI rows."""

    source = repo / "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv"
    if not source.is_file():
        raise FileNotFoundError(f"Required atlas coordinate table is missing: {source}")
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "study_id" not in reader.fieldnames:
            raise ValueError("Source atlas coordinate table has no study_id column")
        selected = [row for row in reader if row["study_id"] in EXTERNAL_SOURCE_ATLAS_STUDY_IDS]
        fieldnames = reader.fieldnames
    selected_ids = [row["study_id"] for row in selected]
    if selected_ids != list(EXTERNAL_SOURCE_ATLAS_STUDY_IDS):
        raise ValueError(
            "External atlas coordinate rows are missing, duplicated, or out of canonical order: "
            f"{selected_ids!r}"
        )
    public_source = repo / "packaging/public_v2/SOURCE_COORDINATE_TABLE.csv"
    with public_source.open(encoding="utf-8", newline="") as handle:
        public_reader = csv.DictReader(handle)
        public_rows = list(public_reader)
    if public_reader.fieldnames != fieldnames or public_rows != selected:
        raise ValueError(
            "Packaged external atlas coordinate table has drifted from the source-bound table"
        )
    destination = bundle / "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(public_source, destination)
    return destination


def _all_files(root: Path) -> list[str]:
    return [path.relative_to(root).as_posix() for path in sorted(root.rglob("*")) if path.is_file()]


def _public_boundary_violations(root: Path) -> list[str]:
    """Return copied paths that violate the explicit public-v2 boundary."""

    violations: list[str] = []
    for relative in _all_files(root):
        normalized = f"/{relative}"
        if any(relative.startswith(prefix) for prefix in FORBIDDEN_PUBLIC_PREFIXES):
            violations.append(relative)
            continue
        if any(fragment in normalized for fragment in FORBIDDEN_PUBLIC_FRAGMENTS):
            violations.append(relative)
            continue
        if (
            relative.startswith("data/source_projections/v2/")
            and relative not in PUBLIC_SOURCE_ATLAS_PATHS
        ):
            violations.append(relative)
    return sorted(set(violations))


def _code_red_binding(
    repo: Path,
    *,
    source_date_epoch: int,
    require_promotion: bool,
) -> dict[str, Any]:
    """Validate Code Red authority and return a hash-bound hold receipt."""

    result = validate_code_red_release(repo_root=repo)
    if result.get("validation_passed") is not True:
        raise SystemExit(
            "Code Red validator failed: "
            + json.dumps(result.get("promotion_blockers", []), sort_keys=True)
        )
    promotion_allowed = result.get("promotion_allowed") is True
    if require_promotion and not promotion_allowed:
        raise SystemExit("Code Red promotion authority is required but promotion_allowed=false")
    validator_path = repo / "scripts" / "validate_code_red_release.py"
    return {
        "contract": "anibench.code-red-hold-binding.v1",
        "source_date_epoch": source_date_epoch,
        "validator": {
            "path": "scripts/validate_code_red_release.py",
            "sha256": hashlib.sha256(validator_path.read_bytes()).hexdigest(),
        },
        "validation_passed": True,
        "promotion_allowed": promotion_allowed,
        "require_promotion": require_promotion,
        "validator_result": result,
    }


def _write_code_red_binding(bundle: Path, binding: Mapping[str, Any]) -> Path:
    path = bundle / "receipts" / "code-red-promotion-validation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(binding), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _git_source_receipt(repo: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=repo, text=True, stderr=subprocess.STDOUT
        ).strip()

    status = git("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "contract": "anibench.source-git-receipt.v1",
        "repository": git("config", "--get", "remote.origin.url"),
        "branch": git("branch", "--show-current"),
        "commit_sha": git("rev-parse", "HEAD"),
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "dirty": bool(status),
        "status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
    }


def _artifact_roles(root: Path) -> tuple[list[str], list[str]]:
    authored = []
    generated = []
    for relative in _all_files(root):
        if relative in {"release-receipt.json", "SHA256SUMS"}:
            continue
        target = (
            generated
            if any(
                relative == prefix or relative.startswith(prefix) for prefix in GENERATED_PREFIXES
            )
            else authored
        )
        target.append(relative)
    return authored, generated


def _set_mtimes(root: Path, epoch: int) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        os.utime(path, (epoch, epoch), follow_symlinks=False)
    os.utime(root, (epoch, epoch), follow_symlinks=False)


def _tar_filter(epoch: int):
    def normalize(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        info.mtime = epoch
        info.mode = 0o755 if info.isdir() else 0o644
        return info

    return normalize


def _archive(bundle: Path, archive: Path, epoch: int) -> str:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                tar.add(bundle, arcname=bundle.name, recursive=True, filter=_tar_filter(epoch))
    return hashlib.sha256(archive.read_bytes()).hexdigest()


def _extract_archive(archive_path: Path, destination: Path, expected_root: str) -> Path:
    """Extract a candidate only after rejecting traversal, links, devices, and archive bombs."""

    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        if not members or len(members) > 10_000:
            raise ValueError("Archive member count is invalid")
        if sum(max(0, member.size) for member in members) > 1_000_000_000:
            raise ValueError("Archive expands beyond the 1 GB review-candidate limit")
        for member in members:
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if not member_path.parts or member_path.parts[0] != expected_root:
                raise ValueError(f"Archive member is outside the expected root: {member.name}")
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"Archive links and devices are forbidden: {member.name}")
        if hasattr(tarfile, "fully_trusted_filter"):
            archive.extractall(destination, members=members, filter="fully_trusted")
        else:  # Python 3.10-3.11; every member was validated above.
            archive.extractall(destination, members=members)
    extracted = destination / expected_root
    if not extracted.is_dir():
        raise ValueError("Archive did not contain the expected bundle root")
    return extracted


def _verify_extracted_archive(archive: Path, bundle_name: str, temp_root: Path) -> Path:
    extracted = _extract_archive(archive, temp_root, bundle_name)
    replay = verify_release(extracted)
    if not replay.integrity_verified:
        raise ValueError(json.dumps(replay.as_dict(), indent=2, sort_keys=True))
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--version", default="2.0.0-rc.1")
    parser.add_argument("--source-date-epoch", type=int, required=True)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Development-only escape hatch; final review candidates must be commit-bound and clean",
    )
    parser.add_argument(
        "--require-promotion",
        action="store_true",
        help="Fail unless the bound Code Red authority permits promotion",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output_root.resolve()
    source_git = _git_source_receipt(repo)
    if source_git["dirty"] and not args.allow_dirty:
        raise SystemExit(
            "Refusing to assemble from a dirty worktree; commit the exact source first"
        )
    code_red = _code_red_binding(
        repo,
        source_date_epoch=args.source_date_epoch,
        require_promotion=args.require_promotion,
    )
    bundle_name = f"AniBench-{args.version}-public-v2-hold-candidate"
    bundle = output / bundle_name
    archive = output / f"{bundle_name}.tar.gz"
    receipt_path = output / f"{bundle_name}.archive-receipt.json"
    if bundle.exists():
        raise SystemExit(
            f"Refusing to replace existing review candidate; choose a fresh output root: {bundle}"
        )
    if archive.exists() or receipt_path.exists():
        raise SystemExit("Refusing to replace an existing archive or archive receipt")
    bundle.mkdir(parents=True)
    for member in PUBLIC_V2_ALLOWLIST:
        _copy_member(repo, bundle, member)
    _write_public_source_atlas_table(repo, bundle)
    _write_code_red_binding(bundle, code_red)
    source_git_path = bundle / "receipts" / "source-git.json"
    source_git_path.write_text(
        json.dumps(source_git, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    boundary_violations = _public_boundary_violations(bundle)
    if boundary_violations:
        raise SystemExit(
            "Public-v2 allowlist copied forbidden paths: " + ", ".join(boundary_violations[:20])
        )

    scan = scan_public_bundle(bundle, exclude_paths=("release-receipt.json", "SHA256SUMS"))
    if not scan.passed:
        summary = ", ".join(f"{finding.path}:{finding.rule_id}" for finding in scan.findings[:20])
        raise SystemExit(f"Public-boundary scan failed: {summary}")

    authored, generated = _artifact_roles(bundle)
    validation = {
        layer: {
            "name": name,
            "status": "not_run",
            "evidence": [],
            "blockers": [],
        }
        for layer, name in VALIDATION_LAYER_NAMES.items()
    }
    validation["V8"]["blockers"] = ["empirical_validation_not_run"]
    validation["V9"]["blockers"] = ["independent_audit_not_run"]
    validation["V10"] = {
        "name": VALIDATION_LAYER_NAMES["V10"],
        "status": "not_run",
        "evidence": [],
        "blockers": [],
    }
    receipt = build_release_receipt(
        bundle,
        benchmark_version=args.version,
        authored_paths=authored,
        generated_paths=generated,
        source_date_epoch=args.source_date_epoch,
        validation_layers=validation,
        scan_report=scan,
        scan_exclude_paths=("release-receipt.json", "SHA256SUMS"),
    )
    write_release_receipt(bundle / "release-receipt.json", receipt)
    generate_sha256sums(bundle)
    first = verify_release(bundle)
    if not first.integrity_verified:
        raise SystemExit(json.dumps(first.as_dict(), indent=2, sort_keys=True))

    _set_mtimes(bundle, args.source_date_epoch)
    with tempfile.TemporaryDirectory(prefix="anibench-release-preflight-") as temp_dir:
        temp = Path(temp_dir)
        preflight_archive = temp / f"{bundle_name}.tar.gz"
        _archive(bundle, preflight_archive, args.source_date_epoch)
        _verify_extracted_archive(preflight_archive, bundle_name, temp / "extract")

    receipt["validation_layers"]["V10"] = {
        "name": VALIDATION_LAYER_NAMES["V10"],
        "status": "passed",
        "evidence": [
            "preflight_archive_extract_receipt_and_sha256_replay",
            "final_archive_extract_and_deterministic_rearchive_match",
        ],
        "blockers": [],
    }
    receipt = refresh_release_receipt_id(receipt)
    write_release_receipt(bundle / "release-receipt.json", receipt)
    generate_sha256sums(bundle)
    final = verify_release(bundle)
    if not final.integrity_verified:
        raise SystemExit(json.dumps(final.as_dict(), indent=2, sort_keys=True))

    try:
        _set_mtimes(bundle, args.source_date_epoch)
        archive_sha256 = _archive(bundle, archive, args.source_date_epoch)
        with tempfile.TemporaryDirectory(prefix="anibench-release-final-") as temp_dir:
            temp = Path(temp_dir)
            extracted = _verify_extracted_archive(archive, bundle_name, temp / "extract")
            replay_archive = temp / "replay.tar.gz"
            replay_sha256 = _archive(extracted, replay_archive, args.source_date_epoch)
            if replay_sha256 != archive_sha256:
                raise ValueError("Deterministic archive replay SHA-256 mismatch")
            # This deterministic hold-candidate archive is a reviewed repository
            # bundle, not the Hatch sdist. Apply every structural and byte scan,
            # but reserve the exact Hatch member-set contract for wheel/sdist
            # artifacts built from pyproject.toml.
            distribution_boundary = inspect_distribution(archive, enforce_exact=False)
            if not distribution_boundary["passed"]:
                raise ValueError(
                    "Distribution boundary failed: "
                    + json.dumps(distribution_boundary["findings"][:20], sort_keys=True)
                )
    except Exception as exc:
        archive.unlink(missing_ok=True)
        receipt["validation_layers"]["V10"] = {
            "name": VALIDATION_LAYER_NAMES["V10"],
            "status": "not_run",
            "evidence": ["preflight_archive_extract_receipt_and_sha256_replay"],
            "blockers": ["final archive extraction or deterministic replay failed"],
        }
        receipt = refresh_release_receipt_id(receipt)
        write_release_receipt(bundle / "release-receipt.json", receipt)
        generate_sha256sums(bundle)
        raise SystemExit(f"Final archive replay failed: {exc}") from exc
    archive_receipt = {
        "contract": "anibench.public-v2-hold-candidate-archive.v1",
        "archive": archive.name,
        "archive_sha256": archive_sha256,
        "archive_bytes": archive.stat().st_size,
        "archive_extract_verified": True,
        "deterministic_rearchive_verified": True,
        "replay_archive_sha256": replay_sha256,
        "bundle": bundle.name,
        "bundle_file_count": len(_all_files(bundle)),
        "release_receipt_id": receipt["release_receipt_id"],
        "code_red_binding_sha256": hashlib.sha256(
            (bundle / "receipts" / "code-red-promotion-validation.json").read_bytes()
        ).hexdigest(),
        "code_red_validation_passed": code_red["validation_passed"],
        "promotion_allowed": code_red["promotion_allowed"],
        "distribution_boundary_verified": distribution_boundary["passed"],
        "validation_complete": final.validation_complete,
        "published": False,
        "source_git": source_git,
    }
    receipt_path.write_text(
        json.dumps(archive_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(archive_receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
