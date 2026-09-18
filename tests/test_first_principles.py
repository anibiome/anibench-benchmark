"""Independent mathematical identities and counterexamples, not golden scores."""

import math

import numpy as np
import pytest

from anibench.information_v2 import (
    EventContribution,
    InformationV2Error,
    absolute_log10_contraction,
    event_information,
    nuisance_adjusted_information,
)


def information(operator, covariance, count=1):
    return event_information(
        EventContribution("synthetic", operator, covariance, count, "synthetic")
    )


def test_units_and_invertible_observer_mixing_do_not_create_information():
    operator = np.array([[1.0, 2.0], [-1.0, 0.5]])
    noise = np.array([[2.0, 0.3], [0.3, 1.0]])
    transform = np.array([[1000.0, 200.0], [0.0, 0.01]])
    expected = information(operator, noise)
    actual = information(transform @ operator, transform @ noise @ transform.T)
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)


def test_parameter_reexpression_preserves_generalized_information():
    info = np.array([[5.0, 1.0], [1.0, 2.0]])
    prior = np.array([[2.0, 0.4], [0.4, 1.0]])
    # theta = T eta: both precision tensors transform by congruence.
    transform = np.array([[10.0, 2.0], [0.0, 0.1]])
    assert absolute_log10_contraction(
        transform.T @ info @ transform, transform.T @ prior @ transform
    ) == pytest.approx(absolute_log10_contraction(info, prior), rel=1e-9)


def test_correlated_replicates_follow_analytic_effective_sample_size():
    for count, rho in [(2, 0.0), (10, 0.5), (100, 0.99)]:
        covariance = (1 - rho) * np.eye(count) + rho * np.ones((count, count))
        observed = information(np.ones((count, 1)), covariance)[0, 0]
        assert observed == pytest.approx(count / (1 + (count - 1) * rho))
    # Almost identical observations contain almost one observation's information.
    assert observed < 1.011


def test_more_independent_people_grow_information_without_a_normalized_ceiling():
    values = [
        absolute_log10_contraction(information([[1.0]], [[1.0]], n), [[1.0]])
        for n in [1, 10, 100, 1_000_000]
    ]
    assert values == sorted(values)
    assert values[-1] == pytest.approx(0.5 * math.log10(1 + 1_000_000))
    assert values[-1] > 1  # Neither 1 nor 100 is a completeness ceiling.


def test_noise_and_nuisance_cannot_increase_target_information():
    clean = information([[1.0, 0.0], [1.0, 1.0]], np.eye(2))
    noisy = information([[1.0, 0.0], [1.0, 1.0]], 10 * np.eye(2))
    assert np.linalg.eigvalsh(clean - noisy).min() >= -1e-12
    adjusted = nuisance_adjusted_information(
        clean, target_indices=[0], nuisance_indices=[1], nuisance_prior_precision=[[0.1]]
    )
    assert 0 <= adjusted[0, 0] < clean[0, 0]


def test_elapsed_time_is_not_automatically_dynamic_information():
    # y(t) = theta exp(-t), fixed observation noise: moving the only
    # measurement later loses information about the initial amplitude.
    early = information([[1.0]], [[1.0]])
    late = information([[math.exp(-5)]], [[1.0]])
    assert late[0, 0] < early[0, 0]
    # Retaining the early measurement and adding an independent late one helps.
    both = information([[1.0], [math.exp(-5)]], np.eye(2))
    assert both[0, 0] > early[0, 0]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_model_inputs_never_emit_information(bad):
    with pytest.raises(InformationV2Error, match="finite"):
        information([[bad]], [[1.0]])
    with pytest.raises(InformationV2Error, match="finite"):
        information([[1.0]], [[bad]])


def test_empty_models_have_no_meaningful_information_geometry():
    with pytest.raises(InformationV2Error, match="nonempty"):
        information(np.zeros((1, 0)), [[1.0]])
    with pytest.raises(InformationV2Error, match="nonempty"):
        absolute_log10_contraction(np.zeros((0, 0)), np.zeros((0, 0)))
