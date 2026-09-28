# AniBench: a task-based reference for the information capacity of human studies

**Bruno Balen · ANI Biome PBC**

**Research protocol and reproducible reference candidate · 28 September 2026.** This manuscript specifies the implemented method and its current evidence. The reference is not a ratified biological standard, and the empirical results do not establish universal reconstruction guarantees.

## Abstract

Human studies differ in whom they observe, what they measure, when they measure it, and which interventions they can distinguish. Participant counts, modality lists and treatment effects each describe part of this structure, but none alone provides a reproducible comparison of what a study can resolve. We introduce a task-based framework that evaluates planned designs and collected records against versioned, explicitly defined biological estimands. Each task specifies its population, measurement scale, time window, required support and precision criterion. Category percentages report attainment of a fixed reference workload; unresolved evidence remains in the denominator. Likelihood-only precision is separated from prior certainty, causal identification, observed treatment benefit and downstream prediction. A conditional reference implementation spans selected molecular, functional, digital, cognitive and neural measurements, with nested challenge levels and an executable design planner. Adversarial review exposed and corrected a small-sample variance-floor error and an inconsistent joint estimand model. Analytic reference boundaries were checked with 117 canonical evaluator runs and independently recomputed. Source-qualified aggregate examples demonstrate native mean precision, while empirical pilots retain negative and mixed findings: a fitted Gaussian inverse estimator did not outperform simple prediction baselines, and temporal placement mattered beyond recording duration, with incomplete calibration of the working approximation. AniBench is intended to make study assumptions, strengths and omissions inspectable. Current reference choices are conventions under review, not a percentage of human biology understood or evidence of a universally optimal study.

## 1. Motivation

A large cohort can estimate a narrow population quantity precisely while offering little evidence about within-person dynamics. A small, intensively measured study can characterize specific individuals without establishing population variation or treatment-response heterogeneity. More data can be complementary, redundant, systematically biased, or unavailable at the same times and in the same people. A useful benchmark must retain these distinctions.

The intended object of evaluation is the human study or planned study design. A null intervention can be informative. A large apparent benefit can coexist with weak identification. Neither the sign nor magnitude of a treatment response therefore supplies an intrinsic collection-capacity score. Demonstrated prediction and treatment outcomes can be reported as separate analyses, each with its own evidence contract.

Established evaluation projects provide useful precedents for making task definitions and evaluation context visible. ARC Prize separates benchmark versions and reports evaluation status; Harvey's BigLaw Bench relates evaluation to recognizable professional tasks; HELM studies multiple dimensions of model performance. We adopt the need for explicit workloads and inspectable conditions, without importing their task domains or treating their success measures as biological information metrics. [ARC Prize leaderboard](https://arcprize.org/leaderboard), [Harvey BigLaw Bench](https://www.harvey.ai/blog/introducing-biglaw-bench), [HELM](https://arxiv.org/abs/2211.09110).

AniBench's motivating horizon is data useful for computational models of human biology. That horizon cannot itself define a measurable denominator. The operational contribution is a finite, versioned set of questions that a specified collection process can or cannot resolve under declared assumptions.

Recent biological evaluation work is directly relevant. PhenoBench v2 uses the Human Phenotype Project to define cohort-based predictive tasks with explicit targets, populations, timing, permitted inputs and evaluation contracts. Its source description includes molecular, imaging and wearable measurements across multiple timescales. AniBench therefore cannot assume that this comparator lacks digital or longitudinal observations. PhenoBench evaluates predictive models and information sources within a cohort; AniBench's proposed study/design-capacity reference requires its own validation. This distinction is a scope statement, not a claim of priority or superiority. [PhenoBench v2, September 2026](https://arxiv.org/abs/2609.06080v2).

## 2. Study, task and evidence contracts

A study representation distinguishes people, visits, physical acquisitions, derived features, interventions, controls, timing, linkage, quality and provenance. An assay file is not an independent person. Multiple derived scores from the same acquisition are not automatically independent measurements. Separate modality subsets do not establish joint within-person information.

