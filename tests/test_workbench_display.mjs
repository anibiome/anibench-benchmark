import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chartSVG, comparisonState, comparisonURL, designCSV, preserveQuestionSupport, recordScore, validatedBounds} from '../src/anibench/workbench_assets/app.mjs';
const catalogue=JSON.parse(fs.readFileSync(new URL('../src/anibench/workbench_assets/catalogue.json',import.meta.url)));

test('all published native results retain canonical bounds and scenario bindings',()=>{
  for(const record of catalogue.records)for(const score of record.scores||[]){
    assert.equal(recordScore(record,score.se_factor,'envelope','attainment').lower,score.envelope.lower_percent);
    for(const scenario of score.scenarios){
      const shown=recordScore(record,score.se_factor,scenario.scenario_id,'precision');
      assert.equal(shown.lower,scenario.precision_toward_target.lower_percent);
      assert.equal(shown.upper,scenario.precision_toward_target.upper_percent);
    }
  }
  const contrast=catalogue.records.find(r=>!r.scores.length);
  assert.equal(recordScore(contrast,1,'envelope','attainment'),null);
});
test('sharing accepts only current public record IDs and valid comparison controls',()=>{
  const state=comparisonState('https://example.test/?record=private-path&metric=invented',catalogue);
  assert.deepEqual(state.records,[]);
  assert.equal(state.metric,'attainment');
  state.records=catalogue.own_population_comparison_groups[0].record_ids.slice(0,2);
  state.ethics='approval_reported';state.publication='peer_reviewed_article';state.metric='precision';
  const url=comparisonURL('http://127.0.0.1:8795/?secret=discard#compare',state);
  assert.equal(url.searchParams.has('secret'),false);
  assert.deepEqual(comparisonState(url,catalogue),state);
});
test('editing a restricted imported design does not add question support',()=>{
  const previous={only_questions:['controlled_contrast']};
  const edited=preserveQuestionSupport(previous,{N:20,depth:2});
  assert.deepEqual(edited.only_questions,previous.only_questions);
  edited.only_questions.push('population_mean');
  assert.deepEqual(previous.only_questions,['controlled_contrast']);
});
test('export preserves unresolved mass, context and safe XML',()=>{
  const svg=chartSVG([{label:'Study <unsafe> & arm A',lower:20,upper:80}], 'Precision target met', 'v3 | reported variance | target SE 0.05 | ethics unknown');
  assert.match(svg,/20–80%/);
  assert.match(svg,/Study &lt;unsafe&gt; &amp; arm A/);
  assert.match(svg,/ethics unknown/);
  for(const bad of [[null,100],[50,40],[0,101]])assert.throws(()=>validatedBounds(...bad));
});
test('CSV export identifies the exact reference, metric, scenario and result',()=>{
  const packet={version:'conditional-reference-0.4',level:'AB2',results:{baseline:{result:{suite_profile_sha256:'suite123',score_profile_sha256:'score456',receipt_sha256:'result789'}}}};
  const csv=designCSV(packet,[{id:'molecular',lane:'baseline',lower:40,upper:80}],'precision','double-noise');
  for(const identity of ['AB2','precision','double-noise','suite123','score456','result789'])assert.ok(csv.includes(identity));
});

import {readFileSync} from 'node:fs';
import {pilotRows, validatePilotBytes, selectedStudies, pilotLegend, publicationText, scenarioLabel} from '../src/anibench/workbench_assets/pilot.mjs';
const pilotBytes=readFileSync(new URL('../src/anibench/workbench_assets/pilot.json',import.meta.url));
const bindingBytes=readFileSync(new URL('../src/anibench/workbench_assets/pilot-bindings.json',import.meta.url));

test('pilot pins reviewed chart bytes, evidence and per-task result identities',async()=>{
  const {data,bindings}=await validatePilotBytes(pilotBytes,bindingBytes);
  assert.equal(bindings.studies.length,2);
  assert.equal(data.results[0].scenarios.length,6);
  const tampered=structuredClone(data);tampered.results[0].envelope[0].categories[0].lower_percent=99;
  await assert.rejects(validatePilotBytes(new TextEncoder().encode(JSON.stringify(tampered)),bindingBytes),/identities differ/);
  await assert.rejects(validatePilotBytes(pilotBytes,new TextEncoder().encode('{}')),/evidence identity/);
});
test('all pilot scenarios and factors preserve canonical percentages and unknowns',async()=>{
  const {data}=await validatePilotBytes(pilotBytes,bindingBytes);
  for(const factor of [.5,1,2])for(const scenario of ['envelope',...data.results[0].scenarios.map(s=>s.scenario_id)])for(const metric of ['attainment','precision']){
    const rows=pilotRows(data,{factor,scenario,metric});assert.equal(rows.length,10);
    for(const row of rows){assert.ok(row.lower>=0&&row.upper<=100&&row.lower<=row.upper);}
    const unknown=rows.find(r=>r.family==='MIPACT'&&r.domain==='neural');assert.equal(unknown.lower,0);assert.equal(unknown.upper,100);
  }
  assert.throws(()=>pilotRows(data,{scenario:'not-a-case'}));
  assert.match(scenarioLabel('q2-rounded-low'),/lower rounding bound/);
});
test('pilot filter metadata, legends and URL state agree',async()=>{
  const {bindings}=await validatePilotBytes(pilotBytes,bindingBytes);
  const mixed=structuredClone(bindings);mixed.studies[1].publication.status='unpublished';mixed.studies[1].ethics.status='unknown';
  const published=selectedStudies(mixed,{publication:'peer_reviewed_results',ethics:'all'});
  assert.equal(published.length,1);assert.doesNotMatch(pilotLegend(published),/DIRECT/);
  const unpublished=selectedStudies(mixed,{publication:'unpublished',ethics:'unknown'});
  assert.equal(unpublished.length,1);assert.equal(publicationText(unpublished[0]),'Unpublished');
  assert.equal(selectedStudies(mixed,{publication:'unpublished',ethics:'approved'}).length,0);
  const url=comparisonURL('http://localhost/?pilot_factor=2&pilot_scenario=q2-rounded-high&pilot_ethics=unknown&private_path=secret',{group:'g',factor:'1',scenario:'envelope',metric:'attainment',publication:'all',ethics:'all',records:[]});
  assert.equal(url.searchParams.get('pilot_factor'),'2');assert.equal(url.searchParams.get('pilot_scenario'),'q2-rounded-high');assert.equal(url.searchParams.get('private_path'),null);
});
