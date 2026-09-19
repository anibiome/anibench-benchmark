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
    new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(value);
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
    targets: ["proteins", "metabolites", "analytes", "targets"],
  };
  const notes = {
    participants:
      "Reported cohort and analysis populations, with each denominator named. Bars use a log scale. These populations do not imply the same measurements per person.",
    duration:
      "Reported windows retain their original units and definitions. Median follow-up, a scheduled endpoint, and maximum observation time are different quantities.",
    targets:
      "Source-reported molecular targets. Target counts describe assay breadth; they do not establish independent biological information or per-participant completeness.",
  };
  function factsFor(study, metric) {
    return studyFacts(study).filter((fact) =>
      unitGroups[metric].includes(fact.unit),
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
    return `${fact.precision === "lower_bound" ? "> " : ""}${number(fact.value)}`;
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
    const rows = studies.filter((study) =>
      `${study.name} ${study.study_id}`.toLowerCase().includes(query),
    );
    document.getElementById("study-count").textContent =
      `${rows.length} of ${studies.length} studies`;
    document.getElementById("metric-note").textContent = notes[metric];
    document.getElementById("value-heading").textContent = {
      participants: "Reported participants",
      duration: "Reported time",
      targets: "Reported targets",
    }[metric];
    document.getElementById("empty-state").hidden = rows.length > 0;
    const max = Math.max(
      1,
      ...studies.flatMap((study) =>
        factsFor(study, "participants").map((fact) => fact.value),
      ),
    );
    document.getElementById("study-rows").innerHTML = rows
      .map((study) => {
        const facts = factsFor(study, metric),
          fact = facts[0];
        const bar =
          fact && metric === "participants"
            ? `<svg class="value-track" viewBox="0 0 145 3" aria-hidden="true"><rect width="145" height="3"/><rect width="${(145 * Math.log10(1 + fact.value)) / Math.log10(1 + max)}" height="3"/></svg>`
            : "";
        return `<tr><td><button class="study-button" data-study="${escape(study.study_id)}">${escape(study.name)}</button></td><td>${fact ? `<span class="fact-value">${escape(factText(fact))}</span>${metric !== "participants" ? `<span class="fact-unit">${escape(fact.unit)}</span>` : ""}${bar}` : '<span class="missing">Not reported here</span>'}</td><td>${fact ? `<span class="fact-label">${escape(fact.label)}${facts.length > 1 ? ` · ${facts.length - 1} more in details` : ""}</span>` : '<span class="missing">Open the source record</span>'}</td><td><button class="row-arrow" data-study="${escape(study.study_id)}" aria-label="Inspect ${escape(study.name)}">↗</button></td></tr>`;
      })
      .join("");
  }
  function detail(study) {
    const facts = studyFacts(study);
    const sources = study.source_binding?.authority_objects || [];
    document.getElementById("detail-content").innerHTML =
      `<h2 id="detail-title">${escape(study.name)}</h2><p class="intro-note">Reported facts preserve the population, assay, and time window described by each source. They are not a complete capacity evaluation.</p>${facts.map((fact) => `<div class="detail-fact"><div><strong>${escape(factText(fact))}</strong><span class="fact-unit">${escape(fact.unit)}</span></div><div><p>${escape(fact.label)}</p><a href="${escape(safeURL(fact.source.url))}" target="_blank" rel="noopener noreferrer">Read source ↗</a><details><summary>Definition &amp; provenance</summary><p>${escape(fact.semantics.replaceAll("_", " "))}</p><code>Source SHA-256: ${escape(fact.source.sha256)}</code><code>Source locator: ${escape(fact.json_pointer || "Official page text")}</code></details></div></div>`).join("") || '<p class="intro-note">No extracted publication facts are available in this release. The source record remains available for inspection.</p>'}<div class="detail-actions">${sources
        .slice(0, 2)
        .map(
          (source) =>
            `<a href="${escape(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">Study source ↗</a>`,
        )
        .join(
          "",
        )}<a href="explore.html#atlas">Full evidence workspace ↗</a></div>`;
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
      render(studies);
      document
        .getElementById("search")
        .addEventListener("input", () => render(studies));
      document
        .getElementById("metric")
        .addEventListener("change", () => render(studies));
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
  return { start, factsFor, factText, safeURL, studyFacts };
})();
if (typeof document !== "undefined") AniBenchPage.start();
if (typeof module !== "undefined") module.exports = AniBenchPage;
