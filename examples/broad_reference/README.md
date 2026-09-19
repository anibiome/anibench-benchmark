# Broad reference workload v1 — research candidate

This is an executable, normative research workload, **not a calibrated standard of sufficient human biological reconstruction**. It supplies a concrete conditional level ladder now: broad layer coverage, finite depth, within-person change, population precision, independent randomized contrasts and linkage must all pass. The actual `finite_suites_v1` evaluator executes every target; `causal_v2.contrast_information` constructs assignment information. There is no replacement solver, aggregate point score, modality bonus or requirement for successful treatment effects.

## What is frozen and why

The eight layer labels cover genomic context, transcript abundance, proteins, metabolites, physiology, digital dynamics, cognition and neural observation. The 16/16/16/16/4/4/4/4 dimensions are **test-coverage conventions**, chosen to exercise multivariate molecular breadth and several small nonmolecular operator blocks at inexpensive execution cost. They are neither estimated biological ranks nor evidence that these layers exhaust biology. Changing these conventions creates a different workload, not an improved score on the same workload. `coordinate_catalogue.json` declares every one of the 160 base/extension coordinates, synthetic role, units, estimand, operator and immutable status. There are no undocumented actual genes, biological axes or anatomical regions behind the indices.

All genomic coordinates are immutable reference context; S in the genomic population calculation is a reference occasion-specific measurement nuisance, not genomic mutation; there are no genomic change or treatment-response tasks. Real inherited variants are discrete and correlated: the synthetic Gaussian context block is not an allele-count calibration. Extension coordinates denote a separate declared latent block; copying the base measurements never supplies them. Digital coordinates are constant, daily cosine/sine and second-harmonic cosine coefficients of a synthetic channel. Sampling only at the same daily phase does not identify them. Neural base/extension labels describe electrical/spatial reference roles without asserting EEG/fMRI equivalence.

Limits are normative marginal likelihood-variance ceilings, not confidence bounds on simultaneous biological accuracy. R=4, B=1 and S=.25 are reference-model assumptions, not observed source estimates. Broad layer naming is a scope convention; no publication demonstrates sufficiency of this complete workload. No scientific reference is being claimed to justify these invented numerical conventions.

## Executable level contract

AB1 has 26 targets / 228 marginal functional checks; AB2 has 64 / 581. AB2 preserves every parent frame and tightens inherited variance limits fourfold, adds a separate coordinate band, an annual change and a factorial interaction. All required roles conjunct; unknown remains unknown, known absence fails, and likelihood precision rather than a strong prior determines attainment. Core neural requirements are observations. The named AB1-neural child adds controlled cortical assignment and matched peripheral control; diagnostics alone cannot pass that child, and stimulation is not a universal core requirement.

| Constraint | AB1 variance ceiling | AB2 ceiling |
|---|---:|---:|
| Person/occasion reference state | .25 | .0625 |
| Population mean | .01 | .0025 |
| Observed 30-day change | .5 | .125 |
| Randomized binary response contrast | .04 | .01 |
| Linked-population scalar reference task | .01 | .0025 |
| Complementary molecular/function task | .25 | .0625 |
| Annual occasion change | absent | .125 |
| Factorial difference-of-differences | absent | .01 |

The linked scalar task is a synthetic jointly collected response mean, **not an estimator of cross-domain covariance**. The complementary task has actual rows [1,1] and [1,-1]; either alone has rank one, both identify two states. This tests nonlinear complementarity without summing units or inventing independent information from layer counts. Other task receipts are marginal checks and cannot be summed into a joint information receipt.

## Conditional witnesses and frontier

Let d=m/[1+(m−1)ρ] for equicorrelated repeated measurements with 0≤ρ<1. Independent-person variance v=B+S+R/d. State variance is R/d, observed-occasion change variance 2R/d, population-mean variance v/N, balanced randomized binary contrast variance 4v/N and balanced factorial difference-of-differences variance 16v/N. Assignment inputs have specified ±1 coding; the existing causal helper normalizes the columns, and the interaction functional [0,0,2] restores the declared difference-of-differences. These equations are checked against actual receipts, independently of their implementation.

