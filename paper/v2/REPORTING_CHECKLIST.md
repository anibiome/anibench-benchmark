# AniBench v2 methods and evaluation reporting checklist

Checklist status: AniBench v2 release candidate with role-aware Level-1 v3 authority

Use: manuscript, supplement, score packet, trial-design preview, validation report,
and independent review

Every applicable item requires an artifact path or content-addressed receipt.
`Yes` without a retrieval handle is incomplete. `Not applicable` requires a
reason. A planned study may complete Design Preview items while realized,
accessible, and demonstrated items remain ineligible.

## A. Document identity and claim state

- [ ] Benchmark suite version is stated.
- [ ] Document class is stated: protocol, implementation report, validation
  report, evaluation report, or release record.
- [ ] Evidence lane is stated.
- [ ] Study lifecycle and assertion source are stated separately from the lane.
- [ ] Formula implementation hash is provided.
- [ ] Parameter-space, prior-metric, reference-level, event-manifest,
  intervention-design, uncertainty-model, and corpus hashes are provided.
- [ ] Candidate, validated, audited, and released states are not conflated.
- [ ] No current trial rank is stated without a bound metric, lane, corpus,
  denominator, formula version, uncertainty semantics, and packet hash.
- [ ] No authorship, identifier, validation, or release status is inferred from a
  draft document or green software test.

## B. Benchmark construct

- [ ] Intensive Biological Resolution is reported separately.
- [ ] Extensive Biological Reconstruction Capacity is reported separately.
- [ ] Longitudinal Resolution is reported separately.
- [ ] Causal Architecture is reported separately.
- [ ] Personalized and Sequential Learning is reported separately.
- [ ] Population Transport is reported separately.
- [ ] No unlabeled overall trial-quality composite is used.
- [ ] Any completeness diagnostic is named as such and does not replace the
  component profile.
- [ ] Intrinsic and accessible capacity are separate.
- [ ] Every construct includes its estimand, unit, scale, denominator, and
  normalization.
- [ ] `schemas/v2/protocol-capacity-input.schema.json` validation passes.
- [ ] The reusable nonnegative numeric coordinate uses only exact, interval, or
  conditional form; unknown or structurally absent geometry is carried only by the
  enumerated authority/evidence objects that define those states.
- [ ] An unresolved authority/evidence object produces a null or unresolved family
  output, never a fabricated numeric zero.

## C. Parameter space and prior metric

- [ ] `spec/v2/parameter-space.json` version and hash are provided.
- [ ] State-observation coordinates are frozen and listed.
- [ ] Natural-dynamics coordinates and timescale registry are frozen and listed.
- [ ] Perturbation-response coordinates are frozen and listed.
- [ ] Person-context heterogeneity coordinates are frozen and listed.
- [ ] Functional/lived-state coordinates are frozen and listed.
- [ ] Population-transport coordinates are frozen and listed.
- [ ] All 64 coordinates are assigned exactly once to the seven disjoint v3 roles:
  22 direct mutable outcomes, `S01` baseline modifier, `S09` exposure/context,
  `D01-D12` longitudinal estimands, `P01-P12` causal-response estimands, `H01-H08`
  heterogeneity operating characteristics, and `T01-T08` transport estimands.
- [ ] `D`, `P`, `H`, and `T` coordinates are not encoded as direct event outcomes,
  raw moderators, or raw context strata.
- [ ] Raw source/target context covariates are source-bound outside the 64-coordinate
  map; naming a site or demographic field does not create a `T` estimand.
- [ ] Target and nuisance parameter blocks are explicit.
- [ ] Prior metric is positive definite and hash-bound.
- [ ] Prior derivation data exclude evaluation cases and ANI-affiliated trials.
- [ ] Reparameterization invariance test is reported.
- [ ] Prior sensitivity set and impact analysis are reported.

## D. Participant-event manifest

- [ ] `schemas/v2/event-manifest.schema.json` validation passes.
- [ ] Participant sets are aggregate and privacy-preserving.
- [ ] Enrolled, retained, assayed, contrast-supported, decision-eligible, and
  analysis-complete sets are distinct where applicable.
- [ ] Every quantitative participant or event field references a typed
  uncertainty coordinate.
