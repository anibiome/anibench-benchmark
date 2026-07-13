from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from anibench.optimizer_protocol_v2 import optimize_protocol
from anibench.protocol_capacity_v2 import compile_protocol_capacity


ROOT = Path(__file__).resolve().parents[1]


def _source_hashes(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [
            *(str(child) for key, child in value.items() if key.endswith("source_object_sha256")),
            *(item for child in value.values() for item in _source_hashes(child)),
        ]
    if isinstance(value, list):
        return [item for child in value for item in _source_hashes(child)]
    return []


def _without_provenance(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_provenance(child)
            for key, child in value.items()
            if not (
                key.endswith("source_object_sha256")
                or key.endswith("source_locator")
            )
        }
    if isinstance(value, list):
        return [_without_provenance(child) for child in value]
    return value


def test_shipped_examples_bind_a_real_synthetic_source_object() -> None:
    source = ROOT / "examples/v2/illustrative-protocol-source.json"
    source_hash = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    source_object = json.loads(source.read_text(encoding="utf-8"))
    assert source_object["claim_class"] == "synthetic_mechanics_fixture_not_empirical_trial"

    protocol = json.loads((ROOT / "web/protocol-capacity-example.json").read_text())
    optimizer = json.loads((ROOT / "web/optimizer-protocol-example.json").read_text())
    hashes = [*_source_hashes(protocol), *_source_hashes(optimizer)]
    assert hashes
    assert set(hashes) == {source_hash}
    assert _without_provenance(protocol) == source_object[
        "protocol_geometry_without_provenance_fields"
    ]
    causal = protocol["causal_geometry"]
    assert causal["decision_rule_operators"] == [
        {
            "decision_rule_operator_id": "static-equal-randomization-rule",
            "state": "static",
            "policy_ids": ["control", "active"],
            "reason": (
                "Each decision epoch randomizes equally between control and active "
                "without state-dependent assignment."
            ),
            "source_object_sha256": source_hash,
            "source_locator": "illustrative:decision-rule:static-equal-randomization",
        }
    ]
    assert causal["assignment_stages"][0]["decision_rule_operator_id"] == (
        "static-equal-randomization-rule"
    )
    assert "decision_rule_uses_measured_state" not in causal["assignment_stages"][0]
    assert all(
        schedule["retention_overlap_authority"]["state"] == "registered_nested"
        for schedule in protocol["measurement_geometry"]["participant_event_schedules"]
    )


def test_web_protocol_example_compiles_deterministically_without_public_rank() -> None:
    protocol = json.loads((ROOT / "web/protocol-capacity-example.json").read_text())
    first = compile_protocol_capacity(protocol)
    second = compile_protocol_capacity(protocol)
    assert first == second
    assert first["overall_scalar"] is None
    assert first["comparison_eligible"] is False
    assert first["public_rank_emission_permitted"] is False


def test_web_optimizer_example_mutates_and_recompiles_the_web_protocol() -> None:
    protocol = json.loads((ROOT / "web/protocol-capacity-example.json").read_text())
    request = json.loads((ROOT / "web/optimizer-protocol-example.json").read_text())
    request["base_protocol"] = protocol
    result = optimize_protocol(request)
    assert result["candidate_count"] == 2
    assert result["pareto_frontier_candidate_ids"] == [
        "base",
        "expand-outcome-schedule",
    ]
    assert result["overall_scalar"] is None
    assert all(
        candidate["capacity_result"]["overall_scalar"] is None
        for candidate in result["candidates"]
    )
