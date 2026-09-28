# Reproduce the native-mean pilot

This exploratory example compares **MIPACT and DIRECT PLUS** on ten fixed
population-mean precision tasks: two each for molecular measurements, physiology,
device activity, cognition and brain structure. It does not score whole-study
quality, certify AB1/AB2, or measure a percentage of human biology understood.
Blood pressure and body mass do not represent all physical function.

## Run

For the exact Python 3.12.13, locked dependency and Node 24.18.0 setup, follow
[the reproduction guide](../../docs/REPRODUCING_TASK_REFERENCE.md). The guide
distinguishes ordinary package use from byte-exact receipt replay.

Install the matching AniBench release and its locked dependencies, with Node.js
available for the workbench's shared SVG renderer. From this directory:

```sh
python replay.py --out replay-output
```

For a development checkout, from the repository root:

```sh
PYTHONPATH=src python examples/native_mean_pilot/replay.py --out pilot-replay-output
```

Use `--node /path/to/node` when Node.js is not on PATH. The output directory must
not exist. No network request, source download, account, or participant data is
needed. The example creates `pilot.json`, `chart.svg` and `receipt.json` only after
the checks pass; existing files are never overwritten.

The replay uses installed `compile_summary_task` and `evaluate_benchmark`.
It verifies the content identities of the frozen inputs, recompiles all 360
summary derivations, checks six result receipts, and compares regenerated chart
data semantically and byte-for-byte with both the bundled and installed
`pilot.json`. The SVG uses the installed workbench's `pilotRows` and `chartSVG`
functions and must match `expected-chart.svg` byte-for-byte. There is no second
scoring formula in this example.

Exact receipt identity includes implementation and runtime versions. See
`manifest.json` for the reference environment. A different Python, NumPy,
jsonschema or scientific implementation may fail exact replay even if a numerical
result looks similar. A mismatch is reported, never silently blessed. Use the
matching release environment for exact reproduction.

## Meaning and limits

Each domain has a fixed denominator of two equally weighted tasks. Missing
precision remains unknown; it is not zero, missing acquisition, or evidence of
low study quality. DIRECT PLUS's source-reported hippocampal volume is retained
as a separate native fact: its bilateral aggregation was not established, so the
bilateral task remains unknown. Its fasting plasma glucose method is supported
by Supplemental Methods 2, linked in `sources.json`.

Three precision-target factors (0.5, 1, 2) and six coherent variance/rounding
scenarios are evaluated. The rounding scenarios shift every available source SD
to its lower or upper rounding boundary before applying the whole-variance
multiplier. The envelope is sensitivity plus unresolved task mass, not a
confidence interval. Table-header participant counts assume per-variable
completeness; the published summaries do not independently verify that condition.
Independent-person sampling and source-specific population support are explicit
assumptions. Laboratory scales and protocols are not empirically harmonized.

The new round native-unit thresholds were chosen **after inspecting the source
studies, before numerical scoring**. They are disclosed research conventions,
not clinical cutoffs, blinded calibration or independently validated measures of
biological sufficiency. Some thresholds inherit earlier illustrative policies.
Comparisons concern precision for each study's own population, not a shared
population effect or intervention efficacy. No treatment-effect magnitude enters
these baseline-mean task scores. The separate hypothetical controlled-contrast
experiment is outside this example.

## Files and provenance

- `inputs.json`: content-addressed task profiles, score profiles, public aggregate
  summaries, assumptions and expected canonical identities. Repeated inputs are
  shared; full historical result packets are not duplicated.
- `pilot.json`: exact reviewed chart-data packet, including reference conventions,
  selected-source locators and result identities.
- `sources.json`: factual aggregate extractions, study metadata, source locators,
  supplemental-method links and original snapshot hashes.
- `manifest.json`: file hashes and reference runtime identity.
- `expected-chart.svg`: reviewed default comparison rendered by the workbench.

Primary reports: [MIPACT](https://pmc.ncbi.nlm.nih.gov/articles/PMC7414690/)
and [DIRECT PLUS](https://pmc.ncbi.nlm.nih.gov/articles/PMC9071484/).
The [DIRECT PLUS supplementary files](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9071484/supplementaryFiles)
support the fasting collection and assay definitions. Source hashes identify the
reviewed snapshots; obtaining fresh bytes from an external service may produce a
different serialization. A hash establishes identity, not scientific validity.

This package redistributes factual numeric extractions and authored metadata,
not full articles, supplement text, figures or participant records. Original
publications retain their own licenses and attribution requirements; a public
URL does not grant unrestricted redistribution. Example code follows the
repository code license; extracted factual data and source attribution follow
the repository's `LICENSE-DATA` policy. No blanket license for original source
materials is asserted here.
