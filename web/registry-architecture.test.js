"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs");
const api = require("./registry-architecture.js");
const packet = JSON.parse(
  fs.readFileSync(`${__dirname}/registry-architecture-data.json`),
);
const copy = () => structuredClone(packet);
test("all 240 unique frozen studies retain exact lifecycle partition and coordinate values", () => {
  api.validate(packet);
  assert.equal(packet.studies.length, 240);
  assert.deepEqual(
    ["collected", "planned", "reported_unspecified"].map(
      (k) => api.rows(packet, k).length,
    ),
    [127, 107, 6],
  );
  for (const k of ["collected", "planned", "reported_unspecified"])
    for (const row of api.rows(packet, k))
      for (const [field, id] of [
        ["enrollment", "enrollment"],
        ["groups", "arm_groups"],
      ]) {
        const c = row.source.record.coordinates.find(
          (c) => c.coordinate_id === id,
        );
        assert.equal(
          row[field],
          c.value.state === "point" ? c.value.value : null,
        );
      }
});
test("zero is plotted at zero while unknowns remain named outside marks", () => {
  const rows = api.rows(packet, "collected"),
    zero = rows.find((r) => r.enrollment === 0);
  assert.ok(zero);
  assert.match(
    api.plot(packet, "collected"),
    new RegExp(`<circle cx="58"[^>]+><title>${zero.id}: 0 people`),
  );
  const html = api.render(packet, "reported_unspecified");
  assert.match(html, /0 of 6 selected records/);
  assert.match(html, /Records with missing quantities \(6\)/);
  assert.doesNotMatch(api.plot(packet, "reported_unspecified"), /<circle/);
  for (const r of api.rows(packet, "reported_unspecified"))
    assert.ok(html.includes(r.id));
});
test("separate lifecycle plots use shared axes and never silently combine records", () => {
  const actual = api.plot(packet, "collected"),
    planned = api.plot(packet, "planned");
  assert.match(actual, />4,000<\/text>/);
  assert.match(planned, />4,000<\/text>/);
  const plannedId = api.rows(packet, "planned")[0].id;
  assert.ok(!actual.includes(plannedId));
  assert.ok(planned.includes(plannedId));
  assert.throws(() => api.rows(packet, "all"));
});
test("source tables retain exact identifiers, numeric rows and frozen source bindings", () => {
  for (const lifecycle of ["collected", "planned", "reported_unspecified"]) {
    const table = api.table(packet, lifecycle);
    for (const r of api.rows(packet, lifecycle)) {
      assert.ok(table.includes(r.id));
      assert.ok(table.includes(r.source.source_sha256));
      assert.ok(table.includes(r.source.source_uri));
    }
    assert.match(table, /Current API \(may differ from frozen bytes\)/);
  }
});
test("malformed source, lifecycle, identity and count reject rather than create marks", () => {
  for (const mutate of [
    (p) => p.studies.push(p.studies[0]),
    (p) => (p.studies[0].source_uri = "javascript:alert(1)"),
    (p) => (p.studies[0].record.coordinates[0].value.value = -1),
    (p) => (p.studies[0].enrollment_lifecycle = "planned"),
    (p) =>
      (p.studies[0].record.coordinates[0].sources[0].source_sha256 =
        "sha256:" + "0".repeat(64)),
  ]) {
    const p = copy();
    mutate(p);
    assert.throws(() => api.validate(p));
  }
});
test("plain scope, independent filters and reproducibility are explicit", () => {
  const h = api.render(packet);
  for (const text of [
    "query-selected",
    "not an unbiased sample",
    "not assay-complete",
    "independent causal contrasts",
    "filters above apply here too",
    "python replay.py --out reproduced",
    "Exact registry rows",
  ])
    assert.ok(h.includes(text));
  assert.doesNotMatch(h, /phase score|best study|biological rank/i);
});

