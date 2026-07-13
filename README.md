# AniBench

AniBench is an open benchmark and trial-design instrument for one question:

> If this human study were the biological record available to a future
> superintelligence, how much of human state, change, intervention response,
> individual variation, function, and population transfer could it reconstruct?

Here, *reconstruct* means recover a usable model of latent biological state and
trajectory, estimate intervention-response operators, resolve person-by-context
heterogeneity, and transport those relations to new people and settings. It does
not mean predicting one endpoint from a large but biologically shallow table.

AniBench evaluates the experiment and its resulting data—not the sponsor,
journal, institution, or popularity of the intervention. It works on proposed
protocols as well as registered, realized, accessible, and empirically
demonstrated studies.

## What makes AniBench different

Sample size, visit count, assay count, and raw bytes are not interchangeable.
AniBench keeps the following objects separate:

1. **Intensive biological resolution** — what one linked participant-state
   event resolves. Population scale cannot purchase missing biological depth.
2. **Extensive reconstruction capacity** — the retained information contributed
   by the complete experiment across participants and events.
3. **Longitudinal resolution** — within-person time, density, span, and retained
   trajectory support. Disjoint cross-sections cannot manufacture follow-up.
4. **Causal architecture** — whole-policy and component identifiability derived
   from actual assignment geometry rather than arm counts.
5. **Personalized and sequential learning** — repeated randomized decisions,
   pre-assignment moderators, linked biological feedback, and decision support.
6. **Population transport** — outcome-linked policy contrasts across measured
   context coordinates, not a count of sites or countries.

There is no hidden weighted overall trial score. Public comparisons are
family-specific or Pareto relations.

Population transport is itself a vector over registered transport-axis
families. Each family binds an estimand, an ordered required-axis set, and a
hash-addressed coordinate-scale authority. The compiler projects contexts onto
that required set: undeclared extra axes are ledgered but cannot raise the
result, while a missing required axis makes that context ineligible. A
single-family input receives a convenience scalar alias; a multi-family input
does not receive a winner-selected or averaged transport scalar.

## Why biological depth compounds

AniBench does not award points for adding modality names. For event type (e),
the candidate mathematical model is

\[
\mathcal I_e=n_e A_e^\top R_e^{-1}A_e,
\qquad
\mathcal I_{\mathrm{trial}}=\sum_e\mathcal I_e.
\]

Here (A_e) is a registered observation or design operator, (R_e) is its
nuisance-aware covariance, and (n_e) is valid retained support. After prior
whitening and nuisance adjustment, information is reported as local posterior
hypothesis-volume contraction:

\[
L_{\mathrm{abs}}=\frac{1}{2\ln 10}\log\det(I+G).
\]

Independent biological directions multiply the remaining-volume reduction.
Redundant measurements saturate. A synchronized molecular, functional,
contextual, longitudinal, and perturbational record can therefore be much more
informative than the sum of a checklist, while duplicated panels or unlinked
subsets add little or nothing.

## Evidence lanes

The same protocol geometry receives the same design-capacity result regardless
of whether execution has begun. The lane changes what is being claimed, not the
mathematics of the promised design.

| Lane | Meaning |
|---|---|
| Design Preview | Capacity conditional on executing the declared protocol |
| Registered Protocol | Capacity bound to a frozen protocol source |
| Realized | Information actually acquired after retention, linkage, and QC |
| Accessible | Realized information another evaluator can lawfully compute against |
| Demonstrated | Held-out learning with calibration, nulls, and transfer receipts |

Unknown, absent, conditional, interval, and exact facts remain distinct.
Unknown never becomes zero, and a protocol maximum never becomes realized
coverage.

## Trial Designer and protocol compiler

Run the Studio from an installed wheel:

```bash
python -m pip install /path/to/anibench-2.0.0rc1-py3-none-any.whl
anibench studio
# http://127.0.0.1:8765/
```

Or run it from a source checkout with the complete development/test surface:

```bash
python -m pip install -e '.[dev]'
anibench studio
# http://127.0.0.1:8765/
```

The normal-human workflow produces a typed structural receipt. The advanced
workflow compiles explicit participant-event, measurement, schedule, policy,
moderator, and transport geometry into separate capacity families. The file
paths in the following command are source-checkout examples:

The Studio can also search ClinicalTrials.gov or lock one exact NCT record as a
hash-addressed intake snapshot. Registry intake is discovery and source
preservation only: it remains `score_eligible: false`, requires field-level
human review, and never auto-fills biological operators or trial execution.

```bash
anibench v2-protocol-capacity \
  web/protocol-capacity-example.json \
  --out build/protocol-capacity.json --pretty
```

Transport-family results appear at
`transport.axis_families.<family-id>.transport_rank` and
`transport.axis_families.<family-id>.transport_allocation_support_factor`.
This makes an axis-family addition visible without letting a large coordinate
menu inflate an existing family.

The protocol-native optimizer changes the protocol and recompiles every
candidate. It cannot patch family outputs, submit weights, or create a scalar
leaderboard:

```bash
anibench v2-optimize-protocol \
  path/to/optimizer-request.json \
  --out build/optimizer-result.json --pretty
```

Source atlas from a source checkout:

