#!/usr/bin/env python3
"""Create and verify an AniBench public repository with one clean history root.

The private authority repository intentionally retains controlled ANI projections,
source-locator receipts, council material, and superseded development artifacts.
Those bytes must never become part of a public Git object database.  This exporter
therefore copies an explicit allowlist into a new directory, scans the copied
contents, and can initialize a new repository with exactly one root commit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised in the Python 3.10 CI lane
    import tomli as tomllib

from anibench.release.redact import scan_public_bundle


PUBLIC_EXPORT_RECEIPT = "PUBLIC_EXPORT_RECEIPT.json"
PUBLIC_ALLOWLIST_PATH = "packaging/public_v2/REPOSITORY_ALLOWLIST.txt"
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
CONTROLLED_VALUE_MARKERS = (
    "/Users/",
    "controlled-source://",
    "evidence_class\": \"private_protocol",
)
FORBIDDEN_PUBLIC_PREFIXES = (
    "data/source_projections/v2/ani-",
    "data/source_projections/v2/sources/",
    "data/source_projections/v2/suite_inputs/",
    "data/studies/",
    "figures/",
    "paper/build/",
    "patent/",
    "private/",
    "registry/",
    "release/",
    "reviews/",
    "tables/",
    "tasks/v1/",
    "tasks/v1.1/",
)
EXCLUDED_NAMES = {".DS_Store", ".pytest_cache", ".ruff_cache", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _validate_public_member_path(member: str) -> Path:
    path_value = Path(member)
    if (
        not member
        or "\\" in member
        or "\x00" in member
        or member.startswith("./")
        or "//" in member
        or path_value.is_absolute()
        or ".." in path_value.parts
        or path_value.as_posix() != member
        or member == ".git"
        or member.startswith(".git/")
    ):
        raise ValueError(f"Unsafe public allowlist member: {member!r}")
    return path_value


def _parse_public_allowlist(raw: str) -> tuple[str, ...]:
    members = tuple(
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if list(members) != sorted(members):
        raise ValueError("Public repository allowlist must be sorted")
    if len(members) != len(set(members)):
        raise ValueError("Public repository allowlist contains duplicates")
    if PUBLIC_ALLOWLIST_PATH not in members:
        raise ValueError("Public repository allowlist must include itself")
    for member in members:
        _validate_public_member_path(member)
    return members


def _load_public_allowlist(root: Path) -> tuple[str, ...]:
    return _parse_public_allowlist(
        (root / PUBLIC_ALLOWLIST_PATH).read_text(encoding="utf-8")
    )


def _excluded(path: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in path.parts) or path.suffix in EXCLUDED_SUFFIXES


def _copy_member(repo: Path, output: Path, relative: str) -> None:
    _validate_public_member_path(relative)
    source = repo / relative
    if not source.exists():
        raise FileNotFoundError(f"Required public member is missing: {relative}")
    if source.is_symlink():
        raise ValueError(f"Symlinks are not valid public members: {relative}")
    if not source.is_file():
        raise ValueError(f"Public allowlist members must name exact regular files: {relative}")
    if _excluded(source.relative_to(repo)):
        raise ValueError(f"Excluded build residue cannot be a public member: {relative}")
    destination = output / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo,
        stderr=subprocess.STDOUT,
    )


def _git_blob(repo: Path, commit_sha: str, relative: str) -> bytes:
    return _git_bytes(repo, "cat-file", "blob", f"{commit_sha}:{relative}")


def _git_member_entries(
    repo: Path,
    commit_sha: str,
    relative: str,
) -> tuple[tuple[str, str, str], ...]:
    """Return (mode, object-id, path) rows pinned to one immutable commit."""

    _validate_public_member_path(relative)
    raw = _git_bytes(repo, "ls-tree", "-r", "-z", commit_sha, "--", relative)
    rows: list[tuple[str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, encoded_path = record.split(b"\t", 1)
        mode, kind, object_id = header.decode("ascii").split(" ")
        path = encoded_path.decode("utf-8", errors="strict")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"Non-regular Git object is not a public member: {path} ({mode} {kind})")
        rows.append((mode, object_id, path))
    if not rows:
        raise FileNotFoundError(
            f"Required public member is absent from source commit {commit_sha}: {relative}"
        )
    if len(rows) != 1 or rows[0][2] != relative:
        raise ValueError(
            "Public allowlist members must bind exactly one regular Git blob: "
            f"{relative!r} resolved to {[row[2] for row in rows]!r}"
        )
    return tuple(rows)


def _copy_member_from_commit(
    repo: Path,
    output: Path,
    *,
    commit_sha: str,
    relative: str,
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for mode, object_id, path in _git_member_entries(repo, commit_sha, relative):
        path_value = Path(path)
        if _excluded(path_value):
            continue
        body = _git_bytes(repo, "cat-file", "blob", object_id)
        destination = output / path_value
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)
        destination.chmod(0o755 if mode == "100755" else 0o644)
        copied.append(
            {
                "path": path,
                "git_blob_sha": object_id,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
        )
    return copied


def _write_public_source_atlas_table_bytes(
    *,
    source_body: bytes,
    packaged_body: bytes,
    output: Path,
) -> Path:
    with io.StringIO(source_body.decode("utf-8"), newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "study_id" not in reader.fieldnames:
            raise ValueError("Source atlas coordinate table has no study_id column")
        selected = [row for row in reader if row["study_id"] in EXTERNAL_SOURCE_ATLAS_STUDY_IDS]
        fieldnames = reader.fieldnames
    if [row["study_id"] for row in selected] != list(EXTERNAL_SOURCE_ATLAS_STUDY_IDS):
        raise ValueError("External atlas rows are missing, duplicated, or out of order")
    with io.StringIO(packaged_body.decode("utf-8"), newline="") as handle:
        packaged_reader = csv.DictReader(handle)
        packaged_rows = list(packaged_reader)
    if packaged_reader.fieldnames != fieldnames or packaged_rows != selected:
        raise ValueError("Packaged external atlas table has drifted from source-bound rows")
    destination = output / "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(packaged_body)
    return destination


def _write_public_source_atlas_table(repo: Path, output: Path) -> Path:
    source = repo / "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv"
    packaged = repo / "packaging/public_v2/SOURCE_COORDINATE_TABLE.csv"
    return _write_public_source_atlas_table_bytes(
        source_body=source.read_bytes(),
        packaged_body=packaged.read_bytes(),
        output=output,
    )


def _public_boundary_violations(root: Path) -> list[str]:
    violations = []
    allowed_atlas = {
        "EXTERNAL_SOURCE_ACQUISITION_LEDGER.json",
        "SOURCE_COORDINATE_TABLE.csv",
        *(f"{study_id}.json" for study_id in EXTERNAL_SOURCE_ATLAS_STUDY_IDS),
    }
    for path in _files(root):
        relative = path.relative_to(root).as_posix()
        if any(relative.startswith(prefix) for prefix in FORBIDDEN_PUBLIC_PREFIXES):
            violations.append(relative)
            continue
        marker = "data/source_projections/v2/"
        if relative.startswith(marker) and relative.removeprefix(marker) not in allowed_atlas:
            violations.append(relative)
    return sorted(set(violations))


def _git(repo: Path, *args: str, env: Mapping[str, str] | None = None) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo,
        env=None if env is None else dict(env),
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()


def _source_git_state(repo: Path) -> dict[str, Any]:
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "commit_sha": _git(repo, "rev-parse", "HEAD"),
        "tree_sha": _git(repo, "rev-parse", "HEAD^{tree}"),
        "dirty": bool(status),
        "status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
    }


def _assert_source_git_state_unchanged(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    if dict(before) != dict(after):
        raise ValueError(
            "Authority Git state changed during export; refusing a TOCTOU-ambiguous result"
        )


def _source_manifest_sha256(rows: Iterable[Mapping[str, Any]]) -> str:
    normalized = [dict(row) for row in rows]
    normalized.sort(key=lambda row: str(row["path"]))
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _files(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*")) if path.is_file()]


def _audited_relative_files(root: Path) -> set[str]:
    """Return files capable of entering the public commit.

    Before Git initialization every byte is audited. After initialization the
    audit covers tracked files plus unignored untracked files, while ordinary
    ignored build/cache residue cannot make the scanner fail merely by importing
    the scanner itself.
    """

    if not (root / ".git").is_dir():
        return {path.relative_to(root).as_posix() for path in _files(root)}
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
    )
    return {
        value.decode("utf-8")
        for value in output.split(b"\0")
        if value and (root / value.decode("utf-8")).is_file()
    }


def _tree_sha256(root: Path, *, exclude: Iterable[str] = ()) -> str:
    excluded = set(exclude)
    digest = hashlib.sha256()
    for path in _files(root):
        relative = path.relative_to(root).as_posix()
        if relative in excluded or relative.startswith(".git/"):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\n")
    return digest.hexdigest()


def _copied_file_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        for path in _files(root)
        if not path.relative_to(root).as_posix().startswith(".git/")
    ]


def _walk(value: Any, pointer: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_pointer = f"{pointer}/{key}"
            yield child_pointer, child
            yield from _walk(child, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            yield child_pointer, child
            yield from _walk(child, child_pointer)


def _structured_source_findings(root: Path) -> list[dict[str, str]]:
    """Reject controlled ANI provenance from the copied source-atlas objects."""

    findings: list[dict[str, str]] = []
    atlas = root / "data" / "source_projections" / "v2"
    expected_json = {
        "EXTERNAL_SOURCE_ACQUISITION_LEDGER.json",
        *(f"{study_id}.json" for study_id in EXTERNAL_SOURCE_ATLAS_STUDY_IDS),
    }
    actual_json = {path.name for path in atlas.glob("*.json")}
    for name in sorted(actual_json - expected_json):
        findings.append({"path": f"data/source_projections/v2/{name}", "rule_id": "unexpected_projection"})
    for name in sorted(expected_json - actual_json):
        findings.append({"path": f"data/source_projections/v2/{name}", "rule_id": "missing_projection"})

    for path in sorted(atlas.glob("*.json")):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for marker in CONTROLLED_VALUE_MARKERS:
            if marker in text:
                findings.append({"path": relative, "rule_id": "controlled_source_marker"})
        payload = json.loads(text)
        for pointer, value in _walk(payload):
            if isinstance(value, str) and value.startswith("ani-"):
                findings.append({"path": relative, "rule_id": "internal_ani_study_id"})
            if pointer.endswith("/path") and isinstance(value, str):
                if value.startswith(("/", "~", "file://")):
                    findings.append({"path": relative, "rule_id": "absolute_source_path"})

    table = atlas / "SOURCE_COORDINATE_TABLE.csv"
    if table.is_file():
        with table.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        ids = [row.get("study_id", "") for row in rows]
        if ids != list(EXTERNAL_SOURCE_ATLAS_STUDY_IDS):
            findings.append(
                {
                    "path": table.relative_to(root).as_posix(),
                    "rule_id": "external_atlas_identity_or_order_mismatch",
                }
            )
    return findings


def inspect_public_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    boundary = _public_boundary_violations(root)
    all_relative = {path.relative_to(root).as_posix() for path in _files(root)}
    audited = _audited_relative_files(root)
    excluded_members = tuple(sorted(all_relative - audited))
    scan = scan_public_bundle(
        root,
        # The export receipt is excluded only from its self-referential tree
        # digest, not from the privacy/security scan. Before the receipt is
        # written this path is simply absent; after writing, every receipt byte
        # is audited like every other public member.
        exclude_paths=tuple(excluded_members),
    )
    structured = _structured_source_findings(root)
    findings: list[dict[str, str]] = [
        {"path": path, "rule_id": "forbidden_public_path"} for path in boundary
    ]
    findings.extend(
        {"path": finding.path, "rule_id": finding.rule_id} for finding in scan.findings
    )
    findings.extend(structured)
    expected = {
        *_load_public_allowlist(root),
        "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv",
        PUBLIC_EXPORT_RECEIPT,
    }
    actual = audited
    for path in sorted(actual - expected):
        findings.append({"path": path, "rule_id": "unallowlisted_public_member"})
    for path in sorted(expected - actual - {PUBLIC_EXPORT_RECEIPT}):
        findings.append({"path": path, "rule_id": "required_public_member_missing"})
    return {
        "contract": "anibench.public-repository-scan.v1",
        "files_scanned": scan.files_scanned,
        "bytes_scanned": scan.bytes_scanned,
        "findings": sorted(findings, key=lambda row: (row["path"], row["rule_id"])),
        "passed": not findings,
    }


def _write_public_receipt(
    root: Path,
    *,
    version: str,
    epoch: int,
    source_git: Mapping[str, Any],
    source_copy_mode: str,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    source_clean = not bool(source_git["dirty"])
    commit_bound = source_copy_mode == "exact_git_objects_from_pinned_commit"
    receipt = {
        "contract": "anibench.public-repository-export.v1",
        "benchmark_version": version,
        "source_date_epoch": epoch,
        "history_contract": "fresh_repository_exactly_one_root_commit",
        "private_authority_history_included": False,
        "private_ani_projection_objects_included": False,
        "controlled_source_bodies_included": False,
        "public_rank_claim_allowed": False,
        "source_authority_git": {
            "commit_sha": source_git["commit_sha"],
            "tree_sha": source_git["tree_sha"],
            "clean": source_clean,
            "status_sha256": source_git["status_sha256"],
        },
        "source_copy_mode": source_copy_mode,
        "source_object_manifest_sha256": source_manifest_sha256,
        "source_commit_bound": commit_bound,
        "toctou_guard": "pre_and_post_git_state_equal",
        "release_source_eligible": source_clean and commit_bound,
        "public_member_count": len(_files(root)) + 1,
        "public_tree_sha256": _tree_sha256(root, exclude=(PUBLIC_EXPORT_RECEIPT,)),
        "public_tree_hash_scope": "all_public_members_except_this_receipt",
        "scan_contract": "anibench.public-repository-scan.v1",
    }
    path = root / PUBLIC_EXPORT_RECEIPT
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _initialize_fresh_history(root: Path, *, epoch: int) -> dict[str, Any]:
    _git(root, "init", "-b", "main")
    _git(root, "add", "--all")
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "ANI Release Engineering",
            "GIT_AUTHOR_EMAIL": "release@anibench.org",
            "GIT_COMMITTER_NAME": "ANI Release Engineering",
            "GIT_COMMITTER_EMAIL": "release@anibench.org",
            "GIT_AUTHOR_DATE": f"{epoch} +0000",
            "GIT_COMMITTER_DATE": f"{epoch} +0000",
        }
    )
    _git(root, "commit", "-m", "Open-source AniBench v2 release candidate", env=env)
    commit_count = int(_git(root, "rev-list", "--all", "--count"))
    root_count = len(_git(root, "rev-list", "--max-parents=0", "--all").splitlines())
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    remotes = _git(root, "remote")
    if commit_count != 1 or root_count != 1 or status or remotes:
        raise ValueError(
            "Fresh-history verification failed: "
            f"{commit_count=}, {root_count=}, dirty={bool(status)}, remotes={remotes!r}"
        )
    return {
        "initialized": True,
        "branch": _git(root, "branch", "--show-current"),
        "commit_sha": _git(root, "rev-parse", "HEAD"),
        "tree_sha": _git(root, "rev-parse", "HEAD^{tree}"),
        "commit_count": commit_count,
        "root_commit_count": root_count,
        "clean": True,
        "remote_count": 0,
    }


def _materialize_commit_tree(repo: Path, commit_sha: str, output: Path) -> int:
    raw = _git_bytes(repo, "ls-tree", "-r", "-z", commit_sha)
    count = 0
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, encoded_path = record.split(b"\t", 1)
        mode, kind, object_id = header.decode("ascii").split(" ")
        relative = encoded_path.decode("utf-8", errors="strict")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative:
            raise ValueError(f"Unsafe path in reachable Git tree {commit_sha}: {relative!r}")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(
                f"Non-regular reachable Git object {commit_sha}:{relative} ({mode} {kind})"
            )
        body = _git_bytes(repo, "cat-file", "blob", object_id)
        if len(body) > 100_000_000:
            raise ValueError(f"Reachable Git blob exceeds 100 MB: {commit_sha}:{relative}")
        destination = output / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)
        destination.chmod(0o755 if mode == "100755" else 0o644)
        count += 1
    return count


def inspect_public_git_history(repo: Path) -> dict[str, Any]:
    """Replay the public boundary against every tree reachable from every ref."""

    repo = repo.resolve()
    commits = tuple(line for line in _git(repo, "rev-list", "--all").splitlines() if line)
    roots = tuple(
        line
        for line in _git(repo, "rev-list", "--max-parents=0", "--all").splitlines()
        if line
    )
    findings: list[dict[str, Any]] = []
    if len(roots) != 1:
        findings.append(
            {
                "commit": "",
                "path": ".git",
                "rule_id": "reachable_history_must_have_exactly_one_root",
                "observed": len(roots),
            }
        )
    scanned_files = 0
    with tempfile.TemporaryDirectory(prefix="anibench-git-history-") as temporary:
        workspace = Path(temporary)
        for index, commit_sha in enumerate(commits):
            tree = workspace / f"tree-{index:06d}"
            tree.mkdir()
            try:
                scanned_files += _materialize_commit_tree(repo, commit_sha, tree)
                report = inspect_public_repository(tree)
            except Exception as exc:
                findings.append(
                    {
                        "commit": commit_sha,
                        "path": ".git",
                        "rule_id": "reachable_tree_scan_error",
                        "detail": str(exc),
                    }
                )
            else:
                findings.extend(
                    {"commit": commit_sha, **finding}
                    for finding in report["findings"]
                )
            finally:
                shutil.rmtree(tree, ignore_errors=True)
    return {
        "contract": "anibench.public-git-history-scan.v1",
        "commit_count": len(commits),
        "root_commit_count": len(roots),
        "reachable_tree_files_scanned": scanned_files,
        "findings": findings,
        "passed": bool(commits) and not findings,
    }


def export_public_repository(
    repo: Path,
    output: Path,
    *,
    source_date_epoch: int,
    initialize_git: bool,
    allow_dirty: bool,
) -> dict[str, Any]:
    repo = repo.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to replace existing output: {output}")
    try:
        output.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ValueError("Public export must be outside the authority repository")

    source_git = _source_git_state(repo)
    if source_git["dirty"] and not allow_dirty:
        raise ValueError("Refusing to export from a dirty authority worktree")
    commit_bound = not source_git["dirty"]
    if commit_bound:
        pyproject_body = _git_blob(repo, source_git["commit_sha"], "pyproject.toml")
        allowlist_body = _git_blob(repo, source_git["commit_sha"], PUBLIC_ALLOWLIST_PATH)
        allowlist = _parse_public_allowlist(allowlist_body.decode("utf-8"))
        source_copy_mode = "exact_git_objects_from_pinned_commit"
    else:
        pyproject_body = (repo / "pyproject.toml").read_bytes()
        allowlist = _load_public_allowlist(repo)
        source_copy_mode = "working_tree_development_snapshot_non_release"
    project = tomllib.loads(pyproject_body.decode("utf-8"))["project"]
    version = str(project["version"])

    output.mkdir(parents=True)
    try:
        if commit_bound:
            for member in allowlist:
                _copy_member_from_commit(
                    repo,
                    output,
                    commit_sha=source_git["commit_sha"],
                    relative=member,
                )
            _write_public_source_atlas_table_bytes(
                source_body=_git_blob(
                    repo,
                    source_git["commit_sha"],
                    "data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv",
                ),
                packaged_body=_git_blob(
                    repo,
                    source_git["commit_sha"],
                    "packaging/public_v2/SOURCE_COORDINATE_TABLE.csv",
                ),
                output=output,
            )
        else:
            for member in allowlist:
                _copy_member(repo, output, member)
            _write_public_source_atlas_table(repo, output)
        copied_manifest_sha256 = _source_manifest_sha256(_copied_file_manifest(output))
        _assert_source_git_state_unchanged(source_git, _source_git_state(repo))
        scan = inspect_public_repository(output)
        if not scan["passed"]:
            raise ValueError("Public repository scan failed: " + json.dumps(scan["findings"][:20]))
        receipt = _write_public_receipt(
            output,
            version=version,
            epoch=source_date_epoch,
            source_git=source_git,
            source_copy_mode=source_copy_mode,
            source_manifest_sha256=copied_manifest_sha256,
        )
        final_scan = inspect_public_repository(output)
        if not final_scan["passed"]:
            raise ValueError(
                "Public repository scan failed after receipt: "
                + json.dumps(final_scan["findings"][:20])
            )
        _assert_source_git_state_unchanged(source_git, _source_git_state(repo))
        history = (
            _initialize_fresh_history(output, epoch=source_date_epoch)
            if initialize_git
            else {"initialized": False}
        )
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise

    return {
        "contract": "anibench.public-repository-export-run.v1",
        "output": str(output),
        "source_git": source_git,
        "source_copy_mode": source_copy_mode,
        "source_object_manifest_sha256": copied_manifest_sha256,
        "public_receipt": receipt,
        "public_scan": final_scan,
        "fresh_history": history,
        "published": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-date-epoch", type=int)
    parser.add_argument("--init-git", action="store_true")
    parser.add_argument(
        "--verify-public-history",
        action="store_true",
        help="Scan every Git tree reachable from every ref and require one history root",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Development/test escape hatch; final exports must be commit-bound and clean",
    )
    args = parser.parse_args()
    if args.verify_public_history:
        if args.output is not None or args.source_date_epoch is not None or args.init_git:
            parser.error("--verify-public-history cannot be combined with export arguments")
        report = inspect_public_git_history(args.repo)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2
    if args.output is None or args.source_date_epoch is None:
        parser.error("--output and --source-date-epoch are required for export")
    result = export_public_repository(
        args.repo,
        args.output,
        source_date_epoch=args.source_date_epoch,
        initialize_git=args.init_git,
        allow_dirty=args.allow_dirty,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
