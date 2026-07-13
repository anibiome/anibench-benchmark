"""Fail-closed public-bundle scanning without echoing sensitive values."""

from __future__ import annotations

import base64
import csv
import io
import json
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree


MAX_TEXT_SCAN_BYTES = 5_000_000
MAX_PDF_SCAN_BYTES = 50_000_000

TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".svg",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

SAFE_BINARY_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

IMAGE_METADATA_SAFE_KEYS = {
    "creator",
    "dpi",
    "jfif",
    "jfif_density",
    "jfif_unit",
    "jfif_version",
    "software",
}

SVG_ACTIVE_ELEMENTS = {"foreignobject", "iframe", "object", "script"}
SVG_HREF_ATTRIBUTES = {"href", "{http://www.w3.org/1999/xlink}href"}
SVG_DATA_URI = re.compile(
    r"^data:image/(?P<kind>png|jpe?g);base64,(?P<payload>[A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE,
)

PNG_ALLOWED_CHUNKS = {
    b"IDAT",
    b"IEND",
    b"IHDR",
    b"PLTE",
    b"bKGD",
    b"cHRM",
    b"eXIf",
    b"gAMA",
    b"hIST",
    b"iCCP",
    b"iTXt",
    b"pHYs",
    b"sBIT",
    b"sPLT",
    b"sRGB",
    b"tEXt",
    b"tIME",
    b"tRNS",
    b"zTXt",
}

OPAQUE_CONTAINER_SUFFIXES = {".7z", ".gz", ".tar", ".tgz", ".zip", ".zst"}

FORBIDDEN_RAW_SUFFIXES = (
    ".bam",
    ".cram",
    ".dcm",
    ".fastq",
    ".fastq.gz",
    ".fq",
    ".fq.gz",
    ".m4a",
    ".mp3",
    ".mp4",
    ".nii",
    ".nii.gz",
    ".vcf",
    ".vcf.gz",
    ".wav",
)

FORBIDDEN_RAW_DATA_CLASSES = {
    "controlled_access_data",
    "decryption_key",
    "identity_bridge",
    "participant_level_data",
    "raw_audio",
    "raw_clinical_records",
    "raw_imaging",
    "raw_omics",
    "raw_video",
    "raw_wearable_stream",
}

PARTICIPANT_ID_FIELDS = {
    "access_code",
    "accesscode",
    "lab_id",
    "participant_id",
    "participant_key",
    "patient_id",
    "subject_id",
}


@dataclass(frozen=True, order=True)
class ScanFinding:
    path: str
    category: str
    rule_id: str
    line: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.line is None:
            payload.pop("line")
        return payload


@dataclass(frozen=True)
class BundleScanReport:
    files_scanned: int
    bytes_scanned: int
    findings: tuple[ScanFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "files_scanned": self.files_scanned,
            "bytes_scanned": self.bytes_scanned,
            "findings": [finding.as_dict() for finding in self.findings],
        }


