# Conditional reference recipe v0.4

This document specifies every variance used by `anibench plan`. These are
separate, hypothetical task models. They are not fitted biological constants or
one universal variance-components model. It is a documentation clarification;
the byte-pinned v0.4 calculations are unchanged.

## Symbols and scope

For coordinate j, let a_j be the registered native standard-error anchor. Let
N be the number of independent retained people, d the stipulated technical-depth
factor, k the technical repeats per endpoint, and rho their exchangeable
correlation. The recipe permits 0 <= rho <= 1 and defines
`k_eff = k / (1 + (k - 1) rho)`. Depth is a specified reduction of measurement
variance, not an assay, feature, cell, read or dollar count. Technical repeats are
within an endpoint; they do not extend the biological observation window.

Let m be the whole-covariance scenario multiplier (1 or 2). Let g be the
resolution factor: tolerance_factor for AB1 and tolerance_factor/2 for AB2.
Every variance ceiling is `(g s_j)^2`, where s_j is the question-specific SE
reference below. A smaller g is a harder precision challenge. The noise
multiplier scales the full covariance, including the declared population floor.

## Complete variance table

Each expression below is a diagonal marginal variance in squared native units.
The paired-change task contains both rows, with distinct estimands.

| Task / estimand | SE reference s_j | Native likelihood variance |
|---|---|---|
| Current state of a fixed person | a_j | m a_j^2 (4/d) |
| Population mean | a_j/4 | m (a_j/4)^2 (80/N) |
| Fixed focal person's paired change | a_j | m a_j^2 V, with V = 160/(d k_eff) |
| Mean paired change in the other people | a_j/4 | m a_j^2 (40 + V)/(N - 1) |
| Balanced two-arm population contrast | a_j | m a_j^2 4(40 + 80/d)/N |
| Four-cell difference of treatment contrasts | a_j | m a_j^2 16(40 + 80/d)/N |
| Paired platform/site mean offset | a_j/2 | m (a_j/2)^2 (8/N) |

The current-state 4/d, population-mean 80/N and bridge 8/N expressions are
independently selected conventions. Population and bridge precision do not
improve with d in this recipe. They must not be derived from the B=40, R=80
fields appearing in every task's historical model metadata. Those fields apply
to the contrast and longitudinal constructions only. Their broad placement is a
legacy metadata limitation, not a common physical law. Scientific consumers
must use this table and the pinned request construction, not infer an absent
shared generative model from those fields.

Within a non-longitudinal bundle of p coordinates, `C = 0.75 I_p + 0.25 11^T`.
If D is the diagonal matrix of that task's native SE references and r is the
dimensionless ratio in the table, `R = m r D C D` and `H = I`. Thus
`J = R^-1`. The eigenvalues of C are 0.75 and 0.75+0.25p, so C is positive
definite. These fixed within-panel correlations are assumptions, not empirical
cross-omic correlations. Attainment checks named coordinate functionals, not
every rotated direction or a simultaneous confidence region.

For the longitudinal bundle, use D = diag(a_1,...,a_p,a_1,...,a_p) and
`R = D [m diag(V, (40+V)/(N-1)) tensor C] D`. The first block is one fixed
person's change; the second estimates the population mean from N-1 other
independent people. There is no prior or observational covariance linking the
focal parameter to that population mean. This deliberate separation avoids
counting a shared focal observation twice. The endpoints have zero declared
measurement-error correlation; V includes measurement noise at both endpoints.

## Derived precision boundaries

With required support present, divide each variance by its corresponding
reference variance. All coordinates in one row have the same standardized
ratio. At scenario m, the necessary and sufficient named-functional precision
conditions of this recipe are:

| Task | Boundary |
|---|---|
| Current state | d >= 4m/g^2 |
| Population mean | N >= 80m/g^2 |
| Focal paired change | d k_eff >= 160m/g^2 |
| Other-person mean change | N >= 1 + 16m(40 + 160/(d k_eff))/g^2 |
| Controlled contrast | N >= 4m(40 + 80/d)/g^2 |
| Heterogeneity contrast | N >= 16m(40 + 80/d)/g^2 |
| Measurement bridge | N >= 8m/g^2 |

Round upward to feasible integer retained allocations. Controlled designs require
even N; the four-cell heterogeneity task additionally requires N divisible by
four. N must be at least two because the longitudinal model separates a focal
person from others. Both declared noise scenarios must pass; for these monotone
expressions m=2 is the limiting scenario. These are algebraic boundaries of the
declared model, not recruitment recommendations.

For example, k=4 and rho=0.2 give k_eff=2.5. For AB1 at d=128, the other-person
mean-change constraint is N>=1297, hence N=1298 after balanced two-arm allocation.
For AB2 at d=512, g=0.5 gives N>=5137, hence N=5140 after the required four-cell
allocation. In both cases
the other required precision conditions also hold. Neither example establishes
that those biological measurements can actually be acquired with that variance.

## Support and level definitions

AB1 includes current-state, population-mean and paired-change bundles in five
domains, plus controlled contrasts in molecular, physiological and digital
domains: 18 bundles. AB2 retains those estimands, halves their SE limits, and
adds cognitive and neural controlled contrasts, molecular and physiological
heterogeneity, and molecular and neural bridges: 24 bundles. These are selected
tasks, not all biology. Neural observations here are named ERP measurements;
neural controlled contrasts concern assigned stimulus protocols, not inferred
effects of neurostimulation.

The default domain-budget convention allocates equal total mass to five domains
and equal mass to the bundles within each domain. Question-budget and equal-
bundle policies are separate sensitivity profiles. Full attainment requires all
registered tasks and support under the same required scenarios, regardless of
the weights or a rounded displayed percentage.

An explicitly absent required domain fails its tasks. An unresolved domain
leaves them unknown unless another known condition already fails. Controlled,
paired and bridge flags declare required design support; they do not verify
randomization, adherence, acquisition, causal assumptions or measurement
equivalence. Actual studies require qualified source mappings. There is no
automatic inference from modality names or from treatment benefit.

## Reproduction and identity

`anibench.reference_planner.evaluate_plan` calls the installed canonical
`evaluate_benchmark` on the same profile for both designs. The adapter verifies
the reference script and anchor catalogue before evaluation. v0.4 script SHA-256:
`0cec8d966af3ab41edef2b900d3f547e812bd86247f1092bd45a9a3441db313f`.
The receipt includes the full task model, input design, likelihood geometry,
scenario outcomes, precision diagnostics and result identity. Editing a model,
task frame, threshold or weight creates a different reference identity.
