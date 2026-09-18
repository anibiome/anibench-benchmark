"use strict";

// Rendering only. Scientific evaluation and Pareto comparisons come from Python.
const FAMILY_LABELS = {
  intensive: "Biological depth",
  extensive: "Population information",
  longitudinal: "Time & trajectories",
  causal: "Perturbation & causality",
  personalized_sequential: "Personalized learning",
  transport: "Transfer across contexts",
};
const PALETTE = ["#28716a", "#c94428", "#6e60a1", "#8a691e", "#306e9b"];

function human(value) {
  return String(value ?? "Unknown").replaceAll("_", " ");
}

function numberLabel(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Unknown";
  if (value !== 0 && (Math.abs(value) < 0.001 || Math.abs(value) >= 1e9))
    return value.toExponential(3);
  return new Intl.NumberFormat("en", { maximumFractionDigits: 3 }).format(
    value,
  );
}

function knownNumber(fact) {
  return fact &&
    ["known", "exact"].includes(fact.state) &&
    typeof fact.value === "number" &&
    Number.isFinite(fact.value)
    ? fact.value
    : null;
}

function factLabel(fact) {
  if (
    !fact ||
    ![
      "known",
      "exact",
      "reported",
      "conditional",
      "interval",
      "absent",
    ].includes(fact.state)
  )
    return "Unknown";
  if (fact.state === "absent") return "Absent";
  if (fact.state === "interval")
    return `${numberLabel(fact.lower)}–${numberLabel(fact.upper)} (interval)`;
  const value =
    typeof fact.value === "boolean"
      ? fact.value
        ? "Yes"
        : "No"
      : numberLabel(fact.value);
  if (fact.precision === "lower_bound") return `>${value}`;
  return fact.state === "conditional" ? `${value} (conditional)` : value;
}

function displayPopulation(study) {
  return (
    study.publication_facts?.find(
      (fact) => fact.unit === "participants" && reportedNumber(fact) !== null,
    ) || study.population
  );
}

function displayDuration(study) {
  return (
    study.publication_facts?.find(
      (fact) =>
        ["years", "days", "months", "weeks"].includes(fact.unit) &&
        reportedNumber(fact) !== null,
    ) || study.duration
  );
}

function reportedNumber(fact) {
  return fact?.state === "reported" &&
    typeof fact.value === "number" &&
    Number.isFinite(fact.value)
    ? fact.value
    : knownNumber(fact);
}

const TIME_TO_DAYS = { days: 1, weeks: 7, months: 365.25 / 12, years: 365.25 };
const COORDINATES = {
  participants: {
    title: "People in the record",
    unit: "participants",
    note: "Each reported denominator is shown separately. Registry enrollment, analyzed subsets, and completers are not interchangeable and are never added together.",
  },
  duration: {
    title: "Time in the record",
    unit: "days",
    note: "Intervention periods, mean and median follow-up, and scheduled endpoints retain their own meanings. For plotting only, a year is 365.25 days and a month is one twelfth of a year. Original units remain on every row.",
  },
  proteins: {
    title: "Reported protein targets",
    unit: "proteins",
    note: "Assay target counts do not establish independent biological dimensions, assay accuracy, or complete measurements for every person.",
  },
  metabolites: {
    title: "Reported metabolite targets",
    unit: "metabolites",
    note: "Reported metabolite counts retain their assay definitions. Correlation, coverage, noise, and person-event completeness require separate evidence.",
  },
  transcripts: {
    title: "Reported transcript targets",
    unit: "transcripts",
    note: "Transcript counts are assay descriptors. They are not directly comparable to protein or metabolite counts and are never summed into a depth score.",
  },
  cells: {
    title: "Profiled cells",
    unit: "cells",
    note: "Cells are nested within people. Their count is not a participant count or an independent sample size.",
  },
};

