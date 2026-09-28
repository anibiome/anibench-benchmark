<!-- SPDX-FileCopyrightText: 2026 AniBench contributors -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Bind a study design to its evidence

`anibench bind-design` checks that every field of a proposed input has an explicit
source or assumption. It runs offline. The output is an input and evidence
bundle for further validation; it does not calculate a study score or certify
that a source is true.

```sh
anibench bind-design request.json --out new-private-bundle.json
```

The request has exactly three keys: `design`, `bindings`, and `sources`.
`sources` maps canonical JSON digests to local parsed source objects. The design
must not contain `source_sha256`: the adapter derives this identity from its
complete evidence mapping. Use the Python helper `digest()` to construct these
digests; byte hashes of a PDF are a different identity from parsed JSON hashes.

Each binding names one JSON leaf using an RFC 6901 pointer, its `value_sha256`,
a `mode`, and a short `rationale`. Empty arrays and objects also need bindings.
Source references use `source_sha256` and a `pointer` into the corresponding
source object. The supported modes are:

| Mode | What is checked |
|---|---|
| `literal` | The exact source value and design value match, including JSON type. |
| `derived` | A registered arithmetic operation reproduces the design value. |
| `qualified_extraction` | An explicitly trusted review qualifies that exact value, source and locator. |
| `normative_assumption` | The input is explicitly conditional; it is not a source fact. |
| `unknown` | The value remains `null` or `"unknown"`, never zero or absence. |

Available derivations are `sum`, `affine_unit_conversion` with both units and
the declared scale/offset, and `two_set_intersection_lower` or
`two_set_intersection_upper` within a common parent population. Bind lower and
upper bounds to their individual leaves. The Python `derive()` helper also
returns both bounds with `two_set_intersection`.

Integral arithmetic results retain arbitrary-precision integers. Nonintegral
results use finite JSON floating-point values; an approximately integral float
is not accepted as an exact integer count. Correct arithmetic does not establish that the source
sets share a parent, that summed counts are disjoint, or that a conversion has a
valid scientific interpretation. Those claims need source review.

Text extraction requires a separate trust decision:

```sh
anibench bind-design request.json --reviews reviewed-claims.json --out new-private-bundle.json
```

The trusted map is keyed by each review's canonical digest. A review uses schema
`anibench.source-extraction-review.v1` and contains a `claims` list. Each claim
must match the binding's `target`, `value_sha256`, and `source_refs`, with
`disposition: "qualified"`. Supplying a review means the caller trusts it. A
matching hash does not prove independent review, reviewer identity, source
authenticity, or scientific correctness. Omitting `--reviews` trusts no textual
extractions.

The bundle contains the bound design, an intake receipt, and the complete
binding explanations. It does not embed the supplied raw source objects, but
the design or explanations can themselves be private. Keep the bundle local
unless its actual contents have been reviewed for disclosure. Existing output
files are never overwritten. The numerical evaluator must still validate the
study geometry, units, scientific task and declared assumptions.
