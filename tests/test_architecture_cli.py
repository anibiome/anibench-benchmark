# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""The local architecture command preserves its inputs and source attribution."""

import json
from pathlib import Path

from anibench.architecture_v1 import compare_architecture
from anibench.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/architecture/protein-inventory.json"


def test_source_example_and_cli_agree(tmp_path, capsys):
    request = json.loads(EXAMPLE.read_text())
    source = tmp_path / "private-design.json"
    source.write_text(json.dumps(request))
    output = tmp_path / "private-result.json"
    before = source.read_bytes()
    assert main(["compare-architecture", str(source), "--out", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result == compare_architecture(request)
    assert result["definitely_undominated_record_ids"] == ["ukb-ppp-2023"]
    assert result["overall_score"] is None
    assert source.read_bytes() == before
    assert json.loads(capsys.readouterr().out) == {
        "basis_sha256": result["basis_sha256"], "receipt_sha256": result["receipt_sha256"]
    }


def test_no_source_or_link_overwrite(tmp_path):
    source = tmp_path / "input.json"
    source.write_bytes(EXAMPLE.read_bytes())
    hardlink, symlink = tmp_path / "hard.json", tmp_path / "sym.json"
    hardlink.hardlink_to(source)
    symlink.symlink_to(source)
    before = source.read_bytes()
    for output in (source, hardlink, symlink):
        assert main(["compare-architecture", str(source), "--out", str(output)]) == 2
    assert source.read_bytes() == before


def test_bad_semantics_never_writes_receipt(tmp_path):
    request = json.loads(EXAMPLE.read_text())
    request["basis"]["coordinates"][0]["direction"] = "overall_quality"
    source, output = tmp_path / "invalid.json", tmp_path / "result.json"
    source.write_text(json.dumps(request))
    assert main(["compare-architecture", str(source), "--out", str(output)]) == 2
    assert not output.exists()
