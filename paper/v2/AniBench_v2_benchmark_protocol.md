# AniBench v2: an information-geometric benchmark and design system for human trials

**Article type:** methods, benchmark specification, and validation protocol

**Software version:** AniBench 2.0 release candidate

**Level-1 authority:** role-aware v3 candidate; v2 target semantics quarantined

**Manuscript status:** submission candidate; not submitted and not peer reviewed

**Authors:** `[AUTHOR LIST AND ORDER REQUIRE CONTRIBUTOR CONFIRMATION]`

**Affiliations:** `[AFFILIATIONS REQUIRE AUTHOR CONFIRMATION]`

**Corresponding author:** `[CORRESPONDING AUTHOR AND CONTACT REQUIRE CONFIRMATION]`

**Biological validation state:** prospective validation plan specified; not yet
deposited in an immutable public registry and not yet executed

Empirical validation state: `not_run`

Trial-ranking results: absent

Public source release: published at
`https://github.com/anibiome/anibench-benchmark`; the exact evaluated commit is
recorded in the release/readback receipt rather than recursively embedded here

Stable tag, package-index release, archive DOI, and public ranking: absent

**Public trial ranking state:** withheld until reference, source, calibration, and
independent-review gates are complete

## Abstract

Trials are normally compared by endpoint power, participant count, duration,
or assay inventory, although none alone determines how much a study can teach a
future biological model about human state, change, intervention response,
individual variation, function, and population transfer. AniBench is designed
for open release as a benchmark and prospective trial-design system that represents a study as
source-bound participant-event geometry. It separates six non-interchangeable
families: intensive biological resolution, extensive reconstruction capacity,
longitudinal resolution, causal architecture, personalized and sequential learning,
and population transport. It emits no hidden overall trial score.

Observation operators, nuisance-aware covariances, and retained support form
event-level information contributions. Participant-event hyperedges prevent
unlinked assays from appearing joint; ancestry and covariance prevent duplicates and
autocorrelated records from manufacturing independent directions. Target information,
when a family authority resolves it, is nuisance conditioned and prior whitened.
Direction-capped family attainment prevents surplus depth from purchasing missing
directions without implying that a current Level-1 percentage exists.
Separate policy, component, sequential, and transport structural-support operators
prevent arm counts or personalization labels from substituting for identified
experimental contrasts.

The same capacity mathematics applies to planned and executed protocols, while
evidence lanes keep their claims distinct. Numeric coordinates preserve exact,
interval, and conditional states; selected authority objects preserve unknown or
absent states as nonnumeric blockers. A protocol-native optimizer recompiles every
permitted design mutation and returns a Pareto set under explicit resources. We
specify the Level-1 construction, source corpus, anti-gaming invariants, prospective
validation tasks, and promotion gates. Software and test receipts establish only
replayable implementation evidence. Held-out biological utility, immutable
preregistration, and public ranking remain separate validation and release gates.

## 1. Research question

AniBench asks:

> If a human study were the biological record available to a future
> superintelligence, how much of human state, change, intervention response,
> individual variation, function, and population transfer could it reconstruct?

In this question, reconstruct means recover a usable model of latent biological
state and trajectory, estimate intervention-response operators, resolve
person-by-context heterogeneity, and transport those relations to new people and
settings. It does not mean prediction of one endpoint from a large but biologically
shallow table.

The evaluated object is the experiment and the resulting data, not the prestige of
the sponsor, journal, institution, intervention, or analysis team. Proposed,
registered, ongoing, completed, and published human studies are eligible, but their
claims remain in separate evidence lanes. Animal-only, organoid-only, cell-line-only,
and purely synthetic experiments are outside the primary corpus.

The aim is not a universal scalar called trial quality. The aim is a reproducible map
of which biological directions an experiment resolves, which intervention operators
it identifies, how those constraints accumulate over people and time, how they
transfer, and which protocol change would add the most new information under an
explicit budget.

Figure 1 summarizes the specified compilation chain from source objects to records
for each family and auditable design changes. The benchmark question is future-facing;
every
present-tense implementation or empirical statement in this article remains bounded
to the evidence class stated in Sections 17 and 20.

![Figure 1. AniBench source-bound compilation. Source bytes, participant-event
identity, operator geometry, family outputs, and design-change receipts form one
auditable chain. No trial score or empirical result is shown.](figures/figure_01_source_bound_pipeline.png)

## 2. Design requirements

AniBench is governed by ten requirements.

1. **Biological directions precede modality menus.** A modality name is not an
   information direction. Observation operators and covariance determine what is
   resolved.
2. **Intensive and extensive quantities remain separate.** More participants cannot
   buy missing per-event biological depth; deeper events do not substitute for
   population scale.
3. **Jointness is explicit.** Measurements are combined only when a source binds them
   to the same participant-event intersection.
4. **Redundancy saturates.** Shared ancestry and covariance remove duplicate or
   highly correlated contribution.
5. **Experimental contrasts are derived.** Policy, component, sequential, and
   transport ranks are computed from assignment geometry, not labels or arm counts.
6. **Longitudinal evidence is within person.** Disjoint cross-sections cannot create
   follow-up.
7. **Unknown is not zero.** Exact, interval, conditional, unknown, and absent facts
   retain their types.
8. **Evidence status does not change design capacity.** Planned and realized versions
   of identical geometry receive identical capacity calculations; the evidence lane
   changes the authorized claim.
9. **Reference levels are independent engineering targets.** Current or desired
   trial ordering cannot enter authority construction.
10. **Implementation, calibration, and release are distinct gates.** Passing schemas
    and unit tests does not prove biological validity or authorize public ranks.

These requirements adapt transparent, multidimensional benchmark governance from
HELM and MLPerf while changing the evaluated object from a computational model to a
human experiment [11,12]. They also adopt the measurement discipline of declaring
the evaluation objective and construct before evaluation, separating implementation
from analysis, quantifying uncertainty, and qualifying claims [15]. Statistical
benchmark guidance further motivates an explicit distinction between a result on one
frozen corpus and a generalization claim beyond that corpus [16]. Neither source
validates AniBench's biological ontology, formulas, or target levels.

Clinical-trial guidance adds complementary constraints: estimands and sensitivity
analyses must be specified rather than inferred after observation [4], adaptive
design decisions require explicit operating characteristics [5], and protocol and
result reporting must expose the design, analysis, and deviations needed for
independent interpretation [6,7]. AniBench uses these as reporting and governance
lineage, not as endorsement of its benchmark coordinates.

## 3. Six benchmark families

### 3.1 Intensive biological resolution

Intensive resolution describes what one explicitly joint participant-state event can
resolve. The primary objects are the rank, spectrum, posterior-volume contraction,
and coordinate coverage of the strongest declared joint-observation bundle. Total
participant count does not enter this family. Incompatible bundles are never unioned.

### 3.2 Extensive reconstruction capacity

Extensive capacity aggregates valid information across retained participants and
events. It reports effective participant-event support, information rank, and total
posterior-volume contraction. It therefore distinguishes a deeply measured small
study from a similarly deep, much larger experiment without claiming that either is
globally better.

### 3.3 Longitudinal resolution

Longitudinal resolution is computed inside participant sets. It reports retained
participant-events, linked participant support, distinct within-person offsets, and
within-person span. Participant-weighted medians are primary summaries; maxima remain
audits so a tiny long-followed subset cannot dominate the study summary.

### 3.4 Causal architecture

Causal architecture reports whole-policy and component contrast rank together with
allocation-support factors. Those factors are structural design proxies and are not
inferential precision.
A bundled multi-component intervention may identify one whole-policy contrast while
leaving its components unidentified. Factorial, SMART, and micro-randomized designs
may identify additional operator directions when the source geometry supports them.
The current compiler treats cluster-randomized and crossover labels as insufficient:
both fail closed until their cluster, period, sequence, carryover, and covariance
dependence geometry is registered rather than inferred from the design name. The
eval represents this state with null native metrics and an explicit blocker code,
never with numerical zero capacity.

