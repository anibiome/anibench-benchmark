"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const view = require("./explore.js");

test("receipt upload preserves floating-point spelling and large integers", async () => {
  const raw = '{"value":1.0,"count":9007199254740993}';
  const file = {
    name: "receipt.json",
    size: raw.length,
    text: async () => raw,
  };
  assert.equal(await view.readFile(file), raw);
  const request = JSON.stringify({
    receipt_documents: [await view.readFile(file)],
  });
  assert.equal(JSON.parse(request).receipt_documents[0], raw);
  assert.notEqual(JSON.stringify(JSON.parse(raw)), raw);
  await assert.rejects(
    view.readFile({ ...file, text: async () => "invalid" }),
    /Invalid JSON/,
  );
});

test("unknown, absent, conditional and zero are not interchangeable", () => {
  assert.equal(view.factLabel({ state: "unknown", value: 0 }), "Unknown");
  assert.equal(view.factLabel({ state: "exact", value: 0 }), "0");
  assert.equal(view.factLabel({ state: "absent" }), "Absent");
  assert.equal(
    view.factLabel({ state: "conditional", value: 10 }),
    "10 (conditional)",
  );
  assert.equal(
    view.factLabel({
      state: "reported",
      value: 500000,
      precision: "lower_bound",
    }),
    ">500,000",
  );
  assert.equal(view.knownNumber({ state: "conditional", value: 10 }), null);
});

test("source links reject scripts, credentials and non-HTTPS origins", () => {
  assert.equal(view.safeSourceURL("javascript:alert(1)"), null);
  assert.equal(view.safeSourceURL("https://user:password@example.com"), null);
  assert.equal(view.safeSourceURL("http://example.com"), null);
  assert.equal(
    view.safeSourceURL("https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/"),
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/",
  );
});

function study(overrides = {}) {
  return {
    study_id: "study-a",
    name: "Study A",
    projection_lane: "cohort",
    population: { value: null, state: "unknown" },
    causal_architecture: { randomized_policy: null },
    source_binding: { authority_objects: [{ source_id: "paper" }] },
    reported_evidence: { measurements: [{ id: "proteomics" }] },
    ...overrides,
  };
}

test("filter keeps unknown assignment distinct from no randomization", () => {
  const rows = [
    study(),
    study({
      study_id: "study-b",
      causal_architecture: { randomized_policy: true },
    }),
  ];
  assert.equal(view.filterStudies(rows, "proteomics", "all").length, 2);
  assert.deepEqual(
    view.filterStudies(rows, "", "unknown").map((row) => row.study_id),
    ["study-a"],
  );
  assert.deepEqual(
    view.filterStudies(rows, "", "randomized").map((row) => row.study_id),
    ["study-b"],
  );
  assert.equal(view.filterStudies(rows, "no match", "all").length, 0);
});

test("population chart omits unknown and nonfinite values, preserving lower bounds", () => {
  const rows = [
    study(),
    study({ population: { value: Infinity, state: "known" } }),
    study({
      study_id: "reported",
      publication_facts: [
        {
          unit: "participants",
          state: "reported",
          value: 500000,
          precision: "lower_bound",
        },
      ],
    }),
  ];
  assert.equal(view.populationRows(rows).length, 1);
  assert.equal(view.populationRows(rows)[0].lowerBound, true);
});

test("registry and paper denominators remain separate", () => {
  const row = study({
    population: { state: "known", value: 40 },
    publication_facts: [{ state: "reported", value: 42, unit: "participants" }],
  });
  assert.equal(view.displayPopulation(row).value, 40);
  assert.equal(row.publication_facts[0].value, 42);
});

test("transport families are preserved rather than averaged", () => {
  const groups = view.metricGroups({
    metric_groups: [
      { group_id: "site", native_metrics: [{ metric_id: "rank", value: 1 }] },
      { group_id: "age", native_metrics: [{ metric_id: "rank", value: null }] },
    ],
  });
  assert.equal(groups.length, 2);
  assert.equal(groups[1].metrics[0].value, null);
});
