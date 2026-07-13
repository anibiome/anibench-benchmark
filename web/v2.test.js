"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const v2 = require("./v2.js");

function designInput(overrides = {}) {
  return {
    assessment_lane: "design_preview",
    study_id: "trial-200",
    name: "Two-year personalized trial",
    population_value: "200",
    population_state: "conditional",
    population_semantics: "planned_enrollment",
    duration_value: "730",
    duration_state: "exact",
    duration_semantics: "intervention_duration_days",
    policy_arms: "4",
    randomized_policy: "true",
    concurrent_control: "true",
    adaptive_reassignment: "true",
    within_policy_randomized: "unknown",
    operator_families: "nutrition, exercise, nutrition",
    measurement_modules: [
      {module_id: "omics", label: "Multi-omics", evidence_state: "conditional", events_per_participant: "6"},
      {module_id: "voice", label: "Voice", evidence_state: "unknown", events_per_participant: "100"}
    ],
    ...overrides
  };
}

test("buildDesignPayload matches the compact v2 design-input contract", () => {
  const payload = v2.buildDesignPayload(designInput());
  assert.deepEqual(payload, {
    contract: "anibench.design-input.v2-candidate1",
    assessment_lane: "design_preview",
    study_id: "trial-200",
    name: "Two-year personalized trial",
    population: {value: 200, state: "conditional", semantics: "planned_enrollment"},
    duration: {value: 730, state: "exact", semantics: "intervention_duration_days"},
    policy_arms: 4,
    randomized_policy: true,
    concurrent_control: true,
    adaptive_reassignment: true,
    within_policy_randomized: null,
    operator_families: ["nutrition", "exercise"],
    measurement_modules: [
      {module_id: "omics", label: "Multi-omics", evidence_state: "conditional", events_per_participant: 6},
      {module_id: "voice", label: "Voice", evidence_state: "unknown", events_per_participant: null}
    ]
  });
});

test("unknown typed population and duration values compile to null", () => {
  const payload = v2.buildDesignPayload(designInput({
    population_state: "unknown",
    population_value: "999",
    duration_state: "unknown",
    duration_value: "999"
  }));
  assert.deepEqual(payload.population, {value: null, state: "unknown", semantics: "planned_enrollment"});
  assert.deepEqual(payload.duration, {value: null, state: "unknown", semantics: "intervention_duration_days"});
});

test("invalid counts and duplicate module IDs fail before network submission", () => {
  assert.throws(() => v2.buildDesignPayload(designInput({population_value: "0"})), /positive whole number/);
  assert.throws(() => v2.buildDesignPayload(designInput({measurement_modules: [
    {module_id: "same", label: "A", evidence_state: "exact", events_per_participant: 1},
    {module_id: "same", label: "B", evidence_state: "exact", events_per_participant: 2}
  ]})), /unique/);
  assert.throws(() => v2.buildDesignPayload(designInput({study_id: "bad id"})), /Study ID/);
  assert.throws(() => v2.buildDesignPayload(designInput({policy_arms: "1", randomized_policy: "true"})), /at least two/);
});

test("tri-state causal fields preserve unknown instead of coercing false", () => {
  assert.equal(v2.triState("true"), true);
  assert.equal(v2.triState("false"), false);
  assert.equal(v2.triState("unknown"), null);
});

test("coordinate render helper supports object and array response shapes", () => {
  const objectRows = v2.normalizeCoordinates({
    population: {state: "conditional", value: 200, unit: "people", semantics: "planned enrollment"}
  });
  assert.deepEqual(objectRows[0], {
    id: "population",
    label: "Population",
    state: "conditional",
    value: 200,
    unit: "people",
    semantics: "planned enrollment",
    source: ""
  });
  const arrayRows = v2.normalizeCoordinates([{coordinate_id: "events", state: "unknown", value: null}]);
  assert.equal(arrayRows[0].label, "Events");
  assert.equal(arrayRows[0].state, "unknown");
});

test("gate and upgrade helpers retain objective grouping and next actions", () => {
  const gates = v2.normalizeGates([{gate_id: "duration", reason: "Not frozen", close_when: "Freeze protocol"}]);
  assert.equal(gates[0].title, "Duration");
  assert.equal(gates[0].nextAction, "Freeze protocol");
  const groups = v2.groupUpgrades([
    {objective_group: "causal architecture", title: "Add control"},
    {objective_group: "biological resolution", title: "Add function"}
  ]);
  assert.deepEqual(Object.keys(groups), ["causal architecture", "biological resolution"]);
});

