"""Exercise the normal caller-data entry with the real Python CLI, no mock pipeline."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from tools.build_developer_kit import PAYLOADS, make_archive

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def kit(tmp_path):
    target = tmp_path / "kit"
    payload = {name: (ROOT / source).read_bytes() for name, source in PAYLOADS.items()}
    with zipfile.ZipFile(io.BytesIO(make_archive(payload, {"test": True}))) as archive:
        archive.extractall(target)
    return target


def invoke(kit, *arguments):
    return subprocess.run([sys.executable, str(kit / "try_kit.py"), *map(str, arguments)],
                          cwd=kit.parent, capture_output=True, text=True, timeout=60)


def arguments(kit):
    return ["--csv", kit / "data/synthetic_odornet_batch.csv", "--source", kit / "data/source.json",
            "--profile", kit / "profiles/semantic.json"]


def test_passive_caller_selection_keeps_refusals_raw_values_and_profile(kit):
    result = invoke(kit, *arguments(kit), "--rows", "3", "2", "1", "99")
    assert result.returncode == 3, result.stderr
    report = json.loads(result.stdout)
    assert report["execution"] == "not_attempted"
    assert [x["row"] for x in report["records"]] == [3, 2, 1, 99]
    assert report["counts"] == {"planned": 2, "import_rejected": 2}
    assert report["records"][0]["plan"]["plan"]["commands"] == [{"channel": 1, "intensity": 0.6}]
    assert report["records"][2]["plan"]["plan"]["commands"] == [{"channel": 0, "intensity": 0.25}]
    assert report["batch"]["results"][1]["raw_cells"][3] == "2"
    assert all("software_observations" not in x for x in report["records"])


def test_unmappable_accepted_row_is_not_silently_dropped(kit, tmp_path):
    data = tmp_path / "custom.csv"
    with (kit / "data/synthetic_odornet_batch.csv").open(newline="") as source:
        rows = list(csv.reader(source))
    rows.append(["CCO", *(["0"] * 12), "Unknown column retained"])
    with data.open("w", newline="") as output:
        csv.writer(output).writerows(rows)
    args = arguments(kit)
    args[1] = data
    result = invoke(kit, *args, "--rows", "4")
    assert result.returncode == 3, result.stderr
    report = json.loads(result.stdout)
    record, = report["records"]
    assert record["import_status"] == "accepted"
    assert record["status"] == "planning_rejected"
    assert "no commands" in record["error"]["error"]
    assert report["batch"]["results"][0]["raw_cells"][-1] == "Unknown column retained"


@pytest.mark.parametrize("options", [["--csv", "missing"], ["--simulate"],
                                      ["--rows", "0"], ["--rows", "1", "1"]])
def test_invalid_entry_options_fail_before_work(kit, options):
    result = invoke(kit, *(arguments(kit) if options[0] == "--rows" else []), *options)
    assert result.returncode == 2
    assert not result.stdout


def test_existing_report_blocks_before_inputs_or_simulation(kit, tmp_path):
    report = tmp_path / "previous.json"
    report.write_bytes(b"keep previous evidence")
    args = arguments(kit)
    args[1] = tmp_path / "absent.csv"
    result = invoke(kit, *args, "--rows", "1", "--simulate", "--report", report)
    assert result.returncode == 2
    assert report.read_bytes() == b"keep previous evidence"


def test_bad_source_reserves_an_error_report_without_execution(kit, tmp_path):
    source = tmp_path / "bad.json"
    source.write_text('{"kind":"synthetic"}')
    report = tmp_path / "error.json"
    args = arguments(kit)
    args[3] = source
    result = invoke(kit, *args, "--rows", "1", "--report", report)
    assert result.returncode == 1
    retained = json.loads(report.read_bytes())
    assert retained["result"] == "error"
    assert retained["execution"] == "not_attempted"
    assert retained["error"]["phase"] == "import"
