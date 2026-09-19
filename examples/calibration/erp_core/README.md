<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# ERP CORE conditional precision calibration

This example independently recomputes aggregate, within-session precision estimates from five existing ERP CORE derived files. It does not select a biological resolution threshold or define normative AniBench 1 attainment. No source workbooks, participant rows, or raw EEG are included.

Optional analysis dependencies are Python, NumPy, SciPy, h5py and openpyxl. Install them in an analysis environment of your choice. Acquire the five files separately from the exact public URLs in `source_manifest.json`, preserving their license notices. The script performs no network requests. It verifies all pinned byte sizes and SHA-256 hashes before opening any source.

Run from the repository root:

```sh
python -m pip install numpy scipy h5py openpyxl
python examples/calibration/erp_core/analyze_erp.py --source-dir /path/to/local/source --out aggregate.json
python -m pytest tests/test_erp_calibration_recipe.py
```

Choose a new output path outside the source directory. Existing outputs are rejected, source files are read only, and stdout contains no participant data. The aggregate JSON binds source, manifest and script hashes and records dependency versions. With identical versions and inputs, the fixed-seed calculation is deterministic. Numerical-library versions can affect resampling or floating-point results; no cross-version bitwise guarantee is claimed.

The example uses P3b rare-minus-frequent fixed-window mean voltage at Pz, 300–600 ms, baseline −200–0 ms. `REPORT.md` explains mappings, estimates and limitations. Source settings were optimized on the source cohort; this is an independent computational audit, not independent biological validation.

The [design sensitivity example](DESIGN_SENSITIVITY.md) uses these aggregate
estimates to examine 27 hypothetical combinations of people, trial depth and
visits. Its chart preserves the unknown split between persistent-person and
visit variability. Those ranges are conditional identification bounds, not
confidence intervals. The example requires matplotlib for plotting.

## License boundary

Original `analyze_erp.py` and the synthetic tests are licensed Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0 . Copyright 2026 AniBench contributors.

The source-derived Markdown reports, JSON manifests/results, and PNG figure in this directory are licensed CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/ . Attribute ERP CORE by Emily S. Kappenman and Steven J. Luck; Kappenman et al. (2021); Guanghui Zhang and Steven J. Luck (2023); and the analysis modifications by AniBench contributors. No endorsement is implied.

This separation does not resolve a source-license conflict: OSF metadata states CC BY 4.0, while the official project page and bundled License.txt state CC BY-SA 4.0. This package conservatively retains attribution and ShareAlike for its source-derived reports/data. It does not relicense or include original source files, and its software license does not replace source-data obligations.

Primary references:

- Kappenman et al. (2021), [ERP CORE](https://doi.org/10.1016/j.neuroimage.2020.117465); [archival resource](https://doi.org/10.18115/D5JW4R).
- Zhang and Luck (2023), [Variations in ERP data quality across paradigms, participants, and scoring procedures](https://doi.org/10.1111/psyp.14264); [derived SME resource](https://osf.io/p3bqd/).

Tests use synthetic arrays and bytes to check variance mathematics, finite empirical-bootstrap correction, unit scaling, trial-count effects, invalid values, join failures and content tampering. Actual-data controls check exact joins/HDF5 counts and published rounded aggregates. They do not test clinical validity or generalization.
