from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from anibench.cli import main
from anibench.collection_ingest import import_collection_tables
from anibench.collection_v1 import CollectionError, profile_collection


def mapping(path="assays.csv"):
    return {
        "schema_version": "anibench.collection-table-map.v1",
        "study_id": "synthetic-table-study", "record_basis": "collected",
        "inventory_status": "partial", "time_resolution_days": 1,
        "participant_ids": ["private-person-a", "private-person-b", "private-person-c"],
        "outside_roster": "exclude",
        "modules": [{"module_id": "proteomics", "domain": "molecular",
                     "target_unit": "proteins", "target_definition_id": "synthetic-proteins-v1"}],
        "sources": [{"path": path, "format": "wide", "participant_column": "person",
                     "event_column": "visit", "time_column": "day", "time_format": "iso_date",
                     "module_id": "proteomics", "quality_column": "qc",
                     "quality_map": {"ok": "pass", "bad": "fail", "pending": "unknown"},
                     "feature_columns": ["protein-a", "protein-b"], "value_kind": "numeric"}],
    }


WIDE = (
    "person,visit,day,qc,protein-a,protein-b\n"
    "private-person-a,v1,2026-01-01,ok,0,4\n"
    "private-person-a,v2,2026-01-29,ok,3,NA\n"
    "private-person-b,v1,,pending,7,8\n"
    "outside-person,v1,2026-01-01,ok,9,10\n"
)


@pytest.mark.parametrize("compressed", [False, True])
def test_wide_csv_and_gzip_preserve_zero_missingness_dates_and_roster(tmp_path, compressed):
    path = tmp_path / ("assays.csv.gz" if compressed else "assays.csv")
    path.write_bytes(gzip.compress(WIDE.encode()) if compressed else WIDE.encode())
    manifest, audit = import_collection_tables(mapping(path.name), base=tmp_path)
    result = profile_collection(manifest)
    assert result["population"]["roster_participants"] == 3
    assert result["population"]["participants_with_accepted_targets"] == 1
    assert result["modules"][0]["target_observations"] == 3
    assert result["modules"][0]["targets_per_participant"]["median"] == 0
    assert result["longitudinal"]["span_days_among_repeated_participants"]["median"] == 28
    assert audit["sources"][0]["missing_target_cells"] == 1
    assert audit["sources"][0]["outside_roster_rows"] == 1
    assert audit["sources"][0]["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert all(p not in json.dumps(result) + json.dumps(audit) for p in mapping()["participant_ids"])


def test_long_rows_and_duplicate_cells_do_not_add_distinct_targets(tmp_path):
    payload = mapping()
    source = payload["sources"][0]
    source.update(format="long", feature_column="target", value_column="value")
    del source["feature_columns"]
    (tmp_path / "assays.csv").write_text(
        "person,visit,day,qc,target,value\n"
        "private-person-a,v1,2026-01-01,ok,protein-a,0\n"
        "private-person-a,v1,2026-01-01,ok,protein-a,0\n"
        "private-person-a,v1,2026-01-01,ok,protein-b,4\n"
    )
    manifest, audit = import_collection_tables(payload, base=tmp_path)
    result = profile_collection(manifest)
    assert result["modules"][0]["target_observations"] == 2
    assert result["modules"][0]["participant_events_with_accepted_targets"] == 1
    assert audit["sources"][0]["included_rows"] == 3
    assert len(manifest["acquisitions"]) == 1


@pytest.mark.parametrize("destination", ["source", "mapping", "hardlink", "outputs"])
def test_cli_refuses_to_overwrite_sources_or_mix_private_and_aggregate_outputs(tmp_path, destination):
    assays = tmp_path / "assays.csv"
    assays.write_text(WIDE)
    recipe = tmp_path / "mapping.json"
    recipe.write_text(json.dumps(mapping()))
    before = recipe.read_bytes()
    out = tmp_path / "aggregate.json"
    extra = []
    if destination == "source":
        out = assays
    elif destination == "mapping":
        out = recipe
    elif destination == "hardlink":
        out.hardlink_to(assays)
    else:
        extra = ["--manifest-out", str(out)]
    assert main(["profile-tables", str(recipe), "--out", str(out), *extra]) == 2
    assert assays.read_text() == WIDE
    assert recipe.read_bytes() == before


@pytest.mark.parametrize("edit", ["hash", "duplicate_header", "bad_quality", "nonfinite", "not_numeric", "conflicting_clock"])
def test_import_rejects_ambiguous_or_changed_sources_without_echoing_cells(tmp_path, edit):
    payload = mapping()
    raw = WIDE
    if edit == "hash":
        payload["sources"][0]["sha256"] = "0" * 64
    elif edit == "duplicate_header":
        raw = raw.replace("protein-a,protein-b", "protein-a,protein-a")
    elif edit == "bad_quality":
        raw = raw.replace(",ok,", ",private-unknown-quality,")
    elif edit == "nonfinite":
        raw = raw.replace(",0,4", ",inf,4")
    elif edit == "not_numeric":
        raw = raw.replace(",0,4", ",private-text-value,4")
    else:
        raw = raw.replace("v2,2026-01-29", "v1,2026-01-29")
    (tmp_path / "assays.csv").write_text(raw)
    with pytest.raises(CollectionError) as error:
        import_collection_tables(payload, base=tmp_path)
    assert "private-" not in str(error.value)


def test_cli_default_writes_only_aggregate_output(tmp_path, capsys):
    (tmp_path / "assays.csv").write_text(WIDE)
    recipe = tmp_path / "mapping.json"
    recipe.write_text(json.dumps(mapping()))
    output = tmp_path / "profile.json"
    assert main(["profile-tables", str(recipe), "--out", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["profile"]["population"]["roster_participants"] == 3
    assert {p.name for p in tmp_path.iterdir()} == {"assays.csv", "mapping.json", "profile.json"}
    assert "private-person" not in output.read_text() + capsys.readouterr().out


def test_mixed_absolute_and_relative_clocks_require_explicit_alignment(tmp_path):
    payload = mapping()
    payload["sources"].append({**payload["sources"][0], "time_format": "elapsed_days"})
    with pytest.raises(CollectionError, match="alignment"):
        import_collection_tables(payload, base=tmp_path)