- [ ] Event types identify role, participant set, time basis, measurement modules,
  linkage, and source receipts.
- [ ] Measurement modules identify modality registry entry, information role,
  platform, specimen/signal, tissue/compartment, cell resolution, target count,
  quality, completeness, standardization, error scale, covariance, and ancestry.
- [ ] Feature or specimen ancestry prevents split-panel duplication.
- [ ] Covariance groups identify protocol prior, empirical covariance, perfect
  duplication, independence bound, or unknown state.
- [ ] Multi-measurement claims use participant-event hyperedges.
- [ ] Every hyperedge binds joint participants, joint events, identity linkage,
  temporal compatibility, specimen lineage, intersection semantics, and source.
- [ ] Pairwise chains are not reported as undeclared higher-order intersections.
- [ ] Physical events are counted once in joint information assembly.
- [ ] High-frequency rows are not relabeled as independent events.
- [ ] Participant-event lineage identifiers are unique or exact semantic aliases;
  conflicting geometry under one lineage fails closed.
- [ ] Measurement layers sharing canonical participant-event support occupy one
  joint bundle and contribute one longitudinal event denominator.
- [ ] Exact-offset schedules have one offset per declared event.
- [ ] A `rate_process` is not compiled without a registered observation window,
  rate unit, and event-count model.

## E. Intervention and estimand geometry

- [ ] `schemas/v2/intervention-design.schema.json` validation passes.
- [ ] Whole policies and operator components are separate objects.
- [ ] Operator components include family, target/mechanism, dose/intensity,
  schedule, route, washout, exposure, adherence, and provenance where applicable.
- [ ] Assignment stages identify assignment unit, decision event, eligible set,
  alternatives, mechanism, probabilities, positivity, repeated-assignment state,
  carryover, censoring, and source.
- [ ] Every assignment probability is bound at the applicable decision stage.
- [ ] Every estimand states population, treatment conditions, outcome support,
  summary measure, intercurrent-event strategy, multiplicity family, and source.
- [ ] Whole-policy contrast matrices are explicit.
- [ ] Component contrast matrices are explicit.
- [ ] Sequential/path contrast matrices are explicit.
- [ ] Matrix dimensions, row IDs, column IDs, and values are verified.
- [ ] Contrast rank is calculated from the explicit matrix under a versioned
  numerical tolerance.
- [ ] Top-level policy count is not used as component or sequential rank.
- [ ] Causal endpoint and dynamic operator information are separate.
- [ ] Repeated natural history receives no operator-causal credit without
  exogenous operator variation.
- [ ] Prospective personalization requires eligible decisions, genuine
  alternatives, known propensities, pre-decision state/context support, a declared
  rule that uses measured state, and timely linked readback.
- [ ] Every contributing decision epoch explicitly binds availability, canonical
  policy propensities, pre-decision history features and schedules, and unique
  post-decision observations to a frozen proximal estimand; a compact regular process
  may use one fully bound template only when count, start, interval, cadence,
  duration, readback lag, stationary moderator covariance, and source are registered.
- [ ] Compact regular-process support is analytically equivalent to its explicit-grid
  expansion and does not materialize thousands of duplicate epoch rows.
- [ ] Every proximal estimand freezes outcome definition and features, policy
  contrast, horizon, and source receipts; its contrast policies have positive
  propensity in the linked epoch.
- [ ] Eligible linked-outcome support is capped by stage enrollment times epoch
  availability and retained outcome support; moderator support is capped again by
  retained pre-decision history support.
- [ ] A registered population moderator covariance covers every contributing epoch,
  matches the epoch history feature set, and passes finite, symmetric, positive-
  semidefinite checks.
- [ ] The heterogeneous-response gate is not described as a deployed personalized
  rule; it may be earned by randomized estimand-contrast-by-population-moderator
  covariance geometry without a state-dependent policy operator.
- [ ] Personalized-policy credit additionally requires repeated SMART or
  micro-randomized epochs and a registered nonzero state-to-policy contrast operator
  whose state features are measured before every eligible decision.
- [ ] SMART paths cover the complete chronological epoch ledger, use only policies
  with positive epoch propensity, link response states to next-epoch measured
  history, sum to one, and reproduce epoch propensity marginals.