A planned-design record declares a future acquisition and assignment process. Its result is conditional on those declarations and the reference model. A collected-record input adds verification of what was actually acquired. Prospective status does not itself reduce capacity. Missing collection evidence in a realized-record claim remains unresolved; it is not silently supplied by the planned protocol.

Each task defines:

1. A target quantity, parameterization and native unit.
2. An estimand, population and time window.
3. An admissible observation model or source-summary route.
4. Required observational or assignment support.
5. A precision criterion and its authority.
6. Version and source/model identities.

Instrument-specific observables remain distinct from latent constructs. An observed questionnaire sum is not a calibrated measure of all mental health. Scored sleep duration is not latent sleep truth. A microbial relative abundance is not an absolute cell count, a pathway flux or a metabolite concentration. A neural acquisition does not establish a neural intervention effect.

Scientific-frame compatibility is checked before comparison. A unit conversion must transform the quantities and variances consistently. Population means from different source cohorts may be compared as the precision of each cohort's own named mean when the comparison explicitly says so; they are not evidence that the populations or assays are interchangeable.

## 3. Percentage semantics

Let category `g` contain a frozen set of canonical task bundles `T_g` with strictly positive weights `w_t`. If `a_t` is one for a supported task meeting its precision criterion and zero for a confirmed failure, the resolved category percentage is

`S_g = 100 × Σ(w_t a_t) / Σ(w_t)`.

The denominator is the declared workload, not the studies currently displayed. It cannot shrink when a measurement is missing or a difficult task is unresolved. If `P`, `F` and `U` are confirmed passed, failed and unresolved tasks, the epistemic interval is

`[100 × Σ_P w_t / Σ_T w_t, 100 × (Σ_P w_t + Σ_U w_t) / Σ_T w_t]`.

This interval is not a frequentist confidence interval. Its upper endpoint need not be jointly attainable when different unresolved tasks require incompatible assumptions. The evaluator preserves coherent shared scenarios and identifies outer bounds separately. Changing an ethics or publication flag does not alter this numerical result.

A secondary precision-progress diagnostic uses `min(1, τ_t²/v_t)` for an identified scalar functional variance `v_t` and registered target variance `τ_t²`. Multivariate bundles retain their explicit conjunction and limiting-functional rule; their implementation details cannot introduce extra task votes. Missing required support prevents attainment even when the numerical variance is small. Known false requirements dominate unknown ones in conjunction.

Threshold attainment was selected as the primary candidate because its numerator and denominator are directly explainable. Continuous adequacy shows improvements before a threshold is crossed. Reference-relative information and decision utility remain useful for declared purposes, but neither is silently presented as a universal quality ranking. Task weights and resolutions are normative choices, with sensitivity results retained. They are not discovered constants of human biology.

Full level attainment is computed from exact required tasks and support, not from rounded percentages. A displayed 100% after rounding cannot confer a pass. A strong category cannot compensate for a missing mandatory domain. An optional purpose-specific workload average cannot replace the category vector.

## 4. Conditional information and estimability

For the stated linear Gaussian model `y = Hθ + ε`, with positive-definite observation covariance `R`, the likelihood information is `J = HᵀR⁻¹H`. For an estimable functional `cᵀθ`, the corresponding likelihood variance is evaluated on the identified subspace. Prior precision can be used as a coordinate-whitening metric for numerical analysis; prior information does not count as information acquired by the study.

The model requires an interpretable operator `H` and a qualified covariance `R`. An assay menu cannot provide either by itself. Shared batch effects, biological dependence, repeated measurements and cross-platform offsets must be modeled where relevant. A tiny numerical ridge changes the assumed experiment and cannot silently create independent evidence. Ambiguous numerical rank yields an unresolved result.

Named marginal variances and all-direction precision are different claims. The present finite-functionals workload evaluates its named targets. It does not claim a simultaneous 95% confidence region or bound every unregistered linear combination. Full rank also does not establish randomized assignment, absence of confounding or transportability.

