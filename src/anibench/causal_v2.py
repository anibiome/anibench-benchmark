from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

from .information_v2 import InformationV2Error


V2_CAUSAL_VERSION = "anibench.causal-design.v2-candidate2"


@dataclass(frozen=True)
class DesignInformation:
    rank: int
    smallest_nonzero_eigenvalue: float
    geometric_mean_nonzero_eigenvalue: float
    information_matrix: tuple[tuple[float, ...], ...]
    formula_version: str = V2_CAUSAL_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CausalArchitecture:
    policy: DesignInformation
    component: DesignInformation
    endpoint_policy_identifiable: bool
    dynamic_operator_identifiable: bool
    sequential: DesignInformation | None
    formula_version: str = V2_CAUSAL_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _summarize(matrix: np.ndarray, *, tolerance: float = 1e-10) -> DesignInformation:
    symmetric = 0.5 * (matrix + matrix.T)
    values = np.linalg.eigvalsh(symmetric)
    scale = float(np.max(np.abs(values), initial=0.0))
    relative_tolerance = max(
        tolerance,
        float(np.finfo(float).eps * max(1, symmetric.shape[0]) * 10.0),
    )
    threshold = relative_tolerance * scale if scale > 0.0 else 0.0
    if float(np.min(values, initial=0.0)) < -threshold:
        raise InformationV2Error("design information is materially non-PSD")
    positive = values[values > threshold]
    rank = int(len(positive))
    smallest = float(np.min(positive)) if rank else 0.0
    geometric = float(math.exp(np.mean(np.log(positive)))) if rank else 0.0
    return DesignInformation(
        rank=rank,
        smallest_nonzero_eigenvalue=smallest,
        geometric_mean_nonzero_eigenvalue=geometric,
        # Do not decimal-round mechanics: that creates a hidden absolute unit
        # floor and can change rank/gates under an otherwise harmless unit
        # conversion. JSON float serialization remains deterministic.
        information_matrix=tuple(tuple(float(value) for value in row) for row in symmetric),
    )


def contrast_information(
    design_matrix: Sequence[Sequence[float]] | np.ndarray,
    *,
    observation_precision: Sequence[Sequence[float]] | Sequence[float] | np.ndarray | None = None,
) -> DesignInformation:
    design = np.asarray(design_matrix, dtype=float)
    if design.ndim != 2 or design.shape[0] < 1 or design.shape[1] < 1:
        raise InformationV2Error("design_matrix must be a nonempty matrix")
    if not np.all(np.isfinite(design)):
        raise InformationV2Error("design_matrix contains non-finite values")
    if observation_precision is None:
        precision = np.eye(design.shape[0])
    else:
        precision = np.asarray(observation_precision, dtype=float)
        if precision.ndim == 1:
            if precision.shape[0] != design.shape[0] or np.any(precision < 0):
                raise InformationV2Error("precision weights must be nonnegative and row-aligned")
            precision = np.diag(precision)
        if precision.shape != (design.shape[0], design.shape[0]):
            raise InformationV2Error("observation_precision must match design rows")
        if not np.allclose(precision, precision.T, atol=1e-10, rtol=0.0):
            raise InformationV2Error("observation_precision must be symmetric")
        if float(np.min(np.linalg.eigvalsh(precision))) < -1e-10:
            raise InformationV2Error("observation_precision must be PSD")
    # Contrast columns describe movement across observed assignment support,
    # not arbitrary caller-selected coefficient units. Centering removes
    # intercept leakage; range normalization makes x, 10*x, and x+c the same
    # experimental contrast while row precision retains sample support.
    ones = np.ones(design.shape[0], dtype=float)
    intercept_precision = float(ones @ precision @ ones)
    precision_scale = float(np.max(np.abs(precision), initial=0.0))
    intercept_threshold = (
        float(np.finfo(float).eps * max(precision.shape) * 10.0) * precision_scale
        if precision_scale > 0.0
        else 0.0
    )
    canonical = np.zeros_like(design)
    for column in range(design.shape[1]):
        values = design[:, column]
        span = float(np.max(values) - np.min(values))
        value_scale = float(np.max(np.abs(values), initial=0.0))
        span_threshold = (
            float(np.finfo(float).eps * max(1, values.shape[0]) * 10.0) * value_scale
            if value_scale > 0.0
            else 0.0
        )
        if value_scale == 0.0 or span <= span_threshold:
            continue
        center = (
            float(ones @ precision @ values) / intercept_precision
            if intercept_precision > intercept_threshold
            else float(np.mean(values))
        )
        canonical[:, column] = (values - center) / span
    return _summarize(canonical.T @ precision @ canonical)


def sequential_information(
    actions: Sequence[float],
    assignment_probabilities: Sequence[float],
    state_basis: Sequence[Sequence[float]] | np.ndarray,
    *,
    eligible: Sequence[bool] | None = None,
) -> DesignInformation:
    action = np.asarray(actions, dtype=float)
    probability = np.asarray(assignment_probabilities, dtype=float)
    basis = np.asarray(state_basis, dtype=float)
    if action.ndim != 1 or probability.shape != action.shape:
        raise InformationV2Error("actions and assignment_probabilities must be aligned vectors")
    if basis.ndim != 2 or basis.shape[0] != action.shape[0]:
        raise InformationV2Error("state_basis rows must align with actions")
    if not np.all(np.isfinite(action)) or not np.all(np.isin(action, (0.0, 1.0))):
        raise InformationV2Error("binary sequential actions must be encoded as 0 or 1")
    if not np.all(np.isfinite(probability)):
        raise InformationV2Error("sequential assignment probabilities must be finite")
    if not np.all(np.isfinite(basis)):
        raise InformationV2Error("state_basis contains non-finite values")
    if np.any((probability <= 0) | (probability >= 1)):
        raise InformationV2Error("sequential assignment probabilities must satisfy positivity")
    mask = (
        np.ones(action.shape[0], dtype=bool)
        if eligible is None
        else np.asarray(eligible, dtype=bool)
    )
    if mask.shape != action.shape:
        raise InformationV2Error("eligible must align with actions")
    matrix = np.zeros((basis.shape[1], basis.shape[1]), dtype=float)
    for _observed, propensity, row, include in zip(action, probability, basis, mask):
        if not include:
            continue
        # Expected randomized-design information under unit residual precision.
        # Near-deterministic assignment loses rather than inflates information.
        # Realized outcome precision requires a separate covariance model.
        weight = propensity * (1.0 - propensity)
        matrix += weight * np.outer(row, row)
    return _summarize(matrix)


def causal_architecture(
    *,
    policy_design_matrix: Sequence[Sequence[float]] | np.ndarray,
    component_design_matrix: Sequence[Sequence[float]] | np.ndarray,
    endpoint_measured: bool,
    repeated_linked_biology: bool,
    exogenous_operator_variation: bool,
    observation_precision: Sequence[Sequence[float]] | Sequence[float] | np.ndarray | None = None,
    sequential: DesignInformation | None = None,
) -> CausalArchitecture:
    policy = contrast_information(policy_design_matrix, observation_precision=observation_precision)
    component = contrast_information(
        component_design_matrix, observation_precision=observation_precision
    )
    endpoint_identifiable = bool(endpoint_measured and policy.rank > 0)
    dynamic_identifiable = bool(
        repeated_linked_biology and exogenous_operator_variation and component.rank > 0
    )
    return CausalArchitecture(
        policy=policy,
        component=component,
        endpoint_policy_identifiable=endpoint_identifiable,
        dynamic_operator_identifiable=dynamic_identifiable,
        sequential=sequential,
    )
