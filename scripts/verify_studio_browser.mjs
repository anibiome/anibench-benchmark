#!/usr/bin/env node

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import {spawn} from "node:child_process";

function parseArgs(argv) {
  const result = {url: null, downloadsDir: null, browserBinary: null};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === "--url") result.url = argv[++index];
    else if (key === "--downloads-dir") result.downloadsDir = argv[++index];
    else if (key === "--browser-binary") result.browserBinary = argv[++index];
    else throw new Error(`Unknown argument: ${key}`);
  }
  if (!result.url) throw new Error("--url is required");
  if (!result.downloadsDir) throw new Error("--downloads-dir is required");
  return result;
}

function findBrowser(explicit) {
  const candidates = [
    explicit,
    process.env.CHROME_BIN,
    process.env.GOOGLE_CHROME_BIN,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser"
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error(
    "Chrome or Chromium is required for the installed Studio browser gate; set CHROME_BIN"
  );
}

async function waitForDevToolsPort(profile, browser, timeoutMs = 20000) {
  const activePortFile = path.join(profile, "DevToolsActivePort");
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    if (browser.exitCode !== null) {
      throw new Error(`Chrome exited before opening DevTools (exit ${browser.exitCode})`);
    }
    try {
      const [portText] = fs.readFileSync(activePortFile, "utf8").trim().split(/\r?\n/);
      const port = Number(portText);
      if (Number.isInteger(port) && port > 0 && port <= 65535) return port;
      lastError = new Error(`invalid DevToolsActivePort value ${JSON.stringify(portText)}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(
    `Timed out waiting for ${activePortFile}: ${lastError?.message || "unknown error"}`
  );
}

async function waitForJson(url, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, {cache: "no-store"});
      if (response.ok) return await response.json();
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for ${url}: ${lastError?.message || "unknown error"}`);
}

class CdpClient {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(`${message.error.code}: ${message.error.message}`));
        else pending.resolve(message.result || {});
        return;
      }
      for (const listener of this.listeners.get(message.method) || []) listener(message.params || {});
    });
    socket.addEventListener("close", () => {
      for (const pending of this.pending.values()) pending.reject(new Error("CDP socket closed"));
      this.pending.clear();
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) || [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.socket.send(JSON.stringify({id, method, params}));
    });
  }
}

async function connectWebSocket(url) {
  const socket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  return socket;
}

async function evaluate(client, expression) {
  const result = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true
  });
  if (result.exceptionDetails) {
    const description = result.exceptionDetails.exception?.description
      || result.exceptionDetails.text
      || "browser evaluation failed";
    throw new Error(description);
  }
  return result.result?.value;
}

async function waitForExpression(client, expression, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      if (await evaluate(client, `Boolean(${expression})`)) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for browser state ${expression}: ${lastError?.message || "false"}`);
}

async function waitForDownload(directory, prefix, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const candidates = fs.readdirSync(directory)
      .filter(name => name.startsWith(prefix) && name.endsWith(".json"))
      .filter(name => !name.endsWith(".crdownload"))
      .sort();
    if (candidates.length === 1) {
      const file = path.join(directory, candidates[0]);
      try {
        const bytes = fs.readFileSync(file);
        const payload = JSON.parse(bytes.toString("utf8"));
        return {
          name: candidates[0],
          sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
          payload
        };
      } catch {
        // Chrome may have renamed the file just before the final write becomes visible.
      }
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for download prefix ${prefix}`);
}

