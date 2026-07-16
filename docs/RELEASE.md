# Open-source release procedure

## Current public source RC

The public source repository is
`https://github.com/anibiome/anibench-benchmark`. Each evaluated public commit,
GitHub verification/CodeQL run, anonymous-clone build, clean install, artifact
scan, and installed-Studio browser roundtrip is bound in its release/readback
receipt. Documentation descendants require their own commit and CI readback. A
protected stable tag, PyPI release, archive DOI,
empirical V8 result, and stable public biological rank remain separate gates.

AniBench has two repositories in the release model:

1. the private authority repository, which retains controlled ANI projections,
   source-body snapshots, council material, and historical artifacts; and
2. a fresh-history public repository created only from the executable allowlist.

Excluding a file from a wheel is not enough. If a private byte ever entered the
public Git object database, deleting it in a later commit would not remove it
from history. The public repository therefore starts from one root commit made
by `scripts/export_public_repository.py`.

## 1. Verify the authority checkout

The final export must be made from a clean, commit-bound checkout:

```bash
python -m pip install -e '.[dev]'
python -m pip install build packaging 'reuse[charset-normalizer]'
make lint
make metadata
make test
make web-test
make protocol-smoke
make verify-corpus-fields
```

Passing software tests proves implementation behavior. It does not assert
independent biological calibration, source-complete comparator geometry, or a
public scalar rank. Those claim gates remain separate.

## 2. Create the fresh-history public repository

Choose a new path outside the authority checkout. The exporter refuses to
replace an existing path and refuses a dirty source checkout.

```bash
SOURCE_DATE_EPOCH=1783900800
make public-export \
  OUTPUT=/absolute/path/to/new/anibench-public \
  SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH"
```

The exporter:

- reads the allowlist and every copied byte from the exact pinned source
  commit's Git objects rather than from mutable worktree paths;
- materializes an external-only source-atlas table;
- excludes private ANI projection objects, raw source snapshots, internal
  receipts, releases, papers builds, patents, and legacy rank surfaces;
- scans text, structured data, PDFs, images, SVG, paths, credentials, participant
  identifiers, raw-data classes, archive containers, and source-projection IDs;
- verifies that HEAD, tree, and clean status are unchanged before and after the
  copy; writes `PUBLIC_EXPORT_RECEIPT.json` with the exact source-authority
  commit/tree, copy mode, copied-object manifest digest, and TOCTOU guard; and
- initializes `main` with exactly one root commit, a clean status, and no remote.

Replay the boundary before adding any remote:

```bash
cd /absolute/path/to/new/anibench-public
test "$(git rev-list --all --count)" = "1"
test "$(git rev-list --max-parents=0 --all | wc -l | tr -d ' ')" = "1"
test -z "$(git status --porcelain=v1)"
test -z "$(git remote)"
PYTHONPATH=src python -c \
  "from pathlib import Path; from scripts.export_public_repository import inspect_public_repository; assert inspect_public_repository(Path('.'))['passed']"
python scripts/verify_external_field_receipts.py --pretty
python scripts/export_public_repository.py --repo . --verify-public-history
```

## 3. Test the exact public tree

All release verification runs again inside the exported tree:

```bash
python -m pip install -e '.[dev]'
python -m pip install build packaging 'reuse[charset-normalizer]'
reuse lint
ruff check src tests scripts
python scripts/verify_release_metadata.py --pretty
python scripts/verify_external_field_receipts.py --pretty
python -m pytest -q
node --test web/v2.test.js
python -m build
python scripts/verify_distribution_boundary.py dist/*.whl dist/*.tar.gz --pretty
python scripts/verify_installed_studio.py \
  --wheel dist/anibench-2.0.0rc1-py3-none-any.whl \
  --receipt dist/INSTALLED_STUDIO_E2E_RECEIPT.json --pretty
```

Smoke-install the wheel in a clean environment and execute both compilers from
outside the checkout:

