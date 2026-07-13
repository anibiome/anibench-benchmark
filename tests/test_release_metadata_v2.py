from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_release_metadata import verify_release_metadata


ROOT = Path(__file__).resolve().parents[1]


def test_current_release_metadata_versions_are_consistent() -> None:
    report = verify_release_metadata(ROOT, tag="v2.0.0-rc.1")
    assert report["passed"] is True, json.dumps(report, indent=2)
    assert set(report["normalized_versions"].values()) == {"2.0.0rc1"}
    assert report["versions"]["src/anibench/__init__.py"] == "2.0.0rc1"


def test_release_metadata_rejects_wrong_tag() -> None:
    report = verify_release_metadata(ROOT, tag="v2.0.0")
    assert report["passed"] is False
    assert "tag_version_mismatch" in report["findings"]


def test_release_workflow_binds_tag_history_approvals_and_artifact_digests() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" refs/remotes/origin/main' in workflow
    assert "--verify-public-history" in workflow
    assert "git rev-list --max-parents=0 --all" in workflow
    for variable in (
        "FIRST_PATENT_FILING_BOUND_SHA",
        "FIRST_PATENT_FILING_RECEIPT_SHA256",
        "PUBLIC_RELEASE_APPROVED_SHA",
        "INDEPENDENT_RELEASE_AUDIT_APPROVED_SHA",
        "INDEPENDENT_RELEASE_AUDIT_RECEIPT_SHA256",
        "APPROVED_SHA256SUMS_SHA256",
    ):
        assert variable in workflow
    for unbound_boolean in (
        "FIRST_PATENT_FILING_CONFIRMED:",
        "PUBLIC_RELEASE_APPROVED:",
        "INDEPENDENT_RELEASE_AUDIT_APPROVED:",
    ):
        assert unbound_boolean not in workflow


def test_release_docs_require_commit_bound_export_and_exact_distribution_sets() -> None:
    release = (ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    for marker in (
        "exact pinned source",
        "--verify-public-history",
        "exact wheel and source-distribution",
        "APPROVED_SHA256SUMS_SHA256",
    ):
        assert marker in release
    for marker in (
        "source_copy_mode=exact_git_objects_from_pinned_commit",
        "--verify-public-history",
        "exact member set",
        "exact tagged `github.sha`",
    ):
        assert marker in checklist
