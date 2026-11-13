"""Archive interchange and normal builder refusal; full installed trial runs in CI."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from tools.build_developer_kit import make_archive

ROOT = Path(__file__).resolve().parents[1]


def test_archive_preserves_arbitrary_bytes_and_build_context():
    original = b'\xef\xbb\xbf{"unknown":123456789012345678901,"null":null}\r\n'
    artifacts = {"data/source.osmell": original, "packages/local.tgz": b"\x00\xff\x01"}
    source = {"checkout_commit": "test-source", "checkout_dirty": True}
    raw = make_archive(artifacts, source)
    assert raw == make_archive(dict(reversed(list(artifacts.items()))), source)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["source"] == source
        assert manifest["physical_validation"] is False
        assert set(archive.namelist()) == {*artifacts, "manifest.json"}
        for name, expected in artifacts.items():
            assert archive.read(name) == expected
            identity = manifest["files"][name]
            assert identity["sha256"] == hashlib.sha256(expected).hexdigest()
            assert identity["byte_length"] == len(expected)


def test_builder_entry_refuses_existing_output_before_build(tmp_path):
    target = tmp_path / "existing.zip"
    target.write_bytes(b"keep this artifact")
    result = subprocess.run([sys.executable, "-m", "tools.build_developer_kit", "--output", str(target)],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "Output already exists" in result.stderr
    assert target.read_bytes() == b"keep this artifact"
