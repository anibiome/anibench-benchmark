# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Synthetic conditional-reference sensitivity using actual AniBench benchmark engine."""
import argparse,copy,hashlib,json,math,pathlib
from fractions import Fraction
import numpy as np
from anibench.benchmark_v1 import evaluate_benchmark
from anibench.finite_suites_v1 import scientific_frame_sha256,suite_sha256
from anibench.finite_tasks_v1 import finite_task_sha256
B=pathlib.Path(__file__).parent
POOL=json.loads((B.parent/'WORKLOAD_CANDIDATE.json').read_text());ANCHORS={x['id']:x for x in POOL['targets']}
DOMAINS={'molecular_panel':['albumin','il6','apob','fasting_glucose','triglycerides','leucine','lactate','cd4_count','cd4_naive_fraction','microbial_f_prausnitzii','microbial_butyrate_pathway','muscle_ppargc1a','adipose_adipocyte_area'],'physiological_function':['grip','gait','systolic'],'digital_record':['acceleration','sleep_duration'],'cognitive_psychological':['reaction_time','symbol_coding','depressive_symptoms'],'neural_observation':['p3b','n170']}
QUESTIONS=['current_state','population_mean','longitudinal_change','controlled_contrast','heterogeneity','measurement_bridge']
REQUIRED={d:QUESTIONS[:3]+(['controlled_contrast'] if d in ['molecular_panel','physiological_function','digital_record'] else []) for d in DOMAINS}
AB2={d:list(qs) for d,qs in REQUIRED.items()}
for d in ['cognitive_psychological','neural_observation']:AB2[d].append('controlled_contrast')
for d in ['molecular_panel','physiological_function']:AB2[d].append('heterogeneity')
for d in ['molecular_panel','neural_observation']:AB2[d].append('measurement_bridge')
# Chosen task subsets; panel depth is explicit, not an omics label.
def coordinates(d,q):
 if q in ['current_state','population_mean','longitudinal_change']:return DOMAINS[d]
 return {'molecular_panel':{'controlled_contrast':['fasting_glucose','triglycerides','muscle_ppargc1a'],'heterogeneity':['fasting_glucose','triglycerides'],'measurement_bridge':['albumin','il6','apob']},'physiological_function':{'controlled_contrast':['grip','gait'],'heterogeneity':['grip','gait']},'digital_record':{'controlled_contrast':['sleep_duration']},'cognitive_psychological':{'controlled_contrast':['reaction_time','symbol_coding']},'neural_observation':{'controlled_contrast':['p3b','n170'],'measurement_bridge':['p3b','n170']}}[d][q]
