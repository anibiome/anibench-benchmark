# Finite estimator-error examples

Five fictional mathematical examples show a pass, a proven failure, a biased
failure, a loose-bound unknown and unresolved support. They are software
examples, not measurements or scores for any human study. A hypothetical iid
Bernoulli sample proportion at p=1/2 has variance 1/(4n); the exact-pass case
uses n=100 and an RMS-error limit of0.05. The failure uses n=25. These are
binary trial counts within the fictional process, not independent people.
The bias example has a faulty recorder that always reports one when the
underlying probability is0.9; its zero variance does not remove its0.1bias.
The loose-bound example keeps n=100 and marginal probability0.5 but leaves
dependence unspecified. No Gaussian approximation enters these calculations.

`METHODS.json` specifies and binds each finite law. Its canonical JSON hash is
recorded in the definition and moment requests. Unknown acquisition support
does not become verified because a conditional moment calculation is supplied.

Run the definition and a request through `anibench estimator-moments` as shown
in `docs/ESTIMATOR_MOMENTS.md`. Change only supported moment assumptions in a
new request; changing an estimator, target, method, context or resolution needs
a new trusted definition. No broad reference-level certification is implied.
