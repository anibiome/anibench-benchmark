# Different measurement subsets in one study

`anibench paired-collection INPUT --out NEW_RESULT` evaluates one molecular and
functional question when different subsets of people have different measurements.
It uses the [paired-question equations](PAIRED_QUESTION.md) and assigns each
calculation the people who actually support it.

For example, a study could measure baseline molecules and grip twice in 256
people, but repeat the molecular assay in only 16. Functional change and the
specified baseline-to-future learning calculation can use 256 people. The
relationship between molecular **change** and functional **change** can use only
16. The supplied example is wholly synthetic, including its covariance and
precision targets; these numbers are not results from a human study.

```sh
anibench paired-collection examples/paired_collection/input.json --out collection-result.json
```

Installed example location:
`importlib.resources.files("anibench").joinpath("examples/paired_collection/input.json")`.
The command makes no network requests and refuses to overwrite an existing file.

## Input contract

The question and covariance scenario are identical to the paired-question
contract. The design gives a full population count and disjoint acquisition
patterns. Every person in a pattern has the same declared measurement support;
the input contains aggregate counts, not participant identifiers or clinical
values. Adapters are responsible for verifying membership, linkage and quality.

Each pattern declares its count, an inventory-closure flag, optional two-arm
counts and physical acquisitions. Each acquisition has one occasion and one or
more named outputs with `true`, `false` or `null` qualification. Multiple outputs
from one assay retain their full declared covariance. They are not automatically
independent measurements. A directly measured function must not be replaced by a
prediction or a score derived from the molecular inputs.

Physical IDs identify acquisition slots within a disjoint pattern template.
They may recur in another disjoint pattern. Exact duplicate pattern IDs and
acquisition IDs are coalesced; contradictory reuse is rejected. A second physical
acquisition of the same coordinate at the same occasion requires a separately
specified repeat-error model and is rejected by this version. Renaming a
duplicate participant group is not proof that it is disjoint.

`closed_pattern_roster: true` requires the patterns to partition `n_people`.
Otherwise unrepresented people remain unresolved. Within a closed acquisition
inventory, an omitted output is absent; in an open or unresolved inventory it is
unknown. Explicitly false qualification remains false in either case.

The input requires declarations of a common covariance model across patterns
and acquisition independent of biological state. The latter is needed for
population and learning calculations on the selected complete cases. It does
not change measurement error for a person already observed. Heterogeneous
covariance, informative missingness and selection-adjusted estimators need
different models; setting a flag to true does not verify those assumptions.
The inherited support flags separately cover timing, population, measurement
validity, linkage, exposure and causal identification. Realized inputs require
collection verification; planned designs need no treatment outcomes.

## Which observations support each result?

| Result | Required measurements in the same people |
|---|---|
| Molecular or functional state | That domain at baseline |
| Individual or population mean change | That domain at both occasions |
| Molecular–function change relation | Both domains at both occasions |
| Exposure-aligned change or controlled functional effect | Function at both occasions, plus the corresponding exposure/identification requirements |
| Intercept-only future-function prediction | Follow-up function |
| Baseline-function prediction | Baseline and follow-up function |
| Baseline-function-plus-molecules prediction | Baseline molecules and function, plus follow-up function |

Separate groups with molecular and functional measurements retain their
respective state/change information. They do not provide a jointly observed
molecular–function relationship. More people never sharpen an individual
reading's measurement-error covariance.

## Bounds and interpretation

For each required slot set, the lower count includes patterns definitely
supporting every slot. The upper count adds unresolved compatible patterns and
unrepresented people. Both endpoints use the same declared covariance scenario.
Mean-change covariance scales as `1/n`, and Gaussian sample-covariance error as
`1/(n−1)`. Under these assumptions, endpoint calculations bound the attainable
precision for the specified complete-case estimators. They are not a claim that
these estimators use every possible incomplete observation optimally.

For a controlled contrast, known arm allocations are preserved at both
endpoints. At maximum possible support, only people whose arm allocation is
unknown can be allocated optimistically. The algorithm minimizes
`1/n0 + 1/n1` over that feasible integer range, giving the closest admissible
balance. If any definitely acquired group's allocation is unknown, the lower
precision bound conservatively remains zero rather than inventing its split.
All assignment and selection assumptions still apply.

The output labels these as **outer acquisition-support bounds**, not confidence
intervals. Endpoints for different tasks need not describe one jointly feasible
study. Conditional OLS risk is reported at both support endpoints; the larger
sample endpoint has lower risk for a fixed route when finite. An insufficient
sample can give no finite expected OLS risk. This concerns that learner only.
Observed held-out prediction remains `not_evaluated`.

Adequacy percentages keep the paired-question definition: progress toward the
declared estimator-covariance limit. They are neither accuracy percentages nor
whole-study scores. The receipt contains independent-person bounds, required
slots, both endpoint calculations, assumptions and input/calculation hashes.
Metadata-only edits and duplicate rows do not change the calculation hash.

## Source limits

Marginal assay counts do not identify disjoint participant patterns. Do not
construct a complete cohort by taking their minimum. Compatible population
counts may support mathematical intersection bounds, but using them requires a
source-qualified common universe and an explicit adapter. Serum and plasma,
different instrument procedures, and different time windows cannot be silently
declared equivalent because their columns share a name.

This adapter does not adopt AniBench 1/2 thresholds, provide a broad biological
workload, calibrate real-study covariance, or complete the benchmark. The schema
is `schemas/paired_collection/v1/input.schema.json`.
