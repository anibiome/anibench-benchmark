<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Frozen workload percentages

`anibench benchmark` evaluates named tasks and reports **benchmark targets met (%)**
for each declared category. A percentage refers to the frozen workload, not all
of human biology. The command adds an aggregation layer to the existing
likelihood-only finite-suite evaluator; it does not estimate observation
operators, covariance, causal identification or biological targets from an assay
menu. Existing `anibench eval` and `anibench compare` contracts are unchanged.

For a category with positive integer weights, its denominator is the sum of all
weights. Passed weight supplies the lower endpoint; passed plus unresolved
weight supplies the upper endpoint. Failed tasks remain in the denominator.
For example, 12 passed, five failed and three unresolved equal-weight tasks give
60–75%, not a score calculated from the 17 resolved tasks. These are epistemic
outer bounds, not confidence intervals. Outcomes come from a fresh execution of
the finite suite, never caller-edited pass/fail result rows.

Every view partitions the same scored targets into categories. A target cannot
appear twice within a view or silently disappear. A profile can also name
`gate_only_targets`: explicit required targets outside the scored denominator.
Their states remain visible and affect exact level attainment. Level attainment
comes from every suite target and required role under the frozen scenario
quantifier. It is never inferred from rounded percentages. A category can display
100% while an unresolved gate prevents level attainment.

## Precision toward targets

The secondary **precision toward targets** measure retains closeness to a
threshold. For a functional with identified likelihood variance `v` and limit
`tau²`, adequacy is `min(1, tau²/v)`. Within a task, the minimum adequacy over its
required functionals applies; across tasks, the declared category weights apply.
These are explicit conventions. A joint all-direction task must be defined and
evaluated as such; this aggregation does not infer it from marginal functionals.

A variance 1% above its limit fails the threshold task but has 99.01% precision
adequacy. The measures answer different questions. Neither is prediction accuracy
or the probability that a study is good. Known failed support or identification
gives zero adequacy. Unresolved support preserves an interval; a strong prior
cannot substitute for information supplied by the study. Native likelihood
variances, support checks and task definitions remain in the nested receipt.

Every scenario produces its own complete category vector. The envelope takes
the minimum lower and maximum upper endpoints across whole scenarios. Envelope
endpoints across different categories need not be jointly attainable. A finite
scenario set is sensitivity analysis, not a calibrated uncertainty distribution.
The suite's existential level rule requires one *same* scenario to pass every
required task. Separately favorable scenarios cannot be combined into a pass.

## Local execution

The request has contract `anibench.benchmark-request.v1`, a
`score_profile_sha256`, and a complete `suite_request`. The trusted suite registry
maps profile digests to finite-suite profiles. The separate trusted score
registry maps digests to `anibench.score-profile.v1` declarations containing:

- `score_profile_id`, `suite_profile_sha256`, and `weighting_rationale`;
- explicit `gate_only_targets`, possibly empty;
- views with stable IDs and labels, each containing categories with a question,
  a label, and canonical target IDs with positive integer weights.

The exported `SCORE_PROFILE_SCHEMA` in `anibench.benchmark_v1` is the strict schema.
Changing targets, grouping, weights or rationale changes the trusted digest.
Trusting a registry is an explicit local scientific choice, not external review.
Same-frame aliases are rejected by the underlying suite, but biological
equivalence across newly defined task frames requires scientific review.
Splitting one biological requirement into several tasks cannot be justified
solely by giving them different names. Workload version changes must preserve
or explicitly revise parent task mass and document rank sensitivity.

```sh
anibench benchmark request.json --registry profiles.json \
  --scores score-profiles.json --out new-result.json
```

All inputs stay local; no network operation occurs. An existing output file is
preserved and causes an error. The output binds the request, score profile,
suite profile, design source, implementation and underlying task receipts.
Biological calibration and public saturation claims are not established by
running this mechanism. Real-study use additionally requires source-qualified
task mappings and defensible calibration or clearly declared conditional models.

Validation includes a 20-task 60–75% arithmetic example, prior-only acquisition,
unknown support, absent tasks, duplicate and missing mass, scenario incompatibility,
gate-only failure, near-100 rounding, identity invariance and CLI preservation.
These software checks do not establish empirical biological usefulness.
