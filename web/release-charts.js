/* Source-bound release figures. Geometry and benchmark scores are never inferred from counts. */
"use strict";
const AniBenchCharts = (() => {
  const esc = (v) =>
    String(v).replace(
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
  const num = (v) =>
    Math.abs(v) > 0 && Math.abs(v) < 0.01
      ? v.toExponential(3)
      : new Intl.NumberFormat("en", { maximumFractionDigits: 3 }).format(v);
  const safeURL = (v) => {
    try {
      const u = new URL(v);
      return u.protocol === "https:" && !u.username && !u.password
        ? u.href
        : "#";
    } catch {
      return "#";
    }
  };
  const names = {
    "all-of-us-cdrv9": "All of Us",
    "motrpac-human-pre-suspension-expanded": "MoTrPAC",
    "ani-elite-sheba": "ELITE",
    "sheba-sharp": "SHARP",
    "do-health-bio-age": "DO-HEALTH",
    "dq-senolytic-bone": "D+Q bone trial",
    aspree: "ASPREE",
    "calerie-phase-2-expanded": "CALERIE",
    "circulate-tpe-ivig": "CIRCULATE TPE",
    "life-study": "LIFE",
    "mitoimmune-urolithin-a": "MitoImmune",
    "pearl-rapamycin": "PEARL",
    "predict-1": "PREDICT 1",
    "snyder-ipop-ihmp-106": "iPOP / iHMP",
    triim: "TRIIM",
    "uk-biobank": "UK Biobank",
    "zoe-method": "ZOE METHOD",
    "wur-oh-my-gut": "Oh My Gut!",
  };
  const sets = {
    population: [
      "all-of-us-cdrv9:reported-cohort",
      "aspree:randomized_primary_trial_population",
      "circulate-tpe-ivig:paper-enrolled",
      "snyder-ipop-ihmp-106:profiled-participants",
      "uk-biobank:cohort-size",
      "zoe-method:randomized_population",
    ],
    time: [
      "aspree:median_followup_not_uniform_duration",
      "calerie-phase-2-expanded:scheduled_followup_anchor_not_uniform_person_span",
      "snyder-ipop-ihmp-106:median-span",
      "life-study:median_followup_any_contact",
      "pearl-rapamycin:planned_treatment_duration",
      "zoe-method:endpoint_assessment_horizon",
    ],
  };
  function selectFacts(atlas, ids) {
    const facts = new Map(
      atlas.studies.flatMap((s) =>
        (s.publication_facts || []).map((f) => [
          f.fact_id,
          { ...f, study_id: s.study_id },
        ]),
      ),
    );
    return ids.map((id) => {
      const f = facts.get(id);
      if (!f || !Number.isFinite(f.value) || f.value <= 0 || !f.source?.sha256)
        throw Error("Required source-bound chart fact is unavailable");
      return f;
    });
  }
  function svgShell(title, content, height = 374, width = 560) {
    return `<svg xmlns="http://www.w3.org/2000/svg" class="release-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title><rect width="${width}" height="${height}" fill="white"/>${content}</svg>`;
  }
  const text = (x, y, value, attrs = {}) =>
    `<text x="${x}" y="${y}" ${Object.entries({
      fill: "#52616d",
      "font-family": "Arial,sans-serif",
      "font-size": 16,
      ...attrs,
    })
      .map(([key, val]) => `${key}="${esc(val)}"`)
      .join(" ")}>${esc(value)}</text>`;
  function factPlot(facts, kind) {
    if (!facts.length)
      return '<p class="chart-empty">No source facts match these filters. Unknown is not zero or evidence of no approval.</p>';
    const left = 8,
      right = 456,
      top = 55,
      gap = 76,
      height = top + facts.length * gap + 28;
    const isPopulation = kind === "population",
      isProtein = kind === "proteins";
    const toYears = (f) =>
      f.value /
      ({ years: 1, months: 12, weeks: 365.25 / 7, days: 365.25 }[f.unit] || 1);
    const scale = (v) =>
      left +
      (right - left) *
        (isPopulation ? Math.log10(v) / 6 : isProtein ? v / 3000 : v / 5);
    const ticks = isPopulation
      ? [1, 100, 10000, 1000000]
      : isProtein
        ? [0, 1000, 2000, 3000]
        : [0, 1, 2, 3, 4, 5];
    let body = ticks
      .map((v) =>
        text(
          scale(v),
          20,
          isPopulation
            ? { 1: "1", 100: "100", 10000: "10k", 1000000: "1m" }[v]
            : num(v),
          {
            "text-anchor":
              v === ticks[0]
                ? "start"
                : v === ticks[ticks.length - 1]
                  ? "end"
                  : "middle",
            "font-size": 15,
          },
        ),
      )
      .join("");
    facts.forEach((f, i) => {
      const y = top + i * gap;
      const value = isPopulation || isProtein ? f.value : toYears(f);
      const x = scale(value);
      const label =
        (f.precision === "lower_bound"
          ? "> "
          : f.precision === "source_approximate"
            ? "≈ "
            : "") +
        num(f.value) +
        (isPopulation ? "" : " " + f.unit);
      const definition =
        f.semantics === "planned_treatment_duration"
          ? "Planned treatment period"
          : f.label;
      body +=
        text(8, y, names[f.study_id] || f.study_id, {
          fill: "#172026",
          "font-weight": 600,
          "font-size": 17,
        }) +
        text(right, y, label, {
          "text-anchor": "end",
          fill: "#172026",
          "font-weight": 600,
          "font-size": 17,
        }) +
        text(8, y + 20, definition, { "font-size": 15 }) +
        `<line x1="${left}" x2="${right}" y1="${y + 37}" y2="${y + 37}" stroke="#e5ebf1" stroke-width="2"/><line x1="${left}" x2="${x}" y1="${y + 37}" y2="${y + 37}" stroke="#809dc9" stroke-width="3"/><circle cx="${x}" cy="${y + 37}" r="5" fill="${f.precision === "lower_bound" ? "white" : "#235bd6"}" stroke="#235bd6" stroke-width="2"/>` +
        (f.precision === "lower_bound"
          ? `<path d="M ${x + 9} ${y + 32} l 6 5 l -6 5" fill="none" stroke="#235bd6" stroke-width="2"/>`
          : "");
    });
    body += text(
      8,
      height - 11,
      isPopulation
        ? "People · log scale · open point = lower bound"
        : isProtein
          ? "Proteins · assay targets, not independent dimensions"
          : "Years on axis · original units retained",
      { "font-size": 14 },
    );
    return svgShell(
      isPopulation
        ? "Reported study populations with named denominators"
        : isProtein
          ? "Reported protein target counts with named definitions"
          : "Reported study windows with named definitions",
      body,
      height,
      480,
    );
  }
  function sources(facts) {
    return `<details class="figure-sources"><summary>Sources & definitions</summary><ul>${facts.map((f) => `<li><a href="${esc(safeURL(f.source.url))}" target="_blank" rel="noopener">${esc(names[f.study_id])}: ${esc(f.label)}</a> · ${esc(num(f.value))} ${esc(f.unit)} · ${esc(f.semantics)} · ${esc(f.json_pointer || "source text")}<br/><small>Source SHA-256 ${esc(f.source.sha256)}</small></li>`).join("")}</ul></details>`;
  }
  function figure(id, title, subtitle, svg, caption, source) {
    return `<figure class="release-figure" id="${id}"><div class="figure-top"><div><h3>${esc(title)}</h3><p>${esc(subtitle)}</p></div></div>${svg}<figcaption>${caption}</figcaption><div class="figure-actions"><span>ANIBENCH / ${esc(id.replace("figure-", ""))}</span>${svg.includes("<svg") ? `<button type="button" data-export="${id}">Download SVG ↓</button>` : "<span>No plotted values</span>"}</div>${source || ""}</figure>`;
  }
  const publicationLabels = {
    peer_reviewed_article: "Peer-reviewed article",
    preprint: "Preprint",
    public_participant_protocol: "Protocol",
    registry_record: "Registry",
    first_party_resource_release: "Official data release",
    first_party_self_report: "First-party report",
    unpublished: "Unpublished",
    unknown: "Unknown",
  };
  const ethicsLabels = {
    approval_reported: "Approval reported",
    explicitly_not_approved: "Explicitly not approved",
    exempt_reported: "Exemption reported",
    unknown: "Unknown",
  };
  function factStatus(fact, statuses) {
    const source = Object.entries(statuses?.sources || {}).find(
      ([, s]) => s.sha256 === fact.source?.sha256 && s.url === fact.source?.url,
    );
    const card = statuses?.cards.find((c) => c.study_id === fact.study_id);
    return {
      publication: source
        ? card?.publication_sources.find((p) => p.source_id === source[0])
            ?.status ||
          source[1].publication_type ||
          "unknown"
        : "unknown",
      ethics: card?.ethics?.status || "unknown",
    };
  }
  function matchesStatus(
    status,
    filters = { publication: "all", ethics: "all" },
  ) {
    return (
      (filters.publication === "all" ||
        status.publication === filters.publication) &&
      (filters.ethics === "all" || status.ethics === filters.ethics)
    );
  }
  function filterCounts(statuses, filters) {
    const counts = {
      shown: 0,
      publicationOnly: 0,
      ethicsOnly: 0,
      both: 0,
      unknownPublication: 0,
      unknownEthics: 0,
    };
    for (const status of statuses) {
      const p =
        filters.publication !== "all" &&
        status.publication !== filters.publication;
      const e = filters.ethics !== "all" && status.ethics !== filters.ethics;
      counts[
        p && e ? "both" : p ? "publicationOnly" : e ? "ethicsOnly" : "shown"
      ]++;
      if (status.publication === "unknown") counts.unknownPublication++;
      if (status.ethics === "unknown") counts.unknownEthics++;
    }
    return counts;
  }
  function allFactSets(atlas) {
    const facts = atlas.studies.flatMap(
      (study) => study.publication_facts || [],
    );
    return {
      population: facts
        .filter((f) => f.unit === "participants")
        .map((f) => f.fact_id),
      time: facts
        .filter((f) => ["years", "months", "weeks", "days"].includes(f.unit))
        .map((f) => f.fact_id),
    };
  }
  function reported(
    atlas,
    statuses,
    filters = { publication: "all", ethics: "all" },
  ) {
    const ids = filters.scope === "all" ? allFactSets(atlas) : sets;
    const choose = (ids) =>
      selectFacts(atlas, ids).filter((f) =>
        matchesStatus(factStatus(f, statuses), filters),
      );
    const people = choose(ids.population),
      time = choose(ids.time);
    return (
      figure(
        "figure-population",
        "How many people?",
        "Reported populations · real studies",
        factPlot(people, "population"),
        "<strong>Large cohorts cover more people.</strong> These are planned, released, randomized, enrolled or profiled populations, as labeled—not a shared assay-complete denominator. Study order does not denote rank.",
        sources(people),
      ) +
      figure(
        "figure-time",
        "How much time?",
        "Reported observation windows · real studies",
        factPlot(time, "time"),
        "<strong>Follow-up and treatment duration answer different questions.</strong> Compare the labeled definitions. A longer window does not tell you how often the same person was measured. Years use 365.25 days; months use 1/12 year.",
        sources(time),
      ) +
      figure(
        "figure-proteins",
        "How broad is a protein panel?",
        "Reported assay targets · real studies",
        factPlot(
          choose([
            "snyder-ipop-ihmp-106:proteins",
            "uk-biobank:unique_proteins_not_analytes_or_independent_dimensions",
          ]),
          "proteins",
        ),
        "<strong>Protein counts describe assay breadth.</strong> Platforms, target definitions and measurement coverage differ. These counts do not measure independent biological dimensions or total depth across all modalities.",
        sources(
          choose([
            "snyder-ipop-ihmp-106:proteins",
            "uk-biobank:unique_proteins_not_analytes_or_independent_dimensions",
          ]),
        ),
      )
    );
  }
  const designNames = {
    two_people_extreme_depth: "Two people, extreme depth",
    large_complete_shallow: "2,000 people, shallow",
    balanced_complete: "2,000 people, deep",
  };
  function tradeoffPlot(packet, task) {
    const rows = ["two_people_extreme_depth", "large_complete_shallow"].map(
      (id) => packet.points.find((p) => p.design.id === id && p.task === task),
    );
    if (rows.some((p) => !p)) throw Error("Missing executed trade-off");
    const left = 16,
      right = 455,
      scale = (v) => left + ((Math.log10(v) + 3) / 4) * (right - left);
    let body = [0.001, 0.01, 0.1, 1, 10]
      .map((v) =>
        text(scale(v), 25, num(v), {
          "text-anchor": v === 0.001 ? "start" : v === 10 ? "end" : "middle",
          "font-size": 15,
        }),
      )
      .join("");
    rows.forEach((p, i) => {
      const y = 65 + i * 105,
        x = scale(p.posterior_standard_deviation),
        color = i === 0 ? "#235bd6" : "#b65a32";
      body +=
        text(16, y, designNames[p.design.id], {
          fill: color,
          "font-weight": 600,
          "font-size": 18,
        }) +
        text(
          16,
          y + 24,
          `${num(p.design.N)} people · ${num(p.design.m)} readings per person`,
          { "font-size": 15 },
        ) +
        `<line x1="${left}" x2="${right}" y1="${y + 48}" y2="${y + 48}" stroke="#dbe4ed" stroke-width="3"/><circle cx="${x}" cy="${y + 48}" r="7" fill="${color}"/>` +
        text(
          Math.min(right, x + 13),
          y + 55,
          num(p.posterior_standard_deviation),
          { "font-size": 17, fill: color, "font-weight": 600 },
        );
    });
    body +=
      text(16, 293, "Posterior standard deviation · toy units · log axis", {
        "font-size": 14,
      }) +
      text(16, 316, "← Lower uncertainty is better", {
        "font-size": 15,
        fill: "#172026",
      });
    return svgShell(
      (task === "person_state"
        ? "Uncertainty in one person’s scalar state. "
        : "Uncertainty in a population mean. ") +
        rows
          .map(
            (p) =>
              designNames[p.design.id] +
              ": " +
              num(p.posterior_standard_deviation) +
              " toy units",
          )
          .join(". "),
      body,
      332,
      480,
    );
  }
  function tradeoffs(packet) {
    const audit =
      '<details class="figure-sources"><summary>Model, inputs & reproducible results</summary><p>Invented Gaussian model. Measurement-noise variance R = 4; between-person variance B = 1; prior precision = 0.000001. Readings are conditionally independent; people are independent. These are separate scalar inference problems, not a complete biological model.</p><p><a href="release-chart-receipts.json" download>Full evaluator inputs and receipts</a> · <a href="release-chart-provenance.json" download>Assumptions</a></p><p class="source-scroll">Receipt file SHA-256 ' +
      esc(packet.receipts_sha256) +
      "</p></details>";
    return (
      figure(
        "figure-individual",
        "Resolve one person’s state",
        "Hypothetical designs · lower uncertainty is better",
        tradeoffPlot(packet, "person_state"),
        "<strong>The two-person study leads this task.</strong> Repeating an independent measurement can sharply reduce measurement noise for the person measured. This does not create new people.",
        audit,
      ) +
      figure(
        "figure-population-precision",
        "Resolve the population mean",
        "Hypothetical designs · lower uncertainty is better",
        tradeoffPlot(packet, "population_mean"),
        "<strong>The 2,000-person study leads this task.</strong> Measuring two people more deeply cannot remove uncertainty about variation across the population.",
        audit,
      )
    );
  }
  function gates(packet) {
    return (
      '<div class="model-note"><strong>Spending more is not a score.</strong> The executed audit also increases the two-person design’s declared budget 100-fold without changing its measurements. Its evaluator receipts stay identical.</div><h3>Missing a required observation remains a limitation.</h3><p class="diagram-note">In a separate synthetic support test, all three designs pass the scalar precision criterion. A declared neural observation requirement still changes task attainment:</p><div class="gate-row">' +
      packet.neural_role_gates
        .map(
          (g) =>
            `<div><h3>Neural observation: ${g.declared_neural_support === null ? "unknown" : g.declared_neural_support ? "present" : "absent"}</h3><strong>${{ attained: "Task attained", not_attained: "Task not attained", unknown: "Unresolved" }[g.attainment]}</strong><p>Hypothetical support declaration. No real EEG, brain model or clinical result is implied.</p></div>`,
        )
        .join("") +
      "</div>"
    );
  }
  function erpPlot(packet, N, k, d) {
    const row = packet.rows.find((r) => r.N === N && r.k === k && r.d === d);
    if (!row) throw Error("Scenario unavailable");
    const rows = [
      {
        name: "Current-session state",
        low: row.current_session_root_variance,
        high: row.current_session_root_variance,
      },
      {
        name: "Persistent person mean",
        low: row.persistent_root_variance_lower,
        high: row.persistent_root_variance_upper,
      },
      {
        name: "Population mean",
        low: row.population_root_variance_lower,
        high: row.population_root_variance_upper,
      },
    ];
    const left = 12,
      right = 455,
      scale = (v) => left + ((Math.log10(v) + 4) / 5) * (right - left);
    let body = [0.0001, 0.001, 0.01, 0.1, 1, 10]
      .map((v) =>
        text(
          scale(v),
          24,
          v === 0.0001 ? "10⁻⁴" : v === 0.001 ? "0.001" : num(v),
          {
            "text-anchor": v === 0.0001 ? "start" : v === 10 ? "end" : "middle",
            "font-size": 15,
          },
        ),
      )
      .join("");
    rows.forEach((r, i) => {
      const y = 65 + i * 83,
        a = scale(r.low),
        b = scale(r.high);
      body +=
        text(12, y, r.name, {
          "font-size": 17,
          fill: "#172026",
          "font-weight": 600,
        }) +
        text(
          12,
          y + 24,
          (r.low === r.high ? num(r.low) : num(r.low) + "–" + num(r.high)) +
            " µV",
          { "font-size": 17, fill: "#235bd6" },
        ) +
        `<line x1="${left}" x2="${right}" y1="${y + 44}" y2="${y + 44}" stroke="#e2e8ef" stroke-width="2"/><line x1="${a}" x2="${b}" y1="${y + 44}" y2="${y + 44}" stroke="#235bd6" stroke-width="7"/><circle cx="${a}" cy="${y + 44}" r="5" fill="#235bd6"/><circle cx="${b}" cy="${y + 44}" r="5" fill="#235bd6"/>`;
    });
    body += text(
      12,
      328,
      "Estimation uncertainty · µV · log axis · lower is better",
      { "font-size": 14 },
    );
    return svgShell(
      `ERP P3 conditional design: ${N} people, ${k} visits, ${d} times recording depth`,
      body,
      346,
      480,
    );
  }
  function heatmap(packet, d) {
    const status = {
      robust: [
        "✓",
        "Meets all three tolerances for every allowed variance split",
      ],
      assumption_sensitive: [
        "~",
        "Meets all three tolerances for some allowed variance splits",
      ],
      infeasible: ["×", "No allowed variance split meets all three tolerances"],
      unresolved: ["?", "Unresolved"],
    };
    return (
      '<div class="table-scroll"><table class="heatmap-table"><caption>Participants → · visits ↓ · ' +
      num(d) +
      '× recording depth</caption><thead><tr><th scope="col">Visits</th>' +
      packet.request.grid.N.map((N) => `<th scope="col">${num(N)}</th>`).join(
        "",
      ) +
      "</tr></thead><tbody>" +
      packet.request.grid.k
        .map(
          (k) =>
            '<tr><th scope="row">' +
            k +
            "</th>" +
            packet.request.grid.N.map((N) => {
              const row = packet.rows.find(
                (r) => r.N === N && r.k === k && r.d === d,
              );
              return `<td class="cell-${row.status}" aria-label="${N} participants, ${k} visits: ${status[row.status][1]}" title="${esc(status[row.status][1])}">${status[row.status][0]}</td>`;
            }).join("") +
            "</tr>",
        )
        .join("") +
      '</tbody></table></div><div class="heatmap-legend"><span class="cell-robust">✓ All allowed splits</span><span class="cell-assumption_sensitive">~ Some splits</span><span class="cell-infeasible">× None</span></div>'
    );
  }
  function renderERP(sensitivity, plan) {
    const area = document.getElementById("erp-design-lab");
    area.innerHTML =
      '<div class="design-controls"><label>Participants<select id="erp-people"><option value="2">2 people</option><option value="40" selected>40 people</option><option value="2000">2,000 people</option></select></label><label>Repeat visits<select id="erp-visits"><option value="1">1 visit</option><option value="4">4 visits</option><option value="12">12 visits</option></select></label><label>Recording depth<select id="erp-depth"><option value="1">1× source recording</option><option value="4">4× source recording</option><option value="1000000">1,000,000× stress test</option></select></label></div><div class="chart-grid"><div id="erp-figure-slot" aria-live="polite"></div><div class="release-figure"><h3>What these intervals mean</h3><p>The source measured 40 people in one session. Measurement noise is calibrated to that recording. Additional visits and deeper recordings are hypothetical.</p><p>The source cannot separate persistent differences between people from variation between sessions. The blue ranges show that unresolved split, holding the measured noise estimates fixed.</p><p><strong>These are identification ranges, not confidence intervals.</strong> Their endpoints are not necessarily jointly attainable. The planner below enforces one shared variance split across all targets.</p><p>Neural observation answers a measurement question here. It does not imply neurostimulation, a causal brain model or whole-person biological depth.</p><a class="export-data" href="erp-design-sensitivity.json" download>Download all 27 scenarios ↓</a></div></div><details class="model-note"><summary>Calibration, equations and limits</summary><p>P3 rare-minus-frequent voltage, Pz, 300–600 ms, ERP CORE. A = ' +
      num(sensitivity.A_uV2) +
      " µV² (combined person/session variance); v = " +
      num(sensitivity.v_uV2) +
      ' µV² (contrast measurement variance). With session variance S between 0 and A: current-session variance v/d; persistent-signal variance S/k + v/(kd); population-mean variance (A−S+S/k+v/(kd))/N.</p><p>Recording depth scales retained trial counts proportionally, with the same operator and independent-trial noise. Repeated sessions are conditionally independent. These assumptions may fail at extreme depth. Source estimates also have sampling uncertainty not represented by these ranges.</p><p><a href="https://doi.org/10.1111/psyp.14264">ERP CORE source methodology</a> · <a href="https://github.com/anibiome/anibench-benchmark/tree/main/examples/calibration/erp_core">Code, aggregation and source hashes</a>. Derived ERP figures: CC BY-SA 4.0. Attribution: ERP CORE contributors; Zhang and Luck; AniBench analysis.</p></details><section class="planner-section"><h3>Which designs meet three chosen tolerances together?</h3><p class="section-deck">A worked planning example with invented tolerances: variance ≤1.5 µV² for the current session, ≤1 µV² for the persistent signal, and ≤0.04 µV² for the population mean. These are not AniBench 1 or 2 thresholds.</p><div class="design-controls"><label>Planner recording depth<select id="planner-depth"><option value="1">1× source recording</option><option value="4" selected>4× source recording</option><option value="16">16× source recording</option></select></label></div><div id="planner-grid" aria-live="polite"></div><p class="model-note">Each cell is an executed design-planner result. Green means all allowed person/session variance splits satisfy the three invented tolerances jointly; amber means only some do. It is conditional on fixed calibration estimates and a bounded grid, not biological validation or a global optimum. <a href="erp-design-plan.json" download>Download all 105 design results.</a></p></section>';
    const update = () => {
      const N = Number(document.getElementById("erp-people").value),
        k = Number(document.getElementById("erp-visits").value),
        d = Number(document.getElementById("erp-depth").value);
      document.getElementById("erp-figure-slot").innerHTML = figure(
        "figure-erp",
        "Precision across three questions",
        `${num(N)} people · ${k} ${k === 1 ? "visit" : "visits"} · ${num(d)}× recording depth`,
        erpPlot(sensitivity, N, k, d),
        "<strong>Measured noise; hypothetical design.</strong> Root-variance ranges (µV), conditional on the unresolved person/session split. Not confidence intervals. ERP CORE-derived figure: CC BY-SA 4.0.",
        '<details class="figure-sources"><summary>Data & attribution</summary><p>ERP CORE contributors; Zhang and Luck (2023), https://doi.org/10.1111/psyp.14264. AniBench analysis. CC BY-SA 4.0.</p><p class="source-scroll">Aggregate SHA-256 ' +
          esc(sensitivity.aggregate_sha256) +
          "</p></details>",
      );
    };
    for (const id of ["erp-people", "erp-visits", "erp-depth"])
      document.getElementById(id).addEventListener("change", update);
    document
      .getElementById("planner-depth")
      .addEventListener(
        "change",
        () =>
          (document.getElementById("planner-grid").innerHTML = heatmap(
            plan,
            Number(document.getElementById("planner-depth").value),
          )),
      );
    update();
    document.getElementById("planner-grid").innerHTML = heatmap(plan, 4);
  }
  function wrap(value, limit = 62) {
    const lines = [];
    let line = "";
    for (const word of value.split(/\s+/)) {
      if (line.length + word.length + 1 > limit) {
        lines.push(line);
        line = "";
      }
      line += (line ? " " : "") + word;
    }
    if (line) lines.push(line);
    return lines;
  }
  function exportSVG({
    original,
    width,
    height,
    heading,
    subtitle,
    caption,
    metadata,
  }) {
    const notes = wrap(caption, Math.floor(width / 8));
    const header = 75,
      footer = notes.length * 21 + 46;
    const inner = original.replace(/^<svg[^>]*>/, "").replace(/<\/svg>$/, "");
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height + header + footer}" viewBox="0 0 ${width} ${height + header + footer}"><title>${esc(heading)}</title><desc>${esc(subtitle + ". " + notes.join(" ") + " Sources: " + metadata)}</desc><metadata>${esc(JSON.stringify({ title: heading, evidence: subtitle, caution: notes.join(" "), source_information: metadata, website: "https://anibench.ani-ai-is-alive.chatgpt.site/" }))}</metadata><rect width="100%" height="100%" fill="white"/>${text(8, 25, heading, { fill: "#172026", "font-size": 21, "font-weight": 600 })}${text(8, 51, subtitle, { "font-size": 14 })}<g transform="translate(0,${header})">${inner}</g>${notes.map((line, i) => text(8, height + header + 23 + i * 21, line, { "font-size": 14 })).join("")}${text(8, height + header + footer - 9, "ANIBENCH · source details in SVG metadata", { "font-size": 13 })}</svg>`;
  }
  function download(id) {
    const target = document.getElementById(id),
      svg = target?.querySelector("svg");
    if (!svg) return;
    const metadata =
      (target.querySelector(".figure-sources")?.textContent ||
        "Source-backed AniBench study properties; full records in explorer-atlas.json.") +
      " Links: " +
      [...target.querySelectorAll(".figure-sources a")]
        .map((a) => a.href)
        .join("; ");
    const output = exportSVG({
      original: new XMLSerializer().serializeToString(svg),
      width: svg.viewBox.baseVal.width,
      height: svg.viewBox.baseVal.height,
      heading: target.querySelector("h3").textContent,
      subtitle: target.querySelector(".figure-top p").textContent,
      caption: target.querySelector("figcaption").textContent,
      metadata,
    });
    const blob = new Blob([output], { type: "image/svg+xml" }),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = `anibench-${id}.svg`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function jsonFile(path) {
    const response = await fetch(path, { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw Error("Data unavailable");
    return response.json();
  }
  function eliteCard(card) {
    return `<aside class="release-figure elite-profile"><div><p class="eyebrow">ELITE / SHEBA · OFFICIAL DESCRIPTION</p><h3>A multi-layer study of each person.</h3></div><p>ANI describes ELITE as a healthspan intervention study combining longitudinal molecular, functional, cognitive and digital observations.</p><ul class="profile-domain-list">${card.collection_domains.map((d) => `<li>${esc(d.label)}</li>`).join("")}</ul><p><strong>Numerical comparison is not yet available.</strong> The public description does not supply enrollment, measurement counts or completed-record coverage. This card is not a benchmark score.</p><p class="diagram-note">Cognitive testing does not establish EEG, fMRI or neural stimulation. Collection and approval status need their own evidence.</p><details class="figure-sources"><summary>Source & scope</summary><p><a href="${esc(safeURL(card.source.url))}">ANI’s official ELITE description</a> · checked ${esc(card.source.checked_date)}. Describes intended collections; does not independently verify execution.</p><p class="source-scroll">Source SHA-256 ${esc(card.source.sha256)} · ${esc(card.source.locator)}</p><a href="elite-public-card.json" download>Download the source card</a></details></aside>`;
  }
  function statusRoster(statuses, filters) {
    const rows = statuses.cards.filter(
      (c) =>
        (filters.ethics === "all" || c.ethics.status === filters.ethics) &&
        (filters.publication === "all" ||
          c.publication_sources.some((s) => s.status === filters.publication)),
    );
    return `<details class="status-roster"><summary>Study evidence status · ${rows.length} of ${statuses.cards.length} profiles</summary><p>These labels report what the linked sources say. Unknown means unverified here. Peer-review status applies to each source, not every claim about a study.</p><div class="table-scroll"><table><thead><tr><th>Study</th><th>Source publication</th><th>Ethics / IRB</th></tr></thead><tbody>${rows
      .map((c) => {
        const e = statuses.sources[c.ethics.source_id];
        return `<tr><td>${esc(names[c.study_id] || { "ani-elite-sheba": "ELITE", "dq-senolytic-bone": "D+Q bone trial", "do-health-bio-age": "DO-HEALTH", "sheba-sharp": "SHARP", "motrpac-human-pre-suspension-expanded": "MoTrPAC" }[c.study_id] || c.study_id)}</td><td>${c.publication_sources.map((p) => `<a href="${esc(safeURL(statuses.sources[p.source_id]?.url))}">${esc(publicationLabels[p.status] || p.status)}</a>`).join(" · ")}</td><td>${e ? `<a href="${esc(safeURL(e.url))}">${esc(ethicsLabels[c.ethics.status])}</a>` : esc(ethicsLabels[c.ethics.status] || "Unknown")}<small>${esc(c.ethics.summary || c.ethics.reason || "")}</small></td></tr>`;
      })
      .join(
        "",
      )}</tbody></table></div><a class="export-data" href="study-status-cards.json" download>Download source-bound publication and ethics records</a></details>`;
  }
  async function start() {
    const area = document.getElementById("reported-chart-grid");
    if (!area) return;
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-export]");
      if (button) download(button.dataset.export);
    });
    try {
      const atlas = await jsonFile("explorer-atlas.json");
      const extras = await Promise.allSettled([
        jsonFile("study-status-cards.json"),
        jsonFile("elite-public-card.json"),
      ]);
      const statuses =
        extras[0].status === "fulfilled" ? extras[0].value : null;
      const elite = extras[1].status === "fulfilled" ? extras[1].value : null;
      const controls = document.getElementById("evidence-filters");
      controls.innerHTML =
        '<label>Comparison set<select id="chart-scope"><option value="featured">Featured comparisons</option><option value="all">Expanded comparisons</option></select></label><label>Publication source<select id="publication-filter"><option value="all">All sources</option><option value="peer_reviewed_article">Peer-reviewed only</option><option value="preprint">Preprints only</option><option value="public_participant_protocol">Protocols only</option><option value="registry_record">Registry records only</option><option value="first_party_resource_release">Official data releases</option><option value="first_party_self_report">First-party reports</option><option value="unpublished">Unpublished only</option><option value="unknown">Unknown status</option></select></label><label>Ethics / IRB status<select id="ethics-filter"><option value="all">All approval states</option><option value="approval_reported">Approval reported</option><option value="explicitly_not_approved">Explicitly not approved</option><option value="exempt_reported">Exemption reported</option><option value="unknown">Unknown status</option></select></label><button type="button" id="reset-evidence-filters">Reset filters</button>';
      const update = () => {
        const filters = {
          scope: document.getElementById("chart-scope").value,
          publication: document.getElementById("publication-filter").value,
          ethics: document.getElementById("ethics-filter").value,
        };
        document.getElementById("filter-toggle").textContent =
          `Filters · ${filters.publication === "all" ? "all publication types" : publicationLabels[filters.publication] || "unknown publication"} · ${filters.ethics === "all" ? "all ethics states" : ethicsLabels[filters.ethics] || "unknown ethics"}`;
        area.innerHTML = reported(atlas, statuses, filters);
        const eliteStatus = {
          publication: "first_party_self_report",
          ethics:
            statuses?.cards.find((c) => c.study_id === "ani-elite-sheba")
              ?.ethics.status || "unknown",
        };
        if (elite && matchesStatus(eliteStatus, filters))
          area.insertAdjacentHTML("beforeend", eliteCard(elite));
        const plotted = selectFacts(atlas, [
          ...(filters.scope === "all" ? allFactSets(atlas) : sets).population,
          ...(filters.scope === "all" ? allFactSets(atlas) : sets).time,
          "snyder-ipop-ihmp-106:proteins",
          "uk-biobank:unique_proteins_not_analytes_or_independent_dimensions",
        ]);
        const shown = plotted.filter((f) =>
          matchesStatus(factStatus(f, statuses), filters),
        );
        const counts = filterCounts(
          plotted.map((f) => factStatus(f, statuses)),
          filters,
        );
        document.getElementById("filter-details").textContent =
          `Hidden by publication only: ${counts.publicationOnly}; ethics only: ${counts.ethicsOnly}; both: ${counts.both}. In this comparison set, publication is unknown for ${counts.unknownPublication} source facts and ethics for ${counts.unknownEthics}.`;
        document.getElementById("filter-summary").textContent =
          `${shown.length} of ${plotted.length} selected source facts shown. Filters change inclusion, not the values. ${statuses ? "Unknown approval stays distinct from explicitly no approval." : "Status records unavailable: classification is unknown."}`;
        document.getElementById("status-roster").innerHTML = statuses
          ? statusRoster(statuses, filters)
          : "";
        const url = new URL(location.href);
        for (const [k, v] of Object.entries(filters)) {
          if (k === "scope" ? v === "featured" : v === "all")
            url.searchParams.delete(k);
          else url.searchParams.set(k, v);
        }
        history.replaceState(null, "", url);
      };
      const params = new URLSearchParams(location.search);
      for (const kind of ["publication", "ethics"]) {
        const select = document.getElementById(kind + "-filter");
        if ([...select.options].some((o) => o.value === params.get(kind)))
          select.value = params.get(kind);
        select.addEventListener("change", update);
      }
      const chartScope = document.getElementById("chart-scope");
      if (["featured", "all"].includes(params.get("scope")))
        chartScope.value = params.get("scope");
      chartScope.addEventListener("change", update);
      document
        .getElementById("reset-evidence-filters")
        .addEventListener("click", () => {
          document.getElementById("chart-scope").value = "featured";
          document.getElementById("publication-filter").value = "all";
          document.getElementById("ethics-filter").value = "all";
          update();
        });
      update();
    } catch {
      area.innerHTML =
        '<p class="chart-message">The source records could not be loaded. <a href="explorer-atlas.json">Open the data</a> or reload to retry.</p>';
    }
    const tasks = await Promise.allSettled([
      jsonFile("release-results.json"),
      Promise.all([
        jsonFile("erp-design-sensitivity.json"),
        jsonFile("erp-design-plan.json"),
      ]),
    ]);
    if (tasks[0].status === "fulfilled") {
      document.getElementById("tradeoff-charts").innerHTML = tradeoffs(
        tasks[0].value,
      );
      document
        .getElementById("tradeoff-charts")
        .insertAdjacentHTML("afterend", gates(tasks[0].value));
    } else
      document.getElementById("tradeoff-charts").innerHTML =
        '<p class="chart-message">Model results are unavailable. <a href="release-results.json">Open the result packet</a> or reload to retry.</p>';
    if (tasks[1].status === "fulfilled") renderERP(...tasks[1].value);
    else
      document.getElementById("erp-design-lab").innerHTML =
        '<p class="chart-message">Design results are unavailable. <a href="erp-design-sensitivity.json">Open the calibration data</a> or reload to retry.</p>';
  }
  return {
    allFactSets,
    matchesStatus,
    filterCounts,
    factStatus,
    statusRoster,
    eliteCard,
    tradeoffPlot,
    tradeoffs,
    erpPlot,
    heatmap,
    wrap,
    exportSVG,
    selectFacts,
    factPlot,
    reported,
    sets,
    figure,
    svgShell,
    text,
    esc,
    num,
    safeURL,
    start,
  };
})();
if (typeof document !== "undefined") AniBenchCharts.start();
if (typeof module !== "undefined") module.exports = AniBenchCharts;
