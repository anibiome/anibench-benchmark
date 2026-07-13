"use strict";

const DESIGN_CONTRACT = "anibench.design-input.v2-candidate1";
const FAMILY_UI = [
  {
    id: "intensive",
    label: "Biological resolution",
    question: "What can one explicitly linked participant-state event resolve?",
    requirements: ["observation operators", "nuisance covariance", "joint event bundles"]
  },
  {
    id: "extensive",
    label: "Total reconstruction",
    question: "How does retained joint information accumulate across the experiment?",
    requirements: ["participant-event support", "retention", "repetition dependence"]
  },
  {
    id: "longitudinal",
    label: "Longitudinal resolution",
    question: "How densely and how long are the same participants measured?",
    requirements: ["participant-set linkage", "temporal offsets", "within-person covariance"]
  },
  {
    id: "causal",
    label: "Causal architecture",
    question: "Which policy and component contrasts are identified?",
    requirements: ["assignment stages", "policy geometry", "linked post-decision outcomes"]
  },
  {
    id: "personalized_sequential",
    label: "Personalized learning",
    question: "Which moderators and repeated decisions identify adaptive policies?",
    requirements: ["pre-decision moderators", "decision propensities", "linked later outcomes"]
  },
  {
    id: "transport",
    label: "Population transport",
    question: "Across which measured contexts can common policy effects transfer?",
    requirements: ["context coordinates", "common policies", "outcome-linked support"]
  }
];

const METRIC_UI = {
  "intensive.effective_rank": ["Resolved directions", "directions"],
  "intensive.maximum_joint_bundle_log10_contraction": ["Per-event log₁₀ contraction", "log₁₀"],
  "extensive.retained_participant_events": ["Retained participant-events", "participant-events"],
  "extensive.effective_rank": ["Resolved directions", "directions"],
  "extensive.retained_log10_contraction": ["Experiment log₁₀ contraction", "log₁₀"],
  "longitudinal.participant_weighted_median_distinct_offsets": ["Weighted median time points", "offsets"],
  "longitudinal.participant_weighted_median_span": ["Weighted median within-person span", "time units"],
  "longitudinal.retained_participant_events": ["Retained linked events", "participant-events"],
  "causal.policy_rank": ["Independent policy contrasts", "directions"],
  "causal.component_rank": ["Independent component contrasts", "directions"],
  "causal.policy_allocation_support_factor": ["Policy allocation-support proxy", "support factor"],
  "causal.component_allocation_support_factor": ["Component allocation-support proxy", "support factor"],
  "causal.eligible_randomized_participants": ["Outcome-linked randomized people", "participants"],
  "causal.eligible_randomized_participant_decisions": ["Eligible randomized decisions", "decisions"],
  "personalized_sequential.sequential_moderator_rank": ["Independent moderator directions", "directions"],
  "personalized_sequential.sequential_moderator_allocation_support_factor": ["Moderator allocation-support proxy", "support factor"],
  "personalized_sequential.eligible_randomized_participants": ["Personalization-supporting people", "participants"],
  "personalized_sequential.eligible_randomized_participant_decisions": ["Personalization-supporting decisions", "decisions"],
  "transport.transport_rank": ["Independent transport contrasts", "directions"],
  "transport.transport_allocation_support_factor": ["Transport allocation-support proxy", "support factor"]
};

// Raw JSON preserves decimal tokens in the registered fixture. Re-parsing and
// JSON.stringify-ing it would turn 2.0 into 2 and break exact payload identity.
const MECHANICS_FIXTURE_TEXT = `{
  "contract": "anibench.information-run.v2-candidate1",
  "benchmark_suite_version": "anibench.v2-illustrative-mechanics-candidate1",
  "lane": "design_preview",
  "parameter_space_hash": "sha256:6390361dfdff141a9223d632accf61242133a92d83f2a71be7233bb1cdbacca2",
  "prior_metric_hash": "sha256:e5bade0e979cb8cf6e53303dae696c6631a5c82ce60386d7a602f85fb249fcc0",
  "reference_level_hash": "sha256:52367a6622b19f08825e915fad80c542ad4f4c34dbcebad9f5007994b3e39208",
  "event_manifest_hash": "sha256:862417b9e7c3720bcb3263cd873b09892d787823b6f9a0f453e42824c5a4d4b6",
  "intervention_design_hash": "sha256:77f4c0b60ee93a5cb1e56f7a4817b8b115d2de78a4da19cb6e6243a00c17898b",
  "uncertainty_model_hash": "sha256:9019f8058b99ac31bb7dfedda8717b003d6a9ac5b8a809f9e5e08e2349e4c4d4",
  "reference_authority_id": "illustrative-mechanics-2d-v1",
  "matrix_hashes": {
    "information_matrix_sha256": "sha256:716e79aac26e68e22f33daef9fadc2af17450a7d4f8c331abf6c7a98d86e35f9",
    "prior_precision_matrix_sha256": "sha256:9edef8c16d436d60ee71fc92b2312d7ee052657f77a487bd809d383cba012000",
    "reference_information_matrix_sha256": "sha256:23c72720e4c8d2b5ab66350180e724b56350aff7c15e0bd4e11baebe344ba07a",
    "reference_direction_basis_sha256": "sha256:9edef8c16d436d60ee71fc92b2312d7ee052657f77a487bd809d383cba012000"
  },
  "information_matrix": [[2.0, 0.0], [0.0, 1.0]],
  "prior_precision": [[1.0, 0.0], [0.0, 1.0]],
  "reference_information": [[4.0, 0.0], [0.0, 4.0]],
  "reference_direction_basis": [[1.0, 0.0], [0.0, 1.0]],
  "source_objects": [
    {
      "object_id": "source:fixture",
      "sha256": "sha256:41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d"
    }
  ]
}`;

// Exact copy of spec/v2/mechanics-fixtures/illustrative-reference-2d.json.
const mechanicsFixture = {
  contract: "anibench.information-run.v2-candidate1",
  benchmark_suite_version: "anibench.v2-illustrative-mechanics-candidate1",
  lane: "design_preview",
  parameter_space_hash: "sha256:6390361dfdff141a9223d632accf61242133a92d83f2a71be7233bb1cdbacca2",
  prior_metric_hash: "sha256:e5bade0e979cb8cf6e53303dae696c6631a5c82ce60386d7a602f85fb249fcc0",
  reference_level_hash: "sha256:52367a6622b19f08825e915fad80c542ad4f4c34dbcebad9f5007994b3e39208",
  event_manifest_hash: "sha256:862417b9e7c3720bcb3263cd873b09892d787823b6f9a0f453e42824c5a4d4b6",
  intervention_design_hash: "sha256:77f4c0b60ee93a5cb1e56f7a4817b8b115d2de78a4da19cb6e6243a00c17898b",
  uncertainty_model_hash: "sha256:9019f8058b99ac31bb7dfedda8717b003d6a9ac5b8a809f9e5e08e2349e4c4d4",
  reference_authority_id: "illustrative-mechanics-2d-v1",
  matrix_hashes: {
    information_matrix_sha256: "sha256:716e79aac26e68e22f33daef9fadc2af17450a7d4f8c331abf6c7a98d86e35f9",
    prior_precision_matrix_sha256: "sha256:9edef8c16d436d60ee71fc92b2312d7ee052657f77a487bd809d383cba012000",
    reference_information_matrix_sha256: "sha256:23c72720e4c8d2b5ab66350180e724b56350aff7c15e0bd4e11baebe344ba07a",
    reference_direction_basis_sha256: "sha256:9edef8c16d436d60ee71fc92b2312d7ee052657f77a487bd809d383cba012000"
  },
  information_matrix: [[2.0, 0.0], [0.0, 1.0]],
  prior_precision: [[1.0, 0.0], [0.0, 1.0]],
  reference_information: [[4.0, 0.0], [0.0, 4.0]],
  reference_direction_basis: [[1.0, 0.0], [0.0, 1.0]],
  source_objects: [{
    object_id: "source:fixture",
    sha256: "sha256:41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d"
  }]
};

let compiledDesign = null;
let replayPacket = null;
let capacityPacket = null;
let level1AssessmentPacket = null;
let optimizerPacket = null;
let comparatorAtlas = null;
let ctgovSearchSnapshot = null;
let ctgovStudySnapshot = null;
let moduleSerial = 0;
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const NCT_ID_PATTERN = /^NCT[0-9]{8}$/;

function requireId(value, label) {
  const normalized = String(value || "").trim();
  if (!ID_PATTERN.test(normalized)) throw new Error(`${label} must use letters, numbers, dot, underscore, colon, or hyphen`);
  return normalized;
}

function uniqueStrings(values) {
  const seen = new Set();
  return values.map(value => String(value).trim()).filter(value => {
    const folded = value.toLocaleLowerCase();
    if (!value || seen.has(folded)) return false;
    seen.add(folded);
    return true;
  });
}