- [ ] Structural rank and allocation-support factors are reported separately, and
  allocation support is never labeled inferential precision or biological information.
- [ ] Declared assignment participants are capped by retained participant support
  from linked active-observer outcomes.
- [ ] Eligible participant-decisions are capped by linked retained outcome
  participant-events.
- [ ] Exact semantic duplicate stages are removed. An unbound stage remains a
  singleton alternative; multiple stages can combine only inside one explicit
  authority-registered stage set whose participant sets are mutually disjoint and
  whose assignment, allocation, outcome, moderator, decision-rule, and SMART
  semantics are identical.
- [ ] One stage cannot belong to multiple aggregation sets. Heterogeneous stage kinds
  remain separate frontier members. Factorial, SMART, and micro-randomized designs
  remain estimand-specific protocol geometries, not universal Level-1 components.
- [ ] Causal and personalized summaries select one eligible stage-set frontier member
  under frozen deterministic rules. A registered set sums its complete aligned
  policy, component, and moderator information matrices; no summary mixes rank,
  allocation support, participant support, outcome geometry, or moderator geometry
  across frontier members.
- [ ] The selected personalized stage set binds every member's decision-epoch ledger,
  frozen estimand contrasts, population moderator covariance, state-to-policy
  operator, participant-set authority, and outcome/moderator geometry hashes.
- [ ] Cluster-randomized and crossover labels receive no numeric causal credit
  until cluster/period/sequence/carryover and covariance dependence are explicit.

## F. Joint information computation

- [ ] `schemas/v2/information-run.schema.json` validation passes.
- [ ] Each event contribution binds (A_e), (R_e), effective count, and source.
- [ ] Noise and covariance matrices are positive definite or fail closed.
- [ ] Event contributions are positive semidefinite.
- [ ] Joint information is assembled event by event.
- [ ] Shared measurements are not independently added into multiple composite
  log determinants.
- [ ] Nuisance adjustment uses the declared Schur complement.
- [ ] The nuisance claim is limited to explicitly modeled, correctly specified
  structure; omitted or misspecified nuisance processes remain sensitivity and
  falsification targets.
- [ ] The adjusted target matrix is positive semidefinite within the frozen
  tolerance.
- [ ] Prior whitening uses the exact bound prior metric.
- [ ] Absolute log local contraction is reported with formula version.
- [ ] Any future family-reference attainment uses a canonical biological direction
  basis and direction-wise caps; matrix diagonalization alone is not treated as a
  unique biological basis when reference eigenvalues repeat.
- [ ] Any resolved future family coordinate reports capped attainment beside its
  uncapped observed-to-target ratio using the same information and reference objects.
- [ ] The current role-aware Level-1 authority emits no target percentage or
  attainment claim while family operating-characteristic targets are unresolved.
- [ ] Coverage thresholds come from a versioned registry.
- [ ] All matrix inputs and outputs are content-hashed.
- [ ] Numerical tolerances, library versions, and deterministic execution details
  are recorded.
- [ ] Caller-declared hashes equal server-computed canonical matrix hashes.
- [ ] Caller-declared reference authority is not treated as server verification.
- [ ] `reference_metrics` is null unless a frozen local reference authority is
  verified.
- [ ] Illustrative fixture output is labeled `illustrative_reference_metrics`
  and cannot be reported as family attainment or a biological reference.
- [ ] Every matrix, count, profile weight, action, propensity, state-basis row,
  eligibility vector, and structural boolean binds an exact source object hash
  and source locator.
- [ ] Caller-declared source bindings are not labeled content-verified unless the
  runtime retrieved and checked the cited bytes and locator.
- [ ] Intensive and Extensive inputs pass the count-weighted information-matrix
  cross-binding check when both are present.
- [ ] Inactive outcome observers contribute zero eligible causal and transport
  support rather than inheriting declared counts.
- [ ] Unknown outcome observers remain unresolved with blocker provenance; they
  are not silently coerced to zero or treated as inactive.

## G. Intensive resolution

