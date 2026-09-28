# SPDX-FileCopyrightText: 2026 AniBench contributors
# SPDX-License-Identifier: Apache-2.0
"""Replay the frozen experiment in a newly created private directory."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(expected, actual, location=""):
    """Exact structure/counts; declared tolerance only for numerical results."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            raise ValueError("Replay object mismatch at " + location)
        for key in expected:
            compare(expected[key], actual[key], location + "/" + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError("Replay list mismatch at " + location)
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, location + "/" + str(index))
    elif type(expected) is float:
        if (
            type(actual) not in (float, int)
            or not math.isfinite(expected)
            or not math.isfinite(actual)
            or not math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10)
        ):
            raise ValueError("Replay numerical mismatch at " + location)
    elif type(expected) is not type(actual) or expected != actual:
        raise ValueError("Replay exact-value mismatch at " + location)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Local directory containing the four pinned official source files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New private directory; contains source records and private split",
    )
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output directory must not exist")
    manifest = json.loads((BASE / "source/SOURCE_MANIFEST.json").read_text())
    freeze = json.loads((BASE / "FREEZE.json").read_text())
    preread = json.loads((BASE / "source/PRE_READ_RECEIPT.json").read_text())
    if sha(BASE / "source/SOURCE_MANIFEST.json") != preread["source_manifest_sha256"]:
        parser.error("Source manifest changed")
    for name, key in [("run.py", "run_sha256"), ("PROTOCOL.json", "protocol_sha256")]:
        if sha(BASE / name) != freeze[key]:
            parser.error("Frozen experiment file changed")
    for item in manifest["sources"]:
        source = args.source / item["file"]
        if (
            not source.is_file()
            or source.stat().st_size != item["bytes"]
            or sha(source) != item["sha256"]
        ):
            parser.error("Official source bytes do not match the frozen manifest: " + item["file"])
    helper = importlib.import_module("anibench.information_v2")
    helper_hash = sha(Path(helper.__file__))
    if helper_hash != freeze["information_helper_sha256"]:
        parser.error("Numerical helper differs from the frozen experiment")
    args.out.mkdir(mode=0o700, parents=True)
    source_out = args.out / "source"
    source_out.mkdir(mode=0o700)
    for name in ["run.py", "PROTOCOL.json", "FREEZE.json"]:
        shutil.copyfile(BASE / name, args.out / name)
    for name in ["SOURCE_MANIFEST.json", "PRE_READ_RECEIPT.json"]:
        shutil.copyfile(BASE / "source" / name, source_out / name)
    for item in manifest["sources"]:
        shutil.copyfile(args.source / item["file"], source_out / item["file"])
    # Record the current replay's imported helper; never backdate the original run.
    with (args.out / "REPLAY_RUNTIME.json").open("x") as stream:
        json.dump(
            {
                "schema": "anibench.native-repeat-replay-runtime.v1",
                "information_helper_sha256": helper_hash,
                "run_sha256": sha(args.out / "run.py"),
                "python": sys.version.split()[0],
                "scope": "Current portable replay, not a retrospective original-runtime receipt",
            },
            stream,
            indent=2,
        )
        stream.write("\n")
    subprocess.run(
        [sys.executable, str(args.out / "run.py"), "--out", str(args.out / "results.json")],
        check=True,
    )
    actual = json.loads((args.out / "results.json").read_text())
    expected = json.loads((BASE / "aggregate-results.json").read_text())
    for key in ["split_sha256", "participant_split_sha256"]:
        actual.pop(key)
    expected.pop("public_projection")
    # Runtime versions are evidence to retain, not numerical expected results.
    actual.pop("runtime")
    expected.pop("runtime")
    compare(expected, actual)
    with (args.out / "COMPARISON.json").open("x") as stream:
        json.dump(
            {
                "schema": "anibench.native-repeat-replay-comparison.v1",
                "aggregate_sha256": sha(BASE / "aggregate-results.json"),
                "results_sha256": sha(args.out / "results.json"),
                "structure_and_counts_exact": True,
                "numerical_relative_tolerance": 1e-10,
                "numerical_absolute_tolerance": 1e-10,
                "matched": True,
            },
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    main()
