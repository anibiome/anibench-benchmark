#!/usr/bin/env python3
"""Replay a frozen public registry corpus without exporting raw records or contacts."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from anibench.intake import (
    DEFAULT_UNRESOLVED_FIELDS,
    _snapshot_registry_json,
    snapshot_clinicaltrials_study,
)
from scripts.run_ctgov_50_stress_test import (
    _compiler_probe,
    extract_registry_record,
    sparse_design_input,
)

DATA = ROOT / "data/registry_stress_240"
MODES = ("missing_enrollment", "duplicate_interventions", "reverse_rows")


class AuditError(ValueError):
    """A safe error code, never a raw source excerpt or filesystem path."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if manifest.get("schema") != "anibench.registry-stress-240.manifest.v1":
        raise AuditError("manifest_schema")
    studies = manifest.get("studies", [])
    strata = {s["id"] for s in manifest["strata"]}
    ids = [s["nct_id"] for s in studies]
    if len(ids) != 240 or len(set(ids)) != 240 or manifest.get("expected_count") != 240:
        raise AuditError("manifest_identity_count")
    if len(strata) != 12 or collections.Counter(s["stratum_id"] for s in studies) != dict.fromkeys(
        strata, 20
    ):
        raise AuditError("manifest_strata")
    for item in studies:
        nct = item["nct_id"]
        if not re.fullmatch(r"NCT\d{8}", nct):
            raise AuditError("manifest_identity_format")
        if not re.fullmatch(r"[a-f0-9]{64}", item["raw_sha256"]):
            raise AuditError("manifest_source_hash")
        if item["source_uri"] != f"https://clinicaltrials.gov/api/v2/studies/{nct}":
            raise AuditError("manifest_source_uri")
        datetime.fromisoformat(item["retrieved_at"].replace("Z", "+00:00"))
    return manifest


