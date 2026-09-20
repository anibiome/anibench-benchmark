/* SPDX-License-Identifier: Apache-2.0 */
"use strict";

// This view presents sourced quantities. It does not calculate a study score.
const Compare = (() => {
  const categories = ["people", "measurements", "time"];
  const publications = [
    "all",
    "peer_reviewed_article",
    "preprint",
    "public_participant_protocol",
    "registry_record",
    "first_party_resource_release",
    "first_party_self_report",
    "unpublished",
    "unknown",
  ];
  const ethicsStates = [
    "all",
    "approval_reported",
    "explicitly_not_approved",
    "exempt_reported",
    "unknown",
  ];
  const domains = {
    molecular: "Molecular",
    digital: "Digital",
    functional: "Function",
    cognitive: "Cognition",
    neural: "Brain",
    perturbation: "Challenges & interventions",
  };
  const populationKeys = {
    "uk-biobank": "baseline_people",
    "human-phenotype-project-2025": "enrolled",
    "snyder-ipop-ihmp-106": "participants",
    "circulate-tpe-ivig": "enrolled",
  };
  const ethicsLabels = {
    approval_reported: "Ethics approval reported",
    explicitly_not_approved: "Explicitly not approved",
    exempt_reported: "Ethics exemption reported",
    unknown: "Ethics status unknown",
  };
  const publicationLabels = {
    peer_reviewed_article: "Peer-reviewed article",
    preprint: "Preprint",
    public_participant_protocol: "Public protocol",
    registry_record: "Registry record",
    first_party_resource_release: "Official data release",
    first_party_self_report: "First-party report",
    unpublished: "Unpublished",
    unknown: "Publication status unknown",
  };
  const escape = (value) =>
    String(value ?? "").replace(
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
  const safeURL = (value) => {
    try {
      const u = new URL(value);
      return u.protocol === "https:" && !u.username && !u.password
        ? u.href
        : null;
    } catch {
      return null;
    }
  };
  function validate(data) {
    if (
      data?.schema_version !== "anibench.public-study-architecture.v1" ||
      !Array.isArray(data.studies) ||
      !data.sources
    )
      throw new Error("Unsupported comparison data");
    const ids = new Set();
    const facts = new Set();
    for (const source of Object.values(data.sources)) {
      if (
        !safeURL(source.url) ||
        !publications.includes(source.publication) ||
        source.publication === "all"
      )
        throw new Error("Invalid source");
    }
    const checkSource = (ref) => {
      if (!ref || !Object.hasOwn(data.sources, ref.source_id))
        throw new Error("Missing source");
    };
    for (const study of data.studies) {
      if (
        !/^[a-z0-9-]+$/.test(study.study_id) ||
        ids.has(study.study_id) ||
        !study.name ||
        !ethicsStates.slice(1).includes(study.ethics?.status) ||
        !Array.isArray(study.numeric_facts) ||
        !Array.isArray(study.coverage)
      )
        throw new Error("Invalid study");
      ids.add(study.study_id);
      if (study.ethics.source_id) checkSource(study.ethics);
      for (const fact of study.numeric_facts) {
        if (
          facts.has(fact.fact_id) ||
          !fact.fact_id?.startsWith(`${study.study_id}:`) ||
          !Number.isFinite(fact.value) ||
          fact.value < 0 ||
          ![
            "exact_reported",
            "approximate",
            "strict_lower_bound",
            "reported_median",
            "typical_schedule",
            "reported_schedule",
          ].includes(fact.precision)
        )
          throw new Error("Invalid numeric fact");
        facts.add(fact.fact_id);
        checkSource(fact.source);
      }
      const seenDomains = new Set();
      for (const item of study.coverage) {
        if (
          !Object.hasOwn(domains, item.domain) ||
          seenDomains.has(item.domain) ||
          !["reported_present", "source_described", "unreported"].includes(
            item.state,
          ) ||
          !Array.isArray(item.sources)
        )
          throw new Error("Invalid measurement coverage");
        seenDomains.add(item.domain);
        item.sources.forEach(checkSource);
        if (item.state !== "unreported" && !item.sources.length)
          throw new Error("Unsupported coverage claim");
      }
      if (seenDomains.size !== Object.keys(domains).length)
        throw new Error("Incomplete measurement coverage");
    }
    return data;
  }
  function readState(search, data) {
    const p = new URLSearchParams(search);
    const choose = (key, allowed, fallback) =>
      allowed.includes(p.get(key)) ? p.get(key) : fallback;
    const all = data.studies.map((s) => s.study_id);
    return {
      category: choose("compare", categories, "people"),
      measurement: choose("measure", ["coverage", "proteins"], "coverage"),
      publication: choose("publication", publications, "all"),
      ethics: choose("ethics", ethicsStates, "all"),
      studies: p.has("compare_studies")
        ? p
            .get("compare_studies")
            .split(",")
            .filter((id, i, a) => all.includes(id) && a.indexOf(id) === i)
        : all,
    };
  }
  function writeState(state, url) {
    const result = new URL(url);
    for (const [key, value] of Object.entries({
      compare: state.category,
      measure: state.measurement,
      publication: state.publication,
      ethics: state.ethics,
      compare_studies: state.studies.join(","),
    }))
      result.searchParams.set(key, value);
    return result;
  }
  const sourceVisible = (ref, state, data) =>
    state.publication === "all" ||
    data.sources[ref.source_id]?.publication === state.publication;
  const factVisible = (fact, state, data) =>
    !!fact && sourceVisible(fact.source, state, data);
  const coverageVisible = (item, state, data) =>
    item.sources.some((ref) => sourceVisible(ref, state, data));
  function visibleStudies(data, state) {
    return data.studies.filter(
      (s) =>
        state.studies.includes(s.study_id) &&
        (state.ethics === "all" || s.ethics.status === state.ethics) &&
        (state.publication === "all" ||
          s.numeric_facts.some((f) => factVisible(f, state, data)) ||
          s.coverage.some((c) => coverageVisible(c, state, data))),
    );
  }
  const primaryPopulation = (study) =>
    study.numeric_facts.find(
      (f) =>
        f.fact_id ===
        `${study.study_id}:architecture:${populationKeys[study.study_id]}`,
    );
  const proteinFact = (study) =>
    study.numeric_facts.find(
      (f) => f.entity === "proteins" && f.unit === "proteins",
    );
  const formatNumber = (n) =>
    new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(n);
  const formatFact = (fact) =>
    (fact.precision === "approximate"
      ? "≈"
      : fact.precision === "strict_lower_bound"
        ? ">"
        : "") + formatNumber(fact.value);
  const studyButton = (study, subtitle = "") =>
    `<button type="button" class="study-name" data-study="${escape(study.study_id)}">${escape(study.name)}${subtitle ? `<span class="study-subtitle">${escape(subtitle)}</span>` : ""}</button>`;
  const noCount = (fact, state) =>
    fact && state.publication !== "all" ? "No matching source" : "Not reported";
  function emptyHTML() {
    return '<div class="empty-state"><strong>No matching studies.</strong>Try another source or ethics filter.<br />Unknown approval is different from explicitly not approved.<button type="button" data-reset>Reset filters</button></div>';
  }
  function barHTML(data, state, mode) {
    const people = mode === "people";
    const rows = visibleStudies(data, state)
      .map((study) => {
        const raw = people ? primaryPopulation(study) : proteinFact(study);
        return { study, raw, fact: factVisible(raw, state, data) ? raw : null };
      })
      .sort((a, b) => (b.fact?.value ?? -1) - (a.fact?.value ?? -1));
    if (!rows.length) return emptyHTML();
    const known = rows.filter((r) => r.fact);
    const max = Math.max(1, ...known.map((r) => r.fact.value));
    const power = Math.max(3, Math.ceil(Math.log10(max)));
    const linearStep = 10 ** Math.floor(Math.log10(max));
    const ceiling = people
      ? 10 ** power
      : Math.ceil(max / (3 * linearStep)) * 3 * linearStep;
    const ticks = Array.from({ length: 4 }, (_, i) =>
      people ? 10 ** ((power * i) / 3) : (ceiling * i) / 3,
    );
    const tickText = (n) =>
      n >= 1e6
        ? `${formatNumber(n / 1e6)}m`
        : n >= 1000
          ? `${formatNumber(n / 1000)}k`
          : formatNumber(n);
    const title = people
      ? "How many people took part?"
      : "How many plasma proteins were measured?";
    const note = people
      ? "Study populations; individual measurements may cover smaller subsets. A larger study is not necessarily a deeper study."
      : "Assay targets, not independent biological dimensions. Different platforms can measure different proteins.";
    return `<div class="chart-heading"><div><h3>${title}</h3><p>${people ? "Reported populations · people · logarithmic scale" : "Reported protein inventory · proteins · linear scale"}</p></div>${people ? "" : measurementNav(state)}</div>
      <div class="bar-chart" aria-label="${people ? "Reported study populations" : "Reported plasma proteins"}">${rows
        .map(({ study, raw, fact }) => {
          const width = fact
            ? (people
                ? Math.log10(Math.max(1, fact.value)) / power
                : fact.value / ceiling) * 100
            : 0;
          return `<div class="bar-row">${studyButton(study, fact?.label ?? (raw ? "Count excluded by source filter" : "Public count unavailable"))}<div class="bar-track" aria-hidden="true">${fact && fact.value > 0 ? `<div class="bar-fill" style="width:${width}%"></div>` : ""}</div><span class="bar-value${fact ? "" : " unknown"}">${fact ? escape(formatFact(fact)) : noCount(raw, state)}</span></div>`;
        })
        .join(
          "",
        )}</div>${known.length ? `<div class="chart-axis" aria-hidden="true"><span></span><div class="axis-ticks">${ticks.map((n) => `<span>${tickText(n)}</span>`).join("")}</div></div>` : '<p class="chart-note">No counts are reported in the selected sources.</p>'}<p class="chart-note">${note}</p>`;
  }
  const peopleHTML = (data, state) => barHTML(data, state, "people");
  const measurementNav = (state) =>
    `<div class="chart-subnav" aria-label="Measurement view"><button type="button" data-measure="coverage" aria-pressed="${state.measurement === "coverage"}">Coverage</button><button type="button" data-measure="proteins" aria-pressed="${state.measurement === "proteins"}">Proteins</button></div>`;
  function measurementState(item, state, data) {
    if (!item || item.state === "unreported")
      return { label: "Not reported", symbol: "—", css: "unreported" };
    if (!coverageVisible(item, state, data))
      return { label: "No matching source", symbol: "—", css: "unreported" };
    return item.state === "reported_present"
      ? { label: "Documented", symbol: "✓", css: "documented" }
      : { label: "Study description", symbol: "○", css: "described" };
  }
  function measurementsHTML(data, state) {
    if (state.measurement === "proteins")
      return barHTML(data, state, "proteins");
    const studies = visibleStudies(data, state);
    if (!studies.length) return emptyHTML();
    return `<div class="chart-heading"><div><h3>What does each study measure?</h3><p>Six areas of human biology and study design.</p></div>${measurementNav(state)}</div><p class="swipe-note">Swipe to see all six areas →</p><div class="table-scroll"><table class="measurement-table"><thead><tr><th scope="col">Study</th>${Object.values(
      domains,
    )
      .map((label) => `<th scope="col">${label}</th>`)
      .join("")}</tr></thead><tbody>${studies
      .map(
        (study) =>
          `<tr><th scope="row">${studyButton(study)}</th>${Object.keys(domains)
            .map((domain) => {
              const result = measurementState(
                study.coverage.find((c) => c.domain === domain),
                state,
                data,
              );
              return `<td><button type="button" class="cell-button ${result.css}" data-study="${study.study_id}" data-domain="${domain}" aria-label="${escape(`${study.name}, ${domains[domain]}: ${result.label}`)}" title="${result.label}">${result.symbol}</button></td>`;
            })
            .join("")}</tr>`,
      )
      .join(
        "",
      )}</tbody></table></div><div class="legend"><span><b class="documented">✓</b> Documented</span><span><b class="described">○</b> Study description</span><span><b class="unreported">—</b> Not reported${state.publication !== "all" ? " / no matching source" : ""}</span></div><p class="chart-note">Presence in a source does not mean every participant completed that measurement. Click a cell for the exact method.</p>`;
  }
  function timeHTML(data, state) {
    const studies = visibleStudies(data, state);
    if (!studies.length) return emptyHTML();
    const units = {
      years: "years",
      months: "months",
      days: "days",
      visits_per_participant: "visits",
      treatment_sessions: "sessions",
    };
    return `<div class="chart-heading"><div><h3>When and how often were people measured?</h3><p>Follow-up, treatment and sensor windows describe different parts of a study.</p></div></div><div class="time-list">${studies
      .map((study) => {
        const facts = study.numeric_facts.filter(
          (f) =>
            f.panel === "timing" &&
            !f.fact_id.endsWith(":healthy_sampling_interval") &&
            factVisible(f, state, data),
        );
        return `<div class="time-row">${studyButton(study)}<div class="time-values">${facts.length ? facts.map((f) => `<div class="time-value"><strong>${escape(formatFact(f))} ${escape(units[f.unit] ?? f.unit)}</strong><span>${escape(f.label)}</span></div>`).join("") : '<span class="no-value">Not reported in the selected sources</span>'}</div></div>`;
      })
      .join(
        "",
      )}</div><p class="chart-note">These are different kinds of time windows, so there is no single duration ranking.</p>`;
  }
  function sourceLink(ref, data) {
    const source = data.sources[ref.source_id];
    const url = source && safeURL(source.url);
    return url
      ? `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(publicationLabels[source.publication] ?? "Source")} ↗</a>`
      : "Source unavailable";
  }
  function detailHTML(study, data, state, domain) {
    const selected = study.coverage.filter(
      (c) => !domain || c.domain === domain,
    );
    const facts = domain
      ? []
      : study.numeric_facts.filter((f) => factVisible(f, state, data));
    return `<h2 id="detail-title">${escape(study.name)}${domain ? ` / ${domains[domain]}` : ""}</h2><p>${ethicsLabels[study.ethics.status]}. ${escape(study.ethics.summary || "Approval has not been established in the reviewed sources.")}${study.ethics.source_id ? ` ${sourceLink(study.ethics, data)}` : ""}</p>${facts.length ? `<h3>Reported quantities</h3>${facts.map((f) => `<div class="detail-fact"><div>${escape(f.label)}<small>${escape(f.scope)}<br />${sourceLink(f.source, data)}</small></div><strong>${escape(formatFact(f))} ${escape(f.unit.replaceAll("_", " "))}</strong></div>`).join("")}` : domain ? "" : "<p>No numerical profile is available in the selected public sources.</p>"}<h3>${domain ? "What the source establishes" : "Measurements and intervention"}</h3>${selected
      .map((c) => {
        const visible =
          c.state === "unreported" || coverageVisible(c, state, data);
        return `<p><strong>${domains[c.domain]} · ${measurementState(c, state, data).label}</strong><br />${visible ? escape(c.description) : "No supporting source matches the current publication filter."}<br />${c.sources
          .filter((ref) => sourceVisible(ref, state, data))
          .map((ref) => sourceLink(ref, data))
          .join(" · ")}</p>`;
      })
      .join(
        "",
      )}<p>“Not reported” means not established by these sources. It does not mean the study did not collect it.</p>`;
  }
  function mount() {
    let data, state;
    const panel = document.querySelector("#comparison-panel");
    const filters = document.querySelector("#filters");
    const dialog = document.querySelector("#study-detail");
    function render() {
      const shown = visibleStudies(data, state);
      document.querySelector("#study-count").textContent =
        `${shown.length} of ${data.studies.length} studies · public evidence`;
      for (const tab of document.querySelectorAll("[data-category]")) {
        const active = tab.dataset.category === state.category;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
      }
      panel.setAttribute("aria-labelledby", `tab-${state.category}`);
      panel.innerHTML = {
        people: peopleHTML,
        measurements: measurementsHTML,
        time: timeHTML,
      }[state.category](data, state);
      for (const key of ["publication", "ethics"])
        document.getElementById(key).value = state[key];
      for (const input of document.querySelectorAll("[data-study-choice]"))
        input.checked = state.studies.includes(input.value);
      const active = [];
      if (state.publication !== "all")
        active.push(
          document.querySelector("#publication").selectedOptions[0].textContent,
        );
      if (state.ethics !== "all")
        active.push(
          document.querySelector("#ethics").selectedOptions[0].textContent,
        );
      if (state.studies.length !== data.studies.length)
        active.push(`${state.studies.length} studies selected`);
      document.querySelector("#filter-count").textContent = active.length
        ? `(${active.length})`
        : "";
      const summary = document.querySelector("#active-filters");
      summary.hidden = !active.length;
      summary.textContent = active.join(" · ");
    }
    function change(patch) {
      if (!data) return;
      state = { ...state, ...patch };
      history.pushState(null, "", writeState(state, location.href));
      render();
    }
    function reset() {
      change({
        publication: "all",
        ethics: "all",
        studies: data.studies.map((s) => s.study_id),
      });
    }
    async function load() {
      panel.innerHTML =
        '<p class="loading" role="status">Loading study comparison…</p>';
      try {
        const response = await fetch("source-architecture.json", {
          credentials: "same-origin",
        });
        if (!response.ok) throw new Error("Comparison unavailable");
        data = validate(await response.json());
        state = readState(location.search, data);
        document.querySelector("#study-options").innerHTML = data.studies
          .map(
            (s) =>
              `<label><input type="checkbox" data-study-choice value="${s.study_id}" />${escape(s.name)}</label>`,
          )
          .join("");
        render();
      } catch {
        data = null;
        panel.innerHTML =
          '<div class="empty-state" role="alert"><strong>The comparison could not load.</strong>Please try again.<button type="button" data-retry>Retry</button></div>';
      }
    }
    document.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (button?.hasAttribute("data-retry")) {
        load();
        return;
      }
      if (data && button) {
        if (button.dataset.category)
          change({ category: button.dataset.category });
        if (button.dataset.measure) {
          const measure = button.dataset.measure;
          change({ measurement: measure });
          panel.querySelector(`[data-measure="${measure}"]`)?.focus();
        }
        if (
          button.hasAttribute("data-reset") ||
          button.id === "reset-filters"
        ) {
          reset();
          filters.open = false;
          document.querySelector('[aria-selected="true"]').focus();
        }
        if (button.dataset.study) {
          const study = data.studies.find(
            (s) => s.study_id === button.dataset.study,
          );
          if (study) {
            document.querySelector("#detail-content").innerHTML = detailHTML(
              study,
              data,
              state,
              button.dataset.domain,
            );
            dialog.showModal();
            dialog.scrollTop = 0;
          }
        }
      }
      if (button?.classList.contains("close-dialog")) dialog.close();
      if (!filters.contains(event.target)) filters.open = false;
    });
    document.querySelector(".tabs").addEventListener("keydown", (event) => {
      const index = categories.indexOf(event.target.dataset.category);
      if (
        index < 0 ||
        !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)
      )
        return;
      event.preventDefault();
      const next =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? categories.length - 1
            : (index +
                (event.key === "ArrowRight" ? 1 : -1) +
                categories.length) %
              categories.length;
      change({ category: categories[next] });
      document.getElementById(`tab-${categories[next]}`).focus();
    });
    filters.addEventListener("change", (event) => {
      if (!data) return;
      if (["publication", "ethics"].includes(event.target.id))
        change({ [event.target.id]: event.target.value });
      if (event.target.hasAttribute("data-study-choice"))
        change({
          studies: [
            ...document.querySelectorAll("[data-study-choice]:checked"),
          ].map((input) => input.value),
        });
    });
    filters.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        filters.open = false;
        filters.querySelector("summary").focus();
      }
    });
    window.addEventListener("popstate", () => {
      if (data) {
        state = readState(location.search, data);
        render();
      }
    });
    load();
  }
  return {
    validate,
    readState,
    writeState,
    visibleStudies,
    factVisible,
    coverageVisible,
    primaryPopulation,
    proteinFact,
    formatFact,
    peopleHTML,
    measurementsHTML,
    timeHTML,
    detailHTML,
    measurementState,
    safeURL,
    mount,
  };
})();
if (typeof module !== "undefined") module.exports = Compare;
if (typeof document !== "undefined")
  document.addEventListener("DOMContentLoaded", Compare.mount);
