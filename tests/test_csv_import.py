import csv
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from copy import deepcopy

import pytest

from opensmell.experimental.csv_import import IMPORT_KEY, import_odornet_csv
from opensmell.experimental.core_interchange import bridge_core_bytes
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest
from opensmell.serializer import _serialize_document

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/synthetic_odornet.csv").read_bytes()
SOURCE = json.loads((ROOT / "examples/synthetic_odornet_source.json").read_bytes())


def rewrite(*, header=None, cells=None, extra_rows=()):
    rows = list(csv.reader(StringIO(RAW.decode())))
    out = StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(header if header is not None else rows[0])
    writer.writerow(cells if cells is not None else rows[1])
    writer.writerows(extra_rows)
    return out.getvalue().encode()


def test_selected_record_provenance_unknown_columns_and_plan():
    source = deepcopy(SOURCE)
    source["future"] = {"keep": [1, None]}
    result = import_odornet_csv(RAW, row=1, source=source)
    snapshot = result.extra[IMPORT_KEY]
    assert snapshot["raw_record"]["sample_note"].startswith("Synthetic")
    assert snapshot["headers"][-1] == "sample_note"
    assert snapshot["data_record"] == 1
    states = {a["value"]: a["state"] for a in result.odor.representations[1].data["annotations"]}
    assert states["floral"] == "present"
    assert states["animalic&ambery"] == "absent"
    assert states["sweety&gourmand"] == "unknown"
    assert result.odor.representations[0].extra["provenance"]["kind"] == "synthetic"
    assert result.odor.representations[0].extra["provenance"]["source"] != "OdorNet"
    source["future"]["keep"].append(2)
    assert snapshot["source"]["future"]["keep"] == [1, None]
    raw = _serialize_document(result).encode()
    imported = bridge_core_bytes(raw)
    profile = json.loads((ROOT / "examples/offline_semantic_profile.json").read_bytes())
    plan = plan_with_profile(imported.graph, RenderRequest(imported.primary_resource_id, 5), profile)
    assert [(c.channel, c.intensity) for c in plan.commands] == [(0, 0.25)]


def test_identity_deterministic_but_record_and_manifest_specific():
    first = import_odornet_csv(RAW, row=1, source=SOURCE)
    assert _serialize_document(first) == _serialize_document(import_odornet_csv(RAW, row=1, source=SOURCE))
    rows = list(csv.reader(StringIO(RAW.decode())))
    raw = rewrite(extra_rows=[rows[1]])
    assert import_odornet_csv(raw, row=1, source=SOURCE).odor.id != import_odornet_csv(raw, row=2, source=SOURCE).odor.id
    source = {**SOURCE, "license": "LicenseRef-Example"}
    assert first.odor.id != import_odornet_csv(RAW, row=1, source=source).odor.id


@pytest.mark.parametrize("row", [0, -1, True, 1.0, 2, "1"])
def test_invalid_or_missing_row(row):
    with pytest.raises(ValueError):
        import_odornet_csv(RAW, row=row, source=SOURCE)


@pytest.mark.parametrize("field", ["name", "url", "license", "kind"])
def test_missing_source_declaration(field):
    source = dict(SOURCE)
    del source[field]
    with pytest.raises(ValueError):
        import_odornet_csv(RAW, row=1, source=source)


@pytest.mark.parametrize("token", ["NaN", "true", "-1", "2", "NA", "0.5"])
def test_invalid_label_is_not_silently_absent(token):
    rows = list(csv.reader(StringIO(RAW.decode())))
    rows[1][3] = token
    with pytest.raises(ValueError, match="semantic value"):
        import_odornet_csv(rewrite(cells=rows[1]), row=1, source=SOURCE)


@pytest.mark.parametrize("fault", ["duplicate", "padded", "missing", "short", "long", "smiles", "utf8", "empty"])
def test_ambiguous_csv_refused(fault):
    rows = list(csv.reader(StringIO(RAW.decode())))
    header, cells = rows
    if fault == "duplicate":
        header[-1] = "SMILES"
    elif fault == "padded":
        header[0] = " SMILES"
    elif fault == "missing":
        header[3] = "unknown"
    elif fault == "short":
        cells.pop()
    elif fault == "long":
        cells.append("extra")
    elif fault == "smiles":
        cells[0] = " "
    raw = b"\xff" if fault == "utf8" else b"" if fault == "empty" else rewrite(header=header, cells=cells)
    with pytest.raises((ValueError, UnicodeError)):
        import_odornet_csv(raw, row=1, source=SOURCE)


def test_multiline_unknown_column_and_bom():
    rows = list(csv.reader(StringIO(RAW.decode())))
    rows[1][-1] = "keep\nmultiline, notes"
    raw = b"\xef\xbb\xbf" + rewrite(cells=rows[1])
    document = import_odornet_csv(raw, row=1, source=SOURCE)
    assert document.extra[IMPORT_KEY]["raw_record"]["sample_note"] == rows[1][-1]


def test_cli_source_errors_stdin_and_no_overwrite(tmp_path):
    def run(*args, data=None):
        return subprocess.run([sys.executable, "-m", "opensmell", "import-odornet", *map(str,args)],
                              input=data, capture_output=True)
    source = tmp_path / "source.json"
    source.write_text(json.dumps(SOURCE))
    out = tmp_path / "out.osmell"
    result = run("-", "--row", 1, "--source", source, "--output", out, data=RAW)
    assert result.returncode == 0 and result.stdout == result.stderr == b""
    before = out.read_bytes()
    assert json.loads(before)["opensmell"] == "0.1"
    assert run("-", "--row", 1, "--source", source, "--output", out, data=RAW).returncode == 2
    assert out.read_bytes() == before
    missing = tmp_path / "not-created"
    assert run("-", "--row", 99, "--source", source, "--output", missing, data=RAW).returncode == 1
    assert not missing.exists()
    source.write_text('{"kind":"synthetic","kind":"dataset"}')
    assert run("-", "--row", 1, "--source", source, data=RAW).returncode == 1
