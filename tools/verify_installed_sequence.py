"""Prove installed sequence CLI/SDK against explicit software, never hardware."""
import argparse
import base64
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
    parser.add_argument("--host", type=Path, help="Optional explicit trusted actual native lifecycle sketch executable")
    parser.add_argument("--evidence-directory", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    wheel = args.wheel.resolve(strict=True)
    host = args.host.resolve(strict=True) if args.host else None
    evidence = args.evidence_directory.resolve(); evidence.mkdir(parents=True, exist_ok=False)
    summary = {"result": "incomplete", "experimental": True, "physical_validation": False,
               "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "cases": [],
               "dependency_scope": "Wheel installed outside checkout; build-environment dependencies inherited, not a clean/offline dependency proof"}
    if host: summary["native_sha256"] = hashlib.sha256(host.read_bytes()).hexdigest()
    def write(name, value):
        (evidence / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    write("result.json", summary)
    with tempfile.TemporaryDirectory(prefix="opensmell-installed-sequence-") as directory:
        work = Path(directory)
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(work / "venv")
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = [python, "-I", "-m", "opensmell"]
        def run(command, expected=0):
            result = subprocess.run([str(x) for x in command], cwd=work, env=env, capture_output=True, timeout=60)
            if result.returncode != expected:
                raise RuntimeError(f"{command}: exit {result.returncode}; {result.stdout!r} {result.stderr!r}")
            return result.stdout
        run([python, "-m", "pip", "install", "--no-index", "--no-deps", "--ignore-installed", wheel])
        location = run([python, "-I", "-c", "import opensmell; print(opensmell.__file__)"]).decode().strip()
        assert Path(location).is_relative_to(work / "venv")
        summary["installed_outside_checkout"] = True
        for name in ("multisource_diphenyl_ether.osmell", "offline_semantic_profile.json", "offline_perceptual_profile.json"):
            shutil.copyfile(root / "examples" / name, work / name)
        for source, name in [(root / "examples/lifecycle_adapter/python_device.py", "python_device.py"),
                             (root / "examples/lifecycle_adapter/device.cjs", "device.cjs"),
                             (root / "examples/sequence/stop_after_acceptance.py", "stop_after_acceptance.py")]:
            shutil.copyfile(source, work / name)
        plans = []
        for name, resource, duration in [("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", ".1"),
                                          ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857", ".1"),
                                          ("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", "5")]:
            raw = run([*cli, "plan", work / "multisource_diphenyl_ether.osmell", "--profile", work / f"offline_{name}_profile.json",
                       "--resource-id", resource, "--duration", duration])
            path = work / f"plan-{len(plans)}.json"; path.write_bytes(raw); plans.append(path)
        assert json.loads(plans[0].read_bytes())["plan"]["commands"] != json.loads(plans[1].read_bytes())["plan"]["commands"]
        node = shutil.which("node")
        if not node: raise RuntimeError("Explicit Node reference runtime required")
        endpoints = [("python", [str(python), "-I", "-u", str(work / "python_device.py")], "opensmell-local-simulator-001"),
                     ("node", [node, str(work / "device.cjs")], "opensmell-node-simulator-001")]
        if host: endpoints.append(("native", [str(host), "--realtime"], "opensmell-esp32-lifecycle-led-001"))
        # This trusted proxy deliberately discards the second actual acceptance.
        # Retain downstream replies separately; they never become client receipts.
        proxy = work / "lost_reply.py"
        proxy.write_text('''import json,sys
from pathlib import Path
from opensmell.experimental.process_transport import ProcessTransport
command=json.loads(sys.argv[1]); log=Path(sys.argv[2]); count=0
child=ProcessTransport(command,startup_timeout=5)
try:
 for line in sys.stdin:
  request=json.loads(line); reply=child.exchange(line.rstrip('\\n'))
  with log.open('a') as output:output.write(json.dumps({'request':request,'actual_reply':json.loads(reply)})+'\\n')
  if request['type']=='render':
   count+=1
   if count==2:break
  print(reply,end='',flush=True)
finally:child.close()
''')
        for name, command, identity in endpoints:
            command_json = json.dumps(command)
            output = work / f"{name}-complete.json"
            raw = run([*cli, "run-sequence", *plans[:2], "--software-command-json", command_json,
                       "--expected-device-id", identity, "--output", output])
            report = json.loads(raw); assert report == json.loads(output.read_bytes())
            assert report["status"] == "completed" and not report["physical_validation"]
            assert [s["state"] for s in report["sequence"]["steps"]] == ["completed", "completed"]
            for step, path in zip(report["sequence"]["steps"], plans):
                assert base64.b64decode(step["context"]["input"]["data"]) == path.read_bytes()
            renders = [i for i,e in enumerate(report["transcript"]) if json.loads(e["request_line"])["type"] == "render"]
            assert len(renders) == 2
            terminal = json.loads(report["transcript"][renders[1]-1]["response_line"])
            first = report["sequence"]["steps"][0]["execution"]
            assert terminal["state"] == "completed" and terminal["execution_id"] == first["execution_id"]
            write(f"{name}-complete.json", report)
            summary["cases"].append({"endpoint": name, "case": "two distinct plans with correlated completion before advancement", "result": "passed"})
            stopped = json.loads(run([python, "-I", work / "stop_after_acceptance.py", plans[2], plans[1],
                                      "--software-command-json", command_json, "--expected-device-id", identity]))
            assert [s["state"] for s in stopped["steps"]] == ["stopped", "not_attempted"]
            assert [json.loads(e["request_line"])["type"] for e in stopped["transcript"]][3:] == ["render", "stop"]
            write(f"{name}-stop.json", stopped)
            summary["cases"].append({"endpoint": name, "case": "installed SDK cooperative Stop; no second render", "result": "passed"})
            log = work / f"{name}-proxy.jsonl"
            lost_command = [str(python), "-I", "-u", str(proxy), command_json, str(log)]
            lost = json.loads(run([*cli, "run-sequence", plans[0], plans[1], plans[0], "--software-command-json", json.dumps(lost_command),
                                  "--expected-device-id", identity, "--output", work / f"{name}-lost.json"], expected=1))
            assert [s["state"] for s in lost["sequence"]["steps"]] == ["completed", "unknown", "not_attempted"]
            actual = [json.loads(line) for line in log.read_text().splitlines()]
            assert sum(e["request"]["type"] == "render" for e in actual) == 2
            assert actual[-1]["actual_reply"]["type"] == "ok"
            assert "response_line" not in lost["transcript"][-1]
            write(f"{name}-lost.json", lost); write(f"{name}-proxy-observations.json", actual)
            summary["cases"].append({"endpoint": name, "case": "second acceptance lost: earlier receipt retained; no third render", "result": "passed"})
            write("result.json", summary)
    summary["result"] = "passed"; write("result.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
