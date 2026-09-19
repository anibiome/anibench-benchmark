"""Evidence sidecars: byte binding and hypothetical identity, never scoring.

Hashes establish integrity, not that evidence is true or a result was computed
from an input. Callers must separately validate the scientific receipt.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, ValidationError

CONTRACT = "anibench.study-context.v1"


def bytes_sha256(value: bytes) -> str:
    """Hash exact bytes, without parsing or reformatting JSON."""
    if not isinstance(value, bytes):
        raise TypeError("Input and result must be bytes")
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _context_hash(context: dict[str, Any]) -> str:
    body = {k: v for k, v in context.items() if k != "context_sha256"}
    return bytes_sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    )


def _schema() -> dict[str, Any]:
    relative = Path("schemas/collection/study-context.schema.json")
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parent):
        path = root / relative
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise ValueError("Study-context schema is not installed")


def _safe_url(value: str) -> None:
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        port = url.port
        if (
            url.scheme != "https"
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or port not in (None, 443)
            or not host
            or "." not in host
            or host.endswith(".")
            or host.lower().endswith((".localhost", ".local", ".internal", ".test"))
            or any(ord(c) <= 32 or c in "\\%" for c in value)
        ):
            raise ValueError("Unsafe source URL")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP source URLs are not supported")
        if any(
            not label
            or any(not (c.isascii() and (c.isalnum() or c == "-")) for c in label)
            or label.startswith("-")
            or label.endswith("-")
            for label in host.split(".")
        ):
            raise ValueError("Unsafe source hostname")
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "Source URL must be credential-free public HTTPS without query/fragment"
        ) from exc


def validate_context(
    context: dict[str, Any],
    *,
    input_bytes: bytes,
    result_bytes: bytes | None = None,
    parent: dict[str, Any] | None = None,
) -> None:
    """Validate structure, exact byte bindings and (for copies) supplied parent.

    No network requests. A syntactically public URL is not source verification.
    Hypothetical copies support approval-only changes, not geometry edits.
    """
    try:
        Draft202012Validator(_schema()).validate(context)
    except ValidationError:
        raise ValueError("Invalid study-context structure") from None
    if context["context_sha256"] != _context_hash(context):
        raise ValueError("Context hash mismatch")
    binding = context["design_binding"]
    if binding["input_sha256"] != bytes_sha256(input_bytes):
        raise ValueError("Input binding mismatch; result is stale")
    expected_result = None if result_bytes is None else bytes_sha256(result_bytes)
    if binding["result_sha256"] != expected_result:
        raise ValueError("Result binding mismatch or missing result bytes")
    if binding["result_state"] != ("not_run" if result_bytes is None else "bytes_bound"):
        raise ValueError("Result state mismatch")
    for evidence in context["evidence"].values():
        if (evidence["status"] == "unknown") != (evidence["basis"] == "unknown"):
            raise ValueError("Unknown status and basis must agree")
        if evidence["basis"] == "unknown" and evidence["sources"]:
            raise ValueError("Unknown evidence cannot assert sources")
        if evidence["basis"] == "source_reported" and not evidence["sources"]:
            raise ValueError("Source-reported evidence requires a source")
        for source in evidence["sources"]:
            _safe_url(source["url"])
    if context["record_kind"] == "actual":
        if (
            context["parent"] is not None
            or context["assumptions"]
            or context["evidence_scope"] != "this_record"
        ):
            raise ValueError("Actual records cannot carry scenario assumptions or parents")
        if parent is not None:
            raise ValueError("Actual records do not accept a parent")
        return
    if parent is None or parent.get("record_kind") != "actual":
        raise ValueError("Hypothetical approval copy requires an actual parent")
    validate_context(parent, input_bytes=input_bytes, result_bytes=result_bytes)
    expected_parent = {"record_id": parent["record_id"], "context_sha256": parent["context_sha256"]}
    if context["parent"] != expected_parent or context["record_id"] == parent["record_id"]:
        raise ValueError("Parent binding or scenario identity mismatch")
    if (
        context["evidence"] != parent["evidence"]
        or context["design_binding"] != parent["design_binding"]
        or context["evidence_scope"] != "parent_study"
    ):
        raise ValueError("Approval copy must preserve parent evidence and design binding")
    if len(context["assumptions"]) != 1:
        raise ValueError("Approval copy requires exactly one explicit assumption")
    assumption = context["assumptions"][0]
    if assumption["parent_value"] != parent["evidence"]["ethics"]["status"]:
        raise ValueError("Assumption parent value mismatch")


def create_context(
    record_id: str,
    display_name: str,
    *,
    input_bytes: bytes,
    result_bytes: bytes | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an actual-record sidecar, defaulting both evidence axes to unknown."""
    unknown = {"status": "unknown", "basis": "unknown", "sources": []}
    context = {
        "schema_version": CONTRACT,
        "record_id": record_id,
        "display_name": display_name,
        "record_kind": "actual",
        "parent": None,
        "evidence_scope": "this_record",
        "evidence": copy.deepcopy(
            evidence
            if evidence is not None
            else {"publication": copy.deepcopy(unknown), "ethics": copy.deepcopy(unknown)}
        ),
        "design_binding": {
            "input_sha256": bytes_sha256(input_bytes),
            "result_sha256": None if result_bytes is None else bytes_sha256(result_bytes),
            "result_state": "not_run" if result_bytes is None else "bytes_bound",
        },
        "assumptions": [],
    }
    context["context_sha256"] = _context_hash(context)
    validate_context(context, input_bytes=input_bytes, result_bytes=result_bytes)
    return context


def hypothetical_approval_copy(
    parent: dict[str, Any],
    record_id: str,
    display_name: str,
    *,
    reason: str,
    input_bytes: bytes,
    result_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Copy identity/evidence only; never create approval evidence or rescore."""
    validate_context(parent, input_bytes=input_bytes, result_bytes=result_bytes)
    if parent["record_kind"] != "actual":
        raise ValueError("Only actual records can be copied")
    context = copy.deepcopy(parent)
    context.update(
        record_id=record_id,
        display_name=display_name,
        record_kind="hypothetical",
        evidence_scope="parent_study",
        parent={"record_id": parent["record_id"], "context_sha256": parent["context_sha256"]},
        assumptions=[
            {
                "path": "/scenario_assumptions/ethics_status",
                "parent_value": parent["evidence"]["ethics"]["status"],
                "assumed_value": "approved",
                "reason": reason,
                "affects_design": False,
            }
        ],
    )
    context["context_sha256"] = _context_hash(context)
    validate_context(context, input_bytes=input_bytes, result_bytes=result_bytes, parent=parent)
    return context
