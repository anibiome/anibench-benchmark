# Study evidence context and hypothetical approval copies

`anibench.study_context` provides a thin sidecar, not a solver, approval verifier,
or scientific receipt validator. It never modifies, parses, scores or transmits
the supplied input/result bytes. Publication and ethics evidence are independent;
unknown is not explicitly not approved. All objects are JSON-compatible.

```python
from anibench.study_context import create_context, hypothetical_approval_copy, validate_context

# Synthetic bytes only; ordinary application code reads exact local file bytes.
design = b'{"synthetic": 2.0}\n'
result = b'{"synthetic_result": 1}\n'
actual = create_context("synthetic-study", "Synthetic study",
                        input_bytes=design, result_bytes=result)
scenario = hypothetical_approval_copy(
    actual, "synthetic-study-approval-copy", "Hypothetical approval copy",
    reason="Assume approval with no design changes",
    input_bytes=design, result_bytes=result,
)
validate_context(scenario, input_bytes=design, result_bytes=result, parent=actual)
```

The caller supplies globally distinct IDs; validation rejects reuse of the parent
ID, but there is no global registry or persistence service. Hypothetical copies
require an actual parent, its canonical context hash, unchanged byte bindings and
unchanged evidence. Their sole changed assumption is stored in `assumptions`,
with `assumed_value: approved` and `affects_design: false`. It never changes
`evidence.ethics.status`. Inherited evidence is labeled `parent_study`, not proof
of approval of a new protocol. Copies cannot be used as independent acquired
studies or additional participants. UI and comparison integrations must enforce
that separation; this module does not aggregate or filter records.

`create_context(..., evidence=...)` accepts independent `publication` and `ethics`
objects with `status`, `basis` and `sources`. Basis is `source_reported`,
`user_declared` or `unknown`. Unknown status and basis must agree. Source-reported
status requires a source containing a public HTTPS `url` and a short `locator`.
User declarations remain declarations. No free-form private file paths or source
attachments are supported. URLs with credentials, queries, fragments, IP hosts,
local hostnames, backslashes or percent escapes are deliberately unsupported.
The validator performs no DNS/network access: syntactic acceptance is not proof
of public accessibility, source authenticity or committee approval. Do not put
private details in display names, reasons or locators in public artifacts.

The JSON schema defines structural constraints; `validate_context` additionally
checks semantic invariants and supplied byte bindings. `bytes_sha256` uses exact
bytes and a `sha256:` prefix. Context hashes use UTF-8 JSON with sorted keys,
compact separators, no ASCII escaping, no NaN, and omit `context_sha256` itself.
Changing metadata changes the context hash, not the design/result hashes.
A changed parent invalidates existing parent bindings. Reopening a hypothetical
requires the bound parent; reopening any result-bound context requires both
original input and result bytes. Changed bytes or missing bound bytes reject.

`result_state: bytes_bound` means only that these result bytes are bound to this
sidecar. It does **not** prove they were computed from the input, are valid
scientific results or are externally verified. Existing evaluator receipt
validation remains necessary. Without result bytes the state is `not_run` and
result hash is null; an approval assumption cannot manufacture a result.
Future geometry changes require a separate fresh scientific run and new context;
this API supports approval-only copies, not arbitrary protocol editing.

Integration should wrap unchanged scientific receipts plus this sidecar in a
new versioned outer bundle. Do not add fields to the strict compiler input,
rewrite existing hashed receipts or trigger recomputation on evidence edits.
Keep actual approval filters based on actual source/declaration evidence, with
assumed approval in a separately labeled hypothetical lane. The local CLI is shown below. This module does not fetch sources, publish files,
or manage a browser scenario catalog. The schema is included in the wheel.


## Local command-line workflow

Use the included synthetic design to run a real evaluation, then attach optional
context. Keeping context separate preserves the evaluator's strict input contract.

```bash
anibench eval web/protocol-capacity-example.json --out build/design-result.json
anibench study-context create web/protocol-capacity-example.json \
  --result build/design-result.json --id synthetic-study --name "Synthetic study" \
  --out build/study-context.json
anibench study-context assume-approval web/protocol-capacity-example.json \
  --result build/design-result.json --parent build/study-context.json \
  --id synthetic-approval-copy --name "Hypothetical approval copy" \
  --reason "Compare the same design under assumed approval" \
  --out build/approval-copy.json
anibench study-context verify web/protocol-capacity-example.json \
  --result build/design-result.json --context build/approval-copy.json \
  --parent build/study-context.json
```

A successful final command reports `valid: true` for byte and parent bindings;
`scientific_result_verified: false` prevents that from being mistaken for a
scientific validation result. Inputs, results, parents and evidence files cannot
be overwritten by the context output, including through hard-link aliases.
Omit `--result` to bind a design before running it. Supply `--evidence evidence.json`
on `create` to set the two independent axes; otherwise both remain unknown.
An unpublished example, requiring no asserted committee evidence, is:

```json
{
  "publication": {"status": "unpublished", "basis": "user_declared", "sources": []},
  "ethics": {"status": "unknown", "basis": "unknown", "sources": []}
}
```

The commands are local and make no network requests. A context file does not
change which scientific comparisons the bound design supports.
