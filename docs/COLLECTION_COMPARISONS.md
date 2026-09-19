# Native collection comparisons

`anibench compare-records` compares **one declared metric** across hashed
collection profiles. It is separate from `anibench compare`, which retains its
six-family geometry/Pareto contract. Neither creates a weighted overall score.

A study can participate in a count comparison without an information/noise model.
A native-count leader is not thereby a biological-information or overall-quality
leader. The selected metric, corpus, evidence basis and uncertainty rule travel
with every comparison receipt.

## Run

Create profiles with `anibench profile` or `anibench profile-tables`, then:

```bash
anibench compare-records study-a-profile.json study-b-profile.json \
  --basis comparison-basis.json --out comparison.json --pretty
```

The command accepts either a direct collection profile or the aggregate envelope
from `profile-tables`. It never needs participant identifiers or measurement
values. Outputs cannot overwrite inputs or the basis file.

Start from `examples/collection/comparison-basis.json`. Declare:

- the metric and planned or collected evidence basis;
- a population definition, including enrollment, dropout and exclusion rules;
- the observation scope, including collection window and time origin;
- an acceptance/QC definition and common timestamp resolution;
- a review protocol describing how source assertions will be verified;
- for module metrics, a selected module ID and a common target definition,
  target unit and biological domain.

The tool checks bytes and structural compatibility. It cannot determine whether
an arbitrary caller's population or QC description is scientifically appropriate.
A hash is an integrity check, not a signature, source authentication, independent
review, or proof of a complete inventory. Identical labels do not establish that
two assays count the same biological entities. Target ancestry and aliasing need
review before a public comparison.

## Version 1 metric cards

All metrics use higher **quantity**, not necessarily higher overall quality.

| Metric identifier | Quantity | Denominator/scope |
|---|---|---|
| `roster_participants` | Declared people | Whole declared roster |
| `measured_participants` | People with any accepted target | Whole roster |
| `repeated_participants` | People with at least two distinct dated observations | Whole roster |
| `median_observation_times` | Median distinct dated observations per person | Whole roster, zeros retained |
| `median_observed_span_days` | Median elapsed span | People with at least two dated observations |
| `module_participants` | People with accepted module targets | Whole roster |
| `module_targets` | Distinct accepted module targets | Union across people and events; not depth for every person |
| `module_median_targets` | Median distinct module targets per person | Whole roster, zeros retained |
| `module_participant_events` | Accepted module participant-events | Canonical events |
| `module_target_observations` | Distinct target/person/event tuples | Selected module, repeats at different events retained |

The last metric can grow by more targets, people or events. It must not be labeled
independent depth, biological dimensions or information gain. Unlike units are
never added; module target metrics require the same domain, unit and target
registry definition. Unequal rosters are permitted, but displayed denominators
remain attached. The basis must explain why those populations are comparable.

## Missingness, ties and possible ranks

For nonnegative coverage quantities, a partial inventory or unresolved QC gives
a lower bound. A participant count has the declared roster as a conservative upper
bound. Other partial quantities retain an unbounded upper bound (`null`). An
unreported module is unresolved, even when the submitted inventory claims to be
complete; omission alone does not prove absence.

Unknown timestamps prevent exact ordering of repeated-person and distinct-time
quantities. Event-based totals with undated observations become unresolved because
event aliases could collapse when dates resolve. A partial or incompletely dated
conditional span gets `[0, unbounded]`, with its observed value preserved
separately. New repeat participants could move the median in either direction.
No repeat participants means the conditional median is undefined, not zero.

For closed bounds `[L_i, U_i]`, study i is **definitely strictly higher** than j
only if `L_i > U_j`. Exact identical points are exact ties. Every other overlap,
including a touching boundary, remains unresolved. These are evidence bounds,
not confidence intervals, p-values or claims about a superpopulation.

The competition rank is `1 + number of studies with strictly higher values`.
Conservative possible ranks are:

```
rank_min(i) = 1 + count(j where L_j > U_i)
rank_max(i) = 1 + count(j where U_j > L_i)
```

An unknown upper bound acts as infinity for these comparisons and is serialized
as `null`. Equal exact values share a rank. Bounds are conservative; dependencies
between studies or bounds can make some apparent joint extremes impossible.
The receipt does not assume those extremes are statistically independent.

`leaders` means guaranteed to be first or tied first within this bound corpus
(`rank_max == 1`). It does not necessarily mean a unique winner.
`possible_leaders` means first remains possible (`rank_min == 1`). A result with
no guaranteed leader is valid. Entries remain in alphabetical study-ID order;
row position is not a rank.

## Claim and submission protocol

Before evaluating desired winners, commit the metric card, target definition,
comparison basis, cutoff date, corpus inclusion rule and reviewed study versions.
Record the excluded or unresolved studies and reasons. Do not select whichever
population, assay interpretation or reporting window makes a preferred study win.

A reproducible submission consists of:

1. The collection profile and its content hash, source hashes and locators.
2. The comparison basis and the exact evaluator version/dependencies.
3. A source adapter or executable derivation; access instructions for governed
   inputs can remain private under an appropriate review arrangement.
4. A completeness and QC statement, participant-denominator reconciliation,
   target registry and derivation/alias ancestry.
5. The resulting receipt and proposed claim naming the metric, units, date and
   comparison corpus. Disclose sponsorship and unresolved conflicts.

Independent review checks the source-to-number chain and scientific suitability
of the basis. The current software does not issue independent-review badges.
Public submissions can be proposed through a GitHub issue or pull request after
reviewing the actual artifacts for participant, clinical and credential data.
Do not upload private manifests just to demonstrate reproducibility.

If a source changes, publish a new receipt and corpus hash. If a metric changes,
create a new rule version and preserve old results. The standard is extensible:
new target-specific tasks can raise depth, temporal, intervention and population
requirements without silently redefining previous benchmark results.
