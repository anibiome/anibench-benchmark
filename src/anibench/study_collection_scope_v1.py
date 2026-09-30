# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Preserve the acquisition scope around a finite study-question evaluation.

This is a source and interpretation boundary, not another scoring formula.
Mappings describe which part of an acquisition a reference addresses. They do
not establish precision, independent information, or scientific completeness.
"""
from __future__ import annotations

from collections.abc import Mapping

from .estimator_moments_v1 import _hash
from .question_routes_v1 import digest
from .study_questions_v2 import (
    StudyQuestionError,
    _keys,
    _snapshot,
    _text,
    evaluate_study_questions,
)

CONTRACT = "anibench.study-collection-request.v1"
FIELDS = (
    "biology", "compartment", "channel", "observable", "resolution",
    "timing", "population", "quality", "raw_and_derived",
)
STATES = {"documented", "declared", "unknown", "documented_absent"}


def _choice(value, allowed, message):
    if not isinstance(value, str) or value not in allowed:
        raise StudyQuestionError(message)


def _identities(values, allowed):
    if (not isinstance(values, list) or any(not isinstance(v, str) for v in values)
            or len(values) != len(set(values)) or not set(values) <= allowed):
        raise StudyQuestionError("Unknown or duplicate collection reference")


def _fact(value, sources):
    _keys(value, {"state", "description", "source_ids"})
    _choice(value["state"], STATES, "Unknown source-fact state")
    _text(value["description"])
    _identities(value["source_ids"], sources)
    if value["state"] in {"documented", "documented_absent"} and not value["source_ids"]:
        raise StudyQuestionError("Documented facts require source locators")


def collection_scope(collection, *, profile, question_inputs):
    """Validate and retain a declared collection graph and its reference limits.

    Documented means a supplied source claim; this function cannot authenticate
    a paper or verify an acquisition. Open inventories never imply absence.
    Exact duplicate acquisition rows collapse; conflicting identities fail.
    """
    c = _snapshot(collection)
    _keys(c, {"contract", "study_id", "source_scope", "inventory_status",
              "sources", "acquisitions", "links", "reference_mappings"})
    if c["contract"] != "anibench.study-collection.v1":
        raise StudyQuestionError("Unknown collection contract")
    _text(c["study_id"])
    _text(c["source_scope"])
    _choice(c["inventory_status"], {"open", "closed_within_source_scope"},
            "Unknown inventory scope")
    sources = {}
    if not isinstance(c["sources"], list):
        raise StudyQuestionError("Expected source list")
    for source in c["sources"]:
        _keys(source, {"source_id", "url", "locator", "sha256"})
        for name in ("source_id", "url", "locator"):
            _text(source[name])
        if source["sha256"] is not None:
            _hash(source["sha256"])
        if source["source_id"] in sources:
            raise StudyQuestionError("Duplicate source identity")
        sources[source["source_id"]] = source
    if not isinstance(c["acquisitions"], list):
        raise StudyQuestionError("Expected acquisitions list")
    nodes = {}
    for node in c["acquisitions"]:
        _keys(node, {"acquisition_id", "acquisition_state", *FIELDS})
        _text(node["acquisition_id"])
        _choice(node["acquisition_state"], {
            "reported_protocol", "declared_plan", "reported_acquired",
            "unknown", "documented_not_acquired",
        }, "Unknown acquisition evidence state")
        for name in FIELDS:
            _fact(node[name], set(sources))
        identity = node["acquisition_id"]
        if identity in nodes and nodes[identity] != node:
            raise StudyQuestionError("Conflicting acquisition identity")
        nodes[identity] = node
    if not isinstance(c["links"], list):
        raise StudyQuestionError("Expected collection links")
    links = {}
    for link in c["links"]:
        _keys(link, {"from", "to", "relation", "evidence"})
        _text(link["from"])
        _text(link["to"])
        if link["from"] not in nodes or link["to"] not in nodes or link["from"] == link["to"]:
            raise StudyQuestionError("Collection link needs two distinct known acquisitions")
        _choice(link["relation"], {"derived_from", "same_person", "time_aligned",
                                   "exposure_aligned", "controlled_contrast"},
                "Unknown acquisition relation")
        _fact(link["evidence"], set(sources))
        identity = (link["from"], link["to"], link["relation"])
        if identity in links and links[identity] != link:
            raise StudyQuestionError("Conflicting collection relation")
        links[identity] = link
    # A derived output cannot eventually be its own physical ancestor.
    parents = {key: set() for key in nodes}
    for link in links.values():
        if link["relation"] == "derived_from" and link["evidence"]["state"] in {"documented", "declared"}:
            parents[link["from"]].add(link["to"])
    remaining = set(parents)
    while remaining:
        leaves = {key for key in remaining if not parents[key] & remaining}
        if not leaves:
            raise StudyQuestionError("Cyclic acquisition derivation")
        remaining -= leaves
    questions = {q["question_id"]: q for q in profile["questions"]}
    if not isinstance(c["reference_mappings"], list):
        raise StudyQuestionError("Expected explicit reference mappings")
    mappings = {}
    for mapping in c["reference_mappings"]:
        _keys(mapping, {"acquisition_id", "question_id", "definition_sha256",
                        "extent", "addressed", "unaddressed", "qualification"})
        aid, qid = mapping["acquisition_id"], mapping["question_id"]
        _text(aid)
        _text(qid)
        if aid not in nodes or qid not in questions:
            raise StudyQuestionError("Mapping refers to an unknown acquisition or question")
        if mapping["definition_sha256"] != digest(questions[qid]["definition"]):
            raise StudyQuestionError("Mapping changed the exact reference definition")
        _choice(mapping["extent"], {"selected_observables", "exact_named_observable",
                                     "incompatible", "unresolved"}, "Unknown mapping scope")
        for name in ("addressed", "unaddressed"):
            _text(mapping[name])
        _fact(mapping["qualification"], set(sources))
        identity = (aid, qid)
        if identity in mappings:
            raise StudyQuestionError("Duplicate acquisition/question mapping")
        mappings[identity] = mapping
    rows = []
    for identity, node in sorted(nodes.items()):
        selected = [mapping for (aid, _), mapping in sorted(mappings.items()) if aid == identity]
        rows.append({
            **node, "reference_mappings": selected,
            "reference_scope": "outside_reference" if not selected else "see_exact_mapping_limits",
            "questions_with_supplied_inputs": sorted({m["question_id"] for m in selected
                                                       if m["question_id"] in question_inputs}),
        })
    normalized = {**c, "sources": [sources[k] for k in sorted(sources)],
                  "acquisitions": [nodes[k] for k in sorted(nodes)],
                  "links": [links[k] for k in sorted(links)],
                  "reference_mappings": [mappings[k] for k in sorted(mappings)]}
    return {
        "contract": "anibench.study-collection-scope.v1",
        "collection_sha256": digest(normalized),
        "source_scope": c["source_scope"], "inventory_status": c["inventory_status"],
        "sources": normalized["sources"], "acquisitions": rows, "links": normalized["links"],
        "unmapped_acquisition_ids": [r["acquisition_id"] for r in rows if not r["reference_mappings"]],
        "mapping_meaning": "Source-qualified or declared reference scope, not evidence of a passed target or coverage of all information in an acquisition",
        "input_presence_meaning": "Input supplied in at least one scenario, not validated acquisition or target attainment",
        "unlisted_acquisition_meaning": "Not documented in this record; absence is not inferred",
        "whole_study_depth_established": False,
        "domain_completeness_established": False,
    }


def evaluate_study_collection(request: Mapping, *, trusted_profiles: Mapping):
    """Run the existing evaluator and retain the entire supplied source graph.

    The finite result is nested to avoid relabeling it a whole-study score.
    No acquisition, channel, derived output or linkage earns automatic points.
    """
    request = _snapshot(request)
    _keys(request, {"contract", "evaluation", "collection"})
    if request["contract"] != CONTRACT:
        raise StudyQuestionError("Unknown study-collection request")
    evaluation = request["evaluation"]
    if (not isinstance(evaluation, dict) or not isinstance(request["collection"], dict)
            or evaluation.get("study_id") != request["collection"].get("study_id")):
        raise StudyQuestionError("Collection and evaluation must identify the same study")
    result = evaluate_study_questions(evaluation, trusted_profiles=trusted_profiles)
    inputs = {qid for scenario in evaluation["scenarios"] for qid, value in scenario["inputs"].items()
              if value is not None}
    scope = collection_scope(request["collection"], profile=result["profile"], question_inputs=inputs)
    output = {
        "contract": "anibench.study-collection-result.v1",
        "study_id": result["study_id"], "lifecycle": result["lifecycle"],
        "request_sha256": digest(request), "collection_scope": scope,
        "reference_evaluation": result,
        "interpretation": "The percentages describe the registered reference only; collection scope shows relevant acquisitions that those targets do not assess",
        "collection_to_evaluator_input_linkage_verified": False,
        "whole_study_depth_established": False,
        "whole_benchmark_complete": False,
    }
    output["receipt_sha256"] = digest(output)
    return output
