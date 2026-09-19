from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest

from scripts import run_registry_stress_240 as audit
from tests.test_ctgov_50_stress_test import _study


def fixture():
    raw = json.dumps(_study()).encode()
    item = {
        "nct_id": "NCT01234567",
        "stratum_id": "fixture",
        "raw_sha256": audit.digest(raw),
        "source_uri": "https://clinicaltrials.gov/api/v2/studies/NCT01234567",
        "retrieved_at": "2026-09-19T00:00:00Z",
    }
    return raw, item


def test_frozen_identity_provenance_and_aggregate_correspondence():
    manifest = audit.load_manifest(audit.DATA / "manifest.json")
    baseline = json.loads((audit.DATA / "baseline.json").read_text())
    report = json.loads((audit.DATA / "postfix.json").read_text())
    assert (
        audit.digest((audit.DATA / "preregistration.json").read_bytes())
        == manifest["preregistration_sha256"]
    )
    assert report["manifest_sha256"] == audit.digest((audit.DATA / "manifest.json").read_bytes())
    assert baseline["selected"] == 240 and baseline["passed"] == 239
    assert baseline["processing_failures"] == [
        {"nct_id": "NCT00489970", "reason_code": "display_name_schema_length"}
    ]
    ids = {r["nct_id"] for r in manifest["studies"]}
    assert ids == {r["nct_id"] for r in report["records"]}
    assert len(report["records"]) == report["passed"] == report["attempted"] == 240
    assert report["failed"] == 0
    assert (
        sum(r["outcome_state"] == "exact" for r in report["records"])
        == report["outcome_states"]["exact"]
        == 234
    )
    assert sum(r["outcome_state"] == "unknown" for r in report["records"]) == 6
    for mode in audit.MODES:
        assert (
            sum(r["probes"][mode] for r in report["records"])
            == report["metamorphic_probes"][mode]["passed"]
            == 240
        )
    source = {r["nct_id"]: r for r in manifest["studies"]}
    for row in report["records"]:
        assert row["raw_sha256"] == source[row["nct_id"]]["raw_sha256"]
        assert row["stratum_id"] == source[row["nct_id"]]["stratum_id"]
        assert row["promotion_allowed"] is False


def test_manifest_rejects_duplicate_identity_and_external_uri(tmp_path):
    source = json.loads((audit.DATA / "manifest.json").read_text())
    for field, value in [
        ("nct_id", source["studies"][1]["nct_id"]),
        ("source_uri", "https://example.com/unsafe"),
    ]:
        manifest = copy.deepcopy(source)
        manifest["studies"][0][field] = value
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(manifest))
        with pytest.raises(audit.AuditError):
            audit.load_manifest(path)


def test_offline_cache_hash_gate_and_no_replacement(tmp_path, monkeypatch):
    raw, item = fixture()
    monkeypatch.setattr(
        audit, "snapshot_clinicaltrials_study", lambda *a, **k: pytest.fail("network")
    )
    with pytest.raises(audit.AuditError, match="cache_missing"):
        audit.get_raw(item, tmp_path, True)
    p = tmp_path / f"{item['nct_id']}.json"
    p.write_bytes(b"stale")
    with pytest.raises(audit.AuditError, match="source_hash_mismatch"):
        audit.get_raw(item, tmp_path, True)
    assert p.read_bytes() == b"stale"
    p.write_bytes(raw)
    assert audit.get_raw(item, tmp_path, True) == raw


def test_online_changed_snapshot_is_not_saved(tmp_path, monkeypatch):
    _, item = fixture()

    class Snapshot:
        raw_content = b"changed registry response"

    monkeypatch.setattr(audit, "snapshot_clinicaltrials_study", lambda *a, **k: Snapshot())
    with pytest.raises(audit.AuditError, match="source_hash_mismatch"):
        audit.get_raw(item, tmp_path, False)
    assert list(tmp_path.iterdir()) == []


def test_executed_probes_and_public_output_allowlist():
    raw, item = fixture()
    row = audit.evaluate(raw, item)
    assert row["passed"] and all(row["probes"].values())
    assert row["outcome_count"] == 1 and row["outcome_state"] == "exact"
    assert row["promotion_allowed"] is False
    text = json.dumps(row)
    assert "Fixture trial" not in text and "Intervention that" not in text
    assert set(row) == {
        "nct_id",
        "stratum_id",
        "raw_sha256",
        "passed",
        "promotion_allowed",
        "outcome_count",
        "outcome_state",
        "display_name_shortened",
        "full_title_preserved",
        "probes",
        "nontrivial_probes",
    }
    report = audit.summarize([row], [], "a" * 64, {}, True)
    assert report["passed"] == 1 and report["failed"] == 0
    assert report["metamorphic_probes"]["missing_enrollment"]["passed"] == 1


def test_cli_help_and_no_overwrite(tmp_path):
    script = audit.ROOT / "scripts/run_registry_stress_240.py"
    help_run = subprocess.run(
        [sys.executable, str(script), "--help"], capture_output=True, text=True, check=False
    )
    assert help_run.returncode == 0 and "--offline" in help_run.stdout
    output = tmp_path / "output.json"
    output.write_text("preserve")
    run = subprocess.run(
        [
            sys.executable,
            str(script),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--out",
            str(output),
            "--offline",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 2 and "output_exists" in run.stderr
    assert str(tmp_path) not in run.stderr and output.read_text() == "preserve"


def test_public_artifacts_do_not_export_paths_contacts_or_source_titles():
    for path in audit.DATA.glob("*.json"):
        text = path.read_text()
        assert "/Users/" not in text and "@" not in text
        assert '"contacts"' not in text and '"briefTitle"' not in text


def test_manifest_json_schema():
    from jsonschema import Draft202012Validator, FormatChecker

    schema = json.loads((audit.DATA / "manifest.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    manifest = json.loads((audit.DATA / "manifest.json").read_text())
    validator.validate(manifest)
    manifest["studies"][0]["raw_sha256"] = "not-a-hash"
    assert list(validator.iter_errors(manifest))


def test_public_data_checksums_and_portable_runner_receipt():
    for line in (audit.DATA / "SHA256SUMS").read_text().splitlines():
        checksum, name = line.split()
        assert audit.digest((audit.DATA / name).read_bytes()) == checksum
    receipt = json.loads((audit.DATA / "portable-verification.json").read_text())
    assert receipt["portable_runner_sha256"] == audit.digest(
        (audit.ROOT / "scripts/run_registry_stress_240.py").read_bytes()
    )
    assert receipt["all240_historical_record_fields_match"] is True
    assert receipt["passed"] == 240 and receipt["failed"] == 0
