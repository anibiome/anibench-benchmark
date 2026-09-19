<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Finite tasks, sample requirements, and saturation

This is a mathematical proposal with illustrative numerical assumptions, not an
approved AniBench target or a clinical study-design recommendation. There is no
validated universal participant count, duration, arm count, or modality list that
constitutes complete human biology. Software versions and task levels are
separate: changing AniBench's implementation does not establish a biological
level's adequacy.

The [candidate task scopes](CANDIDATE_LEVELS.md) make this proposal concrete for
metabolic, immune, functional, daily-rhythm, neural and population questions.
They include a machine-readable discussion specification and an actual-evaluator
depth-versus-population example. Native biological precision limits remain
uncalibrated; these candidate scopes do not replace the current evaluator.

## Three independently reported lanes

| Lane | What can be concluded | Required evidence |
|---|---|---|
| Planned conditional capacity | A proposed acquisition/assignment design meets a stated target under a registered model | Target, observation operators, prior/noise/dependence assumptions, schedule, allocation and precision calculation |
| Realized conditional capacity | Retained records meet that target under the same stated modeling assumptions | Verified collection, QC, linkage, missingness, actual support and updated geometry |
| Empirical learning plateau | A specified learning procedure gains less than a registered amount over a specified design expansion range | Held-out performance, uncertainty/coverage, equivalence analysis and appropriate person/time/context splits |

Planned capacity does not require later study results or demonstrated model
utility. Realized capacity does not require a successful downstream algorithm.
A failed learner is not proof of uninformative data. Conversely conditional
precision is not proof that an assumed biological model is correct. A plateau
for one algorithm can reflect algorithm limitations; it is not universal
saturation. Nonsignificant improvement is not evidence of equivalence.

## Proposed finite-task contract

Freeze a task identifier/version, target population, estimand, units, biological
resolution, input availability, prediction/response horizons, intervention space,
required domains, precision/error tolerances, missing-data model and comparison
rule before examining winners. Bind operators, covariance and priors to declared
sources or explicitly illustrative assumptions. Later levels may add specified
compartments, timescales, modifiers or contexts while preserving earlier results.
No finite level is a percentage of all biology.

For a finite set of registered linear functionals c_j, a Gaussian posterior
precision requirement can be expressed as

    c_j^T Sigma_post c_j <= (h_j / z_j)^2  for every required j.

Here h_j is the registered interval half-width in the estimand's units, and z_j
reflects the declared marginal or simultaneous coverage rule. Bayesian credible
interval precision is conditional on the prior/model; frequentist coverage or
empirical calibration requires separate justification. For a requirement on all
linear functionals, use the worst generalized posterior variance ratio described
in [the conditional diagnostic](CONDITIONAL_POSTERIOR_REFERENCE.md).

Attainment is a conjunction over required tasks and domains. Verified absence
fails a required acquisition/identifiability gate; unavailable evidence leaves it
unknown. Molecular depth cannot replace a required neural response observation.
A narrow task may legitimately require fewer domains than a broad task; it must
not drop difficult requirements after results are known. Functional, digital,
molecular and neural domains are acquisition/target categories, not the six ANI
mesoscopic axes or the six benchmark capacity families.

## Deriving enrollment from a precision target

Consider K equally allocated arms and K-1 active-versus-control mean contrasts.
Assume independent people, homoscedastic normal measurements with known single-
reading variance sigma^2, m exchangeable repeated endpoint readings per person,
within-person correlation rho, and noninformative equal attrition a. The variance
of a person's averaged endpoint is

    v = sigma^2 [rho + (1-rho)/m].

If n is the retained total across arms, each arm has n/K people. Therefore each
active-versus-control contrast has SE^2 = 2 K v / n. For familywise two-sided
error alpha using Bonferroni, let z = Phi^-1(1-alpha/[2(K-1)]). To obtain interval
half-width at most h, require

    n_precision >= 2 K v z^2 / h^2.

For a prespecified nonzero effect delta, the conventional normal approximation
to marginal power 1-beta for each contrast gives

    n_power >= 2 K v (z + Phi^-1(1-beta))^2 / delta^2.

