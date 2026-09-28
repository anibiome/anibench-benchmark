"""Loopback-only, bounded-lifetime AniBench interface with no input persistence."""

from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

from .reference_planner import ASSETS, default_request, evaluate_plan, verify_reference

MAX_REQUEST_BYTES = 16_384
PUBLIC_ASSETS = {
    "index.html", "app.mjs", "style.css", "catalogue.json", "paper.md",
    "conditional_frontier.svg", "temporal_sampling.svg", "molecular_validation.svg",
    "pilot.mjs", "pilot.json", "pilot-bindings.json",
}


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON fields must be unique")
        result[key] = value
    return result


class WorkbenchHandler(BaseHTTPRequestHandler):
    """Serve an explicit safe asset set; never expose arbitrary local files."""

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_args: object) -> None:
        pass

    def _same_origin(self) -> bool:
        host = f"127.0.0.1:{self.server.server_port}"
        return (
            self.headers.get("Host") == host
            and self.headers.get("Origin", f"http://{host}") == f"http://{host}"
        )

    def _send(self, status: int, body: bytes, mime: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' blob:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        ))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._same_origin():
            return self._send(403, b'{"error":"Local origin required"}')
        route = urlsplit(self.path).path
        if route == "/api/defaults":
            return self._send(200, json.dumps(default_request(), allow_nan=False).encode())
        name = "index.html" if route == "/" else route.removeprefix("/")
        if name not in PUBLIC_ASSETS or not (ASSETS / name).is_file():
            return self._send(404, b'{"error":"Resource unavailable"}')
        mime = "text/javascript" if name.endswith(".mjs") else (
            mimetypes.guess_type(name)[0] or "application/octet-stream"
        )
        return self._send(200, (ASSETS / name).read_bytes(), mime)

    def do_POST(self) -> None:
        if self.path != "/api/plan" or not self._same_origin():
            return self._send(403, b'{"error":"Local planner endpoint required"}')
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_REQUEST_BYTES:
                raise ValueError("Design JSON must be between 1 byte and 16 KiB")
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Chunked requests are not supported")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Send an application/json design")
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError("Incomplete JSON request")
            payload = json.loads(raw, object_pairs_hook=_unique_object)
            result = evaluate_plan(payload)
            self._send(200, json.dumps(result, allow_nan=False, sort_keys=True).encode())
        except (ValueError, TypeError, KeyError, ArithmeticError, UnicodeError) as exc:
            # These are schema/reference messages. Raw request data is never logged.
            message = str(exc)
            if "Balancedtwoarm" in message:
                message = "Use an even number of people for two equally sized groups."
            self._send(400, json.dumps({"error": message}).encode())


def serve_workbench(port: int = 8795, ttl: int = 1800) -> None:
    """Start a local server; its automatic stop requires no browser interaction."""
    if type(ttl) is not int or not 1 <= ttl <= 3600:
        raise ValueError("Automatic stop must be between 1 and 3600 seconds")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Invalid local port")
    verify_reference()
    server = HTTPServer(("127.0.0.1", port), WorkbenchHandler)
    timer = threading.Timer(ttl, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f"AniBench: http://127.0.0.1:{server.server_port}/ (auto-stop in {ttl}s)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        server.server_close()
