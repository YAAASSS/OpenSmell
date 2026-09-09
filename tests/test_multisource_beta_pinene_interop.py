"""Cross-language interoperability checks for the multi-source beta-pinene fixture."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from opensmell.experimental.annotation import register_annotation_resource_type
from opensmell.experimental.generic_graph import (
    create_default_resource_type_registry,
    generic_graph_loads,
)
from opensmell.experimental.molecule import register_molecule_resource_type


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "multisource_beta_pinene.osmell"
VERIFIER = ROOT / "tools" / "verify_multisource_beta_pinene_interop.js"


def _registry():
    registry = create_default_resource_type_registry()
    register_molecule_resource_type(registry)
    register_annotation_resource_type(registry)
    return registry


def test_multisource_beta_pinene_fixture_loads_with_registered_types() -> None:
    graph = generic_graph_loads(FIXTURE.read_text(encoding="utf-8"), registry=_registry())

    assert len(graph) == 5
    assert len(graph.unknown_resources(registry=_registry())) == 0


def test_javascript_reserialization_is_readable_by_python(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available")

    output = tmp_path / "multisource_beta_pinene_js.json"
    completed = subprocess.run(
        [node, str(VERIFIER), str(FIXTURE), str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, (
        f"JavaScript verifier failed.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
    )
    assert "Multi-source beta-pinene interoperability: 8 passed, 0 failed" in completed.stdout

    original_raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    javascript_raw = json.loads(output.read_text(encoding="utf-8"))
    assert javascript_raw == original_raw

    graph = generic_graph_loads(output.read_text(encoding="utf-8"), registry=_registry())
    assert len(graph) == 5
    assert len(graph.unknown_resources(registry=_registry())) == 0
