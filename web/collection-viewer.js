/* Local aggregate-receipt viewer. No file uploads, storage or browser scoring. */
"use strict";
const AniBenchCollection = (() => {
  const escape = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const fmt = (value) =>
    value === null
      ? "Not available"
      : new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(value);
  function text(value) {
    if (typeof value !== "string" || !value.trim() || value.length > 4000)
      throw Error("A required receipt label is invalid.");
    return value;
  }
  function quantity(value, integer = false) {
    if (
      typeof value !== "number" ||
      !Number.isFinite(value) ||
      value < 0 ||
      value > Number.MAX_SAFE_INTEGER ||
      (integer && !Number.isSafeInteger(value))
    )
      throw Error(
        "The receipt contains an invalid or unsupported numeric quantity.",
      );
    return value;
  }
  function distribution(value) {
    if (!value || quantity(value.n, true) === 0) {
      if (
        !value ||
        [value.min, value.p10, value.median, value.p90, value.max].some(
          (v) => v !== null,
        )
      )
        throw Error("An empty distribution must retain unknown quantiles.");
      return;
    }
    const values = [
      value.min,
      value.p10,
      value.median,
      value.p90,
      value.max,
    ].map((v) => quantity(v));
    if (values.some((v, i) => i && v < values[i - 1]))
      throw Error("Distribution quantiles are not ordered.");
  }
  function validate(value) {
    if (value?.schema_version === "anibench.collection-table-evaluation.v1")
      value = value.profile;
    if (value?.schema_version === "anibench.collection-profile.v1") {
      text(value.study_id);
      if (
        !["planned", "collected"].includes(value.record_basis) ||
        !["partial", "complete"].includes(value.inventory_status)
      )
        throw Error("Unsupported collection basis.");
      const roster = quantity(value.population?.roster_participants, true);
      if (
        !roster ||
        !Array.isArray(value.modules) ||
        value.modules.length > 128
      )
        throw Error("Invalid population or module inventory.");
      for (const key of [
        "participants_with_accepted_targets",
        "participants_with_two_or_more_times",
      ])
        if (quantity(value.population[key], true) > roster)
          throw Error("Participant coverage exceeds the roster.");
      if (value.population.participants_with_two_or_more_times >
          value.population.participants_with_accepted_targets)
        throw Error("Repeated participants exceed measured participants.");
      const ids = new Set();
      for (const row of value.modules) {
        text(row.module_id);
        text(row.target_unit);
        text(row.domain);
        if (ids.has(row.module_id)) throw Error("Duplicate module identifier.");
        ids.add(row.module_id);
        if (
          row.roster_denominator !== roster ||
          quantity(row.people_with_accepted_targets, true) > roster
        )
          throw Error("Module denominator does not match the roster.");
        for (const key of [
          "observed_target_count",
          "target_observations",
          "participant_events_with_accepted_targets",
        ])
          quantity(row[key], true);
        if (row.observed_target_count > quantity(row.registered_target_count, true))
          throw Error("Observed targets exceed registered targets.");
        distribution(row.targets_per_participant);
        if (row.targets_per_participant.n !== roster)
          throw Error(
            "Per-person target summaries must include the whole roster.",
          );
      }
      distribution(value.longitudinal?.distinct_known_times_per_participant);
      distribution(value.longitudinal?.span_days_among_repeated_participants);
      if (value.longitudinal.distinct_known_times_per_participant.n !== roster)
        throw Error("Time summaries must retain the whole roster.");
      quantity(value.longitudinal.events_with_unknown_time, true);
      if (
        !Array.isArray(value.joint_coverage) ||
        value.joint_coverage.length > 8128
      )
        throw Error("Invalid linkage inventory.");
      for (const pair of value.joint_coverage) {
        if (
          !Array.isArray(pair.module_ids) ||
          pair.module_ids.length !== 2 ||
          pair.module_ids[0] === pair.module_ids[1] ||
          pair.module_ids.some((id) => !ids.has(id))
        )
          throw Error("Unknown module in linkage inventory.");
        for (const key of [
          "people_with_both_modules_at_any_time",
          "people_with_both_modules_at_same_event",
        ])
          if (quantity(pair[key], true) > roster)
            throw Error("Linked-person coverage exceeds the roster.");
        quantity(pair.participant_events_with_both_modules, true);
      }
      return { kind: "profile", value };
    }
    if (value?.schema_version === "anibench.collection-metric-comparison.v1") {
      text(value.metric_card?.definition);
      text(value.metric_card?.units);
      text(value.basis?.record_basis);
      if (
        !Array.isArray(value.entries) ||
        value.entries.length < 2 ||
        value.entries.length > 500
      )
        throw Error("Choose a comparison with 2 to 500 studies.");
      const ids = new Set();
      for (const row of value.entries) {
        text(row.study_id);
        if (ids.has(row.study_id)) throw Error("Duplicate comparison study.");
        ids.add(row.study_id);
        quantity(row.lower);
        if (row.upper !== null && quantity(row.upper) < row.lower)
          throw Error("Invalid evidence bounds.");
        if (
          quantity(row.rank_min, true) < 1 ||
          quantity(row.rank_max, true) > value.entries.length ||
          row.rank_min > row.rank_max
        )
          throw Error("Invalid possible rank range.");
        quantity(row.denominator, true);
      }
      return { kind: "comparison", value };
    }
    throw Error(
      "Choose an aggregate output from profile, profile-tables, or compare-records. Raw participant records are not supported here.",
    );
  }
  const bar = (count, roster) =>
    `<svg class="coverage-track" viewBox="0 0 160 5" aria-hidden="true"><rect width="160" height="5"/><rect width="${(160 * count) / roster}" height="5"/></svg>`;
  const stat = (label, value, note) =>
    `<div><dt>${escape(label)}</dt><dd>${escape(value)}</dd><small>${escape(note)}</small></div>`;
  function profileHTML(p) {
    const n = p.population.roster_participants,
      times = p.longitudinal.distinct_known_times_per_participant,
      span = p.longitudinal.span_days_among_repeated_participants;
    return `<div class="surface-heading"><div><p class="eyebrow">YOUR COLLECTION RECORD</p><h2>${escape(p.study_id)}</h2></div><p class="muted">${escape(p.record_basis)} · ${escape(p.inventory_status)} inventory</p></div>
      <dl class="receipt-stats">${stat("Declared roster", fmt(n), "Includes unmeasured people")}${stat("With accepted measurements", fmt(p.population.participants_with_accepted_targets), `Out of ${fmt(n)} roster members`)}${stat("Median observation dates", fmt(times.median), "Per roster member, including zeros")}${stat("Median observed span", span.median === null ? "Not available" : `${fmt(span.median)} days`, `Among ${fmt(span.n)} ${span.n === 1 ? "person" : "people"} with repeated dates`)}</dl>
      <p class="table-note">Coverage counts accepted observations. Targets retain each module's own unit; they are not added into biological information. ${p.inventory_status === "partial" ? "This partial inventory does not establish what the complete study contains." : "Completeness and quality are declarations in the supplied receipt."}</p>
      <h3>Depth and coverage by measurement</h3><div class="table-scroll"><table><caption class="sr-only">Native module coverage and per-person target depth</caption><thead><tr><th>Measurement</th><th>People covered</th><th>Median targets per person</th><th>Distinct targets observed</th></tr></thead><tbody>${p.modules.map((m) => `<tr><td><strong>${escape(m.module_id)}</strong><small class="receipt-unit">${escape(m.domain)} · ${escape(m.target_unit.replaceAll("_", " "))}</small></td><td>${fmt(m.people_with_accepted_targets)} / ${fmt(n)}${bar(m.people_with_accepted_targets, n)}</td><td>${fmt(m.targets_per_participant.median)}<small class="receipt-unit">Whole-roster denominator</small></td><td>${fmt(m.observed_target_count)}<small class="receipt-unit">Union across people and events</small></td></tr>`).join("")}</tbody></table></div>
      <details class="receipt-details"><summary>Repeated observation and linked measurements</summary><p>${fmt(p.population.participants_with_two_or_more_times)} of ${fmt(n)} people have two or more known dates. ${fmt(p.longitudinal.events_with_unknown_time)} accepted events have no known time. The observed span ranges from ${fmt(span.min)} to ${fmt(span.max)} days among repeat participants; it is not intervention duration or a bound on unobserved follow-up.</p><label for="linkage-module">Inspect links to</label> <select id="linkage-module">${p.modules.map((m) => `<option value="${escape(m.module_id)}">${escape(m.module_id)}</option>`).join("")}</select><div id="linkage-view" class="table-scroll"></div></details>
      <details class="receipt-details"><summary>Evidence and reproducibility</summary><p>This view displays the supplied aggregate receipt. It does not verify original sources, reconstruct participant records, or certify the receipt's hash. Re-run the open Python evaluator to reproduce it.</p><code class="receipt-hash">Profile: ${escape(p.profile_sha256 || "Not supplied")}</code><code class="receipt-hash">Manifest: ${escape(p.manifest_sha256 || "Not supplied")}</code><p>Quality, population and target definitions remain review obligations. An aggregate is not automatically anonymous or safe to publish.</p></details>`;
  }
  function linkageHTML(p, module) {
    if (!p.joint_coverage.length)
      return '<p class="table-note">This receipt contains no module pairs to compare.</p>';
    return `<table><thead><tr><th>Other measurement</th><th>People with both, any time</th><th>People with both, same event</th></tr></thead><tbody>${p.joint_coverage
      .filter((r) => r.module_ids.includes(module))
      .map(
        (r) =>
          `<tr><td>${escape(r.module_ids.find((id) => id !== module))}</td><td>${fmt(r.people_with_both_modules_at_any_time)} / ${fmt(p.population.roster_participants)}</td><td>${fmt(r.people_with_both_modules_at_same_event)} / ${fmt(p.population.roster_participants)}</td></tr>`,
      )
      .join(
        "",
      )}</tbody></table><p class="table-note">Same-event linkage uses the receipt's time resolution. Shared dates do not prove exact simultaneity.</p>`;
  }
  function comparisonHTML(p) {
    return `<p class="eyebrow">ONE CATEGORY. ONE DEFINED CORPUS.</p><h2>${escape(p.metric_card.definition)}</h2><p class="lead">${escape(p.metric_card.units)} · ${escape(p.basis.record_basis)} records</p><p class="table-note">Ranks apply to this metric and these studies. Ranges preserve unresolved evidence. A first-place result can be tied; it does not establish an overall best study.</p><div class="table-scroll"><table><thead><tr><th>Study</th><th>Evidence bounds</th><th>Possible rank</th><th>Denominator</th></tr></thead><tbody>${p.entries.map((r) => `<tr><td>${escape(r.study_id)}</td><td>${r.upper === r.lower ? fmt(r.lower) : r.upper === null ? `${fmt(r.lower)} to unknown upper bound` : `${fmt(r.lower)} to ${fmt(r.upper)}`}</td><td>${r.rank_min === r.rank_max ? fmt(r.rank_min) : `${fmt(r.rank_min)}–${fmt(r.rank_max)}`}</td><td>${fmt(r.denominator)}</td></tr>`).join("")}</tbody></table></div><details class="receipt-details"><summary>Comparison basis and evidence</summary>${["population_definition", "observation_scope", "quality_definition", "review_protocol"].map((k) => `<h3>${escape(k.replaceAll("_", " "))}</h3><p>${escape(p.basis[k] || "Not supplied")}</p>`).join("")}<code class="receipt-hash">Receipt: ${escape(p.comparison_sha256 || "Not supplied")}</code><code class="receipt-hash">Corpus: ${escape(p.corpus_sha256 || "Not supplied")}</code><p>These results are displayed from the supplied receipt, not recomputed or hash-verified in this browser. Original sources and basis declarations require review.</p></details>`;
  }
  function show(payload) {
    const { kind, value } = validate(payload),
      container = document.getElementById("receipt-view");
    container.innerHTML =
      kind === "profile" ? profileHTML(value) : comparisonHTML(value);
    container.hidden = false;
    document.getElementById("clear-receipt").hidden = false;
    if (kind === "profile" && value.modules.length) {
      const select = document.getElementById("linkage-module");
      const render = () => {
        document.getElementById("linkage-view").innerHTML = linkageHTML(
          value,
          select.value,
        );
      };
      select.addEventListener("change", render);
      render();
    }
  }
  function start() {
    const input = document.getElementById("receipt-file"),
      status = document.getElementById("receipt-status");
    if (!input) return;
    let requestGeneration = 0;
    const clear = () => {
      requestGeneration += 1;
      input.value = "";
      document.getElementById("receipt-view").replaceChildren();
      document.getElementById("receipt-view").hidden = true;
      document.getElementById("clear-receipt").hidden = true;
    };
    document.getElementById("clear-receipt").addEventListener("click", () => {
      clear();
      status.textContent = "Receipt cleared from this view.";
    });
    input.addEventListener("change", async () => {
      const file = input.files[0];
      if (!file) return;
      const generation = ++requestGeneration;
      try {
        if (file.size > 5 * 1024 * 1024)
          throw Error("Choose an aggregate receipt smaller than 5 MB.");
        const contents = await file.text();
        if (generation !== requestGeneration) return;
        show(JSON.parse(contents));
        status.textContent =
          "Local receipt opened. Its contents stay in this browser and are not saved by this page.";
      } catch (error) {
        if (generation !== requestGeneration) return;
        clear();
        status.textContent =
          error instanceof SyntaxError
            ? "The file is not valid JSON."
            : error.message;
      }
    });
    document
      .getElementById("demo-receipt")
      .addEventListener("click", async () => {
        const generation = ++requestGeneration;
        try {
          const response = await fetch("collection-example.json");
          if (!response.ok) throw Error("The example could not be loaded.");
          const payload = await response.json();
          if (generation !== requestGeneration) return;
          show(payload);
          status.textContent =
            "Synthetic example generated by the public collection profiler. No real participant data.";
        } catch {
          if (generation !== requestGeneration) return;
          clear();
          status.textContent =
            "The example could not be loaded. You can still open a local aggregate receipt.";
        }
      });
  }
  return { validate, profileHTML, comparisonHTML, linkageHTML, start };
})();
if (typeof document !== "undefined") AniBenchCollection.start();
if (typeof module !== "undefined") module.exports = AniBenchCollection;
