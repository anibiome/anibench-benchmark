<!-- SPDX-FileCopyrightText: 2026 ANI -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Compare a reported molecular inventory

```bash
anibench compare-architecture examples/architecture/protein-inventory.json \
  --out output/protein-comparison.json --pretty
```

The example compares the **reported protein inventory** of two studies, using
public aggregate facts. It asks one narrow question: how many unique proteins
does each source report? It does not compare assay accuracy, independent
biological information, complete observations per person, or overall study quality.

| Source | Reported proteins | Assay and source location |
| --- | ---: | --- |
| [iPOP/iHMP (2019)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/) | 302 | Plasma SWATH-MS; BioC `/0/documents/0/passages/12/text` |
| [UKB-PPP (2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10567551/) | 2,923 | Plasma Olink Explore; BioC `/0/documents/0/passages/10/text` |

The latter source distinguishes 2,941 analytes from 2,923 unique proteins.
These quantities are not interchangeable. The iPOP source reports an assay
inventory and incomplete multi-assay coverage across visits; the example does
not assign all 302 proteins to every person at every visit.

The request binds the exact public BioC response hashes and JSON pointers from
source retrieval on 19 September 2026. Retrieval endpoints follow
`https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC_ID/unicode`.
Hashes verify source identity when replayed against those bytes; the comparison
command itself checks the supplied contract, not remote source truth. Original
articles remain at their publishers; no participant tables are redistributed.

The result identifies UKB-PPP as larger on this one inventory quantity. Add a
different quantity with an incompatible scope or unknown value and the joint
comparison stays unresolved. A greater target inventory alone never establishes
greater biological information or an overall winner.
