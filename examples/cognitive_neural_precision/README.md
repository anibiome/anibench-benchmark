# Cognitive and neural precision: reproduce the published aggregates

This example evaluates **12 measurement records from seven human study
families**: ACTIVE, the Dallas Lifespan Brain Study, AIBL, Rhineland, MAPT,
ADNI and PPMI. It asks how precisely each source-selected sample estimates a
specified measured population mean. It does not rank whole studies, measure
cognitive health, establish anatomical accuracy, or certify AniBench 1.

## Run offline

Install the matching AniBench package and dependencies, then run from this
directory:

```sh
python replay.py --out replay-output
```

For a development checkout, from the repository root:

```sh
PYTHONPATH=src python examples/cognitive_neural_precision/replay.py --out cognitive-neural-output
```

No network request, account, article download, participant data, sibling example,
Node.js or private workstation path is needed. The output directory must be new.
After verification, the script writes `results.json` and `receipt.json`.

The replay calls the installed canonical `compile_summary_task`,
`functional_likelihood_precision` and `evaluate_benchmark`. It verifies all
content-addressed inputs, recompiles 216 derivations, reproduces 72 native
diagnostics and 24 single-task suites, and checks the full results and output
bytes against `expected-results.json`. Each suite has six scenarios, giving 144
task-scenario evaluations. These repeated calculations are not independent
studies. Exact receipts bind implementation and runtime versions; see
`manifest.json`. A mismatch fails explicitly rather than silently accepting a
numerically similar result.

## What can be compared

| Question | Families in this example | Criterion |
|---|---|---|
| Mean source-administered MMSE score | ACTIVE, DLBS, AIBL | SE ≤ 0.1 points on the 0–30 scale |
| Mean left hippocampal pipeline output | MAPT, Rhineland | SE ≤ 0.05 cm³ |
| Mean right hippocampal pipeline output | MAPT, Rhineland | SE ≤ 0.05 cm³ |
| Mean source-defined frontal cortical thickness | ADNI, PPMI | Native precision only |
| Mean source-defined occipital cortical thickness | ADNI, PPMI | Native precision only |

The MMSE and unilateral-volume criteria reuse earlier illustrative research
conventions. They are not validated clinical cutoffs. Factors 0.5, 1 and 2 show
criterion sensitivity; they were not changed to select a winner. No cortical
threshold was invented. Its native diagnostic uses an inert API variance-limit
placeholder and emits no pass decision or percentage.

Every scored suite contains one named task. Its 0% or 100% describes that one
precision requirement, not an entire biological domain. Each source-specific
population, operator and timepoint remains bound to its own scientific frame.
Juxtaposing native precision does not create a common-population treatment
contrast or authorize cross-frame `anibench compare` rankings.

### Important distinctions

- **MMSE selection:** ACTIVE excludes low baseline scores; DLBS selects healthy
  volunteers with higher baseline scores; the two AIBL groups are selected
  healthy amyloid strata. Narrow dispersion and ceiling effects can improve
  mean precision without improving cognitive sensitivity. Two AIBL subgroups
  remain one family. Table-header N assumes per-item completeness where not
  independently verified; DLBS's other table fields show missing values.
- **MRI operators:** MAPT uses SACHA and Rhineland FreeSurfer 6.0. Equal native
  tolerances compare each pipeline's own output precision; no calibrated
  crosswalk to common anatomical truth is asserted. Left and right marginal
  SDs are never added to manufacture bilateral precision.
- **Cortical operators:** ADNI 107 and PPMI 20 are additional source-selected
  controls processed in the same paper using FreeSurfer 5.1 and a comparable
  Siemens/TI 900 ms acquisition class. Exact hemispheric/vertex weighting of
  lobar outputs is not fully specified, so these are shared-paper quantities;
  external studies cannot join merely because their labels match. The source
  mentions 137 additional participants elsewhere, but its detailed group counts
  total 127; this example uses 107 and 20. Failure to detect a group difference is
  not proof of measurement equivalence.
- **Variance assumptions:** independent-person Gaussian mean sampling gives
  SD²/N, conditionally on source population and completeness. q1/q2 apply whole
  variance multipliers 1 and 2. Rounded-low/high scenarios move the reported SD by
  half its last displayed unit before applying q. These are coherent sensitivity
  scenarios, not confidence intervals or measurement-bias calibration.

MMSE does not replace two-choice reaction time or antisaccade accuracy. These
examples do not modify the separate ten-target native-mean pilot, infer
longitudinal precision from baseline N, or award causal capacity from an MRI.

## Files and sources

- `inputs.json`: shared content-addressed task/profile/summary/evidence objects
  and expected canonical identities.
- `sources.json`: factual aggregate extractions, source URLs, locators,
  assumptions, publication/ethics states and original snapshot hashes.
- `expected-results.json`: the reviewed result packet reproduced exactly.
- `manifest.json`: package-file hashes and reference runtime.

Primary reports: [ACTIVE](https://pmc.ncbi.nlm.nih.gov/articles/PMC2916176/),
[DLBS](https://pmc.ncbi.nlm.nih.gov/articles/PMC12106762/),
[AIBL](https://pmc.ncbi.nlm.nih.gov/articles/PMC4299972/),
[Rhineland](https://pmc.ncbi.nlm.nih.gov/articles/PMC13441870/),
[MAPT](https://pmc.ncbi.nlm.nih.gov/articles/PMC4652787/), and
[ADNI–PPMI methods comparison](https://pmc.ncbi.nlm.nih.gov/articles/PMC5943040/).
Snapshot hashes identify reviewed serializations; refreshed provider bytes may
differ. A source hash proves identity, not completeness or scientific validity.

Only factual numeric extractions and authored metadata are redistributed here,
not full articles, figures or participant records. Source publications retain
their own licenses, including restrictions where applicable. Public access is
not a blanket redistribution license. Code follows the repository code license;
factual extractions and attribution follow `LICENSE-DATA`.
