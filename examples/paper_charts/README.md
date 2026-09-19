# Manuscript charts

Six source-bound plates retain readable labels at a native width of 6.5 inches.
Figures 3–6 reproduce reported source inventories; Figures 7–8 show conditional
synthetic reference-workload results, not real-study rankings. Exact input hashes
are checked before rendering. Changed inputs require a newly reviewed contract.

Regenerate into a new directory from the repository root:

```bash
python examples/paper_charts/plot_paper_plates.py \
  --architecture web/source-architecture.json \
  --reference examples/broad_reference/figure-data.json \
  --profiles examples/broad_reference/profile-declarations.json \
  --out build/paper-charts
```

Install the `paper` extra first. `metadata.json` binds the source packets, plotting
code, artifact bytes, and exact plotted facts. The manuscript builder verifies
these bindings. SVGs support vector export; PNGs are embedded without reducing
the native label size. All source qualifiers and category outcomes are retained.