function positiveInteger(value, label, {nullable = false} = {}) {
  if (value === null || value === undefined || String(value).trim() === "") {
    if (nullable) return null;
    throw new Error(`${label} is required`);
  }
  const number = Number(value);
  if (!Number.isInteger(number) || number < 1) throw new Error(`${label} must be a positive whole number`);
  return number;
}

function triState(value) {
  if (value === true || value === "true" || value === "yes") return true;
  if (value === false || value === "false" || value === "no") return false;
  if (value === null || value === undefined || value === "unknown" || value === "") return null;
  throw new Error(`Invalid three-state value: ${value}`);
}

function typedQuantity(value, state, semantics, label) {
  if (!new Set(["exact", "conditional", "unknown"]).has(state)) throw new Error(`${label} has an invalid evidence state`);
  return {
    value: state === "unknown" ? null : positiveInteger(value, label),
    state,
    semantics: String(semantics || "").trim()
  };
}

function normalizeModule(module, index) {
  const evidenceState = module.evidence_state;
  if (!new Set(["exact", "conditional", "unknown"]).has(evidenceState)) {
    throw new Error(`Measurement module ${index + 1} has an invalid evidence state`);
  }
  const moduleId = requireId(module.module_id, `Measurement module ${index + 1} ID`);
  const label = String(module.label || "").trim();
  if (!label) throw new Error(`Measurement module ${index + 1} needs a label`);
  return {
    module_id: moduleId,
    label,
    evidence_state: evidenceState,
    events_per_participant: evidenceState === "unknown"
      ? null
      : positiveInteger(module.events_per_participant, `${label} events per participant`, {nullable: true})
  };
}

function buildDesignPayload(input) {
  const studyId = requireId(input.study_id, "Study ID");
  const name = String(input.name || "").trim();
  if (!name) throw new Error("Study name is required");
  if (!new Set(["design_preview", "registered", "realized", "accessible", "demonstrated"]).has(input.assessment_lane)) {
    throw new Error("Evidence lane is invalid");
  }
  const modules = (input.measurement_modules || []).map(normalizeModule);
  if (!modules.length) throw new Error("Add at least one measurement module");
  const moduleIds = modules.map(module => module.module_id);
  if (new Set(moduleIds).size !== moduleIds.length) throw new Error("Measurement module IDs must be unique");

  const policyArms = positiveInteger(input.policy_arms, "Policy arms", {nullable: true});
  const randomizedPolicy = triState(input.randomized_policy);
  const concurrentControl = triState(input.concurrent_control);
  if ((randomizedPolicy === true || concurrentControl === true) && (policyArms === null || policyArms < 2)) {
    throw new Error("Randomization or a concurrent control requires at least two policy arms");
  }
  return {
    contract: DESIGN_CONTRACT,
    assessment_lane: input.assessment_lane,
    study_id: studyId,
    name,
    population: typedQuantity(input.population_value, input.population_state, input.population_semantics, "Population"),
    duration: typedQuantity(input.duration_value, input.duration_state, input.duration_semantics, "Duration"),
    policy_arms: policyArms,
    randomized_policy: randomizedPolicy,
    concurrent_control: concurrentControl,
    adaptive_reassignment: triState(input.adaptive_reassignment),
    within_policy_randomized: triState(input.within_policy_randomized),
    operator_families: uniqueStrings(Array.isArray(input.operator_families)
      ? input.operator_families
      : String(input.operator_families || "").split(",")).map((family, index) => requireId(family, `Operator family ${index + 1}`)),
    measurement_modules: modules
  };
}

function displayValue(value, unit) {
  if (value === null || value === undefined || value === "") return "Not resolved";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ") || "None declared";
  if (typeof value === "object") return JSON.stringify(value);
  return `${value}${unit ? ` ${unit}` : ""}`;
}

function humanize(value) {
  return String(value || "").replace(/[_:-]+/g, " ").replace(/\b\w/g, letter => letter.toUpperCase());
}

function normalizeCoordinates(coordinates) {
  if (Array.isArray(coordinates)) {
    return coordinates.map((coordinate, index) => ({
      id: coordinate.coordinate_id || coordinate.id || `coordinate-${index + 1}`,
      label: coordinate.label || humanize(coordinate.coordinate_id || coordinate.id || `Coordinate ${index + 1}`),
      state: coordinate.state || coordinate.evidence_state || "unknown",
      value: coordinate.value,
      unit: coordinate.unit || "",
      semantics: coordinate.semantics || coordinate.formula || coordinate.derivation || "",
      source: coordinate.source_pointer || coordinate.source || coordinate.source_receipt_id || (coordinate.source_json_pointers || []).join(", ") || ""
    }));
  }
  return Object.entries(coordinates || {}).map(([id, raw]) => {
    const coordinate = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {value: raw};
    return {
      id,
      label: coordinate.label || humanize(id),
      state: coordinate.state || coordinate.evidence_state || "unknown",
      value: coordinate.value,
      unit: coordinate.unit || "",
      semantics: coordinate.semantics || coordinate.formula || coordinate.derivation || "",
      source: coordinate.source_pointer || coordinate.source || coordinate.source_receipt_id || (coordinate.source_json_pointers || []).join(", ") || ""
    };
  });
}

function flattenAssessmentCoordinates(result) {
  const coordinates = result.coordinates || {};
  const rows = [];
  for (const key of ["population", "duration", "policy_arms", "operator_families"]) {
    if (coordinates[key] !== undefined) rows.push(...normalizeCoordinates({[key]: coordinates[key]}));
  }
  Object.entries(coordinates.causal_architecture || {}).forEach(([key, value]) => {
    rows.push(...normalizeCoordinates({[`causal_${key}`]: value}));
  });
  (coordinates.measurement_modules || []).forEach(module => {
    rows.push({
      id: `module_${module.module_id}`,
      label: module.label,
      state: module.evidence_state,
      value: module.events_per_participant,
      unit: "events per participant",
      semantics: `Measurement module · ${module.module_id}`,
      source: (module.source_json_pointers || []).join(", ")
    });
  });
  const derived = result.derived_coordinates || {};
  if (derived.measurement_module_state_counts) {
    const counts = derived.measurement_module_state_counts;
    rows.push({
      id: "measurement_module_state_counts",
      label: "Measurement evidence states",
      state: "derived",
      value: `Exact ${counts.exact} · Conditional ${counts.conditional} · Unknown ${counts.unknown}`,
      unit: "",
      semantics: counts.formula || "Count modules by evidence state",
      source: (counts.source_json_pointers || []).join(", ")
    });
  }
  (derived.participant_event_totals_by_module || []).forEach(total => {
    rows.push({
      id: `derived_events_${total.module_id}`,
      label: `${humanize(total.module_id)} participant-events`,
      state: total.state,
      value: total.value,
      unit: total.unit,
      semantics: total.formula && total.formula.expression ? total.formula.expression : "Derived participant-event count",
      source: "Derived from declared population and module events"
    });
  });
  if (derived.participant_module_observation_total) {
    const total = derived.participant_module_observation_total;
    rows.push({
      id: "participant_module_observation_total",
      label: "Participant-module observations",
      state: total.state,
      value: total.value,
      unit: total.unit,
      semantics: humanize(total.semantics),
      source: "Derived workload count; not unique joint events or biological information"
    });
  }
  return rows;
}

function normalizeGates(openGates) {
  return (openGates || []).map((gate, index) => typeof gate === "string"
    ? {id: `gate-${index + 1}`, title: gate, reason: "", nextAction: ""}
    : {
        id: gate.gate_id || gate.id || `gate-${index + 1}`,
        title: gate.title || gate.label || humanize(gate.gate_id || gate.id || `Gate ${index + 1}`),
        reason: gate.reason || gate.detail || gate.message || "",
        nextAction: gate.close_when || gate.next_action || gate.required_action || gate.action || ""
      });
}

function normalizeUpgrades(upgrades) {
  const source = Array.isArray(upgrades)
    ? upgrades
    : Object.entries(upgrades || {}).flatMap(([objective, rows]) => (rows || []).map(row => ({objective_group: objective, ...row})));
  return source.map((upgrade, index) => typeof upgrade === "string"
    ? {id: `upgrade-${index + 1}`, objective: "Design structure", title: upgrade, rationale: "", action: ""}
    : {
        id: upgrade.upgrade_id || upgrade.id || `upgrade-${index + 1}`,
        objective: upgrade.objective_group || upgrade.objective || upgrade.family || "Design structure",
        title: upgrade.title || upgrade.label || upgrade.suggestion || humanize(upgrade.upgrade_id || upgrade.id || `Upgrade ${index + 1}`),
        rationale: upgrade.decision_rule || upgrade.rationale || upgrade.reason || upgrade.expected_gain || "",
        action: upgrade.design_change || upgrade.action || upgrade.change || upgrade.next_action || ""
      });
}

