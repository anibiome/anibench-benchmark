from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def make_input(case: str) -> dict:
    """Expand a frozen hypothetical acquisition recipe without private inputs."""
    if case not in ("standard_candidate", "fine_candidate"):
        raise ValueError("Unknown frozen design")
    recipe = json.loads((ROOT / "INPUT_TEMPLATE.json").read_text())
    design = copy.deepcopy(recipe["template"])
    n, blocks = (2048, 4) if case == "standard_candidate" else (8192, 16)
    design["cohort_n"] = n
    design["design_id"] = "hypothetical-native36-capability-v3-" + case
    for panel_id, panel in design["panels"].items():
        spec = recipe["event_recipes"][panel_id]
        events = []
        for coordinate in spec["coordinates"]:
            for day in spec["dates"]:
                for block in range(blocks):
                    session = f"{coordinate}-{day}-{block}"
                    for reading in range(4):
                        events.append({"coordinate": coordinate, "time": day,
                                       "session_id": session,
                                       "physical_id": f"{session}-{reading}"})
        for group in panel["groups"]:
            group["n"] = n // 8
            group["events"] = copy.deepcopy(events)
    for partition in design["cross_panel_linkage"]["partitions"]:
        partition["n"] = n // 8
    raw = (json.dumps(design, sort_keys=True, separators=(",", ":"),
                      allow_nan=False) + "\n").encode()
    expected = json.loads((ROOT / "EXPECTED_INPUTS.json").read_text())[case]
    if hashlib.sha256(raw).hexdigest() != expected["new_raw_sha256"]:
        raise ValueError("Generated input differs from the frozen source-reviewed input")
    return design
