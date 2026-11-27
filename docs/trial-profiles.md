# Explicit per-trial profiles (experimental)

An installed caller can now prepare one dossier with a separately supplied profile
for each trial ID. The normal `prepare-experiment --trial-profiles FILE` entry and
SDK `prepare_experiment_profiles` compile all choices before creating output.
No profile is inferred from measurements, missing data, resource type or file paths.

## Prepare the caller inputs

First create a declared synthetic cohort using [cohort import](perceptual-cohort.md),
selecting records1 and2. With the resulting `cohort.osmell` and the example
`offline_perceptual_profile.json` in your working directory, this explicit example
writes the two remaining inputs (run only with new output filenames):

```python
from copy import deepcopy
import json
from pathlib import Path
cohort = json.loads(Path('cohort.osmell').read_bytes())
results = cohort['org.opensmell.experimental.perceptual-csv-cohort']['results']
ids = {r['data_record']: r['observation_id'] for r in results if r['status'] == 'accepted'}
base = json.loads(Path('offline_perceptual_profile.json').read_bytes())
second = deepcopy(base)
second['bindings'] = second['bindings'][:2]  # caller intentionally binds flower/grass
second['bindings'][0]['channel'] = 1        # caller chooses a different channel policy
second['bindings'][1]['channel'] = 0
bundle = {'format': 'org.opensmell.experimental.trial-profiles', 'version': '0.1',
          'profiles': {'first': base, 'second': second}}
with Path('policies.json').open('x') as output:
    json.dump(bundle, output, indent=2)
with Path('trials.csv').open('x') as output:
    output.write('trial_id,resource_id,duration,note\n'
                 f'first,{ids[1]},1,caller-policy-A\nsecond,{ids[2]},0.1,caller-policy-B\n')
```

These are declared synthetic source observations and illustrative channel choices,
not evidence of odor reproduction or new participant measurements. The graph
mapper's existing partial-property behavior stays unchanged: configured properties
without measurements are not silently created. The narrower second profile here
is an explicit caller choice, not a newly enforced scientific completeness rule.

## Installed normal entry

```sh
opensmell prepare-experiment trials.csv --graph cohort.osmell \
  --trial-profiles policies.json --output-directory experiment
opensmell run-experiment experiment \
  --software-command-json '["python","-m","opensmell","simulate-device"]' \
  --expected-device-id opensmell-local-simulator-001 --action complete --output receipts.json
```

The simulator command must resolve to the Python environment containing this SDK;
use its absolute executable path in your own environment. Preparation itself
opens no transport. Sending is a separate explicit choice. The dossier can move
and original paths can disappear before execution. On the synthetic example,
first trial commands are CH0=.26,CH1=0,CH2=.89 for1s; second commands are CH0=.2,
CH1=.8 for.1s. Inspect channel IDs rather than relying on command array order.
A receipt's software completion does not establish physical or olfactory results.

`--profile` and `--trial-profiles` are mutually exclusive and one is required.
The historical shared `--profile` entry/API and dossier0.1 remain unchanged.
For the new mode use a trial-profiles0.1 bundle: a `profiles` object keyed by all
and only the selected `trial_id` values, each containing a normal mapping/capability
profile. Missing, unused or malformed choices refuse; no default/fallback occurs.
Unknown bundle/profile fields remain retained in the exact bundle snapshot.
IDs are metadata, never filenames. CSV extra columns remain opaque in both modes.

## Dossier and verification boundaries

New preparation emits experimental **prepared-experiment0.2**, a local application
dossier version, not OpenSmell Core0.2 or a new device protocol. It retains exact
`trials.csv`, `source.osmell`, `profiles.json` and normal offline-plan0.1 files.
Each plan embeds only the selected profile object. Its declared profile hash is
of that object's sorted compact ensure-ASCII JSON serialization; it is not a byte
slice/hash of the entire bundle. The exact bundle bytes/hash remain separately
retained by the dossier and execution report. No original standalone profile file
is implied by this selection convention.

The loader explicitly dispatches dossier versions0.1/0.2, reads only their fixed
filenames, verifies inventory/hashes, and recomputes every trial/profile binding
before opening a separately supplied transport. A changed policy with updated
file hash still refuses if retained plans disagree. Unknown extra manifest/plan
fields remain passive. Unsupported versions, invalid last choice, stale bindings,
symlinks and output collisions refuse; there is no retry, scheduler or auto-send.

Existing bounds remain: table64KiB, source8MiB, bundle1MiB,1..16 trials/profiles,
120s total requested duration,16MiB combined plans and per-plan frame/capability
checks. All validation occurs before exclusive directory creation. Later filesystem
failures may leave an incomplete directory; preparation is not a crash-safe database.
The bundle can contain source declarations; hashes establish consistency, not
scientific validity, source authenticity, calibrated delivery or outside adoption.

SDK:

```python
from opensmell.experimental.experiment import prepare_experiment_profiles
from opensmell.experimental.experiment_run import load_prepared_experiment
prepare_experiment_profiles(table_bytes, graph_bytes, bundle_bytes, new_directory)
plans, context = load_prepared_experiment(new_directory)
```

Repeat the installed wheel/relocation/cohort proof on independent Python and Node
endpoints, optionally the explicitly selected actual-sketch native harness:

```sh
python -m build --wheel
python -m tools.verify_installed_trial_profiles dist/opensmell-0.1.0-py3-none-any.whl --output /absolute/new/proof
# Optional software-only native target, compiled as in the firmware bench guide:
python -m tools.verify_installed_trial_profiles dist/opensmell-0.1.0-py3-none-any.whl --host /absolute/trusted/native-harness --output /absolute/new/native-proof
```

The proof covers distinct policies, three ordered trials, completion, Stop-first,
second refusal/lost reply halting the tail, exact retained bundle, collision/no
traffic and hash-consistent stale policy/no process. Python dependencies are
inherited for this proof; no new clean closure or physical compatibility is claimed.
The historical single-profile, clean offline kit and existing device gates remain.