function groupUpgrades(upgrades) {
  return normalizeUpgrades(upgrades).reduce((groups, upgrade) => {
    const group = upgrade.objective;
    if (!groups[group]) groups[group] = [];
    groups[group].push(upgrade);
    return groups;
  }, {});
}

function text(tag, value, className) {
  const node = document.createElement(tag);
  node.textContent = String(value);
  if (className) node.className = className;
  return node;
}

function format(value, digits = 4) {
  return Number(value).toLocaleString(undefined, {maximumFractionDigits: digits});
}

function setStatus(id, message, error = false) {
  const node = document.getElementById(id);
  node.textContent = message;
  node.classList.toggle("error", error);
}

function canonicalNctId(value) {
  const normalized = String(value || "").trim().toUpperCase();
  if (!NCT_ID_PATTERN.test(normalized)) {
    throw new Error("NCT identifier must match NCT followed by eight digits");
  }
  return normalized;
}

function ctgovStudyRows(snapshot) {
  const studies = snapshot && snapshot.parsed_content && snapshot.parsed_content.studies;
  if (!Array.isArray(studies)) return [];
  return studies.map(study => {
    const protocol = study && study.protocolSection || {};
    const identity = protocol.identificationModule || {};
    const status = protocol.statusModule || {};
    const design = protocol.designModule || {};
    const nctId = typeof identity.nctId === "string" && NCT_ID_PATTERN.test(identity.nctId)
      ? identity.nctId
      : null;
    const title = identity.briefTitle || identity.officialTitle || "Untitled registry record";
    const phases = Array.isArray(design.phases) ? design.phases.join(", ") : null;
    const enrollment = design.enrollmentInfo && design.enrollmentInfo.count;
    return {
      nct_id: nctId,
      title: String(title),
      status: typeof status.overallStatus === "string" ? status.overallStatus : null,
      phases,
      enrollment: Number.isInteger(enrollment) && enrollment >= 0 ? enrollment : null
    };
  });
}

function renderCtgovReceipt(snapshot, mode) {
  const target = document.getElementById("ctgov-result");
  const rows = mode === "search" ? ctgovStudyRows(snapshot) : [];
  const title = mode === "search"
    ? `${rows.length} registry result${rows.length === 1 ? "" : "s"} captured`
    : canonicalNctId(snapshot.request && snapshot.request.nct_id);
  target.replaceChildren(
    text("p", "INTAKE RECEIPT", "kicker"),
    text("h4", title),
    text(
      "p",
      `Raw source SHA-256 ${snapshot.raw_content_sha256} · ${format(snapshot.raw_content_bytes, 0)} bytes · human review required. No score or family projection was emitted.`
    )
  );
  const receipt = document.createElement("dl");
  receipt.className = "receipt-grid compact-receipt";
  [
    ["Intake ID", snapshot.intake_id],
    ["Source", snapshot.source_uri],
    ["Retrieved", snapshot.retrieved_at],
    ["Promotion", snapshot.promotion_state],
    ["Score eligible", snapshot.score_eligible ? "Yes" : "No"],
    ["Open review fields", Array.isArray(snapshot.unresolved_fields) ? snapshot.unresolved_fields.length : 0]
  ].forEach(([label, value]) => receipt.append(text("dt", label), text("dd", value)));
  target.append(receipt);
  if (rows.length) {
    const list = document.createElement("ol");
    list.className = "registry-study-list";
    rows.forEach(row => {
      const item = document.createElement("li");
      item.className = "registry-study-row";
      item.append(
        text("strong", row.nct_id || "NCT ID unavailable"),
        text(
          "span",
          [row.title, row.status && humanize(row.status), row.phases, row.enrollment !== null && `${format(row.enrollment, 0)} enrolled`]
            .filter(Boolean)
            .join(" · ")
        )
      );
      const button = text("button", "Use exact NCT ID", "secondary");
      button.type = "button";
      button.disabled = !row.nct_id;
      button.addEventListener("click", () => {
        document.getElementById("ctgov-nct-id").value = row.nct_id || "";
        document.getElementById("ctgov-nct-id").focus();
        setStatus("ctgov-intake-status", `${row.nct_id} selected. Lock its exact registry response before review.`);
      });
      item.append(button);
      list.append(item);
    });
    target.append(list);
  }
}

