from __future__ import annotations

import copy
import hashlib
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from anibench import run_trial_eval
from anibench.comparison_v1 import EvalComparisonError, _canonical_sha256, compare_trial_evals
from anibench.explorer import build_explorer_demo
from anibench.reported_facts import extract_number, load_reported_facts, replay_reported_facts
from anibench.studio import StudioHandler
from anibench.studio_product import StudioAtlasError, _number, build_studio_comparator_atlas
from scripts.build_explorer import build_explorer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def demo():
    return build_explorer_demo(ROOT)


def test_demo_has_opposing_strengths_without_a_winner(demo):
    families = {row["family_id"]: row for row in demo["comparison"]["families"]}
    assert families["intensive"]["pareto_front_protocol_ids"] == ["illustrative-deeper-design"]
    assert families["longitudinal"]["pareto_front_protocol_ids"] == ["illustrative-longer-design"]
    for family in ("causal", "personalized_sequential", "transport"):
        assert len(families[family]["pareto_front_protocol_ids"]) == 2
    assert demo["illustrative"] is True
    assert demo["comparison"]["overall_rank"] is None
    assert demo["comparison"]["overall_scalar"] is None
    assert all(
        receipt["geometry_authority_state"] == "custom_unverified" for receipt in demo["receipts"]
    )


def test_demo_receipts_replay_from_downloadable_inputs(demo):
    for protocol, receipt in zip(demo["protocols"], demo["receipts"], strict=True):
        assert run_trial_eval(protocol) == receipt
    for source in demo["source_objects"]:
        assert source["source_object_sha256"] == _canonical_sha256(source["object"])


def test_comparison_schema_rejects_rehashed_invalid_input(demo):
    bad = copy.deepcopy(demo["receipts"])
    bad[1]["scenarios"][0]["families"][0]["native_metrics"][0]["value"] = "1e99"
    bad[1].pop("assessment_receipt_sha256")
    bad[1]["assessment_receipt_sha256"] = _canonical_sha256(bad[1])
    with pytest.raises(EvalComparisonError, match="schema violation"):
        compare_trial_evals(bad)


def test_comparison_missing_nested_basis_is_a_controlled_error(demo):
    bad = copy.deepcopy(demo["receipts"])
    bad[1]["level1_authority"] = {}
    bad[1].pop("assessment_receipt_sha256")
    bad[1]["assessment_receipt_sha256"] = _canonical_sha256(bad[1])
    with pytest.raises(EvalComparisonError, match="complete comparison basis"):
        compare_trial_evals(bad)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1e999"])
def test_atlas_rejects_nonfinite_coordinates(value):
    with pytest.raises(ValueError, match="nonfinite"):
        _number(value)


def test_source_view_preserves_unknowns_and_conflicting_denominators():
    atlas = build_studio_comparator_atlas(ROOT)
    studies = {row["study_id"]: row for row in atlas["studies"]}
    ipop = studies["snyder-ipop-ihmp-106"]
    assert ipop["population"]["value"] is None
    assert ipop["publication_facts"][0]["value"] == 106
    assert ipop["comparison_eligible"] is False
    tpe = studies["circulate-tpe-ivig"]
    assert tpe["population"]["value"] == 40
    assert {fact["value"] for fact in tpe["publication_facts"]} == {42, 44}
    assert all(fact["state"] == "reported" for fact in tpe["publication_facts"])
    assert all(
        study["source_binding"]["authority_objects"][0]["url"].startswith("https://")
        for study in studies.values()
    )


def test_literal_extractor_never_guesses_numeric_tokens():
    assert extract_number("1,092 time points", "1,092") == 1092
    assert extract_number("median 1.6 years", "1.6") == 1.6
    assert extract_number("Ten nominally healthy adult men", "Ten") == 10
    with pytest.raises(ValueError):
        extract_number("Tension", "Ten")
    for excerpt, token in [("44 then 44", "44"), ("142", "42"), ("NaN", "NaN"), ("1e99", "1e99")]:
        with pytest.raises(ValueError):
            extract_number(excerpt, token)


def test_publication_packet_preserves_precision():
    packet = load_reported_facts(ROOT)
    ukb = next(fact for fact in packet["facts"] if fact["study_id"] == "uk-biobank")
    assert ukb["precision"] == "lower_bound"
    assert ukb["semantics"] == "strict_lower_bound_not_exact_enrollment"
    assert packet["independent_review"] is False
    life = {
        fact["semantics"]: fact["value"]
        for fact in packet["facts"]
        if fact["study_id"] == "life-study"
    }
    assert life["mean_followup_any_contact_not_median"] == 2.6
    assert life["median_followup_any_contact"] == 2.7
    assert len(packet["facts"]) == 37


def test_refreshed_source_must_match_the_registered_url(monkeypatch):
    packet = load_reported_facts(ROOT)
    packet["sources"]["AOUCDRv9"]["url"] = "https://unrelated.example/"
    monkeypatch.setattr("anibench.studio_product.load_reported_facts", lambda root: packet)
    with pytest.raises(StudioAtlasError, match="not bound"):
        build_studio_comparator_atlas(ROOT)


def test_source_replay_rejects_hash_drift(tmp_path):
    packet = load_reported_facts(ROOT)
    for source_id, source in packet["sources"].items():
        suffix = "txt" if source.get("source_format") == "utf8_text" else "json"
        (tmp_path / f"{source_id}.{suffix}").write_text("[]")
    with pytest.raises(ValueError, match="hash mismatch"):
        replay_reported_facts(packet, tmp_path)


def test_static_build_is_create_only_and_binds_every_asset(tmp_path):
    output = tmp_path / "site"
    manifest = build_explorer(output)
    assert manifest["study_count"] == 16
    assert manifest["capacity_comparison_complete_studies"] == 0
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        build_explorer(output)
    # Native core results, not another set of browser formulas.
    packet = json.loads((output / "explorer-demo.json").read_text())
    assert packet["comparison"] == compare_trial_evals(packet["receipts"])


@pytest.fixture
def studio_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_browser_api_is_canonical_cli_authority(studio_url, demo):
    def post(route, body):
        request = Request(
            studio_url + route,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    assert post("/api/v3/eval", demo["protocols"][0]) == demo["receipts"][0]
    assert post("/api/v3/compare", {"receipts": demo["receipts"]}) == demo["comparison"]
    assert (
        post("/api/v3/compare", {"receipt_documents": demo["receipt_documents"]})
        == demo["comparison"]
    )
    assert all(
        json.loads(raw) == receipt
        for raw, receipt in zip(demo["receipt_documents"], demo["receipts"], strict=True)
    )
    assert json.loads(demo["comparison_document"]) == demo["comparison"]
    for invalid in [
        {"receipt_documents": ["{}", "invalid"]},
        {"receipt_documents": ["null", "[]"]},
        {"receipt_documents": [1, 2]},
        {"receipt_documents": demo["receipt_documents"], "receipts": demo["receipts"]},
    ]:
        with pytest.raises(HTTPError) as error:
            post("/api/v3/compare", invalid)
        assert error.value.code == 400
    with pytest.raises(HTTPError) as error:
        post("/api/v3/compare", {"receipts": [demo["receipts"][0]]})
    assert error.value.code == 400
    tampered = copy.deepcopy(demo["receipts"])
    tampered[0]["protocol_id"] = "renamed-without-rehashing"
    with pytest.raises(HTTPError) as error:
        post("/api/v3/compare", {"receipts": tampered})
    assert error.value.code == 400