function coordinateRows(studies, coordinate) {
  const rows = [];
  for (const study of studies) {
    const base =
      coordinate === "participants"
        ? study.population
        : coordinate === "duration"
          ? study.duration
          : null;
    const candidates = [...(study.publication_facts || [])];
    if (base && knownNumber(base) !== null)
      candidates.push({ ...base, label: "Frozen source record" });
    for (const fact of candidates) {
      const value = reportedNumber(fact);
      const multiplier =
        coordinate === "duration"
          ? TIME_TO_DAYS[fact.unit]
          : fact.unit === coordinate
            ? 1
            : null;
      if (value === null || value <= 0 || multiplier == null) continue;
      rows.push({
        id: study.study_id,
        name: study.name,
        value: value * multiplier,
        label: `${factLabel(fact)} ${fact.unit} · ${fact.label || human(fact.semantics)}`,
        semantics: fact.semantics,
        fact,
      });
    }
  }
  return rows;
}

function safeSourceURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

function filterStudies(studies, query, filter) {
  const term = query.trim().toLocaleLowerCase();
  return studies.filter((study) => {
    const assignment = study.causal_architecture.randomized_policy;
    const matchesFilter =
      filter === "all" ||
      (filter === "randomized" && assignment === true) ||
      (filter === "unknown" && assignment === null);
    // Include named source modules without claiming their unresolved values are known.
    const searchText = [
      study.name,
      study.study_id,
      study.projection_lane,
      ...(study.reported_evidence?.measurements || []).map((row) => row.id),
      ...study.source_binding.authority_objects.map((row) => row.source_id),
    ]
      .join(" ")
      .toLocaleLowerCase();
    return matchesFilter && (!term || searchText.includes(term));
  });
}

function populationRows(studies) {
  return studies
    .map((study) => {
      const fact = displayPopulation(study);
      const value =
        fact.state === "reported" && Number.isFinite(fact.value)
          ? fact.value
          : knownNumber(fact);
      return {
        id: study.study_id,
        name: study.name,
        value,
        semantics: fact.semantics,
        lowerBound: fact.precision === "lower_bound",
      };
    })
    .filter((row) => row.value !== null && row.value > 0);
}

function metricGroups(family) {
  return family.metric_groups?.length
    ? family.metric_groups.map((group) => ({
        label: human(group.group_id),
        metrics: group.native_metrics,
      }))
    : [{ label: null, metrics: family.native_metrics }];
}

function el(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined && content !== null) node.textContent = content;
  if (className) node.className = className;
  return node;
}

function svgEl(tag, attributes = {}, content) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes))
    node.setAttribute(key, String(value));
  if (content !== undefined) node.textContent = content;
  return node;
}

