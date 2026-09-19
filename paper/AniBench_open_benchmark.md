# AniBench: an open benchmark for biological learning capacity in human studies

**Bruno Balen**<br/>
ANI Biome PBC<br/>
Research manuscript, 19 September 2026

## Abstract

Human studies differ in the biological questions their records can support.
Enrollment, assay breadth, repeated observation, intervention assignment, and
cross-modal linkage describe different properties; none alone measures the
capacity to learn human biology. We introduce AniBench, an open framework for
evaluating study design and collected-record capacity independently of favorable
treatment outcomes. The framework separates auditable collection facts from
information estimates conditional on an explicit biological target, prior,
observation operator, and noise model. Six complementary families describe
intensive, extensive, longitudinal, causal, personalized/sequential, and transport
capacity. The implementation includes a local collection profiler, explicit
CSV/CSV.gz adapters, a geometry evaluator, a comparator for compatible evaluation
receipts, a finite-task conditional precision runner, and a public study explorer.
A separate design planner checks whether shared model assumptions can satisfy
several declared precision constraints together. Collection metrics preserve the complete
declared participant roster, distinguish quality states, deduplicate target-event
coverage, and report joint measurement and follow-up distributions. We derive
the connection between linear Gaussian information gain and posterior-volume
contraction and explain why neither target count nor data volume substitutes
for this quantity. Reproducible synthetic examples demonstrate opposing strengths
in depth and temporal span without an overall winner. A public literature atlas
illustrates heterogeneous denominators and the limits of comparisons from
published summaries. The present results establish software behavior and
conditional mathematical properties; they do not establish a biologically
validated ranking of real studies. AniBench is intended as an extensible standard
whose targets, assumptions, evidence, and implementation can be inspected,
challenged, and reproduced while participant data remain private.

**Keywords:** human studies; biological information; experimental design;
longitudinal measurement; causal inference; open benchmarks; reproducibility.

## 1. Introduction

An increasingly capable biological model would need more than a large table of
endpoints. It would need observations of states and transitions, measurements
that can be linked within people, interventions with interpretable assignment,
and evidence about variation across people and settings. Some human studies
provide population breadth, others dense molecular observations, and others
stronger experimental control. Comparing these contributions requires preserving
their differences.

The motivating question is: **what can a future model learn from the biological
record produced by this study?** This is a question about the experiment and its
record. It is distinct from whether an intervention produced a desirable result.
A precisely measured null response can be informative. Conversely, a favorable
endpoint does not establish broad observability, temporal resolution, or transport
to another population.

Benchmark practice in machine learning provides useful organizational precedents:
published tasks, versioned rules, reproducible implementations, multiple metrics,
and explicit conditions for comparison. Those practices do not supply the
biological targets or validate a particular information model. AniBench combines
this release structure with statistical experimental design and the distinction
between biological observability and parameter identifiability [1–4].

The contribution is an explicit separation of four questions:

1. **Collection:** what observations exist, for whom, when, and with what linkage
   and declared quality?
2. **Conditional capacity:** what could the design resolve under a specified
   biological and statistical model?
3. **Demonstrated learning:** what does a specified learning procedure recover on
   genuinely held-out people, events, interventions, or contexts?
4. **Intervention outcomes:** what happened to specified endpoints under a defined
   treatment contrast and follow-up window?

The first two define the main benchmark. The latter two are separate, optional
evaluations. Open implementation does not require public participant records.

## 2. Evaluated objects and evidence

### 2.1 A study is a linked observation system

For participant i, consider biological state z_i(t), exposures u_i(t), context
c_i(t), and measurements y_ij(t). A useful modeling template is

\[
dz_i(t)=f_\theta(z_i(t),u_i(t),c_i(t))dt+
G_\theta(z_i(t),u_i(t),c_i(t))dW_i(t),
\qquad
y_{ij}(t)=h_j(z_i(t),s_{ij},b_{ij})+\epsilon_{ij}(t).
\]

Here s identifies specimen or device context and b represents relevant batch
conditions. The expression is a modeling language, not a claim that one diffusion
process describes all human biology. Discrete events, delays, spatial structure,
multiple compartments, and non-Gaussian observations may require other models.
Observability is always relative to the model, outputs, inputs, and initial
conditions being considered [3].