Repeated randomization in micro-randomized trials can identify proximal component
effects and time-varying moderation when the trial records eligible decisions,
propensities, pre-decision history, and linked outcomes [17,18]. Sample-size theory
for binary proximal outcomes further shows that decision cadence, randomization
probability, effect model, and working assumptions matter at design time [19]. SMART
methods can exploit compatible embedded-regime data through explicit models rather
than treating a design label or arm count as information [20]. These sources motivate
the declared geometry and moderator gates; they do not validate AniBench's specific
matrix summaries or Level-1 targets.

The sample-size implication is estimand specific. A SMART powered for comparison of
embedded dynamic treatment regimens requires the corresponding longitudinal outcome
and working-assumption authority [21]. A micro-randomized trial powered for a proximal
main effect requires its decision schedule, availability, randomization probabilities,
effect model, and within-person dependence assumptions [22]. Neither design name has
a universal participant multiplier.

### 3.5 Personalized and sequential learning

The target construct for personalized learning requires prospectively measured
pre-decision state, eligible repeated randomized decisions, non-degenerate known
propensities, a declared decision rule that actually uses measured state, and linked
later biology or outcomes. A retrospective subgroup analysis, a fixed rule that
ignores measured state, or a clinician-discretion label does not satisfy that
construct.

The release-candidate compiler requires either an explicit decision-epoch ledger or
a registered regular decision-epoch process with one fully bound template. Every
explicit epoch, and the template inherited by every regular-process occurrence,
binds availability, canonical policy propensities, pre-decision history features and
schedules, and one or more unique post-decision observations to a frozen proximal
estimand. A regular process additionally freezes its count, start, interval, daily
cadence, duration, readback lag, source object, and stationary moderator covariance;
the compiler uses the declared multiplicity analytically rather than materializing
thousands of repeated JSON rows. The compact and explicitly expanded forms must
produce equivalent support geometry. Each estimand freezes its outcome definition
and features, policy contrast, and horizon. The compiler caps eligible outcome
support by stage availability and retained linked-outcome support, then caps moderator
support again by retained pre-decision history support. A registered population
moderator covariance is required for every epoch that contributes moderator support
geometry.

Personalized-policy credit is stricter than heterogeneous-response credit. The
personalized gate requires repeated SMART or micro-randomized epochs and a registered,
nonzero state-to-policy contrast operator whose state features are measured before
each eligible decision. The heterogeneous-response gate may use randomized
estimand-contrast-by-moderator-covariance geometry without asserting that a
state-dependent policy was deployed. For SMART designs, registered paths must cover
the complete chronological epoch ledger; their policies must have positive epoch
support, response states must be rule features measured in the next epoch's history,
and path-probability marginals must reproduce the registered epoch propensities.
These are prospective structural-rank and allocation-support coordinates, not fitted
treatment effects, empirical moderation surfaces, biological-information estimates,
or proof that a learned policy improves outcomes.

### 3.6 Population transport

The release-candidate transport coordinate requires common numeric context axes,
positive randomized allocation, distinct participant-set identifiers, active
post-assignment outcome schedules, retained linked support, and direct binding to the
same frozen outcome/operator/horizon estimand in every context. A registered
crosswalk is preserved as provenance but remains numerically unresolved until an
executable mapping operator and its uncertainty attenuation are authority-bound. The
resulting matrix is prospective, allocation-aware context-contrast geometry. It is
not an estimate of transported treatment effects, a proof of causal
transportability, or evidence that a fitted model generalizes to a held-out
population. This distinction follows the broader requirement to define the target
population, conditional transportability assumptions, and positivity explicitly
[8,23]. The number of sites, countries, or demographic labels alone does not create
transport rank.

Uncertainty and reuse are cross-cutting layers rather than extra points. Every family
has a scenario envelope, source-binding state, evidence lane, and reproducibility
receipt. Comparisons are family specific or Pareto based; `overall_scalar` is null.

Figure 2 makes the non-substitution rule explicit. A protocol can be unusually deep
at one participant-state event, broad across people, longitudinally dense, causally
identifying, sequentially personalized, transportable, or several of these at once.
The benchmark reports those relations rather than hiding them in a weighted total.

![Figure 2. Six non-interchangeable benchmark families. Uncertainty, source binding,
evidence lane, and reproducibility apply across every family; no central scalar is
computed.](figures/figure_02_six_family_map.png)

## 4. Biological state and operator space

For participant $i$, latent biological state $z_{it}$, context $c_{it}$,
intervention decision $u_{it}$, and measurement module $m$, the working local
model is

$$
z_{i,t+1}=f_\theta(z_{it},u_{it},c_{it})+w_{it},
\qquad
x^{(m)}_{it}=h^{(m)}_\theta(z_{it})+v^{(m)}_{it}.
$$

Level 1 freezes a mesoscopic target vector

$$
\theta=(\theta_S,\theta_D,\theta_P,\theta_H,\theta_F,\theta_T),
$$

with blocks for biological state, endogenous dynamics, perturbation response,
person-context heterogeneity, functional or lived state, and population transport.
Nuisance blocks include batch, site, measurement error, missingness, dropout,
adherence, exposure ascertainment, clustering, and temporal autocorrelation.

The six blocks are a scientific map, not sixty-four interchangeable assay outcomes.
The role-aware authority partitions every coordinate exactly once: twenty-two
coordinates are eligible direct mutable outcomes; `S01` is a baseline modifier;
`S09` is an exposure/context coordinate; and the `D`, `P`, `H`, and `T` blocks are
relational estimands. They are learned from appropriately linked observations,
assignments, trajectories, people, and populations; they are not measured again as
raw outcomes, moderators, or context strata. Section 9 defines the complete role
partition and its operating-characteristic gates.

The coordinate registry is finite and versioned. It is not a claim that Level 1
contains all human biology. Later levels may add spatial, temporal, molecular,
tissue, environmental, functional, and intervention resolution without changing the
meaning of a frozen earlier level.

## 5. Participant-event information

### 5.1 Event hyperedges

Each valid information event is a typed hyperedge binding participant set, biological
time or window, physical measurement ancestry, joint-observation bundle, intervention
or exposure lineage, target coordinates, nuisance coordinates, evidence state, and
source object. Pairwise linkage does not imply an undeclared higher-order
intersection.

For event type $e$,

$$
\mathcal I_e=n_eA_e^\mathsf{T}R_e^{-1}A_e,
\qquad
\mathcal I_{\mathrm{trial}}=\sum_{e\in\mathcal E}\mathcal I_e.
$$

The operator $A_e$ describes local sensitivity to the frozen parameter basis;
$R_e$ is a positive-definite nuisance-aware covariance; and $n_e$ is retained
effective support. One physical measurement lineage contributes at most once to one
joint event. Perfect duplicates add zero conditional information. Correlated repeats
use a joint covariance or a declared conservative envelope rather than independent
summation.

Figure 3 illustrates the same-event rule. The rule permits independent layers on the
same participant-event support to combine through a joint covariance model while
preventing bundle splitting, conflicting lineage reuse, and duplicate physical
ancestry from manufacturing extra support.

![Figure 3. Same-event identity and anti-gaming. Compatible layers can contribute
conditional information inside one canonical event; aliases, conflicts, and split
bundles fail closed.](figures/figure_03_same_event_antigaming.png)

### 5.2 Nuisance adjustment

Partition the information matrix into target parameters $\theta$ and nuisance
parameters $\eta$:

$$
\mathcal I=
\begin{bmatrix}
\mathcal I_{\theta\theta} & \mathcal I_{\theta\eta}\\
\mathcal I_{\eta\theta} & \mathcal I_{\eta\eta}
\end{bmatrix}.
$$

With nuisance prior precision $\Lambda_\eta$, conditional target information is

$$
\mathcal I_{\theta\mid\eta}=
\mathcal I_{\theta\theta}-
\mathcal I_{\theta\eta}
(\Lambda_\eta+\mathcal I_{\eta\eta})^{-1}
\mathcal I_{\eta\theta}.
$$

