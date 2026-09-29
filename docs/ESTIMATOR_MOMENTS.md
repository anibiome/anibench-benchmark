# Error of a specified estimator

This development API checks whether a **specified estimator** meets a native
mean-squared-error target under declared moment assumptions. It handles discrete,
continuous and nonlinear targets without declaring their raw observations
Gaussian. It does not discover the best estimator or infer precision from an
assay list. Biological admission and integration into a reference remain separate.

Let `T` estimate the registered target vector `theta`, with covariance `V` and
bias `b = E[T] - theta`. For a frozen linear functional `c`, the identity is

```
E[(c'T - c'theta)^2] = c' V c + (c'b)^2.
```

Finite second moments suffice. For a nonlinear target such as the latency of a
mean EEG waveform, `T` must estimate that exact target. Moments of a different
quantity, such as mean per-trial latency, cannot be substituted. Random
denominators, selection, dependence and estimator bias need their own justified
moment contract. Population variance and covariance estimators may require
fourth moments of the original observations.

The input supplies Loewner covariance bounds `L <= V <= U` and a Cartesian bias
box `b_lower <= b <= b_upper`. These define an outer uncertainty set. For each
functional the evaluator computes exact variance bounds and the smallest and
largest squared bias on that box. It sums those bounds to obtain `[risk_low,
risk_high]`. A missing lower covariance bound means the universal PSD bound zero;
a missing upper covariance bound is unbounded. Missing bias bounds do not mean
unbiasedness. Equal bounds specify exact moments under the declared model.

- **Pass:** qualified support and `risk_high <= mse_limit`.
- **Fail:** qualified support and `risk_low > mse_limit`, or a known failed
  required acquisition/support condition.
- **Unknown:** a bound straddles the limit, is too loose, or support is unresolved.

A conservative upper bound above the limit does **not** prove failure. For
example, an iid Bernoulli mean has variance at most `1/(4n)`. If this bound passes,
it certifies the variance criterion throughout the stated probability range.
If it fails to pass, a smaller variance may still meet the target. Perfectly
dependent trials do not earn the independent-trial reduction.

The secondary precision diagnostic is the interval
`[min(1, limit/risk_high), min(1, limit/risk_low)]`, with the usual zero/unbounded
conventions. It is neither a probability of success nor an information fraction.
All functionals are conjunctive. Their separately extremal bounds need not be
jointly attained by one biological process. This is a finite named-functional
criterion, with no all-direction covariance or confidence-coverage guarantee.

Use `evaluate_estimator_moments(request, trusted_definitions={digest(definition):
definition})` from `anibench.estimator_moments_v1`. The reviewed definition binds
targets, units, estimator methods, independent units, required support, sources
and MSE limits. The request binds lifecycle, physical output identities,
estimator-input mappings, support and moment derivations. Duplicate exports are
coalesced for identity; they never add precision. Realized inputs additionally
require collection verification. Planned inputs are conditional and need no
observed treatment success.

The API interprets `str(value)` of each received Python integer/float as an exact
rational, including PSD and bound-order checks. It cannot recover original JSON
number spellings. The `estimator-moments` CLI rejects duplicate object keys and
decimal numbers that cannot round-trip through that representation without
changing their decimal value, including numeric underflow/overflow. Singular PSD covariance is valid; an indefinite matrix
is rejected without a ridge. Rounded covariance exports that are no longer PSD
must be corrected at the source with documented bounds. The implementation
currently supports up to 128 estimator coordinates per definition. It reports
exact rational risks and approximate display values, with exact threshold
decisions. This choice favors inspectability for finite reference targets.

Run a supplied software example with:

```sh
anibench estimator-moments examples/estimator_moments/definition.json \
  examples/estimator_moments/exact-pass.json --out new-result.json
```

The command creates a new private-permission output and refuses to overwrite
existing files. Structural schemas are in `schemas/estimator_moments/v1`;
dimension, binding, PSD, identity and bound-order checks are enforced at runtime.

Hashes bind inputs and code; they do not certify calibration, biological truth,
causal identification or source validity. The evaluator computes no Gaussian
Fisher information, posterior, empirical learning curve or study ranking.

## Joint separable loss (definition/request v2)

Some biological criteria concern total error across a vector. Definition v2
replaces each functional's `coefficients` with nonnegative `loss_weights`, at
least one of which is positive. It evaluates

```
E[sum_j w_j (T_j - theta_j)^2] = sum_j w_j (V_jj + b_j^2).
```

The loss weights and `mse_limit` must use one declared loss unit. For targets
with unlike native units, the definition must justify the associated weight
units and scaling. Merely adding unlike measurements is not a valid biological
criterion. The evaluator checks structure and arithmetic, not dimensional or
biological truth of the supplied definition.

Nonnegative weights preserve lower and upper variance bounds under Loewner
order. On a Cartesian bias box, each squared bias has minimum zero if its
interval contains zero, otherwise the smaller squared endpoint; its maximum is
the larger squared endpoint. Weighted sums give the exact extrema on that box.
Covariance and bias bounds may be jointly conservative because a particular
estimator law can further couple them. Complete covariance matrices must still
be PSD and consistently ordered, even though this loss uses their diagonals.

Pass, fail, unknown, physical identity and evidence rules are unchanged.
Unknown bias is not zero bias. A constant biased estimator can fail with zero
variance. An excessively loose upper bound cannot by itself establish failure.
This finite registered loss does not imply an all-direction error guarantee.

Use the same CLI, or import the dispatching API from
`anibench.estimator_moments_v2`. It accepts matching v1 or v2 requests and
preserves the v1 result exactly. The v1 API remains available. V2 structural
schemas are in `schemas/estimator_moments/v2`; study-question profile v4 accepts
both versions. Equivalent rank-one and diagonal loss representations cannot
create an extra reference budget by renaming the same target frame.

The [categorical call example](../examples/estimator_moments/quadratic/README.md)
shows why a joint misclassification criterion should be evaluated directly.
Arbitrarily allocated coordinate error limits can be sufficient for its success
without their failure proving that the joint criterion failed. The example
also demonstrates retained bias and missing acquisition verification.
