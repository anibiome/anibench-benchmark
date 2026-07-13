from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

from scripts.verify_distribution_boundary import inspect_distribution


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_force_includes_only_named_public_runtime_assets() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    wheel_boundary = text.split("[tool.hatch.build.targets.wheel.force-include]", 1)[1]
    wheel_boundary = wheel_boundary.split("[tool.hatch.build.targets.sdist]", 1)[0]

    assert '"/src/anibench/optimizer_v2.py"' in text
    assert '"/src/anibench/scoring.py"' in text
    assert '"/src/anibench/ranking_v2.py"' in text
    assert '"/src/anibench/release/receipt.py"' in text
    assert '"/src/anibench/release/verify.py"' in text
    assert '"/data/source_projections/v2/sources"' in text
    assert '"/data/source_projections/v2/suite_inputs"' in text
    assert '"/data/source_projections/v2/ani-*.json"' in text
    assert '"/web/public"' in text

    assert '"src/anibench/optimizer_v2.py"' not in wheel_boundary
    assert '"src/anibench/release/receipt.py"' not in wheel_boundary
    assert '"src/anibench/release/verify.py"' not in wheel_boundary
    assert '"schemas" =' not in wheel_boundary
    assert '"spec/v2" =' not in wheel_boundary
    assert '"web" =' not in wheel_boundary
    assert '"data/source_projections/v2" =' not in wheel_boundary
    assert '"schemas/v2/optimizer-protocol-input.schema.json"' in wheel_boundary
    assert '"schemas/v2/design-input.schema.json"' in wheel_boundary
    assert '"schemas/v2/benchmark-suite-run.schema.json"' not in wheel_boundary
    assert '"spec/v2/authority/manifest.json"' in wheel_boundary
    assert '"spec/v2/level1/normative-target-requirements.v2.json"' not in wheel_boundary
    assert '"spec/v2/level1/reference-protocol-authority-resolution-receipt.json"' not in wheel_boundary
    assert '"spec/v3/level1/role-aware-target-requirements.v3.json"' in wheel_boundary
    assert '"spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json"' in wheel_boundary
    assert '"spec/v2/level1/reference-design.json"' not in wheel_boundary
    assert '"spec/v2/level1/reference-protocol-mapping-receipt.json"' not in wheel_boundary
    assert '"data/source_projections/v2/aspree.json"' in wheel_boundary
    assert (
        '"packaging/public_v2/SOURCE_COORDINATE_TABLE.csv" = '
        '"anibench/data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv"'
    ) in wheel_boundary
    assert (
        '"packaging/public_v2/EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json" = '
        '"anibench/data/source_projections/v2/EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json"'
    ) in wheel_boundary
    assert (
        '"packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json" = '
        '"anibench/data/source_projections/v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json"'
    ) in wheel_boundary
    assert '"web/v2.html"' in wheel_boundary
    assert '"web/protocol-capacity-example.json"' in wheel_boundary
    assert '"web/optimizer-protocol-example.json"' in wheel_boundary
    assert "/ani-" not in wheel_boundary
    assert "/sources/" not in wheel_boundary
    assert "/suite_inputs/" not in wheel_boundary


def test_distribution_boundary_accepts_normalized_external_atlas_assets(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "anibench.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("anibench/protocol_capacity_v2.py", "pass\n")
        archive.writestr("anibench/optimizer_protocol_v2.py", "pass\n")
        archive.writestr("anibench/data/source_projections/v2/aspree.json", "{}\n")
        archive.writestr(
            "anibench/data/source_projections/v2/EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json",
            "{}\n",
        )
        archive.writestr(
            "anibench/data/source_projections/v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
            "{}\n",
        )
    assert inspect_distribution(wheel, enforce_exact=False)["passed"] is True


def test_distribution_boundary_allows_only_the_publication_method_figure_path(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "anibench.tar.gz"
    figure = tmp_path / "method.svg"
    figure.write_text("<svg/>\n", encoding="utf-8")
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(
            figure,
            arcname="anibench-2.0.0rc1/paper/v2/figures/01_method.svg",
        )

    assert inspect_distribution(archive_path, enforce_exact=False)["passed"] is True


def test_distribution_boundary_rejects_withdrawn_and_private_surface_classes(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "anibench.tar.gz"
    forbidden = (
        "anibench/src/anibench/optimizer_v2.py",
        "anibench/src/anibench/ranking_v2.py",
        "anibench/src/anibench/scoring.py",
        "anibench/schemas/v2/optimizer-run.schema.json",
        "anibench/src/anibench/simulation.py",
        "anibench/src/anibench/suite_v2.py",
        "anibench/src/anibench/release/receipt.py",
        "anibench/src/anibench/release/verify.py",
        "anibench/spec/v2/level1/reference-design.json",
        "anibench/tests/test_v2_optimizer.py",
        "anibench/web/public/data/leaderboard.json",
        "anibench/data/source_projections/v2/ani-elite-sheba.json",
        "anibench/data/source_projections/v2/sources/private.json",
        "anibench/data/source_projections/v2/suite_inputs/legacy.json",
        "anibench/data/source_projections/v2/unlisted.json",
        "anibench/web/styles.css",
        "anibench/figures/private.png",
    )
    with tarfile.open(archive_path, "w:gz") as archive:
        for name in forbidden:
            source = tmp_path / Path(name).name
            source.write_text("private\n", encoding="utf-8")
            archive.add(source, arcname=name)
    report = inspect_distribution(archive_path, enforce_exact=False)
    assert report["passed"] is False
    found = {row["path"] for row in report["findings"]}
    assert set(forbidden) <= found
