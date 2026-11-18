"""Installed Python/Node clients against the actual opt-in native LED sketch.

Explicit trusted executable only; no serial/GPIO access, downloads or retries.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--evidence-directory", required=True, type=Path,
                        help="New directory; never overwrite existing evidence")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    wheel = args.wheel.resolve(strict=True)
    host = args.host.resolve(strict=True)
    if not host.is_file():
        parser.error("Explicit trusted host must be a regular executable file")
    evidence = args.evidence_directory.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    summary = {"result": "incomplete", "physical_validation": False,
               "native_sha256": hashlib.sha256(host.read_bytes()).hexdigest(),
               "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "cases": []}
    def checkpoint():
        (evidence / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    checkpoint()
    try:
        with tempfile.TemporaryDirectory(prefix="opensmell-installed-firmware-life-") as directory:
            work = Path(directory)
            env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(work / "venv")
            python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            def run(command, *, cwd=work, expected=0):
                result = subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                                        capture_output=True, timeout=60)
                if result.returncode != expected:
                    raise RuntimeError(f"{command}: {result.returncode} {result.stdout!r} {result.stderr!r}")
                return result.stdout
            run([python, "-m", "pip", "install", "--no-index", "--no-deps", "--ignore-installed", wheel])
            location = run([python, "-I", "-c", "import opensmell; print(opensmell.__file__)"]).decode().strip()
            assert Path(location).is_relative_to(work / "venv")
            summary["installed_outside_checkout"] = True
            summary["dependency_scope"] = "Wheel installed locally; host build dependencies inherited, not a clean/offline kit proof"
            npm = shutil.which("npm")
            if not npm:
                raise RuntimeError("npm and Node >=22 required")
            packed = json.loads(run([npm, "pack", "--ignore-scripts", "--json", "--pack-destination", work],
                                    cwd=root / "packages/lifecycle-client"))[0]
            (work / "package.json").write_text('{"private":true}')
            run([npm, "install", "--offline", "--ignore-scripts", "--no-audit", "--no-fund", "--package-lock=false",
                 work / packed["filename"]])
            for target, source in (("try_native.py", "examples/firmware_lifecycle/try_native.py"),
                                   ("try_client.cjs", "examples/lifecycle_client/try_client.cjs"),
                                   ("graph.osmell", "examples/multisource_diphenyl_ether.osmell")):
                (work / target).write_bytes((root / source).read_bytes())
            for mapper, resource in (("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b"),
                                     ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857")):
                (work / "profile.json").write_bytes((root / f"examples/offline_{mapper}_profile.json").read_bytes())
                report = work / f"python-{mapper}.json"
                command = [python, "-I", "try_native.py", "--native-host", host,
                           "--graph", "graph.osmell", "--profile", "profile.json", "--resource-id", resource,
                           "--output", report]
                run(command)
                result = json.loads(report.read_bytes())
                assert result["result"] == "passed" and result["duplicate_request_refused_before_io"]
                assert [result["results"][key]["state"] for key in ("completion", "stop", "disconnect")] == ["completed", "stopped", "unknown"]
                before = report.read_bytes()
                run(command, expected=1)  # exclusive checkpoint fails before creating a process
                assert report.read_bytes() == before
                (evidence / report.name).write_bytes(before)
                plan_report = json.loads(run([python, "-I", "-m", "opensmell", "plan", "graph.osmell",
                                               "--profile", "profile.json", "--resource-id", resource, "--duration", "5"]))
                plan = plan_report["plan"]
                (work / "plan.json").write_text(json.dumps(plan))
                node_result = json.loads(run(["node", "try_client.cjs", json.dumps([str(host), "--realtime"]),
                                              "opensmell-esp32-lifecycle-led-001", "plan.json"]))
                assert [node_result[key]["state"] for key in ("completed", "stopped", "unknown")] == ["completed", "stopped", "unknown"]
                (evidence / f"node-{mapper}.json").write_text(json.dumps(node_result, indent=2) + "\n")
                (evidence / f"plan-{mapper}.json").write_text(json.dumps(plan_report, indent=2) + "\n")
                summary["cases"].append({"mapper": mapper, "clients": ["python", "node"],
                                          "states": ["completed", "stopped", "unknown"], "report_collision_refused": True})
                checkpoint()
            summary["result"] = "passed"
    except BaseException as error:
        summary.update(result="error", error=str(error))
        checkpoint()
        raise
    checkpoint()
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
