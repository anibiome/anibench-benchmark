<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Conditional finite-suite profiles

`anibench.finite_suites_v1.evaluate_finite_suite(request, trusted_profiles=registry)`
executes frozen profiles through the existing finite-task evaluator. The caller
supplies a trusted local registry keyed by `suite_sha256(profile)`; no network
registry is fetched. Inputs are detached JSON snapshots. A trusted digest proves
identity, not scientific correctness. A `normative` profile is a governance
choice; `custom` and `illustrative` profiles never acquire official status by
passing. The result preserves `promotion_allowed=false` and
`public_saturation_claim_allowed=false`.

The strict input schema contains the profile schema in `$defs.profile`. Each
profile binds exact tasks, canonical target IDs, scientific-frame digests,
precision basis, shared scenario IDs, tolerance authority and calibration
authority. Use `scientific_frame_sha256(task)` to compute frame identity. A
request contains one row per frozen scenario and optional target rows; each
present target has a canonical ID, `known_absent` Boolean and an existing
finite-task request or null. The request, each scenario and each supplied target row must carry the same
`design_id` and `design_source_sha256`. These bind the caller-declared source
identity to every geometry in the receipt; they do not independently verify the
source bytes, collection or scientific derivation. Missing/unverified required targets remain unknown;
known absence fails. Duplicate IDs, renamed equivalent target frames, unregistered
targets, changed frozen tasks and stale hashes raise errors.

```python
from anibench.finite_suites_v1 import evaluate_finite_suite, suite_sha256

# profile and request are finite JSON objects matching the installed schemas.
registry = {suite_sha256(profile): profile}
request["profile_sha256"] = suite_sha256(profile)
receipt = evaluate_finite_suite(request, trusted_profiles=registry)
```

Every required target and role must pass. With `all_declared_scenarios`, every
scenario must pass. With `exists_declared_scenario`, at least one **same** scenario
must pass every target. Favorable assumptions from different scenarios cannot be
combined. `single_conditional` requires exactly one scenario. A finite scenario
set is not a calibrated confidence region. The profile's frozen model identities
must describe the common scenario assumptions; this engine checks identity and
precision, not whether supplied information matrices were scientifically derived.

`likelihood_only` requires precision supplied by the declared collection model.
The additive `functional_likelihood_precision` helper uses the existing prior
whitening and a range-tested generalized inverse. Missing directions never obtain
zero variance from a pseudoinverse. Any nonzero functional coefficient on an exactly zero information row/column
fails, even when that coefficient is tiny. Confident full rank on the exact structural support must hold in both the raw
information matrix and the prior-whitened matrix; whitening cannot turn
roundoff amplified by an ill-conditioned prior into an identified direction.
Near-zero positive or tolerated negative eigenvalues do not certify rank.
These conservative checks can return unknown after an extreme change of units.
Full rank under both checks certifies the range; other numerically singular ranges conservatively
produce unknown, including rotated identifiable functionals where floating-point
evidence cannot certify exact range membership. A small residual is never used
as a pass tolerance. Rank tolerance and range residual are recorded. Returned
identified variances must be finite and strictly positive; numerical underflow or
overflow raises an error. The prior
is a whitening metric, not data. `posterior_total` legitimately permits a strong
prior to satisfy precision; original task receipts always show prior-only
attainment. A positive trace or tiny variance reduction does not establish
adequate acquired precision.

A child profile binds its parent digest, retains canonical scientific targets
and required roles, and cannot loosen variance limits or change inherited
functionals, precision basis or scenario frame. Unit/parameter transformations
belong in a separately reviewed frozen task; the numerical helper is invariant
under consistent transformations away from finite-precision rank boundaries.
Same-frame sign/scale aliases are rejected without attempting automatic biological
alias discovery. Required neural observation cannot be replaced by molecular
depth. Sensory input, neural observation and direct cortical intervention use
different domain IDs. A cortical extension is a separately named child profile
with required assignment, response and control roles; its absence does not change
an independently evaluated core profile. No treatment benefit is required.

Planned and realized profiles stay distinct: planned capacity does not require
verified collection or model utility; realized tasks require collection
verification. Empirical learning plateau is never inferred. Finite profile
attainment is neither all-direction covariance order nor saturation of biology.
The existing all-direction diagnostic remains separate.

## Illustrative ERP component

[`erp-p3b-resolution.json`](../spec/finite_suites/v1/erp-p3b-resolution.json)
chooses a marginal Gaussian 95% half-width of 1 microvolt, giving variance limit
`(1 / 1.959963984540054)^2`. This is an explicit illustrative resolution choice,
not an empirically discovered biological minimum or full AB1 profile. It binds a
source-manifest digest and a model-description digest (SHA-256 of the UTF-8
`calibration_authority` string). It supplies no information matrix or empirical
noise number: those require a declared design/calibration scenario. The registered
sensory task is not direct cortical stimulation.

Source protocol attribution: ERP CORE by Emily S. Kappenman and Steven J. Luck;
Kappenman et al. (2021), [ERP CORE](https://doi.org/10.1016/j.neuroimage.2020.117465).
The source-derived profile is CC-BY-SA-4.0; its source-manifest and calibration
limitations are described in the [ERP example](../examples/calibration/erp_core/README.md).
No source records are included. Original suite code is Apache-2.0. No new biological
variance calibration is claimed by this mechanism.

Receipts bind the suite code, information helper, finite-task implementation,
schemas, profile, request and numerical runtime. Digests are computed from files
at evaluation time; no self-referential file hash is stored inside those files.

## Run the packaged example

The [ERP suite replay](../examples/finite_suites/README.md) creates twelve
conditional requests, actual receipts and a trusted profile registry from the
shipped aggregate. Run it, then reproduce one receipt through the CLI:

```sh
python examples/finite_suites/replay_erp.py --out /tmp/anibench-erp-suite-new
anibench finite-suite /tmp/anibench-erp-suite-new/R1-depth-23.request.json \
  --registry /tmp/anibench-erp-suite-new/trusted-profiles.json \
  --out /tmp/anibench-erp-suite-cli.json --pretty
```

The same example is shipped inside the wheel; its README provides the installed
path. The CLI requires an explicit local registry and refuses an output path
that aliases either input. Console output contains receipt identities and
attainment, without echoing local paths.
