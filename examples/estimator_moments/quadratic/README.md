# Joint error of a categorical call

This fictional example evaluates a four-class hard call against a joint error
limit of 1%. It contains no study or participant data. `METHODS.json` defines the
complete finite probability law and is canonically hash-bound to the inputs.

The true class is fixed. The call is correct with probability 99.2%, otherwise
it selects one other class. Encode truth and call as one-hot vectors. Half the
sum of squared coordinate errors equals 0 for a correct call and 1 for a wrong
call. Its expectation is therefore the 0.8% misclassification probability.

```sh
anibench estimator-moments examples/estimator_moments/quadratic/definition.json \
  examples/estimator_moments/quadratic/joint-pass.json --out new-joint-result.json
anibench study-questions examples/estimator_moments/quadratic/profile.json \
  examples/estimator_moments/quadratic/study.json --out new-study-result.json
```

| Input | Result | Reason |
|---|---|---|
| `joint-pass.json` | Pass | Exact joint error 0.8% is below the 1% target. |
| `joint-failure.json` | Fail | Exact joint error 3% exceeds the target. |
| `constant-wrong.json` | Fail | A constant wrong call has zero variance but 100% error. |
| `unknown-moments.json` | Unknown | No qualified numerical moment or bias bounds. |
| `unverified-collection.json` | Unknown | The realized acquisition is unverified. |

Dividing the 1% target into four equal coordinate limits would wrongly reject
the first case: two coordinate errors each have MSE 0.8%, above 0.25%. Passing
those allocated limits is sufficient for the joint criterion, but failing them
does not prove joint failure. The evaluator computes the registered joint loss
directly. The study wrapper retains its original receipt and one indivisible
requirement; four coordinates do not create four independent budget votes.

The misclassification identity requires hard one-hot calls. Soft probabilities
have a different squared-error interpretation. These are conditional finite-law
witnesses, not calibrated biological measurements or uniform error guarantees
across people. The 1% cutoff is an example convention. No actual-study ranking,
reference-level saturation or causal claim follows.
