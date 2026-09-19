<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Conditional ERP measurement precision

Five pinned, first-party ERP CORE derived files support an aggregate check of fixed-window P3b measurement precision. The source comprises 40 selected neurotypical young adults aged 18–30 from the UC Davis community. The measurement is rare-minus-frequent mean voltage at Pz, 300–600 ms, baseline −200–0 ms, using the mean P9/P10 reference. These source settings were optimized on the same recordings. [Kappenman et al.](https://doi.org/10.1016/j.neuroimage.2020.117465), [Zhang and Luck](https://doi.org/10.1111/psyp.14264).

## Aggregate calculations

| Quantity | Estimate | Exploratory 95% interval |
|---|---:|---:|
| Mean analytic within-session contrast measurement variance | 5.859 µV² | 3.471–9.001 µV² |
| RMS analytic contrast SME | 2.421 µV | — |
| RMS supplied bootstrap contrast SME | 2.349 µV | — |
| Observed variance across person contrasts | 15.220 µV² | 8.152–22.341 µV² |
| Measurement-adjusted person-plus-session variance | 9.360 µV² | 2.352–16.566 µV² |

Mean contrast is 7.047 µV. Its observed cohort-mean SE is 0.617 µV. These are descriptive estimates for this cohort and pipeline, not biological resolution limits.

For each person i and condition c, analytic mean variance is `v_ic = s_ic² / m_ic`, using sample trial-score SD and accepted trial count. Contrast variance is the sum of the two condition variances **conditional on zero cross-condition error covariance**. Trials are assumed independent for this calculation. Scalar summaries cannot test serial dependence, drift or that covariance assumption.

The supplied bootstrap SME is a distinct quantity. A mean formed by resampling m trials from their empirical distribution has exact conditional variance `s²(m−1)/m²`. Applying this finite-m correction predicts contrast RMS 2.327 µV, versus supplied 2.349 µV. Maximum relative parent-wave discrepancy declines from 12.17% to 5.65%. Finite bootstrap randomness may contribute; the summaries cannot establish complete attribution. Discrepancies are retained.

Subtracting mean analytic measurement variance from the observed across-person sample variance gives the reported adjusted estimate. Under an additive model with independent stable-person and session effects, it estimates **B + S**. Neither B nor S is separately identified with one measured session. Without independence, their covariance also enters that combined dispersion. The nonnegative and untruncated estimates are both retained; no truncation occurs for this source.

Intervals use 20,000 paired resamples of people, fixed seed 20260919. They are exploratory percentile intervals conditional on estimated per-person noise summaries. They do not propagate full trial-level variance-estimation uncertainty or establish coverage for the underlying biological variance components. People, not trials, are the resampling units.

## Mapping and controls

| Source | Location |
|---|---|
| Parent mean-amplitude bootstrap SME | `P3_Individual_SME.xlsx`, `Sheet1!B5:C44` |
| Contrast mean-amplitude bootstrap SME | same file, `Sheet1!K5:K44` |
| SME keys | same file, `Sheet1!A5:A44`, `J5:J44` |
| Accepted rare and frequent trial counts | `P3_Individual_Number-trials.xlsx`, `Sheet1!B3:B42`, `G3:G42` |
| Count keys | same file, `Sheet1!A3:A42`, `F3:F42` |
| Trial-score SD | `D_SD_mean_amp_Parent.mat`, MATLAB `D_p(:,1,:)` |
| Mean amplitudes | `D_amp_parent.mat`, MATLAB `D_p(:,1,:,1)` |

All four identifier vectors align exactly and contain 40 unique entries. Source scripts specify P3 first, rare/frequent conditions and mean amplitude in the first scoring slot. Peak/latency columns are excluded. The source header typo `Frequenct` is checked literally. The [SD script](https://osf.io/download/a6j32/) removes rejected epochs before calculating SD; the [amplitude script](https://osf.io/download/fuzdt/) establishes matrix indexing.

Standard SciPy and h5py readers are used. HDF5 `D_trial_number_1` has stored shape `(7,2,40)`; reversing its axes gives MATLAB `(40,2,7)`. Every P3 count matches the workbook. The distributed key adds `_1` to the inspected source script's `D_trial_number`; this naming discrepancy is documented rather than hidden.

Count means and parent amplitudes match the paper's rounded aggregate controls. Recomputed RMS values match the workbook's two-decimal summary cells `B46:C46` and `K46` within 0.005 µV. Input byte hashes are checked before and after analysis. The output contains aggregates, mappings and provenance only.

## Boundaries

There are no measured repeat sessions, external validation cohort, clinical discrimination target or causal cortical intervention in this analysis. Windows selected on the same data are not independently validated by recomputation. No biological cutoff, normative AniBench target or saturation certificate is proposed. A future design calculation must justify its resolution separately and propagate calibration uncertainty.

Source-license ambiguity is retained: OSF metadata states CC BY 4.0, while the official project page and bundled license state CC BY-SA 4.0. This source-derived report and aggregate data are CC BY-SA 4.0; original analysis code is Apache-2.0. Source files are not redistributed. Attribution: ERP CORE by Emily S. Kappenman and Steven J. Luck; Kappenman et al. (2021); Guanghui Zhang and Steven J. Luck (2023); analysis modifications by AniBench contributors. No endorsement implied. See `source_manifest.json` and `README.md` for exact provenance and license boundary.