Biophysical restrictions belong in a target model when justified: units must be
consistent; designated concentrations and rates must remain admissible; balance
equations must account for exchange with the environment; responses cannot
precede their causes. A human is an open system. Invoking thermodynamics does
not justify assuming constant whole-body mass or energy, nor does a pathway
label establish a conservation law.

### 2.2 Proposed and collected records

A planned record describes intended participants, observations, and assignment.
A collected record describes retained observations. They use the same counting
definitions but remain distinct evidence bases. A study does not receive a
numerical maturity bonus because it has been published, registered, or made
accessible. Real losses of participants, measurements, or linkage do change the
collected record.

Evidence distinguishes exact source-bound quantities, reported values and their
precision, intervals, conditional estimates, unknown quantities, and verified
absence. Missing information is not zero. A content hash binds an object to its
bytes; it does not certify the truth, completeness, or authority of that object.

## 3. Collection metrics

### 3.1 Definitions

Let R be the explicitly declared participant roster. For module m, participant i,
and canonical event e, let A(i,e,m) contain the registered target identifiers
with accepted availability. Modules identify a measurement definition and unit;
analytes, derived image coordinates, functional measures, and inferred microbial
pathways are not interchangeable targets.

The profiler computes:

\[
N_m=|\{i\in R:\exists e, A(i,e,m)\ne\varnothing\}|,
\quad
E_m=|\{(i,e):A(i,e,m)\ne\varnothing\}|,
\quad
C_m=\sum_{i,e}|A(i,e,m)|.
\]

N_m is participant coverage, E_m is participant-event coverage, and C_m is target
observations. The distinct targets observed for person i are

\[
D_{im}=\left|\bigcup_e A(i,e,m)\right|.
\]

The distribution of D_im includes every roster member, including zero for a
person without accepted targets. By contrast, target counts per observed event
condition on populated events. Both the numerator and its population are
reported. No sum across unlike module units is presented as biological depth.

For modules m and n, joint event coverage is

\[
J_{mn}=|\{(i,e):A(i,e,m)\ne\varnothing
\land A(i,e,n)\ne\varnothing\}|.
\]

The implementation additionally reports people with both modules at any time
and people with both at the same event. These are different statements about
linkage. Co-dated observations at day resolution need not be simultaneous.

### 3.2 Quality, missingness, and time

Collected acquisitions have declared pass, fail, or unknown quality. Only pass
contributes to accepted coverage; planned acquisitions use a separate planned
state. Quality definitions remain source obligations: a caller's pass label is
not an independent laboratory audit. Numeric zero is available; explicitly
declared missing tokens are not. Counts describe availability, not detection
above a limit of quantification, unless that criterion is part of the declared
source rule.

Dated event aliases at an identical participant/time coordinate are combined.
Undated events retain source identity and contribute no duration. No inferred
matching window, time imputation, or independence assumption is introduced.
Absolute timestamps are aligned to each participant's first included event; this
origin is not automatically intervention start.

For participants with at least two known observation times, the profiler reports
the distribution of max(t)-min(t). It also reports distinct times for all roster
members and adjacent intervals. Interval distributions weight each interval once;
they are not person-weighted estimates. Quantiles use linear interpolation and
describe the supplied record, not sampling uncertainty.

Partial inventories and unresolved QC produce lower bounds on accepted coverage
counts, conditional on a fixed roster, event identity and target definitions.
Undated event aliases can collapse when dates resolve, so event-based comparison
bounds remain unresolved in that case. This does not make
the median span of observed repeat participants a lower bound on the full
cohort's median follow-up. Duration summaries retain this conditional scope.

### 3.3 Representation invariance

Repeated export rows and target aliases cannot create additional distinct
target-event coverage when their lineage and target definitions are unchanged.
This follows directly from set union: A union A equals A. Conflict in a reused
acquisition identifier is rejected instead of silently adjudicated.

Reusable target sets provide a compact encoding for wide repeated assays. An
acquisition references a module-bound target set rather than copying thousands
of names. Expansion produces the same A(i,e,m), and therefore the same N_m, E_m,
C_m, D_im, and J_mn. The implementation tests this equivalence. Encoding
invariance does not establish that two differently named source targets are
biologically distinct; target ancestry remains an evidence-review obligation.