- [ ] Intensive outputs are normalized to the participant-event distribution.
- [ ] Participant count does not alter an unchanged intensive profile.
- [ ] State-resolution spectrum is reported.
- [ ] Timescale-resolution profile uses the actual schedule.
- [ ] Direct functional resolution is reported.
- [ ] Biological-to-functional linkage is reported.
- [ ] Context and exposure resolution are reported.
- [ ] Joint covariance-adjusted directional information is computed from verified
  same-event bundles; no empirical multimodal synergy is inferred.
- [ ] Protocol complementarity is not labeled empirical synergy.
- [ ] Empirical synergy, when reported, uses held-out coalition ablation,
  multiplicity control, positive uncertainty bounds, and falsifier tests.

## H. Extensive reconstruction capacity

- [ ] Retained and assay-supported events, not enrolled N alone, enter the matrix.
- [ ] Repeated-event autocorrelation and irregular timing are represented.
- [ ] Site, cluster, household, and batch effects are represented where relevant.
- [ ] Missingness and informative dropout are represented.
- [ ] Arm, sequence, component, and decision-specific support are represented.
- [ ] Joint multimodal support uses actual intersections.
- [ ] Absolute information is reported; family attainment, overflow, and a coverage
  curve are reported only when a source-bound family reference exists.
- [ ] Shallow information cannot fill unmeasured reference directions.
- [ ] Additional valid information in a saturated direction remains visible in
  overflow or absolute information.
- [ ] Extensive posterior-direction information is computed from the declared
  prior-whitened posterior covariance, not from raw marginal diagonals alone.

## I. Typed uncertainty

- [ ] `schemas/v2/uncertainty.schema.json` validation passes.
- [ ] Each reusable generic nonnegative numeric coordinate uses exact, interval, or
  conditional form without cross-type coercion.
- [ ] Selected authority/evidence objects may carry unknown or absent states only
  where their schema explicitly permits them; their affected numerical outputs remain
  null or unresolved.
- [ ] Units and evidence class are present.
- [ ] Exact values include source receipts.
- [ ] Interval endpoints and inclusivity are present.
- [ ] Any schema-specific distributional uncertainty includes family, parameters,
  support, seed where sampling applies, and provenance; it is not implied to be a
  generic coordinate form.
- [ ] Structural absence includes a reason and zero semantics only for the
  affected construct.
- [ ] Unknown values include a reason and are not point-imputed.
- [ ] Interval endpoint replays contain the reported bound.
- [ ] Protocol uncertainty is not labeled a sampling confidence interval.
- [ ] Realized statistical uncertainty uses an estimand-appropriate method.
- [ ] Rank uncertainty is derived from joint bootstrap or posterior draws under a
  frozen dependence and multiplicity rule; marginal interval overlap is not used as
  a ranking procedure.
- [ ] A tie uses exact numerical tolerance or a preregistered practical-equivalence
  margin, not overlapping marginal intervals.
- [ ] Global sensitivity contributions are reported.

## J. Evidence lanes and access

- [ ] Design Preview uses only protocol-committed coordinates.
- [ ] Registered Protocol binds the exact frozen source and does not change the
  capacity of otherwise identical design geometry.
- [ ] Optional or conditional uncommitted modules are not scored as exact.
- [ ] Realized lane uses actual retained events, QC, linkage, assignment, and
  covariance.
- [ ] Accessible lane has a successful lawful download or governed
  compute-to-data receipt.
- [ ] Documentation alone does not activate accessible capacity.
- [ ] Demonstrated lane has frozen held-out task receipts.
- [ ] Planned studies are marked ineligible, not numeric zero, outside Design
  Preview.
- [ ] Protocol and realized contradictions resolve in favor of realized source
  truth for realized claims.

## K. Role-aware Level-1 authority

- [ ] Coordinate identity, names, order, and six-block membership are frozen before
  any candidate study is evaluated.
- [ ] The seven-role partition is exhaustive and pairwise disjoint.
- [ ] Only `S02-S08`, `S10-S16`, and `F01-F08` are eligible direct mutable outcome
  coordinates, and even those require source-bound observation operators, scales,
  reliability, missingness, and event linkage before measurement credit.
- [ ] `S01` is a baseline modifier and `S09` is exposure/context; neither is coerced
  into another role.
