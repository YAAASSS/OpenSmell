# Windows extracted native kit (experimental)

This first Windows path builds a local executable of the actual dry-load sketch
with fake serial/GPIO/clock. It requires installed Python 3.12, Node 22 with its
standard npm layout, an explicitly supplied MinGW-w64 C++17 compiler, and its
runtime directory on PATH. No compiler installation/download occurs at use.
No WSL, hardware port, GPIO or flash is used. POSIX PTY coverage is separate.

Extract the optional native ZIP into a trusted directory. From PowerShell there,
create a virtual environment and install the included SDK wheel (its normal
Python dependencies must be available). Choose the compiler path that is actually
installed on your machine; the example is not a promise that this path exists.

```powershell
python -m venv '.\my venv'
& '.\my venv\Scripts\python.exe' -m pip install '.\packages\opensmell-0.1.0-py3-none-any.whl'
$compiler = 'C:\msys64\ucrt64\bin\g++.exe'
$env:PATH = (Split-Path $compiler) + ';' + $env:PATH
& '.\my venv\Scripts\python.exe' native_bench.py --compiler $compiler --output 'native build'
& '.\my venv\Scripts\python.exe' native\tools\verify_dry_load.py '.\native build\dry-load-host.exe' --output native-proof.json
```

Build only compiles; it never launches the produced executable. Subsequent
commands explicitly select the trusted .exe. `--simulate-enable` injects fake
input only. Native evidence covers arm/drop/refusal, not electrical behavior.

The included installed-SDK consumer avoids PowerShell JSON quoting. It requires
explicit source/profile/selection, creates a fresh report and runs the declared
short completion, explicit Stop and deliberate disconnect cases:

```powershell
& '.\my venv\Scripts\python.exe' native_trial.py --dry-load --native-host '.\native build\dry-load-host.exe' --graph data/multisource_diphenyl_ether.osmell --profile native/hardware/esp32/dry_load_profile.json --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --output sdk-trial.json
```

Expected: `result:passed`, `completed/stopped/unknown`; disconnect is not Stop.
The standard installed `plan` and `lifecycle-trial` CLI entries remain available
and are separately exercised by the automated proof using explicit argument arrays.

The full automated extracted-kit proof uses argument arrays for Python and Node,
paths with spaces, and verifies completion/Stop/unknown and collision/source
refusals on the real Windows runner. Build dependencies there are inherited;
this is not a clean offline Windows dependency closure. No MSVC/clang, arbitrary
Windows version or physical serial driver compatibility is claimed. Compiler
and source are trusted executable inputs, not sandboxed. Inventory hashes are
not signatures; machine code is not promised bit-reproducible.
