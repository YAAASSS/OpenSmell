"""Sequence behavior proven by actual lifecycle exchanges, never inferred time."""
import json
from types import SimpleNamespace

import pytest

from opensmell.experimental.device_protocol import error_response
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint, SIMULATOR_ID
from opensmell.experimental.rendering import DeviceCommand, RenderingPlan
from opensmell.experimental.sequence import SequenceRunner, SequenceStep


def step(name="a", duration=.1, channel=0):
    return SequenceStep(name, RenderingPlan([DeviceCommand(channel, .25)], duration), {"source": name})


@pytest.fixture
def session():
    def make(fault=None, at=1):
        now = [0]
        endpoint = SimulatedEndpoint(lambda: now[0])
        original = endpoint.exchange
        calls = []
        count = [0]
        def exchange(text):
            request = json.loads(text); calls.append(request)
            if request["type"] == "render":
                count[0] += 1
                if count[0] == at:
                    if fault == "rejected":
                        return json.dumps(error_response("busy", "Explicit software refusal"))
                    if fault == "lost":
                        raise EOFError("Software link lost")
                    if fault == "malformed":
                        return "{"
                    if fault == "missing_id":
                        return '{"type":"ok","protocol_version":"0.1"}'
            if request["type"] == "execution_status" and fault != "never":
                now[0] += 30
            response = json.loads(original(text))
            if count[0] == at:
                if request["type"] == "execution_status":
                    if fault == "wrong_id": response["execution_id"] = "stale"
                    if fault == "stopped": response["state"] = "stopped"
                if request["type"] == "stop" and fault == "stop_running": response["state"] = "running"
                if request["type"] == "render" and fault == "reused_id": response["execution_id"] = "sim-1"
            return json.dumps(response)
        endpoint.exchange = exchange
        client = LifecycleAdapter(endpoint, expected_device_id=SIMULATOR_ID)
        return client, endpoint, calls
    return make


def renders(calls):
    return [c for c in calls if c["type"] == "render"]


def test_two_plans_only_after_correlated_completion_and_passive_copies(session):
    client, endpoint, calls = session()
    checkpoints = []
    first = step(); second = step("b", channel=2)
    runner = SequenceRunner(client, [first, second], on_progress=checkpoints.append)
    first.plan.commands.clear(); first.context["source"] = "changed"
    report = runner.run()
    assert report["status"] == "completed"
    assert [s["state"] for s in report["steps"]] == ["completed"] * 2
    assert report["steps"][0]["context"] == {"source": "a"}
    assert [r["commands"][0]["channel"] for r in renders(calls)] == [0, 2]
    assert [c["type"] for c in calls][3:] == ["render", "execution_status", "render", "execution_status"]
    assert endpoint.closed and not report["physical_validation"]
    assert checkpoints[1]["steps"][0]["state"] == "not_attempted"
    report["steps"][0]["state"] = "unknown"
    assert runner.report["steps"][0]["state"] == "completed"
    count = len(calls)
    with pytest.raises(ValueError, match="consumed"): runner.run()
    assert not runner.request_stop() and len(calls) == count


@pytest.mark.parametrize("fault,state", [("rejected", "rejected"), ("lost", "unknown"),
    ("malformed", "unknown"), ("missing_id", "unknown"), ("wrong_id", "unknown"), ("stopped", "stopped")])
@pytest.mark.parametrize("at", [1, 2])
def test_abort_keeps_earlier_receipts_and_never_sends_later(session, fault, state, at):
    client, endpoint, calls = session(fault, at)
    report = SequenceRunner(client, [step(), step("b"), step("c")]).run()
    assert report["status"] == state and endpoint.closed
    assert len(renders(calls)) == at
    assert [s["state"] for s in report["steps"]] == ["completed"] * (at - 1) + [state] + ["not_attempted"] * (3 - at)
    assert len({s.get("request_id") for s in report["steps"][:at]}) == at


def test_stop_after_acceptance_is_observed_and_cancels_later(session):
    client, endpoint, calls = session()
    def progress(report):
        if report["steps"][0]["state"] == "accepted": runner.request_stop()
    runner = SequenceRunner(client, [step(duration=5), step("b")], on_progress=progress)
    report = runner.run()
    assert report["status"] == "stopped"
    assert [c["type"] for c in calls][3:] == ["render", "stop"]
    assert report["steps"][1]["state"] == "not_attempted"
    assert endpoint.closed


@pytest.mark.parametrize("when", ["before", "pre_send", "between"])
def test_cancel_without_claiming_a_stop(session, when):
    client, endpoint, calls = session()
    def progress(report):
        if when == "pre_send" and report["status"] == "running": runner.request_stop()
        if when == "between" and report["steps"][0]["state"] == "completed": runner.request_stop()
    runner = SequenceRunner(client, [step(), step("b")], on_progress=progress)
    if when == "before": runner.request_stop()
    report = runner.run()
    assert report["status"] == "cancelled"
    assert len(renders(calls)) == int(when == "between")
    assert not any(c["type"] == "stop" for c in calls)


