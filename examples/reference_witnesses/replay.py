"""Reproduce one frozen, synthetic native36 reference experiment."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
CASES = {
    "standard_candidate-standard": ("standard_candidate", "standard", "pass"),
    "standard_candidate-fine": ("standard_candidate", "fine", "fail"),
    "fine_candidate-fine": ("fine_candidate", "fine", "pass"),
}
PRIVATE_PATH = re.compile(r"(?:/Users/|/home/|gs://|s3://|file://)", re.IGNORECASE)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def encoded(value):
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), allow_nan=False)
    for chunk in encoder.iterencode(value):
        if PRIVATE_PATH.search(chunk):
            raise ValueError("A private-location marker was found; output is not exportable")
        yield chunk.encode()


def write(path, value):
    with path.open("xb") as f:
        for chunk in encoded(value):
            f.write(chunk)
        f.write(b"\n")


def compressed(path, value):
    with path.open("xb") as f, gzip.GzipFile(
        filename="", fileobj=f, mode="wb", mtime=0, compresslevel=9
    ) as z:
        for chunk in encoded(value):
            z.write(chunk)
            if f.tell() > 160 * 1024 * 1024:
                raise RuntimeError("Compressed output cap exceeded; partial file retained")


def verify():
    manifest = json.loads((ROOT / "REPRO_MANIFEST.json").read_text())
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"REPRO_MANIFEST.json"}:
        raise ValueError("Reproduction example has extra or missing files")
    for name, expected in manifest["files"].items():
        p = (ROOT / name).resolve()
        if not p.is_relative_to(ROOT) or sha(p) != expected:
            raise ValueError("Reproduction example identity changed: " + name)
    return manifest


def runtime(target):
    target = target.resolve()
    members = json.loads((ROOT / "RUNTIME_MEMBERS.json").read_text())
    actual = {p.relative_to(target).as_posix() for p in (target / "anibench").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts}
    if actual != set(members):
        raise ValueError("Installed package has extra or missing files")
    for name, expected in members.items():
        p = (target / name).resolve()
        if not p.is_relative_to(target) or sha(p) != expected:
            raise ValueError("Installed package differs from frozen runtime: " + name)
    cache = target / ".anibench-disabled-bytecode-cache"
    if cache.exists():
        raise ValueError("Alternate bytecode-cache sentinel must remain absent")
    sys.pycache_prefix = str(cache)
    if platform.python_version() != "3.12.13":
        raise ValueError("Use the frozen Python 3.12.13 environment")
    versions = json.loads((ROOT / "DEPENDENCY_VERSIONS.json").read_text())
    for name, version in versions.items():
        if importlib.metadata.version(name) != version:
            raise ValueError("Dependency version changed: " + name)
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[key] = "1"
    if "anibench" in sys.modules:
        raise ValueError("AniBench was imported before runtime verification")
    sys.path.insert(0, str(target))
    from anibench.study_capability_candidate import charts, entrypoint, study_profile
    if not Path(study_profile.__file__).resolve().is_relative_to(target):
        raise ValueError("Imported the wrong package")
    expected_profiles = json.loads((ROOT / "REFERENCE_BINDINGS.json").read_text())
    for resolution, expected in expected_profiles.items():
        if study_profile.c.digest(study_profile.profile(resolution, "normative")) != expected:
            raise ValueError("Reference profile changed: " + resolution)
    return study_profile, entrypoint, charts, versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "check-runtime", "run"))
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    manifest = verify()
    from make_input import make_input

    if args.command == "verify":
        print(json.dumps({"files_verified": len(manifest["files"]), "numerical_runs": 0}))
        return 0
    if args.runtime is None:
        parser.error("--runtime is required")
    s, e, charts, versions = runtime(args.runtime)
    if args.command == "check-runtime":
        for case in ("standard_candidate", "fine_candidate"):
            design, _ = e.load_input(make_input(case))
            s.linked.validate_raw(design)
        print(json.dumps({"runtime_and_inputs_verified": True, "numerical_runs": 0}))
        return 0
    if args.case is None or args.out is None:
        parser.error("run requires --case and --out")
    if args.out.resolve().is_relative_to(ROOT):
        raise ValueError("Output must be outside the frozen example")
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    case, resolution, hypothesis = CASES[args.case]
    design, _ = e.load_input(make_input(case))
    result, components, profile = s.evaluate(design, resolution=resolution,
                                             noise_profile="normative")
    verify()
    members = json.loads((ROOT / "RUNTIME_MEMBERS.json").read_text())
    if any(sha(args.runtime / name) != digest for name, digest in members.items()):
        raise ValueError("Runtime changed during calculation")
    write(args.out / "RESULT.json", result)
    write(args.out / "REFERENCE_PROFILE.json", profile)
    compressed(args.out / "INPUT.json.gz", design)
    compressed(args.out / "CANONICAL_COMPONENTS.json.gz", components)
    del components
    saved_result = json.loads((args.out / "RESULT.json").read_text())
    saved_profile = json.loads((args.out / "REFERENCE_PROFILE.json").read_text())
    with gzip.open(args.out / "CANONICAL_COMPONENTS.json.gz", "rt") as f:
        components = json.load(f)
    expected_profiles = json.loads((ROOT / "REFERENCE_BINDINGS.json").read_text())
    checks = {
        "persisted_certificate_matches": s.decide(saved_result, components, saved_profile)
        == saved_result["hybrid_profile_decision"],
        "exact_current_profile": s.c.digest(saved_profile) == expected_profiles[resolution],
        "original_input_bound": saved_result["source_input_sha256"] == s.c.digest(design),
        "components_bound": saved_result["provenance"]["canonical_components_sha256"]
        == s.c.digest(components),
        "chart_admitted": charts.registered_basis(saved_result)["reference_profile_sha256"]
        == s.c.digest(saved_profile),
    }
    receipt = {
        "case": args.case,
        "hypothesized_status": hypothesis,
        "actual_status": saved_result["hybrid_profile_decision"]["status"],
        "hypothesis_supported": saved_result["hybrid_profile_decision"]["status"] == hypothesis,
        "integrity_checks": checks,
        "manifest_sha256": sha(ROOT / "REPRO_MANIFEST.json"),
        "original_preparation_manifest_sha256": manifest["original_preparation_manifest_sha256"],
        "runtime_members_sha256": sha(ROOT / "RUNTIME_MEMBERS.json"),
        "components": len(components),
        "environment": {"python": platform.python_version(), "system": platform.system(),
                        "machine": platform.machine(), "dependencies": versions},
        "files": {p.name: sha(p) for p in args.out.iterdir() if p.is_file()},
        "scope": "Synthetic conditional reference feasibility; not minimum enrollment, "
                 "biological calibration, clinical feasibility or whole-benchmark completion.",
    }
    write(args.out / "RECEIPT.json", receipt)
    print(json.dumps({"case": args.case, "status": receipt["actual_status"],
                      "hypothesis_supported": receipt["hypothesis_supported"],
                      "integrity_passed": all(checks.values())}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
