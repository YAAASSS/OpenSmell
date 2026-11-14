'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {LifecycleClient,ProcessTransport,PROFILE} = require('../packages/lifecycle-client');
const plan = {commands:[{channel:0,intensity:0.25}],duration:5};
function endpoint(change = x=>x) {
  const t={closed:false,calls:[],close(){this.closed=true;},async exchange(m){
    this.calls.push(m);
    let r = m.type==='hello' ? {protocol_version:'0.1',type:'hello_response',device_id:'test'} :
      m.type==='get_capabilities' ? {protocol_version:'0.1',type:'capabilities',device_id:'test',channels:[{channel:0,min_intensity:0,max_intensity:1}],min_duration:0.1,max_duration:30} :
      m.type==='lifecycle_capabilities' ? {profile:PROFILE,status:true,stop:true} :
      m.type==='render' ? {protocol_version:'0.1',type:'ok',execution_id:String(this.calls.length)} :
      {profile:PROFILE,execution_id:m.execution_id,state:m.type==='stop'?'stopped':'completed'};
    return change(r,m);
  }};return t;
}
const connect=t=>LifecycleClient.connect(t,{expectedDeviceId:'test'});
test('CJS and ESM share a client',async()=>assert.equal((await import('../packages/lifecycle-client/index.mjs')).LifecycleClient,LifecycleClient));
test('identity/profile mismatch closes before render',async()=>{
 for(const type of ['hello','get_capabilities','lifecycle_capabilities']){
  const t=endpoint((r,m)=>m.type===type?{}:r);await assert.rejects(connect(t));assert.ok(t.closed);assert.equal(t.calls.length, ['hello','get_capabilities','lifecycle_capabilities'].indexOf(type)+1);
 }
});
test('capability guards make no render I/O',async()=>{
 const t=endpoint(),c=await connect(t);
 for(const p of [{...plan,duration:NaN},{...plan,duration:31},{...plan,commands:[]},{...plan,commands:[{channel:1,intensity:0.2}]},{...plan,commands:[...plan.commands,...plan.commands]},{...plan,commands:[{channel:0,intensity:Infinity}]}])await assert.rejects(c.render(p,{requestId:'guard'}));
 assert.equal(t.calls.length,3);c.close();
});
test('serialized concurrent renders consume ID only once and freeze plan input',async()=>{
 const t=endpoint(),c=await connect(t),p=structuredClone(plan);
 const first=c.render(p,{requestId:'one'});p.commands[0].intensity=99;
 const second=c.render(plan,{requestId:'one'});assert.equal((await first).state,'accepted');await assert.rejects(second);
 assert.equal(t.calls[3].commands[0].intensity,0.25);assert.equal(t.calls.length,4);c.close();assert.equal(c.execution.state,'unknown');
});
test('snapshots, stale stop and terminal stability',async()=>{
 const t=endpoint(),c=await connect(t);c.capabilities.channels[0].max_intensity=99;
 const r=await c.render(plan,{requestId:'x'});await assert.rejects(c.stop('old'));const done=await c.status(r.execution_id);
 done.state='running';assert.equal(c.execution.state,'completed');const n=t.calls.length;assert.equal((await c.stop(r.execution_id)).state,'completed');c.close();assert.equal(t.calls.length,n);assert.equal(c.execution.state,'completed');
});
test('refusal consumes ID, leaves connection usable',async()=>{
 let refused=false;const t=endpoint((r,m)=>{if(m.type==='render'&&!refused){refused=true;return {protocol_version:'0.1',type:'error',code:'busy',message:'busy'};}return r;});
 const c=await connect(t);assert.equal((await c.render(plan,{requestId:'x'})).state,'rejected');await assert.rejects(c.render(plan,{requestId:'x'}));assert.equal((await c.render(plan,{requestId:'y'})).state,'accepted');c.close();
});
test('mismatched or lost observation stays unknown, never retries',async()=>{
 for(const mode of ['mismatch','throw']){
  const t=endpoint((r,m)=>{if(m.type==='stop'){if(mode==='throw')throw Error('lost');r.execution_id='wrong';}return r;});const c=await connect(t);
  const r=await c.render(plan,{requestId:'x'});assert.equal((await c.stop(r.execution_id)).state,'unknown');assert.ok(t.closed);const n=t.calls.length;await c.status(r.execution_id);assert.equal(t.calls.length,n);
 }
});
test('close during an outstanding send cannot resurrect acceptance',async()=>{
 const t=endpoint(),base=t.exchange.bind(t);let release;
 t.exchange=m=>m.type==='render'?new Promise(r=>{release=()=>r({protocol_version:'0.1',type:'ok',execution_id:'x'});}):base(m);
 const c=await connect(t),pending=c.render(plan,{requestId:'x'});await new Promise(r=>setImmediate(r));c.close();release();assert.equal((await pending).state,'unknown');
});
for(const [name,source] of [['EOF','process.exit(0)'],['malformed',"process.stdin.once('data',()=>console.log('no json'))"],['oversized',"process.stdin.once('data',()=>console.log(' '.repeat(65537)))"],['unsolicited',"console.log('{}\\n{}')"],['timeout','setInterval(()=>{},1000)']])test('process fail-closed: '+name,async()=>{
 const t=new ProcessTransport([process.execPath,'-e',source],{startupTimeout:name==='timeout'?100:5000,timeout:100});await assert.rejects(t.exchange({type:'hello'}));assert.ok(t.closed);
});

test('lost render and reused execution identifiers fail closed',async()=>{
 for(const mode of ['lost','reused']) {
  const t=endpoint((r,m)=>{if(m.type==='render'){if(mode==='lost')throw Error('reply lost');r.execution_id='same';}return r;});
  const c=await connect(t);let r=await c.render(plan,{requestId:'first'});
  if(mode==='reused'){await c.stop(r.execution_id);r=await c.render(plan,{requestId:'second'});}
  assert.equal(r.state,'unknown');assert.ok(t.closed);await assert.rejects(c.render(plan,{requestId:'third'}));
 }
});
