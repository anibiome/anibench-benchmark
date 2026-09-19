# Public protocol descriptions

The explorer combines the existing 16 mechanical source projections with
separately identified public protocol cards. These cards expose useful planned
design facts without fabricating a registry record or a complete information
model. Their fields do not enter the existing mechanical projection receipt.

The first card is **Oh My Gut! (Wageningen)**, public identifier
`wur-oh-my-gut`. Its authority is the linked public participant-information
brochure, version 2, June 2025. This is a versioned source, not a claim that the
latest approved investigator protocol has been recovered. The brochure identifier
is not promoted to a verified registry accession. No private protocol is included.

`data/protocol_cards/v1/public.json` distinguishes:

- Numeric tokens, replayable against exact original PDF bytes and a named page.
  Units, denominators and biological meanings are separately curated. Approximate
  quantities retain an approximation marker in the interface.
- Curated prose and figure interpretations, with explicit page/figure locators.
  Successful text extraction does not validate those interpretations.
- Unresolved and conflicting source statements. Neither becomes zero, an absent
  modality, an achieved study count, or a favorable capacity result.

The displayed card retains the written participation span and the different
follow-up anchor in the figure. It does not choose an overall duration from them.
Supplement assignment, an acute challenge, digital observations, functional tasks
and direct neural measurement have distinct roles. Labels do not supply an
observation operator, independent information dimension or causal rank.

## Reproduce the evidence

Run the structural and canonical-hash checks:

```sh
python scripts/verify_protocol_cards.py
```

For full replay, download the exact linked public source independently into a
local directory as `wur-omg-brochure-2025-v2.pdf`, then run:

```sh
python scripts/verify_protocol_cards.py --raw-source-dir /path/to/public-pdfs
```

The replay checks the complete PDF hash, all page-text hashes and every numeric
excerpt. Page extraction uses `pypdf`; the packet records the reviewed version.
Normalization is Unicode NFC, whitespace-run replacement with one ASCII space,
strip, UTF-8 encoding and SHA-256. A different extraction version may fail the
page hashes even when the PDF matches; this is a reproducibility difference to
resolve explicitly. Full text and PDF copies are not shipped in the repository.

Packet hashes detect changes relative to a particular packet; they do not
authenticate a publisher or make altered-and-rehashed claims true. The original
source and interpretation remain reviewable. This feature is after the immutable
RC3 package; install current repository source to use it.
