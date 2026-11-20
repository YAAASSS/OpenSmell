# Bounded software sequences (experimental)

The installed `opensmell run-sequence` runs **explicit offline plans in argument
order**, advancing only after a correlated `completed` observation. It uses the
existing experimental lifecycle contract; Device Protocol 0.1 is unchanged.
Python, independent Node and the actual native LED sketch are software targets.
No physical board, diffusion or olfactory result is established.

## Try two distinct plans

Install the SDK from this source revision with `python -m pip install .` (or
install the locally built wheel). From the checkout, use the documented fixture
and explicit demonstration profiles; channel meanings are application-defined:

```sh
opensmell plan examples/multisource_diphenyl_ether.osmell \
  --profile examples/offline_semantic_profile.json \
  --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 0.1 > semantic-plan.json
opensmell plan examples/multisource_diphenyl_ether.osmell \
  --profile examples/offline_perceptual_profile.json \
  --resource-id 219ef28c-9b58-52f2-93a7-0807f5897857 --duration 0.1 > perceptual-plan.json
opensmell run-sequence semantic-plan.json perceptual-plan.json \
  --software-command-json '["node","examples/lifecycle_adapter/device.cjs"]' \
  --expected-device-id opensmell-node-simulator-001 --output sequence-report.json
```

The command accepts 1–16 plan files, at most 8 MiB each / 16 MiB combined and
120 seconds of summed requested duration. Every artifact is recomputed from its
embedded source/profile/request **before launching** the child. Every plan is
also checked against negotiated live capabilities before the first render.
There is no duration substitution, remapping, automatic retry or reconnect.
The software command and pinned expected identity are explicit caller choices;
source data never selects an executable. The child is trusted, not sandboxed.
Do not supply serial/GPIO helpers or physical device commands.

Copy the fixture, profiles and standalone endpoint to any work directory to run
outside the checkout; no `apps/local_demo` import or repository working directory
is required. With Python use `["/absolute/path/to/python","-I","-u",
"/absolute/path/to/python_device.py"]` and identity
`opensmell-local-simulator-001`. The extracted developer kit includes the guide
as `SOFTWARE_SEQUENCE.md` and the Stop consumer as `stop_after_acceptance.py`;
its equivalent fixture is `data/multisource_diphenyl_ether.osmell`, profiles are
`profiles/semantic.json` and `profiles/perceptual.json`, endpoints are in
`software/`. These are source/wheel trials, not a registry release.

## Receipts and failure boundaries

The exclusively created output is checkpointed before exchanges and after
observations. Its nested `sequence.steps` keeps each plan, exact offline-artifact
bytes in Base64, declared source/profile hashes, request, local request ID and
execution receipt. Unknown input extensions survive in that exact input; they
never enter command frames. Source/profile hashes and endpoint identity are not
authenticated. Reports retain supplied data and executable arguments.

| Observation | Sequence behavior |
|---|---|
| `accepted` / `running` | Poll the same execution ID; never send the next plan yet |
| Correlated `completed` | Retain the receipt, then send the next explicit plan |
| `rejected` / `stopped` | Retain the refusal/Stop observation; later steps stay `not_attempted` |
| EOF, timeout, malformed/mismatched reply, missing/reused ID | Close the link, retain `unknown`; no resend or next plan |
| No terminal receipt within requested duration + 3 seconds | Close as `unknown`; elapsed time is not proof of completion |
| Report write/callback failure | Abort and close; never advance on missing evidence |

Earlier completed receipts remain completed after a later failure. A checkpoint
without a response is intent, **not** acceptance. After interruption, an incomplete
file is not a completed report; there is no automatic resume or reconciliation.
Ctrl-C closes the link and can leave execution unknown; it does not establish Stop.
Exit codes: 0 all steps completed, 3 refusal/incompatibility or deliberate stop/
cancellation, 1 invalid/uncertain result, 2 file access/collision. Existing evidence
is never overwritten. Checkpoint writes are flushed, not crash-atomic/fsynced;
a crash or storage failure may leave a partial report.

## Reuse the installed SDK and cooperative Stop

`opensmell.experimental.sequence.SequenceStep(step_id, plan, context)` and
`SequenceRunner(client, steps, on_progress=callback)` accept an already negotiated
`LifecycleAdapter` and copy explicit plans/JSON context. The runner takes
exclusive ownership and closes the client on exit; do not use that client from
another caller. Construction refuses an active/uncertain execution before taking
ownership. A run is one-shot, even after failure. Passive `runner.report` snapshots
never poll or execute. Application checkpoints receive copies.

`runner.request_stop()` cooperatively cancels later sends and requests Stop for
a known active execution at the next checkpoint. It is serialized with synchronous
exchanges and can wait for an in-progress I/O; this is not an emergency stop or
instant preemption. A Stop racing completion records that completion and cancels
later steps without falsely claiming `stopped`. Cancellation before any render
or between steps is `cancelled`; only an actual endpoint reply establishes Stop.

The standalone installed-SDK consumer demonstrates cancellation after acceptance:

```sh
opensmell plan examples/multisource_diphenyl_ether.osmell \
  --profile examples/offline_semantic_profile.json \
  --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 5 > stop-plan.json
python examples/sequence/stop_after_acceptance.py stop-plan.json perceptual-plan.json \
  --software-command-json '["node","examples/lifecycle_adapter/device.cjs"]' \
  --expected-device-id opensmell-node-simulator-001 > stopped-report.json
```

Use a new report name. Expected: first step `stopped`, second `not_attempted`, one
render followed by a correlated Stop. If the endpoint completed before Stop,
the consumer reports cancellation/completion honestly and exits nonzero for this
demonstration. No physical Stop guarantee follows from software observations.

## Reproduce installed evidence

```sh
python -m build --wheel
python -m tools.verify_installed_sequence dist/opensmell-0.1.0-py3-none-any.whl \
  --evidence-directory dist/sequence-proof
```

This creates a wheel installation outside the checkout and copies standalone
consumers. Against Python and independent Node, it checks two distinct plans,
cooperative Stop and a proxy that deliberately discards the second actual
acceptance: the first receipt survives, the second is unknown, no third render.
Raw client transcripts and separate proxy observations are retained. Host build
dependencies are inherited; this is not a clean offline dependency closure proof.

To include the **actual sketch compiled natively**, first follow
[firmware-lifecycle.md](firmware-lifecycle.md) to compile the opt-in host harness,
then add `--host /absolute/path/to/opensmell-lifecycle-host` and choose another new
evidence directory. Native timing is input-sampled and synthetic output is not an
independent physical observation. Board compilation/manual validation are separate
boundaries; no port or flash action occurs here.

Exit criterion for this slice: installed CLI/SDK, both distinct plans, correlated
advancement, Stop and lost-reply abort against all three software targets; bounds,
late-capability refusal, cancellation and no-overwrite tests. After these pass,
close this first sequence slice; no scheduling engine, physical sequence mode or
additional lifecycle diagnostics by default.
