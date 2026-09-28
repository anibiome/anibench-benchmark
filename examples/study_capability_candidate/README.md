# Hypothetical study input

This example declares 200 independent people, four same-session readings of
grip strength, gait speed and systolic blood pressure at baseline and day 90.
These are illustrative acquisition assumptions, not observations from a real
study. Other quantities remain unknown. No randomization, modifier contrast or
external-site replication is claimed.

`minimal.json` binds this description as its source. It contains no participant
identifiers or clinical values. Group and acquisition identifiers describe
synthetic repeated patterns, not people.

```sh
anibench study-capability examples/study_capability_candidate/minimal.json --validate-only
anibench study-capability examples/study_capability_candidate/minimal.json --out example-result
```

See [the measurement workload guide](../../docs/STUDY_CAPABILITY.md) for score
meaning, assumptions, version identities and local comparison charts. Output
directories must be new. A successful example run does not establish biological
calibration or constitute a real-study benchmark result.
