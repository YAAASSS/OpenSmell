"""Local application hardware boundary. All devices are software doubles."""

from copy import deepcopy
from dataclasses import asdict
import http.client
import json
import sys
import threading
from types import SimpleNamespace

import pytest

from apps.local_demo.__main__ import create_server
from apps.local_demo.hardware import EXPECTED_DEVICE_ID, HardwareError, HardwareService, open_transport
from apps.local_demo.preview_store import PreviewStore, StalePreview
from apps.local_demo.service import FIXTURE, preview
from opensmell.experimental.device_capabilities import DeviceCapabilities, DeviceChannelCapability
from opensmell.experimental.device_protocol import capabilities_response, hello_response, ok_response, error_response


def capabilities(**kwargs):
    return DeviceCapabilities(**{
        "device_id": EXPECTED_DEVICE_ID,
        "channels": [DeviceChannelCapability(channel=i) for i in range(3)],
        "min_duration": 0.1, "max_duration": 30, **kwargs,
    })


class FakeTransport:
    def __init__(self, replies=None, *, caps=None):
        self.replies = list(replies if replies is not None else [
            hello_response(EXPECTED_DEVICE_ID), capabilities_response(caps or capabilities()), ok_response(),
        ])
        self.messages = []
        self.closed = 0
        self.entered = self.release = None

    def exchange(self, message):
        self.messages.append(json.loads(message))
        if self.entered is not None and self.messages[-1]["type"] == "render":
            self.entered.set()
            assert self.release.wait(5), "Test did not release the simulated exchange"
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply) if isinstance(reply, dict) else reply

    def close(self):
        self.closed += 1


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def setup_hardware(transport=None, *, clock=None):
    transport = transport or FakeTransport()
    opened = []

    def factory(port):
        opened.append(port)
        return transport

    hardware = HardwareService(factory=factory, available=lambda: True,
                               ports=lambda: [{"port": "SIMULATED", "description": "Software test only"}],
                               clock=clock or Clock(), simulated=True)
    return hardware, transport, opened


def make_preview(store, *, revision=1, client="test-browser-session", **kwargs):
    payload = {"client_id": client, "revision": revision}
    store.begin(payload)
    result = preview(FIXTURE.read_text(encoding="utf-8"), **kwargs)
    return store.publish(payload, result), result


def test_enumeration_preview_and_status_never_open_a_port():
    hardware, transport, opened = setup_hardware()
    assert hardware.status()["connection"] == "disconnected"
    assert hardware.ports()["ports"][0]["port"] == "SIMULATED"
    make_preview(PreviewStore())
    assert opened == transport.messages == []


def test_missing_serial_keeps_preview_available():
    hardware = HardwareService(available=lambda: False, factory=lambda _: pytest.fail("Port opened"))
    assert "pip install" in hardware.status()["message"]
    assert hardware.ports()["ports"] == []
    assert make_preview(PreviewStore())[1]["plans"]["semantic"]["commands"]
    with pytest.raises(HardwareError, match="PySerial"):
        hardware.connect("COM3")


def test_connect_displays_received_identity_capabilities_and_closes():
    caps = capabilities(min_duration=1, max_duration=12)
    hardware, transport, opened = setup_hardware(FakeTransport(caps=caps))
    result = hardware.connect(" SIMULATED ")
    assert result["device_id"] == EXPECTED_DEVICE_ID
    assert result["capabilities"] == asdict(caps)
    assert result["connection"] == "connected"
    for revision in range(1, 4):
        make_preview(PreviewStore(), revision=revision)
        hardware.status()
    assert opened == ["SIMULATED"]
    assert [m["type"] for m in transport.messages] == ["hello", "get_capabilities"]
    result = hardware.disconnect()
    assert result["connection"] == "disconnected"
    assert "does not stop" in result["message"]
    hardware.close()
    assert transport.closed == 1
    assert len(transport.messages) == 2


