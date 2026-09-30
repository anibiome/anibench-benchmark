"""Acquisitions outside a selective reference must survive unchanged."""
import json
import stat
from copy import deepcopy
from pathlib import Path

import pytest

from anibench.cli import main
from anibench.question_routes_v1 import digest
from anibench.study_collection_scope_v1 import evaluate_study_collection
from anibench.study_questions_v2 import StudyQuestionError, evaluate_study_questions

EXAMPLES = Path(__file__).resolve().parents[1] / "examples/study_questions"


def fixture():
    p = json.loads((EXAMPLES / "PROFILE.json").read_text())
    r = json.loads((EXAMPLES / "collection_scope_REQUEST.json").read_text())
    return p, r


def run(p, r):
    return evaluate_study_collection(r, trusted_profiles={digest(p): p})


def test_broad_acquisitions_do_not_disappear_or_create_unearned_scores():
    p, r = fixture()
    original = evaluate_study_questions(r["evaluation"], trusted_profiles={digest(p): p})
    broad = run(p, r)
    r["collection"]["acquisitions"] = r["collection"]["acquisitions"][:2]
    narrow = run(p, r)
    assert broad["reference_evaluation"] == narrow["reference_evaluation"] == original
    assert set(broad["collection_scope"]["unmapped_acquisition_ids"]) == {
        "oral_dna", "skin_dna", "voice", "movement_video", "retinal_image", "reflectance"}
    assert narrow["collection_scope"]["unmapped_acquisition_ids"] == []
    assert broad["collection_scope"]["collection_sha256"] != narrow["collection_scope"]["collection_sha256"]
    assert not broad["whole_study_depth_established"]
    assert not narrow["whole_study_depth_established"]
    assert not narrow["collection_to_evaluator_input_linkage_verified"]


def test_missing_functional_evaluation_does_not_erase_native_collection():
    p, r = fixture()
    before = run(p, r)["collection_scope"]
    for scenario in r["evaluation"]["scenarios"]:
        scenario["inputs"] = {}
    result = run(p, r)
    assert result["reference_evaluation"]["robust_reference_attainment"] == "unknown"
    after = result["collection_scope"]
    assert before["collection_sha256"] == after["collection_sha256"]
    microbial_before = [x for x in before["acquisitions"] if x["acquisition_id"].endswith("dna")]
    microbial_after = [x for x in after["acquisitions"] if x["acquisition_id"].endswith("dna")]
    assert microbial_after == microbial_before


def test_duplicates_and_input_order_cannot_change_collection_identity():
    p, r = fixture()
    original = run(p, r)
    r["collection"]["acquisitions"] *= 5
    r["collection"]["acquisitions"].reverse()
    r["collection"]["reference_mappings"].reverse()
    result = run(p, r)
    assert original["collection_scope"] == result["collection_scope"]
    assert original["reference_evaluation"] == result["reference_evaluation"]


@pytest.mark.parametrize("fault", ["study", "definition", "source", "conflict", "cycle", "mapping", "collection_type"])
def test_evidence_and_identity_guards(fault):
    p, r = fixture()
    c = r["collection"]
    if fault == "study": c["study_id"] = "another-study"
    elif fault == "definition": c["reference_mappings"][0]["definition_sha256"] = digest({})
    elif fault == "source": c["acquisitions"][0]["quality"]["state"] = "documented"
    elif fault == "conflict":
        node = deepcopy(c["acquisitions"][0]); node["channel"]["description"] = "Conflicting channel"
        c["acquisitions"].append(node)
    elif fault == "cycle":
        evidence = {"state": "declared", "description": "Hypothetical derivation", "source_ids": []}
        c["links"] = [{"from": a, "to": b, "relation": "derived_from", "evidence": evidence}
                      for a, b in (("activity", "cognition"), ("cognition", "activity"))]
    elif fault == "mapping": c["reference_mappings"][0]["acquisition_id"] = "invented"
    else: r["collection"] = []
    with pytest.raises(StudyQuestionError): run(p, r)


def test_cli_keeps_input_private_and_reproduces_original_receipt(tmp_path, capsys):
    out = tmp_path / "result.json"
    assert main(["study-questions", str(EXAMPLES / "PROFILE.json"),
                 str(EXAMPLES / "collection_scope_REQUEST.json"), "--out", str(out)]) == 0
    p, r = fixture()
    assert json.loads(out.read_text()) == run(p, r)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    original = out.read_bytes()
    assert main(["study-questions", str(EXAMPLES / "PROFILE.json"),
                 str(EXAMPLES / "collection_scope_REQUEST.json"), "--out", str(out)]) == 2
    assert out.read_bytes() == original
    assert str(tmp_path) not in capsys.readouterr().err


@pytest.mark.parametrize("path", [
    ("inventory_status",), ("acquisitions", 0, "acquisition_state"),
    ("acquisitions", 0, "quality", "state"),
    ("reference_mappings", 0, "extent"), ("reference_mappings", 0, "acquisition_id"),
    ("reference_mappings", 0, "question_id"),
])
def test_malformed_collection_values_raise_domain_error(path):
    p, r = fixture()
    field = r["collection"]
    for key in path[:-1]: field = field[key]
    field[path[-1]] = []
    with pytest.raises(StudyQuestionError): run(p, r)
