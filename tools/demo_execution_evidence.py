"""Capture and diagnose three real Node simulator runs through Local Explorer HTTP.

Explicit software demonstration only. Never loads commands from an evidence file.
"""
import argparse
import http.client
import json
from pathlib import Path
import threading
import time

from apps.local_demo.__main__ import create_server
from apps.local_demo.process_transport import NODE_DEVICE_ID, node_transport
from apps.local_demo.simulator import SimulatedHardwareService
from tools.diagnose_execution_evidence import diagnose


def capture(destination):
    # Require a fresh directory: never overwrite earlier experimental evidence.
    destination.mkdir(parents=True, exist_ok=False)
    hardware = SimulatedHardwareService(factory=node_transport, expected_device_id=NODE_DEVICE_ID)
    server = create_server(0, hardware=hardware)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def api(route, data=None):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
            connection.request('GET' if data is None else 'POST', '/api/' + route,
                               body=None if data is None else json.dumps(data),
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            result = json.loads(response.read())
            if response.status != 200:
                raise RuntimeError(f'{route}: {result}')
            return result
        finally:
            connection.close()

    def send(revision):
        preview = api('preview', dict(client_id='evidence-walkthrough', revision=revision,
                                      duration=5, policy='semantic'))
        ticket = preview['preview_ticket']
        api('hardware/check', ticket)
        return api('hardware/send', ticket)

    def save(name, value):
        with (destination / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')

    try:
        api('hardware/connect', {'port':'SIMULATED'})
        first = send(1)
        deadline = time.monotonic() + 10
        while first['execution']['state'] in ('accepted', 'running') and time.monotonic() < deadline:
            time.sleep(0.1)
            first = api('hardware/status')
        if first['execution']['state'] != 'completed':
            raise RuntimeError('Node did not confirm completion within ten seconds')
        save('completed.json', api('hardware/evidence?report_id=' + first['evidence_id']))
        second = send(2)
        api('hardware/stop', {'execution_id': second['execution']['execution_id']})
        save('stopped.json', api('hardware/evidence?report_id=' + second['evidence_id']))
        third = send(3)
        api('hardware/disconnect', {})
        save('unknown.json', api('hardware/evidence?report_id=' + third['evidence_id']))
        bundle = api('hardware/evidence-history')
        save('history.json', bundle)
    finally:
        server.shutdown()
        worker.join()
        server.server_close()
        hardware.close()
    # Analysis starts only after all transports and the server have closed.
    result = diagnose(bundle)
    save('diagnostics.json', result)
    if [r['state'] for r in result['reports']] != ['unknown', 'stopped', 'completed'] or result['errors']:
        raise RuntimeError('Unexpected captured evidence; inspect saved reports')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='New output directory (must not exist)')
    args = parser.parse_args(argv)
    try:
        result = capture(args.directory)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f'Capture failed: {exc}. Existing outputs were not overwritten.\n')
    print(f"Saved completed, stopped and unknown evidence in {args.directory}")
    print(f"Offline verdict: {result['verdict']} (unknown is intentionally unresolved). No physical validation.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
