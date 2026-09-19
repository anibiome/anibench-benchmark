# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Independent joint-posterior requirements, not biological calibration tests."""

import json
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from anibench.information_v2 import (
    InformationV2Error,
    posterior_reference_diagnostic,
    reconstruction_metrics,
)
from anibench.v2 import score_information_run

ROOT = Path(__file__).resolve().parents[1]


def test_marginal_completion_does_not_mask_joint_failure():
    posterior = np.array([[0.5, 0.49], [0.49, 0.5]])
    information = np.linalg.inv(posterior) - np.eye(2)
    result = reconstruction_metrics(information, np.eye(2), np.eye(2), np.eye(2))
    assert result.level1_completion_percent == 100
    assert result.coverage_curve["q_1"] == 1
    assert result.basis_marginal_semantics == "reference_basis_marginal_variance_attainment_only"
    diagnostic = result.conditional_joint_diagnostic
    assert diagnostic["worst_direction_posterior_variance_ratio"] == pytest.approx(1.98)
    assert diagnostic["all_direction_reference_attainment"] is False
    assert diagnostic["public_saturation_claim_allowed"] is False


def test_self_reference_and_more_information():
    prior = np.array([[2.0, 0.4], [0.4, 3.0]])
    reference = np.array([[4.0, -0.3], [-0.3, 1.0]])
    same = posterior_reference_diagnostic(reference, prior, reference)
    assert same["worst_direction_posterior_variance_ratio"] == pytest.approx(1)
    assert same["all_direction_reference_attainment"] is True
    improved = posterior_reference_diagnostic(reference + np.eye(2), prior, reference)
    assert improved["worst_direction_posterior_variance_ratio"] < 1
    assert improved["all_direction_reference_attainment"] is True
    zero = posterior_reference_diagnostic(np.zeros((2, 2)), prior, reference)
    assert zero["worst_direction_posterior_variance_ratio"] > 1
    assert zero["all_direction_reference_attainment"] is False


def test_invertible_coordinate_change_with_nonidentity_prior():
    prior = np.array([[2.0, 0.6], [0.6, 4.0]])
    trial = np.array([[1.0, 0.7], [0.7, 2.0]])
    reference = np.array([[3.0, -0.2], [-0.2, 1.0]])
    # theta = T eta transforms every precision by T.T @ precision @ T.
    transform = np.array([[3.0, 0.4], [-0.7, 0.2]])
    before = posterior_reference_diagnostic(trial, prior, reference)
    after = posterior_reference_diagnostic(
        transform.T @ trial @ transform,
        transform.T @ prior @ transform,
        transform.T @ reference @ transform,
    )
    assert after["worst_direction_posterior_variance_ratio"] == pytest.approx(
        before["worst_direction_posterior_variance_ratio"], rel=1e-10
    )
    assert (
        after["all_direction_reference_attainment"] == before["all_direction_reference_attainment"]
    )


def test_psd_increment_cannot_worsen_worst_direction():
    prior = np.diag([2.0, 5.0])
    reference = np.array([[3.0, 1.0], [1.0, 4.0]])
    trial = np.array([[1.0, 0.3], [0.3, 0.5]])
    v = np.array([1.2, -0.8])
    values = [
        posterior_reference_diagnostic(trial + t * np.outer(v, v), prior, reference)[
            "worst_direction_posterior_variance_ratio"
        ]
        for t in (0, 0.1, 1, 100)
    ]
    assert all(b <= a + 1e-10 for a, b in pairwise(values))


@pytest.mark.parametrize(
    "reference",
    [
        np.zeros((2, 2)),
        np.diag([1, -1]),
        np.array([[1, 0.1], [0, 1]]),
        np.diag([1, float("nan")]),
        np.eye(3),
    ],
)
def test_invalid_reference_rejected(reference):
    with pytest.raises(InformationV2Error):
        posterior_reference_diagnostic(np.eye(2), np.eye(2), reference)


def test_partial_reference_valid_but_zero_prior_invalid():
    result = posterior_reference_diagnostic(np.eye(2), np.eye(2), np.diag([1, 0]))
    assert result["all_direction_reference_attainment"] is True
    with pytest.raises(InformationV2Error):
        posterior_reference_diagnostic(np.eye(2), np.zeros((2, 2)), np.eye(2))


def test_versioned_schema_and_fixture_gates():
    fixture = json.loads(
        (ROOT / "spec/v2/mechanics-fixtures/illustrative-reference-2d.json").read_text()
    )
    packet = score_information_run(fixture)
    diagnostic = packet["illustrative_reference_metrics"]["conditional_joint_diagnostic"]
    schema = json.loads(
        (ROOT / "schemas/v2/conditional-posterior-reference.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(diagnostic)
    assert packet["promotion_allowed"] is False
    assert packet["claim_permissions"]["public_rank_allowed"] is False
    assert packet["claim_permissions"]["public_completion_claim_allowed"] is False


def test_openapi_nested_diagnostic_matches_standalone_schema():
    text = (ROOT / "openapi/anibench-v2-candidate.yaml").read_text()
    declaration = next(
        line
        for line in text.splitlines()
        if line.strip().startswith("conditional_joint_diagnostic:")
    )
    inline_schema = json.loads(declaration.split(":", 1)[1].strip())
    standalone = json.loads(
        (ROOT / "schemas/v2/conditional-posterior-reference.schema.json").read_text()
    )
    for key in ("type", "required", "properties", "additionalProperties"):
        assert inline_schema[key] == standalone[key]
    actual = posterior_reference_diagnostic(np.eye(2), np.eye(2), np.eye(2))
    Draft202012Validator(inline_schema).validate(actual)
