"""Explicit, trusted software-only command selected at server startup.

This is not a sandbox. No command can be supplied or changed through HTTP.
The child is started only by Connect and never restarted automatically.
"""
from .process_transport import ProcessTransport
from .simulator import SimulatedHardwareService


class SoftwareAdapterService(SimulatedHardwareService):
    endpoint_port = "SOFTWARE"
    endpoint_description = "User-selected software adapter; experimental"
    endpoint_label = "Software adapter"
    endpoint_scope = "Software test mode; no physical compatibility claimed."

    def __init__(self, command, expected_device_id):
        if (not isinstance(command, (list, tuple)) or not command
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)
                or not command[0].strip()):
            raise ValueError("Provide a nonempty executable and its separate arguments.")
        if (not isinstance(expected_device_id, str) or not expected_device_id.strip()
                or len(expected_device_id) > 256
                or any(char in expected_device_id for char in "\r\n\0")):
            raise ValueError("Provide the expected software device ID (1–256 characters).")
        self._command = tuple(command)
        self._selection = {
            "kind": "custom-software", "executable": command[0],
            "expected_device_id": expected_device_id,
            "software_only_basis": "User-selected test mode, not verified physical isolation.",
        }
        super().__init__(factory=lambda _: ProcessTransport(self._command, startup_timeout=5.0),
                         expected_device_id=expected_device_id)
        self._message = "Software adapter selected. Click Connect to launch it and verify its identity and capabilities."

    def status(self):
        result = super().status()
        result["software_adapter"] = dict(self._selection)
        return result

    def evidence(self, report_id):
        result = super().evidence(report_id)
        result["software_adapter"] = dict(self._selection)
        result["limitations"].append(
            "Custom executable selected for software testing; not sandboxed or certified. "
            "The simulated flag describes the selected mode, not measured physical isolation. "
            "Command arguments are not exported."
        )
        return result
