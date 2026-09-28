## Mathematical properties and failure conditions

The following statements concern the declared experiment and fixed workload.
They are not empirical claims about every biological assay. They identify what
the evaluator can guarantee and which inputs scientific review must establish.

### Estimable functionals

For a linear Gaussian experiment with known positive-definite R, the score
derivative gives likelihood information J = H^T R^-1 H. A linear functional
c^T theta is identified exactly when c belongs to the range of J. Its
likelihood variance is c^T J^+ c on that range. J^+ denotes the Moore-Penrose
inverse. This expression must not be used for a functional outside the range:
the pseudoinverse would discard an unobserved direction and report false
certainty. A null direction is unbounded by the observations, even if a prior
assigns it a small variance.

The implementation is deliberately more conservative than the exact algebra.
It checks rank in the raw and prior-whitened information matrices, recognizes
exact structural zero rows/columns, and requires a full-rank certificate on
the remaining structural support. A general numerically singular rotated
subspace remains unknown rather than being certified from a small projection
residual. The prior-whitening metric assists numerical analysis; no prior-only
pass is credited as acquired information. Finite floating-point tolerances
are recorded in each receipt and can make borderline classifications depend
on the numerical environment.

### Additional valid information cannot worsen identified precision

On a fixed identified parameter space, let J_1 be positive definite and let
Delta be positive semidefinite information from additional conditionally
independent, correctly modeled observations. Then J_2 = J_1 + Delta and
J_2^-1 is no larger than J_1^-1 in the positive-semidefinite order. To see this,
whiten by J_1: I + J_1^-1/2 Delta J_1^-1/2 has eigenvalues at least one;
its inverse has eigenvalues at most one. Transforming back proves the result.
Thus every fixed functional variance can only decrease. In exact arithmetic,
fixed-threshold attainment and precision adequacy cannot decrease when their
support and identification conditions remain unchanged. Numerical software
classification has a separate limitation: adding an extremely strong direction
can make a weaker direction numerically unresolved under a relative-rank
tolerance. For example, J=I changed to diag(1e20,1) leaves the second
coordinate's exact variance at one, but the conservative implementation returns
unknown for the latter matrix. The theorem does not promise monotonic
floating-point classification under arbitrarily ill-conditioned inputs.

This proposition does not justify adding information matrices for dependent
observations, mixing populations, or ignoring newly discovered bias. A revised
model or evidence correction can lower a previously overstated result. For
correlated acquisitions, use the full joint observation model or its justified
conditional innovation, not an independent-observation sum.

### Exact copies do not add information

If a recorded value y is copied, the pair (y,y) is a deterministic transform of
y, and y can be recovered from the pair. They generate the same statistical
experiment. Treating the two entries as independent changes the model and is
invalid. Physical acquisition identity therefore belongs in the input contract.
The correlated-repeat example gives the same conclusion: for k exchangeable
repeats with correlation rho, the mean variance is sigma^2[1+(k-1)rho]/k.
At rho=1, it is sigma^2 for every k. At rho=0, it is sigma^2/k. The current
reference restricts rho to [0,1]; it does not claim that all biological noise
has this exchangeable form.

### Complementarity differs from repeated precision

Consider independent unit-variance observations with rows H_1 = [1,1] and
H_2 = [1,-1]. Each alone identifies one sum or difference, but neither identifies
theta_1 or theta_2 separately. Together J = 2I, yielding variance 1/2 for each
coordinate. Repeating the first row independently reduces uncertainty in the
sum while leaving the difference unidentified. This is a nonlinear gain in
the set of answerable questions, without assuming an exponential bonus for
each modality label. A real modality earns this interpretation only through
a defensible operator and covariance.

### Units do not define the ranking

Under an invertible change of parameter units theta' = A theta, the transformed
information is J' = A^-T J A^-1 and the transformed functional coefficients are
c' = A^-T c. On an identified space, c'^T J'^-1 c' = c^T J^-1 c. If the reported
target itself is rescaled by a scalar b, both its variance and its ceiling must
be multiplied by b^2. The threshold decision and variance-to-ceiling ratio then
remain unchanged. Inconsistent conversion of a source variance or a target
ceiling is a different, invalid input. Numerical extreme-unit cases can remain
unresolved under the conservative rank checks.

### Fixed workload bounds and scenario coherence

For fixed nonnegative normalized task masses, every assignment of unresolved
tasks to pass or fail lies between confirmed-pass mass and confirmed-pass plus
unresolved mass. This proves the reported epistemic outer interval. It does
not prove that its endpoints are jointly feasible. If tasks A and B can pass
only in mutually exclusive scenarios, their separate optimistic possibilities
cannot establish a simultaneous level pass. The evaluator applies the declared
scenario quantifier to complete task vectors before deciding attainment.

Copying or renaming a task cannot legitimately add workload mass. Exact
canonical duplicates and invalid partitions are rejected by the software.
Biological synonymy across newly authored frames still needs scientific
review; a hash cannot detect a misleading scientific redefinition. Subdividing
one requirement must preserve its original total mass if the claimed workload
is unchanged. New versions may deliberately change the workload, but cannot be
compared as though their denominators were identical.

### Nested levels

Suppose a child profile retains every parent task's scientific frame, support
and scenario semantics, and does not loosen any inherited precision ceiling.
If all child requirements pass under the declared coherent scenario rule, all
parent requirements pass under the same conditions. This is the level
inheritance guarantee. It is violated by changing populations, dropping a
parent task, relaxing a ceiling, or assembling passes from different scenarios;
these are checked separately from numerical score rounding.

### What these properties do not prove

Sampling precision is not protection against bias. For an estimator with bias
b and variance v, mean squared error is v+b^2. Increasing N can reduce v while
leaving b unchanged. The native-summary route estimates the sampling term and
must not describe it as total biological truth. Likewise, full-rank design
geometry does not establish exchangeability, randomized assignment, adherence, absence of interference, measurement equivalence or transportability.

Unknown population support, linkage or covariance must be resolved by evidence,
an explicitly conditional scenario, or an alternative model. Neither spending,
prestige, publication, ethics status nor a favorable observed treatment effect
supplies missing mathematical information. These remain separately reported
properties of the source and study.
