"""Check a wheel in a fresh venv, from a directory outside the checkout.

Dependencies are inherited from the build/test environment; the wheel itself is
installed locally without accessing an index. No application modules are used.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m tools.verify_installed_cli path/to/opensmell.whl")
    wheel = Path(sys.argv[1]).resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="opensmell-wheel-") as directory:
        work = Path(directory)
        environment = work / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        executable = scripts / ("opensmell.exe" if os.name == "nt" else "opensmell")
        env = {key: value for key, value in os.environ.items()
               if key not in {"PYTHONPATH", "PYTHONHOME"}}

        def run(arguments, *, expected=0, data=None):
            result = subprocess.run([str(arg) for arg in arguments], cwd=work, env=env,
                                    input=data, capture_output=True, check=False)
            if result.returncode != expected:
                raise RuntimeError(f"Command failed ({result.returncode}): {arguments}\n"
                                   f"{result.stdout.decode()}\n{result.stderr.decode()}")
            return result

        run([python, "-m", "pip", "install", "--no-deps", "--no-index", "--ignore-installed", wheel])
        location = run([python, "-I", "-c", "import opensmell; print(opensmell.__file__)"])
        if not Path(location.stdout.decode().strip()).is_relative_to(environment):
            raise RuntimeError("Import did not resolve to the wheel installed in the fresh environment")
        for name in ("geraniol.osmell", "multisource_beta_pinene.osmell",
                     "multisource_diphenyl_ether.osmell", "offline_semantic_profile.json",
                     "offline_perceptual_profile.json"):
            shutil.copyfile(root / "examples" / name, work / name)
        result = run([executable, "validate", "geraniol.osmell", "multisource_beta_pinene.osmell", "--json"])
        if [item["status"] for item in json.loads(result.stdout)["results"]] != ["valid", "valid"]:
            raise RuntimeError("Installed validator did not accept both formats")
        result = run([python, "-I", "-m", "opensmell", "inspect", "-", "--json"],
                     data=(work / "multisource_beta_pinene.osmell").read_bytes())
        if json.loads(result.stdout)["results"][0]["known_reference_count"] <= 0:
            raise RuntimeError("Installed inspector did not discover graph references")
        run([executable, "validate", "-", "--json"], expected=1, data=b'{"x":1,"x":2}')
        run([executable, "validate", "missing.osmell", "--json"], expected=2)
        for mapper, resource_id, channels in (
            ("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", [0, 1]),
            ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857", [0, 1, 2]),
        ):
            result = run([executable, "plan", "multisource_diphenyl_ether.osmell", "--profile",
                          f"offline_{mapper}_profile.json", "--resource-id", resource_id, "--duration", "5"])
            artifact = json.loads(result.stdout)
            if artifact["execution"] != "not_attempted" or sorted(c["channel"] for c in artifact["plan"]["commands"]) != channels:
                raise RuntimeError("Installed planner did not produce expected passive plan")
        # Core bridge/export/recovery from the installed entry point.
        original = (work / "geraniol.osmell").read_bytes()
        run([executable, "bridge-core", "geraniol.osmell", "--output", "core-graph.osmell"])
        graph_raw = (work / "core-graph.osmell").read_bytes()
        imported = json.loads(graph_raw)
        key = "org.opensmell.experimental.core-import"
        resource_id = imported[key]["primary_resource_id"]
        run([executable, "validate", "core-graph.osmell", "--json"])
        recovery = run([python, "-I", "-m", "opensmell", "extract-core", "-"], data=graph_raw)
        if recovery.stdout != original:
            raise RuntimeError("Installed Core recovery did not preserve exact bytes")
        run([executable, "bridge-core", "geraniol.osmell", "--output", "geraniol.osmell"], expected=2)
        if (work / "geraniol.osmell").read_bytes() != original:
            raise RuntimeError("Core source was overwritten")
        result = run([executable, "plan", "core-graph.osmell", "--profile",
                      "offline_semantic_profile.json", "--resource-id", resource_id, "--duration", "5"])
        commands = json.loads(result.stdout)["plan"]["commands"]
        if commands != [{"channel": 0, "intensity": 0.25}]:
            raise RuntimeError("Installed bridged graph did not produce expected plan")
        run([executable, "bridge-core", "-"], data=b"{}", expected=1)
        print("Installed Core bridge: graph validation, plan, exact recovery and no-overwrite checks passed.")
        # Both clients run in the installed environment, with no app imports.
        node = shutil.which("node")
        if node:
            shutil.copyfile(root / "examples/lifecycle_adapter/device.cjs", work / "device.cjs")
            # Independent JS inspection returns original graph bytes, preserving the snapshot.
            shutil.copyfile(root / "apps/graph_viewer_js/reader.js", work / "reader.cjs")
            run([node, "-e", """
const fs = require('node:fs');
globalThis.crypto = require('node:crypto').webcrypto;
const reader = require('./reader.cjs');
reader.inspectBytes(fs.readFileSync('core-graph.osmell')).then(value => {
  if (value.report.status === 'rejected') throw Error(JSON.stringify(value.report.diagnostics));
  fs.writeFileSync('core-graph-js.osmell', value.copyBytes());
}).catch(error => { console.error(error); process.exitCode = 1; });
"""])
            recovery = run([executable, "extract-core", "core-graph-js.osmell"])
            if recovery.stdout != original or (work / "core-graph-js.osmell").read_bytes() != graph_raw:
                raise RuntimeError("JS inspection/exchange changed graph or original Core bytes")

        for arguments in ([], ["--node", str(work / "device.cjs")]) if node else ([],):
            result = run([python, "-I", "-m", "opensmell.experimental.lifecycle_demo", *arguments])
            states = json.loads(result.stdout)["results"]
            if [states[k]["state"] for k in ("completion", "stop", "disconnect")] != ["completed", "stopped", "unknown"]:
                raise RuntimeError("Installed lifecycle proof failed")
        for mapper, resource in (("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b"),
                                 ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857")):
            for endpoint in ([], ["--node", str(work / "device.cjs")]) if node else ([],):
                result = run([python, "-I", "-m", "opensmell.experimental.lifecycle_demo",
                              "--graph", "multisource_diphenyl_ether.osmell",
                              "--profile", f"offline_{mapper}_profile.json",
                              "--resource-id", resource, *endpoint])
                report = json.loads(result.stdout)
                if report["results"]["completion"]["state"] != "completed" or not report["source"]["inspection"]["sha256"]:
                    raise RuntimeError("Installed graph-to-execution proof failed")
        for endpoint in ([], ["--node", str(work / "device.cjs")]) if node else ([],):
            result = run([python, "-I", "-m", "opensmell.experimental.lifecycle_demo",
                          "--graph", "core-graph.osmell", "--profile", "offline_semantic_profile.json",
                          "--resource-id", resource_id, *endpoint])
            if json.loads(result.stdout)["results"]["completion"]["state"] != "completed":
                raise RuntimeError("Installed Core-to-execution proof failed")
        run([python, "-I", "-m", "opensmell.experimental.lifecycle_demo", "--graph", "missing"], expected=2)
        print("Installed lifecycle proof passed: Python" + (" and Node." if node else "; Node unavailable."))
        print("Installed wheel CLI passed outside the checkout: Core, graph, stdin, errors, both offline mappers and import location.")


if __name__ == "__main__":
    main()