Complementarity needs no universal exponential reward. For example, observations of `θ₁+θ₂` and `θ₁−θ₂` together identify coordinates that either alone cannot. Copying the first observation into another file does not create that complementarity. Real biological operators require source or empirical justification before this example can become a biological claim.

## 5. Native aggregate routes

Where a source reports independent-person sample SD `s` and the applicable usable count `n`, the plug-in population-mean variance is `s²/n`. An explicitly unadjusted mean SEM may be used directly as `SEM²`; no individual SD is invented from an ambiguous adjusted estimate. Two disjoint independent groups produce a contrast variance equal to the sum of their mean variances. A paired change requires the SD of individual changes, or equivalent covariance evidence, rather than two marginal SDs treated as independent.

These routes quantify sampling precision for a named mean or contrast. They do not estimate an individual's assay error, certify causal identification, or cure selection bias. Registry enrollment is not automatically the usable denominator for every outcome. Rounded source statistics, conditional header denominators and disagreement between publication and registry are retained in source records.

Adjusted model contrasts require a separate contract preserving the source model and its uncertainty assumptions. They must not enter an unadjusted-SEM adapter merely because both contain the letters “SE.” Family-related and clustered cohorts require appropriate dependence treatment or a documented independent subset.

## 6. Conditional reference levels and design boundaries

### 6.1 Workload and evidence scope

The current v0.4 research reference contains 23 named native anchors grouped into 18 AB1 and 24 AB2 task bundles across five domains. It is a deliberately limited reference recipe, not coverage of all omics, tissues, mechanisms or human experience. The task registry states the exact observables and windows. AB2 inherits the AB1 scientific frames, tightens SE requirements, and adds defined contrast, heterogeneity or measurement-bridge tasks. Changes in meaning require a separately identified profile rather than a misleading nested label.

### 6.2 Symbols and full recipe

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

### 6.3 Native variance formulas

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

### 6.4 Derived precision boundaries

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


### 6.5 Reference evaluations

Analytic constraints derive a finite participant/depth frontier conditional on every required source of support, fixed time windows, variance assumptions and balanced retained allocation. The current sweep comprises 720 algebraic settings, with 117 canonical boundary evaluations. An independent reviewer recomputed all rows using exact rational arithmetic, reconstructed 224 nondominated sampled-grid points, and reproduced three saved witnesses.

At four technical repeats, repeat correlation 0.2 and the standard reference resolution under both declared noise scenarios, an illustrative AB1 boundary is 1,298 retained people at depth 128; AB2 has a boundary of 5,140 at depth 512. These numbers follow from the chosen model. They are not recommendations that these counts, assays or budgets suffice for human biological reconstruction. Missing individual precision can remain unattainable at any N; missing population support cannot be repaired by extreme individual depth. Costs, attrition assurance and participant burden require additional qualified inputs.

**Figure 1.** Conditional N-versus-depth boundaries: [conditional frontier](conditional_frontier.svg). The displayed frontier is conditional on a sampled grid and fixed repeat/correlation settings. Different correlation curves can coincide when another requirement is limiting.

## 7. Current source examples and empirical evidence

### 7.1 Native source comparisons

The first integrated source comparison evaluates two named own-population mean tasks using LIFE, CALERIE and ASPREE aggregate sources. It preserves native units, source-specific populations, conditional denominators and the distinction between an unadjusted reported SEM and an individual SD. Six source-group records produce 18 suite executions across three illustrative SE resolutions. These are three studies, not 18 trials, and the two-task comparison is not a whole-study ranking.

The integrated source snapshot includes 54 family-level qualification dispositions, of which 22 have numerical native-precision inputs, comprising 76 aggregate records. Canonical likelihood-only replay includes 183 single-task benchmark evaluations and 30 contrast diagnostics. These are not 183 distinct studies or whole-reference evaluations. Twelve historical posterior-based pass labels became failures when prior information was excluded. Five explicitly conditional own-population comparison groups contain 42 source-record pairs; measurement-equivalence assumptions remain disclosed. Publication, arms and strata of one study do not become independent studies. Missing denominators, dependence and operator qualification remain explicit gaps. Broad multi-category real-study coverage is not complete.

