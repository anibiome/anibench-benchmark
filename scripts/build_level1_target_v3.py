#!/usr/bin/env python3
"""Build or check the deterministic role-aware AniBench Level-1 v3 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from anibench.level1_target_v3 import (
    V2_TARGET_PATH,
    build_artifact_bytes,
    readback_role_aware_authority,
    write_artifacts,
)


AUTHORITY_PATH = "spec/v3/level1/role-aware-target-requirements.v3.json"
IMPACT_PATH = "spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    repo_root = args.repo_root.resolve()
    if args.check:
        mismatches: list[str] = []
        if (repo_root / V2_TARGET_PATH).exists():
            for relative_path, expected in build_artifact_bytes(repo_root).items():
                actual_path = repo_root / relative_path
                if not actual_path.exists() or actual_path.read_bytes() != expected:
                    mismatches.append(relative_path)
        else:
            try:
                readback_role_aware_authority(
                    repo_root / AUTHORITY_PATH,
                    repo_root / IMPACT_PATH,
                )
            except (OSError, ValueError, KeyError) as exc:
                mismatches.append(f"public_v3_readback:{exc}")
        print(json.dumps({"valid": not mismatches, "mismatches": mismatches}, sort_keys=True))
        return 0 if not mismatches else 1

    hashes = write_artifacts(repo_root, args.output_root)
    print(json.dumps({"artifacts": hashes}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
