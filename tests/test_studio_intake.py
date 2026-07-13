from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import anibench.studio as studio
from anibench.studio import StudioHandler


ROOT = Path(__file__).resolve().parents[1]


def _post(base_url: str, route: str, payload: dict[str, object]) -> tuple[int, dict]:
    request = Request(
        f"{base_url}{route}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _serve() -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}"


def test_studio_clinicaltrials_intake_routes_capture_only_source_snapshots(
    monkeypatch,
) -> None:
    calls: list[tuple] = []

    def fake_study(nct_id: str):
        calls.append(("study", nct_id))
        return SimpleNamespace(
            as_dict=lambda: {
                "schema_version": "anibench.intake-snapshot.v1",
                "source_kind": "clinicaltrials_gov_v2_study",
                "request": {"nct_id": nct_id},
                "raw_content_sha256": "a" * 64,
                "score_eligible": False,
                "requires_human_review": True,
                "promotion_state": "intake_only_unreviewed",
            }
        )

    def fake_search(query: str, *, page_size: int, page_token: str | None):
        calls.append(("search", query, page_size, page_token))
        return SimpleNamespace(
            as_dict=lambda: {
                "schema_version": "anibench.intake-snapshot.v1",
                "source_kind": "clinicaltrials_gov_v2_search",
                "request": {
                    "query": query,
                    "page_size": page_size,
                    "page_token": page_token,
                },
                "raw_content_sha256": "b" * 64,
                "parsed_content": {"studies": []},
                "score_eligible": False,
                "requires_human_review": True,
                "promotion_state": "intake_only_unreviewed",
            }
        )

    monkeypatch.setattr(studio, "snapshot_clinicaltrials_study", fake_study)
    monkeypatch.setattr(studio, "snapshot_clinicaltrials_search", fake_search)
    server, thread, base_url = _serve()
    try:
        status, study = _post(base_url, "/api/intake/ctgov", {"nct_id": "NCT01234567"})
        assert status == 200
        assert study["score_eligible"] is False
        assert study["requires_human_review"] is True

        status, search = _post(
            base_url,
            "/api/intake/ctgov-search",
            {"query": "healthy aging AND proteomics", "page_size": 25, "page_token": "next"},
        )
        assert status == 200
        assert search["score_eligible"] is False
        assert search["promotion_state"] == "intake_only_unreviewed"
        assert calls == [
            ("study", "NCT01234567"),
            ("search", "healthy aging AND proteomics", 25, "next"),
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_studio_clinicaltrials_search_rejects_invalid_queries_before_network() -> None:
    server, thread, base_url = _serve()
    try:
        status, payload = _post(
            base_url,
            "/api/intake/ctgov-search",
            {"query": "", "page_size": 10, "page_token": None},
        )
        assert status == 400
        assert "non-empty" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
