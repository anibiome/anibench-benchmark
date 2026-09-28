# Reproduce the four task-reference paper figures

These files reproduce chart geometry and values from public aggregate data.
They do **not** rerun participant-level preprocessing, model fitting, bootstrap
resampling, or the full reference sweep. No participant records are included or
required. The empirical result hashes identify the frozen source results; a hash
does not make those full results or their inputs part of this package.

From the repository root, with Python 3.12 and Matplotlib 3.11.0 installed:

```sh
python paper/task_reference/figures/plot.py --out figure-replay
```

The output directory must not already exist. The command creates four SVGs,
four 220-dpi PNGs, and a receipt binding the aggregate data, script, renderer
version and generated files. It runs offline after dependencies are installed.
Only Matplotlib and the Python standard library are required for chart replay.

The first three SVGs alongside this README preserve the published workbench images
byte-for-byte. The replay fixes SVG element IDs and omits timestamps. Therefore
raw SVG hashes may differ from the preserved images even when all geometry,
labels and plotted values match. In the documented environment, all three
replayed SVGs match the preserved figures exactly after removing metadata and
consistently normalizing element IDs. Renderer/font version changes can alter
layout; the figure-data files remain the numeric reference.

## Figure 1: conditional design frontier

`conditional_frontier.json` has 32 feasible sampled design points. The curves
hold four technical repeats and standard reference resolution fixed, vary repeat
correlation and technical depth, and require both declared noise scenarios.
Each plotted N is the smallest compatible balanced integer allocation at that
grid point. Dashed horizontal lines are continuous large-depth limits, not
attainable balanced integer counts. The chart does not interpolate a validated
biological optimum or estimate actual collection cost.

The formulas and coordinate scales are specified in
[the complete v0.4 recipe](../../../docs/REFERENCE_RECIPE_V04.md).
At correlation 0.2, AB1 depth 128 gives continuous N >= 1297 and balanced N =
1298; AB2 depth 512 gives N >= 5137 and balanced four-cell N = 5140.
All 32 exported points were independently checked with exact rational arithmetic.

Caption: **Depth cannot replace independent people.** Conditional retained-person
boundaries for the hypothetical v0.4 recipe, with all required support, four
technical repeats and both noise scenarios. Lines begin where individual
precision is feasible. These are model-dependent reference calculations, not
ideal-trial recommendations or biological sufficiency claims.

## Figure 2: temporal sampling

`temporal_sampling.json` has 18 aggregate records: two annotation targets,
three sampling placements and three sample durations. Solid curves are held-out
exact design RMSE; dashed curves use training-estimated covariance. The 108
eligible nights belong to 68 people split 34/12/22 across training, calibration
and evaluation. Nights remain grouped by person. The horizontal lines are the
illustrative 20- and 10-minute target limits. The plot shows point estimates,
not uncertainty bands or formal significance results.

Caption: **Equal recording time can reveal different amounts.** Training-predicted
SE and held-out exact sampling RMSE for total-sleep and REM annotation minutes.
Circular blocks can wrap. The experiment samples existing scored annotations;
it does not evaluate newly acquired EEG, waveform quality or persistent traits.

Source: [Sleep-EDF Expanded 1.0.0](https://physionet.org/content/sleep-edfx/1.0.0/).

## Figure 3: molecular estimator validation

`molecular_validation.json` has six aggregate points: two native targets and
three estimators. The data preserve the frozen observed RMSE and person-bootstrap
95% percentile limits. Each target used 1,000 successful bootstrap refits and
32 held-out people, with 53 training and 21 calibration people. The targets are
released microbial relative abundances; they are not absolute organism counts,
physiological fluxes or calibrated latent biological states.

Caption: **The inverse estimator underperformed simple baselines.** Held-out
native-unit RMSE with 95% person-bootstrap intervals for two released microbial
outputs. Bootstrap refits independently resampled the fixed training,
calibration and test partitions. This figure shows prediction error and its
uncertainty; it does not plot risk calibration, rank study quality or measure
treatment benefit. Interval overlap alone is not a formal paired comparison.

Source: [Primary HMP2 study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6650278/).

## Figure 4: real-source native mean precision pilot

`native_mean_pilot.json` is a projection of the exact canonical result packet
[examples/native_mean_pilot/pilot.json](../../../examples/native_mean_pilot/pilot.json),
whose SHA-256 is recorded in the dataset. It selects default SE factor 1 and
preserves all six coherent scenarios. It does not rerun the evaluator or change
any target decision. The ten domains-by-study rows have two equally weighted
targets per domain; a passed task contributes 50 percentage points. The data
include the ten task definitions, source result/profile identities, and all
scenario-level target states so the plotted bounds can be independently checked.

The lower endpoint is the minimum confirmed-pass percentage across scenarios;
the upper endpoint is the maximum passed-plus-unknown percentage. Solid segments
show variation in confirmed passes across scenarios. Dashed extensions show
additional unresolved task mass. The envelope is an outer bound, not a confidence
interval, probability of success, or claim that all domains attain their best
endpoints simultaneously. No overall score is computed.

| Domain | MIPACT | DIRECT PLUS |
|---|---:|---:|
| Molecular | 0–50% | 0% |
| Physiological | 0% | 0–50% |
| Digital | 0–50% | 0–100% |
| Cognitive | 0–100% | 0–100% |
| Structural brain | 0–100% | 0–50% |

At these particular default limits, every domain has a zero lower bound across
all six scenarios. This is not a finding that either study is worthless. Missing
precision remains unknown, including both cognitive tasks and unsupported brain
measurements; DIRECT PLUS bilateral hippocampal interpretation remains unresolved.
The brain panel concerns structural volumes, not neurophysiology or a broad
neural capacity score. Source populations, operators and sampling assumptions
remain distinct. Cross-operator comparisons are conditional. Thresholds were
selected after source inspection and frozen before scoring; this is a draft
pilot, not independently calibrated biological sufficiency.

Caption: **What do the reported data resolve?** MIPACT and DIRECT PLUS compared
on the fraction of two declared own-population mean-precision tasks met in each
of five domains. Default SE limits and all six variance/rounding scenarios are
retained. Solid ranges show scenario variation in confirmed passes; dashed ranges
retain unknown task mass. These are not whole-study quality, treatment-benefit
or AB1 percentages. Each study concerns its own population and source operator.

Sources: [MIPACT](https://pmc.ncbi.nlm.nih.gov/articles/PMC7414690/) and
[DIRECT PLUS](https://pmc.ncbi.nlm.nih.gov/articles/PMC9071484/).

## Provenance and changes

`manifest.json` pins every aggregate data file and preserved SVG. The plotting
script checks data hashes before rendering. The published summaries come from
separate frozen experiments; no figure is evidence that the complete AniBench
reference has been empirically calibrated. The scripts and generated figures
are ANI-authored; primary-source links identify underlying study material, not
third-party figures copied into this repository.

Code license: Apache-2.0, consistent with the repository license. Empirical
source data remain subject to their original source terms. To propose corrected
aggregate values, include the source result identity, reason and a new manifest;
do not silently change a published figure dataset.
