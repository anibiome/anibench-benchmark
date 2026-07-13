#!/usr/bin/env python3
"""Fail when AniBench release metadata describes different versions or scope."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised in the Python 3.10 CI lane
    import tomli as tomllib

from packaging.version import InvalidVersion, Version


def _cff_version(path: Path) -> str:
    match = re.search(r"(?m)^version:\s*[\"']?([^\s\"']+)[\"']?\s*$", path.read_text())
    if match is None:
        raise ValueError("CITATION.cff has no top-level version")
    return match.group(1)


def _runtime_version(path: Path) -> str:
    match = re.search(
        r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
        path.read_text(encoding="utf-8"),
    )
    if match is None:
        raise ValueError("src/anibench/__init__.py has no literal __version__")
    return match.group(1)


def verify_release_metadata(root: Path, *, tag: str | None = None) -> dict[str, object]:
    root = root.resolve()
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    versions = {
        "pyproject.toml": str(project["version"]),
        "src/anibench/__init__.py": _runtime_version(root / "src/anibench/__init__.py"),
        "CITATION.cff": _cff_version(root / "CITATION.cff"),
        ".zenodo.json": str(json.loads((root / ".zenodo.json").read_text())["version"]),
        "codemeta.json": str(json.loads((root / "codemeta.json").read_text())["version"]),
    }
    normalized: dict[str, str] = {}
    findings: list[str] = []
    for name, value in versions.items():
        try:
            normalized[name] = str(Version(value))
        except InvalidVersion:
            findings.append(f"invalid_version:{name}")
    if normalized and len(set(normalized.values())) != 1:
        findings.append("metadata_version_mismatch")
    project_version = Version(versions["pyproject.toml"])
    changelog_version = f"{project_version.major}.{project_version.minor}.{project_version.micro}"
    if project_version.pre:
        pre_name, pre_number = project_version.pre
        changelog_version += f"-{pre_name}.{pre_number}"
    if f"## {changelog_version} " not in (root / "CHANGELOG.md").read_text(encoding="utf-8"):
        findings.append("changelog_version_missing")
    if tag is not None:
        if not tag.startswith("v"):
            findings.append("tag_missing_v_prefix")
        else:
            try:
                if Version(tag[1:]) != project_version:
                    findings.append("tag_version_mismatch")
            except InvalidVersion:
                findings.append("invalid_tag_version")
    return {
        "contract": "anibench.release-metadata-consistency.v1",
        "versions": versions,
        "normalized_versions": normalized,
        "tag": tag,
        "findings": findings,
        "passed": not findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = verify_release_metadata(args.root, tag=args.tag)
    print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
