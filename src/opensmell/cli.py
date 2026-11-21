"""Installed command-line tools for OpenSmell files and explicit native software replay.

File/plan/frame-export commands are passive. The explicitly selected native replay
launches trusted software over process pipes, never a serial port or physical device.
The CLI's strict text boundary additionally rejects duplicate JSON members.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from ._json import decode_bytes as _decode
from . import __version__
from .exceptions import OpenSmellError
from .schemes import get_definition
from .validation import validate_document
from .experimental.annotation import register_annotation_resource_type
from .experimental.generic_graph import (
    GENERIC_RESOURCE_GRAPH_FORMAT,
    GenericResource,
    create_default_resource_type_registry,
    generic_graph_from_dict,
)
from .experimental.molecule import register_molecule_resource_type
from .experimental.reference_discovery import discover_graph_references
from .experimental.planning import plan_with_profile
from .experimental.rendering import RenderRequest


def _graph_registry():
    registry = create_default_resource_type_registry()
    register_molecule_resource_type(registry)
    register_annotation_resource_type(registry)
    return registry


def _core_summary(document: dict[str, Any]) -> dict[str, Any]:
    validate_document(document)
    odor = document["odor"]
    representations = []
    warnings = []
    for index, representation in enumerate(odor["representations"]):
        scheme = representation["scheme"]
        known = get_definition(scheme["id"], scheme["version"]) is not None
        representations.append({
            "type": representation["type"],
            "scheme": scheme,
            "scheme_validation": "validated" if known else "unknown",
            "provenance": representation.get("provenance"),
        })
        if not known:
            warnings.append({
                "code": "unknown_scheme",
                "path": f"$.odor.representations[{index}].scheme",
                "message": "Envelope accepted; scheme payload semantics are not validated.",
            })
    return {
        "format": "opensmell-core",
        "version": document["opensmell"],
        "odor_id": odor["id"],
        "metadata": odor.get("metadata"),
        "representations": representations,
        "warnings": warnings,
    }


def _graph_summary(document: dict[str, Any]) -> dict[str, Any]:
    registry = _graph_registry()
    graph = generic_graph_from_dict(document, registry=registry)
    references = discover_graph_references(graph)
    ids = graph.ids()
    unresolved = [
        {"source_id": ref.source_id, "target_id": ref.target_id}
        for ref in references if ref.target_id not in ids
    ]
    warnings = []
    resources = []
    for index, (resource, raw) in enumerate(zip(graph.resources, document["resources"])):
        unknown = isinstance(resource, GenericResource)
        resources.append({
            "id": resource.id,
            "type": raw["type"],
            "type_version": raw.get("type_version"),
            "type_validation": "unknown" if unknown else "validated",
            "provenance": raw.get("provenance"),
        })
        if unknown:
            warnings.append({
                "code": "unknown_resource_type",
                "path": f"$.resources[{index}]",
                "message": "Envelope accepted; resource semantics and references are not inspected.",
            })
    if unresolved:
        warnings.append({
            "code": "unresolved_references",
            "path": "$.resources",
            "message": "Some known structural references target resources outside this file; this is permitted.",
        })
    return {
        "format": document["format"],
        "version": document["version"],
        "experimental": True,
        "resource_count": len(resources),
        "resource_types": dict(sorted(Counter(r["type"] for r in resources).items())),
        "resources": resources,
        "known_reference_count": len(references),
        "unresolved_references": unresolved,
        "warnings": warnings,
    }


def inspect_bytes(raw: bytes) -> dict[str, Any]:
    """Validate one UTF-8 file and describe it without rewriting its bytes.

    Unknown contracts are permitted by the format and explicitly disclosed.
    Provenance is reported as supplied, not independently authenticated.
    """
    document = _decode(raw)
    if not isinstance(document, dict):
        raise ValueError("document root must be a JSON object")
    if "opensmell" in document and "format" in document:
        raise ValueError("ambiguous envelope: both 'opensmell' and 'format' are present")
    if "opensmell" in document:
        summary = _core_summary(document)
    elif document.get("format") == GENERIC_RESOURCE_GRAPH_FORMAT:
        summary = _graph_summary(document)
    else:
        raise ValueError("unsupported document format; expected Core 0.1 or generic ResourceGraph 0.1")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw), **summary}


def _reference_graph_command(args):
    from .experimental.reference_graph import export_reference_graph, MAX_BYTES
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.file).open("rb") as source:
                raw = source.read(MAX_BYTES + 1)
        result = export_reference_graph(raw, args.output_directory)
        print(json.dumps(result, allow_nan=False))
        return 0
    except OSError as error:
        print(json.dumps({"status":"error", "error":str(error)})); return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        print(json.dumps({"status":"invalid", "error":str(error)})); return 1


def _replay_frame_command(args):
    from .experimental.native_replay import replay_frame
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(24 * 1048576 + 1)
        else:
            with Path(args.file).open("rb") as source:
                raw = source.read(24 * 1048576 + 1)
        # Reserve before any selected executable can launch. A crash leaves an
        # incomplete marker; an existing report cannot cause a duplicate replay.
        with Path(args.output).open("x", encoding="utf-8") as output:
            def save(report):
                output.seek(0); output.truncate()
                json.dump(report, output, ensure_ascii=True, allow_nan=False, indent=2)
                output.write("\n"); output.flush()
            save({"status": "incomplete", "acceptance": "not_established", "physical_validation": False})
            try:
                report = replay_frame(raw, args.native_host, on_progress=save)
            except Exception as error:
                save({"status": "invalid", "acceptance": "not_established", "error": str(error), "physical_validation": False})
                raise
            save(report)
        print(json.dumps(report, ensure_ascii=True, allow_nan=False))
        return 0 if report["status"] == "accepted" else 3 if report["status"] in {"rejected", "incompatible"} else 1
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1


def _lifecycle_trial_command(args):
    from .experimental.lifecycle_trial import lifecycle_trial, MAX_BYTES
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.file).open("rb") as source:
                raw = source.read(MAX_BYTES + 1)
        command = _decode(args.software_command_json.encode())
        with Path(args.output).open("x", encoding="utf-8") as output:
            def save(report):
                output.seek(0); output.truncate()
                json.dump(report, output, allow_nan=False, indent=2)
                output.write("\n"); output.flush()
            save({"status": "incomplete", "acceptance": "not_attempted", "physical_validation": False})
            report = lifecycle_trial(raw, command, expected_device_id=args.expected_device_id, on_progress=save)
            save(report)
        print(json.dumps(report, allow_nan=False))
        return 0 if report["status"] == "passed" else 3 if report["status"] in {"rejected", "incompatible"} else 1
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1


def _prepare_experiment_command(args):
    from .experimental.experiment import prepare_experiment
    import csv
    try:
        inputs = []
        for name, bound in ((args.table, 65536), (args.graph, 8*1048576), (args.profile, 1048576)):
            with Path(name).open("rb") as source:
                inputs.append(source.read(bound+1))
        report = prepare_experiment(*inputs, args.output_directory)
        print(json.dumps(report, allow_nan=False)); return 0
    except OSError as error:
        print(json.dumps({"status":"error","error":str(error)})); return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError, csv.Error) as error:
        print(json.dumps({"status":"invalid","error":str(error)})); return 1


def _sequence_command(args):
    from .experimental.software_sequence import run_software_sequence, MAX_BYTES
    try:
        if not 1 <= len(args.files) <= 16:
            raise ValueError("A sequence requires 1–16 explicit plan files")
        inputs = []
        for name in args.files:
            with Path(name).open("rb") as source:
                inputs.append(source.read(MAX_BYTES + 1))
            if sum(map(len, inputs)) > 16 * 1048576:
                raise ValueError("Combined inputs exceed 16 MiB")
        command = _decode(args.software_command_json.encode())
        with Path(args.output).open("x", encoding="utf-8") as output:
            def save(report):
                output.seek(0); output.truncate()
                json.dump(report, output, allow_nan=False, indent=2)
                output.write("\n"); output.flush()
            report = run_software_sequence(inputs, command, expected_device_id=args.expected_device_id, on_progress=save)
        print(json.dumps(report, allow_nan=False))
        return 0 if report["status"] == "completed" else 3 if report["status"] in {"rejected", "incompatible", "stopped", "cancelled"} else 1
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1


def _encode_frame_command(args):
    from .experimental.frame_export import encode_plan_frame
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(8 * 1048576 + 1)
        else:
            with Path(args.file).open("rb") as source:
                raw = source.read(8 * 1048576 + 1)
        with Path(args.capabilities).open("rb") as source:
            capabilities = source.read(1048576 + 1)
        report = encode_plan_frame(raw, capabilities, max_message_bytes=args.max_message_bytes)
        output = (json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()
        if args.output:
            with Path(args.output).open("xb") as target:
                target.write(output)
        else:
            sys.stdout.buffer.write(output)
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1
    return 0


def _plan_core_command(args):
    from .experimental.core_planning import plan_core_bytes, MAX_CORE_BYTES
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(MAX_CORE_BYTES+1)
        else:
            with Path(args.file).open("rb") as source:
                raw = source.read(MAX_CORE_BYTES+1)
        with Path(args.profile).open("rb") as source:
            profile = source.read(1048576+1)
        artifact = plan_core_bytes(raw, profile, representation_index=args.representation_index, duration=args.duration)
        encoded = (json.dumps(artifact,indent=2,allow_nan=False,ensure_ascii=True)+"\n").encode()
        if len(encoded) > 8*1048576:
            raise ValueError("Serialized offline plan exceeds8MiB")
        if args.output:
            with Path(args.output).open("xb") as target: target.write(encoded)
        else:
            sys.stdout.buffer.write(encoded)
        return 0
    except OSError as error:
        print(json.dumps({"status":"error","error":str(error)}),file=sys.stderr); return 2
    except (OpenSmellError,ValueError,TypeError,KeyError,RecursionError,OverflowError) as error:
        print(json.dumps({"status":"invalid","error":str(error)}),file=sys.stderr); return 1


def _plan_command(args: argparse.Namespace) -> int:
    """Produce a passive planning artifact, not an executable wire request."""
    try:
        raw = sys.stdin.buffer.read() if args.file == "-" else Path(args.file).read_bytes()
        profile_raw = Path(args.profile).read_bytes()
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=True))
        return 2
    try:
        source = inspect_bytes(raw)
        if source["format"] != GENERIC_RESOURCE_GRAPH_FORMAT:
            raise ValueError("plan currently requires a generic ResourceGraph; Core bridging is not automatic")
        document = _decode(raw)
        profile = _decode(profile_raw)
        # Check finite numbers in every extension before emitting strict JSON.
        json.dumps(profile, allow_nan=False)
        graph = generic_graph_from_dict(document, registry=_graph_registry())
        request = RenderRequest(resource_id=args.resource_id, duration=args.duration)
        plan = plan_with_profile(graph, request, profile)
    except (OpenSmellError, ValueError, TypeError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}, ensure_ascii=True))
        return 1
    print(json.dumps({
        "format": "org.opensmell.experimental.offline-plan",
        "version": "0.1",
        "status": "planned",
        "execution": "not_attempted",
        "capability_basis": "supplied_profile_not_live_device",
        "source": {"input": args.file, **source, "document": document},
        "profile": {"input": args.profile, "sha256": hashlib.sha256(profile_raw).hexdigest(),
                    "document": profile},
        "request": {"resource_id": request.resource_id, "duration": request.duration},
        "plan": {"duration": plan.duration, "commands": [
            {"channel": command.channel, "intensity": command.intensity} for command in plan.commands
        ], "extra": plan.extra},
        "limitations": ["Application-defined channel mapping; no universal odor primaries.",
                        "No hardware access, device acceptance, execution or odor reproduction is established."],
    }, ensure_ascii=True, allow_nan=False, indent=2))
    return 0


def _observation_table_command(args):
    from .experimental.observation_table import observation_table, MAX_BYTES
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.file).open("rb") as source:
                raw = source.read(MAX_BYTES + 1)
        report = observation_table(raw)
        encoded = (json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()
        if args.output:
            with Path(args.output).open("xb") as output:
                output.write(encoded)
        else:
            sys.stdout.buffer.write(encoded)
        return 3 if report["status"] == "partial" else 0
    except OSError as error:
        print(json.dumps({"status":"error", "error":str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, RecursionError, OverflowError) as error:
        print(json.dumps({"status":"invalid", "error":str(error)}), file=sys.stderr)
        return 1


def _import_perceptual_command(args):
    import csv
    from .experimental.perceptual_import import import_keller_csv, MAX_CSV_BYTES, MAX_SOURCE_BYTES
    from .experimental.generic_graph import generic_graph_to_dict
    from .experimental.core_interchange import interchange_registry
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read(MAX_CSV_BYTES + 1)
        else:
            with Path(args.file).open("rb") as input_file:
                raw = input_file.read(MAX_CSV_BYTES + 1)
        with Path(args.source).open("rb") as declaration:
            source_raw = declaration.read(MAX_SOURCE_BYTES + 1)
        if len(source_raw) > MAX_SOURCE_BYTES:
            raise ValueError("Source declaration exceeds 1 MiB")
        graph = import_keller_csv(raw, row=args.row, source=_decode(source_raw))
        output = (json.dumps(generic_graph_to_dict(graph, registry=interchange_registry()),
                             ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()
        if args.output:
            with Path(args.output).open("xb") as target:
                target.write(output)
        else:
            sys.stdout.buffer.write(output)
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, csv.Error, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1
    return 0


def _import_csv_command(args):
    import csv
    from .experimental.csv_import import import_odornet_csv
    from .serializer import _serialize_document
    try:
        raw = sys.stdin.buffer.read() if args.file == "-" else Path(args.file).read_bytes()
        source = _decode(Path(args.source).read_bytes())
        document = import_odornet_csv(raw, row=args.row, source=source)
        output = (_serialize_document(document) + "\n").encode("utf-8")
        if args.output:
            with Path(args.output).open("xb") as target:
                target.write(output)
        else:
            sys.stdout.buffer.write(output)
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, csv.Error, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1
    return 0


def _batch_csv_command(args):
    import csv
    from .experimental.csv_import import import_odornet_csv_batch, extract_batch_record
    code = 0
    try:
        raw = sys.stdin.buffer.read() if args.file == "-" else Path(args.file).read_bytes()
        if args.command == "import-odornet-batch":
            result = import_odornet_csv_batch(raw, rows=args.rows, source=_decode(Path(args.source).read_bytes()))
            output = (json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()
            code = 3 if result["counts"]["rejected"] else 0
        else:
            output = extract_batch_record(raw, row=args.row)
        if args.output:
            with Path(args.output).open("xb") as target:
                target.write(output)
        else:
            sys.stdout.buffer.write(output)
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, KeyError, csv.Error, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1
    return code


def _bridge_command(args):
    from .experimental.core_interchange import (
        bridge_core_bytes, extract_core_bytes, interchange_registry,
    )
    from .experimental.generic_graph import generic_graph_to_dict
    try:
        raw = sys.stdin.buffer.read() if args.file == "-" else Path(args.file).read_bytes()
        if args.command == "bridge-core":
            result = bridge_core_bytes(raw)
            output = (json.dumps(generic_graph_to_dict(result.graph, registry=interchange_registry()),
                                 ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("utf-8")
        else:
            output = extract_core_bytes(raw)
        if args.output:
            # Exclusive create prevents overwriting source or another deliverable.
            with Path(args.output).open("xb") as target:
                target.write(output)
        else:
            sys.stdout.buffer.write(output)
    except OSError as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    except (OpenSmellError, ValueError, TypeError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 1
    return 0


def _text_result(result: dict[str, Any], *, detailed: bool) -> str:
    # Escape file-controlled text so terminal control characters are not emitted.
    def quoted(value: Any) -> str:
        return json.dumps(value, ensure_ascii=True)

    prefix = f"{quoted(result['input'])}: {result['status'].upper()}"
    if result["status"] != "valid":
        return f"{prefix} - {quoted(result['error']['message'])}"
    lines = [f"{prefix} ({result['format']} {result['version']})"]
    if detailed:
        lines.append(f"  SHA-256: {result['sha256']}")
        if "odor_id" in result:
            lines.append(f"  Odor: {quoted(result['odor_id'])}")
            lines.append(f"  Metadata: {quoted(result['metadata'])}")
            for rep in result["representations"]:
                lines.append(f"  Representation: {quoted(rep)}")
        else:
            lines.append(f"  Resources: {result['resource_count']}; known references: {result['known_reference_count']}")
            for resource in result["resources"]:
                lines.append(f"  Resource: {quoted(resource)}")
            for ref in result["unresolved_references"]:
                lines.append(f"  Unresolved reference: {quoted(ref)}")
    for warning in result["warnings"]:
        lines.append(f"  Warning {warning['code']}: {warning['path']} - {warning['message']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="opensmell",
        description="Inspect, import and plan offline; explicitly selected software trials are opt-in.",
    )
    parser.add_argument("--version", action="version", version=f"OpenSmell {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "inspect"):
        subparser = commands.add_parser(command, help=f"{command.capitalize()} Core or experimental graph files")
        subparser.add_argument("files", nargs="+", help="UTF-8 file paths; '-' reads standard input once")
        subparser.add_argument("--json", action="store_true", help="Print one JSON report for all inputs")
    core_planning = commands.add_parser("plan-core", help="Plan one explicitly selected Core semantic representation passively")
    core_planning.add_argument("file", help="Core0.1 file or stdin (-); max4MiB")
    core_planning.add_argument("--representation-index", type=int, required=True, help="Explicit zero-based semantic annotations0.1 representation index")
    core_planning.add_argument("--profile", required=True, help="Explicit semantic mapping/capability profile")
    core_planning.add_argument("--duration", type=float, required=True, help="Explicit requested duration in seconds")
    core_planning.add_argument("--output", help="New normal offline-plan JSON artifact; never overwrite")
    planning = commands.add_parser("plan", help="Create an offline JSON plan from a graph and explicit profile")
    planning.add_argument("file", help="Generic ResourceGraph file; '-' reads stdin")
    planning.add_argument("--profile", required=True, help="Mapping profile JSON file")
    planning.add_argument("--resource-id", required=True, help="Explicit graph resource to map")
    planning.add_argument("--duration", type=float, required=True, help="Requested seconds")
    for name, help_text in (
        ("bridge-core", "Project Core 0.1 into a graph retaining the original source"),
        ("extract-core", "Recover the original Core source embedded in an imported graph"),
    ):
        bridge = commands.add_parser(name, help=help_text)
        bridge.add_argument("file", help="Input file; '-' reads stdin")
        bridge.add_argument("--output", help="Create a new output file; existing paths are refused")
    importer = commands.add_parser("import-odornet", help="Import one explicit OdorNet-shaped CSV record")
    importer.add_argument("file", help="UTF-8 CSV input; '-' reads stdin")
    importer.add_argument("--row", type=int, required=True, help="One-based data record, excluding header")
    importer.add_argument("--source", required=True, help="Source/license manifest JSON")
    importer.add_argument("--output", help="Create a new Core file; existing paths are refused")
    perceptual = commands.add_parser("import-keller", help="Import one prepared Keller/Vosshall-shaped CSV observation as a graph")
    perceptual.add_argument("file", help="UTF-8 CSV; '-' reads stdin; 8 MiB maximum")
    perceptual.add_argument("--row", type=int, required=True, help="One-based logical data record, excluding header")
    perceptual.add_argument("--source", required=True, help="Source/license/preparation/rating-scale declaration JSON")
    perceptual.add_argument("--output", help="New graph file; existing paths are refused")
    batch = commands.add_parser("import-odornet-batch", help="Import explicit CSV records with per-record outcomes")
    batch.add_argument("file", help="UTF-8 CSV; '-' reads stdin")
    batch.add_argument("--rows", required=True, nargs="+", type=int, help="Unique one-based data records")
    batch.add_argument("--source", required=True, help="Source manifest JSON")
    batch.add_argument("--output", help="Create a new batch JSON file; never overwrite")
    extract = commands.add_parser("extract-csv-record", help="Extract one accepted Core record from a CSV batch")
    extract.add_argument("file", help="Batch JSON; '-' reads stdin")
    extract.add_argument("--row", required=True, type=int)
    extract.add_argument("--output", help="Create a new Core file; never overwrite")
    encoder = commands.add_parser("encode-frame", help="Export a checked offline plan as protocol frame data; never send")
    encoder.add_argument("file", help="Offline-plan artifact JSON; '-' reads stdin")
    encoder.add_argument("--capabilities", required=True, help="Explicit target capability response JSON")
    encoder.add_argument("--max-message-bytes", type=int, default=1024, help="Message bound excluding LF; ESP32 reference default 1024")
    encoder.add_argument("--output", help="New export artifact JSON; never overwrite")
    replay = commands.add_parser("replay-frame", help="Replay an export against an explicit trusted native software harness; no hardware")
    replay.add_argument("file", help="Frame export artifact; '-' reads stdin")
    replay.add_argument("--native-host", required=True, help="Explicit trusted native harness executable, not a serial port")
    replay.add_argument("--output", required=True, help="New checkpointed native transcript; never overwrite")
    trial = commands.add_parser("lifecycle-trial", help="Try an explicit trusted software adapter with an offline plan; no hardware")
    trial.add_argument("file", help="Explicit 5-second offline-plan artifact; '-' reads stdin; 8MiB maximum")
    trial.add_argument("--software-command-json", required=True, help="Trusted software executable/argument JSON array; no shell; report retains arguments")
    trial.add_argument("--expected-device-id", required=True, help="Explicit endpoint identity; never inferred from source")
    trial.add_argument("--output", required=True, help="New checkpointed trial report; never overwrite")
    experiment = commands.add_parser("prepare-experiment", help="Compile an explicit ordered CSV trial table into passive offline plans")
    experiment.add_argument("table", help="UTF-8 CSV with trial_id,resource_id,duration; max 64 KiB")
    experiment.add_argument("--graph", required=True, help="Explicit source ResourceGraph")
    experiment.add_argument("--profile", required=True, help="Explicit mapping/capability profile for every trial")
    experiment.add_argument("--output-directory", required=True, help="New portable experiment directory; never overwrite")
    sequence = commands.add_parser("run-sequence", help="Run explicit offline plans in order on trusted software; no hardware")
    sequence.add_argument("files", nargs="+", help="1–16 explicit offline-plan JSON files in execution order; no stdin")
    sequence.add_argument("--software-command-json", required=True, help="Trusted executable/argument JSON array; no shell; arguments retained")
    sequence.add_argument("--expected-device-id", required=True, help="Explicit software endpoint identity")
    sequence.add_argument("--output", required=True, help="New checkpointed sequence report; never overwrite")
    table = commands.add_parser("observation-table", help="Project graph measurements for analysis, preserving source/context; never execute")
    table.add_argument("file", help="Generic ResourceGraph; '-' reads stdin; 8 MiB maximum")
    table.add_argument("--output", help="New JSON analysis artifact; never overwrite")
    reference = commands.add_parser("reference-graph", help="Export known structural references as GraphML with exact source; no device action")
    reference.add_argument("file", help="Generic ResourceGraph file or stdin (-); 8 MiB maximum")
    reference.add_argument("--output-directory", required=True, help="New bundle directory; never overwrite")
    args = parser.parse_args(argv)
    if args.command == "plan-core":
        return _plan_core_command(args)
    if args.command == "prepare-experiment":
        return _prepare_experiment_command(args)
    if args.command == "run-sequence":
        return _sequence_command(args)
    if args.command == "reference-graph":
        return _reference_graph_command(args)
    if args.command == "lifecycle-trial":
        return _lifecycle_trial_command(args)
    if args.command == "observation-table":
        return _observation_table_command(args)
    if args.command == "import-keller":
        return _import_perceptual_command(args)
    if args.command == "replay-frame":
        return _replay_frame_command(args)
    if args.command == "encode-frame":
        return _encode_frame_command(args)
    if args.command in {"import-odornet-batch", "extract-csv-record"}:
        return _batch_csv_command(args)
    if args.command == "import-odornet":
        return _import_csv_command(args)
    if args.command in {"bridge-core", "extract-core"}:
        return _bridge_command(args)
    if args.command == "plan":
        return _plan_command(args)
    if args.files.count("-") > 1:
        parser.error("standard input '-' can appear only once")

    results = []
    exit_code = 0
    for filename in args.files:
        result: dict[str, Any] = {"input": filename}
        try:
            raw = sys.stdin.buffer.read() if filename == "-" else Path(filename).read_bytes()
        except OSError as error:
            result.update(status="error", error={"code": "input_error", "message": str(error)})
            exit_code = 2
        else:
            try:
                summary = inspect_bytes(raw)
            except (OpenSmellError, ValueError, TypeError, RecursionError) as error:
                result.update(status="invalid", error={"code": "invalid_document", "message": str(error)})
                exit_code = max(exit_code, 1)
            else:
                result.update(status="valid", **summary)
        results.append(result)

    if args.json:
        print(json.dumps({
            "report_version": "0.1",
            "command": args.command,
            "results": results,
        }, ensure_ascii=True, indent=2, allow_nan=False))
    else:
        print("\n".join(_text_result(result, detailed=args.command == "inspect") for result in results))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