## 4. Conditional information and six capacity families

### 4.1 Linear Gaussian information

For an explicitly defined target parameter theta with Gaussian prior N(mu_0,P_0),
consider y=A theta+epsilon. Let epsilon be independent of theta and distributed
as N(0,R), with P_0 and R positive definite. With parameter-independent noise,

\[
F=A^T R^{-1}A,\qquad
P_{post}=(P_0^{-1}+F)^{-1}.
\]

The expected information gain in nats is

\[
\mathcal I(\theta;y)
=\tfrac12\log\frac{\det P_0}{\det P_{post}}
=\tfrac12\log\det(I+P_0^{1/2}FP_0^{1/2})
=\tfrac12\sum_k\log(1+\lambda_k).
\]

The lambda_k are eigenvalues of prior-whitened likelihood information. This is
an exact identity for the stated Gaussian model [1]. The core implementation
stores prior precision and reports the corresponding log10 posterior-volume
contraction, I/log(10). A local sensitivity approximation for a nonlinear model
is not automatically its global expected information gain.

The spectrum matters. A large volume contraction can coexist with an unresolved
direction. Rank, weak directions, target uncertainty, and model assumptions must
accompany a log-volume value. Numerical rank is tolerance-dependent and must not
be represented as a count of all biologically meaningful dimensions.

**Units.** Under an invertible observation transform y'=By, transforming both
A and R gives F'=A^T B^T(BRB^T)^{-1}BA=F. Parameter re-expression similarly
preserves information when both the prior and likelihood transform. Changing
units while leaving noise or the prior fixed changes the problem, not merely
its notation.

**Additional observations.** For conditionally independent observations on a
shared target, likelihood information adds. Adding a positive semidefinite
increment cannot decrease log-determinant information. Correlated observations
require their joint covariance or conditional information; simply adding their
standalone contributions overcounts evidence. Optimal information-based sensor
selection provides a related, model-specific design literature [2].

**Duplicates.** For any probability model, I(theta; y,y)=I(theta; y): a copy of
an observation cannot create information. A new independent technical replicate
can reduce measurement uncertainty, but it does not create a new biological
target. The collection layer and information layer therefore treat these two
questions separately.

### 4.2 The capacity vector

| Family | Question | Required structure |
|---|---|---|
| Intensive | What can one linked participant-event resolve? | Joint observations, target sensitivities, noise and ancestry |
| Extensive | What information does the retained population contribute? | Participant/event support, dependence, and target definition |
| Longitudinal | Which changes and timescales are distinguishable? | Actual times, repeat linkage, temporal sensitivities and dependence |
| Causal | Which intervention contrasts are identifiable? | Assignment, comparator, exposure and response-window structure |
| Personalized/sequential | Which modifiers or decision histories are supported? | Pre-assignment modifiers, sequential randomization and eligible histories |
| Transport | Which relations are supported in other contexts? | Context definition, overlap, effect-modifier support and transport assumptions |

These families form a vector. Sample size cannot replace an unobserved direction
within an event. Additional modalities cannot replace a missing randomized
contrast. Native allocation-support quantities are labeled as support proxies,
not converted into biological information by renaming their units.

Extensive information depends on what is shared across people. Learning a common
population parameter differs from resolving a separate latent state for every
person. Neither multiplying a one-person score by enrollment nor treating all
repeated samples as independent is generally justified.

For a dynamical model, sensitivities propagate through the system. In a linear
state model they involve H_t Phi(t,t_0), with a joint covariance across observation
times. Elapsed duration alone is not observability. For example, observing
y(t)=theta exp(-t)+epsilon later reduces information about theta at fixed noise
if it replaces an earlier observation. Adding the later observation while
retaining the earlier one is a different experiment.

A randomized active-versus-active study may identify the assigned policy
contrast without identifying the effect of every shared ingredient. Observational
perturbations may inform dynamics while requiring additional confounding
assumptions for causal claims. Individual prediction, heterogeneous treatment
effects, and adaptive policy learning require distinct estimands and validation.
Transport to another population requires assumptions beyond overlap counts [5].

## 5. Comparison and benchmark evolution

