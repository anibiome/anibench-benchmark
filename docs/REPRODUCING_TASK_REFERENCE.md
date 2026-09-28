# Reproduce the task reference and paper

The methods manuscript is `paper/task_reference/AniBench_task_reference.md`.
The current recipe is specified in `REFERENCE_RECIPE_V04.md`. The core
calculations and public examples run locally; a browser, account and participant
upload are unnecessary.

## Exact reference environment

The reviewed environment uses CPython 3.12.13, NumPy 2.5.1 and jsonschema 4.26.0.
The native-pilot chart replay was checked with Node.js 24.18.0. The package also
declares broader compatible Python/dependency ranges for normal use; that does
not promise identical receipt hashes across those ranges. Do not relax a hash
check to hide a runtime mismatch.

From the matching release checkout, with `uv` and the named Python available:

```sh
uv venv --python 3.12.13 .reproduce
uv export --frozen --no-dev --no-emit-project --format requirements-txt --output-file runtime-requirements.txt
uv pip sync --python .reproduce/bin/python --require-hashes runtime-requirements.txt
uv build --out-dir candidate-dist
uv pip install --python .reproduce/bin/python --no-deps candidate-dist/anibench-2.0.0rc6.dev0-py3-none-any.whl
```

Use fresh paths for the environment and generated files. `uv.lock` supplies the
runtime pins and distribution hashes. Hatchling 1.32.4 is the pinned build
backend. Build receipts also record the resolved build environment; the package
does not promise identical archives under arbitrary build tooling. Dependency
installation may access package indexes. Example evaluation is offline afterward.

Run the example from its **installed** resource directory to avoid accidentally
importing a checkout. For example, in a directory outside the repository:

```sh
/path/to/checkout/.reproduce/bin/python -I -c 'from pathlib import Path; import anibench, runpy, sys; p=Path(anibench.__file__).parent/"examples/native_mean_pilot/replay.py"; sys.argv=[str(p),"--out","native-pilot-result"]; runpy.run_path(str(p),run_name="__main__")'
```

This recompiles 360 derivations and six canonical suite receipts and checks exact
pilot JSON and shared-renderer SVG output. Node must be available on PATH; the
example also accepts `--node /path/to/node`. Inputs are published factual
aggregates and explicit assumptions, not participant records.

The cognitive/neural example has a separate replay:

```sh
/path/to/checkout/.reproduce/bin/python -I -c 'from pathlib import Path; import anibench, runpy, sys; p=Path(anibench.__file__).parent/"examples/cognitive_neural_precision/replay.py"; sys.argv=[str(p),"--out","cognitive-neural-result"]; runpy.run_path(str(p),run_name="__main__")'
```

It reproduces 12 native records, 72 diagnostics, 216 derivations and 24 suites.
These are repeated analyses of the disclosed source families, not 216 studies.
The cognitive/neural README explains operator-specific comparisons, selected
MMSE populations, unknown hemisphere weighting and unthresholded cortical data.

## Evaluate a planned design

```sh
.reproduce/bin/python -c 'import json; from anibench.reference_planner import default_request; print(json.dumps(default_request(), indent=2))' > design.json
.reproduce/bin/anibench plan design.json --out design-result.json
```

Edit the baseline and changed design declarations in a new input file. The
request contains N, modeled depth, technical repeats/correlation and required
support. The receipt contains the full frozen tasks, geometry, scenario results
and exact level decisions. Output paths are create-only. The planner does not
infer a biological noise model from an assay list.

For a source-qualified summary, use `anibench summary-task` as documented in
`SUMMARY_GEOMETRY.md`; it compiles `task`, `summary` and `evidence` to the same
finite-task engine. To evaluate a workload, use `anibench benchmark` with trusted
task and score registries as documented in `WORKLOAD_PERCENTAGES.md`. Trust is a
local scientific choice; a successful schema check does not validate a source.

## Recheck mathematical properties

```sh
.reproduce/bin/python paper/task_reference/verify_math.py --out math-receipt.json
```

This replays independent covariance oracles and synthetic adversaries, including
tiny-N/extreme-depth, repeated correlated measurements, prior-only acquisition,
unit transformations, missing versus unresolved support and the documented
numerical rank limitation. It is mathematical/software evidence, not biological
calibration. Existing outputs are preserved.

## Rebuild the paper

From the matching source release, install the locked paper dependencies:

```sh
uv export --frozen --no-dev --extra paper --no-emit-project --format requirements-txt --output-file paper-requirements.txt
uv pip sync --python .reproduce/bin/python --require-hashes paper-requirements.txt
uv pip install --python .reproduce/bin/python --no-deps candidate-dist/anibench-2.0.0rc6.dev0-py3-none-any.whl
.reproduce/bin/python paper/task_reference/build.py --out output/pdf/AniBench_task_reference.pdf
```

The builder regenerates four charts from checked aggregate figure data, renders
the manuscript, and writes a receipt with source, builder, PDF and figure hashes.
It preserves existing outputs. `paper/task_reference/figures/README.md` explains
exact chart geometry versus timestamp/element-ID differences. Aggregate figure
replay does not rerun the original participant-level preprocessing, fitting or
bootstrap experiments. Their negative results remain disclosed in the paper.

The paper extra is not needed for normal scoring or the two native examples.
The published package contains the manuscript, builder, figures and public
examples. Private inputs and internal authority archives are excluded.
