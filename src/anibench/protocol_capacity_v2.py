"""Prospective, non-circular protocol-capacity compiler for AniBench v2.

The compiler accepts the same declarative protocol geometry for every planned
trial.  It emits family-specific
mechanics and typed scenario envelopes; it never accepts caller supplied ranks
or emits an overall score.
"""

from __future__ import annotations

import bisect
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from jsonschema import Draft202012Validator

from .causal_v2 import contrast_information
from .information_v2 import absolute_mechanics, prior_whitened_information


PROTOCOL_CAPACITY_VERSION = "anibench.protocol-capacity.v2-candidate9"
CONDITIONAL_MODERATED_ELIGIBILITY_SCOPE = (
    "pointwise_by_stage_context_policy_over_every_preassignment_history_for_"
    "treatment_by_moderator_information"
)
RANK_RELATIVE_TOLERANCE = 1e-10
# Runtime admission guard only: admitted frontiers are evaluated exactly and
# never pruned or approximated. Changing this limit can only admit or reject a
# protocol; it cannot change any below-limit numeric result.
TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT = 100_000
INDEPENDENT_RANDOMIZED_MECHANISMS = {
    "simple_randomized",
    "stratified_randomized",
    "factorial_randomized",
    "smart_rerandomized",
    "micro_randomized",
}


class ProtocolCapacityError(ValueError):
    """Raised when declarative protocol geometry is invalid or gameable."""


def _rank_receipt(matrix: np.ndarray) -> dict[str, Any]:
    """Return a scale-aware, replayable numerical-rank decision."""

    symmetric = 0.5 * (np.asarray(matrix, dtype=float) + np.asarray(matrix, dtype=float).T)
    if symmetric.ndim != 2 or symmetric.shape[0] != symmetric.shape[1]:
        raise ProtocolCapacityError("rank receipt requires a square matrix")
    if not np.all(np.isfinite(symmetric)):
        raise ProtocolCapacityError("rank receipt matrix must be finite")
    eigenvalues = np.linalg.eigvalsh(symmetric)
    spectral_scale = float(np.max(np.abs(eigenvalues), initial=0.0))
    relative_tolerance = max(
        RANK_RELATIVE_TOLERANCE,
        float(np.finfo(float).eps * max(1, symmetric.shape[0]) * 10.0),
    )
    threshold = relative_tolerance * spectral_scale if spectral_scale > 0.0 else 0.0
    if float(np.min(eigenvalues, initial=0.0)) < -threshold:
        raise ProtocolCapacityError("rank receipt matrix is materially non-PSD")
    return {
        "rule": "eigenvalue > max(configured_relative_tolerance, 10*machine_epsilon*dimension) * max_abs_eigenvalue; exact zero is rank zero",
        "configured_relative_tolerance": RANK_RELATIVE_TOLERANCE,
        "relative_tolerance": relative_tolerance,
        "spectral_scale": spectral_scale,
        "absolute_threshold": threshold,
        "effective_rank": int(np.count_nonzero(eigenvalues > threshold)),
        "minimum_eigenvalue": float(np.min(eigenvalues, initial=0.0)),
        "maximum_eigenvalue": float(np.max(eigenvalues, initial=0.0)),
    }


def _bounded_state_conditioned_propensities(
    *,
    baseline_propensities: Mapping[str, float],
    ordered_policy_ids: tuple[str, ...],
    state_to_policy_contrast_matrix: np.ndarray,
    state_values: np.ndarray,
    conditional_probability_shift: float,
) -> dict[str, float]:
    """Execute the canonical bounded MRT state-to-propensity rule.

    State coordinates are transformed with ``tanh`` and the centered policy
    contrast is divided by the largest row L1 norm. The resulting contrast is
    in [-1, 1] for every policy and sums to zero across policies. Requiring the
    shift to be smaller than every baseline propensity therefore proves strict
    positivity without assuming a state distribution or response prevalence.
    """

    contrast_matrix = np.asarray(state_to_policy_contrast_matrix, dtype=float)
    state = np.asarray(state_values, dtype=float)
    expected_shape = (len(ordered_policy_ids), state.size)
    if (
        state.ndim != 1
        or contrast_matrix.shape != expected_shape
        or not np.all(np.isfinite(contrast_matrix))
        or not np.all(np.isfinite(state))
    ):
        raise ProtocolCapacityError(
            "bounded state-conditioned propensity geometry must be finite and dimensionally aligned"
        )
    if set(baseline_propensities) != set(ordered_policy_ids):
        raise ProtocolCapacityError(
            "bounded state-conditioned propensity geometry must cover the exact policy set"
        )
    baseline = np.asarray(
        [float(baseline_propensities[policy_id]) for policy_id in ordered_policy_ids],
        dtype=float,
    )
    shift = float(conditional_probability_shift)
    row_l1_bound = float(np.max(np.sum(np.abs(contrast_matrix), axis=1), initial=0.0))
    if (
        not np.all(np.isfinite(baseline))
        or not math.isclose(float(np.sum(baseline)), 1.0, abs_tol=1e-9)
        or np.any(baseline <= 0.0)
        or np.any(baseline >= 1.0)
        or not math.isfinite(shift)
        or shift <= 0.0
        or shift >= float(np.min(baseline))
        or row_l1_bound <= 0.0
    ):
        raise ProtocolCapacityError(
            "bounded state-conditioned propensity shift must be finite, positive, "
            "and smaller than every baseline policy propensity"
        )
    centered_contrast = contrast_matrix @ np.tanh(state) / row_l1_bound
    propensities = baseline + shift * centered_contrast
    if (
        not math.isclose(float(np.sum(centered_contrast)), 0.0, abs_tol=1e-9)
        or not math.isclose(float(np.sum(propensities)), 1.0, abs_tol=1e-9)
        or np.any(propensities <= 0.0)
        or np.any(propensities >= 1.0)
    ):
        raise ProtocolCapacityError(
            "bounded state-conditioned propensity rule did not produce a positive distribution"
        )
    return {
        policy_id: float(probability)
        for policy_id, probability in zip(ordered_policy_ids, propensities, strict=True)
    }


def _rectangular_rank_receipt(matrix: np.ndarray) -> dict[str, Any]:
    """Return a scale-aware rank receipt for an arbitrary finite operator."""

    value = np.asarray(matrix, dtype=float)
    if value.ndim != 2 or not value.size:
        raise ProtocolCapacityError("operator rank receipt requires a nonempty matrix")
    if not np.all(np.isfinite(value)):
        raise ProtocolCapacityError("operator rank receipt matrix must be finite")
    singular_values = np.linalg.svd(value, compute_uv=False)
    spectral_scale = float(np.max(np.abs(singular_values), initial=0.0))
    relative_tolerance = max(
        RANK_RELATIVE_TOLERANCE,
        float(np.finfo(float).eps * max(value.shape) * 10.0),
    )
    threshold = relative_tolerance * spectral_scale if spectral_scale > 0.0 else 0.0
    return {
        "rule": "singular_value > max(configured_relative_tolerance, 10*machine_epsilon*max_dimension) * maximum_singular_value; exact zero is rank zero",
        "configured_relative_tolerance": RANK_RELATIVE_TOLERANCE,
        "relative_tolerance": relative_tolerance,
        "spectral_scale": spectral_scale,
        "absolute_threshold": threshold,
        "effective_rank": int(np.count_nonzero(singular_values > threshold)),
        "minimum_singular_value": float(np.min(singular_values, initial=0.0)),
        "maximum_singular_value": float(np.max(singular_values, initial=0.0)),
    }


def _block_diagonal(matrices: Sequence[np.ndarray]) -> np.ndarray:
    """Return a deterministic dense block diagonal without a SciPy dependency."""

    rows = sum(matrix.shape[0] for matrix in matrices)
    columns = sum(matrix.shape[1] for matrix in matrices)
    result = np.zeros((rows, columns), dtype=float)
    row_cursor = 0
    column_cursor = 0
    for matrix in matrices:
        row_stop = row_cursor + matrix.shape[0]
        column_stop = column_cursor + matrix.shape[1]
        result[row_cursor:row_stop, column_cursor:column_stop] = matrix
        row_cursor = row_stop
        column_cursor = column_stop
    return result


def _weighted_median(values: list[float], weights: list[float]) -> float:
    if len(values) != len(weights) or not values:
        raise ProtocolCapacityError("weighted median requires aligned nonempty values")
    if any(not math.isfinite(value) for value in values):
        raise ProtocolCapacityError("weighted median values must be finite")
    if any(not math.isfinite(weight) or weight <= 0 for weight in weights):
        raise ProtocolCapacityError("weighted median weights must be finite and positive")
    ordered = sorted(zip(values, weights, strict=True), key=lambda row: row[0])
    threshold = sum(weights) / 2.0
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= threshold:
            return float(value)
    return float(ordered[-1][0])


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_support(value: float) -> float:
    """Canonicalize support arithmetic across supported Python/NumPy builds.

    Equivalent explicit and compact protocol representations can accumulate the
    same decimal support through a sum or a multiplication.  Both operations
    are mathematically identical but can differ by one binary floating-point
    ulp across Python versions.  Support values are protocol-scale counts, so a
    fixed 12-decimal serialization boundary removes that implementation detail
    without changing any meaningful trial geometry.
    """

    return round(float(value), 12)


def _retention_overlap_support_receipt(
    *,
    outcome_schedules: Iterable[Mapping[str, Any]],
    history_schedules: Iterable[Mapping[str, Any]],
    cohort_population_bound: float,
    availability_participant_support: float,
    history_valid: bool,
) -> dict[str, Any]:
    """Resolve outcome/history support once per source-bound retained lineage.

    A ``registered_nested`` identifier binds nested complete-case supports within
    one parent participant set.  Repeating the same identifier across outcome
    and history schedules therefore names one retained lineage, not independent
    missingness events.  The distribution-free lower bound intersects
    availability with each *unique* registered lineage exactly once.  Unknown
    or absent overlap authority cannot establish a joint moderator population
    and fails closed to zero.
    """

    outcome_rows = list(outcome_schedules)
    history_rows = list(history_schedules)
    all_rows = [*outcome_rows, *history_rows]
    outcome_states = sorted({row["retention_overlap_authority"]["state"] for row in outcome_rows})
    history_states = sorted({row["retention_overlap_authority"]["state"] for row in history_rows})
    outcome_ids = sorted(
        {
            row["retention_overlap_authority"]["retained_participant_set_id"]
            for row in outcome_rows
            if row["retention_overlap_authority"]["state"] == "registered_nested"
        }
    )
    history_ids = sorted(
        {
            row["retention_overlap_authority"]["retained_participant_set_id"]
            for row in history_rows
            if row["retention_overlap_authority"]["state"] == "registered_nested"
        }
    )
    unresolved_schedule_ids = sorted(
        row["schedule_id"]
        for row in all_rows
        if row["retention_overlap_authority"]["state"] != "registered_nested"
    )
    lineage_supports: dict[str, dict[str, Any]] = {}
    for row in all_rows:
        authority = row["retention_overlap_authority"]
        if authority["state"] != "registered_nested":
            continue
        lineage_id = authority["retained_participant_set_id"]
        marginal_support = min(
            cohort_population_bound,
            float(row["participant_count"]) * float(row["retention_fraction"]),
        )
        lineage = lineage_supports.setdefault(
            lineage_id,
            {
                "retained_participant_set_id": lineage_id,
                "marginal_participant_support": marginal_support,
                "schedule_ids": [],
            },
        )
        lineage["marginal_participant_support"] = min(
            float(lineage["marginal_participant_support"]), marginal_support
        )
        lineage["schedule_ids"].append(row["schedule_id"])

    ordered_lineage_supports = []
    for lineage_id in sorted(lineage_supports):
        row = lineage_supports[lineage_id]
        ordered_lineage_supports.append(
            {
                **row,
                "schedule_ids": sorted(set(row["schedule_ids"])),
            }
        )
    shared_ids = sorted(set(outcome_ids) & set(history_ids))
    unique_lineage_count = len(ordered_lineage_supports)
    rule = (
        "max(0, availability_participant_support + "
        "sum(minimum_marginal_support_per_unique_registered_retained_lineage) - "
        "unique_registered_retained_lineage_count * cohort_population_bound)"
    )
    if not history_valid or not outcome_rows or not history_rows:
        state = "blocked_invalid_history_or_outcome_linkage"
        model = "fail_closed_invalid_history_or_outcome_linkage"
        joint_support = 0.0
    elif unresolved_schedule_ids:
        state = "blocked_unknown_or_absent_retention_authority"
        model = "fail_closed_unknown_or_absent_retention_authority"
        joint_support = 0.0
    else:
        state = "resolved_registered_nested"
        model = (
            "shared_registered_nested_lineage_single_frechet"
            if len(outcome_ids) == len(history_ids) == 1 and outcome_ids == history_ids
            else "nonshared_registered_nested_lineages_generalized_frechet"
        )
        joint_support = max(
            0.0,
            availability_participant_support
            + sum(float(row["marginal_participant_support"]) for row in ordered_lineage_supports)
            - unique_lineage_count * cohort_population_bound,
        )
    return {
        "support_role": (
            "schedule_lineage_support_for_extensive_and_causal_geometry_not_"
            "conditional_treatment_by_moderator_information"
        ),
        "state": state,
        "model": model,
        "rule": rule,
        "cohort_population_bound": cohort_population_bound,
        "availability_participant_support": availability_participant_support,
        "outcome_schedule_ids": sorted({row["schedule_id"] for row in outcome_rows}),
        "history_schedule_ids": sorted({row["schedule_id"] for row in history_rows}),
        "outcome_retention_overlap_states": outcome_states,
        "history_retention_overlap_states": history_states,
        "outcome_retained_participant_set_ids": outcome_ids,
        "history_retained_participant_set_ids": history_ids,
        "shared_outcome_history_retained_participant_set_ids": shared_ids,
        "unresolved_retention_schedule_ids": unresolved_schedule_ids,
        "unique_registered_retained_lineage_count": unique_lineage_count,
        "registered_retained_lineage_supports": ordered_lineage_supports,
        "joint_participant_support": joint_support,
    }


