# Scientific foundation and open research questions

Status: research design and mathematical audit, 2026-09-17. This document
re-examines the benchmark from its scientific purpose. It does not silently
change a versioned scoring contract or claim that every proposed empirical
task is implemented. Earlier category names, reference coordinates, and
release decisions are revisable hypotheses, not laws of biology.

## The question

How much does a human study help us observe, predict, and change a person's
biological trajectory, and how reliably does that knowledge transfer to other
people and conditions?

The destination is increasingly complete biological simulation. No present
benchmark can measure a percentage of all human biology: the state space,
relevant interventions, timescales, and observation limits are not known in
full. A useful standard measures progress on explicit, reproducible questions
and can add harder questions without moving old goalposts.

## Start with a partially observed dynamical system

For person i, biological state z, exposure u, context c, and assay j:

```text
dz_i(t) = f_theta(z_i(t), u_i(t), c_i(t)) dt
          + G_theta(z_i(t), u_i(t), c_i(t)) dW_i(t)
y_ij(t) = h_j(z_i(t), specimen, device, batch) + epsilon_ij(t)
```

This is a modeling framework, not a claim that a particular stochastic
differential equation describes every biological process. Discrete events,
delays, multiple compartments, and discontinuous interventions may require
other models. Molecular, microbial, physiological, functional, cognitive,
psychological, and digital measurements are distinct observation operators.
Some measure related biology; none earns information merely by having a
different name.

Biophysics constrains admissible models where justified: units must match;
concentrations and selected rates must stay nonnegative; compartment fluxes
must respect the relevant balance equations; causal effects cannot precede
exposure. Organisms are open systems, so neither total-body energy nor mass
should be assumed constant without accounting for exchange. Mechanistic
constraints must state their domain and measurement error. A fashionable
pathway label is not a conservation law.

## Separate what was collected from what was learned

The main benchmark evaluates a study's biological learning capacity. It does
not require a beneficial intervention, a positive endpoint, a trained model, or
publication of the underlying participant data. A precise null treatment
effect can be informative; a dramatic reported improvement does not by itself
establish a deep biological record.

Four outputs answer different questions:

1. **Study evidence profile.** People and their denominators, duration, sampling
   times, assay-level target counts, tissue/context coverage, assignment,
   exposure, linkage, missingness, and access. These facts can be useful even
   when no validated observation model exists.
2. **Conditional design information.** What the declared observation, noise,
   assignment, and dynamical model predicts the design could identify. Compare
   uncertainty scenarios, not just the most favorable assumptions.
3. **Demonstrated learning.** Reproducible performance on sealed prediction,
   perturbation, personalization, and transfer tasks with explicit baselines.
   This depends on both the dataset and the learning procedure; it is not an
   intrinsic data quality score.
4. **Intervention outcomes.** Effect sizes, responder fractions, durability,
   functional change, harms, or specified aging-marker changes. These require
   their own endpoint, comparator, denominator, horizon, and uncertainty. They
   are optional outcome benchmarks, not multipliers of the capacity benchmark.

The first two are the main AniBench product. The last two are separate,
optional evaluations. Empirical calibration can test the capacity model's
scientific usefulness without making a trial's favorable results an admission
requirement. An observed biological response used to estimate noise or dynamics
is distinct from awarding points for the direction or size of that response.

"Information compressible into intelligence" names the ambition: a linked
record from which increasingly capable models can learn reusable biological
structure. File compression ratio, raw byte count, and a list of assays do not
measure that capacity. Noise, duplicate signals, measurement error, incomplete
linkage, and unobserved biological directions must be distinguished. The
conditional information model below makes one explicit approximation to this
question; it is not a universal conversion from bytes to intelligence.

The current explorer implements the source profile and the existing conditional
six-family evaluator. Its two design examples are synthetic. It does not yet
implement the complete dynamical and empirical program described here.

## What the information equation actually means

Under a linear Gaussian observation model with parameter-independent noise,
the likelihood information for one joint observation is

```text
F = A^T R^-1 A
P_post = (P_0^-1 + F)^-1
information_gain_nats = 0.5 log det(I + P_0^(1/2) F P_0^(1/2))
```

P_0 is a stated prior covariance, A the sensitivity to the target parameters,
and R the full noise covariance. The core stores prior **precision** Lambda_0
= P_0^-1. Its log10 contraction is information_gain_nats / log(10). This is an
exact expected information gain in that Gaussian model. For nonlinear
biological models, local Fisher information is an approximation and may miss
multimodality, parameter symmetries, and model misspecification.

Independent event contributions can be summed. Correlated observations must
be modeled jointly or use a justified effective-count model. Repeated
measurements from one person are not automatically independent people. For
m equicorrelated observations of the same scalar signal, unit marginal noise,
and correlation rho, effective information is m / (1 + (m - 1) rho).

The quantity is invariant to invertible observation-unit transformations
when A and R transform together. Re-expressing parameters also preserves it
when both information and prior transform together. Its eigenvalue spectrum
shows which directions are resolved and which remain weak. A single log-volume
can hide an unresolved direction, so spectrum, target uncertainty, and
identifiability accompany it.

