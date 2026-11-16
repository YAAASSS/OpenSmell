"""Prepared scientific input boundaries and observation-to-plan semantics."""
import csv
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys

import pytest

from opensmell.experimental.perceptual_import import IMPORT_KEY, MAX_CSV_BYTES, import_keller_csv
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.resources import Observation

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/synthetic_keller.csv").read_bytes()
SOURCE = json.loads((ROOT / "examples/synthetic_keller_source.json").read_bytes())
PROFILE = json.loads((ROOT / "examples/offline_perceptual_profile.json").read_bytes())


def change(**values):
    rows = list(csv.reader(StringIO(RAW.decode())))
    for key, value in values.items():
        rows[1][rows[0].index(key)] = value
    out = StringIO(newline="")
    csv.writer(out).writerows(rows)
    return out.getvalue().encode()


def selected(raw=RAW, row=1, source=SOURCE):
    graph = import_keller_csv(raw, row=row, source=source)
    return graph, next(x for x in graph.resources if isinstance(x, Observation))


def test_values_missing_zero_context_and_explicit_plan():
    source = deepcopy(SOURCE)
    graph, observation = selected(source=source)
    context = graph.extra[IMPORT_KEY]
    values = {x["property"]: x for x in observation.results[-1].data["measurements"]}
    assert values["grass"] == {"property": "grass", "value": 0, "scale": {"min": 0, "max": 100}, "unit": "rating"}
    assert "pleasantness" not in values and "familiarity" not in values
    assert values["flower"]["value"] == 26 and values["wood"]["value"] == 89
    assert context["raw_record"]["HOW PLEASANT IS THE SMELL?"] == ""
    assert context["raw_record"]["sample_note"].startswith("Synthetic")
    stimulus = graph.get(observation.stimulus.resource_id)
    assert stimulus.conditions[0].value == "1/1,000"
    assert graph.get(stimulus.source.resource_id) is not None
    assert graph.get(observation.target.resource_id) is not None
    categories = observation.results[0]
    assert categories.scheme.id.endswith(".categories") and categories.data["detection"] == "unknown"
    assert categories.data["source_fields"]["CAN OR CAN'T SMELL"] == "I smell something"
    source["context"]["future_field"].append(9)
    assert context["source"]["context"]["future_field"] == ["retained", None]
    plan = plan_with_profile(graph, RenderRequest(observation.id, 5), PROFILE)
    assert sorted((x.channel, x.intensity) for x in plan.commands) == [(0, .26), (1, 0), (2, .89)]


def test_same_declared_subject_cid_different_presentations_never_join_or_average():
    first, one = selected()
    second, two = selected(row=2)
    assert {x.id for x in first.resources}.isdisjoint(x.id for x in second.resources)
    assert one.id == selected()[1].id
    assert one.id != selected(source={**SOURCE, "license": "LicenseRef-Other"})[1].id
    plan = plan_with_profile(second, RenderRequest(two.id, 5), PROFILE)
    assert sorted((x.channel, x.intensity) for x in plan.commands) == [(0, .8), (1, .2)]


def test_all_unmeasured_imports_but_cannot_plan_and_zero_remains_actionable():
    graph, observation = selected(row=3)
    assert graph.extra[IMPORT_KEY]["measurement_count"] == 0
    assert len(observation.results) == 1 and observation.results[0].scheme.id.endswith(".categories")
    with pytest.raises(ValueError, match="no commands"):
        plan_with_profile(graph, RenderRequest(observation.id, 5), PROFILE)
    graph, observation = selected(change(FLOWER="0", GRASS="0", WOOD="0"))
    assert [x.intensity for x in plan_with_profile(graph, RenderRequest(observation.id, 5), PROFILE).commands] == [0, 0, 0]


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-1", "101", "NA", "true", "not measured", "1,5"])
def test_invalid_numeric_is_refused_not_silently_missing(token):
    with pytest.raises(ValueError):
        selected(change(FLOWER=token))


@pytest.mark.parametrize("row", [0, -1, True, 1.0, "1", 99])
def test_invalid_or_absent_selection(row):
    with pytest.raises(ValueError):
        selected(row=row)


@pytest.mark.parametrize("field", ["name", "url", "license", "preparation", "kind", "rating_scale"])
def test_source_requires_explicit_context(field):
    source = deepcopy(SOURCE); del source[field]
    with pytest.raises(ValueError):
        selected(source=source)


@pytest.mark.parametrize("scale", [{"min": 0, "max": 10, "unit": "rating"}, {"min": False, "max": 100, "unit": "rating"},
                                    {"min": 0, "max": 100, "unit": "ppm"}])
def test_unsupported_scale_never_rescaled_or_mislabeled(scale):
    with pytest.raises(ValueError):
        selected(source={**SOURCE, "rating_scale": scale})


@pytest.mark.parametrize("field,value", [("CID", "1.0"), ("CID", ""), ("CID", "-1"), ("Odor dilution", ""),
                                         ("Odor", " "), ("Subject # (this study)", "")])
def test_incomplete_identity_refused(field, value):
    with pytest.raises(ValueError):
        selected(change(**{field: value}))


def test_csv_contract_and_limits():
    for raw in (b"", RAW.replace(b"FLOWER", b"GRASS", 1), RAW.replace(b"CID,", b" CID,", 1),
                RAW.replace(b"CID,", b"Unknown,", 1), b"\xff", b"x" * (MAX_CSV_BYTES + 1),
                RAW.splitlines(keepends=True)[0] + b"1,short\n"):
        with pytest.raises((ValueError, csv.Error)):
            selected(raw)
    # CRLF/BOM and embedded newlines are legal; row indexes count CSV records.
    graph, observation = selected(b"\xef\xbb\xbf" + change(sample_note="line one\nline two"))
    assert graph.extra[IMPORT_KEY]["raw_record"]["sample_note"] == "line one\nline two"
    assert observation.id


def test_cli_normal_entry_stdin_exclusive_output_and_invalid_source(tmp_path):
    def cli(*args, raw=RAW):
        return subprocess.run([sys.executable, "-m", "opensmell", *args], input=raw, capture_output=True, cwd=tmp_path, timeout=15)
    source = ROOT / "examples/synthetic_keller_source.json"
    output = tmp_path / "observation.osmell"
    args = ("import-keller", "-", "--source", str(source), "--row", "1", "--output", str(output))
    assert cli(*args).returncode == 0
    saved = output.read_bytes()
    assert cli(*args).returncode == 2 and output.read_bytes() == saved
    assert cli("validate", str(output), "--json").returncode == 0
    assert cli("import-keller", "-", "--source", str(source), "--row", "4").returncode == 1
    (tmp_path / "bad.json").write_text('{"kind":"synthetic","kind":"dataset"}')
    assert cli("import-keller", "-", "--source", "bad.json", "--row", "1").returncode == 1
