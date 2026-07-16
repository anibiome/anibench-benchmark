# AniBench v2 API

The local API is a loopback-only design and replay service. It processes study
structure and aggregate protocol geometry; it is not a participant-data API.

Start it with:

```bash
anibench studio --host 127.0.0.1 --port 8765
```

The normative machine contract is
[`openapi/anibench-v2-candidate.yaml`](../openapi/anibench-v2-candidate.yaml).

## Current endpoints

| Method and route | Input | Output | Claim boundary |
|---|---|---|---|
| `GET /api/health` | none | service/version status | runtime only |
| `GET /api/v2/comparator-atlas` | none | hash-verified public source ledger and typed family eligibility | descriptive source corpus; source order is not rank |
| `POST /api/v2/design` | compact human-facing design | typed coordinates, gates, upgrades | no biological capacity |
| `POST /api/v2/protocol-capacity` | explicit protocol geometry | six separate capacity families plus audit metadata | candidate capacity; no overall scalar |
| `GET /api/v2/level1-authority` | none | frozen 64-coordinate, seven-role, six-family Level-1 definition and open gates | machine authority; no enrollment target, scalar, or rank |
| `GET /api/v2/level1-template` | none | HTTP 410 retirement receipt | the fictitious perfect-trial template is not part of v3 |
| `POST /api/v2/level1-assessment` | explicit protocol geometry | six native design-family metrics, source locators, derivations, and unresolved target gates | planned or realized protocol assessment; no target percentage, scalar, or rank |
| `POST /api/v2/optimize-protocol` | base protocol, mutations, resources, objectives | candidate receipts and Pareto frontier | design sandbox; no stable rank |
| `POST /api/v2/information` | explicit matrix replay | absolute information mechanics | caller matrices cannot authorize a reference |
| `POST /api/intake/ctgov` | NCT identifier | immutable intake snapshot | human review required; never auto-score |
| `POST /api/intake/ctgov-search` | query, page size, optional page token | immutable ClinicalTrials.gov result-page snapshot | discovery only; never auto-score or infer geometry |

Level-1 basis comparison follows JSON's single-number semantics: finite values
such as `1` and `1.0` are mathematically equivalent even though the submitted
input hash preserves their different serializations. Booleans never alias
numbers, non-finite values fail closed, and genuinely different numeric values
remain basis mismatches.

Legacy scalar/rank previews, the superseded three-family suite, and the
unversioned shadow-capacity simulation return HTTP `410 Gone`.

## Protocol-capacity request

The exact input schema is
[`schemas/v2/protocol-capacity-input.schema.json`](../schemas/v2/protocol-capacity-input.schema.json).
It requires:

- a parameter space and prior precision;
- canonical signals, ancestry and observation operators;
- covariance groups and measurement modules;
- participant-event schedules, retention-overlap authority, and joint-observation bundles;
- source-bound components, policies, decision-rule operators, and randomized assignment stages;
- pre-assignment moderator measurements; and
- source-bound transport coordinates with linked outcomes and common policies;
  and
- one or more transport-axis-family declarations, each binding the reference
  estimand, its ordered required axes, and the hash-addressed authority for
  those axes' units, transforms, and ranges.

Assignment and context counts are capped by linked retained outcome support. Cluster
and crossover designs are typed unresolved—never zero capacity—until the input
contract can express their ICC/cluster or period/sequence/carryover geometry.
Participant measurement schedules use exact offsets. High-frequency
decision processes use the compact registered regular-process contract so runtime
and payload size do not scale by materializing every repeated epoch.

Causal, personalized, and transport outputs expose structural ranks and
`*_allocation_support_factor` coordinates. These are allocation/design-support
proxies, not biological information or inferential precision: they exclude outcome
noise, observation-operator uncertainty, temporal covariance, effect size, and
estimator performance.

Transport is emitted as an axis-family vector. Its envelope paths are
`transport.axis_families.<family-id>.transport_rank` and
`transport.axis_families.<family-id>.transport_allocation_support_factor`.
Contexts are projected onto each family's required axes. Extra coordinates are
preserved in the context ledger but ignored numerically; a context missing any
required axis is typed ineligible. With exactly one family, the legacy
`transport.transport_*` paths are deterministic aliases. With multiple
families, those aggregate envelope aliases are omitted and the compiler emits
no averaged, maximum, or winner-selected transport scalar.

The result always exposes `overall_scalar: null`. Custom caller geometry remains
`comparison_eligible: false`; a comparison requires the installed hash-pinned
authority resolver.

