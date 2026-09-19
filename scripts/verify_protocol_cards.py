"""Verify public protocol-card structure and optionally replay original PDFs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from anibench.protocol_cards import load_protocol_cards, replay_protocol_cards

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-source-dir", type=Path)
    args = parser.parse_args()
    packet = load_protocol_cards(Path(__file__).resolve().parents[1])
    if packet is None:
        raise SystemExit("No public protocol cards installed")
    result = (
        replay_protocol_cards(packet, args.raw_source_dir)
        if args.raw_source_dir
        else {
            "packet_sha256": packet["packet_sha256"],
            "card_count": len(packet["cards"]),
            "source_bytes_replayed": False,
        }
    )
    print(json.dumps(result, indent=2))
