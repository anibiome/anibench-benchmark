const DOMAINS = {molecular_panel:'Molecular panel',physiological_function:'Physical function',digital_record:'Digital records',cognitive_psychological:'Cognition & mood',neural_observation:'Neural observations'};
const QUESTIONS = {current_state:'Current measurements',population_mean:'Population mean',longitudinal_change:'Change over time',controlled_contrast:'Assigned treatment comparison',heterogeneity:'Differences between subgroup effects',measurement_bridge:'Comparison across measurement platforms'};
export const escapeHTML = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const esc = escapeHTML;
const number = value => Number.isInteger(value) ? String(value) : `≈${value.toFixed(1)}`;
const statusName = value => ({attained:'Met',not_attained:'Not met',unknown:'Unknown'}[value] || 'Unknown');
const COMPARE_DEFAULTS = {group:'',factor:1,scenario:'envelope',metric:'attainment',publication:'all',ethics:'all',records:[]};
export function comparisonState(url, catalogue) {
  const params = new URL(url).searchParams;
  const state = structuredClone(COMPARE_DEFAULTS);
  const groups = [...(catalogue.own_population_comparison_groups||[]),...catalogue.comparison_groups];
  state.group = groups.find(g=>g.id===params.get('question'))?.id || groups[0]?.id || '';
  for (const [key, choices] of Object.entries({metric:['attainment','precision'],scenario:['envelope','reported-plug-in','twice-variance'],publication:['all','peer_reviewed_article','unknown'],ethics:['all','approval_reported','unknown']})) {
    if (choices.includes(params.get(key))) state[key]=params.get(key);
  }
  if (['0.5','1','2'].includes(params.get('factor'))) state.factor=Number(params.get('factor'));
  const eligible=new Set(groups.find(g=>g.id===state.group)?.record_ids||[]);
  state.records=[...new Set(params.getAll('record').filter(id=>eligible.has(id)))];
  return state;
}
export function comparisonURL(url, state) {
  const result=new URL(url);const previous=new URL(url).searchParams;result.search='';
  const pilotValues={factor:['0.5','1','2'],metric:['attainment','precision'],scenario:['envelope','q1','q2','q1-rounded-low','q1-rounded-high','q2-rounded-low','q2-rounded-high'],publication:['all','peer_reviewed_results','unpublished','unknown'],ethics:['all','approved','not_approved','unknown']};
  for(const [key,allowed] of Object.entries(pilotValues)){const value=previous.get('pilot_'+key);if(allowed.includes(value))result.searchParams.set('pilot_'+key,value);}
  result.searchParams.set('view','native');
  for(const key of ['group','factor','scenario','metric','publication','ethics'])result.searchParams.set(key==='group'?'question':key,state[key]);
  for(const id of state.records)result.searchParams.append('record',id);
  return result;
}
export function preserveQuestionSupport(previous, edited) {
  return previous.only_questions ? {...edited,only_questions:[...previous.only_questions]} : edited;
}
export function designCSV(packet, rows, metric, scenario) {
  const header=['reference_version','level','metric','variance_scenario','domain','design','lower_percent','upper_percent','suite_sha256','score_sha256','result_sha256'];
  const quote=value=>'"'+String(value).replaceAll('"','""')+'"';
  return [header,...rows.map(r=>{const result=packet.results[r.lane].result;return [packet.version,packet.level,metric,scenario,r.id,r.lane,r.lower,r.upper,result.suite_profile_sha256,result.score_profile_sha256,result.receipt_sha256];})].map(row=>row.map(quote).join(',')).join('\n')+'\n';
}
export function categoryValues(result, scenario, metric) {
  const views = scenario === 'envelope' ? result.envelope : result.scenarios.find(s=>s.scenario_id===scenario)?.views;
  const categories = views?.find(v=>v.view_id==='domain')?.categories;
  if (!categories) throw Error('The result does not contain the selected category view.');
  return categories.map(c=>({id:c.category_id,label:DOMAINS[c.category_id]||c.label,
    lower:metric==='precision'?c.precision_toward_targets.lower_percent:(scenario==='envelope'?c.lower_percent:c.passed_percent),
    upper:metric==='precision'?c.precision_toward_targets.upper_percent:c.upper_percent}));
}
export function validatedBounds(lower, upper) {
  if (![lower,upper].every(Number.isFinite) || lower<0 || upper>100 || lower>upper) throw Error('Invalid percentage bounds.');
  return {lower,upper};
}
export function chartSVG(rows, title, subtitle) {
  const wrap=(text,width)=>String(text).match(new RegExp(`.{1,${width}}(?:\\s|$)|.{1,${width}}`,'g'))||[''];
  const subtitles=wrap(subtitle,130);
  let cursor=95+subtitles.length*18;
  const plotted=rows.map(r=>{validatedBounds(r.lower,r.upper);const labels=wrap(r.label,36);const y=cursor;cursor+=Math.max(65,labels.length*17+16);return {...r,y,labels};});
  const height=cursor+50;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="${height}" viewBox="0 0 1000 ${height}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title><desc>${esc(subtitle)}</desc><defs><pattern id="unknown" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#eaf1eb"/><rect width="3" height="7" fill="#b4c9bd"/></pattern></defs><rect width="100%" height="100%" fill="white"/><g font-family="Arial,sans-serif"><text x="30" y="39" font-size="25" fill="#172624">${esc(title)}</text>${subtitles.map((line,i)=>`<text x="30" y="${65+i*18}" font-size="13" fill="#586863">${esc(line)}</text>`).join('')}${plotted.map(r=>`${r.labels.map((line,i)=>`<text x="30" y="${r.y+16+i*17}" font-size="13" fill="#22372c">${esc(line)}</text>`).join('')}<rect x="305" y="${r.y}" width="630" height="27" rx="4" fill="#f1f5f2"/><rect x="305" y="${r.y}" width="${6.3*r.upper}" height="27" fill="url(#unknown)"/><rect x="305" y="${r.y}" width="${6.3*r.lower}" height="27" fill="${r.lane==='baseline'?'#5e7280':'#00795c'}"/><text x="945" y="${r.y+19}" font-size="13" fill="#22372c" text-anchor="end" paint-order="stroke" stroke="white" stroke-width="4">${esc(number(r.lower))}${r.lower!==r.upper?'–'+esc(number(r.upper)):''}%</text>`).join('')}<text x="305" y="${height-25}" font-size="12">0%</text><text x="620" y="${height-25}" font-size="12" text-anchor="middle">50%</text><text x="935" y="${height-25}" font-size="12" text-anchor="end">100%</text></g></svg>`;
}
export function recordScore(record, factor, scenario, metric) {
  const score=record.scores?.find(s=>s.se_factor===Number(factor));
  if (!score) return null;
  if (scenario==='envelope') {
    const value=metric==='precision'?score.envelope.precision_toward_targets:score.envelope;
    return {...validatedBounds(value.lower_percent,value.upper_percent),score};
  }
  const source=score.scenarios.find(s=>s.scenario_id===scenario);
  if (!source) throw Error('Selected variance scenario is unavailable.');
  const value=metric==='precision'?source.precision_toward_target:{lower_percent:source.passed_percent,upper_percent:source.upper_percent};
  return {...validatedBounds(value.lower_percent,value.upper_percent),score};
}
const download=(name,text,type='application/json')=>{const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
const safeLink=url=>{try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:'#';}catch{return '#';}};
export const bar=(lower,upper,label,lane='after')=>{validatedBounds(lower,upper);return `<div class="track ${lane}" role="img" aria-label="${esc(label)}: ${lower} to ${upper} percent"><span class="bar range" style="width:${upper}%"></span><span class="bar" style="width:${lower}%"></span><span class="value">${number(lower)}${lower!==upper?'–'+number(upper):''}%</span></div>`;};
const axis='<div class="axis"><span>0%</span><span>50%</span><span>100%</span></div>';

async function boot() {
  const $=id=>document.getElementById(id);
  let defaults,state,packet,packetBytes,catalogue,loading=false;
  const sessionKey='anibench-reference-design-v04';
  function saveDesign() {
    if(packet)try{sessionStorage.setItem(sessionKey,JSON.stringify({request:state,metric:$('metric').value,scenario:$('scenario').value}));}catch{/* Export remains available when browser storage is disabled. */}
  }
  let cmp=structuredClone(COMPARE_DEFAULTS);
  function route() {
    const wanted=location.hash.slice(1).split(':')[0]||'compare';
    const page=['compare','design','run','methods','paper'].includes(wanted)?wanted:'compare';
    document.querySelectorAll('.page').forEach(node=>node.hidden=node.id!==page);
    document.querySelectorAll('.masthead nav a').forEach(a=>{if(a.hash==='#'+page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    if(page==='design'&&!packet&&!loading&&state)evaluate();
    if(page==='design'&&packet&&location.hash.includes(':')) {
      const detail=$('detail-'+location.hash.split(':')[1]);
      if(detail){detail.open=true;detail.scrollIntoView({block:'start'});}
    }
  }
  window.addEventListener('hashchange',route);
  window.addEventListener('popstate',()=>{if(catalogue){cmp=comparisonState(location.href,catalogue);renderComparison();}route();});
  function fill() {
    $('level').value=state.level;
    $('design-preset').value='custom';
    for(const key of ['controlled','bridge','paired_endpoints'])$('design-form').elements[key].checked=state.changed[key]??true;
    for(const [key,value] of Object.entries(state.changed)){const el=$('design-form').elements[key];if(el){if(el.type==='checkbox')el.checked=value;else el.value=value;}}
    for(const key of ['only_domain','absent_domain','unknown_domain'])$('design-form').elements[key].value=state.changed[key]||'';
  }
  function form() {
    const out={id:'changed-design'};
    for(const key of ['N','depth','technical_repeats_per_endpoint','repeat_rho'])out[key]=Number($('design-form').elements[key].value);
    for(const key of ['controlled','bridge','paired_endpoints'])out[key]=$('design-form').elements[key].checked;
    for(const key of ['only_domain','absent_domain','unknown_domain'])if($('design-form').elements[key].value)out[key]=$('design-form').elements[key].value;
    return preserveQuestionSupport(state.changed,out);
  }
  function designRows() {
    return ['baseline','changed'].flatMap(lane=>categoryValues(packet.results[lane].result,$('scenario').value,$('metric').value).map(r=>({...r,lane})));
  }
  function renderDesign() {
    const rows=designRows();
    $('design-chart-title').textContent=$('metric').value==='precision'?'Progress toward precision targets (%)':'Reference tasks met (%)';
    $('design-meaning').textContent=$('metric').value==='precision'?'Continuous progress toward the fixed native precision targets. Required measurement support still applies.':'Share of each domain’s fixed task budget meeting precision and required measurement support. Stripes show the range across unresolved support or selected variance scenarios.';
    $('design-chart').innerHTML=Object.entries(DOMAINS).map(([id,label])=>`<div class="chart-row"><h3><a href="#design:${id}" data-domain="${id}">${esc(label)}</a></h3><div class="tracks">${['baseline','changed'].map(lane=>{const r=rows.find(r=>r.id===id&&r.lane===lane);return bar(r.lower,r.upper,label+' '+lane,lane==='baseline'?'before':'after');}).join('')}</div></div>`).join('')+axis;
    const b=packet.results.baseline,c=packet.results.changed;
    $('design-summary').innerHTML=`<strong>Exact ${esc(packet.level)} requirements across both variance scenarios:</strong> baseline ${statusName(b.result.level_attainment).toLowerCase()}; changed design ${statusName(c.result.level_attainment).toLowerCase()}.<br>Baseline: ${b.design.N.toLocaleString()} people, depth ${b.design.depth}. Changed: ${c.design.N.toLocaleString()} people, depth ${c.design.depth}.`;
    if(c.design.only_questions)$('design-summary').insertAdjacentHTML('beforeend',`<br>Selected question support: ${c.design.only_questions.map(q=>esc(QUESTIONS[q]||q)).join('; ')}. Other requirements remain in the benchmark.`);
    $('design-details').innerHTML=Object.entries(DOMAINS).map(([id,label])=>`<details id="detail-${id}"><summary>${esc(label)} — what determines the result?</summary>${['baseline','changed'].map(lane=>`<h3>${lane==='baseline'?'Baseline':'Changed design'}</h3>${packet.results[lane].result.suite_result.scenarios.filter(s=>$('scenario').value==='envelope'||s.scenario_id===$('scenario').value).map(s=>`<p><b>${s.scenario_id==='declared-noise'?'Declared variance':'Twice the variance'}</b></p>${s.targets.filter(t=>t.canonical_id.startsWith(id+'.')).map(t=>{const task=packet.profile.targets.find(p=>p.canonical_id===t.canonical_id).task;const question=t.canonical_id.slice(id.length+1);return `<details><summary>${esc(QUESTIONS[question]||question)}: ${statusName(t.attainment)}</summary><p>${esc(packet.metadata[t.canonical_id].rationale)}</p><p><b>Exact timing:</b> ${esc(task.horizon)}</p><div class="table-wrap"><table><thead><tr><th>Target</th><th>Sampling variance</th><th>Allowed variance</th><th>Unit</th></tr></thead><tbody>${task.functionals.map(f=>{const diagnostic=t.likelihood_diagnostics.find(d=>d.functional_id===f.functional_id);return `<tr><td>${esc(f.functional_id)}</td><td>${esc(diagnostic?.variance??'Unknown')}</td><td>${esc(f.variance_limit)}</td><td>${esc(f.unit)}²</td></tr>`;}).join('')}</tbody></table></div></details>`;}).join('')}`).join('')}`).join('')}<p><a href="#design">Back to chart ↑</a></p></details>`).join('');
    document.querySelectorAll('[data-domain]').forEach(a=>a.onclick=()=>{const detail=$('detail-'+a.dataset.domain);detail.open=true;detail.scrollIntoView({behavior:'smooth',block:'start'});});
    if(location.hash.startsWith('#design:'))route();
  }
  async function evaluate() {
    if(loading)return;
    loading=true;packet=null;packetBytes=null;
    $('design-chart').replaceChildren();$('design-summary').replaceChildren();$('design-details').replaceChildren();
    $('design-status').textContent='Evaluating with the local Python engine…';
    $('design-form').querySelectorAll('button,input,select').forEach(e=>e.disabled=true);
    $('level').disabled=true;
    try {
      const response=await fetch('/api/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(state)});
      const bytes=await response.text();const result=JSON.parse(bytes);
      if(!response.ok)throw Error(result.error||'Evaluation failed.');
      packet=result;packetBytes=bytes;$('design-status').textContent='';renderDesign();saveDesign();
    } catch(error){$('design-status').textContent=`Not evaluated: ${error.message} Correct the design and try again.`;}
    finally{loading=false;$('design-form').querySelectorAll('button,input,select').forEach(e=>e.disabled=false);$('level').disabled=false;}
  }
  function calculation(record) {
    const selected=record.scores?.find(s=>s.se_factor===Number(cmp.factor));
    const scenarios=(selected?.scenarios||record.scenarios||[]).filter(s=>cmp.scenario==='envelope'||s.scenario_id===cmp.scenario);
    return `<p><b>Independent units:</b> ${esc(record.n??'Not supplied in this summary')} · <b>Independence:</b> ${esc(record.independence??'See source qualifications')}</p><div class="table-wrap"><table><thead><tr><th>Variance assumption</th><th>Sampling variance</th><th>Standard error (${esc(record.unit)})</th><th>Target SE</th><th>Task decision</th></tr></thead><tbody>${scenarios.map(s=>`<tr><td>${esc(s.scenario_id.replaceAll('-',' '))}</td><td>${esc(s.variance??'Unknown')}</td><td>${esc(s.standard_error??'Unknown')}</td><td>${esc(selected?.target_se??'Not defined')}</td><td>${selected?statusName(s.attainment):'No percentage criterion'}</td></tr>`).join('')}</tbody></table></div><p>${selected?'One task, fixed weight 1. The task passes when its supported likelihood standard error is at or below the target. Precision progress is the target variance divided by the sampling variance, capped at 100%.':'Only native precision is evaluated for this contrast. No percentage threshold has been defined.'}</p><p><b>Reference policy:</b> ${esc(record.reference_policy||catalogue.reference_policy)} These resolution conventions are not established clinical cutoffs. Native variance comes from the qualified source summary; the exact source locator and assumptions are below.</p>`;
  }
  function comparisonGroups() {return [...(catalogue.own_population_comparison_groups||[]),...catalogue.comparison_groups];}
  function renderComparison() {
    const groups=comparisonGroups();if(!groups.length){$('comparison-status').textContent='No qualified task comparison is available in this snapshot.';return;}
    const group=groups.find(g=>g.id===cmp.group)||groups[0];cmp.group=group.id;
    const studies=new Map(catalogue.studies.map(s=>[s.family_id,s]));
    const available=catalogue.records.filter(r=>group.record_ids.includes(r.id));
    if(!cmp.records.length){const families=new Set();cmp.records=available.filter(r=>{if(families.has(r.family_id)||families.size>=3)return false;families.add(r.family_id);return true;}).map(r=>r.id);}
    const records=available.filter(r=>cmp.records.includes(r.id)).filter(r=>{
      const s=studies.get(r.family_id);
      return (cmp.publication==='all'||s?.publication?.status===cmp.publication)&&(cmp.ethics==='all'||s?.ethics?.status===cmp.ethics);
    });
    const option=(v,label,selected)=>`<option value="${esc(v)}"${String(v)===String(selected)?' selected':''}>${esc(label)}</option>`;
    $('comparison-controls').innerHTML=`<div class="toolbar"><label>Biological question<select id="cmp-group">${groups.map(g=>option(g.id,g.label,cmp.group)).join('')}</select></label><label>Show<select id="cmp-metric">${option('attainment','Precision target met (%)',cmp.metric)}${option('precision','Progress toward target (%)',cmp.metric)}</select></label><label>Variance assumption<select id="cmp-scenario">${option('envelope','Both scenarios',cmp.scenario)}${option('reported-plug-in','Reported variance',cmp.scenario)}${option('twice-variance','Twice the variance',cmp.scenario)}</select></label></div><details><summary>Precision target and evidence filters</summary><div class="toolbar filter-strip"><label>Target sensitivity<select id="cmp-factor">${option(.5,'0.5× · stricter',cmp.factor)}${option(1,'1× · reference',cmp.factor)}${option(2,'2× · looser',cmp.factor)}</select></label><label>Study publication<select id="cmp-publication">${option('all','All statuses',cmp.publication)}${option('peer_reviewed_article','Peer-reviewed results',cmp.publication)}${option('unknown','Unknown',cmp.publication)}</select></label><label>Ethics evidence<select id="cmp-ethics">${option('all','All statuses',cmp.ethics)}${option('approval_reported','Approval reported',cmp.ethics)}${option('unknown','Unknown',cmp.ethics)}</select></label></div></details>`;
    const groupName=r=>available.filter(other=>other.family_id===r.family_id&&other.population_scope===r.population_scope).length>1?r.id.replace(r.family_id+'_','').replaceAll('_',' '):r.population_scope.split(';')[0];
    const name=r=>r.family_id.replaceAll('_',' ')+' · '+groupName(r);
    $('comparison-controls').insertAdjacentHTML('beforeend',`<details><summary>Choose study groups (${cmp.records.length} selected)</summary><div class="record-picker">${available.map(r=>`<label class="check"><input type="checkbox" data-record="${esc(r.id)}"${cmp.records.includes(r.id)?' checked':''}>${esc(name(r))}</label>`).join('')}</div></details>`);
    const changed=()=>{renderComparison();history.pushState(null,'',comparisonURL(location.href,cmp));};
    for(const key of ['group','metric','scenario','factor','publication','ethics'])$('cmp-'+key).onchange=e=>{cmp[key]=e.target.value;if(key==='group')cmp.records=[];changed();};
    document.querySelectorAll('[data-record]').forEach(el=>el.onchange=()=>{const selected=[...document.querySelectorAll('[data-record]:checked')].map(e=>e.dataset.record);if(!selected.length){el.checked=true;return;}cmp.records=selected;changed();});
    const scored=records.map(r=>({record:r,value:recordScore(r,cmp.factor,cmp.scenario,cmp.metric)}));
    const targets=[...new Set(scored.filter(x=>x.value).map(x=>x.value.score.target_se+' '+x.record.unit))];
    const filterText=[cmp.publication==='all'?null:'Publication: '+cmp.publication.replaceAll('_',' '),cmp.ethics==='all'?null:'Ethics: '+cmp.ethics.replaceAll('_',' ')].filter(Boolean).join(' · ');
    $('comparison-status').textContent='';
    $('comparison-chart').innerHTML=`<div class="card"><div class="card-heading"><div><span class="eyebrow">${esc(group.estimand_kind?.replaceAll('_',' ')||'SOURCE PRECISION')}</span><h2>${esc(group.label)}</h2></div><span class="chip">Source-conditional</span></div><p class="comparison-note">${group.cross_study_precision_comparison_allowed?'Precision for each study’s own population.':esc(group.comparison_scope)}${targets.length?' Standard-error target: '+esc(targets.join('; '))+'.':''}</p>${group.measurement_equivalence?`<p class="comparison-note"><b>Comparison assumption:</b> ${esc(group.measurement_equivalence)}${group.unit_alias_rule?' '+esc(group.unit_alias_rule):''}</p>`:''}${filterText?`<p class="comparison-note">${esc(filterText)}</p>`:''}${records.length?scored.map(({record:r,value:v})=>`<div class="chart-row"><h3>${esc(r.family_id.replaceAll('_',' '))}<br><span class="small">${esc(groupName(r))}</span></h3><div class="tracks">${v?bar(v.lower,v.upper,r.id):`<p class="comparison-note">Native SE: ${r.scenarios?.filter(s=>cmp.scenario==='envelope'||s.scenario_id===cmp.scenario).map(s=>esc(s.scenario_id.replaceAll('-',' '))+': '+esc(s.standard_error??'Unknown')+' '+esc(r.unit)).join(' / ')||'Unknown'}<br>No frozen percentage threshold.</p>`}</div></div>`).join('')+axis:'<p class="empty">No studies match these evidence filters. Unknown approval does not mean non-approval.</p><button id="clear-filters">Clear filters</button>'}<p class="comparison-note">Each percentage here concerns one precision task. It is not a full biological-domain or whole-study score. Different populations do not support treatment-effect comparisons.</p><div class="actions"><button id="export-comparison">Export selected data</button><button id="export-comparison-svg"${scored.every(x=>!x.value)?' disabled':''}>Export chart SVG</button></div></div>`;
    $('clear-filters')?.addEventListener('click',()=>{cmp.publication='all';cmp.ethics='all';changed();});
    $('export-comparison').onclick=()=>download('anibench-task-comparison.json',JSON.stringify({schema:'anibench.selected-task-comparison.v1',catalogue_version:catalogue.version,evaluator_commit:catalogue.evaluator_commit,selection:structuredClone(cmp),group,records},null,2));
    $('export-comparison-svg').onclick=()=>download('anibench-task-comparison.svg',chartSVG(scored.filter(x=>x.value).map(({record:r,value:v})=>({...v,label:name(r),lane:'changed'})),group.label,['One precision task · '+cmp.metric+' · '+cmp.scenario,'Target: '+targets.join('; '),'Catalogue '+catalogue.version+' · publication '+cmp.publication+' · ethics '+cmp.ethics,group.measurement_equivalence||group.comparison_scope].join(' | ')),'image/svg+xml');
    $('comparison-details').innerHTML=records.map(r=>`<details><summary>${esc(name(r))}: source and calculation</summary>${calculation(r)}<p><b>Population:</b> ${esc(r.population_scope)}<br><b>Timing:</b> ${esc(r.horizon)}<br><b>Measurement:</b> ${esc(r.operator)}</p><p>${(r.qualifications||[]).map(esc).join(' ')}</p><p><a href="${esc(safeLink(r.source?.url))}" target="_blank" rel="noopener noreferrer">Original source ↗</a><br>Locator: <code>${esc(r.source?.locator||'See source ledger')}</code><br>Source SHA-256: <code>${esc(r.source?.sha256||'Not qualified')}</code></p><p>Record identity: <code>${esc(r.record_sha256)}</code></p></details>`).join('');
  }
  for(const key of ['only_domain','absent_domain','unknown_domain'])for(const [id,label]of Object.entries(DOMAINS)){const o=document.createElement('option');o.value=id;o.textContent=label;$('design-form').elements[key].append(o);}
  $('design-form').onsubmit=e=>{e.preventDefault();state={level:$('level').value,baseline:state.baseline,changed:form()};evaluate();};
  $('design-preset').onchange=e=>{
    const preset=e.target.value;if(preset==='custom')return;
    const patches={balanced:{N:1290,depth:256},tiny:{N:2,depth:1000000,technical_repeats_per_endpoint:1000,repeat_rho:.99},shallow:{N:1000000,depth:1,technical_repeats_per_endpoint:1,paired_endpoints:false,controlled:false,bridge:false},neural:{N:1290,depth:256,absent_domain:'neural_observation'}};
    state.changed={...structuredClone(defaults.baseline),id:'hypothetical-'+preset,...patches[preset]};fill();$('design-preset').value=preset;evaluate();
  };
  $('level').onchange=()=>{if(state){state.level=$('level').value;evaluate();}};
  for(const id of ['metric','scenario'])$(id).onchange=()=>{if(packet){renderDesign();saveDesign();}};
  $('reset').onclick=()=>{state=structuredClone(defaults);fill();evaluate();};
  $('pin').onclick=()=>{if(packet){state.baseline={...packet.results.changed.design,id:'baseline-design'};evaluate();}};
  $('export-design').onclick=()=>{if(packetBytes)download('anibench-plan-result.json',packetBytes);};
  $('export-design-svg').onclick=()=>{if(packet)download('anibench-plan-chart.svg',chartSVG(designRows().map(r=>({...r,label:r.label+' · '+(r.lane==='baseline'?'baseline':'changed')})),`${packet.level} · ${$('design-chart-title').textContent}`,'Hypothetical reference v0.4 · '+$('scenario').selectedOptions[0].textContent),'image/svg+xml');};
  $('export-design-csv').onclick=()=>{if(packet)download('anibench-plan-chart.csv',designCSV(packet,designRows(),$('metric').value,$('scenario').value),'text/csv');};
  $('download-template').onclick=()=>{if(defaults)download('design.json',JSON.stringify(defaults,null,2));};
  document.querySelector('.skip').onclick=e=>{e.preventDefault();$('content').focus();};
  $('import-design').onchange=async e=>{try{const file=e.target.files[0];if(!file||file.size>5_000_000)throw Error('Choose an AniBench planner result below 5 MB.');const imported=JSON.parse(await file.text());if(imported.contract!=='anibench.local-planner.v1')throw Error('Expected an AniBench planner result.');state={level:imported.level,baseline:imported.results.baseline.design,changed:imported.results.changed.design};fill();$('import-status').textContent='The imported design will be evaluated again.';location.hash='design';await evaluate();}catch(error){$('import-status').textContent=error.message;}};
  route();
  const initialization=await Promise.allSettled([
    (async()=>{const response=await fetch('/api/defaults');if(!response.ok)throw Error('Local evaluator unavailable. Start anibench workbench.');defaults=await response.json();state=structuredClone(defaults);try{const saved=JSON.parse(sessionStorage.getItem(sessionKey)||'null');if(saved?.request&&JSON.stringify(saved.request).length<=16384){state=saved.request;if(['attainment','precision'].includes(saved.metric))$('metric').value=saved.metric;if(['envelope','declared-noise','double-noise'].includes(saved.scenario))$('scenario').value=saved.scenario;}}catch{/* A damaged local draft falls back to the explicit example. */}fill();if(location.hash.startsWith('#design'))await evaluate();})(),
    (async()=>{const response=await fetch('catalogue.json');if(!response.ok)throw Error('The qualified comparison snapshot is not included.');catalogue=await response.json();cmp=comparisonState(location.href,catalogue);if(catalogue.schema!=='anibench.integrated-public-task-catalogue.v1')throw Error('Unsupported comparison snapshot.');renderComparison();})(),
  ]);
  if(initialization[0].status==='rejected')$('design-status').textContent=initialization[0].reason.message;
  if(initialization[1].status==='rejected')$('comparison-status').textContent=initialization[1].reason.message;
  const selectView=(view,push=false)=>{for(const name of ['pilot','native'])$('view-'+name).setAttribute('aria-pressed',String(view===name));$('pilot-panel').hidden=view!=='pilot';$('single-panel').hidden=view!=='native';if(push){const u=new URL(location.href);u.searchParams.set('view',view);history.pushState(null,'',u);}};
  for(const view of ['pilot','native'])$('view-'+view).onclick=()=>selectView(view,true);
  window.addEventListener('popstate',()=>selectView(new URL(location.href).searchParams.get('view')==='native'?'native':'pilot'));
  selectView(new URL(location.href).searchParams.get('view')==='native'?'native':'pilot');
  try{const pilot=await import('./pilot.mjs');await pilot.bootPilot();}catch{$('pilot-status').textContent='The pilot snapshot is unavailable. Individual measurement comparisons remain available.';}
}
if(typeof document!=='undefined')boot();
