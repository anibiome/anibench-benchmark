#!/usr/bin/env python3
"""Fetch hash-pinned external source bytes into one fixed, private local root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = Path("data/source_projections/v2/EXTERNAL_SOURCE_ACQUISITION_LEDGER.json")
SOURCE_OBJECT_ROOT = PurePosixPath("data/source_projections/v2/sources")
MAX_SOURCE_BYTES = 100_000_000
STREAM_CHUNK_BYTES = 1024 * 1024


class ExternalSourceFetchError(ValueError):
    pass


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        _validate_https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def verify_source_bytes(body: bytes, *, expected_sha256: str, expected_bytes: int) -> None:
    if len(body) != int(expected_bytes):
        raise ExternalSourceFetchError(
            f"byte count mismatch: expected {expected_bytes}, observed {len(body)}"
        )
    observed = sha256_bytes(body)
    if observed != expected_sha256:
        raise ExternalSourceFetchError(
            f"SHA-256 mismatch: expected {expected_sha256}, observed {observed}"
        )


def _validate_sha256(value: Any) -> str:
    if not isinstance(value, str):
        raise ExternalSourceFetchError("source SHA-256 must be a string")
    digest = value
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ExternalSourceFetchError("source SHA-256 must be 64 lowercase hexadecimal characters")
    return digest


def _validate_https_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ExternalSourceFetchError("source URL must be credential-free HTTPS")
    url = value
    parsed = urlsplit(url)
    try:
        parsed.port
    except ValueError as exc:
        raise ExternalSourceFetchError(
            f"credential-free HTTPS source URL has an invalid port: {url!r}"
        ) from exc
    if (
        "\\" in url
        or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in url)
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ExternalSourceFetchError(f"source URL must be credential-free HTTPS: {url!r}")
    return url


def _load_ledger(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ExternalSourceFetchError("acquisition ledger must contain a sources array")
    return payload


def _contained_path(base: Path, relative: Any) -> tuple[str, Path]:
    if not isinstance(relative, str):
        raise ExternalSourceFetchError("source object path must be a string")
    value = relative
    if "\\" in value or not value:
        raise ExternalSourceFetchError(f"unsafe source object path: {value!r}")
    logical = PurePosixPath(value)
    if logical.is_absolute() or ".." in logical.parts or "." in logical.parts:
        raise ExternalSourceFetchError(f"unsafe source object path: {value!r}")
    if logical.as_posix() != value or logical.parts[: len(SOURCE_OBJECT_ROOT.parts)] != (
        SOURCE_OBJECT_ROOT.parts
    ):
        raise ExternalSourceFetchError(
            f"source object must remain under {SOURCE_OBJECT_ROOT.as_posix()}: {value!r}"
        )
    if len(logical.parts) == len(SOURCE_OBJECT_ROOT.parts):
        raise ExternalSourceFetchError("source object path must name a file")
    source_root = (base / Path(*SOURCE_OBJECT_ROOT.parts)).resolve()
    try:
        source_root.relative_to(base)
    except ValueError as exc:
        raise ExternalSourceFetchError("fixed source root escapes repository through a symlink") from exc
    target = base.joinpath(*logical.parts)
    resolved_target = target.resolve(strict=False)
    try:
        resolved_target.relative_to(source_root)
    except ValueError as exc:
        raise ExternalSourceFetchError(f"source object escapes fixed source root: {value!r}") from exc
    if target.is_symlink():
        raise ExternalSourceFetchError(f"source object target may not be a symlink: {value!r}")
    return value, target


def _stream_and_verify(
    handle: BinaryIO,
    output: BinaryIO | None,
    *,
    expected_sha256: str,
    expected_bytes: int,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    observed = 0
    while True:
        chunk = handle.read(min(STREAM_CHUNK_BYTES, expected_bytes - observed + 1))
        if not chunk:
            break
        observed += len(chunk)
        if observed > expected_bytes or observed > MAX_SOURCE_BYTES:
            raise ExternalSourceFetchError(
                f"download exceeded declared or maximum bytes: expected {expected_bytes}, observed >{expected_bytes}"
            )
        digest.update(chunk)
        if output is not None:
            output.write(chunk)
    actual = digest.hexdigest()
    if observed != expected_bytes:
        raise ExternalSourceFetchError(
            f"byte count mismatch: expected {expected_bytes}, observed {observed}"
        )
    if actual != expected_sha256:
        raise ExternalSourceFetchError(
            f"SHA-256 mismatch: expected {expected_sha256}, observed {actual}"
        )
    return observed, actual


def _fetch_to_temporary(
    *,
    url: str,
    target: Path,
    expected_sha256: str,
    expected_bytes: int,
) -> Path:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AniBench/2 source-verification"},
    )
    opener = urllib.request.build_opener(_HttpsOnlyRedirectHandler())
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with opener.open(request, timeout=60) as response:  # noqa: S310
            final_url = response.geturl()
            _validate_https_url(final_url)
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) != expected_bytes:
                raise ExternalSourceFetchError(
                    f"HTTP Content-Length mismatch: expected {expected_bytes}, observed {content_length}"
                )
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                prefix=f".{target.name}.",
                suffix=".partial",
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                _stream_and_verify(
                    response,
                    temporary,
                    expected_sha256=expected_sha256,
                    expected_bytes=expected_bytes,
                )
                temporary.flush()
                os.fsync(temporary.fileno())
        assert temporary_path is not None
        return temporary_path
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def fetch_sources(
    ledger_path: str | Path = DEFAULT_LEDGER,
    *,
    root: str | Path = ROOT,
    verify_only: bool = False,
) -> dict[str, Any]:
    base = Path(root).resolve()
    ledger_file = Path(ledger_path)
    if not ledger_file.is_absolute():
        ledger_file = base / ledger_file
    ledger_file = ledger_file.resolve()
    try:
        ledger_file.relative_to(base)
    except ValueError as exc:
        raise ExternalSourceFetchError("acquisition ledger must remain under repository root") from exc
    ledger = _load_ledger(ledger_file)
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for source in ledger["sources"]:
        if not isinstance(source, dict):
            raise ExternalSourceFetchError("every acquisition ledger source must be an object")
        source_id = source.get("source_id")
        if (
            not isinstance(source_id, str)
            or not source_id
            or source_id != source_id.strip()
            or source_id in seen_ids
        ):
            raise ExternalSourceFetchError("source IDs must be non-empty and unique")
        seen_ids.add(source_id)
        logical_path, target = _contained_path(base, source.get("path", ""))
        if logical_path in seen_paths:
            raise ExternalSourceFetchError("source object paths must be unique")
        seen_paths.add(logical_path)
        url = _validate_https_url(source.get("url", ""))
        expected_sha256 = _validate_sha256(source.get("sha256", ""))
        expected_bytes = source.get("bytes")
        if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int):
            raise ExternalSourceFetchError("source bytes must be an integer")
        if expected_bytes < 0 or expected_bytes > MAX_SOURCE_BYTES:
            raise ExternalSourceFetchError(
                f"source bytes must be between 0 and {MAX_SOURCE_BYTES}"
            )

        if target.is_file():
            _, revalidated_target = _contained_path(base, logical_path)
            if revalidated_target != target:
                raise ExternalSourceFetchError("source object path changed during verification")
            with target.open("rb") as handle:
                _stream_and_verify(
                    handle,
                    None,
                    expected_sha256=expected_sha256,
                    expected_bytes=expected_bytes,
                )
            disposition = "verified_existing_local_object"
        else:
            if target.exists():
                raise ExternalSourceFetchError(
                    f"source object target must be a regular file: {logical_path}"
                )
            if verify_only:
                raise ExternalSourceFetchError(f"source object is missing: {logical_path}")
            temporary = _fetch_to_temporary(
                url=url,
                target=target,
                expected_sha256=expected_sha256,
                expected_bytes=expected_bytes,
            )
            try:
                _, revalidated_target = _contained_path(base, logical_path)
                if revalidated_target != target or target.exists():
                    raise ExternalSourceFetchError(
                        "source object path changed while the download was in progress"
                    )
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            disposition = "fetched_hash_verified_then_atomically_replaced"
        rows.append(
            {
                "source_id": source_id,
                "path": logical_path,
                "sha256": expected_sha256,
                "bytes": expected_bytes,
                "disposition": disposition,
                "verified": True,
            }
        )
    return {
        "contract": "anibench.external-source-fetch-receipt.v1",
        "ledger_path": ledger_file.relative_to(base).as_posix(),
        "ledger_sha256": sha256_bytes(ledger_file.read_bytes()),
        "fixed_source_root": SOURCE_OBJECT_ROOT.as_posix(),
        "maximum_source_bytes": MAX_SOURCE_BYTES,
        "transport_policy": "https_only_including_redirects",
        "write_policy": "hash_verified_temporary_then_atomic_replace",
        "all_verified": all(row["verified"] for row in rows),
        "source_count": len(rows),
        "sources": rows,
        "redistribution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = fetch_sources(args.ledger, verify_only=args.verify_only)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
