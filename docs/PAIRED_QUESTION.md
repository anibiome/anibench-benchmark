# Linked molecular measurements and function

`anibench paired-question INPUT --out NEW_RESULT` evaluates one declared
biological question using linked observations at two occasions. It separates
measurement resolution, precision of change and relationships, descriptive
response to exposure, an identified assignment effect, and expected performance
of a specified linear learner. It is a conditional research component of
AniBench. It does not produce a whole-study rank or an AniBench 1 certificate.

Run the entirely invented example from a checkout:

```sh
anibench paired-question examples/paired_question/input.json --out paired-result.json
```

For an installed package, find the included example with
`importlib.resources.files("anibench").joinpath("examples/paired_question/input.json")`.
The command runs locally, makes no network requests and creates a new result
file. It refuses to overwrite an input or an existing output.

## Input and interpretation

The input binds a question, a covariance scenario and a proposed or collected
design. The question fixes native quantities and units, population, two times,
and precision tolerances. The scenario supplies biological covariance `B` and
additive measurement-error covariance `R` in the ordering
`[all baseline coordinates, all follow-up coordinates]`. Missing covariance is
`null`. Neither assay names nor participant counts supply it automatically.

The count is the number of independent people supporting the homogeneous
question-specific acquisition pattern. It must not be copied from total
enrollment when only a subset has the required measurements. This version does
not combine partial-overlap strata, heterogeneous errors, uncertain calibration
or multiple outputs sharing one physical assay. Such inputs need an explicit
adapter, not invented complete cases. Acquisition IDs identify slots in this
aggregate design; the input contains no participant rows.

For disjoint subsets with different acquisitions or a molecular assay with
multiple outputs, use [`anibench paired-collection`](PAIRED_COLLECTION.md).
It applies these same equations to each question's supported people and retains
unresolved acquisition bounds. It still requires a homogeneous reference model.

Each support flag is explicitly `true`, `false` or `null`. A known failed
requirement dominates an unresolved one. A closed inventory distinguishes an
absent acquisition from one whose presence is unknown. Repeated copies of the
same acquisition give no extra information. Planned inputs need no treatment
result; realized inputs also require collection verification. A true flag is a
declaration, not independent verification by this program.

| Output | What it measures |
|---|---|
| State | Measurement-error covariance of a baseline molecular vector or force reading. More people do not improve one person's reading. |
| Individual change | Error of subtracting that person's linked measurements. |
| Mean change | Sampling precision of mean paired change across independent people. |
| Molecular–function relation | Precision of the vector of covariances between molecular change and functional change. This is association precision, not causal mechanism. |
| Exposure-aligned change | Descriptive functional change around a documented exposure. It need not identify an untreated counterfactual. |
| Controlled effect | Precision of an identified two-arm assignment/ITT mean-change contrast. A null effect can be informative. |
| Conditional learning | Expected new-person error of fixed baseline-input OLS routes under the declared Gaussian reference. Actual held-out performance remains `not_evaluated`. |

Ethics, publication, study name and expense do not enter the calculation. Each
receipt binds the exact inputs and evaluator identity; a separate calculation
hash excludes design metadata and duplicated acquisition rows.

## Mathematics

Let `V=B+R`, `D=[-I,I]`, `W=D V Dᵀ` and `n` be independent complete people.
State error is `R00`; individual change error is `D R Dᵀ`; mean change has
covariance `W/n`. These identities require finite second moments, unbiased
additive error and the stated independence, but do not require Gaussian data.

For Gaussian changes, the unbiased sample covariance `S` uses denominator
`n−1`, and

`Cov(S_ab,S_cd) = (W_ac W_bd + W_ad W_bc)/(n−1)`.

Subtracting a known error covariance corrects expectation without reducing this
sampling covariance. This estimator covariance is not Fisher information and
is not passed to the legacy likelihood evaluator as if it were a likelihood.

With independent arms and the explicitly assumed common covariance, the
mean-change contrast has covariance `W(1/n0+1/n1)`. Assignment identification,
pairing, timing and independent functional acquisition have separate gates.
This does not establish individual causal effects or actual-exposure efficacy.

For each precision output, let `C` be its full estimator covariance and `T` the
diagonal matrix of positive native-unit tolerances. Define
`r = λmax(T⁻¹ C T⁻¹)`. Attainment requires `r≤1` within the published numerical
tolerance `1e-10`; continuous adequacy is `100 min(1,1/r)` (100 when `r=0`).
This is progress toward that explicit covariance limit, not probability,
simultaneous confidence coverage or a percentage of biology. An unresolved
requirement retains the interval 0–100; a known unsupported requirement is 0.
The numerical example's tolerances are invented and are not adopted AB1 limits.

For jointly Gaussian baseline predictors `X` and follow-up measured function
`Y`, residual variance is `s²=Vyy−VyX VXX⁻¹ VXy`. OLS with a fitted intercept,
`p` predictors and `n>p+2` training people has expected independent noisy-target
test MSE `s²(1+1/n)(1+p/(n−p−2))`. Centered predictor scatter has `n−1` Wishart
degrees of freedom; its inverse expectation supplies the `n−p−2` denominator.
Intercept estimation and a new test observation supply the remaining terms.
The intercept-only risk is `Vyy(1+1/n)`. These are analytical expectations, not
trained-model results. Small-N divergence concerns unregularized OLS, not every
possible learner. Nonzero target–predictor error covariance makes that route
unknown because it could exploit shared measurement error.

## Limits and falsification

Two independent binary inputs can determine their product even though each
alone has zero correlation with it. An unrelated target can have the same
covariance matrix and be unpredictable. The executable nonlinear counterexample
in `tests/test_paired_question_v1.py` shows why covariance alone cannot measure
all complementary biological information. No unconditional exponential bonus
or claim of comprehensive functional translation is made here.

Strict input validation rejects unknown scientific fields, numeric strings,
boolean measurements, inconsistent hashes and conflicting acquisition IDs.
Numerically unresolved rank, overflow or underflow must not create a false
perfect score. Extreme units may therefore yield unknown rather than a precise
answer; use well-conditioned native units. The complete input JSON Schema is
`schemas/paired_question/v1/input.schema.json`.
