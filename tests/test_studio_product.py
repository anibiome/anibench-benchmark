from __future__ import annotations

import csv
import hashlib
import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from anibench.studio import StudioHandler
from anibench.studio_product import (
    FAMILY_IDS,
    SOURCE_COORDINATE_CONTRACT,
    StudioAtlasError,
    build_studio_comparator_atlas,
)


ROOT = Path(__file__).resolve().parents[1]


def test_studio_comparator_atlas_is_hash_verified_external_corpus_not_rank() -> None:
    atlas = build_studio_comparator_atlas(ROOT)
    assert atlas == build_studio_comparator_atlas(ROOT)
    assert atlas["schema_version"] == "anibench.studio-comparator-atlas.v1"
    assert atlas["study_count"] == 16
    assert atlas["comparison_eligible_study_count"] == 0
    assert atlas["overall_scalar"] is None
    assert atlas["public_rank_emission_permitted"] is False
    assert atlas["row_order_semantics"] == "coordinate_table_source_order_not_rank"
    assert atlas["source_coordinate_contract"] == SOURCE_COORDINATE_CONTRACT
    assert atlas["coordinate_table"]["path"] == ("packaging/public_v2/SOURCE_COORDINATE_TABLE.csv")
    assert atlas["field_provenance_receipt"]["known_fact_count"] == 27
    assert atlas["field_provenance_receipt"]["mechanically_extracted_fact_count"] == 27
    assert atlas["field_provenance_receipt"]["curated_manual_fact_count"] == 0
    assert atlas["field_provenance_receipt"]["downgraded_unknown_fact_count"] == 328
    assert atlas["field_provenance_receipt"]["all_known_fields_machine_resolved"] is True
    assert (
        atlas["field_provenance_receipt"][
            "manual_interpretations_mechanically_validated"
        ]
        is False
    )
    assert not any(study["study_id"].startswith("ani-") for study in atlas["studies"])
    assert all(study["comparison_eligible"] is False for study in atlas["studies"])
    assert all(
        {row["state"] for row in study["family_eligibility"].values()} == {"not_scoreable"}
        for study in atlas["studies"]
    )
    assert all(
        set(study["family_eligibility"]) == set(FAMILY_IDS)
        and {row["evidence_state"] for row in study["family_eligibility"].values()}
        == {"unknown"}
        and {row["coordinates"] for row in study["family_eligibility"].values()}
        == {None}
        for study in atlas["studies"]
    )
    assert all(
        study["source_binding"]["field_provenance"][
            "mechanically_extracted_source_bound"
        ]
        == study["source_binding"]["field_provenance"]["known_fact_count"]
        for study in atlas["studies"]
    )
    assert sum(
        study["source_binding"]["field_provenance"][
            "downgraded_unknown_fact_count"
        ]
        for study in atlas["studies"]
    ) == 328
    assert all(
        study["source_binding"]["source_projection_sha256"].startswith("sha256:")
        and study["source_binding"]["authority_objects"]
        for study in atlas["studies"]
    )


def test_studio_comparator_atlas_rejects_projection_hash_drift(tmp_path: Path) -> None:
    public_dir = tmp_path / "packaging" / "public_v2"
    public_dir.mkdir(parents=True)
    shutil.copy2(
        ROOT / "packaging" / "public_v2" / "SOURCE_COORDINATE_TABLE.csv",
        public_dir / "SOURCE_COORDINATE_TABLE.csv",
    )
    shutil.copy2(
        ROOT
        / "packaging"
        / "public_v2"
        / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
        public_dir / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
    )
    receipt_path = public_dir / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["coordinate_table"]["sha256"] = hashlib.sha256(
        (public_dir / "SOURCE_COORDINATE_TABLE.csv").read_bytes()
    ).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    projection_dir = tmp_path / "data" / "source_projections" / "v2"
    projection_dir.mkdir(parents=True)
    for source in (ROOT / "data" / "source_projections" / "v2").glob("*.json"):
        shutil.copy2(source, projection_dir / source.name)
    target = projection_dir / "all-of-us-cdrv9.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["name"] = "tampered"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(StudioAtlasError, match="source projection hash mismatch"):
        build_studio_comparator_atlas(tmp_path)


