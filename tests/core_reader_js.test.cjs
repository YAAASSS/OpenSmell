"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const reader = require("../packages/javascript");
const document = () => ({opensmell:"0.1",odor:{id:"caller:odor",representations:[{type:"perceptual",scheme:{id:"org.opensmell.perceptual.measurements",version:"0.1"},data:{measurements:[{property:"flower",value:0,scale:{min:0,max:10}}]}}]}});
const bytes = value => Buffer.from(typeof value === "string" ? value : JSON.stringify(value));
const inspect = value => reader.inspectCoreBytes(bytes(value));

test("explicit Core ESM/CJS and browser API; legacy graph dispatch unchanged", async () => {
  const esm = await import("../packages/javascript/index.mjs");
  assert.equal(esm.inspectCoreBytes,reader.inspectCoreBytes);assert.equal(esm.CORE_LIMIT,4194304);
  assert.equal((await reader.inspectBytes(bytes(document()))).report.status,"rejected");
  const ctx=vm.createContext({Uint8Array,TextDecoder,crypto:require("node:crypto").webcrypto});
  vm.runInContext(fs.readFileSync(require.resolve("../packages/javascript/reader.cjs"),"utf8"),ctx);
  assert.equal((await ctx.OpenSmellReader.inspectCoreBytes(new Uint8Array(bytes(document())))).report.status,"inspected");
});

test("quantitative fields distinguish zero, null, missing, scales, units and provenance",async()=>{
  const d=document();d.provenance={source:"declaration"};d.odor.metadata={labels:{en:"Caller"},extra:9007199254740991};
  const r=d.odor.representations[0];r.provenance={scope:"synthetic"};r.data.measurements.push({property:"null",value:null,scale:null,unit:null},{property:"absent"},{property:"rated",value:2,scale:{min:0,max:5},unit:"rating"});
  const result=await inspect(d);assert.equal(result.report.status,"partial");
  const c=result.report.core,entries=c.representations[0].entries;
  assert.equal(c.odor_id,"caller:odor");assert.equal(c.provenance.json,JSON.stringify(d.provenance));
  assert.equal(entries[0].value.text,"0");assert.equal(entries[0].unit.presence,"missing");
  assert.equal(entries[1].value.presence,"null");assert.equal(entries[1].scale.presence,"null");assert.equal(entries[1].unit.presence,"null");
  assert.equal(entries[2].value.presence,"missing");assert.equal(entries[2].scale.presence,"missing");
  assert.equal(entries[3].unit.text,"rating");assert.equal(c.representations[0].provenance.json,JSON.stringify(r.provenance));
});

test("unsafe, fractional, exponent, negative zero and opaque tokens remain exact; snapshots isolated",async()=>{
  const d=document();d.odor.representations[0].data.measurements=[{property:"token",value:0,scale:{min:0,max:10}}];
  const tokenValues=["9007199254740993","1e400","1e-400","-0","0.10000000000000000001","1.0e2"];
  for(const token of tokenValues){
    const raw=bytes(JSON.stringify(d).replace('"value":0','"value":'+token));
    const result=await reader.inspectCoreBytes(raw);raw[0]=0;
    assert.equal(result.report.status,"partial");assert.equal(result.report.core.representations[0].entries[0].value.json,token);
    const first=result.copyBytes();first[0]=0;assert.equal(result.copyBytes()[0],123);
    assert.ok(result.report.diagnostics.some(x=>x.code==="numeric_limit"));
  }
  const raw=bytes('{"opensmell":"0.1","odor":{"id":"x","representations":[{"type":"future","scheme":{"id":"unknown","version":"9"},"data":{"huge":9007199254740993,"tiny":1e-400},"context":{"x":null}}]},"extension":-0}');
  const result=await reader.inspectCoreBytes(raw);assert.equal(result.report.core.representations[0].status,"opaque");
  assert.match(result.report.core.representations[0].data.json,/9007199254740993/);
  assert.deepEqual(Buffer.from(result.copyBytes()),raw);
});