async function submitCtgovSearch(event) {
  event.preventDefault();
  setStatus("ctgov-search-status", "Capturing one exact ClinicalTrials.gov result page…");
  try {
    const query = document.getElementById("ctgov-query").value.trim();
    if (!query) throw new Error("Search query is required");
    const pageSize = positiveInteger(document.getElementById("ctgov-page-size").value, "Result count");
    if (pageSize > 100) throw new Error("Result count must be at most 100");
    const pageToken = document.getElementById("ctgov-page-token").value.trim();
    const response = await fetch("/api/intake/ctgov-search", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({query, page_size: pageSize, page_token: pageToken || null})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    ctgovSearchSnapshot = result;
    renderCtgovReceipt(result, "search");
    const nextToken = result.parsed_content && result.parsed_content.nextPageToken;
    if (typeof nextToken === "string") document.getElementById("ctgov-page-token").value = nextToken;
    document.getElementById("download-ctgov-search").hidden = false;
    setStatus("ctgov-search-status", `Captured ${ctgovStudyRows(result).length} source record${ctgovStudyRows(result).length === 1 ? "" : "s"} · no scoring`);
  } catch (error) {
    setStatus("ctgov-search-status", `Registry search stopped: ${error.message}`, true);
  }
}

async function submitCtgovStudy(event) {
  event.preventDefault();
  setStatus("ctgov-intake-status", "Locking the exact ClinicalTrials.gov study response…");
  try {
    const nctId = canonicalNctId(document.getElementById("ctgov-nct-id").value);
    const response = await fetch("/api/intake/ctgov", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({nct_id: nctId})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    ctgovStudySnapshot = result;
    renderCtgovReceipt(result, "study");
    document.getElementById("download-ctgov-study").hidden = false;
    setStatus("ctgov-intake-status", `${nctId} source locked · human field review still required`);
  } catch (error) {
    setStatus("ctgov-intake-status", `Registry intake stopped: ${error.message}`, true);
  }
}

function setControlledValue(select) {
  const controlled = document.getElementById(select.dataset.controls);
  if (!controlled) return;
  const unknown = select.value === "unknown";
  controlled.disabled = unknown;
  controlled.required = !unknown;
  if (unknown) controlled.value = "";
}

function addModule(values = {}) {
  moduleSerial += 1;
  const fragment = document.getElementById("module-template").content.cloneNode(true);
  const card = fragment.querySelector(".module-card");
  const title = card.querySelector("h3");
  title.textContent = `Measurement module ${moduleSerial}`;
  const defaults = {
    module_id: `module-${moduleSerial}`,
    label: "Measurement module",
    evidence_state: "unknown",
    events_per_participant: null,
    ...values
  };
  card.querySelectorAll("[data-module-field]").forEach(control => {
    control.value = defaults[control.dataset.moduleField] ?? "";
  });
  const initialEvents = card.querySelector('[data-module-field="events_per_participant"]');
  initialEvents.disabled = defaults.evidence_state === "unknown";
  card.querySelector(".remove-module").addEventListener("click", () => card.remove());
  card.querySelector("[data-module-state]").addEventListener("change", event => {
    const events = card.querySelector('[data-module-field="events_per_participant"]');
    const unknown = event.target.value === "unknown";
    events.disabled = unknown;
    if (unknown) events.value = "";
  });
  document.getElementById("measurement-modules").append(fragment);
}

function readDesignForm(form) {
  const data = new FormData(form);
  const modules = [...document.querySelectorAll(".module-card")].map(card => {
    const module = {};
    card.querySelectorAll("[data-module-field]").forEach(control => {
      module[control.dataset.moduleField] = control.value;
    });
    return module;
  });
  return buildDesignPayload({
    ...Object.fromEntries(data.entries()),
    measurement_modules: modules
  });
}

function renderCoordinates(result) {
  const rows = flattenAssessmentCoordinates(result);
  const target = document.getElementById("design-coordinates");
  target.replaceChildren();
  rows.forEach(coordinate => {
    const card = document.createElement("article");
    card.className = "coordinate-card";
    const head = document.createElement("div");
    head.className = "coordinate-head";
    head.append(text("h4", coordinate.label), text("span", humanize(coordinate.state), `state state-${coordinate.state}`));
    card.append(head, text("strong", displayValue(coordinate.value, coordinate.unit), "coordinate-value"));
    if (coordinate.semantics) card.append(text("p", coordinate.semantics));
    if (coordinate.source) card.append(text("small", `Source: ${coordinate.source}`));
    target.append(card);
  });
  document.getElementById("coordinate-count").textContent = `${rows.length} coordinates`;
  if (!rows.length) target.append(text("p", "No coordinates were returned.", "empty-inline"));
}

function renderGates(openGates) {
  const rows = normalizeGates(openGates);
  const target = document.getElementById("design-gates");
  target.replaceChildren();
  rows.forEach(gate => {
    const item = document.createElement("li");
    item.append(text("strong", gate.title));
    if (gate.reason) item.append(text("p", gate.reason));
    if (gate.nextAction) item.append(text("small", `Next: ${gate.nextAction}`));
    target.append(item);
  });
  document.getElementById("gate-count").textContent = rows.length ? `${rows.length} unresolved` : "None returned";
  if (!rows.length) target.append(text("li", "No open gates were returned for this candidate receipt.", "empty-inline"));
}

function renderUpgrades(upgrades) {
  const groups = groupUpgrades(upgrades);
  const target = document.getElementById("design-upgrades");
  target.replaceChildren();
  Object.entries(groups).forEach(([group, rows]) => {
    const section = document.createElement("section");
    section.className = "upgrade-group";
    section.append(text("h4", humanize(group)));
    const list = document.createElement("ol");
    list.className = "advice-list upgrades";
    rows.forEach(upgrade => {
      const item = document.createElement("li");
      item.append(text("strong", upgrade.title));
      if (upgrade.rationale) item.append(text("p", upgrade.rationale));
      if (upgrade.action) item.append(text("small", `Change: ${upgrade.action}`));
      list.append(item);
    });
    section.append(list);
    target.append(section);
  });
  const count = normalizeUpgrades(upgrades).length;
  document.getElementById("upgrade-count").textContent = count ? `${count} suggestions` : "None returned";
  if (!count) target.append(text("p", "No structural upgrades were returned.", "empty-inline"));
}

function renderDesign(result) {
  compiledDesign = result;
  document.getElementById("design-result-empty").hidden = true;
  document.getElementById("design-result-content").hidden = false;
  document.getElementById("design-claim-badge").textContent = humanize(result.claim_state || "candidate");
  document.getElementById("design-boundary").textContent = result.promotion_allowed
    ? "This receipt reports an allowed promotion state under its bound contract."
    : "Candidate receipt only. Public score, rank, benchmark promotion, and biological completion claims are not allowed.";
  const receipt = document.getElementById("design-receipt");
  receipt.replaceChildren();
  const lane = result.assessment_lane && typeof result.assessment_lane === "object"
    ? result.assessment_lane.value
    : result.assessment_lane;
  const emission = result.emission_policy || {};
  [
    ["Claim state", result.claim_state || "candidate"],
    ["Evidence lane", lane || "Not returned"],
    ["Promotion allowed", result.promotion_allowed === true ? "Yes" : "No"],
    ["Input SHA-256", result.input_sha256 || "Not returned"],
    ["Overall score / rank", emission.composite_coordinate_emitted === false && emission.ordinal_position_emitted === false ? "Not emitted" : "Contract not returned"],
    ["Missing-value imputation", emission.missing_value_imputation_used === false ? "Not used" : "Contract not returned"]
  ].forEach(([label, value]) => receipt.append(text("dt", label), text("dd", value)));
  renderCoordinates(result);
  renderGates(result.open_gates);
  renderUpgrades(result.structural_multiobjective_design_upgrades || result.upgrades);
  renderDesignFamilyReadiness();
}

async function submitDesign(event) {
  event.preventDefault();
  setStatus("design-status", "Compiling typed trial structure…");
  try {
    const payload = readDesignForm(event.currentTarget);
    const response = await fetch("/api/v2/design", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    renderDesign(result);
    setStatus("design-status", `Compiled candidate receipt · ${(result.input_sha256 || "unhashed").slice(0, 19)}`);
    document.getElementById("design-result-content").focus({preventScroll: true});
  } catch (error) {
    setStatus("design-status", `Compilation stopped: ${error.message}`, true);
  }
}

function renderEnvelopeValue(envelope) {
  if (!envelope || typeof envelope !== "object") return "Not resolved";
  if (envelope.minimum === null || envelope.minimum === undefined ||
      envelope.maximum === null || envelope.maximum === undefined) return "Not resolved";
  const minimum = Number(envelope.minimum);
  const maximum = Number(envelope.maximum);
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) return "Not resolved";
  return minimum === maximum ? format(minimum) : `${format(minimum)} – ${format(maximum)}`;
}

function metricPresentation(path) {
  const registered = METRIC_UI[path];
  const transportFamily = path.match(
    /^transport\.axis_families\.([A-Za-z0-9][A-Za-z0-9_:-]{1,127})\.(transport_rank|transport_allocation_support_factor)$/
  );
  if (transportFamily) {
    const familyLabel = humanize(transportFamily[1]);
    return transportFamily[2] === "transport_rank"
      ? {label: `${familyLabel} · independent contrasts`, unit: "directions"}
      : {label: `${familyLabel} · allocation-support proxy`, unit: "support factor"};
  }
  return registered
    ? {label: registered[0], unit: registered[1]}
    : {label: humanize(path.split(".").slice(1).join("_")), unit: "declared units"};
}

function buildFamilyMap(result) {
  const envelopes = result && result.family_envelopes && typeof result.family_envelopes === "object"
    ? result.family_envelopes
    : {};
  return FAMILY_UI.map(family => {
    const familyEntries = Object.entries(envelopes)
      .filter(([path]) => path.startsWith(`${family.id}.`));
    const hasTransportAxisFamilies = family.id === "transport" && familyEntries.some(
      ([path]) => path.startsWith("transport.axis_families.")
    );
    const metrics = familyEntries
      .filter(([path]) => !hasTransportAxisFamilies || ![
        "transport.transport_rank",
        "transport.transport_allocation_support_factor"
      ].includes(path))
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([path, envelope]) => ({path, ...metricPresentation(path), envelope}));
    const resolutionStates = [...new Set(
      (Array.isArray(result && result.scenarios) ? result.scenarios : [])
        .map(scenario => scenario && scenario.families && scenario.families[family.id])
        .filter(value => value && typeof value === "object")
        .map(value => value.resolution_state)
        .filter(value => typeof value === "string" && value)
    )].sort();
    const unresolvedMetricPaths = metrics
      .filter(metric => finiteEnvelope(metric.envelope) === null)
      .map(metric => metric.path);
    const allScenarioStatesResolved = resolutionStates.length > 0 &&
      resolutionStates.every(state => ["resolved", "resolved_axis_family_vector"].includes(state));
    const allScenarioStatesUnresolved = resolutionStates.length > 0 &&
      resolutionStates.every(state =>
        state.startsWith("unresolved") ||
        state.includes("no_eligible") ||
        state.includes("not_available")
      );
    const state = !metrics.length && !resolutionStates.length
      ? "unknown"
      : !metrics.length || unresolvedMetricPaths.length === metrics.length || allScenarioStatesUnresolved
        ? "unresolved"
        : unresolvedMetricPaths.length || !allScenarioStatesResolved
          ? "partial"
          : "resolved";
    return {
      family_id: family.id,
      label: family.label,
      question: family.question,
      state,
      resolution_states: resolutionStates,
      unresolved_metric_paths: unresolvedMetricPaths,
      metrics
    };
  });
}

function buildDesignHandoffReceipt(result) {
  const lane = result && result.assessment_lane && typeof result.assessment_lane === "object"
    ? result.assessment_lane.value
    : result && result.assessment_lane;
  return {
    schema_version: "anibench.studio-design-handoff.v1",
    claim_class: "typed_design_structure_to_protocol_geometry_handoff",
    study_id: result && result.study ? result.study.study_id : null,
    design_input_sha256: result ? result.input_sha256 || null : null,
    assessment_lane: lane || null,
    design_assessment: result,
    family_readiness: FAMILY_UI.map(family => ({
      family_id: family.id,
      state: "requires_explicit_protocol_geometry",
      required_input_groups: [...family.requirements]
    })),
    next_compiler: {
      endpoint: "/api/v2/protocol-capacity",
      input_contract: "anibench.protocol-capacity-input.v2"
    },
    no_inference_policy: {
      matrices_inferred_from_module_names: false,
      missing_geometry_imputed: false,
      menu_counts_converted_to_information: false
    },
    overall_scalar: null,
    public_rank_emission_permitted: false
  };
}

function finiteEnvelope(envelope) {
  if (!envelope || typeof envelope !== "object") return null;
  if (envelope.minimum === null || envelope.minimum === undefined ||
      envelope.maximum === null || envelope.maximum === undefined) return null;
  const minimum = Number(envelope.minimum);
  const maximum = Number(envelope.maximum);
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum > maximum) return null;
  return {minimum, maximum};
}

