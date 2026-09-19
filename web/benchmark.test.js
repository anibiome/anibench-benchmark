"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { factsFor, factText, safeURL, studyFacts } = require("./benchmark.js");

test("unknown population is never displayed as zero or enrollment", () => {
  assert.deepEqual(
    factsFor({ population: { state: "unknown", value: null } }, "participants"),
    [],
  );
});

test("planned registry and published denominators remain separately named", () => {
  const study = {
    population: { state: "known", value: 50, semantics: "planned_enrollment" },
    publication_facts: [
      { value: 42, unit: "participants", label: "Analysis subset" },
    ],
    source_binding: {
      authority_objects: [
        {
          evidence_class: "registry_primary",
          url: "https://clinicaltrials.gov/",
          sha256: "a".repeat(64),
        },
      ],
    },
  };
  const facts = studyFacts(study);
  assert.equal(facts.length, 2);
  assert.equal(facts[0].value, 42);
  assert.equal(facts[1].value, 50);
  assert.equal(facts[1].label, "Planned registry enrollment");
  assert.equal(facts[1].source.sha256, "a".repeat(64));
  assert.equal(
    facts[1].json_pointer,
    "/protocolSection/designModule/enrollmentInfo/count",
  );
});

test("an unbound registry coordinate is not displayed as a verified fact", () => {
  assert.deepEqual(
    studyFacts({ population: { state: "known", value: 50 } }),
    [],
  );
});

test("fact categories retain units and strict lower bounds", () => {
  const study = {
    publication_facts: [
      { value: 500000, unit: "participants", precision: "lower_bound" },
      { value: 4.7, unit: "years" },
      { value: 105, unit: "metabolites" },
    ],
  };
  assert.equal(factText(factsFor(study, "participants")[0]), "> 500,000");
  assert.equal(factsFor(study, "duration")[0].unit, "years");
  assert.equal(factsFor(study, "targets")[0].unit, "metabolites");
});

test("source links reject active content and local file URLs", () => {
  for (const url of [
    "javascript:alert(1)",
    "data:text/html,test",
    "file:///private/input",
    "not-a-url",
  ])
    assert.equal(safeURL(url), "#");
  assert.equal(
    safeURL("https://example.org/paper"),
    "https://example.org/paper",
  );
});
