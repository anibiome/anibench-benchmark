# Repeated measurements: frozen empirical validation

Combining two blood-pressure readings improved prediction of a withheld third
reading in this selected NHANES cohort. The exact equal-error model did not
explain all observed gains. Both findings are retained.

The protocol and code were frozen before downloading or reading the 2015–2016
XPT files. From 5,066 eligible complete-case adults, 2,492 were allocated to
training and 2,574 to evaluation by disjoint sets of 15 masked sampling groups.
Offsets, reading-specific variance and the linear baseline were fitted only on
the training partition. All published numerical results are aggregates.

| Predictor | Systolic RMSE (mmHg) | Diastolic RMSE (mmHg) |
|---|---:|---:|
| Training population average | 17.63 | 12.85 |
| First reading, adjusted for order | 5.59 | 6.58 |
| Second reading, adjusted for order | 4.81 | 5.79 |
| Average of two, adjusted for order | 4.61 | 5.37 |
| Training-only linear regression | 4.45 | 5.27 |

The two-reading average's paired MSE reduction versus the first reading was
9.99 mmHg² for systolic pressure (95% cluster interval 8.88–11.23) and
14.40 mmHg² for diastolic pressure (10.20–19.14). Both averages also improved
over the second reading alone under the frozen interval rule. Weighted
diagnostic sensitivity retained these directions; no national prevalence or
population-mean claim is made.

The exchangeable-error model predicted a two-versus-one error-variance ratio of
0.75, regardless of which single reading was used. The observed ratios were
0.681 and 0.667 versus the first reading, but 0.920 and 0.861 versus the second.
All four paired intervals excluded 0.75. Four of six Gaussian calibration
diagnostics flagged a discrepancy. The diastolic average's overcoverage flag was
close to the decision boundary and is retained without calling it decisive
evidence by itself. A fitted linear model improved systolic prediction over
averaging; the corresponding diastolic difference was inconclusive.

These results support a specific same-session depth ordering, while rejecting
the claim that the exact exchangeable model is generally calibrated. The
measured target is itself a noisy cuff reading. Short-term physiology,
procedure, measurement error and a shared session component are not separately
identified. No persistent biological-state accuracy, broad AniBench validity or
reference-level saturation follows from this experiment.

The earlier 2017–2018 inverse-prediction experiment remains a separate negative
and mixed result. This new direct-repeat question was selected after that
experiment, and is described as such. No model, split, target or threshold was
tuned after the current test results were seen.

The independent reviewer reproduced 74 numerical checks, including cluster
intervals through an independently implemented cluster-sum bootstrap. The
largest numerical difference was 5.69e-14. The original run did not log the
imported numerical helper's identity internally; an immediate independent import
matched the pre-frozen hash, and Git confirmed that helper was unchanged. This
runtime-recording limitation is retained in the review.

Sources: official [BPX_I documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/BPX_I.htm)
and [DEMO_I documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/DEMO_I.htm).
The public package contains the frozen protocol, original run code, source-byte
manifest and aggregate results. Reproduction uses local source files and writes
the participant-key split only into the caller's private output directory.
Never publish the source records or that split file.
