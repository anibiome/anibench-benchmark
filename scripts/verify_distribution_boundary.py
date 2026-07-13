#!/usr/bin/env python3
"""Fail-closed member, structure, and content verification for public distributions."""

from __future__ import annotations

import argparse
import fnmatch
import json
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

from anibench.release.redact import scan_public_bundle


ROOT = Path(__file__).resolve().parents[1]
MAX_MEMBER_BYTES = 100_000_000
MAX_ARCHIVE_BYTES = 500_000_000
PUBLIC_REPOSITORY_ALLOWLIST = Path("packaging/public_v2/REPOSITORY_ALLOWLIST.txt")

FORBIDDEN_FRAGMENTS = (
    "data/studies/",
    "data/source_projections/v2/ani-",
    "data/source_projections/v2/sources/",
    "data/source_projections/v2/suite_inputs/",
    "data/source_projections/v2/SOURCE_PROJECTION_LEDGER.json",
    "registry/score-input-evidence/",
    "registry/deep-scoring-lock/",
    "registry/formal-v1/studies/",
    "release/preview-atlas",
    "release/review/",
    "release/code-red/",
    "release/candidates/",
    "release/v8_",
    "reviews/",
    "figures/",
    "tables/",
    "paper/build/",
    "patent/",
    "private/",
    "schemas/v1/",
    "schemas/v2/optimizer-result.schema.json",
    "schemas/v2/optimizer-run.schema.json",
    "schemas/v2/benchmark-suite-result.schema.json",
    "schemas/v2/benchmark-suite-run.schema.json",
    "schemas/v2/level1-reference-design.schema.json",
    "schemas/v2/level1-reference-protocol-mapping-receipt.schema.json",
    "spec/v1/",
    "tasks/v1/",
    "tasks/v1.1/",
    "anibench/level1_reference.py",
    "anibench/level1_assessment_v2.py",
    "anibench/level1_target_v2.py",
    "anibench/level1_target_migration.py",
    "anibench/protocol_authority_v2.py",
    "anibench/simulation.py",
    "anibench/suite_v2.py",
    "anibench/trial_atlas_v2.py",
    "spec/v2/level1/reference-design.json",
    "spec/v2/level1/reference-protocol-mapping-receipt.json",
    "spec/v2/level1/normative-target-requirements.v2.json",
    "spec/v2/level1/reference-protocol-authority-facts.json",
    "spec/v2/level1/reference-protocol-authority-resolution-receipt.json",
    "scripts/derive_level1_reference.py",
    "anibench/build.py",
    "anibench/contracts/models.py",
    "anibench/contracts/validation.py",
    "anibench/demonstrated.py",
    "anibench/evidence/",
    "anibench/manifest.py",
    "src/anibench/optimizer_v2.py",
    "anibench/optimizer_v2.py",
    "anibench/preview_figures.py",
    "anibench/ranking_v2.py",
    "anibench/reporting.py",
    "anibench/scenario.py",
    "anibench/scoring.py",
    "anibench/specification/",
    "anibench/tasks/",
    "anibench/validation/",
    "anibench/release/external_validation.py",
    "anibench/release/receipt.py",
    "anibench/release/validation_run.py",
    "anibench/release/verify.py",
    "tests/test_v2_optimizer.py",
    "web/app.js",
    "web/app.test.js",
    "web/index.html",
    "web/public/data/leaderboard.json",
)

ALLOWED_SOURCE_ATLAS_FILENAMES = frozenset(
    {
        "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
        "EXTERNAL_SOURCE_ACQUISITION_LEDGER.json",
        "EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json",
        "SOURCE_COORDINATE_TABLE.csv",
        "all-of-us-cdrv9.json",
        "aspree.json",
        "calerie-phase-2-expanded.json",
        "circulate-tpe-ivig.json",
        "do-health-bio-age.json",
        "dq-senolytic-bone.json",
        "life-study.json",
        "mitoimmune-urolithin-a.json",
        "motrpac-human-pre-suspension-expanded.json",
        "pearl-rapamycin.json",
        "predict-1.json",
        "sheba-sharp.json",
        "snyder-ipop-ihmp-106.json",
        "triim.json",
        "uk-biobank.json",
        "zoe-method.json",
    }
)

ALLOWED_WEB_FILENAMES = frozenset(
    {
        "favicon.svg",
        "optimizer-protocol-example.json",
        "protocol-capacity-example.json",
        "v2.css",
        "v2.html",
        "v2.js",
        "v2.test.js",
    }
)

NESTED_CONTAINER_SUFFIXES = (
    ".7z",
    ".gz",
    ".tar",
    ".tar.bz2",
    ".tar.gz",
    ".tar.xz",
    ".tgz",
    ".whl",
    ".zip",
    ".zst",
)


def _safe_name(name: str) -> bool:
    if not name or "\\" in name or "\x00" in name or name.startswith("./"):
        return False
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and "." not in path.parts
        and path.as_posix() == name
        and "//" not in name
    )