def _text_rules() -> tuple[tuple[str, str, re.Pattern[str]], ...]:
    # Build token prefixes from fragments so the scanner's own source does not
    # contain a complete credential-like fixture.
    git_prefix = "gh" + "p_"
    github_pat = "github" + "_pat_"
    slack_prefix = "xo" + "x[baprs]-"
    google_prefix = "AI" + "za"
    aws_prefix = "AK" + "IA"
    return (
        (
            "private_absolute_path",
            "private_path",
            re.compile(
                r"(?:/Users/[A-Za-z0-9._-]+/[^\s\"'<>]+|"
                r"/home/[A-Za-z0-9._-]+/[^\s\"'<>]+|"
                r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\[^\r\n\"'<>]+)"
            ),
        ),
        (
            "private_key_block",
            "credential",
            re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
        ),
        (
            "github_token",
            "credential",
            re.compile(rf"(?:{git_prefix}[A-Za-z0-9]{{30,}}|{github_pat}[A-Za-z0-9_]{{40,}})"),
        ),
        (
            "slack_token",
            "credential",
            re.compile(rf"{slack_prefix}[A-Za-z0-9-]{{20,}}"),
        ),
        (
            "google_api_key",
            "credential",
            re.compile(rf"{google_prefix}[A-Za-z0-9_-]{{30,}}"),
        ),
        (
            "aws_access_key",
            "credential",
            re.compile(rf"{aws_prefix}[A-Z0-9]{{16}}"),
        ),
        (
            "authorization_bearer",
            "credential",
            re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{20,}", re.IGNORECASE),
        ),
        (
            "unreviewed_drive_link",
            "restricted_collaboration_surface",
            re.compile(r"https?://(?:docs|drive)\.google\.com/[^\s\"'<>]+", re.IGNORECASE),
        ),
        (
            "secret_assignment",
            "credential",
            re.compile(
                r"(?:access[_-]?token|api[_-]?key|api[_-]?token|client[_-]?secret|"
                r"password|private[_-]?key|secret[_-]?key)\s*[=:]\s*"
                r"(?:[\"'][^\"']{12,}[\"']|[A-Za-z0-9._~+/=-]{12,})",
                re.IGNORECASE,
            ),
        ),
    )


def _walk_json(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            yield child_path, child
            yield from _walk_json(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_json(child, f"{path}/{index}")


def _structured_findings(path: str, text: str, suffix: str) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    if suffix in {".json", ".jsonl"}:
        objects: list[Any] = []
        try:
            if suffix == ".json":
                objects = [json.loads(text)]
            else:
                objects = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError:
            return findings
        for obj in objects:
            is_json_schema = isinstance(obj, Mapping) and "$schema" in obj and "$id" in obj
            is_v8_matrix_manifest = (
                isinstance(obj, Mapping)
                and obj.get("schema_version")
                == "anibench.v8.reference-matrix-manifest.v1.1"
            )
            for pointer, value in _walk_json(obj):
                key = pointer.rsplit("/", 1)[-1].lower()
                pointer_parts = pointer.strip("/").split("/")
                is_schema_identifier_declaration = bool(
                    is_json_schema
                    and len(pointer_parts) >= 2
                    and pointer_parts[-2] == "properties"
                    and isinstance(value, Mapping)
                )
                if (
                    key in PARTICIPANT_ID_FIELDS
                    and value is not None
                    and value
                    not in (
                        "",
                        "redacted",
                    )
                    and not is_schema_identifier_declaration
                    and not (
                        is_v8_matrix_manifest
                        and pointer == "/id_columns/participant_id"
                    )
                ):
                    findings.append(
                        ScanFinding(path, "phi_like_identifier", "participant_id_field")
                    )
                if (
                    key == "data_class"
                    and isinstance(value, str)
                    and value in FORBIDDEN_RAW_DATA_CLASSES
                ):
                    findings.append(ScanFinding(path, "forbidden_raw_data", "raw_data_class"))
    elif suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            rows = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            headers = {str(name).strip().lower() for name in (rows.fieldnames or [])}
            sensitive_headers = headers & PARTICIPANT_ID_FIELDS
            if sensitive_headers:
                for row in rows:
                    if any(str(row.get(header, "")).strip() for header in sensitive_headers):
                        findings.append(
                            ScanFinding(path, "phi_like_identifier", "participant_id_column")
                        )
                        break
        except csv.Error:
            return findings
    return findings


def _rule_findings(path: str, text: str) -> list[ScanFinding]:
    findings = []
    for rule_id, category, pattern in _text_rules():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(ScanFinding(path, category, rule_id, line))
    return findings


def _decode_text(path: str, raw: bytes) -> tuple[str | None, list[ScanFinding]]:
    """Decode public text strictly, including common UTF-16 encodings without hiding NULs."""

    findings: list[ScanFinding] = []
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16"), findings
        except UnicodeDecodeError:
            return None, [ScanFinding(path, "scan_coverage", "invalid_utf16_text")]
    if b"\x00" in raw:
        candidates: list[str] = []
        for encoding in ("utf-16-le", "utf-16-be"):
            try:
                decoded = raw.decode(encoding)
            except UnicodeDecodeError:
                continue
            if "\x00" not in decoded:
                printable = sum(character.isprintable() or character.isspace() for character in decoded)
                if decoded and printable / len(decoded) >= 0.85:
                    candidates.append(decoded)
        if not candidates:
            return None, [ScanFinding(path, "scan_coverage", "nul_text_not_inspected")]
        return max(candidates, key=lambda value: sum(character.isprintable() for character in value)), findings
    try:
        return raw.decode("utf-8"), findings
    except UnicodeDecodeError:
        return None, [ScanFinding(path, "scan_coverage", "invalid_utf8_text")]


def _png_structure_findings(raw: bytes, relative: str) -> list[ScanFinding]:
    """Reject malformed PNGs, trailing payloads, and unbounded ancillary chunks."""

    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return [ScanFinding(relative, "scan_coverage", "image_signature_mismatch")]
    offset = 8
    saw_iend = False
    findings: list[ScanFinding] = []
    while offset + 12 <= len(raw):
        length = struct.unpack(">I", raw[offset : offset + 4])[0]
        kind = raw[offset + 4 : offset + 8]
        end = offset + 12 + length
        if length > MAX_TEXT_SCAN_BYTES or end > len(raw):
            return [ScanFinding(relative, "scan_coverage", "malformed_png_chunk")]
        payload = raw[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", raw[offset + 8 + length : end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            return [ScanFinding(relative, "scan_coverage", "invalid_png_crc")]
        if kind not in PNG_ALLOWED_CHUNKS:
            findings.append(ScanFinding(relative, "image_metadata", "unreviewed_png_chunk"))
        offset = end
        if kind == b"IEND":
            saw_iend = True
            break
    if not saw_iend:
        findings.append(ScanFinding(relative, "scan_coverage", "missing_png_iend"))
    elif offset != len(raw):
        findings.append(ScanFinding(relative, "scan_coverage", "trailing_image_payload"))
    return findings


def _jpeg_structure_findings(raw: bytes, relative: str) -> list[ScanFinding]:
    """Reject JPEG application/comment segments except the ordinary JFIF header."""

    if not (raw.startswith(b"\xff\xd8") and raw.endswith(b"\xff\xd9")):
        return [ScanFinding(relative, "scan_coverage", "image_signature_mismatch")]
    findings: list[ScanFinding] = []
    offset = 2
    while offset + 1 < len(raw):
        if raw[offset] != 0xFF:
            return [ScanFinding(relative, "scan_coverage", "malformed_jpeg_segment")]
        while offset < len(raw) and raw[offset] == 0xFF:
            offset += 1
        if offset >= len(raw):
            break
        marker = raw[offset]
        offset += 1
        if marker == 0xD9:
            break
        if marker == 0xDA:  # Scan data begins; the final EOI was checked above.
            break
        if marker in {0x01, *range(0xD0, 0xD8)}:
            continue
        if offset + 2 > len(raw):
            return [ScanFinding(relative, "scan_coverage", "malformed_jpeg_segment")]
        length = struct.unpack(">H", raw[offset : offset + 2])[0]
        if length < 2 or offset + length > len(raw):
            return [ScanFinding(relative, "scan_coverage", "malformed_jpeg_segment")]
        payload = raw[offset + 2 : offset + length]
        if 0xE0 <= marker <= 0xEF:
            if marker != 0xE0 or not payload.startswith(b"JFIF\x00"):
                findings.append(
                    ScanFinding(relative, "image_metadata", "unreviewed_jpeg_app_segment")
                )
        elif marker == 0xFE:
            findings.append(ScanFinding(relative, "image_metadata", "jpeg_comment_not_allowed"))
        offset += length
    return findings


def _image_findings_bytes(raw: bytes, relative: str, expected: str) -> list[ScanFinding]:
    """Parse pixels and conservatively inspect all exposed metadata."""

    findings: list[ScanFinding] = []
    if expected == "PNG":
        findings.extend(_png_structure_findings(raw, relative))
        if findings:
            return findings
    elif expected == "JPEG":
        findings.extend(_jpeg_structure_findings(raw, relative))
        if findings:
            return findings
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as image:
            if image.format != expected:
                return [ScanFinding(relative, "scan_coverage", "image_format_mismatch")]
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            metadata = dict(image.info)
            exif = image.getexif()
            if exif:
                findings.append(ScanFinding(relative, "image_metadata", "exif_not_allowed"))
            for key, value in sorted(metadata.items(), key=lambda item: str(item[0]).lower()):
                normalized_key = str(key).lower()
                if normalized_key not in IMAGE_METADATA_SAFE_KEYS:
                    findings.append(
                        ScanFinding(relative, "image_metadata", "unreviewed_image_metadata")
                    )
                if isinstance(value, bytes):
                    decoded = value.decode("utf-8", errors="replace")
                else:
                    decoded = str(value)
                findings.extend(_rule_findings(relative, f"{key}={decoded}"))
    except Exception:
        return [ScanFinding(relative, "scan_coverage", "unparseable_image")]
    return findings


def _svg_findings(relative: str, text: str) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return [ScanFinding(relative, "scan_coverage", "unparseable_svg")]
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1].lower()
        if local_name in SVG_ACTIVE_ELEMENTS:
            findings.append(ScanFinding(relative, "svg_active_content", "svg_active_element"))
        if element.text and re.search(
            r"(?:url\s*\(\s*(?:data:|https?:|file:)|javascript:)",
            unescape(element.text),
            re.IGNORECASE,
        ):
            findings.append(ScanFinding(relative, "svg_active_content", "svg_style_payload"))
        for attribute, raw_value in element.attrib.items():
            local_attribute = attribute.rsplit("}", 1)[-1].lower()
            value = unescape(str(raw_value)).strip()
            if local_attribute.startswith("on") or value.lower().startswith("javascript:"):
                findings.append(ScanFinding(relative, "svg_active_content", "svg_event_or_script"))
            if re.search(
                r"url\s*\(\s*(?:data:|https?:|file:)", value, re.IGNORECASE
            ):
                findings.append(ScanFinding(relative, "svg_active_content", "svg_style_payload"))
            if attribute not in SVG_HREF_ATTRIBUTES and local_attribute != "href":
                continue
            if value.lower().startswith(("http://", "https://", "file:", "//")):
                findings.append(ScanFinding(relative, "svg_external_content", "external_svg_href"))
                continue
            if not value.lower().startswith("data:"):
                continue
            match = SVG_DATA_URI.fullmatch(value)
            if not match:
                findings.append(ScanFinding(relative, "scan_coverage", "unsupported_svg_data_uri"))
                continue
            try:
                encoded = re.sub(r"\s+", "", match.group("payload"))
                embedded = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError):
                findings.append(ScanFinding(relative, "scan_coverage", "invalid_svg_data_uri"))
                continue
            if len(embedded) > MAX_TEXT_SCAN_BYTES:
                findings.append(ScanFinding(relative, "scan_coverage", "oversized_svg_data_uri"))
                continue
            expected = "PNG" if match.group("kind").lower() == "png" else "JPEG"
            findings.extend(_image_findings_bytes(embedded, relative, expected))
    return findings


def _pdf_findings(path: Path, relative: str) -> tuple[list[ScanFinding], int]:
    """Inspect PDF text, metadata, attachments, and active-content entry points."""

    findings: list[ScanFinding] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            return [ScanFinding(relative, "scan_coverage", "encrypted_pdf_not_inspected")], 0
        root = reader.trailer.get("/Root", {})
        names = root.get("/Names", {}) if hasattr(root, "get") else {}
        if hasattr(names, "get") and names.get("/EmbeddedFiles") is not None:
            findings.append(ScanFinding(relative, "pdf_active_content", "embedded_files_not_allowed"))
        if hasattr(names, "get") and names.get("/JavaScript") is not None:
            findings.append(ScanFinding(relative, "pdf_active_content", "javascript_not_allowed"))
        if hasattr(root, "get") and root.get("/OpenAction") is not None:
            findings.append(ScanFinding(relative, "pdf_active_content", "open_action_not_allowed"))
        text_parts = []
        metadata = reader.metadata
        if metadata:
            text_parts.extend(str(value) for value in metadata.values() if value is not None)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts)
        findings.extend(_rule_findings(relative, text))
        return findings, len(text.encode("utf-8"))
    except Exception:
        return [ScanFinding(relative, "scan_coverage", "unparseable_pdf")], 0


def scan_public_bundle(
    root: str | Path,
    *,
    exclude_paths: Iterable[str] = (),
    max_text_bytes: int = MAX_TEXT_SCAN_BYTES,
) -> BundleScanReport:
    """Scan an unpacked public bundle and fail closed on uninspected payloads."""

    root_path = Path(root).resolve()
    excluded = {Path(value).as_posix() for value in exclude_paths}
    findings: list[ScanFinding] = []
    files_scanned = 0
    bytes_scanned = 0

    for path in sorted(
        root_path.rglob("*"), key=lambda item: item.relative_to(root_path).as_posix()
    ):
        relative = path.relative_to(root_path).as_posix()
        if relative in excluded:
            continue
        if path.is_symlink():
            findings.append(ScanFinding(relative, "bundle_structure", "symlink_not_allowed"))
            continue
        if not path.is_file():
            continue
        files_scanned += 1
        size = path.stat().st_size
        lower_name = relative.lower()
        if lower_name.endswith(FORBIDDEN_RAW_SUFFIXES):
            findings.append(ScanFinding(relative, "forbidden_raw_data", "raw_data_extension"))
            continue
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            if size > MAX_PDF_SCAN_BYTES:
                findings.append(ScanFinding(relative, "scan_coverage", "unscanned_large_pdf"))
                continue
            pdf_findings, inspected_bytes = _pdf_findings(path, relative)
            findings.extend(pdf_findings)
            bytes_scanned += inspected_bytes
            continue
        if suffix in OPAQUE_CONTAINER_SUFFIXES:
            findings.append(
                ScanFinding(relative, "scan_coverage", "opaque_container_not_inspected")
            )
            continue
        if suffix in SAFE_BINARY_SUFFIXES:
            if size > max_text_bytes:
                findings.append(ScanFinding(relative, "scan_coverage", "unscanned_large_file"))
                continue
            raw = path.read_bytes()
            bytes_scanned += len(raw)
            expected = "PNG" if suffix == ".png" else "JPEG" if suffix in {".jpg", ".jpeg"} else ""
            if not expected:
                findings.append(ScanFinding(relative, "scan_coverage", "unsupported_image_format"))
                continue
            findings.extend(_image_findings_bytes(raw, relative, expected))
            continue
        if size > max_text_bytes:
            findings.append(ScanFinding(relative, "scan_coverage", "unscanned_large_file"))
            continue
        raw = path.read_bytes()
        bytes_scanned += len(raw)
        if b"\x00" in raw and suffix not in TEXT_SUFFIXES:
            findings.append(ScanFinding(relative, "scan_coverage", "unclassified_binary"))
            continue
        text, decoding_findings = _decode_text(relative, raw)
        findings.extend(decoding_findings)
        if text is None:
            continue
        findings.extend(_rule_findings(relative, text))
        findings.extend(_structured_findings(relative, text, suffix))
        if suffix == ".svg":
            findings.extend(_svg_findings(relative, text))

    return BundleScanReport(
        files_scanned=files_scanned,
        bytes_scanned=bytes_scanned,
        findings=tuple(sorted(set(findings))),
    )


def redact_text_for_log(text: str) -> str:
    """Redact matched values for logs; release artifacts should fail instead."""

    redacted = text
    for rule_id, _, pattern in _text_rules():
        redacted = pattern.sub(f"[REDACTED:{rule_id}]", redacted)
    return redacted