function download(value, filename) {
  const body =
    typeof value === "string" ? value : JSON.stringify(value, null, 2) + "\n";
  const url = URL.createObjectURL(
    new Blob([body], { type: "application/json" }),
  );
  const link = el("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function downloadButton(label, value, filename) {
  const button = el("button", label);
  button.addEventListener("click", () => download(value, filename));
  return button;
}

function sourceLinks(study) {
  const list = el("div", null, "source-list");
  for (const source of study.source_binding.authority_objects) {
    const item = el("div", null, "source-item");
    const url = safeSourceURL(source.url);
    if (url) {
      const link = el("a", `${source.source_id} ↗`);
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      item.append(link);
    } else {
      item.append(el("span", source.source_id));
    }
    item.append(
      el("span", human(source.evidence_class), "caption"),
      el("code", `SHA-256 ${source.sha256}`),
    );
    list.append(item);
  }
  return list;
}

function factDetails(name, fact) {
  const item = el("details");
  item.append(el("summary", `${human(name)}: ${factLabel(fact)}`));
  if (fact?.reason) item.append(el("p", fact.reason, "caption"));
  if (fact?.unit) item.append(el("p", `Unit: ${human(fact.unit)}`, "caption"));
  for (const [source, locator] of Object.entries(fact?.source_locators || {})) {
    item.append(el("p", `${source} · ${locator}`, "caption"));
  }
  return item;
}

function renderPopulation(studies) {
  const target = document.getElementById("population-chart");
  target.replaceChildren();
  const coordinate = document.getElementById("source-coordinate").value;
  const settings = COORDINATES[coordinate];
  const rows = coordinateRows(studies, coordinate);
  document.getElementById("coordinate-title").textContent = settings.title;
  document.getElementById("coordinate-description").textContent = settings.note;
  const caption = document.getElementById("population-caption");
  caption.textContent = `${rows.length} source figures from ${new Set(rows.map((row) => row.id)).size} of ${studies.length} displayed studies. Logarithmic axis in ${settings.unit}; > means a reported lower bound. Missing values are omitted. Order follows the source catalogue, not a rank.`;
  if (!rows.length) {
    target.append(
      el(
        "p",
        "No source-bound values for this coordinate in this selection.",
        "caption",
      ),
    );
    return;
  }
  const width = 370;
  const height = rows.length * 67 + 37;
  const maxExponent = Math.max(
    1,
    Math.ceil(Math.log10(Math.max(...rows.map((row) => row.value)))),
  );
  const minExponent = Math.min(
    0,
    Math.floor(Math.log10(Math.min(...rows.map((row) => row.value)))),
  );
  const x = (value) =>
    5 + ((Math.log10(value) - minExponent) / (maxExponent - minExponent)) * 350;
  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `${settings.title} on a logarithmic axis in ${settings.unit}`,
  });
  svg.append(
    svgEl(
      "title",
      {},
      `${settings.title}; all source denominators and meanings remain separate`,
    ),
  );
  rows.forEach((row, index) => {
    const y = index * 67 + 19;
    const name = row.name.length > 42 ? `${row.name.slice(0, 40)}…` : row.name;
    svg.append(
      svgEl("text", { x: 5, y, fill: "#182a2b", "font-size": 10 }, name),
    );
    const bar = svgEl("rect", {
      x: 5,
      y: y + 8,
      width: Math.max(1, x(row.value) - 5),
      height: 9,
      fill: "#28716a",
    });
    bar.append(
      svgEl("title", {}, `${row.name}: ${row.label} · ${human(row.semantics)}`),
    );
    svg.append(bar);
    svg.append(
      svgEl(
        "text",
        { x: 5, y: y + 34, fill: "#5b6a69", "font-size": 9 },
        row.label.length > 66 ? `${row.label.slice(0, 64)}…` : row.label,
      ),
    );
  });
  for (let exponent = minExponent; exponent <= maxExponent; exponent += 1) {
    const position = x(10 ** exponent);
    svg.append(
      svgEl("line", {
        x1: position,
        x2: position,
        y1: height - 27,
        y2: height - 22,
        stroke: "#5b6a69",
      }),
    );
    svg.append(
      svgEl(
        "text",
        {
          x: position,
          y: height - 9,
          "text-anchor":
            exponent === minExponent
              ? "start"
              : exponent === maxExponent
                ? "end"
                : "middle",
          fill: "#5b6a69",
          "font-size": 9,
        },
        numberLabel(10 ** exponent),
      ),
    );
  }
  target.append(svg);
}

