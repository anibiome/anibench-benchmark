# AniBench v2.0.0-rc.1 release checklist

This checklist distinguishes open-source software readiness from biological
validation and public ranking authority.

## A. Freeze source and claims

- [ ] Run `python scripts/fetch_v2_external_sources.py --verify-only` against
  every frozen source snapshot and confirm all 32 exact byte/hash checks pass.
- [ ] Confirm the packaged `EXTERNAL_SOURCE_VERIFICATION_RECEIPT.json` is bound
  to the exact acquisition-ledger hash and contains no redistributed body bytes.
- [ ] Run `python scripts/verify_external_field_receipts.py --raw-source-bytes
  --pretty` in the authority checkout; confirm every displayed known projection
  field is machine-resolved by an executable derivation, no manual known facts
  remain, and every nonmechanical candidate is typed unknown.
- [ ] Run `python scripts/verify_external_field_receipts.py --pretty` in the
  fresh public clone; confirm the sealed field bindings and external coordinate
  derivation replay without upstream source bodies.

- [ ] Exact authority commit selected; source worktree clean.
- [ ] Export receipt says `source_copy_mode=exact_git_objects_from_pinned_commit`,
  `source_commit_bound=true`, and records the copied-object manifest SHA-256.
- [ ] Pre/post HEAD, tree, and clean-status identity passed; no mutable
  working-tree byte was used as release authority.
- [ ] `pyproject.toml`, `uv.lock`, `CITATION.cff`, `.zenodo.json`,
  `codemeta.json`, `CHANGELOG.md`, and proposed tag identify v2.0.0-rc.1.
- [ ] Six family outputs remain non-interchangeable; no hidden scalar or rank.
- [ ] Planned-design capacity has no lifecycle maturity penalty.
- [ ] Unknown, absent, interval, conditional, and exact values remain distinct.
- [ ] Role-aware Level-1 v3 preserves 64 coordinates in seven disjoint roles;
  only 22 are direct mutable outcomes and `D/P/H/T` remain relational estimands.
- [ ] Every displayed native metric carries the protocol-capacity result hash and
  exact JSON locator; six target-attainment fields remain typed unknown until
  family-specific operating-characteristic gates close.
- [ ] The public package contains no recursive v2 perfect-protocol template,
  global enrollment claim, target percentage, or observed-to-target ratio.
- [ ] Public rank permission remains false unless a separately receipted release
  decision changes that claim.

## B. Clear public bytes and rights

- [ ] First patent filing or written release-safe patent decision recorded for
  the exact disclosed scope.
- [ ] `reuse lint` passes in the public export.
- [ ] Every upstream source remains under its own license; AniBench metadata
  does not relicense third-party text or data.
- [ ] Fresh public export contains no private ANI projection objects, absolute
  local paths, controlled source bodies, participant/sample IDs, raw media,
  raw omics, raw clinical data, secrets, private links, nested archives, patent
  drafts, or historical release bundles.
- [ ] External atlas rows resolve only to the 16 allowed public study IDs.

## C. Prove clean history

- [ ] Export created in a new path with `make public-export OUTPUT=...`.
- [ ] Exactly one commit and exactly one root commit.
- [ ] Export branch is `main`, worktree clean, and no remote exists before review.
- [ ] `PUBLIC_EXPORT_RECEIPT.json` reports private history/source bodies/ANI
  projections absent and public rank disabled.
- [ ] The same receipt binds the exact source-authority commit and tree, reports
  `source_authority_git.clean=true`, and reports `release_source_eligible=true`.
- [ ] Independent reviewer replays `inspect_public_repository` on the exact tree.
- [ ] `python scripts/export_public_repository.py --repo .
  --verify-public-history` passes across every commit reachable from every ref.

## D. Verify code, Studio, and distributions

```bash
python -m pip install -e '.[dev]'
python -m pip install build packaging 'reuse[charset-normalizer]'
ruff check src tests scripts
python scripts/verify_release_metadata.py --tag v2.0.0-rc.1 --pretty
python scripts/verify_external_field_receipts.py --pretty
reuse lint
python -m pytest -q
node --test web/v2.test.js
python -m build
python scripts/verify_distribution_boundary.py dist/*.whl dist/*.tar.gz --pretty
python scripts/verify_installed_studio.py \
  --wheel dist/anibench-2.0.0rc1-py3-none-any.whl \
  --receipt dist/INSTALLED_STUDIO_E2E_RECEIPT.json --pretty
```

- [ ] Clean wheel install succeeds outside the checkout.
- [ ] Installed `anibench --help` succeeds.
- [ ] Installed protocol-capacity compiler executes the packaged example.
- [ ] Installed protocol-native optimizer executes the packaged example.
- [ ] Exact unpacked-wheel Studio passes health, static-asset, source-atlas,
  example, capacity, optimizer, retired-route, download, and desktop/mobile
  browser checks with zero page exceptions.
- [ ] Exactly one wheel and one source distribution exist.
- [ ] Distribution reports enforce the exact member set and safely scan all
  unpacked bytes; hostile extra, duplicate, link, encrypted, and nested-container
  fixtures fail.
- [ ] SHA-256 checksums, SPDX SBOM, build provenance, and SBOM attestations bind
  the exact artifacts.

## E. Independent release gate

- [ ] Hostile source, mathematics, anti-gaming, security, privacy, package, and
  usability findings are closed or recorded as explicit blockers.
- [ ] Independent reviewer verifies no ANI study determined formulas, Level-1
  targets, or release thresholds.
- [ ] Comparator source-completeness is stated exactly; missing matrices are not
  invented and unknown is not converted to zero.
- [ ] Manuscript and patent packets have their own exact review disposition.
- [ ] Release manager approves the exact commit and artifact hashes.

## F. Publish and read back

- [ ] Create or select the dedicated public repository; add only its reviewed
  remote to the one-root export.
- [ ] Push `main`; verify remote root commit and file tree.
- [ ] Configure protected branch, tags, security reporting, and required review.
- [ ] Configure `public-release` with human approval and the required
  SHA/digest-bound approval variables documented in `docs/RELEASE.md`.
- [ ] Patent filing, public release, and independent audit approvals bind the
  exact tagged `github.sha`, not a mutable boolean.
- [ ] Patent-filing and independent-audit receipt SHA-256 values are exact,
  lowercase, 64-character digests.
- [ ] `APPROVED_SHA256SUMS_SHA256` equals the downloaded checksum-manifest digest.
- [ ] Tagged commit is an ancestor of `origin/main`; reachable refs have one root.
- [ ] Push the exact version tag only after the gates pass.
- [ ] Verify Actions run ID, conclusion, artifact hashes, SBOM, and attestations.
- [ ] Verify PyPI readback only if publishing was approved and executed.
- [ ] Verify Zenodo/DOI readback only if deposit was approved and executed.
- [ ] Record remaining biological validation, comparator, and public-rank gates.