test("assessment helper flattens declared, causal, module, and derived coordinates", () => {
  const rows = v2.flattenAssessmentCoordinates({
    coordinates: {
      population: {value: 200, state: "conditional", semantics: "planned_enrollment", unit: "people"},
      duration: {value: 730, state: "exact", semantics: "intervention_duration_days", unit: "days"},
      policy_arms: {value: 2, state: "exact", semantics: "declared_policy_arms", unit: "arms"},
      operator_families: {value: ["nutrition"], state: "exact", semantics: "declared_operator_families"},
      causal_architecture: {
        randomized_policy: {value: true, state: "exact", semantics: "policy_randomization"}
      },
      measurement_modules: [{
        module_id: "omics", label: "Multi-omics", evidence_state: "conditional",
        events_per_participant: 6, source_json_pointers: ["/measurement_modules/0"]
      }]
    },
    derived_coordinates: {
      measurement_module_state_counts: {
        exact: 0, conditional: 1, unknown: 0,
        formula: "count(measurement_modules by evidence_state)",
        source_json_pointers: ["/measurement_modules"]
      },
      participant_event_totals_by_module: [{
        module_id: "omics", value: 1200, state: "conditional", unit: "participant_events",
        formula: {expression: "population.value * measurement_modules[i].events_per_participant"}
      }]
    }
  });
  assert.ok(rows.some(row => row.id === "causal_randomized_policy" && row.value === true));
  assert.ok(rows.some(row => row.id === "module_omics" && row.value === 6));
  assert.ok(rows.some(row => row.id === "derived_events_omics" && row.value === 1200));
  assert.ok(rows.some(row => row.id === "measurement_module_state_counts" && row.state === "derived"));
});

test("backend upgrade object is flattened without inventing preference ordering", () => {
  const rows = v2.normalizeUpgrades({
    causal_identifiability: [{
      upgrade_id: "add-control", objective: "causal_identifiability",
      design_change: "Add a concurrent control.", decision_rule: "Apply when drift matters."
    }]
  });
  assert.deepEqual(rows[0], {
    id: "add-control",
    objective: "causal_identifiability",
    title: "Add Control",
    rationale: "Apply when drift matters.",
    action: "Add a concurrent control."
  });
});

