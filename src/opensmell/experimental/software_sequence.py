"""Explicit offline plans to a bounded trusted software process sequence."""
from .process_transport import ProcessTransport
from .transport_sequence import MAX_BYTES, MAX_INPUT_BYTES, MAX_STEPS, prepare_steps, _run_sequence


def run_software_sequence(inputs, command, *, expected_device_id, on_progress=None):
    """Compatible software-only entry; no serial/GPIO selection or auto-retry."""
    selected = []
    def context():
        if (not isinstance(command, (list, tuple)) or not 1 <= len(command) <= 64
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)
                or not command[0].strip() or sum(map(len, command)) > 16384):
            raise ValueError("Explicit command must be an executable/argument array (max64 items/16KiB)")
        selected[:] = command
        return {"command": list(selected)}
    report = {"format": "org.opensmell.experimental.software-sequence", "version": "0.1",
              "experimental": True, "physical_validation": False, "status": "incomplete",
              "phase": "preflight", "transcript": [], "sequence": None,
              "scope": "Trusted software process pipes only; no physical observations"}
    return _run_sequence(inputs, lambda: ProcessTransport(list(selected), startup_timeout=5),
                         expected_device_id=expected_device_id, on_progress=on_progress,
                         stop_requested=None, report=report, validate_context=context)
