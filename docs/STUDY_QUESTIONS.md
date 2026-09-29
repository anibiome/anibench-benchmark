# Compare studies against fixed biological questions

`anibench study-questions PROFILE INPUT --out NEW_RESULT` evaluates a study's
original measurement inputs against an explicit reference. Each category reports
the percentage of its fixed biological requirements met, with unresolved
requirements retained in the denominator. The reference is supplied separately
so changing a study cannot silently change what counts as success.

This is a conditional research interface. It does not yet supply the broad
AniBench 1/2 reference or a validated ranking of real studies.

## Run locally

From a checkout with AniBench installed:

```sh
anibench study-questions examples/study_questions/PROFILE.json \
  examples/study_questions/paired256_REQUEST.json --out activity-result.json
```

The wheel also includes these examples. To locate them after installation:

```python
from importlib.resources import files
print(files("anibench").joinpath("examples/study_questions"))
```

Inputs remain local. Results can contain private input definitions and must be
handled as private research outputs. The command creates a new file with private
permissions, refuses to overwrite existing files and avoids printing input
values or private paths in validation errors. It performs no upload.

## Read a percentage

A category has fixed questions and positive integer weights. A question passes
only when all its selected outcomes pass. Ten outputs from one assay do not
receive ten votes unless the scientifically reviewed reference explicitly
defines different biological questions and allocates their weights.

For total weight W, passed weight P and unresolved weight U, the result is
100P/W through 100(P+U)/W. Known failures remain in W. This is an evidence bound,
not a confidence interval or the percentage of all human biology understood.
The separate `precision_toward_targets` field reports capped variance-ratio
progress; it is not a success probability. Exact reference attainment uses
unrounded question outcomes.

Each scenario evaluates one coherent set of assumptions. Its acquisition design
stays fixed across scenarios. To change people, sampling, linkage or assays,
create a separate study request. The cross-scenario envelope is an outer bound;
its category endpoints need not be jointly attainable.

## What can be supplied

The profile defines biological question identities, population and time scope,
native units, measurement definitions, required outcomes, category weights and
common reference scenarios. The caller explicitly selects this trusted profile;
its digest prevents accidental modification, not poor scientific choices.

The request identifies a planned, hypothetical or realized study and supplies
original inputs for each question. Omitted question inputs remain unresolved.
Closed, qualified inventories can establish absent measurements. Realized
collection requires the existing engines' collection-verification conditions;
planned designs are conditional on their declared acquisition.

Three existing engines are supported:

| Engine | Question it can calculate |
|---|---|
| `question_routes` | Whether registered physical observations resolve a fixed native target through a declared observation operator and joint error model. |
| `paired_collection` | Molecular and functional state, change and selected relationships from linked acquisition patterns. |
| `cross_domain_collection` | The same paired calculations with explicit biological domains, such as digital observations linked to independently measured cognitive performance. |

Native-domain inputs require v2 or v3 profiles and matching requests. Existing
v1 and v2 profiles retain their original result contracts and calculations.
A native-domain label does not establish measurement
validity, a Gaussian likelihood or biological relevance.

The runtime validates the complete profile and nested engine inputs before
scoring; the example JSON files show the exact structures. The API is
`anibench.study_questions_v2.evaluate_study_questions(request,
trusted_profiles={profile_digest: profile})`. Use
`anibench.question_routes_v1.digest(profile)` for the binding.

## Alternative native measurement frames (v3)

A reference may explicitly ask whether **one of several complete native
measurement frames** meets a requirement. For example, a scientifically reviewed
reference could accept either a complete serum panel or a complete EDTA-plasma
panel. These are different native targets. Acceptance does not make their values
interchangeable, permit pooling participants across them, or establish equal
biological utility. A serum-specific target still requires serum measurements or
a qualified bridge.

Use `anibench.study-question-profile.v3` with a matching
`anibench.study-questions-request.v3`. Categories use `requirements` instead of
the older `questions` entries:

```json
{
  "requirement_id": "complete_native_panel",
  "rationale": "Why each complete frame answers the declared biological purpose",
  "weight": 1,
  "alternatives": [
    {"question_id": "native_frame_a", "outcomes": ["molecular_state", "function_state"]},
    {"question_id": "native_frame_b", "outcomes": ["molecular_state", "function_state"]}
  ]
}
```

Each alternative refers to a separately defined question in the same profile.
The underlying engines still validate its full targets, covariance, linkage and
support. The study cannot supply scores or shorten the frozen target panel.
Each requirement receives one budget, regardless of its number of alternatives.
The runtime rejects duplicate frames and reusing a frame for additional
requirement weight inside the same category.

