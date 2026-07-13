from __future__ import annotations

import io
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.verify_distribution_boundary import inspect_distribution


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("exact-distributions")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return next(output.glob("*.whl")), next(output.glob("*.tar.gz"))


def test_distribution_boundary_accepts_public_runtime(tmp_path: Path) -> None:
    wheel = tmp_path / "anibench.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("anibench/protocol_capacity_v2.py", "pass\n")
        archive.writestr("anibench/schemas/v2/protocol-capacity-input.schema.json", "{}\n")
        archive.writestr("anibench/data/source_projections/v2/aspree.json", "{}\n")
    assert inspect_distribution(wheel, enforce_exact=False)["passed"] is True


def test_distribution_boundary_rejects_ani_sources_and_archive_links(tmp_path: Path) -> None:
    wheel = tmp_path / "anibench.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("anibench/data/studies/ani-elite-sheba.json", "{}\n")
    report = inspect_distribution(wheel, enforce_exact=False)
    assert report["passed"] is False
    assert any(row["rule_id"].startswith("forbidden:") for row in report["findings"])

    sdist = tmp_path / "anibench.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("anibench/patent/private.md")
        payload = b"private"
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
        link = tarfile.TarInfo("anibench/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "target"
        archive.addfile(link)
    report = inspect_distribution(sdist, enforce_exact=False)
    assert report["passed"] is False
    assert {row["rule_id"] for row in report["findings"]} >= {
        "archive_non_regular_forbidden",
        "forbidden:patent/",
    }


def test_exact_built_member_sets_and_unpacked_bytes_pass(
    built_distributions: tuple[Path, Path],
) -> None:
    for distribution in built_distributions:
        report = inspect_distribution(distribution)
        assert report["passed"] is True, report["findings"]
        assert report["exact_member_set_enforced"] is True
        assert report["public_scan_files"] == report["member_count"]


def test_exact_member_set_rejects_innocent_extra_that_old_filter_allowed(
    tmp_path: Path,
    built_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = built_distributions
    hostile = tmp_path / wheel.name
    shutil.copy2(wheel, hostile)
    with zipfile.ZipFile(hostile, "a") as archive:
        archive.writestr("anibench/harmless_extra.py", "VALUE = 1\n")
    report = inspect_distribution(hostile)
    assert report["passed"] is False
    assert {row["rule_id"] for row in report["findings"]} >= {
        "unallowlisted_distribution_member"
    }


def test_archive_duplicate_zip_symlink_and_disguised_nested_container_fail(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "hostile.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("anibench/probe.py", "pass\n")
        archive.writestr("anibench/probe.py", "pass\n")
        link = zipfile.ZipInfo("anibench/link.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "probe.py")
        archive.writestr("anibench/innocent.dat", b"PK\x03\x04" + b"hidden")
    report = inspect_distribution(wheel, enforce_exact=False)
    assert report["passed"] is False
    assert {row["rule_id"] for row in report["findings"]} >= {
        "duplicate_archive_member",
        "archive_link_or_directory_forbidden",
        "nested_archive_forbidden",
    }


def test_unpacked_distribution_bytes_are_scanned_for_secrets(tmp_path: Path) -> None:
    wheel = tmp_path / "secret.whl"
    token_name = "api" + "_key"
    token_value = "A" * 32
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("anibench/probe.py", f'{token_name}="{token_value}"\n')
    report = inspect_distribution(wheel, enforce_exact=False)
    assert report["passed"] is False
    assert "public_scan:secret_assignment" in {
        row["rule_id"] for row in report["findings"]
    }


def test_encrypted_and_traversal_zip_members_fail_before_extraction(tmp_path: Path) -> None:
    wheel = tmp_path / "encrypted.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("anibench/probe.py", "pass\n")
        archive.writestr("../escape.py", "pass\n")
    raw = bytearray(wheel.read_bytes())
    local = raw.find(b"PK\x03\x04")
    central = raw.find(b"PK\x01\x02")
    assert local >= 0 and central >= 0
    raw[local + 6 : local + 8] = (
        int.from_bytes(raw[local + 6 : local + 8], "little") | 1
    ).to_bytes(2, "little")
    raw[central + 8 : central + 10] = (
        int.from_bytes(raw[central + 8 : central + 10], "little") | 1
    ).to_bytes(2, "little")
    wheel.write_bytes(raw)

    report = inspect_distribution(wheel, enforce_exact=False)
    assert report["passed"] is False
    assert {row["rule_id"] for row in report["findings"]} >= {
        "encrypted_member_forbidden",
        "unsafe_archive_path",
    }
    assert not (tmp_path / "escape.py").exists()


def test_safe_archive_directories_are_ignored_but_unsafe_directories_fail(
    tmp_path: Path,
) -> None:
    safe = tmp_path / "safe.tar.gz"
    with tarfile.open(safe, "w:gz") as archive:
        directory = tarfile.TarInfo("anibench")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        body = b"pass\n"
        member = tarfile.TarInfo("anibench/module.py")
        member.size = len(body)
        archive.addfile(member, io.BytesIO(body))
    assert inspect_distribution(safe, enforce_exact=False)["passed"] is True

    hostile = tmp_path / "hostile.tar.gz"
    with tarfile.open(hostile, "w:gz") as archive:
        directory = tarfile.TarInfo("../escape")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
    report = inspect_distribution(hostile, enforce_exact=False)
    assert report["passed"] is False
    assert "unsafe_archive_path" in {
        row["rule_id"] for row in report["findings"]
    }