A comparison claim must name the metric, target, units, denominator, evidence
basis, source version, implementation, uncertainty rule, and comparison corpus.
Compatible information estimates share their target and prior/noise semantics.
Observed counts and conditional model estimates occupy separate comparisons.
Unknown information geometry does not erase otherwise supported source facts.

The implemented `anibench compare` operation checks canonical receipt hashes
and one shared implementation and authority basis before computing within-family
Pareto relations. For a directionally aligned metric vector, a design dominates
another only when it is no worse on all included coordinates and better on at
least one under the comparator's supported uncertainty rules. Incompatible
objects are rejected. The command does not emit an overall scalar or ordinal
study rank.

For metric-specific public leaderboards, the rule and corpus must be frozen
before assessing desired winners. A participant-count leader is a leader on a
specified population count, not necessarily the best experiment. Ties and
overlapping uncertainty must remain visible. A lower bound cannot be treated as
an exact point; an unbounded missing quantity prevents a definite ordering when
it could change the comparison. The implemented `anibench compare-records` operation provides native-metric
comparison cards independently of the geometry comparator. It checks profile
hashes, a common implementation, evidence basis, time resolution, and declared
population, observation and quality definitions. Module comparisons additionally
require matching target definitions and units. These declarations make the
comparison reviewable; they are not independent scientific certification.

For closed evidence bounds [L_i,U_i], strict superiority requires L_i > U_j.
Competition-rank bounds are 1 plus the number of definitely higher studies, and
1 plus the number of possibly higher studies. Exact ties share a rank; an
unbounded upper value is retained as unknown support. A conditional span from
an incomplete record is not treated as a monotone lower bound. Native-metric
receipts identify guaranteed and possible leaders within their bound corpus,
not overall quality or global biological-information leaders. The source-review
protocol is documented; independent review of real submissions remains necessary.

Benchmark evolution should add explicitly versioned challenges without silently
changing old results. A fixed target may saturate, while harder targets introduce
new biological compartments, timescales, interventions, or external populations.
No finite present-day target is a universal denominator for all human biology.

### 5.1 Finite-task conditional precision

The implemented `anibench finite-task` runner evaluates a declared finite set of
linear functionals under a shared Gaussian model. For coefficients c, prior
precision P and likelihood information F, it computes c^T(P+F)^(-1)c and checks
a declared variance ceiling in squared output units. The frozen task binds the
population, estimand, horizon, parameter units, prior, functionals, required
acquisition roles and source/model identities. Receipts additionally bind the
evaluator, schemas and numerical runtime. They report prior-only attainment
and acquired variance reduction separately.

Required domain/role support is noncompensatory: a failed required neural
observation cannot be replaced by precise molecular measurements. An unknown
requirement remains unknown, and diagnostic observation does not establish
perturbation support. The planned-design lane does not require treatment success
or held-out predictive utility; the realized-record lane additionally requires
collection verification. These are caller-supported conditional evaluations,
not independent protocol audits. Passing the specified functionals establishes
neither all-direction covariance attainment nor an empirical learning plateau.
The mechanism is executable, but a biologically calibrated AniBench 1 or 2 task
registry is not supplied. See the [finite-task contract](../docs/FINITE_TASK_PRECISION_V1.md).

## 6. Reproducible results

### 6.1 A synthetic collected record

The shipped table example contains three roster members and two protein target
columns. Two participants have accepted observations. A pending follow-up for one
participant is retained in the audit but does not contribute accepted coverage.

| Quantity | Reproduced value | Population or meaning |
|---|---:|---|
| Declared roster | 3 | Includes the person with no accepted assay |
| People with accepted protein targets | 2 | Denominator 3 |
| Accepted participant-events | 3 | One module |
| Accepted target observations | 6 | Repeated targets count at distinct events |
| Median distinct proteins per person | 2 | Includes zero for the unmeasured person |
| People with at least two dated observations | 1 | Denominator 3 |
| Span among those repeat participants | 28 days | One-person conditional distribution |

These are deterministic bookkeeping results on synthetic data. They are not
estimates of clinical efficacy, independent protein information, or population
follow-up. Duplication, row order, zero-versus-missing values, unknown dates,
source-hash mismatch, conflicting linkage, and compact-encoding invariance are
covered by executable tests. Native-metric comparison tests additionally check
exact ties, incomplete evidence, touching interval boundaries, unreported
modules, incompatible definitions, and possible ranks against exhaustive
enumeration of small admissible integer-valued worlds.

