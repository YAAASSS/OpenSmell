"""Bounded, revisioned, single-use previews. No hardware dependencies."""

from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
import secrets
import threading
import time

from opensmell.experimental.rendering import DeviceCommand, RenderingPlan


class StalePreview(ValueError):
    pass


class PreviewStore:
    def __init__(self, *, clock=time.monotonic, max_clients=64, lifetime=600):
        self.lock = threading.RLock()
        self.clients = OrderedDict()
        self.clock = clock
        self.max_clients = max_clients
        self.lifetime = lifetime

    @staticmethod
    def identity(payload):
        client = payload.get("client_id")
        revision = payload.get("revision")
        if not isinstance(client, str) or not 16 <= len(client) <= 80:
            raise StalePreview("A valid preview session is required. Reload the page.")
        if isinstance(revision, bool) or not isinstance(revision, int) or not 0 <= revision < 2**53:
            raise StalePreview("A valid preview revision is required.")
        return client, revision

    def begin(self, payload):
        client, revision = self.identity(payload)
        with self.lock:
            previous = self.clients.get(client)
            if previous and revision <= previous["revision"]:
                raise StalePreview("Outdated preview request. Recalculate before sending.")
            self.clients[client] = {"revision": revision, "plan": None}
            self.clients.move_to_end(client)
            while len(self.clients) > self.max_clients:
                self.clients.popitem(last=False)

    def publish(self, payload, result):
        client, revision = self.identity(payload)
        # Construct only from the trusted Python mapper result, never browser commands.
        data = result["plans"][result["policy"]]
        plan = RenderingPlan(
            commands=[DeviceCommand(**command) for command in data["commands"]],
            duration=data["duration"], extra=deepcopy(data["extra"]),
        )
        with self.lock:
            entry = self.clients.get(client)
            if entry is None or entry["revision"] != revision:
                raise StalePreview("Preview changed during calculation. Recalculate before sending.")
            entry.update(plan=plan, preview_id=secrets.token_urlsafe(24),
                         expires=self.clock() + self.lifetime, used=False)
            return {"client_id": client, "revision": revision, "preview_id": entry["preview_id"]}

    @contextmanager
    def current(self, ticket):
        if set(ticket) != {"client_id", "revision", "preview_id"}:
            raise StalePreview("Send only the preview ticket, not a browser-generated command list.")
        client, revision = self.identity(ticket)
        with self.lock:
            entry = self.clients.get(client)
            if (not entry or entry["revision"] != revision or entry["plan"] is None
                    or entry["preview_id"] != ticket.get("preview_id")
                    or self.clock() >= entry["expires"]):
                raise StalePreview("Preview is outdated or expired. Recalculate before sending.")
            if entry["used"]:
                raise StalePreview("Preview already submitted. Recalculate for a new explicit send.")
            yield entry
