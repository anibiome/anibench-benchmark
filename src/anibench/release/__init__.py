"""Public scanning primitives plus source-checkout-only legacy release helpers.

The v2 wheel intentionally ships only :mod:`anibench.release.redact`.  Older v1
receipt and adjudication helpers remain in the private authority checkout so old
receipts can still be audited, but they are not a supported or importable public
runtime API.
"""

from pathlib import Path

from .redact import BundleScanReport, ScanFinding, redact_text_for_log, scan_public_bundle

__all__ = [
    "BundleScanReport",
    "ScanFinding",
    "redact_text_for_log",
    "scan_public_bundle",
]


# Compatibility is deliberately conditional on the archival implementation
# files being present.  Hatch excludes those files from both public wheel and
# public sdist, so no installed distribution can accidentally revive this API.
if Path(__file__).with_name("receipt.py").is_file():  # pragma: no cover - absent in wheel
    from .external_validation import (
        EXTERNAL_BOUND_LAYERS,
        ExternalValidationError,
        verify_external_validation_receipt,
        verify_review_subject,
    )
    from .receipt import (
        VALIDATION_LAYER_NAMES,
        ArtifactDigest,
        ValidationLayerResult,
        artifact_set_sha256,
        build_release_receipt,
        canonical_file_bytes,
        canonical_file_sha256,
        collect_artifacts,
        created_at_from_epoch,
        default_validation_layers,
        normalize_validation_layers,
        raw_file_sha256,
        refresh_release_receipt_id,
        release_receipt_content_id,
        write_release_receipt,
    )
    from .validation_run import (
        BOUND_VALIDATION_LAYERS,
        COMMAND_BOUND_LAYERS,
        RUN_BOUND_LAYERS,
        VALIDATION_RESULTS_CONTRACT,
        VALIDATION_RUN_CONTRACT,
        ValidationRunError,
        load_bound_validation_results,
        validation_run_content_id,
    )
    from .verify import (
        VerificationProblem,
        VerificationReport,
        generate_sha256sums,
        parse_sha256sums,
        verify_release,
        verify_sha256sums,
    )

    __all__ += [
        "VALIDATION_LAYER_NAMES",
        "ArtifactDigest",
        "ValidationLayerResult",
        "VerificationProblem",
        "VerificationReport",
        "ValidationRunError",
        "ExternalValidationError",
        "VALIDATION_RESULTS_CONTRACT",
        "VALIDATION_RUN_CONTRACT",
        "RUN_BOUND_LAYERS",
        "COMMAND_BOUND_LAYERS",
        "EXTERNAL_BOUND_LAYERS",
        "BOUND_VALIDATION_LAYERS",
        "artifact_set_sha256",
        "build_release_receipt",
        "canonical_file_bytes",
        "canonical_file_sha256",
        "collect_artifacts",
        "created_at_from_epoch",
        "default_validation_layers",
        "generate_sha256sums",
        "load_bound_validation_results",
        "normalize_validation_layers",
        "parse_sha256sums",
        "raw_file_sha256",
        "refresh_release_receipt_id",
        "release_receipt_content_id",
        "verify_release",
        "verify_sha256sums",
        "verify_external_validation_receipt",
        "verify_review_subject",
        "validation_run_content_id",
        "write_release_receipt",
    ]

del Path
