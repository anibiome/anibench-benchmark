#!/usr/bin/env python3
"""Enforce the AniBench Code Red hold before any release promotion.

The validator is deliberately independent of the scoring implementation.  It
binds the Code Red ledger to the audited Git branch and commit, council-report
bytes, and frozen evidence inventory.  An optional future release receipt is
also inspected for maturity claims that are impossible while the hold remains
active.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


DEFAULT_LEDGER = Path("release/code-red/ANIBENCH_CODE_RED_REVALIDATION_2026-07-12.json")
EXPECTED_LEDGER_CONTRACT = "ani.code_red.acceptance.v1"
EXPECTED_INVENTORY_PATH = "release/review/alpha3/evidence-cell-inventory.csv"
EXPECTED_INVENTORY_COUNT = 2_944
REQUIRED_HASHED_ARTIFACTS = frozenset(
    {
        "reviews/council/HOSTILE_RELEASE_REVIEW_2026-07-12.md",
        "reviews/council/MATH_COUNCIL_2026-07-12.md",
        "reviews/council/SCIENCE_SOURCE_COUNCIL_2026-07-12.md",
        EXPECTED_INVENTORY_PATH,
    }
)

HASH_RECEIPT_PATTERN = re.compile(
    r"(?P<path>(?:reviews|release)/[A-Za-z0-9_.\-/]+)\s+sha256:"
    r"(?P<sha256>[a-f0-9]{64})(?:\s|$)"
)
FULL_GIT_SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")

FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "benchmark_validated",
        "claim_allowed",
        "demonstrated_learning_claim_allowed",
        "empirical_study_validation_claim_allowed",
        "leaderboard_validated",
        "promotion_allowed",
        "public_ranking_allowed",
        "public_ready",
        "publication_ready",
        "published",
        "release_eligible",
    }
)
FORBIDDEN_STRING_VALUES = {
    "claim_class": frozenset(
        {
            "demonstrated_benchmark",
            "public_benchmark",
            "validated_benchmark",
        }
    ),
    "claim_state": frozenset({"public_ready", "released", "validated"}),
    "disposition": frozenset(
        {
            "complete_pushed_verified",
            "public_release",
            "published",
            "released",
        }
    ),
    "publication_state": frozenset({"public", "published", "released"}),
    "maturity": frozenset({"public_ready", "released", "validated"}),
}
CLAIM_CONTAINER_FIELDS = frozenset(
    {
        "allowed_claims",
        "claim",
        "claims",
        "headline_claim",
        "maturity_claims",
    }
)


class CodeRedValidationError(ValueError):
    """Raised when the Code Red inputs cannot be parsed safely."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CodeRedValidationError(f"Could not read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CodeRedValidationError(f"Expected one JSON object in {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown Git failure"
        raise CodeRedValidationError(f"git {' '.join(args)} failed: {message}")
    return result.stdout.strip()


def _git_succeeds(repo_root: Path, *args: str) -> bool:
    return (
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _normalized_repository(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def _check(check_id: str, passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    return {"check_id": check_id, "passed": bool(passed), "detail": dict(detail)}


def _iter_receipts(gates: Mapping[str, Any]) -> Iterable[str]:
    for gate in gates.values():
        if not isinstance(gate, Mapping):
            continue
        receipts = gate.get("receipts", [])
        if isinstance(receipts, list):
            yield from (receipt for receipt in receipts if isinstance(receipt, str))


def _hash_bindings(gates: Mapping[str, Any]) -> tuple[dict[str, str], list[str]]:
    bindings: dict[str, str] = {}
    conflicts: list[str] = []
    for receipt in _iter_receipts(gates):
        for match in HASH_RECEIPT_PATTERN.finditer(receipt):
            path = match.group("path")
            digest = match.group("sha256")
            existing = bindings.get(path)
            if existing is not None and existing != digest:
                conflicts.append(path)
            bindings[path] = digest
    return bindings, sorted(set(conflicts))


def _safe_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise CodeRedValidationError(f"Receipt path escapes repository root: {relative}") from exc
    return candidate


def _inventory_summary(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        raise CodeRedValidationError(f"Could not read evidence inventory {path}: {exc}") from exc
    if not rows:
        return {"row_count": 0, "unique_evidence_cell_ids": 0, "status_counts": {}}
    required = {"evidence_cell_id", "status"}
    if not required.issubset(rows[0]):
        raise CodeRedValidationError(
            f"Evidence inventory is missing columns: {sorted(required - set(rows[0]))}"
        )
    return {
        "row_count": len(rows),
        "unique_evidence_cell_ids": len({row["evidence_cell_id"] for row in rows}),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
    }


def _gate_disposition(gates: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    blocking: list[str] = []
    not_applicable: list[str] = []
    malformed: list[str] = []
    if not gates:
        malformed.append("gates_missing_or_empty")
    for gate_id, gate in gates.items():
        if not isinstance(gate, Mapping) or not isinstance(gate.get("status"), str):
            malformed.append(str(gate_id))
            continue
        status = str(gate["status"])
        if status == "passed" or status.startswith("passed_"):
            continue
        if status == "not_applicable" or status.startswith("not_applicable_"):
            not_applicable.append(str(gate_id))
            continue
        if status in {"failed", "partial", "not_run", "blocked"} or status.startswith(
            ("failed_", "partial_", "not_run_", "blocked_")
        ):
            blocking.append(str(gate_id))
            continue
        malformed.append(str(gate_id))
    return sorted(blocking), sorted(not_applicable), sorted(malformed)


def _iter_json(value: Any, pointer: str = "") -> Iterable[tuple[str, str | None, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{escaped}"
            yield child_pointer, str(key), child
            yield from _iter_json(child, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            yield child_pointer, None, child
            yield from _iter_json(child, child_pointer)


def forbidden_maturity_claims(
    receipt: Mapping[str, Any], withdrawn_claims: Iterable[str]
) -> list[dict[str, str]]:
    """Return release-receipt claims that contradict an active Code Red hold."""

    findings: list[dict[str, str]] = []
    withdrawn = {claim.casefold().strip() for claim in withdrawn_claims if claim.strip()}
    for pointer, key, value in _iter_json(receipt):
        normalized_key = key.casefold() if key is not None else None
        if normalized_key in FORBIDDEN_TRUE_FIELDS and value is True:
            findings.append(
                {"pointer": pointer, "rule_id": "forbidden_true_maturity_field"}
            )
        if normalized_key in FORBIDDEN_STRING_VALUES and isinstance(value, str):
            if value.casefold() in FORBIDDEN_STRING_VALUES[normalized_key]:
                findings.append(
                    {"pointer": pointer, "rule_id": "forbidden_maturity_value"}
                )
        if (
            pointer.endswith("/validation_layers/V8/status")
            or pointer.endswith("/validation_layers/V9/status")
        ) and isinstance(value, str) and value.startswith("passed"):
            findings.append(
                {"pointer": pointer, "rule_id": "forbidden_code_red_validation_pass"}
            )
        if normalized_key in CLAIM_CONTAINER_FIELDS:
            candidates = [value] if isinstance(value, str) else value if isinstance(value, list) else []
            for candidate in candidates:
                if isinstance(candidate, str) and candidate.casefold().strip() in withdrawn:
                    findings.append(
                        {"pointer": pointer, "rule_id": "withdrawn_claim_reasserted"}
                    )
                    break
    return sorted(findings, key=lambda row: (row["pointer"], row["rule_id"]))


def validate_code_red_release(
    *,
    repo_root: str | Path,
    ledger_path: str | Path = DEFAULT_LEDGER,
    release_receipt_path: str | Path | None = None,
    allow_detached_head: bool = False,
) -> dict[str, Any]:
    """Validate the Code Red authority and return its effective promotion decision."""

    root = Path(repo_root).resolve()
    ledger_file = Path(ledger_path)
    if not ledger_file.is_absolute():
        ledger_file = root / ledger_file
    ledger = _load_json(ledger_file)
    checks: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    contract_ok = ledger.get("contract") == EXPECTED_LEDGER_CONTRACT
    checks.append(
        _check(
            "ledger_contract",
            contract_ok,
            {"expected": EXPECTED_LEDGER_CONTRACT, "actual": ledger.get("contract")},
        )
    )
    if not contract_ok:
        validation_errors.append("ledger_contract_invalid")

    gates_value = ledger.get("gates")
    gates = gates_value if isinstance(gates_value, Mapping) else {}
    blocking_gates, not_applicable_gates, malformed_gates = _gate_disposition(gates)
    gate_status_ok = not malformed_gates
    checks.append(
        _check(
            "gate_status_contract",
            gate_status_ok,
            {
                "blocking_gates": blocking_gates,
                "not_applicable_gates": not_applicable_gates,
                "malformed_gates": malformed_gates,
            },
        )
    )
    if not gate_status_ok:
        validation_errors.append("gate_status_contract_invalid")

    audited_head = ledger.get("audited_head")
    expected_branch = ledger.get("branch")
    current_head = _git(root, "rev-parse", "HEAD")
    current_branch = _git(root, "branch", "--show-current")
    audited_head_well_formed = isinstance(audited_head, str) and bool(
        FULL_GIT_SHA_PATTERN.fullmatch(audited_head)
    )
    head_ok = bool(
        audited_head_well_formed
        and _git_succeeds(root, "merge-base", "--is-ancestor", str(audited_head), "HEAD")
    )
    detached_branch_refs: list[str] = []
    if isinstance(expected_branch, str) and not current_branch and allow_detached_head:
        for ref in (
            f"refs/heads/{expected_branch}",
            f"refs/remotes/origin/{expected_branch}",
        ):
            if _git_succeeds(root, "show-ref", "--verify", "--quiet", ref) and _git_succeeds(
                root, "merge-base", "--is-ancestor", "HEAD", ref
            ):
                detached_branch_refs.append(ref)
    branch_ok = isinstance(expected_branch, str) and (
        current_branch == expected_branch or bool(detached_branch_refs)
    )
    checks.append(
        _check(
            "audited_git_identity",
            head_ok and branch_ok,
            {
                "expected_branch": expected_branch,
                "actual_branch": current_branch,
                "allow_detached_head": allow_detached_head,
                "detached_branch_refs_containing_head": detached_branch_refs,
                "expected_head": audited_head,
                "actual_head": current_head,
                "audited_head_is_ancestor": head_ok,
            },
        )
    )
    if not head_ok:
        validation_errors.append("audited_head_mismatch")
    if not branch_ok:
        validation_errors.append("audited_branch_mismatch")

    expected_repository = ledger.get("repository")
    actual_repository = _git(root, "remote", "get-url", "origin")
    repository_ok = isinstance(expected_repository, str) and _normalized_repository(
        actual_repository
    ) == _normalized_repository(expected_repository)
    checks.append(
        _check(
            "repository_remote",
            repository_ok,
            {"expected": expected_repository, "actual": actual_repository},
        )
    )
    if not repository_ok:
        validation_errors.append("repository_remote_mismatch")

    bindings, binding_conflicts = _hash_bindings(gates)
    missing_bindings = sorted(REQUIRED_HASHED_ARTIFACTS - set(bindings))
    artifact_rows: list[dict[str, Any]] = []
    for relative in sorted(REQUIRED_HASHED_ARTIFACTS & set(bindings)):
        path = _safe_repo_path(root, relative)
        actual = _sha256(path) if path.is_file() else None
        artifact_rows.append(
            {
                "path": relative,
                "expected_sha256": bindings[relative],
                "actual_sha256": actual,
                "passed": actual == bindings[relative],
            }
        )
    hashes_ok = (
        not missing_bindings
        and not binding_conflicts
        and all(row["passed"] for row in artifact_rows)
    )
    checks.append(
        _check(
            "bound_artifact_hashes",
            hashes_ok,
            {
                "artifacts": artifact_rows,
                "missing_bindings": missing_bindings,
                "conflicting_bindings": binding_conflicts,
            },
        )
    )
    if not hashes_ok:
        validation_errors.append("bound_artifact_hash_mismatch")

    inventory_path = _safe_repo_path(root, EXPECTED_INVENTORY_PATH)
    inventory = _inventory_summary(inventory_path)
    inventory_ok = (
        inventory["row_count"] == EXPECTED_INVENTORY_COUNT
        and inventory["unique_evidence_cell_ids"] == EXPECTED_INVENTORY_COUNT
    )
    checks.append(
        _check(
            "evidence_inventory_identity",
            inventory_ok,
            {"expected_row_count": EXPECTED_INVENTORY_COUNT, **inventory},
        )
    )
    if not inventory_ok:
        validation_errors.append("evidence_inventory_count_mismatch")

    maturity_findings: list[dict[str, str]] = []
    receipt_label: str | None = None
    if release_receipt_path is not None:
        receipt_file = Path(release_receipt_path)
        if not receipt_file.is_absolute():
            receipt_file = root / receipt_file
        receipt_label = (
            receipt_file.relative_to(root).as_posix()
            if receipt_file.is_relative_to(root)
            else str(receipt_file)
        )
        receipt = _load_json(receipt_file)
        maturity_findings = forbidden_maturity_claims(
            receipt,
            (
                claim
                for claim in ledger.get("withdrawn_claims", [])
                if isinstance(claim, str)
            ),
        )
        checks.append(
            _check(
                "future_release_maturity_claims",
                not maturity_findings,
                {"release_receipt": receipt_label, "findings": maturity_findings},
            )
        )
        if maturity_findings:
            validation_errors.append("forbidden_maturity_claim")

    declared_promotion = ledger.get("promotion_allowed") is True
    audit_identity_ok = not validation_errors
    all_applicable_gates_passed = gate_status_ok and not blocking_gates
    effective_promotion = bool(
        declared_promotion and all_applicable_gates_passed and audit_identity_ok
    )
    promotion_consistent = not declared_promotion or all_applicable_gates_passed
    checks.append(
        _check(
            "promotion_gate_consistency",
            promotion_consistent,
            {
                "declared_promotion_allowed": declared_promotion,
                "all_applicable_gates_passed": all_applicable_gates_passed,
                "effective_promotion_allowed": effective_promotion,
            },
        )
    )
    if not promotion_consistent:
        validation_errors.append("promotion_true_with_unpassed_gate")

    validation_errors = sorted(set(validation_errors))
    validation_passed = not validation_errors
    if not validation_passed:
        effective_promotion = False

    promotion_blockers = sorted(
        {
            *(f"gate_not_passed:{gate}" for gate in blocking_gates),
            *validation_errors,
        }
    )
    return {
        "contract": "ani.code_red.promotion-validation.v1",
        "ledger_artifact_id": ledger.get("artifact_id"),
        "ledger_path": (
            ledger_file.relative_to(root).as_posix()
            if ledger_file.is_relative_to(root)
            else str(ledger_file)
        ),
        "release_receipt_path": receipt_label,
        "validation_passed": validation_passed,
        "promotion_allowed": effective_promotion,
        "declared_promotion_allowed": declared_promotion,
        "all_applicable_gates_passed": all_applicable_gates_passed,
        "blocking_gates": blocking_gates,
        "not_applicable_gates": not_applicable_gates,
        "promotion_blockers": promotion_blockers,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--release-receipt", type=Path)
    parser.add_argument(
        "--require-promotion",
        action="store_true",
        help="Exit nonzero unless the validated ledger currently permits promotion",
    )
    parser.add_argument(
        "--allow-detached-head",
        action="store_true",
        help="Accept a detached tagged HEAD only when it is contained by the audited branch ref",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate_code_red_release(
            repo_root=args.repo_root,
            ledger_path=args.ledger,
            release_receipt_path=args.release_receipt,
            allow_detached_head=args.allow_detached_head,
        )
    except CodeRedValidationError as exc:
        result = {
            "contract": "ani.code_red.promotion-validation.v1",
            "validation_passed": False,
            "promotion_allowed": False,
            "promotion_blockers": [str(exc)],
        }
    result["require_promotion"] = args.require_promotion
    result["require_promotion_satisfied"] = bool(
        result["validation_passed"]
        and (result["promotion_allowed"] or not args.require_promotion)
    )
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["require_promotion_satisfied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