@pytest.mark.parametrize("replies", [
    [TimeoutError("No response")], ["not json"],
    [hello_response("other"), capabilities_response(capabilities(device_id="other"))],
    [hello_response(EXPECTED_DEVICE_ID), capabilities_response(capabilities(device_id="other"))],
    [hello_response(EXPECTED_DEVICE_ID), {"protocol_version": "0.1", "type": "capabilities"}],
    [hello_response(EXPECTED_DEVICE_ID), TimeoutError("No capabilities")],
])
def test_failed_handshake_closes_and_never_renders_or_retries(replies):
    hardware, transport, opened = setup_hardware(FakeTransport(replies))
    with pytest.raises(HardwareError, match="Connection failed"):
        hardware.connect("SIMULATED")
    assert transport.closed == 1
    assert opened == ["SIMULATED"]
    assert all(m["type"] != "render" for m in transport.messages)
    assert hardware.status()["capabilities"] is None
    assert hardware.status()["connection"] == "disconnected"


def test_busy_or_missing_port_is_diagnosed_without_retry():
    calls = []

    def fail(port):
        calls.append(port)
        raise OSError("Access denied / port busy")

    hardware = HardwareService(factory=fail, available=lambda: True)
    with pytest.raises(HardwareError, match="close any serial monitor"):
        hardware.connect("COM_TEST")
    assert calls == ["COM_TEST"]
    assert hardware.status()["connection"] == "disconnected"


@pytest.mark.parametrize("port", [None, "", "   ", "COM3\n", "x" * 257])
def test_bad_port_never_opens(port):
    hardware, _, opened = setup_hardware()
    with pytest.raises(HardwareError, match="valid serial port"):
        hardware.connect(port)
    assert opened == []


@pytest.mark.parametrize("policy", ["semantic", "perceptual"])
def test_send_is_exactly_the_trusted_preview_and_single_use(policy):
    clock = Clock()
    hardware, transport, _ = setup_hardware(clock=clock)
    hardware.connect("SIMULATED")
    store = PreviewStore()
    ticket, result = make_preview(store, policy=policy)
    assert hardware.check(store, ticket)["ready"] is True
    assert len(transport.messages) == 2
    expected = deepcopy(result["plans"][policy])
    # Browser mutations to the returned document cannot alter the server cache.
    result["plans"][policy]["commands"][0]["intensity"] = 0.123
    status = hardware.send(store, ticket)
    assert status["execution"]["state"] == "accepted"
    assert status["execution"]["response"] == ok_response()
    assert transport.messages[-1] == {
        "protocol_version": "0.1", "type": "render", "duration": expected["duration"],
        "commands": [{"channel": c["channel"], "intensity": c["intensity"]} for c in expected["commands"]],
    }
    clock.now += 6
    with pytest.raises(StalePreview, match="already submitted"):
        hardware.send(store, ticket)
    assert len(transport.messages) == 3


@pytest.mark.parametrize("caps,duration,diagnostic", [
    (capabilities(), 31, "duration"),
    (capabilities(channels=[DeviceChannelCapability(1)]), 5, "channel"),
    (capabilities(channels=[DeviceChannelCapability(1, max_intensity=0.5), DeviceChannelCapability(2)]), 5, "intensity"),
])
def test_full_capability_preflight_rejects_without_emission(caps, duration, diagnostic):
    hardware, transport, _ = setup_hardware(FakeTransport(caps=caps))
    hardware.connect("SIMULATED")
    store = PreviewStore()
    ticket, _ = make_preview(store, duration=duration)
    for action in (hardware.check, hardware.send):
        with pytest.raises(HardwareError, match=diagnostic):
            action(store, ticket)
    assert len(transport.messages) == 2


def test_empty_semantic_plan_can_be_previewed_but_not_sent():
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for item in document["resources"][1]["data"]["annotations"]:
        item["state"] = "absent"
    result = preview(json.dumps(document))
    assert result["plans"]["semantic"]["commands"] == []
    payload = {"client_id": "test-browser-session", "revision": 1}
    store = PreviewStore()
    store.begin(payload)
    ticket = store.publish(payload, result)
    hardware, transport, _ = setup_hardware()
    hardware.connect("SIMULATED")
    with pytest.raises(HardwareError, match="empty plan"):
        hardware.send(store, ticket)
    assert len(transport.messages) == 2


