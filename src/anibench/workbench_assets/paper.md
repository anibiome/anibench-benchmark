# AniBench: a task-based reference for the information capacity of human studies

**Working scientific manuscript. Results and code are still being integrated. This document is not the completed release or a claim of biological standard validation.**

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

The current v0.4 research reference contains 23 named native anchors grouped into 18 AB1 and 24 AB2 task bundles across five domains. It is a deliberately limited reference recipe, not coverage of all omics, tissues, mechanisms or human experience. The task registry states the exact observables and windows. AB2 inherits the AB1 scientific frames, tightens SE requirements, and adds defined contrast, heterogeneity or measurement-bridge tasks. Changes in meaning require a separately identified profile rather than a misleading nested label.

The synthetic model separates a fixed focal person's paired change from a population mean inferred from the other `N−1` independent people. With individual paired measurement variance `V` and between-person change variance `B`, their observations have covariance blocks `V` and `(B+V)/(N−1)`. There is no prior link between the focal parameter and the population mean. This construction corrects an earlier candidate that incorrectly treated a shared focal/cohort summary as an identity observation model.

Balanced population contrasts retain a between-person floor: `4(B+R/d)/N` for two arms, and `16(B+R/d)/N` for a four-cell subgroup-effect contrast. Technical depth `d` reduces specified measurement-noise components; it does not remove population heterogeneity. Technical repeats have effective count `k/[1+(k−1)ρ]` under the declared exchangeable model. They are not extra biological visits.

Analytic constraints derive a finite participant/depth frontier conditional on every required source of support, fixed time windows, variance assumptions and balanced retained allocation. The current sweep comprises 720 algebraic settings, with 117 canonical boundary evaluations. An independent reviewer recomputed all rows using exact rational arithmetic, reconstructed 224 nondominated sampled-grid points, and reproduced three saved witnesses.

At four technical repeats, repeat correlation 0.2 and the standard reference resolution under both declared noise scenarios, an illustrative AB1 boundary is 1,298 retained people at depth 128; AB2 has a boundary of 5,140 at depth 512. These numbers follow from the chosen model. They are not recommendations that these counts, assays or budgets suffice for human biological reconstruction. Missing individual precision can remain unattainable at any N; missing population support cannot be repaired by extreme individual depth. Costs, attrition assurance and participant burden require additional qualified inputs.

**Figure 1.** Conditional N-versus-depth boundaries: [conditional frontier](conditional_frontier.svg). The displayed frontier is conditional on a sampled grid and fixed repeat/correlation settings. Different correlation curves can coincide when another requirement is limiting.

## 7. Current source examples and empirical evidence

### 7.1 Native source comparisons

The first integrated source comparison evaluates two named own-population mean tasks using LIFE, CALERIE and ASPREE aggregate sources. It preserves native units, source-specific populations, conditional denominators and the distinction between an unadjusted reported SEM and an individual SD. Six source-group records produce 18 suite executions across three illustrative SE resolutions. These are three studies, not 18 trials, and the two-task comparison is not a whole-study ranking.

The integrated source snapshot includes 54 family-level qualification dispositions, of which 22 have numerical native-precision inputs, comprising 76 aggregate records. Canonical likelihood-only replay includes 183 single-task benchmark evaluations and 30 contrast diagnostics. These are not 183 distinct studies or whole-reference evaluations. Twelve historical posterior-based pass labels became failures when prior information was excluded. Five explicitly conditional own-population comparison groups contain 42 source-record pairs; measurement-equivalence assumptions remain disclosed. Publication, arms and strata of one study do not become independent studies. Missing denominators, dependence and operator qualification remain explicit gaps. Broad multi-category real-study coverage is not complete.

