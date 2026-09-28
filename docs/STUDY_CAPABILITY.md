# Evaluate what a study can measure

`anibench study-capability` evaluates a design or collected acquisition record
against a fixed set of biological measurement questions. It reports six category
percentages. A percentage means **the share of this reference's requirements met**,
not the share of human biology understood or the probability a treatment works.

| Category | Question |
| --- | --- |
| Individual measurements | Can the acquired measurements resolve the specified native quantities for a person? |
| Differences between people | Can the study estimate the specified population variances and covariances? |
| Change over time | Can observations resolve changes at the reference timescales? |
| Controlled effects | Can randomized groups identify a specified change contrast? |
| Response differences | Can the design resolve the specified modifier-by-treatment contrasts? |
| Replication across sites | Can it compare the specified effects in two observed settings? |

The last category is a comparison of observed sites, not proof of transfer to
every new population. Treatment benefit, study expense, publication and ethics
status do not add points to any category.

## Run locally

Install the package from the checkout with `python -m pip install .`. From the
repository root, validate and then evaluate the included hypothetical example:

```sh
anibench study-capability examples/study_capability_candidate/minimal.json --validate-only
anibench study-capability examples/study_capability_candidate/minimal.json --out my-study-result
```

The same interface is available as
`python -m anibench.study_capability_candidate`. After a wheel install, the example
is a package resource. Copy it to your own working directory without requiring
the source checkout:

```sh
python -c 'from importlib.resources import files; from pathlib import Path; Path("example.json").write_bytes(files("anibench").joinpath("examples/study_capability_candidate/minimal.json").read_bytes())'
anibench study-capability example.json --out my-study-result
```

Use a new output directory. The evaluator writes the result, compressed canonical
calculations, selected reference and checksums. It does not upload input data or
require an account. Place governed inputs and outputs in an appropriately private
directory. Validation checks structure and supplied immutable bindings; it does
not independently authenticate a source claim.

The default is `native36-capability-v3`, at `--resolution standard`, with the two
normative measurement-noise scenarios. `--resolution fine` halves the standard
standard-error limits and quarters variance limits. Select
`--noise-profile common-noise-grid-v1` for the separate four-scenario sensitivity
analysis. Explicit `--study-profile native36-operator-pilot-v2` selects the older
likelihood-only temporal/contrast formulation with the corrected native catalogue;
it is a different comparison basis. Results from different profiles cannot be mixed.
The normative scenario names are `reference` (q = 1) and
`double_measurement_noise` (q = 2). The sensitivity-grid names are
`q0.0625`, `q0.25`, `q1` and `q2`.

## What is held fixed

The catalogue has 36 native quantities in 14 panels and five domains, including
molecular, physical, digital, cognitive and direct neural measurements. It is a
selective reference, not complete omics or all acquired information in a study.
The hybrid profile has 1,065 logical requirements per scenario. Each exact level
decision also checks all required participant-pattern and support instances.

For a native quantity, its reference increment is denoted by Δ. Standard
individual-state and temporal standard-error limits are 0.75Δ. Temporal tasks
also require predictive covariance at most half its no-observation reference;
joint tasks check all directions. Population covariance limits are
0.5ΔᵢΔⱼ; contrast, response-difference and observed-site comparison limits are
0.5Δ. These are declared conventions whose sensitivity can be examined, not
clinically established cutoffs. The package resources record the full target
definitions, frames, units, gates and exact numerical rules.

The conditional measurement model uses fixed native increments and Gaussian
covariance. Repeats within the same qualified coordinate/session share an error
component: two readings do not count as two independent observations. Qualified
complementary observations can resolve a new direction; copying an acquisition
cannot. The implementation calls the existing finite-target evaluator rather
than reimplementing the score in the chart.

Domains have equal budget; panels have equal shares within a domain. Individual
state and population categories allocate 75% to native panels and 25% to registered
cross-panel relationships. These weights are explicit conventions. An unmeasured
or unresolved task keeps its place in the denominator. A 60–75% range means at
least 60% passes and at most a further 15% is unresolved under that scenario;
it is not a confidence interval. An exact reference pass requires all mandatory
requirements, not a rounded mean of 100%.

## Enter your own study

Use `design.schema.json` in `anibench.study_capability_candidate`. The input
declares the full cohort, disjoint participant patterns, acquired physical
channels, timing, native-coordinate coverage, linked panels and qualification
gates. Unknown and absent are different. Do not assign one modality's subset to
everyone, infer dates from visit labels, or replace missing quality information
with a favorable default. Planned and hypothetical inputs declare assumptions;
collected inputs must qualify the actual acquisition.

`anibench bind-design` can attach source identities and assumptions before this
command. Keep contemporaneous assay/export definitions with your input. In
particular, the current N170 observable is face-minus-car mean amplitude at PO8,
110–150 ms, with a −200–0 ms baseline. The former P8/110–170 ms observable is not
an alias. Old inputs and certificates require their original package version;
no silent renaming or transfer of certification is supported. See the
[ERP CORE source](https://github.com/lucklab/ERP_CORE/tree/c18b43d70d791ca914d90410afe4ff06d6f7f429).

## Draw a comparison

Prepare a local comparison JSON matching `chart.schema.json`. Each record binds
an input and result file, their byte hashes, a plain label, lifecycle, study
publication status and ethics status. Then run:

```sh
anibench study-chart comparison.json --scenario reference --out comparison-figure
```

The command writes PNG, SVG, figure data and a table after checking source-input,
result, code and profile bindings. `--published-only` selects peer-reviewed study
results; `--irb-only` selects documented approval. Both select their intersection.
The filters change which studies appear, never their scores. Unknown approval is
not disapproval. Keep private paths and clinical records out of shared manifests.

The native36 profile is a conditional research candidate. It does not yet establish
broad empirical calibration, full real-study rankings or completion of the wider
AniBench programme. Historical reference witnesses use a different N170 frame;
their certificates are not evidence for this corrected profile.
