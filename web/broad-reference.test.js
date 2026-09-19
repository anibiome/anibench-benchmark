"use strict";
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const c=require('./broad-reference.js'),read=()=>JSON.parse(fs.readFileSync(__dirname+'/broad-reference-data.json','utf8'));
test('candidate exposes both witnesses, does not mutate executed evidence',()=>{
 const p=read(),before=JSON.stringify(p),html=c.render(p);
 assert.match(html,/SYNTHETIC REFERENCE CANDIDATE/);assert.match(html,/160/);assert.match(html,/2,112/);
 assert.match(html,/not calibrated biological sufficiency/);assert.match(html,/not a complete score/);
 assert.equal(JSON.stringify(p),before);
});
test('plot uses actual inputs and all points are inside axes, with accessible exact rows',()=>{
 const html=c.designPlot(read());const circles=[...html.matchAll(/<circle cx="([^"]+)" cy="([^"]+)"/g)];
 assert.equal(circles.length,4);for(const m of circles){assert.ok(+m[1]>=58&&+m[1]<=440);assert.ok(+m[2]>=45&&+m[2]<=235);}
 assert.match(html,/Exact design inputs/);assert.match(html,/1,000,000/);assert.match(html,/100,000/);
});
test('absent and unknown neural support remain distinct with exact receipt target sets',()=>{
 const p=read(),abs=c.caseHTML(p,'neural-absent'),unk=c.caseHTML(p,'neural-unknown');
 assert.match(abs,/Does not meet/);assert.match(abs,/3 failed and 0 unresolved/);
 assert.match(unk,/Unresolved/);assert.match(unk,/0 failed and 3 unresolved/);
 for(const id of ['neural.base.state','neural.base.population','neural.base.time']) assert.ok(abs.includes(id)&&unk.includes(id));
});
test('redundant arms and aliases fail named tasks; copies not invented as a separate executed chart row',()=>{
 const p=read();assert.match(c.caseHTML(p,'redundant-arms'),/randomized-input-contrast/);
 assert.match(c.caseHTML(p,'daily-alias'),/digital.base.time/);
 assert.match(c.render(p),/does not contain a separate duplicate-row run/);
});
test('sensitivity plots bind all actual variances and per-level ceilings without rescoring',()=>{
 const p=read();for(const level of ['1','2']) for(const [key,limit] of [['reference_identity_operator_variance',level==='1'?.25:.0625],['reference_population_variance',level==='1'?.01:.0025]]) {
  const h=c.sensitivityPlot(p,level,key,limit,'test');assert.equal((h.match(/<circle/g)||[]).length,5);
  assert.match(h,/squared synthetic reference units/);assert.ok(h.includes(`ceiling ${limit}`));
  for(const m of h.matchAll(/<circle cx="([^"]+)"/g)) assert.ok(+m[1]>=14&&+m[1]<=446);
 }
});
test('URL state remains independent of real-study selection and evidence filters',()=>{
 const u='https://example.test/?studies=a,b&publication=unpublished&ethics=unknown#results';
 const next=c.writeState(u,{level:'2',caseId:'neural-unknown'}),q=new URL(next);
 assert.equal(q.searchParams.get('publication'),'unpublished');assert.equal(q.searchParams.get('ethics'),'unknown');assert.equal(q.searchParams.get('studies'),'a,b');assert.equal(q.hash,'#results');
 assert.deepEqual(c.readState(next),{level:'2',caseId:'neural-unknown'});assert.equal(c.readState('https://example.test/?broad_case=invalid').caseId,'two-people-extreme-depth');
});
test('malformed receipts, unknown noise scenarios and duplicate examples fail closed',()=>{
 for(const mutate of [p=>p.examples[0].profile_sha256='bad',p=>p.examples[0].reference_population_variance=NaN,p=>p.examples[0].failed=['contradiction'],p=>p.examples.push(p.examples[0]),p=>p.sensitivity[0].model.measurement_variance_R=17]) {
 const p=read();mutate(p);assert.throws(()=>c.render(p));}
});
test('source labels cannot inject markup',()=>{const p=read();p.examples.find(r=>r.design_id==='neural-absent').failed.push('<script>bad</script>');const h=c.caseHTML(p,'neural-absent');assert.doesNotMatch(h,/<script>/);assert.match(h,/&lt;script&gt;/);});
test('load failure remains local to synthetic section',async()=>{const host={innerHTML:''};await c.mount(host,{fetcher:async()=>({ok:false}),win:{}});assert.match(host.innerHTML,/role="alert"/);assert.match(host.innerHTML,/Real-study charts remain independent/);});
