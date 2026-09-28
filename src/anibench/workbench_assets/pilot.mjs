import {bar, chartSVG, escapeHTML as esc, validatedBounds} from './app.mjs';

const domains = {
  molecular: 'Molecular', physiological: 'Physiology', digital: 'Digital activity',
  cognitive: 'Cognitive function', neural: 'Brain structure',
};
// Pin the independently reviewed evidence packet; updating it requires a new review.
export const PILOT_BINDINGS_SHA256 = 'a9bee628cf08b2ac3e0bb855acb5baa2e1dae683f949593d8bc31f2a24fc26b7';
const publicationLabels = {peer_reviewed_results: 'Peer-reviewed results', unpublished: 'Unpublished', unknown: 'Publication unknown'};
const ethicsLabels = {approved: 'Approval reported', not_approved: 'Reported not approved', unknown: 'Approval unknown'};
const scenarioLabels = {
  envelope: 'All variance and rounding cases', q1: 'Reported variance', q2: 'Twice the variance',
  'q1-rounded-low': 'Reported variance · lower rounding bound',
  'q1-rounded-high': 'Reported variance · upper rounding bound',
  'q2-rounded-low': 'Twice the variance · lower rounding bound',
  'q2-rounded-high': 'Twice the variance · upper rounding bound',
};
export const scenarioLabel = id => scenarioLabels[id] || id;
const familyLabel = id => id.replaceAll('_', ' ');
const lane = id => id === 'MIPACT' ? 'before' : 'after';
const sha256 = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');

export async function validatePilotBytes(displayBytes, bindingBytes, expectedBindingHash = PILOT_BINDINGS_SHA256) {
  if (await sha256(bindingBytes) !== expectedBindingHash) throw Error('Pilot evidence identity differs from the reviewed release.');
  const decoder = new TextDecoder();
  const data = JSON.parse(decoder.decode(displayBytes));
  const bindings = JSON.parse(decoder.decode(bindingBytes));
  if (data.schema !== 'anibench.multidomain-pilot-display.v1' || bindings.schema !== 'anibench.multidomain-pilot-bindings.v1') throw Error('Pilot schema differs.');
  if (await sha256(displayBytes) !== bindings.bindings['DISPLAY_PILOT.json']) throw Error('Pilot chart and evidence identities differ.');
  const resultMap = new Map(data.results.map(r => [r.family_id + ':' + r.se_factor, r]));
  if (resultMap.size !== data.results.length) throw Error('Duplicate pilot result.');
  const seen = new Set();
  for (const task of bindings.task_scenarios) {
    const result = resultMap.get(task.family_id + ':' + task.se_factor);
    if (!result || ['result_sha256', 'score_profile_sha256', 'suite_profile_sha256'].some(key => result[key] !== task[key])) throw Error('Task and chart result bindings differ.');
    if (!result.scenarios.some(s => s.scenario_id === task.scenario_id)) throw Error('Unbound task scenario.');
    const id = [task.family_id, task.se_factor, task.scenario_id, task.target_id].join(':');
    if (seen.has(id)) throw Error('Duplicate task binding.');
    seen.add(id);
  }
  return {data, bindings};
}

// These are projections of canonical Python receipts. No scientific rescoring runs here.
export function pilotRows(data, {factor = 1, scenario = 'envelope', metric = 'attainment'} = {}) {
  if (!['attainment', 'precision'].includes(metric)) throw Error('Pilot metric unavailable.');
  const results = data.results.filter(r => r.se_factor === Number(factor));
  if (!results.length) throw Error('Pilot target factor unavailable.');
  return results.flatMap(r => {
    const categories = scenario === 'envelope' ? r.envelope[0].categories : r.scenarios.find(s => s.scenario_id === scenario)?.categories;
    if (!categories) throw Error('Pilot scenario unavailable.');
    return categories.map(c => {
      const bounds = metric === 'precision' ? c.precision_toward_targets : {
        lower_percent: scenario === 'envelope' ? c.lower_percent : c.passed_percent, upper_percent: c.upper_percent,
      };
      return {family: r.family_id, domain: c.category_id, ...validatedBounds(bounds.lower_percent, bounds.upper_percent), result_sha256: r.result_sha256};
    });
  });
}
export function selectedStudies(bindings, state) {
  return bindings.studies.filter(s => (state.publication === 'all' || s.publication.status === state.publication) && (state.ethics === 'all' || s.ethics.status === state.ethics));
}
export function pilotLegend(studies) {
  return studies.map(s => `<span class="${lane(s.family_id)}">${esc(familyLabel(s.family_id))}</span>`).join('');
}
export function publicationText(study) {
  return publicationLabels[study.publication.status] || study.publication.status.replaceAll('_', ' ');
}
const sourceLink = source => source?.url?.startsWith('https://')
  ? `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">Original source ↗</a>${source.locator ? ' · ' + esc(source.locator) : ''}`
  : 'Source details unavailable';
