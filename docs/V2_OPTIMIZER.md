# AniBench v2 protocol-native optimizer

Status: executable design sandbox. Public cross-study ranking remains gated.

## Contract

The optimizer answers:

> Under declared resource limits, which explicit protocol changes are
> Pareto-efficient across the selected biological-learning families?

It does not modify a score packet. For every mutation set it:

1. applies JSON Patch-like operations only to measurement or causal protocol
   geometry;
2. validates and recompiles the complete protocol;
3. reads objectives only from compiler-emitted family envelopes;
4. calculates dated, source-pointed resource totals;
5. removes resource-ineligible candidates; and
6. returns the non-dominated candidate set.

Schemas:

- [`optimizer-protocol-input.schema.json`](../schemas/v2/optimizer-protocol-input.schema.json)
- [`optimizer-protocol-result.schema.json`](../schemas/v2/optimizer-protocol-result.schema.json)

Implementation:

- [`optimizer_protocol_v2.py`](../src/anibench/optimizer_protocol_v2.py)

## No hidden overall objective

Objectives name one compiler family path, one uncertainty-envelope bound, and a
direction. The optimizer accepts no metric weights and emits
`overall_scalar: null`. Two objectives cannot point in opposite directions at
the same family envelope.

Resource totals also enter Pareto dominance. Therefore “more informative but
more expensive” remains an explicit trade-off, while “same information but
more expensive” is dominated.

## Anti-gaming rules

- No direct patch to a family result.
- No mutation outside measurement or causal geometry.
- No no-op mutation.
- Every mutation declares at least one positive, dated, source-pointed resource
  delta.
- Resource arithmetic uses exact decimal totals; a delta that disappears at the
  output representation or overflows the result fails closed.
- Sibling list insertions or removals that could shift one another's indices are
  rejected instead of being applied in an arbitrary mutation order.
- Aliases and split panels are deduplicated by canonical ancestry.
- Participant count cannot improve intensive per-event resolution.
- A source-label-only change cannot improve an objective.
- Search expansion is capped before enumeration.
- Custom caller geometry propagates comparison and public-rank holds.

## Example

The example builder accepts a valid base protocol:

```python
from examples.optimizer_protocol_v2_example import build_example_request
from anibench.optimizer_protocol_v2 import optimize_protocol

request = build_example_request(base_protocol)
result = optimize_protocol(request)
```

CLI:

```bash
anibench v2-optimize-protocol request.json \
  --out optimizer-result.json --pretty
```

API:

```text
POST /api/v2/optimize-protocol
```

## Interpretation

Resource magnitudes remain caller-declared until a content-verified cost authority is
bound. That source state is explicit in the receipt.

The returned frontier is conditional on the declared protocol, objectives,
resource model, uncertainty scenarios, and source bindings. It is a design
sandbox frontier—not evidence that any candidate is feasible, approved,
executed, biologically validated, or globally ranked.
