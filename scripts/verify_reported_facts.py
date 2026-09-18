"""Replay literal publication evidence, optionally against complete source bytes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from anibench.reported_facts import load_reported_facts, replay_reported_facts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-source-dir", type=Path)
    args = parser.parse_args()
    packet = load_reported_facts(Path(__file__).resolve().parents[1])
    replayed = replay_reported_facts(packet, args.raw_source_dir) if args.raw_source_dir else 0
    print(
        json.dumps(
            {
                "fact_count": len(packet["facts"]),
                "full_source_facts_replayed": replayed,
                "packet_sha256": packet["packet_sha256"],
                "scope": "literal_numeric_extraction_not_independent_scientific_review",
            },
            indent=2,
        )
    )
