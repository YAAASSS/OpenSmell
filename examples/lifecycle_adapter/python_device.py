"""Trusted software-only JSON-lines endpoint using the installed SDK simulator."""
import sys
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint

endpoint = SimulatedEndpoint()
try:
    for line in sys.stdin:
        if len(line.encode()) > 65536:
            raise ValueError("Request too large")
        print(endpoint.exchange(line), flush=True)
finally:
    endpoint.close()
