<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Native summary sampling precision

The candidate `summary-task` adapter turns a qualified sample size and individual
standard deviation into a **conditional population-mean sampling variance**. It
feeds the existing finite-task engine; it does not score participant counts or
add a second information solver.

For one independent sample, `v = s²/n`. For two disjoint independent groups,
`v = s₀²/n₀ + s₁²/n₁`. An explicit positive scenario multiplier may scale the
whole variance. The finite task receives scalar likelihood information `1/v`.
No treatment-effect estimate or response magnitude enters these calculations.
An explicitly reported **unadjusted sample-mean SE** may instead supply its
group mean variance directly as `SE²`. This route requires no invented individual
SD or denominator; N may remain unknown. A group supplies either `sample_sd` or
`unadjusted_mean_se`, never both. `individual_quantity` names the underlying level
or paired-change quantity in either case, and `spread_locator` identifies the
exact source statistic. Adjusted/model-based SEM does not belong in this adapter.

The mean, mean-change, difference of means, and difference of mean changes have
distinct model identities. A change SD must describe **individual paired
changes**, with the number of retained pairs. Two marginal visit SDs cannot
substitute for it. Source SEM, uncertainty in an adjusted estimator, and assay
technical-repeat SD are different quantities and cannot be passed as individual
SD. A paired-change mean SE must itself refer to the unadjusted mean of paired
individual changes, not a difference between marginal visit means. Any conversion
belongs in a separately reviewed source adapter.

This is a plug-in Gaussian approximation. It treats estimated SDs as fixed and
does not integrate variance-estimation uncertainty, bias, informative missingness,
clustering, finite-population corrections, or cross-group covariance. The input
requires explicit assumption states. Unknown or violated assumptions produce
unavailable geometry, never an assumed zero covariance. A violated model is not
evidence that the study has no information; another appropriate model may work.

The estimand is a population mean under the declared sampling scope, not the
measurement error of one person or of a fixed observed cohort. Source populations,
occasions, instrument definitions and native units must be qualified before
comparing studies. Matching units alone does not establish comparability.
The summary's population, occasion/window and full measurement estimand must
exactly match the frozen task's `target_population`, `horizon` and `estimand`.
No fuzzy textual matching or unit-based substitution is performed. This binds
the declaration; a reviewer must still check that the source SD and denominator
actually refer to that declaration.

## Use with the existing evaluator

```python
from anibench.summary_geometry_v1 import compile_summary_task, summary_model_sha256

# The reviewed frozen task binds the appropriate model:
assert task["model_sha256"] == summary_model_sha256("population_mean")
derivation = compile_summary_task(task, summary, evidence)
request = derivation["finite_task_request"]
# Include request under its exact canonical target in a trusted likelihood-only
# finite-suite request, then use evaluate_benchmark for workload percentages.
```

`SUMMARY_SCHEMA` in the module is the strict JSON contract. The command accepts a
JSON object with exactly `task`, `summary`, and `evidence`:

```sh
anibench summary-task input.json --out new-derivation.json
```

The command preserves existing output files and refuses aliases of its input.
The output retains source hashes and locators, individual variance terms,
assumptions, native variance, compiler identity, and the complete finite-task
request. Missing SD or count remains unknown. Independent counts must be actual
integers, not weighted or effective sample sizes silently substituted for people.

The compiler validates declarations but does not fetch or authenticate source
documents. It does not infer acquisition verification, randomization, causal
identification or population representativeness from a table. Those evidence
conditions remain separately bound in the existing task contract. Planned
designs can use declared assumptions; lacking realized outcomes does not discount
their conditional capacity.

This candidate is one source-to-evaluator route. It does not ratify AB1/AB2,
validate a full biological workload, or establish a universal study ranking.
