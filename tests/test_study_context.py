"""Synthetic sidecar adversaries; no participant or clinical records."""

import copy
import hashlib
import json

import pytest

from anibench.study_context import (
    bytes_sha256,
    create_context,
    hypothetical_approval_copy,
    validate_context,
)

INPUT = b'{"synthetic": 2.0}\n'
RESULT = b'{"synthetic_result": 1}\n'


def seal(context):
    body = {k: v for k, v in context.items() if k != "context_sha256"}
    context["context_sha256"] = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode()
        ).hexdigest()
    )
    return context


def actual(**kwargs):
    return create_context(
        "synthetic-parent", "Synthetic parent", input_bytes=INPUT, result_bytes=RESULT, **kwargs
    )


def scenario(parent):
    return hypothetical_approval_copy(
        parent,
        "synthetic-copy",
        "Hypothetical copy",
        reason="Assume approval only",
        input_bytes=INPUT,
        result_bytes=RESULT,
    )


def test_copy_preserves_parent_and_exact_bytes_and_no_evidence_promotion():
    parent = actual()
    before = copy.deepcopy(parent)
    result = scenario(parent)
    assert parent == before
    assert result["design_binding"] == parent["design_binding"]
    assert result["evidence"] == parent["evidence"]
    assert result["evidence"]["ethics"]["status"] == "unknown"
    assert result["assumptions"][0]["assumed_value"] == "approved"
    assert result["record_id"] != parent["record_id"]
    assert result["evidence_scope"] == "parent_study"
    result["evidence"]["ethics"]["status"] = "explicitly_not_approved"
    assert parent == before  # not a shallow alias


def test_no_result_stays_missing_after_assumption():
    parent = create_context("p", "Synthetic", input_bytes=INPUT)
    result = hypothetical_approval_copy(
        parent, "s", "Hypothetical", reason="Test", input_bytes=INPUT
    )
    assert result["design_binding"]["result_sha256"] is None
    assert result["design_binding"]["result_state"] == "not_run"


@pytest.mark.parametrize(
    "input_bytes,result_bytes",
    [
        (b'{"synthetic":2}', RESULT),
        (INPUT, RESULT + b" "),
        (INPUT, None),
    ],
)
def test_wrong_or_missing_bytes_rejected(input_bytes, result_bytes):
    with pytest.raises(ValueError):
        validate_context(actual(), input_bytes=input_bytes, result_bytes=result_bytes)


def test_parent_tampering_even_after_rehash_rejected():
    parent = actual()
    result = scenario(parent)
    parent["display_name"] = "Changed parent"
    seal(parent)
    with pytest.raises(ValueError, match="Parent binding"):
        validate_context(result, input_bytes=INPUT, result_bytes=RESULT, parent=parent)


@pytest.mark.parametrize(
    "mutation",
    [
        "same_id",
        "actual_assumption",
        "before_value",
        "design_change",
        "evidence_change",
        "extra_field",
    ],
)
def test_rehashed_semantic_attacks_rejected(mutation):
    parent = actual()
    result = scenario(parent)
    if mutation == "same_id":
        result["record_id"] = parent["record_id"]
    if mutation == "actual_assumption":
        result["record_kind"] = "actual"
    if mutation == "before_value":
        result["assumptions"][0]["parent_value"] = "approval_reported"
    if mutation == "design_change":
        result["assumptions"][0]["affects_design"] = True
    if mutation == "evidence_change":
        result["evidence"]["ethics"].update(status="approval_reported", basis="user_declared")
    if mutation == "extra_field":
        result["participants"] = 200
    seal(result)
    with pytest.raises(ValueError):
        validate_context(result, input_bytes=INPUT, result_bytes=RESULT, parent=parent)


def test_metadata_does_not_change_design_or_result_binding():
    context = actual()
    evidence = copy.deepcopy(context["evidence"])
    evidence["ethics"].update(status="explicitly_not_approved", basis="user_declared")
    edited = actual(evidence=evidence)
    assert edited["design_binding"] == context["design_binding"]
    assert edited["context_sha256"] != context["context_sha256"]
    assert edited["evidence"]["publication"]["status"] == "unknown"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/paper",
        "https://user:pass@example.org",
        "https://127.0.0.1/paper",
        "https://localhost/paper",
        "https://host.internal/paper",
        "file:///synthetic",
        "https://example.org/?token=synthetic",
        "//example.org",
        "https://example.org\\@localhost",
        "https://[::1]/",
    ],
)
def test_unsafe_sources_rejected(url):
    evidence = copy.deepcopy(actual()["evidence"])
    evidence["ethics"] = {
        "status": "approval_reported",
        "basis": "source_reported",
        "sources": [{"url": url, "locator": "Synthetic section"}],
    }
    with pytest.raises(ValueError):
        actual(evidence=evidence)


def test_source_reported_requires_source_and_is_independent():
    evidence = copy.deepcopy(actual()["evidence"])
    evidence["publication"] = {
        "status": "peer_reviewed_article",
        "basis": "source_reported",
        "sources": [{"url": "https://example.org/paper", "locator": "Section 2"}],
    }
    context = actual(evidence=evidence)
    assert context["evidence"]["ethics"]["status"] == "unknown"
    evidence["publication"]["sources"] = []
    with pytest.raises(ValueError):
        actual(evidence=evidence)


def test_hash_and_parent_required():
    parent = actual()
    result = scenario(parent)
    with pytest.raises(ValueError):
        validate_context(result, input_bytes=INPUT, result_bytes=RESULT)
    parent["display_name"] = "Tampered"
    with pytest.raises(ValueError):
        validate_context(parent, input_bytes=INPUT, result_bytes=RESULT)
    with pytest.raises(TypeError):
        bytes_sha256("{}")


def test_same_identity_constructor_rejected():
    with pytest.raises(ValueError):
        hypothetical_approval_copy(
            actual(),
            "synthetic-parent",
            "Copy",
            reason="Test",
            input_bytes=INPUT,
            result_bytes=RESULT,
        )


@pytest.mark.parametrize(
    "status,basis", [("unknown", "user_declared"), ("approval_reported", "unknown")]
)
def test_unknown_not_promoted_by_basis(status, basis):
    evidence = copy.deepcopy(actual()["evidence"])
    evidence["ethics"].update(status=status, basis=basis)
    with pytest.raises(ValueError):
        actual(evidence=evidence)


def test_resealed_result_hash_and_state_attacks():
    for field, value in [("result_sha256", "sha256:" + "0" * 64), ("result_state", "not_run")]:
        context = actual()
        context["design_binding"][field] = value
        seal(context)
        with pytest.raises(ValueError):
            validate_context(context, input_bytes=INPUT, result_bytes=RESULT)


def test_metadata_error_does_not_echo_supplied_value():
    context = actual()
    context["unexpected"] = "synthetic-sensitive-placeholder"
    with pytest.raises(ValueError) as caught:
        validate_context(context, input_bytes=INPUT, result_bytes=RESULT)
    assert "synthetic-sensitive-placeholder" not in str(caught.value)
