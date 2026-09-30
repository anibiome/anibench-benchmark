# Keep the study visible beside its reference result

A study can meet every selected test and still contain useful acquisitions the
reference does not assess. Two selected methylation sites do not represent an
epigenome. Sleep summaries do not represent every digital observation. A missing
glucose measurement does not establish missing microbial data.

The `anibench.study-collection-request.v1` input keeps the source-defined
acquisition graph beside the existing evaluator. It uses the same command:

```sh
anibench study-questions examples/study_questions/PROFILE.json \
  examples/study_questions/collection_scope_REQUEST.json --out new-result.json
```

The example is fictional. The wrapper has three fields: `contract`, `evaluation`
(an existing study-question request), and `collection`. It runs the original
calculation unchanged. `reference_evaluation` retains that exact receipt;
`collection_scope` retains observations, uncertainties and mapping limits.
The wrapper emits no new whole-study percentage.

Each acquisition keeps biological subject, anatomical compartment, physical
channel, native observable, resolution, timing, population, quality, and raw versus
derived status. Every property carries a description, source identifiers and one
of `documented`, `declared`, `unknown`, or `documented_absent`. A source claim is
not automatically verified by the evaluator. Protocol presence and reported
acquisition are distinct; neither grants a verified participant-level roster.
Open inventories cannot establish that an unlisted modality is absent.

Links distinguish derivation, same-person membership, time alignment, exposure
alignment and controlled contrasts. None is inferred from co-occurrence in a
paper. Derived outputs retain their parents; cycles and conflicting identities
are rejected. Copies of the same acquisition row collapse. Renamed rows do not
earn points: this layer has no count-based scoring or coverage percentage.

Reference mappings name the exact question definition and the precise observable
it addresses. `selected_observables` is explicitly partial;
`exact_named_observable` means that named target, never every use of a raw asset.
Incompatible and unresolved mappings remain visible. Unmapped acquisitions are
retained as `outside_reference`, not converted to zero. Mappings are qualified
source statements, not proof that estimator inputs came from those acquisitions.
The result explicitly keeps that latter linkage unverified. Numerical attainment
is available only from the nested original evaluator.

This prevents loss of the collection description while constructing and testing
a representative reference. It does not solve reference selection, calibrate a
new biological score, prove independent information from channel names, or finish
the benchmark. Native observation capability, host-function relations and causal
effects still need their own justified targets and input evidence.

## Why a complete denominator can still miss biology

Let `D` denote a study collection, `P_R(D)` its input projection onto reference
`R`, and `s_R(D) = f_R(P_R(D))` the resulting score. If two collections have the
same projection, their scores must be equal:

```math
P_R(D_1)=P_R(D_2) \quad\Longrightarrow\quad s_R(D_1)=s_R(D_2).
```

This follows by substitution. It is a useful invariance for duplicate files,
but a scope limitation when the second collection adds useful acquisitions
outside `R`. No choice of weights within the unchanged reference can distinguish
those collections. The reference must change, or the additional capability must
remain explicitly unassessed. Unknown mass inside `R` does not account for
targets never included in `R`.

Likewise, a combined microbial/host task can require both native microbial
evidence `M` and host-function evidence `F`. Its logical pass is `M AND F`.
When `F` is false, the conjunction is false regardless of `M`. Inferring that
microbial measurement failed from that combined failure is invalid. Native
measurement and linked-function tasks therefore need separate meanings; the
combined task remains legitimate under its exact name.

The collection layer makes the projection boundary inspectable. It does not
turn a documented channel into a numerical observation operator, establish a
new reference distribution, or infer a source-independent error model.
