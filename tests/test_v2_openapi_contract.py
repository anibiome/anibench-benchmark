from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from anibench.information_v2 import canonical_matrix_sha256
from anibench.v2 import score_information_run


ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict:
    def digest(label: str) -> str:
        import hashlib

        return "sha256:" + hashlib.sha256(label.encode()).hexdigest()

    information = [[2.0, 0.0], [0.0, 1.0]]
    prior = [[1.0, 0.0], [0.0, 1.0]]
    reference = [[4.0, 0.0], [0.0, 4.0]]
    basis = [[1.0, 0.0], [0.0, 1.0]]
    return {
        "contract": "anibench.information-run.v2-candidate1",
        "benchmark_suite_version": "anibench.v2-openapi-test",
        "lane": "design_preview",
        "parameter_space_hash": digest("parameter"),
        "prior_metric_hash": digest("prior"),
        "reference_level_hash": digest("reference"),
        "event_manifest_hash": digest("events"),
        "intervention_design_hash": digest("intervention"),
        "uncertainty_model_hash": digest("uncertainty"),
        "reference_authority_id": "unregistered-openapi-test",
        "matrix_hashes": {
            "information_matrix_sha256": canonical_matrix_sha256(information),
            "prior_precision_matrix_sha256": canonical_matrix_sha256(prior),
            "reference_information_matrix_sha256": canonical_matrix_sha256(reference),
            "reference_direction_basis_sha256": canonical_matrix_sha256(basis),
        },
        "information_matrix": information,
        "prior_precision": prior,
        "reference_information": reference,
        "reference_direction_basis": basis,
        "source_objects": [
            {"object_id": "mechanics-fixture-not-a-trial", "sha256": digest("source")}
        ],
    }


def test_openapi_exposes_the_real_candidate_route_and_hold_contract() -> None:
    text = (ROOT / "openapi/anibench-v2-candidate.yaml").read_text(encoding="utf-8")
    assert "/api/v2/information:" in text
    assert "implementation_candidate_biological_promotion_gated" in text
    assert "promotion_allowed" in text
    assert "const: false" in text
    assert "anibench.information-replay-packet.v2-candidate1" in text
    assert "run_input_sha256" in text
    assert "absolute_mechanics:" in text
    assert "reference_metrics:" in text
    assert "illustrative_reference_metrics:" in text
    assert "absolute_log10_contraction" in text
    assert "promotable_level_1_reference_verified" in text
    assert "/v2/information:" not in text.replace("/api/v2/information:", "")


def test_runtime_result_matches_the_public_json_schema_contract() -> None:
    result = score_information_run(_fixture())
    assert result["claim_state"] == "implementation_candidate_biological_promotion_gated"
    assert result["promotion_allowed"] is False
    assert result["reference_metrics"] is None
    assert result["illustrative_reference_metrics"] is None

    schema = json.loads((ROOT / "schemas/v2/information-run.schema.json").read_text())
    Draft202012Validator(schema).validate(_fixture())


def test_openapi_retires_three_family_suite_from_current_contract() -> None:
    text = (ROOT / "openapi/anibench-v2-candidate.yaml").read_text(encoding="utf-8")
    assert "/api/v2/benchmark-suite:" not in text
    assert "benchmark-suite-run.schema.json" not in text
    assert "benchmark-suite-result.schema.json" not in text


def test_openapi_exposes_protocol_native_capacity_and_optimizer_only() -> None:
    text = (ROOT / "openapi/anibench-v2-candidate.yaml").read_text(encoding="utf-8")
    assert "/api/v2/protocol-capacity:" in text
    assert "compileProtocolCapacityCandidate" in text
    assert "../schemas/v2/protocol-capacity-input.schema.json" in text
    assert "../schemas/v2/protocol-capacity-result.schema.json" in text
    assert "/api/v2/optimize-protocol:" in text
    assert "optimizeProtocolParetoCandidate" in text
    assert "../schemas/v2/optimizer-protocol-input.schema.json" in text
    assert "../schemas/v2/optimizer-protocol-result.schema.json" in text
    assert "/api/v2/optimize:" not in text