def verify_code(manifest: dict) -> dict:
    hashes = {}
    for name, expected in manifest["source_code_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise AuditError("implementation_path")
        hashes[name] = digest(path.read_bytes())
        if hashes[name] != expected:
            raise AuditError("implementation_hash_mismatch")
    return hashes


def get_raw(item: dict, cache: Path, offline: bool) -> bytes:
    """Only cache bytes that exactly match the frozen identity and hash."""
    path = cache / f"{item['nct_id']}.json"
    if path.exists():
        raw = path.read_bytes()
    elif offline:
        raise AuditError("cache_missing")
    else:
        try:
            raw = snapshot_clinicaltrials_study(item["nct_id"], timeout=30).raw_content
        except Exception:  # noqa: BLE001 - public output must not expose source/error bodies
            raise AuditError("download_failed") from None
    if digest(raw) != item["raw_sha256"]:
        raise AuditError("source_hash_mismatch")
    if not path.exists():
        with path.open("xb") as handle:
            handle.write(raw)
    return raw


def evaluate(raw: bytes, item: dict) -> dict:
    def snapshot(body: bytes, derived: bool = False):
        return _snapshot_registry_json(
            source_kind="clinicaltrials_gov_v2_study",
            source_uri=item["source_uri"],
            request={"nct_id": item["nct_id"], "derived_test_only": derived},
            raw_content=body,
            content_type="application/json",
            retrieved_at=item["retrieved_at"],
            unresolved_fields=DEFAULT_UNRESOLVED_FIELDS,
        )

    if digest(raw) != item["raw_sha256"]:
        raise AuditError("source_hash_mismatch")
    record = extract_registry_record(snapshot(raw))
    if record["fields"]["nct_id"]["value"] != item["nct_id"]:
        raise AuditError("source_identity_mismatch")
    payload, mapping = sparse_design_input(record)
    base = _compiler_probe(payload)
    probes = {}
    nontrivial = {}
    for mode in MODES:
        document = json.loads(raw)
        protocol = document["protocolSection"]
        before = json.dumps(document, sort_keys=True)
        arms = protocol.get("armsInterventionsModule", {})
        if mode == "missing_enrollment":
            protocol.get("designModule", {}).pop("enrollmentInfo", None)
        elif mode == "duplicate_interventions":
            arms["interventions"] = arms.get("interventions", []) * 2
        else:
            for key in ("armGroups", "interventions"):
                if key in arms:
                    arms[key].reverse()
            for value in protocol.get("outcomesModule", {}).values():
                if isinstance(value, list):
                    value.reverse()
        nontrivial[mode] = json.dumps(document, sort_keys=True) != before
        derived = extract_registry_record(snapshot(json.dumps(document).encode(), True))
        dp, _ = sparse_design_input(derived)
        cp = _compiler_probe(dp)
        invariant = (
            dp["population"]["value"] is None and dp["population"]["state"] == "unknown"
            if mode == "missing_enrollment"
            else dp == payload
        )
        if mode == "reverse_rows":
            invariant &= (
                derived["fields"]["outcome_count"]["value"]
                == record["fields"]["outcome_count"]["value"]
            )
        probes[mode] = bool(invariant and cp["passed"] and not cp["promotion_allowed"])
    # Deliberate allowlist: no titles, source bodies, contacts, paths or exception text.
    return {
        "nct_id": item["nct_id"],
        "stratum_id": item["stratum_id"],
        "raw_sha256": item["raw_sha256"],
        "passed": bool(base["passed"] and all(probes.values())),
        "promotion_allowed": base["promotion_allowed"],
        "outcome_count": record["fields"]["outcome_count"]["value"],
        "outcome_state": record["fields"]["outcome_count"]["state"],
        "display_name_shortened": mapping["name"]["display_name_shortened"],
        "full_title_preserved": mapping["name"]["source_title"]
        == record["fields"]["brief_title"]["value"],
        "probes": probes,
        "nontrivial_probes": nontrivial,
    }


def summarize(
    rows: list[dict], failures: list[dict], manifest_hash: str, code: dict, offline: bool
) -> dict:
    return {
        "schema": "anibench.registry-stress-240.results.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_hash,
        "source_code_sha256": code,
        "network_enabled": not offline,
        "attempted": len(rows) + len(failures),
        "passed": sum(r["passed"] for r in rows),
        "failed": len(failures) + sum(not r["passed"] for r in rows),
        "failures": failures,
        "outcome_states": dict(collections.Counter(r["outcome_state"] for r in rows)),
        "shortened_display_names": sum(r["display_name_shortened"] for r in rows),
        "full_titles_preserved": bool(rows) and all(r["full_title_preserved"] for r in rows),
        "all_promotions_blocked": bool(rows) and all(not r["promotion_allowed"] for r in rows),
        "metamorphic_probes": {
            mode: {
                "executed": len(rows),
                "passed": sum(r["probes"][mode] for r in rows),
                "nontrivial_inputs": sum(r["nontrivial_probes"][mode] for r in rows),
            }
            for mode in MODES
        },
        "records": rows,
        "limitations": [
            "Query-selected registry ingestion, not representative clinical validation.",
            "Sparse geometry remains unresolved; no biological rank or saturation inference.",
            "Listed outcomes are not independent biological information.",
            "Derived probes may leave an already absent or empty structure unchanged; nontrivial counts are reported.",
            "No participant data, intervention execution or empirical calibration.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        required=True,
        help="Private local raw cache outside this repository",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="New sanitized JSON result file; never overwritten"
    )
    parser.add_argument(
        "--offline", action="store_true", help="Require all frozen bytes in cache; no network"
    )
    args = parser.parse_args(argv)
    try:
        if args.cache_dir.resolve().is_relative_to(ROOT):
            raise AuditError("raw_cache_must_be_outside_repository")
        if args.out.exists():
            raise AuditError("output_exists")
        manifest_path = DATA / "manifest.json"
        manifest = load_manifest(manifest_path)
        code = verify_code(manifest)
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        rows, failures = [], []
        for item in manifest["studies"]:
            try:
                rows.append(evaluate(get_raw(item, args.cache_dir, args.offline), item))
            except Exception as exc:  # noqa: BLE001 - sanitize every boundary failure
                # Do not include compiler/source error bodies in public output.
                reason = str(exc) if isinstance(exc, AuditError) else "parse_or_compiler_failure"
                failures.append({"nct_id": item["nct_id"], "reason_code": reason})
        report = summarize(rows, failures, digest(manifest_path.read_bytes()), code, args.offline)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        print(json.dumps({k: report[k] for k in ("attempted", "passed", "failed")}))
        return 0 if report["passed"] == 240 and report["failed"] == 0 else 1
    except Exception as exc:  # noqa: BLE001 - sanitize every boundary failure
        reason = str(exc) if isinstance(exc, AuditError) else "audit_setup_failure"
        print(json.dumps({"error_code": reason}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
