"""Bounded process startup without relaxing live request deadlines or retrying."""
import json
import math
import shutil
import sys

import pytest

from opensmell.experimental.process_transport import ProcessTransport


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js required")
def test_evidence_capture_with_slow_node_startup(tmp_path, monkeypatch):
    # Exercise the same HTTP capture that failed on CI, with a deterministic
    # bootstrap longer than the normal two-second exchange deadline.
    from apps.local_demo import process_transport
    from tools.demo_execution_evidence import capture

    wrapper = tmp_path / "slow node.cjs"
    wrapper.write_text(
        f"setTimeout(() => require({json.dumps(str(process_transport.EXAMPLE))}), 2200);\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(process_transport, "EXAMPLE", wrapper)
    result = capture(tmp_path / "capture")
    assert not result["errors"]
    assert [report["state"] for report in result["reports"]] == [
        "unknown", "stopped", "completed",
    ]


@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan, True, "5"])
def test_invalid_startup_timeout(value):
    with pytest.raises(ValueError, match="Startup timeout"):
        ProcessTransport([sys.executable], startup_timeout=value)


def test_startup_allowance_is_used_once_and_commands_are_not_retried(tmp_path):
    requests = tmp_path / "requests.jsonl"
    program = """
import sys, time
with open(sys.argv[1], 'w') as log:
    for delay in (0.2, 0.4):
        line = sys.stdin.readline()
        log.write(line)
        log.flush()
        time.sleep(delay)
        print('{}', flush=True)
"""
    transport = ProcessTransport(
        [sys.executable, "-u", "-c", program, str(requests)],
        timeout=0.1, startup_timeout=2,
    )
    try:
        # Local validation must not consume the first-response allowance.
        with pytest.raises(ValueError):
            transport.exchange("not JSON")
        assert json.loads(transport.exchange('{"request":1}')) == {}
        assert transport.last_exchange["phase"] == "startup"
        assert transport.last_exchange["outcome"] == "response"
        with pytest.raises(TimeoutError, match="link closed"):
            transport.exchange('{"request":2}')
        assert transport.process.poll() is not None
        assert transport.last_exchange["phase"] == "exchange"
        assert transport.last_exchange["deadline_seconds"] == 0.1
        assert transport.last_exchange["request_written_seconds"] is not None
        with pytest.raises(OSError, match="closed"):
            transport.exchange('{"request":3}')
        assert requests.read_text().splitlines() == ['{"request":1}', '{"request":2}']
    finally:
        transport.close()


def test_startup_deadline_still_closes_and_reaps_child():
    transport = ProcessTransport(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout=2, startup_timeout=0.1,
    )
    try:
        with pytest.raises(TimeoutError, match="link closed") as error:
            transport.exchange("{}")
        assert '"phase": "startup"' in str(error.value)
        assert transport.last_exchange["deadline_seconds"] == 0.1
        assert transport.last_exchange["elapsed_seconds"] >= 0.1
        assert transport.last_exchange["child_returncode"] is None
        assert transport.process.poll() is not None
        with pytest.raises(OSError, match="closed"):
            transport.exchange("{}")
    finally:
        transport.close()
