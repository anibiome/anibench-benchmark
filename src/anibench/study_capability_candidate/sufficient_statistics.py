# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Exact GLS reduction for replicate target rows in independent known error blocks.

Only coordinate/time-homogeneous error blocks qualify. The original physical
input remains authoritative. Returned representative event metadata labels a
retained target row, never an additional physical acquisition.
"""

from collections import defaultdict

VERSION = "known-homogeneous-error-block-gls-v1"


def reduce_events(events):
    """Return target rows and unit-q variances, or None for unchanged geometry."""
    if not events or any(e.get("session_id") is None for e in events):
        return None
    blocks = defaultdict(list)
    for event in events:
        blocks[(event["coordinate"], event["session_id"])].append(event)
    if any(len({e["time"] for e in block}) != 1 for block in blocks.values()):
        return None
    precisions = defaultdict(float)
    representatives = {}
    for block in blocks.values():
        event = block[0]
        key = (event["coordinate"], event["time"])
        representatives.setdefault(key, event)
        precisions[key] += 1.0 / (0.25 + 0.75 / len(block))
    if len(representatives) == len(events):
        return None
    keys = list(representatives)
    return [representatives[k] for k in keys], [1.0 / precisions[k] for k in keys]
