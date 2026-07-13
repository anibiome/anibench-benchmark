from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

import numpy as np


V2_INFORMATION_VERSION = "anibench.joint-information.v2-candidate1"
PSD_TOLERANCE = 1e-10


class InformationV2Error(ValueError):
    pass


@dataclass(frozen=True)
class EventContribution:
    event_type_id: str
    design_operator: tuple[tuple[float, ...], ...]
    noise_covariance: tuple[tuple[float, ...], ...]
    effective_count: float
    source_object_id: str


@dataclass(frozen=True)
class AbsoluteMechanics:
    absolute_log10_contraction: float
    generalized_eigenvalues: tuple[float, ...]
    information_matrix_sha256: str
    prior_precision_matrix_sha256: str
    parameter_dimension: int
    formula_version: str = V2_INFORMATION_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceGeometry:
    reference_values: tuple[float, ...]
    reference_direction_basis: tuple[tuple[float, ...], ...]
    reference_matrix_sha256: str
    reference_direction_basis_sha256: str
    parameter_dimension: int


@dataclass(frozen=True)
class ReconstructionMetrics:
    absolute_log10_contraction: float
    level1_completion_percent: float
    level1_overflow: float
    coverage_curve: dict[str, float]
    generalized_eigenvalues: tuple[float, ...]
    reference_direction_information: tuple[float, ...]
    information_matrix_sha256: str
    reference_matrix_sha256: str
    reference_direction_basis_sha256: str
    formula_version: str = V2_INFORMATION_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _array(value: Sequence[Sequence[float]] | np.ndarray, *, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.ndim != 2 or result.shape[0] != result.shape[1]:
        raise InformationV2Error(f"{name} must be a square matrix")
    if not np.all(np.isfinite(result)):
        raise InformationV2Error(f"{name} contains non-finite values")
    return result


def _symmetric(value: np.ndarray, *, name: str, tolerance: float = PSD_TOLERANCE) -> np.ndarray:
    if not np.allclose(value, value.T, atol=tolerance, rtol=0.0):
        raise InformationV2Error(f"{name} must be symmetric")
    return 0.5 * (value + value.T)


def _psd(value: np.ndarray, *, name: str, tolerance: float = PSD_TOLERANCE) -> np.ndarray:
    symmetric = _symmetric(value, name=name, tolerance=tolerance)
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    scale = max(1.0, float(np.max(np.abs(eigenvalues))))
    if float(np.min(eigenvalues)) < -tolerance * scale:
        raise InformationV2Error(f"{name} is materially non-positive-semidefinite")
    clipped = np.maximum(eigenvalues, 0.0)
    projected = (eigenvectors * clipped) @ eigenvectors.T
    # Eigensolver reconstruction can leave absolute antisymmetric roundoff for
    # high-dynamic-range matrices. Preserve the mathematical PSD projection.
    return 0.5 * (projected + projected.T)


def _positive_definite(value: np.ndarray, *, name: str) -> np.ndarray:
    symmetric = _symmetric(value, name=name)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    if float(np.min(eigenvalues)) <= 0.0:
        raise InformationV2Error(f"{name} must be positive definite")
    return symmetric


def _matrix_hash(value: np.ndarray) -> str:
    payload = json.dumps(value.tolist(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_matrix_sha256(
    value: Sequence[Sequence[float]] | np.ndarray,
    *,
    name: str = "matrix",
) -> str:
    """Return the server's canonical numeric-matrix identity."""

    return "sha256:" + _matrix_hash(_array(value, name=name))


def event_information(contribution: EventContribution) -> np.ndarray:
    operator = np.asarray(contribution.design_operator, dtype=float)
    covariance = np.asarray(contribution.noise_covariance, dtype=float)
    if operator.ndim != 2:
        raise InformationV2Error("design_operator must be a matrix")
    if covariance.shape != (operator.shape[0], operator.shape[0]):
        raise InformationV2Error("noise_covariance must match design_operator rows")
    covariance = _positive_definite(covariance, name="noise_covariance")
    count = float(contribution.effective_count)
    if not math.isfinite(count) or count < 0:
        raise InformationV2Error("effective_count must be finite and nonnegative")
    solved = np.linalg.solve(covariance, operator)
    return _psd(count * (operator.T @ solved), name="event information")


def assemble_joint_information(
    contributions: Iterable[EventContribution],
    *,
    parameter_dimension: int | None = None,
) -> np.ndarray:
    rows = list(contributions)
    if not rows:
        if parameter_dimension is None or parameter_dimension < 1:
            raise InformationV2Error("empty event set requires a positive parameter_dimension")
        return np.zeros((parameter_dimension, parameter_dimension), dtype=float)
    matrices = [event_information(row) for row in rows]
    dimensions = {matrix.shape for matrix in matrices}
    if len(dimensions) != 1:
        raise InformationV2Error("all event contributions must share a parameter dimension")
    if parameter_dimension is not None and matrices[0].shape[0] != parameter_dimension:
        raise InformationV2Error("parameter_dimension disagrees with event contributions")
    return _psd(np.sum(matrices, axis=0), name="joint information")


def nuisance_adjusted_information(
    full_information: Sequence[Sequence[float]] | np.ndarray,
    *,
    target_indices: Sequence[int],
    nuisance_indices: Sequence[int],
    nuisance_prior_precision: Sequence[Sequence[float]] | np.ndarray,
) -> np.ndarray:
    full = _psd(_array(full_information, name="full_information"), name="full_information")
    target = tuple(int(index) for index in target_indices)
    nuisance = tuple(int(index) for index in nuisance_indices)
    if not target or set(target) & set(nuisance):
        raise InformationV2Error("target indices must be nonempty and disjoint from nuisance")
    if min((*target, *nuisance), default=0) < 0 or max((*target, *nuisance)) >= full.shape[0]:
        raise InformationV2Error("target or nuisance index is out of range")
    tt = full[np.ix_(target, target)]
    if not nuisance:
        return _psd(tt, name="target information")
    tn = full[np.ix_(target, nuisance)]
    nn = full[np.ix_(nuisance, nuisance)]
    prior = _positive_definite(
        _array(nuisance_prior_precision, name="nuisance_prior_precision"),
        name="nuisance_prior_precision",
    )
    if prior.shape != nn.shape:
        raise InformationV2Error("nuisance prior dimension does not match nuisance block")
    adjusted = tt - tn @ np.linalg.solve(prior + nn, tn.T)
    return _psd(adjusted, name="nuisance-adjusted information", tolerance=1e-8)


def prior_whitened_information(
    information: Sequence[Sequence[float]] | np.ndarray,
    prior_precision: Sequence[Sequence[float]] | np.ndarray,
) -> np.ndarray:
    info = _psd(_array(information, name="information"), name="information")
    prior = _positive_definite(
        _array(prior_precision, name="prior_precision"), name="prior_precision"
    )
    if info.shape != prior.shape:
        raise InformationV2Error("information and prior_precision dimensions differ")
    values, vectors = np.linalg.eigh(prior)
    inverse_sqrt = (vectors * (1.0 / np.sqrt(values))) @ vectors.T
    whitened = inverse_sqrt @ info @ inverse_sqrt
    whitened = 0.5 * (whitened + whitened.T)
    return _psd(whitened, name="prior-whitened information")


def absolute_log10_contraction(
    information: Sequence[Sequence[float]] | np.ndarray,
    prior_precision: Sequence[Sequence[float]] | np.ndarray,
) -> float:
    whitened = prior_whitened_information(information, prior_precision)
    eigenvalues = np.maximum(np.linalg.eigvalsh(whitened), 0.0)
    return float(np.sum(np.log1p(eigenvalues)) / (2.0 * math.log(10.0)))


def absolute_mechanics(
    information: Sequence[Sequence[float]] | np.ndarray,
    prior_precision: Sequence[Sequence[float]] | np.ndarray,
) -> AbsoluteMechanics:
    """Compute replay-only absolute mechanics without any reference claim."""

    info = _psd(_array(information, name="information"), name="information")
    prior = _positive_definite(
        _array(prior_precision, name="prior_precision"), name="prior_precision"
    )
    if info.shape != prior.shape:
        raise InformationV2Error("information and prior_precision dimensions differ")
    whitened = prior_whitened_information(info, prior)
    eigenvalues = np.maximum(np.linalg.eigvalsh(whitened), 0.0)
    return AbsoluteMechanics(
        absolute_log10_contraction=round(
            float(np.sum(np.log1p(eigenvalues)) / (2.0 * math.log(10.0))), 12
        ),
        generalized_eigenvalues=tuple(round(float(value), 12) for value in eigenvalues),
        information_matrix_sha256="sha256:" + _matrix_hash(info),
        prior_precision_matrix_sha256="sha256:" + _matrix_hash(prior),
        parameter_dimension=int(info.shape[0]),
    )


def validate_reference_geometry(
    reference_information: Sequence[Sequence[float]] | np.ndarray,
    prior_precision: Sequence[Sequence[float]] | np.ndarray,
    reference_direction_basis: Sequence[Sequence[float]] | np.ndarray,
) -> ReferenceGeometry:
    """Verify reference dimension, PSD, whitening, basis, and diagonalization semantics."""

    reference = _psd(
        _array(reference_information, name="reference_information"),
        name="reference_information",
    )
    prior = _positive_definite(
        _array(prior_precision, name="prior_precision"), name="prior_precision"
    )
    if reference.shape != prior.shape:
        raise InformationV2Error("reference information and prior dimensions differ")
    reference_whitened = prior_whitened_information(reference, prior)
    reference_vectors = _array(reference_direction_basis, name="reference_direction_basis")
    if reference_vectors.shape != reference.shape:
        raise InformationV2Error(
            "reference_direction_basis and reference information dimensions differ"
        )
    if not np.allclose(
        reference_vectors.T @ reference_vectors,
        np.eye(reference_vectors.shape[0]),
        atol=1e-8,
        rtol=0.0,
    ):
        raise InformationV2Error("reference_direction_basis must be column-orthonormal")
    reference_in_basis = reference_vectors.T @ reference_whitened @ reference_vectors
    off_diagonal = reference_in_basis - np.diag(np.diag(reference_in_basis))
    reference_scale = max(1.0, float(np.max(np.abs(reference_in_basis))))
    if float(np.max(np.abs(off_diagonal))) > 1e-8 * reference_scale:
        raise InformationV2Error(
            "reference_direction_basis must diagonalize prior-whitened reference information"
        )
    return ReferenceGeometry(
        reference_values=tuple(
            float(value) for value in np.maximum(np.diag(reference_in_basis), 0.0)
        ),
        reference_direction_basis=tuple(
            tuple(float(value) for value in row) for row in reference_vectors
        ),
        reference_matrix_sha256="sha256:" + _matrix_hash(reference),
        reference_direction_basis_sha256="sha256:" + _matrix_hash(reference_vectors),
        parameter_dimension=int(reference.shape[0]),
    )


def reconstruction_metrics(
    information: Sequence[Sequence[float]] | np.ndarray,
    prior_precision: Sequence[Sequence[float]] | np.ndarray,
    reference_information: Sequence[Sequence[float]] | np.ndarray,
    reference_direction_basis: Sequence[Sequence[float]] | np.ndarray,
    *,
    coverage_thresholds: Sequence[float] = (0.1, 0.5, 1.0),
) -> ReconstructionMetrics:
    info = _psd(_array(information, name="information"), name="information")
    prior = _positive_definite(
        _array(prior_precision, name="prior_precision"), name="prior_precision"
    )
    reference = _psd(
        _array(reference_information, name="reference_information"),
        name="reference_information",
    )
    if info.shape != reference.shape or info.shape != prior.shape:
        raise InformationV2Error("information, reference, and prior dimensions differ")
    whitened = prior_whitened_information(info, prior)
    geometry = validate_reference_geometry(
        reference, prior, reference_direction_basis
    )
    reference_vectors = np.asarray(geometry.reference_direction_basis, dtype=float)
    reference_values = np.asarray(geometry.reference_values, dtype=float)
    # Direction completion is evaluated from posterior marginal precision in
    # the explicit, hash-bound reference basis. A large rotated rank-one matrix
    # can place a large diagonal projection in every coordinate while resolving
    # only one linear combination; diagonal allocation would therefore be
    # gameable. Posterior variance closes that exploit:
    #   Sigma = (I + G)^-1
    #   ell_eff,j = 1 / (b_j^T Sigma b_j) - 1.
    posterior_covariance = np.linalg.solve(
        np.eye(whitened.shape[0], dtype=float) + whitened,
        np.eye(whitened.shape[0], dtype=float),
    )
    posterior_covariance = 0.5 * (posterior_covariance + posterior_covariance.T)
    direction_variances = np.diag(
        reference_vectors.T @ posterior_covariance @ reference_vectors
    )
    if np.any(direction_variances <= 0.0):
        raise InformationV2Error("posterior directional variances must be positive")
    trial_direction_values = np.maximum(1.0 / direction_variances - 1.0, 0.0)
    reference_logs = np.log1p(reference_values)
    trial_logs = np.log1p(trial_direction_values)
    denominator = float(np.sum(reference_logs))
    if denominator <= 0:
        raise InformationV2Error("reference information must contain a positive direction")
    completion = 100.0 * float(np.sum(np.minimum(trial_logs, reference_logs))) / denominator
    overflow = float(np.sum(trial_logs)) / denominator
    curve = {}
    for threshold in coverage_thresholds:
        value = float(threshold)
        if not math.isfinite(value) or value < 0:
            raise InformationV2Error("coverage thresholds must be finite and nonnegative")
        # A reference scored against its own independently whitened matrix must
        # reach Q(1)=1.  Use a scale-aware numerical tolerance only at the
        # coverage comparison boundary; it cannot create material information.
        comparison_scale = max(1.0, float(np.max(reference_logs)))
        supported = trial_logs + 1e-12 * comparison_scale >= value * reference_logs
        curve[f"q_{value:g}"] = float(np.sum(reference_logs[supported])) / denominator
    eigenvalues = np.maximum(np.linalg.eigvalsh(whitened), 0.0)
    return ReconstructionMetrics(
        absolute_log10_contraction=round(
            float(np.sum(np.log1p(eigenvalues)) / (2.0 * math.log(10.0))), 12
        ),
        level1_completion_percent=round(min(100.0, max(0.0, completion)), 12),
        level1_overflow=round(max(0.0, overflow), 12),
        coverage_curve={key: round(value, 12) for key, value in curve.items()},
        generalized_eigenvalues=tuple(round(float(value), 12) for value in eigenvalues),
        reference_direction_information=tuple(
            round(float(value), 12) for value in trial_direction_values
        ),
        information_matrix_sha256=_matrix_hash(info),
        reference_matrix_sha256=geometry.reference_matrix_sha256.removeprefix("sha256:"),
        reference_direction_basis_sha256=geometry.reference_direction_basis_sha256.removeprefix(
            "sha256:"
        ),
    )