test("publication and ethics intersect: only registry/all and unknown/all admit rows", () => {
  for (const publication of [
    "all",
    "registry_record",
    "peer_reviewed_article",
    "unknown",
    "unpublished",
  ])
    for (const ethics of [
      "all",
      "unknown",
      "approval_reported",
      "explicitly_not_approved",
      "exempt_reported",
    ]) {
      const f = { publication, ethics },
        expected =
          ["all", "registry_record"].includes(publication) &&
          ["all", "unknown"].includes(ethics);
      assert.equal(api.eligible(f), expected);
      const h = api.render(packet, "collected", f);
      assert.equal(h.includes("<circle"), expected);
      assert.equal(
        h.includes("0 eligible under current evidence filters"),
        !expected,
      );
      assert.ok(h.includes("data-registry-lifecycle"));
    }
});
test("URL restoration matches existing control keys and invalid-option fallbacks", () => {
  assert.deepEqual(
    api.evidenceFilters(
      "https://example.test/?publication=registry_record&ethics=unknown",
    ),
    { publication: "registry_record", ethics: "unknown" },
  );
  assert.deepEqual(
    api.evidenceFilters("https://example.test/?publication=bad&ethics=bad"),
    { publication: "all", ethics: "all" },
  );
  assert.match(
    api.render(packet, "planned", {
      publication: "all",
      ethics: "approval_reported",
    }),
    /approval is unknown for all 240/,
  );
});
test("late controls, change, reset and popstate synchronize without listener-order dependence", async () => {
  const listeners = {},
    windowListeners = {},
    controls = {},
    seen = [];
  const doc = {
    addEventListener: (k, f) => (listeners[k] = f),
    getElementById: (id) => controls[id],
  };
  const env = {
    location: {
      href: "https://example.test/?publication=peer_reviewed_article",
    },
    addEventListener: (k, f) => (windowListeners[k] = f),
  };
  api.bindEvidence(doc, env, (f) => seen.push(f));
  assert.equal(seen.at(-1).publication, "peer_reviewed_article");
  controls["publication-filter"] = { value: "registry_record" };
  controls["ethics-filter"] = { value: "unknown" };
  listeners.change({ target: { id: "publication-filter" } });
  assert.deepEqual(seen.at(-1), {
    publication: "registry_record",
    ethics: "unknown",
  });
  listeners.click({ target: { closest: () => true } });
  controls["publication-filter"].value = "all";
  controls["ethics-filter"].value = "all";
  await Promise.resolve();
  assert.deepEqual(seen.at(-1), { publication: "all", ethics: "all" });
  env.location.href = "https://example.test/?ethics=approval_reported";
  windowListeners.popstate();
  assert.deepEqual(seen.at(-1), {
    publication: "all",
    ethics: "approval_reported",
  });
});

test("web registry packet equals the executable public replay input", () => {
  assert.equal(
    fs.readFileSync(`${__dirname}/registry-architecture-data.json`, "utf8"),
    fs.readFileSync(
      `${__dirname}/../examples/registry_architecture/inputs.json`,
      "utf8",
    ),
  );
});

test("lifecycle URL values validate and default safely", () => {
  for (const value of ["collected", "planned", "reported_unspecified"])
    assert.equal(
      api.lifecycleFromURL(`https://example.test/?registry_lifecycle=${value}`),
      value,
    );
  for (const query of [
    "",
    "?registry_lifecycle=nope",
    "?registry_lifecycle=__proto__",
  ])
    assert.equal(
      api.lifecycleFromURL("https://example.test/" + query),
      "collected",
    );
});
test("lifecycle change preserves other state and restores on reload/back", () => {
  const events = {},
    changes = {};
  const control = {
    value: "collected",
    addEventListener: (k, v) => (changes[k] = v),
  };
  const env = {
    location: {
      href: "https://example.test/?publication=registry_record&ethics=unknown&erp_n=250#registry-architecture",
    },
    history: { pushState: (a, b, url) => (env.location.href = String(url)) },
    addEventListener: (k, v) => (events[k] = v),
  };
  let renders = 0;
  api.bindLifecycle(control, env, () => renders++);
  control.value = "planned";
  changes.change();
  const url = new URL(env.location.href);
  assert.equal(url.searchParams.get("registry_lifecycle"), "planned");
  assert.equal(url.searchParams.get("publication"), "registry_record");
  assert.equal(url.searchParams.get("erp_n"), "250");
  assert.equal(url.hash, "#registry-architecture");
  assert.equal(api.lifecycleFromURL(env.location.href), "planned");
  env.location.href =
    "https://example.test/?registry_lifecycle=reported_unspecified#registry-architecture";
  events.popstate();
  assert.equal(control.value, "reported_unspecified");
  control.value = "collected";
  changes.change();
  assert.equal(
    new URL(env.location.href).searchParams.has("registry_lifecycle"),
    false,
  );
  assert.equal(renders, 4);
});
test("failed fetch exposes working scoped retry and keeps fallback", async () => {
  const listeners = {};
  const button = {
    addEventListener: (name, callback) => (listeners[name] = callback),
  };
  const root = { innerHTML: "", querySelector: () => button };
  const doc = { getElementById: () => root };
  let calls = 0;
  const fetcher = async () => {
    calls++;
    throw Error("offline");
  };
  await api.mount(doc, {}, fetcher);
  assert.match(root.innerHTML, /data-registry-retry/);
  assert.match(root.innerHTML, /reproducible source example/);
  await listeners.click();
  assert.equal(calls, 2);
  assert.match(root.innerHTML, /Registry comparison unavailable/);
});
