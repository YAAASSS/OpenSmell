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
    "START_HERE.md": "examples/developer_kit/START_HERE.md",
    "try_kit.py": "examples/developer_kit/try_kit.py",
    "inspect.cjs": "examples/developer_kit/inspect.cjs",
    "LICENSE": "LICENSE",
    "data/synthetic_odornet_batch.csv": "examples/synthetic_odornet_batch.csv",
    "data/source.json": "examples/synthetic_odornet_source.json",
    "profiles/semantic.json": "examples/offline_semantic_profile.json",
    "software/device.cjs": "examples/lifecycle_adapter/device.cjs",
}


def make_archive(payloads: dict[str, bytes], source: dict) -> bytes:
    files = {name: {"byte_length": len(data), "sha256": hashlib.sha256(data).hexdigest()}
             for name, data in sorted(payloads.items())}
    manifest = {"format": "org.opensmell.experimental.developer-kit", "version": "0.1",
                "source": source, "experimental": True, "physical_validation": False,
                "files": files,
                "limits": ["Hashes are not signatures or proof of source authenticity.",
                           "Python third-party dependencies are not bundled; see START_HERE.md.",
                           "Synthetic data and software endpoints only; not a published release."]}
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
    args = parser.parse_args()
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
        payloads = {name: (ROOT / source).read_bytes() for name, source in PAYLOADS.items()}
        payloads["packages/" + wheels[0].name] = wheels[0].read_bytes()
        payloads["packages/" + packed["filename"]] = (artifacts / packed["filename"]).read_bytes()
        payloads["package.json"] = b'{"name":"opensmell-local-kit-trial","private":true}\n'
        try:
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        except (OSError, subprocess.CalledProcessError):
            revision, dirty = None, None
        data = make_archive(payloads, {"repository": "https://github.com/YAAASSS/OpenSmell",
                                       "checkout_commit": revision, "checkout_dirty": dirty,
                                       "artifact_relation": "Built locally from this checkout; hashes identify included artifacts, not a signed build."})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as output:
            output.write(data)
        print(json.dumps({"output": str(args.output.resolve()), "byte_length": len(data),
                          "sha256": hashlib.sha256(data).hexdigest(), "experimental": True}))


if __name__ == "__main__":
    main()