def test_stale_invalidated_expired_and_forged_previews_are_refused():
    clock = Clock()
    store = PreviewStore(clock=clock)
    ticket, result = make_preview(store)
    newer = {"client_id": ticket["client_id"], "revision": 2}
    store.begin(newer)
    with pytest.raises(StalePreview, match="during calculation"):
        store.publish(ticket, result)
    with pytest.raises(StalePreview):
        with store.current(ticket):
            pytest.fail("Old preview is active")
    with pytest.raises(StalePreview, match="Outdated"):
        store.begin(ticket)
    ticket, _ = make_preview(store, revision=3)
    for forged in ({**ticket, "commands": []}, {**ticket, "preview_id": "invented"}):
        with pytest.raises(StalePreview):
            with store.current(forged):
                pytest.fail("Forged preview accepted")
    clock.now += 601
    with pytest.raises(StalePreview, match="expired"):
        with store.current(ticket):
            pytest.fail("Expired preview accepted")


def test_simultaneous_send_disconnect_and_connect_are_serialized():
    hardware, transport, opened = setup_hardware()
    hardware.connect("SIMULATED")
    store = PreviewStore()
    first, _ = make_preview(store)
    second, _ = make_preview(store, client="second-browser-session")
    transport.entered, transport.release = threading.Event(), threading.Event()
    failures = []

    def send():
        try:
            hardware.send(store, first)
        except Exception as exc:
            failures.append(exc)

    worker = threading.Thread(target=send)
    worker.start()
    try:
        assert transport.entered.wait(5)
        assert hardware.status()["operation_pending"]
        for action in (lambda: hardware.send(store, first), lambda: hardware.send(store, second),
                       hardware.disconnect, lambda: hardware.connect("OTHER")):
            with pytest.raises(HardwareError, match="already in progress"):
                action()
    finally:
        transport.release.set()
        worker.join(5)
    assert failures == []
    assert opened == ["SIMULATED"]
    assert len(transport.messages) == 3


def test_execution_window_blocks_new_plans_and_survives_disconnect():
    clock = Clock()
    hardware, transport, opened = setup_hardware(clock=clock)
    hardware.connect("SIMULATED")
    store = PreviewStore()
    ticket, _ = make_preview(store)
    hardware.send(store, ticket)
    new_ticket, _ = make_preview(store, revision=2)
    with pytest.raises(HardwareError, match="local estimate"):
        hardware.send(store, new_ticket)
    hardware.disconnect()
    assert transport.closed == 1
    with pytest.raises(HardwareError, match="execution window"):
        hardware.connect("SIMULATED")
    assert opened == ["SIMULATED"]
    clock.now += 6
    assert hardware.status()["remaining_seconds"] == 0
    assert hardware.status()["execution"]["state"] == "accepted"  # Never "completed".
    assert len(transport.messages) == 3  # No Stop message.


@pytest.mark.parametrize("reply", [TimeoutError("No response"), OSError("USB removed"), "", "bad json",
                                    {"type": "ok"}, {"protocol_version": "0.1", "type": "error", "code": "bad"}])
def test_possible_send_without_usable_reply_is_uncertain_and_never_retried(reply):
    transport = FakeTransport()
    transport.replies[-1] = reply
    hardware, _, opened = setup_hardware(transport)
    hardware.connect("SIMULATED")
    store = PreviewStore()
    ticket, _ = make_preview(store)
    with pytest.raises(HardwareError, match="Execution uncertain"):
        hardware.send(store, ticket)
    status = hardware.status()
    assert status["connection"] == "disconnected"
    assert status["execution"]["state"] == "uncertain"
    assert status["remaining_seconds"] == 5
    assert "may have reached" in status["message"]
    assert transport.closed == 1
    with pytest.raises(StalePreview, match="already submitted"):
        hardware.send(store, ticket)
    assert opened == ["SIMULATED"]
    assert len(transport.messages) == 3


