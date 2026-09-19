"""End-to-end local metadata flow without mutating design or result bytes."""
from __future__ import annotations

import json

import pytest

from anibench.cli import main


@pytest.mark.parametrize("with_result", [False, True])
def test_local_actual_copy_and_verify_preserve_scientific_inputs(tmp_path, capsys, with_result):
    design = tmp_path / "design.json"
    design.write_bytes(b'{ "synthetic": true, "number": 1.00 }\n')
    result = tmp_path / "result.json"
    result.write_bytes(b'{"synthetic":true,"value":2}\n')
    original = (design.read_bytes(), result.read_bytes())
    actual = tmp_path / "actual.json"
    scenario = tmp_path / "scenario.json"
    extra = ["--result", str(result)] if with_result else []
    assert main(["study-context", "create", str(design), "--id", "actual-test",
                 "--name", "Synthetic source", "--out", str(actual), *extra]) == 0
    assert main(["study-context", "assume-approval", str(design), "--parent", str(actual),
                 "--id", "scenario-test", "--name", "Hypothetical approval",
                 "--reason", "Inspect metadata independently of design",
                 "--out", str(scenario), *extra]) == 0
    a, s = json.loads(actual.read_text()), json.loads(scenario.read_text())
    assert a["evidence"]["ethics"]["status"] == "unknown"
    assert s["evidence"] == a["evidence"]
    assert s["design_binding"] == a["design_binding"]
    assert s["record_kind"] == "hypothetical"
    assert s["assumptions"][0]["affects_design"] is False
    assert (design.read_bytes(), result.read_bytes()) == original
    assert main(["study-context", "verify", str(design), "--context", str(scenario),
                 "--parent", str(actual), *extra]) == 0
    output = capsys.readouterr().out
    assert '"scientific_result_verified": false' in output
    assert str(tmp_path) not in output
    assert 'Synthetic source' not in output
    assert actual.name not in output and scenario.name not in output
    design.write_bytes(b'{"synthetic":true,"number":1.0}\n')
    assert main(["study-context", "verify", str(design), "--context", str(scenario),
                 "--parent", str(actual), *extra]) == 2
    assert "stale" in capsys.readouterr().err


def test_context_outputs_cannot_overwrite_any_bound_input_or_parent(tmp_path):
    design = tmp_path / "design.json"
    design.write_text('{"synthetic":true}\n')
    actual = tmp_path / "actual.json"
    assert main(["study-context", "create", str(design), "--id", "a", "--name", "Test",
                 "--out", str(design)]) == 2
    assert json.loads(design.read_text()) == {"synthetic": True}
    assert main(["study-context", "create", str(design), "--id", "a", "--name", "Test",
                 "--out", str(actual)]) == 0
    before = actual.read_bytes()
    alias = tmp_path / "alias.json"
    alias.hardlink_to(actual)
    assert main(["study-context", "assume-approval", str(design), "--parent", str(actual),
                 "--id", "b", "--name", "Copy", "--reason", "Test", "--out", str(alias)]) == 2
    assert actual.read_bytes() == before
