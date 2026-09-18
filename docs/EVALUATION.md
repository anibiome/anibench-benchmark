# AniBench evaluation

AniBench evaluates a human trial, not a language model. The evaluated object is
the trial's linked participant-event, measurement, intervention, moderator, and
context geometry. The question is how much biological state, movement, causal
response, person-specific response, and population transfer that geometry makes
learnable.

This is a **study-capacity evaluation**, not an intervention-success score.
Treatment effect size, statistical significance, responder fraction,
rejuvenation, and predictive-model accuracy are not inputs to the main result.
In this contract, an `outcome` link identifies a measurement after an assignment;
it does not assert that the measurement improved. Identical study geometry has
identical capacity whether the intervention helps, harms, or has no effect,
holding the declared observation and noise model fixed. Real differences in
retention, measurement quality, noise, or linkage can change realized capacity.

Optional outcome and demonstrated-learning benchmarks can accompany the main
profile, with separate metrics and assumptions. They are not prerequisites for
running it. Their full execution workflows are not implemented by `anibench eval`.

## One command

```bash
anibench eval web/protocol-capacity-example.json \
  --out build/anibench-eval.json --pretty
```

The command accepts the strict
[`protocol-capacity-input`](../schemas/v2/protocol-capacity-input.schema.json)
contract and returns the strict
[`Level-1 assessment`](../schemas/v3/level1-role-aware-assessment.schema.json)
contract. `anibench.run_trial_eval(payload)` is the equivalent Python API.

The output is deterministic within the runtime environment recorded in
`implementation_receipt.runtime_environment`. `protocol_sha256` binds the submitted geometry,
`protocol_capacity_result_sha256` binds the six-family compiler output, the
Level-1 readback binds the installed coordinate and role authority, and
`assessment_receipt_sha256` binds the complete evaluation. The implementation
receipt hashes every installed AniBench Python module, including transitive
information and causal formula modules.

## The six eval tasks

| Task | Biological question | Native outputs |
|---|---|---|
| `intensive` | What independent biological directions can one linked participant-event resolve? | effective observed dimensions; within-event log10 hypothesis-volume contraction |
| `extensive` | How much retained information does the full study contribute across people and events? | retained participant-events; population log10 contraction |
| `longitudinal` | Can the design resolve within-person state movement rather than repeated cross-sections? | participant-weighted median linked time points and span; retained linked events |
| `causal` | Which whole-policy and component contrasts are identified by actual assignment geometry? | policy and component rank; allocation support; eligible randomized people and decisions |
| `personalized_sequential` | Can measured pre-assignment state support response heterogeneity and repeated policy learning? | moderator rank and allocation support; eligible people and decisions; structural personalization state |
| `transport` | Across which registered context directions can outcome-linked intervention relations be learned? | transport rank; allocation support by axis family |

Transport is itself non-collapsible across registered axis families. For a
single axis family, the two top-level native metrics are convenience aliases.
For two or more axis families, those aliases are unresolved and `metric_groups`
emits one source-located metric pair per axis family. AniBench never chooses a
winning axis family or combines incompatible transport directions into a scalar.

These tasks are noncompensatory. AniBench does not average them and does not
permit caller-supplied weights. A large shallow study may raise extensive support
without creating an unmeasured intensive direction. A long modality menu cannot
substitute for observation operators and nuisance covariance. Arm count cannot
substitute for independent randomized contrasts.

The present compiler accepts expert-declared operator, prior, covariance, and
event geometry. Until those objects are content-verified against the installed
Level-1 basis, emitted numbers are labeled `computed_unverified_geometry`, not
resolved Level-1 measurements. Deterministic computation is not ontology
verification, empirical validation, or comparison eligibility.

Cluster-randomized and crossover declarations are accepted for audit intake,
but the current schema does not yet express ICC/cluster-size or
period/sequence/carryover geometry. Their causal, personalization, and transport
eval families therefore emit `DEPENDENT_RANDOMIZATION_GEOMETRY_UNSUPPORTED`
with null native metrics. They never emit a numerical zero for missing geometry.

## Proposed and completed trials

The same geometry receives the same design-capacity result. Evidence maturity
changes what the result can claim, not the result itself:

A completed study is evaluated by setting `claim_class` to
`realized_dataset_geometry_capacity` and replacing scheduled support with its
source-verified retained geometry before running the same command. This claim
class names the geometry basis; it is not an independent evidence attestation.

