# Profile the record a study collected

The collection profile measures participant coverage, distinct assay targets,
repeat measurements, and linkage. It requires no treatment result and fits no
prediction model. Run it locally on a study's private records; the same open
implementation handles public and private inputs.

This is the empirical record layer of AniBench. The existing `anibench eval`
command evaluates a declared study geometry against six capacity families. A
collection profile supplies auditable descriptive measurements; it does not
silently turn them into independent biological information or causal effects.

## Try the complete example

From an installed source checkout:

```bash
anibench profile-tables examples/collection/table-map.json \
  --out build/collection-example.json --pretty
```

Everything under `examples/collection/` is synthetic. The roster has three people.
Two have accepted protein measurements; one has none. Six distinct target
observations survive quality checks across three participant-events. The median
number of distinct proteins observed per roster participant is two. One person
has two dated observations, separated by 28 days. Their follow-up is not the
follow-up of the entire cohort.

Inspect `profile`, then `import_audit`, in the output. Repeat with a structured
record instead of a table mapping:

```bash
anibench profile examples/collection/synthetic-record.json \
  --out build/record-example.json --pretty
```

These are separate synthetic fixtures, not equivalent inputs.

## Map private tables explicitly

Copy `table-map.json` into a private directory next to your CSV or CSV.gz files.
Keep the mapping private too: it contains the participant roster and local paths.
Each source declares its participant, event, time, quality, and target columns.
Wide tables name each target column. Long tables name a target-ID column and a
value column. No column is guessed from a familiar-looking name.

Provide the entire population you mean to assess, including people with no assay
file. Do not infer this denominator from successful measurements. Use
`outside_roster: error` to reject unexpected identifiers, or `exclude` with an
explicitly chosen cohort; excluded rows are counted in the audit.

Sources may declare a constant module or map a module column. Module identities,
target units, and target definitions must be stable and meaningful. A derived
feature should have a separate declared definition from an acquired analyte.
Counts from different modules are never added into a depth score.

Use `neural` for direct neural observations, such as an explicitly defined EEG
or fMRI measurement. Cognitive test performance remains `cognitive`; it is not
proof of neural imaging or recording. A neural collection label does not establish
neurostimulation, randomization, or causal identification. Describe those in the
protocol design separately. Electrode, voxel, and derived-feature counts need
explicit target definitions and do not denote independent biological dimensions.

Map existing QC labels to `pass`, `fail`, or `unknown`. A constant status is an
explicit user declaration, not an independent quality review. Only `pass`
contributes to a collected profile. A planned profile uses `planned` throughout
and cannot contain collected acquisitions. Planned and collected values remain
separate, without a maturity multiplier.

Numeric zero is available. Blank, NA, N/A, NaN, null, and none are missing,
case-insensitively. Other nonnumeric cells and infinities fail validation.
`value_kind: nonempty` is available for explicitly mapped categorical targets;
it is not a check that an image, sequence, or other referenced asset exists or is
usable. Measurements are inspected for availability and discarded. There is no
network request, model fitting, or treatment-effect calculation.

Pin a source's SHA-256 in its mapping when known. Every source is hashed before
and after reading; changing files fail the run. Hashes bind bytes, not scientific
truth or the authority of the submitter.

## Time and linkage

Use elapsed days, ISO dates, or ISO timestamps with timezones. Date/timestamp
inputs are converted to days from each person's earliest included source event.
This origin is not necessarily randomization or intervention start. Absolute and
relative clocks cannot be mixed without explicit upstream alignment.

Declare `time_resolution_days`: for example, 1 for dates, 1/86400 for seconds.
It documents source precision; it does not introduce a matching window. The same
participant at the same exact declared time is one dated event even if the source
uses multiple visit labels. Duplicate rows, aliases, and technical replicates do
not increase target/event coverage. Unknown dates retain the submitted event
identity but contribute no duration. Conflicting dates for the same participant
and event are rejected.

