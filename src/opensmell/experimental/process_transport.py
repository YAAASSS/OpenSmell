"""Bounded JSON-lines transport for the explicitly selected software example.

No shell, network or serial access. A failed exchange closes the child so a late
reply cannot be consumed as the response to a later request. Trusted child commands are not sandboxed.
"""
import json
import math
import queue
import subprocess
import threading
import time

MAX_BYTES = 65536


class ProcessTransport:
    """Use startup_timeout for the first reply, then timeout for later replies.

    Omitting startup_timeout preserves the same bound for every exchange.
    """

    def __init__(self, command, *, timeout=2.0, startup_timeout=None):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be positive")
        if startup_timeout is None:
            startup_timeout = timeout
        if (isinstance(startup_timeout, bool) or not isinstance(startup_timeout, (int, float))
                or not math.isfinite(startup_timeout) or startup_timeout <= 0):
            raise ValueError("Startup timeout must be positive")
        if (not isinstance(command, (list, tuple)) or not command
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)
                or not command[0].strip()):
            raise ValueError("Provide an executable and separate arguments")
        self.timeout = timeout
        self.startup_timeout = startup_timeout
        self._first_exchange = True
        self.last_exchange = None
        self._lock = threading.Lock()
        self._closed = False
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, shell=False)

    def exchange(self, message):
        data = message.encode("utf-8")
        if len(data) > MAX_BYTES or b'\n' in data or b'\r' in data:
            raise ValueError("Expected one bounded JSON line")
        request = json.loads(message)
        with self._lock:
            if self._closed:
                raise OSError("Software device link is closed")
            started = time.monotonic()
            deadline = self.startup_timeout if self._first_exchange else self.timeout
            timing = {"worker_started_seconds": None, "request_written_seconds": None}
            kind = request.get("type") if isinstance(request, dict) else None
            diagnostic = {"phase": "startup" if self._first_exchange else "exchange",
                          "request_type": kind if isinstance(kind, str) and len(kind) <= 128 else None,
                          "deadline_seconds": deadline}
            result = queue.Queue(maxsize=1)
            def transact():
                timing["worker_started_seconds"] = time.monotonic() - started
                try:
                    self.process.stdin.write(data + b'\n')
                    self.process.stdin.flush()
                    timing["request_written_seconds"] = time.monotonic() - started
                    line = self.process.stdout.readline(MAX_BYTES + 1)
                    if not line or len(line) > MAX_BYTES or not line.endswith(b'\n'):
                        raise OSError("Missing or oversized software device response")
                    reply = line.decode("utf-8")
                    if not isinstance(json.loads(reply), dict):
                        raise ValueError("Device response must be a JSON object")
                    result.put(reply)
                except Exception as exc:
                    result.put(exc)
            worker = threading.Thread(target=transact, daemon=True)
            worker.start()
            try:
                reply = result.get(timeout=deadline)
                if isinstance(reply, Exception):
                    raise reply
                self.last_exchange = {**diagnostic, **timing, "elapsed_seconds": time.monotonic() - started,
                                      "child_returncode": self.process.poll(), "outcome": "response"}
                self._first_exchange = False
                return reply
            except queue.Empty as exc:
                self.last_exchange = {**diagnostic, **timing, "elapsed_seconds": time.monotonic() - started,
                                      "child_returncode": self.process.poll(), "outcome": "timeout"}
                self.close()
                raise TimeoutError("Software device response timed out; link closed. " +
                                   json.dumps(self.last_exchange, sort_keys=True)) from exc
            except Exception:
                self.last_exchange = {**diagnostic, **timing, "elapsed_seconds": time.monotonic() - started,
                                      "child_returncode": self.process.poll(), "outcome": "error"}
                self.close()
                raise
            finally:
                worker.join(timeout=0.1)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=1)
        for stream in (self.process.stdin, self.process.stdout):
            stream.close()
