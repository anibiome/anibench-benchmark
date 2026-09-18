"""Reproducible, explicitly synthetic mechanics for the study explorer.

The examples have two latent directions, not a claim to model whole human
biology. Both designs share one parameter space and differ in one observation
direction or follow-up span. No trial identity or clinical input is used.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .api import compare_trial_eval_receipts, run_trial_eval


def _hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def build_explorer_demo(root: Path) -> dict[str, Any]:
    """Compile two hypothetical designs through the canonical evaluator."""
    template_path = root / "web" / "protocol-capacity-example.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    deep = copy.deepcopy(template)
    deep["protocol_id"] = "illustrative-deeper-design"
    geometry = deep["measurement_geometry"]
    signal = copy.deepcopy(geometry["signals"][0])
    signal.update(
        signal_id="signal-b",
        canonical_feature_id="feature-b",
        feature_ancestry_id="ancestry-b",
        operator_row=[0, 1],
        source_locator="illustrative:measurement:independent-direction-b",
    )
    geometry["signals"].append(signal)
    group = geometry["covariance_groups"][0]
    group["signal_ids"].append("signal-b")
    group["covariance"] = [[1, 0], [0, 1]]
    joint = geometry["joint_covariance_authority"]
    joint["signal_ids"].append("signal-b")
    joint["covariance"] = [[1, 0], [0, 1]]
    geometry["measurement_modules"][0]["signal_ids"].append("signal-b")

    long = copy.deepcopy(template)
    long["protocol_id"] = "illustrative-longer-design"
    # Stretch the full time geometry together, preserving outcome windows and
    # pre-assignment moderator ordering. A changed schedule alone would break
    # outcome linkage and silently change causal eligibility.
    time_fields = {
        "decision_time_offset",
        "assignment_time_offset",
        "horizon_start_offset_exclusive",
        "horizon_end_offset_inclusive",
    }

    def stretch_time(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "temporal_offsets":
                    value[key] = [offset * 4 for offset in child]
                elif key in time_fields:
                    value[key] = child * 4
                else:
                    stretch_time(child)
        elif isinstance(value, list):
            for child in value:
                stretch_time(child)

    stretch_time(long)

    protocols = [deep, long]
    source_objects = []
    for protocol in protocols:
        # The full recipe object (before rebinding) is shipped for reproduction.
        # Keep the common parameter-space authority unchanged across designs.
        source_object = {
            "schema_version": "anibench.synthetic-explorer-source.v1",
            "evidence_class": "illustrative_synthetic_not_empirical",
            "base_template_sha256": "sha256:"
            + hashlib.sha256(template_path.read_bytes()).hexdigest(),
            "declared_protocol_before_source_rebinding": copy.deepcopy(protocol),
        }
        digest = _hash(source_object)
        source_objects.append({"source_object_sha256": digest, "object": source_object})

        def rebind(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key.endswith("source_object_sha256"):
                        value[key] = digest
                    else:
                        rebind(child)
            elif isinstance(value, list):
                for child in value:
                    rebind(child)

        for key, value in protocol.items():
            if key != "parameter_space":
                rebind(value)

    receipts = [run_trial_eval(protocol) for protocol in protocols]
    comparison = compare_trial_eval_receipts(receipts)
    return {
        "schema_version": "anibench.explorer-demo.v1",
        "illustrative": True,
        "labels": {
            deep["protocol_id"]: "Deeper observations",
            long["protocol_id"]: "Longer follow-up",
        },
        "protocols": protocols,
        "source_objects": source_objects,
        "receipts": receipts,
        "comparison": comparison,
        # JavaScript merges 1 and 1.0. Preserve serialized documents so a
        # browser round-trip cannot silently invalidate canonical receipt hashes.
        "receipt_documents": [json.dumps(receipt, sort_keys=True) for receipt in receipts],
        "comparison_document": json.dumps(comparison, sort_keys=True),
        "protocol_documents": [json.dumps(protocol, sort_keys=True) for protocol in protocols],
    }
