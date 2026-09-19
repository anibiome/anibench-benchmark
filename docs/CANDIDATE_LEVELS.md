# Candidate AniBench 1 and AniBench 2 finite collection-capacity suites

**Public discussion proposal, not a calibrated or normative target.** This does not replace the canonical six-family evaluator or its role-aware coordinate authority. The machine-readable counterpart is [discussion-v0.1.json](../spec/candidate_levels/discussion-v0.1.json). AB1 is a six-task linked panel of accessible biological states and responses. Core AB2 retains those tasks at finer registered precision and extends cell/spatial/time/context resolution. A separately named optional extension addresses controlled cortical perturbation. It is not a definition of complete human biology. No native-unit biological precision threshold or calibrated biological level is claimed.

The primary literature supports the relevance and measurable nature of the selected quantities. It does not endorse this task set, these particular cross-domain correlations, the coverage policy, or AB2's level boundary. Age, time, task and target choices below remain explicit policy proposals.

The subsequent [ERP CORE example](../examples/calibration/erp_core/README.md)
now recomputes one conditional within-session neural measurement error from
public derived files. Its source records remain outside the repository. It
does not supply repeat-session calibration or a biological precision threshold.

Its [conditional design planner](../examples/calibration/erp_core/DESIGN_PLANNER.md)
demonstrates how declared precision limits produce a bounded design frontier.
All task constraints must share the same variance assumptions. Illustrative
limits in that example are not candidate-level biological thresholds.

## Shared scope

AB1 proposes one named ambulatory adult 18–65 catchment and a 14-day observation block. These boundaries are policy starting points, not empirical minima. People must have linked observations across tasks for cross-domain claims. Meal, exertion, immune draws and neural probes must be scheduled to avoid unmodeled interference; validated recovery/washout is a prerequisite to a final protocol, not guessed here. Task eligibility and resulting population exclusions remain visible.

AB2 retains AB1 and halves each frozen half-width, then adds the named extensions. Baseline, 3-month and 12-month blocks and two named settings are candidate policy scopes, not proof of lifelong dynamics or global transport. A separately named older-adult target needs its own calibration. These six task IDs are not ANI's six mesoscopic axes and do not rename the six benchmark capacity families.

A study can lead a narrow task without passing the suite. A device earns no bonus: it contributes only through a registered operator or perturbation. Planned conditional capacity requires no treatment success or held-out model utility. Realized conditional capacity adds verified retained support/QC/linkage. Empirical learning plateau is a separate optional claim.

## AB1-M — Metabolic response shape

Can the record resolve a persons glucose and C-peptide response to a standardized meal, and variation in those responses across people?

**Frozen estimands proposed:**

- M_g: Signed baseline-subtracted glucose AUC over 0-120 minutes, with baseline modeled jointly; units: mmol/L * min.
- M_c: Signed baseline-subtracted C-peptide AUC over 0-120 minutes; units: nmol/L * min.

**Scope:** time: 0-120 minutes after a registered meal; two repeat occasions within the candidate 14-day block; space: venous circulating concentrations; interstitial glucose substitutes only with calibrated lag/bias operator; population: declared adults 18-65 catchment; population inference uses independent people, not meal repeats.

**Roles:** molecular_metabolic = observation; meal_exposure = controlled_challenge_not_randomized_treatment_contrast.

**Why this supports reconstruction:** Trajectory response adds a state-transition measurement beyond fasting concentrations; it does not identify insulin sensitivity or secretion rates without additional validated model information.

**Missing calibration:** Assay total-error covariance and limits of quantification; Baseline/post-meal covariance and time alignment; Within-person day variance versus between-person variance; Interpolation error at the actual schedule; Meal adherence, circadian phase, medication and prior-exercise effects.

**Calibration deliverables:**

- Use external repeated-meal calibration with split aliquots and dense reference sampling.
- Fit assay + day + donor variance components without using candidate-study outcome benefits.
- Validate downsampled AUC against dense integration and estimate interpolation bias.
- Freeze the matrix of integration weights and joint covariance, including baseline subtraction, then solve required repeats and N.

**AB2:** Retain AB1-M with h_AB2=h_AB1/2. Within-person difference in the two AUCs between two preregistered meal compositions under randomized crossover, with period/carryover adjustment. Both meal conditions at repeated blocks at baseline, 3 months and 12 months (policy windows); no universal annual completeness claim. Missing: Exact contrast protocol, washout validity, carryover covariance and between-person response heterogeneity; no universal arm count beyond the named contrast.