For one scenario, precision progress is `max_frame min_required_outcome`.
An exact pass requires at least one frame in which **every** selected outcome
passes. A frame with good molecular resolution but poor functional resolution
cannot combine with another frame having the reverse weakness. If one complete
frame passes, an unknown unused alternative does not erase that pass. If none
passes, the requirement remains unknown until every alternative is known to fail.

The `robust_categories` output uses one fixed frame across **all** scenarios:
`max_frame min_scenario min_required_outcome`. Its exact pass has the same
quantifier order. A serum route that works only under one assumption and a plasma
route that works only under another do not provide a robust fixed-route witness.
Consequently, the ordinary scenario envelope can read 100–100% while the robust
fixed-frame requirement fails. The receipt preserves both propositions and lists
the attaining question IDs. Unknown upper bounds remain conservative bounds,
not promises that their endpoints can jointly occur.

Different category requirements may use different witnesses. Their combined
attainment does not certify a single linked cross-question dataset or a single
native frame. Put outcomes that require one shared frame into the **same**
requirement. Scenarios change uncertainty assumptions, never acquisition design.

Biological admission is a reviewed reference choice: freezing an arbitrary
alternative does not make it scientifically relevant. Attach resolutions to the
target and purpose, shared by assays measuring that target. Easier thresholds
chosen to match a noisier instrument would trivialize the comparison. Replacing
a serum requirement with a serum-or-plasma requirement changes the benchmark
version; it does not repair or overwrite an earlier serum-specific result.
Adding an easier alternative to AB2 can also break the promise that AB2 implies
AB1, even if other thresholds become stricter.

Every alternative must include all roles required by its parent purpose. A
trusted profile that selects only molecules in one alternative and only function
in another has defined a weaker disjunction; the runtime cannot recover the
intended molecules-and-function requirement from a prose rationale. Reference
review must reject that mismatch before admitting a study comparison.

## Reproduce the software examples

The seven requests in `examples/study_questions` are entirely hypothetical.
Six preserve one activity/reaction-time question while changing people, follow-up,
linkage, error knowledge or duplicate records. The seventh combines a fictional
molecular observation route with a paired question. Their expected receipt
digests preserve the independently reviewed pre-integration calculations.

| Hypothetical change | Expected consequence |
|---|---|
| 256 people to two people | Individual measurement precision stays the same; population and relationship precision decline. |
| Remove follow-up | Baseline measurements remain; change cannot be resolved. |
| Break person-level linkage | Marginal measurements cannot establish the linked change relationship. |
| Unknown measurement error | Relevant requirements remain unresolved. |
| Duplicate each acquisition | No information gain. |

The activity and reaction-time definitions cite public UK Biobank fields in
their input metadata. Participant counts, paired schedule, covariance and
resolutions are stipulated examples, not UK Biobank study results. They must
not be used as the requested real-study leaderboard.

Four additional fictional examples use `ALTERNATIVES_PROFILE.json` and
`alternatives_{complete,mosaic,switching,unknown}_REQUEST.json`. They exercise a
complete native witness, incompatible partial witnesses, scenario-dependent
switching and unresolved measurements. The switching example passes separately
in both scenarios but fails the robust fixed-frame certificate.

```sh
anibench study-questions examples/study_questions/ALTERNATIVES_PROFILE.json \
  examples/study_questions/alternatives_switching_REQUEST.json --out switching-result.json
```

`ALTERNATIVES_EXPECTED.json` binds their receipts. These invented specimen panels
test the logic; they do not admit serum/plasma or any other actual study protocol.

## Mathematical and biological limits

This integration introduces no new estimator. It executes the existing finite
question and paired-collection engines, preserves their receipts and aggregates
their outcomes with the shared benchmark arithmetic. Observation-route information
uses the declared H and R; collection precision uses the declared biological and
measurement covariance. Technical assumptions remain conditional until validated.

Shared physical outputs must agree on quantities, qualification and a valid
complete noise model. Duplicate frames cannot gain another question budget by
renaming a coordinate or relabeling its domain. These checks do not solve general
biological synonymy or prove joint inference across different questions.
Per-question participant subsets are not added into a whole-study roster.

Broader biological reference selection, calibration, source-qualified real-study
comparisons and empirical learning validation remain separate unfinished work.
The existing `eval` and `compare` compatibility contracts are unchanged.
