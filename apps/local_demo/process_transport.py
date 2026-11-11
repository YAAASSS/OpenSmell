"""Repository Node example binding; transport implementation lives in SDK."""
from pathlib import Path
from opensmell.experimental.process_transport import ProcessTransport, MAX_BYTES

NODE_DEVICE_ID = "opensmell-node-simulator-001"
EXAMPLE = Path(__file__).resolve().parents[2] / "examples/lifecycle_adapter/device.cjs"

def node_transport(_port):
    return ProcessTransport(["node", str(EXAMPLE)], startup_timeout=5.0)
