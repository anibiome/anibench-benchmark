# Intake and adjudication

AniBench intake captures source material for evidence review without turning source prose into
score-bearing facts. The implemented adapters cover ClinicalTrials.gov API v2 study and search
responses plus ClinicalTrials.gov protocol PDFs. Every successful snapshot is content-addressed,
locator-preserving, and explicitly held for human review.

## The intake boundary

An intake receipt always carries:

- `raw_content_sha256`, computed from the exact downloaded bytes;
- `raw_content_bytes` and a content-addressed `intake_id`;
- the fixed source URI, request parameters, and retrieval timestamp;
- RFC 6901 JSON pointers for registry fields or one-based page locators for PDF text;
- a non-empty `unresolved_fields` review queue;
- `score_eligible=false`;
- `requires_human_review=true`; and
- `promotion_state=intake_only_unreviewed`.

These values are contract constants, not caller-selected declarations. Changing the source bytes
changes both the SHA-256 digest and the `intake_id`. The CLI JSON receipt records the digest and
byte count rather than serializing the raw byte buffer. Registry JSON and bounded PDF page text are
included for review with their original locators.

The intake module does not import the scorer, create evidence cells, make rating decisions, or
write score-input packets. Intake completion therefore proves source capture and locator integrity;
it does not prove that a protocol statement is true, realized, accessible, independently rated, or
eligible for a benchmark score.

## Controlled source chain

1. **Discover candidates.** `search-ctgov` captures one exact API v2 result page, including the
   query, page size, optional page token, raw-response hash, and JSON pointers. Search results are
   routing evidence only.
2. **Lock the registry response.** `intake-ctgov` validates the canonical `^NCT[0-9]{8}$` form and
   captures the corresponding `/api/v2/studies/{NCT_ID}` response.
3. **Lock the protocol document.** `intake-protocol` downloads a protocol PDF from an allowed
   ClinicalTrials.gov host, hashes its exact bytes, and extracts bounded page text with pypdf while
   preserving one-based page locators.
4. **Reconcile sources.** A human reviewer confirms study identity and protocol version, then
   compares registry fields, protocol language, amendments, statistical-analysis material, assay
   manifests, publications, and realized-data documentation. An NCT identifier links candidates;
   it does not establish that two artifacts describe the same protocol version or evidence state.
5. **Resolve evidence fields.** The reviewer classifies planned versus realized events, exact assay
   platform and resolution, denominators, arms, timepoints, and person/timepoint/specimen linkage.
   Missing, ambiguous, conditional, optional, and contradictory statements remain unresolved or
   disputed rather than being converted to zero or a positive placeholder.
6. **Adjudicate separately.** Only a later evidence workflow may create source spans, evidence
   cells, rating decisions, and adjudication records. Public score-bearing cells require the
   independent-rating and release gates defined in the evidence and source policies.

This separation is the guard against treating registry prose, search-result snippets, or protocol
promises as measured biology.

## Network and parser controls

ClinicalTrials.gov API v2 requests use the fixed HTTPS origin
`https://clinicaltrials.gov/api/v2`; callers cannot override the API root. Protocol retrieval is
limited to HTTPS on `clinicaltrials.gov` or `cdn.clinicaltrials.gov`. User information, non-HTTPS
schemes, unexpected ports, URL fragments, and redirects to other hosts fail closed.

The current CLI uses these fixed limits:

| Input | Limit |
|---|---:|
| Registry/search JSON | 5 MiB |
| Protocol PDF | 25 MiB |
| Protocol pages | 300 |
| Extracted text per page | 100,000 characters |
| Extracted text per PDF | 2,000,000 characters |
| Network timeout | 30 seconds |

JSON responses must be objects and valid JSON; duplicate object keys and non-standard numeric
values such as `NaN` are rejected because they make pointer interpretation ambiguous. PDF input
must have a PDF signature, pass strict pypdf parsing, remain within every byte/page/text cap, and
be unencrypted. Encrypted documents stay outside automated extraction and require a separately
authorized review path.