- Design Preview uses the frozen proposed geometry.
- Registered Protocol binds the geometry to a content-hashed protocol or registry source.
- Realized replaces scheduled support with retained, linked, QC-passing events.
- Accessible additionally proves that an evaluator can lawfully compute against the data.
- Demonstrated adds held-out learning, calibration, null, and transfer receipts.

The canonical `eval` command computes protocol/design capacity. Beyond the
prospective-versus-retained geometry basis, evidence lane is not encoded in this
eval receipt. It does not
promote a proposed schedule into realized data or a realized dataset into
demonstrated biological learning. Those evidence claims travel in separate
source and execution receipts.

## Run on private study data

The public repository is the evaluator, specification, and public examples.
Your private workspace holds your study's measurements, manifests, adapters,
and evaluation outputs. A public source-atlas entry is not required to run a
study, and study identity does not affect the calculation.

1. Inventory the actual participant, specimen, device, assay, and event records
   locally. Preserve distinct enrollment, follow-up, assay-QC, and joint-modality
   denominators. Record when observations can be linked to the same person and
   biological time; repeated or derived records are not new independent signals.
2. Map those records to the existing protocol-capacity input contract. For
   completed studies, use `claim_class: realized_dataset_geometry_capacity` and
   actual retained schedules, linked measurement bundles, exposure and assignment
   support. Include the observation operators, target basis, and noise assumptions
   with their provenance. Biological variation in a raw matrix is not, by itself,
   an estimate of measurement-error covariance.
3. Run the same local evaluator used for a public or proposed study:

   ```bash
   anibench eval /private/elite/realized-geometry.json \
     --out /private/elite/capacity.json --pretty
   ```

4. Inspect the six families and their unresolved fields. Compare compatible
   evaluations locally with `anibench compare`, or open `anibench studio` and
   use `http://127.0.0.1:8765/explore.html`. Publication is a separate choice.

These paths illustrate a private workspace; no Elite participant data ship with
the package. The hosted static website does not accept private uploads. Local
Studio processes the structured inputs in the loopback service on your machine.

**Current adapter boundary:** `anibench eval` accepts geometry JSON. It does not
yet discover arbitrary assay spreadsheets, sequencing files, images, voice
recordings, or wearable streams and compile their geometry automatically.
Study-specific adapters must perform that conversion and retain the source
lineage locally. Full raw-data ingestion is unfinished; an atlas profile or
manuscript summary is not a substitute for that integration. Unknown information
geometry remains unresolved, while known collection facts remain reportable.

## Results and comparison

Every family emits its native metrics and source locators. The top-level
`geometry_authority_state` states whether those metrics are custom sandbox
geometry or content-verified Level-1 geometry. Level-1 target attainment and
enrollment requirements remain typed unknown until their
family-specific operating-characteristic authorities are source-bound. Therefore
the current reference evaluator emits:

- `overall_scalar: null`;
- `scenarios[*].public_rank: null`;
- `comparison_eligible: false` for a standalone run; and
- `public_rank_emission_permitted: false`.

This is a complete deterministic geometry eval, not a calibrated Level-1 or
comparator result. It answers the six design questions without inventing a
percentage. Corpus placement is a second operation. Run it only on complete
eval receipts:

```bash
anibench compare build/design-a.eval.json build/design-b.eval.json \
  --out build/comparison.json --pretty
```

The comparator verifies every source assessment hash and requires an identical
implementation bundle, Level-1 authority, geometry-authority state, and
parameter-space source object. It then emits within-family Pareto fronts and
pairwise dominance. Caller-declared geometry remains a labeled sandbox. No
family is collapsed into an ordinal overall position. Stable family-specific
ranks remain a future corpus-release operation requiring source-complete
geometry, the same evidence view, a frozen comparator corpus, and an explicit
rank authority.

## From a registry record to an eval

ClinicalTrials.gov intake deliberately stops before scoring:

```bash
anibench intake-ctgov NCT00000000 --out build/NCT00000000.snapshot.json
```

The snapshot freezes source bytes, identity, hashes, and locators. A human or
audited parser must then resolve the actual measurement schedule, participant
lineage, observation operators, covariance scenarios, assignment probabilities,
moderators, and transport contexts into the protocol-capacity input. Registry
prose alone cannot manufacture those objects.

## Reproducibility check

```bash
make eval
python -m pytest -q tests/test_eval_cli.py tests/test_eval_comparison.py
```

The regression proves CLI/API parity, six-task identity, schema validity,
determinism, name blindness of native metrics, strict comparison-basis checks,
tamper rejection, and the permanent absence of an overall scalar or public rank.