function renderEvidenceComparison(studies) {
  const target = document.getElementById("evidence-comparison");
  target.replaceChildren();
  target.append(
    el(
      "h3",
      studies.length
        ? `Evidence comparison · ${studies.length} selected`
        : "Select studies to inspect their evidence",
    ),
  );
  if (!studies.length) {
    target.append(
      el(
        "p",
        "Select up to four study cards. Sources, denominators, and missing evidence travel with every value.",
        "caption",
      ),
    );
    return;
  }
  target.append(
    el(
      "p",
      "This is a comparison of documented study facts. Capacity geometry is unresolved for these source projections; no biological winner is inferred.",
      "caption",
    ),
  );
  const wrapper = el("div", null, "table-scroll");
  wrapper.tabIndex = 0;
  wrapper.setAttribute("role", "region");
  wrapper.setAttribute("aria-label", "Scrollable study comparison");
  const table = el("table");
  const head = el("thead");
  const top = el("tr");
  top.append(el("th", "Study characteristic"));
  studies.forEach((study) => {
    const cell = el("th", study.name);
    cell.scope = "col";
    top.append(cell);
  });
  head.append(top);
  table.append(head);
  const body = el("tbody");
  const addRow = (label, fill) => {
    const row = el("tr");
    const title = el("th", label);
    title.scope = "row";
    row.append(title);
    studies.forEach((study) => {
      const cell = el("td");
      fill(cell, study);
      row.append(cell);
    });
    body.append(row);
  };
  addRow("Evidence context", (cell, study) =>
    cell.append(el("span", human(study.projection_lane))),
  );
  addRow("Population", (cell, study) => {
    const fact = displayPopulation(study);
    cell.append(
      el("strong", factLabel(fact)),
      el("span", human(fact.semantics), "caption"),
    );
  });
  addRow("Duration", (cell, study) => {
    const fact = displayDuration(study);
    cell.append(
      el("strong", factLabel(fact)),
      el("span", `${human(fact.semantics)} · ${fact.unit}`, "caption"),
    );
  });
  addRow("Literal publication facts", (cell, study) => {
    const facts = study.publication_facts || [];
    if (!facts.length)
      cell.append(el("span", "No literal extraction supplied", "caption"));
    for (const fact of facts) {
      const detail = el("details");
      detail.append(
        el("summary", `${fact.label}: ${factLabel(fact)} ${fact.unit}`),
        el("p", human(fact.semantics), "caption"),
      );
      const url = safeSourceURL(fact.source.url);
      if (url) {
        const link = el("a", `${fact.source_id} ↗`);
        link.href = url;
        detail.append(link);
      }
      detail.append(
        el("p", `Source excerpt: “${fact.excerpt}”`, "caption"),
        el(
          "code",
          `${fact.json_pointer || "Whole source body"} · SHA-256 ${fact.source.sha256}`,
        ),
      );
      cell.append(detail);
    }
    if (facts.length)
      cell.append(
        el(
          "p",
          "Literal extraction checked against complete source bytes. Reported values retain their stated precision; independent scientific review is pending.",
          "caption",
        ),
      );
  });
  addRow("Randomized assignment", (cell, study) =>
    cell.append(
      el(
        "span",
        study.causal_architecture.randomized_policy === null
          ? "Unknown"
          : study.causal_architecture.randomized_policy
            ? "Yes"
            : "No",
      ),
    ),
  );
  addRow("Reported source fields", (cell, study) => {
    for (const group of ["population", "timeline", "design"]) {
      for (const [name, fact] of Object.entries(
        study.reported_evidence?.[group] || {},
      )) {
        if (fact && typeof fact === "object" && "state" in fact)
          cell.append(factDetails(name, fact));
      }
    }
  });
  addRow("Measurement evidence", (cell, study) => {
    for (const module of study.reported_evidence?.measurements || []) {
      const details = el("details");
      details.append(el("summary", human(module.id)));
      for (const key of [
        "participants",
        "observation_events",
        "targets",
        "completeness",
      ])
        details.append(factDetails(key, module[key]));
      cell.append(details);
    }
    cell.append(
      el(
        "p",
        "A named module is a source-record label, not verified complete coverage.",
        "caption",
      ),
    );
  });
  addRow("Capacity assessment", (cell, study) => {
    for (const [id, label] of Object.entries(FAMILY_LABELS))
      cell.append(
        el(
          "p",
          `${label}: ${study.family_eligibility[id].state === "not_scoreable" ? "unresolved" : human(study.family_eligibility[id].state)}`,
          "caption",
        ),
      );
  });
  addRow("Evidence needed", (cell, study) => {
    const list = el("ul");
    study.open_gates.forEach((gate) => list.append(el("li", human(gate))));
    cell.append(list);
  });
  addRow("Original sources", (cell, study) => cell.append(sourceLinks(study)));
  addRow("Projection fingerprint", (cell, study) =>
    cell.append(el("code", study.source_binding.source_projection_sha256)),
  );
  table.append(body);
  wrapper.append(table);
  target.append(wrapper);
}