### 6.2 Depth and duration can favor different designs

The bundled geometry demonstration compares two synthetic designs in a common
two-coordinate parameter space. The deeper design observes two independent
directions. The longer design observes one direction and stretches its complete
time geometry by a factor of four, preserving assignment and response-window
ordering. Both are evaluated through the canonical Python evaluator.

| Native quantity | Deeper design | Longer design |
|---|---:|---:|
| Intensive numerical rank | 2 | 1 |
| Maximum joint-bundle log10 contraction | 0.301030 | 0.150515 |
| Retained participant-events | 820 | 820 |
| Extensive log10 contraction | 2.645141 | 1.322571 |
| Participant-weighted median distinct offsets | 4 | 4 |
| Participant-weighted median span | 90 | 360 |

Span is in the fixture's declared protocol time units. The deeper design is on
the intensive front; the longer design is on the longitudinal front. Their
unchanged causal, personalization, and transport declarations do not manufacture
a tie-breaker. This illustrates multidimensional comparison under a shared
synthetic model, not a validated estimate of real-study biological information.

### 6.3 Real literature illustrates the denominator problem

The public explorer's mechanical source projections cover 16 study records
and 37 separately extracted publication/official-source facts. A further OMG
protocol card is described in Section 6.7. The projections include UK Biobank, the Snyder iPOP/iHMP
cohort, CIRCULATE therapeutic plasma exchange, and other observational and
interventional studies. Each displayed fact retains its source and definition.

For example, the pinned UK Biobank source packet separately describes an overall
cohort exceeding 500,000 people, a whole-genome sequencing population of 490,640,
and a proteomics resource with 54,219 participants and 2,923 unique proteins
[6–8]. These values do not imply that every cohort member received every assay.
The CIRCULATE record preserves publication enrollment, analyzed participants,
and the frozen registry population as distinct facts [9].

The atlas does not contain complete comparable information geometry for these
studies. Accordingly, it does not establish their six-family rankings. Exact
source replay verifies extraction and byte identity, not the original study's
experimental validity. Private study adapters can use the same public collection
code without adding participant records or unpublished findings to this atlas.

### 6.4 What repeated measurements add

A controlled Gaussian example uses a 16-coordinate target with unit prior
covariance and unit measurement noise. Measuring n different coordinates
provides n/2 bits. Measuring one coordinate n times with independent noise
provides log2(1+n)/2 bits. Copying the same realized measurement n times retains
1/2 bit. The observation counts can match while information and resolved
directions differ. Figure 1 derives these curves directly from the same target
and prior; Figure 2 reproduces the native geometry comparison in Section 6.2.
Neither figure uses clinical data or estimates a real study's information.

### 6.5 Marginal completion and all-direction posterior precision

Reference-basis marginal precision does not guarantee equal precision for every
linear combination. For trial and reference Gaussian posterior covariances
computed with the same prior and parameter space, the implementation adds the
conditional diagnostic

\[
r=\max_{c\ne0}\frac{c^T\Sigma_{trial}c}{c^T\Sigma_{reference}c}
=\lambda_{max}(\Sigma_{reference}^{-1/2}\Sigma_{trial}
\Sigma_{reference}^{-1/2}).
\]

The condition r<=1 is equivalent to the Loewner inequality
Sigma_trial<=Sigma_reference. The implementation reports the unrounded ratio and
uses a fixed 1e-10 numerical boundary tolerance. This is a model-conditional
reference comparison, not certified biological saturation. Historical
basis-marginal completion values are retained with explicit semantics, while
existing public completion and promotion gates remain closed.

A reproducible counterexample uses prior precision I, reference information I,
and trial posterior covariance [[0.5,0.49],[0.49,0.5]]. Both reference-basis
marginals equal 0.5, yielding 100% marginal completion. Variance along the unit
direction (1,1)/sqrt(2) is nevertheless 0.99 against reference variance 0.5.
The new diagnostic reports r=1.98 and rejects all-direction attainment.

