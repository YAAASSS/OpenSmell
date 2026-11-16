"""Fresh installed perceptual CSV -> JS bytes -> plan -> optional native sketch.

No dataset fetch or physical transport. Explicit trusted host argument only.
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
    parser.add_argument("--host", type=Path, help="Explicit trusted native sketch harness; never a serial device")
    parser.add_argument("--evidence-directory", type=Path, help="New directory for passive proof artifacts; never overwrite")
    parser.add_argument("--published-preparation", type=Path, help="Explicit directory produced by the pinned published-reference preparation example")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    wheel = args.wheel.resolve(strict=True)
    host = args.host.resolve(strict=True) if args.host else None
    published = args.published_preparation.resolve(strict=True) if args.published_preparation else None
    expected_csv_hash = "57e9cd4b41bc69d8813726ae80442b177ae52b4e6100ac56872c546db94f991c"
    if published:
        if hashlib.sha256((published / "observations.csv").read_bytes()).hexdigest() != expected_csv_hash:
            raise ValueError("Published preparation does not match the documented selected CSV")
        declaration = json.loads((published / "source.json").read_bytes())
        if (declaration["original"]["sha256"] != "efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62"
                or declaration["kind"] != "dataset" or declaration["prepared_csv"]["sha256"] != expected_csv_hash):
            raise ValueError("Published source declaration does not identify this trial")
    evidence = args.evidence_directory.resolve() if args.evidence_directory else None
    if evidence:
        evidence.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="opensmell-perceptual-installed-") as directory:
        work = Path(directory)
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(work / "venv")
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        def run(command, expected=0, data=None, cwd=work):
            result = subprocess.run([str(x) for x in command], input=data, cwd=cwd, env=env, capture_output=True, timeout=60)
            if result.returncode != expected:
                raise RuntimeError(f"{command}: {result.returncode} {result.stdout!r} {result.stderr!r}")
            return result.stdout
        def cli(*arguments, expected=0, data=None):
            return run([python, "-I", "-m", "opensmell", *arguments], expected, data)
        run([python, "-m", "pip", "install", "--no-deps", "--no-index", "--ignore-installed", wheel])
        location = run([python, "-I", "-c", "import opensmell; print(opensmell.__file__)"]).decode().strip()
        assert Path(location).is_relative_to(work / "venv")
        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("npm is required for the installed reader proof")
        packed = json.loads(run([npm, "pack", "--ignore-scripts", "--json", "--pack-destination", work],
                                cwd=root / "packages/javascript"))[0]
        (work / "package.json").write_text('{"private":true}')
        run([npm, "install", "--offline", "--ignore-scripts", "--no-audit", "--no-fund", "--package-lock=false", work / packed["filename"]])
        (work / "inspect.cjs").write_bytes((root / "examples/developer_kit/inspect.cjs").read_bytes())
        for name, original in (("caller.csv", "examples/synthetic_keller.csv"),
                               ("source.json", "examples/synthetic_keller_source.json"),
                               ("profile.json", "examples/offline_perceptual_profile.json"),
                               ("target.json", "hardware/esp32/led_capabilities.json")):
            (work / name).write_bytes((root / original).read_bytes())
        if published:
            (work / "caller.csv").write_bytes((published / "observations.csv").read_bytes())
            (work / "source.json").write_bytes((published / "source.json").read_bytes())
        refusals = []
        cases = ((1, {0: .26, 1: .38, 2: .89}), (2, None), (3, None)) if published else (
            (1, {0: .26, 1: 0, 2: .89}), (2, {0: .8, 1: .2}), (3, None))
        for row, expected in cases:
            graph_path = work / f"observation-{row}.osmell"
            cli("import-keller", "caller.csv", "--source", "source.json", "--row", str(row), "--output", graph_path)
            raw = graph_path.read_bytes()
            cli("import-keller", "caller.csv", "--source", "source.json", "--row", str(row), "--output", graph_path, expected=2)
            assert graph_path.read_bytes() == raw
            report = json.loads(run(["node", "inspect.cjs", graph_path, f"transferred-{row}.osmell"]))
            # This reader deliberately leaves categorical schemes opaque and
            # reports the absent Annotation branch; never claim full validation.
            assert report["status"] == "partial"
            assert {x["code"] for x in report["diagnostics"]} == {"opaque_scheme", "incomplete_branches", "scope"}
            assert len(report["references"]) == 3 and all(x["resolved"] for x in report["references"])
            (work / f"reader-{row}.json").write_text(json.dumps(report, indent=2) + "\n")
            assert (work / f"transferred-{row}.osmell").read_bytes() == raw
            cli("validate", f"transferred-{row}.osmell")
            graph = json.loads(raw)
            context = graph["org.opensmell.experimental.perceptual-csv-import"]
            assert context["source"]["kind"] == ("dataset" if published else "synthetic")
            assert context["csv_sha256"] == hashlib.sha256((work / "caller.csv").read_bytes()).hexdigest()
            assert context["raw_record"]["Odor dilution"] == (("1/100,000" if published else "1/10,000") if row == 2 else "1/1,000")
            observation = next(x for x in graph["resources"] if x["id"] == context["primary_resource_id"])
            if row == 1:
                values = {m["property"]: m for m in observation["results"][-1]["data"]["measurements"]}
                if published:
                    assert values["grass"]["value"] == 38 and values["pleasantness"]["value"] == 80
                    assert "familiarity" not in values  # source scale ambiguity is deliberately excluded
                else:
                    assert values["grass"]["value"] == 0 and "pleasantness" not in values
                assert all(m["unit"] == "rating" and m["scale"] == {"min": 0, "max": 100} for m in values.values())
            plan_raw = cli("plan", f"transferred-{row}.osmell", "--profile", "profile.json",
                           "--resource-id", observation["id"], "--duration", "5", expected=0 if expected is not None else 1)
            if expected is None:
                assert context["measurement_count"] == (3 if published and row == 3 else 0)
                refusals.append({"prepared_record": row, "report": json.loads(plan_raw)})
                continue
            plan = json.loads(plan_raw)
            assert {c["channel"]: c["intensity"] for c in plan["plan"]["commands"]} == expected
            (work / f"plan-{row}.json").write_bytes(plan_raw)
            cli("encode-frame", f"plan-{row}.json", "--capabilities", "target.json", "--output", f"frame-{row}.json")
        cli("import-keller", "caller.csv", "--source", "source.json", "--row", "4", "--output", "invalid.osmell", expected=1)
        assert not (work / "invalid.osmell").exists()
        # Artifact is self-contained for frame replay, not for CSV recovery.
        for name in ("caller.csv", "source.json", "profile.json", "target.json"):
            (work / name).unlink()
        native = []
        if host:
            for row, pwm in (((1, [66, 97, 227]),) if published else ((1, [66, 0, 227]), (2, [204, 51, 0]))):
                replay = json.loads(cli("replay-frame", f"frame-{row}.json", "--native-host", host,
                                        "--output", f"native-{row}.json"))
                assert replay["status"] == replay["acceptance"] == "accepted"
                assert replay["execution"] == "not_observed" and replay["physical_validation"] is False
                assert replay["fake_outputs"]["after"] == replay["fake_outputs"]["after_negative_control"] == pwm
                assert replay["fake_outputs"]["after_duration"] == [0, 0, 0]
                exported = json.loads((work / f"frame-{row}.json").read_bytes())
                selected = next(x for x in replay["transcript"] if x["role"] == "selected_frame")
                assert selected["request_line"] == exported["frame"]["line"]
                native.append({"record": row, "status": replay["status"], "fake_pwm": pwm,
                               "transcript_exchanges": len(replay["transcript"])})
        result = {"result": "passed", "source_kind": "dataset" if published else "synthetic", "installed_outside_checkout": True,
                  "javascript_transfer": "installed local package; partial inspection, opaque categories; exact bytes",
                  "selected_records": [1, 2, 3], "planned_records": [1] if published else [1, 2],
                  "unmeasured_plan_refused": 2 if published else 3,
                  "unmapped_plan_refused": 3 if published else None,
                  "invalid_or_absent_import_refused": 4, "preparation_files_deleted_before_native": True,
                  "native": native, "physical_validation": False}
        result["planning_refusals"] = refusals
        if published:
            result["source"] = declaration
        if evidence:
            names = [f"observation-{r}.osmell" for r in (1, 2, 3)]
            names += [f"reader-{r}.json" for r in (1, 2, 3)]
            names += [f"{kind}-{r}.json" for kind in ("plan", "frame") for r in ([1] if published else [1, 2])]
            if host:
                names += [f"native-{r}.json" for r in ([1] if published else [1, 2])]
            for name in names:
                (evidence / name).write_bytes((work / name).read_bytes())
            (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