function renderMetric(rows, label, unit) {
  const block = el("div", null, "metric-block");
  block.append(
    el("p", label, "metric-label"),
    el("p", human(unit), "metric-unit"),
  );
  const numbers = rows
    .map((row) => row.value)
    .filter((value) => typeof value === "number" && Number.isFinite(value));
  const max = Math.max(0, ...numbers);
  const height = rows.length * 48 + 17;
  const svg = svgEl("svg", {
    viewBox: `0 0 470 ${height}`,
    role: "img",
    "aria-label": `${label}, ${human(unit)}, independent linear scale from zero`,
    class: "metric-chart",
  });
  svg.append(
    svgEl(
      "title",
      {},
      rows
        .map(
          (row) =>
            `${row.label}: ${typeof row.value === "boolean" ? (row.value ? "Yes" : "No") : numberLabel(row.value)}`,
        )
        .join("; "),
    ),
  );
  rows.forEach((row, index) => {
    const y = index * 48 + 13;
    const color = PALETTE[index % PALETTE.length];
    const displayLabel =
      row.label.length > 43 ? `${row.label.slice(0, 40)}…` : row.label;
    svg.append(
      svgEl(
        "text",
        { x: 0, y, "font-size": 17, fill: "#5b6a69" },
        displayLabel,
      ),
    );
    const value = row.value;
    const finite = typeof value === "number" && Number.isFinite(value);
    if (finite) {
      svg.append(
        svgEl("line", {
          x1: 0,
          x2: 340,
          y1: y + 15,
          y2: y + 15,
          stroke: "#edf1ec",
          "stroke-width": 10,
        }),
      );
      // Each metric has its own native axis. Bars are not percentages or attainment.
      if (value > 0 && max > 0)
        svg.append(
          svgEl("rect", {
            x: 0,
            y: y + 10,
            width: (value / max) * 340,
            height: 10,
            fill: color,
          }),
        );
    }
    const text =
      typeof value === "boolean" ? (value ? "Yes" : "No") : numberLabel(value);
    svg.append(
      svgEl(
        "text",
        {
          x: finite ? 467 : 0,
          y: y + 21,
          "text-anchor": finite ? "end" : "start",
          "font-size": 18,
          fill: finite ? color : "#5b6a69",
        },
        text,
      ),
    );
  });
  block.append(svg);
  return block;
}

