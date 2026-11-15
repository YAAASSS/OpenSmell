"""Fresh installed CLI -> actual-sketch native stdin. No serial/hardware access."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--host", type=Path, required=True, help="Explicit trusted native harness executable")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    wheel, host = args.wheel.resolve(strict=True), args.host.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="opensmell-installed-frame-") as directory:
        work = Path(directory)
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(work / "venv")
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        def run(command, expected=0, data=None):
            result = subprocess.run([str(x) for x in command], input=data, cwd=work, env=env,
                                    capture_output=True, timeout=30)
            if result.returncode != expected:
                raise RuntimeError(f"{command}: {result.stdout!r} {result.stderr!r}")
            return result.stdout
        run([python, "-m", "pip", "install", "--no-deps", "--no-index", "--ignore-installed", wheel])
        location = run([python, "-I", "-c", "import opensmell; print(opensmell.__file__)"]).decode().strip()
        if not Path(location).is_relative_to(work / "venv"):
            raise AssertionError("Import did not resolve to installed wheel")
        def cli(*arguments, expected=0, data=None):
            return run([python, "-I", "-m", "opensmell", *arguments], expected, data)
        target = (root / "hardware/esp32/led_capabilities.json").read_bytes()
        (work / "target.json").write_bytes(target)
        graph = root / "examples/multisource_diphenyl_ether.osmell"
        frames = []
        replay_sizes = []
        for mapper, rid, pwm in (
            ("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", [64,153,0]),
            ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857", [120,46,38]),
        ):
            raw = cli("plan", graph, "--profile", root / f"examples/offline_{mapper}_profile.json",
                      "--resource-id", rid, "--duration", "5")
            exported = json.loads(cli("encode-frame", "-", "--capabilities", "target.json", data=raw))
            assert exported["acceptance"] == "not_observed" and exported["transport"] == "not_opened"
            cli("encode-frame", "-", "--capabilities", "target.json", "--output", f"{mapper}.json", data=raw)
            saved = (work / f"{mapper}.json").read_bytes()
            cli("encode-frame", "-", "--capabilities", "target.json", "--output", f"{mapper}.json", data=raw, expected=2)
            assert saved == (work / f"{mapper}.json").read_bytes()
            altered = json.loads(raw); altered["plan"]["duration"] = 31
            cli("encode-frame", "-", "--capabilities", "target.json", data=json.dumps(altered).encode(), expected=1)
            transcript_path = work / f"{mapper}-native.json"
            replayed = json.loads(cli("replay-frame", f"{mapper}.json", "--native-host", host,
                                      "--output", transcript_path))
            assert replayed["status"] == replayed["acceptance"] == "accepted"
            assert replayed["physical_validation"] is False and replayed["execution"] == "not_observed"
            assert replayed["fake_outputs"]["after"] == replayed["fake_outputs"]["after_negative_control"] == pwm
            assert replayed["fake_outputs"]["after_duration"] == [0,0,0]
            selected = next(x for x in replayed["transcript"] if x["role"] == "selected_frame")
            assert selected["request_line"] == exported["frame"]["line"]
            saved_transcript = transcript_path.read_bytes()
            cli("replay-frame", f"{mapper}.json", "--native-host", host, "--output", transcript_path, expected=2)
            assert transcript_path.read_bytes() == saved_transcript
            replay_sizes.append(len(replayed["transcript"]))
            # A valid export for a differently described target must stop after
            # native negotiation, with no selected command in the transcript.
            other = json.loads(target); other["device_id"] = "other-target"
            (work / "other-target.json").write_text(json.dumps(other))
            cli("encode-frame", "-", "--capabilities", "other-target.json", "--output", f"{mapper}-other.json", data=raw)
            mismatched = json.loads(cli("replay-frame", f"{mapper}-other.json", "--native-host", host,
                                       "--output", f"{mapper}-mismatch.json", expected=3))
            assert mismatched["status"] == "incompatible" and mismatched["acceptance"] == "not_attempted"
            assert not any(x["role"] == "selected_frame" for x in mismatched["transcript"])
            corrupt = json.loads((work / f"{mapper}.json").read_bytes()); corrupt["frame"]["line"] += "!pins\n"
            (work / f"{mapper}-corrupt.json").write_text(json.dumps(corrupt))
            cli("replay-frame", f"{mapper}-corrupt.json", "--native-host", host,
                "--output", f"{mapper}-invalid.json", expected=1)
            frames.append((exported["frame"]["line"], pwm))
        lines = ['{"protocol_version":"0.1","type":"get_capabilities"}', '!pins']
        for frame, _ in frames:
            lines += [frame.rstrip('\n'), '!pins',
                      '{"protocol_version":"0.1","type":"render","duration":31,"commands":[{"channel":0,"intensity":1}]}',
                      '!pins', '!advance 5000', '!pins']
        replies = [json.loads(x) for x in run([host], data=('\n'.join(lines)+'\n').encode()).splitlines()]
        assert len(replies) == len(lines)
        assert replies[0] == json.loads(target)
        assert replies[1] == {"host_pwm":[0,0,0]}
        for offset, (_, pwm) in enumerate(frames):
            r = replies[2+offset*6:8+offset*6]
            assert r[0] == {"protocol_version":"0.1","type":"ok"}
            assert r[1] == r[3] == {"host_pwm":pwm}
            assert r[2]["type"] == "error" and r[2]["code"] == "invalid_plan"
            assert r[4] == {"host":"advanced"}
            assert r[5] == {"host_pwm":[0,0,0]}
        print(json.dumps({"result":"passed", "installed_cli":True, "firmware":"actual sketch in native harness",
                          "mappers":["semantic","perceptual"], "observations":len(replies),
                          "acceptance":"observed_in_native_harness", "replay_transcript_observations":replay_sizes,
                          "supplied_target_mismatch_pre_send":True, "physical_validation":False}))


if __name__ == "__main__":
    main()
