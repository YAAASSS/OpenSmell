"""Install an extracted kit in a fresh environment outside the checkout and try it.

Python dependencies are inherited from the development environment. This verifies
local package installation, not a complete offline third-party wheelhouse.
"""
from __future__ import annotations

import argparse
import csv
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
        # Caller-owned files live outside the immutable kit. Change both row
        # order and profile values so the fixed synthetic self-test cannot pass
        # accidentally in place of the custom workflow.
        caller_csv, caller_source, caller_profile = (work / name for name in
                                                    ("caller.csv", "source.json", "profile.json"))
        with (kit / "data/synthetic_odornet_batch.csv").open(newline="") as source_file:
            rows = list(csv.reader(source_file))
        rows.append(["CCO", *(["0"] * 12), "Caller test record with no positive bindings"])
        with caller_csv.open("w", newline="") as target:
            csv.writer(target).writerows(rows)
        source_metadata = json.loads((kit / "data/source.json").read_bytes())
        source_metadata.update(name="Caller synthetic trial", custom_note="Preserve this unknown declaration")
        caller_source.write_text(json.dumps(source_metadata))
        profile = json.loads((kit / "profiles/semantic.json").read_bytes())
        profile["bindings"][0]["intensity"] = 0.4
        profile["bindings"][1]["intensity"] = 0.8
        caller_profile.write_text(json.dumps(profile))
        invocation = [python, "try_kit.py", "--csv", caller_csv, "--source", caller_source,
                      "--profile", caller_profile, "--rows", "3", "1", "4", "2", "99"]
        passive = json.loads(run(invocation + ["--report", work / "passive.json"], expected=3).stdout)
        if passive["execution"] != "not_attempted" or passive["counts"] != {"planned": 2, "planning_rejected": 1, "import_rejected": 2}:
            raise ValueError("Caller passive outcomes were dropped or executed")
        if [x["row"] for x in passive["records"]] != [3, 1, 4, 2, 99]:
            raise ValueError("Caller-selected order was lost")
        if passive["batch"]["source"].get("custom_note") != source_metadata["custom_note"]:
            raise ValueError("Unknown source declaration was lost")
        for record, expected in zip(passive["records"][:2],
                                    ([{"channel": 1, "intensity": 0.8}], [{"channel": 0, "intensity": 0.4}])):
            if record["plan"]["plan"]["commands"] != expected or record.get("software_observations"):
                raise ValueError("Caller profile was ignored or passive mode observed software")
        simulated_path = work / "simulated.json"
        simulated = json.loads(run(invocation + ["--simulate", "--report", simulated_path], expected=3).stdout)
        if simulated["counts"] != {"software_verified": 2, "planning_rejected": 1, "import_rejected": 2}:
            raise ValueError("Caller software trial lost per-record refusals")
        for record in simulated["records"][:2]:
            observations = record["software_observations"]
            if len(observations) != 4 or record["execution"] != "software_observed":
                raise ValueError("Both installed clients/endpoints were not observed")
            for name, observation in observations.items():
                states = ([observation["results"][key]["state"] for key in ("completion", "stop", "disconnect")]
                          if name.startswith("python_client") else
                          [observation[key]["state"] for key in ("completed", "stopped", "unknown")])
                if states != ["completed", "stopped", "unknown"] or observation["physical_validation"] is not False:
                    raise ValueError("Invalid caller software observation")
        retained = simulated_path.read_bytes()
        run(invocation + ["--simulate", "--report", simulated_path], expected=2)
        if simulated_path.read_bytes() != retained:
            raise ValueError("Caller report was overwritten")
        # A source/profile with a positive minimum duration cannot run the 0.1s
        # demonstration; it must remain planned/refused without launching a client.
        profile["capabilities"]["min_duration"] = 1
        caller_profile.write_text(json.dumps(profile))
        preflight = json.loads(run(invocation + ["--simulate", "--report", work / "preflight.json"], expected=3).stdout)
        if preflight["execution"] != "not_attempted" or preflight["counts"].get("simulation_preflight_rejected") != 2:
            raise ValueError("Incompatible simulation duration was not refused before execution")
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
                          "caller_cohort": "passive and explicit simulation; partial refusals retained",
                          "physical_validation": False}))


if __name__ == "__main__":
    main()