function classifyParetoRelation(candidateEnvelopes, comparatorEnvelopes) {
  const candidatePaths = Object.keys(candidateEnvelopes || {}).sort();
  const comparatorPaths = Object.keys(comparatorEnvelopes || {}).sort();
  if (!candidatePaths.length || candidatePaths.length !== comparatorPaths.length ||
      candidatePaths.some((path, index) => path !== comparatorPaths[index])) {
    return {state: "unknown", reason: "metric_path_mismatch", metric_paths: []};
  }
  const pairs = candidatePaths.map(path => ({
    path,
    candidate: finiteEnvelope(candidateEnvelopes[path]),
    comparator: finiteEnvelope(comparatorEnvelopes[path])
  }));
  if (pairs.some(pair => !pair.candidate || !pair.comparator)) {
    return {state: "unknown", reason: "invalid_or_missing_envelope", metric_paths: candidatePaths};
  }
  const equivalent = pairs.every(pair =>
    pair.candidate.minimum === pair.candidate.maximum &&
    pair.comparator.minimum === pair.comparator.maximum &&
    pair.candidate.minimum === pair.comparator.minimum
  );
  if (equivalent) {
    return {state: "pareto_equivalent", reason: "identical_exact_envelopes", metric_paths: candidatePaths};
  }
  const candidateNoWorse = pairs.every(pair => pair.candidate.minimum >= pair.comparator.maximum);
  const candidateStrict = pairs.some(pair => pair.candidate.minimum > pair.comparator.maximum);
  const comparatorNoWorse = pairs.every(pair => pair.comparator.minimum >= pair.candidate.maximum);
  const comparatorStrict = pairs.some(pair => pair.comparator.minimum > pair.candidate.maximum);
  if (candidateNoWorse && candidateStrict) {
    return {state: "candidate_pareto_dominates", reason: "separated_envelopes", metric_paths: candidatePaths};
  }
  if (comparatorNoWorse && comparatorStrict) {
    return {state: "comparator_pareto_dominates", reason: "separated_envelopes", metric_paths: candidatePaths};
  }
  const overlap = pairs.some(pair =>
    pair.candidate.minimum <= pair.comparator.maximum &&
    pair.comparator.minimum <= pair.candidate.maximum
  );
  return overlap
    ? {state: "indeterminate_interval_overlap", reason: "scenario_envelopes_overlap", metric_paths: candidatePaths}
    : {state: "pareto_incomparable", reason: "tradeoff_across_noninterchangeable_metrics", metric_paths: candidatePaths};
}

function deriveComparatorPlacement(result, atlas) {
  const atlasBinding = atlas && atlas.coordinate_table ? atlas.coordinate_table.sha256 : null;
  const receipt = {
    schema_version: "anibench.studio-comparator-placement.v1",
    protocol_sha256: result ? result.protocol_sha256 || null : null,
    comparator_atlas_sha256: atlasBinding,
    relation_semantics: "pareto_only_no_scalar_no_ordinal_rank",
    overall_scalar: null,
    public_rank_emission_permitted: false,
    relations: []
  };
  if (!result || result.comparison_eligible !== true) {
    return {...receipt, state: "not_comparable_protocol_authority_hold", reason: "protocol_comparison_eligible_false"};
  }
  const basis = result.comparison_basis_sha256;
  if (typeof basis !== "string" || !basis) {
    return {...receipt, state: "not_comparable_missing_shared_basis", reason: "protocol_comparison_basis_missing"};
  }
  const eligible = (atlas && Array.isArray(atlas.studies) ? atlas.studies : []).filter(study =>
    study.comparison_eligible === true &&
    study.comparison_basis_sha256 === basis &&
    study.family_envelopes && typeof study.family_envelopes === "object"
  );
  if (!eligible.length) {
    return {...receipt, state: "not_comparable_no_source_complete_comparator_geometry", reason: "no_eligible_comparator_on_shared_basis"};
  }
  const relations = eligible.map(study => ({
    study_id: study.study_id,
    comparison_basis_sha256: basis,
    ...classifyParetoRelation(result.family_envelopes, study.family_envelopes)
  }));
  return {...receipt, state: "pareto_relations_computed", reason: "shared_source_bound_basis", relations};
}

function designGeometrySourcePointers(design) {
  const pointers = new Set();
  if (design && design.study && design.study.study_id) pointers.add("/study_id");
  const visit = value => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== "object") return;
    if (Array.isArray(value.source_json_pointers)) {
      value.source_json_pointers.forEach(pointer => {
        if (typeof pointer === "string" && pointer.startsWith("/")) pointers.add(pointer);
      });
    }
    Object.values(value).forEach(visit);
  };
  visit(design && design.coordinates);
  return [...pointers].sort();
}

function deriveDesignProtocolBinding(result, design, crosswalk = null) {
  const designId = design && design.study ? design.study.study_id : null;
  const capacityId = result ? result.protocol_id || null : null;
  const requiredPointers = designGeometrySourcePointers(design);
  const base = {
    design_study_id: designId,
    protocol_id: capacityId,
    design_input_sha256: design ? design.input_sha256 || null : null,
    protocol_sha256: result ? result.protocol_sha256 || null : null,
    required_design_geometry_pointers: requiredPointers
  };
  if (!designId) {
    return {...base, state: "no_compact_design_in_session", reason: "no_design_assessment_available"};
  }
  if (!capacityId || designId !== capacityId) {
    return {
      ...base,
      state: "not_bound_study_identifier_mismatch",
      reason: "design_and_protocol_identifiers_do_not_match"
    };
  }

  const bindings = crosswalk && Array.isArray(crosswalk.pointer_bindings)
    ? crosswalk.pointer_bindings
    : [];
  const pointerCounts = new Map();
  bindings.forEach(binding => {
    const pointer = binding && binding.design_source_json_pointer;
    if (typeof pointer === "string") pointerCounts.set(pointer, (pointerCounts.get(pointer) || 0) + 1);
  });
  const missingPointers = requiredPointers.filter(pointer => pointerCounts.get(pointer) !== 1);
  const malformedBindings = bindings.filter(binding =>
    !binding ||
    typeof binding.design_source_json_pointer !== "string" ||
    !binding.design_source_json_pointer.startsWith("/") ||
    !Array.isArray(binding.protocol_source_json_pointers) ||
    !binding.protocol_source_json_pointers.length ||
    binding.protocol_source_json_pointers.some(pointer => typeof pointer !== "string" || !pointer.startsWith("/")) ||
    !/^sha256:[0-9a-f]{64}$/.test(binding.binding_content_sha256 || "")
  );
  const hashAndContractValid = Boolean(
    crosswalk &&
    crosswalk.schema_version === "anibench.design-protocol-crosswalk.v1" &&
    /^sha256:[0-9a-f]{64}$/.test(crosswalk.crosswalk_sha256 || "") &&
    crosswalk.design_input_sha256 === base.design_input_sha256 &&
    crosswalk.protocol_sha256 === base.protocol_sha256
  );
  if (hashAndContractValid && !missingPointers.length && !malformedBindings.length) {
    return {
      ...base,
      state: "bound_by_content_hashed_pointer_crosswalk",
      reason: "crosswalk_hashes_match_and_all_required_design_geometry_pointers_are_covered_once",
      crosswalk_sha256: crosswalk.crosswalk_sha256,
      pointer_binding_count: bindings.length,
      missing_design_geometry_pointers: []
    };
  }
  return {
    ...base,
    state: "identifier_match_only_not_semantic_binding",
    reason: crosswalk
      ? "crosswalk_invalid_or_incomplete"
      : "matching_identifier_without_content_hashed_pointer_crosswalk",
    crosswalk_sha256: crosswalk && crosswalk.crosswalk_sha256 || null,
    pointer_binding_count: bindings.length,
    missing_design_geometry_pointers: missingPointers,
    malformed_pointer_binding_count: malformedBindings.length
  };
}

function buildStudioWorkflowReceipt(result, atlas, design, crosswalk = null) {
  const capacityId = result ? result.protocol_id || null : null;
  return {
    schema_version: "anibench.studio-workflow-receipt.v1",
    claim_class: "prospective_protocol_capacity_with_source_bound_placement",
    protocol_id: capacityId,
    protocol_sha256: result ? result.protocol_sha256 || null : null,
    design_binding: deriveDesignProtocolBinding(result, design, crosswalk),
    capacity_result: result,
    family_map: buildFamilyMap(result),
    comparator_atlas_binding: atlas && atlas.coordinate_table ? {
      schema_version: atlas.schema_version,
      coordinate_table_sha256: atlas.coordinate_table.sha256,
      study_count: atlas.study_count,
      comparison_eligible_study_count: atlas.comparison_eligible_study_count,
      row_order_semantics: atlas.row_order_semantics
    } : null,
    comparator_placement: deriveComparatorPlacement(result, atlas),
    overall_scalar: null,
    public_rank_emission_permitted: false
  };
}

