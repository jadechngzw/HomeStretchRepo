import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
const require=createRequire(import.meta.url),ts=require('typescript'),modules=new Map();
function load(name){if(modules.has(name))return modules.get(name);const exports={},source=readFileSync(new URL(`../src/baseline/${name}.ts`,import.meta.url),'utf8');const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;new Function('require','exports',code)(id=>load(id.replace('./','')),exports);modules.set(name,exports);return exports;}
const {analyze,buildReference}=load('analysis'),{assessFrames,assessAnalysis,paceCue}=load('liveGuidance'),{activeBaselines,autoApprove}=load('activation');
const fixture=JSON.parse(readFileSync(new URL('./fixtures/baseline-synthetic.json',import.meta.url),'utf8'));
const analysis=analyze(fixture.frames),reference=buildReference(analysis,[1,2,3,4,5]);
test('live prefixes assess complete reps with a trailing buffer and final analysis includes last rep',()=>{
 const first=assessFrames(fixture.frames.filter(f=>f.ms<=6000),reference);assert.equal(first.reps.length,0);
 const later=assessFrames(fixture.frames.filter(f=>f.ms<=8000),reference);assert.equal(later.reps.length,1);
 const final=assessFrames(fixture.frames,reference,true);assert.equal(final.reps.length,5);
 assert.deepEqual(final.reps.map(r=>r.id),[1,2,3,4,5]);
});
test('feature departure appears as atypical and unassessable does not appear typical',()=>{
 const changed=structuredClone(analysis);changed.reps[0].features.gyro_peak_deg_s=999;changed.reps[1].eligible=false;
 const r=assessAnalysis(changed,reference);assert.ok(r.reps[0].flags.includes('gyro_peak_deg_s'));assert.equal(r.reps[1].assessable,false);
});
test('pace prompts recover over a recent window and reset with an empty set',()=>{
 assert.equal(paceCue([4,4,4]),'slow');assert.equal(paceCue([4,4,4,2,2]),'steady');
 assert.equal(paceCue([.7,.7,.7]),'fast');assert.equal(paceCue([.7,.7,.7,2,2]),'steady');assert.equal(paceCue([]),'waiting');
});
test('baseline matching isolates exercise, side, wrist, and watch-face placement',()=>{
 const make=(id,patch={})=>({id,exerciseId:'bicep-curls',status:'approved',reference,placement:{side:'right',wrist:'right',face:'top'},...patch});
 const a=make('old'),b=make('latest'),left=make('left',{placement:{side:'left',wrist:'left',face:'top'}}),other=make('other',{exerciseId:'other'});
 const data={version:1,baselines:[a,left,b,other],customExercises:[],surveys:[]};
 assert.deepEqual(activeBaselines(data,'bicep-curls').map(b=>b.id),['latest','left']);
 const broken=make('broken',{reference:{}});assert.equal(activeBaselines({...data,baselines:[broken]},'bicep-curls').length,0);
 const pending=make('pending',{status:'awaiting-review'});assert.equal(autoApprove({...data,baselines:[pending]}).baselines[0].approvalMode,'automatic-prototype');
});
test('new set is assessed independently with no flags or reps carried over',()=>{
 const a=assessFrames(fixture.frames,reference,true);
 const fresh=assessFrames(fixture.frames.filter(f=>f.ms<=6000),reference);
 assert.equal(a.reps.length,5);assert.equal(fresh.reps.length,0);assert.equal(fresh.placementWarning,false);
});
test('legacy live-guidance hook recovers pace and resets on session ID changes',()=>{
 let state,cleanup,snapshot={sessionId:1,phase:'active'},onRep,onState;
 const react={useState:initial=>{state=typeof initial==='function'?initial():initial;return[state,value=>{state=typeof value==='function'?value(state):value;}];},useEffect:fn=>{cleanup=fn();}};
 const session={getSnapshot:()=>snapshot,subscribe:fn=>{onState=fn;return()=>{};},onRep:fn=>{onRep=fn;return()=>{};}};
 const source=readFileSync(new URL('../src/wearable/useLiveGuidance.ts',import.meta.url),'utf8');
 const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText,exports={};
 new Function('require','exports',code)(id=>id==='react'?react:id==='./useCurlSession'?{session}:load('liveGuidance'),exports);
 exports.useLiveGuidance();
 for(let count=1;count<=3;count++)onRep({count,durationSec:4});assert.match(state.message,/quicker/);
 onRep({count:4,durationSec:2});onRep({count:5,durationSec:2});assert.match(state.message,/steady/);
 snapshot={sessionId:2,phase:'starting'};onState();assert.equal(state.repCount,0);assert.equal(state.state,'IDLE_PRE');
 onRep({count:1,durationSec:2});assert.equal(state.repCount,1);assert.match(state.message,/steady/);
 onRep({count:10,durationSec:2});assert.equal(state.state,'EXERCISING');assert.match(state.message,/Target reached/);
 snapshot={sessionId:2,phase:'ended'};onState();assert.equal(state.state,'IDLE_POST');cleanup();
});
