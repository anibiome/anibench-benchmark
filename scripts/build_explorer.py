"""Build a portable, read-only explorer from verified public inputs.

Custom evaluation remains in local Studio; a static host receives no uploads.
The destination must be new. A manifest binds all emitted application bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from anibench.explorer import build_explorer_demo
from anibench.studio_product import build_studio_comparator_atlas

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ("explore.html", "explore.css", "explore.js", "favicon.svg",
          "benchmark.html", "benchmark.css", "benchmark.js")


def build_explorer(output: Path, root: Path = ROOT) -> dict:
    # Verify and calculate before creating an output directory.
    atlas = build_studio_comparator_atlas(root)
    demo = build_explorer_demo(root)
    output.mkdir(parents=True, exist_ok=False)
    for name in ASSETS:
        (output / name).write_bytes((root / "web" / name).read_bytes())
    (output / "index.html").write_bytes((output / "benchmark.html").read_bytes())
    # The Designer needs the local Python service. Give static visitors a
    # working installation page instead of a form whose submission will fail.
    (output / "v2.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Run AniBench locally</title><link rel="stylesheet" href="explore.css">'
        '<main class="section"><p class="eyebrow">ANIBENCH STUDIO</p>'
        "<h1>Evaluate your own study.</h1>"
        "<p>Clone the open repository, install it, and start the local Studio:</p>"
        "<pre>git clone https://github.com/anibiome/anibench-benchmark.git\n"
        "cd anibench-benchmark\npython -m pip install -e .\nanibench studio</pre>"
        "<p>Open http://127.0.0.1:8765/explore.html to evaluate and compare files, "
        "or http://127.0.0.1:8765/ for the Trial Designer.</p>"
        '<p><a href="explore.html">Return to the study atlas</a></p></main></html>',
        encoding="utf-8",
    )
    for name, payload in (("explorer-atlas.json", atlas), ("explorer-demo.json", demo)):
        (output / name).write_text(
            json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    manifest = {
        "schema_version": "anibench.explorer-build.v1",
        "study_count": atlas["study_count"],
        "capacity_comparison_complete_studies": atlas["comparison_eligible_study_count"],
        "source_table_sha256": atlas["coordinate_table"]["sha256"],
        "demo_comparison_sha256": demo["comparison"]["comparison_receipt_sha256"],
        "files": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.iterdir())
            if path.is_file()
        },
    }
    (output / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    print(json.dumps(build_explorer(args.out), indent=2))