function renderDesignFamilyReadiness() {
  const target = document.getElementById("design-family-readiness");
  target.replaceChildren();
  FAMILY_UI.forEach(family => {
    const card = document.createElement("article");
    card.className = `family-readiness-card family-${family.id}`;
    card.append(
      text("strong", family.label),
      text("span", "Geometry required", "family-state family-state-required"),
      text("p", family.requirements.join(" · "))
    );
    target.append(card);
  });
}

function renderFamilyMap(result) {
  const section = document.createElement("section");
  section.className = "capacity-block";
  const head = document.createElement("div");
  head.className = "block-title";
  head.append(text("h4", "Six-family biological-learning map"), text("span", "No family averaging"));
  section.append(head);
  const map = document.createElement("div");
  map.className = "capacity-family-map";
  buildFamilyMap(result).forEach(family => {
    const card = document.createElement("article");
    card.className = `capacity-family-card family-${family.family_id}`;
    const title = document.createElement("div");
    title.className = "capacity-family-head";
    title.append(text("h5", family.label), text("span", humanize(family.state), `family-state family-state-${family.state}`));
    card.append(title, text("p", family.question));
    if (family.state === "partial" || family.state === "unresolved") {
      const states = family.resolution_states.length
        ? family.resolution_states.map(humanize).join(" · ")
        : "No resolved family geometry";
      const unresolved = family.unresolved_metric_paths.length
        ? ` Unresolved metrics: ${family.unresolved_metric_paths.map(path => metricPresentation(path).label).join(", ")}.`
        : "";
      card.append(text("p", `Compiler state: ${states}.${unresolved}`, "family-resolution-note"));
    }
    const metrics = document.createElement("dl");
    metrics.className = "family-metric-list";
    family.metrics.forEach(metric => {
      metrics.append(
        text("dt", metric.label),
        text("dd", `${renderEnvelopeValue(metric.envelope)} ${metric.unit}`.trim())
      );
    });
    if (!family.metrics.length) metrics.append(text("dt", "State"), text("dd", "Not resolved"));
    card.append(metrics);
    map.append(card);
  });
  section.append(map);
  return section;
}

function renderComparatorPlacement(result, atlas) {
  const placement = deriveComparatorPlacement(result, atlas);
  const section = document.createElement("section");
  section.className = "capacity-block comparator-block";
  const head = document.createElement("div");
  head.className = "block-title";
  head.append(text("h4", "Source-bound comparator placement"), text("span", "Pareto only"));
  section.append(head);
  const summary = document.createElement("div");
  summary.className = "comparator-summary";
  const studyCount = atlas && Number.isInteger(atlas.study_count) ? atlas.study_count : null;
  const eligibleCount = atlas && Number.isInteger(atlas.comparison_eligible_study_count)
    ? atlas.comparison_eligible_study_count
    : null;
  summary.append(
    text("strong", humanize(placement.state)),
    text("p", placement.state === "not_comparable_protocol_authority_hold"
      ? "This protocol compiled, but its custom authority is not eligible for cross-study comparison. No position was inferred."
      : placement.state === "not_comparable_no_source_complete_comparator_geometry"
        ? "The public atlas has no comparator with complete geometry on the same verified basis. Placement remains typed unknown."
        : placement.state === "pareto_relations_computed"
          ? `${placement.relations.length} source-complete Pareto relation${placement.relations.length === 1 ? "" : "s"} computed on the shared basis.`
          : "Placement remains unresolved until protocol and comparator geometry share an exact verified basis."),
    text("span", studyCount === null
      ? "Comparator atlas unavailable"
      : `${studyCount} source-bound external studies · ${eligibleCount} comparison-complete`, "comparator-count")
  );
  section.append(summary);
  if (atlas && Array.isArray(atlas.studies)) {
    const details = document.createElement("details");
    details.className = "comparator-ledger";
    const summaryNode = document.createElement("summary");
    summaryNode.textContent = "Inspect external source ledger";
    details.append(summaryNode);
    const wrapper = document.createElement("div");
    wrapper.className = "data-table-wrap";
    const table = document.createElement("table");
    table.className = "data-table comparator-table";
    const caption = document.createElement("caption");
    caption.textContent = "Source order is not a rank. Population and duration retain their declared semantics; only machine-resolved executable derivations remain known, while all other candidate facts are typed unknown.";
    const thead = document.createElement("thead");
    const header = document.createElement("tr");
    ["Study", "Evidence lane", "Population", "Duration", "Field provenance", "Family coordinate state", "Projection hash"].forEach(label => header.append(text("th", label)));
    thead.append(header);
    const tbody = document.createElement("tbody");
    atlas.studies.forEach(study => {
      const row = document.createElement("tr");
      const projectionHash = study.source_binding && study.source_binding.source_projection_sha256
        ? study.source_binding.source_projection_sha256
        : "Not returned";
      const familyStates = Object.values(study.family_eligibility || {}).map(item => item.state);
      const uniqueStates = [...new Set(familyStates)];
      const provenance = study.source_binding && study.source_binding.field_provenance
        ? study.source_binding.field_provenance
        : {};
      [
        study.name || study.study_id,
        humanize(study.projection_lane),
        displayValue(study.population && study.population.value, study.population && study.population.unit),
        displayValue(study.duration && study.duration.value, study.duration && study.duration.unit),
        `${provenance.mechanically_extracted_source_bound ?? "?"} machine-known / ${provenance.downgraded_unknown_fact_count ?? "?"} downgraded unknown`,
        uniqueStates.length === 1 ? humanize(uniqueStates[0]) : "Mixed typed states",
        projectionHash.slice(0, 19)
      ].forEach(value => row.append(text("td", value)));
      tbody.append(row);
    });
    table.append(caption, thead, tbody);
    wrapper.append(table);
    details.append(wrapper);
    section.append(details);
  }
  const receipt = document.createElement("dl");
  receipt.className = "receipt-grid compact-receipt";
  [
    ["Placement state", placement.state],
    ["Placement reason", placement.reason],
    ["Atlas SHA-256", placement.comparator_atlas_sha256 || "Not available"],
    ["Field receipt SHA-256", atlas && atlas.field_provenance_receipt ? atlas.field_provenance_receipt.sha256 : "Not available"],
    ["Field evidence", atlas && atlas.field_provenance_receipt ? `${atlas.field_provenance_receipt.mechanically_extracted_fact_count} machine-known / ${atlas.field_provenance_receipt.downgraded_unknown_fact_count} downgraded unknown` : "Not available"],
    ["Overall score", "Not emitted"],
    ["Ordinal rank", "Not emitted"]
  ].forEach(([label, value]) => receipt.append(text("dt", label), text("dd", value)));
  section.append(receipt);
  return section;
}

function renderCapacity(result, atlas = comparatorAtlas) {
  capacityPacket = buildStudioWorkflowReceipt(result, atlas, compiledDesign);
  const target = document.getElementById("capacity-result");
  target.replaceChildren(
    text("p", "FAMILY RECEIPT", "kicker"),
    text("h3", humanize(result.protocol_id || "Compiled protocol")),
    text(
      "p",
      result.comparison_eligible
        ? "The bound authority permits comparison for this receipt."
        : "This candidate is compiled and replayable, but its current authority does not permit a public rank.",
      "block-explainer"
    )
  );
  target.append(renderFamilyMap(result), renderComparatorPlacement(result, atlas));
  const receipt = document.createElement("dl");
  receipt.className = "receipt-grid";
  [
    ["Protocol SHA-256", result.protocol_sha256],
    ["Scenarios", result.scenario_count],
    ["Ontology binding", result.ontology_binding_state],
    ["Overall scalar", result.overall_scalar === null ? "Not emitted" : result.overall_scalar],
    ["Public rank", result.public_rank_emission_permitted ? "Permitted" : "Not permitted"]
  ].forEach(([label, value]) => receipt.append(text("dt", label), text("dd", value)));
  target.append(receipt);
  const button = text("button", "Download complete workflow receipt", "secondary receipt-action");
  button.type = "button";
  button.addEventListener("click", () => downloadJson(capacityPacket, "anibench-v2-studio-workflow", result.protocol_sha256));
  target.append(button);
}

function level1FamilyMetricRows(family) {
  return family.native_metrics || [];
}

function formatNativeMetric(metric) {
  if (metric.value === null || metric.value === undefined) return "Unknown";
  if (typeof metric.value === "boolean") return metric.value ? "Yes" : "No";
  return `${format(metric.value, 3)} · ${humanize(metric.unit)}`;
}