RATIONALES={'current_state':'Resolve person-specific observable at native reference scale; no population size can replace missing direct/bridged observation. Anchor-specific rationale below.','population_mean':'One quarter of current-state SE: reference population mean challenge exploits independent people; this is a4fold resolution policy, not clinical significance. Source-qualified SD/sqrt(n) is sufficient under sampling assumptions.','longitudinal_change':'Require individual paired-change SE at anchor scale AND cohort mean paired-change SE atquarteranchor scale; focalperson excluded frompopulation sample; independentconditional likelihoodblocks.','controlled_contrast':'Same native scale as state for a prespecified randomized contrast; effect sign/magnitude never gates capacity.','heterogeneity':'Same native scale for difference-of-treatment-effects across two prespecified strata; independent support in four assignment×stratum cells is needed.','measurement_bridge':'Half the native state scale for estimating paired platform/site mean difference; bias need not be zero. Precision of bridge parameters, not model prediction success.'}
ANCHOR_REASONS={'albumin':'1g/L is a transparent fine concentration increment; retained from failedNHANESpilot without retuning.','il6':'0.5pg/mL tests sub-pg resolution and forces LOQ/censoring scrutiny; no claim every platform can attain it.','apob':'0.05g/L is an explicit5centigram/L increment requiring quantitative assay, not RFU.','fasting_glucose':'0.25mmol/L separates fine fasting-state variation; fixed challenge scale, not diagnostic boundary.','triglycerides':'0.15mmol/L is a chosen lipid response increment; fasting/time alignment mandatory.','leucine':'10umol/L is a round targeted-metabolite increment; mass-spectrometry calibration must support it.','lactate':'0.2mmol/L imposes preanalytic timing sensitivity; no conversion from untargeted peak intensity.','cd4_count':'50cells/uL requires absolute-volume calibration, preventing cell-sequencing depth from substituting for cell count.','cd4_naive_fraction':'5percentagepoints is a composition-resolution challenge within a fixed CD4 gate; denominator explicit.','microbial_f_prausnitzii':'0.01relative fraction means1percentagepoint under a fixed compositional denominator, not absolute abundance.','microbial_butyrate_pathway':'10normalized gene copies per million is an operational resolution choice; pathway accession/normalizer must be pinned before biological use.','muscle_ppargc1a':'0.5log2TPM corresponds to sqrt(2)fold on the frozen transformed scale; low-count floor cannot be hidden.','adipose_adipocyte_area':'100um2 is a microscopy area-resolution increment; segmentation/spatial sampling covariance needed.','grip':'2kg-force matches an interpretable dynamometer increment; posture/practice bias separately audited.','gait':'0.05m/s is a task-speed increment with fixed start/course; policy, not asserted MCID.','systolic':'5mmHg retained fromNHANESfalsification; current-session reading summary, not usual long-term pressure.','acceleration':'5milli-g targets a small sensor-scale contrast; wear/nonwear and placement fixed.','sleep_duration':'20minutes is4.17percent of the480minute reference window; observed annotation total, not latent true sleep.','reaction_time':'20ms makes hardware/display latency a material operator issue; correct-trial definition frozen.','symbol_coding':'3correct symbols demands a fixed form/duration; observed score, not interval-scaled intelligence.','depressive_symptoms':'2PHQ9points is an observed-score reference increment; no latent mental-health equivalence asserted.','p3b':'1uV is the inherited explicit ERP resolution convention; does not imply universal person-level source calibration.','n170':'1uV keeps the same voltage scale while requiring a distinct task/window/ROI; no duplication of P3b evidence.'}
SETTINGS={'current_state':'One fixed acquisition session (digital:7day wrist or8hour sleep interval)','population_mean':'Frozen eligible adult sampling frame at baseline; source population mapping exact','longitudinal_change':'Baseline to12months except directERP7days and digital two prespecified weekly/night windows; exact task addendum must freeze intervals','controlled_contrast':'Population mean difference of two disjoint randomized arms; exact domain-specific assigned conditions/horizon declared in coordinate_windows; no individual treatment effect or focal cortical-connectivity claim','heterogeneity':'Same randomized intervention, two baseline strata fixed before assignment; contrast of conditional average effects','measurement_bridge':'Paired same-person/specimen measurements on two fixed platforms/settings; timing and operator order frozen; estimate offset precision'}

def coordinate_window(i,q):
 if i=='acceleration': base='Wrist ENMO mean over first7consecutive24hourdays: at least16validwearhours/day on all7days, equaldayweight; calibratedwristplacement and rawprocessing fixed'
 elif i=='sleep_duration': base='Recording-clock22:00to06:00 fullyscored8hourwindow; scoredW/1/2/3/4/R only, no gaps/movement/unscored; sum1/2/3/4/Rminutes'
 else: base='One fixed acquisition session with registered operator'
 if q=='longitudinal_change':return base+' at baseline and '+('7dayslater' if i in ['p3b','n170','sleep_duration'] else '365dayslater')+'; technical repeats occurwithin eachendpoint, notextra biologicalvisits'
 if q in ['controlled_contrast','heterogeneity']:
  if i in ['fasting_glucose','triglycerides','muscle_ppargc1a']: return base+' at3hoursafter randomized30minute cycling60percentbaselineVO2peak versus seatedrest; populationarmdifference'
  if i in ['grip','gait']: return base+' at365daysafter randomized2sessions/weekresistanceprogramme versus attentioncontrol; populationarmdifference'
  if i=='sleep_duration':return base+' during assigned firstnight22:00bedtime opportunity versus routinebedtime; disjointparallelpersonarms, notcrossover'
  if i in ['reaction_time','symbol_coding']:return base+' at28daysafter randomizedtasktraining versus attentioncontrol; populationarmdifference'
  return base+' afterbetweenperson randomizedstimulus-conditionprotocol A versus B; precise ERPcontrastwindow300-600msPz forP3b,110-170msP8 forN170; syntheticcandidateoperators notsourcecalibration'
 if q=='measurement_bridge':return base+' measured onboth declaredplatforms withinone session/specimen; pairedpopulation meanoffset, platformorder randomized'
 return base+'; '+q+' at this exacttime scale'

