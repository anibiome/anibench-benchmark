from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import anibench

from anibench.studio import StudioHandler


ROOT = Path(__file__).resolve().parents[1]
WITHDRAWN_OPTIMIZER_MARKERS = (
    "anibench.optimizer-run.v2-candidate1",
    "anibench.optimizer-result.v2-candidate1",
    '"/api/v2/optimize"',
)
WITHDRAWN_CURRENT_ROUTES = ("/api/v2/benchmark-suite", "/api/simulate")


def _request(path: str, *, method: str = "GET") -> tuple[int, bytes]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}{path}",
            data=(b"{}" if method == "POST" else None),
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, exc.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_current_public_surfaces_do_not_expose_withdrawn_optimizer() -> None:
    assert not hasattr(anibench, "optimize_trial_design_v2")
    assert not hasattr(anibench, "replay_benchmark_suite_v2")
    current_surfaces = (
        ROOT / "src/anibench/api.py",
        ROOT / "src/anibench/cli.py",
        ROOT / "src/anibench/studio.py",
        ROOT / "openapi/anibench-v2-candidate.yaml",
        ROOT / "web/v2.html",
        ROOT / "web/v2.js",
    )
    for path in current_surfaces:
        text = path.read_text(encoding="utf-8")
        for marker in WITHDRAWN_OPTIMIZER_MARKERS:
            assert marker not in text, f"{marker!r} remains reachable through {path}"
    for path in (
        ROOT / "web/v2.html",
        ROOT / "web/v2.js",
        ROOT / "openapi/anibench-v2-candidate.yaml",
    ):
        text = path.read_text(encoding="utf-8")
        assert "/api/preview" not in text
        assert "/api/optimize" not in text
        for route in WITHDRAWN_CURRENT_ROUTES:
            if path.name != "studio.py":
                assert route not in text


def test_studio_root_serves_v2_and_legacy_rank_routes_are_gone() -> None:
    status, body = _request("/")
    assert status == 200
    assert b"AniBench v2" in body
    assert b"Legacy mixed-axis mean" not in body

    for route in ("/api/preview", "/api/optimize", "/api/v1/preview", "/v1/preview"):
        status, body = _request(route, method="POST")
        payload = json.loads(body)
        assert status == 410
        assert payload["contract"] == "anibench.retired-route.v1"
        assert payload["promotion_allowed"] is False

    status, body = _request("/api/v2/optimize", method="POST")
    assert status == 404
    assert json.loads(body)["error"] == "Unknown endpoint"

    for route in WITHDRAWN_CURRENT_ROUTES:
        status, body = _request(route, method="POST")
        payload = json.loads(body)
        assert status == 410
        assert payload["promotion_allowed"] is False