A biological target and prior remain scientific choices. Comparisons must
state them and examine sensitivity. Restricting two designs to a shared target
does not establish that target as a universal definition of human biology.
[Jagalur-Mohan and Marzouk](https://jmlr.org/papers/v22/20-1023.html) give a
formal treatment of mutual-information experimental design and its optimization.

## Movement requires more than elapsed time

For a specified dynamical model, sensitivities propagate through the dynamics:
A_t = H_t Phi(t, t_0), or the corresponding parameter-sensitivity equations.
The joint information depends on those sensitivities and cross-time noise.
Duration, event count, and temporal leverage remain useful descriptors, but
are not by themselves evidence that velocity, recovery, or a treatment
response can be predicted.

For example, y(t) = theta exp(-t) with constant observation noise loses
information about initial amplitude when the sole measurement is moved later.
Adding a late measurement while retaining the early one helps under the
declared independent-noise model. “Longer” and “more informative” are therefore
different statements. Sampling must resolve the relevant biological timescale;
derivatives amplify measurement noise and cannot be inferred from nominal
sampling frequency alone.

## Perturbation and personalization need identifiable questions

Record intervention identity, dose, route, timing, assignment probability,
realized exposure, adherence, comparator, and the outcome horizon. A randomized
active-versus-active trial identifies its assigned policy contrast under its
assumptions; it does not separately identify every shared ingredient. An
observed natural perturbation can inform dynamics while still requiring
confounding assumptions for causal claims.

Individual predictions, treatment-effect heterogeneity, and adaptive treatment
policies require different tests. Repeated digital measurements do not establish
a personalized intervention benefit. The counterfactual for the same person
under a different intervention is generally unobserved. Report identified
estimands, overlap, attrition, missingness, interference assumptions, and
sensitivity analyses instead of scoring “perturbation: yes” as causal certainty.

## Empirical tests aligned to the intended biological claim

| Question | Required held-out structure | Useful outputs |
|---|---|---|
| Reconstruct unobserved biology | Sealed targets; held people; assay and batch checks | Target-specific error, calibrated uncertainty, incremental value over available measurements |
| Predict movement | Past-only inputs; held future windows and people | Horizon-specific trajectory error, direction, interval coverage, improvement over carry-forward |
| Predict intervention response | Held perturbations and contexts where identification permits | Error in perturbation-specific change; randomized estimand; uncertainty and support |
| Learn the individual | Locked prediction followed by new observation | Prequential gain over the population model using the same history |
| Transfer knowledge | Held site, cohort, device, or assay | External performance and calibration; exact harmonization and overlap |
| Guide a decision | Prospective or identified policy evaluation | Declared utility, harm and burden, uncertainty, comparison with a fixed policy |

Always include strong simple baselines and controls for wrong person, wrong
time, leakage, batch, and target shuffling where scientifically appropriate.
Bootstrap and split at the independent sampling unit; correlated molecular
features and repeated days do not multiply the number of independent people.
Keep negative results and unresolvable tasks visible. A failed model does not
prove that its study contains no useful biology.

This emphasis is supported by recent perturbation research:
[Systema](https://www.nature.com/articles/s41587-025-02777-8.pdf) shows that
systematic variation can inflate apparent perturbation prediction performance.
[Perturbation-method benchmarking](https://www.nature.com/articles/s41592-025-02980-0)
tests generalization across cellular contexts and perturbations. These motivate
controls and held-context tasks in AniBench; results in cells are not validation
of a human-trial benchmark.

## Relevance, trade-offs, and an open-ended ladder

Relevance is conditional on a question: state estimation, recovery dynamics,
response prediction, or decision improvement. Where an aggregate utility is
useful, its task distribution, units, loss, costs, and weights must be stated
before inspecting winners and tested for sensitivity. There is no scientific
derivation for universal weights such as “40% breadth, 30% depth, 30% time.”
Likewise, an assay's number of reported features is not its number of
independent, identifiable biological dimensions.

Native coordinates and task-specific comparisons can show different leaders.
Use partial order or Pareto fronts when objectives conflict; report uncertainty
or rank instability where point differences are not decisive. Do not claim
that these are probabilities of clinical benefit or percentages of a complete
human simulator.

A level should freeze a task set, target population, biological resolution,
prediction horizons, intervention space, split protocol, and defensible error
tolerances. A later level can expand these while preserving earlier results.
Millions of people and petabytes per person may increase useful resolution,
but volume alone can also add redundant, biased, or inaccessible data. The
scientific endpoint is reliable new predictive and interventional knowledge.

## Executable mathematical audit

`tests/test_first_principles.py` verifies unit and parameter invariance,
correlated-repeat effective information, unbounded independent-sample growth,
noise and nuisance penalties, and the elapsed-time counterexample. It also
rejects non-finite and empty model geometry. The existing compiler tests add
event deduplication, source linkage, assignment support, and temporal-order
checks. Nuisance projections reject repeated, fractional, and boolean coordinate
indices so a malformed projection cannot manufacture dimensions. These tests
establish mathematical properties of declared models;
biological calibration still requires real held-out evidence.

Before replacing any existing formula, publish its estimand, derivation,
assumptions, counterexamples, sensitivity analysis, and migration impact.
Correcting an earlier agent's work should improve the scientific argument and
the executable evidence together.
