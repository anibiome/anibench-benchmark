from __future__ import annotations

import json
import ipaddress
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .paths import repo_root
from .design_v2 import compile_design
from .intake import snapshot_clinicaltrials_search, snapshot_clinicaltrials_study
from .level1_assessment_v3 import (
    Level1RoleAwareAssessmentError,
    assess_protocol_capacity_role_aware,
    level1_role_aware_authority_summary,
)
from .optimizer_protocol_v2 import ProtocolOptimizerError, optimize_protocol
from .protocol_capacity_v2 import ProtocolCapacityError, compile_protocol_capacity
from .studio_product import StudioAtlasError, build_studio_comparator_atlas
from .v2 import V2RunError, score_information_run
from . import __version__


class StudioInputError(ValueError):
    """Raised when a Studio transport or binding request is invalid."""


def _repo_root() -> Path:
    candidates = (
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parent,
        repo_root(),
    )
    for root in candidates:
        if root is not None and (root / "web" / "v2.html").exists():
            return root
    raise FileNotFoundError("AniBench web application is not installed")


class StudioHandler(BaseHTTPRequestHandler):
    server_version = f"AniBenchStudio/{__version__}"

    @property
    def root(self) -> Path:
        return self.server.root  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise StudioInputError("POST requests require Content-Type: application/json")
        origin = self.headers.get("Origin")
        if origin:
            parsed_origin = urlparse(origin)
            if parsed_origin.scheme not in {"http", "https"} or parsed_origin.hostname not in {
                "127.0.0.1",
                "localhost",
                "::1",
            }:
                raise StudioInputError("Cross-origin Studio requests are not allowed")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 8_000_000:
            raise StudioInputError("Request body must be a JSON object under 8 MB")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StudioInputError(f"Invalid JSON request: {exc}") from exc
        if not isinstance(payload, dict):
            raise StudioInputError("Request body must be a JSON object")
        return payload

    def _security_headers(self) -> None:
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")

    def do_POST(self) -> None:  # noqa: N802
        try:
            retired_routes = {
                "/api/preview": ("legacy scalar and rank route retired", "/v2.html"),
                "/api/optimize": ("legacy scalar and rank route retired", "/v2.html"),
                "/api/v1/preview": ("legacy scalar and rank route retired", "/v2.html"),
                "/api/v1/optimize": ("legacy scalar and rank route retired", "/v2.html"),
                "/v1/preview": ("legacy scalar and rank route retired", "/v2.html"),
                "/v1/optimize": ("legacy scalar and rank route retired", "/v2.html"),
                "/api/v2/benchmark-suite": (
                    "legacy three-family replay route retired",
                    "/api/v2/protocol-capacity",
                ),
                "/api/simulate": (
                    "unversioned shadow capacity simulation retired",
                    "/api/v2/protocol-capacity",
                ),
            }
            if self.path in retired_routes:
                error, replacement = retired_routes[self.path]
                self._json(
                    HTTPStatus.GONE,
                    {
                        "contract": "anibench.retired-route.v1",
                        "error": error,
                        "route": self.path,
                        "replacement": replacement,
                        "promotion_allowed": False,
                    },
                )
                return
            payload = self._read_json()
            if self.path == "/api/intake/ctgov":
                nct_id = payload.get("nct_id")
                if not isinstance(nct_id, str):
                    raise StudioInputError("nct_id is required")
                self._json(HTTPStatus.OK, snapshot_clinicaltrials_study(nct_id).as_dict())
                return
            if self.path == "/api/intake/ctgov-search":
                query = payload.get("query")
                page_size = payload.get("page_size", 10)
                page_token = payload.get("page_token")
                if not isinstance(query, str):
                    raise StudioInputError("query is required")
                self._json(
                    HTTPStatus.OK,
                    snapshot_clinicaltrials_search(
                        query,
                        page_size=page_size,
                        page_token=page_token,
                    ).as_dict(),
                )
                return
            if self.path == "/api/v2/information":
                self._json(HTTPStatus.OK, score_information_run(payload))
                return
            if self.path == "/api/v2/design":
                self._json(HTTPStatus.OK, compile_design(payload))
                return
            if self.path == "/api/v2/protocol-capacity":
                self._json(HTTPStatus.OK, compile_protocol_capacity(payload))
                return
            if self.path == "/api/v2/level1-assessment":
                self._json(HTTPStatus.OK, assess_protocol_capacity_role_aware(payload))
                return
            if self.path == "/api/v2/optimize-protocol":
                self._json(HTTPStatus.OK, optimize_protocol(payload))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
        except (
            ProtocolCapacityError,
            Level1RoleAwareAssessmentError,
            ProtocolOptimizerError,
            StudioInputError,
            V2RunError,
            ValueError,
        ) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "anibench-studio",
                    "version": __version__,
                },
            )
            return
        if parsed.path == "/api/v2/comparator-atlas":
            try:
                self._json(HTTPStatus.OK, build_studio_comparator_atlas(self.root))
            except StudioAtlasError as exc:
                self._json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "schema_version": "anibench.studio-comparator-atlas-error.v1",
                        "error": str(exc),
                        "overall_scalar": None,
                        "public_rank_emission_permitted": False,
                    },
                )
            return
        if parsed.path == "/api/v2/level1-authority":
            try:
                self._json(HTTPStatus.OK, level1_role_aware_authority_summary())
            except Level1RoleAwareAssessmentError as exc:
                self._json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "schema_version": "anibench.level1-authority-error.v1",
                        "error": str(exc),
                        "promotion_allowed": False,
                    },
                )
            return
        if parsed.path == "/api/v2/level1-template":
            self._json(
                HTTPStatus.GONE,
                {
                    "contract": "anibench.retired-route.v1",
                    "error": "the recursive v2 perfect-protocol template is superseded",
                    "route": parsed.path,
                    "replacement": "/api/v2/level1-authority",
                    "promotion_allowed": False,
                },
            )
            return
        relative = unquote(parsed.path).lstrip("/") or "v2.html"
        target = self.root / "web" / relative
        try:
            target = target.resolve()
            allowed = (self.root / "web").resolve()
            if allowed not in target.parents and target != allowed:
                raise FileNotFoundError
            if not target.is_file():
                raise FileNotFoundError
            body = target.read_bytes()
        except (OSError, FileNotFoundError):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)


def serve_studio(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    unsafe_nonloopback: bool = False,
) -> None:
    try:
        is_loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback and not unsafe_nonloopback:
        raise StudioInputError(
            "AniBench Studio refuses non-loopback binding; use --unsafe-nonloopback only for an isolated development environment"
        )
    root = _repo_root()
    server = ThreadingHTTPServer((host, port), StudioHandler)
    server.root = root  # type: ignore[attr-defined]
    print(f"AniBench Studio: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
