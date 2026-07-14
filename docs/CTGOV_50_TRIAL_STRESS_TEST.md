# ClinicalTrials.gov 50-trial stress test

This audit exercises AniBench against 50 distinct live human interventional
records selected as five trials from each of ten heterogeneous search strata:
aging multi-omics, precision oncology, vaccines, exercise, nutrition and the
microbiome, digital/wearable interventions, gene therapy, cell therapy,
micro-randomized trials, and SMART/adaptive trials.

The test answers a narrow but essential release question: can the public intake
and normal-human design front door accept varied registry shapes without
inventing the biological geometry required for the six benchmark families?

For every trial it:

1. hashes the exact ClinicalTrials.gov API v2 study response;
2. verifies that the requested and returned NCT identifiers match;
3. binds every retained descriptive field to a JSON pointer and source hash;
4. preserves actual versus estimated enrollment as exact versus conditional;
5. passes a sparse registered-study object through the design compiler; and
6. asserts that no score, overall scalar, rank, measurement matrix, operator
   geometry, duration, control policy, or missing-value substitution is emitted.

Run the live audit from a source checkout:

```bash
PYTHONPATH=src python scripts/run_ctgov_50_stress_test.py --pretty
```

The frozen release-candidate result is
`docs/audits/CTGOV_50_TRIAL_STRESS_TEST_2026-07-14.json`. Its source hashes bind
the result to the exact registry bytes and ClinicalTrials.gov data timestamp
observed by the run. Because the registry changes, a later replay is expected to
produce a new source-bound receipt rather than the same trial set or digest.

This stress test does not claim that a registry record contains enough
information to score a biological trial. Exact measurement operators,
participant-event linkage, covariance, schedules, policy contrasts,
moderators, transport axes, and evidence-lane receipts still come from the
protocol compiler and source adjudication workflow. That separation is the
anti-hallucination property the audit is designed to verify.
