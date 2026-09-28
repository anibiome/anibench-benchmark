# Reproduce the native36 reference designs

These synthetic studies test the standard and finer-resolution profiles of the
current conditional benchmark. They demonstrate finite reference attainment;
they do not determine an optimal human trial or biological saturation.

| Design | People | Independent error blocks per quantity and date | Reads per block | Profile | Pre-run hypothesis |
|---|---:|---:|---:|---|---|
| Standard candidate | 2,048 | 4 | 4 | Standard | Pass |
| Same standard candidate | 2,048 | 4 | 4 | Fine | Fail |
| Deeper candidate | 8,192 | 16 | 4 | Fine | Pass |

Each design assumes complete acquisition of all 36 registered quantities at
nine dates over one year, two sites, two assigned arms and two prespecified
modifier groups. Every person has linked measurements across all panels.
All eight site/arm/modifier groups have equal enrollment. Error-block independence,
measurement noise, source qualification and assignment are explicit hypothetical
assumptions. The two noise scenarios are q=1 and q=2. The finer profile preserves
the standard targets and tightens their precision criteria.

The corrected N170 quantity is face-minus-car mean amplitude at PO8 over
110–150 ms, with a −200–0 ms baseline. Its measurement definition follows the
pinned ERP CORE source in `SEMANTIC_DECLARATION.json`; its hypothetical noise
does not come from an empirical ERP calibration. The declaration retains an
inherited v2 recipe description as historical text; the executable bindings
here are native36-capability-v3. No historical certificate is used as a new result.

## Run one calculation

Use Python 3.12.13. From the repository root:

```sh
python3.12 -m venv /tmp/anibench-reference-env
/tmp/anibench-reference-env/bin/python -m pip install --require-hashes --only-binary=:all: -r examples/reference_witnesses/requirements.lock
/tmp/anibench-reference-env/bin/python -m pip wheel --no-deps --wheel-dir /tmp/anibench-reference-wheel .
/tmp/anibench-reference-env/bin/python -m pip install --no-deps --no-compile --target /tmp/anibench-reference-runtime /tmp/anibench-reference-wheel/anibench-*.whl
/tmp/anibench-reference-env/bin/python -B examples/reference_witnesses/replay.py verify
/tmp/anibench-reference-env/bin/python -B examples/reference_witnesses/replay.py check-runtime --runtime /tmp/anibench-reference-runtime
/tmp/anibench-reference-env/bin/python -B examples/reference_witnesses/replay.py run --runtime /tmp/anibench-reference-runtime --case standard_candidate-standard --out /tmp/anibench-reference-standard
```

Use fresh paths. The runner refuses an existing output directory. Other case
names are `standard_candidate-fine` and `fine_candidate-fine`.
This is a substantial calculation; run one case at a time with one numerical
worker. The hosted workflow caps each job at 120 minutes and the calculation
step at 100 minutes. Hosted artifacts expire after seven days; save the required
results before expiry. No private ANI account, source record or credential is needed.

Only a completed run with successful integrity checks uploads scientific artifacts.
Failed, timed-out or cancelled hosted calculations keep their job logs, but their
partial output files are ephemeral. An unsupported pass/fail hypothesis is retained
as a completed scientific result when integrity checks pass. The one-time execution
tag starts two serial cases; a later manual dispatch deliberately repeats those cases.

The compact recipe regenerates the exact frozen physical acquisitions. Its
SHA-256 check rejects any change. The installed package must match all 292
frozen runtime files and all 19 dependency versions. Building a wheel may change
wheel metadata; it must not change these runtime bytes. The public baseline is
commit `ae003cbb8456604255f392a254c7839d9e682e2b`.

Outputs are `RESULT.json`, `REFERENCE_PROFILE.json`, compressed input and
canonical components, and `RECEIPT.json`. The receipt separates numerical
integrity from whether the hypothesis was supported. A scientifically valid
negative finding must be retained. A hosted run may differ in floating-point
bytes from another platform; it generates a fresh certificate from its own
components and preserves its environment. Never copy a certificate between runs.

This reproduction example contains synthetic designs, original code and public
measurement definitions. It contains no private ELITE measurements or identifiers.
Original code is Apache-2.0; authored synthetic data and documentation are
CC BY 4.0 under the repository licenses. Existing dependencies and embedded
package assets retain their own licenses, including ERP-derived CC BY-SA 4.0
assets. Running the reference is separate from accepting the full benchmark.
