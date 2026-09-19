# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 AniBench contributors
"""Compute aggregate-only conditional ERP precision from five pinned local files.

No network access, source modification, participant-row output or biological threshold.
Optional dependencies: numpy, scipy, h5py, openpyxl.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
EXPECTED_FILES = frozenset(
    {
        "P3_Individual_SME.xlsx",
        "P3_Individual_Number-trials.xlsx",
        "D_SD_mean_amp_Parent.mat",
        "D_amp_parent.mat",
        "D_trials_allERP.mat",
    }
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_sources(source, manifest):
    require(len(manifest["files"]) == 5, "Expected five pinned files")
    names = [item["name"] for item in manifest["files"]]
    require(
        all(
            isinstance(name, str)
            and name
            and Path(name).name == name
            and "/" not in name
            and "\\" not in name
            and name not in (".", "..")
            for name in names
        ),
        "Unsafe source basename",
    )
    require(len(set(names)) == len(names), "Duplicate source filenames")
    require(set(names) == EXPECTED_FILES, "Unexpected source file set")
    for item in manifest["files"]:
        data = (source / item["name"]).read_bytes()
        require(len(data) == item["size_bytes"], "Source size mismatch")
        require(
            hashlib.sha256(data).hexdigest() == item["hashes"]["sha256"],
            "Source hash mismatch",
        )


def validate_identifiers(reference, other):
    require(
        np.array_equal(reference, np.arange(1, 41)),
        "Unexpected source participant order",
    )
    require(np.array_equal(reference, other), "Participant keys do not align")


def conditional_variances(sd, counts):
    require(
        sd.shape == counts.shape and sd.ndim == 2 and sd.shape[1] == 2,
        "Expected two aligned conditions",
    )
    require(
        np.isfinite(sd).all() and (sd > 0).all(), "Invalid trial standard deviations"
    )
    require(
        np.isfinite(counts).all()
        and (counts > 1).all()
        and np.equal(counts, np.floor(counts)).all(),
        "Invalid accepted counts",
    )
    analytic = sd**2 / counts
    empirical = analytic * (counts - 1) / counts
    return analytic, empirical


def values(sheet, region):
    a = np.array([[c.value for c in row] for row in sheet[region]], dtype=float)
    require(np.isfinite(a).all(), "Nonfinite workbook values")
    return a


def main():
    import h5py
    import openpyxl
    import scipy
    from scipy.io import loadmat

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    SOURCE = args.source_dir.resolve()
    require(not args.out.exists(), "Output exists; choose a new output path")
    require(
        SOURCE not in args.out.resolve().parents,
        "Output must be outside source directory",
    )
    manifest = json.loads((BASE / "source_manifest.json").read_text())
    verify_sources(SOURCE, manifest)
    sw = openpyxl.load_workbook(
        SOURCE / "P3_Individual_SME.xlsx", read_only=True, data_only=True
    )
    tw = openpyxl.load_workbook(
        SOURCE / "P3_Individual_Number-trials.xlsx", read_only=True, data_only=True
    )
    s = sw["Sheet1"]
    t = tw["Sheet1"]
    require(
        [s[x].value for x in ["A3", "B4", "C4", "K4"]]
        == ["Mean amplitude", "Rare", "Frequenct", "Mean amplitude"],
        "Pinned source structure or aggregate control mismatch",
    )
    require(
        [t[x].value for x in ["A1", "F1", "B2", "G2"]]
        == ["Rare", "Frequent", "Accepted number", "Accepted"],
        "Pinned source structure or aggregate control mismatch",
    )
    ids = values(s, "A5:A44").ravel()
    require(
        len(set(ids)) == 40 and np.array_equal(ids, np.arange(1, 41)),
        "Pinned source structure or aggregate control mismatch",
    )
    for sheet, region in [(s, "J5:J44"), (t, "A3:A42"), (t, "F3:F42")]:
        validate_identifiers(ids, values(sheet, region).ravel())
    n = values(t, "B3:B42")
    n = np.column_stack([n.ravel(), values(t, "G3:G42").ravel()])
    require(
        (n > 1).all() and np.equal(n, np.floor(n)).all(),
        "Pinned source structure or aggregate control mismatch",
    )
    sme = values(s, "B5:C44")
    diffsme = values(s, "K5:K44").ravel()
    with h5py.File(SOURCE / "D_trials_allERP.mat", "r") as h:
        require(
            list(h.keys()) == ["D_trial_number_1"],
            "Pinned source structure or aggregate control mismatch",
        )
        raw = h["D_trial_number_1"][:]
        require(
            raw.shape == (7, 2, 40) and raw.dtype == np.dtype("float64"),
            "Pinned source structure or aggregate control mismatch",
        )
        require(
            h["D_trial_number_1"].attrs["MATLAB_class"] == b"double",
            "Pinned source structure or aggregate control mismatch",
        )
        # HDF5 stores MATLAB axes in reverse order: original person x condition x component.
        counts = raw.transpose(2, 1, 0)
        require(
            np.array_equal(counts[:, :, 0], n),
            "Pinned source structure or aggregate control mismatch",
        )
    sd = loadmat(SOURCE / "D_SD_mean_amp_Parent.mat")["D_p"]
    amp = loadmat(SOURCE / "D_amp_parent.mat")["D_p"]
    require(
        sd.shape == (40, 7, 2) and amp.shape == (40, 7, 2, 2),
        "Pinned source structure or aggregate control mismatch",
    )
    sd = sd[:, 0, :]
    amp = amp[:, 0, :, 0]
    require(
        np.isfinite(sd).all() and (sd > 0).all() and np.isfinite(amp).all(),
        "Pinned source structure or aggregate control mismatch",
    )
    analytic_var, empirical_boot_var = conditional_variances(sd, n)
    analytic_sme = np.sqrt(analytic_var)
    variance = analytic_var.sum(axis=1)
    contrast = amp[:, 0] - amp[:, 1]
    empirical_boot_sme = np.sqrt(empirical_boot_var)
    observed = contrast.var(ddof=1)
    noise = variance.mean()
    corrected = observed - noise
    rng = np.random.default_rng(20260919)
    idx = rng.integers(0, 40, size=(20000, 40))
    bv = variance[idx].mean(axis=1)
    bo = contrast[idx].var(axis=1, ddof=1)
    bc = bo - bv

    def interval(a):
        return np.quantile(a, [0.025, 0.975]).tolist()

    results = {
        "schema_version": "anibench.erp-aggregate-calibration.v1",
        "scope": "conditional within-session precision; aggregate-only",
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "openpyxl": openpyxl.__version__,
            "h5py": h5py.__version__,
            "scipy": scipy.__version__,
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_hashes": {f["name"]: f["hashes"]["sha256"] for f in manifest["files"]},
        "source_manifest_sha256": hashlib.sha256(
            (BASE / "source_manifest.json").read_bytes()
        ).hexdigest(),
        "license": "CC-BY-SA-4.0",
        "attribution": manifest["attribution"],
        "n_people": 40,
        "measurement_units": "microvolt",
        "variance_units": "microvolt^2",
        "mapping": {
            "component_mat_index_1based": 1,
            "component": "P3",
            "condition_order": ["rare", "frequent"],
            "scoring_dimension_1based": 1,
            "scoring": "mean amplitude",
            "workbook_ranges": {
                "SME_parent": "P3_Individual_SME.xlsx/Sheet1!B5:C44",
                "SME_difference": "P3_Individual_SME.xlsx/Sheet1!K5:K44",
                "SME_ids": "P3_Individual_SME.xlsx/Sheet1!A5:A44 and J5:J44",
                "accepted_rare": "P3_Individual_Number-trials.xlsx/Sheet1!B3:B42",
                "accepted_frequent": "P3_Individual_Number-trials.xlsx/Sheet1!G3:G42",
                "trial_ids": "P3_Individual_Number-trials.xlsx/Sheet1!A3:A42 and F3:F42",
            },
            "all_four_identifier_vectors_equal": True,
            "source_script_person_order_matches_ids": True,
            "HDF5_count_variable": "D_trial_number_1 (source script names D_trial_number; shape and count equality verified)",
            "HDF5_raw_shape": [7, 2, 40],
            "HDF5_transposed_matlab_shape": [40, 2, 7],
            "source_mat_shapes": {
                "D_SD_mean_amp_Parent.mat": [40, 7, 2],
                "D_amp_parent.mat": [40, 7, 2, 2],
            },
        },
        "mean_retained_trials": n.mean(axis=0).tolist(),
        "mean_parent_amplitude_uV": amp.mean(axis=0).tolist(),
        "mean_contrast_uV": float(contrast.mean()),
        "analytic_parent_SME_RMS_uV": np.sqrt(analytic_var.mean(axis=0)).tolist(),
        "reported_bootstrap_parent_SME_RMS_uV": np.sqrt((sme**2).mean(axis=0)).tolist(),
        "analytic_vs_bootstrap_parent_relative_difference_max": float(
            np.max(abs(analytic_sme - sme) / analytic_sme)
        ),
        "analytic_vs_bootstrap_parent_relative_difference_median": float(
            np.median(abs(analytic_sme - sme) / analytic_sme)
        ),
        "analytic_contrast_variance_mean_uV2": float(noise),
        "analytic_contrast_SME_RMS_uV": float(np.sqrt(noise)),
        "exact_empirical_resampling_parent_SME_RMS_uV": np.sqrt(
            empirical_boot_var.mean(axis=0)
        ).tolist(),
        "exact_empirical_resampling_contrast_SME_RMS_uV": float(
            np.sqrt(empirical_boot_var.sum(axis=1).mean())
        ),
        "empirical_bootstrap_vs_reported_parent_relative_difference_max": float(
            np.max(abs(empirical_boot_sme - sme) / empirical_boot_sme)
        ),
        "reported_bootstrap_contrast_variance_mean_uV2": float(np.mean(diffsme**2)),
        "reported_bootstrap_contrast_SME_RMS_uV": float(np.sqrt(np.mean(diffsme**2))),
        "observed_person_contrast_variance_uV2": float(observed),
        "measurement_adjusted_person_plus_session_variance_untruncated_uV2": float(
            corrected
        ),
        "measurement_adjusted_person_plus_session_variance_nonnegative_uV2": float(
            max(0, corrected)
        ),
        "cohort_mean_observed_SE_uV": float(np.sqrt(observed / 40)),
        "bootstrap": {
            "method": "paired nonparametric resampling of people, percentile 95% intervals; plug-in source noise summaries, not nested trial resampling",
            "seed": 20260919,
            "replicates": 20000,
            "analytic_contrast_variance_mean_uV2": interval(bv),
            "observed_person_contrast_variance_uV2": interval(bo),
            "adjusted_person_plus_session_variance_untruncated_uV2": interval(bc),
        },
        "checks": {
            "byte_hashes_verified": True,
            "ids_unique_and_aligned": True,
            "no_missing_selected_values": True,
            "positive_integer_trial_counts": True,
            "source_workbooks_unchanged": True,
            "HDF5_P3_counts_equal_workbook_exactly": True,
        },
        "blockers": [
            "Analytic versus supplied bootstrap SME discrepancies are retained; finite empirical-resampling correction is diagnostic, not proof that every discrepancy is Monte Carlo noise.",
            "No actual repeat sessions: stable person and visit variance unidentified.",
            "Scalar summaries cannot diagnose serial or cross-condition error dependence.",
            "Conditional independence of retained trials and zero cross-condition error covariance are assumptions.",
            "Source windows optimized on same cohort: no independent window-selection validation.",
            "Bootstrap intervals condition on estimated participant noise summaries; they do not propagate full within-person trial-variance estimation uncertainty.",
            "CC BY versus CC BY-SA source license discrepancy retained.",
        ],
        "biological_cutoff": None,
        "certified_saturation": False,
    }
    # Paper Table 2 offers independent rounded aggregate controls, never row matching by values.
    require(
        np.allclose(n.mean(axis=0), [30.53, 139.90], atol=0.0051),
        "Pinned source structure or aggregate control mismatch",
    )
    require(
        np.allclose(amp.mean(axis=0), [11.39, 4.34], atol=0.0051),
        "Pinned source structure or aggregate control mismatch",
    )
    results["checks"]["published_rounded_count_and_amplitude_means_reconcile"] = True
    # Source aggregate RMS cells are stored rounded to two decimals; compare within half rounding unit.
    require(
        np.allclose(
            np.sqrt((sme**2).mean(axis=0)),
            values(s, "B46:C46").ravel(),
            atol=0.005,
            rtol=0,
        ),
        "Pinned source structure or aggregate control mismatch",
    )
    require(
        np.isclose(np.sqrt(np.mean(diffsme**2)), s["K46"].value, atol=0.005, rtol=0),
        "Pinned source structure or aggregate control mismatch",
    )
    results["checks"]["workbook_RMS_summary_reconciles"] = True
    sw.close()
    tw.close()
    verify_sources(SOURCE, manifest)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