def make_profiles(tolerance_factor=1.):
 profiles={};metadata={};parent=None
 for level,assignment in [('AB1',REQUIRED),('AB2',AB2)]:
  targets=[]
  for d,qs in assignment.items():
   for q in qs:
    ids=coordinates(d,q);anchorids=list(ids);units=[ANCHORS[i]['unit'] for i in ids];m=len(ids);base=[ANCHORS[i]['resolution']['standard_error_limit'] for i in ids];factor={'population_mean':.25,'measurement_bridge':.5}.get(q,1.)
    reference=[x*factor for x in base];physical_scale=list(reference)
    if q=='longitudinal_change':
     ids=[i+'.individual_change' for i in anchorids]+[i+'.population_mean_change_other_people' for i in anchorids];units=units+units;reference=base+[x*.25 for x in base];physical_scale=base+base;m=len(ids)
    limits=[(x*tolerance_factor*(.5 if level=='AB2' else 1))**2 for x in reference]
    model={'contract':'native-broad-reference.synthetic-model.v0.4','domain':d,'question':q,'coordinate_ids':ids,'units':units,'reference_SE':reference,'geometry':'Hypothetical same-model risk ratios derivedfromdeclaredN/depth/visits/assignment/bridge; notassaynameinference','correlation':'Compound0.25withinpanel; same2sharednoise scenarios','endpoint_error_correlation':0.,'person_residual_B_in_anchor_units':40,'measurement_R_in_anchor_units':80,'longitudinal':'ConditionalGaussian: focalperson fixedchange theta; OTHER N-1people changes iidNormal(mu,Bdelta), independentof focalmeasurementerror. H=I, R=blockdiag[V,(Bdelta+V)/(N-1)]; V=2R/(depth*k_eff),c0,Bdelta40anchorunits. No prior relation between theta andmu.','exact_coordinate_windows':{i:coordinate_window(i,q) for i in anchorids}}
    ident=d+'.'+q;role='perturbation' if q in ['controlled_contrast','heterogeneity'] else 'observation'
    task={'contract':'anibench.finite-task-definition.v1','task_id':ident,'task_version':'reference-candidate0.4','source_sha256':finite_task_sha256({'pool_sha256':hashlib.sha256((B.parent/'WORKLOAD_CANDIDATE.json').read_bytes()).hexdigest(),'settings':SETTINGS[q],'coordinate_ids':ids}),'model_sha256':finite_task_sha256(model),'target_population':'Declared synthetic adult reference population; no real cohort mapping','estimand':d+' '+q+' on exact declared coordinates: '+', '.join(ids)+('; focalindividualfixedchange andpopulationmean inferredfrom OTHER N-1independentpeople; no jointprior relationship' if q=='longitudinal_change' else ''),'horizon':json.dumps({i:coordinate_window(i,q) for i in anchorids},sort_keys=True),'claim_lane':'conditional_design','comparison_scope':'finite_functionals_only','parameter_units':units,'prior_precision':np.diag([1/(1000*x*x) for x in reference]).tolist(),'required_support':[{'domain_id':d,'role':role}],'functionals':[{'functional_id':i,'coefficients':np.eye(m)[k].tolist(),'unit':units[k],'variance_limit':limits[k]} for k,i in enumerate(ids)]}
    targets.append({'canonical_id':ident,'frame_sha256':scientific_frame_sha256(task),'task':task});metadata[ident]={'domain':d,'question':q,'coordinates':ids,'reference_SE':reference,'physical_scale_SE':physical_scale,'model':model,'rationale':RATIONALES[q],'anchor_rationales':{i:ANCHOR_REASONS[i] for i in anchorids}}
  p={'contract':'anibench.finite-suite-profile.v1','profile_id':'native-broad-reference-candidate-'+level+'-v0.4-tolerance'+str(tolerance_factor),'profile_type':'illustrative','scope':'Selected namednativepanels and scientificquestions; NOT fullbiology orcalibratedAB1/2standard','tolerance_authority':'Versioned governance reference increments; half/twice sensitivity','calibration_authority':'Synthetic risk mapping only; real source operators not admitted','precision_basis':'likelihood_only','scenario_quantifier':'all_declared_scenarios','scenario_ids':['declared-noise','double-noise'],'parent_sha256':parent,'targets':targets};key=suite_sha256(p);profiles[key]=p;parent=key
 return profiles,metadata

