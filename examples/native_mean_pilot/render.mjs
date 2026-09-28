// Render canonical receipt values using the installed workbench's own chart code.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const assets = process.argv[2];
if (!assets) throw Error('Provide installed workbench asset directory.');
const {chartSVG} = await import(pathToFileURL(path.join(assets, 'app.mjs')));
const {pilotRows, scenarioLabel} = await import(pathToFileURL(path.join(assets, 'pilot.mjs')));
const data = JSON.parse(fs.readFileSync(0, 'utf8'));
const bindings = JSON.parse(fs.readFileSync(path.join(assets, 'pilot-bindings.json'), 'utf8'));
const domains = {molecular:'Molecular', physiological:'Physiology', digital:'Digital activity', cognitive:'Cognitive function', neural:'Brain structure'};
const rows = pilotRows(data, {factor:1, scenario:'envelope', metric:'attainment'});
const subtitle = `Ten-task native-mean pilot · SE factor 1 · ${scenarioLabel('envelope')} · publication all · ethics all. Ranges: unresolved tasks and sensitivity, not confidence intervals. Source-specific populations, no whole-study rank. Reference ${bindings.reference_sha256}`;
process.stdout.write(chartSVG(rows.map(r => ({...r,
  label:domains[r.domain]+' · '+r.family.replaceAll('_',' '),
  lane:r.family==='MIPACT'?'baseline':'changed',
})), 'Reference tasks met (%)', subtitle));
