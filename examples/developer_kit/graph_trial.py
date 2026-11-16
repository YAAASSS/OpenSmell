"""Caller graph -> installed reader/plan -> explicit fixed software trial only."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from cohort_trial import Refusal, identity, snapshot


def execute(args, root, manifest):
    report = {"format": "org.opensmell.experimental.graph-trial", "version": "0.1",
              "experimental": True, "result": "incomplete", "execution": "not_attempted",
              "physical_validation": False, "simulation_requested": args.simulate,
              "request": {"resource_id": args.resource_id, "duration": args.duration},
              "kit_source": manifest["source"], "inputs": {},
              "limits": ["Supplied provenance/capabilities are declarations, not authentication.",
                         "JS inspection is limited; unknown content is preserved, not interpreted.",
                         "Channel mapping is illustrative, not odor reproduction.",
                         "Only fixed kit software endpoints; no physical transport or automatic retry."]}
    try:
        output = args.report.open("x", encoding="utf-8")
    except OSError as error:
        print(json.dumps({"result": "error", "error": str(error)}), file=sys.stderr)
        return 2

    def save():
        encoded = json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
        output.seek(0); output.truncate(); output.write(encoded); output.flush()
        return encoded

    phase = "snapshot"
    code = 1
    try:
        save()
        with tempfile.TemporaryDirectory(prefix="opensmell-caller-graph-") as temporary:
            work = Path(temporary)
            for name, original in (("graph", args.graph), ("profile", args.profile)):
                raw = snapshot(original, 1048576)
                (work / name).write_bytes(raw)
                report["inputs"][name] = {"input": str(original), **identity(raw),
                                         "encoding": "base64", "data": base64.b64encode(raw).decode("ascii")}
            save()

            def command(arguments):
                result = subprocess.run([str(x) for x in arguments], cwd=work, capture_output=True, timeout=30)
                raw = result.stdout or result.stderr
                try:
                    value = json.loads(raw)
                except (ValueError, UnicodeError):
                    value = {"stdout": result.stdout.decode("utf-8", "replace"), "stderr": result.stderr.decode("utf-8", "replace")}
                if result.returncode == 1:
                    raise Refusal(phase, value)
                if result.returncode:
                    raise RuntimeError(f"{phase}: exit {result.returncode}: {value}")
                return value

            def cli(*arguments):
                return command([sys.executable, "-I", "-m", "opensmell", *arguments])

            phase = "validation"
            report["validation"] = cli("validate", work / "graph", "--json")
            phase = "javascript_inspection"
            report["javascript_inspection"] = command(["node", root / "inspect.cjs", work / "graph", work / "transfer"])
            if (work / "transfer").read_bytes() != (work / "graph").read_bytes():
                raise ValueError("JavaScript transfer changed graph bytes")
            report["transfer_byte_identity"] = True
            phase = "planning"
            report["plan"] = cli("plan", work / "transfer", "--profile", work / "profile",
                                 "--resource-id", args.resource_id, "--duration", args.duration)
            report["result"] = "planned"
            save()
            if args.simulate:
                phase = "simulation_preflight"
                if args.duration != 5:
                    raise Refusal(phase, {"error": "Fixed completion/Stop/disconnect walkthrough requires --duration 5"})
                cli("plan", work / "transfer", "--profile", work / "profile", "--resource-id", args.resource_id, "--duration", .1)
                if any(c["channel"] not in (0, 1, 2) or not 0 <= c["intensity"] <= 1 for c in report["plan"]["plan"]["commands"]):
                    raise Refusal(phase, {"error": "Fixed software endpoints require channels0–2 intensity0–1"})
                plan_file = work / "plan.json"
                plan_file.write_text(json.dumps(report["plan"]["plan"]))
                report["software_observations"] = {}
                report["execution"] = "unknown_if_interrupted"
                save()
                for endpoint, options in (("python", []), ("node", ["--node", root / "software/device.cjs"])):
                    phase = "python_client_" + endpoint
                    report["attempting"] = phase; save()
                    value = command([sys.executable, "-I", "-m", "opensmell.experimental.lifecycle_demo",
                                     "--graph", work / "transfer", "--profile", work / "profile", "--resource-id", args.resource_id, *options])
                    report["software_observations"][phase] = value; save()
                    if ([value["results"][k]["state"] for k in ("completion", "stop", "disconnect")] != ["completed", "stopped", "unknown"]
                            or value["physical_validation"] is not False):
                        raise ValueError("Unexpected Python lifecycle observations")
                for endpoint, selected, device_id in (
                    ("node", ["node", str(root / "software/device.cjs")], "opensmell-node-simulator-001"),
                    ("python", [sys.executable, "-I", "-u", str(root / "software/python_device.py")], "opensmell-local-simulator-001"),
                ):
                    phase = "javascript_client_" + endpoint
                    report["attempting"] = phase; save()
                    value = command(["node", root / "try_client.cjs", json.dumps(selected), device_id, plan_file])
                    report["software_observations"][phase] = value; save()
                    if ([value[k]["state"] for k in ("completed", "stopped", "unknown")] != ["completed", "stopped", "unknown"]
                            or value["physical_validation"] is not False):
                        raise ValueError("Unexpected JavaScript lifecycle observations")
                for name, observed in report["software_observations"].items():
                    states = ([observed["results"][key]["state"] for key in ("completion", "stop", "disconnect")]
                              if name.startswith("python") else [observed[key]["state"] for key in ("completed", "stopped", "unknown")])
                    if states != ["completed", "stopped", "unknown"] or observed["physical_validation"] is not False:
                        raise ValueError("Software walkthrough observations did not match the declared proof")
                report.pop("attempting", None)
                report.update(result="software_verified", execution="software_observed")
            code = 0
    except (Refusal, ValueError, OSError, RuntimeError, subprocess.SubprocessError, KeyError, TypeError) as error:
        attempted = report["execution"] != "not_attempted"
        report.update(result="error" if attempted or not isinstance(error, Refusal) else "rejected",
                      error={"phase": phase, "detail": getattr(error, "response", str(error))})
        if attempted:
            report["execution"] = "unknown"
        code = 3 if report["result"] == "rejected" else 1
    finally:
        encoded = save(); output.close()
    print(encoded, end="")
    return code
