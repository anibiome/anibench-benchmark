# AniBench Trial Designer

The Trial Designer has three connected workflows.

## 0. Source-bound registry discovery

The Studio can search ClinicalTrials.gov or lock one exact NCT record. Each
request produces the same immutable intake contract as the command-line
workflow: exact source URL, retrieval time, raw-byte SHA-256, JSON-pointer
inventory, unresolved review fields, and `score_eligible: false`. A search
result can carry only its NCT identifier into the exact-intake form. It cannot
populate a measurement operator, infer participant-event linkage, classify a
planned field as realized, or enter any capacity family automatically.

The downloadable intake receipt is therefore a reproducible source boundary,
not a benchmark result. Field-level adjudication and a content-hashed protocol
crosswalk remain required before the protocol compiler may use registry facts.

## 1. Study structure

The primary form accepts ordinary protocol terms: evidence lane, participants,
duration, policy arms, control/randomization/adaptation declarations, operator
families, and measurement modules. It produces:

- typed self-declared and derived coordinates;
- the exact input hash;
- unresolved evidence gates; and
- structural upgrades grouped by objective.

This compact receipt is useful before the full biological geometry exists. It
does not infer assay information, emit a scalar, or assign a leaderboard rank.
The Studio also emits a deterministic design-handoff receipt. For each of the
six families it names the exact geometry still required and routes the user to
the protocol-capacity compiler. It never fills those objects from modality
names, arm counts, or optimistic planning assumptions.

## 2. Executable protocol geometry

The advanced lab accepts the complete
[`protocol-capacity-input`](../schemas/v2/protocol-capacity-input.schema.json).
The result renders every family-envelope metric returned by the server:

- per-event effective rank and log contraction;
- retained participant-events and extensive contraction;
- participant-weighted longitudinal offsets and span;
- policy/component structural rank and allocation-support factors;
- randomized participant and decision support;
- moderator/sequential allocation-support geometry; and
- per-axis-family transport rank and allocation-support factors over measured
  context coordinates.

Allocation-support factors are design-support proxies, not biological information
or inferential precision. They summarize registered allocation, linked-participant,
and, where applicable, moderator/context geometry. They intentionally exclude
outcome noise, observation-operator uncertainty, temporal covariance, effect size,
and estimator performance.

The advanced lab separately exposes raw capacity and a role-aware Level-1
assessment. The latter renders the same six native design families with exact
receipt locators, then shows the current target state for each family. Target
attainment remains typed unknown until the family-specific operating-characteristic
authority is source-bound. Unknown is never rendered as zero or as a short
progress bar. The downloadable receipt includes the raw compiler result, v3
authority hash, all native metrics and locators, typed gates, and a deterministic
receipt hash. The retired v2 perfect-protocol template is not a product input.

External JSON serializers may write a finite whole-valued number as either `1`
or `1.0`. Level-1 basis compatibility treats those spellings as the same JSON
number while the submitted-input hash continues to bind the exact serialization.
Booleans, non-finite values, and genuinely different numbers remain fail-closed
mismatches.

Maximum time span remains an audit coordinate; optimizer objectives use the
participant-weighted longitudinal metrics so one outlier cannot purchase the
family.

The rendered result is a six-family map, not a radar score. Each family card
shows only its own scenario envelopes and natural units. The downloadable
workflow receipt contains the untouched compiler result, the display map, the
comparator-atlas hash binding, and the typed placement decision.

The population-transport card expands into one metric pair per registered
transport-axis family. The Studio suppresses unresolved aggregate aliases when
that vector is present, so a multi-family design cannot be visually collapsed
into a false overall transport number. Each compiler receipt retains the
required axes, ignored extra axes, missing-axis reasons, exact context subset,
coordinate-scale authority, and family geometry hash.

