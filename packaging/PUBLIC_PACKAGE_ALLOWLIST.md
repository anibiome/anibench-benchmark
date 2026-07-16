# Public v2 package boundary

The public v2 candidate contains the executable protocol-capacity mechanics,
the hash-pinned candidate authority resolver, the protocol-native Pareto design
optimizer, the score-free source atlas, and the schemas and candidate authority
objects those paths require. The release assembler names every copied file and
derives an external-only atlas coordinate table from hash-bound normalized
projections.

This is a review-candidate boundary, not promotion authority. Release receipts
retain `promotion_allowed=false` until the independent validation gates pass.

The public Git repository is also an explicit artifact. It is created in a new
directory by `scripts/export_public_repository.py`, scanned before Git
initialization, and committed as exactly one root with no remote. This prevents
private authority history from becoming reachable even if every current-tree
file looks safe. `PUBLIC_EXPORT_RECEIPT.json` records the public tree digest and
the negative private-history/source-body/ANI-projection claims, and binds the
exact clean source-authority commit and tree from which the export was created.
Release exports read every allowlisted byte from that pinned commit's Git
objects, verify pre/post Git-state identity, and bind the copied-object
manifest digest; a development dirty-tree export is permanently non-release.

## Wheel runtime assets

- the explicitly enumerated current v2 protocol, authority, information,
  source-atlas, front-door, and redaction/scanning primitives
- the explicit v2 protocol-capacity, protocol-authority, protocol-native
  optimizer, design, information, uncertainty, and current Level 1
  schemas listed in
  `pyproject.toml`
- the role-aware Level-1 v3 assessment module, schema, headless CLI, and Studio
  endpoint; all six design families expose native metrics with exact receipt
  locators while unresolved targets remain typed unknown
- the canonical `anibench eval` command, public `run_trial_eval` API,
  `evals/level1/eval-card.json`, evaluation guide, and CLI/API parity regression
- the strict `anibench compare` / `compare_trial_eval_receipts` same-basis
  comparator and schema; it verifies source eval hashes and emits only
  within-family Pareto relations with no scalar or ordinal rank
- the seven explicit candidate authority objects and their manifest
- the explicit Level-1 v3 coordinate, role, family, and target-gate authority,
  excluding the quarantined v2 reference-target and assessment artifacts
- the external source-acquisition ledger and 16 normalized external projections
- the hash-bound verification receipt proving that all 32 frozen upstream
  response-body snapshots matched the acquisition ledger at release assembly;
  the upstream bodies themselves remain excluded
- the sealed field-provenance receipt and public verifier: every known
  projection field has all-machine-resolved source bindings and replayable
  operators; nonmechanical candidates remain typed unknown with exact source
  locators and reasons, and the external coordinate table regenerates without
  redistributed bodies
- `openapi/anibench-v2-candidate.yaml`
- `examples/optimizer_protocol_v2_example.py`
- `examples/v2/illustrative-design.json`
- the content-addressed synthetic source object behind the shipped protocol and
  optimizer examples (`examples/v2/illustrative-protocol-source.json`)
- `web/v2.html`, `web/v2.js`, `web/v2.css`, `web/favicon.svg`, and the two
  synthetic JSON mechanics examples loaded by the installed Studio

## Source distribution and review-candidate additions

- `AGENTS.md` and `CURRENT.md` as the repository authority and current-state routers
- source-atlas fetch/rebuild inputs and an external-only coordinate table
- target migration/verification and protocol-authority build/resolution scripts
- focused v2 protocol-capacity, protocol-native optimizer, information, and
  mathematical-invariant tests, including hostile Level-1 basis, covariance,
  dependence, typed-unknown, overflow, and anti-gaming regressions
- the canonical eval command regression, including six-task identity,
  deterministic receipt parity, schema validity, name blindness, and permanent
  null overall score/rank
- strict comparison regressions for hash tampering, authority-basis mismatch,
  family-wise Pareto output, and null ordinal rank
- v2 methods and evidence-governance documents named by the assembler
- the candidate benchmark protocol source and reporting checklist
- the four deterministic, study-free methods figures referenced by the
  benchmark protocol
- distribution-boundary, release-metadata, and external-field receipt verifiers
- exact unpacked-wheel Studio HTTP/browser verifier and its dependency-free
  headless-Chrome driver
- fresh-history public-repository exporter, release-metadata verifier, current
  CI workflows, REUSE declarations, and release procedure/checklist

## Excluded classes

- withdrawn or legacy scalar/rank Python modules, including
  `optimizer_v2.py`, `scoring.py`, `ranking_v2.py`, and their dependency trees
- the superseded three-family suite, shadow-capacity simulation, legacy Level 1
  derivation chain, and internal ANI atlas compiler
- withdrawn optimizer schemas, old documentation, and old tests
- legacy scalar/rank UI files, generated leaderboards, and v1 public assets
- `data/studies/ani-*.json` and `data/source_projections/v2/ani-*.json`
- raw upstream response bodies under `data/source_projections/v2/sources/`
- legacy suite inputs under `data/source_projections/v2/suite_inputs/`
- private scoring registries and controlled evidence cells
- generated trial/result figures, tables, paper builds, prior releases, and
  council worktrees; study-free methods figures explicitly named above are
  included
- patent and invention-disclosure material
- legacy `anibench.release` v1 receipt, validation, verification, and external
  adjudication modules and every v1 release schema; only the current public
  redaction/scanning primitive remains importable in a built distribution

The exact unpacked wheel, source distribution, and review candidate remain
subject to recursive path, link, size, license, privacy, image-metadata, and
nested-archive scans before any promotion decision.
