# Source-reported collection figures

These two full-page charts reproduce all 21 numeric facts and 30 coverage cells
in `web/source-architecture.json`. Population/subset support, molecular inventories
and timing retain their source-defined units. Reported presence does not imply
complete participant coverage; description-only and unknown cells stay distinct.

From the repository root, with the paper extra installed:

```sh
python examples/architecture/charts/plot.py --packet web/source-architecture.json --out output/source-figures
```

The output directory must be new. `metadata.json` binds the exact source packet,
plot script, source URLs and hashes, fact identifiers, and coverage cells. SVG
marks link to source URLs. Source snapshots remain external; no participant data
is needed. Read the figures at full-page scale, not as single-column thumbnails.

The two public plates are `01-populations-and-coverage.svg` and
`02-entities-and-timing.svg`, with corresponding PNGs. HPP quantities are from the
July 2025 abstract. ELITE fields use a public description only. UK Biobank's
perturbation cell refers to a subset exercise challenge, not assigned therapy.
