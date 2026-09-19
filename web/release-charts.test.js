"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const c = require("./release-charts.js");
const read = (name) => JSON.parse(fs.readFileSync(path.join(__dirname, name)));

test("CALERIE figure table shows conditional uncertainty and preserves unidentifiability", () => {
  const packet = read("calerie-design.json");
  const html = c.calerieExample(packet);
  assert.match(html, /Not identifiable/);
  assert.match(html, /185 people/);
  assert.match(html, /179–183/);
  assert.match(html, /not confidence intervals/);
  assert.match(html, /two analyses of one study/);
  assert.match(html, /<caption>Conditional standard errors/);
  for (const row of packet.rows.filter(r => r.variance_interval))
    for (const value of row.variance_interval)
      assert.ok(html.includes(c.num(Math.sqrt(value))));
  const changed = structuredClone(packet);
  changed.model.yearly_correlation = 0.5;
  assert.throws(() => c.calerieExample(changed));
});

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

test("URL controls restore reload/back state and preserve unrelated selection", () => {
  const previous = global.document;
  const elements = Object.fromEntries([
    ["erp-people", ["2", "40", "2000"]], ["erp-visits", ["1", "4", "12"]],
    ["erp-depth", ["1", "4", "1000000"]], ["planner-depth", ["1", "4", "16"]],
  ].map(([id, options]) => [id, {value:"", options:options.map(value=>({value})), addEventListener(type, fn) {this[type]=fn;}}]));
  const env = {location:{href:"https://example.org/?selected=public-study&erp_n=2&erp_k=12&erp_d=4&planner_d=16#design-lab"}, listeners:{}, history:{}, addEventListener(type, fn){this.listeners[type]=fn;}};
  const history = [];
  env.history.pushState = (_, __, url) => { history.push(env.location.href); env.location.href = String(url); };
  global.document = {getElementById:id=>elements[id]};
  let renders = 0;
  try {
    c.bindURLControls([["erp-people","erp_n","40"],["erp-visits","erp_k","1"],["erp-depth","erp_d","1"],["planner-depth","planner_d","4"]],()=>renders++,env);
    assert.equal(elements["erp-visits"].value,"12");
    assert.equal(elements["planner-depth"].value,"16");
    elements["erp-people"].value="2000";
    elements["erp-people"].change();
    assert.match(env.location.href,/selected=public-study/);
    assert.match(env.location.href,/erp_n=2000/);
    assert.match(env.location.href,/#design-lab$/);
    env.location.href=history.pop(); env.listeners.popstate();
    assert.equal(elements["erp-people"].value,"2");
    env.location.href="https://example.org/?erp_n=invalid"; env.listeners.popstate();
    assert.equal(elements["erp-people"].value,"40");
    assert.equal(elements["erp-visits"].value,"1");
    assert.equal(elements["planner-depth"].value,"4");
    assert.equal(renders,4);
  } finally { global.document=previous; }
});

test("ERP HTML table binds all current scenario endpoints without scoring", () => {
  const packet=read("erp-design-sensitivity.json"), before=JSON.stringify(packet);
  for(const row of packet.rows){
    const table=c.erpTable(packet,row.N,row.k,row.d);
    for(const key of ["current_session_root_variance","persistent_root_variance_lower","persistent_root_variance_upper","population_root_variance_lower","population_root_variance_upper"])
      assert.ok(table.includes(`<td>${c.num(row[key])}</td>`));
    assert.match(table,/<th scope="row">This person&#39;s signal in this visit/);
    assert.match(table,/not confidence intervals/);
    assert.match(table,/µV/);
  }
  assert.equal(JSON.stringify(packet),before);
});

test("independent section loader renders fast data before a slow section and isolates failure", async () => {
  let release;
  const pending=new Promise(resolve=>{release=resolve;});
  const seen=[];
  const slow=c.loadSection(()=>pending,()=>seen.push("optional"),()=>seen.push("optional-error"));
  await c.loadSection(()=>Promise.resolve("real"),value=>seen.push(value),()=>seen.push("real-error"));
  assert.deepEqual(seen,["real"]);
  await c.loadSection(()=>Promise.reject(Error("unavailable")),()=>seen.push("bad"),()=>seen.push("failure"));
  assert.deepEqual(seen,["real","failure"]);
  release(); await slow;
  assert.deepEqual(seen,["real","failure","optional"]);
});

test("CALERIE paired cards use exact row variances, fixed scale and source provenance", () => {
  const packet = read("calerie-design.json"), before = JSON.stringify(packet);
  for (const estimand of ["CR_minus_AL_24mo_endpoint_change", "CR_minus_AL_24mo_curvature"]) {
    const svg = c.caleriePlot(packet, estimand);
    assert.match(svg, /fixed standard-error axis 0 to 0.3/);
    for (const row of packet.rows.filter(r => r.estimand_id === estimand)) {
      if (row.state === "unidentifiable") {
        assert.match(svg, /Not identifiable · midpoint missing/);
        continue;
      }
      for (const variance of row.variance_interval) {
        const value = Math.sqrt(variance);
        assert.ok(svg.includes(c.num(value)));
        assert.ok(svg.includes(String(14 + value / 0.3 * (426 - 14))));
      }
    }
    if (estimand.endsWith("curvature"))
      assert.equal((svg.match(/<circle/g) || []).length, 2, "Unidentifiable row has no zero mark");
  }
  const html = c.calerieExample(packet);
  assert.equal((html.match(/<svg /g) || []).length, 2);
  assert.equal((html.match(/<tbody>/g) || []).length, 1);
  assert.equal((html.match(/<tr><td>/g) || []).length, 4);
  for (const token of [packet.source_sha256, packet.chart_results_sha256, "https://doi.org/10.1038/s43587-022-00357-y"])
    assert.ok(html.includes(token));
  assert.match(html, /href="calerie-design.svg" download/);
  assert.match(html, /assumed standardized scalar variance of 1 and yearly correlation of 0/);
  assert.equal(JSON.stringify(packet), before);
});

test("CALERIE embeds responsive native cards instead of shrinking the standalone figure", () => {
  const html = c.calerieExample(read("calerie-design.json"));
  assert.match(html, /^<div class="chart-grid"><figure/);
  assert.equal((html.match(/viewBox="0 0 440 332"/g) || []).length, 2);
  assert.doesNotMatch(html, /<img/);
  const css = fs.readFileSync(path.join(__dirname, "release-charts.css"), "utf8");
  assert.match(css, /\.chart-grid\s*\{[^}]*grid-template-columns:\s*1fr 1fr/s);
  assert.match(css, /@media\s*\(max-width:\s*760px\)\s*\{\s*\.chart-grid\s*\{\s*grid-template-columns:\s*1fr/s);
  assert.match(css, /\.release-svg\s*\{[^}]*width:\s*100%;[^}]*height:\s*auto/s);
});

test("CALERIE rejects duplicate, stale-state and out-of-scale rows instead of drawing misleading marks", () => {
  const packet = read("calerie-design.json");
  const duplicate = structuredClone(packet); duplicate.rows.push(duplicate.rows[0]);
  assert.throws(() => c.caleriePlot(duplicate, packet.rows[0].estimand_id));
  const stale = structuredClone(packet); stale.rows[0].state = "unidentifiable";
  assert.throws(() => c.caleriePlot(stale, packet.rows[0].estimand_id));
  const outside = structuredClone(packet); outside.rows[0].variance_interval = [1, 1];
  assert.throws(() => c.caleriePlot(outside, packet.rows[0].estimand_id));
});