**Objection:** Two metabolites under one meal are not a full metabolic model. AUC can hide timing; include prespecified early/late contrasts in a later task revision if calibration shows material aliasing.

**Primary evidence:** [S01](https://www.nature.com/articles/s41591-020-0934-0).

## AB1-I — Peripheral immune responsiveness

Can an accessible blood sample resolve specified molecular immune responses while separating donor biology from handling and cell mixture?

**Frozen estimands proposed:**

- I_tnf: Paired stimulated-minus-control TNF concentration at the frozen endpoint of a validated whole-blood assay; units: pg/mL.
- I_il6: Paired stimulated-minus-control IL-6 concentration at the same endpoint; units: pg/mL.
- I_cells: Absolute monocyte and lymphocyte abundance in the input specimen as separate adjustment observables; units: cells per microliter.

**Scope:** time: One registered ex-vivo endpoint t_immune, to be selected from validated assay protocol; repeat draw at matched clock phase within 14-day block; space: whole blood only; not brain, liver, gut or lung immune states; population: same named adult catchment; donors are independent units.

**Roles:** immune_molecular = observation; blood_cell_composition = observation; ex_vivo_stimulus = specimen_perturbation_not_in_vivo_human_treatment.

**Why this supports reconstruction:** Perturbed immune output distinguishes resting abundance from responsiveness; matched cell composition helps detect a mixture explanation for molecular change.

**Missing calibration:** Preanalytic delay/storage/lot effects; Stimulus/control paired covariance and batch interaction; Censoring and heteroscedastic cytokine errors; Donor-by-day and donor-by-stimulus variability; Cell-count error and composition-response sensitivity.

**Calibration deliverables:**

- Run reference-lab split-sample and repeat-draw calibration across donor and handling blocks.
- Use validated safe assay authority; this candidate specifies no stimulus dose or procedure.
- Fit composition-adjusted response model while retaining unadjusted response.
- Freeze endpoint, two cytokines and limits before examining competitor designs.

**AB2:** Retain AB1-I and tighten h by factor 2. Within prespecified monocyte and T-cell compartments, a frozen small transcript-response set under one validated matched specimen challenge; separate cell abundance from within-cell response. Cell-type resolution in blood; repeat at baseline, 3 and 12 months. Missing: Cell-assignment confusion, capture bias, transcript count/noise model, donor covariance and protein/transcript relation; no assumption that single-cell RNA measures protein function.

**Objection:** Selected cytokines and cell classes privilege peripheral immunity; the assay cannot certify immune competence or whole-body tissue coverage.

**Primary evidence:** [S02](https://pubmed.ncbi.nlm.nih.gov/24656047/), [S06](https://www.nature.com/articles/s41467-021-25960-2), [S07](https://www.nature.com/articles/s41586-023-06422-9).

## AB1-F — Functional exertion and recovery

Can the record resolve physiological response to a fixed registered workload and the early recovery trajectory?

**Frozen estimands proposed:**

- F_hr: Peak-to-one-minute heart-rate decrease under a frozen exercise and recovery posture/procedure; units: beats/min.
- F_vo2: Integrated oxygen uptake above pre-exercise baseline over first 5 recovery minutes; units: mL O2/kg.

**Scope:** time: During registered exertion and 0-5 minutes recovery; repeat occasion after validated recovery; space: cardiorespiratory functional outputs, not every organ or autonomic mechanism; population: eligible subset of the named catchment; exclusions and support limit must be explicit.

**Roles:** functional_exercise = controlled_challenge; cardiorespiratory_response = observation.

**Why this supports reconstruction:** A fixed input and recovery response constrain physiological transitions and functional reserve that static molecular counts alone do not measure.

**Missing calibration:** Workload and posture repeatability; Heart-rate/sensor latency and breath-by-breath VO2 covariance; Day-to-day and between-person response variance; Peak selection and temporal interpolation uncertainty; Eligibility-related population selection.

**Calibration deliverables:**

- Calibrate sensor outputs against criterion instruments and repeated challenge records.
- Freeze workload parameterization and recovery conditions; assess peak-selection bias.
- Use known time-integration weights where valid and propagate correlated error.
- Do not import a mortality-risk threshold as an estimation tolerance.

**AB2:** Retain AB1-F and tighten h by factor 2. Response slope across two registered workload conditions and between-block change in that slope. At baseline, 3 and 12 months; fixed functional eligibility population. Missing: Dose-response linearity/locality, order/fatigue covariance, selection and temporal stationarity.

**Objection:** The one-minute HR measure is protocol-sensitive and the source clinical population does not establish normative values for all adults.

**Primary evidence:** [S03](https://www.nejm.org/doi/full/10.1056/NEJM199910283411804).

## AB1-D — Daily physiological rhythm and behavior linkage

Can linked digital observations separate a persons daily physiological rhythm from movement and sleep timing?

**Frozen estimands proposed:**

- D_cos: Cosine coefficient in a preregistered 24-hour HR rhythm model adjusted for activity and measured context; units: beats/min.
- D_sin: Sine coefficient in the same model; units: beats/min.
- D_sleep: Person-level mean sleep midpoint under a registered sleep-detection definition; units: hours relative to local reference time.

**Scope:** time: Candidate 14-day observation block; timestamps, time zone and valid-wear support preserved; duration is policy not universal sufficiency; space: peripheral cardiovascular rhythm and behavioral sleep, not a direct central circadian clock measurement; population: named catchment; shift-work status and missingness declared.

**Roles:** digital_activity_sleep = observation; physiological_rhythm = observation.

**Why this supports reconstruction:** Links temporal context to physiological state and prevents a daytime snapshot from being treated as a universal baseline. Sine/cosine coefficients avoid unstable phase estimates when amplitude approaches zero.

**Missing calibration:** Wearable/device bias versus ECG and sleep reference; Wear-time dependent missingness; Autocorrelation and activity-rhythm confounding; Day-level drift and person variance; Clock/time-zone changes and sleep-label reliability.

**Calibration deliverables:**

- Obtain independent simultaneous device/reference recordings across rest/activity/skin-tone/context coverage.
- Estimate autocorrelation and missingness model from repeated complete days.
- Use DLMO or a justified central-clock reference only if a later task claims central circadian phase.
- Freeze design columns and reference time; derive cadence/day support from coefficient precision and conditioning.

**AB2:** Retain AB1-D and tighten h by factor 2. Change in sine/cosine coefficients under a registered within-person schedule/context contrast plus stability across repeated blocks. Baseline, 3 and 12-month blocks; prespecified schedule groups. Missing: Phase-response nonlinearity, schedule assignment/overlap, light exposure, confounding and drift.

**Objection:** Behavior-adjusted rhythm remains model-dependent; wearable sleep midpoint cannot be relabeled melatonin phase or neural sleep architecture.

**Primary evidence:** [S04](https://pubmed.ncbi.nlm.nih.gov/34568865/).

## AB1-N — Time-resolved neural response

Can the record resolve a prespecified event-related neural contrast together with task behavior?

**Frozen estimands proposed:**

- N_erp: Mean deviant-minus-standard ERP voltage over a fixed task-specific time window and registered sensor cluster, selected before study scoring; units: microvolt.
- N_rt: Mean correct-trial reaction time under the fixed paradigm, with error rate retained as a separate observable; units: milliseconds.

**Scope:** time: Stimulus-locked millisecond timing; window and trial counts selected by independent reference-paradigm calibration; two sessions in candidate 14-day block; space: registered scalp observation field only; no unvalidated cortical-source localization; population: named adult catchment with sensory/task eligibility declared.

**Roles:** neural_electrophysiology = observation; task_behavior = observation; sensory_task_input = controlled_probe_not_therapeutic_neurostimulation.

**Why this supports reconstruction:** Provides an actual neural temporal response linked to behavior, rather than assuming peripheral biomarkers or questionnaires observe neural function.

**Missing calibration:** Trial noise/autocorrelation and retained artifact-free trial support; Session-to-session reliability; Electrode/reference/filter operator effects; Stimulus timestamp jitter; Amplitude dependence on task performance and sensory input; Cross-person covariance and age effects.

**Calibration deliverables:**

- Use a frozen ERP CORE-style paradigm and reference preprocessing, then calibrate repeat sessions independently.
- Prefer a preregistered window-average linear contrast over winner-picked peak amplitude.
- Estimate trial/session/person variance and artifact-related selection.
- Derive trial counts and people separately; no universal EEG channel count or MRI requirement.

**AB2:** Retain AB1-N and tighten h by factor 2. Add a preregistered left/right cortical-region hemodynamic task contrast with linked electrophysiological measurements, plus between-block change. Two named cortical ROIs and frozen hemodynamic model; baseline, 3 and 12-month blocks. Missing: Spatial sensitivity/registration, HRF uncertainty, physiological confounds, cross-modal residual covariance and motion bias; fMRI earns no credit outside this spatial task.

**Objection:** ERP is an accessible neural probe, not comprehensive cognition; the spatial extension may make this candidate unnecessarily expensive and should be separately ratified.

**Primary evidence:** [S05](https://escholarship.org/uc/item/9cf2f1xw), [S11](https://www.nature.com/articles/s41586-022-04492-9).

## AB1-P — Linked population variation

Can the study estimate population means and specified cross-domain associations without confusing repeated measurements with independent people?

**Frozen estimands proposed:**

- P_means: Population means of each prespecified AB1-M/I/F/D/N scalar target under declared sampling/selection weights; units: each target native unit.
- P_links: Three prespecified descriptive correlations: meal glucose AUC with HR recovery; immune TNF response with daily HR cosine coefficient; neural ERP mean with task reaction time; units: Fisher-z scale for precision calculation; report native correlations too.

**Scope:** time: Cross-domain records within same 14-day state block; exact timing/ordering accounted for; space: person-linked outputs from five tasks; unrelated participants cannot supply cross-domain covariance; population: fixed adult catchment, eligibility and sampling weights; not all humanity.

**Roles:** cross_domain_participant_linkage = observation; population_sampling_support = observation.

**Why this supports reconstruction:** Population reconstruction requires between-person structure; this task prevents unlimited data on two people from masquerading as population breadth. Correlations are descriptive, not causal biology.

**Missing calibration:** Between-person variance after measurement-error correction; Cross-domain covariance and common nuisance structure; Inclusion/sampling weights and missing joint modules; Family/household dependence; Age/sex/context support and weight instability.

**Calibration deliverables:**

- Use independent donors with all required linked modules, stratified to the declared population.
- Fit multilevel measurement-error model with repeat occasions separating within-person noise from between-person variability.
- Freeze only these descriptive edges before scoring; validate delta-method/Fisher-z coverage by simulation under actual sampling.
- If Gaussian linearization fails, retain this task unresolved rather than supply invented F.

**AB2:** Retain AB1-P and tighten h by factor 2. Fixed site-A versus site-B difference in the same means/associations, plus change across baseline, 3 and 12-month blocks. Two named settings with overlap; optional age extension to 18-80 must be separately specified and is not automatically covered. Missing: Selection overlap, site measurement invariance, attrition, site-by-person response covariance; two sites do not establish universal random-site transport.

**Objection:** The selected correlations are arbitrary but falsifiable cross-domain probes; evidence has not established these particular edges as privileged biological coordinates. Their inclusion is a policy choice.

**Primary evidence:** [S01](https://www.nature.com/articles/s41591-020-0934-0), [S04](https://pubmed.ncbi.nlm.nih.gov/34568865/), [S06](https://www.nature.com/articles/s41467-021-25960-2), [S11](https://www.nature.com/articles/s41586-022-04492-9).

## Optional AB2-NP — Controlled cortical perturbation

The additional target is a within-person active-minus-sensory-matched-sham evoked neural response in a preregistered artifact-free window and observation region. It requires verified assignment, target engagement, sham/sensory control and electrophysiological observation. Diagnostic EEG/fMRI or an oddball task cannot supply this intervention contrast. A fixed neural target does not certify whole-brain coverage.

A separately validated and approved research protocol is required before choosing stimulation site, parameters or analysis window; none is prescribed here. Missing calibration includes device artifact, sensory coactivation, masking, exposure fidelity, trial/session dependence and between-person heterogeneity. [Ilmoniemi et al.](https://pubmed.ncbi.nlm.nih.gov/9427322/) motivates the perturbation-observation distinction; [the sensory-artifact experiment](https://www.nature.com/articles/s41598-023-29920-2) gives a concrete identification objection. This is the optional AB2-NP extension and does not gate core AB2. A claim to the extension must satisfy its own requirements; diagnostics cannot silently substitute for perturbation.

## Parameterized precision targets

For every registered functional c_j define a native-unit half-width h_j and variance limit (h_j/z_j)^2. Candidate policy h_j=delta_star_j/2 requires an independently justified biologically meaningful resolution delta_star_j. Instrument calibration alone cannot determine which differences matter biologically. If such a resolution is not defensible, the named target remains unresolved; do not substitute the competing study's standard deviation or a universal N. A proposed 95% familywise interval coverage and its multiplicity rule are policy choices, not claims established by the cited papers.

AUCs, fixed-window means, paired differences and harmonic coefficients can be linear functionals under explicit models. For AUC weights w and joint covariance R, variance is w^T R w. Subtracting a noisy baseline creates shared error across timepoints. Peak selection, cell-type composition, correlations and latent kinetic rates need additional models. The finite-task API cannot turn these into exact Gaussian targets by assertion; inappropriate local linearizations must remain unresolved.

AB2 half-width halving divides the corresponding variance limits by four. Under an independent normal-mean model this requires four times the information, not necessarily four times enrollment: better measurements or allocation can also change information. Extra contrasts, times and subgroups require joint precision calculations. Redundant arm labels create no new rank; more cells do not create donors.

## Concrete calibration protocol

- C1: Ratified task definitions and native-unit meaningful-resolution dossier; blinded task relevance/measurement review before comparing studies.
- C2: Independent crossed donor x occasion x batch x device reference data, with paired technical replicates and dense time/reference measurements as appropriate.
- C3: Estimated operator H, residual R, between-person B, nuisance blocks and uncertainty envelope; effective independent units explicit.
- C4: Precision-target derivation using H^T R^-1 H, random effects and frozen c_j; choose cadence/repeats/N jointly, not a universal N.
- C5: Operating-characteristic simulations at lower/upper plausible calibration bounds, including censoring/missingness/nonlinearity and nuisance sensitivity.
- C6: Source-bound authority and machine input only after h_j,H,R,P definitions are available; biology utility evaluation remains separate.

Use an independent crossed donor-by-occasion-by-batch/device calibration design. Technical replicates estimate assay noise; repeated occasions separate within-person biological variation from between-person variation. Dense criterion acquisition calibrates interpolation, filtering and timestamp bias. Freeze H, R, nuisance structure and uncertainty envelopes before comparing candidate studies. Simulate the actual estimator under censoring, informative missingness and plausible misspecification. Enrollment, cadence and repeats must jointly satisfy every task requirement across the accepted envelope. Calibration sample size itself should target precision of these operator/variance estimates; no pilot N is invented here.

Freeze the prior independently and expose prior-only precision and acquired variance reduction. A strong prior can meet a loose posterior target before anyone is measured. For claims about acquired population knowledge, additionally report likelihood-only identifiability/precision or a separately ratified baseline-relative requirement. This is a distinction between claims, not a blanket Bayesian penalty or an unannounced change to the finite-task API.

## Executed adversarial challenge

The worked example [audit_depth_population_tradeoff.py](../scripts/audit_depth_population_tradeoff.py) uses a deliberately invented normal random-effects model: independent people have between-person variance B=1; conditionally independent readings have noise variance R=4. Its toy 95% interval half-width h=0.1 is **not an AB1/AB2 threshold**. Person-state variance is R/m; population-mean variance is (B+R/m)/N. The API replay uses a weak, explicit prior for separate scalar tasks; 34 analytic and semantic assertions pass. The likelihood limits below describe the same invented model:

- Two people with one million independent readings each have individual-state half-width 0.00392 but population-mean half-width 1.386.
- Two thousand people with one reading each have population-mean half-width 0.0980 but individual-state half-width 3.92.
- Unlimited per-person depth cannot remove the population variance floor B/N. Treating B as known already favors the tiny cohort; estimating it adds uncertainty.
- Any N with observation operator [1,0] leaves the second likelihood direction null. A large shallow cohort cannot buy missing neural support with molecular population count.
- Increasing hypothetical spend from $100M to $10B changes neither precision. Copies do not increment independent m.
- A balanced complete synthetic design can satisfy both toy requirements. The benchmark should not force every design to fail or arbitrarily penalize proof-of-concept work.

These comparisons concern different explicit estimands; they do not justify a global winner. Person-level depth, population sampling, cross-domain linkage and required perturbations are noncompensatory requirements when the suite claim needs all of them.

## Falsifiers and objections before ratification

1. Missing required domain/role support must fail or remain unknown; no compensatory score.
2. Ex-vivo immune response cannot be called an in-vivo human treatment effect. Diagnostic neural observation cannot be called randomized neurostimulation evidence.
3. Aliases, exported copies, redundant arms and zero-sensitivity channels must not increase supported information. Calibrated unit transformations and covariance propagation must preserve results.
4. Published cohorts/effects do not automatically calibrate our population, operators or tolerances. Each source's actual scope stays visible.
5. This panel privileges blood, accessible peripheral physiology and selected neural probes. It omits many tissues, pathologies, developmental processes and long-timescale dynamics. Calling it complete biological reconstruction would be false.
6. The proposed spatial imaging scope needs independent review of relevance and burden. Cortical stimulation belongs to optional AB2-NP, not core AB2. Missing an optional extension never vetoes a core claim.
7. The three cross-domain association edges, age range, 14-day block, repeat horizons and h/2 rule are falsifiable policy choices needing opposition and independent calibration. None is scientific certification.

## Primary source authority and access limits

- [S01: Berry et al. 2020, Human postprandial responses to food and potential for precision nutrition](https://www.nature.com/articles/s41591-020-0934-0). Human meal-response heterogeneity supports measuring dynamic metabolic responses; does not validate our task thresholds. Primary publisher abstract and PMC-indexed methods excerpt reviewed.
- [S02: Duffy et al. 2014, Functional analysis via standardized whole-blood stimulation systems](https://pubmed.ncbi.nlm.nih.gov/24656047/). Standardized induced immune-response measurements can characterize donor variation; our stimulus/time/target subset is a policy proposal. Primary research abstract reviewed.
- [S03: Cole et al. 1999, Heart-rate recovery immediately after exercise](https://www.nejm.org/doi/full/10.1056/NEJM199910283411804). One-minute post-exercise heart-rate drop is an established measurable recovery quantity; prognostic cutoffs are not adopted as precision targets. Primary publisher abstract and methods summary reviewed.
- [S04: Bowman et al. 2021, A method for characterizing daily physiology from widely used wearables](https://pubmed.ncbi.nlm.nih.gov/34568865/). Wearable HR and activity support model-based daily-rhythm estimation; behavior and physiological phase are distinct. Primary research abstract and indexed full-text excerpt reviewed.
- [S05: Kappenman et al. 2021, ERP CORE](https://escholarship.org/uc/item/9cf2f1xw). Standardized ERP paradigms and prespecified processing support bounded neural response measurements; source sample size is not benchmark saturation. Author repository abstract and primary author PDF excerpt reviewed.
- [S06: Squair et al. 2021, Confronting false discoveries in single-cell differential expression](https://www.nature.com/articles/s41467-021-25960-2). Independent biological replication must not be replaced by pseudo-replicated cells. Primary full-text sections reviewed in earlier council audit.
- [S07: Dissecting human population variation in single-cell responses to SARS-CoV-2, 2023](https://www.nature.com/articles/s41586-023-06422-9). Cell-type-resolved donor responses and tissue limits are empirically demonstrated; blood does not become lung or brain. Primary publisher abstract and tissue-limitation passage reviewed; no viral experiment proposed.
- [S08: An open-access dataset of naturalistic viewing using simultaneous EEG-fMRI, 2023](https://www.nature.com/articles/s41597-023-02458-8). Linked EEG/fMRI observations are feasible; no complete neural reconstruction claim follows. Primary indexed abstract/PDF summary reviewed; HTML fetch failed.
- [S09: Ilmoniemi et al. 1997, Neuronal responses to magnetic stimulation reveal cortical reactivity and connectivity](https://pubmed.ncbi.nlm.nih.gov/9427322/). Human stimulation with electrophysiological observation motivates a distinct cortical perturbation task. Primary abstract reviewed.
- [S10: Isolating sensory artifacts in the suprathreshold TMS-EEG signal over DLPFC, 2023](https://www.nature.com/articles/s41598-023-29920-2). Auditory/somatosensory coactivation can confound direct cortical interpretations; sham and artifact calibration are essential. Primary indexed full-text passages reviewed.
- [S11: Marek et al. 2022, Reproducible brain-wide association studies require thousands of individuals](https://www.nature.com/articles/s41586-022-04492-9). Small population associations require appropriate independent-person support; this is not a universal N minimum for within-person tasks. Primary full-text abstract/methods reviewed in earlier council audit.

## Reproduce the implemented synthetic example

```sh
python scripts/audit_depth_population_tradeoff.py --out build/depth-population-audit
```

This executes ten separate scalar-task evaluations and three support-gate variants. It checks posterior variance against the analytic result, source/model/task hashes, changed-budget equality, and failed/unknown missing-support states. Separate scalar receipts do not imply a joint independent covariance model. The input precision target is in invented units; it does not calibrate the biological tasks above. See [finite-task mechanics](FINITE_TASK_PRECISION_V1.md).
