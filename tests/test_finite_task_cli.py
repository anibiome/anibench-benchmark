# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Exercise the file interface and preserve evidence semantics at the boundary."""

import json
from pathlib import Path

from anibench.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/finite_tasks/synthetic-request.json"


def test_cli_unknown_required_domain_remains_unknown(tmp_path, capsys):
    request = json.loads(EXAMPLE.read_text())
    request["evidence"]["support"] = [
        row for row in request["evidence"]["support"] if row["domain_id"] != "neural"
    ]
    source, output = tmp_path / "input.json", tmp_path / "receipt.json"
    source.write_text(json.dumps(request))
    assert main(["finite-task", str(source), "--out", str(output), "--pretty"]) == 0
    receipt = json.loads(output.read_text())
    assert receipt["attainment"] == "unknown"
    assert receipt["public_saturation_claim_allowed"] is False
    assert json.loads(capsys.readouterr().out)["attainment"] == "unknown"


def test_cli_invalid_task_binding_does_not_write_output(tmp_path):
    request = json.loads(EXAMPLE.read_text())
    request["task"]["functionals"][0]["variance_limit"] *= 100
    source, output = tmp_path / "input.json", tmp_path / "receipt.json"
    source.write_text(json.dumps(request))
    assert main(["finite-task", str(source), "--out", str(output)]) == 2
    assert not output.exists()


def test_cli_refuses_to_overwrite_the_request(tmp_path):
    source = tmp_path / "input.json"
    original = EXAMPLE.read_bytes()
    source.write_bytes(original)
    assert main(["finite-task", str(source), "--out", str(source)]) == 2
    assert source.read_bytes() == original
