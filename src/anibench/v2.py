from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .information_v2 import (
    absolute_mechanics,
    canonical_matrix_sha256,
    reconstruction_metrics,
    validate_reference_geometry,
)


class V2RunError(ValueError):
    pass


def _asset_path(relative: str) -> Path:
    checkout = Path(__file__).resolve().parents[2] / relative
    installed = Path(__file__).resolve().parent / relative
    for candidate in (checkout, installed):
        if candidate.is_file():
            return candidate
    raise V2RunError(f"required v2 authority asset is not installed: {relative}")


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise V2RunError(f"could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise V2RunError(f"{label} must be one JSON object")
    return payload


def _schema() -> dict[str, Any]:
    return _load_json(
        _asset_path("schemas/v2/information-run.schema.json"),
        label="v2 information-run schema",
    )


def _reference_registry() -> tuple[dict[str, Any], str]:
    registry_path = _asset_path("spec/v2/reference-registry.json")
    registry = _load_json(registry_path, label="v2 local reference registry")
    registry_schema = _load_json(
        _asset_path("schemas/v2/reference-registry.schema.json"),
        label="v2 local reference-registry schema",
    )
    errors = sorted(
        Draft202012Validator(registry_schema).iter_errors(registry),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise V2RunError(
            "local reference registry is invalid: "
            + "; ".join(
                f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
                for error in errors
            )
        )
    if (
        registry["promotable_level_1_reference"] is not None
        or registry["public_completion_claim_allowed"] is not False
    ):
        raise V2RunError("local reference registry violates the packaged authority boundary")
    registry_sha256 = "sha256:" + hashlib.sha256(registry_path.read_bytes()).hexdigest()
    return registry, registry_sha256


def _canonical_payload_sha256(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def validate_information_run(payload: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(dict(payload)),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise V2RunError(
            "\n".join(
                f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
                for error in errors
            )
        )


def load_information_run(path: str | Path) -> dict[str, Any]:
    payload = _load_json(Path(path), label="v2 information run")
    validate_information_run(payload)
    return payload


def _verified_matrix_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    matrix_fields = {
        "information_matrix_sha256": "information_matrix",
        "prior_precision_matrix_sha256": "prior_precision",
        "reference_information_matrix_sha256": "reference_information",
        "reference_direction_basis_sha256": "reference_direction_basis",
    }
    declared = payload["matrix_hashes"]
    verified: dict[str, Any] = {}
    for hash_field, matrix_field in matrix_fields.items():
        computed = canonical_matrix_sha256(payload[matrix_field], name=matrix_field)
        claimed = declared[hash_field]
        if claimed != computed:
            raise V2RunError(
                f"matrix_hashes.{hash_field} does not match server-computed {matrix_field}"
            )
        verified[hash_field] = {
            "declared_sha256": claimed,
            "server_computed_sha256": computed,
            "verified": True,
        }
    return verified


def _recognize_illustrative_fixture(
    payload: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    authority_id = payload.get("reference_authority_id")
    if not isinstance(authority_id, str):
        return None
    for row in registry["illustrative_mechanics_fixtures"]:
        if row["reference_authority_id"] != authority_id:
            continue
        fixture_path = _asset_path(row["fixture_path"])
        raw_sha256 = "sha256:" + hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        if raw_sha256 != row["fixture_raw_sha256"]:
            raise V2RunError("registered illustrative mechanics fixture raw hash mismatch")
        fixture = _load_json(fixture_path, label="illustrative mechanics fixture")
        validate_information_run(fixture)
        fixture_payload_sha256 = _canonical_payload_sha256(fixture)
        if fixture_payload_sha256 != row["fixture_payload_sha256"]:
            raise V2RunError("registered illustrative mechanics fixture payload hash mismatch")
        if _canonical_payload_sha256(payload) != fixture_payload_sha256:
            return None
        if payload["reference_level_hash"] != row["reference_level_hash"]:
            return None
        if payload["matrix_hashes"] != row["matrix_hashes"]:
            return None
        return row
    return None


def score_information_run(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Replay absolute mechanics and fail closed on all reference-level claims."""

    validate_information_run(payload)
    matrix_identity = _verified_matrix_identity(payload)
    absolute = absolute_mechanics(payload["information_matrix"], payload["prior_precision"])
    reference_geometry = validate_reference_geometry(
        payload["reference_information"],
        payload["prior_precision"],
        payload["reference_direction_basis"],
    )
    if absolute.parameter_dimension != reference_geometry.parameter_dimension:
        raise V2RunError("information and reference geometry dimensions differ")

    registry, registry_sha256 = _reference_registry()
    fixture_authority = _recognize_illustrative_fixture(payload, registry)
    illustrative_reference_metrics: dict[str, Any] | None = None
    if fixture_authority is not None:
        internal = reconstruction_metrics(
            payload["information_matrix"],
            payload["prior_precision"],
            payload["reference_information"],
            payload["reference_direction_basis"],
        )
        illustrative_reference_metrics = {
            "metric_contract": "anibench.illustrative-reference-mechanics.v2-candidate1",
            "claim_class": fixture_authority["claim_class"],
            "reference_authority_id": fixture_authority["reference_authority_id"],
            "illustrative_completion_percent": internal.level1_completion_percent,
            "illustrative_overflow": internal.level1_overflow,
            "illustrative_coverage_curve": internal.coverage_curve,
            "illustrative_reference_direction_information": list(
                internal.reference_direction_information
            ),
            "promotion_allowed": False,
            "public_completion_claim_allowed": False,
        }

    run_input_sha256 = _canonical_payload_sha256(payload)
    caller_identity_fields = (
        "parameter_space_hash",
        "prior_metric_hash",
        "reference_level_hash",
        "event_manifest_hash",
        "intervention_design_hash",
        "uncertainty_model_hash",
    )
    return {
        "contract": "anibench.information-replay-packet.v2-candidate1",
        "claim_state": "implementation_candidate_biological_promotion_gated",
        "promotion_allowed": False,
        "benchmark_suite_version": payload["benchmark_suite_version"],
        "lane": payload["lane"],
        "run_input_sha256": run_input_sha256,
        "caller_declared_identity": {key: payload[key] for key in caller_identity_fields},
        "identity_verification": {
            "verification_contract": "anibench.server-derived-identity-verification.v2-candidate1",
            "parameter_dimension": absolute.parameter_dimension,
            "matrix_hashes": matrix_identity,
            "reference_direction_basis_semantics_verified": True,
            "local_reference_registry_sha256": registry_sha256,
            "local_reference_registry_status": registry["status"],
            "caller_declared_reference_authority_id": payload.get("reference_authority_id"),
            "recognized_illustrative_fixture": fixture_authority is not None,
            "recognized_reference_authority_id": (
                fixture_authority["reference_authority_id"]
                if fixture_authority is not None
                else None
            ),
            "promotable_level_1_reference_verified": False,
        },
        "claim_permissions": {
            "absolute_mechanics_replay_allowed": True,
            "illustrative_reference_metrics_allowed": fixture_authority is not None,
            "level_1_completion_claim_allowed": False,
            "public_completion_claim_allowed": False,
            "public_score_allowed": False,
            "public_rank_allowed": False,
        },
        "source_objects": list(payload["source_objects"]),
        "absolute_mechanics": absolute.as_dict(),
        "reference_metrics": None,
        "illustrative_reference_metrics": illustrative_reference_metrics,
    }
