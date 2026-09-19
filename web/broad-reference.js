/* Conditional synthetic workload; never inferred from source-study counts. */
"use strict";
const AniBenchBroadReference = (() => {
  const esc = v => String(v).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const num = v => new Intl.NumberFormat("en", {maximumSignificantDigits:4}).format(v);
  const states = {attained:"Meets this candidate",not_attained:"Does not meet",unknown:"Unresolved"};
  const cases = {
    "two-people-extreme-depth":["Two people, extreme depth","Repeated measurements improve individual precision. They do not create independent people."],
    "huge-shallow":["Many people, shallow measurements","Population precision cannot supply the missing precision of each person's state."],
    "correlated-oversampling":["A million correlated repeats","At correlation 0.99, repeated depth approaches about one independent repeat."],
    "redundant-arms":["Four redundant arms","Repeated arm labels do not create an independent assignment contrast."],
    "daily-alias":["Always sample at the same daily phase","A daily schedule can miss daily variation: these phases cannot identify the declared digital modes."],
    "unlinked":["Observations without person linkage","Separate measurements cannot establish the required jointly observed-person task."],
    "neural-absent":["Neural observation absent","Known absence fails the required neural observation tasks. Core observation is not a stimulation requirement."],
    "neural-unknown":["Neural observation unknown","Unreported support remains unresolved rather than absent, zero or a pass."],
    "observation-without-cortical-assignment":["Optional cortical-assignment child","Observation alone does not meet the separate AB1-neural child; core AB1 does not require stimulation."]
  };
  function validate(p) {
    if(p?.contract!=="anibench.broad-reference-figure-data.v1" || !Array.isArray(p.examples) || !Array.isArray(p.sensitivity)) throw Error("Invalid broad-reference packet");
    const ids=new Set();
    for(const row of [...p.examples,...p.sensitivity]) {
      if(!Object.hasOwn(states,row.attainment) || !["1","2","1-neural"].includes(row.level) || !Array.isArray(row.failed) || !Array.isArray(row.unknown)) throw Error("Invalid scenario state");
      for(const k of ["people","depth_per_coordinate_per_occasion","effective_depth","reference_identity_operator_variance","reference_population_variance"]) if(!Number.isFinite(row[k]) || row[k]<=0) throw Error("Invalid positive reference quantity");
      for(const k of ["profile_sha256","design_source_sha256"]) if(!/^sha256:[a-f0-9]{64}$/.test(row[k])) throw Error("Missing reference binding");
      if(row.attainment==="attained" && (row.failed.length||row.unknown.length)) throw Error("Inconsistent scenario state");
    }
    for(const row of p.examples) {const id=row.design_id+":"+row.level;if(ids.has(id)) throw Error("Duplicate scenario");ids.add(id);}
    for(const id of Object.keys(cases)) if(!p.examples.some(r=>r.design_id===id)) throw Error("Required scenario missing");
    for(const level of ["1","2"]) {
      if(!p.examples.some(r=>r.design_id===`AB${level}-witness`&&r.level===level)) throw Error("Missing witness");
      const scenarios=p.sensitivity.filter(r=>r.level===level);
      const expected=["4/1/0.25/0","8/1/0.25/0","4/2/0.25/0","4/1/1/0","4/1/0.25/0.1"];
      const keys=scenarios.map(r=>[r.model?.measurement_variance_R,r.model?.between_person_variance_B,r.model?.occasion_variance_S,r.repeat_correlation].join('/'));
      if(keys.length!==5 || new Set(keys).size!==5 || keys.some(k=>!expected.includes(k))) throw Error("Expected five frozen model cases per level");
    }
    return p;
  }
  const badge = r => `<span class="br-state br-${esc(r.attainment)}">${states[r.attainment]}</span>`;
  const source = r => `<small class="br-hash">Profile ${esc(r.profile_sha256)}<br>Design ${esc(r.design_source_sha256)}</small>`;
  const svg = (title,body,h=290) => `<svg class="br-svg" viewBox="0 0 480 ${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>${body}</svg>`;
  function designPlot(p) {
    const selected=[['AB1-witness','1','AB1 example'],['AB2-witness','2','AB2 example'],['two-people-extreme-depth','1','Two people'],['huge-shallow','1','Many, shallow']];
    const x=n=>58+Math.log10(n/2)/Math.log10(100000/2)*382, y=d=>235-Math.log10(d)/6*190;
    let body='<text x="10" y="18">Measurement depth · log scale</text>';
    for(const n of [2,100,10000,100000]) body+=`<line x1="${x(n)}" x2="${x(n)}" y1="40" y2="235" class="br-grid"/><text x="${x(n)}" y="256" text-anchor="${n===2?'start':n===100000?'end':'middle'}">${n>=10000?`${n/1000}k`:num(n)}</text>`;
    for(const d of [1,1000,1000000]) body+=`<line x1="58" x2="440" y1="${y(d)}" y2="${y(d)}" class="br-grid"/><text x="52" y="${y(d)+5}" text-anchor="end">${d===1000000?'1m':d===1000?'1k':'1'}</text>`;
    for(const [id,level,label] of selected) {
      const r=p.examples.find(r=>r.design_id===id&&r.level===level),cx=x(r.people),cy=y(r.depth_per_coordinate_per_occasion);
      body+=`<circle cx="${cx}" cy="${cy}" r="6" class="br-point"/><text x="${cx+(['huge-shallow','AB1-witness'].includes(id)?-9:9)}" y="${cy-10}" text-anchor="${['huge-shallow','AB1-witness'].includes(id)?'end':'start'}">${esc(label)}</text>`;
    }
    body+='<text x="250" y="284" text-anchor="middle">Independent people · log scale</text>';
    return svg('Declared people and measurement depth for four synthetic designs; positions are not benchmark scores',body)+`<details><summary>Exact design inputs</summary><div class="table-scroll"><table><thead><tr><th>Design</th><th>Independent people</th><th>Repeats / coordinate / occasion</th><th>Full workload</th></tr></thead><tbody>${selected.map(([id,level,label])=>{const r=p.examples.find(r=>r.design_id===id&&r.level===level);return `<tr><th scope="row">${esc(label)} · AB${level}</th><td>${num(r.people)}</td><td>${num(r.depth_per_coordinate_per_occasion)}</td><td>${badge(r)}</td></tr>`;}).join('')}</tbody></table></div></details>`;
  }
  function witness(p,level) {
    const r=p.examples.find(r=>r.design_id===`AB${level}-witness`&&r.level===level);
    return `<article class="br-witness"><h4>AniBench ${level} candidate example</h4>${badge(r)}<p><b>${num(r.people)}</b> linked people · <b>${num(r.depth_per_coordinate_per_occasion)}</b> repeats per coordinate per occasion</p><p>Days ${r.visits_days.map(num).join(', ')} · ${r.assignment_groups} balanced assignment groups</p><small>${level==='1'?'All 26 required targets meet their marginal ceilings.':'Retains AB1 frames, tightens inherited variance ceilings fourfold, and adds extension, annual and interaction tasks.'}</small></article>`;
  }
  function caseHTML(p,id) {
    const r=p.examples.find(r=>r.design_id===id),[title,gloss]=cases[id];
    return `<h4>${esc(title)}</h4>${badge(r)}<p>${esc(gloss)}</p><p>${num(r.people)} people · ${num(r.depth_per_coordinate_per_occasion)} raw repeats · ${num(r.effective_depth)} effective repeats per coordinate/occasion · workload AB${esc(r.level)}</p><details><summary>${r.failed.length} failed and ${r.unknown.length} unresolved targets — inspect names and receipt identity</summary><p>Failed: ${r.failed.map(esc).join(', ')||'none'}.</p><p>Unresolved: ${r.unknown.map(esc).join(', ')||'none'}.</p>${source(r)}</details>`;
  }
  function assumption(r) {
    if(r.repeat_correlation) return 'Repeat correlation 0.1';
    if(r.model.measurement_variance_R===8) return 'Measurement variance R = 8';
    if(r.model.between_person_variance_B===2) return 'Person variance B = 2';
    if(r.model.occasion_variance_S===1) return 'Occasion variance S = 1';
    return 'Reference: R 4, B 1, S 0.25';
  }
  function sensitivityPlot(p,level,key,ceiling,title) {
    const rows=p.sensitivity.filter(r=>r.level===level),maximum=Math.max(ceiling,...rows.map(r=>r[key]))*1.12;
    const x=v=>14+v/maximum*432;
    let body='';
    rows.forEach((r,i)=>{const y=38+i*64;body+=`<text x="14" y="${y-16}">${esc(assumption(r))}</text><text x="446" y="${y-16}" text-anchor="end">${num(r[key])}</text><line x1="14" x2="446" y1="${y}" y2="${y}" class="br-grid"/><circle cx="${x(r[key])}" cy="${y}" r="5" class="br-point"/><line x1="${x(ceiling)}" x2="${x(ceiling)}" y1="${y-8}" y2="${y+8}" class="br-limit"/>`;});
    body+=`<text x="14" y="343">0</text><text x="446" y="343" text-anchor="end">${num(maximum)}</text>`;
    return `<article class="release-figure br-panel"><h4>${esc(title)}</h4><p>Variance · squared synthetic reference units · lower is more precise. Tick = AB${level} ceiling ${num(ceiling)}.</p>${svg(title+'; five model scenarios on a shared linear axis',body,354)}</article>`;
  }
  function render(p,state={level:'1',caseId:'two-people-extreme-depth'}) {
    validate(p);const level=state.level==='2'?'2':'1',caseId=Object.hasOwn(cases,state.caseId)?state.caseId:'two-people-extreme-depth';
    const rows=p.sensitivity.filter(r=>r.level===level);
    return `<header class="section-heading"><div><p class="eyebrow">SYNTHETIC REFERENCE CANDIDATE</p><h2>People, depth and the next benchmark.</h2><p>A finite workload to test collection design. These levels are not calibrated biological sufficiency or ratings of real studies.</p></div></header><div class="br-overview"><article class="release-figure br-panel"><h4>Four declared designs</h4>${designPlot(p)}<p>Depth means repeats per coordinate per occasion. Each point shows inputs, not a rank; the two extremes fail different requirements.</p></article><div class="br-witnesses">${witness(p,'1')}${witness(p,'2')}</div></div><div class="release-figure br-panel"><label>Why can a design fail? <select data-br-case>${Object.entries(cases).map(([id,[label]])=>`<option value="${id}"${id===caseId?' selected':''}>${esc(label)}</option>`).join('')}</select></label><div aria-live="polite">${caseHTML(p,caseId)}</div><p>Copied rows and expense add no information in this generator. This is a tested rule; the distributed chart packet does not contain a separate duplicate-row run.</p></div><div class="br-sensitivity-heading"><h4>Do the same designs still meet the workload when assumptions change?</h4><label>Example design <select data-br-level><option value="1"${level==='1'?' selected':''}>AB1 example</option><option value="2"${level==='2'?' selected':''}>AB2 example</option></select></label></div><div class="br-pair">${sensitivityPlot(p,level,'reference_identity_operator_variance',level==='1'?.25:.0625,'Precision of one directly observed coordinate')}${sensitivityPlot(p,level,'reference_population_variance',level==='1'?.01:.0025,'Precision of its population mean')}</div><p>These are two reference-operator diagnostics, not a complete score or the digital-mode geometry. Complete attainment still requires every target; passing both plots is insufficient.</p><details class="br-evidence"><summary>All five sensitivity results, units and provenance</summary><div class="table-scroll"><table><thead><tr><th>Assumption</th><th>Coordinate variance</th><th>Population variance</th><th>Full workload result</th><th>Receipt</th></tr></thead><tbody>${rows.map(r=>`<tr><th scope="row">${esc(assumption(r))}</th><td>${num(r.reference_identity_operator_variance)}</td><td>${num(r.reference_population_variance)}</td><td>${badge(r)}<br>${r.failed.map(esc).join(', ')}</td><td>${source(r)}</td></tr>`).join('')}</tbody></table></div><p>R is measurement variance, B between-person variance, S occasion variance. Genomic S is observation nuisance, not mutation. Repeat dependence reduces effective depth. Values and ceilings are normative model conventions, not clinical units, confidence intervals or empirical thresholds. Changing a noise model changes the frozen profile identity.</p></details><p><a href="broad-reference-data.json" download>Download executed scenarios and bindings</a> · <a href="https://github.com/anibiome/anibench-benchmark/tree/main/examples/broad_reference">Model, rationale and replay</a></p>`;
  }
  function readState(url) {const q=new URL(url).searchParams;return {level:q.get('broad_level')==='2'?'2':'1',caseId:Object.hasOwn(cases,q.get('broad_case'))?q.get('broad_case'):'two-people-extreme-depth'};}
  function writeState(url,state) {const u=new URL(url);u.searchParams.set('broad_level',state.level==='2'?'2':'1');u.searchParams.set('broad_case',Object.hasOwn(cases,state.caseId)?state.caseId:'two-people-extreme-depth');return u.href;}
  async function mount(host,{fetcher=fetch,win=window}={}) {
    try {
      const response=await fetcher('broad-reference-data.json');if(!response.ok) throw Error('Reference packet unavailable');const p=validate(await response.json());
      const update=()=>{const focused=host.contains(win.document.activeElement)?win.document.activeElement?.dataset:null;host.innerHTML=render(p,readState(win.location.href));if(focused?.brCase!==undefined) host.querySelector('[data-br-case]').focus();else if(focused?.brLevel!==undefined) host.querySelector('[data-br-level]').focus();};
      host.addEventListener('change',event=>{if(!event.target.matches('[data-br-case],[data-br-level]'))return;const s={level:host.querySelector('[data-br-level]').value,caseId:host.querySelector('[data-br-case]').value};win.history.pushState(null,'',writeState(win.location.href,s));update();});
      win.addEventListener('popstate',update);update();
    } catch {host.innerHTML='<p role="alert">The synthetic reference examples could not load. Real-study charts remain independent.</p>';}
  }
  return {validate,designPlot,caseHTML,sensitivityPlot,render,readState,writeState,mount};
})();
if(typeof module!=="undefined") module.exports=AniBenchBroadReference;

if (typeof document !== "undefined") AniBenchBroadReference.mount(document.getElementById("broad-reference"));
