# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Bind a proposed capability design to immutable source facts and assumptions.

This is an intake adapter, not a scoring implementation or source-truth oracle.
It never downloads sources and never promotes a missing value into a measurement.
Source JSON is supplied locally. Raw source objects are not embedded in receipts;
caller-provided design values and binding explanations remain in the evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from fractions import Fraction


class BindingError(ValueError):
    pass


def digest(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise BindingError("Finite JSON values required") from exc
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _json_keys(value):
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise BindingError("JSON object keys must be strings")
        for item in value.values():
            _json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _json_keys(item)


def pointer(value, path):
    """RFC 6901 object/array pointer with strict array indices."""
    if path == "":
        return value
    if not isinstance(path, str) or not path.startswith("/"):
        raise BindingError("Expected an absolute JSON pointer")
    current = value
    try:
        for token in path[1:].split("/"):
            if re.search(r"~(?![01])", token):
                raise BindingError("Invalid JSON pointer escape")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(current, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise BindingError("Invalid array index")
                current = current[int(token)]
            elif isinstance(current, dict):
                current = current[token]
            else:
                raise BindingError("Pointer continues past a scalar")
    except (KeyError, IndexError) as exc:
        raise BindingError("Source or design pointer is missing") from exc
    return current


def leaves(value, prefix=""):
    # Empty containers are intentional declarations and also require a binding.
    if isinstance(value, dict) and value:
        for key, item in value.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from leaves(item, prefix + "/" + escaped)
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from leaves(item, prefix + "/" + str(index))
    else:
        yield prefix


def _same(a, b):
    # Python True == 1 must not qualify a numeric source claim.
    return digest(a) == digest(b)


def _number(value):
    if type(value) is int:
        return Fraction(value)
    if type(value) is not float or not math.isfinite(value):
        raise BindingError("Derivations require finite real values, not booleans")
    return Fraction(str(value))


def _derived_number(value):
    if value.denominator == 1:
        return value.numerator
    try:
        result = float(value)
    except OverflowError as exc:
        raise BindingError("Nonintegral result exceeds finite JSON float range") from exc
    if not math.isfinite(result):
        raise BindingError("Nonintegral result exceeds finite JSON float range")
    return result


def derive(identifier, values, parameters):
    if identifier == "sum" and values and not parameters:
        return _derived_number(sum((_number(x) for x in values), Fraction()))
    if identifier == "affine_unit_conversion" and len(values) == 1:
        if set(parameters) != {"scale", "offset", "source_unit", "target_unit"}:
            raise BindingError("Unit conversion must identify both units")
        if any(not isinstance(parameters[key], str) or not parameters[key].strip()
               for key in ["source_unit", "target_unit"]):
            raise BindingError("Named units required")
        return _derived_number(_number(values[0]) * _number(parameters["scale"]) + _number(parameters["offset"]))
    if identifier in ["two_set_intersection", "two_set_intersection_lower", "two_set_intersection_upper"] and len(values) == 3 and not parameters:
        n, a, b = values
        if any(type(x) is not int or x < 0 for x in values) or max(a, b) > n:
            raise BindingError("Invalid same-universe participant counts")
        bounds = [max(0, a + b - n), min(a, b)]
        if identifier.endswith("_lower"):
            return bounds[0]
        if identifier.endswith("_upper"):
            return bounds[1]
        return bounds
    raise BindingError("Unregistered derivation or parameters")


def bind_design(design, bindings, sources, *, trusted_review_receipts=None):
    """Verify each design leaf; return a private compiler input and audit receipt.

    sources maps a source-object digest to its exact parsed JSON. Text extraction
    requires a digest-valid review from an explicitly supplied trusted registry,
    bound to this value, source locators and a qualified disposition. A hash does
    not establish the scientific truth of the review or the reviewer's identity.
    Protocol assumptions stay explicitly conditional even for a collected study.
    """
    if not isinstance(design, dict) or not isinstance(sources, dict) or not isinstance(bindings, list):
        raise BindingError("Expected design/source objects and a binding list")
    if trusted_review_receipts is not None and not isinstance(trusted_review_receipts, dict):
        raise BindingError("Trusted reviews must be an explicit object map")
    _json_keys(design)
    _json_keys(sources)
    design = copy.deepcopy(design)
    if "source_sha256" in design:
        raise BindingError("source_sha256 is derived by this adapter, never caller-selected")
    digest(design)
    reviews = trusted_review_receipts or {}
    for key, value in reviews.items():
        if not isinstance(value, dict) or key != digest(value):
            raise BindingError("Stale review receipt digest")
        claims = value.get("claims")
        if not isinstance(claims, list):
            raise BindingError("Review claims must be a list")
        for claim in claims:
            if (not isinstance(claim, dict)
                    or set(claim) != {"target", "value_sha256", "source_refs", "disposition"}
                    or not isinstance(claim["target"], str)
                    or not isinstance(claim["value_sha256"], str)
                    or not isinstance(claim["source_refs"], list)
                    or claim["disposition"] not in ["qualified", "unresolved", "rejected"]):
                raise BindingError("Malformed extraction review claim")
    for key, value in sources.items():
        if key != digest(value):
            raise BindingError("Stale source object digest")
    expected = set(leaves(design))
    covered, rows, assumptions, unresolved, qualifications = set(), [], [], [], []
    for binding in bindings:
        if not isinstance(binding, dict) or not {"target", "value_sha256", "mode", "rationale"} <= set(binding):
            raise BindingError("Incomplete binding object")
        target = binding["target"]
        if not isinstance(target, str) or target in covered or target not in expected:
            raise BindingError("Duplicate or non-leaf design binding")
        covered.add(target)
        value = pointer(design, target)
        if binding.get("value_sha256") != digest(value):
            raise BindingError("Design value changed after evidence mapping")
        mode = binding["mode"]
        if not isinstance(binding.get("rationale"), str) or not binding["rationale"].strip():
            raise BindingError("Every binding needs an explicit interpretation")
        references = binding.get("source_refs", [])
        if not isinstance(references, list):
            raise BindingError("source_refs must be a list")
        source_values = []
        for ref in references:
            if (not isinstance(ref, dict) or set(ref) != {"source_sha256", "pointer"}
                    or not isinstance(ref["source_sha256"], str) or ref["source_sha256"] not in sources):
                raise BindingError("Unregistered source reference")
            source_values.append(pointer(sources[ref["source_sha256"]], ref["pointer"]))
        if mode == "literal":
            if len(source_values) != 1 or not _same(value, source_values[0]):
                raise BindingError("Literal value does not match its exact source field")
        elif mode == "derived":
            if not isinstance(binding.get("derivation"), str) or not isinstance(binding.get("parameters", {}), dict):
                raise BindingError("Named derivation and parameter object required")
            derived = derive(binding["derivation"], source_values, binding.get("parameters", {}))
            if not _same(value, derived):
                raise BindingError("Declared arithmetic does not reproduce the design value")
        elif mode == "qualified_extraction":
            key = binding.get("reviewer_receipt_sha256")
            if not references or not isinstance(key, str) or key not in reviews:
                raise BindingError("Textual extraction requires source locators and a review receipt")
            claim = {"target": target, "value_sha256": digest(value),
                     "source_refs": references, "disposition": "qualified"}
            review = reviews[key]
            if (review.get("schema") != "anibench.source-extraction-review.v1"
                    or claim not in review.get("claims", [])):
                raise BindingError("Review does not qualify this exact source-to-value mapping")
            qualifications.append(target)
        elif mode == "normative_assumption":
            if references:
                raise BindingError("An assumption must not masquerade as a source literal")
            assumptions.append(target)
        elif mode == "unknown":
            if value is not None and value != "unknown":
                raise BindingError("Unknown cannot be encoded as zero, false, absence or empty data")
            unresolved.append(target)
        else:
            raise BindingError("Unknown evidence mode")
        rows.append(copy.deepcopy(binding))
    if expected != covered:
        raise BindingError("Unbound design fields: " + ", ".join(sorted(expected - covered)[:8]))
    evidence = {"schema": "anibench.capability-source-bindings.v1", "design": copy.deepcopy(design),
                "bindings": sorted(rows, key=lambda r: r["target"]),
                "source_objects": sorted({r["source_sha256"] for b in rows for r in b.get("source_refs", [])})}
    design["source_sha256"] = digest(evidence)
    receipt = {"schema": "anibench.capability-intake-receipt.v1",
               "evidence_sha256": design["source_sha256"],
               "design_sha256": digest(design), "source_objects": evidence["source_objects"],
               "conditional_assumption_fields": assumptions, "unresolved_fields": unresolved,
               "reviewed_extraction_fields": qualifications,
               "literal_binding_is_not_source_truth_certification": True,
               "raw_source_objects_embedded": False}
    return design, receipt, evidence