def score_profile(p,policy,meta):
 targets=p['targets'];domaincounts={d:sum(meta[t['canonical_id']]['domain']==d for t in targets) for d in DOMAINS};questions=sorted({meta[t['canonical_id']]['question'] for t in targets});qcounts={q:sum(meta[t['canonical_id']]['question']==q for t in targets) for q in questions}
 weights={t['canonical_id']: Fraction(1,len(DOMAINS)*domaincounts[meta[t['canonical_id']]['domain']]) if policy=='domain_budget' else Fraction(1,len(questions)*qcounts[meta[t['canonical_id']]['question']]) if policy=='question_budget' else Fraction(1,len(targets)) for t in targets};den=math.lcm(*(x.denominator for x in weights.values()));w={k:int(v*den) for k,v in weights.items()};views=[]
 for view,labels in [('overview',['all']),('domain',list(DOMAINS)),('question',questions)]:
  cats=[]
  for label in labels:
   selected=[t for t in targets if view=='overview' or meta[t['canonical_id']][view]==label]
   cats.append({'category_id':label,'label':label+' selected reference tasks','question':'Fraction of frozen '+policy+' taskbudget attained; noallbiologyclaim','targets':[{'canonical_id':t['canonical_id'],'weight':w[t['canonical_id']]} for t in selected]})
  views.append({'view_id':view,'label':view,'categories':cats})
 return {'contract':'anibench.score-profile.v1','score_profile_id':p['profile_id']+'-'+policy,'suite_profile_sha256':suite_sha256(p),'weighting_rationale':policy+' normative fixedbudget; views are alternative partitions not extra votes','gate_only_targets':[],'views':views}

DESIGNS=[{'id':'balanced-reference','N':640,'depth':16,'technical_repeats_per_endpoint':4,'repeat_rho':.2,'controlled':True,'bridge':True}, {'id':'tighter-reference','N':5120,'depth':32,'technical_repeats_per_endpoint':4,'repeat_rho':.2,'controlled':True,'bridge':True}, {'id':'two-person-extreme-depth','N':2,'depth':1000000,'technical_repeats_per_endpoint':1000,'repeat_rho':.99,'controlled':True,'bridge':True}, {'id':'giant-shallow','N':1000000,'depth':1,'technical_repeats_per_endpoint':1,'repeat_rho':.2,'controlled':False,'bridge':False}, {'id':'molecular-specialist','N':640,'depth':32,'technical_repeats_per_endpoint':4,'repeat_rho':.2,'controlled':True,'bridge':True,'only_domain':'molecular_panel'}, {'id':'question-specialist','N':5120,'depth':32,'technical_repeats_per_endpoint':4,'repeat_rho':.2,'controlled':True,'bridge':True,'only_questions':['controlled_contrast','heterogeneity','measurement_bridge']}, {'id':'missing-neural','N':5120,'depth':32,'technical_repeats_per_endpoint':4,'repeat_rho':.2,'controlled':True,'bridge':True,'absent_domain':'neural_observation'}, {'id':'unknown-neural','N':5120,'depth':32,'technical_repeats_per_endpoint':4,'repeat_rho':.2,'controlled':True,'bridge':True,'unknown_domain':'neural_observation'}, {'id':'correlated-repeats','N':640,'depth':16,'technical_repeats_per_endpoint':100,'repeat_rho':1.,'controlled':True,'bridge':True}]
DESIGNS.extend([{'id':'person-floor-AB1-witness','N':640,'depth':256,'technical_repeats_per_endpoint':2,'repeat_rho':.2,'controlled':True,'bridge':True},{'id':'person-floor-AB2-witness','N':6400,'depth':1280,'technical_repeats_per_endpoint':2,'repeat_rho':.2,'controlled':True,'bridge':True}])

