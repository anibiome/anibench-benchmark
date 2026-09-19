"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { factsFor, factText, safeURL, studyFacts } = require("./benchmark.js");

test("approximate protocol duration is never presented as exact", () => {
  assert.equal(factText({ value: 6, precision: "source_approximate" }), "≈ 6");
});

test("protocol description retains uncertainty and escapes curated source text", () => {
  const { protocolDetails } = require("./benchmark.js");
  const html = protocolDetails({ protocol_observations: [{
    id: "neural", label: "Neural", state: "unknown", value: null,
    note: "<script>unsafe()</script>", pages: [5, 15], locator: "Figures",
    curation: "unresolved_source_scope",
  }] });
  assert.ok(html.includes("Unknown"));
  assert.ok(html.includes("5, 15"));
  assert.ok(html.includes("not machine-verified"));
  assert.ok(!html.includes("<script>"));
});

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

const {
  factRows,
  plot,
  readState,
  demoMetrics,
  syntheticPlot,
} = require("./benchmark.js");

test("plot preserves every denominator and facets incompatible units", () => {
  const studies = [
    {
      study_id: "trial",
      name: "Example",
      publication_facts: [
        {
          value: 50,
          unit: "participants",
          label: "Planned",
          semantics: "planned",
        },
        {
          value: 42,
          unit: "participants",
          label: "Analyzed",
          semantics: "analysis",
        },
        { value: 100, unit: "proteins", label: "Proteins" },
        { value: 250, unit: "metabolites", label: "Metabolites" },
      ],
    },
  ];
  assert.equal(factRows(studies, "participants").length, 2);
  const chart = plot(studies, "targets");
  assert.match(chart, /Reported proteins/);
  assert.match(chart, /Reported metabolites/);
  assert.equal((chart.match(/plot-facet/g) || []).length, 2);
  assert.doesNotMatch(chart, /rank|winner/);
});

test("zero is retained, invalid numeric facts omitted, tiny values stay nonzero", () => {
  const study = {
    study_id: "s",
    name: "Zero",
    publication_facts: [0, null, -1, NaN, Infinity, "2"].map((value) => ({
      value,
      unit: "participants",
      label: "Count",
    })),
  };
  assert.equal(factsFor(study, "participants").length, 1);
  assert.match(plot([study], "participants"), /plot-number">0</);
  assert.equal(factText({ value: 0.000013 }), "1.300e-5");
});

test("URL state round trips an explicitly empty selection and rejects unknown IDs", () => {
  const studies = [{ study_id: "a" }, { study_id: "b" }];
  assert.deepEqual(
    readState(
      "?family=causal&studies=b,a,unknown&view=synthetic&examples=x",
      studies,
      ["x", "y"],
    ),
    {
      family: "causal",
      mode: "synthetic",
      metric: null,
      studies: ["b", "a"],
      examples: ["x"],
    },
  );
  assert.deepEqual(
    readState("?studies=&examples=", studies, ["x"]).studies,
    [],
  );
  assert.deepEqual(
    readState("?family=__proto__", studies, []).family,
    "extensive",
  );
});

test("synthetic charts retain zero, unknown and provenance without a saturation claim", () => {
  const receipt = (id, value, state) => ({
    protocol_id: id,
    assessment_receipt_sha256: "sha256:receipt",
    scenarios: [
      {
        families: [
          {
            family_id: "intensive",
            native_metrics: [
              {
                metric_id: "rank",
                label: "Independent directions",
                value,
                state,
                unit: "dimensions",
                source_locator: "/rank",
                source_object_sha256: "sha256:source",
              },
            ],
          },
        ],
      },
    ],
  });
  const packet = {
    labels: { zero: "Zero", unknown: "Unknown" },
    receipts: [
      receipt("zero", 0, "computed_unverified_geometry"),
      receipt("unknown", null, "unresolved"),
    ],
  };
  const metrics = demoMetrics(packet, "intensive");
  assert.equal(metrics.length, 1);
  const chart = syntheticPlot(
    packet,
    "intensive",
    metrics[0].id,
    new Set(["zero", "unknown"]),
  );
  assert.match(chart, /plot-number">0</);
  assert.match(chart, /class="missing">unresolved/);
  assert.match(chart, /sha256:source/);
  assert.match(chart, /Synthetic model output/);
  assert.doesNotMatch(chart, /100%|winner/);
});

test("missing selected studies remain visible outside numerical axes", () => {
  const known = {
    study_id: "known",
    name: "Known",
    publication_facts: [{ value: 100, unit: "proteins", label: "Panel" }],
  };
  const unknown = {
    study_id: "unknown",
    name: "Unknown cohort",
    publication_facts: [],
  };
  const chart = plot([known, unknown], "targets");
  assert.match(chart, /Not reported in these records/);
  assert.match(chart, /Unknown cohort/);
  assert.equal((chart.match(/plot-number/g) || []).length, 1);
});

test("Boolean design support distinguishes yes, no and unknown without a numeric axis", () => {
  const packet = {
    labels: {},
    receipts: [true, false, null].map((value, index) => ({
      protocol_id: String(index),
      assessment_receipt_sha256: "sha256:receipt",
      scenarios: [{ families: [{ family_id: "personalized_sequential", native_metrics: [{
        metric_id: "adaptive", label: "Adaptive structure", value, unit: "boolean",
        state: value === null ? "unresolved" : "computed_unverified_geometry",
      }] }] }],
    })),
  };
  const metric = demoMetrics(packet, "personalized_sequential")[0];
  const chart = syntheticPlot(packet, "personalized_sequential", metric.id, new Set(["0", "1", "2"]));
  assert.match(chart, /plot-number">Yes</);
  assert.match(chart, /plot-number">No</);
  assert.match(chart, /class="missing">unresolved/);
  assert.match(chart, /Yes \/ No · Synthetic model output/);
  assert.doesNotMatch(chart, /Linear scale|plot-bar/);
});

test("different follow-up semantics are separated even within the same unit", () => {
  const study = {
    study_id: "time",
    name: "Timeline",
    publication_facts: [
      {
        value: 12,
        unit: "months",
        label: "Treatment",
        semantics: "treatment_period",
      },
      {
        value: 12,
        unit: "months",
        label: "Endpoint",
        semantics: "scheduled_endpoint",
      },
    ],
  };
  assert.equal(
    (plot([study], "duration").match(/plot-facet/g) || []).length,
    2,
  );
});
