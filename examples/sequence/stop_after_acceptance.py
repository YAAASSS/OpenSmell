"""Installed SDK consumer: cooperative Stop after the first software acceptance.

Explicit trusted child process only, no serial/GPIO. Run from any directory.
This is a deterministic Stop demonstration, not an emergency-stop facility.
"""
import argparse
import json
from pathlib import Path

from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.process_transport import ProcessTransport
from opensmell.experimental.sequence import SequenceRunner
from opensmell.experimental.software_sequence import prepare_steps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+")
    parser.add_argument("--software-command-json", required=True)
    parser.add_argument("--expected-device-id", required=True)
    args = parser.parse_args()
    if not 2 <= len(args.plans) <= 16:
        parser.error("Supply 2–16 explicit plans; use a 5-second first plan for this Stop demonstration")
    inputs = []
    for name in args.plans:
        with Path(name).open("rb") as source:
            inputs.append(source.read(8 * 1048576 + 1))
        if sum(map(len, inputs)) > 16 * 1048576:
            parser.error("Combined plan artifacts exceed 16 MiB")
    steps = prepare_steps(inputs)
    if steps[0].plan.duration != 5:
        parser.error("This demonstration requires an explicit 5-second first plan")
    transcript = []
    transport = ProcessTransport(json.loads(args.software_command_json), startup_timeout=5)
    class Recorded:
        def exchange(self, request):
            entry = {"request_line": request + "\n"}; transcript.append(entry)
            reply = transport.exchange(request); entry["response_line"] = reply
            return reply
        def close(self): transport.close()
    try:
        with LifecycleAdapter(Recorded(), expected_device_id=args.expected_device_id) as client:
            def progress(report):
                if report["steps"][0]["state"] == "accepted":
                    runner.request_stop()
            runner = SequenceRunner(client, steps, on_progress=progress)
            report = runner.run()
            report["transcript"] = transcript
            print(json.dumps(report, allow_nan=False))
            return 0 if report["status"] == "stopped" and all(s["state"] == "not_attempted" for s in report["steps"][1:]) else 1
    finally:
        transport.close()


if __name__ == "__main__":
    raise SystemExit(main())