def forbidden_fragment_applies(normalized_path: str, fragment: str) -> bool:
    if fragment == "figures/" and "/paper/v2/figures/" in f"/{normalized_path}":
        return False
    return fragment in normalized_path


def _load_project(authority_root: Path) -> dict[str, Any]:
    return tomllib.loads((authority_root / "pyproject.toml").read_text(encoding="utf-8"))


def _distribution_identity(authority_root: Path) -> tuple[str, str, str]:
    project = _load_project(authority_root)["project"]
    name = str(project["name"]).replace("-", "_")
    version = str(project["version"])
    sdist_root = f"{str(project['name']).replace('_', '-')}-{version}"
    return name, version, sdist_root


def _repository_allowlist(authority_root: Path) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in (authority_root / PUBLIC_REPOSITORY_ALLOWLIST)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _is_hatch_excluded(relative: str, patterns: list[str]) -> bool:
    for raw in patterns:
        pattern = raw.lstrip("/").rstrip("/")
        if any(character in pattern for character in "*?["):
            if fnmatch.fnmatch(relative, pattern):
                return True
        elif relative == pattern or relative.startswith(pattern + "/"):
            return True
    return False


def _expand_sdist_include(authority_root: Path, relative: str) -> set[str]:
    path = authority_root / relative
    if not path.exists() or path.is_symlink():
        raise ValueError(f"sdist include is missing or unsafe: {relative}")
    if path.is_file():
        return {relative}
    members = set()
    for candidate in path.rglob("*"):
        if candidate.is_symlink():
            raise ValueError(f"symlink inside sdist include: {candidate}")
        if candidate.is_file() and "__pycache__" not in candidate.parts:
            members.add(candidate.relative_to(authority_root).as_posix())
    return members


def expected_distribution_members(
    *,
    authority_root: Path = ROOT,
    kind: str,
) -> frozenset[str]:
    authority_root = authority_root.resolve()
    configuration = _load_project(authority_root)
    name, version, sdist_root = _distribution_identity(authority_root)
    build = configuration["tool"]["hatch"]["build"]
    excludes = [str(value) for value in build.get("exclude", [])]
    if kind == "wheel":
        expected = {
            relative.removeprefix("src/")
            for relative in _repository_allowlist(authority_root)
            if relative.startswith("src/anibench/")
        }
        force_include = build["targets"]["wheel"]["force-include"]
        expected.update(str(destination) for destination in force_include.values())
        dist_info = f"{name}-{version}.dist-info"
        expected.update(
            {
                f"{dist_info}/METADATA",
                f"{dist_info}/RECORD",
                f"{dist_info}/WHEEL",
                f"{dist_info}/entry_points.txt",
                f"{dist_info}/licenses/LICENSE",
                f"{dist_info}/licenses/LICENSE-DATA",
            }
        )
        return frozenset(expected)
    if kind != "sdist":
        raise ValueError(f"unsupported expected member kind: {kind}")
    relative_members: set[str] = set()
    for raw in build["targets"]["sdist"]["include"]:
        relative_members.update(_expand_sdist_include(authority_root, str(raw).lstrip("/")))
    # Hatch includes .gitignore as reproducible source-build metadata.
    if (authority_root / ".gitignore").is_file():
        relative_members.add(".gitignore")
    relative_members = {
        relative
        for relative in relative_members
        if not _is_hatch_excluded(relative, excludes)
    }
    relative_members.add("PKG-INFO")
    return frozenset(f"{sdist_root}/{relative}" for relative in relative_members)


def _nested_container(body: bytes, name: str) -> bool:
    lower = name.lower()
    if lower.endswith(NESTED_CONTAINER_SUFFIXES):
        return True
    if body.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return True
    if body.startswith((b"\x1f\x8b", b"7z\xbc\xaf\x27\x1c", b"\x28\xb5\x2f\xfd")):
        return True
    return len(body) >= 262 and body[257:262] == b"ustar"


def _member_findings(name: str, size: int) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not _safe_name(name):
        findings.append({"path": name, "rule_id": "unsafe_archive_path"})
        return findings
    if size > MAX_MEMBER_BYTES:
        findings.append({"path": name, "rule_id": "member_over_100mb"})
    for fragment in FORBIDDEN_FRAGMENTS:
        if forbidden_fragment_applies(name, fragment):
            findings.append({"path": name, "rule_id": f"forbidden:{fragment}"})
    atlas_marker = "data/source_projections/v2/"
    if atlas_marker in name:
        atlas_member = name.split(atlas_marker, 1)[1]
        if atlas_member not in ALLOWED_SOURCE_ATLAS_FILENAMES:
            findings.append({"path": name, "rule_id": "unexpected_source_atlas_member"})
    web_marker = "web/"
    if web_marker in name:
        web_member = name.rsplit(web_marker, 1)[1]
        if web_member not in ALLOWED_WEB_FILENAMES:
            findings.append({"path": name, "rule_id": "unexpected_web_member"})
    return findings


