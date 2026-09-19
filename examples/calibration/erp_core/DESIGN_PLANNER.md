<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# A conditional design planner with joint constraints

Given declared precision limits, this executable searches a declared grid of
independent people, visits and per-visit measurement depth. It asks whether the
**same** model assumptions can satisfy all three limits. It does not establish
biological precision limits, the ideal human study, or AniBench 1/2 attainment.

The [source calibration](REPORT.md) estimates within-session contrast noise
`v = 5.859430882401938 µV²` and combined person-plus-session variance
`A = 9.360227534862045 µV²`. It cannot separate persistent-person variance B
from session variance S. The planner retains every decomposition
`0 ≤ S ≤ A`, `B = A − S`, at these fixed plug-in estimates.

## Run and change the target

From the repository root, with Python and no additional dependencies:

```sh
python examples/calibration/erp_core/plan_design.py \
  --aggregates examples/calibration/erp_core/aggregate_results.json \
  --request examples/calibration/erp_core/illustrative-plan.json \
  --out /path/to/new-plan-results.json
python -m pytest tests/test_erp_design_planner.py
```

The output must be a new file. Inputs are read only; no network request or
participant-level input is used. SHA-256 binds the aggregate, request and
executable. A hash establishes content identity, not truth of a supplied
aggregate or target. Runtime version is recorded.

Copy the request and declare all three `variance_limits_uV2` keys. A limit of
`null` means unknown; it is not zero or permission to omit a requirement. Zero
is a literal zero-variance target. `target_status` must be `illustrative` or
`user_declared_unvalidated`, and a rationale is required. This planner has no
target-certification mechanism. Unknown fields, duplicate JSON keys, duplicate
grid values, nonfinite numbers, booleans used as numbers and grids over 10,000
designs are rejected. The grid limit bounds computation, not biology.

Variance ceilings use squared precision units; they are not automatically
confidence intervals, effect sizes, power requirements or simultaneous
coverage. Converting a half-width to a ceiling needs a separately justified
coverage rule and distributional model.

## Shared-parameter feasibility

Under the [declared independent additive model](DESIGN_SENSITIVITY.md), for
N independent people, k hypothetical visits per person and source-schedule
depth multiplier d:

```
current-session error variance   = v/d
persistent-person error variance = S/k + v/(k*d)
population-mean variance         = [A - S + S/k + v/(k*d)]/N
```

Current-session precision uses that session's readings. Other visits do not
sharpen that particular state without another temporal model. Persistent-person
precision concerns the unshrunk average over visits. Population precision also
retains sampling variation across people. d proportionally scales both
condition trial counts; it is not the number of raw readings.

Write the ceilings as c, p and q. Current-session feasibility requires
`v/d ≤ c`. Persistent precision requires `S ≤ k*p − v/d`.
For `k > 1`, population precision requires:

```
S ≥ [A + v/(k*d) - N*q] / (1 - 1/k)
```

For `k = 1`, population feasibility is instead independent of S:
`A + v/d ≤ N*q`. The executable intersects all inequalities with `[0,A]`.
It compares exact rational representations of supplied numeric values' decimal
strings; it never merges an empty interval into a pass using a tolerance.
Arithmetic exactness for those values is not knowledge of the true variances.
Python's JSON number parsing determines the input values; no arbitrary-precision
decimal-input contract is claimed.

| Status | Meaning within the declared model and precision targets |
|---|---|
| `robust` | Every S in the original `[0,A]` satisfies all required ceilings |
| `assumption_sensitive` | A nonempty strict subset satisfies all ceilings together |
| `infeasible` | No shared S satisfies the known ceilings for this design |
| `unresolved` | A ceiling is unknown and the known constraints are consistent |

A contradiction among known constraints remains infeasible even when another
ceiling is unknown. An unresolved design never enters a passing frontier.
Robust refers only to the retained B/S split, not uncertainty in A and v,
alternative dependence, model bias or population transport.

## The counterexample a separate-task check misses

Use invented values `A=8`, `v=1`, `N=2`, `k=4`, `d=1`, with current ceiling 1,
persistent ceiling 1 and population ceiling 1.25 in a common squared unit.
Persistent precision requires `S ≤ 3`; population precision requires
`S ≥ 23/3`. Each is individually possible on `[0,8]`; their intersection is
empty. Taking the favorable endpoint for each task incorrectly approves this
design. The executable rejects it.

It also rejects confusing an infinite-depth limit with a finite solution.
At k=1, N=2 and A=8, population variance approaches 4 from above as d increases
when v>0. No finite d reaches a ceiling of exactly 4.

## Reproducible illustrative grid

The [request](illustrative-plan.json) deliberately invents ceilings 1.5, 1.0
and 0.04 µV² for current, persistent and population precision. They demonstrate
the software; they are not validated biological tolerances. The 105 candidates
combine N={2,20,40,100,250,500,2000}, k={1,2,4,8,12}, d={1,4,16}.

The [receipt](illustrative-plan-results.json) contains 6 robust,
27 assumption-sensitive and 72 infeasible designs. Componentwise resource
frontiers in `(N,k,d)` use no prices or weighted overall score:

| Frontier | N | Hypothetical visits k | Depth multiplier d |
|---|---:|---:|---:|
| Robust to all retained B/S splits | 250 | 12 | 4 |
| Possible for at least one common split | 40 | 12 | 4 |
| Possible for at least one common split | 100 | 8 | 4 |
| Possible for at least one common split | 250 | 1 | 16 |
| Possible for at least one common split | 250 | 2 | 4 |

These are nondominated members of the **listed grid**, not global minimum
enrollments or recommended studies. A possible frontier can contain designs
that require different splits; one split need not make all its designs adequate.
The receipt preserves each design's admissible interval. A robust design may be
dominated on the possible frontier by an assumption-sensitive design. The two
frontiers answer different questions.

Changing the ceilings changes the answer. More measurements cannot erase
independent-person sampling variation or create a missing modality. This ERP
example says nothing about absent metabolic, immune, functional, digital,
spatial or causal tasks. Passing it cannot stand in for the candidate six-task
biological suite. Treatment benefits are not ranked.

Source-derived analysis: ERP CORE contributors, Zhang and Luck (2023),
[doi:10.1111/psyp.14264](https://doi.org/10.1111/psyp.14264), with AniBench
modifications under CC BY-SA 4.0. Original planner and tests: Apache-2.0.
The [source license boundary](README.md#license-boundary) is unchanged.
No endorsement is implied.