def test_device_rejection_is_reported_faithfully_without_retry():
    transport = FakeTransport()
    rejection = error_response("busy", "Device busy")
    transport.replies[-1] = rejection
    hardware, _, _ = setup_hardware(transport)
    hardware.connect("SIMULATED")
    store = PreviewStore()
    ticket, _ = make_preview(store)
    with pytest.raises(HardwareError, match="busy: Device busy"):
        hardware.send(store, ticket)
    status = hardware.status()
    assert status["execution"]["state"] == "rejected"
    assert status["execution"]["response"] == rejection
    assert status["remaining_seconds"] == 0
    assert len(transport.messages) == 3
    assert transport.closed == 0


@pytest.mark.parametrize("fail_reset", [False, True])
def test_real_transport_configuration_and_startup_failure_cleanup(monkeypatch, fail_reset):
    import opensmell.experimental.serial_device_transport as sdk
    events = []

    class FakeSerial:
        def write(self, value):
            return len(value)

        def readline(self):
            return b""

        def flush(self):
            pass

        def reset_input_buffer(self):
            events.append("discard")
            if fail_reset:
                raise OSError("Startup preparation failed")

        def close(self):
            events.append("close")

    def serial_factory(**kwargs):
        events.append(kwargs)
        return FakeSerial()

    monkeypatch.setitem(sys.modules, "serial", SimpleNamespace(Serial=serial_factory))
    monkeypatch.setattr(sdk.time, "sleep", lambda seconds: events.append(seconds))
    if fail_reset:
        with pytest.raises(OSError, match="Startup"):
            open_transport("COM_TEST")
    else:
        open_transport("COM_TEST").close()
    assert events == [{"port": "COM_TEST", "baudrate": 115200, "timeout": 2.0, "write_timeout": 2.0},
                      2.0, "discard", "close"]


def request(server, method, path, payload=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, None if payload is None else json.dumps(payload),
                           headers=headers or {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


@pytest.fixture
def simulated_server():
    hardware, transport, opened = setup_hardware()
    server = create_server(0, hardware=hardware)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, transport, opened
    server.shutdown()
    server.server_close()
    thread.join(5)
    assert hardware.status()["connection"] == "disconnected"
    if opened:
        assert transport.closed == 1


def test_http_hardware_boundary_and_preview_freshness(simulated_server):
    server, transport, opened = simulated_server
    assert request(server, "GET", "/api/hardware/status")[1]["connection"] == "disconnected"
    assert request(server, "GET", "/api/hardware/ports")[0] == 200
    for path in ("connect", "disconnect", "send"):
        assert request(server, "GET", f"/api/hardware/{path}")[0] == 404
        assert request(server, "POST", f"/api/hardware/{path}", {},
                       {"Content-Type": "application/json", "Origin": "https://other.example"})[0] == 403
    assert opened == []
    assert request(server, "POST", "/api/hardware/connect", {"port": "SIMULATED"})[0] == 200
    payload = {"client_id": "test-browser-session", "revision": 1, "duration": 5}
    code, result = request(server, "POST", "/api/preview", payload)
    assert code == 200
    ticket = result["preview_ticket"]
    assert request(server, "POST", "/api/hardware/check", ticket)[1]["ready"]
    assert len(transport.messages) == 2
    # A failed recalculation must still revoke the previous sendable preview.
    assert request(server, "POST", "/api/preview", {**payload, "revision": 2, "duration": 0})[0] == 400
    assert request(server, "POST", "/api/hardware/send", ticket)[0] == 409
    _, result = request(server, "POST", "/api/preview", {**payload, "revision": 3})
    ticket = result["preview_ticket"]
    assert request(server, "POST", "/api/hardware/send", {**ticket, "commands": []})[0] == 409
    assert request(server, "POST", "/api/hardware/send", ticket)[1]["execution"]["state"] == "accepted"
    assert request(server, "POST", "/api/hardware/send", ticket)[0] == 409
    assert request(server, "POST", "/api/hardware/disconnect", {})[0] == 200
    assert [m["type"] for m in transport.messages] == ["hello", "get_capabilities", "render"]


def test_server_shutdown_closes_an_open_connection(simulated_server):
    server, _, _ = simulated_server
    assert request(server, "POST", "/api/hardware/connect", {"port": "SIMULATED"})[0] == 200
    # Fixture shutdown, without an explicit disconnect, asserts closure.