## CLI commands

Run these from the repository root after installing AniBench in the active environment. The
repository virtual environment exposes the executable as `.venv/bin/anibench`; an installed
environment may use `anibench` directly.

Capture one registry study:

```bash
.venv/bin/anibench intake-ctgov NCT01234567 \
  --out tmp/intake/NCT01234567.registry.json
```

Capture the first page of a discovery query:

```bash
.venv/bin/anibench search-ctgov "healthy aging AND proteomics" \
  --page-size 25 \
  --out tmp/intake/healthy-aging-proteomics.page-1.json
```

Capture a subsequent search page using the exact token returned by the prior API response:

```bash
.venv/bin/anibench search-ctgov "healthy aging AND proteomics" \
  --page-size 25 \
  --page-token "EXACT_NEXT_PAGE_TOKEN" \
  --out tmp/intake/healthy-aging-proteomics.page-2.json
```

Capture and extract a ClinicalTrials.gov protocol PDF:

```bash
.venv/bin/anibench intake-protocol \
  "https://cdn.clinicaltrials.gov/large-docs/path/to/protocol.pdf" \
  --nct-id NCT01234567 \
  --out tmp/intake/NCT01234567.protocol.json
```

The commands print a compact write receipt containing the output path, `intake_id`, and
`score_eligible=false`. The output directory is created when needed. Search pagination is explicit:
one command captures one immutable result page, and the next page requires the exact returned page
token.

## Human review and adjudication record

The default unresolved queue requires review of:

- study identity;
- protocol version;
- planned versus realized measurement-event classification;
- assay platform and measurement resolution;
- participant, timepoint, and specimen linkage;
- mapping into any score field; and
- independent rating and adjudication.

Reviewers should retain the intake ID, digest, source URI, retrieval time, and exact JSON pointer or
page locator in every downstream proposal. A correction should supersede the earlier proposal while
retaining its provenance. Disagreement remains `disputed` until adjudicated. Source disappearance
does not erase the receipt; it changes current availability and triggers source review.

No reviewer should copy a value into a scoring packet directly from an intake receipt. Promotion
must pass through the typed source-span, evidence-cell, rating-decision, and release-gate contracts.

## Source rights and redistribution

ClinicalTrials.gov availability does not transfer ownership of an upstream protocol, publication,
supplement, or dataset to AniBench. Each review must record the upstream license or terms when
known, the access class, and any redistribution constraint. A citation or content hash is not a
relicense.

Use captured text inside the controlled review surface and retain only the minimum source excerpt
needed for a downstream evidence span. Do not place complete protocol text, publication text,
controlled data, or rights-unclear attachments into a public AniBench bundle. Public artifacts may
publish AniBench-authored metadata and analysis under their declared license while preserving a
source URL, digest, retrieval timestamp, and locator for upstream material that cannot be
redistributed.

## Future structured adapters

USDM and JATS are planned intake adapters, not implemented score paths.

- **CDISC USDM:** ingest a versioned structured protocol artifact while preserving the original
  bytes, USDM version, study/version identifiers, object identifiers, JSON pointers, and adapter
  version. USDM structure can reduce transcription ambiguity, but every extracted field will remain
  `score_eligible=false` until human review and evidence adjudication are complete.
- **JATS XML:** ingest source-qualified article XML while preserving original bytes, DOI/PMCID or
  other article identity, JATS version, element-level XML locators, and adapter version. Tables,
  supplements, corrections, and retractions will remain distinct source objects with independent
  rights and evidence review.

Both adapters must follow the same invariant chain:

```text
raw source bytes
  -> immutable source hash and identity
  -> lossless source locators
  -> bounded structural extraction
  -> unresolved human-review queue
  -> independent rating and adjudication
  -> separately gated score-input evidence
```

Structured source formats make evidence easier to locate. They do not bypass source rights,
planned-versus-realized classification, linkage verification, independent review, or release
eligibility gates.
