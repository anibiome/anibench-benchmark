from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from scripts.fetch_v2_external_sources import (
    ExternalSourceFetchError,
    _stream_and_verify,
    fetch_sources,
)


def _write_ledger(root: Path, *, path: str, url: str, body: bytes = b"source") -> Path:
    ledger = root / "ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "source-1",
                        "path": path,
                        "url": url,
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "bytes": len(body),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return ledger


@pytest.mark.parametrize(
    "path",
    (
        "/tmp/escape.bin",
        "../escape.bin",
        "data/source_projections/v2/sources/../../escape.bin",
        "data/source_projections/v2/not-sources/object.bin",
        "data\\source_projections\\v2\\sources\\object.bin",
    ),
)
def test_fetch_rejects_absolute_traversal_and_non_source_paths(
    tmp_path: Path,
    path: str,
) -> None:
    ledger = _write_ledger(tmp_path, path=path, url="https://example.invalid/source")
    with pytest.raises(ExternalSourceFetchError, match="source object|unsafe"):
        fetch_sources(ledger, root=tmp_path, verify_only=True)


@pytest.mark.parametrize(
    "url",
    (
        "file:///etc/passwd",
        "http://example.invalid/source",
        "https://user:password@example.invalid/source",
        "https://example.invalid/source#fragment",
        "https://example.invalid/bad\\path",
        "https://example.invalid/line\nbreak",
        "https://example.invalid:99999/source",
    ),
)
def test_fetch_rejects_file_http_credentials_and_fragments(
    tmp_path: Path,
    url: str,
) -> None:
    path = "data/source_projections/v2/sources/object.bin"
    ledger = _write_ledger(tmp_path, path=path, url=url)
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"source")
    with pytest.raises(ExternalSourceFetchError, match="HTTPS"):
        fetch_sources(ledger, root=tmp_path, verify_only=True)


def test_fetch_rejects_fixed_source_root_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    source_parent = tmp_path / "data/source_projections/v2"
    source_parent.mkdir(parents=True)
    (source_parent / "sources").symlink_to(outside, target_is_directory=True)
    path = "data/source_projections/v2/sources/object.bin"
    ledger = _write_ledger(tmp_path, path=path, url="https://example.invalid/source")
    with pytest.raises(ExternalSourceFetchError, match="fixed source root escapes"):
        fetch_sources(ledger, root=tmp_path, verify_only=True)


def test_fetch_rejects_non_regular_existing_target(tmp_path: Path) -> None:
    path = "data/source_projections/v2/sources/object.bin"
    ledger = _write_ledger(tmp_path, path=path, url="https://example.invalid/source")
    target = tmp_path / path
    target.mkdir(parents=True)
    with pytest.raises(ExternalSourceFetchError, match="regular file"):
        fetch_sources(ledger, root=tmp_path)


@pytest.mark.parametrize("invalid_bytes", (True, 1.0, "1", None))
def test_fetch_rejects_non_integer_byte_contract(
    tmp_path: Path,
    invalid_bytes: object,
) -> None:
    path = "data/source_projections/v2/sources/object.bin"
    ledger = _write_ledger(tmp_path, path=path, url="https://example.invalid/source")
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["sources"][0]["bytes"] = invalid_bytes
    ledger.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ExternalSourceFetchError, match="bytes must be an integer"):
        fetch_sources(ledger, root=tmp_path, verify_only=True)


def test_existing_object_is_streamed_and_verified_without_rewrite(tmp_path: Path) -> None:
    body = b"verified source bytes"
    path = "data/source_projections/v2/sources/object.bin"
    ledger = _write_ledger(
        tmp_path,
        path=path,
        url="https://example.invalid/source",
        body=body,
    )
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_bytes(body)
    before = target.stat().st_mtime_ns
    receipt = fetch_sources(ledger, root=tmp_path, verify_only=True)
    assert receipt["all_verified"] is True
    assert receipt["fixed_source_root"] == "data/source_projections/v2/sources"
    assert receipt["sources"][0]["disposition"] == "verified_existing_local_object"
    assert target.stat().st_mtime_ns == before


def test_download_uses_temporary_then_atomic_replace(tmp_path: Path, monkeypatch) -> None:
    body = b"new verified source"
    path = "data/source_projections/v2/sources/object.bin"
    ledger = _write_ledger(
        tmp_path,
        path=path,
        url="https://example.invalid/source",
        body=body,
    )
    target = tmp_path / path

    def fake_fetch(**kwargs) -> Path:
        assert kwargs["target"] == target
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.parent / ".object.bin.test.partial"
        partial.write_bytes(body)
        return partial

    monkeypatch.setattr(
        "scripts.fetch_v2_external_sources._fetch_to_temporary",
        fake_fetch,
    )
    receipt = fetch_sources(ledger, root=tmp_path)
    assert target.read_bytes() == body
    assert not list(target.parent.glob("*.partial"))
    assert receipt["sources"][0]["disposition"] == (
        "fetched_hash_verified_then_atomically_replaced"
    )


def test_stream_verifier_rejects_overrun_without_writing_past_bound() -> None:
    output = io.BytesIO()
    with pytest.raises(ExternalSourceFetchError, match="exceeded"):
        _stream_and_verify(
            io.BytesIO(b"four"),
            output,
            expected_sha256=hashlib.sha256(b"thr").hexdigest(),
            expected_bytes=3,
        )
    assert len(output.getvalue()) <= 3
