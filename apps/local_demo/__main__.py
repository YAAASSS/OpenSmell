"""Run with python -m apps.local_demo from the repository root."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlsplit
import webbrowser

from .service import FIXTURE, PROJECT_ROOT, PreviewError, preview
from .hardware import HardwareError, HardwareService
from .preview_store import PreviewStore, StalePreview

STATIC = Path(__file__).parent / "static"
MAX_IMPORT_BYTES = 1024 * 1024
# JSON may represent each source byte as six ASCII bytes (e.g. \u007b).
# Reserve another 64 KiB for the request fields, independently of the file cap.
MAX_BODY = 6 * MAX_IMPORT_BYTES + 64 * 1024
ASSETS = {
    "/": (STATIC / "index.html", "text/html; charset=utf-8"),
    "/app.css": (STATIC / "app.css", "text/css; charset=utf-8"),
    "/app.js": (STATIC / "app.js", "text/javascript; charset=utf-8"),
    "/hardware.js": (STATIC / "hardware.js", "text/javascript; charset=utf-8"),
    "/logo-full.png": (PROJECT_ROOT / "docs/images/OpenSmell_Official_Logo_Full.png", "image/png"),
    "/logo-small.png": (PROJECT_ROOT / "docs/images/OpenSmell_Official_Logo_Small.png", "image/png"),
}


class Handler(BaseHTTPRequestHandler):
    """Known assets and explicit local preview/hardware actions only."""

    def _local_request(self):
        authority = f"127.0.0.1:{self.server.server_port}"
        return (
            self.headers.get("Host") == authority
            and self.headers.get("Origin") in (None, f"http://{authority}")
            and self.headers.get("Sec-Fetch-Site") != "cross-site"
        )

    def _reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(
            data, ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._local_request():
            return self._reply(403, {"error": "Local access only, via 127.0.0.1."})
        route = urlsplit(self.path).path
        if route == "/api/hardware/status":
            return self._reply(200, self.server.hardware.status())
        if route == "/api/hardware/ports":
            try:
                return self._reply(200, self.server.hardware.ports())
            except HardwareError as exc:
                return self._reply(exc.status, {"error": str(exc)})
        asset = ASSETS.get(route)
        if asset is None:
            return self._reply(404, {"error": "Unknown resource."})
        path, content_type = asset
        try:
            data = path.read_bytes()
        except OSError:
            return self._reply(404, {"error": f"Required file missing: {path.name}"})
        self._reply(200, data, content_type)

    def do_POST(self):
        if not self._local_request():
            return self._reply(403, {"error": "Local access only, via 127.0.0.1."})
        if self.path not in {"/api/preview", "/api/preview/invalidate",
                             "/api/hardware/connect", "/api/hardware/disconnect",
                             "/api/hardware/check", "/api/hardware/send"}:
            return self._reply(404, {"error": "Unknown action."})
        if self.headers.get("Content-Type") != "application/json":
            return self._reply(415, {"error": "A JSON request is required."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > MAX_BODY:
                return self._reply(413, {"error": "HTTP request too large: the limit is 6,356,992 bytes (6 MiB + 64 KiB)."})
            if size <= 0:
                return self._reply(400, {"error": "A non-empty JSON request is required."})
            self.connection.settimeout(10)
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(payload, dict):
                raise PreviewError("The request must be a JSON object.")
            if self.path == "/api/preview/invalidate":
                self.server.previews.begin(payload)
                return self._reply(200, {"invalidated": True})
            if self.path.startswith("/api/hardware/"):
                hardware = self.server.hardware
                if self.path.endswith("/connect"):
                    if set(payload) != {"port"}:
                        raise HardwareError("Select exactly one serial port.", 400)
                    result = hardware.connect(payload["port"])
                elif self.path.endswith("/disconnect"):
                    if payload:
                        raise HardwareError("Disconnect does not accept commands.", 400)
                    result = hardware.disconnect()
                elif self.path.endswith("/check"):
                    result = hardware.check(self.server.previews, payload)
                else:
                    result = hardware.send(self.server.previews, payload)
                return self._reply(200, result)
            tracked = "client_id" in payload or "revision" in payload
            if tracked:
                self.server.previews.begin(payload)
            source = payload.get("source", "fixture")
            if source == "fixture":
                graph_text = FIXTURE.read_text(encoding="utf-8")
            elif source == "file" and isinstance(payload.get("text"), str):
                graph_text = payload["text"]
                # Measure the received text, not client metadata or reserialized JSON.
                # Count a leading UTF-8 BOM before ignoring it for graph parsing.
                if len(graph_text.encode("utf-8")) > MAX_IMPORT_BYTES:
                    return self._reply(413, {"error": "File too large: the limit is 1 MiB (1,048,576 bytes)."})
                if graph_text.startswith("\ufeff"):
                    graph_text = graph_text[1:]
            else:
                raise PreviewError("Unknown source or missing file content.")
            result = preview(
                graph_text,
                policy=payload.get("policy", "semantic"),
                duration=payload.get("duration", 5.0),
            )
            if tracked:
                result["preview_ticket"] = self.server.previews.publish(payload, result)
            self._reply(200, result)
        except HardwareError as exc:
            self._reply(exc.status, {"error": str(exc), "hardware": self.server.hardware.status()})
        except StalePreview as exc:
            self._reply(409, {"error": str(exc)})
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            self._reply(400, {"error": str(exc)})
        except OSError:
            self._reply(500, {"error": "Cannot read the local file. Check that the sample file exists and try again."})


class LocalServer(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, port, hardware=None):
        self.hardware = hardware if hardware is not None else HardwareService()
        self.previews = PreviewStore()
        super().__init__(("127.0.0.1", port), Handler)

    def server_close(self):
        try:
            super().server_close()
        finally:
            self.hardware.close()


def create_server(port=8765, *, hardware=None):
    return LocalServer(port, hardware)


def main():
    parser = argparse.ArgumentParser(description="OpenSmell — Local Explorer, offline preview and explicit ESP32 control.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()
    try:
        server = create_server(args.port)
    except (OSError, OverflowError) as exc:
        parser.exit(1, f"Could not start: {exc}. Try --port 8766.\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"OpenSmell — Experimental pre-alpha\n{url}\nPreview is offline. Hardware requires explicit Connect and Send to device actions. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
