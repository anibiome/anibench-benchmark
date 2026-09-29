# Linked observations and measured function

`anibench cross-domain-collection INPUT.json --out NEW_RESULT.json` evaluates a
continuous observer vector and one separately measured functional quantity at
two specified occasions. Observers can be molecular, digital, neural or other
declared biological measurements. The function can be a physical measurement or
a defined cognitive/psychological outcome. Each coordinate retains its native
unit, exact definition and biological domain.

This is a conditional question evaluator. The supplied example combines public
activity and reaction-time definitions in an **invented two-occasion design**.
It is not an evaluation of UK Biobank and does not report measured study scores.
It demonstrates a previously missing input path for non-molecular observations.

```sh
anibench cross-domain-collection examples/cross_domain_collection/input.json \
  --out /tmp/activity-cognition-result.json
```

The output file must be new. Inputs stay local. The JSON schema is
`schemas/cross_domain_collection/v1/input.schema.json`.

## What the calculation answers

The result reports individual observer/function resolution, paired change,
population mean-change precision, and precision for the covariance between
observer change and functional change. Exposure-aligned descriptive change and
an identified controlled contrast have separate support requirements.
Conditional analytical prediction errors remain separate from these quantities
and from actual held-out learning. A domain label grants none of those supports.

An observer vector has one joint precision requirement. Adding aliases or more
copies does not add independent information. Different participant subsets may
support their own measurements without supporting a paired relationship.
Unknown covariance remains unknown. The same model assumptions apply in
planned and realized modes; realized collection additionally needs verification.

The hypothetical example uses the native overall wrist-acceleration average and
matching-card reaction-time summary defined in [UK Biobank field90012](https://biobank.ndph.ox.ac.uk/ukb/field.cgi?id=90012)
and [field20023](https://biobank.ndph.ox.ac.uk/ukb/field.cgi?id=20023).
The source definitions do not establish the example's 256-person joint roster,
annual alignment, covariance, measurement error or target resolutions. Those are
explicit software-example assumptions. Cross-person source standard deviations
are not substituted for instrument measurement errors.

## Relation to the existing mathematics

This adapter introduces no new estimator. It binds the native question, checks
the explicit `observer`/`function` roles, then compiles to the unchanged
[`paired-collection`](PAIRED_COLLECTION.md) estimator. Its legacy `molecular`
slot is only a computational vector slot in this translation. A neural
measurement is never described as molecular in the native results. The exact
compiled-input hash, coordinate mapping and original compatibility receipt are
included for inspection.

For measurement error covariance R, the individual-change error is D R Dᵀ,
where D subtracts baseline from follow-up. Under the declared independent-person
model, the population mean-change variance is D(B+R)Dᵀ/n. All-direction precision
and covariance-estimation equations, gates and uncertainty bounds are inherited
unchanged. Native question/domain changes alter the native receipt even when the
algebra happens to be identical. Duplicate records and irrelevant metadata leave
the calculation identity unchanged.

## Limits

The model requires an appropriate continuous additive-error reference and its
declared independence/homogeneity assumptions. Naming a genotype, read count,
composition, questionnaire or bounded response does not establish such a model.
Source-specific likelihood and measurement validity need separate justification.
The Gaussian approximation in this example is stipulated rather than calibrated.

A covariance relationship is neither a demonstrated predictive gain nor a
causal mechanism. EEG observation alone does not establish neurostimulation
effects. A cognitive response is not a direct neural recording. Clinical benefit
is not required to evaluate the design.

This path is not the whole AniBench reference, a broadly validated study ranking
or an AB1/AB2 saturation certificate. It supplies truthful cross-domain inputs to
the existing question mathematics; the broader benchmark integration is ongoing.
