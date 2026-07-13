"""Controlled, fail-closed source intake for ClinicalTrials.gov and protocol PDFs.

This module deliberately stops before AniBench evidence rating or scoring.  It
captures immutable source bytes, source locators, and an explicit human-review
queue.  A successful intake is therefore never a score-bearing promotion.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from types import MappingProxyType
from typing import Any, BinaryIO, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pypdf import PdfReader


NCT_ID_PATTERN = re.compile(r"^NCT[0-9]{8}$")
CLINICALTRIALS_GOV_HOST = "clinicaltrials.gov"
CLINICALTRIALS_GOV_API_ROOT = "https://clinicaltrials.gov/api/v2"
PROTOCOL_PDF_HOSTS = frozenset({CLINICALTRIALS_GOV_HOST, "cdn.clinicaltrials.gov"})

DEFAULT_JSON_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_PDF_MAX_BYTES = 25 * 1024 * 1024
DEFAULT_PDF_MAX_PAGES = 300
DEFAULT_PDF_MAX_TEXT_CHARS = 2_000_000
DEFAULT_PDF_MAX_PAGE_TEXT_CHARS = 100_000
DEFAULT_TIMEOUT_SECONDS = 30.0
READ_CHUNK_BYTES = 64 * 1024

DEFAULT_UNRESOLVED_FIELDS = (
    "study_identity_review",
    "protocol_version_review",
    "planned_vs_realized_event_classification",
    "assay_platform_and_resolution_review",
    "participant_timepoint_specimen_linkage_review",
    "score_field_mapping_review",
    "independent_rating_and_adjudication",
)


class IntakeError(ValueError):
    """Base class for controlled-intake failures."""


class IntakeValidationError(IntakeError):
    """Raised when an intake request violates the source contract."""


class IntakeLimitError(IntakeError):
    """Raised before or during parsing when a configured safety cap is exceeded."""


class IntakeFetchError(IntakeError):
    """Raised when a remote source cannot be retrieved or changes origin."""


def validate_nct_id(nct_id: str) -> str:
    """Return an NCT identifier only when it has the exact canonical form."""

    if not isinstance(nct_id, str) or NCT_ID_PATTERN.fullmatch(nct_id) is None:
        raise IntakeValidationError("NCT identifier must match ^NCT[0-9]{8}$ exactly")
    return nct_id


def _validate_positive_number(value: int | float, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise IntakeValidationError(f"{label} must be positive")


def _validate_positive_integer(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise IntakeValidationError(f"{label} must be a positive integer")


def _validate_https_url(
    url: str,
    *,
    allowed_hosts: frozenset[str],
    label: str,
) -> str:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise IntakeValidationError(f"{label} is not a valid URL") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        hosts = ", ".join(sorted(allowed_hosts))
        raise IntakeValidationError(
            f"{label} must use HTTPS on the fixed allowed host set: {hosts}"
        )
    normalized_host = str(parsed.hostname)
    normalized_netloc = normalized_host if port is None else f"{normalized_host}:{port}"
    return urlunsplit(("https", normalized_netloc, parsed.path or "/", parsed.query, ""))


def _validate_retrieved_at(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise IntakeValidationError("retrieved_at must be a timezone-aware ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntakeValidationError(
            "retrieved_at must be a timezone-aware ISO 8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IntakeValidationError("retrieved_at must include a timezone")


def clinicaltrials_study_url(nct_id: str) -> str:
    """Build the fixed-origin ClinicalTrials.gov v2 study URL."""

    return f"{CLINICALTRIALS_GOV_API_ROOT}/studies/{validate_nct_id(nct_id)}"


def clinicaltrials_search_url(
    query: str,
    *,
    page_size: int = 10,
    page_token: str | None = None,
) -> str:
    """Build a deterministic v2 search URL without accepting an endpoint override."""

    if not isinstance(query, str) or not query.strip():
        raise IntakeValidationError("ClinicalTrials.gov search query must be non-empty")
    if len(query) > 512 or any(ord(character) < 32 for character in query):
        raise IntakeValidationError("ClinicalTrials.gov search query is invalid or too long")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 1000:
        raise IntakeValidationError("page_size must be an integer in [1, 1000]")
    if page_token is not None and (
        not isinstance(page_token, str)
        or not page_token
        or len(page_token) > 2048
        or any(ord(character) < 32 for character in page_token)
    ):
        raise IntakeValidationError("page_token is invalid or too long")
    parameters = {"format": "json", "pageSize": str(page_size), "query.term": query}
    if page_token is not None:
        parameters["pageToken"] = page_token
    return f"{CLINICALTRIALS_GOV_API_ROOT}/studies?{urlencode(parameters)}"


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_thaw(item) for item in value]
    return value


def _json_pointer_escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def iter_json_pointers(value: Any, pointer: str = "") -> Iterator[str]:
    """Yield RFC 6901 pointers for every scalar or empty node in a JSON value."""

    if isinstance(value, Mapping):
        if not value:
            yield pointer or "/"
        for key, item in value.items():
            child = f"{pointer}/{_json_pointer_escape(str(key))}"
            yield from iter_json_pointers(item, child)
        return
    if isinstance(value, (list, tuple)):
        if not value:
            yield pointer or "/"
        for index, item in enumerate(value):
            yield from iter_json_pointers(item, f"{pointer}/{index}")
        return
    yield pointer or "/"


@dataclass(frozen=True)
class SourceLocator:
    locator_type: str
    locator: str

    def __post_init__(self) -> None:
        if self.locator_type not in {"json_pointer", "page"}:
            raise IntakeValidationError("Intake locator_type must be json_pointer or page")
        if not isinstance(self.locator, str) or not self.locator:
            raise IntakeValidationError("Intake locator cannot be empty")

    def as_dict(self) -> dict[str, str]:
        return {"locator_type": self.locator_type, "locator": self.locator}


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    locator: SourceLocator = field(init=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.page_number, bool)
            or not isinstance(self.page_number, int)
            or self.page_number < 1
        ):
            raise IntakeValidationError("PDF page numbers are one-based positive integers")
        if not isinstance(self.text, str):
            raise IntakeValidationError("Extracted PDF page text must be a string")
        object.__setattr__(self, "locator", SourceLocator("page", f"page {self.page_number}"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            **self.locator.as_dict(),
        }


@dataclass(frozen=True)
class IntakeSnapshot:
    """Immutable raw-source snapshot that is permanently ineligible for scoring."""

    source_kind: str
    source_uri: str
    retrieved_at: str
    request: Mapping[str, Any]
    raw_content: bytes = field(repr=False)
    source_locators: tuple[SourceLocator, ...]
    unresolved_fields: tuple[str, ...] = DEFAULT_UNRESOLVED_FIELDS
    parsed_content: Any | None = field(default=None, repr=False)
    extracted_pages: tuple[ExtractedPage, ...] = ()
    schema_version: str = "anibench.intake-snapshot.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "anibench.intake-snapshot.v1":
            raise IntakeValidationError("Unsupported intake snapshot schema version")
        if self.source_kind not in {
            "clinicaltrials_gov_v2_study",
            "clinicaltrials_gov_v2_search",
            "clinicaltrials_gov_protocol_pdf",
        }:
            raise IntakeValidationError(f"Unsupported intake source kind: {self.source_kind!r}")
        allowed_hosts = (
            PROTOCOL_PDF_HOSTS
            if self.source_kind == "clinicaltrials_gov_protocol_pdf"
            else frozenset({CLINICALTRIALS_GOV_HOST})
        )
        _validate_https_url(self.source_uri, allowed_hosts=allowed_hosts, label="source URL")
        _validate_retrieved_at(self.retrieved_at)
        if not isinstance(self.request, Mapping):
            raise IntakeValidationError("Intake request must be an object")
        if not isinstance(self.raw_content, bytes) or not self.raw_content:
            raise IntakeValidationError("raw_content must be non-empty immutable bytes")
        if not self.source_locators or not all(
            isinstance(locator, SourceLocator) for locator in self.source_locators
        ):
            raise IntakeValidationError("Intake snapshot must preserve at least one source locator")
        if not self.unresolved_fields or any(
            not isinstance(item, str) or not item.strip() for item in self.unresolved_fields
        ):
            raise IntakeValidationError("Intake snapshot requires explicit unresolved fields")
        if not all(isinstance(page, ExtractedPage) for page in self.extracted_pages):
            raise IntakeValidationError("Extracted PDF pages must use ExtractedPage records")
        if self.source_kind.endswith("protocol_pdf") and self.parsed_content is not None:
            raise IntakeValidationError("PDF snapshots cannot carry parsed JSON content")
        if not self.source_kind.endswith("protocol_pdf") and self.parsed_content is None:
            raise IntakeValidationError("Registry snapshots require parsed JSON content")
        object.__setattr__(self, "request", _deep_freeze(self.request))
        if self.parsed_content is not None:
            object.__setattr__(self, "parsed_content", _deep_freeze(self.parsed_content))
        object.__setattr__(self, "source_locators", tuple(self.source_locators))
        object.__setattr__(self, "unresolved_fields", tuple(dict.fromkeys(self.unresolved_fields)))
        object.__setattr__(self, "extracted_pages", tuple(self.extracted_pages))

    @property
    def raw_content_sha256(self) -> str:
        return hashlib.sha256(self.raw_content).hexdigest()

    @property
    def raw_content_bytes(self) -> int:
        return len(self.raw_content)

    @property
    def intake_id(self) -> str:
        return f"anibench:intake-snapshot:sha256:{self.raw_content_sha256}"

    @property
    def score_eligible(self) -> bool:
        return False

    @property
    def requires_human_review(self) -> bool:
        return True

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "intake_id": self.intake_id,
            "source_kind": self.source_kind,
            "source_uri": self.source_uri,
            "retrieved_at": self.retrieved_at,
            "request": _deep_thaw(self.request),
            "raw_content_sha256": self.raw_content_sha256,
            "raw_content_bytes": self.raw_content_bytes,
            "source_locators": [locator.as_dict() for locator in self.source_locators],
            "unresolved_fields": list(self.unresolved_fields),
            "score_eligible": False,
            "requires_human_review": True,
            "promotion_state": "intake_only_unreviewed",
        }
        if self.parsed_content is not None:
            payload["parsed_content"] = _deep_thaw(self.parsed_content)
        if self.extracted_pages:
            payload["extracted_pages"] = [page.as_dict() for page in self.extracted_pages]
        return payload


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _response_header(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if callable(getter):
        value = getter(name)
        return None if value is None else str(value)
    return None


def _read_limited(stream: BinaryIO, *, max_bytes: int, label: str) -> bytes:
    _validate_positive_integer(max_bytes, "max_bytes")
    output = bytearray()
    while True:
        chunk = stream.read(min(READ_CHUNK_BYTES, max_bytes + 1 - len(output)))
        if not chunk:
            return bytes(output)
        if not isinstance(chunk, bytes):
            raise IntakeFetchError(f"{label} source returned non-byte content")
        output.extend(chunk)
        if len(output) > max_bytes:
            raise IntakeLimitError(f"{label} exceeds the {max_bytes}-byte intake cap")


def _fetch_bytes(
    url: str,
    *,
    accept: str,
    max_bytes: int,
    timeout: float,
    allowed_hosts: frozenset[str],
    opener: Callable[..., Any] | None,
) -> tuple[bytes, str | None]:
    _validate_positive_number(timeout, "timeout")
    _validate_positive_integer(max_bytes, "max_bytes")
    _validate_https_url(url, allowed_hosts=allowed_hosts, label="source URL")
    request = Request(url, headers={"Accept": accept, "User-Agent": "AniBench-controlled-intake/1"})
    open_request = opener or urlopen
    response: Any | None = None
    try:
        response = open_request(request, timeout=timeout)
        if isinstance(response, bytes):
            if len(response) > max_bytes:
                raise IntakeLimitError(f"Remote source exceeds the {max_bytes}-byte intake cap")
            return response, None
        final_url_getter = getattr(response, "geturl", None)
        if callable(final_url_getter):
            final_url = str(final_url_getter())
            _validate_https_url(
                final_url,
                allowed_hosts=allowed_hosts,
                label="redirected source URL",
            )
        content_length = _response_header(response, "Content-Length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError as exc:
                raise IntakeFetchError("Remote source returned an invalid Content-Length") from exc
            if declared_length < 0:
                raise IntakeFetchError("Remote source returned a negative Content-Length")
            if declared_length > max_bytes:
                raise IntakeLimitError(f"Remote source exceeds the {max_bytes}-byte intake cap")
        content_type = _response_header(response, "Content-Type")
        content = _read_limited(response, max_bytes=max_bytes, label="Remote source")
        return content, content_type
    except IntakeError:
        raise
    except Exception as exc:
        raise IntakeFetchError(f"Remote source retrieval failed: {exc}") from exc
    finally:
        if response is not None and not isinstance(response, bytes):
            close = getattr(response, "close", None)
            if callable(close):
                close()


def _snapshot_registry_json(
    *,
    source_kind: str,
    source_uri: str,
    request: Mapping[str, Any],
    raw_content: bytes,
    content_type: str | None,
    retrieved_at: str | None,
    unresolved_fields: Sequence[str],
) -> IntakeSnapshot:
    if content_type is not None and "json" not in content_type.lower():
        raise IntakeValidationError("ClinicalTrials.gov v2 response is not JSON")
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise IntakeValidationError(
                    f"ClinicalTrials.gov v2 JSON repeats object key {key!r}"
                )
            result[key] = value
        return result

    def reject_nonstandard_number(value: str) -> None:
        raise IntakeValidationError(
            f"ClinicalTrials.gov v2 JSON contains non-standard number {value!r}"
        )

    try:
        parsed = json.loads(
            raw_content,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_number,
        )
    except IntakeError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeValidationError("ClinicalTrials.gov v2 returned invalid JSON") from exc
    if not isinstance(parsed, Mapping):
        raise IntakeValidationError("ClinicalTrials.gov v2 response must be a JSON object")
    locators = tuple(SourceLocator("json_pointer", pointer) for pointer in iter_json_pointers(parsed))
    return IntakeSnapshot(
        source_kind=source_kind,
        source_uri=source_uri,
        retrieved_at=retrieved_at or _now_utc(),
        request=request,
        raw_content=raw_content,
        source_locators=locators,
        unresolved_fields=tuple(unresolved_fields),
        parsed_content=parsed,
    )


def snapshot_clinicaltrials_study(
    nct_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_JSON_MAX_BYTES,
    opener: Callable[..., Any] | None = None,
    retrieved_at: str | None = None,
    unresolved_fields: Sequence[str] = DEFAULT_UNRESOLVED_FIELDS,
) -> IntakeSnapshot:
    """Fetch one ClinicalTrials.gov v2 study into an intake-only snapshot."""

    nct_id = validate_nct_id(nct_id)
    url = clinicaltrials_study_url(nct_id)
    raw, content_type = _fetch_bytes(
        url,
        accept="application/json",
        max_bytes=max_bytes,
        timeout=timeout,
        allowed_hosts=frozenset({CLINICALTRIALS_GOV_HOST}),
        opener=opener,
    )
    return _snapshot_registry_json(
        source_kind="clinicaltrials_gov_v2_study",
        source_uri=url,
        request={"nct_id": nct_id},
        raw_content=raw,
        content_type=content_type,
        retrieved_at=retrieved_at,
        unresolved_fields=unresolved_fields,
    )


def snapshot_clinicaltrials_search(
    query: str,
    *,
    page_size: int = 10,
    page_token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_JSON_MAX_BYTES,
    opener: Callable[..., Any] | None = None,
    retrieved_at: str | None = None,
    unresolved_fields: Sequence[str] = DEFAULT_UNRESOLVED_FIELDS,
) -> IntakeSnapshot:
    """Capture one deterministic ClinicalTrials.gov v2 search-result page."""

    url = clinicaltrials_search_url(query, page_size=page_size, page_token=page_token)
    raw, content_type = _fetch_bytes(
        url,
        accept="application/json",
        max_bytes=max_bytes,
        timeout=timeout,
        allowed_hosts=frozenset({CLINICALTRIALS_GOV_HOST}),
        opener=opener,
    )
    request: dict[str, Any] = {"query": query, "page_size": page_size}
    if page_token is not None:
        request["page_token"] = page_token
    return _snapshot_registry_json(
        source_kind="clinicaltrials_gov_v2_search",
        source_uri=url,
        request=request,
        raw_content=raw,
        content_type=content_type,
        retrieved_at=retrieved_at,
        unresolved_fields=unresolved_fields,
    )


def extract_protocol_pdf(
    raw_content: bytes,
    *,
    source_uri: str,
    nct_id: str | None = None,
    max_bytes: int = DEFAULT_PDF_MAX_BYTES,
    max_pages: int = DEFAULT_PDF_MAX_PAGES,
    max_text_chars: int = DEFAULT_PDF_MAX_TEXT_CHARS,
    max_page_text_chars: int = DEFAULT_PDF_MAX_PAGE_TEXT_CHARS,
    retrieved_at: str | None = None,
    unresolved_fields: Sequence[str] = DEFAULT_UNRESOLVED_FIELDS,
) -> IntakeSnapshot:
    """Extract bounded page text from immutable protocol-PDF bytes using pypdf."""

    _validate_https_url(source_uri, allowed_hosts=PROTOCOL_PDF_HOSTS, label="protocol PDF URL")
    for value, label in (
        (max_bytes, "max_bytes"),
        (max_pages, "max_pages"),
        (max_text_chars, "max_text_chars"),
        (max_page_text_chars, "max_page_text_chars"),
    ):
        _validate_positive_integer(value, label)
    if not isinstance(raw_content, bytes) or not raw_content:
        raise IntakeValidationError("Protocol PDF content must be non-empty immutable bytes")
    if len(raw_content) > max_bytes:
        raise IntakeLimitError(f"Protocol PDF exceeds the {max_bytes}-byte intake cap")
    if not raw_content.lstrip().startswith(b"%PDF-"):
        raise IntakeValidationError("Protocol source does not have a PDF signature")
    if nct_id is not None:
        validate_nct_id(nct_id)

    try:
        reader = PdfReader(BytesIO(raw_content), strict=True)
        if reader.is_encrypted:
            raise IntakeValidationError("Encrypted protocol PDFs require controlled human review")
        page_count = len(reader.pages)
    except IntakeError:
        raise
    except Exception as exc:
        raise IntakeValidationError(f"Protocol PDF could not be parsed: {exc}") from exc
    if page_count == 0:
        raise IntakeValidationError("Protocol PDF has no pages")
    if page_count > max_pages:
        raise IntakeLimitError(f"Protocol PDF exceeds the {max_pages}-page intake cap")

    pages: list[ExtractedPage] = []
    total_chars = 0
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise IntakeValidationError(f"Protocol PDF page {index} extraction failed: {exc}") from exc
        if not isinstance(text, str):
            raise IntakeValidationError(f"Protocol PDF page {index} returned non-text content")
        if len(text) > max_page_text_chars:
            raise IntakeLimitError(
                f"Protocol PDF page {index} exceeds the {max_page_text_chars}-character cap"
            )
        total_chars += len(text)
        if total_chars > max_text_chars:
            raise IntakeLimitError(
                f"Protocol PDF extracted text exceeds the {max_text_chars}-character cap"
            )
        pages.append(ExtractedPage(page_number=index, text=text))

    request: dict[str, Any] = {"document_type": "protocol_pdf"}
    if nct_id is not None:
        request["nct_id"] = nct_id
    return IntakeSnapshot(
        source_kind="clinicaltrials_gov_protocol_pdf",
        source_uri=source_uri,
        retrieved_at=retrieved_at or _now_utc(),
        request=request,
        raw_content=raw_content,
        source_locators=tuple(page.locator for page in pages),
        unresolved_fields=tuple(unresolved_fields),
        extracted_pages=tuple(pages),
    )


def snapshot_protocol_pdf(
    source_uri: str,
    *,
    nct_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_PDF_MAX_BYTES,
    max_pages: int = DEFAULT_PDF_MAX_PAGES,
    max_text_chars: int = DEFAULT_PDF_MAX_TEXT_CHARS,
    max_page_text_chars: int = DEFAULT_PDF_MAX_PAGE_TEXT_CHARS,
    opener: Callable[..., Any] | None = None,
    retrieved_at: str | None = None,
    unresolved_fields: Sequence[str] = DEFAULT_UNRESOLVED_FIELDS,
) -> IntakeSnapshot:
    """Fetch and extract a protocol PDF from the fixed ClinicalTrials.gov hosts."""

    source_uri = _validate_https_url(
        source_uri,
        allowed_hosts=PROTOCOL_PDF_HOSTS,
        label="protocol PDF URL",
    )
    raw, content_type = _fetch_bytes(
        source_uri,
        accept="application/pdf",
        max_bytes=max_bytes,
        timeout=timeout,
        allowed_hosts=PROTOCOL_PDF_HOSTS,
        opener=opener,
    )
    if content_type is not None and "pdf" not in content_type.lower():
        raise IntakeValidationError("Protocol response is not a PDF")
    return extract_protocol_pdf(
        raw,
        source_uri=source_uri,
        nct_id=nct_id,
        max_bytes=max_bytes,
        max_pages=max_pages,
        max_text_chars=max_text_chars,
        max_page_text_chars=max_page_text_chars,
        retrieved_at=retrieved_at,
        unresolved_fields=unresolved_fields,
    )


__all__ = [
    "CLINICALTRIALS_GOV_API_ROOT",
    "CLINICALTRIALS_GOV_HOST",
    "DEFAULT_JSON_MAX_BYTES",
    "DEFAULT_PDF_MAX_BYTES",
    "DEFAULT_PDF_MAX_PAGES",
    "DEFAULT_PDF_MAX_PAGE_TEXT_CHARS",
    "DEFAULT_PDF_MAX_TEXT_CHARS",
    "DEFAULT_UNRESOLVED_FIELDS",
    "ExtractedPage",
    "IntakeError",
    "IntakeFetchError",
    "IntakeLimitError",
    "IntakeSnapshot",
    "IntakeValidationError",
    "NCT_ID_PATTERN",
    "PROTOCOL_PDF_HOSTS",
    "SourceLocator",
    "clinicaltrials_search_url",
    "clinicaltrials_study_url",
    "extract_protocol_pdf",
    "iter_json_pointers",
    "snapshot_clinicaltrials_search",
    "snapshot_clinicaltrials_study",
    "snapshot_protocol_pdf",
    "validate_nct_id",
]