This discounts batch, site, missingness, or ascertainment directions that are
explicitly included in a correctly specified joint model. Omitted or misspecified
nuisance structure remains a release falsifier and must be tested by sensitivity
analysis; the Schur complement cannot protect against structure the model never binds.

### 5.3 Prior whitening and absolute contraction

For frozen positive-definite prior precision $\Lambda_0$, define

$$
G=\Lambda_0^{-1/2}\mathcal I_{\theta\mid\eta}\Lambda_0^{-1/2}.
$$

The base-10 local posterior-volume contraction is

$$
L_{\mathrm{abs}}
=\frac{1}{2\ln 10}\log\det(I+G)
=\frac{1}{2\ln 10}\sum_j\log(1+\lambda_j(G)).
$$

Independent directions multiply remaining-volume reduction; repeated information in
an already precise direction has diminishing marginal value. This is a local
Gaussian design quantity in the Fisher-information and Bayesian experimental-design
lineage [1-3]. It is not an empirical model score or a literal count of biological
hypotheses.

### 5.4 Direction-capped family-reference attainment

An eigenvalue list alone does not preserve *which* biological directions are
resolved: a rotated rank-one operator can have an impressive eigenvalue while leaving
most registered coordinates uncertain. A resolved family authority would therefore
evaluate reference attainment in a frozen prior-whitened direction basis $b_j$. The basis matrix is
required to be column-orthonormal and to diagonalize the frozen prior-whitened
reference information. Biological coordinate identity independently freezes the
canonical basis. Diagonalization validates that authority but does not identify a
unique eigenbasis when reference eigenvalues repeat; arbitrary rotations inside a
degenerate eigenspace remain mathematically possible without that external basis
authority.

Let

$$
\Sigma=(I+G)^{-1},
\qquad
q_j=b_j^\mathsf{T}\Sigma b_j,
\qquad
\ell_j^{\mathrm{eff}}=q_j^{-1}-1.
$$

If a future family-specific operating-characteristic authority freezes a reference
requirement $\ell_j^*$, direction-capped family attainment can be defined as

$$
Y_f=100\frac{\sum_j
\min\{\log(1+\ell_j^{\mathrm{eff}}),\log(1+\ell_j^*)\}}
{\sum_j\log(1+\ell_j^*)}.
$$

Uncapped overflow can be reported separately:

$$
O_f=\frac{\sum_j\log(1+\ell_j^{\mathrm{eff}})}
{\sum_j\log(1+\ell_j^*)}.
$$

These would be paired outputs for the same frozen family direction set. An unresolved
authority object remains typed null rather than being converted to zero. The
role-aware Level-1 candidate intentionally supplies no current $\ell_j^*$, no
family percentage, and no target-attainment claim: every family operating
characteristic is unresolved pending source-bound authority.

When activated by a resolved family authority, the direction-wise cap prevents
surplus depth in one direction from filling an unobserved direction. A coverage curve
can report the fraction of reference weight reaching declared fractions of its
family target. Direction basis, target vector, prior scenario, formula version, and
source authority must be content hashed.

For a future resolved family authority, a coordinate target may be expressed as a
posterior standard-deviation ratio $r_j$ in a frozen prior-whitened basis. The
corresponding target information would be

$$
\ell_j^*=r_j^{-2}-1.
$$

For prior precision $\Lambda_0$, the abstract target rows are constructed as

$$
A^*=\operatorname{diag}(\sqrt{\ell^*})\,\Lambda_0^{1/2}.
$$

This is a candidate normalization construction, not an assertion that a named assay
attains those rows and not a current Level-1 value. Any activated family authority
must freeze its prior and covariance scenario before projection; an evaluated
scenario cannot redefine its own denominator. Repeated reference eigenvalues do not
create a biologically identified basis: coordinate identity must come from the
external canonical biological authority, while diagonalization serves only as a
compatibility check.

## 6. Per-event, total, and longitudinal construction

For each joint-observation bundle, AniBench assembles per-bundle information without
the participant multiplier. The intensive family selects the bundle with the largest
contraction, with rank and stable bundle identifier as deterministic tie breakers.
This represents a maximum resolved participant-state event, not the union of
incompatible subsets.

Participant-event schedules carry explicit lineage identifiers. Exact semantic
duplicates collapse to one schedule, while reuse of one lineage identifier with
conflicting participant, module, feature, offset, retention, or correlation geometry
is rejected. Different measurement layers on the same canonical participant-event
support must occupy one joint bundle: their information can combine, but their
longitudinal participant-event denominator is counted once. Splitting that support
across bundles fails closed. The current compiler accepts exact offsets only. A `rate_process`
declaration fails closed until a registered observation window, rate unit, and event
count model can convert the process to auditable participant-events.

Extensive information multiplies a bundle by

$$
n_e^{\mathrm{eff}}=N_er_e
\frac{k_e}{1+(k_e-1)\rho_e},
$$

where $N_e$ is participant support, $r_e$ is retention, $k_e$ is repeated
events per participant, and $\rho_e$ is the declared within-person repetition
correlation. Raw event support $N_er_ek_e$ is also retained for audit. The
correlation adjustment is a scenario parameter until event-specific covariance is
measured.

When several bundles are registered as nested retained subsets of the same
participant-set lineage, AniBench does not enumerate bundle subsets. Let $s_e$ be
retained participant support, $t_h$ the distinct supports in descending order,
$\Delta s_h=t_h-t_{h+1}$, and $E_h=\{e:s_e\ge t_h\}$. For bundle event count
$k_e$, per-event information $I_e$, canonical positive-semidefinite root
$B_e=I_e^{1/2}$, and frozen compound-symmetric envelope
$0\le\rho_g<1$, define

$$
K_h=\sum_{e\in E_h}k_e,\qquad
Q_h=\sum_{e\in E_h}k_eI_e,\qquad
S_h=\sum_{e\in E_h}k_eB_e,
$$

$$
J_h=
\frac{Q_h-
\frac{\rho_g}{1+(K_h-1)\rho_g}S_h^\mathsf{T}S_h}
{1-\rho_g},
\qquad
I_{\mathrm{set}}=\sum_h\Delta s_hJ_h.
$$

For $\rho_g=0$, $J_h=Q_h$. This is the exact registered-nesting result under
the declared compound-symmetric model and runs in
$O(B\log B+Bd^2)$, rather than an exponential subset or Pareto-frontier search.
If cross-bundle overlap is not source-resolved as nested, the compiler requires an
explicit source-bound primary bundle or keeps the alternatives ledger-only. Matrices
from different participant sets are summed only under explicit exact-disjointness
authority.

Longitudinal trajectories are assembled only inside the same participant-set
lineage. For trajectory $g$, AniBench records distinct offsets $d_g$, span
$s_g$, retained participant support $w_g$, and retained participant-events.
Primary study summaries are weighted medians

$$
\widetilde d=\operatorname{wmed}\{(d_g,w_g)\},
\qquad
\widetilde s=\operatorname{wmed}\{(s_g,w_g)\}.
$$

Maximum duration and global calendar coverage remain explicit audits and are never
relabeled as within-person follow-up.

## 7. Causal, sequential, and transport geometry

### 7.1 Policy and component allocation support

For contrast-coded design matrix $X_k$ and registered allocation-linked support
weighting $W_k$,

$$
\mathcal S_k=X_k^\mathsf{T}W_kX_k,
\qquad k\in\{\mathrm{policy},\mathrm{component}\}.
$$

Columns are centered under the declared allocation and normalized to an invariant
contrast range. Translation or arbitrary contrast-code rescaling therefore cannot
inflate structural support. Policy and component ranks and support spectra remain
separate. The geometric mean of each nonzero support spectrum is emitted as an
allocation-support factor. It is not biological information or inferential
precision: outcome residual covariance, observation-operator uncertainty, temporal
dependence, effect magnitude, and estimator performance are not included.