function renderWorkspace(packet, scenarioIndex = 0) {
  const target = document.getElementById("workspace-result");
  target.replaceChildren();
  const receipts = packet.receipts;
  const comparison = packet.comparison;
  const labels =
    packet.labels ||
    Object.fromEntries(
      receipts.map((receipt) => [receipt.protocol_id, receipt.protocol_id]),
    );
  const heading = el("div", null, "workspace-result-head");
  heading.append(
    el(
      "h3",
      packet.illustrative
        ? "Illustrative mechanics · two hypothetical designs"
        : `${receipts.length} study assessment${receipts.length === 1 ? "" : "s"}`,
    ),
  );
  const buttons = el("div", null, "download-actions");
  if (comparison)
    buttons.append(
      downloadButton(
        "Comparison receipt ↓",
        packet.comparison_document,
        "anibench-comparison.json",
      ),
    );
  receipts.forEach((receipt, index) =>
    buttons.append(
      downloadButton(
        `Eval ${index + 1} ↓`,
        packet.receipt_documents[index],
        `anibench-eval-${index + 1}.json`,
      ),
    ),
  );
  if (packet.protocol_documents)
    packet.protocol_documents.forEach((document, index) =>
      buttons.append(
        downloadButton(
          `Protocol ${index + 1} ↓`,
          document,
          `anibench-protocol-${index + 1}.json`,
        ),
      ),
    );
  heading.append(buttons);
  target.append(heading);
  if (receipts.length === 1 && receipts[0].scenarios.length > 1) {
    const label = el("label", "Scenario ");
    const select = el("select");
    select.setAttribute("aria-label", "Assessment scenario");
    receipts[0].scenarios.forEach((scenario, index) => {
      const option = el("option", scenario.scenario_id);
      option.value = String(index);
      option.selected = index === scenarioIndex;
      select.append(option);
    });
    select.addEventListener("change", () =>
      renderWorkspace(packet, Number(select.value)),
    );
    label.append(select);
    target.append(label);
    target.append(
      el(
        "p",
        "Each scenario is conditional on its own assumptions. Select a scenario to inspect its native metrics; the download preserves every scenario.",
        "caption",
      ),
    );
  }
  const description = packet.illustrative
    ? "Synthetic examples demonstrate the mathematics only. They are not Elite, an external trial, a biological calibration, or evidence of an actual study's performance."
    : receipts
        .map(
          (receipt) =>
            `${labels[receipt.protocol_id]}: ${human(receipt.claim_class)} · ${human(receipt.geometry_authority_state)}`,
        )
        .join(". ");
  target.append(el("p", description, "notice"));
  if (packet.source_objects)
    target.append(
      el(
        "p",
        "Synthetic source objects and recipe hashes are included in the full packet below.",
        "caption",
      ),
    );
  target.append(
    el(
      "p",
      "Each metric uses its own linear axis in native units. Bar widths are relative to the displayed values, not a target or a percentage of biological understanding. Zero is displayed explicitly; unknown has no bar.",
      "caption",
    ),
  );
  const grid = el("div", null, "family-charts");
  const families = receipts[0].scenarios[scenarioIndex].families;
  for (const family of families) {
    const card = el("article", null, "family-chart");
    card.append(
      el("h3", FAMILY_LABELS[family.family_id] || human(family.family_id)),
    );
    const compared = comparison?.families.find(
      (item) => item.family_id === family.family_id,
    );
    if (compared) {
      const message = compared.comparison_eligible
        ? `Pareto frontier: ${compared.pareto_front_protocol_ids.map((id) => labels[id] || id).join(" · ")}. Frontier membership is not an ordinal rank.`
        : `Comparison unresolved: ${compared.blocker_codes.map(human).join("; ")}`;
      card.append(el("p", message, "front"));
    }
    for (const group of metricGroups(family)) {
      for (const metric of group.metrics) {
        const rows = receipts.map((receipt) => {
          const otherFamily = receipt.scenarios[scenarioIndex].families.find(
            (item) => item.family_id === family.family_id,
          );
          const matchingGroup = metricGroups(otherFamily).find(
            (item) => item.label === group.label,
          );
          const otherMetric = matchingGroup?.metrics.find(
            (item) => item.metric_id === metric.metric_id,
          );
          return {
            label: labels[receipt.protocol_id],
            value: otherMetric?.value ?? null,
          };
        });
        card.append(
          renderMetric(
            rows,
            `${group.label ? `${group.label} · ` : ""}${metric.label || human(metric.metric_id)}`,
            metric.unit,
          ),
        );
      }
    }
    grid.append(card);
  }
  target.append(grid);
  const details = el("details", null, "result-receipt");
  details.append(
    el(
      "summary",
      "Inspect assessment values; downloads preserve original documents",
    ),
    el("pre", JSON.stringify(packet, null, 2)),
  );
  const archive = {
    schema_version: "anibench.explorer-document-archive.v1",
    illustrative: packet.illustrative || false,
    labels,
    receipt_documents: packet.receipt_documents,
    comparison_document: packet.comparison_document,
    protocol_documents: packet.protocol_documents,
    source_objects: packet.source_objects,
  };
  target.append(
    details,
    downloadButton(
      "Download full packet ↓",
      archive,
      "anibench-workspace.json",
    ),
  );
}