def test_stop_races_completion_and_does_not_claim_stopped(session):
    client, endpoint, calls = session()
    original = endpoint.exchange
    def exchange(text):
        if json.loads(text)["type"] == "stop":
            execution = client.execution
            return json.dumps({"profile": "local-simulator-lifecycle-v1", "execution_id": execution["execution_id"], "state": "completed"})
        return original(text)
    endpoint.exchange = exchange
    def progress(report):
        if report["steps"][0]["state"] == "accepted": runner.request_stop()
    runner = SequenceRunner(client, [step(), step("b")], on_progress=progress)
    report = runner.run()
    assert report["status"] == "cancelled" and report["steps"][0]["state"] == "completed"
    assert len(renders(calls)) == 1


def test_stop_without_terminal_confirmation_is_unknown(session):
    client, endpoint, calls = session("stop_running")
    def progress(report):
        if report["steps"][0]["state"] == "accepted": runner.request_stop()
    runner = SequenceRunner(client, [step(), step("b")], on_progress=progress)
    assert runner.run()["status"] == "unknown"
    assert len(renders(calls)) == 1 and endpoint.closed


def test_all_live_capabilities_checked_before_first_send(session):
    client, endpoint, calls = session()
    report = SequenceRunner(client, [step(), step("unsupported", channel=99)]).run()
    assert report["status"] == "invalid"
    assert not renders(calls) and endpoint.closed
    assert all(s["state"] == "not_attempted" for s in report["steps"])


@pytest.mark.parametrize("where", ["accepted", "completed"])
def test_failing_checkpoint_prevents_next_render(session, where):
    client, endpoint, calls = session()
    def fail(report):
        if report["steps"][0]["state"] == where: raise OSError("Checkpoint storage unavailable")
    report = SequenceRunner(client, [step(), step("b")], on_progress=fail).run()
    assert report["status"] == "unknown" and len(renders(calls)) == 1 and endpoint.closed
    assert report["steps"][0]["state"] == ("unknown" if where == "accepted" else "completed")


def test_never_completed_closes_unknown_no_later_send(session, monkeypatch):
    client, endpoint, calls = session("never")
    now = [0]
    def tick(): now[0] += 1; return now[0]
    monkeypatch.setattr("opensmell.experimental.sequence.time", SimpleNamespace(monotonic=tick, sleep=lambda _: None))
    report = SequenceRunner(client, [step(), step("b")]).run()
    assert report["status"] == "unknown" and len(renders(calls)) == 1 and endpoint.closed
    assert any(c["type"] == "execution_status" for c in calls)


@pytest.mark.parametrize("bad", [[], [step()] * 17, [step(), step()], [step(duration=121)], [SequenceStep("", step().plan)],
    [SequenceStep("a", RenderingPlan([], .1))], [SequenceStep("a", step().plan, {"bad": float("nan")})]])
def test_invalid_sequences_fail_before_ownership(session, bad):
    client, endpoint, calls = session()
    with pytest.raises((ValueError, TypeError)): SequenceRunner(client, bad)
    assert not renders(calls) and not endpoint.closed
    client.close()


def test_cannot_take_over_active_or_unknown_client(session):
    client, endpoint, calls = session()
    client.render(step().plan, request_id="existing")
    with pytest.raises(ValueError, match="active"): SequenceRunner(client, [step()])
    assert not endpoint.closed
    client.close()
    with pytest.raises(ValueError, match="uncertain"): SequenceRunner(client, [step()])


def test_reused_execution_id_aborts_second_send_without_third(session):
    client, endpoint, calls = session()
    original = endpoint.exchange
    def exchange(text):
        request = json.loads(text)
        if request["type"] == "execution_status":
            request["execution_id"] = endpoint.execution["execution_id"]
        reply = json.loads(original(json.dumps(request)))
        if request["type"] in {"render", "execution_status"}: reply["execution_id"] = "reused"
        return json.dumps(reply)
    endpoint.exchange = exchange
    report = SequenceRunner(client, [step(), step("b"), step("c")]).run()
    assert [s["state"] for s in report["steps"]] == ["completed", "unknown", "not_attempted"]
    assert len(renders(calls)) == 2 and endpoint.closed


@pytest.mark.parametrize("where", ["render", "execution_status"])
def test_interrupt_after_possible_acceptance_closes_unknown_without_stop_or_next(session, where):
    client, endpoint, calls = session()
    original = endpoint.exchange
    def exchange(text):
        response = original(text)
        if json.loads(text)["type"] == where: raise KeyboardInterrupt()
        return response
    endpoint.exchange = exchange
    report = SequenceRunner(client, [step(), step("b")]).run()
    assert report["status"] == "unknown" and endpoint.closed
    assert report["steps"][0]["state"] == "unknown" and report["steps"][1]["state"] == "not_attempted"
    assert len(renders(calls)) == 1 and not any(c["type"] == "stop" for c in calls)


def test_presend_checkpoint_is_uncertain_and_can_cancel_before_io(session):
    client, endpoint, calls = session()
    checkpoints = []
    def progress(report):
        checkpoints.append(report)
        if report["steps"][0]["state"] == "unknown": runner.request_stop()
    runner = SequenceRunner(client, [step()], on_progress=progress)
    report = runner.run()
    assert report["status"] == "cancelled" and not renders(calls)
    assert report["steps"][0]["state"] == "not_attempted"
    assert any(c["steps"][0]["state"] == "unknown" for c in checkpoints)
