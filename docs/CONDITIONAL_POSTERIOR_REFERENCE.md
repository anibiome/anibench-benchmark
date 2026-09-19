<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Conditional posterior-reference diagnostics

The additive contract `anibench.conditional-posterior-reference.v1` distinguishes
reference-basis marginal completion from a joint posterior guarantee. Neither
quantity certifies biological saturation, empirical model utility, or a public
rank. Current role-aware assessment and promotion permissions remain unchanged.

The historical `level1_completion_percent` and coverage-curve values are retained
for compatibility. Their explicit semantics are
`reference_basis_marginal_variance_attainment_only`: they compare posterior
marginal uncertainty along the declared reference basis. A large number does not
establish precision for every other linear combination.

For example, with prior precision I and reference information I, the reference
posterior covariance is 0.5 I. A trial posterior covariance
`[[0.5, 0.49], [0.49, 0.5]]` meets both reference-basis marginals. Historical
completion is 100% and q(1) is 1, but variance along `(1,1)/sqrt(2)` is 0.99,
which is **1.98 times** reference variance. This is an explicitly hypothetical
Gaussian model, not a study or a biological calibration result.

`posterior_reference_diagnostic` reports

    r = max over nonzero c of (cᵀ Σtrial c) / (cᵀ Σreference c).

Both posteriors use the same registered parameter space and prior. With
prior-whitened likelihood information G, posterior precision is I+G. If
`L Lᵀ = I+Greference`, the eigenvalues of
`Lᵀ solve(I+Gtrial, L)` are the generalized posterior variance ratios. Thus
`r <= 1` is equivalent to the Loewner inequality
`Σtrial <= Σreference`: no linear functional has worse posterior variance.
The computation uses a linear solve rather than explicit posterior inversion.
It is invariant to invertible parameter transformations when prior, trial, and
reference information are transformed consistently. Adding positive
semidefinite trial information cannot increase r.

The diagnostic's `all_direction_reference_attainment` uses `r <= 1 + 1e-10`.
This fixed tolerance handles floating-point boundary error; it is not a
biological or clinical equivalence margin. The raw ratio is retained, with the
rule and tolerance in the receipt. Inputs require a positive-definite prior,
positive-semidefinite information, compatible dimensions, and a nonzero
reference likelihood direction. A rank-deficient reference remains valid
because the proper prior makes its posterior covariance positive definite.
Zero trial information is valid and generally fails reference attainment.

The nested diagnostic is exposed in the illustrative replay packet only when
its existing exact locally registered fixture gate is satisfied. Caller-selected
references still receive absolute replay mechanics only. The new nested contract
is independently versioned; the historical envelope and marginal quantities
retain their existing names and formula versions. Strict output-schema validators
must accept the two added fields; historical numerical compatibility does not
imply byte-identical receipts. New readers can distinguish
both semantics without rewriting historical results.

## Capacity, collection, and demonstrated learning

Conditional design attainment uses planned observations under explicit model
assumptions. It does not require study outcomes or demonstrated model utility.
Realized-record attainment adds verified retained observations, quality and
linkage. Empirical learning plateau is a separate evaluation requiring held-out
performance, uncertainty and a prespecified equivalence criterion. These lanes
must not be collapsed into a maturity penalty for planned studies.

A task can instead require only a finite preregistered set of linear functionals
with their own precision tolerances. In that case report exactly those results;
do not silently replace a finite-functional contract with an all-directions
claim, or vice versa. Missing required domain observations cannot be filled by
unrelated assay depth. The Gaussian diagnostic alone cannot detect a biologically
misspecified operator, nuisance omission, unjustified prior, or false source.

## Additive information precondition

`assemble_joint_information` adds contributions already established to have
additive conditional information. Its `event_type_id` and `source_object_id` are
not unique acquisition identities. Legitimate independent repeats can share
both labels; rejecting every repeated label would incorrectly discard evidence.
Exact copies must be deduplicated using actual acquisition lineage upstream.
Correlated observations require a joint covariance or valid conditional
information decomposition. This helper cannot infer either fact from labels.
No new guessed-identity deduplication rule is introduced.

## Reproduction and scope

Run `python scripts/audit_synthetic_geometry.py` from an environment containing
AniBench's dependencies. The portable runner produces
`data/synthetic_geometry_audit/actual_geometry_results.json` with source hashes,
225 distinct synthetic matrices, 15 families, analytic expectations, actual
helper/replay results, and separate semantic counterexample counts. All scenario
numbers are invented for testing; none is attributed to a person or real study.
The two-person/$100M scenario makes no claim that money enters the information
formula or that a small proof-of-concept cannot lead a narrow task.

Tests in `tests/test_posterior_reference_diagnostic.py` check the exact 1.98 case,
self-reference, nonidentity-prior coordinate invariance, positive-semidefinite
improvement, zero and invalid inputs, the schema and unchanged fixture gates.
The runner checks the new joint diagnostic against independent analytic answers
for all 15 joint-completion counterexamples. Copied contributions deliberately
expose the low-level additive precondition; these are not claimed upstream
compiler failures. Cost and duration checks establish only the low-level input
boundary. This suite does not constitute a 200-real-study evaluation, a full
protocol-compiler audit, or biological validation.
