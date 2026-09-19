/* Frozen registry descriptors; never biological capacity or treatment-effect scores. */
"use strict";
const AniBenchRegistryArchitecture = (() => {
  const labels = {
    collected: "Actual enrollment reported",
    planned: "Estimated enrollment reported",
    reported_unspecified: "Enrollment lifecycle unknown",
  };
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
  const coordinate = (study, id) =>
    study.record.coordinates.find((c) => c.coordinate_id === id);
  const quantity = (c) => (c.value.state === "point" ? c.value.value : null);
  function validate(packet) {
    if (
      packet?.schema !== "anibench.registry-native-architecture-inputs.v1" ||
      !Array.isArray(packet.studies) ||
      !packet.studies.length
    )
      throw Error("Unsupported registry packet");
    for (const key of ["snapshot_manifest_sha256", "preregistration_sha256"])
      if (!/^[a-f0-9]{64}$/.test(packet[key]))
        throw Error("Missing frozen provenance");
    const ids = new Set();
    for (const study of packet.studies) {
      const id = study.record?.record_id;
      if (!/^NCT\d{8}$/.test(id) || ids.has(id) || study.record.study_id !== id)
        throw Error("Invalid or duplicate registry identity");
      ids.add(id);
      if (
        !Object.hasOwn(labels, study.enrollment_lifecycle) ||
        !/^[a-f0-9]{64}$/.test(study.source_sha256) ||
        study.source_uri !== `https://clinicaltrials.gov/api/v2/studies/${id}`
      )
        throw Error("Invalid lifecycle/source");
      for (const [key, unit, namespace] of [
        ["enrollment", "people", "registry_enrollment_not_assay_complete"],
        [
          "arm_groups",
          "listed_arm_groups",
          "registry_protocol_arm_group_entries_not_verified_executed_arms",
        ],
      ]) {
        if (
          study.record.coordinates.filter((c) => c.coordinate_id === key)
            .length !== 1
        )
          throw Error("Missing or duplicate quantity");
        const c = coordinate(study, key);
        if (
          c.semantics?.unit !== unit ||
          c.semantics?.entity_namespace !== namespace ||
          !["point", "unknown"].includes(c.value?.state)
        )
          throw Error("Unsupported quantity semantics");
        if (
          c.value.state === "point" &&
          (!Number.isSafeInteger(c.value.value) || c.value.value < 0)
        )
          throw Error("Invalid count");
        if (
          !Array.isArray(c.sources) ||
          !c.sources.length ||
          c.sources.some(
            (s) =>
              s.source_sha256 !== `sha256:${study.source_sha256}` ||
              typeof s.locator !== "string" ||
              !s.locator.startsWith("/protocolSection/"),
          )
        )
          throw Error("Unbound source");
        if (
          key === "enrollment" &&
          (c.semantics.collection_status !== study.enrollment_lifecycle ||
            (study.enrollment_lifecycle === "reported_unspecified" &&
              c.value.state !== "unknown"))
        )
          throw Error("Inconsistent enrollment lifecycle");
      }
    }
    return packet;
  }
  function rows(packet, lifecycle) {
    if (!Object.hasOwn(labels, lifecycle))
      throw Error("Unknown lifecycle filter");
    return packet.studies
      .filter((s) => s.enrollment_lifecycle === lifecycle)
      .map((s) => ({
        id: s.record.record_id,
        enrollment: quantity(coordinate(s, "enrollment")),
        groups: quantity(coordinate(s, "arm_groups")),
        source: s,
      }));
  }
  const shown = (n) =>
    n === null ? "Unknown" : new Intl.NumberFormat("en").format(n);
  function plot(packet, lifecycle) {
    const selected = rows(packet, lifecycle),
      known = selected.filter(
        (r) => r.enrollment !== null && r.groups !== null,
      );
    // Shared native linear axes across lifecycle views; exact zero remains zero. No jitter or invented counts.
    const all = packet.studies,
      maxX = Math.max(
        1,
        ...all.map((s) => quantity(coordinate(s, "enrollment")) || 0),
      ),
      maxY = Math.max(
        1,
        ...all.map((s) => quantity(coordinate(s, "arm_groups")) || 0),
      );
    const xTop = Math.ceil(maxX / 1000) * 1000,
      yTop = Math.ceil(maxY),
      x = (n) => 58 + (n / xTop) * 400,
      y = (n) => 235 - (n / yTop) * 180;
    let body = "";
    for (let i = 0; i <= 4; i++) {
      const n = (xTop * i) / 4;
      body += `<line x1="${x(n)}" x2="${x(n)}" y1="55" y2="235" class="registry-grid"/><text x="${x(n)}" y="257" text-anchor="${i === 0 ? "start" : i === 4 ? "end" : "middle"}">${shown(n)}</text>`;
    }
    for (let i = 0; i <= 3; i++) {
      const n = (yTop * i) / 3;
      body += `<line x1="58" x2="458" y1="${y(n)}" y2="${y(n)}" class="registry-grid"/><text x="48" y="${y(n) + 4}" text-anchor="end">${shown(n)}</text>`;
    }
    for (const r of known)
      body += `<circle cx="${x(r.enrollment)}" cy="${y(r.groups)}" r="4.5" class="registry-point"><title>${r.id}: ${shown(r.enrollment)} people; ${shown(r.groups)} listed groups</title></circle>`;
    body +=
      '<text x="58" y="23">Listed arm groups · protocol entries</text><text x="258" y="286" text-anchor="middle">Registry enrollment · people</text>';
    return `<svg viewBox="0 0 490 300" role="img" aria-label="${escape(labels[lifecycle])}: ${known.length} registry records with both quantities, on shared linear axes. Exact values in table.">${body}</svg><p>${known.length} of ${selected.length} selected records have both quantities. ${selected.length - known.length} cannot be plotted because at least one quantity is unknown. Points may overlap; opacity is not a density estimate.</p>`;
  }
  function table(packet, lifecycle) {
    return `<details><summary>Exact registry rows and source bindings (${rows(packet, lifecycle).length})</summary><div class="table-scroll"><table><caption>${labels[lifecycle]}; each denominator is its own registered cohort.</caption><thead><tr><th>Registry identity</th><th>Enrollment (people)</th><th>Listed groups</th><th>Frozen evidence</th></tr></thead><tbody>${rows(
      packet,
      lifecycle,
    )
      .map(
        (r) =>
          `<tr><th scope="row"><a href="https://clinicaltrials.gov/study/${r.id}">${r.id}</a></th><td>${shown(r.enrollment)}</td><td>${shown(r.groups)}</td><td><details><summary>Source, retrieval and locators</summary><p>Query stratum: ${escape(r.source.stratum_id)}. Retrieved ${escape(r.source.retrieved_at)}; registry update ${escape(r.source.registry_last_update_date)}.</p><a href="${escape(r.source.source_uri)}">Current API (may differ from frozen bytes)</a><code>${escape(r.source.source_sha256)}</code>${[
            "enrollment",
            "arm_groups",
          ]
            .map(
              (k) =>
                `<p>${escape(k)}: ${coordinate(r.source, k)
                  .sources.map((s) => escape(s.locator))
                  .join("; ")}</p>`,
            )
            .join("")}</details></td></tr>`,
      )
      .join("")}</tbody></table></div></details>`;
  }
  function evidenceFilters(href, controls = null) {
    const params = new URL(href).searchParams;
    const allowed = {
      publication: [
        "all",
        "peer_reviewed_article",
        "preprint",
        "public_participant_protocol",
        "registry_record",
        "first_party_resource_release",
        "first_party_self_report",
        "unpublished",
        "unknown",
      ],
      ethics: [
        "all",
        "approval_reported",
        "explicitly_not_approved",
        "exempt_reported",
        "unknown",
      ],
    };
    return Object.fromEntries(
      Object.entries(allowed).map(([key, values]) => {
        const v = controls?.[key] ?? params.get(key);
        return [key, values.includes(v) ? v : "all"];
      }),
    );
  }
  function eligible(filters) {
    return (
      ["all", "registry_record"].includes(filters.publication) &&
      ["all", "unknown"].includes(filters.ethics)
    );
  }
  function bindEvidence(doc, environment, update) {
    const fromURL = () => update(evidenceFilters(environment.location.href));
    const fromControls = () =>
      update(
        evidenceFilters(environment.location.href, {
          publication: doc.getElementById("publication-filter")?.value,
          ethics: doc.getElementById("ethics-filter")?.value,
        }),
      );
    doc.addEventListener("change", (event) => {
      if (["publication-filter", "ethics-filter"].includes(event.target?.id))
        fromControls();
    });
    // Bubbling sees the original control's own reset handler first. Deferring also avoids listener-order races.
    doc.addEventListener("click", (event) => {
      if (event.target?.closest?.("#reset-evidence-filters"))
        queueMicrotask(fromControls);
    });
    environment.addEventListener("popstate", fromURL);
    fromURL();
  }
  function content(
    packet,
    lifecycle,
    filters = { publication: "all", ethics: "all" },
  ) {
    if (!eligible(filters))
      return `<p role="status">0 eligible under current evidence filters. All ${packet.studies.length} records use registry sources; approval is unknown for all ${packet.studies.length}. Unknown is not explicitly no approval. Change publication/ethics filters to include registry sources and unknown approval. Exclusion is not a zero measurement.</p>`;
    const selected = rows(packet, lifecycle),
      missing = selected.filter(
        (r) => r.enrollment === null || r.groups === null,
      );
    return `<h3>${labels[lifecycle]}</h3>${plot(packet, lifecycle)}${missing.length ? `<details><summary>Records with missing quantities (${missing.length})</summary><ul>${missing.map((r) => `<li>${r.id}: enrollment ${shown(r.enrollment)}; listed groups ${shown(r.groups)}.</li>`).join("")}</ul></details>` : ""}${table(packet, lifecycle)}`;
  }
  function render(
    packet,
    lifecycle = "collected",
    filters = { publication: "all", ethics: "all" },
  ) {
    validate(packet);
    return `<header class="section-heading"><div><p class="eyebrow">FROZEN REGISTRY DESCRIPTORS</p><h2>How do registered studies differ in size and listed groups?</h2><p>${packet.studies.length} query-selected records, not an unbiased sample of all studies. Enrollment is not assay-complete coverage; listed groups are not verified executed arms or independent causal contrasts.</p></div></header><article class="release-figure registry-panel"><label>Enrollment lifecycle <select data-registry-lifecycle>${Object.entries(
      labels,
    )
      .map(
        ([key, label]) =>
          `<option value="${key}"${key === lifecycle ? " selected" : ""}>${label} (${rows(packet, key).length})</option>`,
      )
      .join(
        "",
      )}</select></label><div data-registry-result aria-live="polite">${content(packet, lifecycle, filters)}</div><p>Neither axis is a biological-capacity or quality score. The publication and ethics filters above apply here too: all records are registry sources with unknown approval. The enrollment selector further separates their lifecycle. Registry reporting does not establish ethics approval.</p><details><summary>Selection and reproducibility</summary><p>${escape(packet.selection_rule)} Frozen ${escape(packet.selection_frozen_at)}. ${escape(packet.snapshot_freshness)}</p><p>Manifest SHA-256 <code>${escape(packet.snapshot_manifest_sha256)}</code></p><p>From a repository checkout:</p><pre><code>cd examples/registry_architecture\npython replay.py --out reproduced</code></pre><p>With exact frozen snapshots, add <code>--snapshot-cache /path/to/frozen-snapshots</code>; without them this replays supplied aggregates, not fresh raw-source verification.</p><a href="https://github.com/anibiome/anibench-benchmark/tree/main/examples/registry_architecture">Adapter, rules and runnable source package</a> · <a href="registry-architecture-data.json" download>Download exact input facts</a></details></article>`;
  }
  async function mount() {
    const root = document.getElementById("registry-architecture");
    if (!root) return;
    try {
      const response = await fetch("registry-architecture-data.json");
      if (!response.ok) throw Error("Unavailable");
      const packet = validate(await response.json());
      let filters = evidenceFilters(window.location.href);
      root.innerHTML = render(packet, "collected", filters);
      const refresh = () => {
        root.querySelector("[data-registry-result]").innerHTML = content(
          packet,
          root.querySelector("[data-registry-lifecycle]").value,
          filters,
        );
      };
      root
        .querySelector("[data-registry-lifecycle]")
        .addEventListener("change", refresh);
      bindEvidence(document, window, (value) => {
        filters = value;
        refresh();
      });
    } catch {
      root.innerHTML =
        '<p role="status">Registry comparison unavailable. Other charts remain available. <a href="https://github.com/anibiome/anibench-benchmark/tree/main/examples/registry_architecture">Open the reproducible source example</a>.</p>';
    }
  }
  return {
    validate,
    rows,
    plot,
    table,
    render,
    content,
    evidenceFilters,
    eligible,
    bindEvidence,
    mount,
  };
})();
if (typeof module !== "undefined")
  module.exports = AniBenchRegistryArchitecture;
if (typeof document !== "undefined") AniBenchRegistryArchitecture.mount();
