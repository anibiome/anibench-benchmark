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

test("source architecture preserves HPP bounds, five identities and separate molecular entities", () => {
  const packet = read("source-architecture.json"), before = JSON.stringify(packet);
  c.validateArchitecture(packet);
  const html = c.architectureHTML(packet);
  assert.equal(packet.studies.length, 5);
  assert.match(html, /≈ 28,000/);
  assert.match(html, /&gt; 13,000/);
  assert.match(html, /Description only/);
  assert.match(html, /Online self-report; wearable sensing not established/);
  assert.match(html, /Metabolic challenges/);
  assert.match(html, /Exercise\/fitness challenge in a subset/);
  assert.match(html, /infection is observational/);
  const molecular = c.architectureNumeric(packet, "molecular", {publication:"all",ethics:"all"});
  assert.match(molecular, /13,379/);
  assert.match(molecular, /2,923/);
  assert.match(molecular, /derived glycan traits/);
  assert.doesNotMatch(molecular, /16,302/);
  const hpp = packet.studies.find(s=>s.study_id==="human-phenotype-project-2025");
  assert.equal(hpp.ethics.status,"unknown");
  assert.equal(packet.sources[hpp.numeric_facts[0].source.source_id].publication,"peer_reviewed_article");
  assert.equal(JSON.stringify(packet), before);
});

test("architecture source and ethics filters stay independent and distinguish filtered from unreported", () => {
  const packet=read("source-architecture.json");
  const peer = c.architectureHTML(packet,{publication:"peer_reviewed_article",ethics:"all"});
  assert.match(peer,/Human Phenotype Project/);
  // ELITE may appear in the explicit scope caveat; no matching ELITE row or mark.
  assert.doesNotMatch(peer,/<th scope="row">ELITE/);
  assert.match(peer,/Filtered source/); // UKB neural/digital official sources, not its journal source.
  const approved = c.architectureHTML(packet,{publication:"all",ethics:"approval_reported"});
  assert.doesNotMatch(approved,/<strong>Human Phenotype Project<\/strong>/);
  assert.doesNotMatch(approved,/<th scope="row">ELITE/);
  assert.match(approved,/<th scope="row">UK Biobank/);
  const official = c.architectureHTML(packet,{publication:"first_party_self_report",ethics:"all"});
  assert.match(official,/<th scope="row">ELITE/);
  assert.match(official,/No numerical facts match/);
  const none = c.architectureHTML(packet,{publication:"unpublished",ethics:"approval_reported"});
  assert.match(none,/0 of 5 study descriptions/);
  assert.doesNotMatch(none,/<circle/);
});

test("public architecture packet contains bound references but no raw passages or private paths", () => {
  const packet=read("source-architecture.json"), serialized=JSON.stringify(packet);
  assert.doesNotMatch(serialized,/\/Users\/|raw_path|normalized_paragraph|epmc-core|participant_id|email/);
  for (const study of packet.studies) {
    for (const fact of study.numeric_facts) {
      assert.match(packet.sources[fact.source.source_id].sha256,/^[a-f0-9]{64}$/);
      assert.match(fact.source.passage_sha256,/^[a-f0-9]{64}$/);
      assert.ok(fact.scope && fact.precision && fact.unit);
    }
    assert.equal(new Set(study.coverage.map(c=>c.domain)).size,6);
  }
  const wrong=structuredClone(packet);wrong.studies[0].numeric_facts[0].value=NaN;
  assert.throws(()=>c.architectureHTML(wrong));
  const missing=structuredClone(packet);delete missing.sources[missing.studies[0].numeric_facts[0].source.source_id];
  assert.throws(()=>c.architectureHTML(missing));
});


test("architecture fails closed for malformed domains, identities and source metadata", () => {
  const mutations = [
    p => p.studies[0].coverage.pop(),
    p => p.studies[0].coverage[1].domain = p.studies[0].coverage[0].domain,
    p => p.studies[0].numeric_facts[1].fact_id = p.studies[0].numeric_facts[0].fact_id,
    p => p.studies[0].numeric_facts[0].fact_id = "",
    p => p.studies[0].name = null,
    p => Object.values(p.sources)[0].sha256 = "unverified",
    p => Object.values(p.sources)[0].publication = "approved",
    p => Object.values(p.sources)[0].fetch_url = "javascript:alert(1)",
    p => p.studies[0].coverage[0].sources = [],
  ];
  for (const mutate of mutations) {
    const packet = read("source-architecture.json"); mutate(packet);
    assert.throws(() => c.architectureHTML(packet));
  }
});

test("zero is an explicit separate population point, never logarithmic unknown", () => {
  const packet = read("source-architecture.json");
  const fact = packet.studies[0].numeric_facts.find(f => f.panel === "population");
  fact.value = 0; fact.precision = "exact_reported";
  c.validateArchitecture(packet);
  const html = c.architectureNumeric(packet, "population", {publication:"all",ethics:"all"});
  assert.match(html, /0 separate; positive axis 1 to 1,000,000/);
  assert.match(html, /circle cx="12"/);
  assert.doesNotMatch(html, /NaN|Infinity/);
});

test("source acquisition locators are distinct from human article URLs", () => {
  const packet = read("source-architecture.json");
  for (const source of Object.values(packet.sources)) {
    assert.match(source.fetch_url, /^https:\/\//);
    assert.ok(Object.hasOwn(source, "retrieved_at"));
    if (source.retrieved_at !== null) assert.ok(Number.isFinite(Date.parse(source.retrieved_at)));
  }
  assert.notEqual(packet.sources.PMC6666404.fetch_url, packet.sources.PMC6666404.url);
  assert.equal(packet.sources.ELITE_PUBLIC.retrieved_at, null);
});


test("compact architecture charts retain every row with one expandable evidence table", () => {
  const packet = read("source-architecture.json");
  const html = c.architectureNumeric(packet, "population", {publication:"all",ethics:"all"});
  assert.equal((html.match(/class="architecture-number"/g)||[]).length, 8);
  assert.equal((html.match(/<details/g)||[]).length, 1);
  assert.equal((html.match(/viewBox="0 0 440 20"/g)||[]).length, 8);
  assert.match(html, /<caption>Exact source-specific denominators/);
  for (const study of packet.studies) for (const fact of study.numeric_facts.filter(f=>f.panel === "population")) {
    assert.ok(html.includes(fact.scope));
    assert.ok(html.includes(packet.sources[fact.source.source_id].sha256));
  }
});
