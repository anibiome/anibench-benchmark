# Data governance

AniBench publishes source-bound benchmark metadata and software while keeping
controlled values and participant-level material inside their authorized
boundaries. Evidence locators may describe where a fact was assessed; they do
not authorize copying the source value into a release.

## Data classes

| Class | Examples | Public package rule |
|---|---|---|
| Public source | Open protocol, registry record, openly licensed aggregate table | Include only with provenance, retrieval date, content hash, and compatible terms |
| Public derived | AniBench-authored score input, aggregate table, figure, receipt | Include with formula/version provenance and CC BY 4.0 attribution |
| Controlled source | Licensed publication text, controlled dataset, private protocol | Locator and release-safe derived fact only; never copy the controlled source payload |
| Evaluator-private | V8 targets, blinded holdouts, private task labels | Exclude from public artifacts and prediction submissions |
| Participant or sample level | Identifiers, bridge maps, omics, clinical records, images, audio, video | Never include in this repository or its release artifacts |
| Secret or operational | Credentials, tokens, private bucket paths, access URLs | Never commit, log, attest, or package |

## Collection and minimization

1. Collect only fields required by a declared benchmark construct or audit.
2. Store stable source identity, exact locator, retrieval date, hash, access
   class, evidence state, and value state separately from the source payload.
3. Prefer aggregate QA counts and hashes in receipts. Do not place participant,
   sample, bridge, row, or raw-path values in proof surfaces.
4. Record missingness and exclusion explicitly; do not fill absent source facts
   from reputation, title keywords, or a neighboring study.
5. A public URL does not imply an open license. Record access and reuse rights
   independently.

## Processing boundaries

- Controlled and participant-level data are processed only in their approved
  environment. Public release assembly receives allowlisted derived artifacts,
  never the raw workspace.
- Blinded predictions and evaluator-private targets remain separated. A public
  prediction package cannot contain target values or reversible row identity.
- Every transformation that can affect a score records its code version, input
  hashes, output hashes, denominators, and evidence state.
- External sources retain their original licenses. The CC BY 4.0 declaration
  applies only to AniBench-authored benchmark material.

## Release controls

Before every public release or update:

- scan tracked files, generated artifacts, nested archives, document metadata,
  images, SVG content, PDFs, and Git history for forbidden classes;
- verify release allowlists and reject symlinks or path traversal;
- inspect all fields whose names end in `_exported` as factual booleans;
- require `private_values_exported=false`, empty leak-file lists, and explicit
  outward-identifier policy in privacy receipts;
- require license provenance for every third-party input;
- require the applicable patent/disclosure decision before expanding the public
  scope, creating a protected release tag, or publishing to a package index or
  archive deposit.

## Retention and correction

Release receipts, source hashes, decisions, and supersession records are
retained with the version they govern. Raw or controlled working material
follows the source system's retention and access policy and is not copied into
AniBench for convenience.

If a released artifact contains restricted data or an incorrect rights claim:

1. stop further publication and downloads where the platform permits;
2. preserve hashes, run IDs, access logs, and the exact affected artifact;
3. rotate exposed credentials and notify the responsible data/security owner;
4. publish a correction or withdrawal record without repeating the restricted
   content;
5. repair the scanner, allowlist, test, or governance rule that allowed the
   incident.

This document defines repository controls. It does not assert that any specific
external legal, ethics, or institutional review regime has approved a dataset.