Joint coverage reports both people measured by two modules at any time and
people measured by both at the same declared event. Co-dated observations at
day resolution are not necessarily simultaneous. These checks cannot establish
that caller-supplied identities refer to the same biological person, that two
module names describe different assays, or that source clocks were calibrated.
Those remain reviewable source obligations.

## Mathematical definitions

Let R be the explicit participant roster, m a module, and e a canonical event.
Let A(i,e,m) be the set of registered target IDs with accepted availability for
participant i. Repeated rows combine by set union.

* Participants covered: |{i in R : there exists e with A(i,e,m) nonempty}|.
* Participant-events: |{(i,e) : A(i,e,m) nonempty}|.
* Target observations: sum over (i,e) of |A(i,e,m)|.
* Distinct targets per person: |union over e of A(i,e,m)|, including zero for
  every roster member without accepted targets.
* Joint event coverage for m and n: |{(i,e) : both A(i,e,m) and A(i,e,n)
  are nonempty}|.

Per-person summaries use one weight per roster member. Per-event target summaries
condition on events with accepted targets. Known observation times are deduplicated
per person; duration is max(t)-min(t) only for people with at least two known
times. Interval summaries weight each adjacent interval once, so densely sampled
people contribute more intervals. Quantiles use linear interpolation (NumPy's
`linear` method). These are descriptive distributions, not confidence intervals.

Partial inventories and unknown QC give lower bounds for coverage counts,
conditional on the fixed roster and submitted target definitions. This does
**not** make a median follow-up among the observed repeat participants a lower
bound for the cohort's median follow-up. Follow-up summaries explicitly describe
their observed subset. `complete` is a submitter declaration about the supplied
inventory, not proof of completeness against an external registry.

There is no overall score. Target counts do not measure independent biological
dimensions, information bits, biological rejuvenation, or future intelligence.
Information estimates require an explicit target, observation/noise model, and
empirical checks. Causal identification additionally needs assignment and
confounding assumptions. More targets need not mean more useful information.

## Outputs and publication

The default output contains aggregate profiles, a source audit, and hashes. It
omits measurement values, participant IDs, per-person dates, and source paths.
Use neutral module/study labels; caller-supplied labels remain in the output.
Hashes can link runs, and small-cell aggregates can be identifying. Review a
receipt before publishing it; aggregate output is not automatically anonymous.

An optional `--manifest-out /private/path/record.json` saves the intermediate
participant-linked record. It is private input, not a submission artifact. Keep
clinical records, mapping files, and this intermediate outside Git.

The collection schema and importer are versioned. A profile binds its complete
manifest and source bytes. A valid hash proves reproducibility of the submitted
object; it does not certify source accuracy. Public leader claims must additionally
name a metric, its comparison basis and corpus, and the evidence review used.

For repeated wide assays, a record can declare reusable `target_sets`, each with
`target_set_id`, `module_id`, and `target_ids`. An acquisition then supplies
`target_set_id` instead of `target_ids`. The evaluator checks that every referenced
set belongs to the acquisition's module and contains only registered targets.
This lossless representation avoids repeating thousands of target names per
sample; it changes neither coverage nor lineage counts. It is not downsampling.

## View a local receipt

Start `anibench studio`, open `http://127.0.0.1:8765/benchmark.html#run`, and
choose the aggregate JSON produced by either collection command. The viewer
shows the full roster, accepted coverage, native target depth, conditional
follow-up and pairwise measurement linkage. It also reads `compare-records`
receipts with evidence bounds and possible ranks.

File contents are read in browser memory, with no upload, persistent storage or
analytics. Clear the receipt to remove the view. Raw participant manifests are
rejected. This is a viewer of supplied results, not independent source or hash
verification; reproduce the receipt with the Python commands before making a
public claim. The built-in example is generated from the shipped synthetic
tables and checked against the Python profiler in the test suite.


Publication/ethics evidence and hypothetical approval copies can be attached
without changing these results; see [Study context](STUDY_CONTEXT.md).
