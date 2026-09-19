"""Public protocol descriptions with explicit numeric and curated provenance.

These records do not populate the mechanical registry-projection receipt or any
capacity score. A hash binds bytes; it does not certify the source or semantics.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, ValidationError

from .reported_facts import digest, extract_number

CONTRACT = "anibench.public-protocol-cards.v1"
RELATIVE_PATH = Path("data/protocol_cards/v1/public.json")
HASH_RE = re.compile(r"[a-f0-9]{64}")
ID_RE = re.compile(r"[a-z][a-z0-9-]{0,127}")
NORMALIZATION = "unicode_nfc_whitespace_collapse_strip_utf8_v1"


def _schema() -> dict[str, Any]:
    relative = Path("schemas/protocol_cards/v1/packet.schema.json")
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parent):
        path = root / relative
        if path.is_file():
            return json.loads(path.read_text())
    raise ValueError("Protocol-card schema is not installed")


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def validate_packet(packet: dict[str, Any]) -> None:
    """Reject ambiguous provenance and numeric/unknown state promotion."""
    try:
        Draft202012Validator(_schema()).validate(packet)
    except ValidationError as exc:
        raise ValueError(f"Invalid protocol-card structure: {exc.message}") from exc
    body = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if (
        packet.get("schema_version") != CONTRACT
        or packet.get("packet_sha256") != digest(body)
        or packet.get("public_rank_allowed") is not False
        or packet.get("claim_scope") != "reported_planned_design_not_capacity"
    ):
        raise ValueError("protocol-card contract, hash or claim scope mismatch")
    seen_studies: set[str] = set()
    for card in packet["cards"]:
        study_id = card["study_id"]
        if not ID_RE.fullmatch(study_id) or study_id in seen_studies:
            raise ValueError("invalid or duplicate protocol-card study")
        seen_studies.add(study_id)
        source = card["source"]
        url = urlsplit(source["url"])
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or not HASH_RE.fullmatch(source["sha256"])
            or not ID_RE.fullmatch(source["source_id"])
            or source["hash_scope"] != "complete_original_pdf_bytes"
            or source["extraction"]["normalization"] != NORMALIZATION
        ):
            raise ValueError("invalid protocol-card source binding")
        page_count = source["page_count"]
        pages = source["extraction"]["page_text_hashes"]
        if (
            type(page_count) is not int
            or page_count < 1
            or [row["page"] for row in pages] != list(range(1, page_count + 1))
            or any(not HASH_RE.fullmatch(row["sha256"]) for row in pages)
        ):
            raise ValueError("invalid protocol-card page hash set")
        seen_facts: set[str] = set()
        for fact in card["numeric_facts"]:
            if (
                fact["fact_id"] in seen_facts
                or fact["study_id"] != study_id
                or fact["source_id"] != source["source_id"]
                or fact["state"] != "reported"
                or fact["claim_lane"] != "planned_design"
                or type(fact["pdf_page"]) is not int
                or not 1 <= fact["pdf_page"] <= page_count
                or type(fact["value"]) not in (int, float)
                or fact["value"] != extract_number(fact["excerpt"], fact["numeric_token"])
                or fact["precision"] not in {"reported_integer", "source_approximate"}
                or fact["curation"] != "numeric_token_replay_with_curated_semantics"
            ):
                raise ValueError("invalid protocol-card numeric fact")
            seen_facts.add(fact["fact_id"])
        seen_observations: set[str] = set()
        for item in card["observations"]:
            if (
                item["id"] in seen_observations
                or not ID_RE.fullmatch(item["id"])
                or item["state"] not in {"reported", "unknown", "conflicting"}
                or (item["state"] == "unknown") != (item["value"] is None)
                or item["curation"]
                not in {"text_interpretation", "visual_interpretation", "unresolved_source_scope"}
                or not item["pages"]
                or any(type(p) is not int or not 1 <= p <= page_count for p in item["pages"])
                or not item["locator"]
                or not item["note"]
            ):
                raise ValueError("invalid protocol-card observation state or locator")
            seen_observations.add(item["id"])
        assignment = card["reported_randomization"]
        if assignment["value"] is None:
            if assignment["observation_id"] is not None:
                raise ValueError("Unknown randomization must not claim a bound classification")
        elif not any(
            item["id"] == assignment["observation_id"] and item["state"] == "reported"
            for item in card["observations"]
        ):
            raise ValueError("Reported randomization lacks a bound source interpretation")


def load_protocol_cards(root: Path) -> dict[str, Any] | None:
    path = root / RELATIVE_PATH
    if not path.exists():
        return None
    packet = json.loads(path.read_text(encoding="utf-8"))
    validate_packet(packet)
    return packet


def replay_protocol_cards(packet: dict[str, Any], raw_root: Path) -> dict[str, Any]:
    """Replay exact PDF bytes, normalized page text and literal numeric tokens.

    Inputs are local SOURCE_ID.pdf files; this function performs no download.
    Curated semantics and image interpretation still require source review.
    """
    from pypdf import PdfReader

    validate_packet(packet)
    rows = []
    for card in packet["cards"]:
        source = card["source"]
        path = raw_root / f"{source['source_id']}.pdf"
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("protocol-card PDF hash mismatch")
        reader = PdfReader(path)
        texts = [normalized_text(page.extract_text() or "") for page in reader.pages]
        actual_hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]
        expected = [p["sha256"] for p in source["extraction"]["page_text_hashes"]]
        if actual_hashes != expected:
            raise ValueError("protocol-card page extraction hash mismatch")
        for fact in card["numeric_facts"]:
            if texts[fact["pdf_page"] - 1].count(normalized_text(fact["excerpt"])) != 1:
                raise ValueError("protocol-card excerpt must resolve exactly once")
        rows.append(
            {
                "study_id": card["study_id"],
                "source_sha256": source["sha256"],
                "pages_replayed": len(texts),
                "numeric_facts_replayed": len(card["numeric_facts"]),
            }
        )
    return {
        "packet_sha256": packet["packet_sha256"],
        "sources": rows,
        "pypdf_version": importlib.metadata.version("pypdf"),
        "curated_semantics_machine_verified": False,
        "capacity_evaluation_performed": False,
    }


def card_studies(packet: dict[str, Any], family_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    """Adapt verified record structure without inventing a registry projection."""
    validate_packet(packet)
    studies = []
    for card in packet["cards"]:
        source = card["source"]
        source_hash = f"sha256:{digest(card)}"
        unknown = {"value": None, "state": "unknown", "semantics": "unresolved"}
        studies.append(
            {
                "study_id": card["study_id"],
                "name": card["name"],
                "record_kind": "public_protocol_card",
                "projection_lane": "planned_design",
                "projection_status": "public_source_description_not_capacity_model",
                "population": {**unknown, "unit": "participants"},
                "duration": {**unknown, "unit": "days"},
                "causal_architecture": dict.fromkeys(
                    (
                        "policy_arms",
                        "randomized_policy",
                        "concurrent_control",
                        "deployed_operator_families",
                        "identifiable_policy_contrasts",
                        "adaptive_reassignment",
                        "within_policy_randomized",
                    )
                ),
                "measurement_module_states": dict.fromkeys(
                    ("known_projected", "conditional", "unknown")
                ),
                "open_gates": card["open_gates"],
                "comparison_eligible": False,
                "family_eligibility": {
                    family: {
                        "state": "not_scoreable",
                        "evidence_state": "unknown",
                        "coordinates": None,
                        "reason": "source_complete_protocol_capacity_geometry_not_available",
                        "open_gate_ids": card["open_gates"],
                        "source_record_sha256": source_hash,
                    }
                    for family in family_ids
                },
                "publication_facts": [
                    {
                        **fact,
                        "source": source,
                        "packet_sha256": packet["packet_sha256"],
                        "json_pointer": f"PDF page {fact['pdf_page']} / normalized text",
                    }
                    for fact in card["numeric_facts"]
                ],
                "protocol_observations": card["observations"],
                "reported_randomization": {
                    **card["reported_randomization"],
                    "provenance_mode": "curated_public_protocol",
                    "source_record_sha256": source_hash,
                },
                "reported_evidence": {},
                "source_binding": {
                    "source_record_sha256": source_hash,
                    "source_record_path": RELATIVE_PATH.as_posix(),
                    "authority_objects": [
                        {**source, "evidence_class": "public_participant_information"}
                    ],
                    "packet_sha256": packet["packet_sha256"],
                    "provenance_scope": "numeric_extraction_and_separately_curated_source_interpretation",
                },
            }
        )
    return studies
