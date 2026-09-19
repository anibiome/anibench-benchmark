<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Finite-task conditional precision mechanism v1

`anibench.finite_tasks_v1.evaluate_finite_task` evaluates a finite declared set of
linear Gaussian targets. It implements a mechanism, not a calibrated AniBench 1
or AniBench 2 task set, benchmark promotion, clinical recommendation, or a
universal biological saturation threshold. The Python API and `finite-task`
command are available on main after RC3; the immutable RC3 package does not
include this later addition. A normative biological task registry remains open.

The input and output contracts are
`schemas/finite_precision/v1/evaluation-input.schema.json` and
`schemas/finite_precision/v1/evaluation-result.schema.json`. Import the evaluator and
`finite_task_sha256`, construct an input matching the schema, and supply the hash
of its complete task. The synthetic examples in `tests/test_finite_tasks_v1.py`
are executable task definitions and do not contain participant records.

`examples/finite_tasks/synthetic-request.json` is a complete example. Its
`source_sha256` is the SHA-256 of the exact bytes of the adjacent
`synthetic-provenance.json`. Its `model_sha256` hashes the provenance file's
`model` object as UTF-8 JSON with sorted keys and compact separators, with
non-finite values forbidden. The task digest uses the same canonical JSON rule
over the complete task. The provenance explicitly identifies an invented
Gaussian model and illustrative domain labels, with no real study or biological
calibration. From an installed main checkout, run:

```sh
anibench finite-task examples/finite_tasks/synthetic-request.json --out finite-receipt.json --pretty
```

The output preserves conditional attainment, required-support states, each
functional's variance and the evidence limits. An unsuccessful or unknown task
is a valid evaluation, while invalid input returns a nonzero exit status.

Receipts bind both evaluator source files (`finite_tasks_v1.py` and
`information_v2.py`), both schema files, and Python, NumPy and jsonschema
versions. Only stable relative labels and digests are emitted, never private
filesystem paths. These identify the actual implementation independently of a
Git tag; they do not assert numerical identity across hardware or BLAS builds.

## What is frozen and what is computed

The task includes its identifier and version, source/model hashes, population,
estimand, horizon, claim lane, parameter units, prior precision, required
acquisition domain/role pairs, and a nonempty set of named functionals. Each
functional declares coefficients c, output unit, and a strictly positive
variance limit v. A variance limit has **squared output units**. The task hash
covers every field; changing any field without rebinding the hash is rejected.
A transformed equivalent task legitimately has a new digest. A hash proves byte
binding, not task quality, independent review or source authenticity. No persistent
registry prevents a caller from creating a different target with a new hash.

Geometry declares likelihood information F and the frozen model identity.
Using the existing `information_v2.prior_whitened_information` validation and
whitening machinery, the evaluator computes

    G = P^(-1/2) F P^(-1/2)
    variance(c) = (P^(-1/2)c)^T (I+G)^(-1) (P^(-1/2)c).

P is the task's positive-definite prior precision. The solve avoids an explicit
posterior inverse. Each functional passes if its variance is at most
`variance_limit * (1 + 1e-10)`. The fixed relative tolerance handles numerical
boundary error and scales consistently under unit conversion. It is not a
scientific equivalence margin. The exact floating-point variance and limit are
reported without decimal clipping. Each functional also reports its prior
variance, `prior_only_precision_attainment`, and variance reduction from that
baseline (null when geometry is unknown). A strong prior with zero information
can legitimately attain a loose posterior-precision target; the receipt then
shows prior-only attainment and zero acquired variance reduction. No arbitrary
penalty is imposed, and same frozen-task/prior comparisons remain essential.
Variance reduction is clamped at zero for negligible numerical roundoff; it is
not an independently calibrated biological-information measure.

For theta = T eta, precision matrices become T^T P T and T^T F T, while
functional coefficients become T^T c. Functional variance is invariant under
this joint change. Rescaling the functional's output by k instead multiplies
variance and its limit by k^2. Tests cover both and a nonidentity prior.

## Noncompensatory evidence and lane semantics

A required support pair is a `domain_id` and an `observation` or `perturbation`
role. Evidence for each pair is strictly true, false or null. Omitted pairs and
null values remain unknown; a declared verified absence is false. Extra pairs
are validated but do not affect the task's conjunction. Duplicate pairs are
rejected. The interface trusts caller declarations only within its explicitly
conditional scope; it does not independently verify a laboratory or protocol.

Attainment is three-valued: any failed required support, identifiability or
precision condition gives `not_attained`; otherwise an unresolved required
condition gives `unknown`; only all-pass gives `attained`. A missing neural
observation cannot be compensated by arbitrarily precise molecular observations.
A narrow task need not require neural acquisition. Evidence for neural diagnostic
observation does not satisfy a separate neural perturbation requirement. These
role gates do not replace a full stimulation protocol, randomization, sham,
exposure, timing or target-engagement audit.

`conditional_design` uses planned geometry and does not require collection
completion, treatment success or demonstrated model utility. Later collection
verification is ignored in this lane. `realized_record` additionally requires
`collection_verified: true`. Both require declared identifiability support.
Neither lane claims empirical learning plateau; that lane is deliberately
unsupported here. Missing geometry is represented as null and yields unknown
precision, while malformed or non-finite geometry raises `FiniteTaskError`.
A failed required support can still establish `not_attained` when geometry is
unknown. Boolean fields reject numeric 0/1, strings, lists and objects.

## Finite functionals are not all directions

The result explicitly sets `all_direction_attainment` and
`empirical_learning_plateau` to null, and public saturation/promotion permissions
to false. For posterior covariance `[[0.5,0.49],[0.49,0.5]]`, two coordinate
functionals with variance limits 0.5 both pass. The independent all-direction
reference diagnostic nevertheless gives a worst variance ratio of 1.98 against
reference posterior 0.5 I. Both statements are correct: the finite task did not
require the rotated weak direction. Do not relabel its success as joint
reconstruction or all-biological-domain coverage.

## Depth, population and limitations

A synthetic test derives F using the actual event-information helper. Two people
with complementary high-precision observations meet both chosen functional
limits. A million people measured on one direction attain better precision on
that direction but fail the unobserved second functional. There is no overall
rank, arbitrary small-N penalty, spending credit, or automatic population
transport claim. The target model determines whether parameters are shared
population quantities or person-specific states; this module does not infer
that choice from a headcount.

Noise degradation, zero observations, nearly singular positive-definite noise,
strict identity binding, absent/unknown support, diagnostic versus perturbation
roles, typed inputs and schema-valid outputs are tested. Model validity, prior
calibration, source authenticity, causal identification, QC evidence and the
biological relevance of functionals remain obligations outside this mechanism.
A strong prior can meet a loose precision target with little likelihood
information; results must be read with the frozen prior and target. No conclusion
about incremental information is substituted for posterior precision.

Both schemas and the synthetic example are included in builds from main. The
six-family evaluator and its existing receipts retain their contracts; this
finite-target mechanism is a separate conditional instrument.
