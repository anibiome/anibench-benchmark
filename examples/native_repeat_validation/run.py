"""Frozen native-repeat falsification; only aggregate outputs leave private staging."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from anibench.information_v2 import (
    EventContribution,
    event_information,
    functional_likelihood_precision,
)

BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit(train):
    """The only function allowed to fit offsets, covariance or regression."""
    delta2 = float(np.mean(train[:, 1] - train[:, 0]))
    delta3 = float(np.mean(train[:, 2] - train[:, 0]))
    sigma2 = float(np.var(train[:, 1] - train[:, 0], ddof=1) / 2)
    if not math.isfinite(sigma2) or sigma2 <= 0:
        raise ValueError("Positive identifiable reading-error contrast required")
    X = np.column_stack([np.ones(len(train)), train[:, :2]])
    beta, _, rank, singular = np.linalg.lstsq(X, train[:, 2], rcond=None)
    return {
        "delta2": delta2,
        "delta3": delta3,
        "sigma2": sigma2,
        "train_third_mean": float(np.mean(train[:, 2])),
        "linear_coefficients": beta.tolist() if rank == 3 else None,
        "linear_rank": int(rank),
        "linear_singular_values": singular.tolist(),
    }


def predict(model, first_two):
    x1, x2 = first_two.T
    result = {
        "one_reading": x1 + model["delta3"],
        "two_readings": (x1 + x2 - model["delta2"]) / 2 + model["delta3"],
        "last_reading": x2 - model["delta2"] + model["delta3"],
        "population_mean": np.full(len(x1), model["train_third_mean"]),
    }
    if model["linear_coefficients"] is not None:
        result["linear"] = np.column_stack([np.ones(len(x1)), first_two]) @ model["linear_coefficients"]
    return result


def canonical_variance(sigma2, physical_ids):
    """Reading identities are deduplicated before constructing the noise geometry."""
    n = len(set(physical_ids))
    H = np.ones((n, 1))
    R = np.eye(n) * sigma2
    J = event_information(EventContribution(
        "same-session-reading-errors", tuple(map(tuple, H)), tuple(map(tuple, R)),
        1.0, "train-only-repeat-contrast",
    ))
    answer = functional_likelihood_precision(J, [[1.0]], [1.0])
    if answer["identified"] is not True:
        raise ValueError("Canonical scalar measurement precision unresolved")
    v = answer["variance"]
    if not math.isclose(v, sigma2 / n, rel_tol=1e-10):
        raise AssertionError("Canonical variance disagrees with scalar oracle")
    return float(v)


def main(out):
    if out.exists():
        raise FileExistsError("Create-only output path required")
    pin = json.loads((BASE / "FREEZE.json").read_text())
    if sha(BASE / "PROTOCOL.json") != pin["protocol_sha256"]:
        raise ValueError("Protocol changed after freeze")
    if sha(__file__) != pin["run_sha256"]:
        raise ValueError("Run code changed after freeze")
    protocol = json.loads((BASE / "PROTOCOL.json").read_text())
    source = BASE / "source"
    manifest = json.loads((source / "SOURCE_MANIFEST.json").read_text())
    source_pin = json.loads((source / "PRE_READ_RECEIPT.json").read_text())
    if sha(source / "SOURCE_MANIFEST.json") != source_pin["source_manifest_sha256"]:
        raise ValueError("Source manifest changed after download/pre-read freeze")
    expected_files = {f"{name}.{extension}" for name in ["BPX_I", "DEMO_I"] for extension in ["xpt", "htm"]}
    records = manifest["sources"]
    if len(records) != len(expected_files) or {r["file"] for r in records} != expected_files:
        raise ValueError("Exact unique official source set required")
    for record in manifest["sources"]:
        if record["url"] != protocol["source_base"] + record["file"]:
            raise ValueError("Source URL is outside frozen official source set")
        p = source / record["file"]
        if p.stat().st_size != record["bytes"] or sha(p) != record["sha256"]:
            raise ValueError("Source bytes changed")
    bpx = pd.read_sas(source / "BPX_I.xpt", format="xport")
    demo = pd.read_sas(source / "DEMO_I.xpt", format="xport")
    if not bpx.SEQN.is_unique or not demo.SEQN.is_unique:
        raise ValueError("Nonunique component key")
    columns = [c for t in protocol["targets"] for c in t["columns"]]
    d = demo[protocol["allowed_demo_fields"]].merge(
        bpx[["SEQN", *columns]], on="SEQN", how="inner", validate="one_to_one"
    )
    joined = len(d)
    eligible = (
        (d.RIDAGEYR >= 20) & (d.WTMEC2YR > 0)
        & np.isfinite(d[["WTMEC2YR", "SDMVSTRA", "SDMVPSU"]]).all(axis=1)
    )
    valid = np.isfinite(d[columns]).all(axis=1)
    valid &= (d[["BPXSY1", "BPXSY2", "BPXSY3"]] > 0).all(axis=1)
    valid &= (d[["BPXDI1", "BPXDI2", "BPXDI3"]] >= 0).all(axis=1)
    eligible_n = int(eligible.sum())
    d = d.loc[eligible & valid].copy()
    for field in ["SDMVSTRA", "SDMVPSU"]:
        if not np.equal(d[field], np.floor(d[field])).all():
            raise ValueError("Nonintegral masked group key")
    groups = list(zip(d.SDMVSTRA.astype(int), d.SDMVPSU.astype(int)))
    unique = sorted(set(groups), key=lambda g: hashlib.sha256(
        f"anibench-native-repeats-2015-20260928|{g[0]}|{g[1]}".encode()
    ).hexdigest())
    cut = len(unique) // 2
    sets = [set(unique[:cut]), set(unique[cut:])]
    masks = [np.array([g in s for g in groups]) for s in sets]
    train, test = masks
    if min(map(len, sets)) < protocol["split"]["minimum_groups_per_partition"]:
        raise ValueError("Insufficient independent groups for frozen split")
    if min(int(m.sum()) for m in masks) < protocol["split"]["minimum_people_per_partition"]:
        raise ValueError("Insufficient people for frozen split")
    if sets[0] & sets[1] or set(d.SEQN[train]) & set(d.SEQN[test]):
        raise AssertionError("Participant/group leakage")
    split_record = {
        "schema": "anibench.native-repeat-private-split.v1",
        "protocol_sha256": pin["protocol_sha256"],
        "source_manifest_sha256": sha(source / "SOURCE_MANIFEST.json"),
        "phase": "Before fit or numerical result inspection",
        "groups": [sorted(s) for s in sets],
        "private_participant_keys": [sorted(d.SEQN[m].astype(int).tolist()) for m in masks],
        "eligible_before_completion": eligible_n,
        "common_complete_people": len(d),
    }
    with out.with_suffix(".split.json").open("x") as f:
        json.dump(split_record, f, indent=2)
        f.write("\n")
    group_codes = np.array([unique.index(g) for g in groups])[test]
    labels = np.unique(group_codes)
    rng = np.random.default_rng(protocol["uncertainty"]["seed"])
    draws = rng.choice(labels, (1000, len(labels)), replace=True)
    boot_indices = [np.concatenate([np.flatnonzero(group_codes == g) for g in draw]) for draw in draws]
    weights = d.WTMEC2YR.to_numpy()[test]
    weights = weights / weights.sum()

    def interval(values):
        return np.quantile([np.mean(values[ix]) for ix in boot_indices], [.025, .975]).tolist()

    results, controls = [], []
    for target in protocol["targets"]:
        values = d[target["columns"]].to_numpy()
        train_values = values[train].copy()
        model = fit(train_values)
        inputs = values[test, :2].copy()
        predictions = predict(model, inputs)
        # Predictions have no test-label parameter. Mutation is still exercised explicitly.
        changed = values.copy()
        changed[test, 2] = changed[test, 2] * 17 + 1000
        assert fit(changed[train]) == model
        changed_predictions = predict(model, changed[test, :2])
        assert all(np.array_equal(v, changed_predictions[k]) for k, v in predictions.items())
        one_v = canonical_variance(model["sigma2"], ["reading1"])
        two_v = canonical_variance(model["sigma2"], ["reading1", "reading2"])
        assert one_v == canonical_variance(model["sigma2"], ["reading1", "reading1"])
        expected = {"one_reading": one_v + model["sigma2"], "two_readings": two_v + model["sigma2"], "last_reading": one_v + model["sigma2"]}
        errors = {k: p - values[test, 2] for k, p in predictions.items()}
        metrics = {}
        for name, e in errors.items():
            row = {"RMSE": float(np.sqrt(np.mean(e**2))), "MAE": float(np.mean(np.abs(e))), "bias": float(np.mean(e)), "MSE_cluster_interval": interval(e**2), "weighted_RMSE_sensitivity": float(np.sqrt(weights @ e**2))}
            if name in expected:
                v = expected[name]
                ratio = interval(e**2 / v)
                covered = (np.abs(e) <= 1.959963984540054 * np.sqrt(v)).astype(float)
                coverage_interval = interval(covered)
                row.update({"predicted_error_variance": v, "MSE_over_predicted_variance": float(np.mean(e**2) / v), "MSE_ratio_cluster_interval": ratio, "Gaussian95_coverage": float(np.mean(covered)), "coverage_cluster_interval": coverage_interval, "calibration_falsified": not ratio[0] <= 1 <= ratio[1] or not coverage_interval[0] <= .95 <= coverage_interval[1]})
            metrics[name] = row
        differences = {}
        for baseline in ["one_reading", "last_reading", "population_mean", "linear"]:
            if baseline not in errors:
                differences[baseline] = {"status": "unresolved_baseline_rank"}
                continue
            difference = errors["two_readings"]**2 - errors[baseline]**2
            ci = interval(difference)
            differences[baseline] = {"paired_MSE_change": float(np.mean(difference)), "paired_cluster_interval": ci, "weighted_change_sensitivity": float(weights @ difference), "disposition": "two_readings_better" if ci[1] < 0 else "two_readings_worse" if ci[0] > 0 else "inconclusive"}
            if baseline in ["one_reading", "last_reading"]:
                denominators = [float(np.mean(errors[baseline][ix]**2)) for ix in boot_indices]
                baseline_mse = float(np.mean(errors[baseline]**2))
                ratio = float(np.mean(errors["two_readings"]**2) / baseline_mse) if baseline_mse > 0 else None
                ratios = [float(np.mean(errors["two_readings"][ix]**2) / denominator) for ix, denominator in zip(boot_indices, denominators) if denominator > 0]
                differences[baseline].update({"predicted_MSE_ratio": .75, "observed_MSE_ratio": ratio, "ratio_undefined_reason": "zero baseline MSE" if ratio is None else None, "ratio_cluster_interval": np.quantile(ratios, [.025, .975]).tolist() if len(ratios) == len(boot_indices) else None, "bootstrap_zero_denominator_draws": len(boot_indices) - len(ratios), "bootstrap_ratio_rule": "All draws required; interval unresolved if any denominator is zero"})
        shuffled = inputs.copy()
        shuffled[:, 1] = np.random.default_rng(20260928).permutation(shuffled[:, 1])
        shuffled_error = predict(model, shuffled)["two_readings"] - values[test, 2]
        controls.append({"target": target["id"], "test_label_mutation_invariant": True, "duplicate_physical_reading_invariant": True, "canonical_scalar_oracle_passed": True, "shuffled_second_linkage_RMSE": float(np.sqrt(np.mean(shuffled_error**2))), "shuffled_linkage_scope": "Deliberately invalid linkage, not extra independent same-person information"})
        results.append({"target": target["id"], "unit": target["unit"], "fitted_train_model": model, "models": metrics, "two_reading_comparisons": differences})
    receipt = {
        "schema": "anibench.native-repeat-results.v1",
        "protocol_sha256": pin["protocol_sha256"], "run_sha256": pin["run_sha256"],
        "source_manifest_sha256": sha(source / "SOURCE_MANIFEST.json"),
        "counts": {"BPX_source": len(bpx), "DEMO_source": len(demo), "joined": joined, "eligible_before_reading_completion": eligible_n, "common_complete_people": len(d), "excluded_incomplete_readings": eligible_n - len(d), "split_groups": list(map(len, sets)), "split_people": [int(m.sum()) for m in masks]},
        "split_sha256": hashlib.sha256(json.dumps([sorted(s) for s in sets]).encode()).hexdigest(),
        "participant_split_sha256": hashlib.sha256(json.dumps([sorted(d.SEQN[m].astype(int).tolist()) for m in masks]).encode()).hexdigest(),
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__},
        "results": results, "controls": controls,
        "scope": protocol["relationship_to_goal"], "limits": protocol["uncertainty"]["limits"],
        "latent_state_validation": False,
    }
    with out.open("x") as f:
        json.dump(receipt, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"targets": len(results), "heldout_people": int(test.sum()), "output": str(out)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        main(args.out)
    except Exception as error:
        failure = args.out.with_suffix(".failure.json")
        if not failure.exists():
            failure.write_text(json.dumps({"schema": "anibench.native-repeat-failure.v1", "error_type": type(error).__name__, "message": str(error), "run_sha256": sha(__file__), "scope": "Stopped; no successful experiment or numerical fallback claimed"}, indent=2) + "\n")
        raise