A subsequent source batch adds 20 distinct family dispositions and three numerical native-precision families, bringing the reviewed intake to 74 dispositions and 25 numerical families. Its separate MIPACT/DIRECT PLUS pilot allocates two native population-mean targets to each of five domains. Fixed thresholds were selected after source inspection, frozen before scoring, and tested at half and double the declared standard-error limits. Six coherent scenarios combine reported or doubled variance with reported and half-last-digit rounding bounds. Source-specific populations and conditional table-header counts remain explicit. Unreported cognitive precision and unsupported bilateral hippocampal interpretation remain unknown. These ten targets do not establish complete domain coverage or AB1 attainment. [MIPACT source](https://pmc.ncbi.nlm.nih.gov/articles/PMC7414690/), [DIRECT PLUS source](https://pmc.ncbi.nlm.nih.gov/articles/PMC9071484/).

A cognitive/neural extension adds four new family dispositions and six newly numerical families, giving a deduplicated union of **78 qualification dispositions and 31 families with numeric native precision**. ADNI was already dispositioned but only becomes numerical in this extension. Twelve native records yield 72 variance/rounding diagnostics and 24 canonical suites; repeated scenarios are not additional studies. The extension uses selected-population MMSE means, hemisphere-specific hippocampal volumes and same-paper cortical summaries. Cognitive inclusion cutoffs and ceiling restriction remain part of the sampling frame. SACHA and FreeSurfer measurements retain their distinct operator identities; equal units do not establish harmonization. Cortical means have no invented benchmark threshold, and the source's exact hemisphere weighting remains unresolved. These calculations do not fill unrelated reaction-time, antisaccade or bilateral-volume tasks. The portable example preserves those limitations and source locators.

**Figure 2.** Fixed native-mean pilot tasks met: [native-mean comparison](https://github.com/anibiome/anibench-benchmark/blob/main/paper/task_reference/figures/native_mean_pilot.svg). Each domain contains two equally weighted tasks for each study's own population mean. Solid ranges show variation in confirmed passes across six shared variance/rounding scenarios; dashed extensions show unresolved task mass. All lower endpoints are zero at this resolution, exposing sensitivity to the declared assumptions. Cognitive and brain-structure gaps are not zeros or observed acquisition absence. The thresholds were selected after source inspection, and source operators are only conditionally comparable. This exploratory ten-task calculation is not a whole-study ranking, a full domain assessment, or AB1 attainment.

### 7.2 Reconstruction pilot: negative and mixed findings

A frozen NHANES pilot evaluated two independently measured native targets using three nested input menus, with 4,412 eligible complete-case adults assigned to train, calibration and evaluation partitions while preserving the chosen group structure. Six train-fitted conditional Gaussian inverse models yielded no target-resolution passes and three prespecified calibration flags. Both predicted precision and held-out errors improved in four nested-menu comparisons. Nevertheless, the likelihood-only inverse estimates lost to the training-mean and ridge baselines in all six fits.

This finding does not justify calibrated predictive guarantees from the fitted matrices. The residual covariance in that experiment describes conditional biological variation as well as measurement/model effects; it is not an independently identified technical-noise covariance. The study retains this distinction and the negative baseline comparison. No post-test threshold tuning was used to manufacture a successful result. The result also does not make prediction performance the primary study-capacity score.

### 7.3 Temporal placement beyond recording duration

A separate frozen experiment used public Sleep-EDF sleep-stage annotations to compare temporal sampling placements within fixed eight-hour records. After prespecified exclusions, 108 nights from 68 people remained, with 34/12/22 independent people in train/calibration/evaluation partitions. Repeated nights stayed with their person. Three placement schemes sampled the same 32, 64 or 128 minutes: random scattered epochs, one circular block, or a block within each hour.

For these finite annotation targets, exact design covariance can be computed. All 12 prespecified equal-duration placement contrasts favored scattered or distributed sampling over a contiguous circular block under the implemented Holm-adjusted screen. Calibration was mixed: eight of 18 risk-equivalence screens passed and three target-resolution cells passed. Only the 128-minute scattered design met both illustrative native precision targets. The Gaussian information calculation is a working risk representation, not proof that the annotation process is the true biological likelihood.

**Figure 3.** Training-predicted SE and held-out exact sampling RMSE: [temporal sampling](temporal_sampling.svg). The source is existing scored annotations, not newly acquired EEG or independently established persistent-person sleep traits. Circular wrapping and complete-case selection limit interpretation. [Sleep-EDF source](https://physionet.org/content/sleep-edfx/1.0.0/).

### 7.4 Paired intervention-source eligibility stop

A prespecified telemetry annotation experiment attempted all 22 source people with paired drug/placebo nights. The independently reviewed protocol required a fully scored eight-hour window after each source lights-off clock. Only three pairs passed, below the frozen minimum of ten. Seven files also encountered an EDF+ recording-field parser compatibility limitation. No contrast precision or effect estimate was produced. The window, exclusions and sample floor were not relaxed after inspection. This source attempt does not close intervention validation.

### 7.5 Linked molecular validation: a retained negative result

A frozen HMP2 experiment linked released molecular tables and selected one eligible specimen per person before fitting. There were 454 exact matched collections, 443 after source quality exclusions, and 106 people in fixed 53/21/32 training/calibration/test partitions. The four inputs were lactate, succinate, propionate and butyrate; positive-log transformation and standardization were fitted within training. The two targets were released F. prausnitzii relative abundance and unstratified PWY-5676 relative pathway abundance, not physiological flux or independently assayed latent state. [Primary HMP2 study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6650278/).

| Native target | Training-mean RMSE | Ridge RMSE | Inverse RMSE |
|---|---:|---:|---:|
| F. prausnitzii relative fraction | 0.0899973 | 0.0818297 | 0.334991 |
| PWY-5676 relative pathway abundance | 0.000658683 | 0.000792690 | 0.00351959 |

Both likelihood-inverse estimates performed worse than the simple baselines. Neither raw nor calibration-adjusted risk-to-predicted-variance interval fit inside the frozen equivalence region [0.8, 1.25]. Near-nominal point coverage therefore did not establish calibration. Person-level resampling used 1,000 successful bootstrap fits per target, retaining the fixed partitions. Randomization ranks are descriptive because exchangeability across the selected observational groups is not established. Source-unit corrections were approved before fitting; the original stopped run and the corrected fraction-scale inference remain in the execution record. Exact-copy invariance required a documented contiguous-array numerical correction, without changing the scientific inputs or weakening the equality criterion.

**Figure 4.** Native errors with person-bootstrap uncertainty for the linked molecular pilot: [molecular validation](molecular_validation.svg). This result rejects promoting these fitted inverse estimators as superior or empirically calibrated reconstructors. It does not validate or invalidate every conditional Gaussian design calculation. Multimodal linkage, visit ablations, neural tasks, intervention qualification and cross-study metric-to-learning require further validation; these two outputs do not establish those claims.

## 8. Implementation, use and reproducibility

The canonical Python evaluator validates scientific-frame, task, profile and evidence identities. The browser consumes its outputs rather than implementing a second scoring formula. The local planner evaluates arbitrary supported hypothetical inputs; it does not round user inputs to a stored design grid. Its controls distinguish missing from unresolved domains, preserve exact level attainment, and expose native task limits and timing behind the category chart.

Installed-artifact checks reproduced 18 source-comparison CLI outputs byte-for-byte outside the source checkout and verified the native-summary compilation path. These checks establish package behavior within the tested examples. They do not establish biological validity or complete the release.

Public code and private evaluation are compatible. Raw participant inputs are not required on the public site. Local results and safe aggregate submission bundles carry the evaluator/reference identities. Ethics approval and publication are independently sourced filters; their metadata can change display membership without changing intrinsic scores. Hypothetical approval copies have distinct scenario identities and cannot overwrite the original study's status.

The reproducibility contract distinguishes replay of a calculation from verification of its biological inputs. Public aggregate examples require no account or participant upload. Exact receipts additionally bind implementation and numerical-runtime versions; another runtime can produce numerically similar values but a different receipt. Figure-data replay reproduces the stated aggregate visualization, not the original participant-level fitting. Private data, credentials, communications and the internal authority archive are excluded from public packaging.

## 9. Limitations and governance

The present reference is not a calibrated model of all biology. Its selected native anchors do not justify a complete molecular-depth or organism-reconstruction claim. Instrument mappings, native task relevance, scope omissions, covariance estimates and reference resolutions remain reviewable scientific choices. Task partitioning can change apparent scores unless canonical identities and total budgets are frozen. Normative weighting sensitivity must therefore remain visible.

Conditional likelihood precision cannot by itself establish causal identification, absence of bias, external transportability or useful learned representations. Empirical pilots show why those claims need separate tests. The current small number of empirical source systems, selective eligibility and negative or mixed calibration prohibit universal guarantees. A source failure is not evidence that a study itself is poor; an unknown is not a zero.

The current planner varies only supported parameters in a fixed recipe. It does not yet search all biologically feasible measurement technologies, durations, recruitment structures, costs or burdens. Completing those capabilities requires additional source contracts and validated adapters. Reaching a finite reference does not imply that further useful information is unavailable.

AI-assisted reviewers found material defects in earlier candidate constructions and checked the corrections. These reviews are documented software/scientific audits, not endorsement by independent human clinical experts. Contributor review, conflict disclosure, correction procedures and version governance must accompany the final public release. ANI studies receive the same task definitions and uncertainty rules as other studies; the score must not be tuned to force a desired winner.

## 10. Reproduction and scientific scope

The executable release exposes three complementary routes. `anibench plan` evaluates a declared hypothetical design against the fixed reference recipe. `anibench summary-task` compiles a qualified native summary into a finite task. `anibench benchmark` executes a trusted workload and score profile; it does not accept caller-supplied result percentages. Legacy `anibench eval` and `anibench compare` retain their separate compatibility contracts. See the release README and this paper's reproduction guide for installation and exact commands.

The ten-task native-mean pilot replays 360 summary derivations and six canonical suite receipts, then recreates its shared SVG. The cognitive/neural example separately replays its qualified summaries and frozen tasks. A fresh dependency environment installed the 19 locked runtime packages and reproduced the native-mean pilot outside the checkout. These checks establish reproducibility within that environment; they do not convert conditional source assumptions into observed facts.

The method supports evaluation before outcomes exist and source-qualified collected-data calculations afterward. It does not yet establish a universally calibrated mapping from arbitrary human-study inventories to biological information. Broad cross-study empirical validation and full private multimodal integration remain research and implementation work. Those limitations belong in the scientific claims, rather than being hidden by a release label or by a count of tests.

## 11. Availability, attribution and conflicts

Code is released under Apache-2.0; authored documentation and factual aggregate compilations follow the repository's stated data/document licensing policy. Original studies, source datasets and adapted materials retain their own licenses. Public URLs do not grant permission to redistribute complete articles or participant records. The package preserves source attribution and distinguishes source hashes from scientific verification.

AniBench is developed by ANI. Evaluation of ANI studies creates an institutional interest that must remain visible. No parameters are fitted to obtain a preferred ANI ranking, and private study results are not published through this methods paper. AI assistance contributed to implementation, drafting and adversarial review. Those reviews are not human clinical peer review, and this manuscript does not claim journal acceptance or community ratification.

## Appendix A. Mathematical properties


The following statements concern the declared experiment and fixed workload.
They are not empirical claims about every biological assay. They identify what
the evaluator can guarantee and which inputs scientific review must establish.

### Estimable functionals

For a linear Gaussian experiment with known positive-definite R, the score
derivative gives likelihood information J = H^T R^-1 H. A linear functional
c^T theta is identified exactly when c belongs to the range of J. Its
likelihood variance is c^T J^+ c on that range. J^+ denotes the Moore-Penrose
inverse. This expression must not be used for a functional outside the range:
the pseudoinverse would discard an unobserved direction and report false
certainty. A null direction is unbounded by the observations, even if a prior
assigns it a small variance.

The implementation is deliberately more conservative than the exact algebra.
It checks rank in the raw and prior-whitened information matrices, recognizes
exact structural zero rows/columns, and requires a full-rank certificate on
the remaining structural support. A general numerically singular rotated
subspace remains unknown rather than being certified from a small projection
residual. The prior-whitening metric assists numerical analysis; no prior-only
pass is credited as acquired information. Finite floating-point tolerances
are recorded in each receipt and can make borderline classifications depend
on the numerical environment.

### Additional valid information cannot worsen identified precision

On a fixed identified parameter space, let J_1 be positive definite and let
Delta be positive semidefinite information from additional conditionally
independent, correctly modeled observations. Then J_2 = J_1 + Delta and
J_2^-1 is no larger than J_1^-1 in the positive-semidefinite order. To see this,
whiten by J_1: I + J_1^-1/2 Delta J_1^-1/2 has eigenvalues at least one;
its inverse has eigenvalues at most one. Transforming back proves the result.
Thus every fixed functional variance can only decrease. In exact arithmetic,
fixed-threshold attainment and precision adequacy cannot decrease when their
support and identification conditions remain unchanged. Numerical software
classification has a separate limitation: adding an extremely strong direction
can make a weaker direction numerically unresolved under a relative-rank
tolerance. For example, J=I changed to diag(1e20,1) leaves the second
coordinate's exact variance at one, but the conservative implementation returns
unknown for the latter matrix. The theorem does not promise monotonic
floating-point classification under arbitrarily ill-conditioned inputs.

This proposition does not justify adding information matrices for dependent
observations, mixing populations, or ignoring newly discovered bias. A revised
model or evidence correction can lower a previously overstated result. For
correlated acquisitions, use the full joint observation model or its justified
conditional innovation, not an independent-observation sum.

### Exact copies do not add information

If a recorded value y is copied, the pair (y,y) is a deterministic transform of
y, and y can be recovered from the pair. They generate the same statistical
experiment. Treating the two entries as independent changes the model and is
invalid. Physical acquisition identity therefore belongs in the input contract.
The correlated-repeat example gives the same conclusion: for k exchangeable
repeats with correlation rho, the mean variance is sigma^2[1+(k-1)rho]/k.
At rho=1, it is sigma^2 for every k. At rho=0, it is sigma^2/k. The current
reference restricts rho to [0,1]; it does not claim that all biological noise
has this exchangeable form.

### Complementarity differs from repeated precision

Consider independent unit-variance observations with rows H_1 = [1,1] and
H_2 = [1,-1]. Each alone identifies one sum or difference, but neither identifies
theta_1 or theta_2 separately. Together J = 2I, yielding variance 1/2 for each
coordinate. Repeating the first row independently reduces uncertainty in the
sum while leaving the difference unidentified. This is a nonlinear gain in
the set of answerable questions, without assuming an exponential bonus for
each modality label. A real modality earns this interpretation only through
a defensible operator and covariance.

### Units do not define the ranking

Under an invertible change of parameter units theta' = A theta, the transformed
information is J' = A^-T J A^-1 and the transformed functional coefficients are
c' = A^-T c. On an identified space, c'^T J'^-1 c' = c^T J^-1 c. If the reported
target itself is rescaled by a scalar b, both its variance and its ceiling must
be multiplied by b^2. The threshold decision and variance-to-ceiling ratio then
remain unchanged. Inconsistent conversion of a source variance or a target
ceiling is a different, invalid input. Numerical extreme-unit cases can remain
unresolved under the conservative rank checks.

### Fixed workload bounds and scenario coherence

For fixed nonnegative normalized task masses, every assignment of unresolved
tasks to pass or fail lies between confirmed-pass mass and confirmed-pass plus
unresolved mass. This proves the reported epistemic outer interval. It does
not prove that its endpoints are jointly feasible. If tasks A and B can pass
only in mutually exclusive scenarios, their separate optimistic possibilities
cannot establish a simultaneous level pass. The evaluator applies the declared
scenario quantifier to complete task vectors before deciding attainment.

Copying or renaming a task cannot legitimately add workload mass. Exact
canonical duplicates and invalid partitions are rejected by the software.
Biological synonymy across newly authored frames still needs scientific
review; a hash cannot detect a misleading scientific redefinition. Subdividing
one requirement must preserve its original total mass if the claimed workload
is unchanged. New versions may deliberately change the workload, but cannot be
compared as though their denominators were identical.

### Nested levels

Suppose a child profile retains every parent task's scientific frame, support
and scenario semantics, and does not loosen any inherited precision ceiling.
If all child requirements pass under the declared coherent scenario rule, all
parent requirements pass under the same conditions. This is the level
inheritance guarantee. It is violated by changing populations, dropping a
parent task, relaxing a ceiling, or assembling passes from different scenarios;
these are checked separately from numerical score rounding.

### What these properties do not prove

Sampling precision is not protection against bias. For an estimator with bias
b and variance v, mean squared error is v+b^2. Increasing N can reduce v while
leaving b unchanged. The native-summary route estimates the sampling term and
must not describe it as total biological truth. Likewise, full-rank design
geometry does not establish exchangeability, randomized assignment, adherence, absence of interference, measurement equivalence or transportability.

Unknown population support, linkage or covariance must be resolved by evidence,
an explicitly conditional scenario, or an alternative model. Neither spending,
prestige, publication, ethics status nor a favorable observed treatment effect
supplies missing mathematical information. These remain separately reported
properties of the source and study.

## Appendix B. Native reference anchors

These are the 23 anchors used by the conditional recipe, not the ten-task real-source pilot. Every value is a research convention; none is asserted to be a clinical cutoff or independently calibrated biological sufficiency threshold. Population-mean and bridge scales, and AB2 tightening, follow Section 6. The frozen machine catalogue carries additional compartment and operator restrictions.

| Domain | Named observable | Native SE anchor |
|---|---|---|
| Molecular | Serum albumin concentration | 1 g/L |
| Molecular | IL-6 immunoreactive concentration | 0.5 pg/mL |
| Molecular | Apolipoprotein B mass concentration | 0.05 g/L |
| Molecular | Fasting plasma glucose concentration | 0.25 mmol/L |
| Molecular | Serum triglyceride concentration | 0.15 mmol/L |
| Molecular | Leucine concentration | 10 µmol/L |
| Molecular | Lactate concentration | 0.2 mmol/L |
| Molecular | CD4 positive T-cell absolute count | 50 cells/uL |
| Molecular | Naive fraction within CD4 T cells | 5 percentage points |
| Molecular | Faecalibacterium prausnitzii relative abundance | 0.01 fraction of assigned microbes |
| Molecular | Butyrate synthesis pathway abundance | 10 copies per million microbial gene copies |
| Molecular | PPARGC1A transcript abundance | 0.5 log2 TPM |
| Molecular | Median adipocyte section area | 100 µm² |
| Physiological | Maximum dominant-hand grip force | 2 kg-force |
| Physiological | Usual 4m gait speed | 0.05 m/s |
| Physiological | Mean current-session systolic pressure | 5 mmHg |
| Digital | Mean waking wrist acceleration ENMO | 5 milli-g |
| Digital | Night total sleep duration | 20 minutes |
| Cognitive / psychological | Median correct simple reaction latency | 20 ms |
| Cognitive / psychological | Digit Symbol Coding correct score | 3 correct symbols |
| Cognitive / psychological | PHQ-9 sum score | 2 score points |
| Neural observation | P3b target-minus-standard mean voltage | 1 µV |
| Neural observation | N170 face-minus-car mean voltage | 1 µV |

The microbial pathway reference uses its explicitly declared normalized gene-copy scale. The HMP2 empirical target is a released relative pathway abundance. They are different quantities and are not interchangeable by a unit conversion. Likewise, the neural reference tasks concern P3b/N170 ERP observables; the source-comparison hippocampal tasks concern structural imaging. One does not stand in for the other.