This is per-contrast power, not the probability of detecting every effect
simultaneously. For both goals use the larger retained requirement, divide by
1-a and round enrollment to a multiple of K. This attrition adjustment targets
expected retention; it is not assurance that realized arm sizes will suffice.
Unknown variance, finite-sample inference, differential dropout, clustering,
survival endpoints or adaptive assignment require different calculations.

For an illustrative sigma=1, m=4, a=0.20, delta=0.30, h=0.15, alpha=0.05 and
90% approximate per-contrast power:

| Arms K | Repeat correlation rho | Required enrollment, rounded to equal arms |
|---:|---:|---:|
| 2 | 0 | 214 |
| 2 | 0.5 | 534 |
| 2 | 0.9 | 790 |
| 3 | 0 | 420 |
| 3 | 0.5 | 1,047 |
| 3 | 0.9 | 1,551 |
| 5 | 0 | 870 |
| 5 | 0.5 | 2,170 |
| 5 | 0.9 | 3,210 |

These are arithmetic consequences of invented assumptions, not validated
AniBench enrollment requirements. Precision is the larger requirement in these
examples. Reproduce every row with `python scripts/illustrate_sample_requirements.py`.
Increasing K changes the required contrast set as well as allocation and
multiplicity; the rows are not rankings of overall study quality.

## Why counts cannot substitute for directions or independent people

For m exchangeable equal-variance readings of one person's mean,
`m_eff = m/[1+(m-1)rho]`. At positive rho, this approaches 1/rho as m grows.
More days can improve temporal resolution, but treating every day as a new person
would target the wrong uncertainty. This expression applies to the specified
averaged endpoint, not automatically to slopes, kinetics or sequential causal
effects. Duration must cover the process of interest and sampling must resolve
it; unobserved calendar time provides no dynamics by itself.

For independent identical linear-Gaussian observations, F_n=nF_1. If F_1 has a
null direction, increasing n preserves it. Information on observed directions
can grow without bound while missing required directions remain unobserved.
Similarly, extra labels for identical interventions do not increase contrast
rank. Factorial main-effect support does not imply powered interactions or
supported adaptive-treatment histories.

Single-cell data contain nested sampling units. More cells can resolve rare
cell types and within-donor states, but do not create independent donors for a
population contrast. Tissue, cell-type abundance, per-donor cells, depth, batch
and between-donor variance all affect the relevant task. The primary
[Squair et al. study](https://www.nature.com/articles/s41467-021-25960-2)
shows the consequences of treating pseudo-replicates as biological replication;
[scPower](https://www.nature.com/articles/s41467-021-26779-7) provides a
multi-sample single-cell design framework. Neither establishes a universal
cell-count saturation threshold.

## Neural measurements, intervention roles, and population scope

EEG and fMRI are observations when used to measure neural activity; their
observation operators, temporal filtering, spatial support, reliability and
linkage differ. A cognitive score or digital proxy is not automatically a
substitute for either. [A simultaneous EEG-fMRI primary dataset](https://www.nature.com/articles/s41597-023-02458-8)
illustrates linked acquisitions, without validating every proposed combined
neural target.

Neurostimulation is a perturbation when assigned to alter neural activity.
A causal contrast requires assignment, stimulation parameters, comparator,
response windows, dependence assumptions and observed responses. Diagnostic-only
EEG/fMRI acquisition cannot supply randomized neurostimulation evidence; a
randomized stimulation study does not automatically observe every neural state.
The benchmark should register these roles, not award a device-name bonus.

[Marek et al.](https://www.nature.com/articles/s41586-022-04492-9) found that
small interindividual brain-behavior associations could require thousands of
people for reproducibility; the paper explicitly distinguishes intervention and
within-person approaches. [Longer scans boost prediction and cut costs in
brain-wide association studies](https://www.nature.com/articles/s41586-025-09250-1)
shows why acquisition duration and population size must be considered jointly
for that task class. Neither result supplies a minimum N for all neural studies.
Repeated randomized decisions require their own estimands and dependence models,
as derived in [Liao et al.](https://www.ambujtewari.com/research/liao16sample.pdf).

A two-person study with exceptionally deep measurements can legitimately lead a
specified within-person task while lacking support for broad population
heterogeneity. A huge shallow cohort can reverse those strengths. Expense is not
an information term. If cost matters, show task utility versus cost as a separate
Pareto comparison with declared utility and constraints, preserving valid narrow
proof-of-concept results and unresolved broader claims.