function renderLevel1Assessment(receipt) {
  level1AssessmentPacket = receipt;
  const target = document.getElementById("capacity-result");
  target.replaceChildren(
    text("p", "ROLE-AWARE TRIAL RECEIPT", "kicker"),
    text("h3", humanize(receipt.protocol_id)),
    text(
      "p",
      "The protocol is compiled into six independent dimensions. Every displayed number is a native compiler output with an exact receipt locator. Level-1 normalization is withheld until its family-specific targets are source-bound; unknown is not zero.",
      "block-explainer"
    )
  );
  receipt.scenarios.forEach((scenario, scenarioIndex) => {
      const section = document.createElement("section");
      section.className = "capacity-block";
      const head = document.createElement("div");
      head.className = "block-title";
      head.append(
        text("h4", `Scenario ${scenarioIndex + 1}: ${humanize(scenario.scenario_id)}`),
        text("span", "six noncompensatory dimensions")
      );
      section.append(head);
      const map = document.createElement("div");
      map.className = "capacity-family-map";
      scenario.families.forEach(family => {
        const card = document.createElement("article");
        card.className = `level1-family-card family-${family.family_id}`;
        card.append(
          text("h5", family.label),
          text("p", `Design geometry: ${humanize(family.design_resolution_state)}`, "level1-hold")
        );
        level1FamilyMetricRows(family).forEach(metric => {
          const row = document.createElement("div");
          row.className = "level1-metric";
          const headRow = document.createElement("div");
          headRow.className = "level1-metric-head";
          headRow.append(text("strong", metric.label), text("span", formatNativeMetric(metric)));
          row.append(headRow);
          row.append(text("p", `Receipt locator ${metric.source_locator}`, "level1-hold"));
          card.append(row);
        });
        card.append(text(
          "p",
          `Level-1 target: unresolved · ${family.level1_target_attainment.required_gate_ids.length} source gate${family.level1_target_attainment.required_gate_ids.length === 1 ? "" : "s"}`,
          "level1-assumption-badge"
        ));
        map.append(card);
      });
      section.append(map);
      target.append(section);
  });
  const authority = document.createElement("dl");
  authority.className = "receipt-grid level1-authority";
  [
    ["Protocol capacity SHA-256", receipt.protocol_capacity_result_sha256],
    ["Level-1 authority SHA-256", receipt.level1_authority.authority_raw_sha256],
    ["Level-1 target state", humanize(receipt.level1_authority.global_enrollment_state)],
    ["Assessment SHA-256", receipt.assessment_receipt_sha256],
    ["Overall scalar", "Not emitted"],
    ["Public rank", "Not emitted"]
  ].forEach(([label, value]) => authority.append(text("dt", label), text("dd", value)));
  target.append(authority);
  const button = text("button", "Download deterministic Level-1 receipt", "secondary receipt-action");
  button.type = "button";
  button.addEventListener("click", () => downloadJson(
    level1AssessmentPacket,
    "anibench-v2-level1-assessment",
    receipt.assessment_receipt_sha256
  ));
  target.append(button);
}

