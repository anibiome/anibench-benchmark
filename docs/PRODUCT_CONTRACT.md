# What AniBench must evaluate

AniBench compares how useful a human study's data would be for understanding
and reconstructing human biology. Researchers must be able to evaluate a
completed study or a proposed design, compare its strengths with other studies,
and identify which collection or design changes would improve it.

The biological content matters: what is observed, at what resolution, whether
different observations describe the same people at relevant times, how they
connect to measured function, and what they reveal about change and response.
Population coverage, context, controls and personalization answer additional
questions. File size, assay names, participant counts and expenditure are inputs
or descriptors; none alone measures the intended capability.

Complementary observations can enable questions that neither observation can
answer alone. Repeated copies cannot create that benefit. A method restricted
to covariance cannot establish all nonlinear predictive relationships. Each
supported calculation must state its target and assumptions, and must be tested
against a counterexample outside its useful scope.

## Required distinctions

| Comparison | Behavior the benchmark must explain |
|---|---|
| Similar depth per occasion; different people, duration and controls | Similar individual measurement capability may coexist with very different population, temporal and intervention capability. |
| Completed versus otherwise equivalent planned collection | Planned capacity is conditional on the declared acquisition; lacking treatment results is not an intrinsic capacity penalty. Realized collection requires evidence of what was acquired. |
| Deep profiling of two people versus a broad cohort | Depth may resolve within-person questions without establishing population variation or generalization. Neither design is a universal winner. |
| Linked versus unlinked molecular and functional records | Separate marginal measurements cannot automatically support within-person molecular-to-functional relationships. |
| Measured response versus controlled effect | Exposure-aligned observations may support descriptive dynamics; causal effects require appropriate identification. A null effect does not make a well-designed study uninformative. |
| More measurements versus more useful information | Independent or complementary information may help; duplication, dependence and irrelevant measurements must not earn an automatic bonus. |
| Reference attainment versus continued scientific value | Meeting a finite AniBench version does not exhaust biology. Later versions need explicit harder or broader requirements. |

## What a result and release must provide

Category percentages need a fixed, inspectable denominator and a plain-language
answer to what a higher value means. They must preserve important differences
between studies and distinguish unresolved evidence from known absence. Ethics
and publication filters describe evidence and eligibility; changing those flags
alone does not change intrinsic collection capacity. Study identity must not
influence the calculation.

The deliverable includes reproducible real-study comparisons, adversarial
examples, justified reference levels and design changes, a scientific paper,
readable charts and installable open code that accepts private inputs locally.
Held-out learning experiments assess claims about downstream utility; they do
not replace the study-design benchmark. Cosmetic website polish is secondary
to sound mathematics, runnable code, the paper and understandable results.

## Current implementation boundary

The selective native36 reference, earlier finite task profiles and numerical
witnesses establish specific conditional calculations. They do not yet establish
broad biological relevance, complete real-study rankings, comprehensive private
modality coverage or empirically validated whole-study utility. Passing software
tests or publishing a package does not close these scientific requirements.

Preserve supported APIs and historical results while improving the primary
benchmark through explicit versioned changes. Question selection, category
structure, weights, precision limits, reference models and instrument mappings
are scientific choices to justify. They must not become unquestioned constraints
merely because they already appear in code.