At R=4, B=1, S=.25 and ρ=0, AB1 state/change need d≥16. Population and binary requirements then each imply N≥150; balanced two-arm N150 passes. N160, two visits at days0/30 and depth16 is a convenient witness. AB2 needs d≥64; population requires N≥525, binary N≥525, interaction N≥2100. Balanced factorial N2100 passes, N2096 fails; N2112 is a convenient witness with four arms and days0/30/365. Counts mean complete linked hypothetical observations, not enrollment before attrition. These are conditional consequences of a frozen model, **not mandatory real-world sample sizes**. As depth tends to infinity the population floor (B+S)/N remains. Two people cannot meet the population targets however much is spent. Conversely huge N with depth1 cannot meet individual state/change limits.

The replay evaluates 14 actual request/receipt pairs including both witnesses, cross-level checks, extreme-depth two-person, huge shallow, redundant arms, missing links, temporal aliasing, absent/unknown neural and the optional cortical extension. The sensitivity replay evaluates another ten actual suites under changed R, B, S or repeat correlation. Each changed noise model has a different profile/model hash; compare the sensitivity as alternative assumptions, never as the same frozen scientific frame. In particular small positive repeat correlation caps attainable d, irrespective of copied rows or raw measurement count.

## Admission from a source-bound real collection

1. Extract named assays, tissue/compartment, unit, protocol timing, acquisition operator, jointly observed-person overlap and randomization contrasts from primary sources. Preserve unknowns. A publication N is never N for every modality or visit.
2. Freeze concrete observable identities and normalization constants before scoring. Select a biologically justified projection into a named reference block or publish a separately named native-unit profile. Baseline genotype enters context or prespecified effect modification, not mutable molecular response.
3. Supply the numerical H operator, with source/calibration provenance or an explicit assumption scenario. Measure repeat covariance R using suitable replicates and separate person/occasion variance where identified. Assay count, device label, number of genes and number of cells cannot instantiate H=I, diagonal R or independent people. Unmeasured directions remain unsupported.
4. Compile actual overlap/times/assignment into existing protocol/causal APIs; run each common frozen scenario with the finite suite executor. Report scenario-dependent attainment and unknown calibrations. Native source-coordinate charts remain available even when this mapping is missing.
5. External transport, individual outcome prediction and empirical learning plateau remain separate claims. No held-out treatment benefit is required for conditional planned collection capacity.

This prototype intentionally rejects `source_backed_real_study` inputs: it has a reference generating instrument, not a validated biological adapter. The immediately implementable public contribution is a named **broad-reference candidate workload plus native real-study architecture charts**. Biological admission requires the concrete mappings above, not an indefinite demand for all biology to be solved first. Tissue specificity, cell populations, rare variants, nonlinear dynamics, population heterogeneity/transport, measurement bias, dropout and causal interference are explicit omissions of this simple model. This reference workload does not by itself supply a biological mapping for any named study.

## Replay

Install AniBench, NumPy and pytest in your environment, then run these commands from this example directory:

```sh
python replay.py --out output
python -m pytest -q test_prototype.py
```

The output directory must not exist. Default replay writes only compact declarations, chart data and summaries; add `--receipts` to save each complete evaluator request and receipt. No source data, participant records, network access or external services are used. `standard.json`, `profile-declarations.json` and `figure-data.json` are frozen generated outputs distributed with this example. Full trusted profiles are regenerated by `profiles()`; the compact declaration lists their exact hashes, target IDs and target frames. Source bindings identify canonical sorted compact JSON objects rather than the pretty-printed file bytes. `PACKAGE_MANIFEST.json` binds distributable file bytes.

`manuscript-prose.md` supplies original explanatory text. Code and documentation are original Apache-2.0 material; all numbers describe synthetic reference models, with no source-derived participant material.

The replay is a standalone deterministic example, not a concurrent model-serving API. A supplied registry or metadata inconsistent with the current frozen model is rejected before geometry is computed. Changing R/B/S regenerates task and profile identities; stale registry reuse is regression-tested. Old exploratory runs outside this package are not distributable evidence.
