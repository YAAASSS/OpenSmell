"""Caller-owned cohort workflow; passive by default, fixed software endpoints only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)}


def snapshot(path, limit):
    with path.open("rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Input exceeds {limit} bytes: {path}")
    return data


class Refusal(Exception):
    def __init__(self, phase, response):
        self.phase, self.response = phase, response


def execute(args, root, manifest):
    report = {"format": "org.opensmell.experimental.cohort-trial", "version": "0.1",
              "experimental": True, "physical_validation": False,
              "result": "incomplete", "simulation_requested": args.simulate,
              "execution": "not_established", "requested_records": args.rows,
              "kit_source": manifest["source"], "records": [],
              "limits": ["OdorNet-shaped CSV only; source/license are declarations, not authentication.",
                         "Selected raw cells and unknown columns are retained; full CSV bytes are not embedded.",
                         "Supplied capabilities and channel meanings are illustrative; no measured odor or hardware evidence.",
                         "Simulation uses fixed trusted repository software endpoints, not arbitrary commands.",
                         "An incomplete or failed simulation must not be retried automatically."]}
    # Reserve a new report before launching any subprocess. A crash leaves an
    # explicit incomplete marker; another invocation cannot silently overwrite it.
    try:
        output = args.report.open("x", encoding="utf-8") if args.report else None
    except OSError as error:
        print(json.dumps({"result": "error", "error": str(error)}), file=sys.stderr)
        return 2

    def save():
        encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if output:
            output.seek(0); output.truncate(); output.write(encoded); output.flush()
        return encoded

    code = 0
    try:
        save()
        with tempfile.TemporaryDirectory(prefix="opensmell-caller-cohort-") as directory:
            work = Path(directory)
            report["inputs"] = {}
            for name, original, limit in (("csv", args.csv, 8 * 1048576),
                                          ("source", args.source, 1048576),
                                          ("profile", args.profile, 1048576)):
                data = snapshot(original, limit)
                (work / name).write_bytes(data)
                report["inputs"][name] = {"input": str(original), **identity(data)}

            def command(arguments, phase, accepted=(0,)):
                result = subprocess.run([str(x) for x in arguments], cwd=work,
                                        capture_output=True, timeout=30)
                raw = result.stdout or result.stderr
                try:
                    value = json.loads(raw) if raw.strip() else None
                except (ValueError, UnicodeError):
                    value = {"stdout": result.stdout.decode("utf-8", "replace"),
                             "stderr": result.stderr.decode("utf-8", "replace")}
                if result.returncode == 1 and result.returncode not in accepted:
                    raise Refusal(phase, value)
                if result.returncode not in accepted:
                    raise RuntimeError(f"{phase}: exit {result.returncode}: {value}")
                return value

            def cli(phase, *arguments, accepted=(0,)):
                return command([sys.executable, "-I", "-m", "opensmell", *arguments], phase, accepted)

            cli("import", "import-odornet-batch", work / "csv", "--source", work / "source",
                "--rows", *args.rows, "--output", work / "batch.json", accepted=(0, 3))
            report["batch"] = json.loads((work / "batch.json").read_bytes())
            report["source_kind"] = report["batch"]["source"]["kind"]
            ready = []
            # Finish all passive planning before any software endpoint is launched.
            for entry in report["batch"]["results"]:
                row = entry["data_record"]
                record = {"row": row, "import_status": entry["status"],
                          "status": "import_rejected", "execution": "not_attempted"}
                report["records"].append(record)
                if entry["status"] != "accepted":
                    record["error"] = entry["error"]
                    continue
                core, graph, recovered = (work / f"{row}-{suffix}" for suffix in ("core", "graph", "recovered"))
                try:
                    cli("extract", "extract-csv-record", work / "batch.json", "--row", row, "--output", core)
                    cli("bridge", "bridge-core", core, "--output", graph)
                    record["graph"] = json.loads(graph.read_bytes())
                    record["graph_identity"] = identity(graph.read_bytes())
                    rid = record["graph"]["org.opensmell.experimental.core-import"]["primary_resource_id"]
                    cli("validate", "validate", graph, "--json")
                    cli("recovery", "extract-core", graph, "--output", recovered)
                    if recovered.read_bytes() != core.read_bytes():
                        raise RuntimeError("Core recovery changed original bytes")
                    record["core_identity"] = identity(core.read_bytes())
                    record["plan"] = cli("planning", "plan", graph, "--profile", work / "profile",
                                         "--resource-id", rid, "--duration", "5")
                    record["status"] = "planned"
                    if args.simulate:
                        # The demonstration trials use 0.1s completion/disconnect
                        # and 5s Stop. Check both durations and fixed 3ch support.
                        cli("simulation_preflight", "plan", graph, "--profile", work / "profile",
                            "--resource-id", rid, "--duration", "0.1")
                        if any(c["channel"] not in (0, 1, 2) or not 0 <= c["intensity"] <= 1
                               for c in record["plan"]["plan"]["commands"]):
                            raise Refusal("simulation_preflight", {"error": "Fixed software endpoints support channels 0–2 at intensity 0–1"})
                        ready.append((record, graph, rid))
                except Refusal as error:
                    record.update(status=error.phase + "_rejected", error=error.response)

            if args.simulate:
                for record, graph, rid in ready:
                    # Persist uncertainty before entering an execution path.
                    report["execution"] = "software_attempted"
                    record["execution"] = "unknown_if_interrupted"
                    record["software_observations"] = {}
                    save()
                    try:
                        transferred = work / f"{record['row']}-transfer"
                        record["javascript_inspection"] = command(["node", root / "inspect.cjs", graph, transferred], "javascript_inspection")
                        if transferred.read_bytes() != graph.read_bytes():
                            raise RuntimeError("JavaScript transfer changed graph bytes")
                        plan_file = work / f"{record['row']}-plan.json"
                        plan_file.write_text(json.dumps(record["plan"]["plan"]))
                        for endpoint, options in (("python", []), ("node", ["--node", root / "software/device.cjs"])):
                            record["software_observations"]["python_client_" + endpoint] = command(
                                [sys.executable, "-I", "-m", "opensmell.experimental.lifecycle_demo",
                                 "--graph", transferred, "--profile", work / "profile", "--resource-id", rid, *options], "python_client")
                            save()
                        for endpoint, selected, device_id in (
                            ("node", ["node", str(root / "software/device.cjs")], "opensmell-node-simulator-001"),
                            ("python", [sys.executable, "-I", "-u", str(root / "software/python_device.py")], "opensmell-local-simulator-001"),
                        ):
                            record["software_observations"]["javascript_client_" + endpoint] = command(
                                ["node", root / "try_client.cjs", json.dumps(selected), device_id, plan_file], "javascript_client")
                            save()
                        record.update(status="software_verified", execution="software_observed")
                    except (Refusal, RuntimeError, OSError, subprocess.SubprocessError) as error:
                        record.update(status="software_failed", execution="unknown", error=str(error))
                        # Never retry; leave later prepared records unattempted.
                        report["result"] = "error"
                        code = 1
                        break
            report["counts"] = {status: sum(r["status"] == status for r in report["records"])
                                for status in sorted({r["status"] for r in report["records"]})}
            if report["result"] != "error":
                good = {"planned", "software_verified"}
                report["result"] = "complete" if all(r["status"] in good for r in report["records"]) else "partial"
                code = 0 if report["result"] == "complete" else 3
            if report["execution"] == "not_established":
                report["execution"] = "not_attempted"
    except (Refusal, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(result="error", error={"phase": getattr(error, "phase", "workflow"),
                                             "detail": getattr(error, "response", str(error))})
        if report["execution"] == "not_established":
            report["execution"] = "not_attempted"
        code = 2 if isinstance(error, OSError) else 1
    finally:
        encoded = save()
        if output:
            output.close()
    print(encoded, end="")
    return code