def validate_design(design):
 required={'id','N','depth','technical_repeats_per_endpoint','repeat_rho','controlled','bridge'}
 allowed=required|{'paired_endpoints','only_domain','only_questions','absent_domain','unknown_domain'}
 if not isinstance(design,dict) or not required<=set(design) or not set(design)<=allowed:raise ValueError('Unknown or missing designfields')
 if not isinstance(design['id'],str) or not design['id'].strip():raise ValueError('NonemptydesignID required')
 for field in ['N','depth','technical_repeats_per_endpoint']:
  if type(design[field]) is not int or not 0<design[field]<=2**53:raise ValueError('Positiveinteger '+field+' required')
 for field in ['controlled','bridge','paired_endpoints']:
  if field in design and type(design[field]) is not bool:raise ValueError('StrictBoolean '+field+' required')
 rho=design['repeat_rho']
 if type(rho) not in [int,float] or not math.isfinite(rho) or not 0<=rho<=1:raise ValueError('Correlation mustbefinite in[0,1]')
 if design['N']<2:raise ValueError('Focalplusotherperson model requires N>=2')
 if design['controlled'] and design['N']%2:raise ValueError('Balancedtwoarm allocation requires evenN')
 for field in ['only_domain','absent_domain','unknown_domain']:
  if field in design and design[field] not in DOMAINS:raise ValueError('Unknown domain')
 if design.get('absent_domain') is not None and design.get('absent_domain')==design.get('unknown_domain'):raise ValueError('Conflicting domainstatus')
 if 'only_questions' in design:
  qs=design['only_questions']
  if not isinstance(qs,list) or not qs or any(not isinstance(q,str) or q not in QUESTIONS for q in qs) or len(set(qs))!=len(qs):raise ValueError('Invalid question subset')

for design in DESIGNS: design['paired_endpoints']=design['id']!='giant-shallow'

