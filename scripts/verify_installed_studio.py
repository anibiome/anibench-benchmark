#!/usr/bin/env python3
"""Exercise the Studio from exact unpacked wheel bytes and a real browser."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BROWSER_SCRIPT = ROOT / "scripts" / "verify_studio_browser.mjs"
SECURITY_HEADERS = {
    "content-security-policy",
    "referrer-policy",
    "x-content-type-options",
    "x-frame-options",
}
RETIRED_ROUTES = (
    "/api/preview",
    "/api/optimize",
    "/api/v1/preview",
    "/api/v1/optimize",
    "/v1/preview",
    "/v1/optimize",
    "/api/v2/benchmark-suite",
    "/api/simulate",
)


class StudioGateError(RuntimeError):
    """Raised when exact installed Studio behavior violates the release contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _request(
    base_url: str,
    route: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 30,
) -> tuple[int, dict[str, str], bytes]:
    body = None if payload is None else json.dumps(payload, sort_keys=True).encode("utf-8")
    request = Request(
        f"{base_url}{route}",
        data=body,
        headers={} if body is None else {"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
            )
    except HTTPError as exc:
        return (
            exc.code,
            {key.lower(): value for key, value in exc.headers.items()},
            exc.read(),
        )


def _json_body(body: bytes, *, route: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StudioGateError(f"{route} did not return valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise StudioGateError(f"{route} did not return one JSON object")
    return payload


def _wait_for_health(base_url: str, process: subprocess.Popen[str], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=5)
            raise StudioGateError(
                f"Installed Studio exited before health check: {stderr or stdout or process.returncode}"
            )
        try:
            status, _, body = _request(base_url, "/api/health", timeout=2)
            if status == 200 and _json_body(body, route="/api/health").get("status") == "ok":
                return
        except (OSError, URLError, StudioGateError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise StudioGateError(f"Timed out waiting for installed Studio: {last_error}")


def _deep_personalized_design(assessment_lane: str) -> dict[str, Any]:
    """Return one deliberately large typed design used by both installed gates."""

    return {
        "contract": "anibench.design-input.v2-candidate1",
        "assessment_lane": assessment_lane,
        "study_id": "future-10m-personalized-trial",
        "name": "Ten-million-person deep adaptive trial",
        "population": {
            "value": 10_000_000,
            "state": "conditional",
            "semantics": "planned_enrollment",
        },
        "duration": {
            "value": 3_650,
            "state": "conditional",
            "semantics": "intervention_duration_days",
        },
        "policy_arms": 8,
        "randomized_policy": True,
        "concurrent_control": True,
        "adaptive_reassignment": True,
        "within_policy_randomized": True,
        "operator_families": ["nutrition", "exercise", "sleep", "combination"],
        "measurement_modules": [
            {
                "module_id": "multi-omics",
                "label": "Multi-omics",
                "evidence_state": "conditional",
                "events_per_participant": 3_650,
            },
            {
                "module_id": "digital-phenotyping",
                "label": "Digital phenotyping",
                "evidence_state": "conditional",
                "events_per_participant": 36_500,
            },
            {
                "module_id": "functional-perturbation",
                "label": "Functional perturbation",
                "evidence_state": "conditional",
                "events_per_participant": 332_150,
            },
        ],
    }


def _verify_http(base_url: str) -> dict[str, Any]:
    checks: list[str] = []

    status, headers, root_body = _request(base_url, "/")
    if (
        status != 200
        or b"AniBench" not in root_body
        or b'id="capacity-form"' not in root_body
        or b'id="ctgov-search-form"' not in root_body
        or b'id="ctgov-intake-form"' not in root_body
    ):
        raise StudioGateError("GET / did not serve the v2 Studio HTML")
    if not SECURITY_HEADERS <= set(headers):
        raise StudioGateError("GET / omitted required browser security headers")
    if "text/html" not in headers.get("content-type", ""):
        raise StudioGateError("GET / did not identify HTML content")
    checks.append("root_html_and_security_headers")

    assets = {
        "/v2.html": ("text/html", b'id="ctgov-search-form"'),
        "/v2.js": ("javascript", b"/api/v2/protocol-capacity"),
        "/v2.css": ("text/css", b"@media(max-width:780px)"),
        "/favicon.svg": ("image/svg+xml", b"<svg"),
    }
    for route, (content_type, marker) in assets.items():
        asset_status, asset_headers, asset_body = _request(base_url, route)
        if asset_status != 200 or marker not in asset_body:
            raise StudioGateError(f"{route} did not serve the packaged asset")
        if content_type not in asset_headers.get("content-type", ""):
            raise StudioGateError(f"{route} returned the wrong content type")
    checks.append("packaged_html_js_css_svg")

    status, _, health_body = _request(base_url, "/api/health")
    health = _json_body(health_body, route="/api/health")
    if status != 200 or health.get("status") != "ok" or health.get("service") != "anibench-studio":
        raise StudioGateError("Studio health contract failed")
    checks.append("health_get")

    planned_request = _deep_personalized_design("design_preview")
    status, _, planned_body = _request(
        base_url, "/api/v2/design", payload=planned_request, timeout=30
    )
    planned = _json_body(planned_body, route="/api/v2/design")
    realized_request = _deep_personalized_design("realized")
    realized_status, _, realized_body = _request(
        base_url, "/api/v2/design", payload=realized_request, timeout=30
    )
    realized = _json_body(realized_body, route="/api/v2/design")
    expected_observations = 3_723_000_000_000
    if (
        status != 200
        or realized_status != 200
        or planned.get("contract") != "anibench.design-assessment.v2-candidate1"
        or realized.get("contract") != "anibench.design-assessment.v2-candidate1"
        or planned.get("study", {}).get("study_id") != planned_request["study_id"]
        or planned.get("assessment_lane", {}).get("value") != "design_preview"
        or realized.get("assessment_lane", {}).get("value") != "realized"
        or planned.get("coordinates", {}).get("population", {}).get("value") != 10_000_000
        or planned.get("derived_coordinates", {})
        .get("participant_module_observation_total", {})
        .get("value")
        != expected_observations
        or planned.get("coordinates") != realized.get("coordinates")
        or planned.get("derived_coordinates") != realized.get("derived_coordinates")
        or planned.get("input_sha256") == realized.get("input_sha256")
    ):
        raise StudioGateError(
            "Primary design POST failed the 10M planned-design or evidence-lane invariance contract"
        )
    checks.append("primary_design_post_10m_and_lane_invariance")

    status, _, atlas_body = _request(base_url, "/api/v2/comparator-atlas")
    atlas = _json_body(atlas_body, route="/api/v2/comparator-atlas")
    if (
        status != 200
        or atlas.get("schema_version") != "anibench.studio-comparator-atlas.v1"
        or atlas.get("study_count") != 16
        or atlas.get("comparison_eligible_study_count") != 0
        or atlas.get("overall_scalar") is not None
        or atlas.get("public_rank_emission_permitted") is not False
    ):
        raise StudioGateError("Comparator atlas GET violated the score-free source contract")
    checks.append("comparator_atlas_get")

    examples: dict[str, dict[str, Any]] = {}
    for route in ("/protocol-capacity-example.json", "/optimizer-protocol-example.json"):
        example_status, example_headers, example_body = _request(base_url, route)
        if example_status != 200 or "application/json" not in example_headers.get(
            "content-type", ""
        ):
            raise StudioGateError(f"{route} was not served as packaged JSON")
        examples[route] = _json_body(example_body, route=route)
    if not str(examples["/protocol-capacity-example.json"].get("schema_version", "")).startswith(
        "anibench.protocol-capacity-input."
    ):
        raise StudioGateError("Protocol example has the wrong contract")
    if not str(examples["/optimizer-protocol-example.json"].get("schema_version", "")).startswith(
        "anibench.optimizer-protocol-input."
    ):
        raise StudioGateError("Optimizer example has the wrong contract")
    checks.append("packaged_example_gets")

    protocol = examples["/protocol-capacity-example.json"]
    status, _, capacity_body = _request(
        base_url, "/api/v2/protocol-capacity", payload=protocol, timeout=45
    )
    capacity = _json_body(capacity_body, route="/api/v2/protocol-capacity")
    if (
        status != 200
        or capacity.get("protocol_id") != protocol.get("protocol_id")
        or capacity.get("scenario_count", 0) < 1
        or capacity.get("overall_scalar") is not None
        or capacity.get("public_rank_emission_permitted") is not False
        or not capacity.get("scenarios")
        or not {
            "intensive",
            "extensive",
            "longitudinal",
            "causal",
            "personalized_sequential",
            "transport",
        }.issubset(set(capacity["scenarios"][0].get("families", {})))
    ):
        raise StudioGateError("Protocol-capacity POST failed its six-family contract")
    checks.append("protocol_capacity_post")

    authority_status, authority_headers, authority_body = _request(
        base_url, "/api/v2/level1-authority", timeout=60
    )
    level1_authority = _json_body(authority_body, route="/api/v2/level1-authority")
    if (
        authority_status != 200
        or "application/json" not in authority_headers.get("content-type", "")
        or level1_authority.get("schema_version")
        != "anibench.level1-role-aware-authority-summary.v1"
        or level1_authority.get("promotion_allowed") is not False
        or level1_authority.get("readback", {}).get("validation", {}).get("family_count") != 6
        or level1_authority.get("readback", {}).get("validation", {}).get(
            "direct_mutable_outcome_count"
        )
        != 22
    ):
        raise StudioGateError("Level-1 authority GET failed its role-aware contract")
    checks.append("level1_role_aware_authority_get")

    retired_status, _, retired_body = _request(
        base_url, "/api/v2/level1-template", timeout=60
    )
    retired = _json_body(retired_body, route="/api/v2/level1-template")
    if retired_status != 410 or retired.get("replacement") != "/api/v2/level1-authority":
        raise StudioGateError("recursive v2 Level-1 template was not retired")
    checks.append("recursive_level1_template_retired")

    level1_status, _, level1_body = _request(
        base_url,
        "/api/v2/level1-assessment",
        payload=protocol,
        timeout=90,
    )
    level1 = _json_body(level1_body, route="/api/v2/level1-assessment")
    replay_status, _, replay_body = _request(
        base_url,
        "/api/v2/level1-assessment",
        payload=protocol,
        timeout=90,
    )
    scenario = (level1.get("scenarios") or [{}])[0]
    families = scenario.get("families", [])
    family_ids = [row.get("family_id") for row in families]
    level1_text = json.dumps(level1, sort_keys=True)
    if (
        level1_status != 200
        or replay_status != 200
        or level1_body != replay_body
        or level1.get("schema_version")
        != "anibench.level1-role-aware-assessment.v3-candidate1"
        or level1.get("comparison_eligible") is not False
        or level1.get("promotion_allowed") is not False
        or level1.get("overall_scalar") is not None
        or level1.get("public_rank_emission_permitted") is not False
        or family_ids
        != [
            "intensive",
            "extensive",
            "longitudinal",
            "causal",
            "personalized_sequential",
            "transport",
        ]
        or not all(
            row.get("level1_target_attainment", {}).get("state") == "unresolved"
            and row.get("level1_target_attainment", {}).get("value") is None
            and row.get("native_metrics")
            and all(
                metric.get("source_object_sha256")
                == level1.get("protocol_capacity_result_sha256")
                and str(metric.get("source_locator", "")).startswith("/scenarios/")
                for metric in row["native_metrics"]
            )
            for row in families
        )
        or "level1_target_percent" in level1_text
        or "level1_uncapped_ratio" in level1_text
        or "target_total_enrollment" in level1_text
    ):
        raise StudioGateError(
            "Level-1 assessment POST failed role-aware family, typed-unknown, source locator, or deterministic replay contract"
        )
    checks.append("level1_assessment_post_and_deterministic_receipt")

    intake_holds = (
        (
            "/api/intake/ctgov",
            {"nct_id": "not-an-nct-id"},
            "must match",
        ),
        (
            "/api/intake/ctgov-search",
            {"query": "", "page_size": 10, "page_token": None},
            "non-empty",
        ),
    )
    for route, payload, marker in intake_holds:
        intake_status, _, intake_body = _request(base_url, route, payload=payload)
        intake = _json_body(intake_body, route=route)
        if intake_status != 400 or marker not in str(intake.get("error", "")):
            raise StudioGateError(f"{route} did not expose the fail-closed intake contract")
    checks.append("clinicaltrials_registry_intake_routes_fail_closed_without_network")

    optimizer_request = examples["/optimizer-protocol-example.json"]
    optimizer_request["base_protocol"] = protocol
    status, _, optimizer_body = _request(
        base_url, "/api/v2/optimize-protocol", payload=optimizer_request, timeout=45
    )
    optimizer = _json_body(optimizer_body, route="/api/v2/optimize-protocol")
    if (
        status != 200
        or optimizer.get("candidate_count", 0) < 1
        or optimizer.get("feasible_candidate_count", 0) < 1
        or optimizer.get("overall_scalar") is not None
        or optimizer.get("public_rank_emission_permitted") is not False
        or not optimizer.get("pareto_frontier_candidate_ids")
    ):
        raise StudioGateError("Protocol optimizer POST failed its Pareto contract")
    checks.append("protocol_optimizer_post")

    for route in RETIRED_ROUTES:
        retired_status, _, retired_body = _request(base_url, route, payload={})
        retired = _json_body(retired_body, route=route)
        if (
            retired_status != 410
            or retired.get("contract") != "anibench.retired-route.v1"
            or retired.get("route") != route
            or retired.get("promotion_allowed") is not False
        ):
            raise StudioGateError(f"Retired route did not fail closed: {route}")
    checks.append("all_retired_post_routes")

    missing_status, _, _ = _request(base_url, "/definitely-not-installed.html")
    if missing_status != 404:
        raise StudioGateError("Unknown static route did not return 404")
    traversal_status, _, _ = _request(base_url, "/..%2Fpyproject.toml")
    if traversal_status != 404:
        raise StudioGateError("Static path traversal did not return 404")
    checks.append("static_404_and_path_traversal")

    return {
        "passed": True,
        "checks": checks,
        "health": health,
        "planned_design_input_sha256": planned["input_sha256"],
        "realized_design_input_sha256": realized["input_sha256"],
        "planned_design_population": planned["coordinates"]["population"]["value"],
        "planned_design_participant_module_observations": expected_observations,
        "planned_realized_geometry_equal": True,
        "comparator_study_count": atlas["study_count"],
        "capacity_protocol_sha256": capacity["protocol_sha256"],
        "capacity_scenario_count": capacity["scenario_count"],
        "level1_assessment_receipt_sha256": level1["assessment_receipt_sha256"],
        "level1_authority_sha256": level1["level1_authority"]["authority_raw_sha256"],
        "level1_family_count": len(families),
        "level1_target_state": "unresolved",
        "level1_overall_scalar": None,
        "level1_receipt_replay_equal": True,
        "optimizer_request_sha256": optimizer["optimizer_request_sha256"],
        "optimizer_candidate_count": optimizer["candidate_count"],
    }


def verify_installed_studio(
    wheel: Path,
    *,
    node: str = "node",
    browser_script: Path = BROWSER_SCRIPT,
    browser_binary: str | None = None,
    require_browser: bool = True,
) -> dict[str, Any]:
    wheel = wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise StudioGateError(f"Wheel does not exist: {wheel}")
    if require_browser and not browser_script.is_file():
        raise StudioGateError(f"Browser gate script does not exist: {browser_script}")

    with tempfile.TemporaryDirectory(prefix="anibench-installed-studio-") as temporary:
        temporary_root = Path(temporary)
        installed = temporary_root / "installed"
        installed.mkdir()
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise StudioGateError(f"Unsafe wheel member path: {member.filename}")
            archive.extractall(installed)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(installed)
        environment["PYTHONNOUSERSITE"] = "1"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        module_check = subprocess.run(
            [sys.executable, "-c", "import anibench; print(anibench.__file__)"],
            cwd=temporary_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if module_check.returncode != 0:
            raise StudioGateError(module_check.stderr or module_check.stdout)
        module_path = Path(module_check.stdout.strip()).resolve()
        if not module_path.is_relative_to(installed.resolve()):
            raise StudioGateError(f"Runtime imported outside unpacked wheel: {module_path}")

        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "anibench.cli",
                "studio",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=temporary_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_health(base_url, server)
            http_receipt = _verify_http(base_url)
            browser_receipt: dict[str, Any] | None = None
            if require_browser:
                downloads = temporary_root / "downloads"
                command = [
                    node,
                    str(browser_script),
                    "--url",
                    base_url,
                    "--downloads-dir",
                    str(downloads),
                ]
                if browser_binary:
                    command.extend(["--browser-binary", browser_binary])
                browser = subprocess.run(
                    command,
                    cwd=temporary_root,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if browser.returncode != 0:
                    raise StudioGateError(browser.stderr or browser.stdout)
                try:
                    browser_receipt = json.loads(browser.stdout)
                except json.JSONDecodeError as exc:
                    raise StudioGateError(
                        f"Browser gate did not emit one JSON receipt: {browser.stdout}"
                    ) from exc
                if browser_receipt.get("passed") is not True:
                    raise StudioGateError("Browser gate receipt did not pass")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    return {
        "contract": "anibench.installed-studio-e2e-gate.v1",
        "passed": True,
        "wheel": {"name": wheel.name, "sha256": _sha256(wheel)},
        "runtime": {
            "installation_mode": "wheel_archive_unpacked_outside_source_checkout",
            "module_path_relative": module_path.relative_to(installed.resolve()).as_posix(),
            "loopback_binding": True,
        },
        "http": http_receipt,
        "browser": browser_receipt,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the exact AniBench wheel Studio over HTTP and in headless Chrome"
    )
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--node", default="node")
    parser.add_argument("--browser-script", default=BROWSER_SCRIPT, type=Path)
    parser.add_argument("--browser-binary")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = verify_installed_studio(
            args.wheel,
            node=args.node,
            browser_script=args.browser_script,
            browser_binary=args.browser_binary,
        )
    except (OSError, StudioGateError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rendered = json.dumps(receipt, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