test("mechanics fixture exactly carries the registered illustrative authority shape", () => {
  assert.equal(v2.mechanicsFixture.reference_authority_id, "illustrative-mechanics-2d-v1");
  assert.deepEqual(v2.mechanicsFixture.information_matrix, [[2, 0], [0, 1]]);
  assert.match(v2.mechanicsFixture.matrix_hashes.information_matrix_sha256, /^sha256:[0-9a-f]{64}$/);
  assert.equal(v2.mechanicsFixture.source_objects[0].object_id, "source:fixture");
  assert.match(v2.MECHANICS_FIXTURE_TEXT, /"information_matrix": \[\[2\.0, 0\.0\]/);
  const registered = fs.readFileSync(
    path.join(__dirname, "..", "spec", "v2", "mechanics-fixtures", "illustrative-reference-2d.json"),
    "utf8"
  ).trim();
  assert.equal(v2.MECHANICS_FIXTURE_TEXT.trim(), registered);
});

test("numeric formatting remains deterministic", () => {
  assert.equal(v2.format(1.23456, 2), "1.23");
  assert.equal(v2.renderEnvelopeValue({minimum: null, maximum: null}), "Not resolved");
});

test("Level-1 family rows preserve native source-located metrics", () => {
  const family = {
    family_id: "intensive",
    native_metrics: [{
      metric_id: "effective_rank",
      label: "Effective observed dimensions",
      value: 4,
      unit: "effective_dimensions",
      state: "resolved",
      source_object_sha256: `sha256:${"a".repeat(64)}`,
      source_locator: "/scenarios/0/families/intensive/effective_rank"
    }],
    level1_target_attainment: {state: "unresolved", value: null}
  };
  assert.deepEqual(v2.level1FamilyMetricRows(family), family.native_metrics);
  assert.equal(family.level1_target_attainment.value, null);
});

test("Level-1 JSON text validation preserves the submitted serialization", () => {
  const raw = '{"operator_row":[1.0,0.0],"participant_count":{"state":"exact","value":1}}\n';
  assert.equal(v2.validateJsonText(raw), raw);
  assert.equal(JSON.stringify(JSON.parse(raw)).includes("1.0"), false);
});

test("ClinicalTrials.gov helpers preserve exact NCT identity without creating geometry", () => {
  assert.equal(v2.canonicalNctId(" nct01234567 "), "NCT01234567");
  assert.throws(() => v2.canonicalNctId("NCT123"), /eight digits/);
  const rows = v2.ctgovStudyRows({
    parsed_content: {
      studies: [{
        protocolSection: {
          identificationModule: {
            nctId: "NCT01234567",
            briefTitle: "Deep longitudinal intervention trial"
          },
          statusModule: {overallStatus: "RECRUITING"},
          designModule: {
            phases: ["PHASE2"],
            enrollmentInfo: {count: 200, type: "ESTIMATED"}
          }
        }
      }]
    }
  });
  assert.deepEqual(rows, [{
    nct_id: "NCT01234567",
    title: "Deep longitudinal intervention trial",
    status: "RECRUITING",
    phases: "PHASE2",
    enrollment: 200
  }]);
  assert.deepEqual(v2.ctgovStudyRows({parsed_content: {}}), []);
});

test("six-family map preserves non-interchangeable families and exact envelopes", () => {
  const map = v2.buildFamilyMap({
    family_envelopes: {
      "transport.transport_rank": {minimum: 1, maximum: 2},
      "intensive.effective_rank": {minimum: 3, maximum: 3},
      "causal.policy_rank": {minimum: 2, maximum: 2}
    }
  });
  assert.deepEqual(map.map(family => family.family_id), [
    "intensive", "extensive", "longitudinal", "causal", "personalized_sequential", "transport"
  ]);
  assert.equal(map[0].metrics[0].label, "Resolved directions");
  assert.deepEqual(map[0].metrics[0].envelope, {minimum: 3, maximum: 3});
  assert.equal(map[0].state, "partial");
  assert.equal(map[1].state, "unknown");
  assert.equal(map[5].metrics[0].path, "transport.transport_rank");
});

test("transport axis-family vector suppresses the unresolved aggregate alias", () => {
  const map = v2.buildFamilyMap({
    scenarios: [{
      scenario_id: "transport-vector",
      families: {transport: {resolution_state: "resolved_axis_family_vector"}}
    }],
    family_envelopes: {
      "transport.transport_rank": {
        resolution_state: "unresolved", minimum: null, maximum: null,
        resolved_scenario_count: 0, total_scenario_count: 1
      },
      "transport.transport_allocation_support_factor": {
        resolution_state: "unresolved", minimum: null, maximum: null,
        resolved_scenario_count: 0, total_scenario_count: 1
      },
      "transport.axis_families.site-transport.transport_rank": {minimum: 1, maximum: 1},
      "transport.axis_families.site-transport.transport_allocation_support_factor": {
        minimum: 5.625, maximum: 5.625
      },
      "transport.axis_families.environment-transport.transport_rank": {
        minimum: 1, maximum: 1
      }
    }
  });
  const transport = map[5];
  assert.equal(transport.state, "resolved");
  assert.equal(transport.metrics.length, 3);
  assert.ok(transport.metrics.every(metric => metric.path.startsWith("transport.axis_families.")));
  assert.deepEqual(v2.metricPresentation(
    "transport.axis_families.site-transport.transport_rank"
  ), {label: "Site Transport · independent contrasts", unit: "directions"});
});

test("six-family map never labels unresolved null envelopes as compiled", () => {
  const map = v2.buildFamilyMap({
    scenarios: [{
      scenario_id: "unknown-covariance",
      families: {
        intensive: {resolution_state: "unresolved_no_known_observer"},
        extensive: {resolution_state: "partial_known_lower_bound_with_unresolved_observers"}
      }
    }],
    family_envelopes: {
      "intensive.effective_rank": {
        resolution_state: "unresolved", minimum: null, maximum: null,
        resolved_scenario_count: 0, total_scenario_count: 1
      },
      "extensive.effective_rank": {minimum: 2, maximum: 2},
      "extensive.retained_log10_contraction": {
        resolution_state: "unresolved", minimum: null, maximum: null,
        resolved_scenario_count: 0, total_scenario_count: 1
      }
    }
  });
  assert.equal(map[0].state, "unresolved");
  assert.deepEqual(map[0].unresolved_metric_paths, ["intensive.effective_rank"]);
  assert.equal(map[1].state, "partial");
  assert.deepEqual(map[1].resolution_states, ["partial_known_lower_bound_with_unresolved_observers"]);
});

test("allocation-support factors are displayed as proxies, never biological information", () => {
  assert.deepEqual(v2.metricPresentation("causal.policy_allocation_support_factor"), {
    label: "Policy allocation-support proxy",
    unit: "support factor"
  });
  assert.deepEqual(
    v2.metricPresentation(
      "personalized_sequential.sequential_moderator_allocation_support_factor"
    ),
    {label: "Moderator allocation-support proxy", unit: "support factor"}
  );
  assert.deepEqual(v2.metricPresentation("transport.transport_allocation_support_factor"), {
    label: "Transport allocation-support proxy",
    unit: "support factor"
  });
});

test("ordinary design receipt hands off required geometry without inferred matrices", () => {
  const assessment = {
    study: {study_id: "planned-trial"},
    assessment_lane: {value: "design_preview"},
    input_sha256: `sha256:${"a".repeat(64)}`
  };
  const handoff = v2.buildDesignHandoffReceipt(assessment);
  assert.equal(handoff.family_readiness.length, 6);
  assert.ok(handoff.family_readiness.every(family => family.state === "requires_explicit_protocol_geometry"));
  assert.deepEqual(handoff.no_inference_policy, {
    matrices_inferred_from_module_names: false,
    missing_geometry_imputed: false,
    menu_counts_converted_to_information: false
  });
  assert.equal(handoff.overall_scalar, null);
  assert.equal(handoff.public_rank_emission_permitted, false);
});

test("comparator placement fails closed before source-complete shared authority", () => {
  const placement = v2.deriveComparatorPlacement({
    protocol_sha256: `sha256:${"b".repeat(64)}`,
    comparison_eligible: false,
    family_envelopes: {"intensive.effective_rank": {minimum: 1, maximum: 1}}
  }, {
    coordinate_table: {sha256: `sha256:${"c".repeat(64)}`},
    studies: []
  });
  assert.equal(placement.state, "not_comparable_protocol_authority_hold");
  assert.deepEqual(placement.relations, []);
  assert.equal(placement.overall_scalar, null);
});

test("comparator placement computes Pareto relation only on an exact shared basis", () => {
  const basis = `sha256:${"9".repeat(64)}`;
  const placement = v2.deriveComparatorPlacement({
    protocol_sha256: `sha256:${"8".repeat(64)}`,
    comparison_eligible: true,
    comparison_basis_sha256: basis,
    family_envelopes: {
      "intensive.effective_rank": {minimum: 3, maximum: 3},
      "causal.policy_rank": {minimum: 2, maximum: 2}
    }
  }, {
    coordinate_table: {sha256: `sha256:${"7".repeat(64)}`},
    studies: [{
      study_id: "source-complete-comparator",
      comparison_eligible: true,
      comparison_basis_sha256: basis,
      family_envelopes: {
        "intensive.effective_rank": {minimum: 2, maximum: 2},
        "causal.policy_rank": {minimum: 1, maximum: 1}
      }
    }]
  });
  assert.equal(placement.state, "pareto_relations_computed");
  assert.equal(placement.relations[0].state, "candidate_pareto_dominates");
  assert.equal(placement.public_rank_emission_permitted, false);
});

test("Pareto relations require identical metrics and separated envelopes", () => {
  assert.deepEqual(v2.classifyParetoRelation(
    {a: {minimum: 3, maximum: 4}, b: {minimum: 5, maximum: 6}},
    {a: {minimum: 1, maximum: 2}, b: {minimum: 3, maximum: 4}}
  ), {
    state: "candidate_pareto_dominates",
    reason: "separated_envelopes",
    metric_paths: ["a", "b"]
  });
  assert.equal(v2.classifyParetoRelation(
    {a: {minimum: 1, maximum: 3}},
    {a: {minimum: 2, maximum: 4}}
  ).state, "indeterminate_interval_overlap");
  assert.equal(v2.classifyParetoRelation(
    {a: {minimum: 2, maximum: 2}},
    {a: {minimum: 2, maximum: 2}}
  ).state, "pareto_equivalent");
  assert.equal(v2.classifyParetoRelation(
    {a: {minimum: 1, maximum: 1}},
    {b: {minimum: 1, maximum: 1}}
  ).state, "unknown");
});

test("matching identifiers remain explicitly non-semantic without a hashed pointer crosswalk", () => {
  const capacity = {
    protocol_id: "same-study",
    protocol_sha256: `sha256:${"d".repeat(64)}`,
    comparison_eligible: false,
    family_envelopes: {"intensive.effective_rank": {minimum: 1, maximum: 1}}
  };
  const receipt = v2.buildStudioWorkflowReceipt(capacity, {
    schema_version: "anibench.studio-comparator-atlas.v1",
    coordinate_table: {sha256: `sha256:${"e".repeat(64)}`},
    study_count: 16,
    comparison_eligible_study_count: 0,
    row_order_semantics: "coordinate_table_source_order_not_rank",
    studies: []
  }, {
    study: {study_id: "same-study"},
    input_sha256: `sha256:${"f".repeat(64)}`
  });
  assert.equal(receipt.design_binding.state, "identifier_match_only_not_semantic_binding");
  assert.equal(
    receipt.design_binding.reason,
    "matching_identifier_without_content_hashed_pointer_crosswalk"
  );
  assert.deepEqual(receipt.design_binding.required_design_geometry_pointers, ["/study_id"]);
  assert.deepEqual(receipt.design_binding.missing_design_geometry_pointers, ["/study_id"]);
  assert.equal(receipt.comparator_atlas_binding.study_count, 16);
  assert.equal(receipt.overall_scalar, null);
  assert.equal(receipt.public_rank_emission_permitted, false);
});

test("semantic binding requires matching object hashes and complete one-to-one pointer coverage", () => {
  const designInputSha256 = `sha256:${"1".repeat(64)}`;
  const protocolSha256 = `sha256:${"2".repeat(64)}`;
  const design = {
    study: {study_id: "same-study"},
    input_sha256: designInputSha256,
    coordinates: {
      population: {source_json_pointers: ["/population/value", "/population/state"]},
      causal_architecture: {
        randomized_policy: {source_json_pointers: ["/randomized_policy"]}
      }
    }
  };
  const capacity = {protocol_id: "same-study", protocol_sha256: protocolSha256};
  const required = v2.designGeometrySourcePointers(design);
  assert.deepEqual(required, [
    "/population/state", "/population/value", "/randomized_policy", "/study_id"
  ]);
  const crosswalk = {
    schema_version: "anibench.design-protocol-crosswalk.v1",
    crosswalk_sha256: `sha256:${"3".repeat(64)}`,
    design_input_sha256: designInputSha256,
    protocol_sha256: protocolSha256,
    pointer_bindings: required.map((pointer, index) => ({
      design_source_json_pointer: pointer,
      protocol_source_json_pointers: [`/registered_geometry/${index}`],
      binding_content_sha256: `sha256:${String(index + 4).repeat(64).slice(0, 64)}`
    }))
  };
  const bound = v2.deriveDesignProtocolBinding(capacity, design, crosswalk);
  assert.equal(bound.state, "bound_by_content_hashed_pointer_crosswalk");
  assert.deepEqual(bound.missing_design_geometry_pointers, []);
  assert.equal(bound.pointer_binding_count, required.length);

  const incomplete = structuredClone(crosswalk);
  incomplete.pointer_bindings.pop();
  const rejected = v2.deriveDesignProtocolBinding(capacity, design, incomplete);
  assert.equal(rejected.state, "identifier_match_only_not_semantic_binding");
  assert.equal(rejected.reason, "crosswalk_invalid_or_incomplete");
  assert.deepEqual(rejected.missing_design_geometry_pointers, ["/study_id"]);
});

test("v2 page excludes withdrawn optimizer contracts and rank-preview routes", () => {
  const html = fs.readFileSync(path.join(__dirname, "v2.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "v2.js"), "utf8");
  for (const value of [
    "anibench.optimizer-run.v2-candidate1",
    '"/api/v2/optimize"',
    "/api/preview",
    "/api/optimize",
    "overall trial quality"
  ]) {
    assert.doesNotMatch(html, new RegExp(value.replaceAll("/", "\\/"), "i"));
    assert.doesNotMatch(script, new RegExp(value.replaceAll("/", "\\/"), "i"));
  }
  assert.match(html, /protocol-native/i);
  assert.match(script, /\/api\/v2\/optimize-protocol/i);
  assert.match(script, /\/api\/v2\/protocol-capacity/i);
  assert.match(script, /\/api\/v2\/comparator-atlas/i);
  assert.match(script, /Family coordinate state/i);
  assert.doesNotMatch(script, /Family placement/i);
  assert.match(html, /Six-family map/i);
  assert.match(html, /Continue to executable geometry/i);
});