def request(p,sp,meta,design):
 validate_design(design)
 binding={'design_id':design['id'],'design_source_sha256':finite_task_sha256(design)};scenarios=[]
 for scenario,mult in [('declared-noise',1.),('double-noise',2.)]:
  out=[]
  for target in p['targets']:
   ident=target['canonical_id'];t=target['task'];md=meta[ident];d,q=md['domain'],md['question'];N,depth,v,rho=[design[k] for k in ['N','depth','technical_repeats_per_endpoint','repeat_rho']]
   ratio={'current_state':4/depth,'population_mean':80/N,'longitudinal_change':8*(1+rho*(v-1))/(v*depth),'controlled_contrast':4*(40+80/depth)/N,'heterogeneity':16*(40+80/depth)/N,'measurement_bridge':4/(N/2)}[q]
   support=not(design.get('only_domain',d)!=d or ('only_questions' in design and q not in design['only_questions']) or design.get('absent_domain')==d or (q in ['controlled_contrast','heterogeneity'] and not design['controlled']) or (q=='measurement_bridge' and not design['bridge']) or (q=='longitudinal_change' and not design.get('paired_endpoints',True)) or (q=='heterogeneity' and (N<4 or N%4!=0)))
   if design.get('unknown_domain')==d and support:support=None
   sigma=np.asarray(md['physical_scale_SE']);m=len(sigma)
   if q=='longitudinal_change':
    k_eff=v/(1+(v-1)*rho);V=160/(depth*k_eff);K=np.diag([V,(40+V)/(N-1)])*mult;dim=m//2;C=.75*np.eye(dim)+.25*np.ones((dim,dim));Cinv=np.eye(dim)/.75-(.25/(.75*(.75+.25*dim)))*np.ones((dim,dim));det=K[0,0]*K[1,1]-K[0,1]**2;Kinv=np.array([[K[1,1],-K[0,1]],[-K[0,1],K[0,0]]])/det;R=np.kron(K,C)*(sigma[:,None]*sigma[None,:]);J=np.kron(Kinv,Cinv)/(sigma[:,None]*sigma[None,:])
   else:
    R=(sigma[:,None]*sigma[None,:])*ratio*mult*(.75*np.eye(m)+.25*np.ones((m,m)));Cinv=np.eye(m)/.75-(.25/(.75*(.75+.25*m)))*np.ones((m,m));J=Cinv/(sigma[:,None]*sigma[None,:]*ratio*mult)
   assert np.allclose(R@J,np.eye(m),atol=1e-7);req={'contract':'anibench.finite-task-request.v1','task':t,'task_sha256':finite_task_sha256(t),'evidence':{'identifiability':True,'collection_verified':None,'support':[dict(x,supported=support) for x in t['required_support']]},'geometry':{'model_sha256':t['model_sha256'],'information_matrix':J.tolist()}}
   out.append({**binding,'canonical_id':ident,'known_absent':False,'request':req})
  scenarios.append({**binding,'scenario_id':scenario,'targets':out})
 return {'contract':'anibench.benchmark-request.v1','score_profile_sha256':suite_sha256(sp),'suite_request':{**binding,'contract':'anibench.finite-suite-request.v1','profile_sha256':suite_sha256(p),'scenarios':scenarios}}

def main(out):
 out.mkdir(exist_ok=False);rows=[];artifacts={};profiles,meta=make_profiles();matrix=[]
 for d in DOMAINS:
  for q in QUESTIONS:matrix.append({'domain':d,'question':q,'AB1':'required' if q in REQUIRED[d] else 'out_of_scope','AB2':'required' if q in AB2[d] else 'out_of_scope','synthetic_support':'executable_declared_model' if q in AB2[d] else 'not_defined','real_support':'unqualified_exactoperator_or_summary_needed' if q in AB2[d] else 'out_of_scope'})
 artifacts['COVERAGE_MATRIX.json']=matrix;artifacts['TASK_METADATA.json']=meta;artifacts['trusted-profiles.json']=profiles;artifacts['designs.json']=DESIGNS
 for tol in [.5,1.,2.]:
  ps,md=make_profiles(tol)
  for key,p in ps.items():
   level='AB2' if p['parent_sha256'] else 'AB1'
   for policy in ['domain_budget','question_budget','equal_bundle']:
    sp=score_profile(p,policy,md)
    if tol==1:artifacts[level+'-'+policy+'-score-profile.json']=sp
    for design in DESIGNS:
     req=request(p,sp,md,design);result=evaluate_benchmark(req,trusted_profiles=ps,trusted_score_profiles={suite_sha256(sp):sp});overall=result['envelope'][0]['categories'][0]
     rows.append({'level':level,'policy':policy,'tolerance_factor':tol,'design':design['id'],'lower_percent':overall['lower_percent'],'upper_percent':overall['upper_percent'],'precision_progress':overall['precision_toward_targets'],'level_attainment':result['level_attainment'],'result_sha256':result['receipt_sha256']})
     if tol==1 and policy=='domain_budget' and design['id'] in ['two-person-extreme-depth','person-floor-AB1-witness','person-floor-AB2-witness']:artifacts[level+'-'+design['id']+'-request.json']=req;artifacts[level+'-'+design['id']+'-receipt.json']=result
 artifacts['RESULTS.json']={'actual_benchmark_runs':len(rows),'rows':rows,'scope':'Synthetic reference sensitivity; no realstudy score or biologicalcalibration'}
 for name,obj in artifacts.items():
  with (out/name).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps({'runs':len(rows),'base_tasks_AB1':18,'base_tasks_AB2':24,'outputs':len(artifacts)}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=pathlib.Path,required=True);main(parser.parse_args().out)