Causal summaries are formed from one coherent randomized stage or one explicitly
registered stage set. An unbound stage remains a singleton alternative and is never
added to another stage. The sole supported aggregation rule sums complete policy,
component, and moderator support matrices across stages whose participant-set IDs are
declared mutually disjoint and whose assignment mechanism, policy allocation,
outcome geometry, moderator geometry, decision rule, and SMART semantics are identical.
One stage cannot appear in two registered sets. Heterogeneous stage kinds remain
separate frontier members. The compiler selects one frontier member by a frozen
lexicographic rule and never constructs a synthetic best case by taking rank from one
member, allocation support from another, and participant support from a third.
Factorial, SMART, and micro-randomized designs are protocol geometries, not universal
Level-1 components; each must be judged against the estimand and operating
characteristics it is designed to identify. Declared assignment counts are capped by
retained, active-observer outcome support, and eligible decisions are capped by linked
retained participant-events. An explicitly inactive observer contributes zero
eligible support. An observer of unknown state leaves the affected result unresolved
with blocker provenance; unknown is never silently treated as inactive.

### 7.2 Decision-epoch sequential allocation support

For decision epoch $e$, let $p_e(a)>0$ be the registered propensity for policy
$a$, and let $c_{ek}$ be frozen estimand contrast $k$ over the supported
policies. The eligible linked-outcome and moderator supports are

$$
n_{e}^{Y}=\min\{N_s q_e,\,n_{e,\mathrm{retained}}^{Y}\},
\qquad
n_{e}^{M}=\min\{n_e^Y,\,n_{e,\mathrm{retained}}^{M}\},
$$

where $N_s$ is stage enrollment, $q_e$ is epoch availability, linked outcomes
must fall within the frozen estimand horizon, and moderator features must be measured
in the pre-decision history. For a longitudinal schedule that also contains future
events, the compiler slices the schedule at the decision time and receipts the count
of strictly pre-decision offsets; future rows are never used as history. The contrast allocation-support term and
moderator-supported allocation term are

$$
\omega_{ek}=
\left\{\sum_a\frac{c_{ek,a}^{2}}{n_e^Yp_e(a)}\right\}^{-1},
\qquad
\widetilde\omega_{ek}=\omega_{ek}\frac{n_e^M}{n_e^Y}.
$$

Both support terms are defined as zero when $n_e^Y=0$; an epoch with no eligible
linked-outcome support therefore cannot create structural support through an undefined
division.

Let $Z$ be the canonical policy-by-component incidence matrix and
$g_{ek}=c_{ek}^{\mathsf T}Z$. With the source-bound population covariance
$\Sigma_{M,e}$ embedded in a frozen moderator basis, the candidate compiler's
treatment-by-moderator support operator is

$$
J_e=\sum_k\widetilde\omega_{ek}g_{ek}g_{ek}^{\mathsf T},
\qquad
\mathcal S_{\mathrm{seq},s}=
\begin{cases}
\displaystyle\bigoplus_e\left(J_e\otimes\Sigma_{M,e}\right),
& \text{SMART epoch-specific estimands},\\
\displaystyle\sum_e J_e\otimes\Sigma_{M,e},
& \text{pooled micro-randomized estimand}.
\end{cases}
$$

Semantic duplicate contrasts within an epoch are removed before summation. Rank and
the moderator allocation-support factor are computed from the resulting spectral
support operator with a scale-aware tolerance receipt. A personalized summary selects
one eligible coherent frontier member and never mixes rank, allocation support, or
covariance across members. A registered disjoint-participant stage set adds the full
aligned support operators, not per-metric maxima. The SMART direct sum preserves
separately registered epoch-specific estimands rather than collapsing them into one
time-agnostic direction. Micro-randomized decisions pool repeated realizations of one
proximal estimand. A registered stationary regular process compiles one
multiplicity-weighted template block that is exactly equivalent to its explicit
decision grid, so changing representations or renaming the template does not
manufacture rank. The
heterogeneous-response gate requires randomized linked contrasts and nonzero
treatment-by-population-moderator support geometry. The personalized-policy gate
additionally requires repeated SMART or micro-randomized epochs and a registered
nonzero state-to-policy contrast operator whose state is measured pre-decision.
Neither gate estimates a moderation effect or demonstrates policy utility.

### 7.3 Population transport

Transport geometry contains distinct participant sets, positive randomized
allocation, active outcome schedules strictly after assignment, and direct binding
to one frozen outcome/operator/horizon estimand. Every transport-axis family binds
that estimand, an ordered set of required context axes, and a registered
coordinate-scale authority with source hash and locator. A context is projected onto
exactly those required axes. Extra declared coordinates are ignored numerically and
retained in the audit ledger; a missing required axis makes that context ineligible
for that family rather than changing the family definition. For estimand contrast
$k$ in context $c$, eligible support is capped by retained linked-outcome support
and the allocation-aware support term is

$$
\omega_{ck}=\left\{\sum_a
\frac{c_{k,a}^{2}}{N_c^{\mathrm{eligible}}p_c(a)}\right\}^{-1},
\qquad w_c=\min_k\omega_{ck}.
$$

For each family independently, the compiler centers and range-normalizes only its
required coordinates and calculates the weighted context-support matrix using
$w_c$. Mutually exclusive alternatives over one participant population are
resolved by the exact Cartesian/Loewner frontier before distinct-population contexts
are combined. Ranks use the same scale-aware spectral receipt as the other causal
families. With one axis family the top-level transport fields are explicit aliases;
with multiple families they are null and the noncompensatory family vector is the
only result. No family is winner-selected to stand in for another. A provenance-only
registered crosswalk remains unresolved for numeric credit in this release
candidate. This is a prospective design coordinate: it does not estimate a
transported effect or establish generalization to an unseen population. The emitted
transport allocation-support factor excludes outcome residual covariance,
observation-operator uncertainty, temporal dependence, effect magnitude, and
estimator performance; it is not biological information or inferential precision.
Site or country count is an audit variable, not a substitute for measured support.

## 8. Typed uncertainty and evidence lanes

### 8.1 Coordinate and authority states

The current generic nonnegative coordinate contract has three numerical forms:

- `exact(value)`;
- `interval(lower, upper[, nominal])`; or
- `conditional(scenario_group, scenarios)`.

Unknown or absent geometry is not encoded as a fabricated numeric coordinate. It is
preserved in the specific authority object that is missing: for example joint
covariance authority, population moderator geometry, an estimand binding, or a
signal/module evidence state. Those objects carry a typed state, reason, source hash,
and locator; affected family outputs are null or unresolved rather than zero. A
conditional coordinate is not promoted to fact. Scenario envelopes are computed by
recompiling the complete protocol under the Cartesian product of compatible declared
scenarios, and the scenario contract is included in the receipt.

### 8.2 Evidence lanes

| Lane | Authorized object | Claim meaning |
|---|---|---|
| Design Preview | author-declared protocol geometry | capacity conditional on executing that geometry |
| Registered Protocol | content-hashed protocol and registry sources | capacity of the frozen promised design |
| Realized | retained participants, events, assignments, linkage, and QC | information actually acquired |
| Accessible | realized data executable through lawful download or verified compute-to-data | information another evaluator can compute |
| Demonstrated | held-out task, calibration, null, and transfer receipts | observed model-learning utility |

The same geometry produces the same design-capacity result in the first two lanes.
Evidence state affects authority, uncertainty, and claim permissions, never by adding
a secret maturity penalty. Contradictions in realized conduct supersede protocol
promises for realized outputs.

Figure 4 separates the capacity of a declared design from later evidence objects.
This prevents the two opposite errors that motivated the evidence lanes: numerically
punishing an ambitious planned trial merely because it has not started, and granting
that same plan realized, accessible, or demonstrated status before the corresponding
receipt exists.

![Figure 4. Evidence lanes. Identical planned geometry receives identical design
capacity, while realized acquisition, executable access, and demonstrated held-out
utility remain separately receipted claims.](figures/figure_04_evidence_lanes.png)

## 9. Level-1 authority

Level 1 is a finite mesoscopic engineering authority. Its construction consumes only
the frozen coordinate registry, role semantics, family questions, and explicit
source-bound closure gates. Study or sponsor identity, current leaders, desired
ordering, assay-menu size, and any named trial's geometry are forbidden inputs. The
firewall is semantic and field based; it does not depend on a denylist of study names.