const download = (name, value, type = 'application/json') => {
  const url = URL.createObjectURL(new Blob([value], {type}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
function taskExplanation(task) {
  const assumptions = Array.isArray(task.assumptions) ? task.assumptions : Object.entries(task.assumptions || {}).map(([key, value]) => key === 'rationale' ? value : key.replaceAll('_', ' ') + ': ' + value);
  const status = task.unknown_reason || ('Task ' + (task.status === 'attained' ? 'met' : 'not met') + '; sampling variance ' + task.variance + ', N ' + task.n + '.');
  return `<article class="task-explanation"><p><b>${esc(task.label)} · ${esc(scenarioLabel(task.scenario_id))}</b><br>
    SE: ${esc(task.standard_error ?? 'Unknown')} ${esc(task.unit)} · target: ${esc(task.target_standard_error)} ${esc(task.unit)}<br>${esc(status)}</p>
    <p><b>Population:</b> ${esc(task.population)}<br><b>Timing:</b> ${esc(task.horizon)}<br><b>Measurement:</b> ${esc(task.operator || 'Not qualified')}<br><b>Sample-count status:</b> ${esc(task.n_status || 'Unknown')}</p>
    <p>${assumptions.map(esc).join(' ')} ${esc(task.rounding_scope || '')}</p>
    <p>${(task.equivalence_assumptions || []).map(esc).join(' ')}</p>
    <p>${sourceLink(task.source)}</p>${(task.supplementary_evidence || []).map(s => `<p>${sourceLink(s)}</p>`).join('')}
    <details><summary>Calculation identities</summary><p>Source: <code>${esc(task.source?.sha256 || 'Unresolved')}</code><br>Task: <code>${esc(task.task_sha256)}</code><br>Result: <code>${esc(task.result_sha256)}</code></p></details></article>`;
}

export async function bootPilot() {
  const $ = id => document.getElementById(id);
  const fetchBytes = async name => {
    const response = await fetch(name); if (!response.ok) throw Error('Pilot unavailable.');
    return response.arrayBuffer();
  };
  const bytes = await Promise.all([fetchBytes('pilot.json'), fetchBytes('pilot-bindings.json')]);
  const {data, bindings} = await validatePilotBytes(...bytes);
  const scenarioIDs = ['envelope', ...data.results[0].scenarios.map(s => s.scenario_id)];
  const allowed = {factor: ['0.5', '1', '2'], metric: ['attainment', 'precision'], scenario: scenarioIDs, publication: ['all', ...Object.keys(publicationLabels)], ethics: ['all', ...Object.keys(ethicsLabels)]};
  const defaults = {factor: '1', metric: 'attainment', scenario: 'envelope', publication: 'all', ethics: 'all'};
  const state = {...defaults};
  function restore() {
    const params = new URL(location.href).searchParams;
    for (const [key, values] of Object.entries(allowed)) { const value = params.get('pilot_' + key); state[key] = values.includes(value) ? value : defaults[key]; }
  }
  function update() {
    render(); const url = new URL(location.href); url.searchParams.set('view', 'pilot');
    for (const [key, value] of Object.entries(state)) url.searchParams.set('pilot_' + key, value);
    history.pushState(null, '', url);
  }
  const option = (value, label, key) => `<option value="${esc(value)}"${String(state[key]) === String(value) ? ' selected' : ''}>${esc(label)}</option>`;
  const selectedTasks = studies => bindings.task_scenarios.filter(t => studies.some(s => s.family_id === t.family_id) && t.se_factor === Number(state.factor) && (state.scenario === 'envelope' || t.scenario_id === state.scenario));
  function render() {
    const filtersOpen = $('pilot-controls').querySelector('details')?.open;
    const focusedControl = document.activeElement?.id;
    const studies = selectedStudies(bindings, state);
    const rows = pilotRows(data, state).filter(r => studies.some(s => s.family_id === r.family));
    const tasks = selectedTasks(studies);
    $('pilot-controls').innerHTML = `<div class="toolbar"><label>Reference<select disabled><option>Native precision · 10-task pilot</option></select></label>
      <label>Show<select id="pilot-metric">${option('attainment', 'Reference tasks met (%)', 'metric')}${option('precision', 'Progress toward targets (%)', 'metric')}</select></label>
      <label>Variance and rounding<select id="pilot-scenario">${scenarioIDs.map(id => option(id, scenarioLabel(id), 'scenario')).join('')}</select></label></div>
      <details${filtersOpen ? ' open' : ''}><summary>Precision targets and evidence filters</summary><div class="toolbar">
      <label>Target sensitivity<select id="pilot-factor">${option(.5, '0.5× · stricter', 'factor')}${option(1, '1× · reference', 'factor')}${option(2, '2× · looser', 'factor')}</select></label>
      <label>Study publication<select id="pilot-publication">${option('all', 'All statuses', 'publication')}${Object.entries(publicationLabels).map(([id, label]) => option(id, label, 'publication')).join('')}</select></label>
      <label>Ethics approval<select id="pilot-ethics">${option('all', 'All statuses', 'ethics')}${Object.entries(ethicsLabels).map(([id, label]) => option(id, label, 'ethics')).join('')}</select></label></div></details>`;
    for (const key of Object.keys(state)) $('pilot-' + key).onchange = event => { state[key] = event.target.value; update(); };
    if (Object.keys(state).some(key => 'pilot-' + key === focusedControl)) $(focusedControl).focus();
    const title = state.metric === 'precision' ? 'Progress toward precision targets (%)' : 'Reference tasks met (%)';
    const summary = studies.length ? studies.map(s => familyLabel(s.family_id)).join(' and ') + ' shown. A 0–100% range means the required precision is unresolved; it is not a measured zero.' : 'No eligible studies in this view.';
    $('pilot-status').textContent = '';
    $('pilot-chart').innerHTML = `<div class="card"><div class="card-heading"><div><span class="eyebrow">TWO TASKS PER DOMAIN</span><h2>${title}</h2></div><div class="legend">${pilotLegend(studies)}</div></div>
      <p class="chart-meaning">${state.metric === 'attainment' ? '50% means one of two tasks meets its precision requirement.' : 'Continuous progress toward the same two precision targets per domain.'} These tasks estimate population averages. Hatched ranges show unresolved tasks${state.scenario === 'envelope' ? ' and sensitivity to variance and rounded source values' : ''}; they are not confidence intervals.</p>
      ${studies.length ? Object.entries(domains).map(([id, label]) => `<div class="chart-row"><h3>${label}</h3><div class="tracks">${rows.filter(r => r.domain === id).map(r => bar(r.lower, r.upper, label + ' · ' + familyLabel(r.family), lane(r.family))).join('')}</div></div>`).join('') + '<div class="axis"><span>0%</span><span>50%</span><span>100%</span></div>' : '<p class="empty">No study matches these filters. Unknown approval does not mean non-approval.</p><button id="pilot-reset-filters">Clear filters</button>'}
      <div class="result-summary">${esc(summary)}</div><div class="actions"><button id="pilot-export-svg"${rows.length ? '' : ' disabled'}>Export chart SVG</button><button id="pilot-export-data">Export data and sources</button></div></div>
      <p class="scope-note">Draft reference · Source-specific populations and measurement protocols. Table-header sample counts are conditional where per-variable completeness is unavailable. These research targets have half/double sensitivity; the pilot does not measure whole-study quality or confer AB1.</p>`;
    $('pilot-reset-filters')?.addEventListener('click', () => { state.publication = state.ethics = 'all'; update(); });
    $('pilot-export-svg').onclick = () => download('anibench-multidomain-pilot.svg', chartSVG(rows.map(r => ({...r, label: domains[r.domain] + ' · ' + familyLabel(r.family), lane: r.family === 'MIPACT' ? 'baseline' : 'changed'})), title,
      `Ten-task native-mean pilot · SE factor ${state.factor} · ${scenarioLabel(state.scenario)} · publication ${state.publication} · ethics ${state.ethics}. Ranges: unresolved tasks and sensitivity, not confidence intervals. Source-specific populations, no whole-study rank. Reference ${bindings.reference_sha256}`), 'image/svg+xml');
    $('pilot-export-data').onclick = () => download('anibench-multidomain-pilot.json', JSON.stringify({selection: {...state}, reference: data.reference, reference_sha256: bindings.reference_sha256, rows, studies, task_scenarios: tasks}, null, 2));
    $('pilot-details').innerHTML = `<details><summary>Why these tasks and precision targets?</summary><p>${esc(data.reference.purpose)}</p><p>${esc(data.reference.new_criteria_rationale)}</p><p>${esc(data.reference.freeze_order)}</p><p>${esc(data.reference.joint_claim)}</p></details>` +
      Object.entries(domains).map(([id, label]) => `<details><summary>${label}: tasks, calculations and evidence</summary>${studies.map(study => `<h3>${esc(study.label)}</h3>${tasks.filter(t => t.domain === id && t.family_id === study.family_id).map(taskExplanation).join('')}`).join('')}</details>`).join('') +
      `<details><summary>Publication and ethics evidence</summary>${studies.map(s => `<h3>${esc(s.label)}</h3><p>${esc(s.ethics.statement)} · ${sourceLink(s.ethics.source)}</p><p>${esc(publicationText(s))} · ${sourceLink(s.publication.source)}</p>`).join('')}</details>`;
  }
  restore(); render(); window.addEventListener('popstate', () => { restore(); render(); });
}
