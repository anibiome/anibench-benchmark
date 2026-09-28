# Local AniBench workbench

The workbench combines source-qualified task comparisons, a conditional AB1/AB2
design explorer, local run instructions, methods, and the working manuscript.
It is a research candidate. Compare opens a ten-task, five-domain native-mean
pilot for MIPACT and DIRECT PLUS; its two tasks per domain are not a complete
biological-domain assessment. Individual source-precision comparisons are also
available.

After installing this candidate checkout or wheel:

```sh
anibench workbench --port 8795 --ttl 1800
```

Open the printed `http://127.0.0.1:8795/` address. The server binds only to
loopback, stops automatically after 30 minutes, and does not log or save input
bodies. The last successfully evaluated reference design remains in that browser
tab's session storage for reloads. Export a result for a durable copy. No raw
participant files are accepted by this planner interface.

In **Run AniBench**, download `design.json`, edit the declared design, then run:

```sh
anibench plan design.json --out new-result.json
```

The output is create-only. Reimporting a result runs its declared designs again
using the installed Python evaluator. Imported scores are not trusted.

**Design a study** compares five domain task budgets using a byte-pinned,
hypothetical reference model. Depth means a stipulated measurement-variance
reduction, not the number of assays. Every result includes exact tasks, native
units, windows, variance assumptions, and separate exact level decisions. It
does not establish a universal participant count or clinical sufficiency.

**Compare** uses a source-bound catalogue with independently checked native
calculations. Its cross-study view compares each source population's estimator
precision under an explicit measurement-equivalence assumption. It does not
estimate a treatment difference between populations. Publication and ethics
filters only select records. Comparison URLs preserve public selection state;
design inputs are never placed in those URLs.

The pilot retains six coherent variance/rounding scenarios, half/double target
sensitivity and unresolved tasks. Its ranges are sensitivity and missing-evidence
bounds, not confidence intervals. The browser checks exact reviewed chart and
evidence bytes, plus each task's result identity, before rendering. Source
drawers include the population, timing, measurement operator, conditional sample
counts and primary/supplementary evidence. The thresholds were selected after
source inspection and frozen before scoring; this is exploratory calibration.

Collected records use the existing `profile-tables` workflow described in
[COLLECTION_PROFILE.md](COLLECTION_PROFILE.md). A collection inventory requires
additional justified observation and sampling models before precision scoring.

## Reproduction and limitations

The reference experiment and native task catalogue live in
`anibench/workbench_assets/` inside the installed package. The reference adapter
verifies its scientific source hashes before every evaluation. The browser
renders canonical outputs without implementing a second scoring equation.

```sh
PYTHONPATH=src python -m pytest tests/test_reference_workbench.py
node --test tests/test_workbench_display.mjs
```

The full benchmark programme, multi-domain real-study comparison, private ELITE
coverage, final manuscript and public release acceptance remain open. This
candidate makes specific supported workflows reproducible; its existence does
not establish completion of that programme.