### 9.1 One scientific map, seven estimation roles

The role-aware authority preserves the ordered six-block, 64-coordinate scientific
map while partitioning every coordinate into exactly one of seven disjoint estimation
roles.

| Estimation role | Coordinates | Count | Permitted meaning |
|---|---|---:|---|
| Direct mutable outcome basis | `S02-S08`, `S10-S16`, `F01-F08` | 22 | Event-level latent state or function direction after an observation operator, scale, reliability model, and event linkage are verified |
| Baseline modifier | `S01` | 1 | Stable pre-assignment modifier; not a mutable outcome |
| Exposure/context | `S09` | 1 | Time-indexed exposure or context; not a transport estimand |
| Longitudinal state-space estimand | `D01-D12` | 12 | Relation derived from repeated direct outcomes under an explicit transition, observation, noise, and time model |
| Causal-response estimand | `P01-P12` | 12 | Counterfactual or randomized response relation over direct outcomes and intervention operators |
| Heterogeneity operating characteristic | `H01-H08` | 8 | Variation, calibration, or decision-rule performance across persons or contexts |
| Transport estimand | `T01-T08` | 8 | Source-to-target population relation under an explicit joint-context-support authority |

The partition sums to 64 and has no overlap. Coordinate presence does not prove that
the coordinate was observed. `D`, `P`, `H`, and `T` coordinates cannot be coerced
into direct event outcomes, raw moderators, or raw context strata; `S01` cannot be
coerced into a mutable outcome; and `S09` cannot be relabeled as a transport
estimand. Raw site, geography, age, sex, ancestry, socioeconomic, baseline-health,
comorbidity, medication, environment, and access variables live in source-specific
context registries outside the 64-coordinate map. Naming any such variable does not
manufacture a `T` estimand.

This division is biologically consequential. A molecular or functional observer can
inform the direct mutable outcome basis through a verified observation operator.
Longitudinal dynamics then require repeated linked direct outcomes; perturbation
response additionally requires assignment or another valid identification authority;
heterogeneity requires pre-assignment modifier support and held-person calibration;
and transport requires a defined target population, sampling/selection mechanism,
joint covariate support, positivity diagnostics, and source-to-target assumptions.
The map is therefore a dependency graph of biological questions, not a menu whose
entries may be multiplied together as independent powered endpoints.

### 9.2 Six family-specific operating-characteristic authorities

The authority emits an ordered six-family vector. Each family has its own estimand,
unit, design assumptions, operating characteristics, and enrollment derivation.
Every entry is currently typed `unknown` with a named blocker; no family substitutes
for or compensates another.

| Family | Target role | Required operating-characteristic closure |
|---|---|---|
| Intensive | direct mutable outcome basis | within-event information definition, observation-operator and covariance authority, repeatability and calibration |
| Extensive | direct outcomes plus baseline and exposure support | eligible coverage rule, cross-coordinate redundancy authority, source-bound identifiability |
| Longitudinal | `D01-D12` | transition and observation models, process and measurement noise, time-grid authority, held-time or held-person validation |
| Causal | `P01-P12` | counterfactual estimands, assignment or identification authority, intervention operators, multiplicity, attrition, interference, and adherence models |
| Personalized/sequential | `H01-H08` | effect-variation estimands, false-subgroup and calibration behavior, sequential assignment, policy value/regret/safety, and held-person evaluation |
| Transport | `T01-T08` | defined source and target populations, joint context support, sampling/selection mechanism, positivity diagnostics, transport estimands, and held-context evaluation |

The six entries may eventually report family-specific target attainment only after
their required operating-characteristic objects are source bound and executable. The
aggregation state is `forbidden`: there is no overall scalar, cross-family
compensation, target-completion percentage, or stable rank. Pareto analysis may still
compare fully named capacity coordinates and resource objectives without turning the
vector into a hidden utility function.

### 9.3 Enrollment is an output of estimands and operating characteristics

Level 1 does not declare a global participant target. Enrollment is unresolved for
every family until its estimand, error criterion, target effect or precision, outcome
and dependence model, missingness and retention process, allocation rule, and
validation design are executable. SMART sample size depends on the primary dynamic
treatment-regime comparison and its longitudinal outcome assumptions, not on the
word `SMART` or a count of embedded regimes [21]. Micro-randomized-trial sample size
likewise depends on the proximal-effect model, decision cadence, availability,
randomization probabilities, and within-person dependence [22]. Transport cannot be
powered from a list of sites or marginal demographic counts: the target population,
conditional transportability assumptions, joint support, and positivity must be
specified [23].

A global enrollment value may be emitted only after all six family-specific
operating-characteristic and enrollment derivations resolve, a source-bound joint
context-support object exists, cross-family participant reuse and covariance are
modeled, and an aggregation and rounding rule is frozen. Summing family sample sizes,
taking their maximum as implicit complete reuse, or deriving enrollment from the
number of coordinates or modalities is forbidden. Until those gates close, the
machine value remains `null` with blocker code
`WITHHELD_PENDING_ALL_FAMILY_OPERATING_CHARACTERISTICS_AND_SOURCE_BOUND_JOINT_CONTEXT_SUPPORT`.

This does not block prospective design. The Trial Designer can compile the declared
geometry of a planned protocol and show what observations, trajectories,
intervention contrasts, sequential decisions, and context support it would create.
It cannot claim that the design has completed Level 1, occupies a stable rank, or
meets an invented ideal enrollment before the family authorities exist.

### 9.4 Substantive supersession of target v2

The previous target-v2 derivation treated all 64 coordinates as powered event
outcomes, reused relational `D`, `P`, `H`, and `T` coordinates as moderators or
context strata, and combined those roles again across causal and transport terms.
Those semantics are not inherited. Its global multiplicity, enrollment,
normalization, context-allocation, and target-completion outputs are quarantined as
archival v2 objects and are not values of the role-aware authority.

The machine-readable impact receipt at
`spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json` records every
invalidated v2 path, proves the disjoint role partition, verifies that no joint
support matrix or numeric rank was fabricated, and sets promotion, stable-rank, and
global-enrollment permission to false. The candidate authority is
`spec/v3/level1/role-aware-target-requirements.v3.json`; its executable validator is
`src/anibench/level1_target_v3.py`. Promotion requires source-bound closure of every
listed gate plus independent role, operating-characteristic, sensitivity, and hostile
gaming attestation.

External protocols cannot inline their own prior, operator, covariance, causal basis,
or target geometry in comparable mode. A hash-pinned authority pointer, profile name,
assay label, or source locator alone is not executable geometry. Comparable external
compilation remains blocked until an assay-specific operator and covariance authority,
real operator identity, and field-level source hashes and locators are registered.
Missing families remain typed blockers.

Basis comparison follows JSON's single-number semantics: finite values such as `1`
and `1.0` are numerically equivalent, while the submitted-input hash still preserves
their different serializations. Booleans cannot substitute for numbers, non-finite
values fail closed, and genuinely different values remain mismatches.

## 10. Source-bound protocol compilation

The public comparable object contains source facts and authority references, not
caller-selected matrices. The resolver verifies source-object bytes, JSON pointers,
authority object hashes, schema versions, selected profiles, event units, policies,
moderators, and transport axes before constructing internal protocol geometry.

The role-aware validator verifies coordinate identity, role partition, family-gate
states, and the v2-to-v3 substantive-impact receipt. The generic protocol compiler
can compile source-bound design geometry, but it cannot manufacture a numeric
role-aware target from abstract unit-basis rows. External rows receive the typed blocker
`external-geometry-authority-not-registered` until the field-level authority described
above exists. Descriptive source verification is therefore not silently promoted to
operator resolution or a family score.

For Design Preview, the source may be an author-attested proposed protocol. For
Registered Protocol, it must be a frozen registry, protocol, or statistical-analysis
source. Realized, accessible, and demonstrated lanes require their own execution
receipts. A study that has descriptive facts but lacks operator, covariance, joint
event, assignment, or transport geometry remains visible as `not_scoreable`; it is
not assigned zero and it is not given an invented matrix.

