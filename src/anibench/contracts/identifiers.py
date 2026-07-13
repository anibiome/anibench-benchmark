"""Stable identifiers and canonical hashing for AniBench evidence objects."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any


_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_COMPONENT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_STABLE_ID_PATTERN = re.compile(
    r"^anibench:(?P<kind>[a-z][a-z0-9-]{1,63}):"
    r"(?P<authority>[a-z0-9][a-z0-9._-]{0,127}):"
    r"(?P<local_id>[a-z0-9][a-z0-9._-]{0,127})$"
)


def canonical_json_bytes(payload: Any) -> bytes:
    """Return a deterministic UTF-8 representation suitable for content hashes."""

    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_component(value: str) -> str:
    """Normalize an identifier component without using display-name semantics."""

    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized)
    normalized = re.sub(r"[-_.]{2,}", "-", normalized).strip("-_.")
    if not normalized:
        raise ValueError("Identifier component is empty after normalization")
    if len(normalized) > 128:
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        normalized = f"{normalized[:111].rstrip('-_.')}-{digest}"
    if not _COMPONENT_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid normalized identifier component: {normalized!r}")
    return normalized


def stable_id(kind: str, authority: str, local_id: str) -> str:
    """Build a stable ID from an explicit authority and source identifier."""

    normalized_kind = canonical_component(kind)
    if not _KIND_PATTERN.fullmatch(normalized_kind):
        raise ValueError(f"Invalid identifier kind: {kind!r}")
    return (
        f"anibench:{normalized_kind}:"
        f"{canonical_component(authority)}:{canonical_component(local_id)}"
    )


def content_id(kind: str, payload: Any) -> str:
    """Build a stable content-addressed ID that is invariant to mapping order."""

    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return stable_id(kind, "sha256", digest)


def validate_stable_id(value: str, expected_kind: str | None = None) -> str:
    """Validate and return an AniBench stable ID."""

    match = _STABLE_ID_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid AniBench stable ID: {value!r}")
    if expected_kind is not None and match.group("kind") != expected_kind:
        raise ValueError(
            f"Expected stable ID kind {expected_kind!r}, got {match.group('kind')!r}"
        )
    return value


def parse_stable_id(value: str) -> tuple[str, str, str]:
    """Return ``(kind, authority, local_id)`` for a validated stable ID."""

    validate_stable_id(value)
    _, kind, authority, local_id = value.split(":", 3)
    return kind, authority, local_id