An additional audit executes 225 distinct synthetic information matrices across
15 adversarial families through the information helpers and replay validator.
All 225 agree with their independent analytic or metamorphic mechanics checks
and retain the replay's restrictions on public claims. The cases cover small
populations with deep observations, large shallow populations, repeated and
correlated observations, missing directions, redundant contrasts, near-singular
positive-definite noise, units, nuisance uncertainty and the marginal/joint
precision distinction. All 15 joint-completion counterexamples fail the stronger
all-direction condition. In 15 copied-contribution cases the low-level additive
helper sums repeated inputs: acquisition-lineage deduplication is an upstream
precondition, not something this helper can infer from shared source labels.

This audit does not evaluate 225 real studies, the complete protocol compiler,
empirical learning or biological calibration. Cost and elapsed-duration examples
establish only that these metadata do not enter the low-level information
formula. The source-bound results and portable runner are
`data/synthetic_geometry_audit/actual_geometry_results.json` and
`scripts/audit_synthetic_geometry.py`. The finite-task proposal and illustrative
precision/power derivations are documented in `docs/LEVELS_AND_SATURATION.md`;
planned conditional capacity remains evaluable without demonstrated model utility.

### 6.6 Registry intake across 240 real studies

A separately frozen corpus contains 240 unique ClinicalTrials.gov records across
12 acquisition/design strata, with 20 records per stratum. The initial sparse
intake replay compiled 239 records and exposed one 257-character title that
exceeded the display-name contract. Source inspection also found an incorrect
outcome-array pointer. After preserving the full title in provenance while
bounding the display name, and counting the actual primary, secondary and other
outcome arrays, all 240 records compiled. The extracted count of listed outcome
entries was exact for 234 records and unknown for six. All 720 structural
mutation probes passed. Historical baseline and corrected receipts are retained.

This corpus evaluates registry parsing and conservative sparse compilation. It
does not contain a complete comparable biological information model for each
study and cannot establish study rankings, biological calibration or saturation.
The public manifest binds record identities, acquisition strata, retrieval times
and source hashes. The portable runner supports an external raw-source cache;
changed upstream bytes fail the frozen replay rather than silently replacing
its evidence. See `docs/REGISTRY_STRESS_240.md` for reproduction and sampling limits.

### 6.7 Source cards and planned protocol facts

The public explorer presents 17 source-backed cards: 16 mechanical source
projections and one separately represented protocol card for Oh My Gut!
(Wageningen; OMG). The latter is bound to a public participant-information
brochure, version 2, June 2025, rather than a fabricated registry accession or
an asserted latest investigator protocol. Planned quantities retain their
source status. Conflicting duration anchors remain visible instead of being
collapsed into a favorable scalar.

These cards expose reviewable collection and protocol facts; they do not supply
complete information geometry or establish a comparable ranking of 17 studies.
Numeric-excerpt replay checks source bytes and page text, while biological
interpretations remain curated claims requiring review. This small explorer
collection is also distinct from the registry-intake stress corpus in Section
6.6. See the [protocol-card evidence contract](../docs/PUBLIC_PROTOCOL_CARDS.md).

### 6.8 An empirical measurement example and conditional planning

A public [ERP calibration recipe and report](../examples/calibration/erp_core/REPORT.md)
uses existing derived summaries to examine within-session precision for a
specified P3b voltage contrast. The local runner checks pinned source hashes,
workbook mappings and independent aggregate controls, and exports aggregate
results with implementation provenance. The report distinguishes analytic
measurement variance from bootstrap SME and documents the finite-sample
resampling distinction. Its source-derived numerical results and figures remain
in that separately licensed package rather than being reproduced here.

The accompanying [design planner](../examples/calibration/erp_core/DESIGN_PLANNER.md)
searches a declared grid of people, visits and measurement depth under user-declared
precision ceilings. Current-session, persistent-person and population-mean
estimands have different error terms. Because the calibration cannot separate
persistent-person from session variation, every candidate must satisfy its
constraints using the same admissible variance decomposition. Favorable but
mutually inconsistent assumptions for separate tasks cannot establish joint
feasibility. The planner reports robust, assumption-sensitive, infeasible or
unresolved cases and componentwise resource frontiers within the supplied grid.