- [ ] `D01-D12`, `P01-P12`, `H01-H08`, and `T01-T08` are relational estimands or
  operating-characteristic targets, not directly powered event outcomes.
- [ ] The six family authorities are reported as an ordered noncompensatory vector;
  no overall scalar, cross-family compensation, or stable rank is emitted.
- [ ] Every family names its estimand, unit, operating-characteristic target,
  required source objects, validation design, and blocker state.
- [ ] Unresolved family operating-characteristic targets and enrollments remain typed
  unknown with `value: null`; they are never set to zero or a placeholder percentage.
- [ ] Intensive closure binds observation operators, within-event covariance,
  repeatability, and calibration for the direct mutable outcome basis.
- [ ] Extensive closure binds eligible role coverage, cross-coordinate redundancy,
  and source-bound identifiability.
- [ ] Longitudinal closure binds transition and observation models, process and
  measurement noise, the time grid, and held-time or held-person validation.
- [ ] Causal closure binds counterfactual estimands, assignment or identification,
  intervention operators, multiplicity, attrition, interference, and adherence.
- [ ] Personalized/sequential closure binds effect-variation estimands, false-subgroup
  and calibration behavior, sequential assignment, policy value/regret/safety, and
  held-person validation.
- [ ] Transport closure binds explicit source and target populations, raw context
  covariates, a source-bound joint-support table or identified bound, sampling and
  selection mechanisms, positivity diagnostics, transport estimands, and held-context
  validation.
- [ ] No global enrollment is emitted until all family-specific sample-size and
  operating-characteristic objects, joint context support, cross-family reuse and
  covariance, aggregation, and rounding authorities resolve.
- [ ] Family sample sizes are not summed without disjointness and covariance
  authority, their maximum is not used as an implicit complete-reuse target, and
  coordinate or modality count is not used as a sample-size formula.
- [ ] SMART and micro-randomized enrollment derivations bind their specific primary
  estimands, outcome and dependence models, decision schedule, availability, and
  allocation probabilities.
- [ ] Target-v2 multiplicity, enrollment, context, and normalization outputs remain
  quarantined and are not displayed as current Level-1 values.
- [ ] `spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json` replays and
  binds the exact v2 predecessor and v3 candidate bytes.
- [ ] Independent role-ontology, operating-characteristic, sensitivity, and hostile
  gaming review is complete before promotion.
- [ ] Any future family reference freezes its prior, covariance, direction basis,
  target, and normalization before candidate projection; evaluated scenarios cannot
  choose their denominator.
- [ ] External protocol pointers, labels, and source locators do not invoke abstract
  geometry without registered assay-specific operator/covariance authority, real
  operator identity, and field-level bindings.

## L. Validation and preregistration

- [ ] Prospective hypotheses, estimands, splits, thresholds, multiplicity rules,
  nulls, and analysis-code hashes are listed before target access.
- [ ] A timestamped immutable registration identifier is recorded before target
  access; until then the plan is described as specified, not preregistered.
- [ ] Baselines include participants, visits, modalities, features, bytes/rows,
  and the six-family capacity vector without a hidden scalar.
- [ ] Development, calibration, and untouched holdout studies are distinct.
- [ ] ANI-affiliated studies are excluded from formula, prior, reference, and
  threshold fitting.
- [ ] Person-held-out tasks are included where applicable.
- [ ] Future-time-held-out tasks are included where applicable.
- [ ] Site- and cohort-held-out tasks are included where applicable.
- [ ] Intervention-held-out and policy-value tasks are included where eligible.
- [ ] Modality coalition ablations are included.
- [ ] Calibration and uncertainty metrics are included.
- [ ] Shuffled-person, time, intervention, and outcome nulls are included.
- [ ] Multiplicity and promotion criteria were frozen before evaluation.
- [ ] Registry priors that fail immutably preregistered targets are recalibrated or removed
  in a new version.

## M. Anti-gaming and numerical invariants

- [ ] Name, sponsor, institution, journal, row order, and corpus order are
  invariant.
