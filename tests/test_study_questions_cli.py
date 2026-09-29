"""Portable replay, non-destructive output and privacy at the public entry point."""
import json
import stat
from pathlib import Path

import pytest

from anibench.cli import main
from anibench.question_routes_v1 import digest
from anibench.study_questions_v2 import evaluate_study_questions

EXAMPLES = Path(__file__).resolve().parents[1] / "examples/study_questions"
EXPECTED = json.loads((EXAMPLES / "EXPECTED_RECEIPTS.json").read_text())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_portable_cli_reproduces_independently_reviewed_results(name, tmp_path):
    profile_path = EXAMPLES / ("LEGACY_PROFILE.json" if name.startswith("legacy") else "PROFILE.json")
    profile = json.loads(profile_path.read_text())
    request = json.loads((EXAMPLES / name).read_text())
    result = evaluate_study_questions(request, trusted_profiles={digest(profile): profile})
    assert result["receipt_sha256"] == EXPECTED[name]
    target = tmp_path / "result.json"
    assert main(["study-questions", str(profile_path), str(EXAMPLES / name), "--out", str(target)]) == 0
    assert json.loads(target.read_text()) == result
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    original = target.read_bytes()
    assert main(["study-questions", str(profile_path), str(EXAMPLES / name), "--out", str(target)]) == 2
    assert target.read_bytes() == original


@pytest.mark.parametrize("name,state", [
    ("complete", "attained"), ("mosaic", "not_attained"),
    ("switching", "not_attained"), ("unknown", "unknown")])
def test_complete_frame_examples_reproduce_and_preserve_witness_meaning(name, state, tmp_path):
    profile_path = EXAMPLES / "ALTERNATIVES_PROFILE.json"
    request_path = EXAMPLES / ("alternatives_" + name + "_REQUEST.json")
    expected = json.loads((EXAMPLES / "ALTERNATIVES_EXPECTED.json").read_text())[request_path.name]
    target = tmp_path / "result.json"
    assert main(["study-questions", str(profile_path), str(request_path), "--out", str(target)]) == 0
    result = json.loads(target.read_text())
    assert result["receipt_sha256"] == expected["receipt_sha256"]
    assert result["robust_reference_attainment"] == state
    assert [s["reference_attainment"] for s in result["scenarios"]] == expected["scenario_reference_attainment"]
    if name == "switching":
        assert all(s["reference_attainment"] == "attained" for s in result["scenarios"])
        assert result["robust_categories"][0]["passed_percent"] == 0
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


@pytest.mark.parametrize("fault", [
    "profile", "input", "type", "symlink", "same_input", "missing", "loop_output", "loop_profile"
])
def test_private_errors_and_input_preservation(fault, tmp_path, capsys):
    profile = tmp_path / "private-profile.json"
    request = tmp_path / "private-subject-input.json"
    profile.write_bytes((EXAMPLES / "PROFILE.json").read_bytes())
    request.write_bytes((EXAMPLES / "paired256_REQUEST.json").read_bytes())
    target = tmp_path / "result.json"
    sentinel = "private-sentinel-do-not-print"
    if fault == "profile":
        profile.write_text(json.dumps({sentinel: sentinel}))
    elif fault == "input":
        request.write_text(sentinel)
    elif fault == "type":
        payload = json.loads(request.read_text())
        payload["scenarios"] = {sentinel: sentinel}
        request.write_text(json.dumps(payload))
    elif fault == "symlink":
        target.symlink_to(tmp_path / "missing-secret-destination")
    elif fault == "same_input":
        target = request
    elif fault == "missing":
        profile = tmp_path / "missing-private-profile.json"
    elif fault in {"loop_output", "loop_profile"}:
        first = tmp_path / "private-loop-a"
        second = tmp_path / "private-loop-b"
        first.symlink_to(second)
        second.symlink_to(first)
        if fault == "loop_output":
            target = first
        else:
            profile = first
    original = request.read_bytes()
    assert main(["study-questions", str(profile), str(request), "--out", str(target)]) == 2
    assert request.read_bytes() == original
    output = capsys.readouterr()
    assert str(tmp_path) not in output.err + output.out
    assert sentinel not in output.err + output.out
    if fault not in {"symlink", "same_input", "loop_output"}:
        assert not target.exists()


@pytest.mark.parametrize("command", ["paired-question", "paired-collection", "cross-domain-collection"])
def test_shared_path_guard_sanitizes_loops_for_collection_commands(command, tmp_path, capsys):
    first, second = tmp_path / "private-a", tmp_path / "private-b"
    first.symlink_to(second)
    second.symlink_to(first)
    assert main([command, str(EXAMPLES / "paired256_REQUEST.json"), "--out", str(first)]) == 2
    assert str(tmp_path) not in capsys.readouterr().err
