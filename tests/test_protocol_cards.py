from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from anibench.protocol_cards import (
    RELATIVE_PATH,
    card_studies,
    load_protocol_cards,
    normalized_text,
    replay_protocol_cards,
    validate_packet,
)
from anibench.reported_facts import digest
from anibench.studio_product import FAMILY_IDS, build_studio_comparator_atlas

ROOT = Path(__file__).resolve().parents[1]


def signed(packet: dict) -> dict:
    packet["packet_sha256"] = digest({k: v for k, v in packet.items() if k != "packet_sha256"})
    return packet


def test_public_card_preserves_plan_unknowns_and_conflicting_timing() -> None:
    packet = load_protocol_cards(ROOT)
    card = packet["cards"][0]
    assert card["study_id"] == "wur-oh-my-gut"
    assert [fact["value"] for fact in card["numeric_facts"]] == [222, 6, 6, 2]
    assert all(fact["claim_lane"] == "planned_design" for fact in card["numeric_facts"])
    facts = {row["id"]: row for row in card["observations"]}
    assert facts["timing"]["state"] == "conflicting"
    assert facts["neural"]["value"] is None
    assert facts["retention"]["value"] is None
    study = card_studies(packet, FAMILY_IDS)[0]
    assert study["duration"]["value"] is None
    assert study["population"]["value"] is None
    assert study["comparison_eligible"] is False
    assert all(v["coordinates"] is None for v in study["family_eligibility"].values())
    assert "source_projection_sha256" not in study["source_binding"]
    assert study["publication_facts"][0]["source"]["hash_scope"] == "complete_original_pdf_bytes"


def test_existing_mechanical_receipt_does_not_claim_curated_card_fields() -> None:
    atlas = build_studio_comparator_atlas(ROOT)
    assert atlas["study_count"] == 17
    assert atlas["field_provenance_receipt"]["known_fact_count"] == 27
    assert (
        atlas["field_provenance_receipt"]["scope"] == "mechanical_coordinate_table_projections_only"
    )
    assert atlas["public_protocol_cards"]["count"] == 1
    assert atlas["public_protocol_cards"]["curated_semantics_machine_verified"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(public_rank_allowed=True),
        lambda p: p["cards"].append(copy.deepcopy(p["cards"][0])),
        lambda p: p["cards"][0]["source"].update(source_id="../outside"),
        lambda p: p["cards"][0]["source"].update(url="https://user:secret@example.org/source.pdf"),
        lambda p: p["cards"][0]["source"].update(sha256="invalid"),
        lambda p: p["cards"][0]["source"].update(page_count=18),
        lambda p: p["cards"][0]["numeric_facts"][0].update(value=223),
        lambda p: p["cards"][0]["numeric_facts"][0].update(value=True),
        lambda p: p["cards"][0]["numeric_facts"][0].update(source_id="unbound"),
        lambda p: p["cards"][0]["numeric_facts"][0].update(unit=None),
        lambda p: p["cards"][0]["numeric_facts"][0].pop("semantics"),
        lambda p: p["cards"][0].pop("open_gates"),
        lambda p: p["cards"][0]["observations"][0].update(value={"unexpected": "object"}),
        lambda p: p["cards"][0]["reported_randomization"].update(observation_id="unbound"),
        lambda p: p["cards"][0]["numeric_facts"][0].update(claim_lane="realized"),
        lambda p: p["cards"][0]["numeric_facts"][0].update(pdf_page=18),
        lambda p: p["cards"][0]["observations"][0].update(state="unknown"),
        lambda p: p["cards"][0]["observations"][-1].update(value="complete"),
    ],
)
def test_even_rehashed_cards_cannot_bypass_internal_provenance(mutation) -> None:
    packet = load_protocol_cards(ROOT)
    mutation(packet)
    with pytest.raises(ValueError):
        validate_packet(signed(packet))


def test_mutable_packet_bytes_do_not_pass_original_hash(tmp_path: Path) -> None:
    packet = load_protocol_cards(ROOT)
    packet["cards"][0]["name"] = "changed"
    path = tmp_path / RELATIVE_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="hash"):
        load_protocol_cards(tmp_path)


def pdf_fixture(tmp_path: Path) -> dict:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (222 participants) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    packet = load_protocol_cards(ROOT)
    card = packet["cards"][0]
    path = tmp_path / f"{card['source']['source_id']}.pdf"
    writer.write(path)
    card["source"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    card["source"]["page_count"] = 1
    card["source"]["extraction"]["page_text_hashes"] = [
        {"page": 1, "sha256": hashlib.sha256(b"222 participants").hexdigest()}
    ]
    card["numeric_facts"] = card["numeric_facts"][:1]
    card["numeric_facts"][0].update(pdf_page=1, excerpt="222 participants")
    card["observations"] = []
    card["reported_randomization"] = {"value": None, "observation_id": None}
    return signed(packet)


def test_pdf_replay_checks_complete_bytes_pages_and_exact_excerpt(tmp_path: Path) -> None:
    packet = pdf_fixture(tmp_path)
    result = replay_protocol_cards(packet, tmp_path)
    assert result["sources"][0]["numeric_facts_replayed"] == 1
    assert result["curated_semantics_machine_verified"] is False
    altered = copy.deepcopy(packet)
    altered["cards"][0]["numeric_facts"][0]["excerpt"] = "222 donors"
    with pytest.raises(ValueError, match="excerpt"):
        replay_protocol_cards(signed(altered), tmp_path)
    altered = copy.deepcopy(packet)
    altered["cards"][0]["source"]["extraction"]["page_text_hashes"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="extraction hash"):
        replay_protocol_cards(signed(altered), tmp_path)
    with (tmp_path / f"{packet['cards'][0]['source']['source_id']}.pdf").open("ab") as handle:
        handle.write(b"changed")
    with pytest.raises(ValueError, match="PDF hash"):
        replay_protocol_cards(packet, tmp_path)


def test_normalization_is_explicit_and_unicode_stable() -> None:
    assert normalized_text("\tCafe\u0301\n   222\u00a0participants ") == "Café 222 participants"
