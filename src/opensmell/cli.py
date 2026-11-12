"""Installed, passive command-line tools for OpenSmell files.

No application, transport, device command or network access is used here.
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
        description="Validate, inspect and plan with OpenSmell files without connecting a device.",
    )
    parser.add_argument("--version", action="version", version=f"OpenSmell {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "inspect"):
        subparser = commands.add_parser(command, help=f"{command.capitalize()} Core or experimental graph files")
        subparser.add_argument("files", nargs="+", help="UTF-8 file paths; '-' reads standard input once")
        subparser.add_argument("--json", action="store_true", help="Print one JSON report for all inputs")
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
    args = parser.parse_args(argv)
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