The source bundle follows FAIR and datasheet-style provenance principles by exposing
identifiers, source objects, intended uses, missing fields, and access conditions
[9,10]. Those documentation principles do not by themselves establish executable
geometry or biological validity.

## 11. Prospective protocol optimization

The optimizer receives a base protocol, permitted typed mutations, resource deltas,
resource limits, and explicit family objectives. Each candidate is constructed by
changing protocol geometry and running the compiler again. Direct score patches,
family weights, overall objectives, opposing duplicate objectives, and unsourced
resource changes are rejected.

For candidate protocol $d$, the optimizer returns a vector

$$
f(d)=(f_1(d),\ldots,f_K(d),-c_1(d),\ldots,-c_R(d)),
$$

where $f_k$ are declared family metrics and $c_r$ are sourced resource totals.
Dominance is componentwise under declared maximize or minimize directions. The
output is a Pareto set, not a hidden utility function.

Resource base amounts, limits, and mutation deltas are accumulated and compared as
exact decimal quantities. The emitted floating representation is only an API
projection of that exact ledger. Positive deltas below the representable resolution
at the current floating total, non-finite values, overflow, duplicate resource deltas,
and unsourced zero-cost mutations fail closed; Pareto dominance reads the exact
decimal totals. Resource magnitudes remain caller-declared and are not labeled
content-verified unless a separate resolver retrieves and checks their cited bytes.

Every mutation receipt records changed fields, source locator, resource delta,
recompiled family outputs, comparison eligibility, and binding hashes. The product
therefore allows a sponsor to ask how participants, follow-up, measurement depth,
jointness, randomization, adaptive decisions, context coverage, access, or retention
would change the trial's information map before the study is funded.

## 12. Corpus and chart semantics

The fresh-history public export contains a score-free external source atlas for
reproducible source-acquisition and missingness inspection. Its coordinate table is
derived only from the allowlisted external projections. Controlled ANI projections,
private trial data, upstream response bodies, and internal atlas inputs are excluded
from the public repository and distribution archives. A later public benchmark
corpus is a separately frozen, permissioned artifact rather than an implicit export
of the working tree.

Each public external projection binds study identity, allowlisted source metadata,
hashes, locators, typed population and duration semantics, known measurement-module
descriptions, causal features, and open gates. The atlas reports only facts supported
by those objects and emits machine-readable plot data plus a build receipt. Row order
is not rank. Unknown fields remain visibly unknown. Family comparison charts require
complete authority-resolved protocol geometry; the plotting layer cannot generate a
score or rank from modality counts, publication prose, or curator preference.

A sealed field-provenance receipt enumerates every `state=known` projection pointer,
value digest, source-object digest, and locator. A field may remain known only when a
named executable operator reproduces the value from a resolved source JSON node.
Manual interpretation, even when attached to a replayed raw-source hash, is downgraded
to typed unknown until an executable derivation and exact locator resolve it. The
fresh public clone can replay the sealed machine-derived field set and regenerate the
external coordinate table without redistributing upstream bodies.
The private authority checkout separately replays raw-file hashes, extractors, and
locator-resolution evidence against those bodies.

## 13. Validation protocol

### 13.1 Baselines

AniBench must be compared with participant count, nominal visit count, duration,
modality count, feature count, raw byte or row count, and simple prospectively frozen
combinations. These baselines test whether the information geometry adds utility
beyond scale or inventory.

### 13.2 Held-out tasks

Validation uses frozen, source-linked human datasets and split assignments. Tasks
include held-person state reconstruction, future-state and derivative forecasting,
held-modality reconstruction, held-intervention response estimation, policy-value
estimation under eligible randomized designs, held-site and held-cohort transfer, and
multimodal coalition ablation. Holdouts are by person, future time, modality,
intervention, site, and cohort as appropriate. Performance includes calibration and
uncertainty. Prediction-model reporting maps to TRIPOD+AI, while development and
evaluation risk-of-bias review maps to PROBAST+AI; neither checklist substitutes for
the benchmark's executable split, null, source, or replay receipts [13,14].

### 13.3 Nulls and falsifiers

Applicable tasks include shuffled-person, shuffled-time, shuffled-intervention,
shuffled-outcome, identity-permutation, duplicate-row, duplicate-modality,
missingness, source-resolution, and model-class nulls. Multiplicity procedures and
acceptance thresholds are frozen before target access.

### 13.4 Prospective hypotheses awaiting immutable registration

The following are hypotheses, not findings. They are manuscript declarations only;
they are not called preregistered until the protocol, analysis code, split hashes,
thresholds, multiplicity rule, and timestamped registry identifier are deposited
before protected target or outcome access.

- **H1, incremental utility:** AniBench family metrics predict held-out biological
  model utility beyond simple scale and inventory baselines.
- **H2, intensive invariance:** multiplying participants with unchanged per-event
  geometry does not change intensive resolution.
- **H3, extensive monotonicity:** adding valid source-supported events preserves or
  increases absolute information.
- **H4, redundancy control:** a reliable new biological direction has greater
  conditional gain than an equally precise duplicate.
- **H5, longitudinal validity:** within-person schedule metrics predict forward-time
  reconstruction better than nominal visit count or global duration alone.
- **H6, causal separation:** policy/component structural ranks and sequential
  allocation-support geometry predict their matching held-out estimands without
  borrowing credit across families.
- **H7, personalization specificity:** geometry from eligible repeated randomized
  decisions with timely biological feedback predicts held-out policy-learning utility
  beyond personalization labels lacking that geometry.
- **H8, access specificity:** verified executable access predicts independent
  reanalysis better than publication or portal metadata.
- **H9, identity firewall:** masked, non-ANI authority and calibration decisions do
  not preferentially improve ANI-affiliated cases beyond prospectively frozen
  uncertainty.

## 14. Anti-gaming and mathematical invariants

Release-blocking tests include:

1. study name, sponsor, institution, journal, and row-order invariance;
2. duplicate file, row, feature, event, module, and alias invariance;
3. enrolled-versus-assayed denominator separation;
4. participant-event hyperedge enforcement and pairwise-chain rejection;
5. high-frequency autocorrelation and raw-row inflation rejection;
6. wrong-person, wrong-time, wrong-specimen, and zero-information neutrality;
7. policy, component, and sequential contrast separation;
8. personalization-label rejection without eligible decisions and feedback;
9. shallow scale inability to fill missing reference directions;
10. continued uncapped contraction inside supported directions;
11. intrinsic-versus-accessible separation;
12. unknown, absent, conditional, and zero distinction;
13. simultaneous basis reparameterization invariance;
14. materially non-positive-semidefinite input rejection;
15. deterministic content hashes and exact replay;
16. billion-count attacks capped by linked retained outcome and participant-event
    support;
17. conflicting participant-event lineage reuse and semantic schedule duplication;
18. same-event bundle splitting and multimodal participant-event double counting;
19. zero support for inactive observers and unresolved output for unknown observers;
20. fixed-rule personalization rejection when the decision rule ignores measured
    state;
21. deterministic coherent-frontier selection, with unbound stages remaining
    singleton alternatives and only homogeneous, authority-bound, mutually disjoint
    participant sets permitted to sum complete support matrices;
22. role-partition attacks, including attempts to treat `D`, `P`, `H`, or `T`
    coordinates as direct outcomes, raw moderators, or context strata;
23. cluster and crossover label rejection without explicit dependence geometry;
24. `rate_process` rejection without a registered window and event-count model;
25. external authority-pointer and profile-label attacks without field-level
    operator/covariance authority;
26. exact-decimal resource arithmetic, including sub-resolution positive deltas and
    overflow;
27. order-sensitive sibling-list mutation rejection;
28. resource-free and score-patch optimizer attack rejection; and
29. named-study exclusion from authority construction.

## 15. Ranking and decision semantics

