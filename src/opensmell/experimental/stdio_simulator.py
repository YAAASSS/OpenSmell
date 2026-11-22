"""Bounded JSON-lines entry for the SDK software simulator; never hardware."""
import json
import sys

from .._json import decode_bytes
from .device_protocol import error_response
from .lifecycle_simulator import SimulatedEndpoint, ERROR_PROFILE

MAX_MESSAGE_BYTES = 65536


def serve(input_stream, output_stream, error_stream):
    """Serve binary UTF-8 LF messages. Bad framing closes without accepting it.

    Complete malformed JSON gets a protocol refusal; no banners/logs on stdout.
    Request timing and execution IDs remain owned by SimulatedEndpoint.
    """
    endpoint = SimulatedEndpoint()
    try:
        while True:
            line = input_stream.readline(MAX_MESSAGE_BYTES + 2)
            if not line:
                return 0
            if not line.endswith(b'\n') or len(line)-1 > MAX_MESSAGE_BYTES:
                error_stream.write('Invalid simulator framing: require LF and at most 65536 message bytes\n')
                return 1
            raw = line[:-1]
            try:
                decode_bytes(raw)
            except (ValueError, TypeError, RecursionError) as error:
                reply = json.dumps({**error_response('invalid_request',str(error)[:512]), 'error_profile':ERROR_PROFILE})
            else:
                reply = endpoint.exchange(raw.decode('utf-8'))
            output_stream.write(reply+'\n')
            output_stream.flush()
    finally:
        endpoint.close()


def main():
    return serve(sys.stdin.buffer,sys.stdout,sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())
