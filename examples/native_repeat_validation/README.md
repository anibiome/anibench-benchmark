# Do extra measurements help?

In this experiment, two blood-pressure readings predicted a withheld third
reading better than one. The simple equal-noise model failed several calibration
checks. Both findings are reported in [REPORT.md](REPORT.md).

This is a test of one measurement-depth prediction. It is not a study leaderboard
or a validation of every AniBench category. The protocol was frozen before this
cycle's records were downloaded; the question was selected after a different,
earlier experiment gave negative and mixed results.

## Reproduce the figure without participant data

From an installed package:

```sh
python -m anibench.examples.native_repeat_validation.plot \
  /path/to/aggregate-results.json --out new-figure-directory
```

The supplied `aggregate-results.json` is available in this directory and in the
installed package. From a repository checkout:

```sh
python examples/native_repeat_validation/plot.py \
  examples/native_repeat_validation/aggregate-results.json --out new-figure-directory
```

## Reproduce the complete experiment privately

Obtain the official NHANES 2015–2016 files listed in
[`source/SOURCE_MANIFEST.json`](source/SOURCE_MANIFEST.json): `BPX_I.xpt`,
`DEMO_I.xpt`, and their two HTML codebooks. Keep them together in a private
directory outside the repository. Source documentation is available for
[blood pressure](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/BPX_I.htm)
and [demographics](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/DEMO_I.htm).
The replay verifies their exact byte hashes; changed source documents require
review, rather than silently accepting different data.

```sh
python -m anibench.examples.native_repeat_validation.replay \
  --source /private/path/nhanes-2015 --out /private/path/new-repeat-run
```

From a checkout, replace the module invocation with
`python examples/native_repeat_validation/replay.py`. Install AniBench first.
The output directory must be new. It contains source records and participant
split keys and must remain private. No network requests or uploads occur.
Statistical analysis uses only the stated public-use fields, with no external
identity linkage. Public results contain aggregates only.

The original `run.py`, `PROTOCOL.json`, and `FREEZE.json` are preserved byte for
byte. The portable wrapper adds a current-runtime helper receipt; it does not
claim that the original run logged that import. The original independent review
reproduced 74 numerical checks with maximum discrepancy below 5.7e-14. NumPy and
linear-algebra versions can cause small floating-point differences. Counts and
the deterministic partition must match exactly.

The replay also checks every published result against `aggregate-results.json`.
Object structure, counts and non-numeric fields must match exactly; floating-point
results use relative and absolute tolerances of `1e-10`. Non-finite values fail.
Only runtime versions and the two private split digests are excluded from this
aggregate comparison. A successful run writes `COMPARISON.json` with the input
and result hashes and `matched: true`.

`PROTOCOL.json` retains its pre-freeze drafting status in order to preserve its
hash. `FREEZE.json` records the later actual freeze. Neither file is a claim of
independent prospective preregistration.