Every future rank binds benchmark version, family, metric, evidence lane, corpus hash,
score packet, source objects, authority objects, uncertainty rule, and tie interval.
Design Preview cannot be merged with realized, accessible, or demonstrated ranks.
Rank envelopes must be derived from joint bootstrap or posterior draws under a frozen
dependence and multiplicity rule. Marginal interval overlap alone is not a ranking
procedure. Ties require exact numerical tolerance or a preregistered
practical-equivalence margin. A Pareto front may compare multiple declared objectives
without implying a total order.

No current source-atlas row receives a stable public rank unless all inputs for the
same metric and lane are authority resolved. This restriction applies equally to ANI
and external studies.

## 16. Governance and promotion gates

| Gate | Required artifact | Failure condition |
|---|---|---|
| Parameter space | frozen coordinate registry and target definitions | relevant dimensions are absent or not reproducible |
| Prior and covariance | reviewed positive-definite scenarios and sensitivity | instability or unsupported identity substitution |
| Level-1 authority | exact seven-role partition, six family operating-characteristic objects, hostile scaling tests, independent attestation | role coercion, unresolved operating characteristics, or independence failure |
| Source | exact objects, hashes, locators, and protocol mapping | unsupported substitution or unresolved geometry |
| Event jointness | source-bound hyperedges and ancestry audit | duplicate or false joint information |
| Causal geometry | policy, component, sequential, outcome, and moderator bindings | rank inferred from labels or arm count |
| Uncertainty | complete typed-state ledger and scenario replay | unknowns become point values |
| Calibration | held-out non-ANI task results, nulls, and multiplicity receipt | failure against prospectively frozen baselines or nulls |
| Transfer | measured context support and held-cohort tests | site count drives transport claims |
| Access | clean download or governed compute-to-data execution | documentation exists but independent execution fails |
| Package | clean install, CLI/API/Studio roundtrip, deterministic artifacts | consumer import, runtime, or artifact mismatch |
| Independence | conflict declarations, hostile reviews, adjudication, release vote | unresolved material defect |

Every methods change requires a new version, impact analysis, test update, and
immutable decision record. Released history is not rewritten.

## 17. Current implementation evidence

The candidate repository contains source implementations for strict schemas,
participant-event compilation, information and causal mechanics, typed scenario
envelopes, protocol-native optimization, a source atlas, a command-line interface, a
local API, and an interactive Trial Designer. Candidate chart builders emit CSV or
JSON plot data and a build receipt; candidate packaging rules exclude legacy
scalar/ranking surfaces and private patent material. Clean-install, wheel-content,
browser-roundtrip, and artifact-hash receipts are bound to the exact private
authority and public product commits named in the release/readback receipt. Those receipts establish
the public source-release implementation layer; they do not establish biological
calibration or a cross-trial rank.

The canonical executable benchmark front door is `anibench eval`; it emits the six
noncompensatory families and a hash-bound assessment receipt. `anibench compare`
accepts two or more hash-valid eval receipts only when implementation, Level-1,
geometry-authority, and parameter-space source objects match. It emits within-family
Pareto relations and no scalar or ordinal rank. Caller-declared geometry remains
explicitly labeled as a comparison sandbox rather than a public leaderboard.

Prospective protocol-capacity compilation is distinct from cross-study public
comparison and from role-aware Level-1 attainment. The installed v3 authority
validator can prove the 64-coordinate role partition and unresolved family gates; it
does not emit a target percentage, enrollment, or rank. The public comparator atlas
remains non-scoreable until each external study has source-complete protocol geometry
on the same role authority; registry descriptions and source hashes cannot substitute
for those matrices.

This is **software and methods evidence**. Biological validation remains a separate
future empirical layer. Until the independent authority, source completeness,
calibration, and release gates are closed, public rank permission remains false. This
boundary does not diminish the target system; it makes every eventual biological
claim reproducible.

## 18. Reproducibility map

| Construct | Repository authority |
|---|---|
| Biological Level-1 coordinates | `spec/v2/level1/biological-coordinate-registry.json` |
| Role-aware Level-1 authority | `spec/v3/level1/role-aware-target-requirements.v3.json`; `schemas/v3/level1-role-aware-target-authority.schema.json` |
| Substantive v2-to-v3 impact receipt | `spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json`; `schemas/v3/level1-v2-to-v3-impact-receipt.schema.json` |
| Executable Level-1 authority validator | `src/anibench/level1_target_v3.py`; `scripts/build_level1_target_v3.py` |
| Quarantined v2 target provenance | Intentionally excluded from fresh public history; its raw hash and supersession relation are recorded in the v3 authority and impact receipt above |
| Hash-pinned authority objects | `spec/v2/authority/` |
| Public comparator fact replay | `packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json`; `scripts/verify_external_field_receipts.py`; `src/anibench/source_atlas_v2.py` |
| Protocol-capacity input and compiler | `schemas/v2/protocol-capacity-input.schema.json`; `src/anibench/protocol_capacity_v2.py` |
| Protocol optimizer | `schemas/v2/optimizer-protocol-input.schema.json`; `src/anibench/optimizer_protocol_v2.py` |
| Joint information and nuisance adjustment | `src/anibench/information_v2.py` |
| Policy, component, and sequential support geometry | `src/anibench/causal_v2.py` |
| Source projections and atlas | `data/source_projections/v2/EXTERNAL_SOURCE_ACQUISITION_LEDGER.json`; `packaging/public_v2/EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json`; `packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json`; `src/anibench/source_atlas_v2.py` |
| API, CLI, and interactive Studio | `src/anibench/api.py`; `src/anibench/cli.py`; `src/anibench/studio.py`; `web/v2.*` |
| Anti-gaming contract | `docs/ANTI_GAMING.md` |
| Evidence policy | `docs/EVIDENCE_POLICY.md` |
| Reporting checklist | `paper/v2/REPORTING_CHECKLIST.md` |

Reproducible release verification must bind the exact commit, built wheel and source
archive hashes, authority and corpus hashes, generated artifact hashes, test commands,
clean-install environment, and browser readback.

## 19. Limitations and next empirical step

The local information model linearizes complex biology; its operator and covariance
authority must be empirically calibrated and may require nonlinear or task-specific
extensions. A finite mesoscopic coordinate registry necessarily omits biology.
Protocol documents may under-specify realized linkage and missingness. Trial-level
information cannot guarantee clinical utility, safety, fairness, or ethical
acceptability. Pareto-efficient designs still require human scientific, clinical,
operational, and ethics review.

The next empirical step is an immutably preregistered, multi-study validation in
which simple scale baselines and AniBench families predict held-person, future-time,
held-intervention, and held-cohort biological learning. The registration must precede
protected target or outcome access. Those results determine whether the candidate
authority is promoted, recalibrated, or superseded.

The empirical falsifiers are direct. AniBench should not be promoted if its family
metrics fail to add held-out utility beyond frozen scale and inventory baselines; if
duplicate or renamed measurements increase capacity; if longitudinal summaries show
no prespecified incremental predictive association beyond nominal visits for
forward-time tasks; if causal families predict
nonmatching estimands as well as matching ones; if identity masking reveals
self-favoring authority choices; or if results are unstable to defensible prior,
covariance, missingness, or source-resolution scenarios.

## 20. Declarations and submission gates

### 20.1 Author, affiliation, and contribution status

The author list, order, affiliations, corresponding author, and CRediT contribution
statement are unresolved in this draft. Repository access, company role, document
authorship, code authorship, and instruction of an automated system do not by
themselves determine scholarly authorship. Every listed author must confirm
substantial contribution, approve the submitted version, accept accountability, and
approve the final contribution statement before submission.

### 20.2 Funding

`[FUNDING SOURCES, GRANT NUMBERS, SPONSOR ROLES, AND ANY IN-KIND SUPPORT REQUIRE
AUTHORIZED COMPANY AND AUTHOR CONFIRMATION.]`

### 20.3 Competing interests

ANI Biome PBC is developing AniBench and may benefit from its adoption. The complete
employment, equity, intellectual-property, consulting, advisory, and sponsor-interest
declarations require author-by-author confirmation before submission. No patent
filing or patentability claim is made in this manuscript.

### 20.4 Ethics and participant data

