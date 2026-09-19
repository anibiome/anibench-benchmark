# Benchmark release and comparison standard

AniBench measures human study design and collection capacity. Treatment effects
and demonstrated machine-learning performance are separate evaluations. A
descriptive chart is not an information-capacity score.

## Lessons from established benchmarks

These are design references, not validation or endorsement of AniBench.

- [HealthBench](https://openai.com/index/healthbench/) specifies the tasks,
  conversation-specific criteria and evaluation procedure. The transferable
  principle is to define success before comparing systems. Biological study
  capacity requires explicit estimands, observation models and tolerances;
  importing a response-quality rubric would not supply those definitions.
- [Harvey LAB](https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark)
  packages tasks, environments, deliverables and review criteria for independent
  use. AniBench submissions likewise need a frozen definition, inputs, executable
  evaluation and inspectable result. A runnable harness alone does not establish
  that its criteria capture the intended scientific construct.
- [ARC Prize](https://arcprize.org/leaderboard) distinguishes benchmark versions
  and evaluation settings, and exposes resource/performance tradeoffs. AniBench
  must bind comparisons to the same task and version, and expose depth, people,
  time and resource constraints without equating expenditure with information.
- [LiveBench](https://livebench.ai/) presents overall and category results with
  visible benchmark context. AniBench needs equally legible category figures.
  A universal aggregate is not justified merely because another benchmark has
  one; its utility function and units would need a separate scientific argument.
- [SWE-bench](https://www.swebench.com/) separates benchmark subsets, exposes
  comparison charts and marks independently checked runs. AniBench likewise
  distinguishes a declared result from a replayed result, with the exact
  evaluator and comparison set visible. An approval badge cannot replace the
  input and execution evidence.
- [MLPerf Training](https://mlcommons.org/benchmarks/training/) fixes each task's
  dataset and quality target before measuring time to reach it. The transferable
  distinction is between an openly chosen benchmark target and the empirical
  evidence used to measure progress. AniBench may choose a resolution convention;
  it must label that choice and separately justify measurement/noise models.
  A convention is not a discovered threshold for biological sufficiency.
- [HELM](https://crfm.stanford.edu/2022/11/17/helm.html) makes coverage and
  multiple evaluation dimensions explicit. AniBench should expose which
  biological questions its current tasks cover and omit, alongside category
  results, rather than turn missing questions into a favorable average.

References inspected 2026-09-19. These observations do not assert that all
benchmarks share one scoring system or submission policy.

## A comparable numerical result

Source-literal quantities can be compared before an information model exists.
`compare-architecture` freezes the selected quantity meanings, units,
denominators, aggregation, collection status and preference directions. Each
record retains its own population scope. Comparing reported protein inventory
sizes does not require exchangeable populations, equal assay noise or complete
participant tables; it also cannot establish equal assay quality, information
per person or transportability. Missing and incompatible ordered quantities
remain unresolved, and categorical descriptions carry no implicit preference.

Every information comparison needs the same target population, estimand, horizon,
parameterization, observation/noise assumptions, evaluation version and evidence
lane. A study may lead one declared task and trail another. Unobserved directions
remain unresolved; duplicating dependent measurements must not create independent
information. Greater per-person precision cannot manufacture additional people.

For a finite scalar task, the implemented conditional Gaussian reference uses
prior precision `P_prior`, information `I`, posterior covariance
`(P_prior + I)^-1`, and functional variance `a^T (P_prior + I)^-1 a`.
It requires explicit support and identifiability evidence.
The synthetic examples demonstrate this mathematics; they do not calibrate all
human biology. Biological tolerances, valid observation operators and uncertainty
in nuisance parameters need independent scientific justification.

Planned geometry can be evaluated before collection. Collection verification,
data access, ethics approval, publication and downstream model performance are
separate facts. Changing those labels alone must not change the modeled geometry.

## Publication and ethics filters

The default comparison includes every supported record. Optional filters select
the evidence users wish to inspect; they do not silently rescore a design.

- Publication attaches to the source supporting each fact. A peer-reviewed
  article and a preprint from the same study remain distinct.
- Ethics approval attaches to a specific study and protocol scope. Approval,
  documented exemption/waiver, documented absence and unknown are distinct.
  Failure to find approval is not evidence of its absence.
- Published-only and approved-only filters intersect when both are active.
  Excluded unknowns remain counted and explainable.
- An assumed approval in a hypothetical design is not actual approval. Such a
  scenario needs its own identity and visible assumption, without changing the
  source study or increasing the number of real studies.
- Neither publication nor ethics approval alone establishes collection
  completeness, data quality, treatment benefit or biological information.

## Release figures

The chart front door separates reported study properties, executed hypothetical
comparisons and calibrated-noise design illustrations. Counts retain their
denominators; bounds have explicit glyphs; unit conversions are declared. Missing
values are never plotted at zero. Each export retains its evidence label,
interpretation and source/receipt binding.

Required release evidence includes reproducible inputs and outputs, meaningful
adversarial checks, source coverage, uncertainty and sensitivity analyses,
independent review attribution, and browser verification of actual user flows.
AI-assisted reviews are not human peer review. A published package or successful
test run does not complete scientific validation or the requested comparative
study corpus.
