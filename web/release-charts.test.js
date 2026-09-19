"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const c = require("./release-charts.js");
const read = (name) => JSON.parse(fs.readFileSync(path.join(__dirname, name)));

test("source publication is bound to exact source, not the study's journal prestige", () => {
  const packet = read("study-status-cards.json");
  for (const [id, expected] of [
    ["PMC11370476", "preprint"],
    ["PMC10148951", "peer_reviewed_article"],
  ]) {
    const source = packet.sources[id];
    const fact = { study_id: "calerie-phase-2-expanded", source };
    assert.equal(c.factStatus(fact, packet).publication, expected);
    assert.equal(c.factStatus(fact, packet).ethics, "approval_reported");
    assert.equal(
      c.factStatus(
        { ...fact, source: { ...source, sha256: "0".repeat(64) } },
        packet,
      ).publication,
      "unknown",
    );
  }
  assert.equal(
    c.factStatus(
      { study_id: "all-of-us-cdrv9", source: packet.sources.AOUCDRv9 },
      packet,
    ).publication,
    "first_party_resource_release",
  );
});

test("publication and approval form an independent filter cross-product; unknown is not no", () => {
  const publications = [
    "peer_reviewed_article",
    "preprint",
    "first_party_self_report",
    "unknown",
  ];
  const ethics = [
    "approval_reported",
    "explicitly_not_approved",
    "exempt_reported",
    "unknown",
  ];
  for (const publication of publications)
    for (const status of ethics) {
      const record = { publication, ethics: status };
      assert.equal(c.matchesStatus(record), true);
      assert.equal(
        c.matchesStatus(record, {
          publication: "peer_reviewed_article",
          ethics: "all",
        }),
        publication === "peer_reviewed_article",
      );
      assert.equal(
        c.matchesStatus(record, {
          publication: "all",
          ethics: "approval_reported",
        }),
        status === "approval_reported",
      );
      assert.equal(
        c.matchesStatus(record, {
          publication: "peer_reviewed_article",
          ethics: "approval_reported",
        }),
        publication === "peer_reviewed_article" &&
          status === "approval_reported",
      );
      assert.equal(
        c.matchesStatus(record, {
          publication: "all",
          ethics: "explicitly_not_approved",
        }),
        status === "explicitly_not_approved",
      );
    }
});

test("all ERP scenario endpoints fit the declared log axis including extreme-depth cases", () => {
  const packet = read("erp-design-sensitivity.json");
  for (const row of packet.rows) {
    const svg = c.erpPlot(packet, row.N, row.k, row.d);
    const circles = [...svg.matchAll(/<circle cx="([^"]+)"/g)].map((m) =>
      Number(m[1]),
    );
    assert.equal(circles.length, 6);
    assert.ok(
      circles.every((x) => x >= 5 && x <= 475),
      `${row.N}/${row.k}/${row.d}: ${circles}`,
    );
  }
});

test("all 105 planner cells preserve executed classifications with no browser rescoring", () => {
  const plan = read("erp-design-plan.json");
  for (const depth of plan.request.grid.d) {
    const html = c.heatmap(plan, depth);
    for (const status of ["robust", "assumption_sensitive", "infeasible"]) {
      assert.equal(
        (html.match(new RegExp(`<td class="cell-${status}"`, "g")) || [])
          .length,
        plan.rows.filter((r) => r.d === depth && r.status === status).length,
      );
    }
  }
});

test("SVG attributes remain unique and small positive values never become zero", () => {
  assert.equal(
    (c.text(0, 0, "x", { fill: "blue", "font-size": 18 }).match(/fill=/g) || [])
      .length,
    1,
  );
  assert.equal(
    (c.text(0, 0, "x", { "font-size": 18 }).match(/font-size=/g) || []).length,
    1,
  );
  assert.notEqual(c.num(0.0001), "0");
  assert.equal(c.num(0), "0");
});

test("lower bounds, planned periods and absent values cannot masquerade as exact observations", () => {
  const f = {
    study_id: "uk-biobank",
    value: 500000,
    precision: "lower_bound",
    label: "Cohort",
    unit: "participants",
  };
  const svg = c.factPlot([f], "population");
  assert.match(svg, /&gt; 500,000/);
  assert.match(svg, /fill="white" stroke="#235bd6"/);
  assert.match(svg, /lower bound/);
  assert.match(
    c.factPlot(
      [
        {
          study_id: "pearl-rapamycin",
          value: 48,
          unit: "weeks",
          semantics: "planned_treatment_duration",
          label: "Treatment duration",
        },
      ],
      "time",
    ),
    /Planned treatment period/,
  );
  assert.doesNotMatch(c.factPlot([], "population"), /<svg/);
});

test("plots use actual evaluator results and retain separate scalar-task interpretation", () => {
  const packet = read("release-results.json");
  for (const task of ["person_state", "population_mean"]) {
    const svg = c.tradeoffPlot(packet, task);
    for (const id of ["two_people_extreme_depth", "large_complete_shallow"]) {
      const point = packet.points.find(
        (p) => p.design.id === id && p.task === task,
      );
      assert.ok(svg.includes(c.num(point.posterior_standard_deviation)));
    }
    assert.match(svg, /toy units/);
  }
  assert.equal(packet.biological_threshold_validated, false);
});

test("source-provided strings cannot add active markup or unsafe links", () => {
  assert.equal(c.safeURL("javascript:alert(1)"), "#");
  assert.equal(c.safeURL("https://user:password@example.org/"), "#");
  assert.doesNotMatch(c.text(0, 0, "<script>unsafe()</script>"), /<script>/);
});

test("standalone SVG exports retain visible interpretation, escaped source provenance and plot geometry", () => {
  const original = c.factPlot(
    [
      {
        study_id: "uk-biobank",
        value: 500000,
        precision: "lower_bound",
        label: "Cohort",
        unit: "participants",
      },
    ],
    "population",
  );
  const [, width, height] = original.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/);
  const metadata =
    "Source <paper> & locator; SHA-256 " +
    "a".repeat(64) +
    "; https://example.org/?a=1&b=2";
  const svg = c.exportSVG({
    original,
    width: +width,
    height: +height,
    heading: "People & depth",
    subtitle: "Reported properties",
    caption: "A lower bound, not a benchmark score.",
    metadata,
  });
  assert.match(svg, /<title>People &amp; depth<\/title>/);
  assert.match(svg, /A lower bound, not a benchmark score\./);
  assert.match(svg, /Source &lt;paper&gt; &amp; locator/);
  assert.match(svg, /a{64}/);
  assert.match(svg, /&gt; 500,000/);
  assert.match(svg, /<g transform="translate\(0,75\)">/);
  assert.ok(!svg.includes("<paper>"));
});

test("filter exclusion reasons partition hidden facts and retain unknown counts", () => {
  const states = [
    { publication: "peer_reviewed_article", ethics: "approval_reported" },
    { publication: "unpublished", ethics: "approval_reported" },
    { publication: "peer_reviewed_article", ethics: "unknown" },
    { publication: "unknown", ethics: "unknown" },
  ];
  assert.deepEqual(
    c.filterCounts(states, {
      publication: "peer_reviewed_article",
      ethics: "approval_reported",
    }),
    {
      shown: 1,
      publicationOnly: 1,
      ethicsOnly: 1,
      both: 1,
      unknownPublication: 1,
      unknownEthics: 2,
    },
  );
  assert.equal(
    c.filterCounts(states, { publication: "all", ethics: "all" }).shown,
    4,
  );
});