This methods manuscript and the software tests described here do not report a new
analysis of identifiable human-participant data or a clinical intervention. Any
future empirical validation using protected participant data requires the applicable
ethics approval, consent or waiver, data-use authorization, privacy controls, and
dataset-specific reporting. This statement is not a determination that every future
AniBench use is non-human-subjects research.

### 20.5 Code, data, and materials availability

The public source repository is
`https://github.com/anibiome/anibench-benchmark`. The exact evaluated public
commit, verification runs, anonymous-clone build, clean-install, distribution-scan,
and browser-roundtrip receipts are recorded together in the release readback; the
manuscript does not recursively embed its own release commit. No stable tag, package-index publication,
or archive DOI is asserted here. The source atlas contains
hash-bound public evidence objects and typed missing fields; it is not a substitute
for source-complete trial matrices or participant-level data. No private patent
packet, unpublished protocol, absolute workstation path, credential, or participant-
level private source is authorized for the public package.

### 20.6 Protocol registration and results status

The validation hypotheses and analysis requirements in Section 13 are prospectively
specified but not yet registered. The immutable registration identifier, timestamp,
frozen split hashes, analysis-code hash, multiplicity procedure, thresholds, and
target-access boundary are required before the work may be described as
preregistered. No empirical validation result, stable trial rank, or biological
superiority claim is reported in this article.

### 20.7 Submission checklist

Submission requires: confirmed authorship and declarations; journal-specific format;
immutable protocol registration; exact release commit and archive; figure-license
and accessibility review; independent statistical and biological-methods review;
and a final consistency check between manuscript claims, executable outputs, and the
public release receipt.

## References

1. Lindley DV. On a measure of the information provided by an experiment.
   *Annals of Mathematical Statistics*. 1956;27:986–1005.
   [DOI 10.1214/aoms/1177728069](https://doi.org/10.1214/aoms/1177728069)
2. Chaloner K, Verdinelli I. Bayesian experimental design: a review.
   *Statistical Science*. 1995;10(3):273–304.
   [DOI 10.1214/ss/1177009939](https://doi.org/10.1214/ss/1177009939)
3. Kiefer J, Wolfowitz J. The equivalence of two extremum problems.
   *Canadian Journal of Mathematics*. 1960;12:363–366.
   [DOI 10.4153/CJM-1960-030-4](https://doi.org/10.4153/CJM-1960-030-4)
4. International Council for Harmonisation. E9(R1): estimands and sensitivity
   analysis in clinical trials. Step 4 guideline. 2019.
   [ICH E9(R1) guideline](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
5. US Food and Drug Administration. Adaptive designs for clinical trials of drugs
   and biologics: guidance for industry. 2019.
   [FDA guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/adaptive-design-clinical-trials-drugs-and-biologics-guidance-industry)
6. Hopewell S, Chan A-W, Collins GS, et al. CONSORT 2025 statement: updated
   guideline for reporting randomised trials. *BMJ*. 2025;389:e081123.
   [CONSORT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081123)
7. Chan A-W, Boutron I, Hopewell S, et al. SPIRIT 2025 statement: updated
   guideline for protocols of randomised trials. *BMJ*. 2025;389:e081477.
   [SPIRIT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081477)
8. Cole SR, Stuart EA. Generalizing evidence from randomized clinical trials to
   target populations: the ACTG 320 trial. *American Journal of Epidemiology*.
   2010;172(1):107–115.
   [DOI 10.1093/aje/kwq084](https://doi.org/10.1093/aje/kwq084)
9. Wilkinson MD, et al. The FAIR Guiding Principles for scientific data management
   and stewardship. *Scientific Data*. 2016;3:160018.
   [DOI 10.1038/sdata.2016.18](https://doi.org/10.1038/sdata.2016.18)
10. Gebru T, et al. Datasheets for datasets. *Communications of the ACM*.
    2021;64(12):86–92.
    [DOI 10.1145/3458723](https://doi.org/10.1145/3458723)
11. Liang P, et al. Holistic evaluation of language models. *Transactions on
    Machine Learning Research*. 2023.
    [arXiv 2211.09110](https://arxiv.org/abs/2211.09110)
12. Mattson P, Micikevicius P, Janapa Reddi V, et al. MLPerf: an industry
    standard benchmark suite for machine learning performance. *IEEE Micro*.
    2020;40(2):8–16.
    [DOI 10.1109/MM.2020.2974843](https://doi.org/10.1109/MM.2020.2974843)
13. Collins GS, et al. TRIPOD+AI statement: updated guidance for reporting clinical
    prediction models that use regression or machine learning methods. *BMJ*.
    2024;385:e078378.
    [TRIPOD+AI statement](https://www.bmj.com/content/385/bmj-2023-078378)
14. Moons KGM, et al. PROBAST+AI: an updated quality, risk of bias, and
    applicability assessment tool for prediction models using regression or
    artificial intelligence methods. *BMJ*. 2025;388:e082505.
    [PROBAST+AI statement](https://www.bmj.com/content/388/bmj-2024-082505)
15. Keller D, Steed R, Wang T, Bergman AS, Cihon P. *Practices for Automated
    Benchmark Evaluations of Language Models*. NIST AI 800-2 Initial Public Draft.
    January 2026.
    [DOI 10.6028/NIST.AI.800-2.ipd](https://doi.org/10.6028/NIST.AI.800-2.ipd)
16. Keller AJ, Kwegyir-Aggrey K, Steed R, Rao AK, Sharp JL, Bergman AS.
    *Expanding the AI Evaluation Toolbox with Statistical Models*. NIST AI 800-3.
    February 2026.
    [DOI 10.6028/NIST.AI.800-3](https://doi.org/10.6028/NIST.AI.800-3)
17. Klasnja P, Hekler EB, Shiffman S, et al. Microrandomized trials: an
    experimental design for developing just-in-time adaptive interventions.
    *Health Psychology*. 2015;34(Suppl):1220–1228.
    [DOI 10.1037/hea0000305](https://doi.org/10.1037/hea0000305)
18. Qian T, Yoo H, Klasnja P, Almirall D, Murphy SA. Estimating time-varying
    causal excursion effects in mobile health with binary outcomes. *Biometrika*.
    2021;108(3):507–527.
    [DOI 10.1093/biomet/asaa070](https://doi.org/10.1093/biomet/asaa070)
19. Cohn ER, Qian T, Murphy SA. Sample size considerations for micro-randomized
    trials with binary proximal outcomes. *Statistics in Medicine*.
    2023;42(16):2777–2796.
    [DOI 10.1002/sim.9748](https://doi.org/10.1002/sim.9748)
20. Kotalik A, Vock DM, Sherwood NE, Hobbs BP, Koopmeiners JS. Within-trial data
    borrowing for sequential multiple assignment randomized trials. *Biostatistics*.
    2025;26(1):kxaf003.
    [DOI 10.1093/biostatistics/kxaf003](https://doi.org/10.1093/biostatistics/kxaf003)
21. Seewald NJ, Kidwell KM, Nahum-Shani I, Wu T, McKay JR, Almirall D. Sample
    size considerations for comparing dynamic treatment regimens in a sequential
    multiple-assignment randomized trial with a continuous longitudinal outcome.
    *Statistical Methods in Medical Research*. 2020;29(7):1891-1912.
    [DOI 10.1177/0962280219877520](https://doi.org/10.1177/0962280219877520)
22. Liao P, Klasnja P, Tewari A, Murphy SA. Sample size calculations for
    micro-randomized trials in mHealth. *Statistics in Medicine*.
    2016;35(12):1944-1971.
    [DOI 10.1002/sim.6847](https://doi.org/10.1002/sim.6847)
23. Westreich D, Edwards JK, Lesko CR, Stuart EA, Cole SR. Transportability of
    trial results using inverse odds of sampling weights. *American Journal of
    Epidemiology*. 2017;186(8):1010-1014.
    [DOI 10.1093/aje/kwx164](https://doi.org/10.1093/aje/kwx164)

These sources establish the statistical, trial-design, data-reuse, and benchmark
governance lineage. They do not endorse AniBench formulas, reference targets, or
study evaluations.