```bash
python -m venv /tmp/anibench-wheel-smoke
/tmp/anibench-wheel-smoke/bin/python -m pip install dist/*.whl
cd /tmp
/tmp/anibench-wheel-smoke/bin/anibench --help
/tmp/anibench-wheel-smoke/bin/anibench v2-protocol-capacity \
  /absolute/path/to/new/anibench-public/web/protocol-capacity-example.json \
  --out /tmp/protocol-capacity.json --pretty
/tmp/anibench-wheel-smoke/bin/python -c \
  "import json,pathlib; root=pathlib.Path('/absolute/path/to/new/anibench-public/web'); request=json.loads(root.joinpath('optimizer-protocol-example.json').read_text()); request['base_protocol']=json.loads(root.joinpath('protocol-capacity-example.json').read_text()); pathlib.Path('/tmp/optimizer-request.json').write_text(json.dumps(request))"
/tmp/anibench-wheel-smoke/bin/anibench v2-optimize-protocol \
  /tmp/optimizer-request.json \
  --out /tmp/optimizer-result.json --pretty
```

The installed-Studio receipt is the browser-product gate. It binds the exact
wheel hash, proves the imported module came from unpacked wheel bytes, records
the health/comparator/example/capacity/optimizer/retired-route HTTP roundtrips,
and captures hashes of desktop/mobile screenshots plus both downloaded JSON
receipts. A source-checkout page or handler-only test cannot substitute for it.

The distribution verifier requires the exact wheel and source-distribution
member sets derived from the checked-out public authority. It rejects missing
or extra members, duplicate names, traversal paths, links and special files,
encrypted ZIP members, nested containers (including disguised archive magic),
oversized payloads, and any secret/private/raw-data finding discovered by the
public-bundle scanner over safely unpacked bytes.

## 4. Publish without broadening claims

Repository creation, visibility change, tagging, PyPI publication, Zenodo
deposit, DOI registration, and public ranking are distinct actions. A release
manager records exact readback for each action that actually occurs.

The tagged workflow builds, tests, scans, smoke-installs, generates an SPDX
SBOM, writes checksums, and creates GitHub attestations. Its `public-release`
environment blocks package publication unless all of these exact variables are
set for the tagged commit:

| Variable | Required value |
|---|---:|
| `FIRST_PATENT_FILING_BOUND_SHA` | exact tagged `github.sha` |
| `FIRST_PATENT_FILING_RECEIPT_SHA256` | 64-character lowercase SHA-256 |
| `PUBLIC_RELEASE_APPROVED_SHA` | exact tagged `github.sha` |
| `INDEPENDENT_RELEASE_AUDIT_APPROVED_SHA` | exact tagged `github.sha` |
| `INDEPENDENT_RELEASE_AUDIT_RECEIPT_SHA256` | 64-character lowercase SHA-256 |
| `APPROVED_SHA256SUMS_SHA256` | exact SHA-256 of downloaded `dist/SHA256SUMS` |
| `PUBLIC_RANK_CLAIM_ALLOWED` | `false` |

The tag must resolve to `github.sha`, that commit must be contained in
`origin/main`, all reachable refs must have exactly one history root, and every
reachable commit tree must pass the same public-member and byte scanner. The
repository must also be public. `PUBLIC_RANK_CLAIM_ALLOWED=false` is
intentional for v2.0.0-rc.1: open software and a stable cross-trial biological
ranking are different release objects.

## 5. Immutable readback

After publication, record:

- public repository URL and visibility;
- root commit, tag commit, and protected branch;
- Actions workflow run ID and conclusion;
- wheel, source-distribution, SBOM, and checksum digests;
- PyPI project/version readback;
- Zenodo record and DOI only if created;
- patent filing reference only in the private release receipt; and
- every remaining biological-validation or comparator-completeness gate.

Never silently replace a published artifact. A correction is a new version with
an explicit supersession record.