def test_studio_comparator_atlas_rejects_path_like_study_identifiers(tmp_path: Path) -> None:
    public_dir = tmp_path / "packaging" / "public_v2"
    public_dir.mkdir(parents=True)
    source_table = (ROOT / "packaging" / "public_v2" / "SOURCE_COORDINATE_TABLE.csv").read_text(
        encoding="utf-8"
    )
    (public_dir / "SOURCE_COORDINATE_TABLE.csv").write_text(
        source_table.replace("all-of-us-cdrv9", "../outside", 1),
        encoding="utf-8",
    )
    shutil.copy2(
        ROOT
        / "packaging"
        / "public_v2"
        / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
        public_dir / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
    )
    receipt_path = public_dir / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["coordinate_table"]["sha256"] = hashlib.sha256(
        (public_dir / "SOURCE_COORDINATE_TABLE.csv").read_bytes()
    ).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    projection_dir = tmp_path / "data" / "source_projections" / "v2"
    projection_dir.mkdir(parents=True)

    with pytest.raises(StudioAtlasError, match="invalid or duplicate study_id"):
        build_studio_comparator_atlas(tmp_path)


def test_studio_comparator_atlas_rejects_retired_or_inflated_family_contract(
    tmp_path: Path,
) -> None:
    public_dir = tmp_path / "packaging" / "public_v2"
    public_dir.mkdir(parents=True)
    projection_dir = tmp_path / "data" / "source_projections" / "v2"
    projection_dir.mkdir(parents=True)
    for source in (ROOT / "data" / "source_projections" / "v2").glob("*.json"):
        shutil.copy2(source, projection_dir / source.name)
    table_path = public_dir / "SOURCE_COORDINATE_TABLE.csv"
    shutil.copy2(
        ROOT / "packaging" / "public_v2" / "SOURCE_COORDINATE_TABLE.csv",
        table_path,
    )
    receipt_path = public_dir / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json"
    shutil.copy2(
        ROOT / "packaging" / "public_v2" / "EXTERNAL_FIELD_PROVENANCE_RECEIPT.json",
        receipt_path,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["coordinate_table"]["sha256"] = hashlib.sha256(table_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    target = projection_dir / "all-of-us-cdrv9.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["source_coordinate_contract"]["families"]["seventh_menu_family"] = {
        "evidence_state": "unknown",
        "coordinate_state": "not_scoreable",
        "coordinates": None,
        "reason": "source_complete_protocol_capacity_geometry_not_available",
        "open_gate_ids": payload["open_gates"],
    }
    target.write_text(json.dumps(payload), encoding="utf-8")
    attacked_hash = hashlib.sha256(target.read_bytes()).hexdigest()

    with table_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    assert fieldnames is not None
    next(row for row in rows if row["study_id"] == "all-of-us-cdrv9")[
        "source_projection_sha256"
    ] = attacked_hash
    with table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    projection_receipt = next(
        row
        for row in receipt["projections"]
        if row["study_id"] == "all-of-us-cdrv9"
    )
    projection_receipt["projection_sha256"] = attacked_hash
    receipt["coordinate_table"]["sha256"] = hashlib.sha256(table_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(StudioAtlasError, match="does not declare exactly six families"):
        build_studio_comparator_atlas(tmp_path)


def test_studio_get_comparator_atlas_returns_verified_contract() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    server.root = ROOT  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urlopen(f"http://{host}:{port}/api/v2/comparator-atlas", timeout=5) as response:
            payload = json.loads(response.read())
        assert response.status == 200
        assert payload["schema_version"] == "anibench.studio-comparator-atlas.v1"
        assert payload["study_count"] == 16
        assert payload["comparison_eligible_study_count"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
