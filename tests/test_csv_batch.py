from copy import deepcopy
import csv
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys

import pytest

from opensmell.experimental.csv_import import (
    IMPORT_KEY, import_odornet_csv, import_odornet_csv_batch, extract_batch_record,
)
from opensmell.serializer import _document_to_dict

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/synthetic_odornet_batch.csv").read_bytes()
SOURCE = json.loads((ROOT / "examples/synthetic_odornet_source.json").read_bytes())


def encoded(value):
    return json.dumps(value).encode()


def test_mixed_selection_preserves_order_source_and_single_api_identity():
    batch = import_odornet_csv_batch(RAW, rows=[3, 2, 1, 99], source=SOURCE)
    assert batch["requested_records"] == [3, 2, 1, 99]
    assert batch["status"] == "partial"
    assert batch["counts"] == {"accepted": 2, "rejected": 2}
    assert [r["status"] for r in batch["results"]] == ["accepted", "rejected", "accepted", "rejected"]
    assert batch["results"][1]["raw_cells"][3] == "2"
    assert batch["results"][-1]["error"]["code"] == "missing_record"
    for row in [1, 3]:
        document = json.loads(extract_batch_record(encoded(batch), row=row))
        assert document == _document_to_dict(import_odornet_csv(RAW, row=row, source=SOURCE))
        assert document[IMPORT_KEY]["csv_sha256"] == batch["csv_sha256"]
        assert document[IMPORT_KEY]["raw_record"]["sample_note"].startswith("Synthetic")
    batch["results"][0]["document"][IMPORT_KEY]["source"]["name"] = "changed"
    assert batch["source"]["name"] == SOURCE["name"]
    assert batch["results"][2]["document"][IMPORT_KEY]["source"]["name"] == SOURCE["name"]


@pytest.mark.parametrize("rows", [[], [True], [0], [-1], [1, 1], [1.0], "1", list(range(1, 1002))])
def test_invalid_selection_is_fatal(rows):
    with pytest.raises(ValueError):
        import_odornet_csv_batch(RAW, rows=rows, source=SOURCE)


@pytest.mark.parametrize("rows,status", [([1, 3], "accepted"), ([2, 99], "rejected")])
def test_all_valid_and_all_rejected(rows, status):
    batch = import_odornet_csv_batch(RAW, rows=rows, source=SOURCE)
    assert batch["status"] == status
    assert batch == import_odornet_csv_batch(RAW, rows=rows, source=SOURCE)


@pytest.mark.parametrize("row", [2, 99, 5, True, 0])
def test_rejected_missing_unselected_and_invalid_extraction(row):
    batch = import_odornet_csv_batch(RAW, rows=[1, 2, 99], source=SOURCE)
    with pytest.raises(ValueError):
        extract_batch_record(encoded(batch), row=row)


@pytest.mark.parametrize("fault", ["hash", "context", "identity", "duplicate", "source", "format", "counts", "status"])
def test_tampered_bundle_rejected(fault):
    batch = import_odornet_csv_batch(RAW, rows=[1, 3], source=SOURCE)
    entry = batch["results"][0]
    if fault == "hash":
        entry["document"]["odor"]["id"] = "changed"
    elif fault == "context":
        batch["csv_sha256"] = "0" * 64
    elif fault == "identity":
        batch["source_manifest_sha256"] = "0" * 64
    elif fault == "duplicate":
        batch["results"][1]["data_record"] = 1
    elif fault == "source":
        batch["source"]["name"] = "changed"
    elif fault == "counts":
        batch["counts"]["rejected"] = 7
    elif fault == "status":
        batch["status"] = "rejected"
    else:
        batch["format"] = "unknown"
    with pytest.raises(ValueError):
        extract_batch_record(encoded(batch), row=1)


def test_malformed_syntax_does_not_publish_partial_bundle():
    with pytest.raises(csv.Error):
        import_odornet_csv_batch(RAW + b'"unterminated', rows=[1, 4], source=SOURCE)


def test_cli_partial_exit_and_exclusive_outputs(tmp_path):
    def run(*args, data=None):
        return subprocess.run([sys.executable, "-m", "opensmell", *map(str,args)],
                              input=data, capture_output=True)
    source = tmp_path / "source.json"
    source.write_text(json.dumps(SOURCE))
    output = tmp_path / "batch.json"
    args = ("import-odornet-batch", "-", "--rows", 1, 2, 3, 9, "--source", source, "--output", output)
    result = run(*args, data=RAW)
    assert result.returncode == 3 and result.stdout == result.stderr == b""
    before = output.read_bytes()
    assert run(*args, data=RAW).returncode == 2
    assert output.read_bytes() == before
    core = tmp_path / "core.osmell"
    assert run("extract-csv-record", output, "--row", 1, "--output", core).returncode == 0
    assert run("validate", core, "--json").returncode == 0
    assert run("extract-csv-record", output, "--row", 1, "--output", core).returncode == 2
    missing = tmp_path / "rejected.osmell"
    assert run("extract-csv-record", output, "--row", 2, "--output", missing).returncode == 1
    assert not missing.exists()
    fatal = tmp_path / "fatal.json"
    assert run("import-odornet-batch", "-", "--rows", 1, 1, "--source", source,
               "--output", fatal, data=RAW).returncode == 1
    assert not fatal.exists()