Here, robust means only robust to the retained decomposition at fixed estimated
variances. It does not cover calibration uncertainty, dependence misspecification
or population transfer. The example's ceilings are illustrative, depth scales
the source measurement schedule, and hypothetical visits are not observed
retests. Neither frontier certifies an optimal biological study or normative
AniBench attainment.

### 6.9 A source-supported temporal design comparison

The [CALERIE example](../examples/design_geometry/calerie/README.md) compares
two analysis designs using public collection counts from
[Waziry et al. (2023)](https://doi.org/10.1038/s43587-022-00357-y).
The reported change-analysis denominators are 125/66 participants in the
restriction/control arms at 12 months and 117/68 at 24 months, within a
197-person baseline-plus-follow-up population. Disjoint-arm constraints imply
179–183 people in both endpoint-analysis subsets under the conservative common
universe interpretation. If those subsets exactly cover the 197, their overlap
is 179. The code retains both interpretations explicitly.

For an illustrative common scalar with residual variance one and independent
annual errors, existing AniBench information APIs evaluate a two-year endpoint
change and midpoint curvature. Baseline plus 24-month data give endpoint-change
variance 0.046505782 and cannot identify curvature. Complete three-visit records
give endpoint-change variance 0.047397047–0.049352082 and curvature variance
0.035547786–0.037014061. These are conditional model predictions, not observed
clock uncertainty or treatment effects. The source does not estimate the
assumed covariance or establish retained-subset exchangeability.

The example illustrates why visit counts are insufficient: added temporal
support can identify another question, while selecting complete cases reduces
population support. Nine noise scenarios produce 144 bound evaluations, kept
separate by model; the support ranges are not confidence intervals. All feasible
arm supports must be included exactly once in each comparison envelope. The
replay, source manifest, numerical receipts and publication figure are runnable
from the public source package without participant data.

## 7. Validation and limitations

The implementation is tested for mathematical/representation invariants,
input validation, denominator preservation, deterministic receipts, and public
distribution boundaries. These tests establish specified software behavior.
They do not establish that a chosen biological target is sufficient or that a
capacity metric predicts useful future discoveries.

Empirical calibration should freeze the target, source revision, preprocessing,
and evaluation split before model selection. Hold out entire participants where
the claim concerns new people. For forecasting, prevent later observations and
post-event processing from entering training. Compare against meaningful
population, persistence, missingness, and wrong-person controls. Estimate
uncertainty with the appropriate participant or randomization unit. Report
negative and failed tasks rather than only favorable averages. Clinical
prediction reporting standards provide complementary guidance [10].

Several limits remain material. Source identities, units, and QC declarations
can be wrong. A participant roster may omit failures. Compositional coordinates
and assay-derived features can exaggerate apparent breadth. A Gaussian or local
information approximation can miss multimodality and nonlinear nonidentifiability.
Information priors and target registries can favor a sponsor's measurement choices.
Transport assumptions may fail outside observed support. Cluster and crossover
assignment require dependence structures that the current canonical evaluator
does not fully express; those unsupported families remain unresolved.

The finite-task runner does not validate a supplied prior, observation operator,
variance ceiling or support declaration. The empirical measurement example also
leaves repeat-session variation and independent operator validation unresolved.
Genuine repeated recordings with defensible linkage and independently specified
measurement rules are needed before a persistent-person/session decomposition can
be treated as calibrated. Diagnostic precision alone does not establish causal
perturbation coverage or a sufficient set of biological reconstruction tasks.

Raw data volume and compression ratio are not validated proxies for biological
information. Random noise can be difficult to compress; repeated measurements
can be highly compressible and scientifically useful. The motivating phrase
“information that can become intelligence” therefore requires explicit predictive,
dynamical, or causal tasks before it becomes a measured claim.

AniBench is developed by an organization that also conducts human studies.
This creates an incentive to favor its own study designs. Public methods,
versioned evidence, challengeable source records, and independent review are
necessary responses. They do not eliminate that conflict by themselves.

## 8. Reproducibility, access, and governance

The source package, schemas, examples, contribution process, and citation metadata
are available at [the AniBench repository](https://github.com/anibiome/anibench-benchmark).
Code uses Apache 2.0; documentation and curated data artifacts use their declared
CC BY 4.0 terms, except where an explicit file or REUSE declaration specifies
otherwise. The ERP source-derived reports, manifests, aggregate results and
figures use CC BY-SA 4.0; their original analysis code uses Apache 2.0. Primary
study sources retain their own rights and access rules.

Reproduce the collection example with:

```bash
anibench profile-tables examples/collection/table-map.json \
  --out build/collection-example.json --pretty
```

Reproduce the geometry demonstration and its exact input/receipt packet with:

```bash
python scripts/build_explorer.py --out build/explorer-paper-replay
```

The `explorer-demo.json` artifact contains both protocols, source objects,
canonical receipts, and the comparison. The existing
[technical protocol](v2/AniBench_v2_benchmark_protocol.md) documents the
versioned evaluator in more detail. Record the exact Git commit, dependencies,
source hashes, and command when reporting a result.

Build the manuscript PDF, figures and replay metadata with:

```bash
python -m pip install -e ".[paper]"
python scripts/build_manuscript.py --out output/pdf/AniBench_open_benchmark.pdf
```

Public code can compute against private data. The collection profiler emits
aggregate receipts by default and does not upload inputs. Participant-linked
intermediates are explicitly optional private outputs. Aggregation is not an
anonymization guarantee: labels, rare cells, and hashes can remain identifying.
Publication therefore requires a separate review of the actual output scope.

## 9. Conclusion

AniBench makes the object of evaluation explicit: the study's linked biological
record and the questions its design can support. Collection coverage, conditional
information, demonstrated learning, and treatment outcomes are related but
different objects. Preserving this distinction enables transparent, reproducible
comparisons without turning an assay menu or a favorable endpoint into a universal
quality score. The present release provides working collection and geometry
instruments and evidence-bounded native-metric comparisons. Biological
calibration and independent review remain necessary for stronger public claims.

## References

1. Alexanderian A. A brief note on the Bayesian D-optimality criterion.
   arXiv:2212.11466, version 3, 2023.
   <https://arxiv.org/abs/2212.11466v3>
2. Krause A, Singh A, Guestrin C. Near-optimal sensor placements in Gaussian
   processes: theory, efficient algorithms and empirical studies. JMLR.
   2008;9:235–284. <https://jmlr.org/papers/v9/krause08a.html>
3. Villaverde AF, Tsiantis N, Banga JR. Full observability and estimation of
   unknown inputs, states and parameters of nonlinear biological models.
   J R Soc Interface. 2019;16:20190043.
   <https://doi.org/10.1098/rsif.2019.0043>
4. Liang P, et al. Holistic evaluation of language models. TMLR. 2023.
   <https://arxiv.org/abs/2211.09110>
5. Westreich D, Edwards JK, Lesko CR, Stuart EA, Cole SR. Transportability of
   trial results using inverse odds of sampling weights. Am J Epidemiol.
   2017;186:1010–1014. <https://doi.org/10.1093/aje/kwx164>
6. Sudlow C, et al. UK Biobank: an open access resource for identifying the
   causes of a wide range of complex diseases of middle and old age. PLoS Med.
   2015;12:e1001779. <https://pmc.ncbi.nlm.nih.gov/articles/PMC4380465/>
7. UK Biobank Whole-Genome Sequencing Consortium. Whole-genome sequencing of
   490,640 UK Biobank participants. Nature. 2025;645:692-701.
   <https://doi.org/10.1038/s41586-025-09272-9>
8. Sun BB, et al. Plasma proteomic associations with genetics and health in the
   UK Biobank. Nature. 2023;622:329-338.
   <https://doi.org/10.1038/s41586-023-06592-6>
9. Fuentealba M, Kiprov D, Schneider K, et al. Multi-Omics Analysis Reveals
   Biomarkers That Contribute to Biological Age Rejuvenation in Response to
   Single-Blinded Randomized Placebo-Controlled Therapeutic Plasma Exchange.
   Aging Cell. 2025;24:e70103. <https://doi.org/10.1111/acel.70103>
10. Collins GS, et al. TRIPOD+AI statement: updated guidance for reporting
    clinical prediction models that use regression or machine learning methods.
    BMJ. 2024;385:e078378. <https://doi.org/10.1136/bmj-2023-078378>
