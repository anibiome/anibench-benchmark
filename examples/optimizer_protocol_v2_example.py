"""Minimal request builder for the protocol-native AniBench v2 optimizer.

Pass a valid ``anibench.protocol-capacity-input.v2`` object.  This example adds
one protocol-native mutation: it changes the declared participant count in the
first participant-event schedule.  It cannot patch compiled family results.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

from anibench.optimizer_protocol_v2 import optimize_protocol


EXAMPLE_SOURCE_SHA256 = "sha256:" + "0" * 64


def build_example_request(base_protocol: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "anibench.optimizer-protocol-input.v2",
        "optimizer_id": "prospective-reach-sandbox",
        "base_protocol": copy.deepcopy(dict(base_protocol)),
        "objectives": [
            {
                "objective_id": "conservative-extensive-reach",
                "family_path": "extensive.retained_participant_events",
                "envelope_bound": "minimum",
                "direction": "maximize",
            },
            {
                "objective_id": "conservative-longitudinal-density",
                "family_path": "longitudinal.retained_participant_events",
                "envelope_bound": "minimum",
                "direction": "maximize",
            },
        ],
        "resource_constraints": [
            {
                "resource_id": "direct-cost",
                "unit": "USD_2026",
                "base_amount": 1_000_000,
                "maximum_amount": 2_000_000,
                "as_of": "2026-07-12",
                "source_object_sha256": EXAMPLE_SOURCE_SHA256,
                "source_locator": "example:budget:approved-envelope",
            }
        ],
        "mutations": [
            {
                "mutation_id": "expand-first-schedule-to-200",
                "description": "Raise the first schedule's committed participant count to 200.",
                "protocol_operations": [
                    {
                        "op": "replace",
                        "path": "/measurement_geometry/participant_event_schedules/0/participant_count",
                        "value": {"state": "exact", "value": 200},
                    }
                ],
                "resource_deltas": [
                    {
                        "resource_id": "direct-cost",
                        "unit": "USD_2026",
                        "amount": 500_000,
                        "as_of": "2026-07-12",
                        "source_object_sha256": EXAMPLE_SOURCE_SHA256,
                        "source_locator": "example:cost-model:expand-first-schedule",
                    }
                ],
                "source_object_sha256": EXAMPLE_SOURCE_SHA256,
                "source_locator": "example:protocol-amendment:expand-first-schedule",
            }
        ],
        "maximum_mutations_per_candidate": 1,
        "candidate_limit": 2,
    }


def run(base_protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Compile the base and mutated candidate and return their Pareto relation."""

    return optimize_protocol(build_example_request(base_protocol))
