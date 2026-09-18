"""Literal publication facts, independent of modeled capacity and adjudication.

A numeric token can be extracted exactly while the publication itself reports
a rounded denominator. Preserve both kinds of precision. A successful replay
establishes what the source reports, not whether the study's claim is true.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CONTRACT = "anibench.literal-publication-facts.v1"
RELATIVE_PATH = Path("data/reported_facts/v1/literature.json")
NUMBER_WORDS = {"ten": 10}


def digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def extract_number(excerpt: str, token: str) -> int | float:
    """Parse one explicit numeric token without guessing units or denominators."""
    word_value = NUMBER_WORDS.get(token.lower())
    if word_value is None and not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", token):
        raise ValueError("invalid publication numeric token")
    matches = re.findall(r"(?<![\w.,])" + re.escape(token) + r"(?![\w.,])", excerpt)
    if len(matches) != 1:
        raise ValueError("numeric token must occur exactly once in its excerpt")
    if word_value is not None:
        return word_value
    return float(token.replace(",", "")) if "." in token else int(token.replace(",", ""))


def load_reported_facts(root: Path) -> dict[str, Any]:
    path = root / RELATIVE_PATH
    packet = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if packet.get("schema_version") != CONTRACT or packet.get("packet_sha256") != digest(body):
        raise ValueError("literal publication fact packet hash or contract mismatch")
    sources = packet["sources"]
    identifiers = set()
    for fact in packet["facts"]:
        if fact["fact_id"] in identifiers:
            raise ValueError("duplicate publication fact")
        identifiers.add(fact["fact_id"])
        if fact["source_id"] not in sources or fact["state"] != "reported":
            raise ValueError("unbound publication fact")
        if extract_number(fact["excerpt"], fact["numeric_token"]) != fact["value"]:
            raise ValueError("publication fact disagrees with its numeric token")
    return packet


def replay_reported_facts(packet: dict[str, Any], raw_root: Path) -> int:
    """Verify entire source-body hashes and exact JSON-pointer excerpt matches."""
    sources = {}
    for source_id, source in packet["sources"].items():
        # Filenames are source identifiers, never arbitrary paths from data.
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,63}", source_id):
            raise ValueError("unsupported publication source identifier")
        source_format = source.get("source_format", "json")
        if source_format not in {"json", "utf8_text"}:
            raise ValueError("unsupported publication source format")
        suffix = "txt" if source_format == "utf8_text" else "json"
        body = (raw_root / f"{source_id}.{suffix}").read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"publication source hash mismatch: {source_id}")
        sources[source_id] = (
            body.decode("utf-8") if source_format == "utf8_text" else json.loads(body)
        )
    for fact in packet["facts"]:
        value = sources[fact["source_id"]]
        for part in fact["json_pointer"].split("/")[1:]:
            value = value[int(part)] if isinstance(value, list) else value[part]
        if not isinstance(value, str) or value.count(fact["excerpt"]) != 1:
            raise ValueError(f"publication excerpt does not resolve once: {fact['fact_id']}")
        if extract_number(fact["excerpt"], fact["numeric_token"]) != fact["value"]:
            raise ValueError(f"publication extraction mismatch: {fact['fact_id']}")
    return len(packet["facts"])
