"""Import byte boundaries through isolated HTTP servers, with no serial access."""

from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import threading

import pytest

from apps.local_demo import __main__ as app
from apps.local_demo.hardware import HardwareService
from apps.local_demo.preview_store import StalePreview
from apps.local_demo.service import FIXTURE


LIMIT = 1_048_576
CLIENT = "import-size-test-client"


def graph_text(size, *, token="a", bom=False):
    """Build a valid fixture graph with an opaque extension of exact byte size."""
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    prefix = ("\ufeff" if bom else "") + json.dumps(document)[:-1] + ',"import_test":"'
    suffix = '"}'
    escaped = json.dumps(token, ensure_ascii=False)[1:-1]
    budget = size - len((prefix + suffix).encode("utf-8"))
    count, remainder = divmod(budget, len(escaped.encode("utf-8")))
    text = prefix + escaped * count + " " * remainder + suffix
    assert len(text.encode("utf-8")) == size
    # Even the rejected cases must be valid graphs, not malformed JSON padding.
    assert json.loads(text.removeprefix("\ufeff"))["resources"] == document["resources"]
    return text


@pytest.fixture
def server():
    def no_serial(*args, **kwargs):
        pytest.fail("Import test attempted a serial operation")

    hardware = HardwareService(factory=no_serial, ports=no_serial, available=lambda: False)
    httpd = app.create_server(0, hardware=hardware)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(5)
        assert not thread.is_alive()
        assert hardware.status()["connection"] == "disconnected"


def post(server, payload=None, *, body=None):
    if body is None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request("POST", "/api/preview", body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def assert_plans(result):
    for policy, expected in (("semantic", {1: 0.6, 2: 1.0}),
                             ("perceptual", {0: 0.01, 1: 0.86, 2: 0.97})):
        plan = result["plans"][policy]
        assert {command["channel"]: command["intensity"] for command in plan["commands"]} == expected
        assert plan["duration"] == 5


@pytest.mark.parametrize("size", [LIMIT - 1, LIMIT, LIMIT + 1])
@pytest.mark.parametrize("token", ["a", "é🧪", '\\"'])
def test_direct_import_byte_boundaries(server, monkeypatch, size, token):
    text = graph_text(size, token=token)
    calls = []
    original = app.preview

    def preview_spy(received, **kwargs):
        calls.append(received)
        return original(received, **kwargs)

    monkeypatch.setattr(app, "preview", preview_spy)
    # Deliberately false client metadata must not affect the server's count.
    code, result = post(server, {"source": "file", "text": text, "size": 1})
    if size <= LIMIT:
        assert code == 200
        assert calls == [text]
        assert_plans(result)
        assert result["document"]["import_test"] == json.loads(text)["import_test"]
    else:
        assert code == 413
        assert result == {"error": "File too large: the limit is 1 MiB (1,048,576 bytes)."}
        assert calls == []  # Rejected before graph loading or mapper execution.
    assert "preview_ticket" not in result  # Direct untracked requests cannot be sent.
    assert not server.previews.clients


@pytest.mark.parametrize("size", [LIMIT - 1, LIMIT, LIMIT + 1])
def test_bom_counts_as_three_bytes_before_parsing(server, monkeypatch, size):
    text = graph_text(size, token="é\ufeff", bom=True)
    original = app.preview
    calls = []

    def preview_spy(received, **kwargs):
        calls.append(received)
        return original(received, **kwargs)

    monkeypatch.setattr(app, "preview", preview_spy)
    code, result = post(server, {"source": "file", "text": text})
    if size <= LIMIT:
        assert code == 200
        assert calls == [text[1:]]  # Only the initial BOM is ignored after sizing.
        assert result["document"]["import_test"] == json.loads(text[1:])["import_test"]
        assert_plans(result)
    else:
        assert code == 413
        assert calls == []


@pytest.mark.parametrize("encoding", ["ascii-escaped-unicode", "all-source-characters-escaped"])
def test_admissible_graph_with_large_json_transport(server, encoding):
    if encoding == "ascii-escaped-unicode":
        text = graph_text(LIMIT, token="é🧪")
        body = json.dumps({"source": "file", "text": text}).encode("ascii")
    else:
        text = graph_text(LIMIT)
        assert text.isascii()
        body = ('{"source":"file","text":"' +
                "".join(f"\\u{ord(char):04x}" for char in text) + '"}').encode("ascii")
    assert 2 * 1024 * 1024 < len(body) < app.MAX_BODY
    code, result = post(server, body=body)
    assert code == 200
    assert_plans(result)
    assert result["document"]["import_test"] == json.loads(text)["import_test"]


@pytest.mark.parametrize("size", [6_356_991, 6_356_992])
def test_http_envelope_boundary_accepts_valid_graph(server, size):
    body = json.dumps({"source": "file", "text": graph_text(8192)}).encode("utf-8")
    body += b" " * (size - len(body))
    assert len(body) == size
    code, result = post(server, body=body)
    assert code == 200
    assert_plans(result)


def test_http_envelope_overflow_is_rejected_before_reading_body(server, monkeypatch):
    original = app.preview

    def unexpected_preview(*args, **kwargs):
        pytest.fail("Oversized envelope reached graph processing")

    monkeypatch.setattr(app, "preview", unexpected_preview)
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.putrequest("POST", "/api/preview")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "6356993")
        connection.endheaders()
        # No body is sent: waiting to read it would time out rather than return 413.
        response = connection.getresponse()
        assert response.status == 413
        assert json.loads(response.read()) == {
            "error": "HTTP request too large: the limit is 6,356,992 bytes (6 MiB + 64 KiB).",
        }
    finally:
        connection.close()
    assert not server.previews.clients
    monkeypatch.setattr(app, "preview", original)
    assert post(server, {"source": "file", "text": graph_text(8192)})[0] == 200


def test_oversized_import_revokes_previous_preview_and_allows_recovery(server):
    payload = {"client_id": CLIENT, "revision": 1, "source": "file", "text": graph_text(8192)}
    code, result = post(server, payload)
    assert code == 200
    old_ticket = result["preview_ticket"]
    code, result = post(server, {**payload, "revision": 2, "text": graph_text(LIMIT + 1)})
    assert code == 413
    assert "preview_ticket" not in result
    assert server.previews.clients[CLIENT]["plan"] is None
    with pytest.raises(StalePreview):
        with server.previews.current(old_ticket):
            pytest.fail("Rejected import left the old preview usable")
    assert post(server, payload)[0] == 409  # An older revision cannot restore it.
    code, result = post(server, {**payload, "revision": 3, "text": graph_text(LIMIT)})
    assert code == 200
    assert_plans(result)
    with server.previews.current(result["preview_ticket"]) as entry:
        assert not entry["used"]


def test_late_calculation_cannot_publish_after_oversized_import(server, monkeypatch):
    started, release = threading.Event(), threading.Event()
    original = app.preview

    def delayed_preview(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(app, "preview", delayed_preview)
    payload = {"client_id": CLIENT, "revision": 1, "source": "file", "text": graph_text(8192)}
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(post, server, payload)
        try:
            assert started.wait(5)
            assert post(server, {**payload, "revision": 2, "text": graph_text(LIMIT + 1)})[0] == 413
        finally:
            release.set()
        code, result = pending.result(timeout=5)
    assert code == 409
    assert "preview_ticket" not in result
    assert server.previews.clients[CLIENT]["plan"] is None
