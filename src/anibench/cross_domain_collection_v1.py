# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Native biological domains with explicit roles in the paired estimator.

The legacy solver partitions a vector and one functional quantity using the
labels molecular/functional. Those are computational slots here, not a claim
that a digital or neural acquisition is molecular. Preserve its original
receipt and expose the exact translation. No new estimator is introduced.
"""
from __future__ import annotations

import copy
import json

from jsonschema import Draft202012Validator

from .paired_collection_v1 import INPUT_SCHEMA as LEGACY_SCHEMA
from .paired_collection_v1 import evaluate_paired_collection
from .paired_question_v1 import digest

EVALUATOR = "anibench.cross-domain-collection.v1-candidate1"
DOMAINS = (
    "molecular", "cellular", "microbial", "physiological", "digital",
    "functional", "cognitive", "neural", "psychological", "context",
)


def native_key(key):
    """Translate fixed solver identifiers only; never rewrite source text."""
    return key.replace("molecular", "observer")


INPUT_SCHEMA = copy.deepcopy(LEGACY_SCHEMA)
INPUT_SCHEMA["properties"]["contract"] = {"const": "anibench.cross-domain-collection-input.v1"}
QUESTION_SCHEMA = INPUT_SCHEMA["properties"]["question"]
QUESTION_SCHEMA["properties"]["contract"] = {"const": "anibench.cross-domain-question.v1"}
coordinate = QUESTION_SCHEMA["properties"]["coordinates"]["items"]
coordinate["properties"].pop("domain")
coordinate["required"].remove("domain")
coordinate["properties"].update({
    "biological_domain": {"enum": list(DOMAINS)},
    "role": {"enum": ["observer", "function"]},
})
coordinate["required"].extend(["biological_domain", "role"])
tolerances = QUESTION_SCHEMA["properties"]["tolerances"]
tolerances["properties"] = {native_key(k): v for k, v in tolerances["properties"].items()}
tolerances["required"] = [native_key(k) for k in tolerances["required"]]


def _snapshot(payload):
    try:
        snapshot = json.loads(json.dumps(payload, allow_nan=False))
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Cross-domain collection requires finite JSON values") from exc
    error = next(Draft202012Validator(INPUT_SCHEMA).iter_errors(snapshot), None)
    if error is not None:
        raise ValueError(f"Cross-domain collection input violates schema ({error.validator})")
    return snapshot


def compile_cross_domain_collection(payload):
    """Lower native roles to the unchanged compatibility solver contract.

    Native hashes are checked before replacement, including when acquisition is
    empty. Domain labels grant no acquisition, linkage, causal or noise support.
    """
    source = _snapshot(payload)
    question = source["question"]
    native_hash = digest(question)
    if any(source[k]["question_sha256"] != native_hash for k in ("scenario", "design")):
        raise ValueError("Cross-domain scenario and design must bind the exact native question")
    roles = [c["role"] for c in question["coordinates"]]
    if roles.count("function") != 1 or "observer" not in roles:
        raise ValueError("A question requires an observer vector and exactly one functional target")
    compiled = copy.deepcopy(source)
    compiled["contract"] = "anibench.paired-collection-input.v1"
    lowered = compiled["question"]
    lowered["contract"] = "anibench.paired-biological-question.v1"
    for c in lowered["coordinates"]:
        c.pop("biological_domain")
        c["domain"] = "molecular" if c.pop("role") == "observer" else "functional"
    lowered["tolerances"] = {
        k.replace("observer", "molecular"): v for k, v in lowered["tolerances"].items()
    }
    for key in ("scenario", "design"):
        compiled[key]["question_sha256"] = digest(lowered)
    return source, compiled


def _native_results(results):
    rows = copy.deepcopy(results)
    relation = rows["molecular_function_change_relation"]
    for endpoint in ("lower_support_result", "upper_support_result"):
        row = relation[endpoint]
        if row.get("reason") == "Requires paired molecular and independently measured functional change in the same people":
            row["reason"] = "Requires paired observers and independently measured function in the same people"
        row["estimand"] = "Covariance of observer change with functional change, after subtraction of known error covariance"
    return {native_key(k): v for k, v in rows.items()}


def evaluate_cross_domain_collection(payload):
    """Evaluate collection, never inferred biological relevance from a domain name."""
    source, compiled = compile_cross_domain_collection(payload)
    legacy = evaluate_paired_collection(compiled)
    result = {
        "contract": "anibench.cross-domain-collection-result.v1", "evaluator": EVALUATOR,
        "question_sha256": digest(source["question"]),
        "scenario_sha256": digest(source["scenario"]), "input_sha256": digest(source),
        "question": source["question"]["question"],
        "native_coordinates": source["question"]["coordinates"],
        "lifecycle": legacy["lifecycle"],
        "scope": "One continuous paired observer/function question under a declared reference; not whole-study biology",
        "n_people": legacy["n_people"], "omitted_people": legacy["omitted_people"],
        "canonical_patterns": legacy["canonical_patterns"],
        "canonical_physical_slots": legacy["canonical_physical_slots"],
        "coverage": {native_key(k): v for k, v in legacy["coverage"].items()},
        "results": _native_results(legacy["results"]),
        "conditional_functional_learning": {
            native_key(k): v for k, v in legacy["conditional_functional_learning"].items()
        },
        "uncertainty": legacy["uncertainty"], "model_assumptions": legacy["model_assumptions"],
        "translation": {
            "meaning": "Legacy molecular/functional names denote observer/function computational slots only; native domains above remain authoritative",
            "compiled_input_sha256": digest(compiled),
            "coordinate_roles": [{"id": c["id"], "native_domain": c["biological_domain"],
                                  "role": c["role"],
                                  "legacy_slot": "molecular" if c["role"] == "observer" else "functional"}
                                 for c in source["question"]["coordinates"]],
        },
        "compatibility_receipt": legacy,
        "public_rank_emission_permitted": False,
        "biological_calibration_established": False,
        "whole_benchmark_complete": False,
    }
    result["calculation_sha256"] = digest({
        "evaluator": EVALUATOR, "question": source["question"],
        "scenario": source["scenario"], "results": result["results"],
        "learning": result["conditional_functional_learning"],
    })
    result["receipt_sha256"] = digest(result)
    return result