- [ ] Duplicate row, file, feature, event, and modality attacks are neutral.
- [ ] Split-panel aliases are neutral.
- [ ] Enrolled N cannot replace an assay or contrast denominator.
- [ ] Wrong-person, wrong-time, wrong-specimen, and zero-quality links add zero.
- [ ] Pairwise chains cannot unlock undeclared multiway jointness.
- [ ] A one-time randomized endpoint can have endpoint causal information and no
  dynamic operator information.
- [ ] Repeated unassigned observations can have dynamic information and no
  operator causal information.
- [ ] Explicit sequential randomization can create contrast rank beyond top-level
  policy count.
- [ ] Personalization labels without assignment geometry add no sequential
  information.
- [ ] A fixed decision rule that ignores measured state adds no personalized-policy
  credit.
- [ ] Billion-scale declared participants or decisions cannot exceed linked retained
  outcome support or linked retained participant-events.
- [ ] An inactive outcome observer contributes zero eligible causal or transport
  support.
- [ ] An unknown outcome observer leaves the affected result unresolved with blocker
  provenance and is not treated as inactive or coerced to zero.
- [ ] Conflicting participant-event lineage reuse fails closed and exact semantic
  duplicates do not add information.
- [ ] Same-event bundle splitting cannot discard cross-modal covariance or multiply
  the longitudinal event denominator.
- [ ] Incompatible stage classes cannot manufacture a summary by mixing the best
  rank, allocation support, outcome geometry, or moderator identity from different
  stages.
- [ ] Cluster and crossover design labels add no numeric credit without explicit
  dependence geometry.
- [ ] A `rate_process` adds no events without its registered window and event-count
  model.
- [ ] External authority pointers and modality/profile labels add no family score
  without field-level executable geometry.
- [ ] Valid positive-semidefinite additions cannot reduce absolute information.
- [ ] Perfect correlation adds zero conditional information.
- [ ] Simultaneous nonsingular reparameterization preserves generalized
  information.
- [ ] Materially non-positive-semidefinite inputs fail closed.
- [ ] Basis compatibility follows JSON single-number semantics: finite equal
  values such as `1` and `1.0` are equivalent, booleans and non-finite values
  fail closed, and the submitted-input hash still binds the exact serialization.
- [ ] Exact hashes and deterministic replay are verified.
- [ ] Optimizer resource arithmetic uses exact decimal totals for constraints and
  Pareto dominance.
- [ ] Positive resource deltas below floating representable resolution, overflow,
  repeated deltas, and unsourced zero-cost mutations fail closed.
- [ ] Sibling list insertions/removals that can shift one another's indices fail
  closed instead of producing mutation-order-dependent candidates.
- [ ] Caller-declared resource amounts remain labeled not content-verified until
  their cited bytes are retrieved and checked.

## N. Ranking and visualization

- [ ] Rank object identifies benchmark family and metric.
- [ ] Lane, corpus hash, denominator, formula version, and score-packet hash are
  shown.
- [ ] Tie policy and rank interval semantics are shown.
- [ ] Uncertainty envelope is shown where coordinates are uncertain.
- [ ] Design, realized, accessible, and demonstrated values are not merged.
- [ ] Intensive and extensive charts have unambiguous titles and units.
- [ ] When a family reference is resolved, capped attainment and uncapped overflow
  are visually distinct; no target track is drawn for unresolved family authority.
- [ ] Pareto displays name every objective.
- [ ] No visual position or sorted row index is presented as an unqualified
  scientific rank.
- [ ] Every figure binds a machine-readable source table and formula hashes.

## O. Governance, independence, and release

- [ ] Methods decision record identifies proposal, alternatives, falsifiers,
  hashes, reviewers, conflicts, recusals, tests, and superseded decisions.
- [ ] Every score-bearing source cell has independent rating where required.
- [ ] Disagreements have eligible independent adjudication.
- [ ] Evaluator targets and submissions remain separated.
- [ ] Hostile audit has no open blocking finding.
- [ ] Validation receipt binds the exact frozen review subject.
- [ ] Independent-review receipt binds declarations, coverage, adjudication, and
  vote arithmetic.
- [ ] Security, privacy, rights, accessibility, and patent gates are separately
  recorded.
- [ ] Artifact bytes are unchanged after external review or the review is rerun.
- [ ] Repository visibility, tag, package publication, and public distribution
  require a separate authorized release decision.