The non-HTTP Python/CLI comparator is
`anibench.compare_trial_eval_receipts(receipts)` / `anibench compare`. It accepts
only hash-valid canonical eval receipts on one exact implementation, Level-1,
geometry, and parameter-space basis, then returns family-wise Pareto relations.
It never returns an overall scalar or ordinal rank.

Evidence lane is not a numeric multiplier. Identical declared geometry in Design
Preview and Realized lanes has identical design capacity; the lane changes claim
permissions and required receipts, not the capacity mathematics.

A compact `/api/v2/design` receipt and a `/api/v2/protocol-capacity` receipt are
not semantically joined merely because `study_id == protocol_id`. The Studio
labels that condition `identifier_match_only_not_semantic_binding`. A semantic
join requires a content-hashed pointer crosswalk matching both object hashes and
covering every required design-geometry source pointer exactly once.

```bash
curl -sS http://127.0.0.1:8765/api/v2/protocol-capacity \
  -H 'Content-Type: application/json' \
  --data-binary @web/protocol-capacity-example.json
```

## Level-1 role-aware assessment

Level-1 assessment compiles a protocol into six independent native design
dimensions and binds every displayed metric to the protocol-capacity receipt
and an exact JSON pointer. The role authority is verified with:

```bash
python scripts/build_level1_target_v3.py --check
```

The receipt exposes native metrics under
`scenarios[*].families[*].native_metrics[*]`. Each row includes its value, unit,
source-object SHA-256, compiler locator, and derivation. Target attainment under
`level1_target_attainment` is currently typed `unknown/unresolved/null` for all
six families. The receipt keeps `overall_scalar: null` and emits no rank.

The canonical CLI entry point is `anibench eval`. The same path handles the
design-capacity view of prospective and realized protocols; the evidence lane
changes claim permissions, not design geometry:

```bash
anibench v2-level1-authority --out level1-authority.json --pretty
anibench eval web/protocol-capacity-example.json \
  --out planned-level1-receipt.json --pretty
```

`v2-level1-assessment` remains a byte-identical compatibility alias. The eval
card and complete task semantics are in `evals/level1/eval-card.json` and
`docs/EVALUATION.md`.

Or use the loopback API:

```bash
curl -sS http://127.0.0.1:8765/api/v2/level1-authority \
  -o level1-authority.json
curl -sS http://127.0.0.1:8765/api/v2/level1-assessment \
  -H 'Content-Type: application/json' \
  --data-binary @web/protocol-capacity-example.json \
  -o planned-level1-receipt.json
```

The retired `/api/v2/level1-template` returns HTTP 410. AniBench does not ship a
fictitious perfect-trial template or a global enrollment number. Family-specific
targets can become numeric only through a new source-bound authority receipt.

## Comparator atlas

`GET /api/v2/comparator-atlas` reads the explicitly public coordinate table,
replays every listed projection SHA-256 against the exact packaged source
projection, and returns descriptive population, duration, causal, measurement,
gate, and source-binding fields. It also binds the packaged field-provenance
receipt and returns its hash plus counts of machine-resolved known facts and
nonmechanical candidate values downgraded to typed unknown for the corpus and
each study. The endpoint rejects any manual known fact and fails closed on a missing object,
identity mismatch, hash drift, malformed authority, field-receipt mismatch, or
table/projection gate-count disagreement.

The current public corpus does not contain source-complete protocol-capacity
geometry on a common verified basis. Every study therefore remains
`not_scoreable` across the six families and `comparison_eligible: false`; the
endpoint reports a typed unknown placement instead of manufacturing matrices or
using population and module counts as substitutes.

```bash
curl -sS http://127.0.0.1:8765/api/v2/comparator-atlas
```

## Protocol optimizer

The optimizer accepts only protocol mutations under `/measurement_geometry` or
`/causal_geometry`. It recompiles every candidate through the protocol compiler.
Direct family-output patches, hidden weights, duplicate opposing objectives,
zero-resource mutations, and searches beyond the candidate cap fail closed.

Resource totals are part of Pareto dominance. A higher-capacity design that
costs more can coexist with the base design on the frontier; a costlier design
with no capacity improvement is dominated.

## Error semantics

Invalid JSON shapes, non-positive covariance, inconsistent event support,
unknown references, non-positive assignment probability, unlinked moderators,
and gameable optimizer requests return HTTP `400` with a deterministic error.
Unknown scientific facts must be represented in the fact layer; they are never
silently replaced by an API default.

## Security boundary

The Studio refuses non-loopback binding unless explicitly overridden for an
isolated development environment. It enforces JSON content type, an 8 MB request
limit sized for explicit protocol-capacity objects,
loopback-origin checks, no-store responses, a restrictive content security
policy, and static-path containment.