A subsequent source batch adds 20 distinct family dispositions and three numerical native-precision families, bringing the reviewed intake to 74 dispositions and 25 numerical families. Its separate MIPACT/DIRECT PLUS pilot allocates two native population-mean targets to each of five domains. Fixed thresholds were selected after source inspection, frozen before scoring, and tested at half and double the declared standard-error limits. Six coherent scenarios combine reported or doubled variance with reported and half-last-digit rounding bounds. Source-specific populations and conditional table-header counts remain explicit. Unreported cognitive precision and unsupported bilateral hippocampal interpretation remain unknown. These ten targets do not establish complete domain coverage or AB1 attainment. [MIPACT source](https://pmc.ncbi.nlm.nih.gov/articles/PMC7414690/), [DIRECT PLUS source](https://pmc.ncbi.nlm.nih.gov/articles/PMC9071484/).

### 7.2 Reconstruction pilot: negative and mixed findings

A frozen NHANES pilot evaluated two independently measured native targets using three nested input menus, with 4,412 eligible complete-case adults assigned to train, calibration and evaluation partitions while preserving the chosen group structure. Six train-fitted conditional Gaussian inverse models yielded no target-resolution passes and three prespecified calibration flags. Both predicted precision and held-out errors improved in four nested-menu comparisons. Nevertheless, the likelihood-only inverse estimates lost to the training-mean and ridge baselines in all six fits.

This finding does not justify calibrated predictive guarantees from the fitted matrices. The residual covariance in that experiment describes conditional biological variation as well as measurement/model effects; it is not an independently identified technical-noise covariance. The study retains this distinction and the negative baseline comparison. No post-test threshold tuning was used to manufacture a successful result. The result also does not make prediction performance the primary study-capacity score.

### 7.3 Temporal placement beyond recording duration

A separate frozen experiment used public Sleep-EDF sleep-stage annotations to compare temporal sampling placements within fixed eight-hour records. After prespecified exclusions, 108 nights from 68 people remained, with 34/12/22 independent people in train/calibration/evaluation partitions. Repeated nights stayed with their person. Three placement schemes sampled the same 32, 64 or 128 minutes: random scattered epochs, one circular block, or a block within each hour.

For these finite annotation targets, exact design covariance can be computed. All 12 prespecified equal-duration placement contrasts favored scattered or distributed sampling over a contiguous circular block under the implemented Holm-adjusted screen. Calibration was mixed: eight of 18 risk-equivalence screens passed and three target-resolution cells passed. Only the 128-minute scattered design met both illustrative native precision targets. The Gaussian information calculation is a working risk representation, not proof that the annotation process is the true biological likelihood.

**Figure 2.** Training-predicted SE and held-out exact sampling RMSE: [temporal sampling](temporal_sampling.svg). The source is existing scored annotations, not newly acquired EEG or independently established persistent-person sleep traits. Circular wrapping and complete-case selection limit interpretation. [Sleep-EDF source](https://physionet.org/content/sleep-edfx/1.0.0/).

### 7.4 Paired intervention-source eligibility stop

A prespecified telemetry annotation experiment attempted all 22 source people with paired drug/placebo nights. The independently reviewed protocol required a fully scored eight-hour window after each source lights-off clock. Only three pairs passed, below the frozen minimum of ten. Seven files also encountered an EDF+ recording-field parser compatibility limitation. No contrast precision or effect estimate was produced. The window, exclusions and sample floor were not relaxed after inspection. This source attempt does not close intervention validation.

### 7.5 Linked molecular validation: a retained negative result

A frozen HMP2 experiment linked released molecular tables and selected one eligible specimen per person before fitting. There were 454 exact matched collections, 443 after source quality exclusions, and 106 people in fixed 53/21/32 training/calibration/test partitions. The four inputs were lactate, succinate, propionate and butyrate; positive-log transformation and standardization were fitted within training. The two targets were released F. prausnitzii relative abundance and unstratified PWY-5676 relative pathway abundance, not physiological flux or independently assayed latent state. [Primary HMP2 study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6650278/).

| Native target | Training-mean RMSE | Ridge RMSE | Inverse RMSE |
|---|---:|---:|---:|
| F. prausnitzii relative fraction | 0.0899973 | 0.0818297 | 0.334991 |
| PWY-5676 relative pathway abundance | 0.000658683 | 0.000792690 | 0.00351959 |

Both likelihood-inverse estimates performed worse than the simple baselines. Neither raw nor calibration-adjusted risk-to-predicted-variance interval fit inside the frozen equivalence region [0.8, 1.25]. Near-nominal point coverage therefore did not establish calibration. Person-level resampling used 1,000 successful bootstrap fits per target, retaining the fixed partitions. Randomization ranks are descriptive because exchangeability across the selected observational groups is not established. Source-unit corrections were approved before fitting; the original stopped run and the corrected fraction-scale inference remain in the execution record. Exact-copy invariance required a documented contiguous-array numerical correction, without changing the scientific inputs or weakening the equality criterion.

**Figure 3.** Native errors and risk calibration for the linked molecular pilot: [molecular validation](molecular_validation.svg). This result rejects promoting these fitted inverse estimators as superior or empirically calibrated reconstructors. It does not validate or invalidate every conditional Gaussian design calculation. The original broader requirements for multimodal linkage, visit ablations, neural tasks, intervention qualification and cross-study metric-to-learning remain open; these two outputs are not substitutes for that programme.

## 8. Implementation, use and reproducibility

The canonical Python evaluator validates scientific-frame, task, profile and evidence identities. The browser consumes its outputs rather than implementing a second scoring formula. The local planner evaluates arbitrary supported hypothetical inputs; it does not round user inputs to a stored design grid. Its controls distinguish missing from unresolved domains, preserve exact level attainment, and expose native task limits and timing behind the category chart.

Installed-artifact checks reproduced 18 source-comparison CLI outputs byte-for-byte outside the source checkout and verified the native-summary compilation path. These checks establish package behavior within the tested examples. They do not establish biological validity or complete the release.

Public code and private evaluation are compatible. Raw participant inputs are not required on the public site. Local results and safe aggregate submission bundles carry the evaluator/reference identities. Ethics approval and publication are independently sourced filters; their metadata can change display membership without changing intrinsic scores. Hypothetical approval copies have distinct scenario identities and cannot overwrite the original study's status.

Current artifacts are still being reconciled into a complete release. A final reproducibility manifest must bind the package, schemas, reference definitions, source-qualified outputs, figures, paper and deployed site. Private data, credentials, communications and this project's internal authority archive are excluded from public packaging.

## 9. Limitations and governance

The present reference is not a calibrated model of all biology. Its selected native anchors do not justify a complete molecular-depth or organism-reconstruction claim. Instrument mappings, native task relevance, scope omissions, covariance estimates and reference resolutions remain reviewable scientific choices. Task partitioning can change apparent scores unless canonical identities and total budgets are frozen. Normative weighting sensitivity must therefore remain visible.

Conditional likelihood precision cannot by itself establish causal identification, absence of bias, external transportability or useful learned representations. Empirical pilots show why those claims need separate tests. The current small number of empirical source systems, selective eligibility and negative or mixed calibration prohibit universal guarantees. A source failure is not evidence that a study itself is poor; an unknown is not a zero.

The current planner varies only supported parameters in a fixed recipe. It does not yet search all biologically feasible measurement technologies, durations, recruitment structures, costs or burdens. Completing those capabilities requires additional source contracts and validated adapters. Reaching a finite reference does not imply that further useful information is unavailable.

AI-assisted reviewers found material defects in earlier candidate constructions and checked the corrections. These reviews are documented software/scientific audits, not endorsement by independent human clinical experts. Contributor review, conflict disclosure, correction procedures and version governance must accompany the final public release. ANI studies receive the same task definitions and uncertainty rules as other studies; the score must not be tuned to force a desired winner.

## Working-paper completion obligations

Before public release, reconcile the broader source corpus and paired/controlled contrasts; complete the finite empirical programme with all negative results; resolve the required private ELITE coverage or retain exact open contracts; integrate the complete product journeys; reproduce all figure classes; verify licenses and public disclosure scope; finalize authorship, citations and contribution governance; render and inspect every paper page; and bind the paper to the independently checked release. This list records unfinished work and is removed or replaced by actual evidence at publication. It is not a claim that a draft is the finished deliverable.
