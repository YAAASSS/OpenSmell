# Experimental JavaScript software lifecycle client

Private local package, Node.js 22+, no dependencies, no npm publication.
Uses the existing Draft RFC-0014 `local-simulator-lifecycle-v1` software contract.
Physical Device Protocol 0.1/ESP32 does not implement these observations.

From the checkout: `npm pack ./packages/lifecycle-client --ignore-scripts`.
Install the resulting tarball in your own project with
`npm install --offline --ignore-scripts --no-audit --no-fund /absolute/path/to/package.tgz`.

```js
// ESM: import {LifecycleClient, ProcessTransport} from '@opensmell/lifecycle-client';
const {LifecycleClient, ProcessTransport} = require('@opensmell/lifecycle-client');
const client = await LifecycleClient.connect(
  new ProcessTransport(['node', '/absolute/path/to/trusted-device.cjs']),
  {expectedDeviceId:'opensmell-node-simulator-001'});
try {
  const run = await client.render({duration:5,commands:[{channel:0,intensity:0.25}]},
                                  {requestId:'caller-unique-1'});
  if (run.state === 'accepted') console.log(await client.stop(run.execution_id));
} finally { client.close(); }
```

Use the example inside an async function in CommonJS. The caller supplies an
explicit plan (for a Python CLI planning artifact use its `plan` property).
No graph mapping, preview freshness or provenance is inferred by this client.
Capabilities and duration are checked before sending. Session-local request IDs
are consumed before exchange, including refusal or unknown results; they cannot
be reused. Concurrent operations serialize and input plans are snapshotted.
`capabilities` and passive `execution` return independent copies.

`render` returns accepted/rejected/unknown. Acceptance is not completion.
`status(id)`/`stop(id)` require the current execution ID, validate correlation and
return running/completed/stopped or unknown on a broken exchange. Terminal states
remain stable. Close/lost replies leave active execution unknown, with no retry,
reconnection, scheduling or persistent exactly-once guarantee. Local validation
and connection negotiation failures reject the Promise. A refused render leaves
the connection usable; a malformed reply closes it.

`ProcessTransport(commandArray, {timeout:2000,startupTimeout:5000})` executes an
explicit trusted command without a shell; it is not a sandbox. Deadlines are in
milliseconds; the startup bound applies to the first response, subsequent bounds
to each exchange. Frames are limited to 65,536 UTF-8 bytes excluding newline;
malformed/unsolicited/multiple replies, EOF and timeout close the process.
Stderr is discarded. A custom transport implements async `exchange(object)` and
`close()`; it must enforce its own framing/deadlines. This is a Node subprocess
client, not a browser, serial or physical-device compatibility claim.

See `docs/javascript-lifecycle.md` in the repository for installed cross-language
proof. Source/plan, acceptance, software observation and measured odor output
remain separate evidence. No third-party adoption or physical result is implied.
