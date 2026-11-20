"""Build a local trial ZIP with the wheel, JS package and explicit runnable fixtures.

Requires the normal Python development build dependencies and Node/npm. Builds
local artifacts only; never publishes, creates a tag or runs a device endpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Explicit allowlist; external datasets, caches and arbitrary checkout files are excluded.
PAYLOADS = {
    "EXPERIMENT_TABLE.md": "docs/experiment-table.md",
    "data/trials.csv": "examples/experiment/trials.csv",
    "data/multisource_diphenyl_ether.osmell": "examples/multisource_diphenyl_ether.osmell",
    "SOFTWARE_SEQUENCE.md": "docs/software-sequence.md",
    "stop_after_acceptance.py": "examples/sequence/stop_after_acceptance.py",
    "SCIENTIFIC_PLAN_TRIAL.md": "docs/scientific-plan-trial.md",
    "science_to_plan.py": "examples/rdkit_molecule/science_to_plan.py",
    "RDKIT_MOLECULE.md": "docs/rdkit-molecule.md",
    "analyze_molecule.py": "examples/rdkit_molecule/analyze.py",
    "read_molecule_sdf.py": "examples/rdkit_molecule/read_sdf.py",
    "REFERENCE_GRAPH.md": "docs/reference-graph.md",
    "inspect_reference_graph.py": "examples/networkx_graph/inspect_bundle.py",
    "LIFECYCLE_TRIAL.md": "docs/lifecycle-trial.md",
    "OBSERVATION_ANALYSIS.md": "docs/observation-analysis.md",
    "analyze_observations.py": "examples/pandas_analysis/analyze.py",
    "OFFLINE_INSTALL.md": "docs/offline-kit.md",
    "CALLER_GRAPH.md": "docs/caller-graph-trial.md",
    "graph_trial.py": "examples/developer_kit/graph_trial.py",
    "PERCEPTUAL_IMPORT.md": "docs/perceptual-csv-import.md",
    "prepare_keller_reference.py": "examples/perceptual_import/prepare_reference.py",
    "data/synthetic_keller.csv": "examples/synthetic_keller.csv",
    "data/synthetic_keller_source.json": "examples/synthetic_keller_source.json",
    "profiles/perceptual.json": "examples/offline_perceptual_profile.json",
    "NATIVE_REPLAY.md": "docs/native-frame-replay.md",
    "PROTOCOL_FRAMES.md": "docs/protocol-frame-export.md",
    "profiles/esp32-led-capabilities.json": "hardware/esp32/led_capabilities.json",
    "CALLER_COHORT.md": "docs/caller-cohort-trial.md",
    "START_HERE.md": "examples/developer_kit/START_HERE.md",
    "cohort_trial.py": "examples/developer_kit/cohort_trial.py",
    "try_kit.py": "examples/developer_kit/try_kit.py",
    "try_client.cjs": "examples/lifecycle_client/try_client.cjs",
    "software/python_device.py": "examples/lifecycle_adapter/python_device.py",
    "inspect.cjs": "examples/developer_kit/inspect.cjs",
    "LICENSE": "LICENSE",
    "data/synthetic_odornet_batch.csv": "examples/synthetic_odornet_batch.csv",
    "data/odornet_public_source.json": "examples/odornet_public_source.json",
    "data/source.json": "examples/synthetic_odornet_source.json",
    "profiles/semantic.json": "examples/offline_semantic_profile.json",
    "software/device.cjs": "examples/lifecycle_adapter/device.cjs",
}


def make_archive(payloads: dict[str, bytes], source: dict, offline_target=None) -> bytes:
    files = {name: {"byte_length": len(data), "sha256": hashlib.sha256(data).hexdigest()}
             for name, data in sorted(payloads.items())}
    manifest = {"format": "org.opensmell.experimental.developer-kit", "version": "0.1",
                "source": source, "experimental": True, "physical_validation": False,
                "files": files,
                "limits": ["Hashes are not signatures or proof of source authenticity.",
                           "Python third-party dependencies are not bundled; see START_HERE.md.",
                           "Bundled CSV is synthetic; caller data is separate. Software endpoints only; not a published release."]}
    if offline_target:
        manifest['offline_target'] = offline_target
        manifest['limits'][1] = 'Pinned Python wheels bundled for the declared offline target; Python/venv and Node/npm must already be installed.'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted({**payloads, "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}.items()):
            # Stable metadata for a given set of artifact bytes; wheels may vary across builds.
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New ZIP file; existing outputs are refused")
    parser.add_argument('--wheelhouse',type=Path,help='Explicit prepared pinned dependency directory; adds offline target, no automatic download')
    args = parser.parse_args()
    offline_payloads = {}
    target = None
    if args.wheelhouse:
        from .offline_dependencies import load_wheelhouse, TARGET
        offline_payloads = load_wheelhouse(args.wheelhouse)
        target = TARGET
    if args.output.exists():
        parser.error("Output already exists")
    npm = shutil.which("npm")
    if not npm:
        parser.error("npm is required to pack the local JavaScript SDK")
    with tempfile.TemporaryDirectory(prefix="opensmell-kit-build-") as temporary:
        artifacts = Path(temporary)
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", artifacts],
                       cwd=ROOT, check=True, stdout=sys.stderr)
        wheels = list(artifacts.glob("*.whl"))
        if len(wheels) != 1 or wheels[0].name != "opensmell-0.1.0-py3-none-any.whl":
            raise ValueError("Unexpected Python artifact; update kit install instructions when changing version")
        packed = json.loads(subprocess.check_output([npm, "pack", "--ignore-scripts", "--json", "--pack-destination", artifacts],
                                                   cwd=ROOT / "packages/javascript"))[0]
        if packed["name"] != "@opensmell/graph-reader" or packed["filename"] != "opensmell-graph-reader-0.1.0-experimental.0.tgz":
            raise ValueError("Unexpected JavaScript artifact; update kit install instructions when changing version")
        lifecycle = json.loads(subprocess.check_output([npm, "pack", "--ignore-scripts", "--json", "--pack-destination", artifacts],
                                                      cwd=ROOT / "packages/lifecycle-client"))[0]
        if lifecycle["filename"] != "opensmell-lifecycle-client-0.1.0-experimental.0.tgz":
            raise ValueError("Unexpected lifecycle package version")
        payloads = {name: (ROOT / source).read_bytes() for name, source in PAYLOADS.items()}
        payloads["packages/" + wheels[0].name] = wheels[0].read_bytes()
        payloads["packages/" + packed["filename"]] = (artifacts / packed["filename"]).read_bytes()
        payloads["packages/" + lifecycle["filename"]] = (artifacts / lifecycle["filename"]).read_bytes()
        if target:
            payloads.update(offline_payloads)
            payloads['offline_dependencies.py'] = (ROOT/'tools/offline_dependencies.py').read_bytes()
            payloads['install_offline.py'] = (ROOT/'examples/developer_kit/install_offline.py').read_bytes()
            inventory = json.loads(payloads['wheelhouse/inventory.json'])
            requirements = [f"opensmell==0.1.0 --hash=sha256:{hashlib.sha256(wheels[0].read_bytes()).hexdigest()}"]
            requirements += [f"{e['metadata']['name']}=={e['metadata']['version']} --hash=sha256:{e['sha256']}" for e in inventory['wheels']]
            payloads['offline-requirements.txt'] = ('\n'.join(requirements)+'\n').encode()
        payloads["package.json"] = b'{"name":"opensmell-local-kit-trial","private":true}\n'
        try:
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        except (OSError, subprocess.CalledProcessError):
            revision, dirty = None, None
        data = make_archive(payloads, {"repository": "https://github.com/YAAASSS/OpenSmell",
                                       "checkout_commit": revision, "checkout_dirty": dirty,
                                       "artifact_relation": "Built locally from this checkout; hashes identify included artifacts, not a signed build."}, offline_target=target)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as output:
            output.write(data)
        print(json.dumps({"output": str(args.output.resolve()), "byte_length": len(data),
                          "sha256": hashlib.sha256(data).hexdigest(), "experimental": True}))


if __name__ == "__main__":
    main()