def _conditional_moderated_eligibility_receipts(
    *,
    authority: Mapping[str, Any],
    stage_context_id: str,
    epoch_allocations: Mapping[str, Mapping[str, float]],
    policy_aliases: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Resolve pointwise q(H), r(A,H), and their Frechet lower bound.

    Schedule retention and retained-lineage identities are intentionally absent
    from this function.  They remain valid for extensive/causal support, but
    they cannot prove treatment-by-moderator complete-case information.
    """

    state = authority["state"]
    if authority["scope"] != CONDITIONAL_MODERATED_ELIGIBILITY_SCOPE:
        raise ProtocolCapacityError(
            "conditional moderated-eligibility authority has the wrong scope"
        )
    if authority["context_id"] != stage_context_id:
        raise ProtocolCapacityError(
            "conditional moderated-eligibility authority must bind the exact stage context"
        )
    source = {
        "source_object_sha256": authority["source_object_sha256"],
        "source_locator": authority["source_locator"],
    }
    if state in {"unknown", "absent"}:
        return {
            epoch_id: {
                "state": f"blocked_{state}_pointwise_conditional_eligibility",
                "scope": authority["scope"],
                "context_id": stage_context_id,
                "history_scope_id": None,
                "history_scope_semantics": None,
                "minimum_conditional_availability_probability": None,
                "minimum_complete_case_outcome_moderator_retention_probability": None,
                "minimum_pointwise_frechet_joint_eligible_fraction": 0.0,
                "policy_bound_count": 0,
                "policy_bounds_sha256": None,
                "reason": authority["reason"],
                **source,
            }
            for epoch_id in epoch_allocations
        }
    if state != "registered_pointwise_lower_bounds":
        raise ProtocolCapacityError(
            "conditional moderated-eligibility authority state is unsupported"
        )
    if authority["history_scope_semantics"] != (
        "uniform_lower_bound_over_every_preassignment_history_in_stage_context"
    ):
        raise ProtocolCapacityError(
            "conditional moderated-eligibility authority must cover every preassignment history"
        )

    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in authority["bounds"]:
        epoch_id = row["decision_epoch_id"]
        try:
            policy_id = policy_aliases[row["policy_id"]]
        except KeyError as error:
            raise ProtocolCapacityError(
                "conditional moderated-eligibility bound references an unknown policy"
            ) from error
        if epoch_id not in epoch_allocations or policy_id not in epoch_allocations[epoch_id]:
            raise ProtocolCapacityError(
                "conditional moderated-eligibility bound is outside stage epoch-policy support"
            )
        key = (epoch_id, policy_id)
        if key in rows_by_key:
            raise ProtocolCapacityError(
                "conditional moderated-eligibility authority repeats an epoch-policy bound"
            )
        q = float(row["minimum_conditional_availability_probability"])
        retention = float(
            row["minimum_complete_case_outcome_moderator_retention_probability"]
        )
        if (
            not math.isfinite(q)
            or not math.isfinite(retention)
            or not 0.0 <= q <= 1.0
            or not 0.0 <= retention <= 1.0
        ):
            raise ProtocolCapacityError(
                "conditional moderated-eligibility probabilities must be finite in [0, 1]"
            )
        rows_by_key[key] = {
            "decision_epoch_id": epoch_id,
            "policy_id": policy_id,
            "minimum_conditional_availability_probability": q,
            "minimum_complete_case_outcome_moderator_retention_probability": retention,
            "pointwise_frechet_joint_eligible_fraction": max(0.0, q + retention - 1.0),
        }

    expected_keys = {
        (epoch_id, policy_id)
        for epoch_id, allocations in epoch_allocations.items()
        for policy_id in allocations
    }
    if set(rows_by_key) != expected_keys:
        raise ProtocolCapacityError(
            "conditional moderated-eligibility authority must cover every stage epoch-policy pair exactly once"
        )

    receipts: dict[str, dict[str, Any]] = {}
    for epoch_id in epoch_allocations:
        rows = [rows_by_key[(epoch_id, policy_id)] for policy_id in sorted(epoch_allocations[epoch_id])]
        q_values = {row["minimum_conditional_availability_probability"] for row in rows}
        if len(q_values) != 1:
            raise ProtocolCapacityError(
                "q(H) must be policy-invariant within an epoch under the uniform history-scope authority"
            )
        receipts[epoch_id] = {
            "state": "resolved_registered_pointwise_lower_bounds",
            "scope": authority["scope"],
            "context_id": stage_context_id,
            "history_scope_id": authority["history_scope_id"],
            "history_scope_semantics": authority["history_scope_semantics"],
            "minimum_conditional_availability_probability": min(q_values),
            "minimum_complete_case_outcome_moderator_retention_probability": min(
                row[
                    "minimum_complete_case_outcome_moderator_retention_probability"
                ]
                for row in rows
            ),
            "minimum_pointwise_frechet_joint_eligible_fraction": min(
                row["pointwise_frechet_joint_eligible_fraction"] for row in rows
            ),
            "policy_bound_count": len(rows),
            "policy_bounds_sha256": _canonical_sha256(rows),
            "reason": None,
            **source,
        }
    return receipts


def _schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2] / "schemas" / "v2"
    if not root.is_dir():
        root = Path(__file__).resolve().parent / "schemas" / "v2"
    return json.loads((root / "protocol-capacity-input.schema.json").read_text(encoding="utf-8"))


def _validate(protocol: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(dict(protocol)),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        detail = "; ".join(
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise ProtocolCapacityError(detail)


def _walk_coordinates(value: Any, path: tuple[str | int, ...] = ()) -> Iterable[tuple[Any, ...]]:
    if isinstance(value, Mapping) and value.get("state") in {"exact", "interval", "conditional"}:
        yield path, value
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk_coordinates(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_coordinates(child, (*path, index))


def _coordinate_options(coordinate: Mapping[str, Any]) -> list[tuple[str, float]]:
    state = coordinate["state"]
    if state == "exact":
        value = float(coordinate["value"])
        if not math.isfinite(value):
            raise ProtocolCapacityError("coordinate values must be finite")
        return [("exact", value)]
    if state == "interval":
        lower = float(coordinate["lower"])
        upper = float(coordinate["upper"])
        if not math.isfinite(lower) or not math.isfinite(upper):
            raise ProtocolCapacityError("coordinate interval bounds must be finite")
        if lower > upper:
            raise ProtocolCapacityError("coordinate interval lower exceeds upper")
        options = [("lower", lower), ("upper", upper)]
        nominal = coordinate.get("nominal")
        if nominal is not None:
            nominal = float(nominal)
            if not math.isfinite(nominal):
                raise ProtocolCapacityError("coordinate interval nominal must be finite")
            if not lower <= nominal <= upper:
                raise ProtocolCapacityError("coordinate interval nominal is outside support")
            options.insert(1, ("nominal", nominal))
        return list(dict.fromkeys(options))
    options = [(str(row["scenario_id"]), float(row["value"])) for row in coordinate["scenarios"]]
    if any(not math.isfinite(value) for _, value in options):
        raise ProtocolCapacityError("conditional coordinate values must be finite")
    if len({label for label, _ in options}) != len(options):
        raise ProtocolCapacityError("conditional scenario identifiers must be unique")
    return options


def _set_path(value: Any, path: tuple[str | int, ...], replacement: float) -> None:
    cursor = value
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = replacement


def _scenarios(
    protocol: Mapping[str, Any], *, maximum: int = 256
) -> list[tuple[str, dict[str, Any]]]:
    coordinates = list(_walk_coordinates(protocol))
    dimensions: list[list[tuple[str, list[tuple[tuple[str | int, ...], float]]]]] = []
    conditional_groups: dict[str, list[tuple[tuple[str | int, ...], Mapping[str, Any]]]] = {}
    for path, coordinate in coordinates:
        if coordinate["state"] == "conditional":
            conditional_groups.setdefault(coordinate["scenario_group_id"], []).append(
                (path, coordinate)
            )
        else:
            dimensions.append(
                [(label, [(path, number)]) for label, number in _coordinate_options(coordinate)]
            )
    for group_id, grouped in sorted(conditional_groups.items()):
        option_maps = [dict(_coordinate_options(coordinate)) for _, coordinate in grouped]
        labels = set(option_maps[0])
        if any(set(options) != labels for options in option_maps[1:]):
            raise ProtocolCapacityError(
                f"coupled conditional group {group_id!r} has inconsistent scenario IDs"
            )
        dimensions.append(
            [
                (
                    f"{group_id}:{label}",
                    [(path, options[label]) for (path, _), options in zip(grouped, option_maps)],
                )
                for label in sorted(labels)
            ]
        )
    option_sets = dimensions
    scenario_count = math.prod(len(options) for options in option_sets)
    if scenario_count > maximum:
        raise ProtocolCapacityError(
            f"conditional geometry expands to {scenario_count} scenarios; maximum is {maximum}"
        )
    rows: list[tuple[str, dict[str, Any]]] = []
    for combination in itertools.product(*option_sets):
        resolved = copy.deepcopy(dict(protocol))
        labels = []
        for label, assignments in combination:
            for path, number in assignments:
                _set_path(resolved, path, number)
            if label != "exact":
                labels.append(label)
        rows.append(("nominal" if not labels else "|".join(labels), resolved))
    return rows


def _positive(value: float, *, name: str, zero_allowed: bool = False) -> float:
    number = float(value)
    valid = number >= 0 if zero_allowed else number > 0
    if not math.isfinite(number) or not valid:
        qualifier = "nonnegative" if zero_allowed else "positive"
        raise ProtocolCapacityError(f"{name} must be finite and {qualifier}")
    return number


def _effective_estimating_score_repetitions(
    count: int, model: str, correlation: float
) -> float:
    """Effective repeated-decision count from a registered score dependence law."""

    if count < 1 or not math.isfinite(correlation):
        raise ProtocolCapacityError(
            "estimating-score dependence requires a positive count and finite correlation"
        )
    if model == "independent":
        if correlation != 0.0:
            raise ProtocolCapacityError(
                "independent estimating-score dependence requires zero correlation"
            )
        return float(count)
    if model == "ar1":
        if not 0.0 <= correlation < 1.0:
            raise ProtocolCapacityError(
                "AR(1) estimating-score correlation must be in [0, 1)"
            )
        denominator = count + 2.0 * sum(
            (count - lag) * correlation**lag for lag in range(1, count)
        )
        return count**2 / denominator
    if model == "exchangeable":
        lower = -1.0 / max(count - 1, 1)
        if not lower < correlation < 1.0:
            raise ProtocolCapacityError(
                "exchangeable estimating-score correlation is outside PSD support"
            )
        return count / (1.0 + (count - 1) * correlation)
    raise ProtocolCapacityError(
        f"unsupported estimating-score dependence model {model!r}"
    )


def _canonical_signals(protocol: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    canonical: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}
    ancestry_lineages: dict[str, str] = {}
    dimension = int(protocol["parameter_space"]["dimension"])
    for signal in protocol["measurement_geometry"]["signals"]:
        signal_id = signal["signal_id"]
        if signal_id in aliases:
            raise ProtocolCapacityError(f"duplicate signal_id {signal_id!r}")
        feature_id = signal["canonical_feature_id"]
        row = np.asarray(signal["operator_row"], dtype=float)
        if row.shape != (dimension,) or not np.all(np.isfinite(row)):
            raise ProtocolCapacityError(
                f"signal {signal_id!r} operator_row must have parameter dimension {dimension}"
            )
        normalized = {
            "feature_ancestry_id": signal["feature_ancestry_id"],
            "operator_row": row.tolist(),
            "evidence_state": signal["evidence_state"],
            "source_object_sha256": signal["source_object_sha256"],
            "source_locator": signal["source_locator"],
        }
        if signal["evidence_state"] == "conditional":
            include = float(signal["inclusion_coordinate"])
            if include not in {0.0, 1.0}:
                raise ProtocolCapacityError("conditional signal inclusion must resolve to 0 or 1")
        else:
            include = 1.0
        normalized["included_in_primary_mechanics"] = bool(
            signal["evidence_state"] != "unknown" and include == 1.0
        )
        ancestry_id = signal["feature_ancestry_id"]
        ancestry_feature_id = ancestry_lineages.get(ancestry_id)
        if ancestry_feature_id is not None:
            previous_geometry = canonical[ancestry_feature_id]
            if previous_geometry["operator_row"] != normalized["operator_row"]:
                raise ProtocolCapacityError(
                    f"feature ancestry {ancestry_id!r} has conflicting operator geometry"
                )
            aliases[signal_id] = ancestry_feature_id
            continue
        previous = canonical.get(feature_id)
        if previous is not None and previous != normalized:
            raise ProtocolCapacityError(
                f"canonical feature {feature_id!r} has conflicting alias geometry"
            )
        canonical[feature_id] = normalized
        aliases[signal_id] = feature_id
        ancestry_lineages[ancestry_id] = feature_id
    return {
        "features": canonical,
        "aliases": aliases,
        "eligible_features": {
            feature_id
            for feature_id, row in canonical.items()
            if row["included_in_primary_mechanics"]
        },
    }


def _covariance_index(
    protocol: Mapping[str, Any], signal_index: Mapping[str, Any]
) -> tuple[dict[str, tuple[str, int]], dict[str, np.ndarray], dict[str, Any]]:
    memberships: dict[str, tuple[str, int]] = {}
    matrices: dict[str, np.ndarray] = {}
    aliases = signal_index["aliases"]
    for group in protocol["measurement_geometry"]["covariance_groups"]:
        group_id = group["covariance_group_id"]
        if group_id in matrices:
            raise ProtocolCapacityError(f"duplicate covariance_group_id {group_id!r}")
        signal_ids = group["signal_ids"]
        if len(signal_ids) != len(set(signal_ids)):
            raise ProtocolCapacityError(f"covariance group {group_id!r} repeats signal aliases")
        try:
            features = [aliases[signal_id] for signal_id in signal_ids]
        except KeyError as error:
            raise ProtocolCapacityError(
                f"covariance group {group_id!r} references an unknown signal"
            ) from error
        if len(features) != len(set(features)):
            raise ProtocolCapacityError(
                f"covariance group {group_id!r} repeats one canonical feature through aliases"
            )
        covariance = np.asarray(group["covariance"], dtype=float)
        if covariance.shape != (len(features), len(features)):
            raise ProtocolCapacityError(f"covariance group {group_id!r} has wrong dimensions")
        if not np.all(np.isfinite(covariance)):
            raise ProtocolCapacityError(f"covariance group {group_id!r} must be finite")
        if not np.allclose(covariance, covariance.T, atol=1e-10, rtol=0.0):
            raise ProtocolCapacityError(f"covariance group {group_id!r} must be symmetric")
        if float(np.min(np.linalg.eigvalsh(covariance))) <= 0:
            raise ProtocolCapacityError(f"covariance group {group_id!r} must be positive definite")
        matrices[group_id] = covariance
        for index, feature_id in enumerate(features):
            if feature_id in memberships:
                raise ProtocolCapacityError(
                    f"canonical feature {feature_id!r} occurs in multiple covariance groups"
                )
            memberships[feature_id] = (group_id, index)
    missing = set(signal_index["features"]) - set(memberships)
    if missing:
        raise ProtocolCapacityError(
            f"canonical features missing covariance controls: {sorted(missing)}"
        )
    authority = protocol["measurement_geometry"]["joint_covariance_authority"]
    state = authority["state"]
    if state != "complete":
        return (
            memberships,
            matrices,
            {
                "state": f"unresolved_{state}_joint_covariance_authority",
                "authority_state": state,
                "source_object_sha256": authority["source_object_sha256"],
                "source_locator": authority["source_locator"],
                "cross_block_independence_assumed": False,
            },
        )

    joint_signal_ids = authority["signal_ids"]
    if len(joint_signal_ids) != len(set(joint_signal_ids)):
        raise ProtocolCapacityError("joint covariance authority repeats signal aliases")
    try:
        joint_features = [aliases[signal_id] for signal_id in joint_signal_ids]
    except KeyError as error:
        raise ProtocolCapacityError(
            "joint covariance authority references an unknown signal"
        ) from error
    if len(joint_features) != len(set(joint_features)):
        raise ProtocolCapacityError(
            "joint covariance authority repeats one canonical feature through aliases"
        )
    if set(joint_features) != set(signal_index["features"]):
        raise ProtocolCapacityError(
            "complete joint covariance authority must cover every canonical feature exactly once"
        )
    joint = np.asarray(authority["covariance"], dtype=float)
    if joint.shape != (len(joint_features), len(joint_features)):
        raise ProtocolCapacityError("joint covariance authority has wrong dimensions")
    if not np.all(np.isfinite(joint)):
        raise ProtocolCapacityError("joint covariance authority must be finite")
    if not np.allclose(joint, joint.T, atol=1e-10, rtol=0.0):
        raise ProtocolCapacityError("joint covariance authority must be symmetric")
    eigenvalues = np.linalg.eigvalsh(joint)
    scale = float(np.max(np.abs(eigenvalues), initial=0.0))
    pd_tolerance = max(
        RANK_RELATIVE_TOLERANCE,
        float(np.finfo(float).eps * max(1, joint.shape[0]) * 10.0),
    )
    if scale == 0.0 or float(np.min(eigenvalues)) <= pd_tolerance * scale:
        raise ProtocolCapacityError("joint covariance authority must be positive definite")
    joint_group_id = "__complete_joint_covariance_authority__"
    joint_memberships = {
        feature_id: (joint_group_id, index) for index, feature_id in enumerate(joint_features)
    }
    return (
        joint_memberships,
        {joint_group_id: joint},
        {
            "state": "resolved_complete_joint_covariance_authority",
            "authority_state": state,
            "source_object_sha256": authority["source_object_sha256"],
            "source_locator": authority["source_locator"],
            "canonical_feature_count": len(joint_features),
            "joint_covariance_sha256": _canonical_sha256(joint.tolist()),
            "cross_block_independence_assumed": False,
        },
    )


def _event_information(
    feature_ids: set[str],
    signal_index: Mapping[str, Any],
    memberships: Mapping[str, tuple[str, int]],
    matrices: Mapping[str, np.ndarray],
    dimension: int,
) -> np.ndarray:
    blocks = []
    grouped: dict[str, list[tuple[str, int]]] = {}
    for feature_id in sorted(feature_ids):
        group_id, index = memberships[feature_id]
        grouped.setdefault(group_id, []).append((feature_id, index))
    for group_id, rows in sorted(grouped.items()):
        feature_rows = [row[0] for row in rows]
        indices = [row[1] for row in rows]
        operator = np.asarray(
            [signal_index["features"][feature_id]["operator_row"] for feature_id in feature_rows],
            dtype=float,
        )
        covariance = matrices[group_id][np.ix_(indices, indices)]
        blocks.append(operator.T @ np.linalg.solve(covariance, operator))
    return np.sum(blocks, axis=0) if blocks else np.zeros((dimension, dimension), dtype=float)


def _covariance_adjusted_operator_basis(
    feature_ids: set[str],
    signal_index: Mapping[str, Any],
    memberships: Mapping[str, tuple[str, int]],
    matrices: Mapping[str, np.ndarray],
    dimension: int,
) -> np.ndarray:
    """Return registered feature operators whitened by their declared covariance.

    Rows are measurement directions, not caller-provided moderator identifiers.
    Collinear or redundant registered features therefore cannot manufacture
    moderator rank.
    """

    blocks: list[np.ndarray] = []
    grouped: dict[str, list[tuple[str, int]]] = {}
    for feature_id in sorted(feature_ids):
        group_id, index = memberships[feature_id]
        grouped.setdefault(group_id, []).append((feature_id, index))
    for group_id, rows in sorted(grouped.items()):
        feature_rows = [row[0] for row in rows]
        indices = [row[1] for row in rows]
        operator = np.asarray(
            [signal_index["features"][feature_id]["operator_row"] for feature_id in feature_rows],
            dtype=float,
        )
        covariance = matrices[group_id][np.ix_(indices, indices)]
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        whitening = eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues)) @ eigenvectors.T
        blocks.append(whitening @ operator)
    return np.vstack(blocks) if blocks else np.zeros((0, dimension), dtype=float)


def _measurement_feature_gram(
    feature_ids: Sequence[str],
    signal_index: Mapping[str, Any],
    memberships: Mapping[str, tuple[str, int]],
    matrices: Mapping[str, np.ndarray],
    dimension: int,
) -> dict[str, Any]:
    """Return covariance-adjusted observability over declared feature coordinates.

    The result is deliberately a lower-bound object. Features spanning multiple
    covariance groups are unresolved unless a complete joint covariance
    authority has collapsed them into one verified group. Full-row-rank
    observability is required for a joint declared outcome/moderator vector;
    the weakest covariance-adjusted direction, capped at one, continuously
    attenuates downstream causal information and prevents operator rescaling
    from creating super-unit credit.
    """

    ordered = list(dict.fromkeys(feature_ids))
    if not ordered:
        zero = np.zeros((0, 0), dtype=float)
        return {
            "state": "resolved_empty",
            "gram": zero,
            "rank_receipt": _rank_receipt(zero),
            "minimum_observability_factor": 0.0,
            "gram_sha256": _canonical_sha256(zero.tolist()),
        }
    if any(feature_id not in signal_index["features"] for feature_id in ordered):
        raise ProtocolCapacityError(
            "measurement observability references an unknown canonical feature"
        )
    group_ids = {memberships[feature_id][0] for feature_id in ordered}
    if len(group_ids) != 1:
        return {
            "state": "unresolved_joint_covariance_for_declared_feature_vector",
            "gram": None,
            "rank_receipt": None,
            "minimum_observability_factor": None,
            "gram_sha256": None,
        }
    group_id = next(iter(group_ids))
    indices = [memberships[feature_id][1] for feature_id in ordered]
    operator = np.asarray(
        [signal_index["features"][feature_id]["operator_row"] for feature_id in ordered],
        dtype=float,
    )
    covariance = matrices[group_id][np.ix_(indices, indices)]
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    whitening = eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues)) @ eigenvectors.T
    basis = whitening @ operator
    if basis.shape != (len(ordered), dimension):
        raise ProtocolCapacityError(
            "covariance-adjusted measurement operator has inconsistent dimensions"
        )
    gram = 0.5 * (basis @ basis.T + (basis @ basis.T).T)
    receipt = _rank_receipt(gram)
    spectrum = np.linalg.eigvalsh(gram)
    factor = (
        min(1.0, max(0.0, float(np.min(spectrum))))
        if receipt["effective_rank"] == len(ordered)
        else 0.0
    )
    return {
        "state": "resolved_covariance_adjusted_operator_gram",
        "gram": gram,
        "rank_receipt": receipt,
        "minimum_observability_factor": factor,
        "gram_sha256": _canonical_sha256(gram.tolist()),
    }


def _posterior_direction_information(
    information: np.ndarray, prior_precision: np.ndarray
) -> list[float]:
    """Effective information in each declared prior-whitened parameter direction."""

    whitened = prior_whitened_information(information, prior_precision)
    posterior_covariance = np.linalg.solve(
        np.eye(whitened.shape[0], dtype=float) + whitened,
        np.eye(whitened.shape[0], dtype=float),
    )
    posterior_covariance = 0.5 * (posterior_covariance + posterior_covariance.T)
    variances = np.diag(posterior_covariance)
    if np.any(variances <= 0.0):
        raise ProtocolCapacityError("posterior directional variances must be positive")
    values = np.maximum(1.0 / variances - 1.0, 0.0)
    return [round(float(value), 12) for value in values]


def _single_bundle_extensive_candidate(row: Mapping[str, Any], *, dimension: int) -> dict[str, Any]:
    """Compile one bundle without imputing any cross-bundle overlap."""

    support = float(row["retained_participant_support"])
    events = float(row["events_per_participant"])
    correlation = float(row["within_person_repetition_correlation"])
    denominator = 1.0 + (events - 1.0) * correlation
    information = support * events * np.asarray(row["event_information"], dtype=float) / denominator
    bundle_id = str(row["joint_observation_bundle_id"])
    return {
        "candidate_kind": "single_bundle_no_cross_bundle_overlap_imputed",
        "joint_observation_bundle_ids": (bundle_id,),
        "information": information,
        "linked_retained_participant_support": support,
        "retained_participant_events": support * events,
        "total_events": events,
        "temporal_offsets": tuple(row["temporal_offsets"]),
        "trajectory_repetition_correlation": correlation,
        "trajectory_repetition_denominator": denominator,
        "trajectory_effective_information_count": support * events / denominator,
        "retention_overlap_model": "single_bundle_no_cross_bundle_overlap_imputed",
        "support_thresholds": (support,),
        "longitudinal_strata": (
            {
                "participant_support": support,
                "temporal_offsets": tuple(row["temporal_offsets"]),
            },
        ),
        "complexity_receipt": {
            "algorithm": "single_bundle_closed_form_v1",
            "bundle_count": 1,
            "support_threshold_stratum_count": 1,
            "matrix_accumulation_count": 1,
            "peak_live_information_matrix_count": 2,
            "parameter_dimension": dimension,
            "asymptotic_time": "O(d^2)",
            "asymptotic_space": "O(d^2)",
        },
    }


def _registered_nested_extensive_candidate(
    rows: list[dict[str, Any]], *, dimension: int
) -> dict[str, Any]:
    """Compile exact retained-support strata for a registered nested bundle family.

    Each bundle contributes its event-information matrix and canonical PSD
    square root once. Sorting retained support creates disjoint participant
    strata. Compound-symmetric inverse covariance is then evaluated from those
    sufficient statistics; no event, bundle-subset, or PSD-frontier expansion is
    performed. The result is polynomial and exactly equivalent to expanding
    every registered participant stratum under the frozen equicorrelation
    model.
    """

    if not rows:
        raise ProtocolCapacityError("registered nested extensive candidate requires rows")
    support_rows: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        support_rows.setdefault(float(row["retained_participant_support"]), []).append(row)
    thresholds = sorted(support_rows, reverse=True)
    information = np.zeros((dimension, dimension), dtype=float)
    cumulative_event_information = np.zeros((dimension, dimension), dtype=float)
    cumulative_information_root = np.zeros((dimension, dimension), dtype=float)
    cumulative_events = 0.0
    maximum_correlation = max(float(row["within_person_repetition_correlation"]) for row in rows)
    effective_information_count = 0.0
    matrix_accumulations = 0
    cumulative_offsets: set[float] = set()
    longitudinal_strata: list[dict[str, Any]] = []
    for index, threshold in enumerate(thresholds):
        for row in support_rows[threshold]:
            events = float(row["events_per_participant"])
            event_information = np.asarray(row["event_information"], dtype=float)
            eigenvalues, eigenvectors = np.linalg.eigh(
                0.5 * (event_information + event_information.T)
            )
            scale = float(np.max(np.abs(eigenvalues), initial=0.0))
            tolerance = max(1.0, scale) * RANK_RELATIVE_TOLERANCE
            if float(np.min(eigenvalues, initial=0.0)) < -tolerance:
                raise ProtocolCapacityError(
                    "registered nested event information must be positive semidefinite"
                )
            information_root = (
                eigenvectors @ np.diag(np.sqrt(np.maximum(eigenvalues, 0.0))) @ eigenvectors.T
            )
            cumulative_event_information += events * event_information
            cumulative_information_root += events * information_root
            cumulative_events += events
            cumulative_offsets.update(float(value) for value in row["temporal_offsets"])
            matrix_accumulations += 1
        next_threshold = thresholds[index + 1] if index + 1 < len(thresholds) else 0.0
        stratum_support = threshold - next_threshold
        denominator = 1.0 + (cumulative_events - 1.0) * maximum_correlation
        if maximum_correlation == 0.0:
            stratum_information = cumulative_event_information
        else:
            correction = maximum_correlation / denominator
            stratum_information = (
                cumulative_event_information
                - correction * (cumulative_information_root.T @ cumulative_information_root)
            ) / (1.0 - maximum_correlation)
        stratum_information = 0.5 * (stratum_information + stratum_information.T)
        information += stratum_support * stratum_information
        effective_information_count += stratum_support * cumulative_events / denominator
        longitudinal_strata.append(
            {
                "participant_support": stratum_support,
                "temporal_offsets": tuple(sorted(cumulative_offsets)),
            }
        )
        matrix_accumulations += 1

    ordered_rows = sorted(rows, key=lambda row: row["joint_observation_bundle_id"])
    all_events = sum(float(row["events_per_participant"]) for row in rows)
    all_correlation = max(float(row["within_person_repetition_correlation"]) for row in rows)
    all_denominator = 1.0 + (all_events - 1.0) * all_correlation
    return {
        "candidate_kind": "registered_nested_retained_support_threshold_strata",
        "joint_observation_bundle_ids": tuple(
            row["joint_observation_bundle_id"] for row in ordered_rows
        ),
        "information": information,
        "linked_retained_participant_support": min(thresholds),
        "retained_participant_events": sum(
            float(row["retained_participant_support"]) * float(row["events_per_participant"])
            for row in rows
        ),
        "total_events": all_events,
        "temporal_offsets": tuple(
            sorted({offset for row in rows for offset in row["temporal_offsets"]})
        ),
        "trajectory_repetition_correlation": all_correlation,
        "trajectory_repetition_denominator": all_denominator,
        "trajectory_effective_information_count": effective_information_count,
        "retention_overlap_model": "source_bound_registered_nested_threshold_strata",
        "support_thresholds": tuple(thresholds),
        "longitudinal_strata": tuple(longitudinal_strata),
        "complexity_receipt": {
            "algorithm": "registered_nested_retained_support_threshold_strata_v1",
            "bundle_count": len(rows),
            "support_threshold_stratum_count": len(thresholds),
            "matrix_accumulation_count": matrix_accumulations,
            "peak_live_information_matrix_count": 3,
            "parameter_dimension": dimension,
            "asymptotic_time": "O(B log B + B d^2)",
            "asymptotic_space": "O(B + d^2)",
        },
    }


def _measurement_families(protocol: Mapping[str, Any]) -> dict[str, Any]:
    geometry = protocol["measurement_geometry"]
    dimension = int(protocol["parameter_space"]["dimension"])
    prior = np.asarray(protocol["parameter_space"]["prior_precision"], dtype=float)
    if prior.shape != (dimension, dimension):
        raise ProtocolCapacityError("prior_precision dimensions disagree with parameter space")
    if not np.all(np.isfinite(prior)):
        raise ProtocolCapacityError("prior_precision must be finite")
    signal_index = _canonical_signals(protocol)
    memberships, matrices, covariance_authority_receipt = _covariance_index(protocol, signal_index)
    covariance_resolved = covariance_authority_receipt["authority_state"] == "complete"
    aliases = signal_index["aliases"]
    eligible_features = signal_index["eligible_features"]

    modules: dict[str, dict[str, Any]] = {}
    module_evidence_counts: dict[str, int] = {}
    for module in geometry["measurement_modules"]:
        module_id = module["module_id"]
        if module_id in modules:
            raise ProtocolCapacityError(f"duplicate module_id {module_id!r}")
        if module["evidence_state"] == "conditional":
            include = float(module["inclusion_coordinate"])
            if include not in {0.0, 1.0}:
                raise ProtocolCapacityError("conditional module inclusion must resolve to 0 or 1")
        else:
            include = 1.0
        module_enabled = module["evidence_state"] != "unknown" and include == 1.0
        try:
            features = {aliases[signal_id] for signal_id in module["signal_ids"]}
        except KeyError as error:
            raise ProtocolCapacityError(
                f"module {module_id!r} references an unknown signal"
            ) from error
        active_features = features & eligible_features if module_enabled else set()
        unresolved_features = {
            feature_id
            for feature_id in features
            if module["evidence_state"] == "unknown"
            or signal_index["features"][feature_id]["evidence_state"] == "unknown"
        }
        modules[module_id] = {
            **module,
            "canonical_features": features,
            "active_features": active_features,
            "unresolved_features": unresolved_features,
        }
        state = module["evidence_state"]
        module_evidence_counts[state] = module_evidence_counts.get(state, 0) + 1

    schedules: dict[str, dict[str, Any]] = {}
    schedule_aliases: dict[str, str] = {}
    semantic_schedules: dict[tuple[Any, ...], str] = {}
    lineage_schedules: dict[str, tuple[Any, ...]] = {}
    participant_dependence_models: dict[str, str] = {}
    dependence_participant_sets: dict[str, str] = {}
    retained_participant_set_parents: dict[str, str] = {}
    canonical_event_support: dict[tuple[str, float], tuple[Any, ...]] = {}
    bundle_rows: dict[str, list[str]] = {}
    declared_bundle_units: dict[str, str] = {}
    for bundle in geometry["joint_observation_bundles"]:
        bundle_id = bundle["joint_observation_bundle_id"]
        if bundle_id in declared_bundle_units:
            raise ProtocolCapacityError("joint observation bundle identifiers must be unique")
        declared_bundle_units[bundle_id] = bundle["canonical_event_unit_id"]
    for schedule in geometry["participant_event_schedules"]:
        schedule_id = schedule["schedule_id"]
        if schedule_id in schedule_aliases:
            raise ProtocolCapacityError(f"duplicate schedule_id {schedule_id!r}")
        module_ids = sorted(set(schedule["measurement_module_ids"]))
        if any(module_id not in modules for module_id in module_ids):
            raise ProtocolCapacityError(f"schedule {schedule_id!r} references an unknown module")
        schedule_event_unit = schedule["canonical_event_unit_id"]
        module_event_units = {
            modules[module_id]["canonical_event_unit_id"] for module_id in module_ids
        }
        if module_event_units != {schedule_event_unit}:
            raise ProtocolCapacityError(
                f"schedule {schedule_id!r} has incompatible module event units"
            )
        bundle_id = schedule["joint_observation_bundle_id"]
        bundle_event_unit = declared_bundle_units.get(bundle_id)
        if bundle_event_unit is None:
            raise ProtocolCapacityError("schedule references undeclared joint observation bundle")
        if bundle_event_unit != schedule_event_unit:
            raise ProtocolCapacityError(
                f"schedule {schedule_id!r} and joint bundle {bundle_id!r} "
                "have incompatible event units"
            )
        features = set().union(*(modules[module_id]["active_features"] for module_id in module_ids))
        unresolved_features = set().union(
            *(modules[module_id]["unresolved_features"] for module_id in module_ids)
        )
        participant_set_id = schedule["participant_set_id"]
        retention_overlap_authority = schedule["retention_overlap_authority"]
        if retention_overlap_authority["state"] == "registered_nested":
            retained_participant_set_id = retention_overlap_authority["retained_participant_set_id"]
            prior_retained_parent = retained_participant_set_parents.get(
                retained_participant_set_id
            )
            if prior_retained_parent is not None and prior_retained_parent != participant_set_id:
                raise ProtocolCapacityError(
                    "retained participant-set lineage cannot be reused across parent "
                    f"participant sets: {retained_participant_set_id!r} maps to both "
                    f"{prior_retained_parent!r} and {participant_set_id!r}"
                )
            retained_participant_set_parents[retained_participant_set_id] = participant_set_id
        retention_overlap_authority_sha256 = _canonical_sha256(retention_overlap_authority)
        dependence_id = schedule["trajectory_dependence_id"]
        prior_dependence = participant_dependence_models.get(participant_set_id)
        if prior_dependence is not None and prior_dependence != dependence_id:
            raise ProtocolCapacityError(
                f"participant set {participant_set_id!r} is split across trajectory dependence models"
            )
        prior_participant_set = dependence_participant_sets.get(dependence_id)
        if prior_participant_set is not None and prior_participant_set != participant_set_id:
            raise ProtocolCapacityError(
                f"trajectory dependence model {dependence_id!r} is reused across participant sets"
            )
        participant_dependence_models[participant_set_id] = dependence_id
        dependence_participant_sets[dependence_id] = participant_set_id
        participants = _positive(schedule["participant_count"], name="participant_count")
        events = _positive(schedule["events_per_participant"], name="events_per_participant")
        retention = _positive(schedule["retention_fraction"], name="retention_fraction")
        correlation = _positive(
            schedule["within_person_repetition_correlation"],
            name="within_person_repetition_correlation",
            zero_allowed=True,
        )
        offsets = tuple(float(value) for value in schedule["temporal_offsets"])
        if any(not math.isfinite(value) for value in offsets):
            raise ProtocolCapacityError("temporal offsets must be finite")
        if retention > 1 or correlation >= 1:
            raise ProtocolCapacityError("retention must be <= 1 and repetition correlation < 1")
        if schedule["schedule_semantics"] != "exact_offsets":
            raise ProtocolCapacityError(
                "rate_process schedules require a registered window, rate unit, and event "
                "count model; the current deterministic compiler accepts exact_offsets only"
            )
        if not events.is_integer() or int(events) != len(offsets):
            raise ProtocolCapacityError(
                f"schedule {schedule_id!r} exact offsets disagree with event count"
            )
        semantic_key = (
            schedule_event_unit,
            bundle_id,
            participant_set_id,
            dependence_id,
            tuple(sorted(features)),
            tuple(sorted(unresolved_features)),
            offsets,
            participants,
            events,
            retention,
            correlation,
            retention_overlap_authority_sha256,
        )
        lineage_id = schedule["participant_event_lineage_id"]
        lineage_key = (
            schedule["canonical_event_unit_id"],
            participant_set_id,
            dependence_id,
            tuple(module_ids),
            tuple(sorted(features)),
            tuple(sorted(unresolved_features)),
            offsets,
            participants,
            events,
            retention,
            correlation,
            retention_overlap_authority_sha256,
        )
        prior_lineage = lineage_schedules.get(lineage_id)
        if prior_lineage is not None and prior_lineage != lineage_key:
            raise ProtocolCapacityError(
                f"participant-event lineage {lineage_id!r} has conflicting geometry"
            )
        lineage_schedules[lineage_id] = lineage_key
        event_geometry = (
            bundle_id,
            schedule_event_unit,
            participants,
            retention,
            correlation,
        )
        for offset in offsets:
            event_identity = (participant_set_id, offset)
            prior_geometry = canonical_event_support.get(event_identity)
            if prior_geometry is not None and prior_geometry != event_geometry:
                raise ProtocolCapacityError(
                    "canonical participant-event identity has incompatible geometry or "
                    "was split across joint observation bundles"
                )
            canonical_event_support[event_identity] = event_geometry
        canonical_schedule_id = semantic_schedules.get(semantic_key)
        if canonical_schedule_id is not None:
            schedule_aliases[schedule_id] = canonical_schedule_id
            continue
        row = {
            **schedule,
            "measurement_module_ids": module_ids,
            "active_features": features,
            "unresolved_features": unresolved_features,
            "participant_count": participants,
            "events_per_participant": events,
            "retention_fraction": retention,
            "within_person_repetition_correlation": correlation,
            "temporal_offsets": offsets,
        }
        schedules[schedule_id] = row
        schedule_aliases[schedule_id] = schedule_id
        semantic_schedules[semantic_key] = schedule_id
        bundle_rows.setdefault(bundle_id, []).append(schedule_id)

    bundle_ledger = []
    bundle_information: dict[str, np.ndarray] = {}
    temporal_offsets: set[float] = set()
    for bundle_id, schedule_ids in sorted(bundle_rows.items()):
        rows = [schedules[schedule_id] for schedule_id in schedule_ids]
        event_units = {row["canonical_event_unit_id"] for row in rows}
        participant_sets = {row["participant_set_id"] for row in rows}
        offset_sets = {row["temporal_offsets"] for row in rows}
        count_geometry = {
            (
                row["participant_count"],
                row["events_per_participant"],
                row["retention_fraction"],
                row["within_person_repetition_correlation"],
            )
            for row in rows
        }
        retention_overlap_authorities = {
            _canonical_sha256(row["retention_overlap_authority"]): row[
                "retention_overlap_authority"
            ]
            for row in rows
        }
        if (
            len(event_units) != 1
            or len(participant_sets) != 1
            or len(offset_sets) != 1
            or len(count_geometry) != 1
        ):
            raise ProtocolCapacityError(
                f"joint bundle {bundle_id!r} lacks compatible participant-event support"
            )
        if len(retention_overlap_authorities) != 1:
            raise ProtocolCapacityError(
                f"joint bundle {bundle_id!r} has conflicting retention-overlap authority"
            )
        retention_overlap = next(iter(retention_overlap_authorities.values()))
        features = set().union(*(row["active_features"] for row in rows))
        unresolved_features = set().union(*(row["unresolved_features"] for row in rows))
        covariance_group_ids = sorted({memberships[feature_id][0] for feature_id in features})
        if covariance_resolved:
            selected_covariance_group_ids = covariance_group_ids
            information = _event_information(
                features, signal_index, memberships, matrices, dimension
            )
        elif covariance_group_ids:
            covariance_group_candidates = []
            for group_id in covariance_group_ids:
                group_features = {
                    feature_id for feature_id in features if memberships[feature_id][0] == group_id
                }
                group_information = _event_information(
                    group_features, signal_index, memberships, matrices, dimension
                )
                covariance_group_candidates.append(
                    (group_id, group_information, absolute_mechanics(group_information, prior))
                )
            selected_group, information, _ = max(
                covariance_group_candidates,
                key=lambda row: (
                    row[2].absolute_log10_contraction,
                    _rank_receipt(prior_whitened_information(row[1], prior))["effective_rank"],
                    row[0],
                ),
            )
            selected_covariance_group_ids = [selected_group]
        else:
            selected_covariance_group_ids = []
            information = np.zeros((dimension, dimension), dtype=float)
        observer_resolution_state = (
            "unresolved_no_known_observer"
            if not features and unresolved_features
            else (
                "resolved_no_observer"
                if not features
                else "partial_known_lower_bound_with_unresolved_observers"
                if unresolved_features
                or (not covariance_resolved and len(covariance_group_ids) > 1)
                else "resolved"
            )
        )
        mechanics = absolute_mechanics(information, prior)
        bundle_rank_receipt = _rank_receipt(prior_whitened_information(information, prior))
        participants, events, retention, correlation = next(iter(count_geometry))
        effective_repetitions = events / (1.0 + (events - 1.0) * correlation)
        effective_count = participants * retention * effective_repetitions
        bundle_information[bundle_id] = information
        offsets = next(iter(offset_sets))
        temporal_offsets.update(offsets)
        bundle_ledger.append(
            {
                "joint_observation_bundle_id": bundle_id,
                "schedule_ids": sorted(schedule_ids),
                "canonical_event_unit_id": next(iter(event_units)),
                "participant_set_id": next(iter(participant_sets)),
                "temporal_offsets": list(offsets),
                "participant_count": participants,
                "events_per_participant": events,
                "retention_fraction": retention,
                "within_person_repetition_correlation": correlation,
                "retention_overlap_state": retention_overlap["state"],
                "retained_participant_set_id": retention_overlap.get("retained_participant_set_id"),
                "retention_overlap_source_object_sha256": retention_overlap["source_object_sha256"],
                "retention_overlap_source_locator": retention_overlap["source_locator"],
                "observer_resolution_state": observer_resolution_state,
                "declared_covariance_group_ids": covariance_group_ids,
                "selected_covariance_group_ids": selected_covariance_group_ids,
                "unresolved_feature_count": len(unresolved_features),
                "canonical_feature_count": len(features),
                "effective_rank": bundle_rank_receipt["effective_rank"],
                "rank_tolerance_receipt": bundle_rank_receipt,
                "per_bundle_log10_contraction": mechanics.absolute_log10_contraction,
                "information_matrix_sha256": mechanics.information_matrix_sha256,
                "posterior_direction_information": _posterior_direction_information(
                    information, prior
                ),
                "standalone_effective_information_count_not_summed": effective_count,
            }
        )
    if not bundle_ledger:
        raise ProtocolCapacityError("at least one populated joint observation bundle is required")
    numeric_bundle_ledger = [
        row
        for row in bundle_ledger
        if row["observer_resolution_state"] != "unresolved_no_known_observer"
    ]
    selected_bundle = max(
        numeric_bundle_ledger or bundle_ledger,
        key=lambda row: (
            row["per_bundle_log10_contraction"],
            row["effective_rank"],
            row["joint_observation_bundle_id"],
        ),
    )
    intensive_bundle_ledger = [
        {
            key: value
            for key, value in row.items()
            if key
            not in {
                "effective_information_count",
                "standalone_effective_information_count_not_summed",
                "participant_count",
                "events_per_participant",
                "retention_fraction",
                "within_person_repetition_correlation",
            }
        }
        for row in bundle_ledger
    ]
    trajectory_rows: dict[str, dict[str, Any]] = {}
    for bundle in bundle_ledger:
        if bundle["observer_resolution_state"] == "unresolved_no_known_observer":
            continue
        participant_set_id = bundle["participant_set_id"]
        trajectory = trajectory_rows.setdefault(
            participant_set_id,
            {
                "participant_set_id": participant_set_id,
                "participant_counts": [],
                "retained_participant_support": [],
                "joint_observation_bundle_ids": [],
                "schedule_ids": [],
                "offsets": set(),
                "retained_participant_events": 0.0,
                "bundle_candidates": [],
            },
        )
        trajectory["participant_counts"].append(bundle["participant_count"])
        trajectory["retained_participant_support"].append(
            bundle["participant_count"] * bundle["retention_fraction"]
        )
        trajectory["joint_observation_bundle_ids"].append(bundle["joint_observation_bundle_id"])
        trajectory["schedule_ids"].extend(bundle["schedule_ids"])
        trajectory["offsets"].update(bundle["temporal_offsets"])
        trajectory["retained_participant_events"] += (
            bundle["participant_count"]
            * bundle["retention_fraction"]
            * bundle["events_per_participant"]
        )
        trajectory["bundle_candidates"].append(
            {
                "joint_observation_bundle_id": bundle["joint_observation_bundle_id"],
                "retained_participant_support": (
                    bundle["participant_count"] * bundle["retention_fraction"]
                ),
                "participant_count": bundle["participant_count"],
                "events_per_participant": bundle["events_per_participant"],
                "temporal_offsets": tuple(bundle["temporal_offsets"]),
                "within_person_repetition_correlation": bundle[
                    "within_person_repetition_correlation"
                ],
                "retention_overlap_state": bundle["retention_overlap_state"],
                "retained_participant_set_id": bundle["retained_participant_set_id"],
                "selected_covariance_group_ids": tuple(bundle["selected_covariance_group_ids"]),
                "event_information": bundle_information[bundle["joint_observation_bundle_id"]],
            }
        )
    extensive_selection_authorities: dict[str, dict[str, Any]] = {}
    for authority in geometry.get("extensive_selection_authorities", []):
        participant_set_id = authority["participant_set_id"]
        if participant_set_id in extensive_selection_authorities:
            raise ProtocolCapacityError(
                f"duplicate extensive selection authority for participant set "
                f"{participant_set_id!r}"
            )
        extensive_selection_authorities[participant_set_id] = authority

    participant_extensive_candidates: dict[str, dict[str, Any]] = {}
    participant_candidate_counts: dict[str, int] = {}
    extensive_complexity = {
        "bundle_count": 0,
        "registered_nested_bundle_count": 0,
        "unresolved_overlap_bundle_count": 0,
        "nested_group_count": 0,
        "support_threshold_stratum_count": 0,
        "candidate_count": 0,
        "matrix_accumulation_count": 0,
        "peak_live_information_matrix_count": 0,
    }
    for participant_set_id, trajectory in sorted(trajectory_rows.items()):
        bundles = sorted(
            trajectory["bundle_candidates"],
            key=lambda row: row["joint_observation_bundle_id"],
        )
        extensive_complexity["bundle_count"] += len(bundles)
        nested_pool_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        unresolved_rows: list[dict[str, Any]] = []
        for row in bundles:
            if row["retention_overlap_state"] == "registered_nested":
                extensive_complexity["registered_nested_bundle_count"] += 1
                covariance_compatibility_key = (
                    ("complete_joint_covariance_authority",)
                    if covariance_resolved
                    else tuple(row["selected_covariance_group_ids"])
                )
                pool_key = (
                    row["retained_participant_set_id"],
                    covariance_compatibility_key,
                )
                nested_pool_groups.setdefault(pool_key, []).append(row)
            else:
                extensive_complexity["unresolved_overlap_bundle_count"] += 1
                unresolved_rows.append(row)

        candidates: list[dict[str, Any]] = []
        candidate_by_bundle_id: dict[str, dict[str, Any]] = {}
        nested_candidates: list[dict[str, Any]] = []
        for rows in nested_pool_groups.values():
            candidate = _registered_nested_extensive_candidate(
                rows,
                dimension=dimension,
            )
            candidates.append(candidate)
            nested_candidates.append(candidate)
            extensive_complexity["nested_group_count"] += 1
            for bundle_id in candidate["joint_observation_bundle_ids"]:
                candidate_by_bundle_id[bundle_id] = candidate
        for row in unresolved_rows:
            candidate = _single_bundle_extensive_candidate(row, dimension=dimension)
            candidates.append(candidate)
            candidate_by_bundle_id[row["joint_observation_bundle_id"]] = candidate
        if not candidates:
            raise ProtocolCapacityError(
                f"participant set {participant_set_id!r} has no numeric extensive candidate"
            )

        authority = extensive_selection_authorities.get(participant_set_id)
        if authority is not None:
            primary_bundle_id = authority["primary_extensive_bundle_id"]
            selected = candidate_by_bundle_id.get(primary_bundle_id)
            if selected is None:
                raise ProtocolCapacityError(
                    f"primary_extensive_bundle_id {primary_bundle_id!r} for participant set "
                    f"{participant_set_id!r} is absent, belongs to another participant set, "
                    "or has no resolved observer"
                )
            selection_state = "source_bound_primary_extensive_bundle"
        elif len(nested_candidates) == 1:
            selected = nested_candidates[0]
            primary_bundle_id = None
            selection_state = (
                "registered_nested_threshold_strata_with_unresolved_bundles_ledger_only"
                if unresolved_rows
                else "registered_nested_threshold_strata"
            )
        elif len(candidates) == 1:
            selected = candidates[0]
            primary_bundle_id = None
            selection_state = "single_bundle_no_selection_choice"
        else:
            raise ProtocolCapacityError(
                f"participant set {participant_set_id!r} has {len(candidates)} incompatible "
                "extensive candidates; unresolved overlap cannot be selected by identifier "
                "or local contraction. Register one source-bound "
                "primary_extensive_bundle_id or keep the optional bundles out of the "
                "numeric protocol candidate."
            )

        selected_ids = set(selected["joint_observation_bundle_ids"])
        selected["selection_state"] = selection_state
        selected["primary_extensive_bundle_id"] = primary_bundle_id
        selected["selection_authority_source_object_sha256"] = (
            authority["source_object_sha256"] if authority is not None else None
        )
        selected["selection_authority_source_locator"] = (
            authority["source_locator"] if authority is not None else None
        )
        selected["ledger_only_joint_observation_bundle_ids"] = tuple(
            sorted(
                row["joint_observation_bundle_id"]
                for row in bundles
                if row["joint_observation_bundle_id"] not in selected_ids
            )
        )
        participant_extensive_candidates[participant_set_id] = selected
        participant_candidate_counts[participant_set_id] = len(candidates)
        extensive_complexity["candidate_count"] += len(candidates)
        extensive_complexity["support_threshold_stratum_count"] += sum(
            candidate["complexity_receipt"]["support_threshold_stratum_count"]
            for candidate in candidates
        )
        extensive_complexity["matrix_accumulation_count"] += sum(
            candidate["complexity_receipt"]["matrix_accumulation_count"] for candidate in candidates
        )
        extensive_complexity["peak_live_information_matrix_count"] = max(
            extensive_complexity["peak_live_information_matrix_count"],
            max(
                candidate["complexity_receipt"]["peak_live_information_matrix_count"]
                for candidate in candidates
            ),
        )

    declared_participant_sets = set(participant_dependence_models)
    unused_selection_authorities = set(extensive_selection_authorities) - declared_participant_sets
    if unused_selection_authorities:
        raise ProtocolCapacityError(
            "extensive selection authority references unknown participant set(s): "
            + ", ".join(sorted(unused_selection_authorities))
        )

    participant_set_ids = tuple(sorted(participant_extensive_candidates))
    population_authorities: dict[str, dict[str, Any]] = {}
    exact_population_authorities: list[dict[str, Any]] = []
    known_participant_sets = declared_participant_sets
    for authority in geometry.get("population_aggregation_authorities", []):
        authority_id = authority["aggregation_authority_id"]
        if authority_id in population_authorities:
            raise ProtocolCapacityError(
                f"duplicate population aggregation authority {authority_id!r}"
            )
        declared_sets = set(authority["participant_set_ids"])
        unknown_sets = declared_sets - known_participant_sets
        if unknown_sets:
            raise ProtocolCapacityError(
                f"population aggregation authority {authority_id!r} references unknown "
                f"participant set(s): {', '.join(sorted(unknown_sets))}"
            )
        population_authorities[authority_id] = authority
        if set(participant_set_ids) == declared_sets:
            exact_population_authorities.append(authority)
    if not participant_set_ids:
        population_aggregation_receipt = {
            "state": "no_numeric_participant_set_candidate",
            "aggregation_authority_id": None,
            "participant_set_ids": [],
            "source_object_sha256": None,
            "source_locator": None,
        }
    elif len(participant_set_ids) == 1:
        population_aggregation_receipt = {
            "state": "single_participant_set_no_cross_population_sum",
            "aggregation_authority_id": None,
            "participant_set_ids": list(participant_set_ids),
            "source_object_sha256": None,
            "source_locator": None,
        }
    elif len(exact_population_authorities) == 1:
        authority = exact_population_authorities[0]
        population_aggregation_receipt = {
            "state": "source_bound_disjoint_population_sum",
            "aggregation_authority_id": authority["aggregation_authority_id"],
            "participant_set_ids": list(participant_set_ids),
            "source_object_sha256": authority["source_object_sha256"],
            "source_locator": authority["source_locator"],
        }
    elif len(exact_population_authorities) > 1:
        raise ProtocolCapacityError(
            "multiple population aggregation authorities claim the same participant sets"
        )
    else:
        raise ProtocolCapacityError(
            "extensive information for multiple participant sets remains separate: summation "
            "requires one source-bound population_aggregation_authority declaring the exact "
            "sets mutually disjoint"
        )

    extensive = sum(
        (
            participant_extensive_candidates[participant_set_id]["information"]
            for participant_set_id in participant_set_ids
        ),
        np.zeros((dimension, dimension), dtype=float),
    )
    extensive_complexity.update(
        {
            "algorithm": "registered_nested_threshold_strata_and_source_bound_primary_v1",
            "participant_set_count": len(participant_set_ids),
            "cross_population_matrix_addition_count": max(0, len(participant_set_ids) - 1),
            "parameter_dimension": dimension,
            "asymptotic_time": "O(B log B + B d^2 + P d^2)",
            "asymptotic_space": "O(B + P + d^2)",
            "subset_enumeration_performed": False,
            "psd_frontier_enumeration_performed": False,
            "numeric_frontier_cap": None,
        }
    )
    trajectory_ledger = []
    longitudinal_strata: list[dict[str, Any]] = []
    for participant_set_id, trajectory in sorted(trajectory_rows.items()):
        declared_offsets = sorted(trajectory.pop("offsets"))
        participant_counts = trajectory.pop("participant_counts")
        trajectory.pop("retained_participant_support")
        trajectory.pop("bundle_candidates")
        trajectory.pop("retained_participant_events")
        selection = participant_extensive_candidates[participant_set_id]
        offsets = list(selection["temporal_offsets"])
        for stratum in selection["longitudinal_strata"]:
            stratum_offsets = list(stratum["temporal_offsets"])
            longitudinal_strata.append(
                {
                    "participant_set_id": participant_set_id,
                    "participant_support": stratum["participant_support"],
                    "distinct_temporal_offsets": len(stratum_offsets),
                    "within_participant_span": (
                        max(stratum_offsets) - min(stratum_offsets) if stratum_offsets else 0.0
                    ),
                }
            )
        trajectory_ledger.append(
            {
                **trajectory,
                "participant_set_id": participant_set_id,
                "joint_observation_bundle_ids": sorted(trajectory["joint_observation_bundle_ids"]),
                "selected_joint_observation_bundle_ids": list(
                    selection["joint_observation_bundle_ids"]
                ),
                "extensive_selected_joint_observation_bundle_ids": list(
                    selection["joint_observation_bundle_ids"]
                ),
                "optional_subset_candidate_count": participant_candidate_counts[participant_set_id],
                "extensive_selection_state": selection["selection_state"],
                "primary_extensive_bundle_id": selection["primary_extensive_bundle_id"],
                "selection_authority_source_object_sha256": selection[
                    "selection_authority_source_object_sha256"
                ],
                "selection_authority_source_locator": selection[
                    "selection_authority_source_locator"
                ],
                "ledger_only_joint_observation_bundle_ids": list(
                    selection["ledger_only_joint_observation_bundle_ids"]
                ),
                "support_thresholds": list(selection["support_thresholds"]),
                "extensive_complexity_receipt": selection["complexity_receipt"],
                "schedule_ids": sorted(trajectory["schedule_ids"]),
                "participant_count_minimum": min(participant_counts),
                "participant_count_maximum": max(participant_counts),
                "linked_retained_participant_support": selection[
                    "linked_retained_participant_support"
                ],
                "distinct_temporal_offsets": len(offsets),
                "temporal_offsets": offsets,
                "within_participant_span": max(offsets) - min(offsets) if offsets else 0.0,
                "trajectory_repetition_correlation": selection["trajectory_repetition_correlation"],
                "trajectory_repetition_denominator": selection["trajectory_repetition_denominator"],
                "trajectory_dependence_id": participant_dependence_models[participant_set_id],
                "trajectory_effective_information_count": selection[
                    "trajectory_effective_information_count"
                ],
                "retained_participant_events": selection["retained_participant_events"],
                "repetition_model": selection["complexity_receipt"]["algorithm"],
                "retention_overlap_model": selection["retention_overlap_model"],
                "declared_calendar_offset_count_not_follow_up": len(declared_offsets),
            }
        )
    extensive_mechanics = absolute_mechanics(extensive, prior)
    extensive_rank_receipt = _rank_receipt(prior_whitened_information(extensive, prior))
    trajectory_spans = [row["within_participant_span"] for row in trajectory_ledger]
    trajectory_offset_counts = [row["distinct_temporal_offsets"] for row in trajectory_ledger]
    longitudinal_stratum_weights = [row["participant_support"] for row in longitudinal_strata]
    longitudinal_stratum_spans = [row["within_participant_span"] for row in longitudinal_strata]
    longitudinal_stratum_offset_counts = [
        row["distinct_temporal_offsets"] for row in longitudinal_strata
    ]
    evidence_counts: dict[str, int] = {}
    ancestry_ids: set[str] = set()
    for feature in signal_index["features"].values():
        evidence_counts[feature["evidence_state"]] = (
            evidence_counts.get(feature["evidence_state"], 0) + 1
        )
        ancestry_ids.add(feature["feature_ancestry_id"])
    bundle_resolution_states = {row["observer_resolution_state"] for row in bundle_ledger}
    measurement_numeric_available = bool(numeric_bundle_ledger)
    measurement_resolution_state = (
        "resolved"
        if bundle_resolution_states == {"resolved"}
        else (
            "partial_known_lower_bound_with_unresolved_observers"
            if measurement_numeric_available
            else "unresolved_unknown_observer_evidence"
        )
    )
    for row in bundle_ledger:
        if row["observer_resolution_state"] == "unresolved_no_known_observer":
            for key in (
                "effective_rank",
                "per_bundle_log10_contraction",
                "information_matrix_sha256",
                "posterior_direction_information",
            ):
                row[key] = None
            row["rank_tolerance_receipt"] = None
    for row in intensive_bundle_ledger:
        if row["observer_resolution_state"] == "unresolved_no_known_observer":
            for key in (
                "effective_rank",
                "per_bundle_log10_contraction",
                "information_matrix_sha256",
                "posterior_direction_information",
            ):
                row[key] = None
            row["rank_tolerance_receipt"] = None
    selected_retained_participant_events = sum(
        participant_extensive_candidates[participant_set_id]["retained_participant_events"]
        for participant_set_id in participant_set_ids
    )
    return {
        "intensive": {
            "definition": "maximum one explicitly joint-observed bundle; incompatible bundles never union",
            "resolution_state": measurement_resolution_state,
            "selected_joint_observation_bundle_id": selected_bundle["joint_observation_bundle_id"],
            "canonical_feature_count": selected_bundle["canonical_feature_count"],
            "feature_ancestry_count": len(ancestry_ids),
            "effective_rank": (
                selected_bundle["effective_rank"] if measurement_numeric_available else None
            ),
            "rank_tolerance_receipt": (
                selected_bundle["rank_tolerance_receipt"] if measurement_numeric_available else None
            ),
            "maximum_joint_bundle_log10_contraction": (
                selected_bundle["per_bundle_log10_contraction"]
                if measurement_numeric_available
                else None
            ),
            "bundle_ledger": intensive_bundle_ledger,
            "information_matrix_sha256": (
                selected_bundle["information_matrix_sha256"]
                if measurement_numeric_available
                else None
            ),
            "posterior_direction_information": (
                selected_bundle["posterior_direction_information"]
                if measurement_numeric_available
                else None
            ),
        },
        "extensive": {
            "definition": "source-bound retained reach from registered nested support strata or an explicit primary bundle; cross-population information is summed only under an exact disjoint-population authority",
            "resolution_state": measurement_resolution_state,
            "retained_participant_events": selected_retained_participant_events,
            "effective_rank": (
                extensive_rank_receipt["effective_rank"] if trajectory_ledger else None
            ),
            "rank_tolerance_receipt": (extensive_rank_receipt if trajectory_ledger else None),
            "retained_log10_contraction": (
                extensive_mechanics.absolute_log10_contraction if trajectory_ledger else None
            ),
            "bundle_ledger": bundle_ledger,
            "information_matrix_sha256": (
                extensive_mechanics.information_matrix_sha256 if trajectory_ledger else None
            ),
            "posterior_direction_information": (
                _posterior_direction_information(extensive, prior) if trajectory_ledger else None
            ),
            "population_aggregation_receipt": population_aggregation_receipt,
            "complexity_receipt": extensive_complexity,
        },
        "measurement_audit": {
            "resolution_state": measurement_resolution_state,
            "joint_covariance_authority": covariance_authority_receipt,
            "evidence_state_counts": evidence_counts,
            "module_evidence_state_counts": module_evidence_counts,
            "excluded_primary_feature_count": len(signal_index["features"])
            - len(eligible_features),
            "alias_count_removed": len(aliases) - len(signal_index["features"]),
            "menu_module_count": len(modules),
            "schedule_alias_count_removed": len(schedule_aliases) - len(schedules),
            "joint_observation_bundle_count": len(bundle_ledger),
            "trajectory_dependence_model_count": len(dependence_participant_sets),
        },
        "longitudinal": {
            "definition": "within-participant-set trajectories; disjoint sets never form follow-up",
            "resolution_state": measurement_resolution_state,
            "trajectory_ledger": trajectory_ledger,
            "maximum_within_participant_distinct_offsets": max(trajectory_offset_counts, default=0),
            "median_within_participant_distinct_offsets": float(
                np.median(trajectory_offset_counts) if trajectory_offset_counts else 0.0
            ),
            "maximum_within_participant_span": max(trajectory_spans, default=0.0),
            "median_within_participant_span": float(
                np.median(trajectory_spans) if trajectory_spans else 0.0
            ),
            "participant_weighted_median_distinct_offsets": (
                _weighted_median(
                    [float(value) for value in longitudinal_stratum_offset_counts],
                    longitudinal_stratum_weights,
                )
                if longitudinal_stratum_weights
                else 0.0
            ),
            "participant_weighted_median_span": (
                _weighted_median(
                    [float(value) for value in longitudinal_stratum_spans],
                    longitudinal_stratum_weights,
                )
                if longitudinal_stratum_weights
                else 0.0
            ),
            "retained_participant_events": selected_retained_participant_events,
            "global_calendar_coverage_audit": {
                "not_longitudinal_follow_up": True,
                "distinct_offsets": len(temporal_offsets),
                "calendar_span": (
                    max(temporal_offsets) - min(temporal_offsets) if temporal_offsets else 0.0
                ),
            },
        },
        "_schedule_registry": schedules,
        "_schedule_aliases": schedule_aliases,
        "_eligible_features": eligible_features,
        "_signal_index": signal_index,
        "_covariance_memberships": memberships,
        "_covariance_matrices": matrices,
        "_parameter_dimension": dimension,
        "_measurement_resolution_state": measurement_resolution_state,
    }


def _causal_family(
    protocol: Mapping[str, Any],
    schedules: Mapping[str, Mapping[str, Any]],
    schedule_aliases: Mapping[str, str],
    eligible_features: set[str],
    signal_index: Mapping[str, Any],
    covariance_memberships: Mapping[str, tuple[str, int]],
    covariance_matrices: Mapping[str, np.ndarray],
    parameter_dimension: int,
    measurement_resolution_state: str,
) -> dict[str, Any]:
    causal = protocol["causal_geometry"]
    component_aliases: dict[str, str] = {}
    component_ids: set[str] = set()
    for component in causal["operator_components"]:
        if component["component_id"] in component_aliases:
            raise ProtocolCapacityError("operator component identifiers must be unique")
        component_aliases[component["component_id"]] = component["canonical_operator_id"]
        component_ids.add(component["canonical_operator_id"])
    ordered_components = sorted(component_ids)
    component_index = {value: index for index, value in enumerate(ordered_components)}

    policy_aliases: dict[str, str] = {}
    canonical_policies: dict[str, tuple[str, ...]] = {}
    policy_signatures: dict[tuple[str, ...], str] = {}
    for policy in causal["policies"]:
        if policy["policy_id"] in policy_aliases:
            raise ProtocolCapacityError("policy identifiers must be unique")
        try:
            components = tuple(
                sorted({component_aliases[value] for value in policy["operator_component_ids"]})
            )
        except KeyError as error:
            raise ProtocolCapacityError("policy references unknown operator component") from error
        # A rule identifier is provenance, not executable rule geometry. Until
        # a rule operator is registered, identical component sets are one
        # numeric contrast and cannot buy rank through renaming.
        signature = components
        canonical_id = policy_signatures.get(signature, policy["policy_id"])
        policy_signatures[signature] = canonical_id
        policy_aliases[policy["policy_id"]] = canonical_id
        canonical_policies[canonical_id] = components
    policy_ids = sorted(canonical_policies)
    policy_index = {value: index for index, value in enumerate(policy_ids)}
    policy_components = np.zeros((len(policy_ids), len(ordered_components)), dtype=float)
    for policy_id, components in canonical_policies.items():
        for component_id in components:
            policy_components[policy_index[policy_id], component_index[component_id]] = 1.0

    decision_rule_operators: dict[str, dict[str, Any]] = {}
    for rule in causal["decision_rule_operators"]:
        rule_id = rule["decision_rule_operator_id"]
        if rule_id in decision_rule_operators:
            raise ProtocolCapacityError("decision rule operator identifiers must be unique")
        try:
            canonical_rule_policies = [policy_aliases[value] for value in rule["policy_ids"]]
        except KeyError as error:
            raise ProtocolCapacityError(
                "decision rule operator references an unknown policy"
            ) from error
        if len(canonical_rule_policies) != len(set(canonical_rule_policies)):
            raise ProtocolCapacityError(
                "decision rule operator policies must remain distinct after canonicalization"
            )
        rule_state = rule["state"]
        receipt = None
        state_feature_ids: tuple[str, ...] = ()
        contrast_matrix = None
        response_state_score_axis_ids: tuple[str, ...] = ()
        response_state_score_matrix = None
        policy_interaction_basis_matrix = None
        conditional_probability_shift = None
        if rule_state == "registered_state_dependent":
            state_feature_ids = tuple(rule["state_feature_ids"])
            if not set(state_feature_ids) <= set(signal_index["features"]):
                raise ProtocolCapacityError(
                    "decision rule operator references an unknown state feature"
                )
            contrast_matrix = np.asarray(rule["state_to_policy_contrast_matrix"], dtype=float)
            expected_shape = (len(canonical_rule_policies), len(state_feature_ids))
            if contrast_matrix.shape != expected_shape or not np.all(np.isfinite(contrast_matrix)):
                raise ProtocolCapacityError(
                    "state-to-policy contrast matrix must be finite and align policy rows with state-feature columns"
                )
            column_scales = np.max(np.abs(contrast_matrix), axis=0, initial=0.0)
            column_sums = np.sum(contrast_matrix, axis=0)
            if any(
                not math.isclose(
                    float(total),
                    0.0,
                    abs_tol=RANK_RELATIVE_TOLERANCE * float(scale),
                )
                for total, scale in zip(column_sums, column_scales, strict=True)
                if scale > 0.0
            ):
                raise ProtocolCapacityError(
                    "state-to-policy rule columns must be policy contrasts that sum to zero"
                )
            receipt = _rectangular_rank_receipt(contrast_matrix)
            if receipt["effective_rank"] == 0:
                raise ProtocolCapacityError(
                    "registered state-dependent rule must contain a nonzero policy contrast"
                )
            state_conditioned_rule_fields = (
                "response_state_score_axis_ids",
                "response_state_score_matrix",
                "policy_interaction_basis_matrix",
                "conditional_probability_shift",
            )
            state_conditioned_rule_presence = [
                field in rule for field in state_conditioned_rule_fields
            ]
            if any(state_conditioned_rule_presence) and not all(state_conditioned_rule_presence):
                raise ProtocolCapacityError(
                    "state-conditioned decision-rule extension must declare every "
                    "response-axis field"
                )
            if all(state_conditioned_rule_presence):
                response_state_score_axis_ids = tuple(rule["response_state_score_axis_ids"])
                if len(response_state_score_axis_ids) != len(set(response_state_score_axis_ids)):
                    raise ProtocolCapacityError(
                        "response-state score axis identifiers must be unique"
                    )
                response_state_score_matrix = np.asarray(
                    rule["response_state_score_matrix"], dtype=float
                )
                policy_interaction_basis_matrix = np.asarray(
                    rule["policy_interaction_basis_matrix"], dtype=float
                )
                axis_count = len(response_state_score_axis_ids)
                if (
                    response_state_score_matrix.shape != (axis_count, len(state_feature_ids))
                    or policy_interaction_basis_matrix.shape
                    != (len(canonical_rule_policies), axis_count)
                    or not np.all(np.isfinite(response_state_score_matrix))
                    or not np.all(np.isfinite(policy_interaction_basis_matrix))
                ):
                    raise ProtocolCapacityError(
                        "state-conditioned response-score and policy-interaction matrices "
                        "must be finite and dimensionally aligned"
                    )
                reconstructed = policy_interaction_basis_matrix @ response_state_score_matrix
                if not np.allclose(
                    reconstructed,
                    contrast_matrix,
                    rtol=0.0,
                    atol=RANK_RELATIVE_TOLERANCE
                    * max(1.0, float(np.max(np.abs(contrast_matrix), initial=0.0))),
                ):
                    raise ProtocolCapacityError(
                        "state-to-policy contrast matrix must equal the registered policy-interaction basis times response-score matrix"
                    )
                basis_column_sums = np.sum(policy_interaction_basis_matrix, axis=0)
                if not np.allclose(
                    basis_column_sums,
                    0.0,
                    rtol=0.0,
                    atol=RANK_RELATIVE_TOLERANCE,
                ):
                    raise ProtocolCapacityError(
                        "state-conditioned policy-interaction basis columns must be centered"
                    )
                if (
                    _rectangular_rank_receipt(policy_interaction_basis_matrix)["effective_rank"]
                    != axis_count
                ):
                    raise ProtocolCapacityError(
                        "state-conditioned policy-interaction basis must have full "
                        "response-axis rank"
                    )
                conditional_probability_shift = float(rule["conditional_probability_shift"])
                if (
                    not math.isfinite(conditional_probability_shift)
                    or conditional_probability_shift <= 0.0
                ):
                    raise ProtocolCapacityError(
                        "state-conditioned probability shift must be finite and positive"
                    )
        decision_rule_operators[rule_id] = {
            "decision_rule_operator_id": rule_id,
            "state": rule_state,
            "canonical_policy_ids": tuple(canonical_rule_policies),
            "state_feature_ids": state_feature_ids,
            "state_to_policy_contrast_matrix": contrast_matrix,
            "rank_tolerance_receipt": receipt,
            "response_state_score_axis_ids": response_state_score_axis_ids,
            "response_state_score_matrix": response_state_score_matrix,
            "policy_interaction_basis_matrix": policy_interaction_basis_matrix,
            "conditional_probability_shift": conditional_probability_shift,
            "source_object_sha256": rule["source_object_sha256"],
            "source_locator": rule["source_locator"],
        }

    estimands: dict[str, dict[str, Any]] = {}
    for estimand in causal["estimands"]:
        estimand_id = estimand["estimand_id"]
        if estimand_id in estimands:
            raise ProtocolCapacityError("estimand identifiers must be unique")
        start = float(estimand["horizon_start_offset_exclusive"])
        end = float(estimand["horizon_end_offset_inclusive"])
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            raise ProtocolCapacityError("estimand horizon must be finite and nonempty")
        contrasts = []
        contrast_ids: set[str] = set()
        for contrast in estimand["operator_contrasts"]:
            contrast_id = contrast["contrast_id"]
            if contrast_id in contrast_ids:
                raise ProtocolCapacityError("operator contrast identifiers must be unique")
            contrast_ids.add(contrast_id)
            coefficients: dict[str, float] = {}
            for coefficient in contrast["policy_coefficients"]:
                try:
                    policy_id = policy_aliases[coefficient["policy_id"]]
                except KeyError as error:
                    raise ProtocolCapacityError(
                        "operator contrast references an unknown policy"
                    ) from error
                value = float(coefficient["coefficient"])
                if not math.isfinite(value):
                    raise ProtocolCapacityError("operator contrast coefficients must be finite")
                coefficients[policy_id] = coefficients.get(policy_id, 0.0) + value
            coefficients = {key: value for key, value in coefficients.items() if value != 0.0}
            coefficient_scale = max((abs(value) for value in coefficients.values()), default=0.0)
            if len(coefficients) < 2 or coefficient_scale == 0.0:
                raise ProtocolCapacityError("operator contrast must retain two canonical policies")
            if not math.isclose(
                sum(coefficients.values()),
                0.0,
                abs_tol=RANK_RELATIVE_TOLERANCE * coefficient_scale,
            ):
                raise ProtocolCapacityError("operator contrast coefficients must sum to zero")
            normalized = {key: value / coefficient_scale for key, value in coefficients.items()}
            first = next(value for _, value in sorted(normalized.items()) if value != 0.0)
            if first < 0:
                normalized = {key: -value for key, value in normalized.items()}
            contrasts.append({"contrast_id": contrast_id, "coefficients": normalized})
        outcome_features = set(estimand["outcome_feature_ids"])
        if not outcome_features <= set(signal_index["features"]):
            raise ProtocolCapacityError("estimand references an unknown outcome feature")
        powered_direction_ids = list(estimand.get("powered_outcome_direction_ids", []))
        powered_direction_rule = estimand.get("powered_outcome_direction_multiplicity_rule")
        if (
            powered_direction_ids
            and {f"feature-{direction_id}" for direction_id in powered_direction_ids}
            != outcome_features
        ):
            raise ProtocolCapacityError(
                "powered biological directions must bind the exact ordered estimand outcome features"
            )
        estimands[estimand_id] = {
            **estimand,
            "horizon_start_offset_exclusive": start,
            "horizon_end_offset_inclusive": end,
            "outcome_features": outcome_features,
            "canonical_operator_contrasts": contrasts,
            "geometry_sha256": _canonical_sha256(
                {
                    "outcome_definition_id": estimand["outcome_definition_id"],
                    "outcome_feature_ids": sorted(outcome_features),
                    "powered_outcome_direction_ids": powered_direction_ids,
                    "powered_outcome_direction_multiplicity_rule": powered_direction_rule,
                    "operator_contrasts": contrasts,
                    "horizon_start_offset_exclusive": start,
                    "horizon_end_offset_inclusive": end,
                }
            ),
        }

    def resolve_schedule_ids(values: list[str]) -> list[Mapping[str, Any]]:
        try:
            canonical_ids = {schedule_aliases[value] for value in values}
            return [schedules[value] for value in sorted(canonical_ids)]
        except KeyError as error:
            raise ProtocolCapacityError("causal geometry references unknown schedule") from error

    stage_ledger = []
    stage_internal_geometry: dict[str, dict[str, Any]] = {}
    declared_stage_ids = [stage["stage_id"] for stage in causal["assignment_stages"]]
    if len(declared_stage_ids) != len(set(declared_stage_ids)):
        raise ProtocolCapacityError("assignment stage identifiers must be unique")
    seen_stage_signatures: set[str] = set()
    for stage in causal["assignment_stages"]:
        signature = _canonical_sha256(
            {
                key: value
                for key, value in stage.items()
                if key not in {"stage_id", "source_object_sha256", "source_locator"}
            }
        )
        if signature in seen_stage_signatures:
            continue
        seen_stage_signatures.add(signature)
        participants = _positive(stage["participant_count"], name="stage participant_count")
        decisions = _positive(stage["decisions_per_participant"], name="decisions")
        sequential_assignment_probability = float(stage["sequential_assignment_probability"])
        if not math.isfinite(sequential_assignment_probability):
            raise ProtocolCapacityError("sequential assignment probabilities must be finite")
        allocations: dict[str, float] = {}
        for row in stage["policy_allocations"]:
            if row["policy_id"] not in policy_aliases:
                raise ProtocolCapacityError("assignment stage references unknown policy")
            policy_id = policy_aliases[row["policy_id"]]
            probability = float(row["probability"])
            if not math.isfinite(probability):
                raise ProtocolCapacityError("assignment probabilities must be finite")
            allocations[policy_id] = allocations.get(policy_id, 0.0) + probability
        if not math.isclose(sum(allocations.values()), 1.0, abs_tol=1e-9):
            raise ProtocolCapacityError("assignment probabilities must sum to one")
        if any(value <= 0 or value >= 1 for value in allocations.values()):
            raise ProtocolCapacityError("canonical assignment probabilities require positivity")
        try:
            decision_rule = decision_rule_operators[stage["decision_rule_operator_id"]]
        except KeyError as error:
            raise ProtocolCapacityError(
                "assignment stage references an unknown decision rule operator"
            ) from error
        if set(decision_rule["canonical_policy_ids"]) != set(allocations):
            raise ProtocolCapacityError(
                "decision rule operator policy support must exactly match stage allocation support"
            )
        component_propensities = [
            sum(
                probability * policy_components[policy_index[policy_id], component_column]
                for policy_id, probability in allocations.items()
            )
            for component_column in range(len(ordered_components))
        ]
        randomized_component_propensities = [
            probability for probability in component_propensities if 0.0 < probability < 1.0
        ]
        allocation_assignment_variance_bound = min(
            (
                probability * (1.0 - probability)
                for probability in randomized_component_propensities
            ),
            default=0.0,
        )
        declared_assignment_variance_bound = sequential_assignment_probability * (
            1.0 - sequential_assignment_probability
        )
        effective_assignment_variance_bound = min(
            allocation_assignment_variance_bound,
            declared_assignment_variance_bound,
        )
        decision_epochs = stage["decision_epochs"]
        regular_process = stage.get("regular_decision_epoch_process")
        regular_decision_count = 1
        regular_interval = None
        regular_readback = None
        regular_start_offset = None
        epoch_multiplicity: dict[str, int] = {
            row["decision_epoch_id"]: 1 for row in decision_epochs
        }
        if regular_process is not None:
            if stage["assignment_mechanism"] != "micro_randomized":
                raise ProtocolCapacityError(
                    "regular decision-epoch processes are supported only for micro-randomized stages"
                )
            if len(decision_epochs) != 1:
                raise ProtocolCapacityError(
                    "regular decision-epoch process requires exactly one explicit template epoch"
                )
            template = decision_epochs[0]
            decision_count = int(regular_process["decision_count"])
            decisions_per_day = int(regular_process["decisions_per_day"])
            duration_days = int(regular_process["duration_days"])
            interval = float(regular_process["decision_interval_days"])
            readback = float(regular_process["proximal_readback_offset_days"])
            start_offset = float(regular_process["start_offset"])
            if not all(math.isfinite(value) for value in (interval, readback, start_offset)):
                raise ProtocolCapacityError("regular decision-epoch process offsets must be finite")
            if (
                regular_process["template_decision_epoch_id"] != template["decision_epoch_id"]
                or not math.isclose(
                    float(template["decision_time_offset"]), start_offset, abs_tol=1e-12
                )
                or not math.isclose(
                    float(stage["decision_time_offset"]), start_offset, abs_tol=1e-12
                )
            ):
                raise ProtocolCapacityError(
                    "regular decision-epoch process must bind its exact template and stage start offset"
                )
            if (
                decision_count != decisions_per_day * duration_days
                or not math.isclose(interval * decisions_per_day, 1.0, rel_tol=0.0, abs_tol=1e-12)
                or not math.isclose(decisions, float(decision_count), abs_tol=1e-9)
            ):
                raise ProtocolCapacityError(
                    "regular decision-epoch count must equal decisions_per_day times duration_days and the declared stage count"
                )
            if not (0.0 < readback < interval):
                raise ProtocolCapacityError(
                    "regular proximal readback must be strictly postdecision and before the next decision"
                )
            epoch_multiplicity[template["decision_epoch_id"]] = decision_count
            regular_decision_count = decision_count
            regular_interval = interval
            regular_readback = readback
            regular_start_offset = start_offset
        if (
            stage["assignment_mechanism"]
            in {
                "simple_randomized",
                "stratified_randomized",
                "factorial_randomized",
            }
            and len(decision_epochs) != 1
        ):
            raise ProtocolCapacityError(
                "single-assignment randomized mechanism requires exactly one decision epoch; "
                "repeated outcome measurements belong inside that epoch's estimand horizon"
            )
        epoch_ids = [row["decision_epoch_id"] for row in decision_epochs]
        if len(epoch_ids) != len(set(epoch_ids)):
            raise ProtocolCapacityError("decision epoch identifiers must be unique per stage")
        epoch_allocations: dict[str, dict[str, float]] = {}
        epoch_times: dict[str, float] = {}
        expected_available_epochs = 0.0
        for epoch in decision_epochs:
            epoch_id = epoch["decision_epoch_id"]
            epoch_time = float(epoch["decision_time_offset"])
            availability = float(epoch["availability_probability"])
            if not math.isfinite(epoch_time) or not math.isfinite(availability):
                raise ProtocolCapacityError("decision epoch times and availability must be finite")
            epoch_times[epoch_id] = epoch_time
            expected_available_epochs += availability * epoch_multiplicity[epoch_id]
            epoch_allocation: dict[str, float] = {}
            for allocation in epoch["policy_propensities"]:
                try:
                    policy_id = policy_aliases[allocation["policy_id"]]
                except KeyError as error:
                    raise ProtocolCapacityError(
                        "decision epoch propensity references an unknown policy"
                    ) from error
                probability = float(allocation["probability"])
                if not math.isfinite(probability):
                    raise ProtocolCapacityError("decision epoch propensities must be finite")
                epoch_allocation[policy_id] = epoch_allocation.get(policy_id, 0.0) + probability
            if len(epoch_allocation) < 2 or not math.isclose(
                sum(epoch_allocation.values()), 1.0, abs_tol=1e-9
            ):
                raise ProtocolCapacityError(
                    "each decision epoch requires a positive canonical propensity distribution"
                )
            epoch_allocations[epoch_id] = epoch_allocation

        if expected_available_epochs <= 0.0:
            raise ProtocolCapacityError(
                "at least one decision epoch must have positive availability"
            )
        score_dependence = stage["estimating_score_dependence_authority"]
        raw_decision_information_count = sum(epoch_multiplicity.values())
        if score_dependence["state"] == "registered":
            score_dependence_model = score_dependence["model"]
            score_dependence_correlation = float(score_dependence["correlation"])
            pooled_decision_information = bool(
                score_dependence["pooled_across_decisions"]
            )
            if regular_process is not None and not pooled_decision_information:
                raise ProtocolCapacityError(
                    "regular decision-epoch process must register pooled estimating-score dependence"
                )
            effective_decision_information_count = (
                _effective_estimating_score_repetitions(
                    raw_decision_information_count,
                    score_dependence_model,
                    score_dependence_correlation,
                )
                if pooled_decision_information
                else float(raw_decision_information_count)
            )
            score_dependence_resolution_state = "resolved_registered"
        else:
            score_dependence_model = None
            score_dependence_correlation = None
            pooled_decision_information = raw_decision_information_count <= 1
            effective_decision_information_count = (
                float(raw_decision_information_count)
                if raw_decision_information_count <= 1
                else 0.0
            )
            score_dependence_resolution_state = (
                "blocked_unknown_repeated_estimating_score_dependence"
            )
        decision_information_scale = (
            effective_decision_information_count / raw_decision_information_count
        )
        effective_information_multiplicity = {
            epoch_id: epoch_multiplicity[epoch_id] * decision_information_scale
            for epoch_id in epoch_multiplicity
        }
        average_epoch_allocations = {
            policy_id: sum(
                epoch_multiplicity[epoch["decision_epoch_id"]]
                * float(epoch["availability_probability"])
                * epoch_allocations[epoch["decision_epoch_id"]].get(policy_id, 0.0)
                for epoch in decision_epochs
            )
            / expected_available_epochs
            for policy_id in set().union(*(set(row) for row in epoch_allocations.values()))
        }
        if set(average_epoch_allocations) != set(allocations) or any(
            not math.isclose(
                average_epoch_allocations[policy_id], allocations[policy_id], abs_tol=1e-9
            )
            for policy_id in allocations
        ):
            raise ProtocolCapacityError(
                "stage policy allocations must equal the availability-weighted explicit epoch propensities"
            )

        conditional_eligibility_receipts = _conditional_moderated_eligibility_receipts(
            authority=stage["conditional_moderated_eligibility_authority"],
            stage_context_id=stage["context_id"],
            epoch_allocations=epoch_allocations,
            policy_aliases=policy_aliases,
        )
        for epoch in decision_epochs:
            receipt = conditional_eligibility_receipts[epoch["decision_epoch_id"]]
            conditional_q = receipt["minimum_conditional_availability_probability"]
            if conditional_q is not None and conditional_q > float(
                epoch["availability_probability"]
            ) + 1e-12:
                raise ProtocolCapacityError(
                    "pointwise conditional availability lower bound cannot exceed "
                    "the declared marginal epoch availability"
                )

        mrt_state_conditioned_propensity_executable = False
        if stage["assignment_mechanism"] == "micro_randomized":
            has_propensity_extension = bool(
                decision_rule["response_state_score_axis_ids"]
                and decision_rule["response_state_score_matrix"] is not None
                and decision_rule["policy_interaction_basis_matrix"] is not None
                and decision_rule["conditional_probability_shift"] is not None
            )
            if has_propensity_extension:
                ordered_rule_policies = tuple(decision_rule["canonical_policy_ids"])
                state_dimension = len(decision_rule["state_feature_ids"])
                # Execute the rule at the origin and both signs of every state
                # coordinate. The row-L1 normalization in the executor proves
                # the same positivity bound over the full tanh hypercube.
                validation_states = [np.zeros(state_dimension, dtype=float)]
                for state_index in range(state_dimension):
                    positive = np.zeros(state_dimension, dtype=float)
                    positive[state_index] = 1.0
                    validation_states.extend((positive, -positive))
                for epoch_allocation in epoch_allocations.values():
                    for validation_state in validation_states:
                        _bounded_state_conditioned_propensities(
                            baseline_propensities=epoch_allocation,
                            ordered_policy_ids=ordered_rule_policies,
                            state_to_policy_contrast_matrix=decision_rule[
                                "state_to_policy_contrast_matrix"
                            ],
                            state_values=validation_state,
                            conditional_probability_shift=decision_rule[
                                "conditional_probability_shift"
                            ],
                        )
                mrt_state_conditioned_propensity_executable = True

        if not epoch_times or float(stage["decision_time_offset"]) != min(epoch_times.values()):
            raise ProtocolCapacityError(
                "stage decision_time_offset must equal its earliest explicit decision epoch"
            )

        smart_geometry = stage["smart_path_geometry"]
        smart_geometry_state = smart_geometry["state"]
        smart_structural_personalization_eligible = False
        smart_response_state_prevalence_state = "not_applicable"
        smart_between_state_policy_distribution_rank = 0
        smart_minimum_conditional_policy_probability = None
        smart_minimum_response_state_participant_support = None
        smart_component_marginals_preserved = False
        smart_path_count = 0
        smart_probability_semantics = None
        conditional_component_variance_bound = allocation_assignment_variance_bound
        epoch_policy_probability_lower_bounds = {
            epoch_id: dict(probabilities)
            for epoch_id, probabilities in epoch_allocations.items()
        }
        if stage["assignment_mechanism"] == "smart_rerandomized":
            if smart_geometry_state != "registered":
                raise ProtocolCapacityError(
                    "SMART rerandomization requires registered path geometry"
                )
            if decision_rule["state"] != "registered_state_dependent":
                raise ProtocolCapacityError(
                    "SMART rerandomization requires a registered state-dependent decision rule operator"
                )
            if (
                not decision_rule["response_state_score_axis_ids"]
                or decision_rule["response_state_score_matrix"] is None
                or decision_rule["policy_interaction_basis_matrix"] is None
                or decision_rule["conditional_probability_shift"] is None
            ):
                raise ProtocolCapacityError(
                    "SMART rerandomization requires the complete response-axis decision-rule extension"
                )
            epoch_by_id = {row["decision_epoch_id"]: row for row in decision_epochs}
            chronological_epoch_ids = sorted(epoch_ids, key=epoch_times.__getitem__)
            if len(chronological_epoch_ids) != 2:
                raise ProtocolCapacityError(
                    "SMART response-state authority requires exactly two ordered decision epochs"
                )
            previous_epoch_id, next_epoch_id = chronological_epoch_ids
            response_states: dict[str, dict[str, Any]] = {}
            classified_state_keys: set[tuple[str, str]] = set()
            unclassifiable_state_ids: set[str] = set()
            axis_ids = tuple(decision_rule["response_state_score_axis_ids"])
            for definition in smart_geometry["response_state_definitions"]:
                state_id = definition["response_state_id"]
                if state_id in response_states:
                    raise ProtocolCapacityError("SMART response-state identifiers must be unique")
                if (
                    definition["transition_from_decision_epoch_id"] != previous_epoch_id
                    or definition["next_decision_epoch_id"] != next_epoch_id
                ):
                    raise ProtocolCapacityError(
                        "SMART response states must bind the declared consecutive decision transition"
                    )
                assessment_time = float(definition["assessment_time_offset"])
                if not (
                    epoch_times[previous_epoch_id] < assessment_time < epoch_times[next_epoch_id]
                ):
                    raise ProtocolCapacityError(
                        "SMART response assessment must occur strictly after the prior decision and before rerandomization"
                    )
                assessment_schedule = resolve_schedule_ids([definition["assessment_schedule_id"]])[
                    0
                ]
                if (
                    assessment_time not in assessment_schedule["temporal_offsets"]
                    or definition["assessment_schedule_id"]
                    not in epoch_by_id[next_epoch_id]["history_measurement_schedule_ids"]
                ):
                    raise ProtocolCapacityError(
                        "SMART response assessment must be an exact event in the next epoch history"
                    )
                state_features = tuple(definition["state_feature_ids"])
                if (
                    set(state_features) != set(decision_rule["state_feature_ids"])
                    or not set(state_features) <= assessment_schedule["active_features"]
                ):
                    raise ProtocolCapacityError(
                        "SMART response-state predicate must use every registered rule feature observed at assessment"
                    )
                predicate = definition["predicate"]
                if definition["classification_state"] == "classified":
                    if predicate["kind"] != (
                        "argmax_absolute_registered_linear_scores_with_ordered_tie_break"
                    ):
                        raise ProtocolCapacityError(
                            "classified SMART response states require the registered argmax/sign predicate"
                        )
                    if tuple(predicate["ordered_axis_priority"]) != axis_ids:
                        raise ProtocolCapacityError(
                            "SMART response-state tie-break priority must equal the registered axis order"
                        )
                    state_key = (predicate["active_score_axis_id"], predicate["direction"])
                    if state_key in classified_state_keys or state_key[0] not in axis_ids:
                        raise ProtocolCapacityError(
                            "SMART classified response states must uniquely cover registered axis/sign pairs"
                        )
                    classified_state_keys.add(state_key)
                else:
                    if predicate["kind"] != "unclassifiable_if_any_required_feature_missing":
                        raise ProtocolCapacityError(
                            "SMART unclassifiable state must explicitly cover missing required features"
                        )
                    unclassifiable_state_ids.add(state_id)
                response_states[state_id] = definition
            expected_classified_keys = {
                (axis_id, direction)
                for axis_id in axis_ids
                for direction in ("nonnegative", "negative")
            }
            if (
                classified_state_keys != expected_classified_keys
                or len(unclassifiable_state_ids) != 1
                or len(response_states) != (2 * len(axis_ids)) + 1
            ):
                raise ProtocolCapacityError(
                    "SMART response-state partition must be mutually exclusive and exhaustive: two signs per axis plus one unclassifiable state"
                )

            conditional_distributions: dict[tuple[str, str], dict[str, float]] = {}
            canonical_rule_policy_ids = tuple(decision_rule["canonical_policy_ids"])
            rule_policy_row = {
                policy_id: index for index, policy_id in enumerate(canonical_rule_policy_ids)
            }
            basis = decision_rule["policy_interaction_basis_matrix"]
            shift = float(decision_rule["conditional_probability_shift"])
            for distribution in smart_geometry["conditional_policy_distributions"]:
                state_id = distribution["response_state_id"]
                distribution_key = (distribution["decision_epoch_id"], state_id)
                if distribution_key in conditional_distributions:
                    raise ProtocolCapacityError(
                        "SMART conditional policy distribution repeats an epoch/state pair"
                    )
                if (
                    distribution["decision_epoch_id"] != next_epoch_id
                    or state_id not in response_states
                ):
                    raise ProtocolCapacityError(
                        "SMART conditional policy distributions must bind the next epoch and a declared response state"
                    )
                probabilities: dict[str, float] = {}
                for allocation in distribution["policy_propensities"]:
                    try:
                        policy_id = policy_aliases[allocation["policy_id"]]
                    except KeyError as error:
                        raise ProtocolCapacityError(
                            "SMART conditional distribution references an unknown policy"
                        ) from error
                    probability = float(allocation["probability"])
                    if not math.isfinite(probability):
                        raise ProtocolCapacityError(
                            "SMART conditional policy probabilities must be finite"
                        )
                    probabilities[policy_id] = probabilities.get(policy_id, 0.0) + probability
                if (
                    set(probabilities) != set(allocations)
                    or not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-9)
                    or any(value <= 0.0 or value >= 1.0 for value in probabilities.values())
                ):
                    raise ProtocolCapacityError(
                        "every SMART response state requires a strictly positive normalized distribution over the complete policy support"
                    )
                definition = response_states[state_id]
                if definition["classification_state"] == "classified":
                    predicate = definition["predicate"]
                    axis_index = axis_ids.index(predicate["active_score_axis_id"])
                    direction = 1.0 if predicate["direction"] == "nonnegative" else -1.0
                    expected = {
                        policy_id: epoch_allocations[next_epoch_id][policy_id]
                        + direction * shift * float(basis[rule_policy_row[policy_id], axis_index])
                        for policy_id in probabilities
                    }
                else:
                    expected = dict(epoch_allocations[next_epoch_id])
                if any(
                    not math.isclose(probabilities[policy_id], expected[policy_id], abs_tol=1e-9)
                    for policy_id in probabilities
                ):
                    raise ProtocolCapacityError(
                        "SMART conditional policy distribution does not execute its registered bounded response-axis rule"
                    )
                conditional_distributions[distribution_key] = probabilities
            expected_distribution_keys = {(next_epoch_id, state_id) for state_id in response_states}
            if set(conditional_distributions) != expected_distribution_keys:
                raise ProtocolCapacityError(
                    "SMART conditional policy distributions must cover every exhaustive response state exactly once"
                )

            component_marginal_rows = []
            for probabilities in conditional_distributions.values():
                component_marginals = np.asarray(
                    [
                        sum(
                            probability
                            * policy_components[policy_index[policy_id], component_column]
                            for policy_id, probability in probabilities.items()
                        )
                        for component_column in range(len(ordered_components))
                    ],
                    dtype=float,
                )
                component_marginal_rows.append(component_marginals)
                if not np.allclose(
                    component_marginals,
                    np.asarray(component_propensities, dtype=float),
                    rtol=0.0,
                    atol=1e-9,
                ):
                    raise ProtocolCapacityError(
                        "SMART response-state distributions must preserve every registered component marginal"
                    )
            smart_component_marginals_preserved = True
            conditional_component_variance_bound = min(
                (
                    float(probability * (1.0 - probability))
                    for row in component_marginal_rows
                    for probability in row
                    if 0.0 < probability < 1.0
                ),
                default=0.0,
            )
            effective_assignment_variance_bound = min(
                effective_assignment_variance_bound,
                conditional_component_variance_bound,
            )
            smart_minimum_conditional_policy_probability = min(
                probability
                for distribution in conditional_distributions.values()
                for probability in distribution.values()
            )
            epoch_policy_probability_lower_bounds[next_epoch_id] = {
                policy_id: min(
                    distribution[policy_id]
                    for distribution in conditional_distributions.values()
                )
                for policy_id in epoch_allocations[next_epoch_id]
            }
            classified_probability_rows = np.asarray(
                [
                    [
                        conditional_distributions[(next_epoch_id, state_id)][policy_id]
                        for policy_id in canonical_rule_policy_ids
                    ]
                    for state_id, definition in response_states.items()
                    if definition["classification_state"] == "classified"
                ],
                dtype=float,
            )
            centered_probability_rows = classified_probability_rows - np.mean(
                classified_probability_rows, axis=0, keepdims=True
            )
            smart_between_state_policy_distribution_rank = _rectangular_rank_receipt(
                centered_probability_rows
            )["effective_rank"]
            if smart_between_state_policy_distribution_rank != len(axis_ids):
                raise ProtocolCapacityError(
                    "SMART between-state policy-distribution contrast must span every registered response axis"
                )

            prevalence = smart_geometry["response_state_prevalence"]
            smart_response_state_prevalence_state = prevalence["state"]
            if prevalence["state"] == "registered":
                prevalence_by_state: dict[str, float] = {}
                for row in prevalence["state_probabilities"]:
                    state_id = row["response_state_id"]
                    if state_id in prevalence_by_state:
                        raise ProtocolCapacityError(
                            "SMART response-state prevalence repeats a state"
                        )
                    prevalence_by_state[state_id] = float(row["probability"])
                if (
                    set(prevalence_by_state) != set(response_states)
                    or any(value <= 0.0 for value in prevalence_by_state.values())
                    or not math.isclose(sum(prevalence_by_state.values()), 1.0, abs_tol=1e-9)
                ):
                    raise ProtocolCapacityError(
                        "registered SMART response-state prevalence must positively normalize across every exhaustive state"
                    )
                smart_minimum_response_state_participant_support = (
                    participants
                    * min(
                        prevalence_by_state[state_id]
                        for state_id, definition in response_states.items()
                        if definition["classification_state"] == "classified"
                    )
                    * float(epoch_by_id[next_epoch_id]["availability_probability"])
                )

            path_ids: set[str] = set()
            path_signatures: set[tuple[str, str, str]] = set()
            probability_semantics = (
                "product_of_conditional_assignment_propensities_excludes_response_state_prevalence"
            )
            for path in smart_geometry["paths"]:
                if path["smart_path_id"] in path_ids:
                    raise ProtocolCapacityError("SMART path identifiers must be unique")
                path_ids.add(path["smart_path_id"])
                ordered = path["ordered_decision_epoch_ids"]
                if any(epoch_id not in epoch_times for epoch_id in ordered):
                    raise ProtocolCapacityError("SMART path references an unknown decision epoch")
                if [epoch_times[value] for value in ordered] != sorted(
                    epoch_times[value] for value in ordered
                ):
                    raise ProtocolCapacityError("SMART path epochs must be time ordered")
                if ordered != chronological_epoch_ids:
                    raise ProtocolCapacityError(
                        "each SMART path must bind the complete chronological decision-epoch ledger"
                    )
                if len(path["policy_sequence_ids"]) != len(ordered):
                    raise ProtocolCapacityError("SMART path policy sequence must align with epochs")
                if any(value not in policy_aliases for value in path["policy_sequence_ids"]):
                    raise ProtocolCapacityError("SMART path references an unknown policy")
                if len(path["response_state_ids"]) != len(ordered) - 1:
                    raise ProtocolCapacityError(
                        "SMART response-state transitions must occur between epochs"
                    )
                canonical_sequence = [
                    policy_aliases[value] for value in path["policy_sequence_ids"]
                ]
                response_state_id = path["response_state_ids"][0]
                if response_state_id not in response_states:
                    raise ProtocolCapacityError(
                        "SMART path references an undeclared response state"
                    )
                signature = (
                    canonical_sequence[0],
                    response_state_id,
                    canonical_sequence[1],
                )
                if signature in path_signatures:
                    raise ProtocolCapacityError("SMART path signatures must be unique")
                path_signatures.add(signature)
                expected_probability = (
                    epoch_allocations[previous_epoch_id][canonical_sequence[0]]
                    * conditional_distributions[(next_epoch_id, response_state_id)][
                        canonical_sequence[1]
                    ]
                )
                if path["probability_semantics"] != probability_semantics or not math.isclose(
                    float(path["assignment_propensity_product"]),
                    expected_probability,
                    abs_tol=1e-12,
                ):
                    raise ProtocolCapacityError(
                        "SMART path weight must equal assignment propensities only and exclude response-state prevalence"
                    )
            expected_path_signatures = {
                (first_policy, state_id, second_policy)
                for first_policy in epoch_allocations[previous_epoch_id]
                for state_id in response_states
                for second_policy in conditional_distributions[(next_epoch_id, state_id)]
            }
            if path_signatures != expected_path_signatures:
                raise ProtocolCapacityError(
                    "SMART paths must enumerate every reachable policy-state-policy sequence exactly once"
                )
            for state_id in response_states:
                state_total = sum(
                    float(path["assignment_propensity_product"])
                    for path in smart_geometry["paths"]
                    if path["response_state_ids"] == [state_id]
                )
                if not math.isclose(state_total, 1.0, abs_tol=1e-9):
                    raise ProtocolCapacityError(
                        "SMART assignment propensity products must normalize within each response state, not across unknown state prevalence"
                    )
            smart_structural_personalization_eligible = True
            smart_path_count = len(path_signatures)
            smart_probability_semantics = probability_semantics
        elif smart_geometry_state != "not_applicable":
            raise ProtocolCapacityError(
                "non-SMART stages must declare SMART path geometry not_applicable"
            )
        if (
            stage["assignment_mechanism"] == "micro_randomized"
            and decision_rule["state"] == "registered_state_dependent"
            and mrt_state_conditioned_propensity_executable
        ):
            shift = float(decision_rule["conditional_probability_shift"])
            for epoch_id, probabilities in epoch_allocations.items():
                lower_bounds = {
                    policy_id: probability - shift
                    for policy_id, probability in probabilities.items()
                }
                if any(value <= 0.0 for value in lower_bounds.values()):
                    raise ProtocolCapacityError(
                        "MRT state-conditioned policy lower bound must remain positive"
                    )
                epoch_policy_probability_lower_bounds[epoch_id] = lower_bounds

        outcomes = resolve_schedule_ids(stage["linked_outcome_schedule_ids"])
        outcome_by_id = {row["schedule_id"]: row for row in outcomes}
        outcome_offset_index = {
            row["schedule_id"]: tuple(sorted(row["temporal_offsets"])) for row in outcomes
        }
        decision_time = float(stage["decision_time_offset"])
        if not math.isfinite(decision_time):
            raise ProtocolCapacityError("decision time offsets must be finite")
        # One joint participant-event may identify multiple distinct outcome
        # estimands.  The estimand geometry is part of the deduplication key so
        # an alias cannot buy support, while a genuinely different jointly
        # measured outcome cannot erase an already valid causal link.
        used_proximal_events: set[tuple[str, float, str]] = set()
        linked_epoch_outcome_support: list[float] = []
        linked_epoch_moderator_support: list[float] = []
        postdecision_offsets_by_schedule: dict[str, tuple[float, ...]] = {}
        epoch_link_ledger: list[dict[str, Any]] = []
        estimand_contrast_ledger: list[dict[str, Any]] = []
        outcome_observability_receipts: dict[str, dict[str, Any]] = {}
        all_outcome_links_valid = True
        outcome_observer_unresolved = False
        all_rule_history_valid = True
        for epoch in decision_epochs:
            epoch_id = epoch["decision_epoch_id"]
            epoch_time = epoch_times[epoch_id]
            history_schedules = resolve_schedule_ids(epoch["history_measurement_schedule_ids"])
            history_features = set(epoch["history_moderator_feature_ids"])
            predecision_offsets_by_schedule = {
                row["schedule_id"]: tuple(
                    offset for offset in row["temporal_offsets"] if offset < epoch_time
                )
                for row in history_schedules
            }
            history_valid = bool(history_schedules) and all(
                row["participant_set_id"] == stage["participant_set_id"]
                and bool(predecision_offsets_by_schedule[row["schedule_id"]])
                for row in history_schedules
            )
            measured_history = (
                set().union(*(row["active_features"] for row in history_schedules))
                if history_schedules
                else set()
            )
            history_valid = bool(history_valid and history_features <= measured_history)
            history_support = (
                min(
                    row["participant_count"] * row["retention_fraction"]
                    for row in history_schedules
                )
                if history_valid and history_schedules
                else 0.0
            )
            rule_history_valid = bool(
                decision_rule["state"] == "registered_state_dependent"
                and set(decision_rule["state_feature_ids"]) <= history_features
                and set(decision_rule["state_feature_ids"]) <= measured_history
                and history_support > 0
            )
            all_rule_history_valid = all_rule_history_valid and rule_history_valid
            proximal_event_count = 0
            epoch_support_rows: list[float] = []
            epoch_population_rows: list[float] = []
            epoch_contrasts: list[dict[str, Any]] = []
            epoch_linked_outcome_schedules: dict[str, Mapping[str, Any]] = {}
            for link in epoch["proximal_outcome_links"]:
                if link["schedule_id"] not in stage["linked_outcome_schedule_ids"]:
                    raise ProtocolCapacityError(
                        "proximal outcome link must be declared in stage outcome schedules"
                    )
                try:
                    outcome = outcome_by_id[schedule_aliases[link["schedule_id"]]]
                    estimand = estimands[link["estimand_id"]]
                except KeyError as error:
                    raise ProtocolCapacityError(
                        "proximal outcome link references unknown schedule or estimand"
                    ) from error
                lower = epoch_time + estimand["horizon_start_offset_exclusive"]
                upper = epoch_time + estimand["horizon_end_offset_inclusive"]
                indexed_offsets = outcome_offset_index[outcome["schedule_id"]]
                if regular_process is not None:
                    assert regular_interval is not None
                    assert regular_readback is not None
                    assert regular_start_offset is not None
                    if not (
                        estimand["horizon_start_offset_exclusive"]
                        < regular_readback
                        <= estimand["horizon_end_offset_inclusive"]
                    ):
                        raise ProtocolCapacityError(
                            "regular proximal readback must fall inside its registered estimand horizon"
                        )
                    expected_readbacks = tuple(
                        regular_start_offset + index * regular_interval + regular_readback
                        for index in range(regular_decision_count)
                    )
                    if len(indexed_offsets) < regular_decision_count or any(
                        not any(
                            math.isclose(
                                observed,
                                expected,
                                rel_tol=0.0,
                                abs_tol=1e-9,
                            )
                            for observed in indexed_offsets[
                                max(
                                    0, bisect.bisect_left(indexed_offsets, expected) - 1
                                ) : bisect.bisect_left(indexed_offsets, expected) + 2
                            ]
                        )
                        for expected in expected_readbacks
                    ):
                        raise ProtocolCapacityError(
                            "regular decision-epoch process requires every exact source-bound proximal readback on its generated grid"
                        )
                    matched = tuple(
                        expected
                        for expected in expected_readbacks
                        if (
                            outcome["schedule_id"],
                            expected,
                            estimand["geometry_sha256"],
                        )
                        not in used_proximal_events
                    )
                else:
                    start_index = bisect.bisect_right(indexed_offsets, lower)
                    end_index = bisect.bisect_right(indexed_offsets, upper)
                    matched = tuple(
                        offset
                        for offset in indexed_offsets[start_index:end_index]
                        if (
                            outcome["schedule_id"],
                            offset,
                            estimand["geometry_sha256"],
                        )
                        not in used_proximal_events
                    )
                outcome_observer_unresolved = bool(
                    outcome_observer_unresolved
                    or estimand["outcome_features"] & outcome["unresolved_features"]
                )
                observability = _measurement_feature_gram(
                    sorted(estimand["outcome_features"]),
                    signal_index,
                    covariance_memberships,
                    covariance_matrices,
                    parameter_dimension,
                )
                outcome_observability_receipts[estimand["geometry_sha256"]] = {
                    key: value
                    for key, value in observability.items()
                    if key != "gram"
                }
                outcome_observer_unresolved = bool(
                    outcome_observer_unresolved
                    or observability["state"]
                    == "unresolved_joint_covariance_for_declared_feature_vector"
                )
                outcome_observability_factor = observability[
                    "minimum_observability_factor"
                ]
                outcome_features_valid = bool(
                    estimand["outcome_features"] <= outcome["active_features"]
                    and outcome_observability_factor is not None
                    and outcome_observability_factor > 0.0
                )
                participant_valid = outcome["participant_set_id"] == stage["participant_set_id"]
                assigned_policies = set(epoch_allocations[epoch_id])
                contrasts_supported = all(
                    set(contrast["coefficients"]) <= assigned_policies
                    for contrast in estimand["canonical_operator_contrasts"]
                )
                if not contrasts_supported:
                    raise ProtocolCapacityError(
                        "proximal estimand contrast references a policy without positive support in its decision epoch"
                    )
                link_valid = bool(matched and outcome_features_valid and participant_valid)
                all_outcome_links_valid = all_outcome_links_valid and link_valid
                if link_valid:
                    used_proximal_events.update(
                        (outcome["schedule_id"], offset, estimand["geometry_sha256"])
                        for offset in matched
                    )
                    postdecision_offsets_by_schedule[outcome["schedule_id"]] = tuple(
                        sorted(
                            {
                                *postdecision_offsets_by_schedule.get(outcome["schedule_id"], ()),
                                *matched,
                            }
                        )
                    )
                    proximal_event_count += len(matched)
                    epoch_support_rows.append(
                        outcome["participant_count"] * outcome["retention_fraction"]
                    )
                    epoch_population_rows.append(outcome["participant_count"])
                    epoch_contrasts.extend(
                        {
                            **contrast,
                            "outcome_observability_factor": float(
                                outcome_observability_factor
                            ),
                            "outcome_observability_gram_sha256": observability[
                                "gram_sha256"
                            ],
                        }
                        for contrast in estimand["canonical_operator_contrasts"]
                    )
                    epoch_linked_outcome_schedules[outcome["schedule_id"]] = outcome
            support = min(epoch_support_rows) if epoch_support_rows else 0.0
            history_population_rows = [row["participant_count"] for row in history_schedules]
            cohort_population = min(
                [participants, *epoch_population_rows, *history_population_rows]
            )
            retained_outcome_support = min(cohort_population, support)
            availability_support = min(
                cohort_population,
                participants * float(epoch["availability_probability"]),
            )
            linked_epoch_outcome_support.append(
                max(
                    0.0,
                    availability_support + retained_outcome_support - cohort_population,
                )
            )
            retention_overlap_receipt = _retention_overlap_support_receipt(
                outcome_schedules=epoch_linked_outcome_schedules.values(),
                history_schedules=history_schedules,
                cohort_population_bound=cohort_population,
                availability_participant_support=availability_support,
                history_valid=history_valid,
            )
            conditional_eligibility_receipt = conditional_eligibility_receipts[
                epoch_id
            ]
            linked_epoch_moderator_support.append(
                cohort_population
                * float(
                    conditional_eligibility_receipt[
                        "minimum_pointwise_frechet_joint_eligible_fraction"
                    ]
                )
                * float(history_valid)
            )
            seen_epoch_contrasts: set[str] = set()
            for contrast in sorted(
                epoch_contrasts,
                key=lambda row: row["outcome_observability_factor"],
                reverse=True,
            ):
                contrast_key = _canonical_sha256(contrast["coefficients"])
                if contrast_key in seen_epoch_contrasts:
                    continue
                seen_epoch_contrasts.add(contrast_key)
                coefficients = contrast["coefficients"]
                contrast_precision = (
                    1.0
                    / sum(
                        coefficient**2
                        / (
                            linked_epoch_outcome_support[-1]
                            * epoch_policy_probability_lower_bounds[epoch_id][policy_id]
                        )
                        for policy_id, coefficient in coefficients.items()
                    )
                    if linked_epoch_outcome_support[-1] > 0
                    else 0.0
                )
                contrast_precision *= contrast["outcome_observability_factor"]
                policy_contrast = np.zeros(len(policy_ids), dtype=float)
                for policy_id, coefficient in coefficients.items():
                    policy_contrast[policy_index[policy_id]] = coefficient
                component_contrast = policy_contrast @ policy_components
                estimand_contrast_ledger.append(
                    {
                        "decision_epoch_id": epoch_id,
                        "decision_epoch_multiplicity": epoch_multiplicity[epoch_id],
                        "contrast_id": contrast["contrast_id"],
                        "canonical_policy_coefficients": coefficients,
                        "minimum_conditional_policy_probabilities": dict(
                            sorted(epoch_policy_probability_lower_bounds[epoch_id].items())
                        ),
                        "policy_contrast": policy_contrast,
                        "component_contrast": component_contrast,
                        "outcome_observability_factor": contrast[
                            "outcome_observability_factor"
                        ],
                        "outcome_observability_gram_sha256": contrast[
                            "outcome_observability_gram_sha256"
                        ],
                        "eligible_contrast_precision": (
                            contrast_precision
                            * effective_information_multiplicity[epoch_id]
                        ),
                        "eligible_moderator_contrast_precision": min(
                            contrast_precision
                            * effective_information_multiplicity[epoch_id],
                            (
                                contrast_precision
                                * linked_epoch_moderator_support[-1]
                                / linked_epoch_outcome_support[-1]
                                * effective_information_multiplicity[epoch_id]
                                if linked_epoch_outcome_support[-1] > 0
                                else 0.0
                            ),
                        ),
                    }
                )
            epoch_link_ledger.append(
                {
                    "decision_epoch_id": epoch_id,
                    "decision_epoch_representation": (
                        "regular_decision_epoch_process"
                        if regular_process is not None
                        else "explicit_epoch"
                    ),
                    "decision_epoch_process_id": (
                        regular_process["decision_epoch_process_id"]
                        if regular_process is not None
                        else None
                    ),
                    "decision_epoch_multiplicity": epoch_multiplicity[epoch_id],
                    "effective_decision_information_multiplicity": (
                        effective_information_multiplicity[epoch_id]
                    ),
                    "decision_time_offset": epoch_time,
                    "availability_probability": float(epoch["availability_probability"]),
                    "history_predecision_offset_count": sum(
                        len(offsets) for offsets in predecision_offsets_by_schedule.values()
                    ),
                    "history_state_linked_predecision": history_valid,
                    "registered_rule_state_linked_predecision": rule_history_valid,
                    "proximal_outcome_event_count": proximal_event_count,
                    "retention_overlap_receipt": retention_overlap_receipt,
                    "conditional_moderated_eligibility_receipt": (
                        conditional_eligibility_receipt
                    ),
                    "eligible_outcome_participant_decision_support": (
                        linked_epoch_outcome_support[-1]
                    ),
                    "eligible_moderator_participant_decision_support": (
                        linked_epoch_moderator_support[-1]
                    ),
                }
            )
        outcome_offsets = {offset for _, offset, _ in used_proximal_events}
        active_outcome_observer = all_outcome_links_valid and bool(outcome_offsets)
        linked_outcome_support = (
            min(linked_epoch_outcome_support) if linked_epoch_outcome_support else 0.0
        )
        outcome_linked = bool(active_outcome_observer and sum(linked_epoch_outcome_support) > 0)
        repeated_outcome = outcome_linked and len(decision_epochs) >= 2
        if regular_process is not None:
            repeated_outcome = bool(outcome_linked and regular_decision_count >= 2)
        causal_participant_support = min(
            participants, max(linked_epoch_outcome_support, default=0.0)
        )
        linked_outcome_participant_events = sum(
            support * epoch_multiplicity[epoch["decision_epoch_id"]]
            for support, epoch in zip(linked_epoch_outcome_support, decision_epochs, strict=True)
        )
        eligible_participant_decisions = _stable_support(
            min(
                participants * decisions,
                participants * expected_available_epochs,
                linked_outcome_participant_events,
            )
        )
        eligible_moderator_participant_decisions = _stable_support(
            min(
                eligible_participant_decisions,
                sum(
                    support * epoch_multiplicity[epoch["decision_epoch_id"]]
                    for support, epoch in zip(
                        linked_epoch_moderator_support, decision_epochs, strict=True
                    )
                ),
            )
        )
        eligible_decisions_per_participant = (
            eligible_participant_decisions / participants if participants > 0 else 0.0
        )
        policy_information_matrix = np.zeros((len(policy_ids), len(policy_ids)), dtype=float)
        component_information_matrix = np.zeros(
            (len(ordered_components), len(ordered_components)), dtype=float
        )
        for row in estimand_contrast_ledger:
            policy_information_matrix += row["eligible_contrast_precision"] * np.outer(
                row["policy_contrast"], row["policy_contrast"]
            )
            component_information_matrix += row["eligible_contrast_precision"] * np.outer(
                row["component_contrast"], row["component_contrast"]
            )
        estimand_contrasts_by_epoch: dict[str, list[dict[str, Any]]] = {
            epoch_id: [] for epoch_id in epoch_ids
        }
        for row in estimand_contrast_ledger:
            estimand_contrasts_by_epoch[row["decision_epoch_id"]].append(row)
        epoch_policy_information_by_id: dict[str, np.ndarray] = {}
        epoch_component_information_by_id: dict[str, np.ndarray] = {}
        for epoch_id, contrasts in estimand_contrasts_by_epoch.items():
            epoch_policy_information = np.zeros((len(policy_ids), len(policy_ids)), dtype=float)
            epoch_component_information = np.zeros(
                (len(ordered_components), len(ordered_components)), dtype=float
            )
            for contrast in contrasts:
                epoch_policy_information += contrast["eligible_contrast_precision"] * np.outer(
                    contrast["policy_contrast"], contrast["policy_contrast"]
                )
                epoch_component_information += contrast["eligible_contrast_precision"] * np.outer(
                    contrast["component_contrast"], contrast["component_contrast"]
                )
            epoch_policy_information_by_id[epoch_id] = epoch_policy_information
            epoch_component_information_by_id[epoch_id] = epoch_component_information
        epoch_specific_information = bool(
            stage["assignment_mechanism"] == "smart_rerandomized"
            and regular_process is None
        )
        if epoch_specific_information:
            ordered_epoch_ids = sorted(epoch_ids, key=epoch_times.__getitem__)
            policy_information_matrix = _block_diagonal(
                [epoch_policy_information_by_id[epoch_id] for epoch_id in ordered_epoch_ids]
            )
            component_information_matrix = _block_diagonal(
                [epoch_component_information_by_id[epoch_id] for epoch_id in ordered_epoch_ids]
            )

        moderator_schedules = resolve_schedule_ids(stage["moderator_measurement_schedule_ids"])
        moderator_ids = set(stage["moderator_feature_ids"])
        moderator_order = sorted(moderator_ids)
        moderator_observability = _measurement_feature_gram(
            moderator_order,
            signal_index,
            covariance_memberships,
            covariance_matrices,
            parameter_dimension,
        )
        moderator_observability_factor = moderator_observability[
            "minimum_observability_factor"
        ]
        measured_moderators = (
            set().union(*(row["active_features"] for row in moderator_schedules))
            if moderator_schedules
            else set()
        )
        moderator_joint = bool(moderator_ids) and all(
            row["participant_set_id"] == stage["participant_set_id"] for row in moderator_schedules
        )
        linked_moderator_support = (
            min(
                min(
                    row["participant_count"] for row in moderator_schedules
                ),
                min(linked_epoch_moderator_support),
            )
            if (moderator_joint and moderator_schedules and linked_epoch_moderator_support)
            else 0.0
        )
        moderator_supported = bool(
            moderator_joint
            and moderator_ids <= measured_moderators
            and moderator_ids <= eligible_features
            and linked_moderator_support > 0
            and moderator_observability_factor is not None
            and moderator_observability_factor > 0.0
        )
        population_geometry = stage["moderator_population_geometry"]
        moderator_resolution_state = population_geometry["state"]
        if moderator_resolution_state in {
            "registered",
            "registered_stationary_rate_process",
        } and population_geometry["population_scope"] != (
            "uniform_loewner_lower_bound_on_standardized_moderator_covariance_"
            "within_every_exact_joint_eligible_predecision_stage_context_policy_"
            "history_population"
        ):
            raise ProtocolCapacityError(
                "moderator covariance must be a uniform pointwise Loewner lower bound, "
                "not a marginal population covariance"
            )
        if (
            moderator_observability["state"]
            == "unresolved_joint_covariance_for_declared_feature_vector"
        ):
            moderator_resolution_state = "unknown"
        moderator_index = {value: index for index, value in enumerate(moderator_order)}
        interaction_block_dimension = len(policy_ids) * len(moderator_order)
        # SMART epochs are distinct stage-specific estimands. Micro-randomized
        # decisions are repeated realizations of one pooled proximal estimand,
        # whether represented as an explicit grid or a compact regular process.
        # Keeping this distinction makes the two MRT representations exactly
        # invariant while retaining the registered SMART epoch geometry.
        epoch_specific_moderation = epoch_specific_information
        interaction_block_count = len(epoch_ids) if epoch_specific_moderation else 1
        interaction_dimension = interaction_block_dimension * interaction_block_count
        interaction_information = np.zeros(
            (interaction_dimension, interaction_dimension), dtype=float
        )
        epoch_moderator_information_by_id: dict[str, np.ndarray] = {}
        population_covariance_hashes: dict[str, str] = {}
        if moderator_resolution_state == "registered":
            covariance_rows = population_geometry["epoch_covariances"]
            covariance_by_epoch: dict[str, Mapping[str, Any]] = {}
            for row in covariance_rows:
                if row["decision_epoch_id"] in covariance_by_epoch:
                    raise ProtocolCapacityError(
                        "moderator population covariance repeats a decision epoch"
                    )
                covariance_by_epoch[row["decision_epoch_id"]] = row
            if set(covariance_by_epoch) != set(epoch_ids):
                raise ProtocolCapacityError(
                    "registered moderator population geometry must cover every decision epoch"
                )
            covariance_hash_by_identity: dict[int, str] = {}
            validated_covariances: dict[str, np.ndarray] = {}
            for epoch in decision_epochs:
                epoch_id = epoch["decision_epoch_id"]
                row = covariance_by_epoch[epoch_id]
                feature_ids = list(row["moderator_feature_ids"])
                if set(feature_ids) != set(epoch["history_moderator_feature_ids"]):
                    raise ProtocolCapacityError(
                        "epoch population covariance must match its history moderator features"
                    )
                if not set(feature_ids) <= moderator_ids:
                    raise ProtocolCapacityError(
                        "epoch population covariance references undeclared moderators"
                    )
                raw_covariance = row["population_covariance"]
                covariance_identity = id(raw_covariance)
                covariance_hash = covariance_hash_by_identity.get(covariance_identity)
                covariance = (
                    validated_covariances.get(covariance_hash)
                    if covariance_hash is not None
                    else None
                )
                if covariance is None:
                    raw_matrix = np.asarray(raw_covariance, dtype=float)
                    if raw_matrix.shape != (len(feature_ids), len(feature_ids)):
                        raise ProtocolCapacityError(
                            "epoch moderator population covariance has wrong dimensions"
                        )
                    if not np.all(np.isfinite(raw_matrix)) or not np.allclose(
                        raw_matrix, raw_matrix.T, atol=1e-10, rtol=0.0
                    ):
                        raise ProtocolCapacityError(
                            "epoch moderator population covariance must be finite and symmetric"
                        )
                    covariance_rank = _rank_receipt(raw_matrix)
                    if (
                        covariance_rank["minimum_eigenvalue"]
                        < -covariance_rank["absolute_threshold"]
                    ):
                        raise ProtocolCapacityError(
                            "epoch moderator population covariance must be positive semidefinite"
                        )
                    diagonal = np.diag(raw_matrix)
                    if np.any(diagonal <= covariance_rank["absolute_threshold"]):
                        raise ProtocolCapacityError(
                            "epoch moderator population covariance requires positive variances "
                            "for standardized canonical moderator coordinates"
                        )
                    standard_deviations = np.sqrt(diagonal)
                    covariance = raw_matrix / np.outer(standard_deviations, standard_deviations)
                    covariance = 0.5 * (covariance + covariance.T)
                    covariance_hash = _canonical_sha256(covariance.tolist())
                    covariance_hash_by_identity[covariance_identity] = covariance_hash
                    validated_covariances[covariance_hash] = covariance
                measurement_gram_receipt = _measurement_feature_gram(
                    feature_ids,
                    signal_index,
                    covariance_memberships,
                    covariance_matrices,
                    parameter_dimension,
                )
                measurement_gram = measurement_gram_receipt["gram"]
                if measurement_gram is None:
                    raise ProtocolCapacityError(
                        "registered moderator covariance requires resolved joint "
                        "measurement-operator covariance"
                    )
                measurement_eigenvalues, measurement_eigenvectors = np.linalg.eigh(
                    measurement_gram
                )
                bounded_measurement_root = (
                    measurement_eigenvectors
                    @ np.diag(np.sqrt(np.clip(measurement_eigenvalues, 0.0, 1.0)))
                    @ measurement_eigenvectors.T
                )
                covariance = (
                    bounded_measurement_root
                    @ covariance
                    @ bounded_measurement_root
                )
                covariance = 0.5 * (covariance + covariance.T)
                covariance_hash = _canonical_sha256(
                    {
                        "measurement_adjusted_population_covariance": covariance.tolist(),
                        "measurement_operator_gram_sha256": measurement_gram_receipt[
                            "gram_sha256"
                        ],
                    }
                )
                epoch_contrasts = [
                    contrast
                    for contrast in estimand_contrasts_by_epoch[epoch_id]
                    if contrast["eligible_moderator_contrast_precision"] > 0.0
                ]
                embedded = np.zeros((len(moderator_order), len(moderator_order)), dtype=float)
                indices = [moderator_index[value] for value in feature_ids]
                embedded[np.ix_(indices, indices)] = covariance
                epoch_policy_moderation_information = np.zeros(
                    (len(policy_ids), len(policy_ids)), dtype=float
                )
                for contrast in epoch_contrasts:
                    vector = contrast["policy_contrast"]
                    epoch_policy_moderation_information += contrast[
                        "eligible_moderator_contrast_precision"
                    ] * np.outer(vector, vector)
                epoch_moderator_information_by_id[epoch_id] = np.kron(
                    epoch_policy_moderation_information, embedded
                )
                population_covariance_hashes[epoch_id] = covariance_hash
            if epoch_specific_moderation:
                cursor = 0
                for epoch_id in sorted(epoch_ids, key=epoch_times.__getitem__):
                    block = epoch_moderator_information_by_id[epoch_id]
                    stop = cursor + block.shape[0]
                    interaction_information[cursor:stop, cursor:stop] = block
                    cursor = stop
            else:
                for epoch_id in sorted(epoch_ids, key=epoch_times.__getitem__):
                    interaction_information += epoch_moderator_information_by_id[epoch_id]
        elif moderator_resolution_state == "registered_stationary_rate_process":
            if regular_process is None:
                raise ProtocolCapacityError(
                    "stationary moderator population geometry requires a regular decision-epoch process"
                )
            if (
                population_geometry["decision_epoch_process_id"]
                != regular_process["decision_epoch_process_id"]
            ):
                raise ProtocolCapacityError(
                    "stationary moderator geometry must bind the stage decision-epoch process"
                )
            template_epoch = decision_epochs[0]
            feature_ids = list(population_geometry["moderator_feature_ids"])
            if (
                set(feature_ids) != set(template_epoch["history_moderator_feature_ids"])
                or not set(feature_ids) <= moderator_ids
            ):
                raise ProtocolCapacityError(
                    "stationary moderator covariance must match template history and declared moderators"
                )
            raw_matrix = np.asarray(population_geometry["population_covariance"], dtype=float)
            if raw_matrix.shape != (len(feature_ids), len(feature_ids)):
                raise ProtocolCapacityError(
                    "stationary moderator population covariance has wrong dimensions"
                )
            if not np.all(np.isfinite(raw_matrix)) or not np.allclose(
                raw_matrix, raw_matrix.T, atol=1e-10, rtol=0.0
            ):
                raise ProtocolCapacityError(
                    "stationary moderator population covariance must be finite and symmetric"
                )
            covariance_rank = _rank_receipt(raw_matrix)
            if covariance_rank["minimum_eigenvalue"] < -covariance_rank["absolute_threshold"]:
                raise ProtocolCapacityError(
                    "stationary moderator population covariance must be positive semidefinite"
                )
            diagonal = np.diag(raw_matrix)
            if np.any(diagonal <= covariance_rank["absolute_threshold"]):
                raise ProtocolCapacityError(
                    "stationary moderator covariance requires positive variances for standardized coordinates"
                )
            covariance = raw_matrix / np.outer(np.sqrt(diagonal), np.sqrt(diagonal))
            covariance = 0.5 * (covariance + covariance.T)
            measurement_gram = moderator_observability["gram"]
            if measurement_gram is None:
                raise ProtocolCapacityError(
                    "stationary moderator covariance requires resolved joint "
                    "measurement-operator covariance"
                )
            measurement_eigenvalues, measurement_eigenvectors = np.linalg.eigh(
                measurement_gram
            )
            bounded_measurement_root = (
                measurement_eigenvectors
                @ np.diag(np.sqrt(np.clip(measurement_eigenvalues, 0.0, 1.0)))
                @ measurement_eigenvectors.T
            )
            covariance = bounded_measurement_root @ covariance @ bounded_measurement_root
            covariance = 0.5 * (covariance + covariance.T)
            covariance_hash = _canonical_sha256(covariance.tolist())
            embedded = np.zeros((len(moderator_order), len(moderator_order)), dtype=float)
            indices = [moderator_index[value] for value in feature_ids]
            embedded[np.ix_(indices, indices)] = covariance
            epoch_policy_moderation_information = np.zeros(
                (len(policy_ids), len(policy_ids)), dtype=float
            )
            for contrast in estimand_contrasts_by_epoch[template_epoch["decision_epoch_id"]]:
                if contrast["eligible_moderator_contrast_precision"] <= 0.0:
                    continue
                vector = contrast["policy_contrast"]
                epoch_policy_moderation_information += contrast[
                    "eligible_moderator_contrast_precision"
                ] * np.outer(vector, vector)
            interaction_information = np.kron(epoch_policy_moderation_information, embedded)
            epoch_moderator_information_by_id[template_epoch["decision_epoch_id"]] = (
                interaction_information.copy()
            )
            population_covariance_hashes[regular_process["decision_epoch_process_id"]] = (
                covariance_hash
            )
            moderator_resolution_state = "registered"
        moderator_rank_receipt = (
            _rank_receipt(interaction_information)
            if moderator_resolution_state == "registered" and interaction_dimension
            else None
        )
        outcome_geometry_sha256 = _canonical_sha256(
            [
                {
                    "canonical_event_unit_id": row["canonical_event_unit_id"],
                    "active_features": sorted(row["active_features"]),
                    "relative_temporal_offsets": [
                        float(offset) - decision_time
                        for offset in postdecision_offsets_by_schedule.get(row["schedule_id"], ())
                    ],
                }
                for row in outcomes
            ]
        )
        if regular_process is not None:
            covariance_process_receipt = [
                {
                    "representation": "registered_regular_decision_epoch_process",
                    "decision_count": regular_decision_count,
                    "start_offset": regular_start_offset,
                    "decision_interval_days": regular_interval,
                    "covariance_sha256": population_covariance_hashes[
                        regular_process["decision_epoch_process_id"]
                    ],
                }
            ]
        else:
            covariance_process_receipt = [
                {
                    "representation": "explicit_epoch",
                    "decision_time_offset": epoch_times[epoch_id],
                    "decision_epoch_multiplicity": epoch_multiplicity[epoch_id],
                    "covariance_sha256": population_covariance_hashes[epoch_id],
                }
                for epoch_id in sorted(epoch_ids, key=epoch_times.__getitem__)
                if epoch_id in population_covariance_hashes
            ]
        moderator_geometry_sha256 = _canonical_sha256(
            {
                "moderator_feature_ids": sorted(moderator_ids),
                "schedules": [
                    {
                        "canonical_event_unit_id": row["canonical_event_unit_id"],
                        "active_features": sorted(row["active_features"]),
                        "relative_temporal_offsets": [
                            float(offset) - decision_time for offset in row["temporal_offsets"]
                        ],
                    }
                    for row in moderator_schedules
                ],
                "population_covariance_process": covariance_process_receipt,
                "population_covariance_scope": population_geometry.get(
                    "population_scope"
                ),
                "interaction_geometry": "treatment_contrast_information_kronecker_population_moderator_covariance",
            }
        )
        moderator_rank = moderator_rank_receipt["effective_rank"] if moderator_rank_receipt else 0
        moderator_positive_eigenvalues = (
            np.linalg.eigvalsh(interaction_information)
            if moderator_rank_receipt is not None
            else np.asarray([], dtype=float)
        )
        moderator_positive_eigenvalues = moderator_positive_eigenvalues[
            moderator_positive_eigenvalues
            > (moderator_rank_receipt["absolute_threshold"] if moderator_rank_receipt else 0.0)
        ]
        moderator_allocation_support_factor = (
            float(math.exp(np.mean(np.log(moderator_positive_eigenvalues))))
            if moderator_positive_eigenvalues.size
            else 0.0
        )
        randomized = stage["assignment_mechanism"] in INDEPENDENT_RANDOMIZED_MECHANISMS
        policy_rank_receipt = _rank_receipt(policy_information_matrix)
        component_rank_receipt = _rank_receipt(component_information_matrix)

        def allocation_support_factor(matrix: np.ndarray, receipt: Mapping[str, Any]) -> float:
            eigenvalues = np.linalg.eigvalsh(matrix)
            positive = eigenvalues[eigenvalues > receipt["absolute_threshold"]]
            return float(math.exp(np.mean(np.log(positive)))) if positive.size else 0.0

        policy_rank = policy_rank_receipt["effective_rank"]
        component_rank = component_rank_receipt["effective_rank"]
        policy_allocation_support_factor = allocation_support_factor(
            policy_information_matrix, policy_rank_receipt
        )
        component_allocation_support_factor = allocation_support_factor(
            component_information_matrix, component_rank_receipt
        )
        epoch_link_by_id = {row["decision_epoch_id"]: row for row in epoch_link_ledger}
        epoch_support_ledger = []
        for epoch_index, epoch_id in enumerate(sorted(epoch_ids, key=epoch_times.__getitem__)):
            epoch_policy = epoch_policy_information_by_id[epoch_id]
            epoch_component = epoch_component_information_by_id[epoch_id]
            epoch_moderator = epoch_moderator_information_by_id.get(
                epoch_id,
                np.zeros(
                    (interaction_block_dimension, interaction_block_dimension),
                    dtype=float,
                ),
            )
            epoch_policy_receipt = _rank_receipt(epoch_policy)
            epoch_component_receipt = _rank_receipt(epoch_component)
            epoch_moderator_receipt = _rank_receipt(epoch_moderator)
            epoch_link = epoch_link_by_id[epoch_id]
            multiplicity = int(epoch_link["decision_epoch_multiplicity"])
            epoch_support_ledger.append(
                {
                    "epoch_index": epoch_index,
                    "decision_time_offset": epoch_times[epoch_id],
                    "decision_epoch_multiplicity": multiplicity,
                    "effective_decision_information_multiplicity": float(
                        effective_information_multiplicity[epoch_id]
                    ),
                    "estimand_contrast_count": len(estimand_contrasts_by_epoch[epoch_id]),
                    "policy_rank": epoch_policy_receipt["effective_rank"],
                    "component_rank": epoch_component_receipt["effective_rank"],
                    "sequential_moderator_rank": epoch_moderator_receipt["effective_rank"],
                    "policy_allocation_support_factor": allocation_support_factor(
                        epoch_policy, epoch_policy_receipt
                    ),
                    "component_allocation_support_factor": allocation_support_factor(
                        epoch_component, epoch_component_receipt
                    ),
                    "sequential_moderator_allocation_support_factor": allocation_support_factor(
                        epoch_moderator, epoch_moderator_receipt
                    ),
                    "eligible_outcome_participant_decisions": float(
                        epoch_link["eligible_outcome_participant_decision_support"]
                    )
                    * multiplicity,
                    "eligible_moderator_participant_decisions": float(
                        epoch_link["eligible_moderator_participant_decision_support"]
                    )
                    * multiplicity,
                    "policy_information_matrix_sha256": _canonical_sha256(epoch_policy.tolist()),
                    "component_information_matrix_sha256": _canonical_sha256(
                        epoch_component.tolist()
                    ),
                    "sequential_moderator_information_matrix_sha256": _canonical_sha256(
                        epoch_moderator.tolist()
                    ),
                }
            )
        adaptive_repeated = (
            stage["assignment_mechanism"] in {"micro_randomized", "smart_rerandomized"}
            and sum(
                int(row["decision_epoch_multiplicity"])
                for row in epoch_link_ledger
                if row["eligible_moderator_participant_decision_support"] > 0
            )
            >= 2
        )
        every_epoch_component_supported = all(
            row["component_rank"] > 0 for row in epoch_support_ledger
        )
        every_epoch_policy_supported = all(
            row["policy_rank"] > 0 for row in epoch_support_ledger
        )
        every_epoch_moderator_supported = all(
            row["sequential_moderator_rank"] > 0 for row in epoch_support_ledger
        )
        state_dependent_policy = bool(
            decision_rule["state"] == "registered_state_dependent"
            and decision_rule["rank_tolerance_receipt"]
            and decision_rule["rank_tolerance_receipt"]["effective_rank"] > 0
            and all_rule_history_valid
            and (
                stage["assignment_mechanism"] != "micro_randomized"
                or mrt_state_conditioned_propensity_executable
            )
        )
        d_gate = bool(
            randomized
            and repeated_outcome
            and outcome_linked
            and component_rank > 0
            and every_epoch_component_supported
        )
        structural_p_gate = bool(
            d_gate
            and adaptive_repeated
            and state_dependent_policy
            and moderator_supported
            and moderator_resolution_state == "registered"
            and moderator_rank > 0
            and every_epoch_moderator_supported
            and (
                stage["assignment_mechanism"] != "smart_rerandomized"
                or smart_structural_personalization_eligible
            )
        )
        if (
            structural_p_gate
            and stage["assignment_mechanism"] == "smart_rerandomized"
            and smart_response_state_prevalence_state == "unknown"
        ):
            p_gate: bool | None = None
        else:
            p_gate = bool(
                structural_p_gate
                and (
                    stage["assignment_mechanism"] != "smart_rerandomized"
                    or smart_minimum_response_state_participant_support is not None
                    and smart_minimum_response_state_participant_support > 0.0
                )
            )
        h_gate = bool(
            randomized
            and outcome_linked
            and policy_rank > 0
            and every_epoch_policy_supported
            and moderator_supported
            and moderator_resolution_state == "registered"
            and moderator_rank > 0
            and every_epoch_moderator_supported
        )
        stage_internal_geometry[stage["stage_id"]] = {
            "policy_information_matrix": policy_information_matrix.copy(),
            "component_information_matrix": component_information_matrix.copy(),
            "sequential_moderator_information_matrix": interaction_information.copy(),
            "epoch_information": {
                row["epoch_index"]: {
                    "decision_time_offset": row["decision_time_offset"],
                    "decision_epoch_multiplicity": row["decision_epoch_multiplicity"],
                    "policy_information_matrix": epoch_policy_information_by_id[
                        sorted(epoch_ids, key=epoch_times.__getitem__)[row["epoch_index"]]
                    ].copy(),
                    "component_information_matrix": epoch_component_information_by_id[
                        sorted(epoch_ids, key=epoch_times.__getitem__)[row["epoch_index"]]
                    ].copy(),
                    "sequential_moderator_information_matrix": epoch_moderator_information_by_id.get(
                        sorted(epoch_ids, key=epoch_times.__getitem__)[row["epoch_index"]],
                        np.zeros(
                            (interaction_block_dimension, interaction_block_dimension),
                            dtype=float,
                        ),
                    ).copy(),
                }
                for row in epoch_support_ledger
            },
            "source_object_sha256": stage["source_object_sha256"],
            "source_locator": stage["source_locator"],
        }
        stage_ledger.append(
            {
                "stage_id": stage["stage_id"],
                "context_id": stage["context_id"],
                "participant_set_id": stage["participant_set_id"],
                "assignment_mechanism": stage["assignment_mechanism"],
                "canonical_policy_ids": sorted(allocations),
                "canonical_policy_allocations": {
                    policy_id: probability for policy_id, probability in sorted(allocations.items())
                },
                "policy_rank": policy_rank,
                "component_rank": component_rank,
                "epoch_block_policy_rank": sum(row["policy_rank"] for row in epoch_support_ledger),
                "policy_rank_tolerance_receipt": policy_rank_receipt,
                "component_rank_tolerance_receipt": component_rank_receipt,
                "sequential_moderator_rank": moderator_rank,
                "epoch_block_sequential_moderator_rank": sum(
                    row["sequential_moderator_rank"] for row in epoch_support_ledger
                ),
                "moderator_rank_tolerance_receipt": moderator_rank_receipt,
                "policy_allocation_support_factor": policy_allocation_support_factor,
                "component_allocation_support_factor": component_allocation_support_factor,
                "sequential_moderator_allocation_support_factor": (
                    moderator_allocation_support_factor
                ),
                "declared_assignment_participants": participants,
                "linked_outcome_retained_participant_support": linked_outcome_support,
                "linked_outcome_retained_participant_events": (linked_outcome_participant_events),
                "strictly_postdecision_outcome_offset_count": len(outcome_offsets),
                "eligible_causal_participant_support": causal_participant_support,
                "declared_decisions_per_participant": decisions,
                "eligible_decisions_per_participant": eligible_decisions_per_participant,
                "raw_decision_information_count": raw_decision_information_count,
                "effective_decision_information_count": (
                    effective_decision_information_count
                ),
                "estimating_score_dependence_resolution_state": (
                    score_dependence_resolution_state
                ),
                "estimating_score_dependence_model": score_dependence_model,
                "estimating_score_dependence_correlation": (
                    score_dependence_correlation
                ),
                "estimating_scores_pooled_across_decisions": (
                    pooled_decision_information
                ),
                "estimating_score_dependence_source_object_sha256": score_dependence[
                    "source_object_sha256"
                ],
                "estimating_score_dependence_source_locator": score_dependence[
                    "source_locator"
                ],
                "linked_moderator_retained_participant_support": linked_moderator_support,
                "conditional_moderated_eligibility_authority_state": stage[
                    "conditional_moderated_eligibility_authority"
                ]["state"],
                "conditional_moderated_eligibility_authority_scope": stage[
                    "conditional_moderated_eligibility_authority"
                ]["scope"],
                "conditional_moderated_eligibility_source_object_sha256": stage[
                    "conditional_moderated_eligibility_authority"
                ]["source_object_sha256"],
                "conditional_moderated_eligibility_source_locator": stage[
                    "conditional_moderated_eligibility_authority"
                ]["source_locator"],
                "eligible_moderator_participant_decisions": (
                    eligible_moderator_participant_decisions
                ),
                "decision_rule_operator_id": decision_rule["decision_rule_operator_id"],
                "decision_rule_geometry_state": decision_rule["state"],
                "decision_rule_rank_tolerance_receipt": decision_rule["rank_tolerance_receipt"],
                "decision_rule_uses_measured_state": state_dependent_policy,
                "declared_sequential_assignment_probability": (sequential_assignment_probability),
                "allocation_assignment_variance_bound": (allocation_assignment_variance_bound),
                "declared_assignment_variance_bound": declared_assignment_variance_bound,
                "effective_assignment_variance_bound": effective_assignment_variance_bound,
                "conditional_component_variance_bound": (conditional_component_variance_bound),
                "outcome_geometry_sha256": outcome_geometry_sha256,
                "outcome_observability_receipts": [
                    {"estimand_geometry_sha256": geometry_sha256, **receipt}
                    for geometry_sha256, receipt in sorted(
                        outcome_observability_receipts.items()
                    )
                ],
                "moderator_geometry_sha256": moderator_geometry_sha256,
                "moderator_observability_receipt": {
                    key: value
                    for key, value in moderator_observability.items()
                    if key != "gram"
                },
                "moderator_population_geometry_state": moderator_resolution_state,
                "moderator_population_geometry_scope": population_geometry.get(
                    "population_scope"
                ),
                "decision_epoch_ledger": epoch_link_ledger,
                "epoch_support_ledger": epoch_support_ledger,
                "estimand_contrast_ledger": [
                    {
                        "decision_epoch_id": row["decision_epoch_id"],
                        "decision_epoch_multiplicity": row["decision_epoch_multiplicity"],
                        "contrast_id": row["contrast_id"],
                        "canonical_policy_coefficients": row["canonical_policy_coefficients"],
                        "policy_contrast": row["policy_contrast"].tolist(),
                        "component_contrast": row["component_contrast"].tolist(),
                        "minimum_conditional_policy_probabilities": row[
                            "minimum_conditional_policy_probabilities"
                        ],
                        "outcome_observability_factor": row[
                            "outcome_observability_factor"
                        ],
                        "outcome_observability_gram_sha256": row[
                            "outcome_observability_gram_sha256"
                        ],
                        "eligible_contrast_precision": row["eligible_contrast_precision"],
                        "eligible_moderator_contrast_precision": row[
                            "eligible_moderator_contrast_precision"
                        ],
                    }
                    for row in estimand_contrast_ledger
                ],
                "smart_path_geometry_state": smart_geometry_state,
                "structural_personalization_eligible": structural_p_gate,
                "smart_structural_personalization_eligible": (
                    smart_structural_personalization_eligible
                ),
                "smart_response_state_prevalence_state": (smart_response_state_prevalence_state),
                "smart_between_state_policy_distribution_rank": (
                    smart_between_state_policy_distribution_rank
                ),
                "smart_minimum_conditional_policy_probability": (
                    smart_minimum_conditional_policy_probability
                ),
                "smart_minimum_response_state_participant_support": (
                    smart_minimum_response_state_participant_support
                ),
                "smart_component_marginals_preserved": (smart_component_marginals_preserved),
                "smart_path_count": smart_path_count,
                "smart_probability_semantics": smart_probability_semantics,
                "randomized_participants": (causal_participant_support if randomized else 0.0),
                "randomized_participant_decisions": (
                    eligible_participant_decisions if randomized else 0.0
                ),
                "randomized_moderator_participant_decisions": (
                    eligible_moderator_participant_decisions if randomized else 0.0
                ),
                "outcome_linked": outcome_linked,
                "outcome_observer_resolution_state": (
                    "unresolved" if outcome_observer_unresolved else "resolved"
                ),
                "repeated_linked_outcome": repeated_outcome,
                "moderator_supported_pre_assignment": moderator_supported,
                "eligible_for_causal_summary": bool(randomized and outcome_linked),
                "numeric_randomization_supported": randomized,
                "dependence_geometry_required": stage["assignment_mechanism"]
                in {"cluster_randomized", "crossover_randomized"},
                "gates": {
                    "D_dynamic_operator": d_gate,
                    "P_personalized_policy": p_gate,
                    "H_heterogeneous_response": h_gate,
                },
            }
        )

    transport_geometry = causal["transport_geometry"]
    try:
        reference_estimand = estimands[transport_geometry["reference_estimand_id"]]
    except KeyError as error:
        raise ProtocolCapacityError("transport references an unknown frozen estimand") from error
    axis_families = transport_geometry["transport_axis_families"]
    axis_family_ids = [row["transport_axis_family_id"] for row in axis_families]
    if len(axis_family_ids) != len(set(axis_family_ids)):
        raise ProtocolCapacityError("transport axis family identifiers must be unique")
    semantic_axis_sets: set[tuple[str, ...]] = set()
    for family in axis_families:
        if family["reference_estimand_id"] != reference_estimand["estimand_id"]:
            raise ProtocolCapacityError(
                "every transport axis family must bind the frozen reference estimand"
            )
        semantic_axis_set = tuple(sorted(family["required_transport_axis_ids"]))
        if semantic_axis_set in semantic_axis_sets:
            raise ProtocolCapacityError(
                "duplicate semantic transport axis families are alternatives, not additive families"
            )
        semantic_axis_sets.add(semantic_axis_set)
    contexts = transport_geometry["contexts"]
    context_ids = [row["context_id"] for row in contexts]
    if len(context_ids) != len(set(context_ids)):
        raise ProtocolCapacityError("transport context identifiers must be unique")
    context_valid: list[bool] = []
    context_coordinate_rows: list[dict[str, float]] = []
    context_weights: list[float] = []
    context_participant_set_ids: list[str] = []
    base_context_support_ledger: list[dict[str, Any]] = []
    transport_binding_states: list[str] = []
    transport_outcome_resolution_states: list[str] = []
    for context in contexts:
        context_participants = _positive(
            context["participant_count"], name="transport participant_count"
        )
        coordinates: dict[str, float] = {}
        for coordinate in context["transport_coordinates"]:
            axis_id = coordinate["transport_axis_id"]
            if axis_id in coordinates:
                raise ProtocolCapacityError("transport axis identifiers must be unique per context")
            value = float(coordinate["value"])
            if not math.isfinite(value):
                raise ProtocolCapacityError("transport coordinate values must be finite")
            coordinates[axis_id] = value
        allocations: dict[str, float] = {}
        for row in context["policy_allocations"]:
            if row["policy_id"] not in policy_aliases:
                raise ProtocolCapacityError("transport context references unknown policy")
            policy_id = policy_aliases[row["policy_id"]]
            probability = float(row["probability"])
            if not math.isfinite(probability):
                raise ProtocolCapacityError("transport policy probabilities must be finite")
            allocations[policy_id] = allocations.get(policy_id, 0.0) + probability
        if not math.isclose(sum(allocations.values()), 1.0, abs_tol=1e-9):
            raise ProtocolCapacityError("transport policy probabilities must sum to one")
        assignment_time = float(context["assignment_time_offset"])
        if not math.isfinite(assignment_time):
            raise ProtocolCapacityError("transport assignment time offsets must be finite")
        binding = context["estimand_binding"]
        binding_state = binding["state"]
        transport_binding_states.append(binding_state)
        if binding_state == "direct":
            binding_resolved = binding["estimand_id"] == reference_estimand["estimand_id"]
        elif binding_state == "registered_crosswalk":
            # Candidate4 preserves a registered crosswalk as provenance, but it
            # cannot earn numeric transport credit until an executable mapping
            # operator and uncertainty attenuation are authority-bound.
            binding_resolved = False
        else:
            binding_resolved = False
        outcomes = resolve_schedule_ids(context["linked_outcome_schedule_ids"])
        outcome_observer_unresolved = any(
            bool(reference_estimand["outcome_features"] & row["unresolved_features"])
            for row in outcomes
        )
        transport_outcome_resolution_states.append(
            "unresolved" if outcome_observer_unresolved else "resolved"
        )
        participant_linked = bool(outcomes) and all(
            row["participant_set_id"] == context["participant_set_id"] for row in outcomes
        )
        active_outcome_observer = bool(outcomes) and all(
            bool(row["active_features"]) for row in outcomes
        )
        lower = assignment_time + reference_estimand["horizon_start_offset_exclusive"]
        upper = assignment_time + reference_estimand["horizon_end_offset_inclusive"]
        postassignment_offsets_by_schedule = {
            row["schedule_id"]: tuple(
                offset for offset in row["temporal_offsets"] if lower < offset <= upper
            )
            for row in outcomes
        }
        frozen_outcome_observer = bool(outcomes) and all(
            reference_estimand["outcome_features"] <= row["active_features"] for row in outcomes
        )
        every_outcome_strictly_postassignment = bool(outcomes) and all(
            postassignment_offsets_by_schedule[row["schedule_id"]] for row in outcomes
        )
        linked_outcome_support = (
            min(row["participant_count"] * row["retention_fraction"] for row in outcomes)
            if (
                participant_linked
                and active_outcome_observer
                and frozen_outcome_observer
                and every_outcome_strictly_postassignment
            )
            else 0.0
        )
        eligible_context_support = min(context_participants, linked_outcome_support)
        linked = (
            participant_linked
            and active_outcome_observer
            and frozen_outcome_observer
            and binding_resolved
            and every_outcome_strictly_postassignment
            and eligible_context_support > 0
        )
        positive = all(value > 0 for value in allocations.values())
        randomized = context["assignment_mechanism"] in INDEPENDENT_RANDOMIZED_MECHANISMS
        context_valid.append(linked and positive and randomized and len(allocations) >= 2)
        context_coordinate_rows.append(coordinates)
        context_participant_set_ids.append(context["participant_set_id"])
        contrast_support = []
        for contrast in reference_estimand["canonical_operator_contrasts"]:
            coefficients = contrast["coefficients"]
            supported = set(coefficients) <= set(allocations)
            precision = (
                1.0
                / sum(
                    coefficient**2 / (eligible_context_support * allocations[policy_id])
                    for policy_id, coefficient in coefficients.items()
                )
                if linked and supported and eligible_context_support > 0
                else 0.0
            )
            contrast_support.append(
                {
                    "contrast_id": contrast["contrast_id"],
                    "canonical_policy_coefficients": coefficients,
                    "eligible_contrast_precision": precision,
                    "all_contrast_policies_randomized": supported,
                }
            )
        allocation_aware_precision = min(
            (row["eligible_contrast_precision"] for row in contrast_support), default=0.0
        )
        context_valid[-1] = bool(context_valid[-1] and allocation_aware_precision > 0)
        context_weights.append(allocation_aware_precision)
        base_context_support_ledger.append(
            {
                "context_id": context["context_id"],
                "declared_context_participants": context_participants,
                "linked_outcome_retained_participant_support": linked_outcome_support,
                "eligible_transport_participant_support": eligible_context_support,
                "strictly_postassignment_outcome_offset_count": len(
                    {
                        offset
                        for offsets in postassignment_offsets_by_schedule.values()
                        for offset in offsets
                    }
                ),
                "allocation_aware_contrast_precision": allocation_aware_precision,
                "contrast_by_context_support": contrast_support,
                "canonical_policy_allocations": {
                    policy_id: probability for policy_id, probability in sorted(allocations.items())
                },
                "active_outcome_observer": active_outcome_observer,
                "outcome_observer_resolution_state": (
                    "unresolved" if outcome_observer_unresolved else "resolved"
                ),
                "frozen_outcome_definition_observed": frozen_outcome_observer,
                "estimand_binding_state": binding_state,
                "estimand_binding_resolved": binding_resolved,
                "numeric_randomization_supported": randomized,
                "dependence_geometry_required": context["assignment_mechanism"]
                in {"cluster_randomized", "crossover_randomized"},
            }
        )
    base_unresolved_context_ids = sorted(
        context_ids[index]
        for index in range(len(contexts))
        if transport_binding_states[index] != "direct"
        or transport_outcome_resolution_states[index] == "unresolved"
    )

    def compile_transport_axis_family(family: Mapping[str, Any]) -> dict[str, Any]:
        """Compile one authority-frozen transport basis without cross-family selection."""

        required_axis_ids = tuple(family["required_transport_axis_ids"])
        missing_by_index = [
            tuple(axis_id for axis_id in required_axis_ids if axis_id not in coordinates)
            for coordinates in context_coordinate_rows
        ]
        missing_context_id_set = {
            context_ids[index]
            for index, missing_axis_ids in enumerate(missing_by_index)
            if missing_axis_ids
        }
        unresolved_context_ids = sorted(
            context_id
            for context_id in base_unresolved_context_ids
            if context_id not in missing_context_id_set
        )
        unresolved_context_id_set = set(unresolved_context_ids)
        candidate_indices = [
            index
            for index in range(len(contexts))
            if context_valid[index]
            and not missing_by_index[index]
            and context_ids[index] not in unresolved_context_id_set
        ]

        # Multiple contexts for one participant population are mutually
        # exclusive alternatives. Exact Cartesian enumeration is performed on
        # the authority-required projection only. Undeclared extra axes cannot
        # create, delete, or tie-break a numeric family result.
        alternatives: dict[str, dict[tuple[float, ...], int]] = {}
        for index in candidate_indices:
            participant_set_id = context_participant_set_ids[index]
            coordinate_key = tuple(
                context_coordinate_rows[index][axis_id] for axis_id in required_axis_ids
            )
            population_alternatives = alternatives.setdefault(participant_set_id, {})
            incumbent = population_alternatives.get(coordinate_key)
            if (
                incumbent is None
                or context_weights[index] > context_weights[incumbent]
                or (
                    context_weights[index] == context_weights[incumbent]
                    and context_ids[index] < context_ids[incumbent]
                )
            ):
                # At an identical coordinate, greater positive observation
                # precision Loewner-dominates lower precision. Context ID is
                # consulted only when geometry and precision are equivalent.
                population_alternatives[coordinate_key] = index
        combination_count = 0
        selected_transport_subset: dict[str, Any] | None = None
        if len(alternatives) >= 2:
            alternative_rows = [
                [
                    alternatives[participant_set_id][key]
                    for key in sorted(alternatives[participant_set_id])
                ]
                for participant_set_id in sorted(alternatives)
            ]
            combination_count = math.prod(len(rows) for rows in alternative_rows)
            if combination_count > TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT:
                raise ProtocolCapacityError(
                    "transport exact duplicate-population alternative frontier requires "
                    f"{combination_count} combinations for family "
                    f"{family['transport_axis_family_id']!r}, above the runtime resource "
                    f"limit of {TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT}; no "
                    "numeric result was approximated or emitted; split mutually exclusive "
                    "design alternatives into separate protocol scenarios or run with a "
                    "reviewed higher resource limit"
                )
            for selected_tuple in itertools.product(*alternative_rows):
                selected_indices = list(selected_tuple)
                subset_information = contrast_information(
                    [
                        [context_coordinate_rows[index][axis_id] for axis_id in required_axis_ids]
                        for index in selected_indices
                    ],
                    observation_precision=[context_weights[index] for index in selected_indices],
                )
                semantic_key = tuple(
                    (
                        context_participant_set_ids[index],
                        tuple(
                            context_coordinate_rows[index][axis_id] for axis_id in required_axis_ids
                        ),
                        context_weights[index],
                    )
                    for index in selected_indices
                )
                candidate = {
                    "indices": selected_indices,
                    "information": subset_information,
                    "rank": subset_information.rank,
                    "allocation_support_factor": (
                        subset_information.geometric_mean_nonzero_eigenvalue
                    ),
                    "semantic_key": semantic_key,
                    "context_id_key": tuple(context_ids[index] for index in selected_indices),
                }
                candidate_order = (
                    -candidate["rank"],
                    -len(candidate["indices"]),
                    -candidate["allocation_support_factor"],
                    candidate["semantic_key"],
                    candidate["context_id_key"],
                )
                if selected_transport_subset is None:
                    selected_transport_subset = candidate
                else:
                    incumbent_order = (
                        -selected_transport_subset["rank"],
                        -len(selected_transport_subset["indices"]),
                        -selected_transport_subset["allocation_support_factor"],
                        selected_transport_subset["semantic_key"],
                        selected_transport_subset["context_id_key"],
                    )
                    if candidate_order < incumbent_order:
                        selected_transport_subset = candidate

        selected_context_indices = (
            selected_transport_subset["indices"] if selected_transport_subset else []
        )
        selected_context_ids = sorted(context_ids[index] for index in selected_context_indices)
        selected_context_id_set = set(selected_context_ids)
        ineligible_context_ids = sorted(
            context_id
            for context_id in context_ids
            if context_id not in selected_context_id_set
            and context_id not in unresolved_context_id_set
        )
        context_support_ledger = []
        required_axis_id_set = set(required_axis_ids)
        for index, base_row in enumerate(base_context_support_ledger):
            context_id = context_ids[index]
            declared_coordinates = context_coordinate_rows[index]
            missing_axis_ids = list(missing_by_index[index])
            ignored_extra_coordinates = [
                {"transport_axis_id": axis_id, "value": declared_coordinates[axis_id]}
                for axis_id in sorted(set(declared_coordinates) - required_axis_id_set)
            ]
            projected_coordinates = [
                {"transport_axis_id": axis_id, "value": declared_coordinates[axis_id]}
                for axis_id in required_axis_ids
                if axis_id in declared_coordinates
            ]
            if context_id in selected_context_id_set:
                selection_state = "selected"
                selection_reason_codes = ["selected_exact_projected_frontier_member"]
            elif missing_axis_ids:
                selection_state = "ineligible"
                selection_reason_codes = ["missing_required_transport_axes"]
            elif context_id in unresolved_context_id_set:
                selection_state = "unresolved"
                selection_reason_codes = ["unresolved_estimand_or_outcome_binding"]
            elif not context_valid[index]:
                selection_state = "ineligible"
                selection_reason_codes = ["ineligible_assignment_estimand_or_outcome_geometry"]
            else:
                selection_state = "ineligible"
                selection_reason_codes = ["unselected_duplicate_population_alternative"]
            context_support_ledger.append(
                {
                    **copy.deepcopy(base_row),
                    "selection_state": selection_state,
                    "declared_transport_axis_ids": sorted(declared_coordinates),
                    "required_transport_axis_ids": list(required_axis_ids),
                    "projected_transport_coordinates": projected_coordinates,
                    "missing_required_transport_axis_ids": missing_axis_ids,
                    "ignored_extra_transport_coordinates": ignored_extra_coordinates,
                    "selection_reason_codes": selection_reason_codes,
                }
            )

        transport_information = (
            selected_transport_subset["information"] if selected_transport_subset else None
        )
        transport_rank = transport_information.rank if transport_information else 0
        rank_receipt = (
            _rank_receipt(np.asarray(transport_information.information_matrix, dtype=float))
            if transport_information
            else _rank_receipt(np.zeros((len(required_axis_ids),) * 2, dtype=float))
        )
        has_known_subset = len(selected_context_ids) >= 2
        resolution_state = (
            "partial_known_lower_bound_with_ineligible_or_unresolved_contexts"
            if has_known_subset and (ineligible_context_ids or unresolved_context_ids)
            else (
                "unresolved_no_known_context_subset"
                if not has_known_subset and unresolved_context_ids
                else ("resolved" if has_known_subset else "resolved_no_eligible_context_subset")
            )
        )
        family_geometry = {
            "reference_estimand_id": family["reference_estimand_id"],
            "required_transport_axis_ids": list(required_axis_ids),
            "coordinate_scale_authority": family["coordinate_scale_authority"],
        }
        return {
            "transport_axis_family_id": family["transport_axis_family_id"],
            "family_geometry_sha256": _canonical_sha256(family_geometry),
            **family_geometry,
            "resolution_state": resolution_state,
            "selection_rule": "project contexts onto the authority-required ordered axes, ledger and ignore extras, then select the maximal exact duplicate-population alternative frontier member without cross-family competition",
            "selected_context_ids": selected_context_ids,
            "ineligible_context_ids": ineligible_context_ids,
            "unresolved_context_ids": unresolved_context_ids,
            "transport_rank": (
                None if not has_known_subset and unresolved_context_ids else transport_rank
            ),
            "rank_tolerance_receipt": (
                None if not has_known_subset and unresolved_context_ids else rank_receipt
            ),
            "transport_allocation_support_factor": (
                None
                if not has_known_subset and unresolved_context_ids
                else (
                    selected_transport_subset["allocation_support_factor"]
                    if selected_transport_subset
                    else 0.0
                )
            ),
            "gates": {
                "T_transport": (
                    None
                    if not has_known_subset and unresolved_context_ids
                    else bool(transport_rank > 0)
                )
            },
            "exact_frontier_combination_count": combination_count,
            "all_contexts_randomized_positive_outcome_linked_and_axis_complete": bool(
                len(selected_context_ids) == len(contexts)
                and all(context_valid)
                and not any(missing_by_index)
            ),
            "context_support_ledger": context_support_ledger,
        }

    axis_family_frontier = sorted(
        (compile_transport_axis_family(family) for family in axis_families),
        key=lambda row: (row["family_geometry_sha256"], row["transport_axis_family_id"]),
    )
    total_frontier_combinations = sum(
        row["exact_frontier_combination_count"] for row in axis_family_frontier
    )
    if total_frontier_combinations > TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT:
        raise ProtocolCapacityError(
            "transport exact axis-family frontiers require "
            f"{total_frontier_combinations} total combinations, above the runtime resource "
            f"limit of {TRANSPORT_EXACT_FRONTIER_RUNTIME_COMBINATION_LIMIT}; no numeric "
            "result was approximated or emitted"
        )

    scalar_alias_state = (
        "single_axis_family_alias"
        if len(axis_family_frontier) == 1
        else "multiple_axis_families_vector_only"
    )
    alias_family = axis_family_frontier[0] if len(axis_family_frontier) == 1 else None
    selected_context_ids = alias_family["selected_context_ids"] if alias_family else []
    ineligible_context_ids = alias_family["ineligible_context_ids"] if alias_family else []
    unresolved_context_ids = alias_family["unresolved_context_ids"] if alias_family else []
    selected_axis_ids = alias_family["required_transport_axis_ids"] if alias_family else []
    common_transport_axes: bool | None = (
        bool(selected_context_ids and selected_axis_ids) if alias_family else None
    )
    raw_transport_rank: int | None = alias_family["transport_rank"] if alias_family else None
    transport_rank = alias_family["transport_rank"] if alias_family else None
    transport_rank_receipt = alias_family["rank_tolerance_receipt"] if alias_family else None
    t_gate = alias_family["gates"]["T_transport"] if alias_family else None
    context_support_ledger = (
        alias_family["context_support_ledger"]
        if alias_family
        else [
            {
                **copy.deepcopy(row),
                "selection_state": "family_specific",
                "declared_transport_axis_ids": sorted(context_coordinate_rows[index]),
                "required_transport_axis_ids": [],
                "projected_transport_coordinates": [],
                "missing_required_transport_axis_ids": [],
                "ignored_extra_transport_coordinates": [],
                "selection_reason_codes": ["see_axis_family_frontier"],
            }
            for index, row in enumerate(base_context_support_ledger)
        ]
    )
    eligible_stages = [
        row
        for row in stage_ledger
        if row["eligible_for_causal_summary"]
        and row["outcome_observer_resolution_state"] == "resolved"
    ]

    stage_by_id = {row["stage_id"]: row for row in stage_ledger}
    registered_sets = causal.get("stage_aggregation_sets", [])
    registered_set_ids = [row["stage_set_id"] for row in registered_sets]
    if len(registered_set_ids) != len(set(registered_set_ids)):
        raise ProtocolCapacityError("stage aggregation set identifiers must be unique")
    registered_member_ids: set[str] = set()

    def identical(rows: list[dict[str, Any]], key: str) -> bool:
        return len({_canonical_sha256(row[key]) for row in rows}) == 1

    def tri_state_all(values: list[bool | None]) -> bool | None:
        if any(value is False for value in values):
            return False
        if any(value is None for value in values):
            return None
        return True

    def support_factor(matrix: np.ndarray, receipt: Mapping[str, Any]) -> float:
        eigenvalues = np.linalg.eigvalsh(matrix)
        positive = eigenvalues[eigenvalues > receipt["absolute_threshold"]]
        return float(math.exp(np.mean(np.log(positive)))) if positive.size else 0.0

    def summarize_stage_set(
        rows: list[dict[str, Any]], authority: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        ordered = sorted(rows, key=lambda row: row["stage_id"])
        if not ordered:
            raise ProtocolCapacityError("stage set cannot be empty")
        stage_ids = [row["stage_id"] for row in ordered]
        internal = [stage_internal_geometry[stage_id] for stage_id in stage_ids]
        if authority is not None:
            if (
                authority["aggregation_rule"]
                != ("sum_information_across_disjoint_participant_sets")
                or authority["participant_relation"] != "mutually_disjoint_participant_sets"
            ):
                raise ProtocolCapacityError(
                    "registered stage sets require the supported disjoint-information rule"
                )
            if len({row["participant_set_id"] for row in ordered}) != len(ordered):
                raise ProtocolCapacityError(
                    "registered stage set participants must be mutually disjoint"
                )
            aggregation_rule = authority["aggregation_rule"]
            participant_relation = authority["participant_relation"]
            stage_set_id = authority["stage_set_id"]
            authority_sha = authority["source_object_sha256"]
            authority_locator = authority["source_locator"]
        else:
            aggregation_rule = "single_stage_no_cross_stage_aggregation"
            participant_relation = "single_participant_set"
            stage_set_id = f"single-stage:{stage_ids[0]}"
            authority_sha = internal[0]["source_object_sha256"]
            authority_locator = internal[0]["source_locator"]
        compatibility_keys = (
            "assignment_mechanism",
            "canonical_policy_ids",
            "canonical_policy_allocations",
            "outcome_geometry_sha256",
            "moderator_geometry_sha256",
            "decision_rule_operator_id",
            "decision_rule_geometry_state",
            "smart_path_geometry_state",
            "smart_response_state_prevalence_state",
            "smart_between_state_policy_distribution_rank",
            "smart_minimum_conditional_policy_probability",
            "smart_component_marginals_preserved",
            "smart_probability_semantics",
        )
        if any(not identical(ordered, key) for key in compatibility_keys):
            raise ProtocolCapacityError(
                "registered stage set members must share one assignment, policy, outcome, "
                "moderator, decision-rule, and SMART estimand class"
            )
        matrix_keys = (
            "policy_information_matrix",
            "component_information_matrix",
            "sequential_moderator_information_matrix",
        )
        combined: dict[str, np.ndarray] = {}
        for key in matrix_keys:
            shapes = {row[key].shape for row in internal}
            if len(shapes) != 1:
                raise ProtocolCapacityError(
                    "registered stage set information matrices must have aligned dimensions"
                )
            combined[key] = sum(
                (row[key] for row in internal),
                np.zeros_like(internal[0][key]),
            )
        policy_receipt = _rank_receipt(combined["policy_information_matrix"])
        component_receipt = _rank_receipt(combined["component_information_matrix"])
        moderator_receipt = _rank_receipt(combined["sequential_moderator_information_matrix"])
        epoch_index_sets = [set(row["epoch_information"]) for row in internal]
        if len({_canonical_sha256(sorted(values)) for values in epoch_index_sets}) != 1:
            raise ProtocolCapacityError(
                "registered stage set members must expose the same decision-epoch blocks"
            )
        epoch_rows_by_stage = [
            {row["epoch_index"]: row for row in stage["epoch_support_ledger"]} for stage in ordered
        ]
        epoch_support_vector = []
        for epoch_index in sorted(epoch_index_sets[0]):
            epoch_internal = [row["epoch_information"][epoch_index] for row in internal]
            epoch_public = [row[epoch_index] for row in epoch_rows_by_stage]
            if (
                len(
                    {
                        (
                            row["decision_time_offset"],
                            row["decision_epoch_multiplicity"],
                        )
                        for row in epoch_internal
                    }
                )
                != 1
            ):
                raise ProtocolCapacityError(
                    "registered stage set decision epochs must align by time and multiplicity"
                )
            epoch_combined = {
                key: sum(
                    (row[key] for row in epoch_internal),
                    np.zeros_like(epoch_internal[0][key]),
                )
                for key in matrix_keys
            }
            epoch_receipts = {key: _rank_receipt(matrix) for key, matrix in epoch_combined.items()}
            epoch_support_vector.append(
                {
                    "epoch_index": epoch_index,
                    "decision_time_offset": epoch_internal[0]["decision_time_offset"],
                    "decision_epoch_multiplicity": epoch_internal[0]["decision_epoch_multiplicity"],
                    "estimand_contrast_count": epoch_public[0]["estimand_contrast_count"],
                    "policy_rank": epoch_receipts["policy_information_matrix"]["effective_rank"],
                    "component_rank": epoch_receipts["component_information_matrix"][
                        "effective_rank"
                    ],
                    "sequential_moderator_rank": epoch_receipts[
                        "sequential_moderator_information_matrix"
                    ]["effective_rank"],
                    "policy_allocation_support_factor": support_factor(
                        epoch_combined["policy_information_matrix"],
                        epoch_receipts["policy_information_matrix"],
                    ),
                    "component_allocation_support_factor": support_factor(
                        epoch_combined["component_information_matrix"],
                        epoch_receipts["component_information_matrix"],
                    ),
                    "sequential_moderator_allocation_support_factor": support_factor(
                        epoch_combined["sequential_moderator_information_matrix"],
                        epoch_receipts["sequential_moderator_information_matrix"],
                    ),
                    "minimum_member_component_allocation_support_factor": min(
                        row["component_allocation_support_factor"] for row in epoch_public
                    ),
                    "minimum_member_sequential_moderator_allocation_support_factor": min(
                        row["sequential_moderator_allocation_support_factor"]
                        for row in epoch_public
                    ),
                    "minimum_member_eligible_outcome_participant_decisions": min(
                        row["eligible_outcome_participant_decisions"] for row in epoch_public
                    ),
                    "minimum_member_eligible_moderator_participant_decisions": min(
                        row["eligible_moderator_participant_decisions"] for row in epoch_public
                    ),
                    "policy_information_matrix_sha256": _canonical_sha256(
                        epoch_combined["policy_information_matrix"].tolist()
                    ),
                    "component_information_matrix_sha256": _canonical_sha256(
                        epoch_combined["component_information_matrix"].tolist()
                    ),
                    "sequential_moderator_information_matrix_sha256": _canonical_sha256(
                        epoch_combined["sequential_moderator_information_matrix"].tolist()
                    ),
                }
            )
        response_support_values = [
            row["smart_minimum_response_state_participant_support"] for row in ordered
        ]
        return {
            "stage_set_id": stage_set_id,
            "stage_ids": stage_ids,
            "aggregation_rule": aggregation_rule,
            "participant_relation": participant_relation,
            "aggregation_authority_sha256": authority_sha,
            "aggregation_authority_locator": authority_locator,
            "assignment_mechanism": ordered[0]["assignment_mechanism"],
            "canonical_policy_ids": ordered[0]["canonical_policy_ids"],
            "canonical_policy_allocations": ordered[0]["canonical_policy_allocations"],
            "policy_rank": policy_receipt["effective_rank"],
            "component_rank": component_receipt["effective_rank"],
            "epoch_block_policy_rank": sum(row["policy_rank"] for row in epoch_support_vector),
            "sequential_moderator_rank": moderator_receipt["effective_rank"],
            "epoch_block_sequential_moderator_rank": sum(
                row["sequential_moderator_rank"] for row in epoch_support_vector
            ),
            "policy_rank_tolerance_receipt": policy_receipt,
            "component_rank_tolerance_receipt": component_receipt,
            "sequential_moderator_rank_tolerance_receipt": moderator_receipt,
            "policy_information_matrix_sha256": _canonical_sha256(
                combined["policy_information_matrix"].tolist()
            ),
            "component_information_matrix_sha256": _canonical_sha256(
                combined["component_information_matrix"].tolist()
            ),
            "sequential_moderator_information_matrix_sha256": _canonical_sha256(
                combined["sequential_moderator_information_matrix"].tolist()
            ),
            "outcome_geometry_sha256": ordered[0]["outcome_geometry_sha256"],
            "moderator_geometry_sha256": ordered[0]["moderator_geometry_sha256"],
            "policy_allocation_support_factor": support_factor(
                combined["policy_information_matrix"], policy_receipt
            ),
            "component_allocation_support_factor": support_factor(
                combined["component_information_matrix"], component_receipt
            ),
            "sequential_moderator_allocation_support_factor": support_factor(
                combined["sequential_moderator_information_matrix"], moderator_receipt
            ),
            "randomized_participants": sum(row["randomized_participants"] for row in ordered),
            "randomized_participant_decisions": sum(
                row["randomized_participant_decisions"] for row in ordered
            ),
            "randomized_moderator_participant_decisions": sum(
                row["randomized_moderator_participant_decisions"] for row in ordered
            ),
            "structural_personalization_eligible": all(
                row["structural_personalization_eligible"] for row in ordered
            ),
            "smart_structural_personalization_eligible": all(
                row["smart_structural_personalization_eligible"] for row in ordered
            ),
            "smart_response_state_prevalence_state": ordered[0][
                "smart_response_state_prevalence_state"
            ],
            "smart_between_state_policy_distribution_rank": ordered[0][
                "smart_between_state_policy_distribution_rank"
            ],
            "smart_minimum_conditional_policy_probability": ordered[0][
                "smart_minimum_conditional_policy_probability"
            ],
            "smart_minimum_response_state_participant_support": (
                sum(float(value) for value in response_support_values)
                if all(value is not None for value in response_support_values)
                else None
            ),
            "smart_component_marginals_preserved": all(
                row["smart_component_marginals_preserved"] for row in ordered
            ),
            "smart_path_count": sum(row["smart_path_count"] for row in ordered),
            "smart_probability_semantics": ordered[0]["smart_probability_semantics"],
            "epoch_support_vector": epoch_support_vector,
            "gates": {
                gate: tri_state_all([row["gates"][gate] for row in ordered])
                for gate in (
                    "D_dynamic_operator",
                    "P_personalized_policy",
                    "H_heterogeneous_response",
                )
            },
        }

    all_groups: list[dict[str, Any]] = []
    for registered_set in registered_sets:
        member_ids = list(registered_set["stage_ids"])
        if any(stage_id not in stage_by_id for stage_id in member_ids):
            raise ProtocolCapacityError(
                "stage aggregation set references a deduplicated, missing, or unknown stage"
            )
        overlap = registered_member_ids & set(member_ids)
        if overlap:
            raise ProtocolCapacityError(
                "one assignment stage cannot belong to multiple aggregation sets"
            )
        registered_member_ids.update(member_ids)
        all_groups.append(
            summarize_stage_set([stage_by_id[stage_id] for stage_id in member_ids], registered_set)
        )
    all_groups.extend(
        summarize_stage_set([row], None)
        for row in stage_ledger
        if row["stage_id"] not in registered_member_ids
    )

    causal_groups = [
        group
        for group in all_groups
        if all(stage_by_id[stage_id] in eligible_stages for stage_id in group["stage_ids"])
    ]
    selected_causal = max(
        causal_groups,
        key=lambda row: (
            row["policy_rank"],
            row["component_rank"],
            min(
                row["policy_allocation_support_factor"],
                row["component_allocation_support_factor"],
            ),
            row["randomized_participants"],
            row["stage_set_id"],
        ),
        default=None,
    )
    personalized_groups = [
        group
        for group in causal_groups
        if all(
            stage_by_id[stage_id]["moderator_supported_pre_assignment"]
            and stage_by_id[stage_id]["moderator_population_geometry_state"] == "registered"
            for stage_id in group["stage_ids"]
        )
    ]
    selected_personalized = max(
        personalized_groups,
        key=lambda row: (
            row["sequential_moderator_rank"],
            row["sequential_moderator_allocation_support_factor"],
            row["randomized_moderator_participant_decisions"],
            row["stage_set_id"],
        ),
        default=None,
    )

    def selected_value(row: Mapping[str, Any] | None, key: str, default: Any) -> Any:
        return row[key] if row is not None else default

    # Measurement depth needs complete joint covariance, but randomized
    # identifiability only depends on the estimand-linked outcome observer.
    # An unrelated unresolved assay block must not erase a valid causal design.
    unresolved_causal_stage_ids = sorted(
        row["stage_id"]
        for row in stage_ledger
        if (
            row["numeric_randomization_supported"]
            and row["outcome_observer_resolution_state"] == "unresolved"
        )
    )
    unresolved_personalized_stage_ids = sorted(
        row["stage_id"]
        for row in stage_ledger
        if row["numeric_randomization_supported"]
        and (
            row["outcome_observer_resolution_state"] == "unresolved"
            or (
                row["eligible_for_causal_summary"]
                and (
                    row["moderator_population_geometry_state"] == "unknown"
                    or row["decision_rule_geometry_state"] == "unknown"
                )
            )
        )
    )
    causal_has_known_candidate = selected_causal is not None
    personalized_has_known_candidate = selected_personalized is not None
    causal_resolution_state = (
        "partial_known_lower_bound_with_unresolved_alternatives"
        if causal_has_known_candidate and unresolved_causal_stage_ids
        else ("unresolved_no_known_candidate" if unresolved_causal_stage_ids else "resolved")
    )
    personalized_resolution_state = (
        "partial_known_lower_bound_with_unresolved_alternatives"
        if personalized_has_known_candidate and unresolved_personalized_stage_ids
        else ("unresolved_no_known_candidate" if unresolved_personalized_stage_ids else "resolved")
    )
    selected_personalized_branch_support_unknown = bool(
        selected_personalized
        and selected_personalized["smart_structural_personalization_eligible"]
        and selected_personalized["smart_response_state_prevalence_state"] == "unknown"
    )
    if alias_family:
        transport_resolution_state = alias_family["resolution_state"]
    else:
        unresolved_family_rows = [
            row
            for row in axis_family_frontier
            if row["resolution_state"]
            in {
                "partial_known_lower_bound_with_ineligible_or_unresolved_contexts",
                "unresolved_no_known_context_subset",
            }
        ]
        numerically_resolved_family_rows = [
            row for row in axis_family_frontier if row["transport_rank"] is not None
        ]
        transport_resolution_state = (
            "resolved_axis_family_vector"
            if not unresolved_family_rows
            else (
                "partial_axis_family_vector_with_unresolved_members"
                if numerically_resolved_family_rows
                else "unresolved_axis_family_vector"
            )
        )

    return {
        "causal": {
            "definition": "one coherent randomized stage or one authority-registered homogeneous stage set over mutually disjoint participant sets; heterogeneous stage classes remain alternatives",
            "allocation_support_factor_definition": "allocation-and-linked-participant support proxy only; excludes outcome noise, operator uncertainty, temporal covariance, biological information, and inferential precision",
            "resolution_state": causal_resolution_state,
            "selection_rule": "select one coherent stage-set frontier member lexicographically; only an explicit disjoint-participant aggregation authority may sum aligned information matrices, and metrics are never mixed across frontier members",
            "selected_stage_set_id": selected_value(selected_causal, "stage_set_id", None),
            "selected_stage_ids": selected_value(selected_causal, "stage_ids", []),
            "stage_set_frontier": causal_groups,
            "unresolved_alternative_stage_ids": unresolved_causal_stage_ids,
            "policy_rank": (
                None
                if not causal_has_known_candidate and unresolved_causal_stage_ids
                else selected_value(selected_causal, "policy_rank", 0)
            ),
            "component_rank": (
                None
                if not causal_has_known_candidate and unresolved_causal_stage_ids
                else selected_value(selected_causal, "component_rank", 0)
            ),
            "outcome_geometry_sha256": selected_value(
                selected_causal, "outcome_geometry_sha256", None
            ),
            "policy_allocation_support_factor": (
                None
                if not causal_has_known_candidate and unresolved_causal_stage_ids
                else selected_value(selected_causal, "policy_allocation_support_factor", 0.0)
            ),
            "component_allocation_support_factor": (
                None
                if not causal_has_known_candidate and unresolved_causal_stage_ids
                else selected_value(selected_causal, "component_allocation_support_factor", 0.0)
            ),
            "eligible_randomized_participants": selected_value(
                selected_causal, "randomized_participants", 0.0
            ),
            "eligible_randomized_participant_decisions": selected_value(
                selected_causal, "randomized_participant_decisions", 0.0
            ),
            "gates": {
                "D_dynamic_operator": (
                    None
                    if not causal_has_known_candidate and unresolved_causal_stage_ids
                    else bool(selected_causal and selected_causal["gates"]["D_dynamic_operator"])
                )
            },
            "stage_ledger": stage_ledger,
            "canonical_policy_count": len(policy_ids),
            "policy_alias_count_removed": len(policy_aliases) - len(policy_ids),
        },
        "personalized_sequential": {
            "definition": "one coherent state-moderated randomized stage or one authority-registered homogeneous stage set over mutually disjoint participant sets, using decision-level treatment contrast x population moderator covariance geometry",
            "allocation_support_factor_definition": "allocation, linked-participant, and registered moderator-geometry support proxy only; excludes outcome noise, operator uncertainty, temporal covariance, biological information, and inferential precision",
            "resolution_state": personalized_resolution_state,
            "selection_rule": "select one coherent stage-set frontier member without cross-member metric mixing or moderator-ID rank credit",
            "selected_stage_set_id": selected_value(selected_personalized, "stage_set_id", None),
            "selected_stage_ids": selected_value(selected_personalized, "stage_ids", []),
            "stage_set_frontier": personalized_groups,
            "unresolved_alternative_stage_ids": unresolved_personalized_stage_ids,
            "sequential_moderator_rank": (
                None
                if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                else selected_value(selected_personalized, "sequential_moderator_rank", 0)
            ),
            "outcome_geometry_sha256": selected_value(
                selected_personalized, "outcome_geometry_sha256", None
            ),
            "moderator_geometry_sha256": selected_value(
                selected_personalized, "moderator_geometry_sha256", None
            ),
            "sequential_moderator_allocation_support_factor": (
                None
                if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                else selected_value(
                    selected_personalized,
                    "sequential_moderator_allocation_support_factor",
                    0.0,
                )
            ),
            "eligible_randomized_participants": selected_value(
                selected_personalized, "randomized_participants", 0.0
            ),
            "eligible_randomized_participant_decisions": selected_value(
                selected_personalized, "randomized_moderator_participant_decisions", 0.0
            ),
            "structural_personalization_eligible": (
                None
                if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                else bool(
                    selected_personalized
                    and selected_personalized["structural_personalization_eligible"]
                )
            ),
            "numeric_branch_support_state": (
                "unknown_response_state_prevalence"
                if selected_personalized_branch_support_unknown
                else (
                    "registered"
                    if selected_personalized
                    and selected_personalized["smart_response_state_prevalence_state"]
                    == "registered"
                    else "not_applicable"
                )
            ),
            "response_state_prevalence_state": selected_value(
                selected_personalized,
                "smart_response_state_prevalence_state",
                "not_applicable",
            ),
            "between_state_policy_distribution_rank": (
                None
                if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                else selected_value(
                    selected_personalized,
                    "smart_between_state_policy_distribution_rank",
                    0,
                )
            ),
            "minimum_conditional_policy_probability": selected_value(
                selected_personalized,
                "smart_minimum_conditional_policy_probability",
                None,
            ),
            "minimum_response_state_participant_support": (
                None
                if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                else selected_value(
                    selected_personalized,
                    "smart_minimum_response_state_participant_support",
                    None,
                )
            ),
            "component_marginals_preserved_within_response_states": (
                None
                if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                else bool(
                    selected_personalized
                    and selected_personalized["smart_component_marginals_preserved"]
                )
            ),
            "smart_path_count": selected_value(selected_personalized, "smart_path_count", 0),
            "smart_probability_semantics": selected_value(
                selected_personalized, "smart_probability_semantics", None
            ),
            "gates": {
                "P_personalized_policy": (
                    None
                    if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                    else (
                        selected_personalized["gates"]["P_personalized_policy"]
                        if selected_personalized
                        else False
                    )
                ),
                "H_heterogeneous_response": (
                    None
                    if not personalized_has_known_candidate and unresolved_personalized_stage_ids
                    else bool(
                        selected_personalized
                        and selected_personalized["gates"]["H_heterogeneous_response"]
                    )
                ),
            },
            "stage_ledger": stage_ledger,
        },
        "transport": {
            "definition": "a noncompensatory vector of authority-frozen transport-axis families for one frozen outcome/operator/horizon estimand, with source-bound crosswalks when required",
            "allocation_support_factor_definition": "context-coordinate, allocation, and linked-participant support proxy only; excludes outcome noise, operator uncertainty, temporal covariance, biological information, and inferential precision",
            "resolution_state": transport_resolution_state,
            "selection_rule": "compile every authority-declared axis family independently after required-axis projection; never winner-select across families; expose top-level numeric fields only as a single-family alias",
            "scalar_alias_state": scalar_alias_state,
            "axis_family_frontier": axis_family_frontier,
            "selected_context_ids": selected_context_ids,
            "ineligible_context_ids": ineligible_context_ids,
            "unresolved_context_ids": unresolved_context_ids,
            "transport_rank": transport_rank,
            "rank_tolerance_receipt": transport_rank_receipt,
            "transport_allocation_support_factor": (
                alias_family["transport_allocation_support_factor"] if alias_family else None
            ),
            "gates": {"T_transport": t_gate},
            "transport_ledger": {
                "context_count": len(contexts),
                "raw_context_contrast_rank": raw_transport_rank,
                "common_transport_axes": common_transport_axes,
                "axis_family_count": len(axis_family_frontier),
                "exact_frontier_combination_count": total_frontier_combinations,
                "reference_estimand_id": reference_estimand["estimand_id"],
                "reference_estimand_geometry_sha256": reference_estimand["geometry_sha256"],
                "reference_outcome_definition_id": reference_estimand["outcome_definition_id"],
                "reference_operator_contrast_ids": [
                    row["contrast_id"] for row in reference_estimand["canonical_operator_contrasts"]
                ],
                "reference_horizon": {
                    "start_offset_exclusive": reference_estimand["horizon_start_offset_exclusive"],
                    "end_offset_inclusive": reference_estimand["horizon_end_offset_inclusive"],
                },
                "transport_axis_ids": selected_axis_ids,
                "common_estimand_policy_ids": sorted(
                    {
                        policy_id
                        for contrast in reference_estimand["canonical_operator_contrasts"]
                        for policy_id in contrast["coefficients"]
                    }
                ),
                "all_contexts_randomized_positive_and_outcome_linked": (
                    alias_family[
                        "all_contexts_randomized_positive_outcome_linked_and_axis_complete"
                    ]
                    if alias_family
                    else None
                ),
                "context_support_ledger": context_support_ledger,
            },
        },
    }


def _compile_scenario(protocol: Mapping[str, Any]) -> dict[str, Any]:
    measurement = _measurement_families(protocol)
    signal_index = measurement.pop("_signal_index")
    covariance_memberships = measurement.pop("_covariance_memberships")
    covariance_matrices = measurement.pop("_covariance_matrices")
    parameter_dimension = measurement.pop("_parameter_dimension")
    measurement_resolution_state = measurement.pop("_measurement_resolution_state")
    intervention_families = _causal_family(
        protocol,
        measurement.pop("_schedule_registry"),
        measurement.pop("_schedule_aliases"),
        measurement.pop("_eligible_features"),
        signal_index,
        covariance_memberships,
        covariance_matrices,
        parameter_dimension,
        measurement_resolution_state,
    )
    return {**measurement, **intervention_families}


def _get_path(value: Mapping[str, Any], path: str) -> Any:
    cursor: Any = value
    for key in path.split("."):
        cursor = cursor[key]
    return cursor


def _uncertainty_reuse(protocol: Mapping[str, Any], scenario_count: int) -> dict[str, Any]:
    coordinate_states: dict[str, int] = {}
    for _, coordinate in _walk_coordinates(protocol):
        state = coordinate["state"]
        coordinate_states[state] = coordinate_states.get(state, 0) + 1

    source_hashes: set[str] = set()
    source_locators: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "source_object_sha256":
                    source_hashes.add(str(child))
                elif key == "source_locator":
                    source_locators.add(str(child))
                else:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(protocol)
    return {
        "definition": "typed planning uncertainty and source-bound reusable geometry",
        "coordinate_state_counts": coordinate_states,
        "scenario_count": scenario_count,
        "source_object_count": len(source_hashes),
        "source_locator_count": len(source_locators),
        "parameter_space_id": protocol["parameter_space"]["parameter_space_id"],
        "parameter_space_source_object_sha256": protocol["parameter_space"]["source_object_sha256"],
        "covariance_controls_required": True,
        "canonical_ancestry_controls_required": True,
    }


def compile_protocol_capacity(protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Compile prospective capacity without empirical-attainment or rank claims."""

    _validate(protocol)
    scenario_rows = []
    for scenario_id, resolved in _scenarios(protocol):
        scenario_rows.append({"scenario_id": scenario_id, "families": _compile_scenario(resolved)})
    transport_axis_family_ids = sorted(
        row["transport_axis_family_id"]
        for row in protocol["causal_geometry"]["transport_geometry"]["transport_axis_families"]
    )
    envelope_paths = (
        "intensive.effective_rank",
        "intensive.maximum_joint_bundle_log10_contraction",
        "extensive.retained_participant_events",
        "extensive.effective_rank",
        "extensive.retained_log10_contraction",
        "longitudinal.participant_weighted_median_distinct_offsets",
        "longitudinal.participant_weighted_median_span",
        "longitudinal.retained_participant_events",
        "causal.policy_rank",
        "causal.component_rank",
        "causal.policy_allocation_support_factor",
        "causal.component_allocation_support_factor",
        "causal.eligible_randomized_participants",
        "causal.eligible_randomized_participant_decisions",
        "personalized_sequential.sequential_moderator_rank",
        "personalized_sequential.sequential_moderator_allocation_support_factor",
        "personalized_sequential.eligible_randomized_participants",
        "personalized_sequential.eligible_randomized_participant_decisions",
    )
    if len(transport_axis_family_ids) == 1:
        envelope_paths += (
            "transport.transport_rank",
            "transport.transport_allocation_support_factor",
        )
    envelopes = {}

    def set_envelope(path: str, values: list[float | int | None]) -> None:
        if any(value is None for value in values):
            resolved_values = [value for value in values if value is not None]
            envelopes[path] = {
                "resolution_state": "unresolved",
                "minimum": min(resolved_values) if resolved_values else None,
                "maximum": max(resolved_values) if resolved_values else None,
                "resolved_scenario_count": len(resolved_values),
                "total_scenario_count": len(values),
            }
        else:
            envelopes[path] = {"minimum": min(values), "maximum": max(values)}

    for path in envelope_paths:
        set_envelope(path, [_get_path(row["families"], path) for row in scenario_rows])
    for family_id in transport_axis_family_ids:
        for metric in ("transport_rank", "transport_allocation_support_factor"):
            values = []
            for scenario in scenario_rows:
                matches = [
                    row
                    for row in scenario["families"]["transport"]["axis_family_frontier"]
                    if row["transport_axis_family_id"] == family_id
                ]
                if len(matches) != 1:
                    raise ProtocolCapacityError(
                        "scenario transport family frontier does not preserve declared family identity"
                    )
                values.append(matches[0][metric])
            set_envelope(f"transport.axis_families.{family_id}.{metric}", values)
    return {
        "schema_version": "anibench.protocol-capacity-result.v2",
        "compiler_version": PROTOCOL_CAPACITY_VERSION,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": _canonical_sha256(protocol),
        "claim_class": protocol["claim_class"],
        "empirical_attainment": False,
        "public_rank_emission_permitted": False,
        "comparison_eligible": False,
        "ontology_binding_state": "custom_unverified",
        "source_binding_state": {
            "protocol_input": "canonical_hash_computed_and_bound",
            "external_objects": "caller_declared_not_content_verified",
        },
        "overall_scalar": None,
        "scenario_count": len(scenario_rows),
        "scenarios": scenario_rows,
        "family_envelopes": envelopes,
        "uncertainty_reuse": _uncertainty_reuse(protocol, len(scenario_rows)),
        "anti_gaming_contract": {
            "caller_supplied_ranks_accepted": False,
            "canonical_feature_aliases_deduplicated": True,
            "module_menu_splitting_invariant": True,
            "participant_event_lineage_deduplicated": True,
            "same_event_support_requires_one_joint_bundle": True,
            "module_schedule_bundle_event_units_must_match": True,
            "one_repetition_model_per_participant_trajectory": True,
            "causal_information_is_attenuated_by_covariance_adjusted_outcome_operator_geometry": True,
            "moderator_rank_uses_covariance_adjusted_operator_geometry": True,
            "moderator_rank_uses_decision_population_kronecker_geometry": True,
            "explicit_decision_epochs_required": True,
            "epoch_availability_history_propensity_and_proximal_links_required": True,
            "personalization_requires_registered_state_to_policy_operator": True,
            "estimand_contrasts_must_have_epoch_assignment_support": True,
            "moderator_information_capped_by_predecision_history_support": True,
            "moderated_information_requires_pointwise_conditional_eligibility_authority": True,
            "moderator_covariance_requires_pointwise_joint_eligible_loewner_lower_bound": True,
            "adaptive_information_uses_minimum_conditional_policy_probability_bounds": True,
            "repeated_decision_information_uses_registered_estimating_score_dependence": True,
            "schedule_retention_lineage_cannot_substitute_for_conditional_interaction_information": True,
            "smart_path_geometry_required_for_smart": True,
            "smart_paths_must_reproduce_epoch_propensity_marginals": True,
            "transport_requires_frozen_estimand_or_registered_crosswalk": True,
            "transport_is_contrast_by_context": True,
            "transport_axis_families_are_coordinate_scale_authority_bound": True,
            "transport_contexts_projected_to_required_axes": True,
            "transport_extra_axes_ledgered_not_scored": True,
            "transport_missing_required_axes_are_ineligible": True,
            "transport_families_never_winner_selected": True,
            "transport_duplicate_population_frontier_exact_per_family": True,
            "joint_covariance_authority_required_without_independence_default": True,
            "unresolved_authority_preserved_as_null_not_zero": True,
            "scale_aware_rank_tolerance_receipted": True,
            "outcomes_must_be_strictly_postdecision": True,
            "same_support_stage_aggregation_without_dependence_geometry": False,
            "transport_precision_is_allocation_aware": True,
            "causal_counts_capped_by_linked_retained_outcomes": True,
            "cluster_and_crossover_require_explicit_dependence_geometry": True,
            "rate_process_requires_registered_window_model": True,
            "population_multiplier_applied_to_intensive_family": False,
            "extensive_unresolved_overlap_requires_source_bound_primary": True,
            "extensive_cross_population_sum_requires_disjoint_authority": True,
            "extensive_registered_nested_threshold_strata_polynomial": True,
            "longitudinal_weighted_summaries_use_retained_support_strata": True,
            "normative_level1_reference_bound": False,
        },
    }
