<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Native architecture comparisons for 240 registry studies

This example runs the current `anibench.architecture_v1` API on source-literal aggregate quantities from 240 distinct ClinicalTrials.gov records. It compares **every pair within each enrollment lifecycle cohort**, not arbitrary identifier batches: 127 registry-reported actual enrollments, 107 estimated enrollments and 6 unknown-status records. This produces 13,687 primary comparisons, including unresolved results. A separate complete calendar-status lane produces 15,433 comparisons.

The frozen corpus was retrieved on **2026-09-19**. This example does not refresh registry records or verify that planned activities occurred. Each study retains its exact retrieval timestamp and source last-update date separately. Selection follows the existing 12-stratum registry stress manifest: first 20 globally unique identifiers per stratum in frozen API response order, without outcome-based replacement. This is a query-selected corpus, not a representative industry sample.

## Run

Install the AniBench checkout or package that includes the architecture API. From this directory:

```sh
python replay.py --out results
```

The output directory must be new. Inputs default to the adjacent `inputs.json`; `--inputs` permits another location. No network access, proprietary data or participant tables are needed. Result receipts bind the input bytes, replay script, source-coordinate records, declared comparison bases, implementation modules and Python runtime. Deterministic full-cohort request packets are saved alongside compact result summaries; complete pairwise results are recomputed rather than storing a large repeated JSON export.

An independent sign-vector oracle checks all 13,687 primary relations without calling the engine's Pareto helper. Additional probes check record-order invariance, duplicate semantic aliases, withheld enrollment and sensitivity to reversing the explicitly declared arm-count preference. These probes are not additional real studies.

## What the coordinates mean

- **Enrollment:** `/protocolSection/designModule/enrollmentInfo/count`, conditioned on its `type`. `ACTUAL` is a registry statement of actual enrollment; `ESTIMATED` is planned. Neither establishes an assay-complete or analyzed population. Missing count/type stays unknown.
- **Arm groups:** length of the nonempty `/protocolSection/armsInterventionsModule/armGroups` list. These are listed protocol-design entries, not verified executed arms, independent causal contrasts or proof of randomization. A missing or empty list stays unknown. The primary comparison explicitly chooses higher listed count; reversing this preference is reported as sensitivity, not an error or a biology claim.
- **Phase:** literal `/protocolSection/designModule/phases` tokens remain categorical metadata. They receive no ordinal score. Missing tokens and `NA` do not mean an early or low-quality phase.
- **Randomization:** `/protocolSection/designModule/designInfo/allocation` is a descriptor-only registry declaration. `RANDOMIZED` and `NON_RANDOMIZED` map to indicator values for display; missing or `NA` stays unknown. This does not certify the implemented assignment mechanism.
- **Calendar span:** study start to primary completion from the two `statusModule` date structures. Only matching known actual/estimated date statuses are combined. Month-only dates are bounded by first and last calendar days; endpoint subtraction propagates those bounds. Mixed status, missing dates or unsupported chronology stays unknown. This is **study-level calendar coverage, never individual participant follow-up or exposure duration**. Calendar comparisons remain separate from the enrollment/arm frontier.

Known quantities carry exact source SHA-256 identities and JSON locators. Population scopes remain separate. No molecular, functional, digital or neural measurement counts are inferred from enrollment, phase or narrative descriptions.

## Provenance and optional frozen-source checks

`inputs.json` contains the original manifest SHA-256, preregistration SHA-256, selection timestamp/rule and, for every study, its ClinicalTrials.gov API URL, raw snapshot SHA-256, retrieval time and exact field locators. The original public manifest is `data/registry_stress_240/manifest.json` in the repository. These are frozen identities, not a promise that today's API response has the same bytes.

If you already hold the exact frozen public snapshots, named `NCTxxxxxxxx.json`, verify all 240 while running:

```sh
python replay.py --snapshot-cache /path/to/frozen-snapshots --out verified-results
```

The script checks raw-byte hashes and NCT identities, then uses `adapter.py` to rederive every numeric/unknown/descriptor coordinate, its semantics and locator, phase/allocation tokens, lifecycle grouping and source last-update date. The supplied aggregates must match exactly before the output directory is created. Changing an enrollment count while retaining the original source hash therefore fails. Current downloaded records may have changed and will fail this check. No automatic fallback substitutes newer data. Without this option, the receipt explicitly records `not_requested`; it does not claim a fresh raw-source verification. Byte identity and rederivation verify correspondence to a snapshot, not source truth or clinical execution. Retrieval timestamps and selection strata remain manifest provenance rather than facts derivable from the study bytes.

The adapter rules reproduced all 240 supplied study rows exactly from the matching source snapshots. `test_adapter.py` includes synthetic regressions for changed counts with unchanged source hashes, modified descriptors, byte changes and partial-month date bounds. Public inputs contain only aggregate counts, date-derived bounds, categorical registry tokens and source provenance; they contain no copied titles, free-text narratives, contacts or participant records.

## Interpretation

The result is a selected-native-quantity comparison. More people and more listed groups can conflict; no sum, weighting or overall biological score resolves that tradeoff. Unknown or incompatible ordered coordinates block definite domination. Definite/possible frontiers refer to the **whole matching lifecycle cohort in this frozen corpus**, not all studies, cross-lifecycle comparisons or biological saturation. Actual and estimated enrollment are not silently interchanged.

Code is Apache-2.0; this explanatory documentation is CC-BY-4.0. Source facts remain attributed to their ClinicalTrials.gov records. No license claim is made over registry facts or third-party source documents.

## Standalone source adapter

To regenerate an aggregate input packet from another directory containing the exact snapshots named by a provenance manifest:

```sh
python adapter.py --manifest manifest.json --snapshot-cache frozen-snapshots --out rederived-inputs.json
python replay.py --inputs rederived-inputs.json --snapshot-cache frozen-snapshots --out rederived-results
python test_adapter.py
```

The manifest must provide a unique `nct_id`, `raw_sha256`, `source_uri` and `retrieved_at` for each study; `stratum_id` is preserved when present. The adapter accepts any nonempty manifest and never overwrites its output. This particular comparison replay intentionally requires 240 distinct study IDs; using a different corpus requires an explicitly reviewed corpus contract, not silently claiming the frozen audit still applies. The adapter needs only the Python standard library; the replay also needs AniBench. Neither command downloads or exports raw snapshots.
