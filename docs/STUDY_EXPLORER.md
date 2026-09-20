# Study explorer

The [public static explorer](https://anibench.ani-ai-is-alive.chatgpt.site)
provides the source atlas, reported-fact comparisons, and synthetic evaluator
demonstration without installation. Use the local Studio for custom inputs.

The public entry page is `web/compare.html` (the static build's `index.html`).
It shows one comparison at a time: **People**, **Measurements**, or **Time**.
Its five-study source packet is `web/source-architecture.json`. Publication and
ethics filters are independent; publication filtering applies to each supporting
source, and unknown approval is distinct from explicitly not approved. Click a
study or measurement to read its definition and source. Locally, this page is at
`http://127.0.0.1:8765/compare.html`.

Population bars display reported counts on a log10 axis, with the population
role and approximate or lower-bound markers retained. Each study uses an explicit
population field; an excluded field never silently switches to another
denominator. Protein inventories use a linear axis. Neither is a benchmark score.
Missing counts have no bar, and a view with no reported counts has no numerical
axis. Coverage distinguishes documented measurements, public study descriptions
and unreported fields. Time windows retain their original labels and units,
without ranking follow-up, treatment and sensor windows against one another.

The research views at `benchmark.html` retain the design examples, 240-record
registry comparison, method and local run instructions. The advanced workspace
below retains its original source atlas and evaluation workflows.

Run `anibench studio` and open `http://127.0.0.1:8765/explore.html`.
The existing Trial Designer remains at `/` and `/v2.html`.

The explorer provides a searchable 16-study source atlas, selectable source plots,
selection of up to four studies for a source comparison, canonical protocol
evaluation, and comparison of 2–20 canonical assessment receipts. All six
families are shown in native units. Download buttons preserve the exact inputs,
assessments, and comparison packet.

Source plots show every available denominator separately, including publication
enrollment, completers, assay subsets, and the frozen registry record. Study
cards foreground the first reported publication population; the original record
is retained in the comparison and the plot. This is a declared presentation
choice, not an adjudication that one denominator supersedes another. Duration
plots retain mean, median, intervention, and scheduled-endpoint meanings. They
use 365.25 days per year and one twelfth of that per month solely for the display
axis; original units remain attached. Protein, metabolite, transcript, and cell
counts each have a separate plot. Counts are never added across assays or
interpreted as independent biological dimensions or people.

Original JSON text is retained for upload and download, including numeric
serialization. The full workspace archive stores `receipt_documents`,
`protocol_documents`, and `comparison_document` as strings so JavaScript cannot
silently change a hash-bound `1.0` into `1` or round a large integer. Parsed
values are used only for display.

The browser contains rendering and input-handling code only. Evaluation calls
`run_trial_eval`; comparison calls `compare_trial_eval_receipts`. It does not
implement a second scoring formula. Custom evals and comparisons execute in the
loopback Python service. A static export disables custom file inputs and explains
how to run that service locally.

## Three distinct kinds of evidence

1. The frozen source atlas retains its original facts, provenance receipts,
   unresolved fields, and absence of comparison-complete geometry.
2. Thirty-seven literal source facts supplement thirteen study records from
   sixteen complete primary-source snapshots. Their full
   source-body hashes, exact JSON pointers, short matching excerpts, numeric
   tokens, units, denominator meanings, and precision are preserved in
   `data/reported_facts/v1/literature.json`. A numerical extraction is not
   independent methodological review or a capacity score.
3. The comparison demonstration uses two synthetic designs in a two-direction
   parameter space. One adds an independent observation direction; the other
   stretches the observation and assignment time geometry together. The
   demonstration is not an assessment of a named human study.

The public cohort projections are still **not capacity-comparison complete**.
The explorer does not imply that the separate 50-record registry-intake stress
test is a 50-study scientific evaluation.

## Source reconciliation

The literal extraction adds source-reported participants, observation span,
time points, and assay targets for the Snyder iPOP/iHMP publication. The UK
Biobank figure is a reported lower bound, not an exact enrollment. Assay target
counts are not independent biological dimensions and are never fed into the
capacity evaluator as such.

The expanded packet restores population and follow-up facts for ASPREE,
CALERIE, LIFE, MitoImmune, MoTrPAC, PEARL, PREDICT, TRIIM, and ZOE METHOD.
UK Biobank's whole-genome and plasma-proteomic subsets retain their separate
denominators. LIFE reports a mean follow-up of 2.6 years and median of 2.7 years;
these are not interchangeable. TRIIM's ten recruits and nine-person thymic
imaging analysis likewise remain distinct. The explicit word token `Ten` is
parsed by a small declared vocabulary, with whole-token matching.

For CIRCULATE, the original frozen registry denominator and the publication's
enrollment and completion denominators are all retained. They cannot be
silently substituted for each other. The literature packet was replayed against
the complete primary-source snapshots on 2026-09-17. Those snapshots matched the
source hashes already present in the repository. The current official All of
Us CDRv9 page is an explicitly recorded source refresh: it preserves the exact
URL and prior snapshot hash while binding the new response bytes. Its reported
cohort size is a lower bound and does not imply every participant has every
assay. Independent source review remains pending.

Check the public packet:

```bash
python scripts/verify_reported_facts.py
```

For full-source replay, retrieve each packet source's `fetch_url` to a private
directory as `<source_id>.json` (or `<source_id>.txt` for a source with
`source_format: utf8_text`), then run:

```bash
python scripts/verify_reported_facts.py --raw-source-dir /path/to/private/snapshots
```

The replay rejects changed response-body hashes, absent or duplicated literal
matches, and mismatched numerical tokens. Upstream source drift must be reviewed
as a new source version, not accepted by silently replacing the digest.

## Portable static build

```bash
python scripts/build_explorer.py --out /path/to/new/site-directory
python -m http.server --bind 127.0.0.1 --directory /path/to/new/site-directory 8766
```

The builder requires a new output directory, verifies the atlas before writing,
runs the canonical evaluator for the illustrative designs, and emits
`BUILD_MANIFEST.json` with hashes for all generated assets. The resulting
directory can be served by any static host. This command does not publish it.

Source files remain in the normal public export allowlist, wheel, and source
distribution. No participant-level inputs, private ANI projection, private
handoff archive, or clinical source body is part of the explorer build.

## Remaining scientific release work

The interface does not resolve missing Elite geometry, a source-complete
heterogeneous comparator evaluation, calibrated observation operators, or
independent benchmark review. Native category positions require those inputs
on a shared metric and claim basis. A polished interface and passing software
tests do not establish those scientific results.
