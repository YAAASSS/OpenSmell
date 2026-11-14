# Installed JavaScript lifecycle client (experimental)

The private `@opensmell/lifecycle-client` Node 22+ package consumes explicit
plans and negotiates the existing Draft RFC-0014 software lifecycle profile.
It is independent of Local Explorer and the Python client implementation.
No npm publication, stable API, physical-device compatibility or measured odor
result is claimed. See [the API and limits](../packages/lifecycle-client/README.md).

## Try a complete installed path

From a development checkout:

```sh
npm pack ./packages/lifecycle-client --ignore-scripts
python -m build --wheel
node tools/verify_js_lifecycle.cjs dist/opensmell-0.1.0-py3-none-any.whl
```

The verifier creates a fresh environment outside the repository, installs the
local wheel and npm tarball, and imports the CJS and ESM entries. Python test
dependencies are inherited from the development environment; this is not a full
offline dependency distribution. It copies the diphenyl ether graph and semantic
profile, calls the installed Python planner, and passes its explicit `plan` to
the installed JavaScript client. The standalone consumer runs against both the
independent Node endpoint and an installed-Python SDK simulator process.
Completion/Stop/lost-link uncertainty, stale Stop, duplicate request ID and
unsupported duration are checked without application imports or hardware access.
`OPENSMELL_PYTHON` may select the Python executable used to create the environment.

## Use your own consumer

Install the local tarball into a separate Node project. Copy
`examples/lifecycle_client/try_client.cjs`, the trusted
`examples/lifecycle_adapter/device.cjs`, the graph and mapping profile there.
Install the Python wheel into your virtual environment, then:

```sh
python -m opensmell plan multisource_diphenyl_ether.osmell --profile offline_semantic_profile.json --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 5 > artifact.json
node -e "const fs=require('node:fs');fs.writeFileSync('plan.json',JSON.stringify(JSON.parse(fs.readFileSync('artifact.json')).plan),{flag:'wx'})"
node try_client.cjs '["node","/absolute/path/to/device.cjs"]' opensmell-node-simulator-001 plan.json
```

The example uses short 0.1-second completion/disconnect plans and the supplied
five-second Stop plan. Expected terminal observations are completed, stopped and
unknown respectively. Closing is not a Stop; elapsed time alone is not completion.
The full planning artifact retains source/profile provenance separately from the
plan accepted by the client. The caller remains responsible for freshness,
source meaning and durable request bookkeeping.

The optional `examples/lifecycle_adapter/python_device.py` is a trusted software
JSON-lines wrapper around the installed SDK simulator. Invoke with the activated
Python environment and expected ID `opensmell-local-simulator-001` to exercise
the same consumer against Python. It is an example endpoint, not a general server.

The client checks capabilities before sending, snapshots caller inputs, serializes
concurrent operations and consumes unique request IDs before I/O. Connection
negotiation errors close the transport. Render refusals are retained as rejected;
missing replies, reused execution IDs and mismatched observations close the link
and preserve unknown without retry. Terminal observations remain stable and stale
IDs fail locally. Identity strings and observations are not authenticated.

## Verification and exit criterion

`node --test tests/lifecycle_client.test.cjs` covers negotiation, pre-send guards,
input/snapshot isolation, concurrent duplicate suppression, refusal/recovery,
terminal stability, lost/mismatched replies, close during send and bounded process
failures. CI also runs the installed cross-language verifier above on Node 22.
This completes the first explicit-plan JavaScript client boundary; reconnect,
persistent recovery, browser transports, richer mapping and physical output stay
outside this slice. Integrate the client into the portable kit next, using the
same declared data and explicit plans rather than a new wire protocol.
