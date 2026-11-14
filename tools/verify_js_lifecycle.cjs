'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),work=fs.mkdtempSync(path.join(os.tmpdir(),'opensmell-node-client-'));
const python=process.env.OPENSMELL_PYTHON||'python';
function run(cmd,args,cwd=work){const r=cp.spawnSync(cmd,args,{cwd,encoding:'utf8',timeout:120000});if(r.error||r.status!==0)throw Error(JSON.stringify({cmd,args,status:r.status,error:r.error?.message,stdout:r.stdout,stderr:r.stderr}));return r.stdout;}
try {
 const wheel=path.resolve(process.argv[2]);
 run(python,['-m','venv','--system-site-packages',path.join(work,'venv')]);
 const installed=path.join(work,'venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 run(installed,['-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel]);
 const location=run(installed,['-I','-c','import opensmell; print(opensmell.__file__)']).trim();
 assert.ok(location.startsWith(path.join(work,'venv')));
 const npm=process.platform==='win32'?'npm.cmd':'npm';
 const pack=JSON.parse(run(npm,['pack','--ignore-scripts','--json','--pack-destination',work],path.join(root,'packages/lifecycle-client')))[0];
 assert.deepEqual(pack.files.map(x=>x.path).sort(),['LICENSE','README.md','index.cjs','index.mjs','package.json']);
 fs.writeFileSync(path.join(work,'package.json'),'{"private":true}');
 run(npm,['install','--offline','--ignore-scripts','--no-save','--no-audit','--no-fund','--package-lock=false',path.join(work,pack.filename)]);
 for(const [from,to] of [['examples/lifecycle_client/try_client.cjs','try_client.cjs'],['examples/lifecycle_adapter/device.cjs','device.cjs'],['examples/lifecycle_adapter/python_device.py','python_device.py'],['examples/multisource_diphenyl_ether.osmell','source.osmell'],['examples/offline_semantic_profile.json','profile.json']])fs.copyFileSync(path.join(root,from),path.join(work,to));
 const artifact=JSON.parse(run(installed,['-I','-m','opensmell','plan','source.osmell','--profile','profile.json','--resource-id','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','--duration','5']));
 assert.equal(artifact.execution,'not_attempted');fs.writeFileSync(path.join(work,'plan.json'),JSON.stringify(artifact.plan));
 const reports=[];
 for(const [command,id] of [[[process.execPath,path.join(work,'device.cjs')],'opensmell-node-simulator-001'],[[installed,'-I','-u',path.join(work,'python_device.py')],'opensmell-local-simulator-001']]){
  const report=JSON.parse(run(process.execPath,['try_client.cjs',JSON.stringify(command),id,'plan.json']));
  assert.equal(report.completed.state,'completed');assert.equal(report.stopped.state,'stopped');assert.equal(report.unknown.state,'unknown');reports.push(report);
 }
 run(process.execPath,['--input-type=module','-e',"import {LifecycleClient} from '@opensmell/lifecycle-client'; if(typeof LifecycleClient.connect!=='function')throw Error('ESM');"]);
 console.log(JSON.stringify({result:'passed',consumer:'fresh installed CJS/ESM package outside checkout',plan:artifact.plan,endpoints:reports.map(r=>r.device_id),outcomes:['completed','stopped','unknown'],physical_validation:false}));
}finally{fs.rmSync(work,{recursive:true,force:true});}
