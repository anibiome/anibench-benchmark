# Hypothetical biological-question replay

These examples test the local evaluation interface. They contain no participant
records or actual-study scores, and do not define AniBench 1 or 2.

Choose the profile matching the request:

| Requests | Profile |
|---|---|
| `paired256`, `paired2`, `baseline256`, `unlinked256`, `unknown_noise256`, `duplicates256` followed by `_REQUEST.json` | `PROFILE.json` |
| `legacy_REQUEST.json` | `LEGACY_PROFILE.json` |
| `alternatives_complete`, `alternatives_mosaic`, `alternatives_switching`, `alternatives_unknown` followed by `_REQUEST.json` | `ALTERNATIVES_PROFILE.json` |

The legacy example combines two fictional questions and checks compatibility
with the earlier contract. The alternatives examples require one complete native
frame per requirement. In `alternatives_switching_REQUEST.json`, a different
frame passes in each scenario; neither frame passes across both scenarios.

```sh
anibench study-questions examples/study_questions/PROFILE.json \
  examples/study_questions/paired256_REQUEST.json --out new-result.json
```

`EXPECTED_RECEIPTS.json` records the canonical result digests from the reviewed
calculations before package integration. Each result includes its full reference,
question outcomes, original engine receipts and limitations.

`ALTERNATIVES_EXPECTED.json` binds the four fictional v3 examples separately.

See `docs/STUDY_QUESTIONS.md` for percentage meaning, assumptions and API use.
# Collection scope example

`collection_scope_REQUEST.json` wraps the existing `paired256_REQUEST.json`
calculation and retains additional fictional microbial, image, video, voice and
spectral acquisitions. Run it with `PROFILE.json` through `anibench study-questions`.
Those acquisitions remain explicitly outside the selected reference; their
presence creates no automatic points. See `docs/STUDY_COLLECTION_SCOPE.md` for
the source-qualified collection contract and its limits.
