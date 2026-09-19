<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Native source-coordinate comparisons

`anibench.architecture_v1.compare_architecture(request)` compares aggregate,
source-literal collection quantities without requiring an information matrix,
noise covariance, treatment results or a participant table. It never derives
individual profiles from a publication's cohort size. One source record is enough
for scalar viewing; two or more enable conservative pairwise comparisons.

Every result is scoped to the **selected compatible quantities**. No aggregate
points, sum of unlike units, biological saturation or overall quality score is
produced. The explicit population basis permits different cohort scopes for
quantity-only comparisons. It does not assert exchangeable populations or
transportability.

## Input

The request has exactly `contract: "anibench.architecture-request.v1"`, `basis`
and `records`. The basis has `basis_id`, `population_comparison` and a nonempty
`coordinates` list. Population comparison has:

```json
{
  "mode": "quantity_only_preserve_each_population_scope",
  "rationale": "Compare collected population reach; preserve differing catchments."
}
```

Each selected coordinate has `coordinate_id`, `semantics` and `direction`.
Directions are `higher_quantity`, `lower_quantity` or `descriptor_only`. A direction
is a declared preference for this quantity, not a universal quality direction.
More arms or a longer study are not automatically preferable. A descriptor
remains visible and does not enter Pareto comparisons.

Semantics contain exactly these fields:

```json
{
  "quantity_kind": "population_count",
  "unit": "people",
  "entity_namespace": "distinct_humans",
  "denominator": "whole_declared_cohort",
  "collection_status": "collected",
  "time_scope": "declared_collection_window",
  "aggregation": "distinct_count"
}
```

Allowed quantity kinds are `population_count`, `measurement_breadth`,
`measurement_depth`, `observation_time`, `temporal_support`,
`perturbation_architecture`, `linkage_support` and `descriptor`. Status is
`planned`, `collected`, `released` or `reported_unspecified`. An unspecified status
is displayable but unresolved for ordering; it cannot silently mix planned and
collected evidence. `descriptor` requires `descriptor_only` direction.

Use canonical semantic identifiers. The denominator describes the *kind* of
population over which a quantity is calculated, such as the entire roster
including zero-observation members. Preserve actual cohort scope in the record;
do not put study-specific roster counts into a shared denominator identifier or
require identical population text. If a literal denominator count is available,
retain it as a separate source coordinate. A cohort count does not establish an
assay-complete or person-linked denominator.

Every record has `record_id`, `study_id`, `population_scope` and `coordinates`.
Each coordinate has `coordinate_id`, its own `semantics`, `value` and `sources`.
It may differ from the basis semantics; that remains visible as incompatible,
not silently coerced or dropped. No financial, weighting or study-name fields
are accepted. Study identity controls receipt attribution, not arithmetic.

Values are nonnegative native quantities with one of these exact forms:

```json
{"state": "point", "value": 106}
{"state": "bounded", "lower": 100, "upper": 120}
{"state": "bounded", "lower": 100, "upper": null}
{"state": "unknown", "reason": "Joint assay-complete count not reported"}
```

A null upper bound is unbounded missing support, not zero. Equal bounds use a
point. A missing selected coordinate becomes unknown, never verified absent;
a source-supported zero is an ordinary point. Bounds describe source evidence,
not confidence intervals. Distinct population counts require integer points
and integer bound endpoints. For rounded source counts, curators must distinguish
a literal reported token from a claim about the exact underlying quantity in
its aggregation semantics; do not invent precision or rounding bounds.

Sources are a list of `{"source_sha256": "sha256:<64 lowercase hex>",
"locator": "exact source location"}` objects. Known quantities require at least
one source; unknown values may have an empty list. This API checks identities,
not the referenced bytes, locator interpretation or source truth. Public callers
should use public aggregate facts only; the API does not authorize disclosure.

## Ordering and receipts

The implementation reuses the native-number validation from `collection_compare`
and the Pareto predicate from `comparison_v1`. It follows the collection
comparison convention that intervals strictly order only when their bounds are
separated; exact ties require equal point values. For a multi-coordinate Pareto
claim, the preferred record's worst endpoint must be at least the other's best
endpoint on every ordered coordinate and strictly better on at least one.
Touching bounds can therefore provide a weak inequality when another coordinate
supplies the strict improvement.

The pairwise result is a selected-quantity dominance relation, `exact_tie`,
`definite_tradeoff`, `unresolved`, or `descriptor_only`. Definite tradeoff requires
opposing strict preferences on at least two coordinates. Overlap alone never
establishes non-dominance. Unknown or incompatible **ordered** coordinates make
the pair unresolved. Descriptor-only coordinates do not veto ordering on the
explicit numeric subset, and their exclusion remains visible in the basis.

`definitely_undominated_record_ids` excludes unresolved comparisons as well as
known dominated records. `possibly_undominated_record_ids` excludes only known
dominated records. Both refer solely to this corpus and selected quantities;
with descriptors alone, both lists are empty. These are not whole-biology leaders.

Receipts include the exact basis/directions, record and request hashes, source
identities/locators, preserved population scopes, numeric bounds, incompatibility
reasons, pairwise relations, implementation hashes and Python version. A final
receipt digest binds the result excluding that digest field. Inputs are detached
JSON snapshots; `CoordinateSemantics` is a frozen dataclass. Duplicate coordinate
IDs or duplicate semantic keys reject renamed aliases. Namespace equivalence
across different assay ontologies requires explicit external curation; no
biological synonym discovery is claimed.

Tests in `tests/test_architecture_v1.py` provide runnable synthetic examples,
including tiny/deep versus large/shallow, bound touching, scope mismatches,
unknown linkage/depth, duplicate aliases and forbidden expense/weight inputs.

## Run from the command line

```bash
anibench compare-architecture examples/architecture/protein-inventory.json \
  --out output/protein-comparison.json --pretty
```

The included public example compares two source-reported protein inventories.
It preserves assay and population differences and does not estimate targets
collected per participant. Known source quantities do not need an information
or noise model before they can be viewed or compared. The output file contains
the full result; terminal output contains its identity only. The command rejects
output paths that would overwrite the input, including hardlinks and symlinks.
