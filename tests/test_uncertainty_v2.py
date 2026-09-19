"""Quantile labels must preserve the propagated interval's ordering."""

import numpy as np
import pytest

from anibench.uncertainty_v2 import Coordinate, UncertaintyV2Error, propagate


@pytest.mark.parametrize("quantiles", [(0.975, 0.5, 0.025), (0.025, 0.975, 0.5)])
def test_reversed_quantiles_rejected_before_evaluation(quantiles):
    def should_not_run(_):
        pytest.fail("invalid quantiles reached the evaluator")

    with pytest.raises(UncertaintyV2Error, match="ordered"):
        propagate({"x": Coordinate("exact", value=1)}, should_not_run, quantiles=quantiles)


@pytest.mark.parametrize("invalid", [True, np.bool_(False), float("nan"), float("inf"), "0.5"])
def test_quantile_probabilities_require_finite_non_boolean_numbers(invalid):
    with pytest.raises(UncertaintyV2Error, match="finite numeric"):
        propagate({"x": Coordinate("exact", value=1)}, lambda x: x["x"], quantiles=(0, invalid, 1))


def test_default_quantiles_match_independent_seeded_sample_quantiles():
    draws, seed = 101, 314
    samples = np.random.default_rng(seed).uniform(-2, 3, size=draws)
    expected = np.quantile(2 * samples + 1, (0.025, 0.5, 0.975))
    result = propagate(
        {"x": Coordinate("interval", lower=-2, upper=3)},
        lambda x: 2 * x["x"] + 1,
        draws=draws,
        seed=seed,
    )
    assert (result.lower, result.median, result.upper) == pytest.approx(expected, abs=1e-12)
    assert result.lower <= result.median <= result.upper


def test_nonmedian_middle_quantile_is_rejected():
    with pytest.raises(UncertaintyV2Error, match="middle quantile must be 0.5"):
        propagate(
            {"x": Coordinate("exact", value=1)},
            lambda x: x["x"],
            quantiles=(0.1, 0.2, 0.9),
        )


@pytest.mark.parametrize("quantiles", [(0, 0.5, 1), (0.5, 0.5, 0.5)])
def test_endpoint_and_tied_quantiles_remain_valid(quantiles):
    result = propagate(
        {"x": Coordinate("exact", value=7)}, lambda x: x["x"], quantiles=quantiles, draws=3
    )
    assert (result.lower, result.median, result.upper) == (7, 7, 7)