async function submitLevel1Assessment() {
  setStatus("capacity-status", "Compiling six independent trial dimensions…");
  try {
    const rawPayload = document.getElementById("capacity-input").value;
    validateJsonText(rawPayload);
    const response = await fetch("/api/v2/level1-assessment", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      // Submit the exact editor bytes so the input hash and downloadable
      // receipt bind what the user saw. Basis comparison separately follows
      // JSON-number semantics, where finite 1 and 1.0 are equivalent.
      body: rawPayload
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    renderLevel1Assessment(result);
    setStatus(
      "capacity-status",
      `Compiled ${result.scenarios.length} scenario${result.scenarios.length === 1 ? "" : "s"} across six dimensions · target normalization remains source-gated`
    );
  } catch (error) {
    setStatus("capacity-status", `Level-1 assessment stopped: ${error.message}`, true);
  }
}

async function submitCapacity(event) {
  event.preventDefault();
  setStatus("capacity-status", "Compiling protocol geometry through every family…");
  try {
    const rawPayload = document.getElementById("capacity-input").value;
    JSON.parse(rawPayload);
    const response = await fetch("/api/v2/protocol-capacity", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: rawPayload
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    let atlas = comparatorAtlas;
    if (!atlas) {
      try {
        atlas = await loadComparatorAtlas();
      } catch (error) {
        atlas = {
          schema_version: "anibench.studio-comparator-atlas-unavailable.v1",
          placement_state: "typed_unknown_comparator_atlas_unavailable",
          error: error.message,
          studies: []
        };
      }
    }
    renderCapacity(result, atlas);
    setStatus("capacity-status", `Compiled ${result.scenario_count} scenario${result.scenario_count === 1 ? "" : "s"} · no overall scalar`);
  } catch (error) {
    setStatus("capacity-status", `Compilation stopped: ${error.message}`, true);
  }
}

function renderOptimizer(result) {
  optimizerPacket = result;
  const target = document.getElementById("protocol-optimizer-result");
  target.replaceChildren(
    text("p", "PARETO RECEIPT", "kicker"),
    text("h3", `${result.feasible_candidate_count} feasible of ${result.candidate_count}`),
    text(
      "p",
      `Pareto frontier: ${(result.pareto_frontier_candidate_ids || []).join(", ") || "none"}. Every candidate was recompiled from protocol geometry.`,
      "block-explainer"
    )
  );
  const grid = document.createElement("div");
  grid.className = "family-receipt-grid";
  (result.candidates || []).forEach(candidate => {
    const card = document.createElement("article");
    card.className = "family-receipt-card";
    const frontier = (result.pareto_frontier_candidate_ids || []).includes(candidate.candidate_id);
    card.append(
      text("span", frontier ? "Sandbox frontier" : candidate.constraint_eligible ? "Feasible candidate" : "Resource-ineligible"),
      text("strong", humanize(candidate.candidate_id))
    );
    (candidate.objective_values || []).forEach(objective => {
      card.append(text("span", `${humanize(objective.objective_id)} · ${format(objective.value)}`));
    });
    (candidate.resource_totals || []).forEach(resource => {
      card.append(text("span", `${humanize(resource.resource_id)} · ${format(resource.total_amount)} ${resource.unit}`));
    });
    card.append(text("span", candidate.comparison_eligible ? "Comparison eligible" : "Comparison hold · custom authority"));
    grid.append(card);
  });
  target.append(grid);
  const receipt = document.createElement("dl");
  receipt.className = "receipt-grid";
  [
    ["Request SHA-256", result.optimizer_request_sha256],
    ["Overall scalar", result.overall_scalar === null ? "Not emitted" : result.overall_scalar],
    ["Stable rank", result.public_rank_emission_permitted ? "Permitted" : "Not emitted"],
    ["Candidate compilation", result.anti_gaming_contract && result.anti_gaming_contract.all_candidates_recompiled_from_protocol_geometry ? "Recompiled from protocol" : "Not returned"],
    ["Resource sources", result.source_binding_state && result.source_binding_state.resource_constraints === "caller_declared_not_content_verified" ? "Caller-declared · not content-verified" : "Not returned"]
  ].forEach(([label, value]) => receipt.append(text("dt", label), text("dd", value)));
  target.append(receipt);
  const button = text("button", "Download Pareto receipt", "secondary receipt-action");
  button.type = "button";
  button.addEventListener("click", () => downloadJson(optimizerPacket, "anibench-v2-protocol-optimizer", result.optimizer_request_sha256));
  target.append(button);
}

async function submitProtocolOptimizer(event) {
  event.preventDefault();
  setStatus("optimizer-status", "Recompiling protocol candidates and finding the Pareto frontier…");
  try {
    const rawPayload = document.getElementById("protocol-optimizer-input").value;
    JSON.parse(rawPayload);
    const response = await fetch("/api/v2/optimize-protocol", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: rawPayload
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    renderOptimizer(result);
    setStatus("optimizer-status", `Explored ${result.candidate_count} protocol candidates · ${result.pareto_frontier_candidate_ids.length} Pareto`);
  } catch (error) {
    setStatus("optimizer-status", `Design search stopped: ${error.message}`, true);
  }
}

async function loadJsonExample(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.json();
}

function validateJsonText(rawPayload) {
  JSON.parse(rawPayload);
  return rawPayload;
}

async function loadJsonText(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return validateJsonText(await response.text());
}

async function loadComparatorAtlas() {
  const atlas = await loadJsonExample("/api/v2/comparator-atlas");
  if (atlas.schema_version !== "anibench.studio-comparator-atlas.v1") {
    throw new Error("Comparator atlas returned an unexpected contract");
  }
  if (atlas.overall_scalar !== null || atlas.public_rank_emission_permitted !== false) {
    throw new Error("Comparator atlas violated the score-free display contract");
  }
  comparatorAtlas = atlas;
  return atlas;
}

function renderCoverage(values) {
  const target = document.getElementById("coverage");
  target.replaceChildren();
  Object.entries(values || {}).forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "coverage-row";
    const track = document.createElement("div");
    track.className = "track";
    const fill = document.createElement("i");
    fill.style.width = `${Math.max(0, Math.min(100, Number(value) * 100))}%`;
    track.append(fill);
    row.append(text("span", key.replace("q_", "≥ ")), track, text("strong", `${format(Number(value) * 100, 1)}%`));
    target.append(row);
  });
}

function renderReplay(result) {
  replayPacket = result;
  const absolute = result.absolute_mechanics;
  document.getElementById("result-empty").hidden = true;
  document.getElementById("result-content").hidden = false;
  document.getElementById("metric-absolute").textContent = format(absolute.absolute_log10_contraction);
  document.getElementById("metric-dimension").textContent = String(absolute.parameter_dimension);
  const illustrative = result.illustrative_reference_metrics;
  const illustrativeSection = document.getElementById("illustrative-reference");
  illustrativeSection.hidden = !illustrative;
  if (illustrative) {
    document.getElementById("metric-illustrative-completion").textContent = `${format(illustrative.illustrative_completion_percent, 2)}%`;
    document.getElementById("metric-illustrative-overflow").textContent = `${format(illustrative.illustrative_overflow, 3)}×`;
    renderCoverage(illustrative.illustrative_coverage_curve);
  }
  const verification = result.identity_verification || {};
  const receipt = document.getElementById("receipt");
  receipt.replaceChildren();
  [
    ["Replay state", result.claim_state],
    ["Public score/rank", "Not allowed"],
    ["Input SHA-256", result.run_input_sha256],
    ["Matrix identities", verification.matrix_hashes ? "Server verified" : "Not returned"],
    ["Reference status", verification.local_reference_registry_status || "Not returned"],
    ["Illustrative fixture", verification.recognized_illustrative_fixture ? "Exact registered fixture" : "No"]
  ].forEach(([label, value]) => receipt.append(text("dt", label), text("dd", value)));
}

async function submitReplay(event) {
  event.preventDefault();
  setStatus("v2-status", "Running explicit mechanics replay…");
  try {
    const rawPayload = document.getElementById("v2-input").value;
    JSON.parse(rawPayload);
    const response = await fetch("/api/v2/information", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: rawPayload
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    renderReplay(result);
    setStatus("v2-status", `Replay complete · ${(result.run_input_sha256 || "unhashed").slice(0, 19)}`);
  } catch (error) {
    setStatus("v2-status", `Replay stopped: ${error.message}`, true);
  }
}

function downloadJson(packet, prefix, hash) {
  if (!packet) return;
  const blob = new Blob([JSON.stringify(packet, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${prefix}-${String(hash || "candidate").replace("sha256:", "").slice(0, 12)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("ctgov-search-form").addEventListener("submit", submitCtgovSearch);
    document.getElementById("ctgov-intake-form").addEventListener("submit", submitCtgovStudy);
    document.getElementById("download-ctgov-search").addEventListener("click", () => {
      downloadJson(
        ctgovSearchSnapshot,
        "anibench-ctgov-search-snapshot",
        ctgovSearchSnapshot && ctgovSearchSnapshot.raw_content_sha256
      );
    });
    document.getElementById("download-ctgov-study").addEventListener("click", () => {
      downloadJson(
        ctgovStudySnapshot,
        "anibench-ctgov-study-snapshot",
        ctgovStudySnapshot && ctgovStudySnapshot.raw_content_sha256
      );
    });
    document.getElementById("design-form").addEventListener("submit", submitDesign);
    document.getElementById("add-module").addEventListener("click", () => addModule());
    document.querySelectorAll("select[data-controls]").forEach(select => {
      select.addEventListener("change", () => setControlledValue(select));
      setControlledValue(select);
    });
    addModule();
    document.getElementById("load-design-example").addEventListener("click", () => {
      document.getElementById("study-id").value = "illustrative-trial-not-a-benchmark";
      document.getElementById("study-name").value = "Illustrative trial form";
      document.getElementById("population-value").value = "120";
      document.getElementById("population-state").value = "conditional";
      document.getElementById("duration-value").value = "180";
      document.getElementById("duration-state").value = "conditional";
      document.getElementById("policy-arms").value = "3";
      document.getElementById("operator-families").value = "operator-a, operator-b";
      document.getElementById("randomized-policy").value = "true";
      document.getElementById("concurrent-control").value = "true";
      document.getElementById("adaptive-reassignment").value = "unknown";
      document.getElementById("within-policy-randomized").value = "unknown";
      document.getElementById("measurement-modules").replaceChildren();
      moduleSerial = 0;
      addModule({
        module_id: "molecular-panel",
        label: "Molecular panel",
        evidence_state: "conditional",
        events_per_participant: 3
      });
      addModule({
        module_id: "direct-function",
        label: "Direct functional testing",
        evidence_state: "conditional",
        events_per_participant: 4
      });
      document.querySelectorAll("select[data-controls]").forEach(setControlledValue);
      setStatus(
        "design-status",
        "Illustrative form values loaded. They are not a reference design, trial claim, or benchmark result."
      );
    });
    document.getElementById("download-design").addEventListener("click", () => {
      const handoff = compiledDesign ? buildDesignHandoffReceipt(compiledDesign) : null;
      downloadJson(handoff, "anibench-v2-design-handoff", compiledDesign && compiledDesign.input_sha256);
    });
    document.getElementById("open-capacity-lab").addEventListener("click", () => {
      const lab = document.getElementById("capacity-lab-title");
      lab.scrollIntoView({behavior: "smooth", block: "start"});
      document.getElementById("capacity-input").focus({preventScroll: true});
      setStatus(
        "capacity-status",
        "Design structure carried forward. Paste exact protocol geometry; no matrix or linkage was inferred from the ordinary form."
      );
    });

    document.getElementById("capacity-form").addEventListener("submit", submitCapacity);
    document.getElementById("assess-level1").addEventListener("click", submitLevel1Assessment);
    document.getElementById("view-level1-authority").addEventListener("click", async () => {
      try {
        setStatus("capacity-status", "Loading the role-aware Level-1 definition…");
        const response = await fetch("/api/v2/level1-authority");
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
        const proof = payload.readback.validation;
        setStatus(
          "capacity-status",
          `Level-1 definition verified: ${proof.ordered_coordinate_count} coordinates, ${proof.role_partition_count} disjoint roles, ${proof.family_count} families; normalization remains unresolved.`
        );
      } catch (error) {
        setStatus("capacity-status", error.message, true);
      }
    });
    document.getElementById("load-capacity-example").addEventListener("click", async () => {
      try {
        const payload = await loadJsonExample("/protocol-capacity-example.json");
        document.getElementById("capacity-input").value = JSON.stringify(payload, null, 2);
        setStatus("capacity-status", "Illustrative protocol loaded. Its sources and geometry are synthetic mechanics fixtures.");
      } catch (error) {
        setStatus("capacity-status", error.message, true);
      }
    });
    document.getElementById("protocol-optimizer-form").addEventListener("submit", submitProtocolOptimizer);
    document.getElementById("load-optimizer-example").addEventListener("click", async () => {
      try {
        const [request, protocol] = await Promise.all([
          loadJsonExample("/optimizer-protocol-example.json"),
          loadJsonExample("/protocol-capacity-example.json")
        ]);
        request.base_protocol = protocol;
        document.getElementById("protocol-optimizer-input").value = JSON.stringify(request, null, 2);
        setStatus("optimizer-status", "Illustrative protocol-native design search loaded. Resource values are mechanics fixtures, not quotes.");
      } catch (error) {
        setStatus("optimizer-status", error.message, true);
      }
    });

    document.getElementById("v2-form").addEventListener("submit", submitReplay);
    document.getElementById("load-mechanics").addEventListener("click", () => {
      document.getElementById("v2-input").value = MECHANICS_FIXTURE_TEXT;
      setStatus("v2-status", "Exact illustrative mechanics fixture loaded. It is not a trial or biological reference.");
    });
    document.getElementById("download-result").addEventListener("click", () => {
      downloadJson(replayPacket, "anibench-v2-mechanics-replay", replayPacket && replayPacket.run_input_sha256);
    });
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    DESIGN_CONTRACT,
    mechanicsFixture,
    MECHANICS_FIXTURE_TEXT,
    buildDesignPayload,
    triState,
    typedQuantity,
    normalizeCoordinates,
    flattenAssessmentCoordinates,
    normalizeGates,
    normalizeUpgrades,
    groupUpgrades,
    format,
    renderEnvelopeValue,
    metricPresentation,
    buildFamilyMap,
    buildDesignHandoffReceipt,
    classifyParetoRelation,
    deriveComparatorPlacement,
    designGeometrySourcePointers,
    deriveDesignProtocolBinding,
    buildStudioWorkflowReceipt,
    level1FamilyMetricRows,
    validateJsonText,
    canonicalNctId,
    ctgovStudyRows
  };
}
