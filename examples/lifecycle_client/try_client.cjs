'use strict';
// Standalone installed consumer. Command JSON explicitly selects trusted software.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const {LifecycleClient,ProcessTransport} = require('@opensmell/lifecycle-client');
(async () => {
  const [commandJson, deviceId, planPath] = process.argv.slice(2);
  const plan = JSON.parse(fs.readFileSync(planPath,'utf8'));
  // Accept the explicit plan object, not source data or implicit mapping.
  const client = await LifecycleClient.connect(new ProcessTransport(JSON.parse(commandJson)), {expectedDeviceId:deviceId});
  try {
    const short = {...plan,duration:0.1};
    let run = await client.render(short,{requestId:'completion'});
    assert.equal(run.state,'accepted');
    const deadline = Date.now()+3000;
    while (['accepted','running'].includes(run.state) && Date.now()<deadline) {
      await new Promise(r=>setTimeout(r,20)); run = await client.status(run.execution_id);
    }
    assert.equal(run.state,'completed');
    const completed = run;
    assert.deepEqual(await client.stop(run.execution_id),completed);
    await assert.rejects(client.render(short,{requestId:'completion'}));
    await assert.rejects(client.render({...plan,duration:31},{requestId:'invalid'}));
    run = await client.render(plan,{requestId:'stop'});
    await assert.rejects(client.stop(completed.execution_id));
    const stopped = await client.stop(run.execution_id); assert.equal(stopped.state,'stopped');
    run = await client.render(plan,{requestId:'disconnect'});
    assert.equal(run.state,'accepted'); client.close();
    const unknown = client.execution; assert.equal(unknown.state,'unknown');
    console.log(JSON.stringify({experimental:true,physical_validation:false,device_id:deviceId,plan,completed,stopped,unknown}));
  } finally {client.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
