"""Public file boundary, schema and executable example checks."""
import json
import stat
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from anibench.cli import main
from anibench.estimator_moments_v1 import evaluate_estimator_moments
from anibench.question_routes_v1 import digest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/estimator_moments"


@pytest.mark.parametrize("name,state", [("exact-pass", "attained"), ("exact-failure", "not_attained"),
                                       ("loose-bound-unknown", "unknown"), ("biased-failure", "not_attained"),
                                       ("missing-support", "unknown")])
def test_example_schema_cli_api_agreement(name, state, tmp_path, capsys):
    dp, rp = EXAMPLES / "definition.json", EXAMPLES / f"{name}.json"
    d, r = json.loads(dp.read_text()), json.loads(rp.read_text())
    for kind, data in (("definition", d), ("request", r)):
        schema = json.loads((ROOT / f"schemas/estimator_moments/v1/{kind}.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
    out = tmp_path / "result.json"
    assert main(["estimator-moments", str(dp), str(rp), "--out", str(out)]) == 0
    expected = evaluate_estimator_moments(r, trusted_definitions={digest(d): d})
    assert json.loads(out.read_text()) == expected
    assert expected["attainment"] == state
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    first = out.read_bytes()
    assert main(["estimator-moments", str(dp), str(rp), "--out", str(out)]) == 2
    assert out.read_bytes() == first
    assert str(tmp_path) not in capsys.readouterr().err


@pytest.mark.parametrize("number", ["1.0000000000000000000000001", "1e-999", "1e999", "NaN", "Infinity"])
def test_lossy_or_nonfinite_json_rejected_without_private_traceback(number, tmp_path, capsys):
    text = (EXAMPLES / "exact-pass.json").read_text()
    text = text.replace("0.0025", number)
    private = tmp_path / "private-sensitive-input.json"
    private.write_text(text)
    out = tmp_path / "result.json"
    assert main(["estimator-moments", str(EXAMPLES / "definition.json"), str(private), "--out", str(out)]) == 2
    assert not out.exists()
    stderr = capsys.readouterr().err
    assert "private-sensitive" not in stderr and "Traceback" not in stderr and number not in stderr


def test_duplicate_json_members_and_input_overwrites_rejected(tmp_path, capsys):
    dp = EXAMPLES / "definition.json"
    rp = tmp_path / "input.json"
    rp.write_text((EXAMPLES / "exact-pass.json").read_text().replace('"lifecycle": "hypothetical",',
                                                                 '"lifecycle": "realized", "lifecycle": "hypothetical",'))
    out = tmp_path / "result.json"
    assert main(["estimator-moments", str(dp), str(rp), "--out", str(out)]) == 2
    assert not out.exists()
    before = rp.read_bytes()
    assert main(["estimator-moments", str(dp), str(rp), "--out", str(rp)]) == 2
    assert rp.read_bytes() == before
    assert str(rp) not in capsys.readouterr().err