async function captureHash(client) {
  const screenshot = await client.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false,
    fromSurface: true
  });
  return crypto.createHash("sha256").update(Buffer.from(screenshot.data, "base64")).digest("hex");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (typeof WebSocket !== "function") {
    throw new Error("Node.js 22 or newer is required for the dependency-free CDP browser gate");
  }
  const browserBinary = findBrowser(args.browserBinary);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "anibench-chrome-"));
  fs.mkdirSync(args.downloadsDir, {recursive: true});
  const browser = spawn(browserBinary, [
    "--headless=new",
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=0",
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-features=Translate,MediaRouter",
    "--disable-gpu",
    "--disable-sync",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-sandbox",
    "about:blank"
  ], {stdio: ["ignore", "pipe", "pipe"]});
  let browserStdout = "";
  let browserStderr = "";
  browser.stdout.on("data", chunk => { browserStdout += chunk.toString(); });
  browser.stderr.on("data", chunk => { browserStderr += chunk.toString(); });
  let socket;
  try {
    const debugPort = await waitForDevToolsPort(profile, browser);
    const version = await waitForJson(`http://127.0.0.1:${debugPort}/json/version`);
    const create = await fetch(
      `http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent("about:blank")}`,
      {method: "PUT"}
    );
    assert.equal(create.ok, true, `Could not create browser target: HTTP ${create.status}`);
    const target = await create.json();
    socket = await connectWebSocket(target.webSocketDebuggerUrl);
    const client = new CdpClient(socket);
    const pageErrors = [];
    const networkEvents = [];
    client.on("Runtime.exceptionThrown", event => {
      pageErrors.push(event.exceptionDetails?.exception?.description || event.exceptionDetails?.text);
    });
    client.on("Network.requestWillBeSent", event => {
      if (event.request?.url?.includes("/api/v2/level1-assessment")) {
        networkEvents.push({
          phase: "request",
          requestId: event.requestId,
          method: event.request.method,
          url: event.request.url,
          postDataBytes: event.request.postData
            ? Buffer.byteLength(event.request.postData, "utf8")
            : null
        });
      }
    });
    client.on("Network.responseReceived", event => {
      if (event.response?.url?.includes("/api/v2/level1-assessment")) {
        networkEvents.push({
          phase: "response",
          requestId: event.requestId,
          status: event.response.status,
          mimeType: event.response.mimeType,
          encodedDataLength: event.response.encodedDataLength
        });
      }
    });
    client.on("Network.loadingFinished", event => {
      if (networkEvents.some(row => row.requestId === event.requestId)) {
        networkEvents.push({
          phase: "finished",
          requestId: event.requestId,
          encodedDataLength: event.encodedDataLength
        });
      }
    });
    client.on("Network.loadingFailed", event => {
      if (networkEvents.some(row => row.requestId === event.requestId)) {
        networkEvents.push({
          phase: "failed",
          requestId: event.requestId,
          errorText: event.errorText,
          canceled: event.canceled || false,
          blockedReason: event.blockedReason || null
        });
      }
    });
    await Promise.all([
      client.send("Page.enable"),
      client.send("Runtime.enable"),
      client.send("Network.enable"),
      client.send("Accessibility.enable")
    ]);
    await client.send("Browser.setDownloadBehavior", {
      behavior: "allow",
      downloadPath: path.resolve(args.downloadsDir),
      eventsEnabled: true
    });
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 1000,
      deviceScaleFactor: 1,
      mobile: false
    });
    await client.send("Page.navigate", {url: args.url});
    await waitForExpression(
      client,
      "document.readyState === 'complete' && document.querySelector('#ctgov-search-form') && document.querySelector('#ctgov-intake-form') && document.querySelector('#capacity-form') && document.querySelector('#protocol-optimizer-form')"
    );

    const loaded = await evaluate(client, `(async () => {
      const read = async (url, options) => {
        const response = await fetch(url, options);
        const contentType = response.headers.get("content-type") || "";
        const body = contentType.includes("application/json") ? await response.json() : await response.text();
        return {status: response.status, contentType, body};
      };
      return {
        title: document.title,
        viewport: document.querySelector('meta[name="viewport"]')?.content || null,
        scriptLoaded: [...document.scripts].some(node => node.src.endsWith('/v2.js')),
        stylesheetLoaded: [...document.styleSheets].some(sheet => (sheet.href || '').endsWith('/v2.css')),
        registryIntake: {
          searchForm: Boolean(document.querySelector('#ctgov-search-form')),
          exactForm: Boolean(document.querySelector('#ctgov-intake-form')),
          boundaryText: document.querySelector('#ctgov-result')?.textContent || ''
        },
        health: await read('/api/health'),
        atlas: await read('/api/v2/comparator-atlas'),
        protocolExample: await read('/protocol-capacity-example.json'),
        optimizerExample: await read('/optimizer-protocol-example.json'),
        level1Authority: await read('/api/v2/level1-authority'),
        retiredLevel1Template: await read('/api/v2/level1-template'),
        retiredPreview: await read('/api/preview', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}),
        retiredSuite: await read('/api/v2/benchmark-suite', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'})
      };
    })()`);
    assert.match(loaded.title, /AniBench/i);
    assert.equal(loaded.viewport, "width=device-width, initial-scale=1");
    assert.equal(loaded.scriptLoaded, true);
    assert.equal(loaded.stylesheetLoaded, true);
    assert.equal(loaded.registryIntake.searchForm, true);
    assert.equal(loaded.registryIntake.exactForm, true);
    assert.match(loaded.registryIntake.boundaryText, /only carries its NCT identifier/i);
    assert.equal(loaded.health.status, 200);
    assert.equal(loaded.health.body.status, "ok");
    assert.equal(loaded.atlas.status, 200);
    assert.equal(loaded.atlas.body.schema_version, "anibench.studio-comparator-atlas.v1");
    assert.equal(loaded.atlas.body.study_count, 16);
    assert.equal(loaded.atlas.body.overall_scalar, null);
    assert.equal(loaded.atlas.body.public_rank_emission_permitted, false);
    assert.equal(loaded.protocolExample.status, 200);
    assert.match(loaded.protocolExample.body.schema_version, /^anibench\.protocol-capacity-input\./);
    assert.equal(loaded.optimizerExample.status, 200);
    assert.match(loaded.optimizerExample.body.schema_version, /^anibench\.optimizer-protocol-input\./);
    assert.equal(loaded.level1Authority.status, 200);
    assert.equal(loaded.level1Authority.body.schema_version, "anibench.level1-role-aware-authority-summary.v1");
    assert.equal(loaded.level1Authority.body.readback.validation.family_count, 6);
    assert.equal(loaded.level1Authority.body.readback.validation.direct_mutable_outcome_count, 22);
    for (const retired of [loaded.retiredPreview, loaded.retiredSuite, loaded.retiredLevel1Template]) {
      assert.equal(retired.status, 410);
      assert.equal(retired.body.contract, "anibench.retired-route.v1");
      assert.equal(retired.body.promotion_allowed, false);
    }
    const accessibilityTree = await client.send("Accessibility.getFullAXTree");
    const accessibleNodes = accessibilityTree.nodes || [];
    const hasAccessibleNode = (role, name) => accessibleNodes.some(node =>
      node.role?.value === role && node.name?.value === name && node.ignored !== true
    );
    for (const [role, name] of [
      ["searchbox", "Search ClinicalTrials.gov"],
      ["textbox", "Exact NCT identifier"],
      ["button", "Capture search page"],
      ["button", "Lock registry snapshot"],
      ["button", "Compile trial design"],
      ["button", "Assess six trial dimensions"]
    ]) {
      assert.equal(hasAccessibleNode(role, name), true, `Missing accessible ${role}: ${name}`);
    }

    await evaluate(client, `(() => {
      const set = (selector, value, change = false) => {
        const control = document.querySelector(selector);
        control.value = String(value);
        if (change) control.dispatchEvent(new Event('change', {bubbles: true}));
      };
      set('#study-id', 'future-10m-personalized-trial');
      set('#study-name', 'Ten-million-person deep adaptive trial');
      set('#assessment-lane', 'design_preview');
      set('#population-state', 'conditional', true);
      set('#population-value', '10000000');
      set('#population-semantics', 'planned_enrollment');
      set('#duration-state', 'conditional', true);
      set('#duration-value', '3650');
      set('#duration-semantics', 'intervention_duration_days');
      set('#policy-arms', '8');
      set('#operator-families', 'nutrition, exercise, sleep, combination');
      set('#randomized-policy', 'true');
      set('#concurrent-control', 'true');
      set('#adaptive-reassignment', 'true');
      set('#within-policy-randomized', 'true');
      document.querySelector('#measurement-modules').replaceChildren();
      addModule({module_id: 'multi-omics', label: 'Multi-omics', evidence_state: 'conditional', events_per_participant: 3650});
      addModule({module_id: 'digital-phenotyping', label: 'Digital phenotyping', evidence_state: 'conditional', events_per_participant: 36500});
      addModule({module_id: 'functional-perturbation', label: 'Functional perturbation', evidence_state: 'conditional', events_per_participant: 332150});
      document.querySelector('#design-form').requestSubmit();
    })()`);
    await waitForExpression(client, `document.querySelector('#design-status').textContent.startsWith('Compiled candidate receipt')`);
    const plannedDesignUi = await evaluate(client, `({
      status: document.querySelector('#design-status').textContent,
      resultText: document.querySelector('#design-result-content').textContent,
      familyReadinessCards: document.querySelectorAll('#design-family-readiness .family-readiness-card').length,
      downloadVisible: document.querySelector('#download-design').getBoundingClientRect().width > 0
    })`);
    assert.equal(plannedDesignUi.familyReadinessCards, 6);
    assert.match(plannedDesignUi.resultText, /10000000 participants/);
    assert.match(plannedDesignUi.resultText, /3723000000000 participant_module_observations/i);
    assert.equal(plannedDesignUi.downloadVisible, true);
    await evaluate(client, `document.querySelector('#download-design').click()`);
    const plannedDesignDownload = await waitForDownload(args.downloadsDir, "anibench-v2-design-handoff-");
    assert.equal(plannedDesignDownload.payload.schema_version, "anibench.studio-design-handoff.v1");
    assert.equal(plannedDesignDownload.payload.assessment_lane, "design_preview");
    assert.equal(
      plannedDesignDownload.payload.design_assessment.coordinates.population.value,
      10000000
    );
    assert.equal(
      plannedDesignDownload.payload.design_assessment.derived_coordinates.participant_module_observation_total.value,
      3723000000000
    );
    fs.unlinkSync(path.join(args.downloadsDir, plannedDesignDownload.name));
    await evaluate(client, `document.querySelector('#download-design').click()`);
    const plannedDesignReplay = await waitForDownload(args.downloadsDir, "anibench-v2-design-handoff-");
    assert.equal(plannedDesignReplay.sha256, plannedDesignDownload.sha256);
    fs.unlinkSync(path.join(args.downloadsDir, plannedDesignReplay.name));

    await evaluate(client, `(() => {
      document.querySelector('#assessment-lane').value = 'realized';
      document.querySelector('#design-form').requestSubmit();
    })()`);
    await waitForExpression(
      client,
      `document.querySelector('#design-status').textContent.startsWith('Compiled candidate receipt') && document.querySelector('#design-receipt').textContent.includes('realized')`
    );
    await evaluate(client, `document.querySelector('#download-design').click()`);
    const realizedDesignDownload = await waitForDownload(args.downloadsDir, "anibench-v2-design-handoff-");
    assert.equal(realizedDesignDownload.payload.assessment_lane, "realized");
    assert.notEqual(
      realizedDesignDownload.payload.design_input_sha256,
      plannedDesignDownload.payload.design_input_sha256
    );
    assert.deepEqual(
      realizedDesignDownload.payload.design_assessment.coordinates,
      plannedDesignDownload.payload.design_assessment.coordinates
    );
    assert.deepEqual(
      realizedDesignDownload.payload.design_assessment.derived_coordinates,
      plannedDesignDownload.payload.design_assessment.derived_coordinates
    );

    await evaluate(client, `document.querySelector('#load-capacity-example').click()`);
    await waitForExpression(client, `document.querySelector('#capacity-input').value.includes('anibench.protocol-capacity-input')`);
    await evaluate(client, `(() => {
      const protocol = JSON.parse(document.querySelector('#capacity-input').value);
      protocol.protocol_id = 'future-10m-personalized-trial';
      document.querySelector('#capacity-input').value = JSON.stringify(protocol, null, 2);
    })()`);
    await evaluate(client, `document.querySelector('#capacity-form').requestSubmit()`);
    await waitForExpression(client, `document.querySelector('#capacity-status').textContent.startsWith('Compiled ')`, 45000);
    const capacityUi = await evaluate(client, `({
      status: document.querySelector('#capacity-status').textContent,
      cards: document.querySelectorAll('#capacity-result .capacity-family-card').length,
      text: document.querySelector('#capacity-result').textContent,
      downloadButtons: document.querySelectorAll('#capacity-result .receipt-action').length
    })`);
    assert.equal(capacityUi.cards, 6);
    assert.match(capacityUi.status, /no overall scalar/);
    assert.match(capacityUi.text, /Overall scalar\s*Not emitted/);
    assert.match(capacityUi.text, /Public rank\s*Not permitted/);
    assert.equal(capacityUi.downloadButtons, 1);
    await evaluate(client, `document.querySelector('#capacity-result .receipt-action').click()`);
    const capacityDownload = await waitForDownload(args.downloadsDir, "anibench-v2-studio-workflow-");
    assert.equal(capacityDownload.payload.schema_version, "anibench.studio-workflow-receipt.v1");
    assert.equal(
      capacityDownload.payload.design_binding.state,
      "identifier_match_only_not_semantic_binding"
    );
    assert.equal(
      capacityDownload.payload.design_binding.reason,
      "matching_identifier_without_content_hashed_pointer_crosswalk"
    );
    assert.ok(capacityDownload.payload.design_binding.missing_design_geometry_pointers.length > 0);
    assert.equal(capacityDownload.payload.capacity_result.overall_scalar, null);
    assert.equal(capacityDownload.payload.capacity_result.public_rank_emission_permitted, false);
    fs.unlinkSync(path.join(args.downloadsDir, capacityDownload.name));
    await evaluate(client, `document.querySelector('#capacity-result .receipt-action').click()`);
    const capacityReplay = await waitForDownload(args.downloadsDir, "anibench-v2-studio-workflow-");
    assert.equal(capacityReplay.sha256, capacityDownload.sha256);

    await evaluate(client, `document.querySelector('#view-level1-authority').click()`);
    await waitForExpression(
      client,
      `document.querySelector('#capacity-status').textContent.startsWith('Level-1 definition verified:')`,
      45000
    );
    await evaluate(client, `document.querySelector('#assess-level1').click()`);
    try {
      await waitForExpression(
        client,
        `document.querySelector('#capacity-status').textContent.startsWith('Compiled ') || document.querySelector('#capacity-status').textContent.startsWith('Level-1 assessment stopped:')`,
        90000
      );
    } catch (error) {
      const diagnostic = await evaluate(client, `({
        status: document.querySelector('#capacity-status')?.textContent || null,
        resultText: document.querySelector('#capacity-result')?.textContent?.slice(0, 1000) || null,
        textareaCharacters: document.querySelector('#capacity-input')?.value?.length || null,
        documentReadyState: document.readyState
      })`);
      throw new Error(
        `${error.message}; diagnostic=${JSON.stringify(diagnostic)}; `
        + `network=${JSON.stringify(networkEvents)}; pageErrors=${JSON.stringify(pageErrors)}`
      );
    }
    const level1Ui = await evaluate(client, `({
      status: document.querySelector('#capacity-status').textContent,
      cards: document.querySelectorAll('#capacity-result .level1-family-card').length,
      text: document.querySelector('#capacity-result').textContent,
      downloadButtons: document.querySelectorAll('#capacity-result .receipt-action').length
    })`);
    assert.match(level1Ui.status, /^Compiled /, level1Ui.status);
    assert.equal(level1Ui.cards, 6);
    assert.match(level1Ui.status, /target normalization remains source-gated/);
    assert.match(level1Ui.text, /six independent dimensions/i);
    assert.match(level1Ui.text, /Level-1 target:\s*unresolved/i);
    assert.match(level1Ui.text, /Receipt locator \/scenarios\/0\/families\//);
    assert.match(level1Ui.text, /Overall scalar\s*Not emitted/);
    assert.match(level1Ui.text, /Public rank\s*Not emitted/);
    assert.equal(level1Ui.downloadButtons, 1);
    await evaluate(client, `document.querySelector('#capacity-result .receipt-action').click()`);
    const level1Download = await waitForDownload(args.downloadsDir, "anibench-v2-level1-assessment-");
    assert.equal(level1Download.payload.schema_version, "anibench.level1-role-aware-assessment.v3-candidate1");
    assert.equal(level1Download.payload.comparison_eligible, false);
    assert.equal(level1Download.payload.promotion_allowed, false);
    assert.equal(level1Download.payload.overall_scalar, null);
    assert.equal(level1Download.payload.public_rank_emission_permitted, false);
    assert.equal(level1Download.payload.scenarios[0].families.length, 6);
    assert.ok(level1Download.payload.scenarios[0].families.every(row =>
      row.level1_target_attainment.state === "unresolved"
      && row.level1_target_attainment.value === null
      && row.native_metrics.every(metric => metric.source_locator.startsWith("/scenarios/0/families/"))
    ));
    fs.unlinkSync(path.join(args.downloadsDir, level1Download.name));
    await evaluate(client, `document.querySelector('#capacity-result .receipt-action').click()`);
    const level1Replay = await waitForDownload(args.downloadsDir, "anibench-v2-level1-assessment-");
    assert.equal(level1Replay.sha256, level1Download.sha256);

    await evaluate(client, `document.querySelector('#load-optimizer-example').click()`);
    await waitForExpression(client, `document.querySelector('#protocol-optimizer-input').value.includes('base_protocol')`);
    await evaluate(client, `document.querySelector('#protocol-optimizer-form').requestSubmit()`);
    await waitForExpression(client, `document.querySelector('#optimizer-status').textContent.startsWith('Explored ')`, 45000);
    const optimizerUi = await evaluate(client, `({
      status: document.querySelector('#optimizer-status').textContent,
      cards: document.querySelectorAll('#protocol-optimizer-result .family-receipt-card').length,
      text: document.querySelector('#protocol-optimizer-result').textContent,
      downloadButtons: document.querySelectorAll('#protocol-optimizer-result .receipt-action').length
    })`);
    assert.ok(optimizerUi.cards > 0);
    assert.match(optimizerUi.status, /Pareto/);
    assert.match(optimizerUi.text, /Overall scalar\s*Not emitted/);
    assert.match(optimizerUi.text, /Stable rank\s*Not emitted/);
    assert.equal(optimizerUi.downloadButtons, 1);
    await evaluate(client, `document.querySelector('#protocol-optimizer-result .receipt-action').click()`);
    const optimizerDownload = await waitForDownload(args.downloadsDir, "anibench-v2-protocol-optimizer-");
    assert.match(optimizerDownload.payload.schema_version, /^anibench\.optimizer-protocol-result\./);
    assert.equal(optimizerDownload.payload.overall_scalar, null);
    assert.equal(optimizerDownload.payload.public_rank_emission_permitted, false);
    fs.unlinkSync(path.join(args.downloadsDir, optimizerDownload.name));
    await evaluate(client, `document.querySelector('#protocol-optimizer-result .receipt-action').click()`);
    const optimizerReplay = await waitForDownload(args.downloadsDir, "anibench-v2-protocol-optimizer-");
    assert.equal(optimizerReplay.sha256, optimizerDownload.sha256);

    const desktop = await evaluate(client, `(() => {
      const columns = selector => getComputedStyle(document.querySelector(selector)).gridTemplateColumns
        .split(' ').filter(Boolean).length;
      return {
        innerWidth,
        narrowQuery: matchMedia('(max-width: 780px)').matches,
        labColumns: columns('.lab-grid'),
        familyColumns: columns('.capacity-family-map'),
        registryColumns: columns('.source-intake-grid'),
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
      };
    })()`);
    assert.equal(desktop.innerWidth, 1440);
    assert.equal(desktop.narrowQuery, false);
    assert.ok(desktop.labColumns >= 2);
    assert.ok(desktop.familyColumns >= 2);
    assert.equal(desktop.registryColumns, 2);
    assert.equal(desktop.horizontalOverflow, false);
    const desktopScreenshotSha256 = await captureHash(client);

    await client.send("Emulation.setDeviceMetricsOverride", {
      width: 390,
      height: 844,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: 390,
      screenHeight: 844,
      dontSetVisibleSize: false
    });
    await waitForExpression(client, `innerWidth === 390 && matchMedia('(max-width: 780px)').matches`);
    const mobile = await evaluate(client, `(() => {
      const columns = selector => getComputedStyle(document.querySelector(selector)).gridTemplateColumns
        .split(' ').filter(Boolean).length;
      return {
        innerWidth,
        narrowQuery: matchMedia('(max-width: 780px)').matches,
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        labColumns: columns('.lab-grid'),
        familyColumns: columns('.capacity-family-map'),
        registryColumns: columns('.source-intake-grid'),
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        overflowingElements: [...document.querySelectorAll('body *')]
          .map(node => ({
            tag: node.tagName.toLowerCase(),
            id: node.id || null,
            className: typeof node.className === 'string' ? node.className : null,
            left: Math.round(node.getBoundingClientRect().left),
            right: Math.round(node.getBoundingClientRect().right),
            scrollWidth: node.scrollWidth,
            clientWidth: node.clientWidth
          }))
          .filter(row => row.left < -1 || row.right > innerWidth + 1 || row.scrollWidth > row.clientWidth + 1)
          .slice(0, 20),
        capacityStatusVisible: document.querySelector('#capacity-status').getBoundingClientRect().width > 0,
        optimizerStatusVisible: document.querySelector('#optimizer-status').getBoundingClientRect().width > 0
      };
    })()`);
    assert.equal(mobile.innerWidth, 390);
    assert.equal(mobile.narrowQuery, true);
    assert.equal(mobile.labColumns, 1);
    assert.equal(mobile.familyColumns, 1);
    assert.equal(mobile.registryColumns, 1);
    assert.equal(mobile.horizontalOverflow, false, JSON.stringify(mobile));
    assert.equal(mobile.capacityStatusVisible, true);
    assert.equal(mobile.optimizerStatusVisible, true);
    const mobileScreenshotSha256 = await captureHash(client);
    assert.deepEqual(pageErrors, []);

    const receipt = {
      contract: "anibench.installed-studio-browser-gate.v1",
      passed: true,
      browser: {
        product: version.Browser,
        protocol_version: version["Protocol-Version"],
        binary: browserBinary
      },
      exercised: {
        html_and_assets: true,
        health_get: true,
        comparator_atlas_get: true,
        clinicaltrials_registry_intake_ui_present: true,
        packaged_examples_get: true,
        primary_design_form_post_and_render_10m: true,
        planned_realized_design_geometry_invariance: true,
        deterministic_design_handoff_download: true,
        identifier_only_binding_fails_closed: true,
        capacity_form_post_and_render: true,
        level1_authority_get_and_role_readback: true,
        level1_six_family_native_geometry_and_typed_unknown_render: true,
        optimizer_form_post_and_render: true,
        retired_routes: true,
        deterministic_json_downloads: true,
        desktop_responsive_state: true,
        mobile_responsive_state: true,
        accessibility_tree_control_names: true
      },
      accessibility: {
        full_ax_tree_node_count: accessibleNodes.length,
        required_control_names_present: true
      },
      responsive: {desktop, mobile},
      screenshots: {
        desktop_png_sha256: desktopScreenshotSha256,
        mobile_png_sha256: mobileScreenshotSha256
      },
      downloads: {
        design_handoff: {
          name: plannedDesignReplay.name,
          sha256: plannedDesignDownload.sha256,
          replay_sha256_equal: true,
          planned_population: 10000000,
          planned_participant_module_observations: 3723000000000,
          planned_realized_geometry_equal: true,
          planned_and_realized_input_hashes_differ: true
        },
        capacity: {
          name: capacityReplay.name,
          sha256: capacityDownload.sha256,
          replay_sha256_equal: true
        },
        level1_assessment: {
          name: level1Replay.name,
          sha256: level1Download.sha256,
          replay_sha256_equal: true,
          family_count: 6,
          target_state: "unresolved",
          overall_scalar: null,
          authority_sha256: level1Download.payload.level1_authority.authority_raw_sha256
        },
        optimizer: {
          name: optimizerReplay.name,
          sha256: optimizerDownload.sha256,
          replay_sha256_equal: true
        }
      },
      page_exceptions: pageErrors
    };
    process.stdout.write(`${JSON.stringify(receipt)}\n`);
  } catch (error) {
    const diagnostics = [
      browserStdout.trim() ? `Chrome stdout:\n${browserStdout.slice(-4000)}` : "",
      browserStderr.trim() ? `Chrome stderr:\n${browserStderr.slice(-4000)}` : ""
    ].filter(Boolean).join("\n");
    const suffix = diagnostics ? `\n${diagnostics}` : "";
    throw new Error(`${error.stack || error.message}${suffix}`);
  } finally {
    if (socket) socket.close();
    browser.kill("SIGTERM");
    await new Promise(resolve => {
      const timeout = setTimeout(resolve, 3000);
      browser.once("exit", () => { clearTimeout(timeout); resolve(); });
    });
    if (browser.exitCode === null) browser.kill("SIGKILL");
    fs.rmSync(profile, {recursive: true, force: true});
  }
}

main().catch(error => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
