/* Source facts are displayed in their native definitions; no browser scoring. */
"use strict";
const AniBenchPage = (() => {
  const escape = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[char],
    );
  const number = (value) =>
    Math.abs(value) > 0 && Math.abs(value) < 0.01
      ? value.toExponential(3)
      : new Intl.NumberFormat("en", { maximumFractionDigits: 3 }).format(value);
  const safeURL = (value) => {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password
        ? url.href
        : "#";
    } catch {
      return "#";
    }
  };
  const unitGroups = {
    participants: ["participants"],
    duration: ["days", "weeks", "months", "years"],
    targets: [
      "proteins",
      "metabolites",
      "analytes",
      "targets",
      "transcripts",
      "cells",
    ],
  };
  const notes = {
    participants:
      "Reported cohort and analysis populations, with each denominator named. Bars use a log scale. These populations do not imply the same measurements per person.",
    duration:
      "Reported windows retain their original units and definitions. Median follow-up, a scheduled endpoint, and maximum observation time are different quantities.",
    targets:
      "Source-reported molecular targets. Target counts describe assay breadth; they do not establish independent biological information or per-participant completeness.",
  };
  const families = {
    intensive: {
      label: "Biological depth",
      metric: "targets",
      question: "What can one measurement resolve?",
      note: "A molecular target count is an assay descriptor. Independent biological resolution also depends on noise, covariance, tissue and linkage.",
    },
    extensive: {
      label: "Population",
      metric: "participants",
      question: "How much of a population is represented?",
      note: "Retained independent people, joint observations and population support govern what can be learned beyond one person.",
    },
    longitudinal: {
      label: "Time & trajectories",
      metric: "duration",
      question: "Which biological changes can we distinguish?",
      note: "Follow-up length, sampling cadence, linked observations and temporal dependence are separate design properties.",
    },
    causal: {
      label: "Perturbation",
      metric: "design",
      question: "Which intervention contrasts are identifiable?",
      note: "Diagnostics measure state. Assigned perturbations probe response. Arm counts alone do not establish independent causal contrasts.",
    },
    personalized_sequential: {
      label: "Personalization",
      metric: "design",
      question: "Whose response can the study distinguish?",
      note: "Personalized effects need supported effect modifiers, decision histories and response windows. Repeating measurements does not create independent people.",
    },
    transport: {
      label: "Transport",
      metric: "design",
      question: "Where can the study support learning?",
      note: "Transport requires declared target contexts and supported overlap. A large sample from one setting does not establish transfer to another.",
    },
  };
  let selectedStudies = new Set();
  let selectedDemos = new Set();
  let family = "extensive";
  let mode = "reported";
  let atlasStudies = [];
  let demo = null;
  const human = (value) => String(value ?? "Unknown").replaceAll("_", " ");
  function demoMetrics(packet, familyId) {
    const result = [];
    for (const receipt of packet?.receipts || []) {
      const item = receipt.scenarios?.[0]?.families?.find(
        (row) => row.family_id === familyId,
      );
      if (!item) continue;
      const groups = item.metric_groups?.length
        ? item.metric_groups
        : [{ native_metrics: item.native_metrics || [] }];
      for (const group of groups)
        for (const metric of group.native_metrics || []) {
          const id = `${group.group_id || group.label || "native"}:${metric.metric_id}`;
          if (!result.some((row) => row.id === id))
            result.push({
              id,
              ...metric,
              label: `${group.label ? group.label + " · " : ""}${metric.label || human(metric.metric_id)}`,
            });
        }
    }
    return result;
  }
  function metricOptions() {
    if (mode === "synthetic")
      return demoMetrics(demo, family).map((metric) => ({
        value: metric.id,
        label: metric.label,
      }));
    return [
      {
        value: families[family].metric,
        label: {
          participants: "People & populations",
          duration: "Time & follow-up",
          targets: "Molecular targets",
          design: "Evidence required for this family",
        }[families[family].metric],
      },
    ];
  }
  function refreshControls(preferred) {
    const focusFamily = document.activeElement?.dataset?.family;
    const options = metricOptions();
    document.getElementById("metric").innerHTML = options
      .map(
        (option) =>
          `<option value="${escape(option.value)}">${escape(option.label)}</option>`,
      )
      .join("");
    if (options.some((option) => option.value === preferred))
      document.getElementById("metric").value = preferred;
    document.getElementById("family-strip").innerHTML = Object.entries(families)
      .map(
        ([id, item], index) =>
          `<button type="button" data-family="${id}" aria-pressed="${family === id}"><span>0${index + 1}</span>${escape(item.label)}</button>`,
      )
      .join("");
    if (focusFamily)
      [...document.querySelectorAll("[data-family]")]
        .find((button) => button.dataset.family === focusFamily)
        ?.focus();
    document
      .querySelectorAll("[data-mode]")
      .forEach((button) =>
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.mode === mode),
        ),
      );
  }
  function readState(search, studies, demoIds) {
    const params = new URLSearchParams(search);
    const familyId = Object.hasOwn(families, params.get("family"))
      ? params.get("family")
      : "extensive";
    const ids = params.has("studies")
      ? params.get("studies").split(",")
      : studies.map((study) => study.study_id);
    const samples = params.has("examples")
      ? params.get("examples").split(",")
      : demoIds;
    return {
      family: familyId,
      mode: params.get("view") === "synthetic" ? "synthetic" : "reported",
      metric: params.get("metric"),
      studies: ids.filter((id) =>
        studies.some((study) => study.study_id === id),
      ),
      examples: samples.filter((id) => demoIds.includes(id)),
    };
  }
  function restoreState() {
    const state = readState(
      location.search,
      atlasStudies,
      Object.keys(demo?.labels || {}),
    );
    family = state.family;
    mode = state.mode;
    selectedStudies = new Set(state.studies);
    selectedDemos = new Set(state.examples);
    refreshControls(state.metric);
    render(atlasStudies);
  }
  function saveState() {
    const url = new URL(location.href);
    url.searchParams.set("family", family);
    url.searchParams.set("view", mode);
    url.searchParams.set("metric", document.getElementById("metric").value);
    url.searchParams.set("studies", [...selectedStudies].sort().join(","));
    url.searchParams.set("examples", [...selectedDemos].sort().join(","));
    history.pushState(null, "", url);
    render(atlasStudies);
  }
  function chooseFamily(id, nextMode = mode, metric) {
    family = id;
    mode = nextMode;
    refreshControls(metric);
    saveState();
  }
  function syntheticPlot(packet, familyId, metricId, selected) {
    const descriptor = demoMetrics(packet, familyId).find(
      (metric) => metric.id === metricId,
    );
    if (!descriptor)
      return '<p class="empty">No model output is available for this metric.</p>';
    const rows = [];
    for (const receipt of packet.receipts || []) {
      if (!selected.has(receipt.protocol_id)) continue;
      const item = receipt.scenarios?.[0]?.families?.find(
        (row) => row.family_id === familyId,
      );
      const groups = item?.metric_groups?.length
        ? item.metric_groups
        : [{ native_metrics: item?.native_metrics || [] }];
      const metrics = groups.flatMap((group) =>
        (group.native_metrics || []).map((metric) => ({
          ...metric,
          id: `${group.group_id || group.label || "native"}:${metric.metric_id}`,
        })),
      );
      const metric = metrics.find((value) => value.id === metricId);
      rows.push({
        name: packet.labels[receipt.protocol_id] || receipt.protocol_id,
        metric,
        receipt,
      });
    }
    const max = Math.max(
      1,
      ...rows.map((row) =>
        Number.isFinite(row.metric?.value) &&
        typeof row.metric.value === "number"
          ? row.metric.value
          : 0,
      ),
    );
    return `<section class="synthetic-chart"><p class="chart-unit">${escape(human(descriptor.unit))} · Linear scale · Synthetic model output</p><ol class="plot-rows">${rows
      .map((row) => {
        const value = row.metric?.value;
        const known = typeof value === "number" && Number.isFinite(value);
        return `<li><div class="plot-study"><span>${escape(row.name)}</span><small>Nominal scenario · assumed geometry</small></div><div class="plot-range">${known ? `<span class="plot-bar" style="width:${Math.max(0, (value / max) * 100)}%"></span><span class="plot-number">${escape(number(value))}</span>` : `<span class="missing">${escape(row.metric?.state || "unresolved")}</span>`}</div></li>`;
      })
      .join(
        "",
      )}</ol><details class="metric-provenance"><summary>Definition, assumptions & reproducible evidence</summary><p>${escape(descriptor.label)}. ${escape(families[familyId].note)}</p><p>Values are computed from the two synthetic protocols with caller-declared operators, priors and covariance. Their scale is relative to these displayed values; it is not a percentage of biological understanding. Allocation support is a design proxy, not inferential precision.</p>${rows.map((row) => `<p><strong>${escape(row.name)}</strong><br/>State: ${escape(human(row.metric?.state))}</p><code>Source object: ${escape(row.metric?.source_object_sha256 || "unresolved")}</code><code>Locator: ${escape(row.metric?.source_locator || "unresolved")}</code><code>Assessment: ${escape(row.receipt.assessment_receipt_sha256)}</code>`).join("")}<a href="explorer-demo.json" download>Download protocols, assumptions & receipts ↓</a> · <a href="https://github.com/anibiome/anibench-benchmark/blob/main/docs/FIRST_PRINCIPLES.md">Mathematical definitions ↗</a></details></section>`;
  }
  function evidencePanel(studies, familyId) {
    return `<div class="evidence-panel"><p>${escape(families[familyId].note)}</p><p>These public records do not yet provide complete, source-bound geometry for this family. This is an evidence gap, not a score of zero.</p><ul>${studies.map((study) => `<li><button data-study="${escape(study.study_id)}">${escape(study.name)}</button><span>Capacity unresolved</span></li>`).join("")}</ul><button type="button" data-show-demo>See the synthetic demonstration →</button></div>`;
  }
  function factRows(studies, metric) {
    return studies
      .flatMap((study) =>
        factsFor(study, metric).map((fact) => ({ study, fact })),
      )
      .sort(
        (a, b) =>
          a.fact.unit.localeCompare(b.fact.unit) ||
          a.study.name.localeCompare(b.study.name) ||
          String(a.fact.label).localeCompare(String(b.fact.label)),
      );
  }
  function plot(studies, metric) {
    const groups = new Map();
    const allRows = factRows(studies, metric);
    for (const row of allRows) {
      const key = JSON.stringify([
        row.fact.unit,
        row.fact.semantics || row.fact.label || row.study.study_id,
      ]);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    }
    const missing = studies.filter((study) => !factsFor(study, metric).length);
    const missingNotice = missing.length
      ? `<details class="missing-studies" ${missing.length <= 3 ? "open" : ""}><summary>Not reported in these records: ${missing.length} selected ${missing.length === 1 ? "study" : "studies"}</summary><p>${missing.map((study) => `<button type="button" data-study="${escape(study.study_id)}">${escape(study.name)}</button>`).join(" · ")}</p><small>These studies remain selected. Missing information is not zero.</small></details>`
      : "";
    return (
      missingNotice +
      ([...groups]
        .map(([, rows]) => {
          const unit = rows[0].fact.unit;
          const max = Math.max(
            1,
            ...allRows
              .filter((row) => row.fact.unit === unit)
              .map((row) => row.fact.value),
          );
          const scale = (value) =>
            metric === "participants"
              ? Math.log10(1 + value) / Math.log10(1 + max)
              : value / max;
          const ticks =
            metric === "participants"
              ? [1, 100, 10000, 1000000].filter((v) => v <= max)
              : [0, max / 2, max];
          return `<section class="plot-facet" aria-label="Reported ${escape(unit)}"><div class="plot-heading"><h3>${escape(unit)} <small>· ${escape(human(rows[0].fact.semantics || rows[0].fact.label))}</small></h3><span>${metric === "participants" ? "Logarithmic scale" : "Linear scale · shared unit, separate definitions"}</span></div><div class="plot-axis" aria-hidden="true">${ticks.map((tick) => `<span style="left:${scale(tick) * 100}%">${escape(new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(tick))}</span>`).join("")}</div><ol class="plot-rows">${rows.map(({ study, fact }) => `<li><button class="plot-study" data-study="${escape(study.study_id)}"><span>${escape(study.name)}</span><small>${escape(fact.label)}</small></button><div class="plot-range"><span class="plot-bar ${fact.precision === "lower_bound" ? "lower-bound" : ""}" style="width:${Math.max(0, scale(fact.value) * 100)}%"></span><span class="plot-number">${escape(factText(fact))}</span></div></li>`).join("")}</ol></section>`;
        })
        .join("") ||
        '<p class="empty">No facts in this category for the selected studies. Missing information is not zero.</p>')
    );
  }
  function factsFor(study, metric) {
    return studyFacts(study).filter(
      (fact) =>
        (unitGroups[metric] || []).includes(fact.unit) &&
        typeof fact.value === "number" &&
        Number.isFinite(fact.value) &&
        fact.value >= 0,
    );
  }
  function studyFacts(study) {
    const facts = [...(study.publication_facts || [])];
    const population = study.population;
    const source = study.source_binding?.authority_objects?.find(
      (item) => item.evidence_class === "registry_primary",
    );
    if (
      population?.state === "known" &&
      Number.isFinite(population.value) &&
      source
    ) {
      facts.push({
        value: population.value,
        unit: "participants",
        label:
          population.semantics === "planned_enrollment"
            ? "Planned registry enrollment"
            : "Registry enrollment",
        precision: "reported_integer",
        semantics: population.semantics,
        source,
        json_pointer: "/protocolSection/designModule/enrollmentInfo/count",
      });
    }
    return facts;
  }
  function factText(fact) {
    const prefix = fact.precision === "lower_bound" ? "> " :
      fact.precision === "source_approximate" ? "≈ " : "";
    return `${prefix}${number(fact.value)}`;
  }
  function protocolDetails(study) {
    const observations = study.protocol_observations || [];
    if (!observations.length) return "";
    const source = study.source_binding?.authority_objects?.[0];
    return `<section class="protocol-description"><h3>Planned protocol</h3><p class="intro-note">${escape(source?.document_version || "Public source")}. These descriptions are curated from the cited pages. Unknowns and conflicting statements remain visible.</p>${observations.map((item) => `<div class="detail-fact"><div><strong>${escape(item.label)}</strong><span class="fact-unit">${escape(human(item.state))}</span></div><div><p>${escape(item.value ?? "Unknown")}</p><p>${escape(item.note)}</p><details><summary>Source & interpretation</summary><p>PDF ${item.pages.length > 1 ? "pages" : "page"} ${escape(item.pages.join(", "))} · ${escape(item.locator)}</p><p>${escape(human(item.curation))}; this interpretation is not machine-verified.</p></details></div></div>`).join("")}</section>`;
  }
  function route() {
    const selected = ["studies", "method", "run"].includes(
      location.hash.slice(1),
    )
      ? location.hash.slice(1)
      : "studies";
    document.querySelectorAll("main > .view").forEach((view) => {
      view.hidden = view.id !== selected;
    });
    document.querySelectorAll(".header nav a").forEach((link) => {
      if (link.hash === `#${selected}`)
        link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }
  function render(studies) {
    const metric = document.getElementById("metric").value;
    const query = document.getElementById("search").value.trim().toLowerCase();
    const matching = studies.filter((study) =>
      `${study.name} ${study.study_id}`.toLowerCase().includes(query),
    );
    const rows = studies.filter((study) => selectedStudies.has(study.study_id));
    const focusId = document.activeElement?.dataset?.select;
    const options =
      mode === "synthetic"
        ? Object.entries(demo?.labels || {}).map(([study_id, name]) => ({
            study_id,
            name,
          }))
        : matching;
    const selection = mode === "synthetic" ? selectedDemos : selectedStudies;
    document.getElementById("study-selection").innerHTML = options
      .map(
        (study) =>
          `<label class="study-choice"><input type="checkbox" data-select="${escape(study.study_id)}" ${selection.has(study.study_id) ? "checked" : ""}/><span>${escape(study.name)}</span></label>`,
      )
      .join("");
    document.getElementById("study-count").textContent =
      mode === "synthetic"
        ? `${selectedDemos.size} examples`
        : `${rows.length} of ${studies.length} studies`;
    if (focusId)
      [...document.querySelectorAll("[data-select]")]
        .find((input) => input.dataset.select === focusId)
        ?.focus();
    document.getElementById("search").disabled = mode === "synthetic";
    const download = document.querySelector(".rail-download");
    download.href =
      mode === "synthetic" ? "explorer-demo.json" : "explorer-atlas.json";
    download.textContent =
      mode === "synthetic"
        ? "Download synthetic protocols ↓"
        : "Download source records ↓";
    document.getElementById("select-all").textContent =
      mode === "synthetic" ? "Both examples" : "All studies";
    document.getElementById("selection-note").hidden = mode !== "synthetic";
    document.getElementById("selection-note").textContent =
      "Two hypothetical protocols. Your real-study selection is preserved.";
    document.getElementById("evidence-label").textContent =
      mode === "synthetic"
        ? "SYNTHETIC · CONDITIONAL MODEL OUTPUT"
        : "REPORTED STUDY FACTS";
    document.getElementById("metric-note").textContent =
      mode === "synthetic"
        ? "Explore a controlled design trade-off: deeper measurements versus longer follow-up. All six families are computed with explicit assumptions; neither example represents a real trial or certified benchmark attainment."
        : notes[metric] || families[family].note;
    document.getElementById("value-heading").textContent = {
      participants: "Reported participants",
      duration: "Reported time",
      targets: "Reported targets",
    }[metric];
    const hasSelection =
      mode === "synthetic" ? selectedDemos.size > 0 : rows.length > 0;
    document.getElementById("empty-state").hidden = hasSelection;
    document.getElementById("study-heading").textContent =
      families[family].question;
    document.getElementById("comparison-chart").innerHTML = !hasSelection
      ? ""
      : mode === "synthetic"
        ? syntheticPlot(demo, family, metric, selectedDemos)
        : metric === "design"
          ? evidencePanel(rows, family)
          : plot(rows, metric);
    document.querySelector(".source-table").hidden =
      mode === "synthetic" || metric === "design" || !hasSelection;
    document.getElementById("chart-context").textContent =
      mode === "synthetic"
        ? "Synthetic protocols · No clinical or saturation claim"
        : "Alphabetical order · Source facts, not a ranking";
    const max = Math.max(
      1,
      ...studies.flatMap((study) =>
        factsFor(study, "participants").map((fact) => fact.value),
      ),
    );
    document.getElementById("study-rows").innerHTML = rows
      .flatMap((study) => {
        const facts = factsFor(study, metric);
        return (facts.length ? facts : [null]).map((fact) => {
          const bar =
            fact && metric === "participants"
              ? `<svg class="value-track" viewBox="0 0 145 3" aria-hidden="true"><rect width="145" height="3"/><rect width="${(145 * Math.log10(1 + fact.value)) / Math.log10(1 + max)}" height="3"/></svg>`
              : "";
          return `<tr><td><button class="study-button" data-study="${escape(study.study_id)}">${escape(study.name)}</button></td><td>${fact ? `<span class="fact-value">${escape(factText(fact))}</span>${metric !== "participants" ? `<span class="fact-unit">${escape(fact.unit)}</span>` : ""}${bar}` : '<span class="missing">Not reported here</span>'}</td><td>${fact ? `<span class="fact-label">${escape(fact.label)}</span>` : '<span class="missing">Open the source record</span>'}</td><td><button class="row-arrow" data-study="${escape(study.study_id)}" aria-label="Inspect ${escape(study.name)}">↗</button></td></tr>`;
        });
      })
      .join("");
  }
  function detail(study) {
    const facts = studyFacts(study);
    const sources = study.source_binding?.authority_objects || [];
    document.getElementById("detail-content").innerHTML =
      `<h2 id="detail-title">${escape(study.name)}</h2><p class="intro-note">Reported facts preserve the population, assay, and time window described by each source. They are not a complete capacity evaluation.</p>${facts.map((fact) => `<div class="detail-fact"><div><strong>${escape(factText(fact))}</strong><span class="fact-unit">${escape(fact.unit)}</span></div><div><p>${escape(fact.label)}</p><a href="${escape(safeURL(fact.source?.url))}" target="_blank" rel="noopener noreferrer">Read source ↗</a><details><summary>Definition &amp; provenance</summary><p>${escape(human(fact.semantics))}</p><code>Source SHA-256: ${escape(fact.source?.sha256 || "unresolved")}</code><code>Source locator: ${escape(fact.json_pointer || "Official page text")}</code></details></div></div>`).join("") || '<p class="intro-note">No extracted publication facts are available in this release. The source record remains available for inspection.</p>'}<div class="detail-actions">${sources
        .slice(0, 2)
        .map(
          (source) =>
            `<a href="${escape(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">Study source ↗</a>`,
        )
        .join(
          "",
        )}<a href="explore.html#atlas">Full evidence workspace ↗</a></div>`;
    document.getElementById("detail-content").insertAdjacentHTML("beforeend", protocolDetails(study));
    document.getElementById("study-detail").showModal();
  }
  async function start() {
    route();
    window.addEventListener("hashchange", route);
    document
      .getElementById("close-detail")
      .addEventListener("click", () =>
        document.getElementById("study-detail").close(),
      );
    try {
      const response = await fetch("explorer-atlas.json");
      if (!response.ok) throw new Error("source records unavailable");
      const atlas = await response.json();
      if (
        !Array.isArray(atlas.studies) ||
        atlas.studies.some(
          (study) =>
            typeof study.study_id !== "string" ||
            typeof study.name !== "string",
        )
      )
        throw new Error("invalid source records");
      const studies = [...atlas.studies].sort((a, b) =>
        a.name.localeCompare(b.name),
      );
      atlasStudies = studies;
      try {
        const demoResponse = await fetch("explorer-demo.json");
        if (demoResponse.ok) demo = await demoResponse.json();
      } catch {
        /* Public records remain usable if the optional demonstration is unavailable. */
      }
      restoreState();
      window.addEventListener("popstate", restoreState);
      document
        .getElementById("family-strip")
        .addEventListener("click", (event) => {
          const button = event.target.closest("[data-family]");
          if (button) chooseFamily(button.dataset.family);
        });
      document
        .querySelector(".mode-switch")
        .addEventListener("click", (event) => {
          const button = event.target.closest("[data-mode]");
          if (button) chooseFamily(family, button.dataset.mode);
        });
      document.getElementById("all-charts").addEventListener("click", () => {
        document.getElementById("chart-index-content").innerHTML =
          Object.entries(families)
            .map(
              ([id, item]) =>
                `<section class="chart-index-family"><h3>${escape(item.label)}</h3><button type="button" data-chart-family="${id}" data-chart-mode="reported">Real studies · ${escape(item.metric === "design" ? "Evidence requirements" : { participants: "People & populations", targets: "Molecular targets", duration: "Time & follow-up" }[item.metric])}</button>${demoMetrics(
                  demo,
                  id,
                )
                  .map(
                    (metric) =>
                      `<button type="button" data-chart-family="${id}" data-chart-mode="synthetic" data-chart-metric="${escape(metric.id)}">Synthetic · ${escape(metric.label)}</button>`,
                  )
                  .join("")}</section>`,
            )
            .join("");
        document.getElementById("chart-index").showModal();
      });
      document
        .getElementById("close-chart-index")
        .addEventListener("click", () =>
          document.getElementById("chart-index").close(),
        );
      document
        .getElementById("chart-index-content")
        .addEventListener("click", (event) => {
          const button = event.target.closest("[data-chart-family]");
          if (button) {
            chooseFamily(
              button.dataset.chartFamily,
              button.dataset.chartMode,
              button.dataset.chartMetric,
            );
            document.getElementById("chart-index").close();
          }
        });
      document
        .getElementById("study-selection")
        .addEventListener("change", (event) => {
          const input = event.target.closest("[data-select]");
          if (input) {
            const selection =
              mode === "synthetic" ? selectedDemos : selectedStudies;
            if (input.checked) selection.add(input.dataset.select);
            else selection.delete(input.dataset.select);
            saveState();
          }
        });
      document.getElementById("select-all").addEventListener("click", () => {
        if (mode === "synthetic")
          selectedDemos = new Set(Object.keys(demo?.labels || {}));
        else selectedStudies = new Set(studies.map((study) => study.study_id));
        saveState();
      });
      document
        .getElementById("clear-selection")
        .addEventListener("click", () => {
          (mode === "synthetic" ? selectedDemos : selectedStudies).clear();
          saveState();
        });
      document
        .getElementById("comparison-chart")
        .addEventListener("click", (event) => {
          if (event.target.closest("[data-show-demo]")) {
            chooseFamily(family, "synthetic");
            return;
          }
          const button = event.target.closest("[data-study]");
          if (button) {
            const study = studies.find(
              (row) => row.study_id === button.dataset.study,
            );
            if (study) detail(study);
          }
        });
      render(studies);
      document
        .getElementById("search")
        .addEventListener("input", () => render(studies));
      document.getElementById("metric").addEventListener("change", saveState);
      document
        .getElementById("study-rows")
        .addEventListener("click", (event) => {
          const button = event.target.closest("[data-study]");
          if (button) {
            const study = studies.find(
              (row) => row.study_id === button.dataset.study,
            );
            if (study) detail(study);
          }
        });
    } catch {
      document.getElementById("study-count").textContent =
        "Records unavailable";
      document.getElementById("load-error").hidden = false;
      document.getElementById("load-error").textContent =
        "Study records could not be loaded. Reload this page or open the source repository.";
    }
  }
  return {
    start,
    factsFor,
    factText,
    safeURL,
    studyFacts,
    factRows,
    plot,
    readState,
    demoMetrics,
    syntheticPlot,
    evidencePanel,
    protocolDetails,
  };
})();
if (typeof document !== "undefined") AniBenchPage.start();
if (typeof module !== "undefined") module.exports = AniBenchPage;