```bash
anibench build-v2-source-atlas \
  --coordinate-table data/source_projections/v2/SOURCE_COORDINATE_TABLE.csv \
  --out build/source-atlas
```

## Reference levels

AniBench levels are finite engineering targets, not claims that a trial has
captured all human biology. Level 1 freezes a mesoscopic coordinate system and
family-specific target geometry. Later levels add finer spatial, temporal,
molecular, tissue, environmental, and interventional resolution without
rewriting earlier levels.

Level 1 freezes the scientific map and the rules for defining a target; it does
not invent a fictitious perfect protocol. The current role-aware authority keeps
all 64 coordinates but assigns each exactly one estimation role. Twenty-two may
serve as direct mutable outcomes after source-bound observation operators;
`S01` is a baseline modifier, `S09` is exposure/context, and `D/P/H/T` are
relational estimands rather than directly measured outcomes or strata.

Each of the six families has its own operating-characteristic and enrollment
authority. Those targets remain typed unknown until their source gates are
closed. AniBench therefore reports native, source-located design geometry today,
not a fake completion percentage. Unknown is not zero, and no family can
compensate for another through an overall scalar or rank.

## Corpus and charts

The public repository includes a source-bound external comparator corpus. The
private authority repository can build a separate, source-bound ANI portfolio
overlay, but that controlled overlay and its source locators are excluded from
the fresh-history public export. Every displayed field is sealed to a source
object hash, locator, projection pointer, and value digest. A value remains
`state=known` only when every declared source binding is machine-resolved by a
receipted executable derivation. Curated, manual, unresolved, or otherwise
non-executable candidate values are removed and retained as typed unknown with
their source identifiers, locators, and reason. A citation or raw-file hash is
never mislabeled as an executable derivation. A study with adequate public
descriptive facts but missing event geometry remains visible as `not_scoreable`;
it is not assigned zero and it is not given an invented matrix.

Generated figures always ship with machine-readable CSV/JSON and a build
receipt. Row order in an atlas is not a rank.

The 32 frozen upstream response-body snapshots behind the public comparator
facts are not redistributed. Their byte counts and SHA-256 values are frozen in
the acquisition ledger. Anyone can replay every sealed field and regenerate the
external coordinate table from a fresh public clone without those bodies:

```bash
python scripts/verify_external_field_receipts.py --pretty
```

The private authority checkout additionally replays exact source hashes,
machine extractors, and locator-resolution evidence against the frozen bodies:

```bash
python scripts/verify_external_field_receipts.py --raw-source-bytes --pretty
```

That raw replay fails closed if any displayed known fact lacks an all-mechanical
binding. It does not promote manually interpreted candidate values; those stay
typed unknown.

## Current evidence boundary

The executable compiler, optimizer, anti-gaming tests, source atlas, and Studio
are implementation evidence. Public biological rankings additionally require:

- an independently reviewed, hash-pinned reference authority;
- source-resolved protocol geometry for every compared study;
- empirical calibration against held-person, time, modality, intervention, and
  cohort tasks;
- hostile mathematical, source, gaming, and package review; and
- a release decision bound to the exact commit and artifacts.

Until those gates are present, outputs state their evidence class and keep
public-rank permission false. This boundary prevents polished software from
being mistaken for biological validation.

## Open-source structure

```text
src/anibench/       compiler, information, causal, optimizer, API and CLI
schemas/v2/         strict machine-readable input and result contracts
spec/v2/            parameter, reference, authority and mechanics objects
data/               source projections and public comparator facts
web/                interactive Trial Designer and protocol design lab
paper/v2/            methods manuscript and reporting checklist
docs/                scientific, evidence, anti-gaming and governance contracts
tests/               unit, metamorphic, hostile, runtime and package tests
```

Deterministic chart/table candidates and receipts are generated into `release/`
by authorized private builds; generated release directories are not copied into
the fresh-history public source repository.

## Reproducibility

```bash
python -m pytest -q
node --test web/v2.test.js
ruff check .
python scripts/export_public_repository.py --help
python -m build
python scripts/verify_installed_studio.py \
  --wheel dist/anibench-2.0.0rc1-py3-none-any.whl --pretty
```

Every result binds the protocol hash, formula version, source state, scenario
envelope, and replay identity. Release archives are deterministic and scanned
for private paths, controlled source bodies, legacy score surfaces, and nested
archives.

The private authority checkout is not made public in place because its history
retains controlled source and ANI study material. Release engineering creates a
new, one-root public repository from the executable allowlist:

```bash
make public-export OUTPUT=/absolute/path/to/new/anibench-public
```

The exporter refuses an existing output path or dirty source checkout, scans the
exact copied tree, excludes private ANI projections and controlled source bodies,
writes `PUBLIC_EXPORT_RECEIPT.json`, and initializes a clean `main` branch with
one root commit and no remote. See `docs/RELEASE.md` for replay and publication
gates.

## License and citation

Code is licensed under Apache-2.0. Benchmark data and documentation are licensed
under CC BY 4.0 unless an upstream source row states otherwise. See
[`LICENSE`](LICENSE), [`LICENSE-DATA`](LICENSE-DATA), and
[`CITATION.cff`](CITATION.cff).
