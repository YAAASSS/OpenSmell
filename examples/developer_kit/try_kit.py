"""Try the installed OpenSmell kit: declared synthetic CSV to software observations.

Run explicitly after installing the included wheel and local JavaScript package.
No repository/application imports, external dataset download or physical access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_manifest():
    manifest = json.loads((ROOT / "manifest.json").read_bytes())
    if manifest["format"] != "org.opensmell.experimental.developer-kit" or manifest["version"] != "0.1":
        raise ValueError("Unsupported kit manifest")
    for name, identity in manifest["files"].items():
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT) or target == ROOT:
            raise ValueError("Manifest path outside kit")
        data = target.read_bytes()
        if len(data) != identity["byte_length"] or digest(data) != identity["sha256"]:
            raise ValueError(f"Kit bytes differ from manifest: {name}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write full software observations to a new JSON file")
    args = parser.parse_args()
    if args.report and args.report.exists():
        parser.error("Report already exists; choose a new output path")
    manifest = check_manifest()
    with tempfile.TemporaryDirectory(prefix="opensmell-kit-trial-") as temporary:
        work = Path(temporary)

        def run(arguments, expected=0):
            result = subprocess.run([str(x) for x in arguments], cwd=work,
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != expected:
                raise RuntimeError(f"Exit {result.returncode} (expected {expected}): {arguments}\n"
                                   f"{result.stdout}\n{result.stderr}")
            return json.loads(result.stdout) if result.stdout.strip() else None

        def cli(*arguments, expected=0):
            return run([sys.executable, "-I", "-m", "opensmell", *arguments], expected)

        batch_path = work / "cohort.json"
        cli("import-odornet-batch", ROOT / "data/synthetic_odornet_batch.csv",
            "--rows", "1", "2", "3", "9", "--source", ROOT / "data/source.json",
            "--output", batch_path, expected=3)
        batch = json.loads(batch_path.read_bytes())
        if batch["counts"] != {"accepted": 2, "rejected": 2}:
            raise ValueError("Unexpected cohort outcomes")
        records = []
        profile = ROOT / "profiles/semantic.json"
        for row, commands in ((1, [{"channel": 0, "intensity": 0.25}]),
                              (3, [{"channel": 1, "intensity": 0.6}])):
            core, graph, transferred = (work / f"record-{row}{suffix}" for suffix in
                                        ("-core.osmell", "-graph.osmell", "-transfer.osmell"))
            cli("extract-csv-record", batch_path, "--row", row, "--output", core)
            cli("bridge-core", core, "--output", graph)
            resource = json.loads(graph.read_bytes())["org.opensmell.experimental.core-import"]["primary_resource_id"]
            inspection = run(["node", ROOT / "inspect.cjs", graph, transferred])
            if transferred.read_bytes() != graph.read_bytes():
                raise ValueError("JavaScript transfer changed graph bytes")
            validation = cli("validate", transferred, "--json")
            if validation["results"][0]["status"] != "valid":
                raise ValueError("Transferred graph failed installed Python validation")
            recovered = work / f"record-{row}-recovered.osmell"
            cli("extract-core", transferred, "--output", recovered)
            if recovered.read_bytes() != core.read_bytes():
                raise ValueError("Original Core source was not recovered intact")
            plan = cli("plan", transferred, "--profile", profile, "--resource-id", resource, "--duration", "5")
            if plan["execution"] != "not_attempted" or plan["plan"]["commands"] != commands:
                raise ValueError("Unexpected passive plan")
            observations = {}
            for endpoint, options in (("python", []), ("node", ["--node", ROOT / "software/device.cjs"])):
                report = run([sys.executable, "-I", "-m", "opensmell.experimental.lifecycle_demo",
                              "--graph", transferred, "--profile", profile, "--resource-id", resource, *options])
                if [report["results"][key]["state"] for key in ("completion", "stop", "disconnect")] != ["completed", "stopped", "unknown"]:
                    raise ValueError("Software lifecycle proof failed")
                if report["physical_validation"] is not False:
                    raise ValueError("Unexpected physical claim")
                observations[endpoint] = report
            records.append({"row": row, "core_sha256": digest(core.read_bytes()),
                            "graph_sha256": digest(graph.read_bytes()), "javascript": inspection,
                            "validation": validation, "plan": plan, "software_observations": observations})
        report = {"experimental": True, "physical_validation": False, "result": "passed",
                  "kit_source": manifest["source"], "manifest_sha256": digest((ROOT / "manifest.json").read_bytes()),
                  "runtime": {"python": sys.version, "node": subprocess.check_output(["node", "--version"], text=True).strip()},
                  "source_kind": "synthetic", "batch": batch, "records": records,
                  "limits": ["Repository-maintained software endpoints; no third-party adoption or physical output evidence.",
                             "Manifest hashes identify bytes, not source authenticity; synthetic labels are not measurements.",
                             "Local development kit, not a release or complete offline dependency distribution."]}
        encoded = json.dumps(report, indent=2) + "\n"
        if args.report:
            with args.report.open("x", encoding="utf-8") as output:
                output.write(encoded)
        print(encoded, end="")


if __name__ == "__main__":
    main()