async function jsonResponse(response) {
  if (!response.ok) {
    let reason = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.error) reason = body.error;
    } catch {
      /* HTTP status remains informative. */
    }
    throw new Error(reason);
  }
  return response.json();
}

async function postDocument(route, body) {
  const response = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  if (!response.ok) return jsonResponse(response);
  return response.text();
}

async function readFile(file) {
  if (!file || file.size > 7_500_000)
    throw new Error("Select a JSON file smaller than 7.5 MB.");
  try {
    const raw = await file.text();
    JSON.parse(raw);
    return raw;
  } catch {
    throw new Error(`Invalid JSON in ${file.name}`);
  }
}

async function startExplorer() {
  let atlas;
  let live = false;
  const selected = new Set();
  const status = document.getElementById("atlas-status");
  const query = document.getElementById("search");
  const filter = document.getElementById("study-filter");
  const workspaceStatus = document.getElementById("workspace-status");
  try {
    const response = await fetch("/api/health");
    live = response.ok && (await response.json()).service === "anibench-studio";
  } catch {
    /* A static export intentionally has no local evaluator. */
  }
  document.getElementById("runtime-note").textContent = live
    ? "Local evaluator connected. Files are processed by this Studio instance."
    : "Static edition. For your own files, install AniBench and run: anibench studio. The source atlas and illustrative comparisons work here.";
  document.getElementById("protocol-file").disabled = !live;
  document.getElementById("receipt-files").disabled = !live;
  function renderStudies() {
    const visible = filterStudies(atlas.studies, query.value, filter.value);
    const list = document.getElementById("study-list");
    list.replaceChildren();
    document.getElementById("study-count").textContent =
      `${visible.length} of ${atlas.study_count} studies · ${selected.size} selected`;
    if (!visible.length)
      list.append(
        el("p", "No studies match this search. Try a shorter term.", "caption"),
      );
    for (const study of visible) {
      const card = el(
        "article",
        null,
        `study-card${selected.has(study.study_id) ? " selected" : ""}`,
      );
      card.append(
        el("span", human(study.projection_lane), "study-lane"),
        el("h3", study.name),
      );
      const stats = el("dl", null, "study-stats");
      const population = displayPopulation(study);
      const duration = displayDuration(study);
      for (const [label, fact] of [
        ["People · source denominator", population],
        [`Span · ${duration.unit}`, duration],
      ]) {
        const block = el("div");
        block.append(
          el(
            "dd",
            factLabel(fact),
            factLabel(fact) === "Unknown" ? "unknown" : "",
          ),
          el("dt", label),
        );
        stats.append(block);
      }
      card.append(
        stats,
        el(
          "p",
          `${population.label || "Frozen source record"} · ${human(population.semantics)}`,
          "caption",
        ),
      );
      const tail = el("div", null, "card-tail");
      tail.append(
        el(
          "small",
          `${study.source_binding.authority_objects.length} source objects`,
        ),
      );
      const button = el(
        "button",
        selected.has(study.study_id) ? "Selected ✓" : "Compare +",
      );
      button.setAttribute("aria-pressed", String(selected.has(study.study_id)));
      button.setAttribute("aria-label", `Compare ${study.name}`);
      button.addEventListener("click", () => {
        if (selected.has(study.study_id)) selected.delete(study.study_id);
        else if (selected.size < 4) selected.add(study.study_id);
        else {
          status.textContent =
            "Compare up to four studies at a time. Remove one selection to add another.";
          return;
        }
        renderStudies();
      });
      tail.append(button);
      card.append(tail);
      list.append(card);
    }
    renderPopulation(visible);
    renderEvidenceComparison(
      atlas.studies.filter((study) => selected.has(study.study_id)),
    );
  }
  try {
    atlas = await jsonResponse(
      await fetch(live ? "/api/v2/comparator-atlas" : "explorer-atlas.json"),
    );
    if (
      atlas.schema_version !== "anibench.studio-comparator-atlas.v1" ||
      atlas.overall_scalar !== null ||
      atlas.public_rank_emission_permitted !== false
    )
      throw new Error("Unexpected atlas contract.");
    status.textContent = `${atlas.study_count} source-bound studies. ${atlas.comparison_eligible_study_count} currently have complete shared-basis geometry for capacity comparison. This snapshot preserves unresolved facts and links the original sources.`;
    for (const id of [
      "uk-biobank",
      "snyder-ipop-ihmp-106",
      "circulate-tpe-ivig",
    ])
      if (atlas.studies.some((study) => study.study_id === id))
        selected.add(id);
    renderStudies();
    query.addEventListener("input", renderStudies);
    filter.addEventListener("change", renderStudies);
    document
      .getElementById("source-coordinate")
      .addEventListener("change", renderStudies);
    const downloadAtlas = document.getElementById("download-atlas");
    downloadAtlas.disabled = false;
    downloadAtlas.addEventListener("click", () =>
      download(atlas, "anibench-source-atlas.json"),
    );
    document.getElementById("clear-selection").addEventListener("click", () => {
      selected.clear();
      renderStudies();
    });
  } catch (error) {
    status.textContent = `Could not load the source atlas: ${error.message}`;
    status.classList.add("error");
  }

  async function run(action, pending) {
    workspaceStatus.textContent = pending;
    workspaceStatus.classList.remove("error");
    const controls = ["load-demo", "protocol-file", "receipt-files"].map((id) =>
      document.getElementById(id),
    );
    controls.forEach((control) => {
      control.disabled = true;
    });
    document.getElementById("workspace-result").replaceChildren();
    try {
      const packet = await action();
      renderWorkspace(packet);
      workspaceStatus.textContent =
        "Assessment ready. Inspect each native metric and download the receipts below.";
    } catch (error) {
      workspaceStatus.textContent = error.message;
      workspaceStatus.classList.add("error");
    } finally {
      controls[0].disabled = false;
      controls.slice(1).forEach((control) => {
        control.disabled = !live;
        control.value = "";
      });
    }
  }
  document
    .getElementById("load-demo")
    .addEventListener("click", () =>
      run(
        async () =>
          jsonResponse(
            await fetch(live ? "/api/v3/explorer-demo" : "explorer-demo.json"),
          ),
        "Evaluating the illustrative designs…",
      ),
    );
  document
    .getElementById("protocol-file")
    .addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (!file) return;
      run(async () => {
        const protocolDocument = await readFile(file);
        const document = await postDocument("/api/v3/eval", protocolDocument);
        return {
          receipts: [JSON.parse(document)],
          receipt_documents: [document],
          protocol_documents: [protocolDocument],
          comparison: null,
        };
      }, "Evaluating protocol geometry…");
    });
  document
    .getElementById("receipt-files")
    .addEventListener("change", (event) => {
      const files = [...event.target.files];
      if (!files.length) return;
      run(async () => {
        if (files.length < 2 || files.length > 20)
          throw new Error("Select between 2 and 20 canonical eval receipts.");
        if (files.reduce((sum, file) => sum + file.size, 0) > 7_500_000)
          throw new Error("Combined receipts must be smaller than 7.5 MB.");
        const documents = await Promise.all(files.map(readFile));
        const document = await postDocument(
          "/api/v3/compare",
          JSON.stringify({ receipt_documents: documents }),
        );
        return {
          receipts: documents.map((raw) => JSON.parse(raw)),
          receipt_documents: documents,
          comparison: JSON.parse(document),
          comparison_document: document,
        };
      }, "Verifying receipt hashes and comparison basis…");
    });
}

if (typeof document !== "undefined") startExplorer();
if (typeof module !== "undefined")
  module.exports = {
    human,
    numberLabel,
    knownNumber,
    factLabel,
    safeSourceURL,
    filterStudies,
    populationRows,
    coordinateRows,
    metricGroups,
    displayPopulation,
    displayDuration,
    readFile,
  };
