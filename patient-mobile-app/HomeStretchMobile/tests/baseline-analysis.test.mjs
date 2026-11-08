import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const require=createRequire(import.meta.url),ts=require('typescript'),dir=mkdtempSync(join(tmpdir(),'baseline-test-'));
writeFileSync(join(dir,'package.json'),'{"type":"commonjs"}');
writeFileSync(join(dir,'analysis.cjs'),ts.transpileModule(readFileSync(new URL('../src/baseline/analysis.ts',import.meta.url),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText);
const {analyze,buildReference,compare,FEATURES}=require(join(dir,'analysis.cjs'));
const fixture=JSON.parse(readFileSync(new URL('./fixtures/baseline-synthetic.json',import.meta.url),'utf8'));
after(()=>rmSync(dir,{recursive:true,force:true}));
test('five synthetic curls reproduce notebook boundaries and nine baseline features',()=>{
 const a=analyze(fixture.frames),r=buildReference(a,a.reps.map(r=>r.id));
 assert.equal(a.reps.length,5);assert.equal(a.stillness,true);assert.equal(a.unconfirmedFinal,false);
 a.reps.forEach((rep,i)=>{assert.ok(Math.abs(rep.start-fixture.reps[i].start_s)<1e-8);assert.ok(Math.abs(rep.end-fixture.reps[i].end_s)<1e-8);});
 for(const key of FEATURES){assert.ok(Math.abs(r.stats[key].mean-fixture.stats.mean[key])<1e-6,`${key} mean: ${r.stats[key].mean} != ${fixture.stats.mean[key]}`);assert.ok(Math.abs(r.stats[key].sd-fixture.stats.sd[key])<1e-6,`${key} sd`);}
});
test('baseline selection requires at least three unique usable reps',()=>{
 const a=analyze(fixture.frames);for(const ids of [[1,2],[1,1,2],[1,2,99]])assert.throws(()=>buildReference(a,ids));
 const r=buildReference(a,[1,3,5]);assert.deepEqual(r.acceptedIds,[1,3,5]);
});
test('invalid data, absent sensor, long gaps, and mixed sessions cannot become baselines',()=>{
 assert.throws(()=>analyze(fixture.frames.filter(f=>f.type===1)));
 assert.throws(()=>analyze(fixture.frames.filter(f=>f.ms<3000||f.ms>3200)));
 assert.throws(()=>analyze(fixture.frames.map((f,i)=>i===5?{...f,valid:false}:f)));
 assert.throws(()=>analyze(fixture.frames.map((f,i)=>i===5?{...f,session:999}:f)));
});
test('truncated final repetition is not silently counted',()=>{
 const a=analyze(fixture.frames.filter(f=>f.ms<=16000));assert.equal(a.reps.length,4);assert.equal(a.unconfirmedFinal,true);
});
test('comparisons preserve frozen reference and distinguish unassessable reps',()=>{
 const a=analyze(fixture.frames),r=buildReference(a,[1,2,3,4,5]),before=JSON.stringify(r);
 const changed=structuredClone(a);changed.reps[0].features.gyro_peak_deg_s*=5;changed.reps[1].eligible=false;
 const results=compare(changed,r);assert.ok(results[0].flags.includes('gyro_peak_deg_s'));assert.equal(results[1].assessable,false);assert.equal(JSON.stringify(r),before);
 assert.throws(()=>compare({...a,version:'other'},r));
});

test('nonzero directional features and changing movement axes match the notebook',()=>{
 const f=JSON.parse(readFileSync(new URL('./fixtures/baseline-multiaxis.json',import.meta.url),'utf8'));
 const a=analyze(f.frames),r=buildReference(a,a.reps.map(r=>r.id));assert.equal(a.reps.length,f.reps.length);
 for(const key of FEATURES){assert.ok(Math.abs(r.stats[key].mean-f.stats.mean[key])<1e-6,`${key} mean ${r.stats[key].mean} vs ${f.stats.mean[key]}`);assert.ok(Math.abs(r.stats[key].sd-f.stats.sd[key])<1e-6,`${key} sd`);}
});
