# OpenSmell software starter (experimental)

Created passively by the installed `opensmell init-workspace` command. No process
or device has been launched. Data are explicitly synthetic, not observations.
`sample.osmell` retains an opaque representation; only index0 is mapped by the
application-owned `profile.json`. CH0=.25 is a software demonstration, not an odor.

From this directory, with the SDK's Python environment active:

```sh
opensmell validate sample.osmell
opensmell inspect sample.osmell --json
opensmell plan-core sample.osmell --representation-index 0 --profile profile.json --duration 0.1 --output plan.json
opensmell run-sequence plan.json --software-command-json '["python","-I","-m","opensmell","simulate-device"]' --expected-device-id opensmell-local-simulator-001 --output receipt.json
```

The last command is a separate explicit software-execution choice. `python` must
resolve to the environment where you installed OpenSmell; use its absolute path
in the command JSON when necessary. No shell is used for the child command. The
installed simulator opens no serial port/GPIO/network or physical device.
Its stdin/stdout are a bounded JSON-lines protocol, not an interactive prompt.

Expected: passive plan `execution:not_attempted`, then receipt `status:completed`
with a correlated software completion. `unknown` annotations do not become
positive bindings. Supplied capabilities are not a live/hardware observation;
execution checks the explicitly pinned software identity and live capabilities.

Try the existing completion/Stop/link-loss trial with a separately explicit plan:

```sh
opensmell plan-core sample.osmell --representation-index 0 --profile profile.json --duration 5 --output trial-plan.json
opensmell lifecycle-trial trial-plan.json --software-command-json '["python","-I","-m","opensmell","simulate-device"]' --expected-device-id opensmell-local-simulator-001 --output trial-receipts.json
```

Expected `status:passed`: completion, observed Stop, and unknown after deliberately
closing a link. The trial declares a short completion derivative; Stop/link-closure
use the explicit 5-second plan. It does not establish emergency Stop or physical output.
An explicit duration31 plan is refused under this profile; selecting opaque index1
also refuses, without silently falling back to index0.

Choose new output filenames; existing workspace/output files are never overwritten.
`workspace.json` records original template byte hashes, not signatures or ongoing
approval of edits. Edit your own input/profile deliberately, then reprepare into a
new plan file. The normal downstream boundary checks the retained Core projection;
unknown source fields are preserved and no original input file needs to remain.

This starter requires only the installed SDK and its normal dependencies; no
checkout, Node, optional scientific library or browser application is needed.
Core0.1/wire contracts are unchanged. The SDK/examples remain experimental;
no physical reproduction, third-party adoption, tag or registry release is claimed.
