"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const viewer = require("./collection-viewer.js");
const example = () =>
  JSON.parse(
    fs.readFileSync(path.join(__dirname, "collection-example.json"), "utf8"),
  );

test("canonical aggregate profile and table envelope retain the unmeasured roster member", () => {
  const profile = example();
  assert.equal(viewer.validate(profile).kind, "profile");
  assert.equal(
    viewer.validate({
      schema_version: "anibench.collection-table-evaluation.v1",
      profile,
    }).value,
    profile,
  );
  const html = viewer.profileHTML(profile);
  assert.match(html, /Includes unmeasured people/);
  assert.match(html, /2 \/ 3/);
  assert.match(html, /Among 1 person with repeated dates/);
  assert.match(html, /partial inventory/);
});
test("private raw records and unknown document formats are rejected before rendering", () => {
  for (const v of [
    {
      schema_version: "anibench.collection-record.v1",
      participant_ids: ["private"],
    },
    {},
    null,
  ])
    assert.throws(() => viewer.validate(v), /aggregate output/);
});
test("invalid counts, denominator changes and unsafe integer rounding fail closed", () => {
  for (const amount of [
    null,
    -1,
    "3",
    true,
    Infinity,
    Number.MAX_SAFE_INTEGER + 1,
  ]) {
    const p = example();
    p.population.roster_participants = amount;
    assert.throws(() => viewer.validate(p));
  }
  const p = example();
  p.modules[0].roster_denominator = 99;
  assert.throws(() => viewer.validate(p), /denominator/);
});
test("empty follow-up stays unknown and malformed quantiles are rejected", () => {
  const p = example();
  p.longitudinal.span_days_among_repeated_participants = {
    n: 0,
    min: null,
    p10: null,
    median: null,
    p90: null,
    max: null,
  };
  viewer.validate(p);
  assert.match(viewer.profileHTML(p), /Not available/);
  p.longitudinal.span_days_among_repeated_participants.median = 0;
  assert.throws(() => viewer.validate(p), /empty distribution/);
});
test("viewer rejects repeated participants outside measured people", () => {
  const p = example();
  p.population.participants_with_accepted_targets = 1;
  p.population.participants_with_two_or_more_times = 2;
  assert.throws(() => viewer.validate(p), /Repeated participants/);
});
test("viewer rejects observed targets outside their registry", () => {
  const p = example();
  p.modules[0].observed_target_count = p.modules[0].registered_target_count + 1;
  assert.throws(() => viewer.validate(p), /Observed targets/);
});
test("labels and provenance never become active HTML", () => {
  const p = example();
  p.study_id = "<img src=x onerror=alert(1)>";
  p.modules[0].module_id = "<script>bad()</script>";
  p.profile_sha256 = "<svg onload=alert(1)>";
  const html = viewer.profileHTML(p);
  assert.doesNotMatch(html, /<img|<script|<svg onload/);
  assert.match(html, /&lt;img/);
});
test("comparison view preserves unbounded evidence and possible rank intervals", () => {
  const p = {
    schema_version: "anibench.collection-metric-comparison.v1",
    metric_card: { definition: "People measured", units: "people" },
    basis: { record_basis: "collected" },
    entries: [
      {
        study_id: "a",
        lower: 3,
        upper: 3,
        rank_min: 1,
        rank_max: 2,
        denominator: 4,
      },
      {
        study_id: "b",
        lower: 1,
        upper: null,
        rank_min: 1,
        rank_max: 2,
        denominator: 4,
      },
    ],
  };
  assert.equal(viewer.validate(p).kind, "comparison");
  const html = viewer.comparisonHTML(p);
  assert.match(html, /unknown upper bound/);
  assert.match(html, /1–2/);
  assert.match(html, /not recomputed or hash-verified/);
  p.entries[1].rank_max = 0;
  assert.throws(() => viewer.validate(p), /rank range/);
});
test("viewer has no persistence, analytics, remote file posting or arbitrary source fetch", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "collection-viewer.js"),
    "utf8",
  );
  assert.doesNotMatch(
    source,
    /localStorage|sessionStorage|indexedDB|sendBeacon|XMLHttpRequest|FormData/,
  );
  const fetches = source.match(/fetch\([^)]*\)/g);
  assert.deepEqual(fetches, ['fetch("collection-example.json")']);
});