for(const [name,change] of [
  ["graph discriminator",d=>d.format="org.opensmell.experimental.generic-resource-graph"],
  ["future version",d=>d.opensmell="0.2"], ["null odor",d=>d.odor=null],
  ["empty odor id",d=>d.odor.id=""], ["empty representations",d=>d.odor.representations=[]],
  ["bad representation",d=>d.odor.representations[0]=null],
  ["empty type",d=>d.odor.representations[0].type=""],
  ["null scheme",d=>d.odor.representations[0].scheme=null],
  ["empty scheme version",d=>d.odor.representations[0].scheme.version=""],
  ["non-object data",d=>d.odor.representations[0].data=[]],
  ["null metadata",d=>d.odor.metadata=null], ["empty labels",d=>d.odor.metadata={labels:{}}],
  ["null label",d=>d.odor.metadata={labels:{en:null}}], ["empty description",d=>d.odor.metadata={description:""}],
  ["absent measurements",d=>delete d.odor.representations[0].data.measurements],
  ["string value",d=>d.odor.representations[0].data.measurements[0].value="0"],
  ["boolean value",d=>d.odor.representations[0].data.measurements[0].value=false],
  ["empty unit",d=>d.odor.representations[0].data.measurements[0].unit=""],
  ["invalid scale",d=>d.odor.representations[0].data.measurements[0].scale=[]],
  ["out of range",d=>d.odor.representations[0].data.measurements[0].value=11],
  ["inverted scale",d=>d.odor.representations[0].data.measurements[0].scale={min:10,max:0}],
]) test("Core refuses "+name+" without copy",async()=>{
  const d=document();change(d);const result=await inspect(d);assert.equal(result.report.status,"rejected");
  result.report.status="inspected";assert.throws(()=>result.copyBytes());
});
for(const [name,input,code] of [
  ["duplicate escaped key",bytes('{"opensmell":"0.1","open\\u0073mell":"0.1"}'),"duplicate_json_key"],
  ["invalid UTF8",Buffer.from([0xff]),"invalid_utf8"],
  ["malformed JSON",bytes('{'),"invalid_json"],
  ["too deep",bytes('{"x":'+"[".repeat(65)+"0"+"]".repeat(65)+'}'),"reading_limit"],
])test("Core refuses "+name,async()=>{const result=await reader.inspectCoreBytes(input);assert.equal(result.report.status,"rejected");assert.ok(result.report.diagnostics.some(x=>x.code===code));assert.throws(()=>result.copyBytes());});

test("unknown scheme version and mismatched type stay opaque, no accidental known dispatch",async()=>{
  for(const key of ["type","version"]){const d=document();const r=d.odor.representations[0];if(key==="type")r.type="chemical";else r.scheme.version="9";r.data={anything:true};
    const result=await inspect(d);assert.equal(result.report.status,"partial");assert.equal(result.report.core.representations[0].entries,undefined);assert.deepEqual(Buffer.from(result.copyBytes()),bytes(d));}
});
for(const bom of [false,true])test("Core inclusive 4MiB bound and BOM="+bom,async()=>{
  const raw=Buffer.concat([bom?Buffer.from([0xef,0xbb,0xbf]):Buffer.alloc(0),bytes(document())]);
  const padded=Buffer.concat([raw,Buffer.alloc(reader.CORE_LIMIT-raw.length,32)]);
  const result=await reader.inspectCoreBytes(padded);assert.equal(result.report.status,"inspected");assert.equal(result.report.file.utf8_bom,bom);assert.deepEqual(Buffer.from(result.copyBytes()),padded);
  await assert.rejects(reader.inspectCoreBytes(Buffer.concat([padded,Buffer.from(" ")])),e=>e.code==="file_too_large");
});

test("legacy graph entry also refuses a competing Core discriminator",async()=>{
  const result=await reader.inspectBytes(bytes({format:reader.FORMAT,version:"0.1",resources:[],opensmell:"0.1"}));
  assert.equal(result.report.status,"rejected");assert.throws(()=>result.copyBytes());
});
