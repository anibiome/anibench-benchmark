"""Portable reference integrity, HTTP isolation, and reproducible CLI behavior."""

import copy
import hashlib
import http.client
import json
import subprocess
import sys
import threading
from http.server import HTTPServer

import pytest

from anibench.cli import main
from anibench.reference_planner import default_request, evaluate_plan
from anibench.workbench import WorkbenchHandler


@pytest.fixture(scope="module")
def evaluated():
    request = default_request()
    return request, evaluate_plan(request)


def test_repeatable_without_input_mutation(evaluated):
    request, result = evaluated
    original = copy.deepcopy(request)
    assert evaluate_plan(request) == result
    assert request == original
    assert result["results"]["baseline"]["result"]["level_attainment"] == "not_attained"
    assert result["results"]["changed"]["design"]["paired_endpoints"] is True


def test_reference_tampering_rejected_even_after_cache_load(tmp_path, monkeypatch):
    import anibench.reference_planner as planner

    planner.default_request()
    changed = tmp_path / "replay.py"
    changed.write_bytes(planner.REFERENCE.read_bytes() + b"\n# changed\n")
    monkeypatch.setattr(planner, "REFERENCE", changed)
    with pytest.raises(ValueError, match="reviewed version"):
        planner.default_request()


@pytest.mark.parametrize("change", [
    {"N": 3}, {"N": True}, {"repeat_rho": float("nan")},
    {"controlled": "false"}, {"only_questions": ["invented"]},
])
def test_invalid_geometry_never_returns_a_score(change):
    request = default_request()
    request["changed"].update(change)
    with pytest.raises(ValueError):
        evaluate_plan(request)


def test_cli_preserves_existing_result_and_input(tmp_path, evaluated, capsys):
    request, expected = evaluated
    source, output = tmp_path / "design.json", tmp_path / "result.json"
    source.write_text(json.dumps(request))
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert main(["plan", str(source), "--out", str(output)]) == 0
    assert json.loads(output.read_text()) == expected
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    assert main(["plan", str(source), "--out", str(output)]) != 0
    assert hashlib.sha256(output.read_bytes()).hexdigest() == output_hash
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert main(["plan", str(source), "--out", str(source)]) != 0


def test_http_origin_allowlist_and_actual_evaluator(evaluated):
    server = HTTPServer(("127.0.0.1", 0), WorkbenchHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def request(method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=20)
        try:
            conn.request(method, path, body, headers or {})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    try:
        status, headers, _ = request("GET", "/")
        assert status == 200
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        for path in ["/../pyproject.toml", "/reference/v0.4/replay.py", "/.git/config"]:
            assert request("GET", path)[0] == 404
        assert request("GET", "/api/defaults", headers={"Host": "external.example"})[0] == 403
        assert request("GET", "/api/defaults", headers={"Origin": "https://external.example"})[0] == 403
        source, expected = evaluated
        status, _, body = request("POST", "/api/plan", json.dumps(source), {"Content-Type": "application/json"})
        assert status == 200
        assert json.loads(body) == expected
        for payload, content_type in [('{}', 'text/plain'), ('{"level":1,"level":2}', 'application/json'), ('x'*16385, 'application/json')]:
            assert request("POST", "/api/plan", payload, {"Content-Type": content_type})[0] == 400
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


def test_server_stops_without_browser():
    process = subprocess.Popen(
        [sys.executable, "-m", "anibench.cli", "workbench", "--port", "0", "--ttl", "1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr
        assert "http://127.0.0.1:" in stdout
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
