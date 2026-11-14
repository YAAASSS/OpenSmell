"""Install an extracted kit in a fresh environment outside the checkout and try it.

Python dependencies are inherited from the development environment. This verifies
local package installation, not a complete offline third-party wheelhouse.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="opensmell-extracted-kit-") as temporary:
        work = Path(temporary)
        kit = work / "kit"
        kit.mkdir()
        with zipfile.ZipFile(args.archive) as archive:
            names = archive.namelist()
            if len(set(names)) != len(names) or any(not (kit / name).resolve().is_relative_to(kit) for name in names):
                raise ValueError("Unsafe or duplicate archive paths")
            archive.extractall(kit)
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        environment = work / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("npm is required")

        def run(command, expected=0):
            result = subprocess.run([str(x) for x in command], cwd=kit, env=env,
                                    capture_output=True, text=True, timeout=120)
            if result.returncode != expected:
                raise RuntimeError(f"{command}\n{result.stdout}\n{result.stderr}")
            return result

        wheel, = (kit / "packages").glob("*.whl")
        packages = sorted((kit / "packages").glob("*.tgz"))
        if len(packages) != 2:
            raise ValueError("Both JavaScript packages are required")
        run([python, "-m", "pip", "install", "--no-index", "--no-deps", "--ignore-installed", wheel])
        location = run([python, "-I", "-c", "import opensmell; print(opensmell.__file__)"]).stdout.strip()
        if not Path(location).is_relative_to(environment):
            raise ValueError("Python import did not resolve to the installed kit wheel")
        run([npm, "install", "--offline", "--ignore-scripts", "--no-save", "--no-audit", "--no-fund", "--package-lock=false", *packages])
        output = kit / "trial.json"
        result = run([python, "try_kit.py", "--report", output])
        report = json.loads(result.stdout)
        if output.read_text() != result.stdout or report["result"] != "passed" or len(report["records"]) != 2:
            raise ValueError("Trial did not retain both records and its full software observations")
        before = output.read_bytes()
        run([python, "try_kit.py", "--report", output], expected=2)
        if output.read_bytes() != before:
            raise ValueError("Existing report was overwritten")
        # A damaged kit must fail at the manifest gate, before running any endpoint.
        source = kit / "data/synthetic_odornet_batch.csv"
        source.write_bytes(source.read_bytes() + b"\n")
        failure = run([python, "try_kit.py"], expected=1)
        if "Kit bytes differ from manifest" not in failure.stderr:
            raise ValueError("Changed data was not diagnosed at the manifest gate")
        print(json.dumps({"result": "passed", "consumer": "fresh extracted kit outside checkout",
                          "records": [x["row"] for x in report["records"]], "counts": report["batch"]["counts"],
                          "endpoints": ["python", "node"], "original_bytes_preserved": True,
                          "report_no_overwrite": True, "modified_data_refused": True,
                          "physical_validation": False}))


if __name__ == "__main__":
    main()
