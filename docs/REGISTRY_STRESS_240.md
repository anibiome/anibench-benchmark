# Frozen 240-study public-registry audit

This reproducible audit tests public ClinicalTrials.gov record ingestion and the
sparse design compiler. It does **not** calculate complete biological capacity,
rank studies, establish clinical validity, or estimate benchmark saturation.
The query-selected corpus is not representative of all human research.

The frozen selection contains 20 globally unique study IDs in each of 12 query
strata. Queries, original retrieval times, source-byte hashes and selection rules
are in `data/registry_stress_240/manifest.json`. The original preregistration is
preserved byte for byte as `preregistration.json`; its hash binds the protocol.
The two neural strata are lexical retrieval groups, not clinically adjudicated
classes. A registry entry can describe a proposed, ongoing, terminated or
completed study; “240 real studies” means 240 actual registry identities, not 240
completed clinical experiments.

## Run from a source checkout

Install AniBench and its development dependencies using the repository's normal
contributor instructions. Then run:

```sh
python scripts/run_registry_stress_240.py \
  --cache-dir /tmp/anibench-registry-cache \
  --out /tmp/anibench-registry-replay.json
```

The command requests only the exact 240 frozen IDs. Each response must match
its original SHA-256 before it can enter the cache or evaluation. Source records
may change after publication: a live API response with different bytes is
reported as `source_hash_mismatch`, never silently substituted, normalized to
hide drift, or counted as passing. The API is not a permanent archive of these
bytes. If the frozen response is no longer obtainable, an exact historical cache
is necessary; report the shortfall rather than claiming reproduction.

For a retained local cache containing `<NCT_ID>.json` raw response files:

```sh
python scripts/run_registry_stress_240.py \
  --cache-dir /tmp/anibench-registry-cache \
  --out /tmp/anibench-registry-offline.json \
  --offline
```

The offline command makes no network calls. It checks every file against the
manifest and verifies the extractor, intake, compiler and schema hashes before
execution. A changed implementation is rejected with
`implementation_hash_mismatch`; this protects historical reproducibility. A new
implementation audit needs a separately reviewed manifest and evidence rather
than overwriting the frozen baseline. The original baseline source hashes are
retained in `baseline.json` and the preregistration; this runner executes the
corrected implementation only.

Output must be a new file. Exit status 0 means all 240 records pass the declared
structural probes; 1 means incomplete/failed record checks; 2 means setup failed.
Failures use safe reason codes rather than source bodies or local paths. Empty
caches in offline mode produce 240 explicit missing-record failures. Raw caches
must be outside this repository: registry responses can contain publicly listed
contact details and are deliberately **not** part of this release. Downloading a
new response does not alter the registry or any clinical study.

## Frozen results and correction provenance

| Implementation | Selected | Base passes | Processing failures | Listed outcome counts |
|---|---:|---:|---:|---|
| Original frozen baseline | 240 | 239 | 1 | All 239 unknown because the old extractor used the wrong JSON pointer |
| Corrected frozen replay | 240 | 240 | 0 | 234 exact counts; 6 unknown |

The original failure was `NCT00489970`: its registry title exceeded the compiler's
240-character display-name limit. The correction bounds the display name while
preserving the full source title in local provenance. The second correction
counts the actual `primaryOutcomes`, `secondaryOutcomes` and `otherOutcomes`
arrays. A listed outcome count is not a count of independent biological
information. Missing/malformed arrays remain unknown.

`baseline.json` preserves the original result, source hashes and failure ID.
`postfix.json` contains a compact allowlisted result for every selected ID and
its aggregate. `portable-verification.json` records an offline execution of this
portable runner against the exact frozen cache, including correspondence with
every allowlisted corrected result field. No raw registry titles, contacts,
source bodies, private paths or participant data are included.

Three derived-input probes run per record:

1. Remove enrollment information: population remains unknown with no imputation.
2. Duplicate intervention-list entries: the entire derived sparse payload stays
   unchanged; a menu cannot fabricate observation operators or capacity.
3. Reverse arm, intervention and outcome rows: sparse payload and listed outcome
   count stay unchanged.

All 720 corrected probes passed. Some mutations are no-ops when the original
structure is empty, absent or not reorderable; the portable receipt separately
reports nontrivial input counts. Compiler probes reject unsupported composite
coordinates, ordinal positions, biological-information inference and imputation;
they require promotion to remain blocked and unresolved gates to remain visible.

These checks establish only these declared invariants. Missing biological
geometry, time structure, covariance and observation operators remain unresolved.
They do not constitute full metric-vector evaluation of 240 study designs,
source-truth verification, comprehensive deduplication testing, or clinical
validation. The separately reported 225 synthetic information-matrix cases are
not part of this corpus and must not be added to its real-study denominator.

## Integrity and tests

```sh
python -m pytest -q tests/test_registry_stress_240.py
```

Tests cover manifest schema, 240 unique identities, 12×20 strata, source-hash and
aggregate correspondence, source drift, offline isolation, no overwrite,
allowlisted output and executed compiler probes on synthetic fixtures. The test
fixtures are not additional real studies. `SHA256SUMS` binds the public data
artifacts. Full reproduction requires the exact raw cache; ordinary unit tests
do not pretend that the private cache is distributed with the package.