## P. Required manuscript tables and supplements

- [ ] Construct-definition table.
- [ ] Parameter and nuisance-block table.
- [ ] Participant-event manifest summary.
- [ ] Measurement ancestry and covariance table.
- [ ] Intervention-stage and estimand table.
- [ ] Policy, component, and sequential contrast-matrix supplement.
- [ ] Typed uncertainty ledger.
- [ ] Role-aware Level-1 authority and v2-to-v3 substantive-impact receipt.
- [ ] Family-specific operating-characteristic and enrollment derivation receipts,
  when resolved.
- [ ] Baseline and held-out task table.
- [ ] Null/falsifier table.
- [ ] Sensitivity and prior-impact table.
- [ ] Metric-specific results with uncertainty, when eligible.
- [ ] Evidence-lane and access table.
- [ ] Conflict and independence declarations.
- [ ] Formula, schema, implementation, source, and packet hash manifest.

## Q. Public fresh-history repository authorities

- [ ] `spec/v2/level1/biological-coordinate-registry.json`
- [ ] `spec/v3/level1/role-aware-target-requirements.v3.json`
- [ ] `spec/v3/level1/migrations/v2-to-v3-substantive-impact-receipt.json`
- [ ] `spec/v2/authority/manifest.json` and every hash-pinned object it lists
- [ ] `schemas/v2/protocol-capacity-input.schema.json`
- [ ] `schemas/v2/protocol-capacity-result.schema.json`
- [ ] `schemas/v3/level1-role-aware-target-authority.schema.json`
- [ ] `schemas/v3/level1-v2-to-v3-impact-receipt.schema.json`
- [ ] `schemas/v3/level1-role-aware-assessment.schema.json`
- [ ] `schemas/v2/optimizer-protocol-input.schema.json`
- [ ] `schemas/v2/optimizer-protocol-result.schema.json`
- [ ] `src/anibench/protocol_capacity_v2.py`
- [ ] `src/anibench/optimizer_protocol_v2.py`
- [ ] `src/anibench/information_v2.py`
- [ ] `src/anibench/causal_v2.py`
- [ ] `src/anibench/level1_target_v3.py`
- [ ] `src/anibench/level1_assessment_v3.py`
- [ ] `scripts/build_level1_target_v3.py --check`
- [ ] `docs/EVIDENCE_POLICY.md`
- [ ] `docs/ANTI_GAMING.md`
- [ ] `paper/v2/AniBench_v2_benchmark_protocol.md`

The private authority checkout additionally reviews the following supplementary
artifacts. They are intentionally excluded from the fresh-history public export
and are not required for a public clone to build, test, or run:

- [ ] `src/anibench/trial_atlas_v2.py`
- [ ] `docs/VALIDATION.md`
- [ ] `docs/CORPUS_SELECTION.md`
- [ ] `docs/EXTERNAL_VALIDATION_GOVERNANCE.md`
- [ ] `docs/GOVERNANCE_OPERATIONS.md`

## R. Submission declarations

- [ ] Author list, order, affiliations, and corresponding author are confirmed by
  every listed author.
- [ ] CRediT contributions and accountability are confirmed; code or document
  metadata are not used as authorship proxies.
- [ ] Funding sources, grant identifiers, sponsor roles, and in-kind support are
  complete.
- [ ] Employment, equity, intellectual-property, consulting, advisory, and sponsor
  conflicts are declared author by author.
- [ ] Ethics, consent or waiver, privacy, and data-use statements match the exact
  empirical work reported.
- [ ] Code/data availability names the frozen public commit, tag, archive DOI,
  distribution hashes, and lawful access surface.
- [ ] Every in-text figure callout resolves to a legible captioned figure with
  meaningful alt text; figures are not appended without body callouts.
- [ ] No private patent, unpublished protocol, workstation path, credential, or
  participant-level private source appears in the public package.
- [ ] The manuscript says `not_run` where validation is not run and reports no
  stable rank where comparable geometry is incomplete.

Completion of this checklist is evidence only for the items with bound receipts.
It does not promote any unexecuted empirical, independent-review, or release gate.
