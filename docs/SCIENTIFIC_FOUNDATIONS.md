# Scientific foundations and novelty boundary

AniBench is an information-geometric benchmark and prospective design system for
human experiments. The scientific contribution is the auditable composition of
participant-event jointness, biological observation operators, nuisance-aware
information, longitudinal support, explicit causal assignment geometry, sequential
personalization, population transport, typed evidence, and source-bound
reproducibility. It does not claim that Fisher information, Bayesian design,
adaptive trials, or data provenance were invented here.

## Established foundations

| Foundation | AniBench use | Claim not made |
|---|---|---|
| Fisher information and Bayesian experimental design | positive-semidefinite event information and posterior-volume contraction | that protocol information equals empirical model utility |
| D-optimal design | log-determinant contraction across independent directions | that one determinant is a complete trial-quality score |
| Local Gaussian inference | prior whitening, posterior covariance, and directional contraction | that all biological systems are linear or Gaussian |
| Longitudinal design | within-person schedules and correlation-adjusted repeated support | that nominal visits or calendar duration are independent observations |
| Causal trial statistics | explicit estimands, assignments, contrasts, positivity, and linked outcomes | that randomization labels or favorable results prove every causal estimand |
| SMART and micro-randomized designs | repeated eligible decisions, known propensities, prospective moderators, and sequential information | that clinician discretion or retrospective subgroups are personalized trials |
| Transportability | context-coordinate contrasts and held-cohort validation | that site, country, or sample count alone proves generalizability |
| FAIR and executable data practice | persistent identifiers, provenance, lawful access, and clean reanalysis | that a publication or portal page makes data accessible |
| Benchmark governance | frozen versions, source receipts, hostile tests, impact analysis, and immutable releases | that passing software tests establishes biological validity |

## AniBench-specific synthesis

The following are versioned AniBench v2 engineering decisions:

1. a finite Level-1 mesoscopic biological coordinate registry spanning state,
   dynamics, perturbation response, heterogeneity, function, and transport;
2. participant-event hyperedges that require explicit higher-order jointness;
3. physical measurement ancestry and covariance controls that make duplicate depth
   saturate;
4. separation of intensive, extensive, longitudinal, causal,
   personalized/sequential, and transport families;
5. reference completion computed in frozen biological directions rather than from
   an unordered eigenvalue list;
6. a direction-wise cap that prevents information in one direction from compensating
   for missing directions, with overflow reported separately;
7. separate whole-policy, component, sequential, and transport matrices derived from
   protocol geometry;
8. Design Preview, Registered Protocol, Realized, Accessible, and Demonstrated
   evidence lanes that do not numerically penalize identical planned geometry;
9. exact, interval, conditional, unknown, and absent coordinate states; and
10. a protocol-native Pareto optimizer that changes source-bound design geometry and
    recompiles every candidate without weights or a hidden overall scalar.

These decisions can change only through a versioned methods proposal, impact report,
test update, and governance decision. ANI-affiliated studies are evaluation cases,
not authority-construction or empirical-calibration inputs.

## Why additional biological layers can compound

For event type \(e\), AniBench constructs

\[
\mathcal I_e=n_eA_e^\mathsf{T}R_e^{-1}A_e.
\]

After nuisance adjustment and prior whitening, local posterior-volume contraction is

\[
L=\frac{1}{2\ln 10}\log\det(I+G).
\]

Independent resolved directions multiply the reduction in remaining local
hypothesis volume. A synchronized molecular, functional, contextual,
longitudinal, and intervention record can therefore add much more than an assay
checklist suggests. The covariance and direction-cap rules are equally important:
duplicated or highly correlated layers saturate, and extreme depth in one direction
does not manufacture breadth.

## Empirical validity contract

The candidate design prior becomes biologically validated only if it predicts what
models actually learn. Validation must use source-linked human datasets with
held-person, future-time, held-modality, held-intervention, held-site, and held-cohort
tasks; calibration; appropriate nulls and permutations; missingness sensitivity;
and coalition ablations. Simple participant, visit, modality, feature, and byte-count
baselines are mandatory. Authority choices that fail their preregistered validation
targets are recalibrated or superseded in a new version.

Software correctness, source completeness, empirical validity, independent review,
and public release remain separate receipt layers.

## Primary standards and methods

- [Lindley: information provided by an experiment](https://doi.org/10.1214/aoms/1177728069)
- [Chaloner and Verdinelli: Bayesian experimental design](https://doi.org/10.1214/ss/1177009939)
- [Kiefer and Wolfowitz: D/G-optimal design equivalence](https://doi.org/10.4153/CJM-1960-030-4)
- [Cole and Stuart: trial transport to target populations](https://doi.org/10.1093/aje/kwq084)
- [ICH E9(R1): Estimands and Sensitivity Analysis](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
- [CONSORT 2025](https://www.bmj.com/content/389/bmj-2024-081123)
- [SPIRIT 2025](https://www.bmj.com/content/389/bmj-2024-081477)
- [FDA adaptive clinical-trial guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/adaptive-design-clinical-trials-drugs-and-biologics-guidance-industry)
- [FAIR Guiding Principles](https://doi.org/10.1038/sdata.2016.18)
- [Datasheets for Datasets](https://doi.org/10.1145/3458723)
- [HELM](https://arxiv.org/abs/2211.09110)
- [MLPerf methodology](https://doi.org/10.1109/MM.2020.2974843)

These sources establish the methodological lineage. They do not endorse AniBench
formulas, target levels, or study evaluations.
