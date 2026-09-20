/* SPDX-License-Identifier: Apache-2.0 */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const C = require("./compare.js");
const data = require("./source-architecture.json");
const state = (patch) => ({ ...C.readState("", data), ...patch });
const study = (id) => data.studies.find((s) => s.study_id === id);

test("public figures retain the population denominator and precision", () => {
  C.validate(data);
  assert.equal(C.primaryPopulation(study("uk-biobank")).value, 500000);
  assert.equal(C.primaryPopulation(study("circulate-tpe-ivig")).value, 44);
  assert.equal(
    C.primaryPopulation(study("human-phenotype-project-2025")).value,
    28000,
  );
  assert.equal(C.primaryPopulation(study("snyder-ipop-ihmp-106")).value, 106);
  assert.equal(C.primaryPopulation(study("ani-elite-sheba")), undefined);
  assert.equal(
    C.formatFact(C.primaryPopulation(study("uk-biobank"))),
    "≈500,000",
  );
  assert.equal(
    C.formatFact(study("human-phenotype-project-2025").numeric_facts[1]),
    ">13,000",
  );
  const html = C.peopleHTML(data, state());
  assert.match(html, /logarithmic scale/);
  assert.match(html, /Enrolled by July 2025/);
  const elite = html.slice(html.indexOf('data-study="ani-elite-sheba"'));
  assert.match(elite, /Not reported/);
  assert.doesNotMatch(elite.split('class="chart-axis"')[0], /class="bar-fill/);
});

test("publication applies to individual facts and coverage, independently of ethics", () => {
  const peer = state({ publication: "peer_reviewed_article" });
  assert.equal(C.visibleStudies(data, peer).length, 4);
  assert.equal(
    C.visibleStudies(data, { ...peer, ethics: "approval_reported" }).length,
    3,
  );
  assert.deepEqual(
    C.visibleStudies(data, { ...peer, ethics: "unknown" }).map(
      (s) => s.study_id,
    ),
    ["human-phenotype-project-2025"],
  );
  assert.equal(
    C.visibleStudies(data, state({ ethics: "explicitly_not_approved" })).length,
    0,
  );
  const ukb = study("uk-biobank");
  assert.equal(C.factVisible(C.primaryPopulation(ukb), peer, data), false);
  assert.match(C.peopleHTML(data, peer), /No matching source/);
  assert.doesNotMatch(C.peopleHTML(data, peer), /≈500,000/);
});

test("measurement coverage preserves described and unreported distinctions", () => {
  const elite = study("ani-elite-sheba");
  assert.equal(
    C.measurementState(
      elite.coverage.find((c) => c.domain === "digital"),
      state(),
      data,
    ).label,
    "Study description",
  );
  assert.equal(
    C.measurementState(
      elite.coverage.find((c) => c.domain === "neural"),
      state(),
      data,
    ).label,
    "Not reported",
  );
  assert.equal(
    C.measurementState(
      elite.coverage.find((c) => c.domain === "digital"),
      state({ publication: "peer_reviewed_article" }),
      data,
    ).label,
    "No matching source",
  );
  const ipop = study("snyder-ipop-ihmp-106");
  assert.match(C.detailHTML(ipop, data, state(), "digital"), /self-report/i);
  assert.match(
    C.detailHTML(ipop, data, state(), "functional"),
    /metabolic|glucose|insulin/i,
  );
});

test("protein chart compares protein inventory without mixing transcripts or glycans", () => {
  const html = C.measurementsHTML(data, state({ measurement: "proteins" }));
  assert.match(html, /2,923/);
  assert.match(html, />302</);
  assert.doesNotMatch(html, /13,379|>27</);
  assert.match(html, /linear scale/);
  assert.match(html, /not independent biological dimensions/);
  const unknown = C.measurementsHTML(
    data,
    state({ measurement: "proteins", studies: ["ani-elite-sheba"] }),
  );
  assert.doesNotMatch(unknown, /class="chart-axis"/);
  assert.match(unknown, /No counts are reported/);
});

test("time view labels unlike windows and keeps source order instead of ranking durations", () => {
  const html = C.timeHTML(data, state());
  assert.match(html, /1.6 years/);
  assert.match(html, /7 visits/);
  assert.match(html, /3 months/);
  assert.match(html, /6 sessions/);
  assert.match(html, /Short-regimen treatment span/);
  assert.match(html, /Monthly-regimen sessions/);
  assert.match(html, /7 days/);
  assert.match(html, /Accelerometer wear window/);
  assert.match(html, /no single duration ranking/);
  assert.ok(
    html.indexOf('data-study="snyder-ipop') <
      html.indexOf('data-study="uk-biobank'),
  );
});

test("URL state round-trips selections and handles invalid or empty choices safely", () => {
  const expected = state({
    category: "measurements",
    measurement: "proteins",
    publication: "peer_reviewed_article",
    ethics: "unknown",
    studies: ["human-phenotype-project-2025"],
  });
  const url = C.writeState(
    expected,
    "https://example.com/?unrelated=keep#comparison",
  );
  assert.deepEqual(C.readState(url.search, data), expected);
  assert.equal(url.hash, "#comparison");
  assert.equal(url.searchParams.get("unrelated"), "keep");
  const invalid = C.readState(
    "?compare=oops&ethics=approved&publication=published&compare_studies=uk-biobank,uk-biobank,invalid",
    data,
  );
  assert.equal(invalid.category, "people");
  assert.equal(invalid.ethics, "all");
  assert.deepEqual(invalid.studies, ["uk-biobank"]);
  assert.deepEqual(C.readState("?compare_studies=", data).studies, []);
  assert.match(
    C.peopleHTML(data, state({ studies: [] })),
    /No matching studies/,
  );
});

test("invalid evidence cannot silently become a visible zero or an executable link", () => {
  for (const bad of [NaN, Infinity, -1, "500"]) {
    const copy = structuredClone(data);
    copy.studies[0].numeric_facts[0].value = bad;
    assert.throws(() => C.validate(copy), /Invalid numeric fact/);
  }
  const missing = structuredClone(data);
  missing.studies[0].numeric_facts[0].source.source_id = "missing";
  assert.throws(() => C.validate(missing), /Missing source/);
  const incomplete = structuredClone(data);
  incomplete.studies[0].coverage.pop();
  assert.throws(
    () => C.validate(incomplete),
    /Incomplete measurement coverage/,
  );
  for (const url of [
    "javascript:alert(1)",
    "https://user:pass@example.com",
    "http://example.com",
  ])
    assert.equal(C.safeURL(url), null);
  const copy = structuredClone(data);
  copy.studies[0].name = '<img src=x onerror="alert(1)">';
  const html = C.peopleHTML(copy, state());
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
  const zero = structuredClone(data);
  zero.studies[0].numeric_facts[0].value = 0;
  const row = C.peopleHTML(zero, state())
    .split('data-study="snyder-ipop-ihmp-106"')[1]
    .split('<div class="bar-row">')[0];
  assert.match(row, /class="bar-value">0</);
  assert.doesNotMatch(row, /Not reported/);
});
