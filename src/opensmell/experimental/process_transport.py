"""Bounded JSON-lines transport for the explicitly selected software example.

No shell, network or serial access. A failed exchange closes the child so a late
reply cannot be consumed as the response to a later request. Trusted child commands are not sandboxed.
"""
import json
import math
import queue
import subprocess
import threading

MAX_BYTES = 65536


class ProcessTransport:
    def __init__(self, command, *, timeout=2.0):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be positive")
        if (not isinstance(command, (list, tuple)) or not command
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)
                or not command[0].strip()):
            raise ValueError("Provide an executable and separate arguments")
        self.timeout = timeout
        self._lock = threading.Lock()
        self._closed = False
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, shell=False)

    def exchange(self, message):
        data = message.encode("utf-8")
        if len(data) > MAX_BYTES or b'\n' in data or b'\r' in data:
            raise ValueError("Expected one bounded JSON line")
        json.loads(message)
        with self._lock:
            if self._closed:
                raise OSError("Software device link is closed")
            result = queue.Queue(maxsize=1)
            def transact():
                try:
                    self.process.stdin.write(data + b'\n')
                    self.process.stdin.flush()
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
                reply = result.get(timeout=self.timeout)
                if isinstance(reply, Exception):
                    raise reply
                return reply
            except queue.Empty as exc:
                self.close()
                raise TimeoutError("Software device response timed out; link closed") from exc
            except Exception:
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
