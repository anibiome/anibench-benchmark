<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Runnable conditional ERP suite example

This example uses the shipped **illustrative** P3b current-session precision
profile and the existing public aggregate measurement-error result. It is not
AniBench1/2 calibration or a study's observed performance. No participant files,
network access or optional scientific-file readers are required.

From a fresh checkout with AniBench installed in its environment:

```sh
python examples/finite_suites/replay_erp.py --out /tmp/anibench-erp-suite-new
```

For an installed package whose example assets are included, locate and run it:

```sh
python -c 'import anibench; from pathlib import Path; print(Path(anibench.__file__).parent / "examples/finite_suites/replay_erp.py")'
python /the/printed/path/replay_erp.py --out /tmp/anibench-erp-suite-new
```

The script discovers packaged or checkout assets. Alternatively supply all three
explicit read-only paths with `--aggregate`, `--profile` and `--source-manifest`.
The aggregate and R1 profile bytes are pinned in the script; the source manifest
must match the profile's source digest. Changed inputs fail rather than silently
changing the example. The destination must not exist. No generated output belongs
in the source checkout.

The script evaluates source-schedule multipliers **1, 22, 23, 90 and 91** through
`evaluate_finite_suite`. It builds R2 as a stricter child retaining the same
scientific frame, prior, roles and model, with one quarter of R1's variance limit.
The illustrative marginal Gaussian half-widths are 1 and 0.5 microvolt. These are
normative demonstration choices, not empirically established biological minima.

Information is calculated as `J = d / v`: `v` is the source's mean analytic
variance of the fixed-window P3b contrast, and `d` is a hypothetical source-schedule
multiplier. **The source mean does not guarantee every person's precision.**
`v` is not single-trial noise, `d` is not a literal trial count, and inverse-depth
scaling is an explicit modeling assumption. No stable-person versus session
variance decomposition, repeated-session calibration or population transport
validity is inferred.

Two separate custom profiles provide a zero-data/strong-prior adversary. Total
posterior precision can pass while likelihood-only collection precision fails.
Those custom profiles change the prior and are not members of the R1/R2 hierarchy.
Planned role support is declared for this adversary; no collection is claimed.

Outputs include `trusted-profiles.json`, one source-provenance file per hypothetical
design, twelve requests and actual suite receipts, `results.json` and `RESULTS.md`.
R1 passes at 23; R2 passes at 91 under these assumptions. Each request, scenario and
target binds the same design ID and SHA-256 of its exact generated provenance file.
The provenance binds script, input and registry bytes. Receipt implementation
hashes bind the actual evaluator. These are reproducibility identities, not an
independent verification of a real collection protocol.

Original Python and tests are Apache-2.0. Generated source-derived data and reports
are **CC-BY-SA-4.0**, with ERP CORE/Kappenman/Luck and Zhang/Luck attribution inside
the output. The ERP source package retains its source-license discrepancy and
calibration limitations; see [its README](../calibration/erp_core/README.md). No
source workbooks or participant rows are copied.
