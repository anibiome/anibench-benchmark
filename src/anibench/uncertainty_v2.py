from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real

import numpy as np


class UncertaintyV2Error(ValueError):
    pass


@dataclass(frozen=True)
class Coordinate:
    state: str
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    distribution: str | None = None
    parameters: Mapping[str, float] | None = None


@dataclass(frozen=True)
class PropagatedInterval:
    lower: float
    median: float
    upper: float
    draws: int
    seed: int


def sample_coordinate(
    coordinate: Coordinate, *, draws: int, rng: np.random.Generator
) -> np.ndarray:
    """Sample a declared model; an interval explicitly assigns a uniform law.

    Bounds alone do not establish that law. Callers must justify this modeling
    choice before interpreting the propagated quantiles as uncertainty.
    """
    if draws < 1:
        raise UncertaintyV2Error("draws must be positive")
    if coordinate.state == "exact":
        if coordinate.value is None or not math.isfinite(coordinate.value):
            raise UncertaintyV2Error("exact coordinate requires a finite value")
        return np.full(draws, float(coordinate.value))
    if coordinate.state == "interval":
        if coordinate.lower is None or coordinate.upper is None:
            raise UncertaintyV2Error("interval coordinate requires lower and upper")
        if not coordinate.lower <= coordinate.upper:
            raise UncertaintyV2Error("interval coordinate lower exceeds upper")
        return rng.uniform(float(coordinate.lower), float(coordinate.upper), size=draws)
    if coordinate.state == "distribution":
        params = dict(coordinate.parameters or {})
        if coordinate.distribution == "beta":
            alpha = float(params.get("alpha", 0))
            beta = float(params.get("beta", 0))
            if alpha <= 0 or beta <= 0:
                raise UncertaintyV2Error("beta distribution requires positive alpha and beta")
            return rng.beta(alpha, beta, size=draws)
        if coordinate.distribution == "normal":
            mean = float(params.get("mean", math.nan))
            sd = float(params.get("sd", math.nan))
            if not math.isfinite(mean) or not math.isfinite(sd) or sd < 0:
                raise UncertaintyV2Error(
                    "normal distribution requires finite mean and nonnegative sd"
                )
            return rng.normal(mean, sd, size=draws)
        raise UncertaintyV2Error("unsupported distribution")
    if coordinate.state in {"unknown", "absent"}:
        raise UncertaintyV2Error(f"{coordinate.state} coordinate is not numerically scoreable")
    raise UncertaintyV2Error(f"unknown coordinate state {coordinate.state!r}")


def propagate(
    coordinates: Mapping[str, Coordinate],
    evaluator: Callable[[Mapping[str, float]], float],
    *,
    draws: int = 2000,
    seed: int = 1729,
    quantiles: Sequence[float] = (0.025, 0.5, 0.975),
) -> PropagatedInterval:
    """Return Monte Carlo quantiles under independent coordinate models.

    These are neither guaranteed bounds nor automatically confidence intervals.
    Dependence between uncertain inputs requires a separate joint sampler.
    """
    if len(quantiles) != 3 or not all(
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= 1
        for value in quantiles
    ):
        raise UncertaintyV2Error("quantiles must contain three finite numeric probabilities")
    if not quantiles[0] <= quantiles[1] <= quantiles[2]:
        raise UncertaintyV2Error("quantiles must be ordered lower <= median <= upper")
    if quantiles[1] != 0.5:
        raise UncertaintyV2Error("the middle quantile must be 0.5 to report a median")
    rng = np.random.default_rng(seed)
    sampled = {
        key: sample_coordinate(coordinate, draws=draws, rng=rng)
        for key, coordinate in coordinates.items()
    }
    values = np.asarray(
        [
            evaluator({key: float(rows[index]) for key, rows in sampled.items()})
            for index in range(draws)
        ],
        dtype=float,
    )
    if not np.all(np.isfinite(values)):
        raise UncertaintyV2Error("evaluator returned non-finite values")
    lower, median, upper = np.quantile(values, quantiles)
    return PropagatedInterval(
        lower=round(float(lower), 12),
        median=round(float(median), 12),
        upper=round(float(upper), 12),
        draws=draws,
        seed=seed,
    )
