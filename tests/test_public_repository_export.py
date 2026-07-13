from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.export_public_repository import (
    EXTERNAL_SOURCE_ATLAS_STUDY_IDS,
    PUBLIC_ALLOWLIST_PATH,
    PUBLIC_EXPORT_RECEIPT,
    _copy_member_from_commit,
    _parse_public_allowlist,
    export_public_repository,
    inspect_public_git_history,
    inspect_public_repository,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATE_EPOCH = 1_784_268_800


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


@pytest.mark.parametrize(
    "unsafe",
    (
        "/absolute",
        "../escape",
        ".git",
        ".git/config",
        "./relative",
        "double//separator",
        "windows\\separator",
        "nul\x00member",
    ),
)
def test_public_allowlist_rejects_noncanonical_and_git_paths(unsafe: str) -> None:
    raw = "\n".join(sorted((PUBLIC_ALLOWLIST_PATH, unsafe))) + "\n"
    with pytest.raises(ValueError, match="Unsafe public allowlist member"):
        _parse_public_allowlist(raw)


def test_public_export_is_allowlisted_scanned_and_one_root_commit(tmp_path: Path) -> None:
    output = tmp_path / "anibench-public"
    result = export_public_repository(
        ROOT,
        output,
        source_date_epoch=SOURCE_DATE_EPOCH,
        initialize_git=True,
        allow_dirty=True,
    )

    assert result["public_scan"]["passed"] is True
    assert result["fresh_history"]["initialized"] is True
    assert result["fresh_history"]["branch"] == "main"
    assert result["fresh_history"]["commit_count"] == 1
    assert result["fresh_history"]["root_commit_count"] == 1
    assert result["fresh_history"]["clean"] is True
    assert result["fresh_history"]["remote_count"] == 0
    assert _git(output, "rev-list", "--all", "--count") == "1"
    assert len(_git(output, "rev-list", "--max-parents=0", "--all").splitlines()) == 1
    assert _git(output, "status", "--porcelain=v1") == ""
    assert _git(output, "remote") == ""

    receipt = json.loads((output / PUBLIC_EXPORT_RECEIPT).read_text(encoding="utf-8"))
    assert receipt["private_authority_history_included"] is False
    assert receipt["private_ani_projection_objects_included"] is False
    assert receipt["controlled_source_bodies_included"] is False
    assert receipt["public_rank_claim_allowed"] is False
    assert receipt["source_authority_git"] == {
        "commit_sha": result["source_git"]["commit_sha"],
        "tree_sha": result["source_git"]["tree_sha"],
        "clean": not result["source_git"]["dirty"],
        "status_sha256": result["source_git"]["status_sha256"],
    }
    assert receipt["release_source_eligible"] is (not result["source_git"]["dirty"])
    assert receipt["source_copy_mode"] == result["source_copy_mode"]
    assert receipt["source_commit_bound"] is (not result["source_git"]["dirty"])
    assert receipt["source_object_manifest_sha256"] == result[
        "source_object_manifest_sha256"
    ]
    assert len(receipt["public_tree_sha256"]) == 64

    tracked = set(_git(output, "ls-files").splitlines())
    assert PUBLIC_EXPORT_RECEIPT in tracked
    assert ".github/workflows/pr.yml" in tracked
    assert "LICENSES/Apache-2.0.txt" in tracked
    assert "scripts/export_public_repository.py" in tracked
    assert "scripts/verify_external_field_receipts.py" in tracked
    assert "packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json" in tracked
    assert not any(path.startswith("data/source_projections/v2/ani-") for path in tracked)
    assert not any(path.startswith("data/source_projections/v2/sources/") for path in tracked)
    assert not any(path.startswith("release/") for path in tracked)

    # The scanner remains replayable after Git initialization; Git objects are
    # ignored because the one-root history is audited separately.
    assert inspect_public_repository(output)["passed"] is True
    history_report = inspect_public_git_history(output)
    assert history_report["passed"] is True, history_report["findings"]
    assert history_report["root_commit_count"] == 1

    # A release export from the clean one-root tree must source every byte from
    # the pinned commit, not from mutable worktree paths.
    commit_bound_output = tmp_path / "anibench-public-commit-bound"
    commit_bound = export_public_repository(
        output,
        commit_bound_output,
        source_date_epoch=SOURCE_DATE_EPOCH,
        initialize_git=False,
        allow_dirty=False,
    )
    assert commit_bound["source_copy_mode"] == "exact_git_objects_from_pinned_commit"
    assert commit_bound["public_receipt"]["source_commit_bound"] is True
    assert commit_bound["public_receipt"]["release_source_eligible"] is True
    assert (commit_bound_output / "README.md").read_bytes() == _git_bytes(
        output, "show", "HEAD:README.md"
    )
    field_replay = subprocess.run(
        [sys.executable, "scripts/verify_external_field_receipts.py", "--pretty"],
        cwd=output,
        check=False,
        capture_output=True,
        text=True,
    )
    assert field_replay.returncode == 0, field_replay.stderr or field_replay.stdout
    replay = json.loads(field_replay.stdout)
    assert replay["public_field_binding_replay_passed"] is True
    assert replay["coordinate_derivation_replay_passed"] is True
    assert replay["raw_source_revalidation_status"] == (
        "not_requested_public_replay_does_not_require_source_bodies"
    )


def test_public_repository_scan_rejects_unallowlisted_and_controlled_projection(
    tmp_path: Path,
) -> None:
    output = tmp_path / "anibench-public"
    export_public_repository(
        ROOT,
        output,
        source_date_epoch=SOURCE_DATE_EPOCH,
        initialize_git=False,
        allow_dirty=True,
    )
    rogue = output / "private-notes.txt"
    rogue.write_text("not allowlisted\n", encoding="utf-8")
    projection = output / "data/source_projections/v2/aspree.json"
    payload = json.loads(projection.read_text(encoding="utf-8"))
    payload["study_id"] = "ani-controlled-fixture"
    payload["path"] = "/" + "Users" + "/example/private/protocol.txt"
    projection.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = inspect_public_repository(output)
    assert report["passed"] is False
    rules = {finding["rule_id"] for finding in report["findings"]}
    assert {
        "unallowlisted_public_member",
        "internal_ani_study_id",
        "absolute_source_path",
        "private_absolute_path",
    } <= rules


def test_public_repository_scan_audits_export_receipt_bytes(tmp_path: Path) -> None:
    output = tmp_path / "anibench-public"
    export_public_repository(
        ROOT,
        output,
        source_date_epoch=SOURCE_DATE_EPOCH,
        initialize_git=False,
        allow_dirty=True,
    )
    receipt = output / PUBLIC_EXPORT_RECEIPT
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["forbidden_path_probe"] = "/" + "Users" + "/private/source"
    receipt.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = inspect_public_repository(output)
    assert report["passed"] is False
    assert "private_absolute_path" in {
        finding["rule_id"] for finding in report["findings"]
    }


def test_structured_scan_rejects_private_ani_namespace_without_identity_allowlist(
    tmp_path: Path,
) -> None:
    output = tmp_path / "anibench-public"
    export_public_repository(
        ROOT,
        output,
        source_date_epoch=SOURCE_DATE_EPOCH,
        initialize_git=False,
        allow_dirty=True,
    )
    assert not any(study_id.startswith("ani-") for study_id in EXTERNAL_SOURCE_ATLAS_STUDY_IDS)
    projection = output / "data/source_projections/v2/aspree.json"
    original = json.loads(projection.read_text(encoding="utf-8"))
    for study_id in ("ani-controlled-fixture", "ani-private-projection-v999"):
        payload = dict(original)
        payload["embedded_private_study_id"] = study_id
        projection.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        report = inspect_public_repository(output)
        assert report["passed"] is False, study_id
        assert "internal_ani_study_id" in {
            finding["rule_id"] for finding in report["findings"]
        }, study_id


def test_export_refuses_dirty_authority_by_default(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "anibench-public"
    monkeypatch.setattr(
        "scripts.export_public_repository._source_git_state",
        lambda _root: {
            "commit_sha": "0" * 40,
            "tree_sha": "1" * 40,
            "dirty": True,
            "status_sha256": "2" * 64,
        },
    )
    with pytest.raises(ValueError, match="dirty authority worktree"):
        export_public_repository(
            ROOT,
            output,
            source_date_epoch=SOURCE_DATE_EPOCH,
            initialize_git=False,
            allow_dirty=False,
        )
    assert not output.exists()


def test_allow_dirty_export_is_durably_marked_non_release(
    tmp_path: Path, monkeypatch
) -> None:
    output = tmp_path / "anibench-public"
    source_git = {
        "commit_sha": "0" * 40,
        "tree_sha": "1" * 40,
        "dirty": True,
        "status_sha256": "2" * 64,
    }
    monkeypatch.setattr(
        "scripts.export_public_repository._source_git_state",
        lambda _root: source_git,
    )

    export_public_repository(
        ROOT,
        output,
        source_date_epoch=SOURCE_DATE_EPOCH,
        initialize_git=False,
        allow_dirty=True,
    )

    receipt = json.loads((output / PUBLIC_EXPORT_RECEIPT).read_text(encoding="utf-8"))
    assert receipt["source_authority_git"]["clean"] is False
    assert receipt["source_authority_git"]["status_sha256"] == "2" * 64
    assert receipt["release_source_eligible"] is False
    assert receipt["source_commit_bound"] is False
    assert receipt["source_copy_mode"] == "working_tree_development_snapshot_non_release"


def test_export_refuses_to_replace_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "anibench-public"
    output.mkdir()
    with pytest.raises(FileExistsError):
        export_public_repository(
            ROOT,
            output,
            source_date_epoch=SOURCE_DATE_EPOCH,
            initialize_git=False,
            allow_dirty=True,
        )


def test_export_cleans_partial_output_on_scan_failure(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "anibench-public"
    def fail_scan(_root: Path):
        return {
            "contract": "anibench.public-repository-scan.v1",
            "files_scanned": 0,
            "bytes_scanned": 0,
            "findings": [{"path": "x", "rule_id": "forced_failure"}],
            "passed": False,
        }

    monkeypatch.setattr("scripts.export_public_repository.inspect_public_repository", fail_scan)
    with pytest.raises(ValueError, match="Public repository scan failed"):
        export_public_repository(
            ROOT,
            output,
            source_date_epoch=SOURCE_DATE_EPOCH,
            initialize_git=False,
            allow_dirty=True,
        )
    assert not output.exists()


def test_pinned_git_object_copy_cannot_be_swapped_by_worktree_mutation(
    tmp_path: Path,
) -> None:
    authority = tmp_path / "authority"
    authority.mkdir()
    _git(authority, "init", "-b", "main")
    _git(authority, "config", "user.email", "test@example.invalid")
    _git(authority, "config", "user.name", "Test")
    source = authority / "public.txt"
    source.write_text("committed bytes\n", encoding="utf-8")
    _git(authority, "add", "public.txt")
    _git(authority, "commit", "-m", "root")
    commit_sha = _git(authority, "rev-parse", "HEAD")

    source.write_text("hostile worktree swap\n", encoding="utf-8")
    output = tmp_path / "export"
    output.mkdir()
    rows = _copy_member_from_commit(
        authority,
        output,
        commit_sha=commit_sha,
        relative="public.txt",
    )

    assert (output / "public.txt").read_text(encoding="utf-8") == "committed bytes\n"
    assert rows[0]["git_blob_sha"] == _git(authority, "rev-parse", f"{commit_sha}:public.txt")