The compact-design and protocol-capacity receipts are not semantically bound by
a matching study or protocol identifier. In that case the workflow receipt says
`identifier_match_only_not_semantic_binding`. Semantic binding requires a
content-hashed crosswalk whose design-input and protocol hashes match the two
receipts and whose pointer bindings cover every required compact-design geometry
pointer exactly once. An absent, incomplete, duplicated, malformed, or
hash-mismatched crosswalk fails closed.

## Design Preview is not a penalty

Evidence lane and mathematical capacity are orthogonal. If a planned protocol
and realized protocol contain identical geometry, their design-capacity result
is identical. The planned object cannot make realized, accessible, or
demonstrated claims, but it is not numerically discounted for being in the
future.

Thus a proposed 10-million-participant design is evaluated from its declared
geometry, not capped or discounted because recruitment has not begun. Its planned
status controls the claim lane; it does not impose a maturity penalty.

This is what makes AniBench useful for fundraising and protocol design: teams
can show exactly which biological-learning families the proposed experiment
would strengthen, which facts remain conditional, and what additional evidence
would move the design onto a stronger Pareto frontier.

## Protocol-native optimizer

The design sandbox loads a base protocol plus source-pointed mutations and
resource constraints. Every candidate is recompiled. The UI shows:

- objective values by family path;
- resource totals and constraint state;
- custom-authority/comparison hold state;
- the sandbox Pareto frontier; and
- a downloadable deterministic receipt.

“Sandbox frontier” is not a stable cross-study rank. It is conditional on the
submitted objectives, resources, protocol geometry, and source state.

## Source-bound comparator placement

`GET /api/v2/comparator-atlas` rebuilds the Studio comparator view from the
public coordinate table and exact packaged source projections. It verifies the
projection SHA-256 in every row and the sealed field-provenance receipt before
returning any coordinate. The response exposes per-study and corpus-wide counts
for machine-resolved known facts versus nonmechanical candidate values downgraded
to typed unknown, plus the receipt hash. The source ledger preserves source order and declared
population/duration semantics.

Cross-study placement fails closed unless both the submitted protocol and a
comparator carry source-complete family envelopes on the same verified
comparison basis. When that condition is absent, placement is a typed unknown;
population, duration, module count, and arm count are never substituted. When
the condition is present, the only allowed relationship is a family-envelope
Pareto relation. No weighted aggregate or ordinal rank is created.

## Source atlas

The source atlas keeps external studies and ANI studies visible even when they
cannot yet compile. It reports only machine-resolved facts as known; curated,
manual, and unresolved candidate values remain typed unknown with source locators
and reasons. It also reports population/duration semantics, causal declarations,
and exact open gates. Atlas row order is fixed source order, never ranking.

## Run and verify

```bash
anibench studio
node --test web/v2.test.js
python -m pytest -q tests/test_protocol_capacity_v2.py \
  tests/test_level1_assessment_v3.py \
  tests/test_optimizer_protocol_v2.py \
  tests/test_protocol_web_examples.py
python -m build
python scripts/verify_installed_studio.py \
  --wheel dist/anibench-2.0.0rc1-py3-none-any.whl \
  --receipt dist/INSTALLED_STUDIO_E2E_RECEIPT.json --pretty
```

The last command imports the runtime only from unpacked wheel bytes outside the
source checkout, starts the packaged Studio on loopback, and then uses headless
Chrome to submit the primary form with a typed 10-million-person planned design,
repeat it in the realized lane, and prove that evidence lane changes neither its
coordinates nor its derived workload geometry. It also verifies deterministic
design-handoff bytes, fail-closed identifier-only binding, example loading,
capacity, Level-1 assessment, and optimizer POST roundtrips, the role-aware
Level-1 authority GET, the comparator-atlas GET roundtrip,
desktop and mobile layouts, deterministic JSON downloads, and retired routes.
It fails when Chrome or Chromium is unavailable; `CHROME_BIN` can name an
explicit browser executable. The dependency-free browser driver uses the
WebSocket API shipped with Node.js 22.