def _record_member(
    *,
    name: str,
    body: bytes,
    declared_size: int,
    unpacked: Path,
    seen: set[str],
    findings: list[dict[str, str]],
) -> None:
    if name in seen:
        findings.append({"path": name, "rule_id": "duplicate_archive_member"})
        return
    seen.add(name)
    findings.extend(_member_findings(name, declared_size))
    if len(body) != declared_size:
        findings.append({"path": name, "rule_id": "archive_member_size_mismatch"})
    if _nested_container(body, name):
        findings.append({"path": name, "rule_id": "nested_archive_forbidden"})
    if (
        not _safe_name(name)
        or declared_size > MAX_MEMBER_BYTES
        or len(body) > MAX_MEMBER_BYTES
        or len(body) != declared_size
    ):
        return
    destination = unpacked / PurePosixPath(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(body)


def inspect_distribution(
    path: Path,
    *,
    authority_root: Path = ROOT,
    enforce_exact: bool = True,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    seen: set[str] = set()
    total_bytes = 0
    kind: str
    with tempfile.TemporaryDirectory(prefix="anibench-dist-scan-") as temporary:
        unpacked = Path(temporary)
        if path.suffix == ".whl":
            kind = "wheel"
            with zipfile.ZipFile(path) as archive:
                for row in archive.infolist():
                    name = row.filename
                    if row.flag_bits & 0x1:
                        findings.append({"path": name, "rule_id": "encrypted_member_forbidden"})
                        continue
                    unix_type = stat.S_IFMT(row.external_attr >> 16)
                    if row.is_dir():
                        directory_name = name.rstrip("/")
                        if directory_name and not _safe_name(directory_name):
                            findings.append({"path": name, "rule_id": "unsafe_archive_path"})
                        continue
                    if unix_type == stat.S_IFLNK:
                        findings.append({"path": name, "rule_id": "archive_link_or_directory_forbidden"})
                        continue
                    if unix_type not in {0, stat.S_IFREG}:
                        findings.append({"path": name, "rule_id": "archive_non_regular_forbidden"})
                        continue
                    if row.file_size > MAX_MEMBER_BYTES:
                        body = b""
                    else:
                        with archive.open(row) as handle:
                            body = handle.read(MAX_MEMBER_BYTES + 1)
                    total_bytes += row.file_size
                    _record_member(
                        name=name,
                        body=body,
                        declared_size=row.file_size,
                        unpacked=unpacked,
                        seen=seen,
                        findings=findings,
                    )
        elif path.name.endswith(".tar.gz"):
            kind = "sdist"
            with tarfile.open(path, "r:gz") as archive:
                for row in archive.getmembers():
                    name = row.name
                    if row.isdir():
                        if not _safe_name(name):
                            findings.append({"path": name, "rule_id": "unsafe_archive_path"})
                        continue
                    if not row.isfile() or row.issym() or row.islnk() or row.issparse():
                        findings.append({"path": name, "rule_id": "archive_non_regular_forbidden"})
                        continue
                    if row.size > MAX_MEMBER_BYTES:
                        body = b""
                    else:
                        handle = archive.extractfile(row)
                        if handle is None:
                            findings.append({"path": name, "rule_id": "archive_member_unreadable"})
                            continue
                        body = handle.read(MAX_MEMBER_BYTES + 1)
                    total_bytes += row.size
                    _record_member(
                        name=name,
                        body=body,
                        declared_size=row.size,
                        unpacked=unpacked,
                        seen=seen,
                        findings=findings,
                    )
        else:
            raise ValueError(f"unsupported distribution: {path}")

        if total_bytes > MAX_ARCHIVE_BYTES:
            findings.append({"path": str(path), "rule_id": "archive_unpacked_size_over_500mb"})

        if enforce_exact:
            expected = expected_distribution_members(authority_root=authority_root, kind=kind)
            for name in sorted(seen - expected):
                findings.append({"path": name, "rule_id": "unallowlisted_distribution_member"})
            for name in sorted(expected - seen):
                findings.append({"path": name, "rule_id": "required_distribution_member_missing"})

        scan = scan_public_bundle(unpacked)
        findings.extend(
            {"path": finding.path, "rule_id": f"public_scan:{finding.rule_id}"}
            for finding in scan.findings
        )

    deduplicated = sorted(
        {json.dumps(row, sort_keys=True): row for row in findings}.values(),
        key=lambda row: (row["path"], row["rule_id"]),
    )
    return {
        "contract": "anibench.distribution-boundary.v2",
        "path": str(path),
        "distribution_kind": kind,
        "exact_member_set_enforced": enforce_exact,
        "member_count": len(seen),
        "unpacked_bytes": total_bytes,
        "public_scan_files": scan.files_scanned,
        "public_scan_bytes": scan.bytes_scanned,
        "findings": deduplicated,
        "passed": not deduplicated,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distributions", type=Path, nargs="+")
    parser.add_argument("--authority-root", type=Path, default=ROOT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    reports = [
        inspect_distribution(path, authority_root=args.authority_root, enforce_exact=True)
        for path in args.distributions
    ]
    print(json.dumps(reports, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if all(report["passed"] for report in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
