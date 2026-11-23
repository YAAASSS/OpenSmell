# Optional actual native dry-load sketch (experimental)

This optional kit includes pinned ArduinoJson 7.2.1 headers/license, the actual
OpenSmell sketch and a fake serial/GPIO/clock harness. Supply Python, an installed
kit SDK and an explicitly trusted local C++17 compiler. No Git, checkout,
PlatformIO, ESP32 toolchain or download is needed at use time. Compiler and source
are trusted executable inputs, not sandboxed. No board port, flash or physical
command is available through this build entry.

For the separate Windows PowerShell path, see [WINDOWS_NATIVE.md](WINDOWS_NATIVE.md).
The commands below use the Linux executable name; Windows build emits `.exe`.

From the extracted kit on Linux:

```sh
python native_bench.py --compiler /usr/bin/g++ --output new-native-build
python native/tools/verify_dry_load.py new-native-build/dry-load-host --output new-native-proof.json
set -C
opensmell plan data/multisource_diphenyl_ether.osmell \
  --profile native/hardware/esp32/dry_load_profile.json \
  --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 5 > new-native-plan.json
opensmell lifecycle-trial new-native-plan.json \
  --software-command-json '["./new-native-build/dry-load-host","--realtime","--simulate-enable"]' \
  --expected-device-id opensmell-esp32-dry-load-001 --output new-native-trial.json
```

Build never launches the endpoint. Explicit subsequent controls sample fake input
only; the native proof exercises arm/drop/refusal and correlated SDK Stop. The
ordinary installed trial observes completion/Stop/unknown. No ESP32 binary is
produced. Compiler/platform compatibility beyond the verified Linux host and
bit-identical machine-code reproducibility are not claimed. CI repeats the extracted
compile/SDK/Node/owned-PTY proof with network interfaces disabled; its Python
build dependencies are inherited, separate from the clean offline SDK target.

The inventory records per-file SHA256/length and ArduinoJson commit
`f9fe8557f13d8949eafd49ebd93a2929c4e5065f`. The packer reads committed headers,
not modified/untracked dependency worktree files. Build checks inventory before
compiler launch, refuses added/missing/modified native files, and exclusively
creates its output directory. A failed compile leaves an error/incomplete report;
use a fresh directory after fixing it. Hashes identify bytes against this inventory,
not source authenticity or malicious replacement of both data and hashes.

BOM/wiring and the NOT RUN measurement sheet are included under
`native/hardware/esp32/DRY_LOAD.md` and `DRY_LOAD_RESULTS.md`. Repository-relative
crosslinks there refer to upstream source documentation; use this guide for kit
commands. The five-second limit is per command; the sampled permissive is not a
hardware emergency stop. No current, calibrated delivery, odor or outside adoption
is established. SDK default dependencies and RFC maturity remain unchanged.

To prepare this optional archive from a source checkout, explicitly obtain the
pinned ArduinoJson repository first, then select it:

```sh
python -m tools.build_developer_kit --native-arduinojson /path/to/ArduinoJson \
  --output new-native-kit.zip
```

This option can be combined with the existing prepared `--wheelhouse` target.
Python/compiler are prerequisites; no toolchain acquisition occurs. Ordinary kits
omit the native source bundle. The dependency license is retained at
`native/ArduinoJson/LICENSE.txt`.
