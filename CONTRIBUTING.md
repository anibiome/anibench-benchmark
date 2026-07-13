# Contributing

AniBench accepts source-located corrections, new studies, methods proposals, code, tests, and independent task executions.

## Evidence contributions

Every capacity-bearing or comparison-bearing fact must include:

- stable study and protocol identity;
- exact field path, value, unit, and denominator;
- evidence state and value state;
- source URI or path plus an exact locator;
- person, specimen, and timepoint linkage state where relevant;
- retrieval date and content hash;
- first rating, second rating, and adjudication state before public ranking.

A title, abstract keyword, sponsor, journal, press release, or institutional reputation cannot create a score-bearing fact.

## Methods contributions

Formula, reference, axis, or evidence-state changes require a methods RFC with:

1. biological construct and failure mode;
2. mathematical expression and units;
3. source-field mapping and missingness behavior;
4. invariants and adversarial tests;
5. blinded impact across the comparator corpus;
6. sensitivity and migration plan;
7. conflict-of-interest declaration.

## Development

```bash
python -m pip install -e '.[dev]'
make test
make verify
```

Do not commit private participant data, controlled source text, credentials, local absolute paths, generated caches, or unlicensed third-party content.
